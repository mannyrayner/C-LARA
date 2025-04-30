# This file is only kept for documentation purposes

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

#-------------------------------------------------------
# Moved to account_views.py

##def register(request):

##@login_required
##def profile(request):

#-------------------------------------------------------
# Moved to home_views.py

##def redirect_login(request):
##
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
# Moved to phonetic_lexicon_views.py

##@login_required
##@language_master_required
##def edit_phonetic_lexicon(request):
##
##def upload_and_install_plain_phonetic_lexicon(file_path, language, callback=None):
##
##@login_required
##@language_master_required
##def import_phonetic_lexicon_status(request, language, report_id):
##
##@login_required
##@language_master_required
##def import_phonetic_lexicon_monitor(request, language, report_id):
##
##@login_required
##@language_master_required
##def import_phonetic_lexicon_monitor(request, language, report_id):
##
##@login_required
##@language_master_required
##def import_phonetic_lexicon_complete(request, language, status):
    
#-------------------------------------------------------
# Moved to simple_clara_views.py

##def get_simple_clara_resources_helper(project_id, user):
##
##@login_required
##def simple_clara(request, project_id, last_operation_status):
##
##def perform_simple_clara_action_helper(username, project_id, simple_clara_action, callback=None):
##
##@login_required
##def simple_clara_status(request, project_id, report_id):
##
##@login_required
##def simple_clara_monitor(request, project_id, report_id):
##
##def simple_clara_create_project_helper(username, simple_clara_action, callback=None):
##
##def simple_clara_change_title_helper(username, project_id, simple_clara_action, callback=None):
##
##def simple_clara_create_text_helper(username, project_id, simple_clara_action, callback=None):
##
##def simple_clara_create_text_and_image_helper(username, project_id, simple_clara_action, callback=None):
##
##def simple_clara_save_text_and_create_image_helper(username, project_id, simple_clara_action, callback=None):
##
##def simple_clara_save_image_and_create_text_helper(username, project_id, simple_clara_action, callback=None):
##
##def simple_clara_regenerate_text_from_image_helper(username, project_id, simple_clara_action, callback=None):
##
##def simple_clara_save_text_helper(username, project_id, simple_clara_action, callback=None):
##
##def simple_clara_save_segmented_text_helper(username, project_id, simple_clara_action, callback=None):
##
##def simple_clara_save_text_title_helper(username, project_id, simple_clara_action, callback=None):
##
##def simple_clara_save_segmented_title_helper(username, project_id, simple_clara_action, callback=None):
##
##def simple_clara_save_uploaded_image_helper(username, project_id, simple_clara_action, callback=None):
##
##def simple_clara_save_preferred_tts_engine_helper(username, project_id, simple_clara_action, callback=None):
##
##def simple_clara_rewrite_text_helper(username, project_id, simple_clara_action, callback=None):
##
##def simple_clara_regenerate_image_helper(username, project_id, simple_clara_action, callback=None):
##
##def simple_clara_create_v2_style_helper(username, project_id, simple_clara_action, callback=None):
##
##def simple_clara_create_v2_elements_helper(username, project_id, simple_clara_action, callback=None):
##
##def simple_clara_delete_v2_element_helper(username, project_id, simple_clara_action, callback=None):
##
##def simple_clara_add_v2_element_helper(username, project_id, simple_clara_action, callback=None):
##
##def simple_clara_create_v2_pages_helper(username, project_id, simple_clara_action, callback=None):
##
##def simple_clara_create_segmented_text_helper(username, project_id, simple_clara_action, callback=None):
##
##def simple_clara_create_rendered_text_helper(username, project_id, simple_clara_action, callback=None):
##
##def simple_clara_post_rendered_text_helper(username, project_id, simple_clara_action, callback=None):
##
##@login_required
##def simple_clara_review_v2_images_for_page(request, project_id, page_number, from_view, status):
##
##@login_required
##def simple_clara_review_v2_images_for_element(request, project_id, element_name, from_view, status):
##
##@login_required
##def simple_clara_review_v2_images_for_style(request, project_id, from_view, status):
##
##def execute_simple_clara_image_requests(project, clara_project_internal, requests, callback=None):
##
##def execute_simple_clara_element_requests(project, clara_project_internal, requests, callback=None):
##
##def execute_simple_clara_style_requests(project, clara_project_internal, requests, callback=None):
##
##@login_required
##@user_has_a_project_role
##def execute_simple_clara_image_requests_status(request, project_id, report_id):
##
##@login_required
##@user_has_a_project_role
##def execute_simple_clara_element_requests_status(request, project_id, report_id):
##
##@login_required
##@user_has_a_project_role
##def execute_simple_clara_style_requests_status(request, project_id, report_id):
##
##@login_required
##@user_has_a_project_role
##def execute_simple_clara_image_requests_monitor(request, project_id, report_id, page_number, from_view):
##
##@login_required
##@user_has_a_project_role
##def execute_simple_clara_element_requests_monitor(request, project_id, report_id, element_name, from_view):
##
##login_required
##@user_has_a_project_role
##def execute_simple_clara_style_requests_monitor(request, project_id, report_id, from_view):

#-------------------------------------------------------
# Moved to create_project_views.py

##@login_required
##def create_project(request):
##
##@login_required
##def import_project(request):
##
##def import_project_from_zip_file(zip_file, project_id, internal_id, callback=None):
##
##@login_required
##@user_has_a_project_role
##def import_project_status(request, project_id, report_id):
##
##@login_required
##@user_has_a_project_role
##def import_project_monitor(request, project_id, report_id):
##
##@login_required
##@user_has_a_project_role
##def import_project_complete(request, project_id, status):
##
##@login_required
##@user_has_a_project_role
##def clone_project(request, project_id):
    
#-------------------------------------------------------
# Moved to manipulate_project_views.py

##@login_required
##def project_list(request, clara_version):
##
##@login_required
##@user_has_a_project_role
##def project_detail(request, project_id):
##
##@login_required
##@user_is_project_owner
##def manage_project_members(request, project_id):
##
##@login_required
##def remove_project_member(request, permission_id):
##
##@login_required
##@user_is_project_owner
##def delete_project(request, project_id):
##
##@login_required
##@user_has_a_project_role
##def project_history(request, project_id):
    
#-------------------------------------------------------
# Moved to export_zipfile_views.py

##def clara_project_internal_make_export_zipfile(clara_project_internal,
##                                               simple_clara_type='create_text_and_image',
##                                               uses_coherent_image_set=False,
##                                               uses_coherent_image_set_v2=False,
##                                               use_translation_for_images=False,
##                                               human_voice_id=None, human_voice_id_phonetic=None,
##                                               audio_type_for_words='tts', audio_type_for_segments='tts', 
##                                               callback=None):
##
##@login_required
##@user_has_a_project_role
##def make_export_zipfile(request, project_id):
##
##@login_required
##@user_has_a_project_role
##def make_export_zipfile_status(request, project_id, report_id):
##
##@login_required
##@user_has_a_project_role
##def make_export_zipfile_monitor(request, project_id, report_id):
##
##@login_required
##@user_has_a_project_role
##def make_export_zipfile_complete(request, project_id, status):
    
#-------------------------------------------------------
# Moved to annotation_views.py

##def create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template, text_choices_info=None):
##
##@login_required
##@user_has_a_project_role
##def generate_text_status(request, project_id, report_id):
## 
##@login_required
##@user_has_a_project_role
##def generate_text_monitor(request, project_id, version, report_id):
##
##@login_required
##@user_has_a_project_role
##def generate_text_complete(request, project_id, version, status):
##
##def CreateAnnotationTextFormOfRightType(version, *args, **kwargs):
##
##def perform_correct_operation_and_store_api_calls(annotated_text, version, project, clara_project_internal,
##                                                  user_object, label, callback=None):
##def perform_correct_operation(annotated_text, version, clara_project_internal, user, label, config_info={}, callback=None):
##
##def perform_generate_operation_and_store_api_calls(version, project, clara_project_internal,
##                                                   user_object, label, previous_version='default', prompt=None, text_type=None, callback=None):
##
##def perform_generate_operation(version, clara_project_internal, user, label, previous_version=None, prompt=None, text_type=None, config_info={}, callback=None):
##
##def perform_improve_operation_and_store_api_calls(version, project, clara_project_internal,
##                                                   user_object, label, prompt=None, text_type=None, callback=None):
##
##def perform_improve_operation(version, clara_project_internal, user, label, prompt=None, text_type=None, config_info={}, callback=None):
##
##def previous_version_and_template_for_version(this_version, previous_version=None):
##
##@login_required
##@user_has_a_project_role
##def create_plain_text(request, project_id):
##
##@login_required
##@user_has_a_project_role
##def create_title(request, project_id):
##
##@login_required
##@user_has_a_project_role
##def create_segmented_title(request, project_id):
##
##@login_required
##@user_has_a_project_role
##def create_summary(request, project_id):
##
##@login_required
##@user_has_a_project_role
##def create_cefr_level(request, project_id):
##
##@login_required
##@user_has_a_project_role
##def create_segmented_text(request, project_id):
##
##@login_required
##@user_has_a_project_role
##def create_translated_text(request, project_id):
##
##@login_required
##@user_has_a_project_role
##def create_phonetic_text(request, project_id):
##
##@login_required
##@user_has_a_project_role
##def create_glossed_text(request, project_id):
##
##@login_required
##@user_has_a_project_role
##def create_glossed_text_from_lemma(request, project_id):
##
##@login_required
##@user_has_a_project_role
##def create_lemma_tagged_text(request, project_id):
##
##@login_required
##@user_has_a_project_role
##def create_mwe_tagged_text(request, project_id):
##
##@login_required
##@user_has_a_project_role
##def create_pinyin_tagged_text(request, project_id):
##
##@login_required
##@user_has_a_project_role
##def create_lemma_and_gloss_tagged_text(request, project_id):
##
##@login_required
##@user_has_a_project_role
##def edit_acknowledgements(request, project_id):
##
##@login_required
##@user_has_a_project_role
##def set_format_preferences(request, project_id):

#-------------------------------------------------------
# Moved to human_audio_views.py

##@login_required
##@user_has_a_project_role
##def get_audio_metadata_view(request, project_id):
##
##@login_required
##@user_has_a_project_role
##def human_audio_processing(request, project_id):
##
##def initial_data_for_audio_upload_formset(clara_project_internal, human_audio_info):
##
##@login_required
##@user_has_a_project_role
##def human_audio_processing_phonetic(request, project_id):
##
##def initial_data_for_audio_upload_formset_phonetic(clara_project_internal, human_audio_info):
##
##def process_ldt_zipfile(clara_project_internal, zip_file, human_voice_id, callback=None):
##
##def process_manual_alignment(clara_project_internal, audio_file, metadata, human_voice_id, use_context=True, callback=None):
##
##@login_required
##@user_has_a_project_role
##def process_ldt_zipfile_status(request, project_id, report_id):
##
##@login_required
##@user_has_a_project_role
##def process_manual_alignment_status(request, project_id, report_id):
##
##@login_required
##@user_has_a_project_role
##def process_ldt_zipfile_monitor(request, project_id, report_id):
##
##@login_required
##@user_has_a_project_role
##def process_manual_alignment_monitor(request, project_id, report_id):
##
##@login_required
##@user_has_a_project_role
##def process_ldt_zipfile_complete(request, project_id, status):
##
##@login_required
##@user_has_a_project_role
##def process_manual_alignment_complete(request, project_id, status):
##
##@login_required
##def generate_audio_metadata(request, project_id, metadata_type, human_voice_id):
##
##@login_required
##def generate_audio_metadata_phonetic(request, project_id, metadata_type, human_voice_id):
##
##def generate_audio_metadata_phonetic_or_normal(request, project_id, metadata_type, human_voice_id, phonetic=False):
##
##@login_required
##def generate_annotated_segmented_file(request, project_id):
#-------------------------------------------------------
# Moved to images_v1_views.py

##@login_required
##@user_has_a_project_role
##def edit_images(request, project_id, dall_e_3_image_status):
##
##@login_required
##@user_has_a_project_role
##def create_dall_e_3_image_status(request, project_id, report_id):
##
##@login_required
##@user_has_a_project_role
##def create_dall_e_3_image_monitor(request, project_id, report_id):
##
##def access_archived_images(request, project_id, image_name):
##
##def restore_image(request, project_id, archived_image_id):
##
##def delete_archive_image(request, project_id, archived_image_id):
#-------------------------------------------------------
# Moved to images_v2_views.py

##@login_required
##@user_has_a_project_role
##def edit_images_v2(request, project_id, status):
##
##@login_required
##@user_has_a_project_role
##def coherent_images_v2_status(request, project_id, report_id):
##
##@login_required
##@user_has_a_project_role
##def coherent_images_v2_monitor(request, project_id, report_id):
##
##def create_style_description_and_image(project, clara_project_internal, params, callback=None):
##
##def create_element_names(project, clara_project_internal, params, callback=None):
##
##def add_v2_element(new_element_text, project, clara_project_internal, params, callback=None):
##
##def create_element_descriptions_and_images(project, clara_project_internal, params, elements_to_generate, callback=None):
##
##def get_elements_with_content_violations(element_texts, params):
##
##def create_page_descriptions_and_images(project, clara_project_internal, params, pages_to_generate, callback=None):
##
##def get_pages_with_content_violations(page_numbers, params):
##
##def create_variant_images(project, clara_project_internal, params, content_type, content_identifier, alternate_image_id, callback=None):

#-------------------------------------------------------
# Moved to community_views.py

##@login_required
##@user_passes_test(lambda u: u.userprofile.is_admin)
##def create_community(request):
##
##@login_required
##@user_passes_test(lambda u: u.userprofile.is_admin)
##def delete_community_menu(request):
##
##@login_required
##def community_home(request, community_id):
##
##@login_required
##@user_passes_test(lambda u: u.userprofile.is_admin)  
##def assign_coordinator_to_community(request):
##
##@login_required
##@user_is_coordinator_of_some_community
##def assign_member_to_community(request):
##
##@login_required
##@user_is_project_owner
##def project_community(request, project_id):
    
#-------------------------------------------------------
# Moved to community_reviewing_views.py

##@login_required
##@user_is_community_member
##def community_review_images(request, project_id):
##
##@login_required
##@user_is_community_coordinator
##def community_organiser_review_images(request, project_id):
##
##@login_required
##def community_review_images_external(request, project_id):
##
##def community_review_images_cm_or_co(request, project_id, cm_or_co):
##
##@login_required
##@community_role_required
##def community_review_images_for_page(request, project_id, page_number, cm_or_co, status):
##
##def execute_community_requests(project, clara_project_internal, requests, callback=None):
##
##@login_required
##@user_has_a_project_role
##def execute_community_requests_for_page_status(request, project_id, report_id):
##
##@login_required
##@user_has_a_project_role
##def execute_community_requests_for_page_monitor(request, project_id, report_id, page_number):
#-------------------------------------------------------
# Moved to image_questionnaire_views.py

##IMAGE_QUESTIONNAIRE_QUESTIONS =
##
##@login_required
##def image_questionnaire_project_list(request):
## 
##@login_required
##def image_questionnaire_start(request, project_id):
##
##@login_required
##def image_questionnaire_item(request, project_id, index):
##
##@login_required
##def image_questionnaire_summary(request, project_id):
##
##@login_required
##def image_questionnaire_all_projects_summary(request):
##
##def _get_relevant_elements(project_dir, page_number):
##
##def _find_previous_relevant_page(pages_with_images, current_index, project_dir, current_elems):
#-------------------------------------------------------
# Moved to rendering_views.py

##def clara_project_internal_render_text(clara_project_internal, project_id,
##                                       audio_type_for_words='tts', audio_type_for_segments='tts',
##                                       preferred_tts_engine=None, preferred_tts_voice=None,
##                                       human_voice_id=None,
##                                       self_contained=False, phonetic=False, callback=None):
##
##@login_required
##@user_has_a_project_role
##def render_text_start_normal(request, project_id):
##
##@login_required
##@user_has_a_project_role
##def render_text_start_phonetic(request, project_id):
##
##def render_text_start_phonetic_or_normal(request, project_id, phonetic_or_normal):
##
##@login_required
##@user_has_a_project_role
##def render_text_status(request, project_id, report_id):
##
##@login_required
##@user_has_a_project_role
##def render_text_monitor(request, project_id, phonetic_or_normal, report_id):
#-------------------------------------------------------
# Moved to satisfaction_questionnaire_views.py

##@login_required
##def satisfaction_questionnaire(request, project_id):
##
##@login_required
##def show_questionnaire(request, project_id, user_id):
##
##@login_required
##@user_passes_test(lambda u: u.userprofile.is_questionnaire_reviewer)
##def manage_questionnaires(request):
##
##def aggregated_questionnaire_results(request):
#-------------------------------------------------------
# Moved to reading_histories_views.py

##@login_required
##def reading_history(request, l2_language, status):
##
##def update_reading_history(reading_history, clara_project_internal, project_id, new_project_id, l2_language,
##                           require_phonetic_text=False, callback=None):
##
##@login_required
##def update_reading_history_status(request, l2_language, report_id):
##
##@login_required
##def update_reading_history_monitor(request, l2_language, report_id):
##
##def create_project_and_project_internal_for_reading_history(reading_history, user, l2_language):
##
##def l2s_in_posted_content(require_phonetic_text=False):
##
##def projects_available_for_adding_to_history(l2_language, projects_in_history, require_phonetic_text=False):

#-------------------------------------------------------
# Moved to serving_content_views.py

##def serve_coherent_images_v2_overview(request, project_id):
##
##@xframe_options_sameorigin
##def serve_rendered_text(request, project_id, phonetic_or_normal, filename):
##
##def serve_rendered_text_static(request, project_id, phonetic_or_normal, filename):
##
##def serve_rendered_text_multimedia(request, project_id, phonetic_or_normal, filename):
##
### Serve up self-contained zipfile of HTML pages created from a project
##@login_required
##
### Serve up export zipfile
##@login_required
##def serve_export_zipfile(request, project_id):
##
##def serve_project_image(request, project_id, base_filename):
##
##def serve_coherent_images_v2_file(request, project_id, relative_path):
##
##@login_required
##def serve_audio_file(request, engine_id, l2, voice_id, base_filename):



