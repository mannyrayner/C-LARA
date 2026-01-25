from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages

from .models import CLARAProject, HumanAudioInfo, PhoneticHumanAudioInfo
from .clara_main import CLARAProjectInternal

from django_q.tasks import async_task
from .forms import ProjectCreationForm
from .forms import ProjectImportForm
from .utils import get_user_config, create_internal_project_id, make_asynch_callback_and_report_id
from .utils import user_has_a_project_role
from .utils import get_task_updates
from .utils import uploaded_file_to_file

#from .clara_main import CLARAProjectInternal
from .clara_export_import import change_project_id_in_imported_directory, update_multimedia_from_imported_directory
from .clara_export_import import get_global_metadata, rename_files_in_project_dir, update_metadata_file_paths
from .clara_utils import get_config, local_file_exists, remove_file
from .clara_utils import local_directory_exists, remove_local_directory
from .clara_utils import copy_local_file_to_s3_if_necessary, copy_s3_file_to_local_if_necessary
from .clara_utils import post_task_update
from .clara_utils import unzip_file

import os
import logging
import traceback
import tempfile

config = get_config()
logger = logging.getLogger(__name__)

# Create a new project
@login_required
def create_project(request):
    if request.method == 'POST':
        form = ProjectCreationForm(request.POST)
        if form.is_valid():
            # Extract the validated data from the form
            title = form.cleaned_data['title']
            l2_language = form.cleaned_data['l2']
            l1_language = form.cleaned_data['l1']
            uses_coherent_image_set = form.cleaned_data['uses_coherent_image_set']
            uses_coherent_image_set_v2 = form.cleaned_data['uses_coherent_image_set_v2']
            use_translation_for_images = form.cleaned_data['use_translation_for_images']
            if uses_coherent_image_set and uses_coherent_image_set_v2:
                messages.error(request, "The coherent image set cannot be both V1 and V2")
                return render(request, 'clara_app/create_project.html', {'form': form})
            # Create a new project in Django's database, associated with the current user
            clara_project = CLARAProject(title=title,
                                         user=request.user,
                                         l2=l2_language,
                                         l1=l1_language,
                                         uses_coherent_image_set=uses_coherent_image_set,
                                         uses_coherent_image_set_v2=uses_coherent_image_set_v2,
                                         use_translation_for_images=use_translation_for_images)
            clara_project.save()
            internal_id = create_internal_project_id(title, clara_project.id)
            # Update the Django project with the internal_id
            clara_project.internal_id = internal_id
            clara_project.save()
            # Create a new internal project in the C-LARA framework
            clara_project_internal = CLARAProjectInternal(internal_id, l2_language, l1_language)
            return redirect('project_detail', project_id=clara_project.id)
        else:
            # The form data was invalid. Re-render the form with error messages.
            return render(request, 'clara_app/create_project.html', {'form': form})
    else:
        # This is a GET request, so create a new blank form
        form = ProjectCreationForm()

        clara_version = get_user_config(request.user)['clara_version']
        
        return render(request, 'clara_app/create_project.html', {'form': form, 'clara_version':clara_version})

# This is the function to run in the worker process when importing a zipfile
def import_project_from_zip_file(zip_file, project_id, internal_id, callback=None):
    try:
        clara_project = get_object_or_404(CLARAProject, pk=project_id)
        # If we're on Heroku, the main thread should have copied the zipfile to S3 so that we can get it
        copy_s3_file_to_local_if_necessary(zip_file, callback=callback)
        if not local_file_exists(zip_file):
            post_task_update(callback, f"Error: unable to find uploaded file {zip_file}")
            post_task_update(callback, f"error")
            return
        
        post_task_update(callback, f"--- Found uploaded file {zip_file}")

        # Create a new internal project from the zipfile
        clara_project_internal, global_metadata = create_CLARAProjectInternal_from_zipfile(zip_file, internal_id, callback=callback)
        if clara_project_internal is None:
            post_task_update(callback, f"Error: unable to create internal project")
            post_task_update(callback, f"error")

        # Now that we have the real l1 and l2, use them to update clara_project. 
        clara_project.l1 = clara_project_internal.l1_language
        clara_project.l2 = clara_project_internal.l2_language
        clara_project.save() 

        # Update simple_clara_type and human audio info from the global metadata, which looks like this:
        #{
        #  "simple_clara_type": "create_text_and_image",
        #  "human_voice_id": "mannyrayner",
        #  "human_voice_id_phonetic": "mannyrayner",
        #  ...
        if global_metadata and isinstance(global_metadata, dict):
            if "simple_clara_type" in global_metadata:
                clara_project.simple_clara_type = global_metadata["simple_clara_type"]
                clara_project.save()

            if "uses_coherent_image_set" in global_metadata:
                clara_project.uses_coherent_image_set = global_metadata["uses_coherent_image_set"]
                clara_project.save()

            if "uses_coherent_image_set_v2" in global_metadata:
                clara_project.uses_coherent_image_set_v2 = global_metadata["uses_coherent_image_set_v2"]
                clara_project.save()

            if "use_translation_for_images" in global_metadata:
                clara_project.use_translation_for_images = global_metadata["use_translation_for_images"]
                clara_project.save()

            if "uses_picture_glossing" in global_metadata:
                clara_project.uses_picture_glossing = global_metadata["uses_picture_glossing"]
                clara_project.save()

            if "picture_gloss_style" in global_metadata:
                clara_project.picture_gloss_style = global_metadata["picture_gloss_style"]
                clara_project.save()
                
            if "human_voice_id" in global_metadata and global_metadata["human_voice_id"]:                       
                plain_human_audio_info, plain_created = HumanAudioInfo.objects.get_or_create(project=clara_project)
                plain_human_audio_info.voice_talent_id = global_metadata["human_voice_id"]
                plain_human_audio_info.use_for_words = True if global_metadata["audio_type_for_words"] == 'human' else False
                plain_human_audio_info.use_for_segments = True if global_metadata["audio_type_for_segments"] == 'human' else False
                plain_human_audio_info.save()
                
            if "human_voice_id_phonetic" in global_metadata and global_metadata["human_voice_id_phonetic"]:   
                phonetic_human_audio_info, phonetic_created = PhoneticHumanAudioInfo.objects.get_or_create(project=clara_project)
                phonetic_human_audio_info.voice_talent_id = global_metadata["human_voice_id_phonetic"]
                phonetic_human_audio_info.use_for_words = True
                phonetic_human_audio_info.save()

        post_task_update(callback, f'--- Created project: id={clara_project.id}, internal_id={internal_id}')
        post_task_update(callback, f"finished")

    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")
    finally:
        # remove_file removes the S3 file if we're in S3 mode (i.e. Heroku) and the local file if we're in local mode.
        remove_file(zip_file)

# Reconstitute a CLARAProjectInternal from an export zipfile
def create_CLARAProjectInternal_from_zipfile(zipfile, new_id, callback=None):
    try:
        tmp_dir = tempfile.mkdtemp()
        unzip_file(zipfile, tmp_dir)
        post_task_update(callback, '--- Unzipped import file')
        change_project_id_in_imported_directory(tmp_dir, new_id)
        tmp_project_dir = os.path.join(tmp_dir, 'project_dir')
        rename_files_in_project_dir(tmp_project_dir, new_id)
        project = CLARAProjectInternal.from_directory(tmp_project_dir)
        update_metadata_file_paths(project, project.project_dir, callback=callback)
        update_multimedia_from_imported_directory(project, tmp_dir, callback=callback)
        global_metadata = get_global_metadata(tmp_dir)
        return ( project, global_metadata )
    except Exception as e:
        post_task_update(callback, f'*** Error when trying to import zipfile {zipfile}')
        error_message = f'"{str(e)}"\n{traceback.format_exc()}'
        post_task_update(callback, error_message)
        return ( None, None )
    finally:
        # Remove the tmp dir once we've used it
        if local_directory_exists(tmp_dir):
            remove_local_directory(tmp_dir)


# Import a new project from a zipfile
@login_required
def import_project(request):
    if request.method == 'POST':
        form = ProjectImportForm(request.POST, request.FILES)
        if form.is_valid():
            # Extract the validated data from the form
            title = form.cleaned_data['title']
            uploaded_file = form.cleaned_data['zipfile']
            zip_file = uploaded_file_to_file(uploaded_file)

            # Check if the zipfile exists
            if not local_file_exists(zip_file):
                messages.error(request, f"Error: unable to find uploaded zipfile {zip_file}")
                return render(request, 'clara_app/import_project.html', {'form': form})

            # If we're on Heroku, we need to copy the zipfile to S3 so that the worker process can get it
            copy_local_file_to_s3_if_necessary(zip_file)

            # Create a new project in Django's database, associated with the current user
            # Use 'english' as a placeholder for l1 and l2 until we have the real values from the zipfile
            clara_project = CLARAProject(title=title, user=request.user, l2='english', l1='english')
            clara_project.save()
            internal_id = create_internal_project_id(title, clara_project.id)
            clara_project.internal_id = internal_id
            clara_project.save()

            task_type = f'import_project_zipfile'
            callback, report_id = make_asynch_callback_and_report_id(request, task_type)

            async_task(import_project_from_zip_file, zip_file, clara_project.id, internal_id, callback=callback)

            # Redirect to the monitor view, passing the task ID and report ID as parameters
            return redirect('import_project_monitor', clara_project.id, report_id)

        else:
            # The form data was invalid. Re-render the form with error messages.
            return render(request, 'clara_app/import_project.html', {'form': form})
    else:
        # This is a GET request, so create a new blank form
        form = ProjectImportForm()

        clara_version = get_user_config(request.user)['clara_version']
        
        return render(request, 'clara_app/import_project.html', {'form': form, 'clara_version': clara_version})

@login_required
@user_has_a_project_role
def import_project_status(request, project_id, report_id):
    messages = get_task_updates(report_id)
    print(f'{len(messages)} messages received')
    if 'error' in messages:
        status = 'error'
    elif 'finished' in messages:
        status = 'finished'  
    else:
        status = 'unknown'    
    return JsonResponse({'messages': messages, 'status': status})

# Render the monitoring page, which will use JavaScript to poll the task status API
@login_required
@user_has_a_project_role
def import_project_monitor(request, project_id, report_id):
    project = get_object_or_404(CLARAProject, pk=project_id)

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/import_project_monitor.html',
                  {'report_id': report_id, 'project_id': project_id, 'project': project, 'clara_version':clara_version})

# Confirm the final result of importing the prouect
@login_required
@user_has_a_project_role
def import_project_complete(request, project_id, status):
    if status == 'error':
        messages.error(request, "Something went wrong when importing the project. Try looking at the 'Recent task updates' view")
        return redirect('import_project')
    else:
        messages.success(request, "Project imported successfully")
        return redirect('project_detail', project_id=project_id)
        
# Create a clone of a project        
@login_required
@user_has_a_project_role
def clone_project(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    if request.method == 'POST':
        form = ProjectCreationForm(request.POST)
        if form.is_valid():
            try:
                # Extract the title and the new L2 and L1 language selections
                new_title = form.cleaned_data['title']
                new_l2 = form.cleaned_data['l2']
                new_l1 = form.cleaned_data['l1']
                # Created the cloned project with the new language selections and a new internal ID
                new_project = CLARAProject(title=new_title, user=request.user, l2=new_l2, l1=new_l1,
                                           simple_clara_type=project.simple_clara_type,
                                           uses_coherent_image_set=project.uses_coherent_image_set,
                                           uses_coherent_image_set_v2=project.uses_coherent_image_set_v2,
                                           use_translation_for_images=project.use_translation_for_images)
                new_internal_id = create_internal_project_id(new_title, new_project.id)
                new_project.internal_id = new_internal_id
                new_project.save()
                # Create a new internal project using the new internal ID
                new_project_internal = CLARAProjectInternal(new_internal_id, new_l2, new_l1)
                # Copy relevant files from the old project
                project_internal.copy_files_to_new_project(new_project_internal)

                # Redirect the user to the cloned project detail page and show a success message
                messages.success(request, "Cloned project created")
                return redirect('project_detail', project_id=new_project.id)
            except Exception as e:
                messages.error(request, f"Something went wrong when cloning the project: {str(e)}\n{traceback.format_exc()}")
                return redirect('project_detail', project_id=project_id)
    else:
        # Prepopulate the form with the copied title and the current language selections as defaults
        new_title = project.title + " - copy"
        form = ProjectCreationForm(initial={'title': new_title, 'l2': project.l2, 'l1': project.l1})

    clara_version = get_user_config(request.user)['clara_version']

    return render(request, 'clara_app/create_cloned_project.html',
                  {'form': form, 'project': project, 'clara_version': clara_version})
