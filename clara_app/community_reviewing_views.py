from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, FileResponse, JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.conf import settings
from django import forms
from django.db import transaction
from django.db.models import Count, Avg, Q, Max, F, Case, Value, When, IntegerField, Sum
from django.db.models.functions import Lower
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, FileResponse, JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.conf import settings
from django import forms
from django.db import transaction
from django.db.models import Count, Avg, Q, Max, F, Case, Value, When, IntegerField, Sum
from django.db.models.functions import Lower
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.http import unquote
from django.urls import reverse

from .models import UserProfile, FriendRequest, UserConfiguration, LanguageMaster, Content, ContentAccess, TaskUpdate, Update, ReadingHistory
from .models import SatisfactionQuestionnaire, FundingRequest, Acknowledgements, Activity, ActivityRegistration, ActivityComment, ActivityVote, CurrentActivityVote
from .models import CLARAProject, HumanAudioInfo, PhoneticHumanAudioInfo, ProjectPermissions, CLARAProjectAction, Comment, Rating, FormatPreferences
from .models import Community, CommunityMembership, ImageQuestionnaireResponse
from django.contrib.auth.models import User

from django_q.tasks import async_task
from django_q.models import Task

from .forms import RegistrationForm, UserForm, UserSelectForm, UserProfileForm, FriendRequestForm, AdminPasswordResetForm, ProjectSelectionFormSet, UserConfigForm
from .forms import AssignLanguageMasterForm, AddProjectMemberForm, FundingRequestForm, FundingRequestSearchForm, ApproveFundingRequestFormSet, UserPermissionsForm
from .forms import ContentSearchForm, ContentRegistrationForm, AcknowledgementsForm, UnifiedSearchForm
from .forms import ProjectCommunityForm, CreateCommunityForm, UserAndCommunityForm, ProjectCommunityForm, AssignMemberForm
from .forms import ActivityForm, ActivitySearchForm, ActivityRegistrationForm, ActivityCommentForm, ActivityVoteForm, ActivityStatusForm, ActivityResolutionForm
from .forms import AIActivitiesUpdateForm, DeleteContentForm
from .forms import ProjectCreationForm, UpdateProjectTitleForm, UpdateCoherentImageSetForm
from .forms import SimpleClaraForm, ProjectImportForm, ProjectSearchForm, AddCreditForm, ConfirmTransferForm
from .forms import DeleteTTSDataForm, AudioMetadataForm, InitialiseORMRepositoriesForm
from .forms import HumanAudioInfoForm, LabelledSegmentedTextForm, AudioItemFormSet, PhoneticHumanAudioInfoForm
from .forms import CreatePlainTextForm, CreateTitleTextForm, CreateSegmentedTitleTextForm, CreateSummaryTextForm, CreateCEFRTextForm, CreateSegmentedTextForm
from .forms import CreateTranslatedTextForm, CreatePhoneticTextForm, CreateGlossedTextForm, CreateLemmaTaggedTextForm, CreateMWETaggedTextForm
from .forms import CreatePinyinTaggedTextForm, CreateLemmaAndGlossTaggedTextForm
from .forms import MakeExportZipForm, RenderTextForm, RegisterAsContentForm, RatingForm, CommentForm, DiffSelectionForm
from .forms import TemplateForm, PromptSelectionForm, StringForm, StringPairForm, CustomTemplateFormSet, CustomStringFormSet, CustomStringPairFormSet
from .forms import MorphologyExampleForm, CustomMorphologyExampleFormSet, MWEExampleForm, CustomMWEExampleFormSet, ExampleWithMWEForm, ExampleWithMWEFormSet
from .forms import ImageForm, ImageFormSet, ImageDescriptionForm, ImageDescriptionFormSet, StyleImageForm, ImageSequenceForm 
from .forms import PhoneticLexiconForm, PlainPhoneticLexiconEntryFormSet, AlignedPhoneticLexiconEntryFormSet
from .forms import L2LanguageSelectionForm, AddProjectToReadingHistoryForm, RequirePhoneticTextForm, SatisfactionQuestionnaireForm
from .forms import GraphemePhonemeCorrespondenceFormSet, AccentCharacterFormSet, FormatPreferencesForm
from .forms import ImageFormV2, ImageFormSetV2, CoherentImagesV2ParamsForm
from .utils import get_user_config, user_has_open_ai_key_or_credit, create_internal_project_id, store_api_calls, store_cost_dict, make_asynch_callback_and_report_id
from .utils import get_user_api_cost, get_project_api_cost, get_project_operation_costs, get_project_api_duration, get_project_operation_durations
from .utils import user_is_project_owner, user_has_a_project_role, user_has_a_named_project_role, language_master_required
from .utils import post_task_update_in_db, get_task_updates, has_saved_internalised_and_annotated_text
from .utils import uploaded_file_to_file, create_update, current_friends_of_user, get_phase_up_to_date_dict
from .utils import send_mail_or_print_trace, get_zoom_meeting_start_date, get_previous_week_start_date
from .utils import user_is_community_member, user_is_community_coordinator, community_role_required, user_is_coordinator_of_some_community
from .utils import is_ai_enabled_language

from .clara_main import CLARAProjectInternal
#from .clara_audio_repository import AudioRepository
from .clara_audio_repository_orm import AudioRepositoryORM
from .clara_image_repository_orm import ImageRepositoryORM
from .clara_audio_annotator import AudioAnnotator
#from .clara_phonetic_lexicon_repository import PhoneticLexiconRepository
from .clara_phonetic_lexicon_repository_orm import PhoneticLexiconRepositoryORM
from .clara_prompt_templates import PromptTemplateRepository
from .clara_dependencies import CLARADependencies
from .clara_reading_histories import ReadingHistoryInternal
from .clara_phonetic_orthography_repository import PhoneticOrthographyRepository, phonetic_orthography_resources_available
from .clara_phonetic_utils import phonetic_resources_are_available

from .clara_community import assign_project_to_community

from .clara_coherent_images_utils import get_style_params_from_project_params, get_element_names_params_from_project_params, project_params_for_simple_clara
from .clara_coherent_images_utils import get_element_names_params_from_project_params, get_element_descriptions_params_from_project_params
from .clara_coherent_images_utils import get_page_params_from_project_params, default_params, style_image_name, element_image_name, page_image_name, get_element_image
from .clara_coherent_images_utils import remove_element_directory, remove_page_directory, remove_element_name_from_list_of_elements, project_pathname
from .clara_coherent_images_utils import read_project_json_file, project_pathname
from .clara_coherent_images_utils import image_dir_shows_content_policy_violation
from .clara_coherent_images_utils import description_dir_shows_only_content_policy_violations
from .clara_coherent_images_utils import content_dir_shows_only_content_policy_violations
from .clara_coherent_images_utils import style_directory, element_directory, page_directory
from .clara_coherent_images_utils import relative_style_directory, relative_element_directory, relative_page_directory

from .clara_coherent_images_alternate import get_alternate_images_json, set_alternate_image_hidden_status

from .clara_coherent_images_export import create_images_zipfile

from .clara_coherent_images_community_feedback import (load_community_feedback, save_community_feedback,
                                                       register_cm_image_vote, register_cm_element_vote, register_cm_style_vote,
                                                       register_cm_image_variants_request,
                                                       register_cm_page_advice,  get_cm_page_advice,
                                                       get_page_overview_info_for_cm_reviewing,
                                                       get_page_description_info_for_cm_reviewing,
                                                       get_element_description_info_for_cm_reviewing,
                                                       get_style_description_info_for_cm_reviewing,
                                                       update_ai_votes_in_feedback, update_ai_votes_for_element_in_feedback, update_ai_votes_for_style_in_feedback,
                                                       determine_preferred_image,
                                                       get_all_cm_requests_for_page, set_cm_request_status,
                                                       get_all_cm_requests)

from .clara_dall_e_3_image import ( create_and_add_dall_e_3_image_for_whole_text,
                                    create_and_add_dall_e_3_image_for_style )

from .save_page_texts_multiple_utils import save_page_texts_multiple

from .clara_images_utils import numbered_page_list_for_coherent_images

from .clara_internalise import internalize_text
from .clara_grapheme_phoneme_resources import grapheme_phoneme_resources_available
from .clara_conventional_tagging import fully_supported_treetagger_language
from .clara_chinese import is_chinese_language
from .clara_mwe import annotate_mwes_in_text
from .clara_annotated_images import make_uninstantiated_annotated_image_structure
from .clara_tts_api import tts_engine_type_supports_language
from .clara_chatgpt4 import call_chat_gpt4, interpret_chat_gpt4_response_as_json, call_chat_gpt4_image, call_chat_gpt4_interpret_image
from .clara_classes import TemplateError, InternalCLARAError, InternalisationError, MWEError, ImageGenerationError
from .clara_utils import _s3_storage, _s3_bucket, s3_file_name, get_config, absolute_file_name, file_exists, local_file_exists, read_txt_file, remove_file, basename
from .clara_utils import copy_local_file_to_s3, copy_local_file_to_s3_if_necessary, copy_s3_file_to_local_if_necessary, generate_s3_presigned_url
from .clara_utils import robust_read_local_txt_file, read_json_or_txt_file, check_if_file_can_be_read
from .clara_utils import output_dir_for_project_id, image_dir_for_project_id, post_task_update, is_rtl_language, is_chinese_language
from .clara_utils import make_mp3_version_of_audio_file_if_necessary

from .constants import SUPPORTED_LANGUAGES, SUPPORTED_LANGUAGES_AND_DEFAULT, SUPPORTED_LANGUAGES_AND_OTHER, SIMPLE_CLARA_TYPES
from .constants import ACTIVITY_CATEGORY_CHOICES, ACTIVITY_STATUS_CHOICES, ACTIVITY_RESOLUTION_CHOICES, DEFAULT_RECENT_TIME_PERIOD
from .constants import TTS_CHOICES

from pathlib import Path
from decimal import Decimal
from urllib.parse import unquote
from datetime import timedelta
from ipware import get_client_ip
from collections import defaultdict

import os
import re
import json
import zipfile
import shutil
import mimetypes
import logging
import pprint
import uuid
import traceback
import tempfile
import pandas as pd
import asyncio

config = get_config()
logger = logging.getLogger(__name__)

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
    can_use_ai = user_has_open_ai_key_or_credit(user)
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
