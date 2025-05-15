from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages

from .models import Content
from .models import CLARAProject, HumanAudioInfo
from django.contrib.auth.models import User

from django_q.tasks import async_task
from .forms import SimpleClaraForm
from .utils import get_user_config, user_has_open_ai_key_or_credit, create_internal_project_id, store_api_calls, store_cost_dict, make_asynch_callback_and_report_id
from .utils import user_has_a_project_role
from .utils import get_task_updates
from .utils import uploaded_file_to_file, get_phase_up_to_date_dict

from .clara_main import CLARAProjectInternal
from .clara_registering_utils import register_project_content_helper
from .clara_phonetic_utils import phonetic_resources_are_available

from .clara_coherent_images_utils import get_style_params_from_project_params, project_params_for_simple_clara
from .clara_coherent_images_utils import get_element_descriptions_params_from_project_params
from .clara_coherent_images_utils import get_page_params_from_project_params
from .clara_coherent_images_utils import project_pathname
from .clara_coherent_images_utils import read_project_json_file, project_pathname

from .clara_coherent_images_alternate import get_alternate_images_json

from .clara_coherent_images_community_feedback import (register_cm_image_vote, register_cm_element_vote, register_cm_style_vote,
                                                       get_page_overview_info_for_cm_reviewing,
                                                       get_page_description_info_for_cm_reviewing,
                                                       get_element_description_info_for_cm_reviewing,
                                                       get_style_description_info_for_cm_reviewing,
                                                       update_ai_votes_in_feedback, update_ai_votes_for_element_in_feedback, update_ai_votes_for_style_in_feedback)

from .clara_dall_e_3_image import ( create_and_add_dall_e_3_image_for_whole_text )

from .clara_images_utils import numbered_page_list_for_coherent_images
from .clara_chinese import is_chinese_language
from .clara_tts_api import tts_engine_type_supports_language
from .clara_chatgpt4 import call_chat_gpt4_interpret_image
from .clara_utils import get_config, basename
from .clara_utils import post_task_update, is_rtl_language, is_chinese_language
from .constants import TTS_CHOICES
import logging
import pprint
import traceback
import asyncio

config = get_config()
logger = logging.getLogger(__name__)

_simple_clara_trace = False
#_simple_clara_trace = True

def get_simple_clara_resources_helper(project_id, user):
    try:
        resources_available = {}
        
        if not project_id:
            # Inital state: we passed in a null (zero) project_id. Nothing exists yet.
            resources_available['status'] = 'No project'
            resources_available['up_to_date_dict'] = {}
            return resources_available

        # We have a project, add the L2, L1, title and simple_clara_type to available resources
        project = get_object_or_404(CLARAProject, pk=project_id)

        # There is an issue where we can lose the simple_clara_type information. Do this to try and recover
        if project.uses_coherent_image_set_v2 or project.uses_coherent_image_set:
            project.simple_clara_type = 'create_text_and_multiple_images'
            project.save()
    
        clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
        up_to_date_dict = get_phase_up_to_date_dict(project, clara_project_internal, user)

        resources_available['l2'] = project.l2
        resources_available['rtl_language'] = is_rtl_language(project.l2)
        resources_available['l1'] = project.l1
        resources_available['title'] = project.title
        resources_available['simple_clara_type'] = project.simple_clara_type
        resources_available['internal_title'] = clara_project_internal.id
        resources_available['up_to_date_dict'] = up_to_date_dict

        image = None

        # In the create_text_and_image and create_text_and_multiple_images versions, we start with a prompt and create a plain_text
        # In the create_text_and_image version we also create an image at once
        if project.simple_clara_type in ( 'create_text_and_image', 'create_text_and_multiple_images' ):
            if not clara_project_internal.text_versions['prompt']:
                # We have a project, but no prompt
                resources_available['status'] = 'No prompt'
                return resources_available
            else:
                resources_available['prompt'] = clara_project_internal.load_text_version('prompt')

            if not clara_project_internal.text_versions['plain']:
                # We have a prompt, but no plain text
                resources_available['status'] = 'No text'
                return resources_available
            else:
                resources_available['plain_text'] = clara_project_internal.load_text_version('plain')
                resources_available['text_title'] = clara_project_internal.load_text_version_or_null('title')

            image = clara_project_internal.get_project_image('DALLE-E-3-Image-For-Whole-Text')
            if image:
                resources_available['image_basename'] = basename(image.image_file_path) if image.image_file_path else None

            # For uploaded image, in case we want to use one
            if project.simple_clara_type == 'create_text_and_image':
                resources_available['image_file_path'] = None

        # In the create_text_and_multiple_images, we are creating the images using the V2 infrastructure
        if project.simple_clara_type == 'create_text_and_multiple_images':
            resources_available['style_advice'] = clara_project_internal.get_style_advice_v2()
            resources_available['v2_images_dict'] = clara_project_internal.get_project_images_dict_v2()
            if resources_available['v2_images_dict']['pages']:
                resources_available['v2_pages_overview_info'] = clara_project_internal.get_page_overview_info_for_cm_reviewing()

        # In the create_text_from_image version, we start with an image and possibly a prompt and create a plain_text
        elif project.simple_clara_type == 'create_text_from_image':
            image = clara_project_internal.get_project_image('DALLE-E-3-Image-For-Whole-Text')
            if not image:
                # We have a project, but no image
                resources_available['status'] = 'No image prompt'
                return resources_available
            else:
                resources_available['image_basename'] = basename(image.image_file_path) if image.image_file_path else None

            # The prompt is optional in create_text_from_image, we can meaningfully use a default
            if clara_project_internal.text_versions['prompt']:
                resources_available['prompt'] = clara_project_internal.load_text_version('prompt')

            if not clara_project_internal.text_versions['plain']:
                # We have an image, but no plain text
                resources_available['status'] = 'No text'
                return resources_available
            else:
                resources_available['plain_text'] = clara_project_internal.load_text_version('plain')
                resources_available['text_title'] = clara_project_internal.load_text_version_or_null('title')

        # In the annotate_existing_text version, we start with plain text and create an image
        elif project.simple_clara_type == 'annotate_existing_text':
            if not clara_project_internal.text_versions['plain']:
                # We have an image, but no plain text
                resources_available['status'] = 'No text'
                return resources_available
            else:
                resources_available['plain_text'] = clara_project_internal.load_text_version('plain')
                resources_available['text_title'] = clara_project_internal.load_text_version_or_null('title')

            image = clara_project_internal.get_project_image('DALLE-E-3-Image-For-Whole-Text')
            if image:
                resources_available['image_basename'] = basename(image.image_file_path) if image.image_file_path else None

            # For uploaded image, in case we want to use one
            resources_available['image_file_path'] = None

        #if clara_project_internal.text_versions['segmented']:
        if up_to_date_dict['segmented']:
            # We have segmented text
            resources_available['segmented_text'] = clara_project_internal.load_text_version('segmented')

        #if clara_project_internal.text_versions['segmented_title']:
        if up_to_date_dict['segmented_title']:
            # We have segmented text
            resources_available['segmented_title'] = clara_project_internal.load_text_version('segmented_title')

        try:
            human_audio_info, human_audio_info_created = HumanAudioInfo.objects.get_or_create(project=project)
            resources_available['preferred_tts_engine'] = human_audio_info.preferred_tts_engine
        except Exception as e:
            resources_available['preferred_tts_engine'] = 'none'

        #if not clara_project_internal.rendered_html_exists(project_id):
        if not up_to_date_dict['render']:
            # We have plain text and image, but no rendered HTML
            #if not clara_project_internal.text_versions['segmented'] or not clara_project_internal.text_versions['segmented_title']:
            if not up_to_date_dict['segmented'] or not up_to_date_dict['segmented_title']:
                resources_available['status'] = 'No segmented text'
            else:
                resources_available['status'] = 'No multimedia' if image else 'No image'
            return resources_available
        else:
            # We have the rendered HTML
            resources_available['rendered_text_available'] = True
            
        try:
            content = Content.objects.get(project=project)
        except Exception as e:
            content = None
            
        if content:
            resources_available['content_id'] = content.id
            resources_available['status'] = 'Posted' if image else 'Posted without image'
            return resources_available
        else:
            resources_available['status'] = 'Everything available' if image else 'Everything available except image'
            return resources_available
            
    except Exception as e:
        return { 'error': f'Exception: {str(e)}\n{traceback.format_exc()}' }

@login_required
def simple_clara(request, project_id, last_operation_status):
    user = request.user
    username = request.user.username
    # Get resources available for display based on the current state
    resources = get_simple_clara_resources_helper(project_id, user)
    if _simple_clara_trace:
        print(f'Resources:')
        pprint.pprint(resources)
   
    status = resources['status']
    simple_clara_type = resources['simple_clara_type'] if 'simple_clara_type' in resources else None
    rtl_language = resources['rtl_language'] if 'rtl_language' in resources else False
    up_to_date_dict = resources['up_to_date_dict']
    
    form = SimpleClaraForm(initial=resources, is_rtl_language=rtl_language)
    content = Content.objects.get(id=resources['content_id']) if 'content_id' in resources else None

    if request.method == 'GET':
        if last_operation_status == 'finished':
             messages.success(request, f"Operation completed successfully")
             return redirect('simple_clara', project_id, 'init')
        elif last_operation_status == 'error':
             messages.error(request, "Something went wrong. Try looking at the 'Recent task updates' view")
             return redirect('simple_clara', project_id, 'init')
    elif request.method == 'POST':
        # Extract action from the POST request
        action = request.POST.get('action')
##        if _simple_clara_trace:
##            print(f'Action = {action}')
        print(f'Action = {action}')
        if action:
            form = SimpleClaraForm(request.POST, request.FILES, is_rtl_language=rtl_language)
            if form.is_valid():
                if _simple_clara_trace:
                    print(f'Status: {status}')
                    print(f'form.cleaned_data')
                    pprint.pprint(form.cleaned_data)
                if action == 'create_project':
                    l2 = form.cleaned_data['l2']
                    l1 = form.cleaned_data['l1']
                    title = form.cleaned_data['title']
                    simple_clara_type = form.cleaned_data['simple_clara_type']
                    simple_clara_action = { 'action': 'create_project', 'l2': l2, 'l1': l1, 'title': title, 'simple_clara_type': simple_clara_type }
                elif action == 'change_title':
                    title = form.cleaned_data['title']
                    simple_clara_action = { 'action': 'change_title', 'title': title }
                elif action == 'create_text':
                    prompt = form.cleaned_data['prompt']
                    simple_clara_action = { 'action': 'create_text', 'prompt': prompt }
                elif action == 'create_text_and_image':
                    prompt = form.cleaned_data['prompt']
                    simple_clara_action = { 'action': 'create_text_and_image', 'prompt': prompt }
                elif action == 'save_uploaded_image_prompt':
                    if form.cleaned_data['image_file_path']:
                        uploaded_image_file_path = form.cleaned_data['image_file_path']
                        image_file_path = uploaded_file_to_file(uploaded_image_file_path)
                        prompt = form.cleaned_data['prompt'] if 'prompt' in form.cleaned_data else ''
                        simple_clara_action = { 'action': 'save_image_and_create_text', 'image_file_path': image_file_path, 'prompt': prompt }
                    else:
                        messages.error(request, f"Error: no image to upload")
                        return redirect('simple_clara', project_id, 'error')
                elif action == 'regenerate_text_from_image':
                    prompt = form.cleaned_data['prompt'] if 'prompt' in form.cleaned_data else ''
                    if prompt:
                        simple_clara_action = { 'action': 'regenerate_text_from_image', 'prompt': prompt }
                    else:
                        messages.error(request, f"Error: no instructions about how to regenerate image")
                        return redirect('simple_clara', project_id, 'error')
                elif action == 'save_text_to_annotate':
                    plain_text = form.cleaned_data['plain_text']
                    simple_clara_action = { 'action': 'save_text_and_create_image', 'plain_text': plain_text }
                elif action == 'save_text':
                    plain_text = form.cleaned_data['plain_text']
                    simple_clara_action = { 'action': 'save_text', 'plain_text': plain_text }
                elif action == 'save_segmented_text':
                    segmented_text = form.cleaned_data['segmented_text']
                    simple_clara_action = { 'action': 'save_segmented_text', 'segmented_text': segmented_text }
                elif action == 'save_segmented_title':
                    segmented_title = form.cleaned_data['segmented_title']
                    simple_clara_action = { 'action': 'save_segmented_title', 'segmented_title': segmented_title }
                elif action == 'save_text_title':
                    text_title = form.cleaned_data['text_title']
                    simple_clara_action = { 'action': 'save_text_title', 'text_title': text_title }
                elif action == 'save_uploaded_image':
                    if form.cleaned_data['image_file_path']:
                        uploaded_image_file_path = form.cleaned_data['image_file_path']
                        image_file_path = uploaded_file_to_file(uploaded_image_file_path)
                        simple_clara_action = { 'action': 'save_uploaded_image', 'image_file_path': image_file_path }
                    else:
                        messages.error(request, f"Error: no image to upload")
                        return redirect('simple_clara', project_id, 'error')
                elif action == 'rewrite_text':
                    prompt = form.cleaned_data['prompt']
                    simple_clara_action = { 'action': 'rewrite_text', 'prompt': prompt }
                elif action == 'regenerate_image':
                    image_advice_prompt = form.cleaned_data['image_advice_prompt']
                    simple_clara_action = { 'action': 'regenerate_image', 'image_advice_prompt':image_advice_prompt }
                elif action == 'create_v2_style':
                    image_generation_model = form.cleaned_data['image_generation_model'] if 'image_generation_model' in form.cleaned_data else None
                    description_language = form.cleaned_data['description_language'] if 'description_language' in form.cleaned_data else None
                    style_advice = form.cleaned_data['style_advice']
                    simple_clara_action = { 'action': 'create_v2_style',
                                            'description_language': description_language,
                                            'image_generation_model': image_generation_model,
                                            'style_advice': style_advice,
                                            'up_to_date_dict': up_to_date_dict }
                elif action == 'create_v2_elements':
                    simple_clara_action = { 'action': 'create_v2_elements', 'up_to_date_dict': up_to_date_dict }
                elif action == 'delete_v2_element':
                    deleted_element_text = request.POST.get('deleted_element_text')
                    simple_clara_action = { 'action': 'delete_v2_element', 'deleted_element_text': deleted_element_text }
                elif action == 'add_v2_element':
                    new_element_text = request.POST.get('new_element_text')
                    simple_clara_action = { 'action': 'add_v2_element', 'new_element_text': new_element_text }
                elif action == 'create_v2_pages':
                    simple_clara_action = { 'action': 'create_v2_pages', 'up_to_date_dict': up_to_date_dict }
                elif action == 'create_segmented_text':
                    simple_clara_action = { 'action': 'create_segmented_text', 'up_to_date_dict': up_to_date_dict }
                elif action == 'save_preferred_tts_engine':
                    preferred_tts_engine = form.cleaned_data['preferred_tts_engine']
                    simple_clara_action = { 'action': 'save_preferred_tts_engine', 'preferred_tts_engine': preferred_tts_engine }
                elif action == 'create_rendered_text':
                    simple_clara_action = { 'action': 'create_rendered_text', 'up_to_date_dict': up_to_date_dict }
                elif action == 'post_rendered_text':
                    simple_clara_action = { 'action': 'post_rendered_text' }
                else:
                    messages.error(request, f"Error: unknown action '{action}'")
                    return redirect('simple_clara', project_id, 'error')

                _simple_clara_actions_to_execute_locally = ( 'create_project', 'change_title', 'save_text', 'save_segmented_text', 'save_segmented_title',
                                                             'save_text_title', 'save_uploaded_image', 'delete_v2_element',
                                                             'save_preferred_tts_engine', 'post_rendered_text' )
                
                if action in _simple_clara_actions_to_execute_locally:
                    result = perform_simple_clara_action_helper(username, project_id, simple_clara_action, callback=None)
                    if _simple_clara_trace:
                        print(f'result = {result}')
                    new_project_id = result['project_id'] if 'project_id' in result else project_id
                    new_status = result['status']
                    if new_status == 'error':
                        #messages.error(request, f"Something went wrong. Try looking at the 'Recent task updates' view")
                        error_message = result['error']
                        messages.error(request, f"Something went wrong: {error_message}")
                    else:
                        success_message = result['message'] if 'message' in result else f'Simple C-LARA operation succeeded'
                        messages.success(request, success_message)
                    return redirect('simple_clara', new_project_id, new_status)
                else:
                    #if not request.user.userprofile.credit > 0:
                    if not user_has_open_ai_key_or_credit(user):
                        messages.error(request, f"Sorry, you need a registered OpenAI API key or money in your account to perform this operation")
                        return redirect('simple_clara', project_id, 'initial')
                    else:
                        task_type = f'simple_clara_action'
                        callback, report_id = make_asynch_callback_and_report_id(request, task_type)

                        print(f'--- Starting async task, simple_clara_action = {simple_clara_action}')
                        
                        async_task(perform_simple_clara_action_helper, username, project_id, simple_clara_action, callback=callback)

                        return redirect('simple_clara_monitor', project_id, report_id)
    
    clara_version = get_user_config(request.user)['clara_version']

    if _simple_clara_trace and 'v2_images_dict' in resources:
        pprint.pprint(resources['v2_images_dict'])
    
    return render(request, 'clara_app/simple_clara.html', {
        'project_id': project_id,
        'form': form,
        'resources': resources,
        'up_to_date_dict': up_to_date_dict,
        'content': content,
        'status': status,
        'simple_clara_type': simple_clara_type,
        'clara_version': clara_version
    })

# Function to be executed, possibly in async process. We pass in the username, a project_id, and a 'simple_clara_action',
# which is a dict containing the other inputs needed for the action in question.
#
# If the action succeeds, it usually returns a dict of the form { 'status': 'finished', 'message': message }
# In the special case of 'create_project', it also returns a 'project_id'.
#
# If it fails, it returns a dict of the form { 'status': 'error', 'error': error_message }
def perform_simple_clara_action_helper(username, project_id, simple_clara_action, callback=None):
    if _simple_clara_trace:
        print(f'perform_simple_clara_action_helper({username}, {project_id}, {simple_clara_action}, callback={callback}')
    try:
        action_type = simple_clara_action['action']
        if action_type == 'create_project':
            # simple_clara_action should be of form { 'action': 'create_project', 'l2': text_language, 'l1': annotation_language,
            #                                         'title': title, 'simple_clara_type': simple_clara_type }
            result = simple_clara_create_project_helper(username, simple_clara_action, callback=callback)
        elif action_type == 'change_title':
            # simple_clara_action should be of form { 'action': 'create_project', 'l2': text_language, 'l1': annotation_language, 'title': title }
            result = simple_clara_change_title_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'create_text':
            # simple_clara_action should be of form { 'action': 'create_text', 'prompt': prompt }
            result = simple_clara_create_text_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'create_text_and_image':
            # simple_clara_action should be of form { 'action': 'create_text_and_image', 'prompt': prompt }
            result = simple_clara_create_text_and_image_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'save_image_and_create_text':
            # simple_clara_action should be of form { 'action': 'save_image_and_create_text', 'image_file_path': image_file_path, 'prompt': prompt }
            result = simple_clara_save_image_and_create_text_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'save_text_and_create_image':
            # simple_clara_action should be of form { 'action': 'save_text_and_create_image', 'plain_text': plain_text }
            result = simple_clara_save_text_and_create_image_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'regenerate_text_from_image':
            # simple_clara_action should be of form { 'action': 'regenerate_text_from_image', 'prompt': prompt }
            result = simple_clara_regenerate_text_from_image_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'save_text':
            # simple_clara_action should be of form { 'action': 'save_text', 'plain_text': plain_text }
            result = simple_clara_save_text_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'save_segmented_text':
            # simple_clara_action should be of form { 'action': 'save_segmented_text', 'segmented_text': segmented_text }
            result = simple_clara_save_segmented_text_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'save_segmented_title':
            # simple_clara_action should be of form { 'action': 'save_segmented_title', 'segmented_title': segmented_title }
            result = simple_clara_save_segmented_title_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'save_text_title':
            # simple_clara_action should be of form { 'action': 'save_text_title', 'text_title': text_title }
            result = simple_clara_save_text_title_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'save_uploaded_image':
            # simple_clara_action should be of form 'action': 'save_uploaded_image', 'image_file_path': image_file_path }
            result = simple_clara_save_uploaded_image_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'rewrite_text':
            # simple_clara_action should be of form { 'action': 'rewrite_text', 'prompt': prompt }
            result = simple_clara_rewrite_text_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'regenerate_image':
            # simple_clara_action should be of form { 'action': 'regenerate_image', 'image_advice_prompt': image_advice_prompt }
            result = simple_clara_regenerate_image_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'create_segmented_text':
            # simple_clara_action should be of form { 'action': 'create_segmented_text', 'up_to_date_dict': up_to_date_dict }
            result = simple_clara_create_segmented_text_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'create_v2_style':
            #simple_clara_action should be of the form { 'action': 'create_v2_style',
            #                                            'description_language': description_language,
            #                                            'style_advice':style_advice, 'up_to_date_dict': up_to_date_dict }
            result = simple_clara_create_v2_style_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'create_v2_elements':
            #simple_clara_action should be of the form { 'action': 'create_v2_elements', 'up_to_date_dict': up_to_date_dict }
            result = simple_clara_create_v2_elements_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'delete_v2_element':
            #simple_clara_action should be of the form { 'action': 'delete_v2_element', 'deleted_element_text': deleted_element_text }
            result = simple_clara_delete_v2_element_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'add_v2_element':
            #simple_clara_action should bge of the form { 'action': 'add_v2_element', 'new_element_text': new_element_text }
            result = simple_clara_add_v2_element_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'create_v2_pages':
            #simple_clara_action should be of the form { 'action': 'create_v2_pages', 'up_to_date_dict': up_to_date_dict }
            result = simple_clara_create_v2_pages_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'save_preferred_tts_engine':
            # simple_clara_action should be of form { 'action': 'save_preferred_tts_engine', 'preferred_tts_engine': preferred_tts_engine }
            result = simple_clara_save_preferred_tts_engine_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'create_rendered_text':
            # simple_clara_action should be of form { 'action': 'create_rendered_text', 'up_to_date_dict': up_to_date_dict }
            result = simple_clara_create_rendered_text_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'post_rendered_text':
            # simple_clara_action should be of form { 'action': 'post_rendered_text' }
            result = simple_clara_post_rendered_text_helper(username, project_id, simple_clara_action, callback=callback)
        else:
            result = { 'status': 'error',
                       'error': f'Unknown simple_clara action type in: {simple_clara_action}' }
    except Exception as e:
        result = { 'status': 'error',
                   'error': f'Exception when executing simple_clara action {simple_clara_action}: {str(e)}\n{traceback.format_exc()}' }

    if result['status'] == 'finished':
        # Note that we post "finished_simple_clara_action" to distinguish from the lower-level "finished".
        # This is what simple_clara_status is listening for
        post_task_update(callback, f"finished_simple_clara_action")
    else:
        if 'error' in result:
            post_task_update(callback, result['error'])
        # Note that we post "error_simple_clara_action" to distinguish from the lower-level "error".
        # This is what simple_clara_status is listening for
        post_task_update(callback, f"error_simple_clara_action")

    return result

@login_required
def simple_clara_status(request, project_id, report_id):
    messages = get_task_updates(report_id)
    print(f'{len(messages)} messages received')
    status = 'unknown'
    new_project_id = 'no_project_id'
    if 'error_simple_clara_action' in messages:
        status = 'error'
    elif 'finished_simple_clara_action' in messages:
        status = 'finished'  
    else:
        status = 'unknown'    
    return JsonResponse({'messages': messages, 'status': status})

@login_required
def simple_clara_monitor(request, project_id, report_id):
    project = get_object_or_404(CLARAProject, pk=project_id)

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/simple_clara_monitor.html',
                  {'project_id': project_id, 'project': project, 'report_id': report_id, 'clara_version':clara_version})

def simple_clara_create_project_helper(username, simple_clara_action, callback=None):
    if _simple_clara_trace:
        print(f'Calling simple_clara_create_project_helper')
    l2_language = simple_clara_action['l2']
    l1_language = simple_clara_action['l1']
    title = simple_clara_action['title']
    simple_clara_type = simple_clara_action['simple_clara_type']
    # Create a new project in Django's database, associated with the current user
    user = User.objects.get(username=username)
    uses_coherent_image_set_v2 = ( simple_clara_type == 'create_text_and_multiple_images' )
    clara_project = CLARAProject(title=title, user=user, l2=l2_language, l1=l1_language, uses_coherent_image_set_v2=uses_coherent_image_set_v2)
    clara_project.save()
    internal_id = create_internal_project_id(title, clara_project.id)
    # Update the Django project with the internal_id and simple_clara_type
    clara_project.internal_id = internal_id
    clara_project.simple_clara_type = simple_clara_type
    clara_project.save()
    # Create a new internal project in the C-LARA framework
    clara_project_internal = CLARAProjectInternal(internal_id, l2_language, l1_language)
    post_task_update(callback, f"--- Created project '{title}'")
    if uses_coherent_image_set_v2:
        clara_project_internal.save_coherent_images_v2_params(project_params_for_simple_clara)
    return { 'status': 'finished',
             'message': 'Project created',
             'project_id': clara_project.id }

def simple_clara_change_title_helper(username, project_id, simple_clara_action, callback=None):
    title = simple_clara_action['title']
    project = get_object_or_404(CLARAProject, pk=project_id)
    
    project.title = title
    project.save()
            
    post_task_update(callback, f"--- Updated project title to '{title}'")
    return { 'status': 'finished',
             'message': 'Title updated',
             'project_id': project_id }

def simple_clara_create_text_helper(username, project_id, simple_clara_action, callback=None):
    prompt = simple_clara_action['prompt']
    
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    title = project.title
    user = project.user
    config_info = get_user_config(user)

    # Create the text
    post_task_update(callback, f"STARTED TASK: create plain text")
    api_calls = clara_project_internal.create_plain_text(prompt=prompt, user=username, config_info=config_info, callback=callback)
    store_api_calls(api_calls, project, user, 'plain')
    post_task_update(callback, f"ENDED TASK: create plain text")

    # Create the title
    post_task_update(callback, f"STARTED TASK: create text title")
    api_calls = clara_project_internal.create_title(user=username, config_info=config_info, callback=callback)
    store_api_calls(api_calls, project, user, 'text_title')
    post_task_update(callback, f"ENDED TASK: create text title")

    return { 'status': 'finished',
             'message': 'Created text and title.' }

def simple_clara_create_text_and_image_helper(username, project_id, simple_clara_action, callback=None):
    prompt = simple_clara_action['prompt']
    
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    title = project.title
    user = project.user
    config_info = get_user_config(user)

    # Create the text
    post_task_update(callback, f"STARTED TASK: create plain text")
    api_calls = clara_project_internal.create_plain_text(prompt=prompt, user=username, config_info=config_info, callback=callback)
    store_api_calls(api_calls, project, user, 'plain')
    post_task_update(callback, f"ENDED TASK: create plain text")

    # Create the title
    post_task_update(callback, f"STARTED TASK: create text title")
    api_calls = clara_project_internal.create_title(user=username, config_info=config_info, callback=callback)
    store_api_calls(api_calls, project, user, 'text_title')
    post_task_update(callback, f"ENDED TASK: create text title")

    # Create the image
    post_task_update(callback, f"STARTED TASK: generate DALL-E-3 image")
    create_and_add_dall_e_3_image_for_whole_text(project_id, callback=None)
    post_task_update(callback, f"ENDED TASK: generate DALL-E-3 image")

    if clara_project_internal.get_project_image('DALLE-E-3-Image-For-Whole-Text'):
        return { 'status': 'finished',
                 'message': 'Created text, title and image' }
    else:
        return { 'status': 'finished',
                 'message': 'Created text and title but was unable to create image. Probably DALL-E-3 thought something was inappropriate.' }

# simple_clara_action should be of form { 'action': 'save_text_and_create_image', 'plain_text': plain_text }
def simple_clara_save_text_and_create_image_helper(username, project_id, simple_clara_action, callback=None):
    plain_text = simple_clara_action['plain_text']
    
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    title = project.title
    user = project.user
    config_info = get_user_config(user)

    # Save the text
    clara_project_internal.save_text_version('plain', plain_text, user=user.username, source='user_provided')

    # Create the title
    post_task_update(callback, f"STARTED TASK: create text title")
    api_calls = clara_project_internal.create_title(user=username, config_info=config_info, callback=callback)
    store_api_calls(api_calls, project, user, 'text_title')
    post_task_update(callback, f"ENDED TASK: create text title")

    # Create the image
    post_task_update(callback, f"STARTED TASK: generate DALL-E-3 image")
    create_and_add_dall_e_3_image_for_whole_text(project_id, callback=None)
    post_task_update(callback, f"ENDED TASK: generate DALL-E-3 image")

    if clara_project_internal.get_project_image('DALLE-E-3-Image-For-Whole-Text'):
        return { 'status': 'finished',
                 'message': 'Created title and image' }
    else:
        return { 'status': 'finished',
                 'message': 'Created title but was unable to create image. Probably DALL-E-3 thought something was inappropriate.' }

# simple_clara_action should be of form { 'action': 'save_image_and_create_text', 'image_file_path': image_file_path, 'prompt': prompt }
def simple_clara_save_image_and_create_text_helper(username, project_id, simple_clara_action, callback=None):
    image_file_path = simple_clara_action['image_file_path']
    prompt = simple_clara_action['prompt']

    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    title = project.title
    user = project.user
    l2 = project.l2
    config_info = get_user_config(user)

    image_name = 'DALLE-E-3-Image-For-Whole-Text'
    clara_project_internal.add_project_image(image_name, image_file_path, 
                                             associated_text='', associated_areas='',
                                             page=1, position='top')

    permanent_image_file_path = clara_project_internal.get_project_image(image_name, callback=callback).image_file_path

    clara_project_internal.save_text_version('prompt', prompt, user=user.username, source='user_supplied')

    if not prompt:
        prompt = f'Write an imaginative story in {l2} based on this image.'
    else:
        language_reminder = f'\nThe text you produce must be written in {l2}.'
        prompt += language_reminder

    # Create the text from the image
    post_task_update(callback, f"STARTED TASK: create plain text from image")
    api_call = call_chat_gpt4_interpret_image(prompt, permanent_image_file_path, config_info=config_info, callback=callback)
    plain_text = api_call.response
    clara_project_internal.save_text_version('plain', plain_text, user=user.username, source='ai_generated')
    store_api_calls([ api_call ], project, user, 'plain')
    post_task_update(callback, f"ENDED TASK: create plain text from image")

    # Create the title
    post_task_update(callback, f"STARTED TASK: create text title")
    api_calls = clara_project_internal.create_title(user=username, config_info=config_info, callback=callback)
    store_api_calls(api_calls, project, user, 'text_title')
    post_task_update(callback, f"ENDED TASK: create text title")

    return { 'status': 'finished',
             'message': 'Created text and title from image' }


# simple_clara_action should be of form { 'action': 'regenerate_text_from_image', 'prompt': prompt }
def simple_clara_regenerate_text_from_image_helper(username, project_id, simple_clara_action, callback=None):
    prompt = simple_clara_action['prompt']
    
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    title = project.title
    user = project.user
    l2 = project.l2
    config_info = get_user_config(user)

    image_name = 'DALLE-E-3-Image-For-Whole-Text'
    image = clara_project_internal.get_project_image(image_name, callback=callback)
    if not image:
         return { 'status': 'error',
                  'error': f'There is no image to generate from' }
    permanent_image_file_path = image.image_file_path

    clara_project_internal.save_text_version('prompt', prompt, user=user.username, source='user_supplied')

    language_reminder = f'\nThe text you produce must be written in {l2}.'
    full_prompt = prompt + language_reminder

    # Create the text from the image
    post_task_update(callback, f"STARTED TASK: regenerate plain text from image")
    api_call = call_chat_gpt4_interpret_image(full_prompt, permanent_image_file_path, config_info=config_info, callback=callback)
    plain_text = api_call.response
    clara_project_internal.save_text_version('plain', plain_text, user=user.username, source='ai_generated')
    store_api_calls([ api_call ], project, user, 'plain')
    post_task_update(callback, f"ENDED TASK: regenerate plain text from image")

    # Create the title
    post_task_update(callback, f"STARTED TASK: create text title")
    api_calls = clara_project_internal.create_title(user=username, config_info=config_info, callback=callback)
    store_api_calls(api_calls, project, user, 'text_title')
    post_task_update(callback, f"ENDED TASK: create text title")

    return { 'status': 'finished',
             'message': 'Regenerated text and title from image' }

def simple_clara_save_text_helper(username, project_id, simple_clara_action, callback=None):
    plain_text = simple_clara_action['plain_text']
    
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    # Save the text
    clara_project_internal.save_text_version('plain', plain_text, source='human_revised', user=username)

    return { 'status': 'finished',
             'message': 'Saved the text.'}

def simple_clara_save_segmented_text_helper(username, project_id, simple_clara_action, callback=None):
    segmented_text = simple_clara_action['segmented_text']
    
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    # Save the segmented text
    clara_project_internal.save_text_version('segmented', segmented_text, source='human_revised', user=username)

    return { 'status': 'finished',
             'message': 'Saved the segmented text.'}

def simple_clara_save_text_title_helper(username, project_id, simple_clara_action, callback=None):
    text_title = simple_clara_action['text_title']
    
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    # Save the text
    clara_project_internal.save_text_version('title', text_title, source='human_revised', user=username)

    return { 'status': 'finished',
             'message': 'Saved the text title.'}

def simple_clara_save_segmented_title_helper(username, project_id, simple_clara_action, callback=None):
    segmented_title = simple_clara_action['segmented_title']
    
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    # Save the segmented title
    clara_project_internal.save_text_version('segmented_title', segmented_title, source='human_revised', user=username)

    return { 'status': 'finished',
             'message': 'Saved the segmented title.'}

# simple_clara_action should be of form 'action': 'save_uploaded_image', 'image_file_path': image_file_path }
def simple_clara_save_uploaded_image_helper(username, project_id, simple_clara_action, callback=None):
    image_file_path = simple_clara_action['image_file_path']

    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    
    image_name = 'DALLE-E-3-Image-For-Whole-Text'
    clara_project_internal.add_project_image(image_name, image_file_path, 
                                             associated_text='', associated_areas='',
                                             page=1, position='top')

    return { 'status': 'finished',
             'message': 'Saved the image.'}

# simple_clara_action should be of form { 'action': 'save_preferred_tts_engine', 'preferred_tts_engine': preferred_tts_engine }
def simple_clara_save_preferred_tts_engine_helper(username, project_id, simple_clara_action, callback=None):
    preferred_tts_engine = simple_clara_action['preferred_tts_engine']
    project = get_object_or_404(CLARAProject, pk=project_id)
    language = project.l2

    human_audio_info, human_audio_info_created = HumanAudioInfo.objects.get_or_create(project=project)
    human_audio_info.preferred_tts_engine = preferred_tts_engine
    human_audio_info.save()

    preferred_tts_engine_name = dict(TTS_CHOICES)[preferred_tts_engine]
    if preferred_tts_engine == 'openai' and language != 'english':
        warning = f' Warning: although {preferred_tts_engine_name} is supposed to be multilingual, it is optimised for English.'
    elif preferred_tts_engine != 'none' and not tts_engine_type_supports_language(preferred_tts_engine, language):
        warning = f' Warning: {preferred_tts_engine_name} does not currently support {language.capitalize()}.'
    else:
        warning = ''

    message = f'Saved {preferred_tts_engine_name} as preferred TTS engine.' + warning

    return { 'status': 'finished',
             'message': message}

def simple_clara_rewrite_text_helper(username, project_id, simple_clara_action, callback=None):
    prompt = simple_clara_action['prompt']
    
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    title = project.title
    user = project.user
    config_info = get_user_config(user)

    # Rewrite the text
    post_task_update(callback, f"STARTED TASK: rewrite plain text")
    api_calls = clara_project_internal.improve_plain_text(prompt=prompt, user=username, config_info=config_info, callback=callback)
    store_api_calls(api_calls, project, user, 'image')
    post_task_update(callback, f"ENDED TASK: rewrite plain text")

    return { 'status': 'finished',
             'message': 'Rewrote the text'}

def simple_clara_regenerate_image_helper(username, project_id, simple_clara_action, callback=None):
    image_advice_prompt = simple_clara_action['image_advice_prompt']
    
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    
    user = project.user
    title = project.title

    # Create the image
    post_task_update(callback, f"STARTED TASK: regenerate DALL-E-3 image")
    result = create_and_add_dall_e_3_image_for_whole_text(project_id, advice_prompt=image_advice_prompt, callback=callback)
    post_task_update(callback, f"ENDED TASK: regenerate DALL-E-3 image")

    if clara_project_internal.get_project_image('DALLE-E-3-Image-For-Whole-Text') and result:
        return { 'status': 'finished',
                 'message': 'Regenerated the image' }
    else:
        return { 'status': 'error',
                 'message': "Unable to regenerate the image. Try looking at the 'Recent task updates' view" }

def simple_clara_create_v2_style_helper(username, project_id, simple_clara_action, callback=None):
    description_language = simple_clara_action['description_language']
    style_advice = simple_clara_action['style_advice']
    up_to_date_dict = simple_clara_action['up_to_date_dict']
    
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    params = clara_project_internal.get_v2_project_params_for_simple_clara()
    if description_language:
        params['text_language'] = description_language
        clara_project_internal.save_coherent_images_v2_params(params)
    
    numbered_page_list = numbered_page_list_for_coherent_images(project, clara_project_internal)
    clara_project_internal.set_story_data_from_numbered_page_list_v2(numbered_page_list)

    # Create or recreate the style
##    if not up_to_date_dict['v2_style_image']:
##        post_task_update(callback, f"STARTED TASK: create image style information")
##        clara_project_internal.set_style_advice_v2(style_advice)
##        style_params = get_style_params_from_project_params(params)
##        style_cost_dict = clara_project_internal.create_style_description_and_image_v2(style_params, callback=callback)
##        store_cost_dict(style_cost_dict, project, project.user)
##        post_task_update(callback, f"ENDED TASK: create image style information")
    post_task_update(callback, f"STARTED TASK: create image style information")
    clara_project_internal.set_style_advice_v2(style_advice)
    style_params = get_style_params_from_project_params(params)
    style_cost_dict = clara_project_internal.create_style_description_and_image_v2(style_params, callback=callback)
    store_cost_dict(style_cost_dict, project, project.user)
    post_task_update(callback, f"ENDED TASK: create image style information")

    return { 'status': 'finished',
             'message': 'Created the images' }

def simple_clara_create_v2_elements_helper(username, project_id, simple_clara_action, callback=None):
    up_to_date_dict = simple_clara_action['up_to_date_dict']
    
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    params = clara_project_internal.get_coherent_images_v2_params()

    # Create the elements
    if not up_to_date_dict['v2_element_images']:
        elements_params = get_element_descriptions_params_from_project_params(params)
        post_task_update(callback, f"STARTED TASK: create element names")
        element_names_cost_dict = clara_project_internal.create_element_names_v2(elements_params, callback=callback)
        store_cost_dict(element_names_cost_dict, project, project.user)
        post_task_update(callback, f"ENDED TASK: create element names")
    
        post_task_update(callback, f"STARTED TASK: create element descriptions and images")
        element_descriptions_cost_dict = clara_project_internal.create_element_descriptions_and_images_v2(elements_params, callback=callback)
        store_cost_dict(element_descriptions_cost_dict, project, project.user)
        post_task_update(callback, f"ENDED TASK: create element descriptions and images")

    return { 'status': 'finished',
             'message': 'Created the images' }

#simple_clara_action should be of the form { 'action': 'delete_v2_element', 'deleted_element_text': deleted_element_text }
def simple_clara_delete_v2_element_helper(username, project_id, simple_clara_action, callback=None):
    deleted_element_text = simple_clara_action['deleted_element_text']
    
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    params = clara_project_internal.get_coherent_images_v2_params()

    # Delete the element
    elements_params = get_element_descriptions_params_from_project_params(params)
    clara_project_internal.delete_element_v2(elements_params, deleted_element_text)

    return { 'status': 'finished',
             'message': f'Deleted element: "{deleted_element_text}"' }

#simple_clara_action should be of the form { 'action': 'add_v2_element', 'new_element_text': new_element_text }
def simple_clara_add_v2_element_helper(username, project_id, simple_clara_action, callback=None):
    new_element_text = simple_clara_action['new_element_text']
    
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    params = clara_project_internal.get_coherent_images_v2_params()

    # Add the elements
    elements_params = get_element_descriptions_params_from_project_params(params)
    post_task_update(callback, f"STARTED TASK: Adding element")
    element_names_cost_dict = clara_project_internal.add_element_v2(elements_params, new_element_text, callback=callback)
    store_cost_dict(element_names_cost_dict, project, project.user)
    post_task_update(callback, f"ENDED TASK: Added element")

    return { 'status': 'finished',
             'message': f'Added element: "{new_element_text}"' }

def simple_clara_create_v2_pages_helper(username, project_id, simple_clara_action, callback=None):
    up_to_date_dict = simple_clara_action['up_to_date_dict']
    
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    params = clara_project_internal.get_coherent_images_v2_params()

    # Create the page images
    if not up_to_date_dict['v2_page_images']:
        post_task_update(callback, f"STARTED TASK: create page images")
        page_params = get_page_params_from_project_params(params)
        pages_cost_dict = clara_project_internal.create_page_descriptions_and_images_v2(page_params, project_id, callback=callback)
        store_cost_dict(pages_cost_dict, project, project.user)
        post_task_update(callback, f"ENDED TASK: create page images")

    return { 'status': 'finished',
             'message': 'Created the images' }  

def simple_clara_create_segmented_text_helper(username, project_id, simple_clara_action, callback=None):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    up_to_date_dict = simple_clara_action['up_to_date_dict']

    l2 = project.l2
    title = project.title
    user = project.user
    config_info = get_user_config(user)

    # Create segmented text
    if not up_to_date_dict['segmented']:
        post_task_update(callback, f"STARTED TASK: add segmentation information")
        api_calls = clara_project_internal.create_segmented_text(user=username, config_info=config_info, callback=callback)
        store_api_calls(api_calls, project, user, 'segmented')
        post_task_update(callback, f"ENDED TASK: add segmentation information")

    # Create segmented title. This will just have been done as part of create_segmented_text if we ran that step
    if up_to_date_dict['segmented'] and not up_to_date_dict['segmented_title']:
        post_task_update(callback, f"STARTED TASK: add segmentation information to text title")
        api_calls = clara_project_internal.create_segmented_title(user=username, config_info=config_info, callback=callback)
        store_api_calls(api_calls, project, user, 'segmented_title')
        post_task_update(callback, f"ENDED TASK: add segmentation information to text title")

    return { 'status': 'finished',
             'message': 'Created the segmented text.'}

def simple_clara_create_rendered_text_helper(username, project_id, simple_clara_action, callback=None):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    up_to_date_dict = simple_clara_action['up_to_date_dict']

    l2 = project.l2
    title = project.title
    user = project.user
    config_info = get_user_config(user)

    audio_info = HumanAudioInfo.objects.filter(project=project).first()
    preferred_tts_engine = audio_info.preferred_tts_engine if audio_info else None
    print(f'--- preferred_tts_engine = {preferred_tts_engine}')

    # Create summary
    if not up_to_date_dict['summary']:
        post_task_update(callback, f"STARTED TASK: create summary")
        api_calls = clara_project_internal.create_summary(user=username, config_info=config_info, callback=callback)
        store_api_calls(api_calls, project, user, 'summary')
        post_task_update(callback, f"ENDED TASK: create summary")

    # Get CEFR level
    if not up_to_date_dict['cefr_level']:
        post_task_update(callback, f"STARTED TASK: get CEFR level")
        api_calls = clara_project_internal.get_cefr_level(user=username, config_info=config_info, callback=callback)
        store_api_calls(api_calls, project, user, 'cefr_level')
        post_task_update(callback, f"ENDED TASK: get CEFR level")

    # Create segmented text
    if not up_to_date_dict['segmented']:
        post_task_update(callback, f"STARTED TASK: add segmentation information")
        api_calls = clara_project_internal.create_segmented_text(user=username, config_info=config_info, callback=callback)
        store_api_calls(api_calls, project, user, 'segmented')
        post_task_update(callback, f"ENDED TASK: add segmentation information")

    # Create segmented title. This will just have been done as part of create_segmented_text if we ran that step
    if up_to_date_dict['segmented'] and not up_to_date_dict['segmented_title']:
        post_task_update(callback, f"STARTED TASK: add segmentation information to text title")
        api_calls = clara_project_internal.create_segmented_title(user=username, config_info=config_info, callback=callback)
        store_api_calls(api_calls, project, user, 'segmented_title')
        post_task_update(callback, f"ENDED TASK: add segmentation information to text title")

    # Create translated text
    if not up_to_date_dict['translated']:
        post_task_update(callback, f"STARTED TASK: add segment translations")
        api_calls = clara_project_internal.create_translated_text(user=username, config_info=config_info, callback=callback)
        store_api_calls(api_calls, project, user, 'translate')
        post_task_update(callback, f"ENDED TASK: add segment translations")

    # Create MWE-annotated text
    if not up_to_date_dict['mwe']:
        post_task_update(callback, f"STARTED TASK: find MWEs")
        api_calls = clara_project_internal.create_mwe_tagged_text(user=username, config_info=config_info, callback=callback)
        store_api_calls(api_calls, project, user, 'mwe')
        post_task_update(callback, f"ENDED TASK: find MWEs")

    # Create glossed text
    if not up_to_date_dict['gloss']:
        post_task_update(callback, f"STARTED TASK: add glosses")
        api_calls = clara_project_internal.create_glossed_text(user=username, config_info=config_info, callback=callback)
        store_api_calls(api_calls, project, user, 'gloss')
        post_task_update(callback, f"ENDED TASK: add glosses")

    # Create lemma-tagged text
    if not up_to_date_dict['lemma']:
        post_task_update(callback, f"STARTED TASK: add lemma tags")
        if is_chinese_language(l2):
            # AI-based tagging doesn't seem to do well with Chinese languages, they lack inflection, and we don't currently use the POS tags
            api_calls = clara_project_internal.create_lemma_tagged_text_with_trivial_tags(user=username, config_info=config_info, callback=callback)
        else:
            api_calls = clara_project_internal.create_lemma_tagged_text(user=username, config_info=config_info, callback=callback)
        store_api_calls(api_calls, project, user, 'lemma')
        post_task_update(callback, f"ENDED TASK: add lemma tags")

    # Create pinyin-tagged text
    if is_chinese_language(l2) and not up_to_date_dict['pinyin']:
        post_task_update(callback, f"STARTED TASK: add pinyin")
        if l2 == 'mandarin':
            # So far, pypinyin seems to do better than the AI, but my understanding is that it only works for Mandarin
             api_calls = clara_project_internal.create_pinyin_tagged_text_using_pypinyin(user=username, config_info=config_info, callback=callback)
        else:
            api_calls = clara_project_internal.create_pinyin_tagged_text(user=username, config_info=config_info, callback=callback)
        store_api_calls(api_calls, project, user, 'pinyin')
        post_task_update(callback, f"ENDED TASK: add pinyin")

    # Render
    if not up_to_date_dict['render']:
        post_task_update(callback, f"STARTED TASK: create TTS audio and multimodal text")
        clara_project_internal.render_text(project_id, phonetic=False, preferred_tts_engine=preferred_tts_engine,
                                           self_contained=True, callback=callback)
        post_task_update(callback, f"ENDED TASK: create TTS audio and multimodal text")

    if phonetic_resources_are_available(project.l2):
        # Create phonetic text
        if not up_to_date_dict['phonetic']:
            post_task_update(callback, f"STARTED TASK: create phonetic text")
            clara_project_internal.create_phonetic_text(user=username, config_info=config_info, callback=callback)
            post_task_update(callback, f"ENDED TASK: create phonetic text")

        # Render phonetic text and then render normal text again to get the links right
        if not up_to_date_dict['render_phonetic']:
            post_task_update(callback, f"STARTED TASK: create phonetic multimodal text")
            clara_project_internal.render_text(project_id, phonetic=True, self_contained=True, callback=callback)
            clara_project_internal.render_text(project_id, phonetic=False, self_contained=True, callback=callback)
            post_task_update(callback, f"ENDED TASK: create phonetic multimodal text")

    return { 'status': 'finished',
             'message': 'Created the multimedia text.'}

def simple_clara_post_rendered_text_helper(username, project_id, simple_clara_action, callback=None):
    project = get_object_or_404(CLARAProject, pk=project_id)
    title = project.title
    
    phonetic_or_normal = 'normal'
    
    register_project_content_helper(project_id, phonetic_or_normal)

    post_task_update(callback, f"--- Registered project content for '{title}'")

    return { 'status': 'finished',
             'message': 'Posted multimedia text on C-LARA social network.'}

@login_required
def simple_clara_review_v2_images_for_page(request, project_id, page_number, from_view, status):
    user = request.user
    can_use_ai = user_has_open_ai_key_or_credit(user)
    config_info = get_user_config(user)
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    project_dir = clara_project_internal.coherent_images_v2_project_dir
    
    story_data = read_project_json_file(project_dir, 'story.json')
    page = story_data[page_number - 1]
    page_text = page.get('text', '').strip()
    original_page_text = page.get('original_page_text', '').strip()

    try:
        advice = clara_project_internal.get_page_advice_v2(page_number)
        print(f'advice = {advice}')
    except Exception as e:
        print(f"Error getting element advice for page {page_number}: {e}\n{traceback.format_exc()}")
        advice = ''

    # Update AI votes
    try:
        update_ai_votes_in_feedback(project_dir, page_number)
    except Exception as e:
        messages.error(request, f"Error updating AI votes: {e}\n{traceback.format_exc()}")

    # Load alternate images
    content_dir = project_pathname(project_dir, f"pages/page{page_number}")
    alternate_images = asyncio.run(get_alternate_images_json(content_dir, project_dir))

    # Process form submissions
    if request.method == 'POST':
        action = request.POST.get('action', '')
        description_index = request.POST.get('description_index', '')
        image_index = request.POST.get('image_index', '')
        userid = request.user.username

        if description_index is not None and description_index != '':
            description_index = int(description_index)
        if image_index is not None and image_index != '':
            image_index = int(image_index)
        else:
            image_index = None

        try:
            #print(f'action = {action}')
            if action in ( 'variants_requests', 'images_with_advice', 'upload_image' ):
                if not can_use_ai:
                    messages.error(request, f"Sorry, you need a registered OpenAI API key or money in your account to create images")
                    return redirect('simple_clara_review_v2_images_for_page', project_id=project_id, page_number=page_number, from_view=from_view, status='none')

                if project.use_translation_for_images and page_number in clara_project_internal.pages_with_missing_story_text_v2():
                    messages.error(request, f"Cannot create images. Project is marked as using translations to create images, but page {page_number} has no translation yet.")
                    return redirect('simple_clara_review_v2_images_for_page', project_id=project_id, page_number=page_number, from_view=from_view, status='none')

                if action == 'variants_requests':
                    requests = [ { 'request_type': 'variants_requests',
                                   'page': page_number,
                                   'description_index': description_index } ]
                elif action == 'images_with_advice':
                    mode = request.POST.get('mode')
                    advice_or_description_text = request.POST.get('advice_or_description_text', '').strip()
                    if mode == 'advice':
                        requests = [ { 'request_type': 'image_with_advice',
                                       'page': page_number,
                                       'advice_text': advice_or_description_text } ]
                    elif mode == 'expanded_description':
                        requests = [ { 'request_type': 'image_with_description',
                                       'page': page_number,
                                       'description_text': advice_or_description_text } ]
                    else:
                        messages.error(request, f"Unknown mode '{mode}'")
                        return redirect('simple_clara_review_v2_images_for_page', project_id=project_id, page_number=page_number, from_view=from_view, status='none')
                elif action == 'upload_image':
                    # The user is uploading a new image
                    if 'uploaded_image_file_path' in request.FILES:
                        # Convert the in-memory file object to a local file path
                        uploaded_file_obj = request.FILES['uploaded_image_file_path']
                        real_image_file_path = uploaded_file_to_file(uploaded_file_obj)

                        requests = [ { 'request_type': 'add_uploaded_page_image',
                                       'page': page_number,
                                       'image_file_path': real_image_file_path } ]

                    else:
                        messages.error(request, "No file found for the upload_image action.")
                        return redirect('simple_clara_review_v2_images_for_page', project_id=project_id, page_number=page_number, from_view=from_view, status='none')

                else:
                    messages.error(request, f"Unknown request type '{action}'")
                    return redirect('simple_clara_review_v2_images_for_page', project_id=project_id, page_number=page_number, from_view=from_view, status='none')

                callback, report_id = make_asynch_callback_and_report_id(request, 'execute_image_requests')

                async_task(execute_simple_clara_image_requests, project, clara_project_internal, requests, callback=callback)

                return redirect('execute_simple_clara_image_requests_monitor', project_id, report_id, page_number, from_view)
                
            elif action == 'vote':
                vote_type = request.POST.get('vote_type')  # "upvote" or "downvote"
                if vote_type in ['upvote', 'downvote'] and image_index is not None:
                    register_cm_image_vote(project_dir, page_number, description_index, image_index, vote_type, userid, override_ai_vote=True)
                else:
                    messages.error(request, "No file found for the upload_image action.")

        except Exception as e:
            messages.error(request, f"Error processing your request: {str(e)}\n{traceback.format_exc()}")

        return redirect('simple_clara_review_v2_images_for_page', project_id=project_id, page_number=page_number, from_view=from_view, status='none')

    # GET

    descriptions_info, preferred_image_id = get_page_description_info_for_cm_reviewing('simple_clara', alternate_images, page_number, project_dir)

    # In case the preferred image has changed from last time promote it
    if preferred_image_id is not None:
        clara_project_internal.promote_v2_page_image(page_number, preferred_image_id)

    # If 'status' is something we got after returning from an async call, display a suitable message
    if status == 'finished':
        messages.success(request, "Image task successfully completed")
    elif status == 'error':
        messages.error(request, "Something went wrong when performing this image task. Look at the 'Recent task updates' view for further information.")

    rendering_parameters = {
        'project': project,
        'page_number': page_number,
        'page_text': page_text,
        'advice': advice,
        'original_page_text': original_page_text,
        'descriptions_info': descriptions_info,
        'from_view': from_view,
    }

    #pprint.pprint(rendering_parameters)

    return render(request, 'clara_app/simple_clara_review_v2_images_for_page.html', rendering_parameters)

@login_required
def simple_clara_review_v2_images_for_element(request, project_id, element_name, from_view, status):
    user = request.user
    can_use_ai = user_has_open_ai_key_or_credit(user)
    config_info = get_user_config(user)
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    project_dir = clara_project_internal.coherent_images_v2_project_dir
    
    story_data = read_project_json_file(project_dir, 'story.json')

    try:
        element_text = clara_project_internal.element_name_to_element_text(element_name)
        print(f'element_text = {element_text}')
        advice = clara_project_internal.get_element_advice_v2(element_text)
        print(f'advice = {advice}')
    except Exception as e:
        print(f"Error getting element advice for {element_name}: {e}\n{traceback.format_exc()}")
        advice = ''

    # Update AI votes
    try:
        # Adapt update_ai_votes_for_element_in_feedback from:
        # clara_coherent_images_community_feedback.update_ai_votes_in_feedback
        update_ai_votes_for_element_in_feedback(project_dir, element_name)
    except Exception as e:
        messages.error(request, f"Error updating AI votes for element {element_name}: {e}\n{traceback.format_exc()}")

    # Load alternate images
    content_dir = project_pathname(project_dir, f"elements/{element_name}")
    alternate_images = asyncio.run(get_alternate_images_json(content_dir, project_dir))

    # Process form submissions
    if request.method == 'POST':
        action = request.POST.get('action', '')
        print(f'action = {action}')
        description_index = request.POST.get('description_index', '')
        userid = request.user.username

        if description_index is not None and description_index != '':
            description_index = int(description_index)

        try:
            #print(f'action = {action}')
            if action == 'images_with_advice_or_description':
                if not can_use_ai:
                    messages.error(request, f"Sorry, you need a registered OpenAI API key or money in your account to create images")
                    return redirect('simple_clara_review_v2_images_for_element', project_id=project_id, element_name=element_name, from_view=from_view, status='none')

                mode = request.POST.get('mode')
                advice_or_description_text = request.POST.get('advice_or_description_text', '').strip()
                
                if mode == 'advice':
                    requests = [ { 'request_type': 'new_element_description_and_images_from_advice',
                                   'element_name': element_name,
                                   'advice_text': advice_or_description_text } ]
                elif mode == 'expanded_description':
                    requests = [ { 'request_type': 'new_element_images_from_description',
                                   'element_name': element_name,
                                   'description_text': advice_or_description_text } ]
                else:
                    messages.error(request, f"Unknown mode '{mode}'")
                    return redirect('simple_clara_review_v2_images_for_element', project_id=project_id, element_name=element_name, from_view=from_view, status='none')

                callback, report_id = make_asynch_callback_and_report_id(request, 'execute_image_requests')

                async_task(execute_simple_clara_element_requests, project, clara_project_internal, requests, callback=callback)

                return redirect('execute_simple_clara_element_requests_monitor', project_id, report_id, element_name, from_view)

            elif action == 'upload_image':
                # The user is uploading a new image
                if not can_use_ai:
                    messages.error(request, f"Sorry, you need a registered OpenAI API key or money in your account to analyse images")
                    return redirect('simple_clara_review_v2_images_for_element', project_id=project_id, element_name=element_name, from_view=from_view, status='none')

                if 'uploaded_image_file_path' in request.FILES:
                    # Convert the in-memory file object to a local file path
                    uploaded_file_obj = request.FILES['uploaded_image_file_path']
                    real_image_file_path = uploaded_file_to_file(uploaded_file_obj)

                    requests = [ { 'request_type': 'add_uploaded_element_image',
                                   'element_name': element_name,
                                   'image_file_path': real_image_file_path } ]

                    callback, report_id = make_asynch_callback_and_report_id(request, 'execute_image_requests')

                    async_task(execute_simple_clara_element_requests, project, clara_project_internal, requests, callback=callback)

                    return redirect('execute_simple_clara_element_requests_monitor', project_id, report_id, element_name, from_view)
                else:
                    messages.error(request, "No file found for the upload_image action.")
                
            elif action == 'vote':
                vote_type = request.POST.get('vote_type')  # "upvote" or "downvote"
                if vote_type in ['upvote', 'downvote']:
                    # Adapt register_cm_element_vote from:
                    # clara_coherent_images_community_feedback.register_cm_image_vote
                    register_cm_element_vote(project_dir, element_name, description_index, vote_type, userid, override_ai_vote=True)

        except Exception as e:
            messages.error(request, f"Error processing your request: {str(e)}\n{traceback.format_exc()}")

        return redirect('simple_clara_review_v2_images_for_element', project_id=project_id, element_name=element_name, from_view=from_view, status='none')

    # GET

    # Adapt get_element_description_info_for_cm_reviewing from:
    # clara_coherent_images_community_feedback.get_page_description_info_for_cm_reviewing
    descriptions_info, preferred_description_id = get_element_description_info_for_cm_reviewing(alternate_images, element_name, project_dir)

    # In case the preferred description has changed from last time promote it
    if preferred_description_id is not None:
        # Adapt promote_v2_element_description from:
        # clara_main.promote_v2_page_image
        clara_project_internal.promote_v2_element_description(element_name, preferred_description_id)

    # If 'status' is something we got after returning from an async call, display a suitable message
    if status == 'finished':
        messages.success(request, "Image task successfully completed")
    elif status == 'error':
        messages.error(request, "Something went wrong when performing this image task. Look at the 'Recent task updates' view for further information.")

    rendering_parameters = {
        'project': project,
        'element_name': element_name,
        'descriptions_info': descriptions_info,
        'advice': advice,
        'from_view': from_view,
    }

    print(f'simple_clara_review_v2_images_for_element')
    pprint.pprint(rendering_parameters)

    return render(request, 'clara_app/simple_clara_review_v2_images_for_element.html', rendering_parameters)

@login_required
def simple_clara_review_v2_images_for_style(request, project_id, from_view, status):
    user = request.user
    can_use_ai = user_has_open_ai_key_or_credit(user)
    config_info = get_user_config(user)
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    project_dir = clara_project_internal.coherent_images_v2_project_dir
    
    story_data = read_project_json_file(project_dir, 'story.json')

    try:
        advice = clara_project_internal.get_style_advice_v2()
        print(f'advice = {advice}')
    except Exception as e:
        print(f"Error getting style advice: {e}\n{traceback.format_exc()}")
        advice = ''

    # Update AI votes
    try:
        update_ai_votes_for_style_in_feedback(project_dir)
    except Exception as e:
        messages.error(request, f"Error updating AI votes for style: {e}\n{traceback.format_exc()}")

    # Load alternate images
    content_dir = project_pathname(project_dir, f"style")
    alternate_images = asyncio.run(get_alternate_images_json(content_dir, project_dir))

    # Process form submissions
    if request.method == 'POST':
        action = request.POST.get('action', '')
        print(f'action = {action}')
        description_index = request.POST.get('description_index', '')
        userid = request.user.username

        if description_index is not None and description_index != '':
            description_index = int(description_index)

        try:
            #print(f'action = {action}')
            if action == 'images_with_advice_or_description':
                if not can_use_ai:
                    messages.error(request, f"Sorry, you need a registered OpenAI API key or money in your account to create images")
                    return redirect('simple_clara_review_v2_images_for_style', project_id=project_id, from_view=from_view, status='none')

                mode = request.POST.get('mode')
                advice_or_description_text = request.POST.get('advice_or_description_text', '').strip()
                
                if mode == 'advice':
                    requests = [ { 'request_type': 'new_style_description_and_images_from_advice',
                                   'advice_text': advice_or_description_text } ]
                elif mode == 'expanded_description':
                    requests = [ { 'request_type': 'new_style_images_from_description',
                                   'description_text': advice_or_description_text } ]
                else:
                    messages.error(request, f"Unknown mode '{mode}'")
                    return redirect('simple_clara_review_v2_images_for_style', project_id=project_id, from_view=from_view, status='none')

                callback, report_id = make_asynch_callback_and_report_id(request, 'execute_image_requests')

                async_task(execute_simple_clara_style_requests, project, clara_project_internal, requests, callback=callback)

                return redirect('execute_simple_clara_style_requests_monitor', project_id, report_id, from_view)
                
            elif action == 'vote':
                vote_type = request.POST.get('vote_type')  # "upvote" or "downvote"
                if vote_type in ['upvote', 'downvote']:
                    # Adapt register_cm_element_vote from:
                    # clara_coherent_images_community_feedback.register_cm_image_vote
                    register_cm_style_vote(project_dir, description_index, vote_type, userid, override_ai_vote=True)

        except Exception as e:
            messages.error(request, f"Error processing your request: {str(e)}\n{traceback.format_exc()}")

        return redirect('simple_clara_review_v2_images_for_style', project_id=project_id, from_view=from_view, status='none')

    # GET

    # Adapt get_element_description_info_for_cm_reviewing from:
    # clara_coherent_images_community_feedback.get_page_description_info_for_cm_reviewing
    descriptions_info, preferred_description_id = get_style_description_info_for_cm_reviewing(alternate_images, project_dir)

    # In case the preferred description has changed from last time promote it
    if preferred_description_id is not None:
        # Adapt promote_v2_element_description from:
        # clara_main.promote_v2_page_image
        clara_project_internal.promote_v2_style_description(preferred_description_id)

    # If 'status' is something we got after returning from an async call, display a suitable message
    if status == 'finished':
        messages.success(request, "Image task successfully completed")
    elif status == 'error':
        messages.error(request, "Something went wrong when performing this image task. Look at the 'Recent task updates' view for further information.")

    rendering_parameters = {
        'project': project,
        'descriptions_info': descriptions_info,
        'advice': advice,
        'from_view': from_view,
    }

    print(f'simple_clara_review_v2_images_for_style')
    pprint.pprint(rendering_parameters)

    return render(request, 'clara_app/simple_clara_review_v2_images_for_style.html', rendering_parameters)

def execute_simple_clara_image_requests(project, clara_project_internal, requests, callback=None):
    try:
        cost_dict = clara_project_internal.execute_simple_clara_image_requests_v2(requests, project.id, callback=callback)
        store_cost_dict(cost_dict, project, project.user)
        post_task_update(callback, f'--- Executed community requests')
        post_task_update(callback, f"finished")

    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")

def execute_simple_clara_element_requests(project, clara_project_internal, requests, callback=None):
    try:
        cost_dict = clara_project_internal.execute_simple_clara_element_requests_v2(requests, callback=callback)
        store_cost_dict(cost_dict, project, project.user)
        post_task_update(callback, f'--- Executed Simple C-LARA requests')
        post_task_update(callback, f"finished")

    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")

def execute_simple_clara_style_requests(project, clara_project_internal, requests, callback=None):
    try:
        cost_dict = clara_project_internal.execute_simple_clara_style_requests_v2(requests, callback=callback)
        store_cost_dict(cost_dict, project, project.user)
        post_task_update(callback, f'--- Executed Simple C-LARA requests')
        post_task_update(callback, f"finished")

    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")

@login_required
@user_has_a_project_role
def execute_simple_clara_image_requests_status(request, project_id, report_id):
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
@user_has_a_project_role
def execute_simple_clara_element_requests_status(request, project_id, report_id):
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
@user_has_a_project_role
def execute_simple_clara_style_requests_status(request, project_id, report_id):
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
@user_has_a_project_role
def execute_simple_clara_image_requests_monitor(request, project_id, report_id, page_number, from_view):
    project = get_object_or_404(CLARAProject, pk=project_id)
    
    return render(request, 'clara_app/execute_simple_clara_image_requests_monitor.html',
                  {'project_id': project_id, 'project': project, 'report_id': report_id, 'page_number': page_number, 'from_view': from_view})

@login_required
@user_has_a_project_role
def execute_simple_clara_element_requests_monitor(request, project_id, report_id, element_name, from_view):
    project = get_object_or_404(CLARAProject, pk=project_id)
    
    return render(request, 'clara_app/execute_simple_clara_element_requests_monitor.html',
                  {'project_id': project_id, 'project': project, 'report_id': report_id, 'element_name': element_name, 'from_view': from_view})

login_required
@user_has_a_project_role
def execute_simple_clara_style_requests_monitor(request, project_id, report_id, from_view):
    project = get_object_or_404(CLARAProject, pk=project_id)
    
    return render(request, 'clara_app/execute_simple_clara_style_requests_monitor.html',
                  {'project_id': project_id, 'project': project, 'report_id': report_id, 'from_view': from_view})
