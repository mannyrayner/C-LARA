from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone

from .models import TaskUpdate
from .utils import get_user_config
from .clara_utils import get_config
from datetime import timedelta
import logging

config = get_config()
logger = logging.getLogger(__name__)

# Display recent task update messages
@login_required
def view_task_updates(request):
    time_threshold = timezone.now() - timedelta(minutes=60)
    user_id = request.user.username
    updates = TaskUpdate.objects.filter(timestamp__gte=time_threshold, user_id=user_id).order_by('-timestamp')

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/view_task_updates.html', {'updates': updates, 'clara_version': clara_version})

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def delete_old_task_updates(request):
    threshold_date = timezone.now() - timedelta(days=30)
    deleted_count, _ = TaskUpdate.objects.filter(timestamp__lt=threshold_date).delete()

    messages.success(request, f"{deleted_count} old task updates were successfully deleted.")
    return redirect('view_task_updates')

