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

