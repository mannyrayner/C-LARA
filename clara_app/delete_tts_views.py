from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages

from django_q.tasks import async_task
from .forms import DeleteTTSDataForm
from .utils import get_user_config, make_asynch_callback_and_report_id
from .utils import get_task_updates
from .clara_audio_annotator import AudioAnnotator
from .clara_utils import get_config
from .clara_utils import post_task_update
import logging

config = get_config()
logger = logging.getLogger(__name__)

def delete_tts_data_for_language(language, callback=None):
    post_task_update(callback, f"--- Starting delete task for language {language}")
    tts_annotator = AudioAnnotator(language, callback=callback)
    tts_annotator.delete_entries_for_language(callback=callback)

# Delete cached TTS data for language   
@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def delete_tts_data(request):
    if request.method == 'POST':
        form = DeleteTTSDataForm(request.POST)
        if form.is_valid():
            language = form.cleaned_data['language']
            
            # Create a unique ID to tag messages posted by this task and a callback
            task_type = f'delete_tts'
            callback, report_id = make_asynch_callback_and_report_id(request, task_type)

            async_task(delete_tts_data_for_language, language, callback=callback)
            print(f'--- Started delete task {language}')
            #Redirect to the monitor view, passing the language and report ID as parameters
            return redirect('delete_tts_data_monitor', language, report_id)

    else:
        form = DeleteTTSDataForm()

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/delete_tts_data.html', {
        'form': form, 'clara_version': clara_version
    })

# This is the API endpoint that the JavaScript will poll
@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def delete_tts_data_status(request, report_id):
    messages = get_task_updates(report_id)
    print(f'{len(messages)} messages received')
    if 'error' in messages:
        status = 'error'
    elif 'finished' in messages:
        status = 'finished'  
    else:
        status = 'unknown'    
    return JsonResponse({'messages': messages, 'status': status})

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def delete_tts_data_monitor(request, language, report_id):

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/delete_tts_data_monitor.html',
                  {'language': language, 'report_id': report_id, 'clara_version': clara_version})

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def delete_tts_data_complete(request, language, status):
    if request.method == 'POST':
        form = DeleteTTSDataForm(request.POST)
        if form.is_valid():
            language = form.cleaned_data['language']
            
            task_type = f'delete_tts'
            callback, report_id = make_asynch_callback_and_report_id(request, task_type)

            async_task(delete_tts_data_for_language, language, callback=callback)
            print(f'--- Started delete task for {language}')
            #Redirect to the monitor view, passing the task ID and report ID as parameters
            return redirect('delete_tts_data_monitor', language, report_id)
    else:
        if status == 'error':
            messages.error(request, f"Something went wrong when deleting TTS data for {language}. Try looking at the 'Recent task updates' view")
        else:
            messages.success(request, f'Deleted TTS data for {language}')

        form = DeleteTTSDataForm()

        clara_version = get_user_config(request.user)['clara_version']

        return render(request, 'clara_app/delete_tts_data.html',
                      { 'form': form, 'clara_version': clara_version, } )
