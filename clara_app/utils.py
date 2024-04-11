
from django.db.models import Sum
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.core.mail import EmailMessage

from .models import CLARAProject, User, UserConfiguration, HumanAudioInfo, PhoneticHumanAudioInfo, FormatPreferences, Acknowledgements
from .models import APICall, ProjectPermissions, LanguageMaster, TaskUpdate, Update, FriendRequest, Content, SatisfactionQuestionnaire

from .clara_main import CLARAProjectInternal

from .clara_dependencies import CLARADependencies

from .clara_utils import write_json_to_file_plain_utf8, read_json_file

from functools import wraps
from decimal import Decimal
import re
import os
#import datetime
from datetime import datetime, timedelta, time
import pytz
#import time
import tempfile
import hashlib
import uuid

def get_user_config(user):
    """
    Returns a dictionary of configuration settings for the given user.
    """
    try:
        user_config = UserConfiguration.objects.get(user=user)
    except UserConfiguration.DoesNotExist:
        # Default configuration if UserConfiguration does not exist
        return {
            'clara_version': 'full_clara',
            'gpt_model': 'gpt-4-1106-preview',
            'max_annotation_words': 250,
            # Add more default configurations here as needed
        }

    return {
        'clara_version': user_config.clara_version,
        'open_ai_api_key': user_config.open_ai_api_key,
        'gpt_model': user_config.gpt_model,
        'max_annotation_words': user_config.max_annotation_words,
    }

def user_has_open_ai_key_or_credit(user):
    user_config = get_user_config(user)
    return ( 'open_ai_api_key' in user_config and user_config['open_ai_api_key'] ) or user.userprofile.credit > 0

def has_saved_internalised_and_annotated_text(project, phonetic=False):
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    return clara_project_internal.get_saved_internalised_and_annotated_text(phonetic=phonetic)

def make_asynch_callback_and_report_id(request, task_type):
    # Create a unique ID to tag messages posted by this task
    report_id = uuid.uuid4()
    user_id = request.user.username
    callback = [ post_task_update_in_db, report_id, user_id, task_type ]
    return ( callback, report_id )

# Used in callback function passed to asynchronous processes,
# so that they can report progress. 
##def post_task_update_in_db(report_id, message):
##    if len(message) > 1000:
##        message = message[:1000] + '...'
##    TaskUpdate.objects.create(report_id=report_id, message=message)

def post_task_update_in_db(report_id, user_id, task_type, message):
    if len(message) > 1000:
        message = message[:1000] + '...'
    TaskUpdate.objects.create(report_id=report_id, user_id=user_id, task_type=task_type, message=message)

# Extract unread messages for a given task ID
##def get_task_updates(report_id):
##    updates = TaskUpdate.objects.filter(report_id=report_id).order_by('timestamp')
##    messages = [update.message for update in updates]
##    updates.delete()  # Delete the updates after reading them
##    for message in messages:
##        print(message)
##    return messages

def get_task_updates(report_id):
    updates = TaskUpdate.objects.filter(report_id=report_id, read=False).order_by('timestamp')
    messages = [update.message for update in updates]
    
    # Mark the updates as read
    updates.update(read=True)
    
    return messages

# Create internal_id by sanitizing the project title and appending the project_id
def create_internal_project_id(title, project_id):
    return re.sub(r'\W+', '_', title) + '_' + str(project_id)

# Old version: incorrect, since people can get back credit by deleting projects

##def store_api_calls(api_calls, project, user, operation):
##    for api_call in api_calls:
##        timestamp = datetime.datetime.fromtimestamp(api_call.timestamp)
##        APICall.objects.create(
##            user=user,
##            project=project,
##            operation=operation,
##            cost=api_call.cost,
##            duration=api_call.duration,
##            retries=api_call.retries,
##            prompt=api_call.prompt,
##            response=api_call.response,
##            timestamp=timestamp,
##        )

# New version: charge calls at once

def store_api_calls(api_calls, project, user, operation):
    user_profile = user.userprofile
    for api_call in api_calls:
        # Now do import datetime from datetime
        # instead of import datetime
        #timestamp = datetime.datetime.fromtimestamp(api_call.timestamp)
        timestamp = datetime.fromtimestamp(api_call.timestamp)
        APICall.objects.create(
            user=user,
            project=project,
            operation=operation,
            cost=api_call.cost,
            duration=api_call.duration,
            retries=api_call.retries,
            prompt=api_call.prompt,
            response=api_call.response,
            timestamp=timestamp,
        )
        # Deduct the cost from the user's credit balance
        user_profile.credit -= Decimal(api_call.cost)
        user_profile.save()


def get_user_api_cost(user):
    total_cost = APICall.objects.filter(user=user).aggregate(Sum('cost'))
    return total_cost['cost__sum'] if total_cost['cost__sum'] is not None else 0

# Temporary function for making credit balances consistent with new scheme of
# charging calls immediately to credit balance.
def update_credit_balances():
    for user in User.objects.all():
        total_cost = get_user_api_cost(user)
        user_profile = user.userprofile
        user_profile.credit -= total_cost
        user_profile.save()

def backup_credit_balances():
    backup_data = []
    for user in User.objects.all():
        total_cost = get_user_api_cost(user)
        credit_balance = user.userprofile.credit
        backup_data.append({
            'user_id': user.id,
            'username': user.username,
            'credit_balance': str(credit_balance),  # Convert Decimal to string for JSON serialization
            'total_cost': str(total_cost),
        })

    backup_file = f"$CLARA/tmp/credit_backup_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
    write_json_to_file_plain_utf8(backup_data, backup_file)

    return backup_file

def restore_credit_balances(backup_file):
    backup_data = read_json_file(backup_file)

    for data in backup_data:
        user = User.objects.get(id=data['user_id'])
        user_profile = user.userprofile
        user_profile.credit = Decimal(data['credit_balance'])
        user_profile.save()

 
def get_project_api_cost(user, project):
    total_cost = APICall.objects.filter(user=user, project=project).aggregate(Sum('cost'))
    return total_cost['cost__sum'] if total_cost['cost__sum'] is not None else 0
   
def get_project_operation_costs(user, project):
    operation_costs = APICall.objects.filter(user=user, project=project).values('operation').annotate(total=Sum('cost'))
    return {item['operation']: item['total'] for item in operation_costs}
    
def get_project_api_duration(user, project):
    total_duration = APICall.objects.filter(user=user, project=project).aggregate(Sum('duration'))
    return total_duration['duration__sum'] / Decimal(60.0) if total_duration['duration__sum'] is not None else 0
    
def get_project_operation_durations(user, project):
    operation_durations = APICall.objects.filter(user=user, project=project).values('operation').annotate(total=Sum('duration'))
    return {item['operation']: item['total'] / Decimal(60.0) for item in operation_durations}

# Decorator to restrict access to project owner
def user_is_project_owner(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        project = CLARAProject.objects.get(pk=kwargs['project_id'])
        if project.user != request.user:
            raise PermissionDenied
        else:
            return function(request, *args, **kwargs)
    return wrap

# Decorator to restrict access to project owner or any user having a role in the project
def user_has_a_project_role(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        project_id = kwargs.get('project_id')
        project = get_object_or_404(CLARAProject, pk=project_id)
        user = request.user
        if user == project.user or ProjectPermissions.objects.filter(user=user, project=project).exists():
            return function(request, *args, **kwargs)
        else:
            raise PermissionDenied
    return wrap

# Check whether user has one of a list of named roles in the project. 
# 'OWNER' matches either the original project owner or another user who has been given the OWNER role.
def user_has_a_named_project_role(user, project_id, role_list):
    return (
        'OWNER' in role_list and user == CLARAProject.objects.get(pk=project_id).user 
        or ProjectPermissions.objects.filter(user=user, project_id=project_id, role__in=role_list).exists()
    )

# Check whether user has language master privileges for at least one language
def language_master_required(function):
    @wraps(function)
    def _wrapped_view(request, *args, **kwargs):
        if LanguageMaster.objects.filter(user=request.user).exists():
            return function(request, *args, **kwargs)
        else:
            return HttpResponseForbidden('You are not authorized to edit language prompts')
    return _wrapped_view

def compute_md5_of_content(content):
    """Compute the MD5 checksum of content."""
    return hashlib.md5(content).hexdigest()

def uploaded_file_to_file(uploaded_file):
    # Read the content from the uploaded file
    file_content = uploaded_file.open("rb").read()
    uploaded_md5 = compute_md5_of_content(file_content)

    # Get the file extension
    file_extension = os.path.splitext(uploaded_file.name)[1]
    
    with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
        
        # Write the content to the temp file
        temp_file.write(file_content)
        
        # Go back to the start of the temp file to read its content
        temp_file.seek(0)
        temp_file_content = temp_file.read()
        temp_file_md5 = compute_md5_of_content(temp_file_content)

        # Check if the MD5 checksums match
        if uploaded_md5 != temp_file_md5:
            print(f'*** Checksum mismatch. Uploaded MD5: {uploaded_md5}, Temp File MD5: {temp_file_md5}')
            return None

        return temp_file.name

# Get current friends. Friend request can work in either direction.
def current_friends_of_user(user):
    return [ friend_request.sender for friend_request in FriendRequest.objects.filter(receiver=user, status='Accepted') ] + \
           [ friend_request.receiver for friend_request in FriendRequest.objects.filter(sender=user, status='Accepted') ]

def create_update(user, update_type, obj):
    """
    Create an Update record for a given user, update type, and object.

    Args:
    user (User): The user who performed the action.
    update_type (str): The type of update (e.g., 'PUBLISH', 'RATE', 'COMMENT', 'FRIEND').
    obj (Model instance): The object related to the update (e.g., Content, Comment, Rating, FriendRequest).
    """
    content_type = ContentType.objects.get_for_model(obj)
    update = Update.objects.create(
        user=user,
        update_type=update_type,
        content_type=content_type,
        object_id=obj.id
    )
    print(f'--- Posted update: "{update}"')
    return update

def get_phase_up_to_date_dict(project, clara_project_internal, user):
    """
    Returns a dict which pairs each phase ID ("plain", "title", "gloss" etc) with
    a Boolean value saying whether the resource in question exists and is up to date.
    """
    human_audio_info = HumanAudioInfo.objects.filter(project=project).first()
    phonetic_human_audio_info = PhoneticHumanAudioInfo.objects.filter(project=project).first()
    format_preferences = FormatPreferences.objects.filter(project=project).first()
    acknowledgements = Acknowledgements.objects.filter(project=project).first()
    content_object = Content.objects.filter(project=project).first()
    questionnaire = SatisfactionQuestionnaire.objects.filter(project=project, user=user).first() 
    clara_dependencies = CLARADependencies(clara_project_internal, project.id,
                                           human_audio_info=human_audio_info, phonetic_human_audio_info=phonetic_human_audio_info,
                                           format_preferences=format_preferences,
                                           acknowledgements=acknowledgements,
                                           content_object=content_object,
                                           questionnaire=questionnaire)
    return clara_dependencies.up_to_date_dict(debug=False)

def send_mail_or_print_trace(subject, body, from_address, to_addresses, fail_silently=False):
    if os.getenv('CLARA_ENVIRONMENT') == 'unisa':
        send_mail(subject, body, from_address, to_addresses, fail_silently=False)
    else:
        print(f' --- On UniSA would do: send_mail({subject}, {body}, {from_address}, {to_addresses}, fail_silently=False)')

def EmailMessage_send_or_print_trace(subject, message, from_email, to_addresses):
    if os.getenv('CLARA_ENVIRONMENT') == 'unisa':
        email = EmailMessage(subject, message, from_email, to_addresses)
        email.content_subtype = "html"  # Set the email content type to HTML
        email.send()
    else:
        print(f' --- On UniSA would do: EmailMessage(subject, message, from_email, to_addresses).send()')

# Gets start time of most recent C-LARA Zoom meeting, assuming it's at 10.30 Swiss time on a Thursday.        
def get_zoom_meeting_start_date():
    adelaide_tz = pytz.timezone('Australia/Adelaide')
    geneva_tz = pytz.timezone('Europe/Zurich')

    now_adelaide = datetime.now(adelaide_tz)
    # Convert 'now' in Adelaide time to Geneva time to calculate based on the meeting start time in Geneva
    now_geneva = now_adelaide.astimezone(geneva_tz)

    # Find the most recent Thursday based on Geneva time
    days_behind = (now_geneva.weekday() - 3) % 7  # Thursday is 3
    last_thursday_geneva = now_geneva.date() - timedelta(days=days_behind)
    # Create a Geneva datetime for last Thursday at 10:30
    meeting_start_geneva = datetime.combine(last_thursday_geneva, time(10, 30), tzinfo=geneva_tz)

    # Convert the meeting time back to Adelaide time to align with server's timezone
    meeting_start_adelaide = meeting_start_geneva.astimezone(adelaide_tz).date()

    return meeting_start_adelaide

from datetime import datetime, timedelta, time
import pytz

def get_previous_week_start_date():
    adelaide_tz = pytz.timezone('Australia/Adelaide')
    geneva_tz = pytz.timezone('Europe/Zurich')

    now_adelaide = datetime.now(adelaide_tz)
    # Convert 'now' in Adelaide time to Geneva time to calculate based on the meeting start time in Geneva
    now_geneva = now_adelaide.astimezone(geneva_tz)

    # Find the most recent Thursday based on Geneva time
    days_behind = (now_geneva.weekday() - 3) % 7  # Thursday is 3
    # Subtract an additional week to get to the previous week's Thursday
    last_thursday_geneva = now_geneva.date() - timedelta(days=days_behind + 7)
    # Create a Geneva datetime for last Thursday at 10:30
    meeting_start_geneva = datetime.combine(last_thursday_geneva, time(10, 30), tzinfo=geneva_tz)

    # Convert the meeting time back to Adelaide time to align with server's timezone
    meeting_start_adelaide = meeting_start_geneva.astimezone(adelaide_tz).date()

    return meeting_start_adelaide

