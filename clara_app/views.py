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



