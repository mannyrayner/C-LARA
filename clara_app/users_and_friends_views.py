
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.core.paginator import Paginator

from .models import FriendRequest
from django.contrib.auth.models import User
from .utils import get_user_config
from .utils import current_friends_of_user
from .clara_utils import get_config
import logging

config = get_config()
logger = logging.getLogger(__name__)

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

