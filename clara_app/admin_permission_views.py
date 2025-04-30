from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.db.models.functions import Lower

from .models import UserProfile
from .models import CLARAProject, ProjectPermissions
from django.contrib.auth.models import User

from .forms import UserSelectForm, AdminPasswordResetForm, ProjectSelectionFormSet
from .forms import UserPermissionsForm
from .forms import ProjectSearchForm
from .utils import get_user_config
from .clara_utils import get_config
import logging

config = get_config()
logger = logging.getLogger(__name__)

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

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def manage_user_permissions(request):
    user_select_form = UserSelectForm(request.POST or None)
    permissions_form = None
    selected_user_id = None  # Initialize selected_user_id

    if request.method == 'POST' and 'select_user' in request.POST:
        if user_select_form.is_valid():
            selected_user = user_select_form.cleaned_data['user']
            selected_user_id = selected_user.id  # Store the selected user's ID
            permissions_form = UserPermissionsForm(instance=selected_user.userprofile)
    elif request.method == 'POST':
        selected_user_id = request.POST.get('selected_user_id')  # Retrieve the selected user's ID from the POST data
        selected_user_profile = get_object_or_404(UserProfile, user__id=selected_user_id)
        permissions_form = UserPermissionsForm(request.POST, instance=selected_user_profile)
        if permissions_form.is_valid():
            permissions_form.save()
            messages.success(request, 'User permissions updated successfully.')
            return redirect('manage_user_permissions')
    else:
        user_select_form = UserSelectForm()

    return render(request, 'clara_app/manage_user_permissions.html', {
        'user_select_form': user_select_form,
        'permissions_form': permissions_form,
        'selected_user_id': selected_user_id,  # Pass selected_user_id to the template
    })
