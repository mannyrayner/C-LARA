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

# Register a piece of content that's already posted somewhere on the web
@login_required
def register_content(request):
    if request.method == "POST":
        form = ContentRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('content_success')
    else:
        form = ContentRegistrationForm()

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/register_content.html', {'form': form, 'clara_version': clara_version})

# Confirm that content has been registered
def content_success(request):

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/content_success.html', {'clara_version': clara_version})
   
# List currently registered content
@login_required
def content_list(request):
    search_form = ContentSearchForm(request.GET or None)
    query = Q()

    if search_form.is_valid():
        l2 = search_form.cleaned_data.get('l2')
        l1 = search_form.cleaned_data.get('l1')
        title = search_form.cleaned_data.get('title')
        time_period = search_form.cleaned_data.get('time_period')

        if l2:
            query &= Q(l2__icontains=l2)
        if l1:
            query &= Q(l1__icontains=l1)
        if title:
            query &= Q(title__icontains=title)
        if time_period:
            days_ago = timezone.now() - timedelta(days=int(time_period))
            query &= Q(updated_at__gte=days_ago)

    content_list = Content.objects.filter(query)

    # Figure out how the user wants to sort:
    order_by = request.GET.get('order_by')
    if order_by == 'title':
        # Order ascending by title
        content_list = content_list.order_by(Lower('title'))
    elif order_by == 'age':
        # "Newest first" or "oldest first"? 
        # If you want newest first, just do '-updated_at'
        content_list = content_list.order_by('-updated_at')
    elif order_by == 'accesses':
        # Sort by number of accesses, largest first
        content_list = content_list.order_by('-unique_access_count')
    else:
        # Default to alphabetical
        content_list = content_list.order_by(Lower('title'))

    paginator = Paginator(content_list, 10)  # Show 10 content items per page
    page = request.GET.get('page')
    contents = paginator.get_page(page)

    clara_version = get_user_config(request.user)['clara_version']

    return render(
        request,
        'clara_app/content_list.html',
        {
            'contents': contents,
            'search_form': search_form,
            'clara_version': clara_version
        }
    )

def public_content_list(request):
    search_form = ContentSearchForm(request.GET or None)
    query = Q()

    if search_form.is_valid():
        l2 = search_form.cleaned_data.get('l2')
        l1 = search_form.cleaned_data.get('l1')
        title = search_form.cleaned_data.get('title')
        time_period = search_form.cleaned_data.get('time_period')

        if l2:
            query &= Q(l2__icontains=l2)
        if l1:
            query &= Q(l1__icontains=l1)
        if title:
            query &= Q(title__icontains=title)
        if time_period:
            days_ago = timezone.now() - timedelta(days=int(time_period))
            query &= Q(updated_at__gte=days_ago)

    content_list = Content.objects.filter(query)

    # Figure out how the user wants to sort:
    order_by = request.GET.get('order_by')
    if order_by == 'title':
        # Order ascending by title
        content_list = content_list.order_by(Lower('title'))
    elif order_by == 'age':
        # "Newest first" or "oldest first"? 
        # If you want newest first, just do '-updated_at'
        content_list = content_list.order_by('-updated_at')
    elif order_by == 'accesses':
        # Sort by number of accesses, largest first
        content_list = content_list.order_by('-unique_access_count')
    else:
        # Default to alphabetical
        content_list = content_list.order_by(Lower('title'))

    paginator = Paginator(content_list, 10)  # Show 10 content items per page
    page = request.GET.get('page')
    contents = paginator.get_page(page)

    return render(request, 'clara_app/public_content_list.html', {'contents': contents, 'search_form': search_form})

# Show a piece of registered content. Users can add ratings and comments.    
@login_required
def content_detail(request, content_id):
    content = get_object_or_404(Content, id=content_id)
    comments = Comment.objects.filter(content=content).order_by('timestamp')
    rating = Rating.objects.filter(content=content, user=request.user).first()
    average_rating = Rating.objects.filter(content=content).aggregate(Avg('rating'))
    comment_form = CommentForm()  # initialize empty comment form
    rating_form = RatingForm()  # initialize empty rating form
    delete_form = DeleteContentForm()
    can_delete = ( content.project and request.user == content.project.user ) or request.user.userprofile.is_admin

    # Get the client's IP address
    #client_ip = get_client_ip(request)

    client_ip, is_routable = get_client_ip(request, request_header_order=['HTTP_X_FORWARDED_FOR', 'HTTP_X_REAL_IP', 'REMOTE_ADDR'])
    
    if client_ip is None:
        client_ip = '0.0.0.0'  # Fallback IP if detection fails
    
    # Check if this IP has accessed this content before
    #if not ContentAccess.objects.filter(content=content, ip_address=client_ip).exists():
    if True:
        # Increment the unique access count
        content.unique_access_count = F('unique_access_count') + 1
        content.save(update_fields=['unique_access_count'])
        content.refresh_from_db()  # Refresh the instance to get the updated count
        # Log the access
        #ContentAccess.objects.create(content=content, ip_address=client_ip)
    
    if request.method == 'POST':
        if 'delete' in request.POST:
            if can_delete:
                content.delete()
                messages.success(request, "Content successfully unregistered.")
                return redirect('content_list')
            else:
                messages.error(request, "You do not have permission to delete this content.")
                return redirect('content_detail', content_id=content_id)
        if 'submit_rating' in request.POST:
            rating_form = RatingForm(request.POST)
            if rating_form.is_valid():
                new_rating = rating_form.save(commit=False)
                new_rating.user = request.user
                new_rating.content = content
                if rating:
                    rating.rating = new_rating.rating
                    rating.save()
                    create_update(request.user, 'RATE', rating)
                else:
                    new_rating.save()
                    create_update(request.user, 'RATE', new_rating)
            
        elif 'submit_comment' in request.POST:
            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                new_comment = comment_form.save(commit=False)
                new_comment.user = request.user
                new_comment.content = content
                new_comment.save()
                create_update(request.user, 'COMMENT', new_comment)

        # Identify recipients
        # For external content, there will be no project
        if content.project and content.project.user:  
            content_creator = content.project.user
            co_owners = User.objects.filter(projectpermissions__project=content.project, projectpermissions__role='OWNER')
            previous_commenters = User.objects.filter(comment__content=content).distinct()
            recipients = set([content_creator] + list(co_owners) + list(previous_commenters))

            # Send email notification
            action = 'rating' if 'submit_rating' in request.POST else 'comment'
            send_rating_or_comment_notification_email(request, recipients, content, action)

        return redirect('content_detail', content_id=content_id)

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/content_detail.html', {
        'can_delete': can_delete,
        'delete_form': delete_form,
        'content': content,
        'rating_form': rating_form,
        'comment_form': comment_form,
        'comments': comments,
        'average_rating': average_rating['rating__avg'],
        'clara_version': clara_version
        
    })

def send_rating_or_comment_notification_email(request, recipients, content, action):
    full_url = request.build_absolute_uri(content.get_absolute_url())
    subject = f"New {action} on your content: {content.title}"
    context = {
        'action': action,
        'content_title': content.title,
        'full_url': full_url,
    }
    message = render_to_string('rating_or_comment_notification_email.html', context)
    from_email = 'clara-no-reply@unisa.edu.au'
    recipient_list = [user.email for user in recipients
                      if user.email and not user == request.user]

    if len(recipient_list) != 0:
        if os.getenv('CLARA_ENVIRONMENT') == 'unisa':
            email = EmailMessage(subject, message, from_email, recipient_list)
            email.content_subtype = "html"  # Set the email content type to HTML
            email.send()
        else:
            print(f' --- On UniSA would do: EmailMessage({subject}, {message}, {from_email}, {recipient_list}).send()')


def public_content_detail(request, content_id):
    content = get_object_or_404(Content, id=content_id)
    comments = Comment.objects.filter(content=content).order_by('timestamp')  
    average_rating = Rating.objects.filter(content=content).aggregate(Avg('rating'))

    # Print out all request headers for debugging
    headers = request.META

    # Get the client's IP address
    #client_ip, is_routable = get_client_ip(request, request_header_order=['X_FORWARDED_FOR', 'REMOTE_ADDR'], proxy_count=1)
    client_ip, is_routable = get_client_ip(request, request_header_order=['HTTP_X_FORWARDED_FOR', 'HTTP_X_REAL_IP', 'REMOTE_ADDR'])
    
    #client_ip, is_routable = get_client_ip(request, proxy_count=1)
    
    if client_ip is None:
        client_ip = '0.0.0.0'  # Fallback IP if detection fails
    
    # Check if this IP has accessed this content before
    #if not ContentAccess.objects.filter(content=content, ip_address=client_ip).exists():
    if True:
        # Increment the unique access count
        content.unique_access_count = F('unique_access_count') + 1
        content.save(update_fields=['unique_access_count'])
        content.refresh_from_db()  # Refresh the instance to get the updated count
        # Log the access
        #ContentAccess.objects.create(content=content, ip_address=client_ip)

    return render(request, 'clara_app/public_content_detail.html', {
        'content': content,
        'comments': comments,
        'average_rating': average_rating['rating__avg']
    })

# Use ipware function instead
##def get_client_ip(request):
##    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
##    if x_forwarded_for:
##        ip = x_forwarded_for.split(',')[0]
##    else:
##        ip = request.META.get('REMOTE_ADDR')
##    return ip

# Get summary tables for projects and content, broken down by language
def language_statistics(request):
    # Aggregate project counts by l2 language, forcing lowercase
    project_stats = (
        CLARAProject.objects
            .annotate(l2_lower=Lower('l2'))
            .values('l2_lower')
            .annotate(total=Count('id'))
            .order_by('-total')
    )

    # Aggregate content counts by l2 language, forcing lowercase
    content_stats = (
        Content.objects
            .annotate(l2_lower=Lower('l2'))
            .values('l2_lower')
            .annotate(total=Count('id'), total_access=Sum('unique_access_count'))
            .order_by('-total')
    )

    # Calculate the totals
    total_projects = sum(stat['total'] for stat in project_stats)
    total_contents = sum(stat['total'] for stat in content_stats)
    total_accesses = sum(
        stat['total_access']
        for stat in content_stats
        if stat['total_access'] is not None
    )

    return render(request, 'clara_app/language_statistics.html', {
        'project_stats': project_stats,
        'content_stats': content_stats,
        'total_projects': total_projects,
        'total_contents': total_contents,
        'total_accesses': total_accesses,
    })
