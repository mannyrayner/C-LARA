from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Count, Avg, Q, F, Sum
from django.db.models.functions import Lower
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone

from .public_api_views import public_content_manifest

from .models import Content
from .models import CLARAProject, Comment, Rating
from django.contrib.auth.models import User
from .forms import ContentSearchForm, ContentRegistrationForm
from .forms import DeleteContentForm
from .forms import RatingForm, CommentForm
from .utils import get_user_config
from .utils import create_update
from .clara_utils import get_config
from datetime import timedelta
from ipware import get_client_ip

import os
import logging

config = get_config()
logger = logging.getLogger(__name__)

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
            days_ago = timezone.now() - timedelta(days=int(time_period))
            query &= Q(updated_at__gte=days_ago)

    content_list = Content.objects.filter(query)

    # Figure out how the user wants to sort:
    order_by = request.GET.get('order_by')
    if order_by == 'title':
        # Order ascending by title
        content_list = content_list.order_by(Lower('title'))
    elif order_by == 'age':
        # "Newest first" or "oldest first"? 
        # If you want newest first, just do '-updated_at'
        content_list = content_list.order_by('-updated_at')
    elif order_by == 'accesses':
        # Sort by number of accesses, largest first
        content_list = content_list.order_by('-unique_access_count')
    else:
        # Default to alphabetical
        content_list = content_list.order_by(Lower('title'))

    paginator = Paginator(content_list, 10)  # Show 10 content items per page
    page = request.GET.get('page')
    contents = paginator.get_page(page)

    clara_version = get_user_config(request.user)['clara_version']

    return render(
        request,
        'clara_app/content_list.html',
        {
            'contents': contents,
            'search_form': search_form,
            'clara_version': clara_version
        }
    )

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
            days_ago = timezone.now() - timedelta(days=int(time_period))
            query &= Q(updated_at__gte=days_ago)

    content_list = Content.objects.filter(query)

    # Figure out how the user wants to sort:
    order_by = request.GET.get('order_by')
    if order_by == 'title':
        # Order ascending by title
        content_list = content_list.order_by(Lower('title'))
    elif order_by == 'age':
        # "Newest first" or "oldest first"? 
        # If you want newest first, just do '-updated_at'
        content_list = content_list.order_by('-updated_at')
    elif order_by == 'accesses':
        # Sort by number of accesses, largest first
        content_list = content_list.order_by('-unique_access_count')
    else:
        # Default to alphabetical
        content_list = content_list.order_by(Lower('title'))

    paginator = Paginator(content_list, 10)  # Show 10 content items per page
    page = request.GET.get('page')
    contents = paginator.get_page(page)

    return render(request, 'clara_app/public_content_list.html', {'contents': contents, 'search_form': search_form})

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


def public_content_detail(request, content_id):
    content = get_object_or_404(Content, id=content_id)
    manifest = public_content_manifest(request, content_id)
    
    comments = Comment.objects.filter(content=content).order_by('timestamp')  
    average_rating = Rating.objects.filter(content=content).aggregate(Avg('rating'))

    # Print out all request headers for debugging
    headers = request.META

    # Get the client's IP address
    #client_ip, is_routable = get_client_ip(request, request_header_order=['X_FORWARDED_FOR', 'REMOTE_ADDR'], proxy_count=1)
    client_ip, is_routable = get_client_ip(request, request_header_order=['HTTP_X_FORWARDED_FOR', 'HTTP_X_REAL_IP', 'REMOTE_ADDR'])
    
    #client_ip, is_routable = get_client_ip(request, proxy_count=1)
    
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

    return render(request, 'clara_app/public_content_detail.html', {
        'content': content,
        'manifest': manifest,
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

# Get summary tables for projects and content, broken down by language
def language_statistics(request):
    # Aggregate project counts by l2 language, forcing lowercase
    project_stats = (
        CLARAProject.objects
            .annotate(l2_lower=Lower('l2'))
            .values('l2_lower')
            .annotate(total=Count('id'))
            .order_by('-total')
    )

    # Aggregate content counts by l2 language, forcing lowercase
    content_stats = (
        Content.objects
            .annotate(l2_lower=Lower('l2'))
            .values('l2_lower')
            .annotate(total=Count('id'), total_access=Sum('unique_access_count'))
            .order_by('-total')
    )

    # Calculate the totals
    total_projects = sum(stat['total'] for stat in project_stats)
    total_contents = sum(stat['total'] for stat in content_stats)
    total_accesses = sum(
        stat['total_access']
        for stat in content_stats
        if stat['total_access'] is not None
    )

    return render(request, 'clara_app/language_statistics.html', {
        'project_stats': project_stats,
        'content_stats': content_stats,
        'total_projects': total_projects,
        'total_contents': total_contents,
        'total_accesses': total_accesses,
    })
