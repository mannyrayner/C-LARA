from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, FileResponse, JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.core.paginator import Paginator
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
from django.urls import reverse

from .models import UserProfile, FriendRequest, UserConfiguration, LanguageMaster, Content, ContentAccess, TaskUpdate, Update, ReadingHistory
from .models import SatisfactionQuestionnaire, FundingRequest, Acknowledgements, Activity, ActivityRegistration, ActivityComment, ActivityVote, CurrentActivityVote
from .models import CLARAProject, HumanAudioInfo, PhoneticHumanAudioInfo, ProjectPermissions, CLARAProjectAction, Comment, Rating, FormatPreferences
from django.contrib.auth.models import User

from django_q.tasks import async_task
from django_q.models import Task

from .forms import RegistrationForm, UserForm, UserSelectForm, UserProfileForm, FriendRequestForm, AdminPasswordResetForm, ProjectSelectionFormSet, UserConfigForm
from .forms import AssignLanguageMasterForm, AddProjectMemberForm, FundingRequestForm, FundingRequestSearchForm, ApproveFundingRequestFormSet, UserPermissionsForm
from .forms import ContentSearchForm, ContentRegistrationForm, AcknowledgementsForm, UnifiedSearchForm
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
from .utils import get_user_config, user_has_open_ai_key_or_credit, create_internal_project_id, store_api_calls, make_asynch_callback_and_report_id
from .utils import get_user_api_cost, get_project_api_cost, get_project_operation_costs, get_project_api_duration, get_project_operation_durations
from .utils import user_is_project_owner, user_has_a_project_role, user_has_a_named_project_role, language_master_required
from .utils import post_task_update_in_db, get_task_updates, has_saved_internalised_and_annotated_text
from .utils import uploaded_file_to_file, create_update, current_friends_of_user, get_phase_up_to_date_dict
from .utils import send_mail_or_print_trace, get_zoom_meeting_start_date, get_previous_week_start_date

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

from .clara_internalise import internalize_text
from .clara_grapheme_phoneme_resources import grapheme_phoneme_resources_available
from .clara_conventional_tagging import fully_supported_treetagger_language
from .clara_chinese import is_chinese_language
from .clara_annotated_images import make_uninstantiated_annotated_image_structure
from .clara_tts_api import tts_engine_type_supports_language
from .clara_chatgpt4 import call_chat_gpt4, interpret_chat_gpt4_response_as_json, call_chat_gpt4_image, call_chat_gpt4_interpret_image
from .clara_classes import TemplateError, InternalCLARAError, InternalisationError
#from .clara_utils import _use_orm_repositories
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

config = get_config()
logger = logging.getLogger(__name__)

def redirect_login(request):
    return redirect('login')

# Create a new account    
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()  # This will save username and password.
            user.email = form.cleaned_data.get('email')  # This will save email.
            user.save()  # Save the user object again.
            
            # Create the UserProfile instance
            UserProfile.objects.create(user=user)

            # Create the UserConfiguration instance
            UserConfiguration.objects.create(user=user)

            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'clara_app/register.html', {'form': form})


# Welcome screen
def home(request):
    
    #return HttpResponse("Welcome to C-LARA!")
    return redirect('home_page')

@login_required
def home_page(request):
    time_period = DEFAULT_RECENT_TIME_PERIOD
    search_form = UnifiedSearchForm(request.GET or None)
    time_period_query = Q()

    if search_form.is_valid() and search_form.cleaned_data.get('time_period'):
        time_period = int(search_form.cleaned_data['time_period'])

    days_ago = timezone.now() - timedelta(days=time_period)
    time_period_query = Q(updated_at__gte=days_ago)

    contents = Content.objects.filter(time_period_query).order_by('-updated_at')
    
    activities = Activity.objects.filter(time_period_query)
    activities = annotate_and_order_activities_for_home_page(activities)

    return render(request, 'clara_app/home_page.html', {
        'contents': contents,
        'activities': activities,
        'search_form': search_form
    })

def annotate_and_order_activities_for_home_page(activities):
    # Annotate activities with a custom order for status
    activities = activities.annotate(
        status_order=Case(
            When(status='in_progress', then=Value(1)),
            When(status='resolved', then=Value(2)),
            When(status='posted', then=Value(3)),
            default=Value(4),
            output_field=IntegerField(),
        )
    )

    # Order by vote score, custom status order, and then by creation date
    return activities.order_by('status_order', '-created_at')

# Show user profile
@login_required
def profile(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/profile.html', {'profile': profile, 'email': request.user.email, 'clara_version': clara_version})

# Edit user profile
@login_required
def edit_profile(request):
    if request.method == 'POST':
        u_form = UserForm(request.POST, instance=request.user)
        p_form = UserProfileForm(request.POST, request.FILES, instance=request.user.userprofile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, f'Your account has been updated!')
            return redirect('profile')
    else:
        u_form = UserForm(instance=request.user)
        p_form = UserProfileForm(instance=request.user.userprofile)

    clara_version = get_user_config(request.user)['clara_version']

    context = {
        'u_form': u_form,
        'p_form': p_form,
        'clara_version': clara_version
    }

    return render(request, 'clara_app/edit_profile.html', context)

def send_friend_request_notification_email(request, other_user):
    friends_url = request.build_absolute_uri(reverse('friends'))
    subject = f"New C-LARA friend request"
    context = {
        'user': request.user,
        'other_user': other_user,
        'friends_url': friends_url,
    }
    message = render_to_string('friend_request_notification_email.html', context)
    from_email = 'clara-no-reply@unisa.edu.au'
    recipient_list = [ other_user.email ]

    if os.getenv('CLARA_ENVIRONMENT') == 'unisa':
        email = EmailMessage(subject, message, from_email, recipient_list)
        email.content_subtype = "html"  # Set the email content type to HTML
        email.send()
    else:
        print(f' --- On UniSA would do: EmailMessage({subject}, {message}, {from_email}, {recipient_list}).send()')

# External user profile view
def external_profile(request, user_id):
    profile_user = get_object_or_404(User, pk=user_id)
    profile = get_object_or_404(UserProfile, user=profile_user)

    # Check if the profile is private
    if profile.is_private and request.user != user:
        return render(request, 'clara_app/external_profile_private.html', {'username': user.username})

    # Check the friend status
    friend_request = FriendRequest.objects.filter(
        (Q(sender=request.user) & Q(receiver=profile_user)) | 
        (Q(sender=profile_user) & Q(receiver=request.user))
    ).first()

    if request.method == 'POST':
        form = FriendRequestForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            friend_request_id = form.cleaned_data.get('friend_request_id')

            if action == 'send':
                FriendRequest.objects.create(sender=request.user, receiver=profile_user, status='Sent')
                send_friend_request_notification_email(request, profile_user)
            elif action in ['cancel', 'reject', 'unfriend'] and friend_request_id:
                FriendRequest.objects.filter(id=friend_request_id).delete()
            elif action == 'accept' and friend_request_id:
                friend_request_query_set = FriendRequest.objects.filter(id=friend_request_id)
                friend_request_query_set.update(status='Accepted')

                # Create an Update record for the update feed
                create_update(request.user, 'FRIEND', friend_request_query_set.first())

            return redirect('external_profile', user_id=user_id)

    else:
        form = FriendRequestForm()

    clara_version = get_user_config(request.user)['clara_version']

    return render(request, 'clara_app/external_profile.html', {
        'profile_user': profile_user,
        'profile': profile,
        'email': profile_user.email,
        'friend_request': friend_request,
        'form': form,
        'clara_version': clara_version
    })

@login_required
def list_users(request):
    users = User.objects.all().order_by('-date_joined')  # Assuming you want the newest users first
    paginator = Paginator(users, 10)  # Show 10 users per page

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'clara_app/list_users.html', {'page_obj': page_obj})

@login_required
def friends(request):
    # Get the current user's profile
    user_profile = request.user.userprofile

    # Get incoming and outgoing friend requests
    incoming_requests = FriendRequest.objects.filter(receiver=request.user, status='Sent')
    outgoing_requests = FriendRequest.objects.filter(sender=request.user, status='Sent')

    # Get current friends 
    current_friends = current_friends_of_user(request.user)

    clara_version = get_user_config(request.user)['clara_version']

    return render(request, 'clara_app/friends.html', {
        'user_profile': user_profile,
        'incoming_requests': incoming_requests,
        'outgoing_requests': outgoing_requests,
        'current_friends': current_friends,
        'clara_version': clara_version,
    })

# Show the update feed
@login_required
def update_feed(request):
    # Retrieve updates related to the user's friends and their own actions
    friends = current_friends_of_user(request.user)
    #print(f'Friends: {friends}')
    updates = Update.objects.filter(
        Q(user__in=friends) | Q(user=request.user)
    ).order_by('-timestamp')[:50]  # Get the latest 50 updates

    #print(f'Updates:')
    #for update in updates:
    #    print(update)

    valid_updates = [ update for update in updates if valid_update_for_update_feed(update) ]

    clara_version = get_user_config(request.user)['clara_version']

    return render(request, 'clara_app/update_feed.html', {'updates': valid_updates, 'clara_version': clara_version})

# Check that the updates are such that we can render them in the template
def valid_update_for_update_feed(update):
##              {% if update.update_type == 'FRIEND' %}
##		   <a href="{% url 'external_profile' update.content_object.sender.id %}">{{ update.content_object.sender.username }}</a>
##                   is now friends with 
##                   <a href="{% url 'external_profile' update.content_object.receiver.id %}">{{ update.content_object.receiver.username }}</a>
    if update.update_type == 'FRIEND':
        return isinstance(update.content_object, FriendRequest) and \
               isinstance(update.content_object.sender, User) and \
               isinstance(update.content_object.receiver, User)
##		{% elif update.update_type == 'RATE' %}
##		   <a href="{% url 'external_profile' update.content_object.user.id %}">{{ update.content_object.user.username }}</a>
##		   gave {{ update.content_object.rating }} stars to 
##		   <a href="{% url 'content_detail' update.content_object.content.id %}">{{ update.content_object.content.title }}</a>
    elif update.update_type == 'RATE':
        return isinstance(update.content_object, Rating) and \
               isinstance(update.content_object.user, User) and \
               isinstance(update.content_object.content, Content)
##		{% elif update.update_type == 'COMMENT' %}
##		   <a href="{% url 'external_profile' update.content_object.user.id %}">{{ update.content_object.user.username }}</a>
##		   posted a comment on 
##		   <a href="{% url 'content_detail' update.content_object.content.id %}">{{ update.content_object.content.title }}</a>:</br>
##		   "{{ update.content_object.comment }}"
    elif update.update_type == 'COMMENT':
        return isinstance(update.content_object, Comment) and \
               isinstance(update.content_object.user, User) and \
               isinstance(update.content_object.content, Content)
##		{% elif update.update_type == 'PUBLISH' %}
##		   <a href="{% url 'external_profile' update.user.id %}">{{ update.user.username }}</a>
##		   published 
##		   <a href="{% url 'content_detail' update.content_object.id %}">{{ update.content_object.title }}</a>
    elif update.update_type == 'PUBLISH':
        return isinstance(update.content_object, Comment) and \
               isinstance(update.user, User) and \
               isinstance(update.content_object, Content)
    else:
        print(f'Warning: bad update: {update}')
        return False


def user_config(request):
    # In the legacy case, we won't have a UserConfiguration object yet, so create one if necessary
    user_config, created = UserConfiguration.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserConfigForm(request.POST, instance=user_config)
        if form.is_valid():
            #open_ai_api_key = form.cleaned_data['open_ai_api_key']
            #print(f'open_ai_api_key = {open_ai_api_key}')
            form.save()
            messages.success(request, f'Configuration information has been updated')
            return redirect('user_config')
    else:
        form = UserConfigForm(instance=user_config)

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/user_config.html', {'form': form, 'clara_version': clara_version})

# Credit balance for money spent on API calls

@login_required
def credit_balance(request):
    credit_balance = request.user.userprofile.credit

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/credit_balance.html', {'credit_balance': credit_balance, 'clara_version': clara_version})

# Allow an admin to manually reset the password on an account
@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def admin_password_reset(request):
    if request.method == 'POST':
        form = AdminPasswordResetForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            new_password = form.cleaned_data['new_password']
            try:
                user.set_password(new_password)
                user.save()
                messages.success(request, f"Password for {user.username} has been updated.")
                return redirect('admin_password_reset')
            except User.DoesNotExist:
                messages.error(request, "User not found.")
    else:
        form = AdminPasswordResetForm()

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/admin_password_reset.html', {'form': form, 'clara_version': clara_version})

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def manage_user_permissions(request):
    user_select_form = UserSelectForm(request.POST or None)
    permissions_form = None
    selected_user_id = None  # Initialize selected_user_id

    if request.method == 'POST' and 'select_user' in request.POST:
        if user_select_form.is_valid():
            selected_user = user_select_form.cleaned_data['user']
            selected_user_id = selected_user.id  # Store the selected user's ID
            permissions_form = UserPermissionsForm(instance=selected_user.userprofile)
    elif request.method == 'POST':
        selected_user_id = request.POST.get('selected_user_id')  # Retrieve the selected user's ID from the POST data
        selected_user_profile = get_object_or_404(UserProfile, user__id=selected_user_id)
        permissions_form = UserPermissionsForm(request.POST, instance=selected_user_profile)
        if permissions_form.is_valid():
            permissions_form.save()
            messages.success(request, 'User permissions updated successfully.')
            return redirect('manage_user_permissions')
    else:
        user_select_form = UserSelectForm()

    return render(request, 'clara_app/manage_user_permissions.html', {
        'user_select_form': user_select_form,
        'permissions_form': permissions_form,
        'selected_user_id': selected_user_id,  # Pass selected_user_id to the template
    })


# Add credit to account
@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def add_credit(request):
    if request.method == 'POST':
        form = AddCreditForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            credit = form.cleaned_data['credit']
            user.userprofile.credit += credit
            user.userprofile.save()
            messages.success(request, "Credit added successfully")
    else:
        form = AddCreditForm()

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/add_credit.html', {'form': form, 'clara_version': clara_version})

# Transfer credit to another account
@login_required
def transfer_credit(request):
    if request.method == 'POST':
        form = AddCreditForm(request.POST)
        if form.is_valid():
            recipient_username = form.cleaned_data['user']
            amount = form.cleaned_data['credit']

            # Check if recipient exists
            try:
                recipient = User.objects.get(username=recipient_username)
            except User.DoesNotExist:
                messages.error(request, 'User not found.')
                return render(request, 'clara_app/transfer_credit.html', {'form': form})

            # Check if user has enough credit
            if request.user.userprofile.credit < amount:
                messages.error(request, 'Insufficient credit.')
                return render(request, 'clara_app/transfer_credit.html', {'form': form})

            # Generate a unique confirmation code
            confirmation_code = str(uuid.uuid4())

            # Store the transfer details and confirmation code in the session
            request.session['credit_transfer'] = {
                'recipient_id': recipient.id,
                'amount': str(amount),  # Convert Decimal to string for session storage
                'confirmation_code': confirmation_code,
            }

            # Send confirmation email
            recipient_email = request.user.email
            send_mail_or_print_trace(
                'Confirm Credit Transfer',
                f'Please confirm your credit transfer of {amount} to {recipient.username} using this code: {confirmation_code}',
                'clara-no-reply@unisa.edu.au',
                [ recipient_email ],
                fail_silently=False,
            )

            anonymised_email = recipient_email[0:3] + '*' * ( len(recipient_email) - 10 ) + recipient_email[-7:]
            messages.info(request, f'A confirmation email has been sent to {anonymised_email}. Please check your email to complete the transfer.')
            return redirect('confirm_transfer')
    else:
        form = AddCreditForm()

    clara_version = get_user_config(request.user)['clara_version']

    return render(request, 'clara_app/transfer_credit.html', {'form': form, 'clara_version': clara_version})

@login_required
def confirm_transfer(request):
    if request.method == 'POST':
        form = ConfirmTransferForm(request.POST)
        if form.is_valid():
            confirmation_code = form.cleaned_data['confirmation_code']

            # Retrieve transfer details from the session
            transfer_details = request.session.get('credit_transfer')
            if not transfer_details:
                messages.error(request, 'Transfer details not found.')
                return redirect('transfer_credit')

            # Check if the confirmation code matches
            if confirmation_code != transfer_details['confirmation_code']:
                messages.error(request, 'Invalid confirmation code.')
                return render(request, 'confirm_transfer.html', {'form': form})

            # Complete the transfer
            recipient = User.objects.get(id=transfer_details['recipient_id'])
            amount = Decimal(transfer_details['amount'])
            request.user.userprofile.credit -= amount
            request.user.userprofile.save()
            recipient.userprofile.credit += amount
            recipient.userprofile.save()

            # Clear the transfer details from the session
            del request.session['credit_transfer']

            messages.success(request, f'Credit transfer of USD {amount} to {recipient.username} completed successfully.')
            return redirect('transfer_credit')
    else:
        form = ConfirmTransferForm()

    clara_version = get_user_config(request.user)['clara_version']

    return render(request, 'clara_app/confirm_transfer.html', {'form': form, 'clara_version': clara_version})

##def initialise_orm_repositories_from_non_orm(callback=None):
##    try:
##        post_task_update(callback, f"--- Initialising ORM repositories from non-ORM repositories")
##        
##        post_task_update(callback, f"--- Initialising ORM audio repository")
##        tts_repo = AudioRepositoryORM(initialise_from_non_orm=True, callback=callback)
##        
##        post_task_update(callback, f"--- Initialising ORM image repository")
##        image_repo = ImageRepositoryORM(initialise_from_non_orm=True, callback=callback)
##
##        post_task_update(callback, f"--- Initialising phonetic lexicon repository")
##        phonetic_lexicon_repo = PhoneticLexiconRepositoryORM(initialise_from_non_orm=True, callback=callback)
##        
##        post_task_update(callback, f"finished")
##    except Exception as e:
##        post_task_update(callback, f'Error initialising from non-ORM repositories: "{str(e)}"\n{traceback.format_exc()}')
##        post_task_update(callback, f"error")
    
# Delete cached TTS data for language   
##@login_required
##@user_passes_test(lambda u: u.userprofile)
##def initialise_orm_repositories(request):
##    if request.method == 'POST':
##        form = InitialiseORMRepositoriesForm(request.POST)
##        if form.is_valid():
##            
##            # Create a unique ID to tag messages posted by this task and a callback
##            task_type = f'initialise_orm_repositories'
##            callback, report_id = make_asynch_callback_and_report_id(request, task_type)
##
##            async_task(initialise_orm_repositories_from_non_orm, callback=callback)
##            print(f'--- Started initialise task')
##            #Redirect to the monitor view, passing report ID as parameter
##            return redirect('initialise_orm_repositories_monitor', report_id)
##
##    else:
##        form = InitialiseORMRepositoriesForm()
##
##    clara_version = get_user_config(request.user)['clara_version']
##    
##    return render(request, 'clara_app/initialise_orm_repositories.html', {
##        'form': form, 'clara_version': clara_version
##    })

# This is the API endpoint that the JavaScript will poll
##@login_required
##@user_passes_test(lambda u: u.userprofile.is_admin)
##def initialise_orm_repositories_status(request, report_id):
##    messages = get_task_updates(report_id)
##    print(f'{len(messages)} messages received')
##    if 'error' in messages:
##        status = 'error'
##    elif 'finished' in messages:
##        status = 'finished'  
##    else:
##        status = 'unknown'    
##    return JsonResponse({'messages': messages, 'status': status})

##@login_required
##@user_passes_test(lambda u: u.userprofile.is_admin)
##def initialise_orm_repositories_monitor(request, report_id):
##
##    clara_version = get_user_config(request.user)['clara_version']
##    
##    return render(request, 'clara_app/initialise_orm_repositories_monitor.html',
##                  {'report_id': report_id, 'clara_version': clara_version})
##
##@login_required
##@user_passes_test(lambda u: u.userprofile.is_admin)
##def initialise_orm_repositories_complete(request, status):
##    if request.method == 'POST':
##        form = InitialiseORMRepositoriesForm(request.POST)
##        if form.is_valid():
##            
##            task_type = f'initialise_orm_repositories'
##            callback, report_id = make_asynch_callback_and_report_id(request, task_type)
##
##            async_task(initialise_orm_repositories_from_non_orm, callback=callback)
##            print(f'--- Started initialise task')
##            #Redirect to the monitor view, passing the task ID and report ID as parameters
##            return redirect('initialise_orm_repositories_monitor', report_id)
##    else:
##        if status == 'error':
##            messages.error(request, f"Something went wrong when initialising the ORM repositories. Try looking at the 'Recent task updates' view")
##        else:
##            messages.success(request, f'Initialised ORM repositories')
##
##        form = InitialiseORMRepositoriesForm()
##
##        clara_version = get_user_config(request.user)['clara_version']
##
##        return render(request, 'clara_app/initialise_orm_repositories.html',
##                      { 'form': form, 'clara_version': clara_version, } )


def delete_tts_data_for_language(language, callback=None):
    post_task_update(callback, f"--- Starting delete task for language {language}")
    tts_annotator = AudioAnnotator(language, callback=callback)
    tts_annotator.delete_entries_for_language(callback=callback)

# Delete cached TTS data for language   
@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def delete_tts_data(request):
    if request.method == 'POST':
        form = DeleteTTSDataForm(request.POST)
        if form.is_valid():
            language = form.cleaned_data['language']
            
            # Create a unique ID to tag messages posted by this task and a callback
            task_type = f'delete_tts'
            callback, report_id = make_asynch_callback_and_report_id(request, task_type)

            async_task(delete_tts_data_for_language, language, callback=callback)
            print(f'--- Started delete task {language}')
            #Redirect to the monitor view, passing the language and report ID as parameters
            return redirect('delete_tts_data_monitor', language, report_id)

    else:
        form = DeleteTTSDataForm()

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/delete_tts_data.html', {
        'form': form, 'clara_version': clara_version
    })

# This is the API endpoint that the JavaScript will poll
@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def delete_tts_data_status(request, report_id):
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
@user_passes_test(lambda u: u.userprofile.is_admin)
def delete_tts_data_monitor(request, language, report_id):

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/delete_tts_data_monitor.html',
                  {'language': language, 'report_id': report_id, 'clara_version': clara_version})

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def delete_tts_data_complete(request, language, status):
    if request.method == 'POST':
        form = DeleteTTSDataForm(request.POST)
        if form.is_valid():
            language = form.cleaned_data['language']
            
            task_type = f'delete_tts'
            callback, report_id = make_asynch_callback_and_report_id(request, task_type)

            async_task(delete_tts_data_for_language, language, callback=callback)
            print(f'--- Started delete task for {language}')
            #Redirect to the monitor view, passing the task ID and report ID as parameters
            return redirect('delete_tts_data_monitor', language, report_id)
    else:
        if status == 'error':
            messages.error(request, f"Something went wrong when deleting TTS data for {language}. Try looking at the 'Recent task updates' view")
        else:
            messages.success(request, f'Deleted TTS data for {language}')

        form = DeleteTTSDataForm()

        clara_version = get_user_config(request.user)['clara_version']

        return render(request, 'clara_app/delete_tts_data.html',
                      { 'form': form, 'clara_version': clara_version, } )

# Select a project and make yourself co-owner of it (admin only)
@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def admin_project_ownership(request):
    search_form = ProjectSearchForm(request.GET or None)
    query = Q()

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

    if request.method == 'POST':
        formset = ProjectSelectionFormSet(request.POST)
        if formset.is_valid():
            for form in formset:
                if form.cleaned_data.get('select'):
                    project_id = form.cleaned_data.get('project_id')
                    selected_project = CLARAProject.objects.get(pk=project_id)
                    ProjectPermissions.objects.create(user=request.user, project=selected_project, role='OWNER')
                    messages.success(request, f"You are now a co-owner of the project: {selected_project.title}")
            return redirect('admin_project_ownership')
    else:
        projects_info = [{'id': project.id, 'title': project.title, 'l2': project.l2} for project in projects]
        initial_data = [{'project_id': project['id']} for project in projects_info]
        formset = ProjectSelectionFormSet(initial=initial_data)

    clara_version = get_user_config(request.user)['clara_version']

    return render(request, 'clara_app/admin_project_ownership.html', {
        'formset': formset,
        'projects_info': projects_info,
        'search_form': search_form,
        'clara_version': clara_version
    })


# Manage users declared as 'language masters', adding or withdrawing the 'language master' privilege   
@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def manage_language_masters(request):
    language_masters = LanguageMaster.objects.all()
    if request.method == 'POST':
        form = AssignLanguageMasterForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            language = form.cleaned_data['language']
            LanguageMaster.objects.get_or_create(user=user, language=language)
            return redirect('manage_language_masters')
    else:
        form = AssignLanguageMasterForm()

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/manage_language_masters.html', {
        'language_masters': language_masters,
        'form': form, 'clara_version': clara_version,
    })

# Remove someone as a language master, asking for confirmation first
@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def remove_language_master(request, pk):
    language_master = get_object_or_404(LanguageMaster, pk=pk)
    if request.method == 'POST':
        language_master.delete()
        return redirect('manage_language_masters')
    else:

        clara_version = get_user_config(request.user)['clara_version']
        
        return render(request, 'clara_app/remove_language_master_confirm.html', {'language_master': language_master, 'clara_version': clara_version})

# Display recent task update messages
@login_required
def view_task_updates(request):
    time_threshold = timezone.now() - timedelta(minutes=60)
    user_id = request.user.username
    updates = TaskUpdate.objects.filter(timestamp__gte=time_threshold, user_id=user_id).order_by('-timestamp')

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/view_task_updates.html', {'updates': updates, 'clara_version': clara_version})

# Allow a language master to edit a phonetic lexicon
@login_required
@language_master_required
def edit_phonetic_lexicon(request):
    orthography_repo = PhoneticOrthographyRepository()
    phonetic_lexicon_repo = PhoneticLexiconRepositoryORM()
    #phonetic_lexicon_repo = PhoneticLexiconRepositoryORM() if _use_orm_repositories else PhoneticLexiconRepository()
    plain_lexicon_formset = None
    aligned_lexicon_formset = None
    grapheme_phoneme_formset = None
    accents_formset = None
    if request.method == 'POST':
        form = PhoneticLexiconForm(request.POST, user=request.user)
        grapheme_phoneme_formset = GraphemePhonemeCorrespondenceFormSet(request.POST, prefix='grapheme_phoneme')
        accents_formset = AccentCharacterFormSet(request.POST, prefix='accents')
        plain_lexicon_formset = PlainPhoneticLexiconEntryFormSet(request.POST, prefix='plain')
        aligned_lexicon_formset = AlignedPhoneticLexiconEntryFormSet(request.POST, prefix='aligned')
        if not form.is_valid():
            messages.error(request, f"Error in form: {form.errors}")
        else:
            action = request.POST.get('action')
            language = form.cleaned_data['language']
            encoding = form.cleaned_data['encoding']
            display_grapheme_to_phoneme_entries = form.cleaned_data['display_grapheme_to_phoneme_entries']
            display_new_plain_lexicon_entries = form.cleaned_data['display_new_plain_lexicon_entries']
            display_new_aligned_lexicon_entries = form.cleaned_data['display_new_aligned_lexicon_entries']
            display_approved_plain_lexicon_entries = form.cleaned_data['display_approved_plain_lexicon_entries']
            display_approved_aligned_lexicon_entries = form.cleaned_data['display_approved_aligned_lexicon_entries']
            if action == 'Refresh':
                if language:
                    encoding = phonetic_lexicon_repo.get_encoding_for_language(language)
                    #letter_groups, accents = orthography_repo.get_text_entry(language)
                    messages.success(request, f"Current data for {language} loaded")
            if action == 'Save':
                if encoding and encoding != phonetic_lexicon_repo.get_encoding_for_language(language):
                    phonetic_lexicon_repo.set_encoding_for_language(language, encoding)
                    messages.success(request, "Language encoding saved")
                if display_grapheme_to_phoneme_entries:
                    grapheme_phoneme_data = []
                    accents_data = []
                    n_orthography_errors = 0
                    for grapheme_phoneme_form in grapheme_phoneme_formset:
                        if grapheme_phoneme_form.is_valid():
                            grapheme_variants = grapheme_phoneme_form.cleaned_data.get('grapheme_variants')
                            phonemes = grapheme_phoneme_form.cleaned_data.get('phonemes')
                            # Ignore null items
                            if grapheme_variants or phonemes:
                                grapheme_phoneme_item = { 'grapheme_variants': grapheme_variants, 'phonemes': phonemes }
                                consistent, error_message = orthography_repo.consistent_orthography_item(grapheme_phoneme_item)
                                if consistent:
                                    grapheme_phoneme_data += [ grapheme_phoneme_item ]
                                else:
                                    messages.error(request, f"Error when trying to save grapheme/phoneme data: {error_message}")
                                    n_orthography_errors += 1
                    for accents_form in accents_formset:
                         if accents_form.is_valid():
                            accent = accents_form.cleaned_data.get('unicode_value')
                            # Ignore null items
                            if accent:
                                accent_item = { 'unicode_value': accent }
                                consistent, error_message = orthography_repo.consistent_accent_item(accent_item)
                                if consistent:
                                    accents_data += [ accent_item ]
                                else:
                                    messages.error(request, f"Error when trying to save grapheme/phoneme data: {error_message}")
                                    n_orthography_errors += 1
                    if n_orthography_errors == 0:
                        orthography_repo.save_structured_data(language, grapheme_phoneme_data, accents_data)
                        messages.success(request, f"Saved grapheme/phoneme data: {len(grapheme_phoneme_data)} grapheme/phoneme items, {len(accents_data)} accent items")
                        orthography_result, orthography_details = phonetic_lexicon_repo.load_and_initialise_aligned_lexicon_from_orthography_data(grapheme_phoneme_data, language)
                        #print(f'orthography_result = {orthography_result}, orthography_details = {orthography_details}')
                        if orthography_result == 'error':
                            messages.error(request, f"Error when converting grapheme/phoneme data into aligned lexicon: {orthography_details}")
                        else:
                            messages.success(request, f"Grapheme/phoneme data also converted into aligned lexicon: {orthography_details}")
                    else:
                        messages.error(request, f"No grapheme/phoneme data saved")
                plain_words_to_save = []
                plain_words_saved = []
                plain_words_to_delete = []
                plain_words_deleted = []
                for lexicon_form in plain_lexicon_formset:
                    if lexicon_form.is_valid():
                        approve = lexicon_form.cleaned_data.get('approve')
                        delete = lexicon_form.cleaned_data.get('delete')
                        word = lexicon_form.cleaned_data.get('word')
                        phonemes = lexicon_form.cleaned_data.get('phonemes')
                        record = { 'word': word, 'phonemes': phonemes }
                        if approve:
                            plain_words_to_save.append(record) 
                        elif delete:
                            plain_words_to_delete.append(record)
                if len(plain_words_to_save) != 0:
                    phonetic_lexicon_repo.record_reviewed_plain_entries(plain_words_to_save, language)
                    plain_words_saved = [ item['word'] for item in plain_words_to_save ]
                    messages.success(request, f"{len(plain_words_saved)} plain lexicon entries saved: {', '.join(plain_words_saved)}")
                if len(plain_words_to_delete) != 0:
                    phonetic_lexicon_repo.delete_plain_entries(plain_words_to_delete, language)
                    plain_words_deleted = [ item['word'] for item in plain_words_to_delete ]
                    messages.success(request, f"{len(plain_words_deleted)} plain lexicon entries deleted: {', '.join(plain_words_deleted)}")
                    
                aligned_words_to_save = []
                aligned_words_saved = []
                aligned_words_to_delete = []
                aligned_words_deleted = []
                for aligned_lexicon_form in aligned_lexicon_formset:
                    if aligned_lexicon_form.is_valid():
                        approve = aligned_lexicon_form.cleaned_data.get('approve')
                        delete = aligned_lexicon_form.cleaned_data.get('delete')
                        word = aligned_lexicon_form.cleaned_data.get('word')
                        phonemes = aligned_lexicon_form.cleaned_data.get('phonemes')
                        aligned_graphemes = aligned_lexicon_form.cleaned_data.get('aligned_graphemes')
                        aligned_phonemes = aligned_lexicon_form.cleaned_data.get('aligned_phonemes')
                        record = { 'word': word, 'phonemes': phonemes, 'aligned_graphemes': aligned_graphemes, 'aligned_phonemes': aligned_phonemes }
                        if approve:
                            consistent, error_message = phonetic_lexicon_repo.consistent_aligned_phonetic_lexicon_entry(word, phonemes, aligned_graphemes, aligned_phonemes)
                            if not consistent:
                                messages.error(request, f"Error when trying to save data for '{word}': {error_message}")
                            else:
                                aligned_words_to_save.append(record) 
                        elif delete:
                            aligned_words_to_delete.append(record)
                if len(aligned_words_to_save) != 0:
                    phonetic_lexicon_repo.record_reviewed_aligned_entries(aligned_words_to_save, language)
                    aligned_words_saved = [ item['word'] for item in aligned_words_to_save ]
                    messages.success(request, f"{len(aligned_words_saved)} aligned lexicon entries saved: {', '.join(aligned_words_saved)}")
                if len(aligned_words_to_delete) != 0:
                    phonetic_lexicon_repo.delete_aligned_entries(aligned_words_to_delete, language)
                    aligned_words_deleted = [ item['word'] for item in aligned_words_to_delete ]
                    messages.success(request, f"{len(aligned_words_deleted)} aligned lexicon entries deleted: {', '.join(aligned_words_deleted)}")
                    
                if ( display_new_plain_lexicon_entries or display_new_aligned_lexicon_entries ) and \
                   len(plain_words_saved) == 0 and len(aligned_words_saved) == 0 and len(plain_words_deleted) == 0 and len(aligned_words_deleted) == 0:
                    messages.error(request, f"Warning: found no entries marked as approved or deleted, did not save anything")
            elif action == 'Upload':
                if 'aligned_lexicon_file' in request.FILES:
                    aligned_file_path = uploaded_file_to_file(request.FILES['aligned_lexicon_file'])
                    aligned_result, aligned_details = phonetic_lexicon_repo.load_and_initialise_aligned_lexicon(aligned_file_path, language)
                    if aligned_result == 'error':
                        messages.error(request, f"Error when uploading aligned phonetic lexicon: {aligned_details}")
                    else:
                        messages.success(request, f"Aligned phonetic lexicon uploaded successfully: {aligned_details}")
                if 'plain_lexicon_file' in request.FILES:
                    plain_file_path = uploaded_file_to_file(request.FILES['plain_lexicon_file'])
                    # If we're on Heroku, we need to copy the zipfile to S3 so that the worker process can get it
                    copy_local_file_to_s3_if_necessary(plain_file_path)

                    task_type = f'import_phonetic_lexicon'
                    callback, report_id = make_asynch_callback_and_report_id(request, task_type)

                    async_task(upload_and_install_plain_phonetic_lexicon, plain_file_path, language, callback=callback)

                    # Redirect to the monitor view, passing the language and report ID as parameters
                    return redirect('import_phonetic_lexicon_monitor', language, report_id)
                        
            if not language:
                form = None
                grapheme_phoneme_correspondence_formset = None
                accents_formset = None
                plain_lexicon_formset = None
                display_plain_lexicon_entries = False
                display_aligned_lexicon_entries = False
            else:
                grapheme_phoneme_correspondence_entries_exist = 'YES' if phonetic_orthography_resources_available(language) else 'NO'
                plain_phonetic_lexicon_entries_exist = 'YES' if phonetic_lexicon_repo.plain_phonetic_entries_exist_for_language(language) else 'NO'
                aligned_phonetic_lexicon_entries_exist = 'YES' if phonetic_lexicon_repo.aligned_entries_exist_for_language(language) else 'NO'
                form = PhoneticLexiconForm(user=request.user, initial = { 'language': language,
                                                                          'encoding': encoding,
                                                                          'grapheme_phoneme_correspondence_entries_exist': grapheme_phoneme_correspondence_entries_exist,
                                                                          'plain_phonetic_lexicon_entries_exist': plain_phonetic_lexicon_entries_exist,
                                                                          'aligned_phonetic_lexicon_entries_exist': aligned_phonetic_lexicon_entries_exist,
                                                                          'display_grapheme_to_phoneme_entries': display_grapheme_to_phoneme_entries,
                                                                          'display_new_plain_lexicon_entries': display_new_plain_lexicon_entries,
                                                                          'display_approved_plain_lexicon_entries': display_approved_plain_lexicon_entries,
                                                                          'display_new_aligned_lexicon_entries': display_new_aligned_lexicon_entries,
                                                                          'display_approved_aligned_lexicon_entries': display_approved_aligned_lexicon_entries,
                                                                          })
                grapheme_phoneme_data, accents_data = orthography_repo.get_parsed_entry(language, formatting='new')

                max_entries_to_show = int(config.get('phonetic_lexicon_repository', 'max_entries_to_show'))
                
                plain_lexicon_data = []
                if display_new_plain_lexicon_entries:
                    plain_lexicon_data += phonetic_lexicon_repo.get_generated_plain_entries(language)[:max_entries_to_show]
                if display_approved_plain_lexicon_entries:
                    plain_lexicon_data += phonetic_lexicon_repo.get_reviewed_plain_entries(language)[:max_entries_to_show]

                aligned_lexicon_data = []
                if display_new_aligned_lexicon_entries:
                    aligned_lexicon_data += phonetic_lexicon_repo.get_generated_aligned_entries(language)[:max_entries_to_show]
                if display_approved_aligned_lexicon_entries:
                    aligned_lexicon_data += phonetic_lexicon_repo.get_reviewed_aligned_entries(language)[:max_entries_to_show]
                #print(f'--- edit_phonetic_lexicon found {len(plain_lexicon_data)} plain lexicon entries to review')
                #print(f'--- edit_phonetic_lexicon found {len(aligned_lexicon_data)} aligned lexicon entries to review')
                
                grapheme_phoneme_formset = GraphemePhonemeCorrespondenceFormSet(initial=grapheme_phoneme_data, prefix='grapheme_phoneme')
                #print(f'grapheme_phoneme_formset length: {len(grapheme_phoneme_formset)}')
                #print(f'accents_formset length: {len(accents_formset)}')
                accents_formset = AccentCharacterFormSet(initial=accents_data, prefix='accents')
                plain_lexicon_formset = PlainPhoneticLexiconEntryFormSet(initial=plain_lexicon_data, prefix='plain')
                aligned_lexicon_formset = AlignedPhoneticLexiconEntryFormSet(initial=aligned_lexicon_data, prefix='aligned') 
    else:
        form = PhoneticLexiconForm(user=request.user)
        plain_lexicon_formset = None
        if form.fields['language'].initial:
            current_encoding = phonetic_lexicon_repo.get_encoding_for_language(form.fields['language'].initial)
            form.fields['encoding'].initial = current_encoding

    clara_version = get_user_config(request.user)['clara_version']

    return render(request, 'clara_app/edit_phonetic_lexicon.html',
                  {'form': form,
                   'grapheme_phoneme_formset': grapheme_phoneme_formset,
                   'accents_formset': accents_formset,
                   'plain_lexicon_formset': plain_lexicon_formset,
                   'aligned_lexicon_formset': aligned_lexicon_formset,
                   'clara_version': clara_version
                   })

def upload_and_install_plain_phonetic_lexicon(file_path, language, callback=None):
    post_task_update(callback, f"--- Installing phonetic lexicon for {language}")

    try:
        phonetic_lexicon_repo = PhoneticLexiconRepositoryORM()
        #phonetic_lexicon_repo = PhoneticLexiconRepositoryORM() if _use_orm_repositories else PhoneticLexiconRepository() 

        result, details = phonetic_lexicon_repo.load_and_initialise_plain_lexicon(file_path, language, callback=callback)
        
        if result == 'error':
            post_task_update(callback, f"Error when uploading phonetic lexicon for {language}: {details}")
            post_task_update(callback, f"error")
        else:
            post_task_update(callback, f"Phonetic lexicon for {language} uploaded successfully: {details}")
            post_task_update(callback, f"finished")

    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")
    finally:
        # remove_file removes the S3 file if we're in S3 mode (i.e. Heroku) and the local file if we're in local mode.
        remove_file(file_path)

@login_required
@language_master_required
def import_phonetic_lexicon_status(request, language, report_id):
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
@language_master_required
def import_phonetic_lexicon_monitor(request, language, report_id):
    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/import_phonetic_lexicon_monitor.html',
                  {'report_id': report_id, 'language': language, 'clara_version': clara_version})

# Confirm the final result of importing the lexicon
@login_required
@language_master_required
def import_phonetic_lexicon_complete(request, language, status):
    if status == 'error':
        messages.error(request, f"Something went wrong when importing the phonetic lexicon for {language}. Try looking at the 'Recent task updates' view")
        return redirect('edit_phonetic_lexicon')
    else:
        messages.success(request, f"Phonetic lexicon for {language} imported successfully")
        return redirect('edit_phonetic_lexicon')

##
# Allow a language master to edit templates and examples
@login_required
@language_master_required
def edit_prompt(request):
    if request.method == 'POST':
        prompt_selection_form = PromptSelectionForm(request.POST, user=request.user)
        if prompt_selection_form.is_valid():
            language = prompt_selection_form.cleaned_data['language']
            default_language = prompt_selection_form.cleaned_data['default_language']
            template_or_examples = prompt_selection_form.cleaned_data['template_or_examples']
            # Assume the template is in English, i.e. an ltr language, but the examples are in "language"
            rtl_language = False if template_or_examples == 'template' else is_rtl_language(language) 
            operation = prompt_selection_form.cleaned_data['operation']
            annotation_type = prompt_selection_form.cleaned_data['annotation_type']
            if template_or_examples == 'template':
                PromptFormSet = forms.formset_factory(TemplateForm, formset=CustomTemplateFormSet, extra=0)
            elif annotation_type == 'morphology':
                PromptFormSet = forms.formset_factory(MorphologyExampleForm, formset=CustomMorphologyExampleFormSet, extra=1)
            elif annotation_type == 'mwe':
                PromptFormSet = forms.formset_factory(MWEExampleForm, formset=CustomMWEExampleFormSet, extra=1)
            elif annotation_type in ( 'gloss_with_mwe', 'lemma_with_mwe' ):
                PromptFormSet = forms.formset_factory(ExampleWithMWEForm, formset=ExampleWithMWEFormSet, extra=1)
            elif (operation == 'annotate' or annotation_type == 'segmented'):
                PromptFormSet = forms.formset_factory(StringForm, formset=CustomStringFormSet, extra=1)
            else:
                PromptFormSet = forms.formset_factory(StringPairForm, formset=CustomStringPairFormSet, extra=1)
                
            prompt_repo = PromptTemplateRepository(language)

            if request.POST.get('action') == 'Load':
                # Start by trying to get the data from our current language
                try:
                    prompts = prompt_repo.load_template_or_examples(template_or_examples, annotation_type, operation)
                except TemplateError as e1:
                    # If we're editing 'default' and we didn't find anything on the previous step, there's nothing to use, so return blank values
                    if language == 'default':
                        messages.success(request, f"Warning: nothing found, you need to write the default {template_or_examples} from scratch")
                        prompt_repo_default = PromptTemplateRepository('default')
                        prompts = prompt_repo_default.blank_template_or_examples(template_or_examples, annotation_type, operation)
                    # If we're not editing 'default' and the default language is different, try that next
                    elif language != default_language:
                        try:
                            prompt_repo_default_language = PromptTemplateRepository(default_language)
                            prompts = prompt_repo_default_language.load_template_or_examples(template_or_examples, annotation_type, operation)
                        except TemplateError as e2:
                            # If we haven't already done that, try 'default'
                            if default_language != 'default':
                                try:
                                    prompt_repo_default = PromptTemplateRepository('default')
                                    prompts = prompt_repo_default.load_template_or_examples(template_or_examples, annotation_type, operation)
                                except TemplateError as e3:
                                    messages.error(request, f"{e3.message}")
                                    prompt_formset = None  # No formset because we couldn't get the data
                                    return render(request, 'clara_app/edit_prompt.html', {'prompt_selection_form': prompt_selection_form, 'prompt_formset': prompt_formset})
                            else:
                                messages.error(request, f"{e2.message}")
                                prompt_formset = None  # No formset because we couldn't get the data
                                return render(request, 'clara_app/edit_prompt.html', {'prompt_selection_form': prompt_selection_form, 'prompt_formset': prompt_formset})
                    else:
                        messages.error(request, f"{e1.message}")
                        prompt_formset = None  # No formset because we couldn't get the data
                        return render(request, 'clara_app/edit_prompt.html', {'prompt_selection_form': prompt_selection_form, 'prompt_formset': prompt_formset})

                # Prepare data
                if template_or_examples == 'template':
                    initial_data = [{'template': prompts}]
                elif annotation_type in ( 'morphology', 'mwe' ):
                    initial_data = [{'string1': triple[0], 'string2': triple[1], 'string3': triple[2]} for triple in prompts]
                elif annotation_type in ( 'gloss_with_mwe', 'lemma_with_mwe' ):
                    initial_data = [{'string1': pair[0], 'string2': pair[1]} for pair in prompts]
                elif template_or_examples == 'examples' and (operation == 'annotate' or annotation_type == 'segmented'):
                    initial_data = [{'string': example} for example in prompts]
                else:
                    initial_data = [{'string1': pair[0], 'string2': pair[1]} for pair in prompts]

                prompt_formset = PromptFormSet(initial=initial_data, prefix='prompts', rtl_language=rtl_language)

            elif request.POST.get('action') == 'Save':
                prompt_formset = PromptFormSet(request.POST, prefix='prompts', rtl_language=rtl_language)
                if prompt_formset.is_valid():
                    # Prepare data for saving
                    if template_or_examples == 'template':
                        new_prompts = prompt_formset[0].cleaned_data.get('template')
                    elif annotation_type in ( 'morphology', 'mwe' ):
                        new_prompts = [[form.cleaned_data.get('string1'), form.cleaned_data.get('string2'), form.cleaned_data.get('string3')]
                                       for form in prompt_formset]
                        if not new_prompts[-1][0] or not new_prompts[-1][1]:
                            # We didn't use the extra last field
                            new_prompts = new_prompts[:-1]
                    elif annotation_type in ( 'gloss_with_mwe', 'lemma_with_mwe' ):
                        new_prompts = [[form.cleaned_data.get('string1'), form.cleaned_data.get('string2')] for form in prompt_formset]
                        if not new_prompts[-1][0]:
                            # We didn't use the extra last field
                            new_prompts = new_prompts[:-1]
                    elif template_or_examples == 'examples' and (operation == 'annotate' or annotation_type == 'segmented'):
                        new_prompts = [form.cleaned_data.get('string') for form in prompt_formset]
                        if not new_prompts[-1]:
                            # We didn't use the extra last field
                            new_prompts = new_prompts[:-1]
                    else:
                        new_prompts = [[form.cleaned_data.get('string1'), form.cleaned_data.get('string2')] for form in prompt_formset]
                        if not new_prompts[-1][0] or not new_prompts[-1][1] or not new_prompts[-1][2]:
                            # We didn't use the extra last field
                            new_prompts = new_prompts[:-1]
                    print(f'new_prompts:')
                    pprint.pprint(new_prompts)
                    try:
                        prompt_repo.save_template_or_examples(template_or_examples, annotation_type, operation, new_prompts, request.user.username)
                        messages.success(request, "Data saved successfully")
                    except TemplateError as e:
                        messages.error(request, f"{e.message}")
                    
            else:
                raise Exception("Internal error: neither Load nor Save found in POST request to edit_prompt")

            clara_version = get_user_config(request.user)['clara_version']

            return render(request, 'clara_app/edit_prompt.html',
                          {'prompt_selection_form': prompt_selection_form, 'prompt_formset': prompt_formset, 'clara_version': clara_version})

    else:
        prompt_selection_form = PromptSelectionForm(user=request.user)
        prompt_formset = None  # No formset when the page is first loaded

    return render(request, 'clara_app/edit_prompt.html', {'prompt_selection_form': prompt_selection_form, 'prompt_formset': prompt_formset})

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
            # Calculate the date offset based on the selected time period
            days_ago = timezone.now() - timedelta(days=int(time_period))
            query &= Q(updated_at__gte=days_ago)

    content_list = Content.objects.filter(query).order_by(Lower('title'))
    paginator = Paginator(content_list, 10)  # Show 10 content items per page

    page = request.GET.get('page')
    contents = paginator.get_page(page)

    clara_version = get_user_config(request.user)['clara_version']

    return render(request, 'clara_app/content_list.html', {'contents': contents, 'search_form': search_form, 'clara_version': clara_version})


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
            # Calculate the date offset based on the selected time period
            days_ago = timezone.now() - timedelta(days=int(time_period))
            query &= Q(updated_at__gte=days_ago)

    content_list = Content.objects.filter(query).order_by(Lower('title'))
    paginator = Paginator(content_list, 10)  # Show 10 content items per page

    page = request.GET.get('page')
    contents = paginator.get_page(page)

    return render(request, 'clara_app/public_content_list.html', {'contents': contents, 'search_form': search_form})

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

def public_content_detail(request, content_id):
    content = get_object_or_404(Content, id=content_id)
    comments = Comment.objects.filter(content=content).order_by('timestamp')  
    average_rating = Rating.objects.filter(content=content).aggregate(Avg('rating'))

    # Print out all request headers for debugging
    headers = request.META
##    for header, value in headers.items():
##       logger.debug(f'header {header}: {value}')
##    for header in ['HTTP_X_FORWARDED_FOR', 'REMOTE_ADDR', 'HTTP_X_REAL_IP']:
##        value = headers.get(header, 'NOT FOUND')
##        messages.success(request, f'Header {header}: "{value}"')
##    for header, value in headers.items():
##        messages.success(request, f'Header {header}: "{value}"')

    # Get the client's IP address
    #client_ip, is_routable = get_client_ip(request, request_header_order=['X_FORWARDED_FOR', 'REMOTE_ADDR'], proxy_count=1)
    client_ip, is_routable = get_client_ip(request, request_header_order=['HTTP_X_FORWARDED_FOR', 'HTTP_X_REAL_IP', 'REMOTE_ADDR'])
    
    #client_ip, is_routable = get_client_ip(request, proxy_count=1)
    
    if client_ip is None:
        client_ip = '0.0.0.0'  # Fallback IP if detection fails
        
##    messages.success(request, f'Accessed content from IP = {client_ip}')
    
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
    return activities.order_by('-vote_score', 'status_order', '-created_at')

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
            use_translation_for_images = form.cleaned_data['use_translation_for_images']
            # Create a new project in Django's database, associated with the current user
            clara_project = CLARAProject(title=title,
                                         user=request.user,
                                         l2=l2_language,
                                         l1=l1_language,
                                         uses_coherent_image_set=uses_coherent_image_set,
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

# Get summary tables for projects and content, broken down by language
def language_statistics(request):
    # Aggregate project counts by l2 language
    project_stats = (
        CLARAProject.objects.values('l2')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    # Aggregate content counts by l2 language
    content_stats = (
        Content.objects.values('l2')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    # Calculate the totals
    total_projects = sum(stat['total'] for stat in project_stats)
    total_contents = sum(stat['total'] for stat in content_stats)

    return render(request, 'clara_app/language_statistics.html', {
        'project_stats': project_stats,
        'content_stats': content_stats,
        'total_projects': total_projects,
        'total_contents': total_contents,
    })

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
        clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
        up_to_date_dict = get_phase_up_to_date_dict(project, clara_project_internal, user)

        resources_available['l2'] = project.l2
        resources_available['rtl_language'] = is_rtl_language(project.l2)
        resources_available['l1'] = project.l1
        resources_available['title'] = project.title
        resources_available['simple_clara_type'] = project.simple_clara_type
        resources_available['internal_title'] = clara_project_internal.id
        resources_available['up_to_date_dict'] = up_to_date_dict

        # In the create_text_and_image version, we start with a prompt and create a plain_text and image
        if project.simple_clara_type == 'create_text_and_image':
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
            resources_available['image_file_path'] = None

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

_simple_clara_trace = False
#_simple_clara_trace = True

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
                                                             'save_text_title', 'save_uploaded_image', 'save_preferred_tts_engine', 'post_rendered_text' )
                
                if action in _simple_clara_actions_to_execute_locally:
                    result = perform_simple_clara_action_helper(username, project_id, simple_clara_action, callback=None)
                    if _simple_clara_trace:
                        print(f'result = {result}')
                    new_project_id = result['project_id'] if 'project_id' in result else project_id
                    new_status = result['status']
                    if new_status == 'error':
                        messages.error(request, f"Something went wrong. Try looking at the 'Recent task updates' view")
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
    
    return render(request, 'clara_app/simple_clara.html', {
        'project_id': project_id,
        'form': form,
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
    try:
        action_type = simple_clara_action['action']
        if action_type == 'create_project':
            # simple_clara_action should be of form { 'action': 'create_project', 'l2': text_language, 'l1': annotation_language,
            #                                         'title': title, 'simple_clara_type': simple_clara_type }
            result = simple_clara_create_project_helper(username, simple_clara_action, callback=callback)
        elif action_type == 'change_title':
            # simple_clara_action should be of form { 'action': 'create_project', 'l2': text_language, 'l1': annotation_language, 'title': title }
            result = simple_clara_change_title_helper(username, project_id, simple_clara_action, callback=callback)
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
        result = { 'status': 'failed',
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
    l2_language = simple_clara_action['l2']
    l1_language = simple_clara_action['l1']
    title = simple_clara_action['title']
    simple_clara_type = simple_clara_action['simple_clara_type']
    # Create a new project in Django's database, associated with the current user
    user = User.objects.get(username=username)
    clara_project = CLARAProject(title=title, user=user, l2=l2_language, l1=l1_language)
    clara_project.save()
    internal_id = create_internal_project_id(title, clara_project.id)
    # Update the Django project with the internal_id and simple_clara_type
    clara_project.internal_id = internal_id
    clara_project.simple_clara_type = simple_clara_type
    clara_project.save()
    # Create a new internal project in the C-LARA framework
    clara_project_internal = CLARAProjectInternal(internal_id, l2_language, l1_language)
    post_task_update(callback, f"--- Created project '{title}'")
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
        #  "audio_type_for_segments": "tts"
        #}
        if global_metadata and isinstance(global_metadata, dict):
            if "simple_clara_type" in global_metadata:
                clara_project.simple_clara_type = global_metadata["simple_clara_type"]
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
            project.use_translation_for_images = image_set_form.cleaned_data['use_translation_for_images']
            project.save()
    else:
        title_form = UpdateProjectTitleForm(prefix="title")
        image_set_form = UpdateCoherentImageSetForm(prefix="image_set",
                                                    initial={'uses_coherent_image_set': project.uses_coherent_image_set,
                                                             'use_translation_for_images': project.use_translation_for_images})

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/project_detail.html', 
                  { 'project': project,
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
            if not text_choice in ( 'manual', 'load_archived', 'correct', 'generate', 'improve', 'trivial', 'tree_tagger', 'jieba', 'pypinyin', 'delete' ):
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
                    internalize_text(annotated_text, clara_project_internal.l2_language, clara_project_internal.l1_language, this_version)
                    clara_project_internal.save_text_version(this_version, annotated_text, 
                                                             user=username, label=label, gold_standard=gold_standard)
                    messages.success(request, "File saved")
                except InternalisationError as e:
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
            elif text_choice in ( 'generate', 'correct', 'improve', 'trivial', 'tree_tagger', 'jieba', 'pypinyin' ):
                if not user_has_a_named_project_role(request.user, project_id, ['OWNER']):
                    raise PermissionDenied("You don't have permission to create text by calling the AI.")
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
                                   request.user, label, previous_version=previous_version, prompt=prompt, callback=callback)
                        print(f'--- Started generation task')
                        #Redirect to the monitor view, passing the task ID and report ID as parameters
                        return redirect('generate_text_monitor', project_id, this_version, report_id)
                    # We are improving the text using the AI
                    elif text_choice == 'improve':
                        # We want to get a possible template error here rather than in the asynch process
                        clara_project_internal.try_to_use_templates('improve', this_version)
                        async_task(perform_improve_operation_and_store_api_calls, this_version, project, clara_project_internal,
                                   request.user, label, prompt=prompt, callback=callback)
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
                    # We are creating the text using TreeTagger. This operation is only possible with lemma tagging
                    elif text_choice == 'tree_tagger':
                        action, api_calls = ( 'generate', clara_project_internal.create_lemma_tagged_text_with_treetagger(user=username, label=label) )
                        # These operations are handled elsewhere for generation and improvement, due to asynchrony
                        store_api_calls(api_calls, project, request.user, this_version)
                        annotated_text = clara_project_internal.load_text_version(this_version)
                        text_choice = 'manual'
                        success_message = f'Created {this_version} text using TreeTagger'
                        print(f'--- {success_message}')
                        messages.success(request, success_message)
                        current_version = clara_project_internal.get_file_description(this_version, 'current')
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
                                                   user_object, label, previous_version='default', prompt=None, callback=None):
    try:
        config_info = get_user_config(user_object)
        operation, api_calls = perform_generate_operation(version, clara_project_internal, user_object.username, label,
                                                          previous_version=previous_version, prompt=prompt,
                                                          config_info=config_info, callback=callback)
        store_api_calls(api_calls, project, user_object, version)
        post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")
    
def perform_generate_operation(version, clara_project_internal, user, label, previous_version=None, prompt=None, config_info={}, callback=None):
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
        return ( 'generate', clara_project_internal.create_segmented_text(user=user, label=label, config_info=config_info, callback=callback) )
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
                                                   user_object, label, prompt=None, callback=None):
    try:
        config_info = get_user_config(user_object)
        operation, api_calls = perform_improve_operation(version, clara_project_internal, user_object.username, label,
                                                         prompt=prompt, config_info=config_info, callback=callback)
        store_api_calls(api_calls, project, user_object, version)
        post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")
 
def perform_improve_operation(version, clara_project_internal, user, label, prompt=None, config_info={}, callback=None):
    if version == 'plain':
        return ( 'generate', clara_project_internal.improve_plain_text(prompt=prompt, user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'title':
        return ( 'generate', clara_project_internal.improve_title(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'summary':
        return ( 'generate', clara_project_internal.improve_summary(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'segmented':
        return ( 'generate', clara_project_internal.improve_segmented_text(user=user, label=label, config_info=config_info, callback=callback) )
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
    clara_version = get_user_config(request.user)['clara_version']
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

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

    # Assuming segmented_text and internalised_segmented_text have already been loaded
    segmented_text = clara_project_internal.load_text_version("segmented_with_images")
    internalised_segmented_text = internalize_text(segmented_text, project.l2, project.l1, "segmented")
    page_objects = internalised_segmented_text.pages
    page_texts = [ page_object.to_text(annotation_type="plain") for page_object in page_objects ]

    # Retrieve existing images
    images = clara_project_internal.get_all_project_images()
    initial_data = [{'image_file_path': img.image_file_path,
                     'image_base_name': basename(img.image_file_path) if img.image_file_path else None,
                     'image_name': img.image_name,
                     'associated_text': img.associated_text,
                     'associated_areas': img.associated_areas,
                     'page': img.page,
                     'page_text': page_texts[img.page - 1] if img.page <= len(page_texts) else '',
                     'position': img.position,
                     'style_description': img.style_description,
                     'content_description': img.content_description,
                     'request_type': img.request_type,
                     'description_variable': img.description_variable,
                     'description_variables': ', '.join(img.description_variables) if img.description_variables else '',
                     'user_prompt': img.user_prompt
                     }
                    for img in images]
    # Sort by page number with generation requests first
    initial_data = sorted(initial_data, key=lambda x: ( x['page'] + ( 0 if x['request_type'] == 'image-generation' else 0.1 ) ) )

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
                if not user_has_open_ai_key_or_credit(request.user):
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
    ##                    print(f'--- Invalid form data (form #{i}): {form}')
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
                print(description_formset)
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
                    previous_record = initial_data[i] if i < len(initial_data) else None
                    #print(f'previous_record#{i} = {previous_record}')
                    # Ignore the last (extra) form if image_file_path has not been changed, i.e. we are not uploading a file
                    #print(f"--- form #{i}: form.changed_data = {form.changed_data}")
                    if not ( i == len(formset) - 1 and not 'image_file_path' in form.changed_data and not 'user_prompt' in form.changed_data ):
##                        if not form.is_valid():
##                            print(f'--- Invalid form data (form #{i}): {form}')
##                            errors.append(f"Invalid form data (form #{i}): {form.errors}")
##                            messages.error(request, f"Invalid form data (form #{i}).")

                        # form.cleaned_data.get('image_file_path') is special, since we get it from uploading a file.
                        # If there is no file upload, the value is null
                        if form.cleaned_data.get('image_file_path'):
                            uploaded_image_file_path = form.cleaned_data.get('image_file_path')
                            real_image_file_path = uploaded_file_to_file(uploaded_image_file_path)
                            #print(f'--- real_image_file_path for {image_name} (from upload) = {real_image_file_path}')
                        elif previous_record:
                            real_image_file_path = previous_record['image_file_path']
                            #print(f'--- real_image_file_path for {image_name} (previously stored) = {real_image_file_path}')
                        else:
                            real_image_file_path = None
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
                        print(f'description_variables = "{description_variables}"')

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
                                                                     description_variables=description_variables
                                                                     )
                        elif ( ( image_name and real_image_file_path ) or user_prompt ) and not errors:
                           # We are uploading an image or changing a generation/understanding line
    ##                        if not associated_areas and associated_text and image_name:  
    ##                            # Generate the uninstantiated annotated image structure
    ##                            structure = make_uninstantiated_annotated_image_structure(image_name, associated_text)
    ##                            # Convert the structure to a string and store it in 'associated_areas'
    ##                            associated_areas = json.dumps(structure)

                            clara_project_internal.add_project_image(image_name, real_image_file_path,
                                                                     associated_text=associated_text,
                                                                     associated_areas=associated_areas,
                                                                     page=page, position=position,
                                                                     request_type=request_type,
                                                                     user_prompt=user_prompt,
                                                                     content_description=content_description,
                                                                     description_variable=description_variable,
                                                                     description_variables=description_variables
                                                                     )
                                                   
                if len(image_requests) != 0:
                    if not user_has_open_ai_key_or_credit(request.user):
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
            messages.success(request, "Something went wrong when performing image task. Look at the 'Recent task updates' view for further information.")

    return render(request, 'clara_app/edit_images.html', {'formset': formset,
                                                          'description_formset': description_formset,
                                                          'style_form': style_form,
                                                          'image_request_sequence_form': image_request_sequence_form,
                                                          'project': project,
                                                          'uses_coherent_image_set': project.uses_coherent_image_set,
                                                          'clara_version': clara_version,
                                                          'errors': []})

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
        translated_text = clara_project_internal.load_text_version("translated")
        translated_text_object = internalize_text(translated_text, project.l2, project.l1, "translated")
        numbered_page_list = translated_text_object.to_numbered_page_list(translated=True)
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

        print(f'numbered_page_list')
        pprint.pprint(numbered_page_list)

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

##          {
##            "request_type": "image-generation",
##            "page": 3,
##            "prompt": "An image of Princess Elara and the dragon Ember in the forest. They have just met. Ember looks sad and lost, Elara looks kind
##            and sympathetic.",
##            "description_variables": [ "Elara-description", "forest-description" ]
##          }

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
#
# Generation requests have this format:
# { 'image_name': image_name,
#   'page': page,
#   'position': position,
#   'user_prompt': user_prompt,
#   'style_description': style_description,
#   'current_image': image_file_path
#  }
# current_image may be null

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

                        clara_project_internal.add_project_image(image_name, tmp_image_file, 
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
                                               human_voice_id=None, human_voice_id_phonetic=None,
                                               audio_type_for_words='tts', audio_type_for_segments='tts', 
                                               callback=None):
    print(f'--- Asynchronous rendering task started for creating export zipfile')
    try:
        clara_project_internal.create_export_zipfile(simple_clara_type=simple_clara_type,
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

# Show all questionnaires
##@login_required
##@user_passes_test(lambda u: u.userprofile.is_questionnaire_reviewer)
##def manage_questionnaires(request):
##    if request.method == 'POST':
##        # Handle the deletion of selected questionnaire responses
##        selected_ids = request.POST.getlist('selected_responses')
##        if selected_ids:
##            SatisfactionQuestionnaire.objects.filter(id__in=selected_ids).delete()
##            messages.success(request, "Selected responses have been deleted.")
##            return redirect('manage_questionnaires')
##    
##    # Display all questionnaire responses
##    questionnaires = SatisfactionQuestionnaire.objects.all()
##    return render(request, 'clara_app/manage_questionnaires.html', {'questionnaires': questionnaires})

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

@login_required
def funding_request(request):
    if request.method == 'POST':
        form = FundingRequestForm(request.POST)
        if form.is_valid():
            funding_request = form.save(commit=False)
            funding_request.user = request.user
            funding_request.save()
            messages.success(request, 'Your funding request has been submitted.')
            return redirect('profile')  
    else:
        form = FundingRequestForm()

    return render(request, 'clara_app/funding_request.html', {'form': form})

@login_required
@user_passes_test(lambda u: u.userprofile.is_funding_reviewer)
def review_funding_requests(request):
    own_credit_balance = request.user.userprofile.credit
    
    search_form = FundingRequestSearchForm(request.GET or None)
    query = Q()

    if search_form.is_valid():
        language = search_form.cleaned_data.get('language')
        native_or_near_native = search_form.cleaned_data.get('native_or_near_native')
        text_type = search_form.cleaned_data.get('text_type')
        purpose = search_form.cleaned_data.get('purpose')
        status = search_form.cleaned_data.get('status')

        if language and language != '':
            query &= Q(language=language)
        if native_or_near_native and native_or_near_native != '':
            query &= Q(native_or_near_native=native_or_near_native)
        if text_type and text_type != '':
            query &= Q(text_type=text_type)
        if purpose and purpose != '':
            query &= Q(purpose=purpose)
        if status and status != '':
            query &= Q(status=status)
    
    if request.method == 'POST':
        formset = ApproveFundingRequestFormSet(request.POST)
        n_filtered_requests = len(formset)
        #print(f'--- Found {n_filtered_requests} requests')
        transfers = []
        total_amount = 0
        for form in formset:
            if not form.is_valid():
                print(f'--- Invalid form data: {form}')
            else:
                request_id = int(form.cleaned_data.get('id'))
                status = form.cleaned_data.get('status')
                credit_assigned = int(form.cleaned_data.get('credit_assigned')) if form.cleaned_data.get('credit_assigned') else 0.0
                #print(f'--- id: {id}, status: {status}, credit_assigned: {credit_assigned}')
                #if status != 'Submitted' and credit_assigned >= 0.01:
                #    messages.error(request, f'Request {request_id}: not meaningful to fund a request with status "{status}"')
                if status == 'Submitted' and credit_assigned >= 0.01:
                    total_amount += credit_assigned
                    transfers.append({
                        'funding_request_id': request_id,
                        'amount': credit_assigned
                    })
        #print(f'--- total_amount = {total_amount}')
        if total_amount == 0:
            messages.error(request, 'No requests to approve.')
        elif total_amount > request.user.userprofile.credit:
            messages.error(request, 'Insufficient funds for these approvals.')
        else:
            confirmation_code = str(uuid.uuid4())
            request.session['funding_transfers'] = {
                'transfers': transfers,
                'total_amount': total_amount,
                'confirmation_code': confirmation_code,
            }
            # Send an email to the reviewer for confirmation
            recipient_email = request.user.email
            send_mail_or_print_trace('Confirm Funding Approvals',
                                     f'Please confirm your funding approvals totaling USD {total_amount:.2f} using this code: {confirmation_code}',
                                     'clara-no-reply@unisa.edu.au',
                                     [ recipient_email ],
                                     fail_silently=False)
            anonymised_email = recipient_email[0:3] + '*' * ( len(recipient_email) - 10 ) + recipient_email[-7:]
            messages.info(request, f'A confirmation email has been sent to {anonymised_email}. Please check your email to complete the approvals.')
            return redirect('confirm_funding_approvals')            

    else:
        # Populate the formset based on the search criteria etc
        filtered_requests = FundingRequest.objects.filter(query)
        n_filtered_requests = len(filtered_requests)
        initial_data = [{'id': fr.id,
                         'user': fr.user.username,
                         'language_native_or_near_native': f'{dict(SUPPORTED_LANGUAGES_AND_OTHER)[fr.language]}/{"Yes" if fr.native_or_near_native else "No"}',
                         'text_type': dict(FundingRequest.CONTENT_TYPE_CHOICES)[fr.text_type],
                         'purpose': dict(FundingRequest.PURPOSE_CHOICES)[fr.purpose],
                         'other_purpose': fr.other_purpose[:500],
                         'status': dict(FundingRequest.STATUS_CHOICES)[fr.status],
                         'credit_assigned': fr.credit_assigned,
                         }
                        for fr in filtered_requests]
        #print(f'--- initial_data from filtered_requests')
        #pprint.pprint(initial_data)
        formset = ApproveFundingRequestFormSet(initial=initial_data)

    return render(request, 'clara_app/review_funding_requests.html',
                  {'own_credit_balance': own_credit_balance, 'n_filtered_requests': n_filtered_requests,
                   'formset': formset, 'search_form': search_form})

@login_required
@user_passes_test(lambda u: u.userprofile.is_funding_reviewer)
def confirm_funding_approvals(request):
    if request.method == 'POST':
        form = ConfirmTransferForm(request.POST)  
        if form.is_valid():
            confirmation_code = form.cleaned_data['confirmation_code']
            session_data = request.session.get('funding_transfers')

            if not session_data:
                messages.error(request, 'No transfers found.')
            elif not confirmation_code == session_data['confirmation_code']:
                messages.error(request, 'Invalid confirmation code.')
            else:
                for transfer in session_data['transfers']:
                    # Update the funding_request
                    funding_request = FundingRequest.objects.get(id=transfer['funding_request_id'])
                    funding_request.status = 'accepted'
                    funding_request.credit_assigned = Decimal(transfer['amount'])
                    funding_request.decision_made_at = timezone.now()
                    funding_request.funder = request.user
                    funding_request.save()
                    # Perform the credit transfer
                    #print(f'Old requester credit ({funding_request.user.username}): {funding_request.user.userprofile.credit}')
                    #print(f'Old funder credit ({request.user.username}): {request.user.userprofile.credit}')
                    if funding_request.user != request.user:
                        funding_request.user.userprofile.credit += Decimal(transfer['amount'])
                        funding_request.user.userprofile.save()
                        request.user.userprofile.credit -= Decimal(transfer['amount'])
                        request.user.userprofile.save()
                    #print(f'New requester credit ({funding_request.user.username}): {funding_request.user.userprofile.credit}')
                    #print(f'New funder credit ({request.user.username}): {request.user.userprofile.credit}')
                    # Send an email to the requester to let them know the request has been approved
                    send_mail_or_print_trace('Your C-LARA funding request has been approved',
                                             f'Your C-LARA funding request was approved, and USD {transfer["amount"]:.2f} has been added to your account balance.',
                                             'clara-no-reply@unisa.edu.au',
                                             [ funding_request.user.email ],
                                             fail_silently=False)
                del request.session['funding_transfers']
                messages.success(request, 'Funding approvals confirmed and funds transferred.')
                return redirect('review_funding_requests')
    # GET request            
    else:
        form = ConfirmTransferForm()

    return render(request, 'clara_app/confirm_funding_approvals.html', {'form': form})    

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



