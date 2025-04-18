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

def redirect_login(request):
    return redirect('login')

#-------------------------------------------------------
# Moved to account_views.py

##def register(request):

##@login_required
##def profile(request):

#-------------------------------------------------------
# Moved to home_views.py

##def home(request):
##
##def home_page(request):
##
##@login_required
##def clara_home_page(request):
##
##def annotate_and_order_activities_for_home_page(activities):

#-------------------------------------------------------
# Moved to profile_views.py

##@login_required
##def edit_profile(request):
##
##def external_profile(request, user_id):
##
##def send_friend_request_notification_email(request, other_user):

#-------------------------------------------------------
# Moved to users_and_friends_views.py

##def list_users(request):
##
##@login_required
##def friends(request):

#-------------------------------------------------------
# Moved to update_feed_views.py

##@login_required
##def update_feed(request):
##
##def valid_update_for_update_feed(update):

#-------------------------------------------------------
# Moved to user_config_views.py

##@login_required
##def user_config(request):

#-------------------------------------------------------
# Moved to task_update_views.py

##@login_required
##def view_task_updates(request):
##
##@login_required
##@user_passes_test(lambda u: u.userprofile.is_admin)

#-------------------------------------------------------
# Moved to admin_permission_views.py

##@login_required
##@user_passes_test(lambda u: u.userprofile.is_admin)
##def admin_password_reset(request):
##
##@login_required
##@user_passes_test(lambda u: u.userprofile.is_admin)
##def admin_project_ownership(request):
##
##@login_required
##@user_passes_test(lambda u: u.userprofile.is_admin)

#-------------------------------------------------------
# Moved to credit_views.py

##@login_required
##def credit_balance(request):
##
### Add credit to account
##@login_required
##@user_passes_test(lambda u: u.userprofile.is_admin)
##
### Transfer credit to another account
##@login_required
##def transfer_credit(request):
##
##@login_required
##def confirm_transfer(request):

#-------------------------------------------------------
# Moved to delete_tts_views.py

##def delete_tts_data_for_language(language, callback=None):
##
##@login_required
##@user_passes_test(lambda u: u.userprofile.is_admin)
##def delete_tts_data(request):
##
##@login_required
##@user_passes_test(lambda u: u.userprofile.is_admin)
##def delete_tts_data_status(request, report_id):
##
##@login_required
##@user_passes_test(lambda u: u.userprofile.is_admin)
##def delete_tts_data_monitor(request, language, report_id):
##
##@login_required
##@user_passes_test(lambda u: u.userprofile.is_admin)
##def delete_tts_data_complete(request, language, status):    

#-------------------------------------------------------
# Moved to content_views.py

##@login_required
##def register_content(request):
##
##def content_success(request):
##
##@login_required
##def content_list(request):
##
##def public_content_list(request):
##
##@login_required
##def content_detail(request, content_id):
##
##def send_rating_or_comment_notification_email(request, recipients, content, action):
##
##def public_content_detail(request, content_id):

#-------------------------------------------------------
# Moved to language_masters_views.py

##@login_required
##@user_passes_test(lambda u: u.userprofile.is_admin)
##
##@login_required
##@user_passes_test(lambda u: u.userprofile.is_admin)

#-------------------------------------------------------
# Moved to funding_requests_views.py

##@login_required
##def funding_request(request):
##
##@login_required
##@user_passes_test(lambda u: u.userprofile.is_funding_reviewer)
##def review_funding_requests(request):
##
##@login_required
##@user_passes_test(lambda u: u.userprofile.is_funding_reviewer)
##def confirm_funding_approvals(request):

#-------------------------------------------------------
# Moved to activity_tracker_views.py

##@login_required
##def create_activity(request):
##
##@login_required
##def activity_detail(request, activity_id):
##
##def notify_activity_participants(request, activity, new_comment):
##
##def send_activity_comment_notification_email(request, recipients, activity, comment):
##
##@login_required
##def list_activities(request):
##
##def annotate_and_order_activities_for_display(activities):
##
##@login_required
##@user_passes_test(lambda u: u.userprofile.is_admin)
##def list_activities_text(request):
##
##@login_required
##@user_passes_test(lambda u: u.userprofile.is_admin)
##def ai_activities_reply(request):

#-------------------------------------------------------
# Moved to annotation_prompts_views.py

##@login_required
##@language_master_required
##def edit_prompt(request):

#-------------------------------------------------------



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

def edit_acknowledgements(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    try:
        acknowledgements = project.acknowledgements
    except Acknowledgements.DoesNotExist:
        acknowledgements = None

    if request.method == 'POST':
        form = AcknowledgementsForm(request.POST, instance=acknowledgements)
        if form.is_valid():
            ack = form.save(commit=False)
            ack.project = project
            ack.save()
            return redirect('project_detail', project_id=project.id)
    else:
        form = AcknowledgementsForm(instance=acknowledgements)

    return render(request, 'clara_app/edit_acknowledgements.html', {'form': form, 'project': project})

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

#_simple_clara_trace = False
_simple_clara_trace = True

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
        if _simple_clara_trace:
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
                    description_language = form.cleaned_data['description_language']
                    style_advice = form.cleaned_data['style_advice']
                    simple_clara_action = { 'action': 'create_v2_style', 'description_language': description_language,
                                            'style_advice': style_advice, 'up_to_date_dict': up_to_date_dict }
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
            #simple_clara_action should be of the form { 'action': 'create_v2_style', 'description_language': description_language,
            #                                            'style_advice':style_advice, 'up_to_date_dict': up_to_date_dict }
            result = simple_clara_create_v2_style_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'create_v2_elements':
            #simple_clara_action should be of the form { 'action': 'create_v2_elements', 'up_to_date_dict': up_to_date_dict }
            result = simple_clara_create_v2_elements_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'delete_v2_element':
            #simple_clara_action should be of the form { 'action': 'delete_v2_element', 'deleted_element_text': deleted_element_text }
            result = simple_clara_delete_v2_element_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'add_v2_element':
            #simple_clara_action should be of the form { 'action': 'add_v2_element', 'new_element_text': new_element_text }
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
    params['text_language'] = description_language
    clara_project_internal.save_coherent_images_v2_params(params)
    
    numbered_page_list = numbered_page_list_for_coherent_images(project, clara_project_internal)
    clara_project_internal.set_story_data_from_numbered_page_list_v2(numbered_page_list)

    # Create the style
    if not up_to_date_dict['v2_style_image']:
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
        clara_project_internal, global_metadata = CLARAProjectInternal.create_CLARAProjectInternal_from_zipfile(zip_file, internal_id, callback=callback)
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
        #  "audio_type_for_words": "human",
        #  "audio_type_for_segments": "tts",
        #  "uses_coherent_image_set": False,
        #  "uses_coherent_image_set_v2": True,
        #  "use_translation_for_images": False
        #}
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

# Manage the users associated with a project. Users can have the roles 'Owner', 'Annotator' or 'Viewer'
@login_required
@user_is_project_owner
def manage_project_members(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    permissions = ProjectPermissions.objects.filter(project=project)

    if request.method == 'POST':
        form = AddProjectMemberForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            role = form.cleaned_data['role']
            user = get_object_or_404(User, username=user)
            if ProjectPermissions.objects.filter(user=user, project=project).exists():
                messages.error(request, 'This user already has permissions for this project.')
            else:
                ProjectPermissions.objects.create(user=user, project=project, role=role)
                messages.success(request, 'User added successfully!')
                return redirect('manage_project_members', project_id=project_id)
        else:
            messages.error(request, 'Invalid form data. Please try again.')
    else:
        form = AddProjectMemberForm()

    clara_version = get_user_config(request.user)['clara_version']

    context = {
        'project': project,
        'permissions': permissions,
        'form': form,
        'clara_version': clara_version,
    }
    
    return render(request, 'clara_app/manage_project_members.html', context)

# Remove a member from a project
@login_required
def remove_project_member(request, permission_id):
    permission = get_object_or_404(ProjectPermissions, pk=permission_id)
    
    if request.method == 'POST':
        permission.delete()
        messages.success(request, 'User removed successfully!')
    else:
        messages.error(request, 'Invalid request.')
    
    return redirect('manage_project_members', project_id=permission.project.id)
      
# List projects on which the user has a role    
@login_required
def project_list(request, clara_version):
    user = request.user
    search_form = ProjectSearchForm(request.GET or None)
    query = Q((Q(user=user) | Q(projectpermissions__user=user)))

    if search_form.is_valid():
        title = search_form.cleaned_data.get('title')
        l2 = search_form.cleaned_data.get('l2')
        l1 = search_form.cleaned_data.get('l1')

        if title:
            query &= Q(title__icontains=title)
        if l2:
            query &= Q(l2__icontains=l2)
        if l1:
            query &= Q(l1__icontains=l1)

    projects = CLARAProject.objects.filter(query).order_by(Lower('title'))
    
    project_data = {}
    for project in projects:
        role = 'OWNER' if project.user == user else ProjectPermissions.objects.get(user=user, project=project).role
        project_data[project] = {
            'role': role,
            'cost': get_project_api_cost(user=user, project=project),
            'operation_costs': get_project_operation_costs(user=user, project=project),
            'duration': get_project_api_duration(user=user, project=project),  
            'operation_durations': get_project_operation_durations(user=user, project=project),  
        }

    paginator = Paginator(list(project_data.items()), 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Display the project using this version of C-LARA
    clara_version_to_access_with = clara_version
    # Display the menus using this version of C-LARA
    clara_version_for_menus = get_user_config(request.user)['clara_version']

    return render(request, 'clara_app/project_list.html',
                  {'search_form': search_form,
                   'page_obj': page_obj,
                   'clara_version_to_access_with': clara_version_to_access_with,
                   'clara_version': clara_version_for_menus})

# Delete a project
@login_required
@user_is_project_owner
def delete_project(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    if request.method == 'POST':
        project.delete()
        clara_project_internal.delete()
        return redirect('project_list', 'normal')
    else:
        
        clara_version = get_user_config(request.user)['clara_version']
        
        return render(request, 'clara_app/confirm_delete.html', {'project': project, 'clara_version': clara_version})

# Display information and functionalities associated with a project     
@login_required
@user_has_a_project_role
def project_detail(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    ai_enabled_l2 = is_ai_enabled_language(project.l2)
    ai_enabled_l1 = is_ai_enabled_language(project.l1)
    text_versions = clara_project_internal.text_versions
    up_to_date_dict = get_phase_up_to_date_dict(project, clara_project_internal, request.user)

    can_create_segmented_text = clara_project_internal.text_versions["plain"]
    can_create_segmented_title = clara_project_internal.text_versions["title"]
    can_create_phonetic_text = clara_project_internal.text_versions["segmented"] and phonetic_resources_are_available(project.l2)
    can_create_glossed_and_lemma_text = clara_project_internal.text_versions["segmented"]
    can_create_glossed_text_from_lemma = clara_project_internal.text_versions["lemma"]
    can_create_pinyin_text = clara_project_internal.text_versions["segmented"] and is_chinese_language(project.l2) 
    can_render_normal = clara_project_internal.text_versions["gloss"] and clara_project_internal.text_versions["lemma"]
    can_render_phonetic = clara_project_internal.text_versions["phonetic"] 
    rendered_html_exists = clara_project_internal.rendered_html_exists(project_id)
    rendered_phonetic_html_exists = clara_project_internal.rendered_phonetic_html_exists(project_id)
    images = clara_project_internal.get_all_project_images()
    images_exist = len(images) != 0
    api_cost = get_project_api_cost(request.user, project)
    if request.method == 'POST':
        title_form = UpdateProjectTitleForm(request.POST, prefix="title")
        image_set_form = UpdateCoherentImageSetForm(request.POST, prefix="image_set")
        if title_form.is_valid() and title_form.cleaned_data['new_title']:
            project.title = title_form.cleaned_data['new_title']
            project.save()
        if image_set_form.is_valid():
            project.uses_coherent_image_set = image_set_form.cleaned_data['uses_coherent_image_set']
            project.uses_coherent_image_set_v2 = image_set_form.cleaned_data['uses_coherent_image_set_v2']
            project.use_translation_for_images = image_set_form.cleaned_data['use_translation_for_images']
            project.has_image_questionnaire = image_set_form.cleaned_data['has_image_questionnaire']
            project.save()
        messages.success(request, f"Project information updated")
    else:
        title_form = UpdateProjectTitleForm(prefix="title")
        image_set_form = UpdateCoherentImageSetForm(prefix="image_set",
                                                    initial={'uses_coherent_image_set': project.uses_coherent_image_set,
                                                             'uses_coherent_image_set_v2': project.uses_coherent_image_set_v2,
                                                             'use_translation_for_images': project.use_translation_for_images,
                                                             'has_image_questionnaire': project.has_image_questionnaire
                                                             })

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/project_detail.html', 
                  { 'project': project,
                    'ai_enabled_l2': ai_enabled_l2,
                    'ai_enabled_l1': ai_enabled_l1,
                    'title_form': title_form,
                    'image_set_form': image_set_form,
                    'api_cost': api_cost,
                    'text_versions': text_versions,
                    'images_exist': images_exist,
                    'up_to_date_dict': up_to_date_dict,
                    'can_create_segmented_text': can_create_segmented_text,
                    'can_create_segmented_title': can_create_segmented_title,
                    'can_create_phonetic_text': can_create_phonetic_text,
                    'can_create_glossed_and_lemma_text': can_create_glossed_and_lemma_text,
                    'can_create_glossed_text_from_lemma': can_create_glossed_text_from_lemma,
                    'can_create_pinyin_text': can_create_pinyin_text,
                    'can_render_normal': can_render_normal,
                    'can_render_phonetic': can_render_phonetic,
                    'rendered_html_exists': rendered_html_exists,
                    'rendered_phonetic_html_exists': rendered_phonetic_html_exists,
                    'clara_version': clara_version,
                    }
                    )

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def create_community(request):
    """
    Admin-only view to create a new Community.
    """
    if request.method == 'POST':
        form = CreateCommunityForm(request.POST)
        if form.is_valid():
            community = form.save()
            # Optionally flash a success message, etc.
            return redirect('clara_home_page')  # Or wherever you want
    else:
        form = CreateCommunityForm()

    return render(request, 'clara_app/admin_create_community.html', {
        'form': form
    })

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def delete_community_menu(request):
    """
    Admin-only view that lists all communities and allows for a two-step
    (dropdown -> confirmation) delete process.
    """
    if request.method == 'POST':
        # Distinguish which form step we're on:
        action = request.POST.get('action')

        if action == 'choose_community':
            # The admin selected a community from the dropdown.
            community_id = request.POST.get('community_id')
            if not community_id:
                messages.error(request, "No community selected.")
                return redirect('delete_community_menu')
            
            try:
                community = Community.objects.get(pk=community_id)
            except Community.DoesNotExist:
                messages.error(request, "Selected community does not exist.")
                return redirect('delete_community_menu')

            # Render a confirmation page, passing the selected community
            return render(request, 'clara_app/admin_delete_community_confirm.html', {
                'community': community
            })

        elif action == 'confirm_delete':
            # The admin confirmed deletion
            community_id = request.POST.get('community_id')
            if not community_id:
                messages.error(request, "No community to delete.")
                return redirect('delete_community_menu')

            try:
                community = Community.objects.get(pk=community_id)
                community.delete()
                messages.success(request, f"Community '{community.name}' deleted successfully.")
            except Community.DoesNotExist:
                messages.error(request, "Community does not exist.")
            
            return redirect('delete_community_menu')

        else:
            # Unknown action, just redirect
            return redirect('delete_community_menu')

    else:
        # GET request: show the dropdown of all communities
        communities = Community.objects.order_by('name')
        return render(request, 'clara_app/admin_delete_community_menu.html', {
            'communities': communities
        })


@login_required
def community_home(request, community_id):
    user = request.user
    community = get_object_or_404(Community, pk=community_id)

    membership = CommunityMembership.objects.filter(
        community=community, user=user
    ).first()

    if not membership:
        # The user is not a member of this community
        raise PermissionDenied

    role = membership.role  # "COORDINATOR" or "MEMBER"
    print(f'role = {role}')

    # Build data to pass to the template
    context = {
        'community': community,
        'user_role': role,
    }

    # Add relevant data, e.g. list of all community projects
    projects = CLARAProject.objects.filter(community=community)
    context['projects'] = projects

    # Possibly link to membership views if user_role == 'CO'
    if role == 'CO':
        # e.g. context['members'] = ...
        pass

    return render(request, 'clara_app/community_home.html', context)


@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)  
def assign_coordinator_to_community(request):
    """
    Admin-only view: Turn a user into COORDINATOR in the selected community.
    """
    if request.method == 'POST':
        form = UserAndCommunityForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            community = form.cleaned_data['community']

            # We create/get the membership and set role = COORDINATOR
            membership, created = CommunityMembership.objects.get_or_create(
                community=community, user=user
            )
            membership.role = 'COORDINATOR'
            membership.save()

            # Redirect or show success message
            return redirect('clara_home_page')  # adapt as needed
    else:
        form = UserAndCommunityForm()

    return render(request, 'clara_app/admin_assign_coordinator.html', {
        'form': form,
    })

@login_required
@user_is_coordinator_of_some_community
def assign_member_to_community(request):
    """
    Only a user who is coordinator in at least one community can access this.
    Lets them pick a (user, community) pair to assign the user as an ordinary member.
    """
    if request.method == 'POST':
        # pass the request.user in as 'coordinator_user' so the form can limit communities
        form = AssignMemberForm(request.POST, coordinator_user=request.user)
        if form.is_valid():
            the_user = form.cleaned_data['user']
            the_community = form.cleaned_data['community']
            
            # check if the requesting user is coordinator of that specific community
            # we do the same membership check as in the form’s queryset logic,
            # but let's be extra safe to avoid tampering
            if not CommunityMembership.objects.filter(
                user=request.user,
                community=the_community,
                role='COORDINATOR'
            ).exists():
                raise PermissionDenied("You are not coordinator of that community.")
            
            # create or update membership
            membership, created = CommunityMembership.objects.get_or_create(
                user=the_user,
                community=the_community
            )
            membership.role = 'MEMBER'
            membership.save()

            messages.success(
                request,
                f"Assigned {the_user.username} as a MEMBER in {the_community.name}."
            )
            return redirect('clara_home_page')  # or wherever you want
    else:
        # GET: just show the form
        form = AssignMemberForm(coordinator_user=request.user)

    return render(request, 'clara_app/assign_member_to_community.html', {
        'form': form,
    })

@login_required
@user_is_project_owner
def project_community(request, project_id):
    """
    Allows a project owner to assign/unassign the project's community.
    """
    project = get_object_or_404(CLARAProject, pk=project_id)

    if request.method == 'POST':
        form = ProjectCommunityForm(request.POST, project=project)
        if form.is_valid():
            community_id_str = form.cleaned_data['community_id']
            try:
                if not community_id_str:
                    # The user chose "No community"
                    project.community = None
                    project.save()
                else:
                    # Assign to a real community
                    community_id = int(community_id_str)
                    community = get_object_or_404(Community, pk=community_id)
                    if project.l2 != community.language:
                        raise ValidationError("Project L2 does not match community language")
                    project.community = community
                    project.save()
                    messages.success(request, f"Assigned project to community '{project.community}'.")
            except (ValueError, ValidationError) as e:
                form.add_error('community_id', str(e))
            else:
                return redirect('project_detail', project_id=project.id)
    else:
        # Pre-select the current community if any
        form = ProjectCommunityForm(project=project, initial={
            'community_id': str(project.community.id) if project.community else ''
        })

    return render(request, 'clara_app/project_community.html', {
        'project': project,
        'form': form,
    })

def phonetic_resources_are_available(l2_language):
    return phonetic_orthography_resources_available(l2_language) or grapheme_phoneme_resources_available(l2_language)

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

# First integration endpoint for Manual Text/Audio Alignment.
# Used by Text/Audio Alignment server to download
#   - labelled segmented text
#   - S3 link to mp3 file
#   - breakpoint text if it exists
# Note that the @login_required or @user_has_a_project_role decorators are intentionally omittted.
# This view is intended to be accessed externally from a server which won't have logged in.
def manual_audio_alignment_integration_endpoint1(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    
    # Get the "labelled segmented" version of the text
    labelled_segmented_text = clara_project_internal.get_labelled_segmented_text()
    
    # Try to get existing HumanAudioInfo for this project or create a new one
    human_audio_info, created = HumanAudioInfo.objects.get_or_create(project=project)
    
    # Access the audio_file and manual_align_metadata_file
    audio_file = human_audio_info.audio_file
    metadata_file = human_audio_info.manual_align_metadata_file
    
    # Copy the audio_file to S3 if it exists as a local file and get a download URL
    if local_file_exists(audio_file):
        copy_local_file_to_s3(audio_file)
    s3_audio_file = s3_file_name(audio_file)
    s3_audio_link = generate_s3_presigned_url(s3_audio_file)
    
    # Read the metadata_file if it already exists to get the breakpoint data
    # It will not exist the first time the endpoint is accessed
    # In subsequent accesses, the Text/Audio Alignment server may have uploaded existing breakpoint data
    # In this case, we pass it back so that it can be edited on the Text/Audio Alignment server
    breakpoint_text = None
    if metadata_file:
        breakpoint_text = read_txt_file(metadata_file)
    
    # Create JSON response
    response_data = {
        'labelled_segmented_text': labelled_segmented_text,
        's3_audio_link': s3_audio_link,
        'breakpoint_text': breakpoint_text    
    }
    
    return JsonResponse(response_data)

# Second integration endpoint for Manual Text/Audio Alignment.
# Used by Text/Audio Alignment server to upload a JSON file.
# The Text/Audio Alignment server also passes a project_id to say where data should be stored.
#
# Note that the @login_required or @user_has_a_project_role decorators are intentionally omittted.
# This view is intended to be accessed externally from a server which won't have logged in.
@csrf_exempt
def manual_audio_alignment_integration_endpoint2(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'failed',
                             'error': 'only POST method is allowed'})
    
    try:
        project_id = request.POST.get('project_id')
        uploaded_file = request.FILES.get('json_file')
        
        project = get_object_or_404(CLARAProject, pk=project_id)
        clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
        human_audio_info, created = HumanAudioInfo.objects.get_or_create(project=project)
        
        # Convert the JSON file to Audacity txt form
        json_file = uploaded_file_to_file(uploaded_file)
        copy_local_file_to_s3_if_necessary(json_file)
        
        # Save the json_file and update human_audio_info
        human_audio_info.manual_align_metadata_file = json_file
        human_audio_info.save()
    
        return JsonResponse({'status': 'success'})
    
    except Exception as e:
        return JsonResponse({'status': 'failed',
                             'error': f'Exception: {str(e)}\n{traceback.format_exc()}'})  # Corrected traceback formatting

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


# Get metadata for a version of a text (internal use only)
@login_required
@user_has_a_project_role                    
def get_metadata_for_version(request, project_id, version):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    metadata = clara_project_internal.get_metadata()

    # Filter metadata by version
    metadata_for_version = [data for data in metadata if data['version'] == version]
    
    return JsonResponse(metadata_for_version, safe=False)
 
# Compare two versions of a project file 
@login_required
@user_has_a_project_role
def compare_versions(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    if request.method == 'POST':
        form = DiffSelectionForm(request.POST)
        # Can't get form validation to work, perhaps something to do with dynamically populating the form?
        #if form.is_valid():
        # version = form.cleaned_data['version']
        # file1 = form.cleaned_data['file1']
        # file2 = form.cleaned_data['file2']
        # required = form.cleaned_data['required']
        version = request.POST['version']
        file1 = request.POST['file1']
        file2 = request.POST['file2']
        required = request.POST.getlist('required')  # getlist is used for fields with multiple values
        
        form1 = DiffSelectionForm(initial={'version': version, 'file1': file1, 'file2': file2})
        metadata = clara_project_internal.get_metadata()
        metadata_for_version = [(data['file'], data['description']) for data in metadata if data['version'] == version]
        form1.fields['file1'].choices = metadata_for_version
        form1.fields['file2'].choices = metadata_for_version

        # This is where the diff is computed
        try:
            diff_result = clara_project_internal.diff_editions_of_text_version(file1, file2, version, required)
        except InternalisationError as e:
            messages.error(request, f'{e.message}')
            return render(request, 'clara_app/diff_and_diff_result.html', {'form': form1, 'project': project})
        
        # Convert markup to HTML
        if 'details' in diff_result:
            diff_result['details'] = diff_result['details'].replace('[inserted]', '<span class="inserted">').replace('[/inserted]', '</span>')
            diff_result['details'] = diff_result['details'].replace('[deleted]', '<span class="deleted">').replace('[/deleted]', '</span>')
            diff_result['details'] = diff_result['details'].replace('[page]', '&lt;page&gt;')

        #return render(request, 'clara_app/diff_result.html', {'diff_result': diff_result, 'project': project})
        return render(request, 'clara_app/diff_and_diff_result.html', {'diff_result': diff_result, 'form': form1, 'project': project})

    else:
        # Initially populate with data for comparing 'plain' files
        metadata = clara_project_internal.get_metadata()
        metadata_for_plain = [(data['file'], data['description']) for data in metadata if data['version'] == 'plain']
        form = DiffSelectionForm(initial={'version': 'plain'})
        form.fields['file1'].choices = metadata_for_plain
        form.fields['file2'].choices = metadata_for_plain

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/diff_and_diff_result.html', {'form': form, 'project': project, 'clara_version': clara_version})

# Generic code for the operations which support creating, annotating, improving and editing text,
# to produce and edit the "plain", "title", "summary", "cefr", "segmented", "gloss", "lemma" and "mwe" versions.
# It is also possible to retrieve archived versions of the files if they exist.
#
# The argument 'this_version' is the version we are currently creating/editing.
# The argument 'previous_version' is the version it is created from. E.g. "gloss" is created from "segmented".
#
# Most of the operations are common to all these types of text, but there are some small divergences
# which have to be treated specially:
#
# - When creating the initial "plain" version, we pass an optional prompt.
# - In the "lemma" version, we may have the additional option of using TreeTagger.
def create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template, text_choices_info=None):
    print(f'create_annotated_text_of_right_type({request}, {project_id}, {this_version}, {previous_version}, {template})')
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    tree_tagger_supported = fully_supported_treetagger_language(project.l2)
    jieba_supported = is_chinese_language(project.l2)
    # The summary and cefr are in English, so always left-to-right even if the main text is right-to-left
    rtl_language=is_rtl_language(project.l2) if not this_version in ( 'summary', 'cefr_level' ) else False
    metadata = clara_project_internal.get_metadata()
    current_version = clara_project_internal.get_file_description(this_version, 'current')
    archived_versions = [(data['file'], data['description']) for data in metadata if data['version'] == this_version]
    text_choice = 'generate' if archived_versions == [] else 'manual'
    prompt = clara_project_internal.load_text_version_or_null('prompt') if this_version == 'plain' else None
    action = None

    if request.method == 'POST':
        form = CreateAnnotationTextFormOfRightType(this_version, request.POST, prompt=prompt,
                                                   archived_versions=archived_versions,
                                                   tree_tagger_supported=tree_tagger_supported, jieba_supported=jieba_supported, is_rtl_language=rtl_language)
        if form.is_valid():
            text_choice = form.cleaned_data['text_choice']
            if text_choice == 'generate_gloss_from_lemma':
                text_choice = 'generate'
                previous_version = 'lemma'
            
            label = form.cleaned_data['label']
            gold_standard = form.cleaned_data['gold_standard']
            username = request.user.username
            # We have an optional prompt when creating or improving the initial text.
            prompt = form.cleaned_data['prompt'] if this_version == 'plain' else None
            text_type = form.cleaned_data['text_type'] if this_version == 'segmented' else None
            if not text_choice in ( 'manual', 'load_archived', 'correct', 'generate', 'improve', 'trivial', 'placeholders', 'mwe_simplify',
                                    'tree_tagger', 'jieba', 'pypinyin', 'delete' ):
                raise InternalCLARAError(message = f'Unknown text_choice type in create_annotated_text_of_right_type: {text_choice}')
            # We're deleting the current version         
            elif text_choice == 'delete':
                annotated_text = ''
                clara_project_internal.save_text_version(this_version, annotated_text, user=username)
                messages.success(request, "File deleted")

                action = 'edit'                                         
                current_version = clara_project_internal.get_file_description(this_version, 'current')
            # We're saving an edited version of a file
            elif text_choice == 'manual':
                if not user_has_a_named_project_role(request.user, project_id, ['OWNER', 'ANNOTATOR']):
                    raise PermissionDenied("You don't have permission to save edited text.")
                annotated_text = form.cleaned_data['text']
                # Check that text is well-formed before trying to save it. If it's not well-formed, we get an InternalisationError
                try:
                    text_object = internalize_text(annotated_text, clara_project_internal.l2_language, clara_project_internal.l1_language, this_version)
                    # Do this so that we get an exception if the MWEs don't match the text
                    if this_version == 'mwe':
                        annotate_mwes_in_text(text_object)
                    clara_project_internal.save_text_version(this_version, annotated_text, 
                                                             user=username, label=label, gold_standard=gold_standard)
                    messages.success(request, "File saved")
                except InternalisationError as e:
                    messages.error(request, e.message)
                except MWEError as e:
                    messages.error(request, e.message)
                
                action = 'edit'                                         
                text_choice = 'manual'
                current_version = clara_project_internal.get_file_description(this_version, 'current')
            # We're loading an archived version of a file
            elif text_choice == 'load_archived':
                try:
                    archived_file = form.cleaned_data['archived_version']
                    annotated_text = read_txt_file(archived_file)
                    text_choice = 'manual'
                    current_version = clara_project_internal.get_file_description(this_version, archived_file)
                    messages.success(request, f"Loaded archived file {archived_file}")
                except FileNotFoundError:
                    messages.error(request, f"Unable to find archived file {archived_file}")
                    try:
                        annotated_text = clara_project_internal.load_text_version(previous_version)
                        text_choice = 'manual'
                    except FileNotFoundError:
                        annotated_text = ""
                        text_choice = 'generate'
                    current_version = ""
            # We're using the AI or a tagger to create a new version of a file
            #elif text_choice in ( 'generate', 'correct', 'improve' ) and not request.user.userprofile.credit > 0:
            elif text_choice in ( 'generate', 'correct', 'improve' ) and not user_has_open_ai_key_or_credit(request.user):
                messages.error(request, f"Sorry, you need a registered OpenAI API key or money in your account to perform this operation")
                annotated_text = ''
                text_choice = 'manual'
            elif text_choice in ( 'generate', 'correct', 'improve', 'trivial', 'placeholders', 'tree_tagger', 'mwe_simplify', 'jieba', 'pypinyin' ):
                if not user_has_a_named_project_role(request.user, project_id, ['OWNER']):
                    raise PermissionDenied("You don't have permission to change the text.")
                try:
                    # Create a unique ID to tag messages posted by this task, and a callback
                    task_type = f'{text_choice}_{this_version}'
                    callback, report_id = make_asynch_callback_and_report_id(request, task_type)

                    # We are correcting the text using the AI and then saving it
                    if text_choice == 'correct':
                        annotated_text = form.cleaned_data['text']
                        async_task(perform_correct_operation_and_store_api_calls, annotated_text, this_version, project, clara_project_internal,
                                   request.user, label, callback=callback)
                        print(f'--- Started correction task')
                        #Redirect to the monitor view, passing the task ID and report ID as parameters
                        return redirect('generate_text_monitor', project_id, this_version, report_id)
                    # We are creating the text using the AI
                    elif text_choice == 'generate':
                        # We want to get a possible template error here rather than in the asynch process
                        clara_project_internal.try_to_use_templates('annotate', this_version)
                        async_task(perform_generate_operation_and_store_api_calls, this_version, project, clara_project_internal,
                                   request.user, label, previous_version=previous_version, prompt=prompt, text_type=text_type, callback=callback)
                        print(f'--- Started generation task, callback = {callback}')
                        #Redirect to the monitor view, passing the task ID and report ID as parameters
                        return redirect('generate_text_monitor', project_id, this_version, report_id)
                    # We are improving the text using the AI
                    elif text_choice == 'improve':
                        # We want to get a possible template error here rather than in the asynch process
                        clara_project_internal.try_to_use_templates('improve', this_version)
                        async_task(perform_improve_operation_and_store_api_calls, this_version, project, clara_project_internal,
                                   request.user, label, prompt=prompt, text_type=text_type, callback=callback)
                        print(f'--- Started improvement task')
                        #Redirect to the monitor view, passing the task ID and report ID as parameters
                        return redirect('generate_text_monitor', project_id, this_version, report_id)
                    # We are creating the text using trivial tagging. This operation is only possible with lemma tagging
                    elif text_choice == 'trivial':
                        action, api_calls = ( 'generate', clara_project_internal.create_lemma_tagged_text_with_trivial_tags(user=username, label=label) )
                        # These operations are handled elsewhere for generation and improvement, due to asynchrony
                        store_api_calls(api_calls, project, request.user, this_version)
                        annotated_text = clara_project_internal.load_text_version(this_version)
                        text_choice = 'manual'
                        success_message = f'Created {this_version} text with trivial tags'
                        print(f'--- {success_message}')
                        messages.success(request, success_message)
                        current_version = clara_project_internal.get_file_description(this_version, 'current')
                    # We are adding placeholders to the text, creating it if it doesn't already exist
                    elif text_choice == 'placeholders':
                        action, api_calls = ( 'generate', clara_project_internal.align_text_version_with_segmented_and_save(this_version,
                                                                                                                            create_if_necessary=True,
                                                                                                                            use_words_for_lemmas=True) )
                        # These operations are handled elsewhere for generation and improvement, due to asynchrony
                        store_api_calls(api_calls, project, request.user, this_version)
                        annotated_text = clara_project_internal.load_text_version(this_version)
                        text_choice = 'manual'
                        success_message = f'Created {this_version} text with trivial tags'
                        print(f'--- {success_message}')
                        messages.success(request, success_message)
                        current_version = clara_project_internal.get_file_description(this_version, 'current')

                    # We are creating the text using TreeTagger. This operation is only possible with lemma tagging
                    elif text_choice == 'tree_tagger':
                        action, api_calls = ( 'generate', clara_project_internal.create_lemma_tagged_text_with_treetagger(user=username, label=label) )
                        store_api_calls(api_calls, project, request.user, this_version)
                        annotated_text = clara_project_internal.load_text_version(this_version)
                        text_choice = 'manual'
                        success_message = f'Created {this_version} text using TreeTagger'
                        print(f'--- {success_message}')
                        messages.success(request, success_message)
                        current_version = clara_project_internal.get_file_description(this_version, 'current')
                    # We are removing MWE analyses. This operation is only possible with MWE tagging
                    elif text_choice == 'mwe_simplify':
                        action, api_calls = ( 'generate', clara_project_internal.remove_analyses_from_mwe_tagged_text(user=username, label=label) )
                        store_api_calls(api_calls, project, request.user, this_version)
                        annotated_text = clara_project_internal.load_text_version('mwe')
                        text_choice = 'manual'
                        success_message = f'Removed CoT traces from {this_version} text'
                        print(f'--- {success_message}')
                        messages.success(request, success_message)
                        current_version = clara_project_internal.get_file_description('mwe', 'current')
                    # We are creating the text using Jieba. This operation is only possible with segmentation
                    elif text_choice == 'jieba':
                        action, api_calls = ( 'generate', clara_project_internal.create_segmented_text_using_jieba(user=username, label=label) )
                        # These operations are handled elsewhere for generation and improvement, due to asynchrony
                        store_api_calls(api_calls, project, request.user, this_version)
                        annotated_text = clara_project_internal.load_text_version(this_version)
                        text_choice = 'manual'
                        success_message = f'Created {this_version} text using Jieba'
                        print(f'--- {success_message}')
                        messages.success(request, success_message)
                        current_version = clara_project_internal.get_file_description(this_version, 'current')
                    # We are creating the text using pypinyin. This operation is only possible with pinyin-annotation
                    elif text_choice == 'pypinyin':
                        action, api_calls = ( 'generate', clara_project_internal.create_pinyin_tagged_text_using_pypinyin(user=username, label=label) )
                        # These operations are handled elsewhere for generation and improvement, due to asynchrony
                        store_api_calls(api_calls, project, request.user, this_version)
                        annotated_text = clara_project_internal.load_text_version(this_version)
                        text_choice = 'manual'
                        success_message = f'Created {this_version} text using pypinyin'
                        print(f'--- {success_message}')
                        messages.success(request, success_message)
                        current_version = clara_project_internal.get_file_description(this_version, 'current')
                except InternalisationError as e:
                    messages.error(request, f"Something appears to be wrong with a prompt example. Error details: {e.message}")
                    annotated_text = ''
                except Exception as e:
                    raise e
                    messages.error(request, f"An error occurred while producing the text. Error details: {str(e)}\n{traceback.format_exc()}")
                    annotated_text = ''
            # If something happened, log it. We don't much care if this fails.
            if action:
                try:
                    CLARAProjectAction.objects.create(
                        project=project,
                        action=action,
                        text_version=this_version,
                        user=request.user
                    )
                except:
                    pass
    # We're displaying the current version of the file, or as close as we can get
    else:
        try:
            annotated_text = clara_project_internal.load_text_version(this_version)
            text_choice = 'manual'
        except FileNotFoundError:
            try:
                annotated_text = clara_project_internal.load_text_version(previous_version)
            except FileNotFoundError:
                annotated_text = ""
            text_choice = 'generate'
        current_version = clara_project_internal.get_file_description(this_version, 'current')

    # The archived versions will have changed if we created a new file
    metadata = clara_project_internal.get_metadata()
    archived_versions = [(data['file'], data['description']) for data in metadata if data['version'] == this_version]
    form = CreateAnnotationTextFormOfRightType(this_version, initial={'text': annotated_text, 'text_choice': text_choice},
                                               prompt=prompt, archived_versions=archived_versions,
                                               current_version=current_version, previous_version=previous_version,
                                               tree_tagger_supported=tree_tagger_supported, jieba_supported=jieba_supported, is_rtl_language=rtl_language)

    #print(f'text_choices_info: {text_choices_info}')
    clara_version = get_user_config(request.user)['clara_version']

    return render(request, template, {'form': form, 'project': project, 'text_choices_info': text_choices_info, 'clara_version': clara_version})

# This is the API endpoint that the JavaScript will poll
@login_required
@user_has_a_project_role
def generate_text_status(request, project_id, report_id):
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
def generate_text_monitor(request, project_id, version, report_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    return render(request, 'clara_app/generate_text_monitor.html',
                  {'version': version, 'report_id': report_id, 'project_id': project_id, 'project': project})

# Display the final result of rendering
@login_required
@user_has_a_project_role
def generate_text_complete(request, project_id, version, status):

    previous_version, template = previous_version_and_template_for_version(version)

    # We are making a new request in this view
    if request.method == 'POST':
        return create_annotated_text_of_right_type(request, project_id, version, previous_version, template)
    # We got here from the monitor view
    else:
        if status == 'error':
            messages.error(request, f"Something went wrong when creating {version} text. Try looking at the 'Recent task updates' view")
        else:
            messages.success(request, f'Created {version} text')
        
        project = get_object_or_404(CLARAProject, pk=project_id)
        clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
        tree_tagger_supported = fully_supported_treetagger_language(project.l2)
        jieba_supported = is_chinese_language(project.l2)
        metadata = clara_project_internal.get_metadata()
        current_version = clara_project_internal.get_file_description(version, 'current')
        archived_versions = [(data['file'], data['description']) for data in metadata if data['version'] == version]
        text_choice = 'generate' if archived_versions == [] else 'manual'
        prompt = clara_project_internal.load_text_version_or_null('prompt') if version == 'plain' else None

        try:
            annotated_text = clara_project_internal.load_text_version(version)
            text_choice = 'manual'
        except FileNotFoundError:
            try:
                annotated_text = clara_project_internal.load_text_version(previous_version)
            except FileNotFoundError:
                annotated_text = ""
            text_choice = 'generate'
        current_version = clara_project_internal.get_file_description(version, 'current')

    # The archived versions will have changed if we created a new file
    metadata = clara_project_internal.get_metadata()
    archived_versions = [(data['file'], data['description']) for data in metadata if data['version'] == version]
    rtl_language=is_rtl_language(project.l2)
    form = CreateAnnotationTextFormOfRightType(version, initial={'text': annotated_text, 'text_choice': text_choice},
                                               prompt=prompt, archived_versions=archived_versions,
                                               current_version=current_version, previous_version=previous_version,
                                               tree_tagger_supported=tree_tagger_supported, jieba_supported=jieba_supported, is_rtl_language=rtl_language)

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, template, {'form': form, 'project': project, 'clara_version': clara_version})

def CreateAnnotationTextFormOfRightType(version, *args, **kwargs):
    if version == 'plain':
        return CreatePlainTextForm(*args, **kwargs)
    elif version == 'title':
        return CreateTitleTextForm(*args, **kwargs)
    elif version == 'segmented_title':
        return CreateSegmentedTitleTextForm(*args, **kwargs)
    elif version == 'summary':
        return CreateSummaryTextForm(*args, **kwargs)
    elif version == 'cefr_level':
        return CreateCEFRTextForm(*args, **kwargs)
    elif version == 'segmented':
        return CreateSegmentedTextForm(*args, **kwargs)
    elif version == 'translated':
        return CreateTranslatedTextForm(*args, **kwargs)
    elif version == 'phonetic':
        return CreatePhoneticTextForm(*args, **kwargs)
    elif version == 'gloss':
        return CreateGlossedTextForm(*args, **kwargs)
    elif version == 'lemma':
        return CreateLemmaTaggedTextForm(*args, **kwargs)
    elif version == 'mwe':
        return CreateMWETaggedTextForm(*args, **kwargs)
    elif version == 'pinyin':
        return CreatePinyinTaggedTextForm(*args, **kwargs)
    elif version == 'lemma_and_gloss':
        return CreateLemmaAndGlossTaggedTextForm(*args, **kwargs)
    else:
        raise InternalCLARAError(message = f'Unknown first argument in CreateAnnotationTextFormOfRightType: {version}')

def perform_correct_operation_and_store_api_calls(annotated_text, version, project, clara_project_internal,
                                                  user_object, label, callback=None):
    try:
        config_info = get_user_config(user_object)
        operation, api_calls = perform_correct_operation(annotated_text, version, clara_project_internal, user_object.username, label, 
                                                         config_info=config_info, callback=callback)
        store_api_calls(api_calls, project, user_object, version)
        post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        #raise e
        post_task_update(callback, f"error")

def perform_correct_operation(annotated_text, version, clara_project_internal, user, label, config_info={}, callback=None):
    #print(f'clara_project_internal.correct_syntax_and_save({annotated_text}, {version}, user={user}, label={label}, callback={callback})')
    return ( 'correct', clara_project_internal.correct_syntax_and_save(annotated_text, version, user=user, label=label,
                                                                       config_info=config_info, callback=callback) )

def perform_generate_operation_and_store_api_calls(version, project, clara_project_internal,
                                                   user_object, label, previous_version='default', prompt=None, text_type=None, callback=None):
    #post_task_update(callback, f'perform_generate_operation_and_store_api_calls({version}, {project}, {clara_project_internal}, {user_object}, {label}, {previous_version}, {prompt}, {callback})')
    try:
        config_info = get_user_config(user_object)
        operation, api_calls = perform_generate_operation(version, clara_project_internal, user_object.username, label,
                                                          previous_version=previous_version, prompt=prompt, text_type=text_type, 
                                                          config_info=config_info, callback=callback)
        #print(f'perform_generate_operation_and_store_api_calls: total cost = {sum([ api_call.cost for api_call in api_calls ])}')
        store_api_calls(api_calls, project, user_object, version)
        post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Exception in perform_generate_operation_and_store_api_calls({version}, ...): {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")
    
def perform_generate_operation(version, clara_project_internal, user, label, previous_version=None, prompt=None, text_type=None, config_info={}, callback=None):
    if version == 'plain':
        return ( 'generate', clara_project_internal.create_plain_text(prompt=prompt, user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'title':
        return ( 'generate', clara_project_internal.create_title(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'segmented_title':
        return ( 'generate', clara_project_internal.create_segmented_title(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'summary':
        return ( 'generate', clara_project_internal.create_summary(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'cefr_level':
        return ( 'generate', clara_project_internal.get_cefr_level(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'segmented':
        return ( 'generate', clara_project_internal.create_segmented_text(text_type=text_type, user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'translated':
        return ( 'generate', clara_project_internal.create_translated_text(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'phonetic':
        return ( 'generate', clara_project_internal.create_phonetic_text(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'gloss':
        return ( 'generate', clara_project_internal.create_glossed_text(previous_version=previous_version,
                                                                        user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'lemma':
        return ( 'generate', clara_project_internal.create_lemma_tagged_text(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'mwe':
        return ( 'generate', clara_project_internal.create_mwe_tagged_text(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'pinyin':
        return ( 'generate', clara_project_internal.create_pinyin_tagged_text(user=user, label=label, config_info=config_info, callback=callback) )
    # There is no generate operation for lemma_and_gloss, since we make it by merging lemma and gloss
    else:
        raise InternalCLARAError(message = f'Unknown first argument in perform_generate_operation: {version}')

def perform_improve_operation_and_store_api_calls(version, project, clara_project_internal,
                                                   user_object, label, prompt=None, text_type=None, callback=None):
    try:
        config_info = get_user_config(user_object)
        operation, api_calls = perform_improve_operation(version, clara_project_internal, user_object.username, label,
                                                         prompt=prompt, text_type=text_type, config_info=config_info, callback=callback)
        store_api_calls(api_calls, project, user_object, version)
        post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Exception in perform_improve_operation_and_store_api_calls({version},...): {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")
 
def perform_improve_operation(version, clara_project_internal, user, label, prompt=None, text_type=None, config_info={}, callback=None):
    if version == 'plain':
        return ( 'generate', clara_project_internal.improve_plain_text(prompt=prompt, user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'title':
        return ( 'generate', clara_project_internal.improve_title(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'summary':
        return ( 'generate', clara_project_internal.improve_summary(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'segmented':
        return ( 'generate', clara_project_internal.improve_segmented_text(text_type=text_type, user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'gloss':
        return ( 'generate', clara_project_internal.improve_glossed_text(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'lemma':
        return ( 'generate', clara_project_internal.improve_lemma_tagged_text(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'pinyin':
        return ( 'generate', clara_project_internal.improve_pinyin_tagged_text(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'lemma_and_gloss':
        return ( 'generate', clara_project_internal.improve_lemma_and_gloss_tagged_text(user=user, label=label, config_info=config_info, callback=callback) )
    else:
        raise InternalCLARAError(message = f'Unknown first argument in perform_improve_operation: {version}')

def previous_version_and_template_for_version(this_version, previous_version=None):
    if this_version == 'plain':
        return ( 'plain', 'clara_app/create_plain_text.html' )
    elif this_version == 'title':
        return ( 'plain', 'clara_app/create_title.html' )
    elif this_version == 'segmented_title':
        return ( 'title', 'clara_app/create_segmented_title.html' )
    elif this_version == 'summary':
        return ( 'plain', 'clara_app/create_summary.html' )
    elif this_version == 'cefr_level':
        return ( 'plain', 'clara_app/get_cefr_level.html' )
    elif this_version == 'segmented':
        return ( 'plain', 'clara_app/create_segmented_text.html' )
    elif this_version == 'translated':
        return ( 'segmented_with_images', 'clara_app/create_translated_text.html' )
    elif this_version == 'phonetic':
        return ( 'segmented_with_images', 'clara_app/create_phonetic_text.html' )
    elif this_version == 'gloss':
        if previous_version == 'lemma':
            return ( 'lemma', 'clara_app/create_glossed_text_from_lemma.html' )
        else:
            return ( 'segmented_with_images', 'clara_app/create_glossed_text.html' )
    elif this_version == 'lemma':
        return ( 'segmented_with_images', 'clara_app/create_lemma_tagged_text.html' )
    elif this_version == 'mwe':
        return ( 'segmented_with_images', 'clara_app/create_mwe_tagged_text.html' )
    elif this_version == 'pinyin':
        return ( 'segmented_with_images', 'clara_app/create_pinyin_tagged_text.html' )
    elif this_version == 'lemma_and_gloss':
        return ( 'lemma_and_gloss', 'clara_app/create_lemma_and_gloss_tagged_text.html' )
    else:
        raise InternalCLARAError(message = f'Unknown first argument in previous_version_and_template_for_version: {this_version}')

# Create or edit "plain" version of the text        
@login_required
@user_has_a_project_role
def create_plain_text(request, project_id):
    this_version = 'plain'
    previous_version, template = previous_version_and_template_for_version(this_version)
    text_choices_info = {
        'generate': "Generate text using AI. Select this option. Type your request into the 'Prompt' box, for example 'Write a short poem about why kittens are cute'. Then press the 'Create' button at the bottom.",
        'improve': "Improve existing text using AI: this only makes sense if there already is text. Select this option. Then press the 'Improve' button at the bottom.",
        'manual': "Manually enter/edit text. Select this option, then type whatever you want into the text box. Then press the 'Save' button at the bottom.",
        'load_archived': "Load archived version. Select this option and also select something from the 'Archived version' menu. Then press the 'Load' button at the bottom."
    }
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template, text_choices_info=text_choices_info)

#Create or edit title for the text     
@login_required
@user_has_a_project_role
def create_title(request, project_id):
    this_version = 'title'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

#Create or edit title for the text     
@login_required
@user_has_a_project_role
def create_segmented_title(request, project_id):
    this_version = 'segmented_title'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

#Create or edit "summary" version of the text     
@login_required
@user_has_a_project_role
def create_summary(request, project_id):
    this_version = 'summary'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

#Create or edit "cefr_level" version of the text     
@login_required
@user_has_a_project_role
def create_cefr_level(request, project_id):
    this_version = 'cefr_level'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Create or edit "segmented" version of the text     
@login_required
@user_has_a_project_role
def create_segmented_text(request, project_id):
    this_version = 'segmented'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Create or edit "translated" version of the text     
@login_required
@user_has_a_project_role
def create_translated_text(request, project_id):
    this_version = 'translated'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Create or edit "phonetic" version of the text     
@login_required
@user_has_a_project_role
def create_phonetic_text(request, project_id):
    this_version = 'phonetic'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Create or edit "glossed" version of the text, using the segmented_with_images version as input     
@login_required
@user_has_a_project_role
def create_glossed_text(request, project_id):
    this_version = 'gloss'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Create or edit "glossed" version of the text, using the lemma version as input      
@login_required
@user_has_a_project_role
def create_glossed_text_from_lemma(request, project_id):
    this_version = 'gloss'
    previous_version = 'lemma'
    previous_version, template = previous_version_and_template_for_version(this_version, previous_version=previous_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Create or edit "lemma-tagged" version of the text 
@login_required
@user_has_a_project_role
def create_lemma_tagged_text(request, project_id):
    this_version = 'lemma'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Create or edit "mwe" version of the text 
@login_required
@user_has_a_project_role
def create_mwe_tagged_text(request, project_id):
    this_version = 'mwe'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Create or edit "pinyin-tagged" version of the text 
@login_required
@user_has_a_project_role
def create_pinyin_tagged_text(request, project_id):
    this_version = 'pinyin'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Create or edit "lemma-and-glossed" version of the text 
@login_required
@user_has_a_project_role
def create_lemma_and_gloss_tagged_text(request, project_id):
    this_version = 'lemma_and_gloss'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Display the history of updates to project files 
@login_required
@user_has_a_project_role
def project_history(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    actions = CLARAProjectAction.objects.filter(project=project).order_by('-timestamp')

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/project_history.html', {'project': project, 'actions': actions, 'clara_version': clara_version})

@login_required
@user_has_a_project_role
def edit_images(request, project_id, dall_e_3_image_status):
    actions_requiring_openai = ( 'create_dalle_image_for_whole_text',
                                 'create_dalle_style_image',
                                 'generate_image_descriptions',
                                 'create_image_request_sequence')
    user = request.user
    can_use_ai = user_has_open_ai_key_or_credit(user)
    config_info = get_user_config(user)
    username = user.username
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    clara_version = get_user_config(request.user)['clara_version']

    if project.uses_coherent_image_set and project.use_translation_for_images and not clara_project_internal.load_text_version("translated"):
        messages.error(request, f"Project is marked as using translations to create images, but there are no translations yet")
        return render(request, 'clara_app/edit_images.html', {
                            'formset': ImageFormSet(initial=[], prefix='images'),
                            'description_formset': None,
                            'style_form': None,
                            'image_request_sequence_form': None,
                            'project': project,
                            'uses_coherent_image_set': False,
                            'clara_version': clara_version,
                            'errors': None,
                        })

    page_texts = None
    segmented_texts = None
    translated_texts = None
    mwe_texts = None
    lemma_texts = None
    gloss_texts = None
    
    try:
        # Don't try to correct syntax errors here, there should not be any.
        all_page_texts = clara_project_internal.get_page_texts()
        #pprint.pprint(all_page_texts)
        page_texts = all_page_texts['plain']
        segmented_texts = all_page_texts['segmented']
        translated_texts = all_page_texts['translated']
        mwe_texts = all_page_texts['mwe']
        lemma_texts = all_page_texts['lemma']
        gloss_texts = all_page_texts['gloss']
        try:
            mwe_text = clara_project_internal.load_text_version_or_null("mwe")
            if mwe_text:
                internalised_mwe_text = clara_project_internal.internalize_text(mwe_text, "mwe")
                # Do this so that we get an exception we can report if the MWEs don't match the text
                annotate_mwes_in_text(internalised_mwe_text)
        except MWEError as e:
             messages.error(request, f"{e.message}")
    except InternalisationError as e:
        messages.error(request, f"{e.message}")
    except InternalCLARAError as e:
        messages.error(request, f"{e.message}")
    except Exception as e:
        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
   
    # Retrieve existing images
    images = clara_project_internal.get_all_project_images()
    initial_data = [{'image_file_path': img.image_file_path,
                     'image_base_name': basename(img.image_file_path) if img.image_file_path else None,
                     'image_name': img.image_name,
                     'associated_text': img.associated_text,
                     'associated_areas': img.associated_areas,
                     'page': img.page,
                     'page_text': page_texts[img.page - 1] if page_texts and img.page <= len(page_texts) else '',
                     'segmented_text': segmented_texts[img.page - 1] if segmented_texts and img.page <= len(segmented_texts) else '',
                     'translated_text': translated_texts[img.page - 1] if translated_texts and img.page <= len(translated_texts) else '',
                     'mwe_text': mwe_texts[img.page - 1] if mwe_texts and img.page <= len(mwe_texts) else '',
                     'lemma_text': lemma_texts[img.page - 1] if lemma_texts and img.page <= len(lemma_texts) else '',
                     'gloss_text': gloss_texts[img.page - 1] if gloss_texts and img.page <= len(gloss_texts) else '',
                     'position': img.position,
                     'style_description': img.style_description,
                     'content_description': img.content_description,
                     'request_type': img.request_type,
                     'description_variable': img.description_variable,
                     'description_variables': ', '.join(img.description_variables) if img.description_variables else '',
                     'user_prompt': img.user_prompt,
                     'display_text_fields': ( img.request_type != 'image-understanding' ),
                     'display_text_fields_label': 'Text versions' if ( img.request_type != 'image-understanding' ) else 'none',
                     }
                    for img in images ]
    pprint.pprint(initial_data)

    # Create placeholder image lines for pages that don't have an image, so that we can display the text versions for those pages.
    if page_texts:
        used_page_numbers = [ item['page'] for item in initial_data ]
        for page_number in range(1, len(page_texts) + 1):
            if not page_number in used_page_numbers:
                placeholder_data = {'image_file_path': None,
                                    'image_base_name': None,
                                    'image_name': f'image_{page_number}_top',
                                    'associated_text': '',
                                    'associated_areas': '',
                                    'page': page_number,
                                    'page_text': page_texts[page_number - 1] if page_number <= len(page_texts) else '',
                                    'segmented_text': segmented_texts[page_number - 1] if page_number <= len(segmented_texts) else '',
                                    'translated_text': translated_texts[page_number - 1] if page_number <= len(translated_texts) else '',
                                    'mwe_text': mwe_texts[page_number - 1] if page_number <= len(mwe_texts) else '',
                                    'lemma_text': lemma_texts[page_number - 1] if page_number <= len(lemma_texts) else '',
                                    'gloss_text': gloss_texts[page_number - 1] if page_number <= len(gloss_texts) else '',
                                    'position': 'top',
                                    'style_description': '',
                                    'content_description': '',
                                    'request_type': 'image-generation',
                                    'description_variable': None,
                                    'description_variables': '',
                                    'user_prompt': '',
                                    'display_text_fields': True,
                                    'display_text_fields_label': 'Text versions'
                                    }
                initial_data.append(placeholder_data)
    # Sort by page number with generation requests first
    initial_data = sorted(initial_data, key=lambda x: ( x['page'] + ( 0 if x['request_type'] == 'image-generation' else 0.1 ) ) )

    # Make sure that we only display text fields for the first image line with a given page number.
    page_numbers_already_mentioned = []
    for data in initial_data:
        page_number = data['page']
        if page_number in page_numbers_already_mentioned:
            data['display_text_fields'] = False
            data['display_text_fields_label'] = 'none'
        else:
            page_numbers_already_mentioned.append(page_number)

    #print(f'initial_data')
    #pprint.pprint(initial_data)
    
    if len(initial_data) != 0 and initial_data[0]['page'] == 0:
        # We have a style image on the notional page 0, move that information to the style image template
        style_image_record = initial_data[0]
        initial_style_image_data = { 'image_base_name': style_image_record['image_base_name'],
                                     'user_prompt': style_image_record['user_prompt'],
                                     'style_description': style_image_record['style_description']
                                     }
        style_description = style_image_record['style_description']
        # The other data is normal images that will appear in the text
        initial_data = initial_data[1:]
    elif project.uses_coherent_image_set:
        initial_style_image_data = { 'image_base_name': None,
                                     'user_prompt': ''
                                     }
        style_description = None
    else:
        initial_style_image_data = None
        style_description = None

    descriptions = clara_project_internal.get_all_project_image_descriptions()
    initial_description_data = [{'description_variable': desc.description_variable,
                                 'explanation': desc.explanation
                                 }
                                for desc in descriptions ]

    valid_description_variables = [desc['description_variable'] for desc in initial_description_data]

    if request.method == 'POST':
        if 'action' in request.POST: 
            action = request.POST['action']
            print(f'--- action = {action}')
            if action in actions_requiring_openai:
                if not can_use_ai:
                    messages.error(request, f"Sorry, you need a registered OpenAI API key or money in your account to create images")
                    return redirect('edit_images', project_id=project_id, dall_e_3_image_status='no_image')
                if action == 'create_dalle_image_for_whole_text':
                    task_type = f'create_dalle_e_3_images'
                    callback, report_id = make_asynch_callback_and_report_id(request, task_type)

                    async_task(create_and_add_dall_e_3_image_for_whole_text, project_id, callback=callback)
                    print(f'--- Started DALL-E-3 image generation task')
                    #Redirect to the monitor view, passing the task ID and report ID as parameters
                    return redirect('create_dall_e_3_image_monitor', project_id, report_id)
                elif action == 'generate_image_descriptions':
                    task_type = f'generate_image_descriptions'
                    callback, report_id = make_asynch_callback_and_report_id(request, task_type)

                    async_task(generate_image_descriptions, project_id, callback=callback)
                    print(f'--- Started image descriptions generation task')
                    #Redirect to the monitor view, passing the task ID and report ID as parameters
                    return redirect('create_dall_e_3_image_monitor', project_id, report_id)
                elif action == 'create_image_request_sequence':
                    task_type = f'create_image_request_sequence'
                    callback, report_id = make_asynch_callback_and_report_id(request, task_type)

                    async_task(create_image_request_sequence, project_id, callback=callback)
                    print(f'--- Started image request sequence generation task')
                    #Redirect to the monitor view, passing the task ID and report ID as parameters
                    return redirect('create_dall_e_3_image_monitor', project_id, report_id)
                elif action == 'create_dalle_style_image':
                    style_image_form = StyleImageForm(request.POST)
                    if not style_image_form.is_valid():
                        messages.error(request, "Invalid form data (form #{i}): {form}")
                        return redirect('edit_images', project_id=project_id, dall_e_3_image_status='no_image')
                    if not style_image_form.cleaned_data.get('user_prompt'):
                        messages.error(request, "No instructions given for creating style image.")
                        return redirect('edit_images', project_id=project_id, dall_e_3_image_status='no_image')
                    user_prompt = style_image_form.cleaned_data.get('user_prompt')
                    task_type = f'create_dalle_e_3_images'
                    callback, report_id = make_asynch_callback_and_report_id(request, task_type)

                    async_task(create_and_add_dall_e_3_image_for_style, project_id, user_prompt, callback=callback)
                    print(f'--- Started DALL-E-3 image generation task')
                    #Redirect to the monitor view, passing the task ID and report ID as parameters
                    return redirect('create_dall_e_3_image_monitor', project_id, report_id)
                
            elif action == 'save_image_descriptions':
                description_formset = ImageDescriptionFormSet(request.POST, prefix='descriptions')
                #print(description_formset)
                for i in range(0, len(description_formset)):
                    form = description_formset[i]
                    # Only use the last row if a new description variable has been filled in
                    if not ( i == len(description_formset) - 1 and not 'description_variable' in form.changed_data ):
                        if not form.is_valid():
                            print(f'--- Invalid description form data (form #{i}): {form}')
                            messages.error(request, "Invalid descrimption form data.")
                            return redirect('edit_images', project_id=project_id, dall_e_3_image_status='no_image')
                        description_variable = form.cleaned_data['description_variable']
                        explanation = form.cleaned_data['explanation']
                        delete = form.cleaned_data['delete']
                        if delete:
                            # We are deleting a variable
                            clara_project_internal.remove_project_image_description(description_variable)
                            messages.success(request, f"Deleted description variable: {description_variable}")
                        else:
                           # We are saving a possibly added or modified variable
                            clara_project_internal.add_project_image_description(description_variable, explanation)
                messages.success(request, "Description data saved")
                return redirect('edit_images', project_id=project_id, dall_e_3_image_status='no_image')
            else:
                image_requests = []
                new_plain_texts = []
                new_segmented_texts = []
                new_translated_texts = []
                new_mwe_texts = []
                new_lemma_texts = []
                new_gloss_texts = []
                formset = ImageFormSet(request.POST, request.FILES, prefix='images', form_kwargs={'valid_description_variables': valid_description_variables})
                
                errors = None
                if not formset.is_valid():
                    errors = formset.errors
                    print(f'errors = "{errors}"')
                    # Pass errors to the template
                    if project.uses_coherent_image_set:
                        style_form = StyleImageForm(initial=initial_style_image_data)
                        description_formset = ImageDescriptionFormSet(initial=initial_description_data, prefix='descriptions')
                        image_request_sequence_form = ImageSequenceForm()
                    else:
                        style_form = None
                        description_formset = None
                        image_request_sequence_form = None
                    return render(request, 'clara_app/edit_images.html', {
                        'formset': formset,
                        'description_formset': description_formset,
                        'style_form': style_form,
                        'image_request_sequence_form': image_request_sequence_form,
                        'project': project,
                        'uses_coherent_image_set': project.uses_coherent_image_set,
                        'clara_version': clara_version,
                        'errors': errors,
                    })
                for i in range(0, len(formset)):
                    form = formset[i]
                    #print(f"i = {i}. form.cleaned_data['display_text_fields_label'] = {form.cleaned_data['display_text_fields_label']}")
                    previous_record = initial_data[i] if i < len(initial_data) else None
                    #print(f'previous_record#{i} = {previous_record}')
                    # Ignore the last (extra) form if image_file_path has not been changed, i.e. we are not uploading a file
                    #print(f"--- form #{i}: form.changed_data = {form.changed_data}")
                    if not ( i == len(formset) - 1 and not 'image_file_path' in form.changed_data and not 'user_prompt' in form.changed_data ):

                        # form.cleaned_data.get('image_file_path') is special, since we get it from uploading a file.
                        # If there is no file upload, the value is null
                        if form.cleaned_data.get('image_file_path'):
                            uploaded_image_file_path = form.cleaned_data.get('image_file_path')
                            real_image_file_path = uploaded_file_to_file(uploaded_image_file_path)
                            uploaded_file = True
                            #print(f'--- real_image_file_path for {image_name} (from upload) = {real_image_file_path}')
                        elif previous_record:
                            real_image_file_path = previous_record['image_file_path']
                            #print(f'--- real_image_file_path for {image_name} (previously stored) = {real_image_file_path}')
                            uploaded_file = False
                        else:
                            real_image_file_path = None
                            uploaded_file = False

                        #print(f"i = {i}, page_text = '{form.cleaned_data['page_text']}', translated_text = '{form.cleaned_data['translated_text']}'")     

                        if 'display_text_fields_label' in form.cleaned_data and form.cleaned_data['display_text_fields_label'] == 'Text versions':
                            new_plain_texts.append(form.cleaned_data['page_text'])
                            new_segmented_texts.append(form.cleaned_data['segmented_text'])
                            new_translated_texts.append(form.cleaned_data['translated_text'])
                            new_mwe_texts.append(form.cleaned_data['mwe_text'])
                            new_lemma_texts.append(form.cleaned_data['lemma_text'])
                            new_gloss_texts.append(form.cleaned_data['gloss_text'])
                            
                        associated_text = form.cleaned_data.get('associated_text')
                        associated_areas = form.cleaned_data.get('associated_areas')
                        page = form.cleaned_data.get('page', 1)
                        position = form.cleaned_data.get('position', 'bottom')
                        user_prompt = form.cleaned_data.get('user_prompt')
                        generate = form.cleaned_data.get('generate')
                        delete = form.cleaned_data.get('delete')
                        request_type = form.cleaned_data.get('request_type')
                        content_description = form.cleaned_data.get('content_description')
                        description_variable = form.cleaned_data.get('description_variable')
                        description_variables = form.cleaned_data.get('description_variables')
                        if form.cleaned_data.get('image_name'):
                            image_name = form.cleaned_data.get('image_name')
                        elif previous_record and previous_record['image_name']:
                            image_name = previous_record['image_name']
                        else:
                            # If we're adding a new description, there will be no image name
                            image_name = f'get_{description_variable}'
                        
                        if previous_record and not content_description:
                            content_description = previous_record['content_description']
                        #print(f'--- real_image_file_path = {real_image_file_path}, image_name = {image_name}, page = {page}, delete = {delete}')

                        #print(f'image_name = "{image_name}", real_image_file_path = "{real_image_file_path}"')
                        #print(f'user_prompt = "{user_prompt}", content_description = "{content_description}"')
                        #print(f'description_variables = "{description_variables}"')

                        if image_name and delete and not errors:
                            # We are deleting an image
                            clara_project_internal.remove_project_image(image_name)
                            messages.success(request, f"Deleted image: {image_name}")
                        elif generate and user_prompt and not errors:
                            # We are generating or understanding an image. Put it on the queue for async processing at the end
                            image_request = { 'image_name': image_name,
                                              'page': page,
                                              'position': position,
                                              'user_prompt': user_prompt,
                                              'content_description': content_description,
                                              'style_description': style_description,
                                              'current_image': previous_record['image_file_path'] if previous_record else None,
                                              'request_type': request_type,
                                              'description_variable': description_variable,
                                              'description_variables': description_variables
                                              }
                            image_requests.append(image_request)
                            clara_project_internal.add_project_image(image_name, real_image_file_path,
                                                                     associated_text=associated_text,
                                                                     associated_areas=associated_areas,
                                                                     page=page, position=position,
                                                                     request_type=request_type,
                                                                     user_prompt=user_prompt,
                                                                     content_description=content_description,
                                                                     description_variable=description_variable,
                                                                     description_variables=description_variables,
                                                                     archive=False
                                                                     )
                        elif ( ( image_name and real_image_file_path ) or user_prompt ) and not errors:

                            clara_project_internal.add_project_image(image_name, real_image_file_path,
                                                                     associated_text=associated_text,
                                                                     associated_areas=associated_areas,
                                                                     page=page, position=position,
                                                                     request_type=request_type,
                                                                     user_prompt=user_prompt,
                                                                     content_description=content_description,
                                                                     description_variable=description_variable,
                                                                     description_variables=description_variables,
                                                                     archive=uploaded_file # Unless it's an uploaded file, we don't want to archive
                                                                     )
                            
                # Save the concatenated texts back to the project
                try:
                    types_and_texts = { 'plain': new_plain_texts,
                                        'segmented': new_segmented_texts,
                                        'translated': new_translated_texts,
                                        'mwe': new_mwe_texts,
                                        'lemma': new_lemma_texts,
                                        'gloss': new_gloss_texts }
                    #print(f'types_and_texts:')
                    #pprint.pprint(types_and_texts)
                    api_calls = clara_project_internal.save_page_texts_multiple(types_and_texts, user=username, can_use_ai=False, config_info=config_info)
                    store_api_calls(api_calls, project, project.user, 'correct')
                except ( InternalisationError, MWEError ) as e:
                    if not can_use_ai:
                        messages.error(request, f"There appears to be an inconsistency. Error details: {e.message}")
                        return redirect('edit_images', project_id=project_id, dall_e_3_image_status='no_image')
                    else:
                        task_type = f'correct_syntax'
                        callback, report_id = make_asynch_callback_and_report_id(request, task_type)

                        print(f'--- About to start syntax correction task')
                        async_task(save_page_texts_multiple, project, clara_project_internal, types_and_texts, username,
                                   config_info=config_info, callback=callback)
                        print(f'--- Started syntax correction task')
                        #Redirect to the monitor view, passing the project ID and report ID as parameters
                        return redirect('save_page_texts_multiple_monitor', project_id, report_id)
                                                   
                if len(image_requests) != 0:
                    if not can_use_ai:
                        messages.error(request, f"Sorry, you need a registered OpenAI API key or money in your account to create images")
                        return redirect('edit_images', project_id=project_id, dall_e_3_image_status='no_image')
                    task_type = f'create_dalle_e_3_images'
                    callback, report_id = make_asynch_callback_and_report_id(request, task_type)
                    async_task(create_and_add_coherent_dall_e_3_images, project_id, image_requests, callback=callback)
                    return redirect('create_dall_e_3_image_monitor', project_id, report_id)
                else:            
                    messages.success(request, "Image data updated")
                    return redirect('edit_images', project_id=project_id, dall_e_3_image_status='no_image')
    else:
        formset = ImageFormSet(initial=initial_data, prefix='images', form_kwargs={'valid_description_variables': valid_description_variables})
        description_formset = ImageDescriptionFormSet(initial=initial_description_data, prefix='descriptions')
        style_form = StyleImageForm(initial=initial_style_image_data)
        if project.uses_coherent_image_set:
            image_request_sequence_form = ImageSequenceForm()
        else:
            image_request_sequence_form = None
        #print(f'--- image_request_sequence_form = {image_request_sequence_form}')
        
        if dall_e_3_image_status == 'finished':
            messages.success(request, "Image task successfully completed")
        elif dall_e_3_image_status == 'error':
            messages.error(request, "Something went wrong when performing image task. Look at the 'Recent task updates' view for further information.")
        elif dall_e_3_image_status == 'finished_syntax_correction':
            messages.success(request, "There was an error in the syntax. This has been corrected and the text has been saved")
        elif dall_e_3_image_status == 'error_syntax_correction':
            messages.error(request, "There was an error in the syntax, and something went wrong when trying to fix it. Look at the 'Recent task updates' view for further information.")

    return render(request, 'clara_app/edit_images.html', {'formset': formset,
                                                          'description_formset': description_formset,
                                                          'style_form': style_form,
                                                          'image_request_sequence_form': image_request_sequence_form,
                                                          'project': project,
                                                          'uses_coherent_image_set': project.uses_coherent_image_set,
                                                          'clara_version': clara_version,
                                                          'errors': []})

#_edit_images_v2_trace = True
_edit_images_v2_trace = False

# Version of edit_images for uses_coherent_image_set_v2
@login_required
@user_has_a_project_role
def edit_images_v2(request, project_id, status):
    actions_requiring_openai = ( 'create_style_description_and_image',
                                 'create_element_names',
                                 'add_v2_element',
                                 'create_element_descriptions_and_images',
                                 'create_page_descriptions_and_images',
                                 'generate_variant_images' )
    user = request.user
    can_use_ai = user_has_open_ai_key_or_credit(user)
    config_info = get_user_config(user)
    username = user.username
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    clara_version = get_user_config(request.user)['clara_version']
    inconsistent = False
    style_exists = False
    element_names_exist = False
    elements_exist = False
    pages_exist = False

    try:
        project_dir = clara_project_internal.coherent_images_v2_project_dir
        # Retrieve the stored params
        params = clara_project_internal.get_coherent_images_v2_params()
    except Exception as e:
        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
        params = default_params
        inconsistent = True

    try:
        overview_file_exists = clara_project_internal.overview_document_v2_exists()
    except Exception as e:
        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
        overview_file_exists = False
        inconsistent = True   
    
    try:
        # Don't try to correct syntax errors here, there should not be any.
        all_page_texts = clara_project_internal.get_page_texts()
        if _edit_images_v2_trace:
            print(f'all_page_texts:')
            pprint.pprint(all_page_texts)
        page_texts = all_page_texts['plain']
        segmented_texts = all_page_texts['segmented']
        translated_texts = all_page_texts['translated']
        mwe_texts = all_page_texts['mwe']
        lemma_texts = all_page_texts['lemma']
        gloss_texts = all_page_texts['gloss']
        try:
            mwe_text = clara_project_internal.load_text_version("mwe")
            internalised_mwe_text = clara_project_internal.internalize_text(mwe_text, "mwe")
            # Do this so that we get an exception we can report if the MWEs don't match the text
            annotate_mwes_in_text(internalised_mwe_text)
        except FileNotFoundError as e:
            pass
        except MWEError as e:
             messages.error(request, f"{e.message}")
    except InternalisationError as e:
        messages.error(request, f"{e.message}")
        inconsistent = True
    except InternalCLARAError as e:
        messages.error(request, f"{e.message}")
        inconsistent = True
    except Exception as e:
        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
        inconsistent = True
   
    # Retrieve existing images for pages, elements and style
    try:
        images = clara_project_internal.get_project_images_dict_v2()
        if _edit_images_v2_trace:
            print(f'images:')
            pprint.pprint(images)
    except Exception as e:
        messages.error(request, f"Unable to retrieve image information")
        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
        style_data = []
        element_data = []
        indexed_page_data = []
        inconsistent = True

    background_advice = images['background']

    try:    
        style_data = [ images['style'] ] if images['style'] else []

        # Add a blank style record if we don't already have one, so that we can start
        if len(style_data) == 0:
            style_data = [{'relative_file_path': None,
                           'alternate_images': [],
                           'advice': '' }]
    except Exception as e:
        messages.error(request, f"Unable to get style information")
        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
        style_data = []
        inconsistent = True

    element_data = []
    try:
        indexed_element_data = images['elements']
        for element_text in indexed_element_data:
            item = indexed_element_data[element_text]
            element_data.append({ 'element_text': element_text,
                                  'element_name': item['element_name'],
                                  'relative_file_path': item['relative_file_path'],
                                  'advice': item['advice'],
                                  'alternate_images': item['alternate_images'] })
    except Exception as e:
        messages.error(request, f"Unable to get element information")
        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
        inconsistent = True

    try:
        indexed_page_data = images['pages']
    except Exception as e:
        messages.error(request, f"Unable to get page information")
        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
        indexed_page_data = {}
        inconsistent = True

    # Since we are displaying text and annotated text data for each page, add it here. 
    # We also need to create entries for the pages that currently have no image.
    try:
        page_data = []
        for index in range(0, len(page_texts)):
            page = index + 1
            item = { 'page': page,
                     'page_text': page_texts[index],
                     'segmented_text': segmented_texts[index],
                     'translated_text': translated_texts[index],
                     'mwe_text': mwe_texts[index],
                     'lemma_text': lemma_texts[index],
                     'gloss_text': gloss_texts[index],
                     'relative_file_path': indexed_page_data[page]['relative_file_path'] if page in indexed_page_data else None,
                     'position': 'top',
                     'advice': indexed_page_data[page]['advice'] if page in indexed_page_data else None,
                     'alternate_images': indexed_page_data[page]['alternate_images'] if page in indexed_page_data else None
                     }
            page_data.append(item)
    except Exception as e:
        messages.error(request, f"Unable to get page information")
        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
        page_data = []
        inconsistent = True

    try:
        style_exists = len(clara_project_internal.get_style_description_v2()) != 0
        element_names_exist = len(clara_project_internal.get_all_element_texts_v2()) != 0
        elements_exist = len(clara_project_internal.get_all_element_images_v2()) != 0
        pages_exist = len(clara_project_internal.get_all_page_images_v2()) != 0
    except Exception as e:
        messages.error(request, f"Unable to get information about existence of element names, elements and page images")
        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
        page_data = []
        inconsistent = True

    if inconsistent:
        return render(request, 'clara_app/edit_images_v2.html', { 'params_form': None,
                                                                  'style_formset': None,
                                                                  'element_formset': None,
                                                                  'page_formset': None,
                                                                  'project': project,
                                                                  'clara_version': clara_version,
                                                                  'overview_file_exists': overview_file_exists,
                                                                  'style_exists': style_exists,
                                                                  'element_names_exist': element_names_exist,
                                                                  'elements_exist': elements_exist,
                                                                  'pages_exist': pages_exist,
                                                                  'errors': None,
                                                                  })
    
    if request.method == 'POST':
        errors = None
        if 'action' in request.POST: 
            action = request.POST['action']
            print(f'--- action = {action}')
            if action == 'save_params':
                params_form = CoherentImagesV2ParamsForm(request.POST, prefix='params')
                if not params_form.is_valid():
                    errors = params_form.errors
                else:
                    # Get the params from the params_form and save them
                    default_model = params_form.cleaned_data['default_model']
                    params_form.cleaned_data['generate_description_model']
                    generate_description_model0 = params_form.cleaned_data['generate_description_model']
                    example_evaluation_model0 = params_form.cleaned_data['example_evaluation_model']
                    generate_element_names_model0 = params_form.cleaned_data['generate_element_names_model']
                    
                    params = { 'n_expanded_descriptions': params_form.cleaned_data['n_expanded_descriptions'],
                               'n_images_per_description': params_form.cleaned_data['n_images_per_description'],
                               'n_previous_pages': params_form.cleaned_data['n_previous_pages'],
                               'max_description_generation_rounds': params_form.cleaned_data['max_description_generation_rounds'],

                               'ai_checking_of_images': params_form.cleaned_data['ai_checking_of_images'],
                               'text_language': params_form.cleaned_data['text_language'],

                               'page_interpretation_prompt': params_form.cleaned_data['page_interpretation_prompt'],
                               'page_evaluation_prompt': params_form.cleaned_data['page_evaluation_prompt'],

                               'image_generation_model': params_form.cleaned_data['image_generation_model'],

                               'default_model': default_model,
                               'generate_element_names_model': default_model if generate_element_names_model0 == 'default' else generate_element_names_model0,
                               'generate_description_model': default_model if generate_description_model0 == 'default' else generate_description_model0,
                               'example_evaluation_model': default_model if example_evaluation_model0 == 'default' else example_evaluation_model0,
                               }
                    try:
                        clara_project_internal.save_coherent_images_v2_params(params)
                    except ImageGenerationError as e:
                        messages.error(request, f"{e.message}")
                    except Exception as e:
                        messages.error(request, f"Error when trying to save parameters")
                        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
            elif action == 'create_overview':
                try:
                    clara_project_internal.create_overview_document_v2(project)
                    if clara_project_internal.overview_document_v2_exists():
                        messages.success(request, "Overview created")
                    else:
                        messages.error(request, f"Error when trying to create overview")
                except Exception as e:
                        messages.error(request, f"Error when trying to create overview")
                        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
                return redirect('edit_images_v2', project_id=project_id, status='none')
            elif action == 'download_images_zip':
                try:
                    params = {
                        'project_dir': clara_project_internal.coherent_images_v2_project_dir,
                        'title': project.title
                    }
                    zip_bytes = create_images_zipfile(params)

                    # Create an HttpResponse to return the in-memory zip as a download
                    response = HttpResponse(zip_bytes, content_type='application/zip')
                    # You can customize the downloaded filename as you like:
                    filename = f"{project.title}_images.zip".replace(' ', '_')
                    response['Content-Disposition'] = f'attachment; filename="{filename}"'
                    return response
                except Exception as e:
                    messages.error(request, f"Error when trying to create images ZIP")
                    messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
                    return redirect('edit_images_v2', project_id=project_id, status='none')
            elif action == 'delete_v2_element':
                try:
                    deleted_element_text = request.POST.get('deleted_element_text')
                    if _edit_images_v2_trace:
                        print(f'Deleting element: {deleted_element_text}')
                    # Delete the element
                    elements_params = get_element_descriptions_params_from_project_params(params)
                    clara_project_internal.delete_element_v2(elements_params, deleted_element_text)
                    messages.success(request, f'Deleted element: {deleted_element_text}')
                    return redirect('edit_images_v2', project_id=project.id, status='none')
                except Exception as e:
                    messages.error(request, f"Error when trying to delete element")
                    messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
                    return redirect('edit_images_v2', project_id=project.id, status='none')
            elif action == 'delete_v2_page':
                try:
                    deleted_page_number = int(request.POST.get('deleted_page_number'))
                    if _edit_images_v2_trace:
                        print(f'Deleting image information for page: {deleted_page_number}')
                    # Delete 
                    page_params = get_page_params_from_project_params(params)
                    clara_project_internal.delete_page_image_v2(page_params, deleted_page_number)
                    messages.success(request, f'Deleted images and descriptions for page {deleted_page_number}')
                    return redirect('edit_images_v2', project_id=project.id, status='none')
                except Exception as e:
                    messages.error(request, f"Error when trying to delete page images")
                    messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
                    return redirect('edit_images_v2', project_id=project.id, status='none')
            elif action == 'delete_all_page_descriptions_and_images':
                print('Deleting all page images (views)') 
                try:
                    # Delete 
                    page_params = get_page_params_from_project_params(params)
                    clara_project_internal.delete_all_page_images_v2(page_params)
                    messages.success(request, f'Deleted images and descriptions for all pages')
                    return redirect('edit_images_v2', project_id=project.id, status='none')
                except Exception as e:
                    messages.error(request, f"Error when trying to delete all page images")
                    messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
                    return redirect('edit_images_v2', project_id=project.id, status='none')
            elif action == 'save_background_advice':
                background_advice_text = request.POST.get('background_advice_text', '').strip()
                print(f'background_advice_text read = "{background_advice_text}"')
                clara_project_internal.set_background_advice_v2(background_advice_text)
                messages.success(request, f'Saved background advice')
                return redirect('edit_images_v2', project_id=project.id, status='none')
            elif action in ( 'save_style_advice', 'create_style_description_and_image'):
                style_formset = ImageFormSetV2(request.POST, request.FILES, prefix='style')
                if not style_formset.is_valid():
                    errors = style_formset.errors
                else:
                    # If we have a style image line, save the advice
                    if len(style_formset) != 0:
                        form = style_formset[0]
                        style_advice = form.cleaned_data.get('advice')
                        style_data[0]['advice'] = style_advice
                        clara_project_internal.set_style_advice_v2(style_advice)
            elif action in ( 'save_element_advice', 'create_element_descriptions_and_images'):
                element_formset = ImageFormSetV2(request.POST, prefix='elements')
                if not element_formset.is_valid():
                    errors = element_formset.errors
                else:
                    # Go through the element items in the form.
                    # Collect material to save
                    for i in range(0, len(element_formset)):
                        form = element_formset[i]
                        element_text = form.cleaned_data['element_text']
                        advice = form.cleaned_data['advice']
                        clara_project_internal.set_element_advice_v2(advice, element_text)
            elif action == 'save_page_texts':
                page_formset = ImageFormSetV2(request.POST, request.FILES, prefix='pages')
                if not page_formset.is_valid():
                    errors = page_formset.errors
                else:
                    # Go through the page items in the form.
                    # Collect material to save 
                    
                    new_plain_texts = []
                    new_segmented_texts = []
                    new_translated_texts = []
                    new_mwe_texts = []
                    new_lemma_texts = []
                    new_gloss_texts = []
                    
                    for i in range(0, len(page_formset)):
                        form = page_formset[i]
                        page_number = i + 1
                        advice = form.cleaned_data['advice']
                        clara_project_internal.set_page_advice_v2(advice, page_number)

                        new_plain_texts.append(form.cleaned_data['page_text'])
                        new_segmented_texts.append(form.cleaned_data['segmented_text'])
                        new_translated_texts.append(form.cleaned_data['translated_text'])
                        new_mwe_texts.append(form.cleaned_data['mwe_text'])
                        new_lemma_texts.append(form.cleaned_data['lemma_text'])
                        new_gloss_texts.append(form.cleaned_data['gloss_text'])
                                    
                    # Save the texts back to the project
                    try:
                        types_and_texts = { 'plain': new_plain_texts,
                                            'segmented': new_segmented_texts,
                                            'translated': new_translated_texts,
                                            'mwe': new_mwe_texts,
                                            'lemma': new_lemma_texts,
                                            'gloss': new_gloss_texts }
                        # First try saving without the option of using the AI
                        api_calls = clara_project_internal.save_page_texts_multiple(types_and_texts, user=username, can_use_ai=False, config_info=config_info)
                        store_api_calls(api_calls, project, project.user, 'correct')
                    except ( InternalisationError, MWEError ) as e:
                        if not can_use_ai:
                            messages.error(request, f"There appears to be an inconsistency. Error details: {e.message}")
                            return redirect('edit_images_v2', project_id=project_id, status='none')
                        else:
                            # There was some kind of inconsistency, so now try doing it again using the AI.
                            task_type = f'correct_syntax'
                            callback, report_id = make_asynch_callback_and_report_id(request, task_type)

                            print(f'--- About to start syntax correction task')
                            async_task(save_page_texts_multiple, project, clara_project_internal, types_and_texts, username,
                                       config_info=config_info, callback=callback)
                            print(f'--- Started syntax correction task')
                            #Redirect to the monitor view, passing the project ID and report ID as parameters
                            return redirect('save_page_texts_multiple_monitor', project_id, report_id)

            # If we have errors, pass them to the template and return
            if errors:
                params_form = CoherentImagesV2ParamsForm(initial=params, prefix='params')
                page_formset = ImageFormSetV2(initial=page_data, prefix='pages')
                element_formset = ImageFormSetV2(initial=element_data, prefix='elements')
                style_formset = ImageFormSetV2(initial=style_data, prefix='style')
                return render(request, 'clara_app/edit_images_v2.html', {
                    'params_form': params_form,
                    'background_advice': background_advice,
                    'page_formset': page_formset,
                    'element_formset': element_formset,
                    'style_formset': style_formset,
                    'project': project,
                    'clara_version': clara_version,
                    'overview_file_exists': overview_file_exists,
                    'style_exists': style_exists,
                    'element_names_exist': element_names_exist,
                    'elements_exist': elements_exist,
                    'pages_exist': pages_exist,
                    'errors': errors,
                })

            # We should have saved everything and have translations, so we can get the story data from the project
            try:
                numbered_page_list = numbered_page_list_for_coherent_images(project, clara_project_internal)
                clara_project_internal.set_story_data_from_numbered_page_list_v2(numbered_page_list)
            except Exception as e:
                messages.error(request, f"Error when trying to update story data")
                messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
                return redirect('edit_images_v2', project_id=project.id, status='none')
                                                                                     
            # If we've got one of the AI actions, again we should have everything saved so we can execute it as an async and return
            if action in actions_requiring_openai:
                if not can_use_ai:
                    messages.error(request, f"Sorry, you need a registered OpenAI API key or money in your account to create images")
                    return redirect('edit_images_v2', project_id=project_id, status='none')

                if project.use_translation_for_images:
                    pages_with_missing_text = clara_project_internal.pages_with_missing_story_text_v2()
                    if pages_with_missing_text:
                        pages_with_missing_text_str = ', '.join([str(page_number) for page_number in pages_with_missing_text])
                        messages.error(request, f"Cannot create images.")
                        messages.error(request, f"Project is marked as using translations to create images, but pages are missing translations: {pages_with_missing_text_str}")
                        return redirect('edit_images_v2', project_id=project_id, status='none')

                callback, report_id = make_asynch_callback_and_report_id(request, action)

                if action == 'create_style_description_and_image':
                    async_task(create_style_description_and_image, project, clara_project_internal, params, callback=callback)
                elif action == 'add_v2_element':
                    try:
                        new_element_text = request.POST.get('new_element_text').strip()
                    except Exception as e:
                        messages.error(request, f"Error when trying to get new element name")
                        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
                        return redirect('edit_images_v2', project_id=project.id, status='none')
                    if not new_element_text:
                        messages.error(request, f"Error, new element name not provided")
                        return redirect('edit_images_v2', project_id=project.id, status='none')
                    async_task(add_v2_element, new_element_text, project, clara_project_internal, params, callback=callback)
                elif action == 'create_element_names':
                    async_task(create_element_names, project, clara_project_internal, params, callback=callback)
                elif action == 'create_element_descriptions_and_images':
                    elements_to_generate = clara_project_internal.get_elements_texts_with_no_image_v2()
                    if _edit_images_v2_trace:
                        print(f'Generating images for elements: {elements_to_generate}')
                    async_task(create_element_descriptions_and_images, project, clara_project_internal, params, elements_to_generate, callback=callback)
                elif action == 'create_page_descriptions_and_images':
                    pages_to_generate = clara_project_internal.get_pages_with_no_image_v2()
                    try:
                        number_of_pages = int(request.POST.get('number_of_pages_to_generate'))
                    except Exception:
                        number_of_pages = 'all'
                    if number_of_pages != 'all':
                        pages_to_generate = pages_to_generate[:number_of_pages]
                    if _edit_images_v2_trace:
                        print(f'Generating images for pages: {pages_to_generate}')
                    async_task(create_page_descriptions_and_images, project, clara_project_internal, params, pages_to_generate, callback=callback)

                print(f'--- Started async "{action}" task')
                #Redirect to the monitor view, passing the task ID and report ID as parameters
                return redirect('coherent_images_v2_monitor', project_id, report_id)
            else:
                # We had a save action
                params_for_project_dir = { 'project_dir': project_dir }
     
                if action == 'save_params':
                    messages.success(request, "Parameter data updated")
                elif action == 'save_style_advice':
                    messages.success(request, "Style advice updated")
                elif action == 'save_element_advice':
                    messages.success(request, "Element advice updated")
                elif action == 'save_page_texts':
                    messages.success(request, "Page text updated")
                return redirect('edit_images_v2', project_id=project_id, status='none')
            
    else:
        # GET
        params_form = CoherentImagesV2ParamsForm(initial=params, prefix='params')
        page_formset = ImageFormSetV2(initial=page_data, prefix='pages')
        element_formset = ImageFormSetV2(initial=element_data, prefix='elements')
        style_formset = ImageFormSetV2(initial=style_data, prefix='style')

        #pprint.pprint(style_data)
        
        # If 'status' is something we got after returning from an async call, display a suitable message
        if status == 'finished':
            messages.success(request, "Image task successfully completed")
        elif status == 'error':
            messages.error(request, "Something went wrong when performing this image task. Look at the 'Recent task updates' view for further information.")
        elif status == 'finished_syntax_correction':
            messages.success(request, "There was an error in the syntax. This has been corrected and the text has been saved")
        elif status == 'error_syntax_correction':
            messages.error(request, "There was an error in the syntax, and something went wrong when trying to fix it. Look at the 'Recent task updates' view for further information.")

    return render(request, 'clara_app/edit_images_v2.html', {'params_form': params_form,
                                                             'background_advice': background_advice,
                                                             'style_formset': style_formset,
                                                             'element_formset': element_formset,
                                                             'page_formset': page_formset,
                                                             'project': project,
                                                             'clara_version': clara_version,
                                                             'overview_file_exists': overview_file_exists,
                                                             'style_exists': style_exists,
                                                             'element_names_exist': element_names_exist,
                                                             'elements_exist': elements_exist,
                                                             'pages_exist': pages_exist,
                                                             'errors': []})

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
def execute_community_requests_for_page_monitor(request, project_id, report_id, page_number):
    project = get_object_or_404(CLARAProject, pk=project_id)
    
    return render(request, 'clara_app/execute_community_requests_for_page_monitor.html',
                  {'project_id': project_id, 'project': project, 'report_id': report_id, 'page_number': page_number})

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

# Async function
def save_page_texts_multiple(project, clara_project_internal, types_and_texts, username, config_info={}, callback=None):
    try:
        api_calls = clara_project_internal.save_page_texts_multiple(types_and_texts, user=username, can_use_ai=True, config_info=config_info, callback=callback)
        store_api_calls(api_calls, project, project.user, 'correct')
        post_task_update(callback, f'--- Corrected texts')
        post_task_update(callback, f"finished")

    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")

@login_required
@user_has_a_project_role
def save_page_texts_multiple_status(request, project_id, report_id):
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
def save_page_texts_multiple_monitor(request, project_id, report_id):
    project = get_object_or_404(CLARAProject, pk=project_id)

    return render(request, 'clara_app/save_page_texts_multiple_monitor.html',
                  {'project_id': project_id, 'project': project, 'report_id': report_id})

def create_style_description_and_image(project, clara_project_internal, params, callback=None):
    try:
        style_params = get_style_params_from_project_params(params)
        cost_dict = clara_project_internal.create_style_description_and_image_v2(style_params, callback=callback)
        store_cost_dict(cost_dict, project, project.user)
        content_dir = relative_style_directory(style_params)
        if content_dir_shows_only_content_policy_violations(content_dir, style_params):
            post_task_update(callback, f"Error: policy content violation when creating style")
            post_task_update(callback, f"error")
        else:
            post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Error when creating style")
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")

def create_element_names(project, clara_project_internal, params, callback=None):
    try:
        element_params = get_element_names_params_from_project_params(params)
        cost_dict = clara_project_internal.create_element_names_v2(element_params, callback=callback)
        store_cost_dict(cost_dict, project, project.user)
        post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Error when creating element names")
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")

def add_v2_element(new_element_text, project, clara_project_internal, params, callback=None):
    try:
        elements_params = get_element_descriptions_params_from_project_params(params)
        cost_dict = clara_project_internal.add_element_v2(elements_params, new_element_text, callback=callback)
        store_cost_dict(cost_dict, project, project.user)
        content_dir = relative_element_directory(new_element_text, elements_params)
        if file_exists(project_pathname(clara_project_internal.coherent_images_v2_project_dir, get_element_image(new_element_text, elements_params))):
            post_task_update(callback, f"Created description and image for '{new_element_text}'")
            post_task_update(callback, f"finished")
        elif content_dir_shows_only_content_policy_violations(content_dir, elements_params):
            post_task_update(callback, f"Error: policy content violation when creating new element")
            post_task_update(callback, f"error")
        else:
            post_task_update(callback, f"Something went wrong when creating description and image for '{new_element_text}'")
            post_task_update(callback, f"error")                   
    except Exception as e:
        post_task_update(callback, f"Error when trying to add element")
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")

# Async functions for coherent images v2

def create_element_descriptions_and_images(project, clara_project_internal, params, elements_to_generate, callback=None):
    try:
        element_params = get_element_descriptions_params_from_project_params(params)
        element_params['elements_to_generate'] = elements_to_generate
        cost_dict = clara_project_internal.create_element_descriptions_and_images_v2(element_params, callback=callback)
        store_cost_dict(cost_dict, project, project.user)
        bad_elements = get_elements_with_content_violations(elements_to_generate, element_params)
        if bad_elements:
            bad_elements_str = ", ".join(bad_elements)
            post_task_update(callback, f"Error: policy content violation when creating elements: {bad_elements_str}")
            post_task_update(callback, f"error")
        else:
            post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Error when creating element descriptions and images")
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")

def get_elements_with_content_violations(element_texts, params):
    bad_elements = []
    for element_text in element_texts:
        content_dir = relative_element_directory(element_text, params)
        if content_dir_shows_only_content_policy_violations(content_dir, params):
            bad_elements.append(element_text)
    return bad_elements

def create_page_descriptions_and_images(project, clara_project_internal, params, pages_to_generate, callback=None):
    try:
        page_params = get_page_params_from_project_params(params)
        page_params['pages_to_generate'] = pages_to_generate
        cost_dict = clara_project_internal.create_page_descriptions_and_images_v2(page_params, project.id, callback=callback)
        store_cost_dict(cost_dict, project, project.user)
        bad_pages = get_pages_with_content_violations(pages_to_generate, page_params)
        if bad_pages:
            bad_pages_str = ", ".join([ str(bad_page) for bad_page in bad_pages ])
            post_task_update(callback, f"Error: policy content violation when creating page: {bad_pages_str}")
            post_task_update(callback, f"error")
        else:
            post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Error when creating page images")
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")

def get_pages_with_content_violations(page_numbers, params):
    bad_pages = []
    for page_number in page_numbers:
        content_dir = relative_page_directory(page_number, params)
        if content_dir_shows_only_content_policy_violations(content_dir, params):
            bad_pages.append(page_number)
    return bad_pages

def create_variant_images(project, clara_project_internal, params, content_type, content_identifier, alternate_image_id, callback=None):
    if content_type != 'page':
        post_task_update(callback, f"Cannot yet create variant images for {content_type}")
        post_task_update(callback, f"error")
    else:
        try:
            page_params = get_page_params_from_project_params(params)
            page = content_identifier
            cost_dict = clara_project_internal.create_variant_images_for_page_v2(page_params, page, alternate_image_id, callback=callback)
            store_cost_dict(cost_dict, project, project.user)
            post_task_update(callback, f"finished")
        except Exception as e:
            post_task_update(callback, f"Error when creating variant page images")
            post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
            post_task_update(callback, f"error")

@login_required
@user_has_a_project_role
def coherent_images_v2_status(request, project_id, report_id):
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
def coherent_images_v2_monitor(request, project_id, report_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    
    return render(request, 'clara_app/coherent_images_v2_monitor.html',
                  {'project_id': project_id, 'project': project, 'report_id': report_id})

def access_archived_images(request, project_id, image_name):
    project = get_object_or_404(CLARAProject, id=project_id)
    image_repo = ImageRepositoryORM()
    archived_images = image_repo.get_archived_images(project.internal_id, image_name)
    
    return render(request, 'clara_app/access_archived_images.html', {
        'project': project,
        'image_name': image_name,
        'archived_images': archived_images,
    })

def restore_image(request, project_id, archived_image_id):
    if request.method == "POST":
        project = get_object_or_404(CLARAProject, id=project_id)
        image_repo = ImageRepositoryORM()
        image_repo.restore_image(project.internal_id, archived_image_id)
        return redirect('edit_images', project_id=project_id, dall_e_3_image_status='no_image')
    else:
        return HttpResponseNotAllowed(['POST'])

def delete_archive_image(request, project_id, archived_image_id):
    if request.method == "POST":
        project = get_object_or_404(CLARAProject, id=project_id)
        image_repo = ImageRepositoryORM()
        image_repo.delete_archived_image(project.internal_id, archived_image_id)
        return redirect('access_archived_images', project_id=project_id, image_name=request.POST.get('image_name'))
    else:
        return HttpResponseNotAllowed(['POST'])

def create_and_add_dall_e_3_image_for_whole_text(project_id, advice_prompt=None, callback=None):
    try:
        project = get_object_or_404(CLARAProject, pk=project_id)
        clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
        text = clara_project_internal.load_text_version('plain')
        text_language = project.l2
        user = project.user
        config_info = get_user_config(user)
        prompt = f"""Please read the following (it is written in {text_language.capitalize()}) and create an image to go with it:

{text}
"""
        if project.l2 != 'english':
            prompt += f"Since the above is written in {text_language.capitalize()}), do not include English text in the image."
        else:
            prompt += "Do not include text in the image unless that is specifically necessary for some reason."
            
        if advice_prompt:
            prompt += f"""
When generating the image, keep the following advice in mind:

{advice_prompt}"""
        temp_dir = tempfile.mkdtemp()
        tmp_image_file = os.path.join(temp_dir, 'image_for_whole_text.jpg')
        
        post_task_update(callback, f"--- Creating a new DALL-E-3 image based on the whole project text")
        api_calls = call_chat_gpt4_image(prompt, tmp_image_file, config_info=config_info, callback=callback)
        post_task_update(callback, f"--- Image created: {tmp_image_file}")

        image_name = 'DALLE-E-3-Image-For-Whole-Text'
        clara_project_internal.add_project_image(image_name, tmp_image_file, 
                                                 associated_text='', associated_areas='',
                                                 page=1, position='top')
        post_task_update(callback, f"--- Image stored")
        post_task_update(callback, f"finished")
        store_api_calls(api_calls, project, project.user, 'image')
        return True
    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")
        return False
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
 
# Create the image using DALL-E-3, interpret it using GPT-4o, then store on notional page 0
def create_and_add_dall_e_3_image_for_style(project_id, prompt, callback=None):
    try:
        project = get_object_or_404(CLARAProject, pk=project_id)
        clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
        user = project.user
        config_info = get_user_config(user)
        temp_dir = tempfile.mkdtemp()
        tmp_image_file = os.path.join(temp_dir, 'image_for_style_prompt.jpg')
        
        post_task_update(callback, f"--- Creating a new DALL-E-3 image to define the style")
        api_calls_generate = call_chat_gpt4_image(prompt, tmp_image_file, config_info=config_info, callback=callback)
        store_api_calls(api_calls_generate, project, project.user, 'image')
        post_task_update(callback, f"--- Image created: {tmp_image_file}")

        style_interpretation_prompt = """Produce a detailed description of this image's style.
The description you give will be used to create a set of thematically related images with a similar style,
so it is important to focus on the style, not describing the content more than absolutely necessary.
"""
        post_task_update(callback, f"--- Creating a description of the style")
        api_call_interpret = call_chat_gpt4_interpret_image(style_interpretation_prompt, tmp_image_file,
                                                            config_info=config_info, callback=callback)
        store_api_calls([ api_call_interpret ], project, project.user, 'image')
        style_description = api_call_interpret.response
        post_task_update(callback, f"--- Description created: {style_description}")

        image_name = 'Style image'
        clara_project_internal.add_project_image(image_name, tmp_image_file, 
                                                 associated_text='', associated_areas='',
                                                 page=0, position='top',
                                                 style_description=style_description,
                                                 user_prompt=prompt)
        post_task_update(callback, f"--- Image stored")
        post_task_update(callback, f"finished")
        return True
    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")
        return False
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def numbered_page_list_for_coherent_images(project, clara_project_internal):
    if project.use_translation_for_images:
        translated_text = clara_project_internal.load_text_version_or_null("translated")
        if translated_text:
            translated_text_object = internalize_text(translated_text, project.l2, project.l1, "translated")
            numbered_page_list = translated_text_object.to_numbered_page_list(translated=True)
        else:
            segmented_text = clara_project_internal.load_text_version("segmented_with_title")
            segmented_text_object = internalize_text(segmented_text, project.l2, project.l1, "segmented")
            numbered_page_list = segmented_text_object.to_numbered_page_list()
            for item in numbered_page_list:
                item['original_page_text'] = item['text']
                item['text'] = ''
    else:
        segmented_text = clara_project_internal.load_text_version("segmented_with_title")
        segmented_text_object = internalize_text(segmented_text, project.l2, project.l1, "segmented")
        numbered_page_list = segmented_text_object.to_numbered_page_list()
        
    return numbered_page_list

# Create the description variables for the text
def generate_image_descriptions(project_id, callback=None):
    try:
        project = get_object_or_404(CLARAProject, pk=project_id)
        clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
        user = project.user
        config_info = get_user_config(user)

        numbered_page_list = numbered_page_list_for_coherent_images(project, clara_project_internal)
        numbered_page_list_text = json.dumps(numbered_page_list)
        prompt = f"""
        You are to perform the first step in a process that will guide DALL-E-3 and GPT-4o in creating a set of
        illustrations for a text, provided in JSON form, which has been divided into numbered pages. In this
        step, you will analyse the text and create a list of items that are referred to more than
        once and whose appearance needs to be kept consistent across illustrations. Typical examples of such
        items are characters in a story (e.g. people, animals) and settings (e.g. buildings, rooms, background scenery).
        In a later stage of the process, we will use DALL-E-3 to create images, and then use GPT-4o to create
        a description for each item the first time it appears. These descriptions will then be inserted in later calls
        to DALL-E-3.

        Each item will be represented as a pair consisting of an identifier (a "description variable") and a
        phrase saying what the variable refers to (an "explanation"), in the format

        {{
            "description_variable": <variable>,
            "explanation": <explanation>
        }},

        The "explanations" will later be used to create instructions of the form

        "Depict <explanation> according to this description: <value of description_variable>"

        Write out the list of pairs in JSON form.

        Here is a simple example:

        Input:

        [
          {{
            "page": 1,
            "text": "Once upon a time, in a faraway kingdom, there lived a brave princess named Elara."
          }},
          {{
            "page": 2,
            "text": "Elara loved exploring the lush forest that surrounded her castle."
          }},
          {{
            "page": 3,
            "text": "One day, when she was out in the forest, Elana met a lost dragon called Ember."
          }},
          {{
            "page": 4,
            "text": "Elana and Ember soon became good friends and were always together."
          }}
        ]

        Output:

        [
          {{
            "description_variable": "Elara-description",
            "explanation": "Princess Elara"
          }},
          {{
            "description_variable": "forest-description",
            "explanation": "the forest"
          }},
          {{
            "description_variable": "Ember-description",
            "explanation": "Ember the dragon"
          }},
          
        ]

        Here is the JSON representation of the text:

        {numbered_page_list_text}

        Only write out the JSON representation of the sequence of ( description variables, explanation ) pairs, since the result will be read by a Python script.
        """
        n_attempts = 0
        limit = int(config.get('chatgpt4_annotation', 'retry_limit'))
        while n_attempts < limit:
            n_attempts += 1
            post_task_update(callback, f'--- Calling ChatGPT-4 (attempt #{n_attempts}) to create description variables')
            try: 
                api_call = call_chat_gpt4(prompt, config_info=config_info, callback=callback)
                store_api_calls([api_call], project, user, 'image_description_generation')
                response = api_call.response
                response_object = interpret_chat_gpt4_response_as_json(response, object_type='list', callback=callback)
                if not isinstance(response_object, list):
                    raise ValueError('Response is not a JSON list')
                if not is_well_formed_description_list(response_object, callback=callback):
                    raise ValueError(f'Error: response {response_object} is not a well-formed description list')
                clara_project_internal.remove_all_project_image_descriptions(callback=callback)
                for description in response_object:
                    description_variable = description['description_variable']
                    explanation = description['explanation']
                    clara_project_internal.add_project_image_description(description_variable, explanation, callback=callback)
                post_task_update(callback, "finished")
                return True
            except Exception as e:
                post_task_update(callback, f'Error: {str(e)}')
        post_task_update(callback, f'*** Giving up, have tried sending this to ChatGPT-4 {limit} times')
        post_task_update(callback, "error")
        return False
    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, "error")
        return False

def is_well_formed_description_list(description_list, callback=None):
    try:
        for item in description_list:
            if not isinstance(item, dict):
                raise ValueError(f'Item {item} is not a dict')
            if 'description_variable' not in item or 'explanation' not in item:
                raise ValueError(f'Item {item} does not contain the fields "description_variable" and "explanation"')
        return True
    except ValueError as ve:
        post_task_update(callback, f'Error: {ve}')
        post_task_update(callback, "error")
        return False

def create_image_request_sequence(project_id, callback=None):
    try:
        project = get_object_or_404(CLARAProject, pk=project_id)
        clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
        user = project.user
        config_info = get_user_config(user)
        
        numbered_page_list = numbered_page_list_for_coherent_images(project, clara_project_internal)
        numbered_page_list_text = json.dumps(numbered_page_list)

        #print(f'numbered_page_list')
        #pprint.pprint(numbered_page_list)

        descriptions = clara_project_internal.get_all_project_image_descriptions(formatting='plain_lists', callback=callback)
        descriptions_text = json.dumps(descriptions)

        prompt = f"""
        You are to write a set of requests, in JSON form, that will guide DALL-E-3 and GPT-4o in creating a set of
        illustrations for a text, also provided in JSON form, which has been divided into numbered pages.

        To maintain visual consistency, a previous processing step has extracted a set of "description_variables"
        which refer to items (characters, objects, locations etc), which may occur in more than one image.

        Take all description variables from the list provided. Each description variable is paired with a brief
        explanation of its purpose, in the format

        {{
            "description_variable": <variable>,
            "explanation": <explanation>
        }},

        Each description variable will add a piece of text to a  DALL-E-3 prompt of the form

        "Depict <explanation> according to this description: <value of description_variable>"
        
        A DALL-E-3 image-generation request to create the image on page <page-number> of the text will be of the form:

        {{
          "request_type": "image-generation",
          "page": <page-number>,
          "prompt": "<main-request-text>",
          "description_variables": <list-of-description-variables>
        }}

        where <list-of-description-variables> is a list of "description_variables" 
        holding relevant descriptions created by previously executed GPT-4o image understanding requests.

        A GPT-4o image-understanding request to extract visual information from the previously generated image on page <page-number>
        of the text and store it in the "description_variable" <variable-name> will be of the form:

        {{
          "request_type": "image-understanding",
          "page": <page-number>,
          "prompt": "<request-text>",
          "description_variable": "<variable-name>"
        }}

        When generating the image requests, ensure that the description_variables from relevant image-understanding requests are included in the prompts
        for subsequent image-generation requests. This ensures visual consistency throughout the story.

        Here is a simple example:

        Text:

        [
          {{
            "page": 1,
            "text": "Once upon a time, in a faraway kingdom, there lived a brave princess named Elara."
          }},
          {{
            "page": 2,
            "text": "Elara loved exploring the lush forest that surrounded her castle."
          }},
          {{
            "page": 3,
            "text": "One day, when she was out in the forest, Elara met a lost dragon called Ember."
          }}
        ]

        Description variables:

        [
          {{
            "description_variable": "Elara-description",
            "explanation": "Princess Elara"
          }},
          {{
            "description_variable": "forest-description",
            "explanation": "the forest"
          }}

        ]

        Output:

        [
          {{
            "request_type": "image-generation",
            "page": 1,
            "prompt": "An image of a brave princess named Elara standing in front of a grand castle, with the lush forest in the background.
            Elara is wearing a simple yet elegant dress, and she has a determined look on her face."
          }},
          {{
            "request_type": "image-understanding",
            "page": 1,
            "prompt": "Analyze this image depicting Princess Elara. Provide a comprehensive description that focuses on her appearance and attire.
            Detail her apparent age, ethnicity, facial features, hair style and colour, body build, clothing style, and overall demeanor. If it
            is not easy to extract this information from the image, e.g. regarding ethnicity, make a plausible decision.
            A detailed description is crucial for ensuring consistency in her portrayal across all subsequent images in the series.
            Use precise, descriptive language to capture her essence, as this information will directly influence the generation of future images.",
            "description_variable": "Elara-description"
          }},
          {{
            "request_type": "image-generation",
            "page": 2,
            "prompt": "An image of Princess Elara exploring the forest, surrounded by tall trees, colorful flowers, and playful animals like rabbits and birds.",
            "description_variables": [ "Elara-description" ]
          }},
          {{
            "request_type": "image-understanding",
            "page": 2,
            "prompt": "Analyze this image depicting Princess Elara in the forest. Provide a comprehensive description of the forest.
            Detail the types, sizes and general appearance of trees and other vegetation, the quality of the lighting, and
            kinds of wildlife (animals, birds). If it is not easy to extract this information from the image, make a plausible decision.
            A detailed description is crucial for ensuring consistency across all subsequent images in the series.
            Use precise, descriptive language to capture the essence of the forest, as this information will directly influence the generation of future images.",
            "description_variable": "forest-description"
          }},
          {{
            "request_type": "image-generation",
            "page": 3,
            "prompt": "An image of Princess Elara and the dragon Ember in the forest. They have just met. Ember looks sad and lost, Elara looks kind
            and sympathetic.",
            "description_variables": [ "Elara-description", "forest-description" ]
          }}
        ]

        Here is the JSON representation of the text:

        {numbered_page_list_text}

        Here are the description variables you can use:

        {descriptions_text}

        Only write out the JSON representation of the sequence of image requests, since the result will be read by a Python script.
        """
        n_attempts = 0
        limit = int(config.get('chatgpt4_annotation', 'retry_limit'))
        while n_attempts < limit:
            n_attempts += 1
            post_task_update(callback, f'--- Calling ChatGPT-4 (attempt #{n_attempts}) to create image request sequence')
            try:
                api_call = call_chat_gpt4(prompt, config_info=config_info, callback=callback)
                store_api_calls([api_call], project, user, 'image_request_sequence')
                response = api_call.response

                sequence = interpret_chat_gpt4_response_as_json(response, object_type='list', callback=callback)
                check_well_formed_image_request_sequence(sequence, numbered_page_list, callback=callback)
                corrected_sequence = check_and_correct_initialization_in_image_request_sequence(sequence, project_id, user, config_info, callback=callback)
                
                clara_project_internal.remove_all_project_images_except_style_images(callback=callback)
                print(f'--- Saving image request sequence with {len(corrected_sequence)} records')
                for req in corrected_sequence:
                    request_type = req['request_type']
                    user_prompt = req['prompt']
                    page = req['page']
                    description_variable = req.get('description_variable', '')
                    position = req.get('position', 'bottom')
                    description_variables = req.get('description_variables', [])
                    image_name = f'image_{page}_{position}' if request_type == 'image-generation' else f'get_{description_variable}'
                    image_file_path = None
                    clara_project_internal.add_project_image(image_name, image_file_path,
                                                             page=page, position=position,
                                                             user_prompt=user_prompt,
                                                             request_type=request_type,
                                                             description_variable=description_variable,
                                                             description_variables=description_variables,
                                                             callback=callback)
                post_task_update(callback, "finished")
                return True
            except Exception as e:
                post_task_update(callback, f'Error: {str(e)}')
        post_task_update(callback, f'*** Giving up, have tried sending this to ChatGPT-4 {limit} times')
        post_task_update(callback, "error")
        return False
    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, "error")
        return False

def check_well_formed_image_request_sequence(requests, numbered_page_list, callback=None):
    if not isinstance(requests, list):
        post_task_update(callback, f'Image request sequence is not a list: {requests}')
        raise ValueError('Bad image request sequence')
    
    for req in requests:
        if not (isinstance(req, dict) and 'request_type' in req and req['request_type'] in ('image-generation', 'image-understanding')):
            post_task_update(callback, f'Image request sequence item is not a dict containing a valid "request_type" field: {req}')
            raise ValueError('Bad image request sequence')
        
        if req['request_type'] == 'image-generation':
            if not ('prompt' in req and 'page' in req):
                post_task_update(callback, f'Image request sequence item of type "image-generation" does not contain "prompt" and "page" fields: {req}')
                raise ValueError('Bad image request sequence')
        
        if req['request_type'] == 'image-understanding':
            if not ('prompt' in req and 'page' in req and 'description_variable' in req):
                post_task_update(callback, f'Image request sequence item of type "image-understanding" does not contain "prompt", "page", and "description_variable" fields: {req}')
                raise ValueError('Bad image request sequence')

    page_numbers = [ item['page'] for item in numbered_page_list ]
    page_numbers_in_generation_requests = [ req['page'] for req in requests if req['request_type'] == 'image-generation' ]

    no_generation_page_numbers = [ page_number for page_number in page_numbers
                                   if not page_number in page_numbers_in_generation_requests and
                                   # We expect nothing to be generated for an empty page
                                   'text' in numbered_page_list[page_number - 1] and
                                   numbered_page_list[page_number - 1]['text'].strip() ]

    if no_generation_page_numbers:
        missing_pages_text = ', '.join([ str(page_number) for page_number in no_generation_page_numbers ])
        post_task_update(callback, f'Error: no image generation requests for page(s): {missing_pages_text}')
        raise ValueError('Bad image request sequence')
    else:
        page_numbers_text = ', '.join([ str(page_number) for page_number in page_numbers ])
        post_task_update(callback, f'--- Image generation requests found for pages: {page_numbers_text}')

    return True

def check_and_correct_initialization_in_image_request_sequence(sequence, project_id, user, config_info, callback=None):
    initialized_vars = set()
    corrected_sequence = []

    for i, req in enumerate(sequence):
        if req["request_type"] == "image-understanding":
            initialized_vars.add(req["description_variable"])
        elif req["request_type"] == "image-generation":
            # Fill in description_variables field if missing
            if not "description_variables" in req:
                req["description_variables"] = []
            # Only keep description variables from previous image-understanding steps
            req["description_variables"] = [var for var in req["description_variables"] if var in initialized_vars]

        corrected_sequence.append(req)

    return corrected_sequence

# Go through the generation requests, creating and storing the images.

def create_and_add_coherent_dall_e_3_images(project_id, requests, callback=None):
    try:
        project = get_object_or_404(CLARAProject, pk=project_id)
        clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
        user = project.user
        config_info = get_user_config(user)
        temp_dir = tempfile.mkdtemp()
        
        for request in requests:
            n_tries = 0
            retry_limit = int(config.get('dall_e_3', 'retry_limit'))
            request_succeeded = False
            
            while not request_succeeded and n_tries <= retry_limit:
                try:
                    request_type = request['request_type']
                    image_name = request['image_name']
                    page = request['page']
                    position = request['position']
                    user_prompt = request['user_prompt']
                    content_description = request['content_description']
                    style_description = request['style_description']
                    current_image = request['current_image']
                    description_variable = request['description_variable']
                    description_variables = request['description_variables']

                    if request_type not in ('image-generation', 'image-understanding'):
                        post_task_update(callback, f"*** Error: unknown request type in image generation sequence: {request_type}")
                        post_task_update(callback, "error")
                        return False

                    if request_type == 'image-generation':
                        full_prompt = f"""Create an image based on the following request: {user_prompt}

Make the style of the image consistent with the style of the previously generated image described here: {style_description}
        """
                        for description_variable in description_variables:
                            image_description = clara_project_internal.get_project_image_description(description_variable, callback=callback)
                            description_text = clara_project_internal.get_image_understanding_result(description_variable, callback=callback)
                            if image_description and description_text:
                                explanation_text = image_description.explanation
                                full_prompt += f"\n\nDepict {explanation_text} according to this description: {description_text}"

                        tmp_image_file = os.path.join(temp_dir, f'{image_name}_{page}_{position}.jpg')
                        post_task_update(callback, f"--- Creating DALL-E-3 image: name {image_name}, page {page}, position {position}")
                        api_calls_generate = call_chat_gpt4_image(full_prompt, tmp_image_file, config_info=config_info, callback=callback)
                        store_api_calls(api_calls_generate, project, project.user, 'image')
                        post_task_update(callback, f"--- Image created: {tmp_image_file}")

                        clara_project_internal.add_project_image(image_name, tmp_image_file, keep_file_name=False,
                                                                 associated_text='', associated_areas='',
                                                                 page=page, position=position,
                                                                 user_prompt=user_prompt,
                                                                 description_variables=description_variables,
                                                                 request_type=request_type)
                        post_task_update(callback, f"--- Image stored")
                        request_succeeded = True

                    elif request_type == 'image-understanding':
                        post_task_update(callback, f"--- Creating a description of part of image")
                        generated_image_object = clara_project_internal.get_generated_project_image_by_position(page, position, callback=callback)
                        if not generated_image_object:
                            post_task_update(callback, "error")
                            return False

                        generated_image_file_path = generated_image_object.image_file_path
                        if not file_exists(generated_image_file_path):
                            post_task_update(callback, f"Error: unable to find generated image for page={page}, position={position}")
                            post_task_update(callback, "error")
                            return False
                        api_call_interpret = call_chat_gpt4_interpret_image(user_prompt, generated_image_file_path,
                                                                            config_info=config_info, callback=callback)
                        description = api_call_interpret.response
                        clara_project_internal.store_image_understanding_result(description_variable, description,
                                                                                image_name=image_name, page=page, position=position, user_prompt=user_prompt,
                                                                                callback=callback)
                        post_task_update(callback, f"--- Description created for '{description_variable}': '{description}'")
                        request_succeeded = True

                except Exception as e:
                    post_task_update(callback, f"{request_type} task failed for page = {page}, position = {position}")
                    post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
                    n_tries += 1
            
            if not request_succeeded:
                post_task_update(callback, f"*** Error: giving up on {request_type} task after {retry_limit} unsuccessful attempts")
                post_task_update(callback, "error")
                return False
        
        post_task_update(callback, "finished")
        return True
    
    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, "error")
        return False
    
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
# This is the API endpoint that the JavaScript will poll
@login_required
@user_has_a_project_role
def create_dall_e_3_image_status(request, project_id, report_id):
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
def create_dall_e_3_image_monitor(request, project_id, report_id):
    project = get_object_or_404(CLARAProject, pk=project_id)

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/create_dall_e_3_image_monitor.html',
                  {'project_id': project_id, 'project': project, 'report_id': report_id, 'clara_version': clara_version})
    

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

@login_required
@user_has_a_project_role
def set_format_preferences(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    preferences, created = FormatPreferences.objects.get_or_create(project=project)

    if request.method == 'POST':
        form = FormatPreferencesForm(request.POST, instance=preferences)
        if form.is_valid():
            form.save()
            messages.success(request, "Format preferences updated successfully.")
            return redirect('set_format_preferences', project_id=project_id)
    else:
        form = FormatPreferencesForm(instance=preferences)

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/set_format_preferences.html', {'form': form, 'project': project, 'clara_version': clara_version})

def clara_project_internal_render_text(clara_project_internal, project_id,
                                       audio_type_for_words='tts', audio_type_for_segments='tts',
                                       preferred_tts_engine=None, preferred_tts_voice=None,
                                       human_voice_id=None,
                                       self_contained=False, phonetic=False, callback=None):
    print(f'--- Asynchronous rendering task started: phonetic={phonetic}, self_contained={self_contained}')
    try:
        project = get_object_or_404(CLARAProject, pk=project_id)
        format_preferences_info = FormatPreferences.objects.filter(project=project).first()
        acknowledgements_info = Acknowledgements.objects.filter(project=project).first()
        clara_project_internal.render_text(project_id,
                                           audio_type_for_words=audio_type_for_words, audio_type_for_segments=audio_type_for_segments,
                                           preferred_tts_engine=preferred_tts_engine, preferred_tts_voice=preferred_tts_voice,
                                           human_voice_id=human_voice_id,
                                           format_preferences_info=format_preferences_info,
                                           acknowledgements_info=acknowledgements_info,
                                           self_contained=self_contained, phonetic=phonetic, callback=callback)
        post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")

# Start the async process that will do the rendering
@login_required
@user_has_a_project_role
def render_text_start_normal(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    
    if "gloss" not in clara_project_internal.text_versions or "lemma" not in clara_project_internal.text_versions:
        messages.error(request, "Glossed and lemma-tagged versions of the text must exist to render it.")
        return redirect('project_detail', project_id=project.id)
    
    return render_text_start_phonetic_or_normal(request, project_id, 'normal')

@login_required
@user_has_a_project_role
def render_text_start_phonetic(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    
    if "phonetic" not in clara_project_internal.text_versions:
        messages.error(request, "Phonetic version of the text must exist to render it.")
        return redirect('project_detail', project_id=project.id)
    
    return render_text_start_phonetic_or_normal(request, project_id, 'phonetic')
      
def render_text_start_phonetic_or_normal(request, project_id, phonetic_or_normal):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    clara_version = get_user_config(request.user)['clara_version']

    # Check if human audio info exists for the project and if voice_talent_id is set
    if phonetic_or_normal == 'phonetic':
        human_audio_info = PhoneticHumanAudioInfo.objects.filter(project=project).first()
    else:
        human_audio_info = HumanAudioInfo.objects.filter(project=project).first()
        
    if human_audio_info:
        human_voice_id = human_audio_info.voice_talent_id
        audio_type_for_words = 'human' if human_audio_info.use_for_words else 'tts'
        audio_type_for_segments = 'human' if human_audio_info.use_for_segments else 'tts'
        preferred_tts_engine = human_audio_info.preferred_tts_engine if audio_type_for_segments == 'tts' else None
        preferred_tts_voice = human_audio_info.preferred_tts_voice if audio_type_for_segments == 'tts' else None
    else:
        audio_type_for_words = 'tts'
        audio_type_for_segments = 'tts'
        human_voice_id = None
        preferred_tts_engine = None
        preferred_tts_voice = None

    #print(f'audio_type_for_words = {audio_type_for_words}, audio_type_for_segments = {audio_type_for_segments}, human_voice_id = {human_voice_id}')

    if request.method == 'POST':
        form = RenderTextForm(request.POST)
        if form.is_valid():
            # Create a unique ID to tag messages posted by this task
            task_type = f'render_{phonetic_or_normal}'
            callback, report_id = make_asynch_callback_and_report_id(request, task_type)
        
            # Enqueue the render_text task
            self_contained = True
            try:
                phonetic = True if phonetic_or_normal == 'phonetic' else False
                internalised_text = clara_project_internal.get_internalised_text(phonetic=phonetic)
                task_id = async_task(clara_project_internal_render_text, clara_project_internal, project_id,
                                     audio_type_for_words=audio_type_for_words, audio_type_for_segments=audio_type_for_segments,
                                     preferred_tts_engine=preferred_tts_engine, preferred_tts_voice=preferred_tts_voice,
                                     human_voice_id=human_voice_id, self_contained=self_contained,
                                     phonetic=phonetic, callback=callback)
                print(f'--- Asynchronous rendering task posted: phonetic={phonetic}, self_contained={self_contained}')

                # Redirect to the monitor view, passing the task ID and report ID as parameters
                return redirect('render_text_monitor', project_id, phonetic_or_normal, report_id)
            except MWEError as e:
                messages.error(request, f'{e.message}')
                form = RenderTextForm()
                return render(request, 'clara_app/render_text_start.html', {'form': form, 'project': project, 'clara_version': clara_version})
            except InternalisationError as e:
                messages.error(request, f'{e.message}')
                form = RenderTextForm()
                return render(request, 'clara_app/render_text_start.html', {'form': form, 'project': project, 'clara_version': clara_version})
            except Exception as e:
                messages.error(request, f"An internal error occurred in rendering. Error details: {str(e)}\n{traceback.format_exc()}")
                form = RenderTextForm()
                return render(request, 'clara_app/render_text_start.html', {'form': form, 'project': project, 'clara_version': clara_version})
    else:
        form = RenderTextForm()
        return render(request, 'clara_app/render_text_start.html', {'form': form, 'project': project, 'clara_version': clara_version})

# This is the API endpoint that the JavaScript will poll
@login_required
@user_has_a_project_role
def render_text_status(request, project_id, report_id):
    messages = get_task_updates(report_id)
    print(f'{len(messages)} messages received')
    #if len(messages) != 0:
    #    pprint.pprint(messages)
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
def render_text_monitor(request, project_id, phonetic_or_normal, report_id):
    project = get_object_or_404(CLARAProject, pk=project_id)

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/render_text_monitor.html',
                  {'phonetic_or_normal': phonetic_or_normal, 'report_id': report_id, 'project_id': project_id, 'project': project, 'clara_version': clara_version})

# Display the final result of rendering
@login_required
@user_has_a_project_role
def render_text_complete(request, project_id, phonetic_or_normal, status):
    project = get_object_or_404(CLARAProject, pk=project_id)
    if status == 'error':
        succeeded = False
    else:
        succeeded = True
    
    if succeeded:
        # Specify whether we have a content URL and a zipfile
        content_url = True
        # Put back zipfile later
        #zipfile_url = True
        zipfile_url = None
        # Create the form for registering the project content
        register_form = RegisterAsContentForm()
        messages.success(request, f'Rendered text created')
    else:
        content_url = None
        zipfile_url = None
        register_form = None
        messages.error(request, "Something went wrong when creating the rendered text. Try looking at the 'Recent task updates' view")
        
    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/render_text_complete.html', 
                  {'phonetic_or_normal': phonetic_or_normal,
                   'content_url': content_url, 'zipfile_url': zipfile_url,
                   'project': project, 'register_form': register_form, 'clara_version': clara_version})

@login_required
@user_has_a_project_role
def offer_to_register_content_normal(request, project_id):
    return offer_to_register_content(request, 'normal', project_id)

@login_required
@user_has_a_project_role
def offer_to_register_content_phonetic(request, project_id):
    return offer_to_register_content(request, 'phonetic', project_id)

def offer_to_register_content(request, phonetic_or_normal, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    if phonetic_or_normal == 'normal':
        succeeded = clara_project_internal.rendered_html_exists(project_id)
    else:
        succeeded = clara_project_internal.rendered_phonetic_html_exists(project_id)

    if succeeded:
        # Define URLs for the first page of content and the zip file
        content_url = True
        # Put back zipfile later
        #zipfile_url = True
        zipfile_url = None
        # Create the form for registering the project content
        register_form = RegisterAsContentForm()
        messages.success(request, f'Rendered text found')
    else:
        content_url = None
        zipfile_url = None
        register_form = None
        messages.error(request, "Rendered text not found")

    clara_version = get_user_config(request.user)['clara_version']
        
    return render(request, 'clara_app/render_text_complete.html',
                  {'phonetic_or_normal': phonetic_or_normal,
                   'content_url': content_url, 'zipfile_url': zipfile_url,
                   'project': project, 'register_form': register_form, 'clara_version': clara_version})

# Register content produced by rendering from a project        
@login_required
@user_has_a_project_role
def register_project_content(request, phonetic_or_normal, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)

    if request.method == 'POST':
        form = RegisterAsContentForm(request.POST)
        if form.is_valid() and form.cleaned_data.get('register_as_content'):
            if not user_has_a_named_project_role(request.user, project_id, ['OWNER']):
                raise PermissionDenied("You don't have permission to register a text.")

            # Main processing happens in the helper function, which is shared with simple-C-LARA
            content = register_project_content_helper(project_id, phonetic_or_normal)
            
            # Create an Update record for the update feed
            if content:
                create_update(request.user, 'PUBLISH', content)
            
            return redirect(content.get_absolute_url())

    # If the form was not submitted or was not valid, redirect back to the project detail page.
    return redirect('project_detail', project_id=project.id)

def register_project_content_helper(project_id, phonetic_or_normal):
    try:
        project = get_object_or_404(CLARAProject, pk=project_id)
        clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
        phonetic = True if phonetic_or_normal == 'phonetic' else False

        # Check if human audio info exists for the project and if voice_talent_id is set
        if phonetic_or_normal == 'phonetic':
            human_audio_info = PhoneticHumanAudioInfo.objects.filter(project=project).first()
        else:
            human_audio_info = HumanAudioInfo.objects.filter(project=project).first()
        if human_audio_info:
            human_voice_id = human_audio_info.voice_talent_id
            audio_type_for_words = 'human' if human_audio_info.use_for_words else 'tts'
            audio_type_for_segments = 'human' if human_audio_info.use_for_segments else 'tts'
        else:
            audio_type_for_words = 'tts'
            audio_type_for_segments = 'tts'
            human_voice_id = None

        word_count0 = clara_project_internal.get_word_count(phonetic=phonetic)
        voice0 = clara_project_internal.get_voice(human_voice_id=human_voice_id, 
                                                  audio_type_for_words=audio_type_for_words, 
                                                  audio_type_for_segments=audio_type_for_segments)
        
        # CEFR level and summary are not essential, just continue if they're not available
        try:
            cefr_level0 = clara_project_internal.load_text_version("cefr_level")
        except Exception as e:
            cefr_level0 = None
        try:
            summary0 = clara_project_internal.load_text_version("summary")
        except Exception as e:
            summary0 = None
        word_count = 0 if not word_count0 else word_count0 # Dummy value if real one unavailable
        voice = "Unknown" if not voice0 else voice0 # Dummy value if real one unavailable
        cefr_level = "Unknown" if not cefr_level0 else cefr_level0 # Dummy value if real one unavailable
        summary = "Unknown" if not summary0 else summary0 # Dummy value if real one unavailable

        title = f'{project.title} (phonetic)' if phonetic_or_normal == 'phonetic' else project.title
        
        content, created = Content.objects.get_or_create(
                                project = project,  
                                defaults = {
                                    'title': title,  
                                    'l2': project.l2,  
                                    'l1': project.l1,
                                    'text_type': phonetic_or_normal,
                                    'length_in_words': word_count,  
                                    'author': project.user.username,  
                                    'voice': voice,  
                                    'annotator': project.user.username,  
                                    'difficulty_level': cefr_level,  
                                    'summary': summary
                                    }
                                )
        # Update any fields that might have changed
        if not created:
            content.title = title
            content.l2 = project.l2
            content.l1 = project.l1
            content.text_type = phonetic_or_normal
            content.length_in_words = word_count  
            content.author = project.user.username
            content.voice = voice 
            content.annotator = project.user.username
            content.difficulty_level = cefr_level
            content.summary = summary
            content.save()

        return content

    except Exception as e:
        post_task_update(callback, f"Exception when posting content: {str(e)}\n{traceback.format_exc()}")
        return None

# Show link to reading history for user and l2_language
# There are controls to change the l2 and add a project to the reading history
# The 'status' argument is used to display a completion message when we redirect back here after updating the history
@login_required
def reading_history(request, l2_language, status):
    user = request.user
    reading_history, created = ReadingHistory.objects.get_or_create(user=user, l2=l2_language)
    require_phonetic_text = reading_history.require_phonetic_text

    if created:
        create_project_and_project_internal_for_reading_history(reading_history, user, l2_language)

    clara_project = reading_history.project
    project_id = clara_project.id
    clara_project_internal = CLARAProjectInternal(clara_project.internal_id, clara_project.l2, clara_project.l1)

    if request.method == 'POST':
        action = request.POST.get('action')

        # Changing the reading history language
        if action == 'select_language':
            l2_language =  request.POST['l2']
            messages.success(request, f"Now on reading history for {l2_language}.")
            return redirect('reading_history', l2_language, 'init')

        # Deleting the reading history for the currently selected language
        elif action == 'delete_reading_history':
            reading_history.delete()
            clara_project.delete()
            clara_project_internal.delete_rendered_html(project_id)
            clara_project_internal.delete()
            messages.success(request, "Reading history deleted successfully.")
            return redirect('reading_history', l2_language, 'init')

        # Changing the status of the require_phonetic_text field for the reading history
        elif action == 'update_phonetic_preference':
            require_phonetic_text = True if 'require_phonetic_text' in request.POST and request.POST['require_phonetic_text'] == 'on' else False
            reading_history.require_phonetic_text = require_phonetic_text
            reading_history.save()
            messages.success(request, "Your preference for phonetic texts has been updated.")
            return redirect('reading_history', l2_language, 'init')

        # Adding a project to the end of the reading history     
        elif action == 'add_project':
            if reading_history:
                try:
                    new_project_id = request.POST['project_id']

                    task_type = f'update_reading_history'
                    callback, report_id = make_asynch_callback_and_report_id(request, task_type)

                    async_task(update_reading_history, reading_history, clara_project_internal, project_id, new_project_id, l2_language,
                               require_phonetic_text=require_phonetic_text, callback=callback)

                    # Redirect to the monitor view, passing the task ID and report ID as parameters
                    return redirect('update_reading_history_monitor', l2_language, report_id)
                        
                except Exception as e:
                    messages.error(request, "Something went wrong when updating the reading history. Try looking at the 'Recent task updates' view")
                    print(f"Exception: {str(e)}\n{traceback.format_exc()}")
                    return redirect('reading_history', l2_language, 'error')
            else:
                messages.error(request, f"Unable to add project to reading history")
            return redirect('reading_history', l2_language, 'error')

    # GET request
    # Display the language, the current reading history projects, a link to the compiled reading history, and controls.
    # If 'status' is 'finished' or 'error', i.e. we got here from a redirect after adding a text, display a suitable message.
    else:
        if status == 'finished':
            messages.success(request, f'Reading history successfully updated')
        elif status == 'error':
            messages.error(request, "Something went wrong when updating the reading history. Try looking at the 'Recent task updates' view")

        phonetic_resources_available = phonetic_resources_are_available(l2_language)
        languages_available = l2s_in_posted_content(require_phonetic_text=require_phonetic_text)
        projects_in_history = reading_history.get_ordered_projects()
        projects_available = projects_available_for_adding_to_history(l2_language, projects_in_history, require_phonetic_text=require_phonetic_text)
        
        l2_form = L2LanguageSelectionForm(languages_available=languages_available, l2=l2_language)
        add_project_form = AddProjectToReadingHistoryForm(projects_available=projects_available)
        require_phonetic_text_form = RequirePhoneticTextForm(initial={ 'require_phonetic_text': require_phonetic_text } )
        rendered_html_exists = clara_project_internal.rendered_html_exists(project_id)

    clara_version = get_user_config(request.user)['clara_version']

    return render(request, 'clara_app/reading_history.html', {
        'l2_form': l2_form,
        'add_project_form': add_project_form,
        'require_phonetic_text_form': require_phonetic_text_form,
        'phonetic_resources_available': phonetic_resources_available,
        'projects_in_history': projects_in_history,
        # project_id is used to construct the link to the compiled reading history
        'project_id': project_id,
        'rendered_html_exists': rendered_html_exists,
        'projects_available': projects_available,
        'clara_version': clara_version
    })

# Function to call in asynch process. Update and render the CLARAProjectInternal associated with the reading history
def update_reading_history(reading_history, clara_project_internal, project_id, new_project_id, l2_language,
                           require_phonetic_text=False, callback=None):
    try:
        project = get_object_or_404(CLARAProject, pk=project_id)
        new_project = get_object_or_404(CLARAProject, pk=new_project_id)
        
        reading_history.add_project(new_project)
        reading_history.save()

        projects_in_history = reading_history.get_ordered_projects()
        
        internal_projects_in_history = [ CLARAProjectInternal(project.internal_id, project.l2, project.l1)
                                         for project in projects_in_history ]
        reading_history_internal = ReadingHistoryInternal(project_id, clara_project_internal, internal_projects_in_history)
        new_project_internal = CLARAProjectInternal(new_project.internal_id, new_project.l2, new_project.l1)
        original_number_of_component_projects = len(reading_history_internal.component_clara_project_internals)
        
        reading_history_internal.add_component_project_and_create_combined_text_object(new_project_internal, phonetic=False)
        reading_history_internal.render_combined_text_object(phonetic=False)

        if require_phonetic_text:
            reading_history_internal.add_component_project_and_create_combined_text_object(new_project_internal, phonetic=True)
            reading_history_internal.render_combined_text_object(phonetic=True)
            # If this is the first time we're compiling this reading history,
            # recompile with phonetic=False to get a link from phonetic=False version to the phonetic=True version
            if original_number_of_component_projects == 0:
                reading_history_internal.render_combined_text_object(phonetic=False)

        post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Something went wrong when trying to add project to reading history.")
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        
        post_task_update(callback, f"error")

@login_required
def update_reading_history_status(request, l2_language, report_id):
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
def update_reading_history_monitor(request, l2_language, report_id):

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/update_reading_history_monitor.html',
                  {'l2_language':l2_language, 'report_id': report_id, 'clara_version':clara_version})


# Create associated CLARAProject and CLARAProjectInternal
def create_project_and_project_internal_for_reading_history(reading_history, user, l2_language):
    title = f"{user}_reading_history_for_{l2_language}"
    l1_language = 'No L1 language'
    # Create a new CLARAProject, associated with the current user
    clara_project = CLARAProject(title=title, user=user, l2=l2_language, l1=l1_language)
    clara_project.save()
    internal_id = create_internal_project_id(title, clara_project.id)
    # Update the CLARAProject with the internal_id
    clara_project.internal_id = internal_id
    clara_project.save()
    # Create a new CLARAProjectInternal
    clara_project_internal = CLARAProjectInternal(internal_id, l2_language, l1_language)
    reading_history.project = clara_project
    reading_history.internal_id = internal_id
    reading_history.save()

# Find the L2s such that
#   - they are the L2 of a piece of posted content
#   - whose project has a saved internalised text
def l2s_in_posted_content(require_phonetic_text=False):
    # Get all Content objects that are linked to a CLARAProject
    contents_with_projects = Content.objects.exclude(project=None)
    l2_languages = set()

    for content in contents_with_projects:
        # Check if the associated project has saved internalized text
        if not require_phonetic_text:
            #if content.project.has_saved_internalised_and_annotated_text():
            if has_saved_internalised_and_annotated_text(content.project):
                l2_languages.add(content.l2)
        else:
            #if content.project.has_saved_internalised_and_annotated_text() and content.project.has_saved_internalised_and_annotated_text(phonetic=True):
            if has_saved_internalised_and_annotated_text(content.project) and has_saved_internalised_and_annotated_text(content.project, phonetic=True):
                l2_languages.add(content.l2)

    return list(l2_languages)

# Find the projects that
#   - have the right l2,
#   - have been posted as content,
#   - have a saved internalised text,
#   - are not already in the history
def projects_available_for_adding_to_history(l2_language, projects_in_history, require_phonetic_text=False):
    # Get all projects that have been posted as content with the specified L2 language
    projects = CLARAProject.objects.filter(
        l2=l2_language,
        related_content__isnull=False
    ).distinct()

    available_projects = []

    for project in projects:
        # Check if the project has the required saved internalized text and is not already in the history
        if not require_phonetic_text:
            #if project.has_saved_internalised_and_annotated_text() and project not in projects_in_history:
            if has_saved_internalised_and_annotated_text(project) and project not in projects_in_history:
                available_projects.append(project)
        else:
            #if project.has_saved_internalised_and_annotated_text() and project.has_saved_internalised_and_annotated_text(phonetic=True) \
            if has_saved_internalised_and_annotated_text(project) and has_saved_internalised_and_annotated_text(project, phonetic=True) \
               and project not in projects_in_history:
                available_projects.append(project)

    return available_projects

# Show a satisfaction questionnaire
@login_required
def satisfaction_questionnaire(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    user = request.user

    # Try to get an existing questionnaire response for this project and user
    try:
        existing_questionnaire = SatisfactionQuestionnaire.objects.get(project=project, user=user)
    except SatisfactionQuestionnaire.DoesNotExist:
        existing_questionnaire = None
    
    if request.method == 'POST':
        if existing_questionnaire:
            # If an existing questionnaire is found, update it
            form = SatisfactionQuestionnaireForm(request.POST, instance=existing_questionnaire)
        else:
            # No existing questionnaire, so create a new instance
            form = SatisfactionQuestionnaireForm(request.POST)
            
        if form.is_valid():
            questionnaire = form.save(commit=False)
            questionnaire.project = project
            questionnaire.user = request.user 
            questionnaire.save()
            messages.success(request, 'Thank you for your feedback!')
            return redirect('project_detail', project_id=project.id)
    else:
        if existing_questionnaire:
            form = SatisfactionQuestionnaireForm(instance=existing_questionnaire)
        else:
            form = SatisfactionQuestionnaireForm()

    return render(request, 'clara_app/satisfaction_questionnaire.html', {'form': form, 'project': project})

# Just show the questionnaire without allowing any editing
@login_required
def show_questionnaire(request, project_id, user_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    user = get_object_or_404(User, pk=user_id)
    
    # Retrieve the existing questionnaire response for this project and user
    questionnaire = get_object_or_404(SatisfactionQuestionnaire, project=project, user=user)

    return render(request, 'clara_app/show_questionnaire.html', {'questionnaire': questionnaire, 'project': project})

@login_required
@user_passes_test(lambda u: u.userprofile.is_questionnaire_reviewer)
def manage_questionnaires(request):
    if request.method == 'POST':
        if 'export' in request.POST:
            # Convert questionnaire data to a pandas DataFrame
            qs = SatisfactionQuestionnaire.objects.all().values()
            
            df = pd.DataFrame(qs)
            
            # Convert timezone-aware 'created_at' to timezone-naive
            df['created_at'] = df['created_at'].apply(lambda x: timezone.make_naive(x) if x is not None else x)

            # Convert DataFrame to Excel file
            response = HttpResponse(content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = 'attachment; filename="questionnaires.xlsx"'

            with pd.ExcelWriter(response, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)

            return response
        elif 'delete' in request.POST:
            # Handle the deletion of selected questionnaire responses
            selected_ids = request.POST.getlist('selected_responses')
            if selected_ids:
                SatisfactionQuestionnaire.objects.filter(id__in=selected_ids).delete()
                messages.success(request, "Selected responses have been deleted.")
                return redirect('manage_questionnaires')

    questionnaires = SatisfactionQuestionnaire.objects.all()
    return render(request, 'clara_app/manage_questionnaires.html', {'questionnaires': questionnaires})

def aggregated_questionnaire_results(request):
    # Aggregate data for each Likert scale question
    ratings = SatisfactionQuestionnaire.objects.aggregate(
        grammar_correctness_avg=Avg('grammar_correctness', filter=Q(grammar_correctness__gt=0)),
        vocabulary_appropriateness_avg=Avg('vocabulary_appropriateness', filter=Q(vocabulary_appropriateness__gt=0)),
        style_appropriateness_avg=Avg('style_appropriateness', filter=Q(style_appropriateness__gt=0)),
        content_appropriateness_avg=Avg('content_appropriateness', filter=Q(content_appropriateness__gt=0)),
        cultural_elements_avg=Avg('cultural_elements', filter=Q(cultural_elements__gt=0)),
        text_engagement_avg=Avg('text_engagement', filter=Q(text_engagement__gt=0)),
        image_match_avg=Avg('image_match', filter=Q(image_match__gt=0)),
        count=Count('id')
    )
    
    # For choices questions (time spent, shared intent, etc.), it might be useful to calculate the distribution
    # For example, how many selected each time range for correction_time_text
    correction_time_text_distribution = SatisfactionQuestionnaire.objects.values('correction_time_text').annotate(total=Count('correction_time_text')).order_by('correction_time_text')
    correction_time_annotations_distribution = SatisfactionQuestionnaire.objects.values('correction_time_annotations').annotate(total=Count('correction_time_annotations')).order_by('correction_time_annotations')
    image_editing_time_distribution = SatisfactionQuestionnaire.objects.values('image_editing_time').annotate(total=Count('image_editing_time')).order_by('image_editing_time')

    generated_by_ai_distribution = SatisfactionQuestionnaire.objects.values('generated_by_ai').annotate(total=Count('generated_by_ai')).order_by('generated_by_ai')
    shared_intent_distribution = SatisfactionQuestionnaire.objects.values('shared_intent').annotate(total=Count('shared_intent')).order_by('shared_intent')
    text_type_distribution = SatisfactionQuestionnaire.objects.values('text_type').annotate(total=Count('text_type')).order_by('text_type')
    
    # For open-ended questions, fetching the latest 50 responses for illustration
    purpose_texts = SatisfactionQuestionnaire.objects.values_list('purpose_text', flat=True).order_by('-created_at')[:50]
    functionality_suggestions = SatisfactionQuestionnaire.objects.values_list('functionality_suggestion', flat=True).order_by('-created_at')[:50]
    ui_improvement_suggestions = SatisfactionQuestionnaire.objects.values_list('ui_improvement_suggestion', flat=True).order_by('-created_at')[:50]

    context = {
        'ratings': ratings,
        'correction_time_text_distribution': correction_time_text_distribution,
        'correction_time_annotations_distribution': correction_time_annotations_distribution,
        'image_editing_time_distribution': image_editing_time_distribution,
        'generated_by_ai_distribution': generated_by_ai_distribution,
        'shared_intent_distribution': shared_intent_distribution,
        'text_type_distribution': text_type_distribution,
        'purpose_texts': list(purpose_texts),
        'functionality_suggestions': list(functionality_suggestions),
        'ui_improvement_suggestions': list(ui_improvement_suggestions),
    }

    return render(request, 'clara_app/aggregated_questionnaire_results.html', context)

IMAGE_QUESTIONNAIRE_QUESTIONS = [
    {
        "id": 1,
        "text": "How well does the image correspond to the page text?",
    },
    {
        "id": 2,
        "text": "How consistent is the style of the image with the overall style?",
    },
    {
        "id": 3,
        "text": "How consistent is the appearance of elements in the image with their previous appearance?",
    },
    {
        "id": 4,
        "text": "Is the image appropriate to the relevant culture?",
    },
    {
        "id": 5,
        "text": "How visually appealing do you find the image?",
    },
]

@login_required
def image_questionnaire_project_list(request):
    """
    Lists all projects that have an image questionnaire, applying optional search/filter criteria.
    Each project entry includes a link to start or continue the questionnaire for that project.
    """

    search_form = ProjectSearchForm(request.GET or None)
    query = Q(has_image_questionnaire=True)

    if search_form.is_valid():
        title = search_form.cleaned_data.get('title')
        l2 = search_form.cleaned_data.get('l2')
        l1 = search_form.cleaned_data.get('l1')

        if title:
            query &= Q(title__icontains=title)
        if l2:
            query &= Q(l2__icontains=l2)
        if l1:
            query &= Q(l1__icontains=l1)

    # Retrieve matching projects, order by title (case-insensitive)
    projects = CLARAProject.objects.filter(query).order_by(Lower('title'))

    return render(request, 'clara_app/image_questionnaire_project_list.html', {
        'search_form': search_form,
        'projects': projects,
    })

@login_required
def image_questionnaire_start(request, project_id):
    """
    Entry point for the image questionnaire. 
    Retrieves the story pages, stores them in session (or you could do it in memory),
    then redirects the user to the first page.
    """
    project = get_object_or_404(CLARAProject, pk=project_id)

    # Make sure the project actually has a questionnaire
    if not project.has_image_questionnaire:
        messages.error(request, 'This project does not have an image questionnaire enabled.')
        return redirect('clara_home_page')

    # Access the internal structure
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    project_dir = clara_project_internal.coherent_images_v2_project_dir

    # Read the story data
    story_data = read_project_json_file(project_dir, 'story.json') or []

    # We’ll build a global frequency map of elements -> how many pages they appear in
    element_page_count = defaultdict(int)
    
    # Filter out pages that don't have images, if you only want those
    pages_with_images = []
    for page in story_data:
        page_number = page.get('page_number')
        rel_img_path = f'pages/page{page_number}/image.jpg'
        if file_exists(project_pathname(project_dir, rel_img_path)):
            pages_with_images.append(page)

            # read relevant elements for that page
            relevant_info_path = f'pages/page{page_number}/relevant_pages_and_elements.json'
            if file_exists(project_pathname(project_dir, relevant_info_path)):
                relevant_info = read_project_json_file(project_dir, relevant_info_path)
                relevant_elems = relevant_info.get('relevant_elements', [])
                # Count how many pages each element appears in
                # We can track if we haven't incremented for this page yet, but a simpler way is to do
                # sets to avoid multiple increments for the same page.
                for elem in set(relevant_elems):
                    element_page_count[elem] += 1

    if not pages_with_images:
        # No images => no questionnaire needed
        messages.error(request, 'This project does not have any images to evaluate.')
        return redirect('clara_home_page')

    # now see if any element appears in a page
    # that indicates there's a chance of continuity
    has_any_relevant_elements = any(count > 0 for count in element_page_count.values())

    # Store pages in session, plus the boolean
    request.session['image_questionnaire_pages'] = pages_with_images
    request.session['has_any_relevant_elements'] = has_any_relevant_elements
    
    return redirect('image_questionnaire_item', project_id=project.id, index=0)


@login_required
def image_questionnaire_item(request, project_id, index):
    """
    Shows a single page's image, text, and the relevant questions.
    Handles form submission for each question, then goes forward or backward.
    """
    project = get_object_or_404(CLARAProject, pk=project_id)

    if not project.has_image_questionnaire:
        messages.error(request, 'This project does not have an image questionnaire enabled.')
        return redirect('clara_home_page')

    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    project_dir = clara_project_internal.coherent_images_v2_project_dir

    # Retrieve info from session
    pages_with_images = request.session.get('image_questionnaire_pages', [])
    has_any_relevant_elements = request.session.get('has_any_relevant_elements', False)
    
    if not pages_with_images or index < 0 or index >= len(pages_with_images):
        # Index out of range: go to a summary or fallback
        return redirect('image_questionnaire_summary', project_id=project.id)

    current_page = pages_with_images[index]
    page_number = current_page.get('page_number')
    page_text = current_page.get('text', '')
    relative_page_image_path = f'pages/page{page_number}/image.jpg'

    # Decide which questions to show
    # For question #3, we see if there's a relevant previous page
    # that shares an element with the current page
    relevant_elements_current = _get_relevant_elements(project_dir, page_number)
    has_prev_relevant_page, prev_page_num = _find_previous_relevant_page(
        pages_with_images, index, project_dir, relevant_elements_current
    )

    questions_to_show = []
    for q in IMAGE_QUESTIONNAIRE_QUESTIONS:
        if q["id"] == 3:
            # Show Q3 only if:
            #   (a) There's at least one recurring element in the entire text
            #   (b) We are not on the first page
            if has_any_relevant_elements and index > 0:
                questions_to_show.append(q)
        else:
            questions_to_show.append(q)

    if request.method == 'POST':
        # Process the user's Likert-scale answers
        for q in questions_to_show:
            q_key = f"q_{q['id']}"
            c_key = f"c_{q['id']}"

            rating_str = request.POST.get(q_key)
            comment = request.POST.get(c_key, '').strip()

            if rating_str:
                # Save or update the user’s response
                rating = int(rating_str)
                ImageQuestionnaireResponse.objects.update_or_create(
                    project=project,
                    user=request.user,
                    page_number=page_number,
                    question_id=q["id"],
                    defaults={"rating": rating, "comment": comment},
                )

        if "previous" in request.POST:
            return redirect('image_questionnaire_item', project_id=project.id, index=index - 1)
        else:
            # Next button or default
            return redirect('image_questionnaire_item', project_id=project.id, index=index + 1)

    # GET request: Load any existing answers for pre-fill
    existing_answers_raw = ImageQuestionnaireResponse.objects.filter(
    project=project,
    user=request.user,
    page_number=page_number
    )
    answers_by_id = {}
    
    for resp in existing_answers_raw:
        answers_by_id[resp.question_id] = (resp.rating, resp.comment)

    # Then build a structure that’s easy to iterate over in the template:
    question_data_list = []
    for q in questions_to_show:
        q_id = q["id"]
        rating_comment = answers_by_id.get(q_id, (None, ""))
        question_data_list.append({
            "id": q_id,
            "text": q["text"],
            "rating": str(rating_comment[0]),
            "comment": rating_comment[1],
        })

    # If we want to show the previous image for question #3, fetch its path
    previous_image_relpath = None
    if has_prev_relevant_page and prev_page_num is not None:
        previous_image_relpath = f'pages/page{prev_page_num}/image.jpg'
        # You can pass this to the template to display side-by-side

    context = {
        "project": project,
        "index": index,
        "total_pages": len(pages_with_images),
        "page_number": page_number,
        "page_text": page_text,
        "relative_image_path": relative_page_image_path,
        "questions": questions_to_show,
        "question_data_list": question_data_list,
        "show_previous": index > 0,
        "show_next": index < len(pages_with_images) - 1,
        "has_prev_relevant_page": has_prev_relevant_page,
        "previous_page_number": prev_page_num,
        "previous_image_relpath": previous_image_relpath,
    }
    #pprint.pprint(context)
    return render(request, "clara_app/image_questionnaire_item.html", context)


@login_required
def image_questionnaire_summary(request, project_id):
    """
    Show a simple "thank you" and optional stats or final summary.
    """
    project = get_object_or_404(CLARAProject, pk=project_id)
    if not project.has_image_questionnaire:
        messages.error(request, 'This project does not have an image questionnaire enabled.')
        return redirect('clara_home_page')

    # Example: let’s get how many total responses the user gave
    user_responses = ImageQuestionnaireResponse.objects.filter(project=project, user=request.user)
    pages_answered = user_responses.values_list('page_number', flat=True).distinct().count()
    questions_answered = user_responses.count()

    context = {
        "project": project,
        "pages_answered": pages_answered,
        "questions_answered": questions_answered,
    }
    return render(request, "clara_app/image_questionnaire_summary.html", context)

@login_required
def image_questionnaire_all_projects_summary(request):
    """
    Presents the aggregated questionnaire results (average ratings etc.) 
    for *all* projects that have an image questionnaire enabled.
    """
    # Optionally restrict this to superusers or some special role
    # if not request.user.is_superuser:
    #     return HttpResponseForbidden("You do not have permission to view this summary.")

    # Gather all projects that have an image questionnaire
    search_form = ProjectSearchForm(request.GET or None)
    query = Q(has_image_questionnaire=True)

    if search_form.is_valid():
        title = search_form.cleaned_data.get('title')
        l2 = search_form.cleaned_data.get('l2')
        l1 = search_form.cleaned_data.get('l1')

        if title:
            query &= Q(title__icontains=title)
        if l2:
            query &= Q(l2__icontains=l2)
        if l1:
            query &= Q(l1__icontains=l1)

    projects = CLARAProject.objects.filter(query).order_by(Lower('title'))

    # Prepare a list of summary data, one entry per project
    all_project_summaries = []

    # Pre-build a quick lookup from question_id to question_text
    question_texts = {q["id"]: q["text"] for q in IMAGE_QUESTIONNAIRE_QUESTIONS}

    for proj in projects:
        # Retrieve all responses for this project
        responses = ImageQuestionnaireResponse.objects.filter(project=proj)

        if not responses.exists():
            # No responses yet, just show zeros
            all_project_summaries.append({
                "search_form": search_form,
                "project": proj,
                "distinct_pages": 0,
                "distinct_users": 0,
                "aggregated_data": [],
            })
            continue

        # Count distinct pages and users
        distinct_pages = responses.values_list("page_number", flat=True).distinct().count()
        distinct_users = responses.values_list("user_id", flat=True).distinct().count()

        # Aggregate by question: average rating and how many total responses
        agg_by_question = (
            responses
            .values("question_id")
            .annotate(avg_rating=Avg("rating"), num_responses=Count("id"))
            .order_by("question_id")
        )

        # Convert query results into a list of dicts with question text
        aggregated_data = []
        for row in agg_by_question:
            q_id = row["question_id"]
            aggregated_data.append({
                "question_id": q_id,
                "question_text": question_texts.get(q_id, f"Q{q_id}"),
                "avg_rating": row["avg_rating"],
                "num_responses": row["num_responses"],
            })

        all_project_summaries.append({
            "project": proj,
            "distinct_pages": distinct_pages,
            "distinct_users": distinct_users,
            "aggregated_data": aggregated_data,
        })

    # Pass everything to the template
    return render(request, "clara_app/image_questionnaire_all_projects_summary.html", {
        "search_form": search_form,
        "all_project_summaries": all_project_summaries,
    })

def _get_relevant_elements(project_dir, page_number):
    """
    Reads relevant_pages_and_elements.json for a given page, 
    returns the list of relevant elements (could be characters, objects, etc.).
    """

    relevant_info_path = f'pages/page{page_number}/relevant_pages_and_elements.json'
    full_path = project_pathname(project_dir, relevant_info_path)
    if file_exists(full_path):
        relevant_info = read_project_json_file(project_dir, relevant_info_path)
        return set(relevant_info.get('relevant_elements', []))
    else:
        return set()

def _find_previous_relevant_page(pages_with_images, current_index, project_dir, current_elems):
    """
    Searches backward for any page that shares at least one relevant element
    with the current page. Returns (bool, page_number).
      - bool: True if found a relevant page
      - page_number: the first page_number that shares an element, or None if none
    """
    if not current_elems:
        return (False, None)

    for i in range(current_index - 1, -1, -1):
        prev_page = pages_with_images[i]
        prev_page_num = prev_page.get("page_number")
        prev_elems = _get_relevant_elements(project_dir, prev_page_num)
        if current_elems.intersection(prev_elems):
            return (True, prev_page_num)

    return (False, None)

def serve_coherent_images_v2_overview(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    file_path = absolute_file_name(Path(clara_project_internal.coherent_images_v2_project_dir / f"overview.html"))
    if file_exists(file_path):
        content_type, _ = mimetypes.guess_type(unquote(str(file_path)))
        return HttpResponse(open(file_path, 'rb'), content_type=content_type)
    else:
        raise Http404

@xframe_options_sameorigin
def serve_rendered_text(request, project_id, phonetic_or_normal, filename):
    file_path = absolute_file_name(Path(output_dir_for_project_id(project_id, phonetic_or_normal)) / f"{filename}")
    if file_exists(file_path):
        content_type, _ = mimetypes.guess_type(unquote(str(file_path)))
        if _s3_storage:
            s3_file = _s3_bucket.Object(key=file_path).get()
            return HttpResponse(s3_file['Body'].read(), content_type=content_type)
        else:
            return HttpResponse(open(file_path, 'rb'), content_type=content_type)
    else:
        raise Http404

def serve_rendered_text_static(request, project_id, phonetic_or_normal, filename):
    file_path = absolute_file_name(Path(output_dir_for_project_id(project_id, phonetic_or_normal)) / f"static/{filename}")
    if file_exists(file_path):
        content_type, _ = mimetypes.guess_type(unquote(str(file_path)))
        if _s3_storage:
            s3_file = _s3_bucket.Object(key=file_path).get()
            return HttpResponse(s3_file['Body'].read(), content_type=content_type)
        else:
            return HttpResponse(open(file_path, 'rb'), content_type=content_type)
    else:
        raise Http404

def serve_rendered_text_multimedia(request, project_id, phonetic_or_normal, filename):
    file_path = absolute_file_name(Path(output_dir_for_project_id(project_id, phonetic_or_normal)) / f"multimedia/{filename}")
    if file_exists(file_path):
        content_type, _ = mimetypes.guess_type(unquote(str(file_path)))
        if _s3_storage:
            s3_file = _s3_bucket.Object(key=file_path).get()
            return HttpResponse(s3_file['Body'].read(), content_type=content_type)
        else:
            return HttpResponse(open(file_path, 'rb'), content_type=content_type)
    else:
        raise Http404

# Serve up self-contained zipfile of HTML pages created from a project
@login_required
def serve_zipfile(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    web_accessible_dir = Path(settings.STATIC_ROOT) / f"rendered_texts/{project.id}"
    zip_filepath = Path(settings.STATIC_ROOT) / f"rendered_texts/{project.id}.zip"

    if not zip_filepath.exists():
        raise Http404("Zipfile does not exist")

    return FileResponse(open(zip_filepath, 'rb'), as_attachment=True)

# Serve up export zipfile
@login_required
def serve_export_zipfile(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    zip_filepath = absolute_file_name(clara_project_internal.export_zipfile_pathname())

    if not file_exists(zip_filepath):
        raise Http404("Zipfile does not exist")

    if _s3_storage:
        print(f'--- Serving existing S3 zipfile {zip_filepath}')
        # Generate a presigned URL for the S3 file
        # In fact this doesn't work, for reasons neither ChatGPT-4 nor I understand.
        # But generating the presigned URL one level up does work, see the make_export_zipfile function
        # The following code should not get called.
        presigned_url = _s3_client.generate_presigned_url('get_object',
                                                          Params={'Bucket': _s3_bucket_name,
                                                                  'Key': str(zip_filepath)},
                                                          ExpiresIn=3600)  # URL expires in 1 hour
        return redirect(presigned_url)
    else:
        print(f'--- Serving existing non-S3 zipfile {zip_filepath}')
        zip_file = open(zip_filepath, 'rb')
        response = FileResponse(zip_file, as_attachment=True)
        response['Content-Type'] = 'application/zip'
        response['Content-Disposition'] = f'attachment; filename="{project_id}.zip"'
        return response

    #return FileResponse(open(zip_filepath, 'rb'), as_attachment=True)

def serve_project_image(request, project_id, base_filename):
    file_path = absolute_file_name(Path(image_dir_for_project_id(project_id)) / base_filename)
    if file_exists(file_path):
        content_type, _ = mimetypes.guess_type(unquote(str(file_path)))
        if _s3_storage:
            s3_file = _s3_bucket.Object(key=file_path).get()
            return HttpResponse(s3_file['Body'].read(), content_type=content_type)
        else:
            return HttpResponse(open(file_path, 'rb'), content_type=content_type)
    else:
        raise Http404

def serve_coherent_images_v2_file(request, project_id, relative_path):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    base_dir = os.path.realpath(absolute_file_name(clara_project_internal.coherent_images_v2_project_dir))

    # Clean and normalize the relative path to prevent directory traversal
    safe_relative_path = os.path.normpath(relative_path)

    # Construct the absolute path to the requested file
    requested_path = os.path.realpath(os.path.join(base_dir, safe_relative_path))

    # Ensure that the requested path is within the base directory
    if not requested_path.startswith(base_dir + os.sep):
        raise Http404("Invalid file path.")

    # Check if the file exists and is a file (not a directory)
    if os.path.isfile(requested_path):
        content_type, _ = mimetypes.guess_type(unquote(str(requested_path)))
        with open(requested_path, 'rb') as f:
            return HttpResponse(f.read(), content_type=content_type)
    else:
        raise Http404("File not found.")

@login_required
def serve_audio_file(request, engine_id, l2, voice_id, base_filename):
    audio_repository = AudioRepositoryORM()
    #audio_repository = AudioRepositoryORM() if _use_orm_repositories else AudioRepository() 
    base_dir = audio_repository.base_dir
    file_path = absolute_file_name( Path(base_dir) / engine_id / l2 / voice_id / base_filename )
    if file_exists(file_path):
        content_type, _ = mimetypes.guess_type(unquote(str(file_path)))
        if _s3_storage:
            s3_file = _s3_bucket.Object(key=file_path).get()
            return HttpResponse(s3_file['Body'].read(), content_type=content_type)
        else:
            return HttpResponse(open(file_path, 'rb'), content_type=content_type)
    else:
        raise Http404



