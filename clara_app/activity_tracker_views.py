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

@login_required
def create_activity(request):
    if request.method == 'POST':
        form = ActivityForm(request.POST)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.creator = request.user
            activity.save()
            messages.success(request, 'Activity created successfully!')
            return redirect('activity_detail', activity_id=activity.id)
    else:
        form = ActivityForm()

        return render(request, 'clara_app/create_activity.html', {'form': form})

@login_required
def activity_detail(request, activity_id):
    activity = get_object_or_404(Activity, pk=activity_id)
    user = request.user
    comments = ActivityComment.objects.filter(activity=activity).order_by('created_at')
    new_comment = None  # For POST method to assign new comment

    # Check if the user is already registered
    registration = ActivityRegistration.objects.filter(user=user, activity=activity).first()

    # Check if the user has already voted
    week_start = get_zoom_meeting_start_date()
    current_vote = ActivityVote.objects.filter(user=user, activity=activity, week=week_start).first()

    all_current_votes = ActivityVote.objects.filter(activity=activity, week=week_start)
    voting_users = {vote.user for vote in all_current_votes if vote.importance != 0}

    if request.method == 'POST':
        comment_form = ActivityCommentForm(request.POST)
        if 'submit_comment' in request.POST and comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.user = request.user
            new_comment.activity = activity
            new_comment.save()

            # Update the activity's updated_at field
            activity.updated_at = timezone.now()
            activity.save()

            notify_activity_participants(request, activity, new_comment)

            return redirect('activity_detail', activity_id=activity.id)
        elif 'register' in request.POST:
            form = ActivityRegistrationForm(request.POST, instance=registration)
            if form.is_valid():
                registration, created = ActivityRegistration.objects.update_or_create(
                    user=user,
                    activity=activity,
                    defaults={'wants_email': form.cleaned_data['wants_email']}
                )
                messages.success(request, "Your registration status has been updated.")
                return redirect('activity_detail', activity_id=activity.id)
        elif 'unregister' in request.POST and registration:
            registration.delete()
            messages.success(request, "You have been unregistered from this activity.")
            return redirect('activity_detail', activity_id=activity.id)
        elif 'update_status' in request.POST:
            if not (user == activity.creator or user.userprofile.is_admin):
                messages.error(request, "Only the person who posted the activity and admins can change the status")
                return redirect('activity_detail', activity_id=activity.id)
            status_form = ActivityStatusForm(request.POST, instance=activity)
            if status_form.is_valid():
                status_form.save()
                messages.success(request, "Activity status updated successfully.")
                return redirect('activity_detail', activity_id=activity.id)
        elif 'update_resolution' in request.POST:
            if not (user == activity.creator or user.userprofile.is_admin):
                messages.error(request, "Only the person who posted the activity and admins can change the resolution")
                return redirect('activity_detail', activity_id=activity.id)
            resolution_form = ActivityResolutionForm(request.POST, instance=activity)
            if resolution_form.is_valid():
                resolution_form.save()
                messages.success(request, "Activity resolution updated successfully.")
                return redirect('activity_detail', activity_id=activity.id)
        elif 'vote' in request.POST:
            form = ActivityVoteForm(request.POST)
            if form.is_valid():
                importance = form.cleaned_data['importance'] if 'importance' in form.cleaned_data else 0
                if importance != 0:
                    # Check if the user has already voted with the same importance this week
                    existing_vote = ActivityVote.objects.filter(user=request.user, week=week_start, importance=importance).exclude(activity=activity).first()
                    if existing_vote:
                        messages.error(request, f"You've already assigned priority '{importance}' to activity '{existing_vote.activity.title}' this week.")
                        return redirect('activity_detail', activity_id=activity.id)

                # Update historical vote
                ActivityVote.objects.update_or_create(
                    user=request.user, 
                    activity=activity, 
                    week=week_start,
                    defaults={'importance': importance}
                )
                # Update current standing vote
                CurrentActivityVote.objects.update_or_create(
                    user=request.user, 
                    activity=activity, 
                    defaults={'importance': importance}
                )

                # Update the activity's updated_at field
                activity.updated_at = timezone.now()
                activity.save()
            
                messages.success(request, "Your vote has been recorded.")
            return redirect('activity_detail', activity_id=activity.id)
    else:
        form = ActivityRegistrationForm(instance=registration)
        comment_form = ActivityCommentForm()
        vote_form = ActivityVoteForm(initial={'importance': current_vote.importance if current_vote else 0})
        status_form = ActivityStatusForm(instance=activity) 
        resolution_form = ActivityResolutionForm(instance=activity)  

    return render(request, 'clara_app/activity_detail.html', {
        'activity': activity,
        'user': user,
        'form': form,
        'registration': registration,
        'comments': comments,
        'comment_form': comment_form,
        'vote_form': vote_form,
        'status_form': status_form,  
        'resolution_form': resolution_form,
        'voting_users': voting_users,  
    })

def notify_activity_participants(request, activity, new_comment):
    # Get the activity creator
    creator = {activity.creator}

    # Get users who voted for the activity
    voters = set(User.objects.filter(
        activityvote__activity=activity
    ).distinct())

    # Get users who commented on the activity
    commenters = set(User.objects.filter(
        activitycomment__activity=activity
    ).distinct())

    # Combine all, remove duplicates
    potential_recipients = creator.union(voters, commenters)

    # Exclude users who opted out
    opted_out_users = set(ActivityRegistration.objects.filter(
        activity=activity, wants_email=False
    ).values_list('user', flat=True))

    recipients = potential_recipients - opted_out_users

    # Send notification emails, except to the new comment's author
    recipients.discard(new_comment.user)
    send_activity_comment_notification_email(request, list(recipients), activity, new_comment)

def send_activity_comment_notification_email(request, recipients, activity, comment):
    full_url = request.build_absolute_uri(activity.get_absolute_url())
    subject = f"New comment on C-LARA activity: {activity.title}"
    context = {
        'comment': comment,
        'activity_title': activity.title,
        'full_url': full_url,
    }
    message = render_to_string('activity_comment_notification_email.html', context)
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

@login_required
def list_activities(request):
    week_start = get_zoom_meeting_start_date()

    search_form = ActivitySearchForm(request.GET or None)
    query = Q()

    if search_form.is_valid():
        activity_id = search_form.cleaned_data.get('id')
        category = search_form.cleaned_data.get('category')
        status = search_form.cleaned_data.get('status')
        resolution = search_form.cleaned_data.get('resolution')
        time_period = search_form.cleaned_data.get('time_period')

        if activity_id:
            query &= Q(id=activity_id)

        else:
            if category:
                query &= Q(category=category)
            if status:
                query &= Q(status=status)
            if resolution:
                query &= Q(resolution=resolution)
            if time_period:
                # Calculate the date offset based on the selected time period
                days_ago = timezone.now() - timedelta(days=int(time_period))
                query &= Q(updated_at__gte=days_ago)

        activities = Activity.objects.filter(query)
    else:
        activities = Activity.objects.all()

    activities = annotate_and_order_activities_for_display(activities)

    return render(request, 'clara_app/list_activities.html', {
        'activities': activities,
        'search_form': search_form,
    })

def annotate_and_order_activities_for_display(activities):
    # Annotate each activity with its score based on current votes
    activities = activities.annotate(
    vote_score=Sum(
        Case(
            When(currentactivityvote__importance=1, then=Value(10)),
            When(currentactivityvote__importance=2, then=Value(7)),
            When(currentactivityvote__importance=3, then=Value(5)),
            default=Value(0),
            output_field=IntegerField()
        )
    )
    )

    # Annotate activities with a custom order for status
    activities = activities.annotate(
        status_order=Case(
            When(status='in_progress', then=Value(1)),
            When(status='posted', then=Value(2)),
            When(status='resolved', then=Value(3)),
            default=Value(4),
            output_field=IntegerField(),
        )
    )

    # Order by vote score, custom status order, and then by creation date
    return activities.order_by('status_order', '-created_at')

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def list_activities_text(request):
    # Instructions for using query parameters for filtering
    category_options = ", ".join([f"'{code}' for {name}" for code, name in ACTIVITY_CATEGORY_CHOICES])
    status_options = ", ".join([f"'{code}' for {name}" for code, name in ACTIVITY_STATUS_CHOICES])
    resolution_options = ", ".join([f"'{code}' for {name}" for code, name in ACTIVITY_RESOLUTION_CHOICES])

    instructions = (
        "To filter activities, append query parameters to the URL. "
        "For example, '?id=5' or '?time_period=30' or '?category=annotation&status=posted'. "
        "Use 'id', 'time_period', 'category', 'status', and 'resolution' as parameters. Possible values for the last three are:\n\n"
        f"Category: {category_options}\n\n"
        f"Status: {status_options}\n\n"
        f"Resolution: {resolution_options}\n\n"
    )

    week_start = get_zoom_meeting_start_date()
    search_form = ActivitySearchForm(request.GET or None)
    query = Q()

    if search_form.is_valid():
        activity_id = int(search_form.cleaned_data.get('id')) if search_form.cleaned_data.get('id') else None
        category = search_form.cleaned_data.get('category')
        status = search_form.cleaned_data.get('status')
        resolution = search_form.cleaned_data.get('resolution')
        time_period = int(search_form.cleaned_data.get('time_period')) if search_form.cleaned_data.get('time_period') else None

        if activity_id:
            query &= Q(id=activity_id)
        else:
            if category and category != 'any':
                query &= Q(category=category)
            if status and status != 'any':
                query &= Q(status=status)
            if resolution and resolution != 'any':
                query &= Q(resolution=resolution)
            if time_period:
                # Calculate the date offset based on the selected time period
                days_ago = timezone.now() - timedelta(days=int(time_period))
                query &= Q(updated_at__gte=days_ago)

    activities =  Activity.objects.filter(query)

    activities = annotate_and_order_activities_for_display(activities)

    # Prepare plain text content
    text_content = instructions + "Activities Summary\n\n"
    for activity in activities:
        text_content += f"Title: {activity.title}\n"
        text_content += f"ID: {activity.id}\n"
        text_content += f"Category: {activity.get_category_display()}\n"
        text_content += f"Description: {activity.description}\n"
        text_content += f"Status: {activity.get_status_display()}\n"
        text_content += f"Resolution: {activity.get_resolution_display()}\n"
        text_content += f"Vote Score: {activity.vote_score or 0}\n"
        text_content += f"Created At: {activity.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        text_content += f"Updated At: {activity.updated_at.strftime('%Y-%m-%d %H:%M:%S')}\n"

        # Fetch and append voters
        voters = ActivityVote.objects.filter(activity=activity, importance__gt=0).values_list('user__username', flat=True).distinct()
        if voters:
            text_content += f"Voters: {', '.join(voters)}\n"
        else:
            text_content += "No voters.\n"

        # Fetch and append comments for the activity
        comments = ActivityComment.objects.filter(activity=activity).order_by('created_at')
        if comments.exists():
            text_content += "Comments:\n"
            for comment in comments:
                text_content += f"{comment.user.username} ({comment.created_at.strftime('%Y-%m-%d %H:%M:%S')}): {comment.comment}\n"
        else:
            text_content += "No comments.\n"
        
        text_content += "\n"  # Extra newline for separation between activities

    example_of_json_text = """
Here is an example of the format to use when replying, showing one comment, one new activity and a set of votes.
There can be zero or more comments or activities, and at most one set of votes:

{
  "activityUpdates": [
    {
      "activityId": 123,
      "comments": [
        {
          "text": "This is an AI-generated comment on activity 123."
        }
      ]
    },
    {
      "newActivity": true,
      "title": "New Activity Suggested by AI",
      "category": "refactoring",
      "description": "Here is a detailed description of the new activity..."
    }
  ],
  "aiVotes": {
    "firstPreference": 123,
    "secondPreference": 124,
    "thirdPreference": 125
  }
}

"""
    text_content += example_of_json_text

    return HttpResponse(text_content, content_type="text/plain")

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def ai_activities_reply(request):
    if request.method == 'POST':
        form = AIActivitiesUpdateForm(request.POST)
        if form.is_valid():
            try:
                ai_user = User.objects.get(username='ai_user')  
                week_start = get_zoom_meeting_start_date()
                updates = json.loads(form.cleaned_data['updates_json'])
                
                with transaction.atomic():
                    for update in updates['activityUpdates']:
                        if 'comments' in update and 'activityId' in update:
                            activity = Activity.objects.get(id=update['activityId'])
                            for comment in update['comments']:
                                new_comment = ActivityComment.objects.create(activity=activity, user=ai_user, comment=comment['text'])
                                # Notify relevant users about the new comment
                                notify_activity_participants(request, activity, new_comment)
                        elif 'newActivity' in update:
                            Activity.objects.create(
                                title=update['title'],
                                category=update['category'],
                                description=update['description'],
                                creator=ai_user
                            )

                # Process AI votes if there are any
                if 'aiVotes' in updates:
                    ai_votes = updates['aiVotes']
                    for importance, activity_id in enumerate([ai_votes.get('firstPreference'),
                                                              ai_votes.get('secondPreference'),
                                                              ai_votes.get('thirdPreference')],
                                                             start=1):
                        if activity_id:
                            # Check if AI has already voted with the same importance this week for a different activity
                            existing_vote = ActivityVote.objects.filter(
                                user=ai_user,
                                week=week_start,
                                importance=importance
                            ).exclude(activity_id=activity_id).first()
                            
                            if existing_vote:
                                # If an existing vote is found, it might be appropriate to either skip updating this vote,
                                # or to implement some logic to handle this case (e.g., reassign votes).
                                # For now, let's just warn and skip to the next vote to maintain data integrity.
                                messages.error(request, f"AI user has already voted with importance {importance} for activity {existing_vote.activity.id} this week.")
                                continue

                            # Save or update vote, ensuring uniqueness of importance per week for the AI
                            ActivityVote.objects.update_or_create(
                                user=ai_user,
                                activity_id=activity_id,
                                week=week_start,
                                defaults={'importance': importance}
                            )
                            # Update current standing vote
                            CurrentActivityVote.objects.update_or_create(
                                user=ai_user, 
                                activity_id=activity_id, 
                                defaults={'importance': importance}
                            )
                    
                messages.success(request, "Activities have been successfully updated.")
                return redirect('list_activities')
            except Exception as e:
                messages.error(request, f"Failed to process updates: {str(e)}")
    else:
        form = AIActivitiesUpdateForm()

    return render(request, 'clara_app/ai_activities_reply.html', {'form': form})
