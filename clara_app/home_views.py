
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Q, Case, Value, When, IntegerField
from django.utils import timezone

from .models import Content
from .models import Activity
from .models import CommunityMembership
from .forms import UnifiedSearchForm
from .clara_utils import get_config
from .constants import DEFAULT_RECENT_TIME_PERIOD
from datetime import timedelta
import logging

config = get_config()
logger = logging.getLogger(__name__)

# Welcome screen
def home(request):
    return redirect('home_page')

def home_page(request):
    user = request.user

    # Find all communities the user belongs to
    memberships = CommunityMembership.objects.filter(user=user)
    
    if not memberships.exists():
        # Not a member of any community => go to normal C-LARA home page
        return redirect('clara_home_page')

    # If the user belongs to exactly one community, go straight there
    if memberships.count() == 1:
        membership = memberships.first()
        return redirect('community_home', community_id=membership.community.id)

    # Otherwise, present a small page letting the user pick which community or normal LARA home
    return render(request, 'clara_app/select_community_or_home.html', {
        'memberships': memberships,
    })

@login_required
def clara_home_page(request):
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

    # Order by custom status order, and then by creation date
    return activities.order_by('status_order', '-created_at')
