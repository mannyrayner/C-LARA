
from django.db.models import Sum
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from django_q.models import OrmQ

from functools import wraps
from decimal import Decimal
import os
import datetime
import time
import tempfile
import hashlib
import uuid

from .models import CLARAProject, UserConfiguration, APICall, ProjectPermissions, LanguageMaster, TaskUpdate

import re

def get_user_config(user):
    """
    Returns a dictionary of configuration settings for the given user.
    """
    try:
        user_config = UserConfiguration.objects.get(user=user)
    except UserConfiguration.DoesNotExist:
        # Default configuration if UserConfiguration does not exist
        return {
            'gpt_model': 'gpt-4',
            # Add more default configurations here as needed
        }

    return {
        'gpt_model': user_config.gpt_model,
        'max_annotation_words': user_config.max_annotation_words,
    }

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

def delete_all_tasks():
    OrmQ.objects.all().delete()
    time.sleep(1)

# Create internal_id by sanitizing the project title and appending the project_id
def create_internal_project_id(title, project_id):
    return re.sub(r'\W+', '_', title) + '_' + str(project_id)

def store_api_calls(api_calls, project, user, operation):
    for api_call in api_calls:
        timestamp = datetime.datetime.fromtimestamp(api_call.timestamp)
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

def get_user_api_cost(user):
    total_cost = APICall.objects.filter(user=user).aggregate(Sum('cost'))
    return total_cost['cost__sum'] if total_cost['cost__sum'] is not None else 0
    
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
 
# Uploaded files aren't always files.
##def uploaded_file_to_file(uploaded_file):
##    try:
##        return uploaded_file.temporary_file_path()
##    except AttributeError:
##        # If not, save the uploaded file to a new temporary file
##        temp_file = tempfile.NamedTemporaryFile(delete=False)
##        for chunk in uploaded_file.chunks():
##            temp_file.write(chunk)
##        temp_file.close()
##        return temp_file.name

##def uploaded_file_to_file(uploaded_file):
##    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
##        print(f'Type: {type(uploaded_file)}')
##        print(f'Size: {uploaded_file.size} bytes')
##        #file_content = uploaded_file.read()  # Read the entire content
##        file_content = uploaded_file.open("rb").read()
##        temp_file.write(file_content)
##        return temp_file.name

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
