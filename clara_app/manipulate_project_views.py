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

# Display the history of updates to project files 
@login_required
@user_has_a_project_role
def project_history(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    actions = CLARAProjectAction.objects.filter(project=project).order_by('-timestamp')

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/project_history.html', {'project': project, 'actions': actions, 'clara_version': clara_version})
