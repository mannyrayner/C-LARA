from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Q

from .models import FriendRequest, Content, Update
from .models import Comment, Rating
from django.contrib.auth.models import User
from .utils import get_user_config
from .utils import current_friends_of_user
from .clara_utils import get_config
import logging

config = get_config()
logger = logging.getLogger(__name__)

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
    if update.update_type == 'FRIEND':
        return isinstance(update.content_object, FriendRequest) and \
               isinstance(update.content_object.sender, User) and \
               isinstance(update.content_object.receiver, User)
    elif update.update_type == 'RATE':
        return isinstance(update.content_object, Rating) and \
               isinstance(update.content_object.user, User) and \
               isinstance(update.content_object.content, Content)
    elif update.update_type == 'COMMENT':
        return isinstance(update.content_object, Comment) and \
               isinstance(update.content_object.user, User) and \
               isinstance(update.content_object.content, Content)
    elif update.update_type == 'PUBLISH':
        return isinstance(update.content_object, Comment) and \
               isinstance(update.user, User) and \
               isinstance(update.content_object, Content)
    else:
        print(f'Warning: bad update: {update}')
        return False

