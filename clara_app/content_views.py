from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Count, Avg, Q, F, Sum
from django.db.models.functions import Lower
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone
from django.core.cache import cache
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.conf import settings

from .public_api_views import public_content_manifest

from .models import Content
from .models import CLARAProject, Comment, Rating, HumanAudioInfo, PhoneticHumanAudioInfo
from .forms import ContentSearchForm, ContentRegistrationForm, ContentUnlockForm
from .forms import DeleteContentForm, RegisterAsContentForm
from .forms import RatingForm, CommentForm
from .utils import get_user_config, user_has_a_project_role, user_has_a_named_project_role, create_update
from .clara_main import CLARAProjectInternal
from .clara_registering_utils import register_project_content_helper
from .clara_utils import get_config
from datetime import timedelta
from ipware import get_client_ip

import os
import logging

config = get_config()
logger = logging.getLogger(__name__)

SIGNER = TimestampSigner(salt="clara-public-content")

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
##@login_required
##@user_has_a_project_role
##def register_project_content(request, phonetic_or_normal, project_id):
##    project = get_object_or_404(CLARAProject, pk=project_id)
##
##    if request.method == 'POST':
##        form = RegisterAsContentForm(request.POST)
##        if form.is_valid() and form.cleaned_data.get('register_as_content'):
##            if not user_has_a_named_project_role(request.user, project_id, ['OWNER']):
##                raise PermissionDenied("You don't have permission to register a text.")
##
##            # register_project_content_helper, shared with simple-C-LARA, creates the associated Content object
##            content = register_project_content_helper(project_id, phonetic_or_normal)
##            
##            # Create an Update record for the update feed
##            if content:
##                create_update(request.user, 'PUBLISH', content)
##            
##            return redirect(content.get_absolute_url())
##
##    # If the form was not submitted or was not valid, redirect back to the project detail page.
##    return redirect('project_detail', project_id=project.id)

@login_required
@user_has_a_project_role
def register_project_content(request, phonetic_or_normal, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)

    if request.method == 'POST':
        form = RegisterAsContentForm(request.POST)
        if form.is_valid() and form.cleaned_data.get('register_as_content'):
            if not user_has_a_named_project_role(request.user, project_id, ['OWNER']):
                raise PermissionDenied("You don't have permission to register a text.")

            content = register_project_content_helper(project_id, phonetic_or_normal)

            if content:
                # Set password if provided
                raw_pw = form.cleaned_data.get("password") or None
                hint = form.cleaned_data.get("password_hint") or ""
                if raw_pw:
                    print(f'set password = {raw_pw}')
                    content.set_password(raw_pw)
                    content.password_hint = hint
                    content.save(update_fields=["password_hash", "password_hint", "password_last_set"])
                create_update(request.user, 'PUBLISH', content)

            return redirect(content.get_absolute_url())

    return redirect('project_detail', project_id=project.id)

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

    unlocked_key = f"content_unlocked_{content.id}"

    unlock_form = None

    # Only increment access count *after* unlock for protected content
    can_view = (not content.is_protected) or request.session.get(unlocked_key, False)

    if can_view:
        # Access counting
        content.unique_access_count = F('unique_access_count') + 1
        content.save(update_fields=['unique_access_count'])
        content.refresh_from_db()
        
    if request.method == 'POST':
        # Handle unlock POST
        if content.is_protected:
            unlock_form = ContentUnlockForm(request.POST)
            client_ip, _ = get_client_ip(request, request_header_order=[
                'HTTP_X_FORWARDED_FOR', 'HTTP_X_REAL_IP', 'REMOTE_ADDR'
            ])
            client_ip = client_ip or '0.0.0.0'
            if too_many_attempts(client_ip, content.id):
                messages.error(request, "Too many attempts. Try again later.")
            elif form.is_valid():
                if content.check_password(form.cleaned_data["password"]):
                    request.session[unlocked_key] = True
                    # create a signed token for programmatic manifest fetches
                    token = SIGNER.sign(f"{content.id}:{request.session.session_key}")
                    request.session[f"{unlocked_key}_token"] = token
                    messages.success(request, "Unlocked.")
                    return redirect('content_detail', content_id=content.id)
                else:
                    messages.error(request, "Incorrect password.")
        else:
            unlock_form = ContentUnlockForm()
        
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

    zip_exists = content.project.zip_exists(content.text_type)
    zip_fresh = content.project.zip_is_fresh(content.text_type) if content.project else False

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/content_detail.html', {
        'unlock_form': unlock_form if content.is_protected and not can_view else None,
        'can_delete': can_delete,
        'delete_form': delete_form,
        'content': content,
        'zip_exists': zip_exists,
        'zip_fresh': zip_fresh,
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
    unlocked_key = f"content_unlocked_{content.id}"

    # Handle unlock POST
    if request.method == "POST" and content.is_protected:
        form = ContentUnlockForm(request.POST)
        client_ip, _ = get_client_ip(request, request_header_order=[
            'HTTP_X_FORWARDED_FOR', 'HTTP_X_REAL_IP', 'REMOTE_ADDR'
        ])
        client_ip = client_ip or '0.0.0.0'
        if too_many_attempts(client_ip, content.id):
            messages.error(request, "Too many attempts. Try again later.")
        elif form.is_valid():
            if content.check_password(form.cleaned_data["password"]):
                request.session[unlocked_key] = True
                # create a signed token for programmatic manifest fetches
                token = SIGNER.sign(f"{content.id}:{request.session.session_key}")
                request.session[f"{unlocked_key}_token"] = token
                messages.success(request, "Unlocked.")
                return redirect('public_content_detail', content_id=content.id)
            else:
                messages.error(request, "Incorrect password.")
    else:
        form = ContentUnlockForm()

    # Only increment access count *after* unlock for protected content
    can_view = (not content.is_protected) or request.session.get(unlocked_key, False)
    manifest = None
    if can_view:
        try:
            manifest = public_content_manifest(request, content_id)
        except Exception:
            manifest = None

        # Access counting
        content.unique_access_count = F('unique_access_count') + 1
        content.save(update_fields=['unique_access_count'])
        content.refresh_from_db()

    comments = Comment.objects.filter(content=content).order_by('timestamp')
    average_rating = Rating.objects.filter(content=content).aggregate(Avg('rating'))

    token = request.session.get(f"{unlocked_key}_token") if can_view and content.is_protected else None

    zip_exists = content.project.zip_exists(content.text_type)
    zip_fresh = content.project.zip_is_fresh(content.text_type) if content.project else False

    return render(request, 'clara_app/public_content_detail.html', {
        'content': content,
        'zip_exists': zip_exists,
        'zip_fresh': zip_fresh,
        'manifest': manifest if can_view else None,
        'comments': comments,
        'average_rating': average_rating['rating__avg'],
        'unlock_form': form if content.is_protected and not can_view else None,
        'access_token': token,  # for programmatic clients
    })

# Use ipware function instead
##def get_client_ip(request):
##    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
##    if x_forwarded_for:
##        ip = x_forwarded_for.split(',')[0]
##    else:
##        ip = request.META.get('REMOTE_ADDR')
##    return ip

def build_content_zip(request, content_id):
    content = get_object_or_404(Content, id=content_id)
    project = content.project
    if not project:
        messages.error(request, "This content is external; no zip can be built.")
        return redirect('public_content_detail', content_id=content.id)

    try:
        project.build_zip(content.text_type)
        messages.success(request, "Zipfile created/updated.")
    except Exception as e:
        messages.error(request, f"Failed to build zipfile: {e}")

    return redirect('public_content_detail', content_id=content.id)

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

def too_many_attempts(ip: str, content_id: int, limit=10, window_minutes=15) -> bool:
    key = f"pw_attempts:{content_id}:{ip}"
    data = cache.get(key, {"count": 0, "start": timezone.now()})
    if (timezone.now() - data["start"]).total_seconds() > window_minutes * 60:
        data = {"count": 0, "start": timezone.now()}
    data["count"] += 1
    cache.set(key, data, timeout=window_minutes * 60)
    return data["count"] > limit
