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
from django.db.models import Avg, Q
from django.db.models.functions import Lower
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone
from django.urls import reverse

from .models import UserProfile, FriendRequest, UserConfiguration, LanguageMaster, Content, TaskUpdate, Update, ReadingHistory
from .models import CLARAProject, HumanAudioInfo, PhoneticHumanAudioInfo, ProjectPermissions, CLARAProjectAction, Comment, Rating, FormatPreferences
from django.contrib.auth.models import User

from django_q.tasks import async_task
from django_q.models import Task

from .forms import RegistrationForm, UserForm, UserProfileForm, FriendRequestForm, AdminPasswordResetForm, ProjectSelectionFormSet, UserConfigForm
from .forms import AssignLanguageMasterForm, AddProjectMemberForm
from .forms import ContentSearchForm, ContentRegistrationForm
from .forms import ProjectCreationForm, UpdateProjectTitleForm, SimpleClaraForm, ProjectImportForm, ProjectSearchForm, AddCreditForm, ConfirmTransferForm
from .forms import DeleteTTSDataForm, AudioMetadataForm
from .forms import HumanAudioInfoForm, AudioItemFormSet, PhoneticHumanAudioInfoForm
from .forms import CreatePlainTextForm, CreateTitleTextForm, CreateSegmentedTitleTextForm, CreateSummaryTextForm, CreateCEFRTextForm, CreateSegmentedTextForm
from .forms import CreatePhoneticTextForm, CreateGlossedTextForm, CreateLemmaTaggedTextForm, CreateLemmaAndGlossTaggedTextForm
from .forms import MakeExportZipForm, RenderTextForm, RegisterAsContentForm, RatingForm, CommentForm, DiffSelectionForm
from .forms import TemplateForm, PromptSelectionForm, StringForm, StringPairForm, CustomTemplateFormSet, CustomStringFormSet, CustomStringPairFormSet
from .forms import ImageForm, ImageFormSet, PhoneticLexiconForm, PlainPhoneticLexiconEntryFormSet, AlignedPhoneticLexiconEntryFormSet
from .forms import L2LanguageSelectionForm, AddProjectToReadingHistoryForm
from .forms import GraphemePhonemeCorrespondenceFormSet, AccentCharacterFormSet, FormatPreferencesForm
from .utils import get_user_config, create_internal_project_id, store_api_calls, make_asynch_callback_and_report_id
from .utils import get_user_api_cost, get_project_api_cost, get_project_operation_costs, get_project_api_duration, get_project_operation_durations
from .utils import user_is_project_owner, user_has_a_project_role, user_has_a_named_project_role, language_master_required
from .utils import post_task_update_in_db, get_task_updates
from .utils import uploaded_file_to_file, create_update, current_friends_of_user, get_phase_up_to_date_dict

from .clara_core.clara_main import CLARAProjectInternal
from .clara_core.clara_audio_repository import AudioRepository
from .clara_core.clara_audio_annotator import AudioAnnotator
from .clara_core.clara_phonetic_lexicon_repository import PhoneticLexiconRepository
from .clara_core.clara_prompt_templates import PromptTemplateRepository
from .clara_core.clara_dependencies import CLARADependencies
from .clara_core.clara_reading_histories import ReadingHistoryInternal
from .clara_core.clara_phonetic_orthography_repository import PhoneticOrthographyRepository, phonetic_orthography_resources_available

from .clara_core.clara_internalise import internalize_text
from .clara_core.clara_grapheme_phoneme_resources import grapheme_phoneme_resources_available
from .clara_core.clara_conventional_tagging import fully_supported_treetagger_language
from .clara_core.clara_chinese import is_chinese_language
from .clara_core.clara_annotated_images import make_uninstantiated_annotated_image_structure
from .clara_core.clara_chatgpt4 import call_chat_gpt4_image
from .clara_core.clara_classes import TemplateError, InternalCLARAError, InternalisationError
from .clara_core.clara_utils import _s3_storage, _s3_bucket, s3_file_name, absolute_file_name, file_exists, local_file_exists, read_txt_file, remove_file, basename
from .clara_core.clara_utils import copy_local_file_to_s3, copy_local_file_to_s3_if_necessary, copy_s3_file_to_local_if_necessary, generate_s3_presigned_url
from .clara_core.clara_utils import robust_read_local_txt_file, read_json_or_txt_file, check_if_file_can_be_read
from .clara_core.clara_utils import output_dir_for_project_id, image_dir_for_project_id, post_task_update, is_rtl_language
from .clara_core.clara_utils import make_mp3_version_of_audio_file_if_necessary

from pathlib import Path
from decimal import Decimal
from urllib.parse import unquote
from datetime import timedelta

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
    return redirect('profile')

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
            send_mail(
                'Confirm Credit Transfer',
                f'Please confirm your credit transfer of {amount} to {recipient.username} using this code: {confirmation_code}',
                'clara-no-reply@unisa.edu.au',
                [recipient_email],
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
            
            # Create a unique ID to tag messages posted by this task, and a callback
            #report_id = uuid.uuid4()
            #callback = [post_task_update_in_db, report_id]
            task_type = f'delete_tts'
            callback, report_id = make_asynch_callback_and_report_id(request, task_type)

            async_task(delete_tts_data_for_language, language, callback=callback)
            print(f'--- Started delete task {language}')
            #Redirect to the monitor view, passing the task ID and report ID as parameters
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
            
            # Create a unique ID to tag messages posted by this task, and a callback
            #report_id = uuid.uuid4()
            #callback = [post_task_update_in_db, report_id]
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
    phonetic_lexicon_repo = PhoneticLexiconRepository()
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
                    phonetic_lexicon_repo.delete_plain_entries(plain_words_to_save, language)
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
                
                plain_lexicon_data = []
                if display_new_plain_lexicon_entries:
                    plain_lexicon_data += phonetic_lexicon_repo.get_generated_plain_entries(language)
                if display_approved_plain_lexicon_entries:
                    plain_lexicon_data += phonetic_lexicon_repo.get_reviewed_plain_entries(language)

                aligned_lexicon_data = []
                if display_new_aligned_lexicon_entries:
                    aligned_lexicon_data += phonetic_lexicon_repo.get_generated_aligned_entries(language)
                if display_approved_aligned_lexicon_entries:
                    aligned_lexicon_data += phonetic_lexicon_repo.get_reviewed_aligned_entries(language)
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
        phonetic_lexicon_repo = PhoneticLexiconRepository() 

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
            elif template_or_examples == 'examples' and (operation == 'annotate' or annotation_type == 'segmented'):
                PromptFormSet = forms.formset_factory(StringForm, formset=CustomStringFormSet, extra=1)
            else:
                PromptFormSet = forms.formset_factory(StringPairForm, formset=CustomStringPairFormSet, extra=1)
                
            prompt_repo = PromptTemplateRepository(language)

            if request.POST.get('action') == 'Load':
                # Start by trying to get the data from our current language
                try:
                    prompts = prompt_repo.load_template_or_examples(template_or_examples, annotation_type, operation)
                except TemplateError as e1:
                    # If the default language is different, try that next
                    if language != default_language:
                        try:
                            prompt_repo_default_language = PromptTemplateRepository(default_language)
                            prompts = prompt_repo_default_language.load_template_or_examples(template_or_examples, annotation_type, operation)
                        except TemplateError as e2:
                            # If we haven't already done that, try 'default'
                            if language != 'default' and default_language != 'default':
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
                    elif template_or_examples == 'examples' and (operation == 'annotate' or annotation_type == 'segmented'):
                        new_prompts = [form.cleaned_data.get('string') for form in prompt_formset]
                        if not new_prompts[-1]:
                            # We didn't use the extra last field
                            new_prompts = new_prompts[:-1]
                    else:
                        new_prompts = [[form.cleaned_data.get('string1'), form.cleaned_data.get('string2')] for form in prompt_formset]
                        if not new_prompts[-1][0] or not new_prompts[-1][1]:
                            # We didn't use the extra last field
                            new_prompts = new_prompts[:-1]
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

        if l2:
            query &= Q(l2__icontains=l2)
        if l1:
            query &= Q(l1__icontains=l1)
        if title:
            query &= Q(title__icontains=title)

    content_list = Content.objects.filter(query).order_by(Lower('title'))
    paginator = Paginator(content_list, 10)  # Show 10 content items per page

    page = request.GET.get('page')
    contents = paginator.get_page(page)

    clara_version = get_user_config(request.user)['clara_version']

    return render(request, 'clara_app/content_list.html', {'contents': contents, 'search_form': search_form, 'clara_version': clara_version})

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
    
    if request.method == 'POST':
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
        'content': content,
        'rating_form': rating_form,
        'comment_form': comment_form,
        'comments': comments,
        'average_rating': average_rating['rating__avg'],
        'clara_version': clara_version
        
    })

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
            # Create a new project in Django's database, associated with the current user
            clara_project = CLARAProject(title=title, user=request.user, l2=l2_language, l1=l1_language)
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

def get_simple_clara_resources_helper(project_id):
    try:
        resources_available = {}
        
        if not project_id:
            # Inital state: we passed in a null (zero) project_id. Nothing exists yet.
            resources_available['status'] = 'No project'
            resources_available['up_to_date_dict'] = {}
            return resources_available

        # We have a project, add the L2, L1 and title to available resources
        project = get_object_or_404(CLARAProject, pk=project_id)
        clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
        up_to_date_dict = get_phase_up_to_date_dict(project, clara_project_internal)

        resources_available['l2'] = project.l2
        resources_available['rtl_language'] = is_rtl_language(project.l2)
        resources_available['l1'] = project.l1
        resources_available['title'] = project.title
        resources_available['internal_title'] = clara_project_internal.id
        resources_available['up_to_date_dict'] = up_to_date_dict

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

        if clara_project_internal.text_versions['segmented']:
            # We have segmented text
            resources_available['segmented_text'] = clara_project_internal.load_text_version('segmented')

        if not clara_project_internal.rendered_html_exists(project_id):
            # We have plain text and image, but no rendered HTML
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

@login_required
def simple_clara(request, project_id, status):
    username = request.user.username
    # Get resources available for display based on the current state
    resources = get_simple_clara_resources_helper(project_id)
    #print(f'Resources:')
    #pprint.pprint(resources)
    
    status = resources['status']
    rtl_language = resources['rtl_language'] if 'rtl_language' in resources else False
    print(f'--- rtl_language = {rtl_language}')
    up_to_date_dict = resources['up_to_date_dict'] 
    form = SimpleClaraForm(initial=resources, is_rtl_language=rtl_language)
    content = Content.objects.get(id=resources['content_id']) if 'content_id' in resources else None

    if request.method == 'POST':
        # Extract action from the POST request
        action = request.POST.get('action')
        #print(f'Action = {action}')
        if action:
            form = SimpleClaraForm(request.POST, request.FILES, is_rtl_language=rtl_language)
            if form.is_valid():
                #print(f'form.cleaned_data')
                #pprint.pprint(form.cleaned_data)
                if action == 'create_project':
                    l2 = form.cleaned_data['l2']
                    l1 = form.cleaned_data['l1']
                    title = form.cleaned_data['title']
                    simple_clara_action = { 'action': 'create_project', 'l2': l2, 'l1': l1, 'title': title }
                elif action == 'change_title':
                    title = form.cleaned_data['title']
                    simple_clara_action = { 'action': 'change_title', 'title': title }
                elif action == 'create_text_and_image':
                    prompt = form.cleaned_data['prompt']
                    simple_clara_action = { 'action': 'create_text_and_image', 'prompt': prompt }
                elif action == 'save_text':
                    plain_text = form.cleaned_data['plain_text']
                    simple_clara_action = { 'action': 'save_text', 'plain_text': plain_text }
                elif action == 'save_segmented_text':
                    segmented_text = form.cleaned_data['segmented_text']
                    simple_clara_action = { 'action': 'save_segmented_text', 'segmented_text': segmented_text }
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
                elif action == 'create_rendered_text':
                    simple_clara_action = { 'action': 'create_rendered_text', 'up_to_date_dict': up_to_date_dict }
                elif action == 'post_rendered_text':
                    simple_clara_action = { 'action': 'post_rendered_text' }
                else:
                    messages.error(request, f"Error: unknown action '{action}'")
                    return redirect('simple_clara', project_id, 'error')

                _simple_clara_actions_to_execute_locally = ( 'create_project', 'change_title', 'save_text', 'save_segmented_text',
                                                             'save_text_title', 'save_uploaded_image', 'post_rendered_text' )
                
                if action in _simple_clara_actions_to_execute_locally:
                    result = perform_simple_clara_action_helper(username, project_id, simple_clara_action, callback=None)
                    new_project_id = result['project_id'] if 'project_id' in result else project_id
                    new_status = result['status']
                    if new_status == 'error':
                        messages.error(request, f"Something went wrong. Try looking at the 'Recent task updates' view")
                    else:
                        success_message = result['message'] if 'message' in result else f'Simple C-LARA operation succeeded'
                        messages.success(request, success_message)
                    return redirect('simple_clara', new_project_id, new_status)
                else:
                    if not request.user.userprofile.credit > 0:
                        messages.error(request, f"Sorry, you need money in your account to perform this operation")
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
            # simple_clara_action should be of form { 'action': 'create_project', 'l2': text_language, 'l1': annotation_language, 'title': title }
            result = simple_clara_create_project_helper(username, simple_clara_action, callback=callback)
        elif action_type == 'change_title':
            # simple_clara_action should be of form { 'action': 'create_project', 'l2': text_language, 'l1': annotation_language, 'title': title }
            result = simple_clara_change_title_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'create_text_and_image':
            # simple_clara_action should be of form { 'action': 'create_text_and_image', 'prompt': prompt }
            result = simple_clara_create_text_and_image_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'save_text':
            # simple_clara_action should be of form { 'action': 'save_text', 'plain_text': plain_text }
            result = simple_clara_save_text_helper(username, project_id, simple_clara_action, callback=callback)
        elif action_type == 'save_segmented_text':
            # simple_clara_action should be of form { 'action': 'save_segmented_text', 'segmented_text': segmented_text }
            result = simple_clara_save_segmented_text_helper(username, project_id, simple_clara_action, callback=callback)
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
    # Create a new project in Django's database, associated with the current user
    user = User.objects.get(username=username)
    clara_project = CLARAProject(title=title, user=user, l2=l2_language, l1=l1_language)
    clara_project.save()
    internal_id = create_internal_project_id(title, clara_project.id)
    # Update the Django project with the internal_id
    clara_project.internal_id = internal_id
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
    store_api_calls(api_calls, project, user, 'plain')
    post_task_update(callback, f"ENDED TASK: create text title")

    # Create the image
    post_task_update(callback, f"STARTED TASK: generate DALL-E-3 image")
    create_and_add_dall_e_3_image(project_id, callback=None)
    #api_calls are stored inside create_and_add_dall_e_3_image
    #store_api_calls(api_calls, project, user, 'image')
    post_task_update(callback, f"ENDED TASK: generate DALL-E-3 image")

    if clara_project_internal.get_project_image('DALLE-E-3-Image-For-Whole-Text'):
        return { 'status': 'finished',
                 'message': 'Created text, title and image' }
    else:
        return { 'status': 'finished',
                 'message': 'Created text and title but was unable to create image. Probably DALL-E-3 thought something was inappropriate.' }

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
    create_and_add_dall_e_3_image(project_id, advice_prompt=image_advice_prompt, callback=callback)
    #api_calls are stored inside create_and_add_dall_e_3_image
    #store_api_calls(api_calls, project, user, 'image')
    post_task_update(callback, f"ENDED TASK: regenerate DALL-E-3 image")

    if clara_project_internal.get_project_image('DALLE-E-3-Image-For-Whole-Text'):
        return { 'status': 'finished',
                 'message': 'Regenerated the image' }
    else:
        return { 'status': 'finished',
                 'message': 'Unable to regenerate the image. Probably DALL-E-3 thought something was inappropriate.' }


def simple_clara_create_rendered_text_helper(username, project_id, simple_clara_action, callback=None):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    up_to_date_dict = simple_clara_action['up_to_date_dict']

    title = project.title
    user = project.user
    config_info = get_user_config(user)

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
        api_calls = clara_project_internal.create_lemma_tagged_text(user=username, config_info=config_info, callback=callback)
        store_api_calls(api_calls, project, user, 'lemma')
        post_task_update(callback, f"ENDED TASK: add lemma tags")

    # Render
    if not up_to_date_dict['render']:
        post_task_update(callback, f"STARTED TASK: create TTS audio and multimodal text")
        clara_project_internal.render_text(project_id, phonetic=False, self_contained=True, callback=callback)
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

        # Update human audio info from the global metadata, which looks like this:
        #{
        #  "human_voice_id": "mannyrayner",
        #  "human_voice_id_phonetic": "mannyrayner",
        #  "audio_type_for_words": "human",
        #  "audio_type_for_segments": "tts"
        #}
        if global_metadata and isinstance(global_metadata, dict):
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
            # Extract the title and the new L2 and L1 language selections
            new_title = form.cleaned_data['title']
            new_l2 = form.cleaned_data['l2']
            new_l1 = form.cleaned_data['l1']

            # Created the cloned project with the new language selections
            new_project = CLARAProject(title=new_title, user=request.user, l2=new_l2, l1=new_l1)
            new_project.save()
            new_internal_id = create_internal_project_id(new_title, new_project.id)
            # Update the Django project with the internal_id
            new_project.internal_id = new_internal_id
            new_project.save()
            # Create a new internal project 
            new_project_internal = CLARAProjectInternal(new_internal_id, new_l2, new_l1)
            # Copy any relevant files from the old project
            project_internal.copy_files_to_newly_cloned_project(new_project_internal)

            # Redirect the user to the cloned project detail page or show a success message
            return redirect('project_detail', project_id=new_project.id)
    else:
        # Prepopulate the form with the copied title and the current language selections as defaults
        new_title = project.title + " - copy"
        form = ProjectCreationForm(initial={'title': new_title, 'l2': project.l2, 'l1': project.l1})

    clara_version = get_user_config(request.user)['clara_version']

    return render(request, 'clara_app/create_cloned_project.html', {'form': form, 'project': project, 'clara_version': clara_version})

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

    return render(request, 'clara_app/project_list.html', {'search_form': search_form, 'page_obj': page_obj, 'clara_version': clara_version})

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
    up_to_date_dict = get_phase_up_to_date_dict(project, clara_project_internal)

    can_create_segmented_text = clara_project_internal.text_versions["plain"]
    can_create_segmented_title = clara_project_internal.text_versions["title"]
    can_create_phonetic_text = clara_project_internal.text_versions["segmented"] and phonetic_resources_are_available(project.l2)
    can_create_glossed_and_lemma_text = clara_project_internal.text_versions["segmented"]
    can_render_normal = clara_project_internal.text_versions["gloss"] and clara_project_internal.text_versions["lemma"]
    can_render_phonetic = clara_project_internal.text_versions["phonetic"] 
    rendered_html_exists = clara_project_internal.rendered_html_exists(project_id)
    rendered_phonetic_html_exists = clara_project_internal.rendered_phonetic_html_exists(project_id)
    images = clara_project_internal.get_all_project_images()
    images_exist = len(images) != 0
    api_cost = get_project_api_cost(request.user, project)
    if request.method == 'POST':
        form = UpdateProjectTitleForm(request.POST)
        if form.is_valid():
            project.title = form.cleaned_data['new_title']
            project.save()
    else:
        form = UpdateProjectTitleForm()

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/project_detail.html', 
                  { 'project': project, 'form': form, 'api_cost': api_cost,
                    'text_versions': text_versions,
                    'images_exist': images_exist,
                    'up_to_date_dict': up_to_date_dict,
                    'can_create_segmented_text': can_create_segmented_text,
                    'can_create_segmented_title': can_create_segmented_title,
                    'can_create_phonetic_text': can_create_phonetic_text,
                    'can_create_glossed_and_lemma_text': can_create_glossed_and_lemma_text,
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

                audio_repository = AudioRepository()
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
                            #print(f'--- real_audio_file_path for {text} (from upload) = {real_audio_file_path}')
                            stored_audio_file_path = audio_repository.store_mp3('human_voice', project.l2, human_voice_id, real_audio_file_path)
                            audio_repository.add_or_update_entry('human_voice', project.l2, human_voice_id, text, stored_audio_file_path)
                            #print(f"--- audio_repository.add_or_update_entry('human_voice', {project.l2}, {human_voice_id}, '{text}', {stored_audio_file_path}")
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
                        async_task(process_manual_alignment, clara_project_internal, audio_file, metadata, human_voice_id, callback=callback)
                        
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
            audio_item_formset = AudioItemFormSet(initial=audio_item_initial_data) if audio_item_initial_data else None
        else:
            audio_item_formset = None

    clara_version = get_user_config(request.user)['clara_version']
    
    context = {
        'project': project,
        'form': form,
        'formset': audio_item_formset,
        'audio_file': human_audio_info.audio_file,
        'manual_align_metadata_file': human_audio_info.manual_align_metadata_file,
        'clara_version': clara_version
    }

    return render(request, 'clara_app/human_audio_processing.html', context)

def initial_data_for_audio_upload_formset(clara_project_internal, human_audio_info):
    metadata = []
    human_voice_id = human_audio_info.voice_talent_id
    if human_audio_info.use_for_words:
        metadata += clara_project_internal.get_audio_metadata(human_voice_id=human_voice_id,
                                                              audio_type_for_words='human', type='words',
                                                              format='text_and_full_file')
    if human_audio_info.use_for_segments:
        metadata += clara_project_internal.get_audio_metadata(human_voice_id=human_voice_id,
                                                              audio_type_for_segments='human', type='segments',
                                                              format='text_and_full_file')
    initial_data = [ { 'text': item['text'],
                       'audio_file_path': item['full_file'],
                       'audio_file_base_name': basename(item['full_file']) }
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

        if form.is_valid():
    
            # 1. Update the model with any new values from the form. Get the method and human_voice_id
            method = request.POST['method']
            human_voice_id = request.POST['voice_talent_id']

            human_audio_info.save()  # Save the restored data back to the database

            # Try forcing this choice to see if we still get 502 errors
            #method = 'upload_zipfile'

            # 2. Update from the formset and save new files
            if method == 'upload_individual' and human_voice_id:
                audio_repository = AudioRepository()
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
                            audio_repository.add_or_update_entry('human_voice', project.l2, human_voice_id, text, stored_audio_file_path)
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

        else:
            messages.error(request, "There was an error processing the form. Please check your input.")

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
                                                         format='text_and_full_file', phonetic=True)

    initial_data = [ { 'text': item['text'],
                       'audio_file_path': item['full_file'],
                       'audio_file_base_name': basename(item['full_file']) }
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

def process_manual_alignment(clara_project_internal, audio_file, metadata, human_voice_id, callback=None):
    post_task_update(callback, "--- Started process_manual_alignment in async thread")
    try:
        # Retrieve files from S3 to local
        copy_s3_file_to_local_if_necessary(audio_file, callback=callback)

        # Process the manual alignment
        result = clara_project_internal.process_manual_alignment(audio_file, metadata, human_voice_id, callback=callback)
        
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
# to produce and edit the "plain", "title", "summary", "cefr", "segmented", "gloss" and "lemma" versions.
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
            label = form.cleaned_data['label']
            gold_standard = form.cleaned_data['gold_standard']
            username = request.user.username
            # We have an optional prompt when creating or improving the initial text.
            prompt = form.cleaned_data['prompt'] if this_version == 'plain' else None
            if not text_choice in ( 'manual', 'load_archived', 'correct', 'generate', 'improve', 'trivial', 'tree_tagger', 'jieba' ):
                raise InternalCLARAError(message = f'Unknown text_choice type in create_annotated_text_of_right_type: {text_choice}')
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
            elif text_choice in ( 'generate', 'correct', 'improve' ) and not request.user.userprofile.credit > 0:
                messages.error(request, f"Sorry, you need money in your account to perform this operation")
                annotated_text = ''
                text_choice = 'manual'
            elif text_choice in ( 'generate', 'correct', 'improve', 'trivial', 'tree_tagger', 'jieba' ):
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
                                   request.user, label, prompt=prompt, callback=callback)
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
                                               prompt=prompt, archived_versions=archived_versions, current_version=current_version,
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
                                               prompt=prompt, archived_versions=archived_versions, current_version=current_version,
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
    elif version == 'phonetic':
        return CreatePhoneticTextForm(*args, **kwargs)
    elif version == 'gloss':
        return CreateGlossedTextForm(*args, **kwargs)
    elif version == 'lemma':
        return CreateLemmaTaggedTextForm(*args, **kwargs)
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
                                                   user_object, label, prompt=None, callback=None):
    try:
        config_info = get_user_config(user_object)
        operation, api_calls = perform_generate_operation(version, clara_project_internal, user_object.username, label, prompt=prompt,
                                                          config_info=config_info, callback=callback)
        store_api_calls(api_calls, project, user_object, version)
        post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")
    
def perform_generate_operation(version, clara_project_internal, user, label, prompt=None, config_info={}, callback=None):
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
    elif version == 'phonetic':
        return ( 'generate', clara_project_internal.create_phonetic_text(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'gloss':
        return ( 'generate', clara_project_internal.create_glossed_text(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'lemma':
        return ( 'generate', clara_project_internal.create_lemma_tagged_text(user=user, label=label, config_info=config_info, callback=callback) )
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
    elif version == 'lemma_and_gloss':
        return ( 'generate', clara_project_internal.improve_lemma_and_gloss_tagged_text(user=user, label=label, config_info=config_info, callback=callback) )
    else:
        raise InternalCLARAError(message = f'Unknown first argument in perform_improve_operation: {version}')

def previous_version_and_template_for_version(this_version):
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
    elif this_version == 'phonetic':
        return ( 'segmented_with_images', 'clara_app/create_phonetic_text.html' )
    elif this_version == 'gloss':
        return ( 'segmented_with_images', 'clara_app/create_glossed_text.html' )
    elif this_version == 'lemma':
        return ( 'segmented_with_images', 'clara_app/create_lemma_tagged_text.html' )
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

# Create or edit "phonetic" version of the text     
@login_required
@user_has_a_project_role
def create_phonetic_text(request, project_id):
    this_version = 'phonetic'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Create or edit "glossed" version of the text     
@login_required
@user_has_a_project_role
def create_glossed_text(request, project_id):
    this_version = 'gloss'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Create or edit "lemma-tagged" version of the text 
@login_required
@user_has_a_project_role
def create_lemma_tagged_text(request, project_id):
    this_version = 'lemma'
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
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    # Retrieve existing images
    images = clara_project_internal.get_all_project_images()
    initial_data = [{'image_file_path': img.image_file_path,
                     'image_base_name': basename(img.image_file_path) if img.image_file_path else None,
                     'image_name': img.image_name,
                     'associated_text': img.associated_text,
                     'associated_areas': img.associated_areas,
                     'page': img.page,
                     'position': img.position}
                    for img in images]
    initial_data = sorted(initial_data, key=lambda x: x['page'])

    if request.method == 'POST':
        if 'action' in request.POST and request.POST['action'] == 'create_dalle_image':
            task_type = f'create_dalle_e_3_image'
            callback, report_id = make_asynch_callback_and_report_id(request, task_type)

            async_task(create_and_add_dall_e_3_image, project_id, callback=callback)
            print(f'--- Started DALL-E-3 image generation task')
            #Redirect to the monitor view, passing the task ID and report ID as parameters
            return redirect('create_dall_e_3_image_monitor', project_id, report_id)

        else:
            formset = ImageFormSet(request.POST, request.FILES)
            for i in range(0, len(formset)):
                form = formset[i]
                previous_record = initial_data[i] if i < len(initial_data) else None
                # Ignore the last (extra) form if image_file_path has not been changed, i.e. we are not uploading a file
                #print(f"--- form #{i}: form.changed_data = {form.changed_data}")
                if not ( i == len(formset) - 1 and not 'image_file_path' in form.changed_data ):
                    if not form.is_valid():
                        #print(f'--- Invalid form data (form #{i}): {form}')
                        messages.error(request, "Invalid form data.")
                        return redirect('edit_images', project_id=project_id)
                    
                    image_name = form.cleaned_data.get('image_name')
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
                    delete = form.cleaned_data.get('delete')
                    #print(f'--- real_image_file_path = {real_image_file_path}, image_name = {image_name}, page = {page}, delete = {delete}')

                    if image_name and delete:
                        clara_project_internal.remove_project_image(image_name)
                        messages.success(request, f"Deleted image: {image_name}")
                    elif image_name and real_image_file_path:
                       # If we don't already have it, try to fill in 'associated_areas' using 'associated_text'
                        if not associated_areas and associated_text and image_name:  
                            # Generate the uninstantiated annotated image structure
                            structure = make_uninstantiated_annotated_image_structure(image_name, associated_text)
                            # Convert the structure to a string and store it in 'associated_areas'
                            associated_areas = json.dumps(structure)

                        clara_project_internal.add_project_image(image_name, real_image_file_path,
                                                                 associated_text=associated_text, associated_areas=associated_areas,
                                                                 page=page, position=position)
            messages.success(request, "Image data updated")
            return redirect('edit_images', project_id=project_id, dall_e_3_image_status='no_image')
    else:
        formset = ImageFormSet(initial=initial_data)
        if dall_e_3_image_status == 'finished':
            messages.success(request, "DALL-E-3 image for whole text successfully generated")
        elif dall_e_3_image_status == 'error':
            messages.success(request, "Something went wrong when generating DALL-E-3 image for whole text. Look at the 'Recent task updates' view for further information.")

    clara_version = get_user_config(request.user)['clara_version']

    return render(request, 'clara_app/edit_images.html', {'formset': formset, 'project': project, 'clara_version': clara_version})

def create_and_add_dall_e_3_image(project_id, advice_prompt=None, callback=None):
    try:
        project = get_object_or_404(CLARAProject, pk=project_id)
        clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
        text = clara_project_internal.load_text_version('plain')
        text_language = project.l2
        prompt = f"""Here is something in {text_language} that another instance of you wrote:

{text}

Could you create an image to go on the front page?"""
        if advice_prompt:
            prompt += f"""
When generating the image, keep the following advice in mind:

{advice_prompt}"""
        temp_dir = tempfile.mkdtemp()
        tmp_image_file = os.path.join(temp_dir, 'image_for_whole_text.jpg')
        
        post_task_update(callback, f"--- Creating a new DALL-E-3 image based on the whole project text")
        api_call = call_chat_gpt4_image(prompt, tmp_image_file, config_info={}, callback=callback)
        post_task_update(callback, f"--- Image created: {tmp_image_file}")

        image_name = 'DALLE-E-3-Image-For-Whole-Text'
        clara_project_internal.add_project_image(image_name, tmp_image_file, 
                                                 associated_text='', associated_areas='',
                                                 page=1, position='top')
        post_task_update(callback, f"--- Image stored")
        post_task_update(callback, f"finished")
        api_calls = [ api_call ]
        store_api_calls(api_calls, project, project.user, 'image')
        return api_calls
    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")
        return []
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
                                               human_voice_id=None, human_voice_id_phonetic=None,
                                               audio_type_for_words='tts', audio_type_for_segments='tts', 
                                               callback=None):
    print(f'--- Asynchronous rendering task started for creating export zipfile')
    try:
        clara_project_internal.create_export_zipfile(human_voice_id=human_voice_id, human_voice_id_phonetic=human_voice_id_phonetic,
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
            # Create a unique ID to tag messages posted by this task
            #report_id = uuid.uuid4()

            # Define a callback as list of the callback function and the first argument
            # We can't use a lambda function or a closure because async_task can't apply pickle to them
            #callback = [post_task_update_in_db, report_id]
            task_type = f'make_export_zipfile'
            callback, report_id = make_asynch_callback_and_report_id(request, task_type)

            # Enqueue the task
            try:
                task_id = async_task(clara_project_internal_make_export_zipfile, clara_project_internal,
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
        clara_project_internal.render_text(project_id,
                                           audio_type_for_words=audio_type_for_words, audio_type_for_segments=audio_type_for_segments,
                                           preferred_tts_engine=preferred_tts_engine, preferred_tts_voice=preferred_tts_voice,
                                           human_voice_id=human_voice_id, format_preferences_info=format_preferences_info,
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
@login_required
def reading_history(request, l2_language):
    user = request.user
    reading_history, created = ReadingHistory.objects.get_or_create(user=user, l2=l2_language)

    if created:
        # Create associated CLARAProject and CLARAProjectInternal
        title = f"{user}_reading_history_for_{l2_language}"
        l1_language = 'No L1 language'
        # Create a new CLARAProject, associated with the current user
        clara_project = CLARAProject(title=title, user=request.user, l2=l2_language, l1=l1_language)
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

    clara_project = reading_history.project
    project_id = clara_project.id
    clara_project_internal = CLARAProjectInternal(clara_project.internal_id, clara_project.l2, clara_project.l1)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'select_language':
##            l2_form = L2LanguageSelectionForm(request.POST)
##            if l2_form.is_valid():
##                l2_language = l2_form.cleaned_data['l2']
##            else:
##                pprint.pprint(l2_form)
##                messages.error(request, f"Unable to set language")
##            l2_language = l2_form.cleaned_data['l2']
            l2_language =  request.POST['l2']
            return redirect('reading_history', l2_language)
            
        elif action == 'add_project':
##            add_project_form = AddProjectToReadingHistoryForm(request.POST)
##            if add_project_form.is_valid() and reading_history:
            if reading_history:
                new_project_id = request.POST['project_id']
                new_project = get_object_or_404(CLARAProject, pk=new_project_id)
                reading_history.add_project(new_project)
                reading_history.save()

                projects_in_history = reading_history.get_ordered_projects()

                if projects_in_history:
                    internal_projects_in_history = [ CLARAProjectInternal(project.internal_id, project.l2, project.l1)
                                                     for project in projects_in_history ]
                    reading_history_internal = ReadingHistoryInternal(project_id, clara_project_internal, internal_projects_in_history)
                    reading_history_internal.create_combined_text_object()
                    reading_history_internal.render_combined_text_object()
                    project_id = clara_project.id
            else:
                messages.error(request, f"Unable to add project to reading history")
            return redirect('reading_history', l2_language)

    # GET request
    else:
        languages_available = l2s_in_posted_content()
        projects_in_history = reading_history.get_ordered_projects()
        projects_available = projects_available_for_adding_to_history(l2_language, projects_in_history)
        
        l2_form = L2LanguageSelectionForm(languages_available=languages_available, l2=l2_language)
        add_project_form = AddProjectToReadingHistoryForm(projects_available=projects_available)

    return render(request, 'clara_app/reading_history.html', {
        'l2_form': l2_form,
        'add_project_form': add_project_form,
        'projects_in_history': projects_in_history,
        'project_id': project_id,
        'projects_available': projects_available
    })

# Find the L2s such that
#   - they are the L2 of a piece of posted content
#   - whose project has a saved internalised text
def l2s_in_posted_content():
    # Get all Content objects that are linked to a CLARAProject
    contents_with_projects = Content.objects.exclude(project=None)
    #pprint.pprint(contents_with_projects)
    l2_languages = set()

    for content in contents_with_projects:
        # Check if the associated project has saved internalized text
        if content.project.has_saved_internalised_and_annotated_text():
            l2_languages.add(content.l2)
##            print(f'{content.title} has saved_internalised_and_annotated_text')
##        else:
##            print(f'{content.title} does not have saved_internalised_and_annotated_text')

    return list(l2_languages)

# Find the projects that
#   - have the right l2,
#   - have been posted as content,
#   - have a saved internalised text,
#   - are not already in the history
def projects_available_for_adding_to_history(l2_language, projects_in_history):
    # Get all projects that have been posted as content with the specified L2 language
    projects = CLARAProject.objects.filter(
        l2=l2_language,
        related_content__isnull=False
    ).distinct()

    available_projects = []

    for project in projects:
        # Check if the project has saved internalized text and is not already in the history
        if project.has_saved_internalised_and_annotated_text() and project not in projects_in_history:
            available_projects.append(project)

    return available_projects
        
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
    audio_repository = AudioRepository()
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



