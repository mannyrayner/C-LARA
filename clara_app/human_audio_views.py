from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from .models import CLARAProject, HumanAudioInfo, PhoneticHumanAudioInfo

from django_q.tasks import async_task
from .forms import AudioMetadataForm
from .forms import HumanAudioInfoForm, LabelledSegmentedTextForm, AudioItemFormSet, PhoneticHumanAudioInfoForm
from .utils import get_user_config, make_asynch_callback_and_report_id
from .utils import user_has_a_project_role
from .utils import get_task_updates
from .utils import uploaded_file_to_file

from .clara_main import CLARAProjectInternal
#from .clara_audio_repository import AudioRepository
from .clara_audio_repository_orm import AudioRepositoryORM
from .clara_utils import get_config, file_exists, local_file_exists, remove_file, basename
from .clara_utils import copy_local_file_to_s3_if_necessary, copy_s3_file_to_local_if_necessary
from .clara_utils import read_json_or_txt_file
from .clara_utils import post_task_update
import json
import logging
import pprint
import traceback

config = get_config()
logger = logging.getLogger(__name__)

@login_required
@user_has_a_project_role
def get_audio_metadata_view(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    
    audio_metadata = clara_project_internal.get_audio_metadata()

    # Convert the metadata to JSON (or similar formatted string)
    audio_metadata_str = json.dumps(audio_metadata, indent=4)
    
    if request.method == 'POST':
        # Handle POST logic if any (like saving the metadata somewhere)
        pass
    else:
        form = AudioMetadataForm(initial={'metadata': audio_metadata_str})

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/audio_metadata.html', 
                  { 'project': project, 'form': form, 'clara_version': clara_version })

@login_required
@user_has_a_project_role
def human_audio_processing(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    
    # Try to get existing HumanAudioInfo for this project or create a new one
    human_audio_info, created = HumanAudioInfo.objects.get_or_create(project=project)

    # Temporarily store existing file data
    existing_audio_file = human_audio_info.audio_file
    existing_metadata_file = human_audio_info.manual_align_metadata_file

    # Initialize the form with the current instance of HumanAudioInfo
    form = HumanAudioInfoForm(instance=human_audio_info)
    audio_item_formset = None
    labelled_segmented_text = clara_project_internal.get_labelled_segmented_text()
    labelled_segmented_text_form = LabelledSegmentedTextForm(initial={'labelled_segmented_text': labelled_segmented_text})

    # Handle POST request
    if request.method == 'POST':
        form = HumanAudioInfoForm(request.POST, request.FILES, instance=human_audio_info)

        if form.is_valid():
    
            # 0. Update the model with any new values from the form. Get the method and human_voice_id
            form.save()

            method = request.POST['method']
            human_voice_id = request.POST['voice_talent_id']
            # Restore existing file data if no new files are uploaded
            if 'manual_align_audio_file' not in request.FILES:
                human_audio_info.audio_file = existing_audio_file
            if 'metadata_file' not in request.FILES:
                human_audio_info.manual_align_metadata_file = existing_metadata_file

            human_audio_info.save()  # Save the restored data back to the database

            if method == 'tts_only':
                messages.success(request, "Saved settings.")

            # 1. If we're doing uploading, get the formset and save uploaded files

            if method == 'upload' and human_voice_id:

                audio_repository = AudioRepositoryORM()
                #audio_repository = AudioRepositoryORM() if _use_orm_repositories else AudioRepository()
                formset = AudioItemFormSet(request.POST, request.FILES)
                n_files_uploaded = 0
                print(f'--- Updating from formset ({len(formset)} items)')
                for form in formset:
                    if form.changed_data:
                        if not form.is_valid():
                            print(f'--- Invalid form data: {form}')
                            messages.error(request, "Invalid form data.")
                            return redirect('human_audio_processing', project_id=project_id)

                        if form.cleaned_data.get('audio_file_path'):
                            text = form.cleaned_data.get('text')
                            context = form.cleaned_data.get('context')
                            pprint.pprint({'text': text, 'context': context})
                            uploaded_audio_file_path = form.cleaned_data.get('audio_file_path')
                            real_audio_file_path = uploaded_file_to_file(uploaded_audio_file_path)
                            #print(f'--- real_audio_file_path for {text} (from upload) = {real_audio_file_path}')
                            stored_audio_file_path = audio_repository.store_mp3('human_voice', project.l2, human_voice_id, real_audio_file_path)
                            audio_repository.add_or_update_entry('human_voice', project.l2, human_voice_id, text, stored_audio_file_path, context=context)
                            print(f"--- audio_repository.add_or_update_entry('human_voice', {project.l2}, {human_voice_id}, '{text}', {stored_audio_file_path}, context={context}")
                            n_files_uploaded += 1
                                
                messages.success(request, f"{n_files_uploaded} audio files uploaded from {len(formset)} items")
                return redirect('human_audio_processing', project_id=project_id)                             

            # 2. Upload and internalise a LiteDevTools zipfile if there is one and we're doing recording.
            
            if method == 'record':
                if 'audio_zip' in request.FILES and human_voice_id:
                    uploaded_file = request.FILES['audio_zip']
                    zip_file = uploaded_file_to_file(uploaded_file)
                    if not local_file_exists(zip_file):
                        messages.error(request, f"Error: unable to find uploaded zipfile {zip_file}")
                    else:
                        print(f"--- Found uploaded file {zip_file}")
                        # If we're on Heroku, we need to copy the zipfile to S3 so that the worker process can get it
                        copy_local_file_to_s3_if_necessary(zip_file)
                        task_type = f'process_ldt_zipfile'
                        callback, report_id = make_asynch_callback_and_report_id(request, task_type)

                        async_task(process_ldt_zipfile, clara_project_internal, zip_file, human_voice_id, callback=callback)

                        # Redirect to the monitor view, passing the task ID and report ID as parameters
                        return redirect('process_ldt_zipfile_monitor', project_id, report_id)
                else:
                    messages.success(request, "Human Audio Info updated successfully!")

            if method == 'manual_align':
                # 3. Handle the original audio file upload
                if 'manual_align_audio_file' in request.FILES:
                    uploaded_audio = request.FILES['manual_align_audio_file']
                    audio_file = uploaded_file_to_file(uploaded_audio)
                    copy_local_file_to_s3_if_necessary(audio_file)
                    human_audio_info.audio_file = audio_file  
                    human_audio_info.save()
                    messages.success(request, "Uploaded audio file saved.")

                # 4. Handle the metadata file upload
                if 'metadata_file' in request.FILES:
                    uploaded_metadata = request.FILES['metadata_file']
                    metadata_file = uploaded_file_to_file(uploaded_metadata)
                    copy_local_file_to_s3_if_necessary(metadata_file)
                    human_audio_info.manual_align_metadata_file = metadata_file  
                    human_audio_info.save()
                    messages.success(request, "Uploaded metadata file saved.")
                    print(f'--- Step 4: human_voice_id = {human_voice_id}')
                    print(f'--- Step 4: human_audio_info.audio_file = {human_audio_info.audio_file}')
                    print(f'--- Step 4: human_audio_info.manual_align_metadata_file = {human_audio_info.manual_align_metadata_file}')

                # 5. If both files are available, trigger the manual alignment processing

                if human_audio_info.audio_file and human_audio_info.manual_align_metadata_file and human_voice_id:
                    audio_file = human_audio_info.audio_file
                    metadata_file = human_audio_info.manual_align_metadata_file
                    # Check that we really do have the files
                    if not file_exists(audio_file):
                        messages.error(request, f"Error: unable to find uploaded audio file {audio_file}")
                    elif not file_exists(metadata_file):
                        messages.error(request, f"Error: unable to find uploaded metadata file {metadata_file}")
                    else:
                        # Create a callback
                        #report_id = uuid.uuid4()
                        #callback = [post_task_update_in_db, report_id]
                        task_type = f'process_manual_alignment'
                        callback, report_id = make_asynch_callback_and_report_id(request, task_type)
                        
                        # The metadata file can either be a .json file with start and end times, or a .txt file of Audacity labels
                        metadata = read_json_or_txt_file(metadata_file)
                        async_task(process_manual_alignment, clara_project_internal, audio_file, metadata, human_voice_id,
                                   use_context=human_audio_info.use_context, callback=callback)
                        
                        print("--- Started async task to process manual alignment data")

                        # Redirect to a monitor view 
                        return redirect('process_manual_alignment_monitor', project_id, report_id)
                else:
                    messages.success(request, "Need all three out of human voice ID, audio and metadata files to proceed.")
        else:
            messages.error(request, "There was an error processing the form. Please check your input.")

    # Handle GET request
    else:
        form = HumanAudioInfoForm(instance=human_audio_info)
        if human_audio_info.method == 'upload':
            audio_item_initial_data = initial_data_for_audio_upload_formset(clara_project_internal, human_audio_info)
            #print(f'audio_item_initial_data =')
            #pprint.pprint(audio_item_initial_data)
            audio_item_formset = AudioItemFormSet(initial=audio_item_initial_data) if audio_item_initial_data else None
            labelled_segmented_text_form = None
        else:
            audio_item_formset = None
            labelled_segmented_text_form = LabelledSegmentedTextForm(initial={'labelled_segmented_text': labelled_segmented_text})

    clara_version = get_user_config(request.user)['clara_version']
    
    context = {
        'project': project,
        'form': form,
        'formset': audio_item_formset,
        'audio_file': human_audio_info.audio_file,
        'manual_align_metadata_file': human_audio_info.manual_align_metadata_file,
        'labelled_segmented_text_form': labelled_segmented_text_form,
        'clara_version': clara_version
    }

    return render(request, 'clara_app/human_audio_processing.html', context)

def initial_data_for_audio_upload_formset(clara_project_internal, human_audio_info):
    use_context = human_audio_info.use_context
    metadata = []
    human_voice_id = human_audio_info.voice_talent_id
    if human_audio_info.use_for_words:
        metadata += clara_project_internal.get_audio_metadata(human_voice_id=human_voice_id,
                                                              audio_type_for_words='human', type='words')
    if human_audio_info.use_for_segments:
        metadata += clara_project_internal.get_audio_metadata(human_voice_id=human_voice_id,
                                                              audio_type_for_segments='human', type='segments',
                                                              use_context=use_context)
    initial_data = [ { 'text': item['canonical_text'],
                       'audio_file_path': item['file_path'],
                       'audio_file_base_name': basename(item['file_path']) if item['file_path'] else None,
                       'context': item['context']}
                     for item in metadata ]
    
    return initial_data

@login_required
@user_has_a_project_role
def human_audio_processing_phonetic(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    
    # Try to get existing HumanAudioInfo for this project or create a new one
    human_audio_info, created = PhoneticHumanAudioInfo.objects.get_or_create(project=project)

    # Try forcing this choice to see if we still get 502 errors
    #human_audio_info.method = 'upload_zipfile'

    # Initialize the form with the current instance of HumanAudioInfo
    form = PhoneticHumanAudioInfoForm(instance=human_audio_info)
    audio_item_formset = None

    # Handle POST request
    if request.method == 'POST':
        form = PhoneticHumanAudioInfoForm(request.POST, request.FILES, instance=human_audio_info)

        #if form.is_valid():
        try:
    
            # 1. Update the model with any new values from the form. Get the method and human_voice_id
            print(f'keys: {request.POST.keys()}')
            method = request.POST['method']
            human_voice_id = request.POST['voice_talent_id']
            use_for_segments = True if 'use_for_segments' in request.POST and request.POST['use_for_segments'] == 'on' else False
            use_for_words = True if 'use_for_words' in request.POST and request.POST['use_for_words'] == 'on' else False
            print(f'use_for_segments = {use_for_segments}')
            print(f'use_for_words = {use_for_words}')
            human_audio_info.method = method
            human_audio_info.voice_talent_id = human_voice_id
            human_audio_info.use_for_segments = use_for_segments
            human_audio_info.use_for_words = use_for_words
            human_audio_info.save()  # Save the restored data back to the database


            # 2. Update from the formset and save new files
            if method == 'upload_individual' and human_voice_id:
                audio_repository = AudioRepositoryORM()
                #audio_repository = AudioRepositoryORM() if _use_orm_repositories else AudioRepository() 
                formset = AudioItemFormSet(request.POST, request.FILES)
                n_files_uploaded = 0
                print(f'--- Updating from formset ({len(formset)} items)')
                for form in formset:
                    if form.changed_data:
                        if not form.is_valid():
                            print(f'--- Invalid form data: {form}')
                            messages.error(request, "Invalid form data.")
                            return redirect('human_audio_processing', project_id=project_id)
                        
                        if form.cleaned_data.get('audio_file_path'):
                            text = form.cleaned_data.get('text')
                            uploaded_audio_file_path = form.cleaned_data.get('audio_file_path')
                            real_audio_file_path = uploaded_file_to_file(uploaded_audio_file_path)
                            print(f'--- real_audio_file_path for {text} (from upload) = {real_audio_file_path}')
                            stored_audio_file_path = audio_repository.store_mp3('human_voice', project.l2, human_voice_id, real_audio_file_path)
                            audio_repository.add_or_update_entry('human_voice', project.l2, human_voice_id, text, stored_audio_file_path, context='')
                            print(f"--- audio_repository.add_or_update_entry('human_voice', {project.l2}, {human_voice_id}, '{text}', {stored_audio_file_path}")
                            n_files_uploaded += 1
                            
                messages.success(request, f"{n_files_uploaded} audio files uploaded from {len(formset)} items")
                return redirect('human_audio_processing_phonetic', project_id=project_id)

             # 2. If we're doing recording and there is a LiteDevTools zipfile, upload and internalise it
            if method == 'upload_zipfile':
                if 'audio_zip' in request.FILES and human_voice_id:
                    uploaded_file = request.FILES['audio_zip']
                    zip_file = uploaded_file_to_file(uploaded_file)
                    if not local_file_exists(zip_file):
                        messages.error(request, f"Error: unable to find uploaded zipfile {zip_file}")
                    else:
                        print(f"--- Found uploaded file {zip_file}")
                        # If we're on Heroku, we need to copy the zipfile to S3 so that the worker process can get it
                        copy_local_file_to_s3_if_necessary(zip_file)
                        # Create a callback
                        #report_id = uuid.uuid4()
                        #callback = [post_task_update_in_db, report_id]
                        task_type = f'process_ldt_zipfile_phonetic'
                        callback, report_id = make_asynch_callback_and_report_id(request, task_type)

                        async_task(process_ldt_zipfile, clara_project_internal, zip_file, human_voice_id, callback=callback)

                        # Redirect to the monitor view, passing the task ID and report ID as parameters
                        return redirect('process_ldt_zipfile_monitor', project_id, report_id)

        #else:
            #messages.error(request, "There was an error processing the form. Please check your input.")
        except Exception as e:
            messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
            return redirect('human_audio_processing_phonetic', project_id)

    # Handle GET request
    form = PhoneticHumanAudioInfoForm(instance=human_audio_info)
    if human_audio_info.method == 'upload_individual':
        audio_item_initial_data = initial_data_for_audio_upload_formset_phonetic(clara_project_internal, human_audio_info)
        audio_item_formset = AudioItemFormSet(initial=audio_item_initial_data) if audio_item_initial_data else None
    else:
        audio_item_formset = None

    clara_version = get_user_config(request.user)['clara_version']
    
    context = {
        'project': project,
        'form': form,
        'formset': audio_item_formset,
        'clara_version': clara_version
    }

    return render(request, 'clara_app/human_audio_processing_phonetic.html', context)

def initial_data_for_audio_upload_formset_phonetic(clara_project_internal, human_audio_info):
    human_voice_id = human_audio_info.voice_talent_id
    metadata = clara_project_internal.get_audio_metadata(human_voice_id=human_voice_id,
                                                         audio_type_for_words='human', type='words',
                                                         phonetic=True)

    initial_data = [ { 'text': item['canonical_text'],
                       'audio_file_path': item['file_path'],
                       'audio_file_base_name': basename(item['file_path']) if item['file_path'] else None }
                     for item in metadata ]
    
    return initial_data

def process_ldt_zipfile(clara_project_internal, zip_file, human_voice_id, callback=None):
    try:
        # If we're on Heroku, the main thread should have copied the zipfile to S3 so that we can can get it
        copy_s3_file_to_local_if_necessary(zip_file, callback=callback)
        if not local_file_exists(zip_file):
            post_task_update(callback, f"Error: unable to find uploaded file {zip_file}")
            post_task_update(callback, f"error")
        else:
            post_task_update(callback, f"--- Found uploaded file {zip_file}")
            result = clara_project_internal.process_lite_dev_tools_zipfile(zip_file, human_voice_id, callback=callback)
            if result:
                post_task_update(callback, f"finished")
            else:
                post_task_update(callback, f"error")
    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")
    finally:
        # remove_file removes the S3 file if we're in S3 mode (i.e. Heroku) and the local file if we're in local mode.
        remove_file(zip_file)

def process_manual_alignment(clara_project_internal, audio_file, metadata, human_voice_id, use_context=True, callback=None):
    post_task_update(callback, "--- Started process_manual_alignment in async thread")
    try:
        # Retrieve files from S3 to local
        copy_s3_file_to_local_if_necessary(audio_file, callback=callback)

        # Process the manual alignment
        result = clara_project_internal.process_manual_alignment(audio_file, metadata, human_voice_id, use_context=use_context, callback=callback)
        
        if result:
            post_task_update(callback, f"finished")
        else:
            post_task_update(callback, f"error")
    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")

# This is the API endpoint that the JavaScript will poll
@login_required
@user_has_a_project_role
def process_ldt_zipfile_status(request, project_id, report_id):
    messages = get_task_updates(report_id)
    print(f'{len(messages)} messages received')
    if 'error' in messages:
        status = 'error'
    elif 'finished' in messages:
        status = 'finished'  
    else:
        status = 'unknown'    
    return JsonResponse({'messages': messages, 'status': status})

# This is the API endpoint that the JavaScript will poll
@login_required
@user_has_a_project_role
def process_manual_alignment_status(request, project_id, report_id):
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
def process_ldt_zipfile_monitor(request, project_id, report_id):
    project = get_object_or_404(CLARAProject, pk=project_id)

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/process_ldt_zipfile_monitor.html',
                  {'report_id': report_id, 'project_id': project_id, 'project': project, 'clara_version': clara_version})

# Render the monitoring page, which will use JavaScript to poll the task status API
@login_required
@user_has_a_project_role
def process_manual_alignment_monitor(request, project_id, report_id):
    project = get_object_or_404(CLARAProject, pk=project_id)

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/process_manual_alignment_monitor.html',
                  {'report_id': report_id, 'project_id': project_id, 'project': project, 'clara_version': clara_version})

# Confirm the final result of processing the zipfile
@login_required
@user_has_a_project_role
def process_ldt_zipfile_complete(request, project_id, status):
    project = get_object_or_404(CLARAProject, pk=project_id)
    if status == 'error':
        succeeded = False
    else:
        succeeded = True
    
    if succeeded:
        messages.success(request, "LiteDevTools zipfile processed successfully!")
    else:
        messages.error(request, "Something went wrong when installing LiteDevTools zipfile. Try looking at the 'Recent task updates' view")

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/process_ldt_zipfile_complete.html',
                  {'project': project, 'clara_version': clara_version})

# Confirm the final result of uploading the manual alignment data
@login_required
@user_has_a_project_role
def process_manual_alignment_complete(request, project_id, status):
    project = get_object_or_404(CLARAProject, pk=project_id)
    if status == 'error':
        succeeded = False
    else:
        succeeded = True
    
    if succeeded:
        messages.success(request, "Manual alignment data processed successfully!")
    else:
        messages.error(request, "Something went wrong when trying to install manual alignment data. Try looking at the 'Recent task updates' view")

    clara_version = get_user_config(request.user)['clara_version']
        
    return render(request, 'clara_app/process_manual_alignment_complete.html',
                  {'project': project, 'clara_version': clara_version})


# Used for Voice Recorder functionality
@login_required
def generate_audio_metadata(request, project_id, metadata_type, human_voice_id):
    return generate_audio_metadata_phonetic_or_normal(request, project_id, metadata_type, human_voice_id, phonetic=False)

@login_required
def generate_audio_metadata_phonetic(request, project_id, metadata_type, human_voice_id):
    return generate_audio_metadata_phonetic_or_normal(request, project_id, metadata_type, human_voice_id, phonetic=True)

def generate_audio_metadata_phonetic_or_normal(request, project_id, metadata_type, human_voice_id, phonetic=False):
    # Ensure the metadata type is valid
    if metadata_type not in ['segments', 'words']:
        return HttpResponse("Invalid metadata type.", status=400)

    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    
    # Get audio metadata in the required LiteDevTools format
    lite_metadata_content = clara_project_internal.get_audio_metadata(human_voice_id=human_voice_id,
                                                                      audio_type_for_segments='human' if metadata_type == 'segments' else 'tts',
                                                                      audio_type_for_words='human' if metadata_type == 'words' else 'tts',
                                                                      type=metadata_type, format="lite_dev_tools", phonetic=phonetic)

    # Create a response object for file download
    response = JsonResponse(lite_metadata_content, safe=False, json_dumps_params={'indent': 4})
    file_name = f"metadata_{metadata_type}_{project_id}.json"
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'

    return response

# Used by Manual Text/Audio Alignment functionality
@login_required
def generate_annotated_segmented_file(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    
    # Get the "labelled segmented" version of the text
    labelled_segmented_text = clara_project_internal.get_labelled_segmented_text()

    # Create a response object for file download
    response = HttpResponse(labelled_segmented_text, content_type='text/plain')
    file_name = f"labelled_segmented_text_{project_id}.txt"
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'

    return response

### First integration endpoint for Manual Text/Audio Alignment.
### Used by Text/Audio Alignment server to download
###   - labelled segmented text
###   - S3 link to mp3 file
###   - breakpoint text if it exists
### Note that the @login_required or @user_has_a_project_role decorators are intentionally omittted.
### This view is intended to be accessed externally from a server which won't have logged in.
##def manual_audio_alignment_integration_endpoint1(request, project_id):
##    project = get_object_or_404(CLARAProject, pk=project_id)
##    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
##    
##    # Get the "labelled segmented" version of the text
##    labelled_segmented_text = clara_project_internal.get_labelled_segmented_text()
##    
##    # Try to get existing HumanAudioInfo for this project or create a new one
##    human_audio_info, created = HumanAudioInfo.objects.get_or_create(project=project)
##    
##    # Access the audio_file and manual_align_metadata_file
##    audio_file = human_audio_info.audio_file
##    metadata_file = human_audio_info.manual_align_metadata_file
##    
##    # Copy the audio_file to S3 if it exists as a local file and get a download URL
##    if local_file_exists(audio_file):
##        copy_local_file_to_s3(audio_file)
##    s3_audio_file = s3_file_name(audio_file)
##    s3_audio_link = generate_s3_presigned_url(s3_audio_file)
##    
##    # Read the metadata_file if it already exists to get the breakpoint data
##    # It will not exist the first time the endpoint is accessed
##    # In subsequent accesses, the Text/Audio Alignment server may have uploaded existing breakpoint data
##    # In this case, we pass it back so that it can be edited on the Text/Audio Alignment server
##    breakpoint_text = None
##    if metadata_file:
##        breakpoint_text = read_txt_file(metadata_file)
##    
##    # Create JSON response
##    response_data = {
##        'labelled_segmented_text': labelled_segmented_text,
##        's3_audio_link': s3_audio_link,
##        'breakpoint_text': breakpoint_text    
##    }
##    
##    return JsonResponse(response_data)
##
### Second integration endpoint for Manual Text/Audio Alignment.
### Used by Text/Audio Alignment server to upload a JSON file.
### The Text/Audio Alignment server also passes a project_id to say where data should be stored.
###
### Note that the @login_required or @user_has_a_project_role decorators are intentionally omittted.
### This view is intended to be accessed externally from a server which won't have logged in.
##@csrf_exempt
##def manual_audio_alignment_integration_endpoint2(request):
##    if request.method != 'POST':
##        return JsonResponse({'status': 'failed',
##                             'error': 'only POST method is allowed'})
##    
##    try:
##        project_id = request.POST.get('project_id')
##        uploaded_file = request.FILES.get('json_file')
##        
##        project = get_object_or_404(CLARAProject, pk=project_id)
##        clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
##        human_audio_info, created = HumanAudioInfo.objects.get_or_create(project=project)
##        
##        # Convert the JSON file to Audacity txt form
##        json_file = uploaded_file_to_file(uploaded_file)
##        copy_local_file_to_s3_if_necessary(json_file)
##        
##        # Save the json_file and update human_audio_info
##        human_audio_info.manual_align_metadata_file = json_file
##        human_audio_info.save()
##    
##        return JsonResponse({'status': 'success'})
##    
##    except Exception as e:
##        return JsonResponse({'status': 'failed',
##                             'error': f'Exception: {str(e)}\n{traceback.format_exc()}'})  # Corrected traceback formatting
