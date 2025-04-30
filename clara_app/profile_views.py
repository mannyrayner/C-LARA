from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.urls import reverse

from .models import UserProfile, FriendRequest
from django.contrib.auth.models import User

from .forms import UserForm, UserProfileForm, FriendRequestForm
from .utils import get_user_config
from .utils import create_update
from .clara_utils import get_config

import os
import logging

config = get_config()
logger = logging.getLogger(__name__)

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
