from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from .models import CLARAProject

from django_q.tasks import async_task
from .utils import get_user_config, user_has_open_ai_key_or_credit, user_has_open_ai_key_or_credit_warn_if_admin_with_negative_balance
from .utils import store_cost_dict, make_asynch_callback_and_report_id
from .utils import user_has_a_project_role
from .utils import get_task_updates
from .utils import uploaded_file_to_file
from .utils import user_is_community_member, user_is_community_coordinator, community_role_required

from .clara_main import CLARAProjectInternal
from .clara_coherent_images_utils import project_pathname
from .clara_coherent_images_utils import read_project_json_file, project_pathname

from clara_app.picture_dictionary import PictureDictionary, PictureDictionaryEntry
from clara_app.clara_image_gloss_annotator import ImageGlossAnnotator
from clara_app.models import CLARAProject, CommunityMembership
from clara_app.clara_main import CLARAProjectInternal

from .clara_coherent_images_alternate import get_alternate_images_json, set_alternate_image_hidden_status

from .clara_coherent_images_community_feedback import (register_cm_image_vote, register_cm_image_variants_request,
                                                       register_cm_page_advice,  get_cm_page_advice,
                                                       get_page_overview_info_for_cm_reviewing,
                                                       get_page_description_info_for_cm_reviewing,
                                                       update_ai_votes_in_feedback, get_all_cm_requests_for_page, set_cm_request_status)
from .clara_utils import get_config
from .clara_utils import post_task_update
import logging
import traceback
import asyncio

config = get_config()
logger = logging.getLogger(__name__)

@login_required
@user_has_a_project_role
@user_is_community_member
def perform_picture_glossing(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)

    # Safety: must be attached to a community and user must be in it
    if not project.community:
        messages.error(request, "Attach this project to a community first.")
        return redirect('project_detail', project_id=project_id)

    if not CommunityMembership.objects.filter(community=project.community, user=request.user).exists():
        messages.error(request, "You are not a member of this community.")
        return redirect('project_detail', project_id=project_id)

    if not project.uses_picture_glossing:
        messages.info(request, "Picture glossing is not enabled for this project.")
        return redirect('project_detail', project_id=project_id)

    # Must be V2 coherent images (dictionary harvesting depends on it)
    if not project.uses_coherent_image_set_v2:
        messages.error(request, "Picture glossing currently requires coherent images V2 (not legacy V1).")
        return redirect('project_detail', project_id=project_id)

    style = project.picture_gloss_style or "any"

    # The dictionary project is always keyed by (community, l2, l1, style)
    pd = PictureDictionary(project.community, project.l2, project.l1, style=style)

    # We want to show link if it exists, but not auto-create on GET
    dict_project = pd.find_existing_project()  # you'll add this (tiny) helper, see below

    if request.method == "GET":
        clara_version = get_user_config(request.user)['clara_version']
        return render(
            request,
            "clara_app/perform_picture_glossing.html",
            {
                "project": project,
                "style": style,
                "dict_project": dict_project,
                "dict_project_exists": bool(dict_project),
                "clara_version": clara_version,
            }
        )

    # POST: perform action
    action = request.POST.get("action", "").strip()

    # We will create the dictionary project if needed for actions that require it
    dict_project, dict_internal, created = pd.get_or_create_project(request.user)

    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    callback, report_id = make_asynch_callback_and_report_id(request, f'picture_glossing_{action or "unknown"}')

    if action == "queue_missing":
        # Use exact internalised text (requires aligned versions)
        try:
            text_obj = clara_project_internal.get_internalised_text_exact()
        except Exception as e:
            messages.error(request, f"Error when trying to internalise text: {e}.")
            raise

        annotator = ImageGlossAnnotator(
            l2_language_id=project.l2,
            style_id=style,
        )

        updated_text_obj, missing_entries = annotator.annotate_text(text_obj, callback=callback)

        pd_entries = [PictureDictionaryEntry.from_dict(d) for d in missing_entries]

        result = pd.append_entries(
            dict_internal,
            pd_entries,
            user_display_name=request.user.username,
            source="human_revised",
            callback=callback,
        )

        clara_project_internal.save_internalised_and_annotated_text(updated_text_obj)

        messages.success(
            request,
            f"Queued missing picture gloss entries: added {result['added']} new dictionary pages, "
            f"skipped {result['skipped']} existing. Dictionary project: {dict_project.title}"
        )
        return redirect('perform_picture_glossing', project_id=project_id)

    elif action == "harvest_images":
        # Harvest from dictionary project into ImageGlossRepositoryORM
        result = pd.harvest_images_to_repository(
            dict_internal,
            callback=callback,
        )
        messages.success(
            request,
            f"Harvested to repository: added {result['added']}, "
            f"skipped (no image) {result['skipped_no_image']}, "
            f"skipped (no lemma) {result['skipped_no_lemma']}, "
            f"skipped (existing) {result['skipped_already_present']}, "
            f"errors {result['errors']}."
            )
        return redirect('perform_picture_glossing', project_id=project_id)

    else:
        messages.error(request, f"Unknown picture glossing action: {action}")
        return redirect('perform_picture_glossing', project_id=project_id)

@login_required
@user_is_community_member
def community_review_images(request, project_id):
    return community_review_images_cm_or_co(request, project_id, 'cm')

@login_required
@user_is_community_coordinator
def community_organiser_review_images(request, project_id):
    return community_review_images_cm_or_co(request, project_id, 'co')

@login_required
def community_review_images_external(request, project_id):
    user = request.user
    config_info = get_user_config(user)
    username = user.username
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    clara_version = get_user_config(request.user)['clara_version']
    project_dir = clara_project_internal.coherent_images_v2_project_dir

    story_data = read_project_json_file(project_dir, 'story.json')
    descriptions_info = []

    for page in story_data:
        page_number = page.get('page_number')
        page_text = page.get('text', '').strip()
        original_page_text = page.get('original_page_text', '').strip()

        # Update AI votes
        try:
            update_ai_votes_in_feedback(project_dir, page_number)
        except Exception as e:
            messages.error(request, f"Error updating AI votes: {e}")

        # Load alternate images
        content_dir = project_pathname(project_dir, f"pages/page{page_number}")
        alternate_images = asyncio.run(get_alternate_images_json(content_dir, project_dir))

        page_descriptions_info, preferred_image_id = get_page_description_info_for_cm_reviewing('cm', alternate_images, page_number, project_dir)

        page_item = { 'page_number': page_number,
                      'page_text': page_text,
                      'original_page_text': original_page_text,
                      'page_description_info': page_descriptions_info
                      }
        descriptions_info.append(page_item)

    rendering_parameters = {
        'project': project,
        'descriptions_info': descriptions_info,
    }

    #pprint.pprint(descriptions_info[:2])

    return render(request, 'clara_app/community_review_images_external.html', rendering_parameters)

def community_review_images_cm_or_co(request, project_id, cm_or_co):
    user = request.user
    config_info = get_user_config(user)
    username = user.username
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    clara_version = get_user_config(request.user)['clara_version']
    project_dir = clara_project_internal.coherent_images_v2_project_dir

    pages_info = get_page_overview_info_for_cm_reviewing(project_dir)

    #pprint.pprint(pages_info)

    return render(request, 'clara_app/community_review_images.html', {
        'cm_or_co': cm_or_co,
        'project': project,
        'pages_info': pages_info,
        'clara_version': clara_version,
    })


@login_required
@community_role_required
def community_review_images_for_page(request, project_id, page_number, cm_or_co, status):
    user = request.user
    can_use_ai = user_has_open_ai_key_or_credit_warn_if_admin_with_negative_balance(request)
    config_info = get_user_config(user)
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    project_dir = clara_project_internal.coherent_images_v2_project_dir
    approved_requests_for_page = get_all_cm_requests_for_page(project_dir, page_number, status='approved')
    n_approved_requests_for_page = len(approved_requests_for_page)
    
    story_data = read_project_json_file(project_dir, 'story.json')
    page = story_data[page_number - 1]
    page_text = page.get('text', '').strip()
    original_page_text = page.get('original_page_text', '').strip()

    # Update AI votes
    try:
        update_ai_votes_in_feedback(project_dir, page_number)
    except Exception as e:
        messages.error(request, f"Error updating AI votes: {e}")

    # Load alternate images
    content_dir = project_pathname(project_dir, f"pages/page{page_number}")
    alternate_images = asyncio.run(get_alternate_images_json(content_dir, project_dir))

    # Process form submissions
    if request.method == 'POST':
        action = request.POST.get('action', '')
        description_index = request.POST.get('description_index', '')
        image_index = request.POST.get('image_index', '')
        index = request.POST.get('index', '')
        userid = request.user.username

        if description_index is not None and description_index != '':
            description_index = int(description_index)
        if image_index is not None and image_index != '':
            image_index = int(image_index)
        else:
            image_index = None
        if index is not None and index != '':
            index = int(index)
        else:
            index = None

        try:
            #print(f'action = {action}')
            if action == 'run_approved_requests':
                if not can_use_ai:
                    messages.error(request, f"Sorry, you need a registered OpenAI API key or money in your account to create images")
                    return redirect('community_review_images_for_page', project_id=project_id, page_number=page_number, cm_or_co=cm_or_co, status='none')

                requests = get_all_cm_requests_for_page(project_dir, page_number, status='approved')

                callback, report_id = make_asynch_callback_and_report_id(request, 'execute_community_requests')

                async_task(execute_community_requests, project, clara_project_internal, requests, callback=callback)

                return redirect('execute_community_requests_for_page_monitor', project_id, report_id, page_number)
                
            elif action == 'vote':
                vote_type = request.POST.get('vote_type')  # "upvote" or "downvote"
                if vote_type in ['upvote', 'downvote'] and image_index is not None:
                    register_cm_image_vote(project_dir, page_number, description_index, image_index, vote_type, userid)

            elif action == 'hide_or_unhide':
                hidden_status = ( request.POST.get('hidden_status')  == 'true' )
                set_alternate_image_hidden_status(content_dir, description_index, image_index, hidden_status)

            elif action == 'variants_requests':
                register_cm_image_variants_request(project_dir, page_number, description_index, userid)

            elif action == 'upload_image':
                # The user is uploading a new image
                if 'uploaded_image_file_path' in request.FILES:
                    # Convert the in-memory file object to a local file path
                    uploaded_file_obj = request.FILES['uploaded_image_file_path']
                    real_image_file_path = uploaded_file_to_file(uploaded_file_obj)

                    clara_project_internal.add_uploaded_page_image_v2(real_image_file_path, page_number)
                    messages.success(request, "Your image was uploaded.")
                else:
                    messages.error(request, "No file found for the upload_image action.")

            elif action == 'set_request_status':
                request_type = request.POST.get('request_type', '')
                status = request.POST.get('status', '')
                if request_type == 'variants_requests' and isinstance(description_index, (int)):
                    request_item = { 'request_type': 'variants_requests',
                                     'page': page_number,
                                     'description_index': description_index }
                elif request_type == 'advice' and isinstance(index, (int)):
                    request_item = { 'request_type': 'advice',
                                     'page': page_number,
                                     'index': index }
                else:
                    messages.error(request, f"Error when trying to set request status for request of type '{request_type}'")
                    messages.error(request, f"page = {page}, request_type = '{request_type}', description_index = '{description_index}', index='{index}'")
                    return redirect('community_review_images_for_page', project_id=project_id, page_number=page_number, cm_or_co=cm_or_co, status='none')
                set_cm_request_status(project_dir, request_item, status)

            elif action == 'add_advice':
                advice_text = request.POST.get('advice_text', '')
                if advice_text.strip():
                    register_cm_page_advice(project_dir, page_number, advice_text.strip(), userid)

        except Exception as e:
            messages.error(request, f"Error processing your request: {str(e)}\n{traceback.format_exc()}")

        return redirect('community_review_images_for_page', project_id=project_id, page_number=page_number, cm_or_co=cm_or_co, status='none')

    # GET
    advice = get_cm_page_advice(project_dir, page_number)

    descriptions_info, preferred_image_id = get_page_description_info_for_cm_reviewing(cm_or_co, alternate_images, page_number, project_dir)

    # In case the preferred image has changed from last time promote it
    if preferred_image_id is not None:
        clara_project_internal.promote_v2_page_image(page_number, preferred_image_id)

    # If 'status' is something we got after returning from an async call, display a suitable message
    if status == 'finished':
        messages.success(request, "Image task successfully completed")
    elif status == 'error':
        messages.error(request, "Something went wrong when performing this image task. Look at the 'Recent task updates' view for further information.")

    rendering_parameters = {
        'cm_or_co': cm_or_co,
        'project': project,
        'page_number': page_number,
        'page_text': page_text,
        'original_page_text': original_page_text,
        'page_advice': advice,
        'descriptions_info': descriptions_info,
        'n_approved_requests_for_page': n_approved_requests_for_page,
    }

    #pprint.pprint(rendering_parameters)

    return render(request, 'clara_app/community_review_images_for_page.html', rendering_parameters)


# Async function
def execute_community_requests(project, clara_project_internal, requests, callback=None):
    try:
        cost_dict = clara_project_internal.execute_community_requests_list_v2(requests, callback=callback)
        store_cost_dict(cost_dict, project, project.user)
        post_task_update(callback, f'--- Executed community requests')
        post_task_update(callback, f"finished")

    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")



@login_required
@user_has_a_project_role
def execute_community_requests_for_page_status(request, project_id, report_id):
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
def execute_community_requests_for_page_monitor(request, project_id, report_id, page_number):
    project = get_object_or_404(CLARAProject, pk=project_id)
    
    return render(request, 'clara_app/execute_community_requests_for_page_monitor.html',
                  {'project_id': project_id, 'project': project, 'report_id': report_id, 'page_number': page_number})
