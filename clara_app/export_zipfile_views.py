from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from .models import CLARAProject, HumanAudioInfo, PhoneticHumanAudioInfo

from django_q.tasks import async_task
from .forms import MakeExportZipForm
from .utils import get_user_config, make_asynch_callback_and_report_id
from .utils import user_has_a_project_role
from .utils import get_task_updates

from .clara_main import CLARAProjectInternal
from .clara_utils import _s3_storage, get_config
from .clara_utils import generate_s3_presigned_url
from .clara_utils import post_task_update
import logging
import traceback

config = get_config()
logger = logging.getLogger(__name__)

def clara_project_internal_make_export_zipfile(clara_project_internal,
                                               simple_clara_type='create_text_and_image',
                                               uses_coherent_image_set=False,
                                               uses_coherent_image_set_v2=False,
                                               use_translation_for_images=False,
                                               human_voice_id=None, human_voice_id_phonetic=None,
                                               audio_type_for_words='tts', audio_type_for_segments='tts', 
                                               callback=None):
    print(f'--- Asynchronous rendering task started for creating export zipfile')
    try:
        clara_project_internal.create_export_zipfile(simple_clara_type=simple_clara_type,
                                                     uses_coherent_image_set=uses_coherent_image_set,
                                                     uses_coherent_image_set_v2=uses_coherent_image_set_v2,
                                                     use_translation_for_images=use_translation_for_images,
                                                     human_voice_id=human_voice_id, human_voice_id_phonetic=human_voice_id_phonetic,
                                                     audio_type_for_words=audio_type_for_words, audio_type_for_segments=audio_type_for_segments,
                                                     callback=callback)
        post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")

# Start the async process that will do the rendering
@login_required
@user_has_a_project_role
def make_export_zipfile(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    human_audio_info = HumanAudioInfo.objects.filter(project=project).first()
    human_audio_info_phonetic = PhoneticHumanAudioInfo.objects.filter(project=project).first()
        
    if human_audio_info and human_audio_info.voice_talent_id:
        human_voice_id = human_audio_info.voice_talent_id
        audio_type_for_words = 'human' if human_audio_info.use_for_words else 'tts'
        audio_type_for_segments = 'human' if human_audio_info.use_for_segments else 'tts'
    else:
        audio_type_for_words = 'tts'
        audio_type_for_segments = 'tts'
        human_voice_id = None

    if human_audio_info_phonetic and human_audio_info_phonetic.voice_talent_id:
        human_voice_id_phonetic = human_audio_info_phonetic.voice_talent_id
    else:
        human_voice_id_phonetic = None

    if request.method == 'POST':
        form = MakeExportZipForm(request.POST)
        if form.is_valid():
            task_type = f'make_export_zipfile'
            callback, report_id = make_asynch_callback_and_report_id(request, task_type)

            # Enqueue the task
            try:
                task_id = async_task(clara_project_internal_make_export_zipfile, clara_project_internal,
                                     simple_clara_type=project.simple_clara_type,
                                     uses_coherent_image_set=project.uses_coherent_image_set,
                                     uses_coherent_image_set_v2=project.uses_coherent_image_set_v2,
                                     use_translation_for_images=project.use_translation_for_images,
                                     human_voice_id=human_voice_id, human_voice_id_phonetic=human_voice_id_phonetic,
                                     audio_type_for_words=audio_type_for_words, audio_type_for_segments=audio_type_for_segments,
                                     callback=callback)

                # Redirect to the monitor view, passing the task ID and report ID as parameters
                return redirect('make_export_zipfile_monitor', project_id, report_id)
            except Exception as e:
                messages.error(request, f"An internal error occurred in export zipfile creation. Error details: {str(e)}\n{traceback.format_exc()}")
                form = MakeExportZipForm()
                return render(request, 'clara_app/make_export_zipfile.html', {'form': form, 'project': project})
    else:
        form = MakeExportZipForm()

        clara_version = get_user_config(request.user)['clara_version']
        
        return render(request, 'clara_app/make_export_zipfile.html', {'form': form, 'project': project, 'clara_version': clara_version})


# This is the API endpoint that the JavaScript will poll
@login_required
@user_has_a_project_role
def make_export_zipfile_status(request, project_id, report_id):
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
def make_export_zipfile_monitor(request, project_id, report_id):
    project = get_object_or_404(CLARAProject, pk=project_id)

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/make_export_zipfile_monitor.html',
                  {'report_id': report_id, 'project_id': project_id, 'project': project, 'clara_version': clara_version})

# Display the final result of creating the zipfile
@login_required
@user_has_a_project_role
def make_export_zipfile_complete(request, project_id, status):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    if status == 'error':
        succeeded = False
        presigned_url = None
        messages.error(request, "Unable to create export zipfile. Try looking at the 'Recent task updates' view")
    else:
        succeeded = True
        messages.success(request, f'Export zipfile created')
        if _s3_storage:
            presigned_url = generate_s3_presigned_url(clara_project_internal.export_zipfile_pathname())
        else:
            presigned_url = None
        
    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/make_export_zipfile_complete.html', 
                  {'succeeded': succeeded,
                   'project': project,
                   'presigned_url': presigned_url,
                   'clara_version': clara_version} )

