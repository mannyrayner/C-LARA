from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from .models import CLARAProject
from .models import Community, CommunityMembership
from .forms import ProjectCommunityForm, CreateCommunityForm, UserAndCommunityForm, AssignMemberForm
from .utils import user_is_project_owner
from .utils import user_is_coordinator_of_some_community
from .clara_utils import get_config
import logging

config = get_config()
logger = logging.getLogger(__name__)

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def create_community(request):
    """
    Admin-only view to create a new Community.
    """
    if request.method == 'POST':
        form = CreateCommunityForm(request.POST)
        if form.is_valid():
            community = form.save()
            # Optionally flash a success message, etc.
            return redirect('clara_home_page')  # Or wherever you want
    else:
        form = CreateCommunityForm()

    return render(request, 'clara_app/admin_create_community.html', {
        'form': form
    })

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def delete_community_menu(request):
    """
    Admin-only view that lists all communities and allows for a two-step
    (dropdown -> confirmation) delete process.
    """
    if request.method == 'POST':
        # Distinguish which form step we're on:
        action = request.POST.get('action')

        if action == 'choose_community':
            # The admin selected a community from the dropdown.
            community_id = request.POST.get('community_id')
            if not community_id:
                messages.error(request, "No community selected.")
                return redirect('delete_community_menu')
            
            try:
                community = Community.objects.get(pk=community_id)
            except Community.DoesNotExist:
                messages.error(request, "Selected community does not exist.")
                return redirect('delete_community_menu')

            # Render a confirmation page, passing the selected community
            return render(request, 'clara_app/admin_delete_community_confirm.html', {
                'community': community
            })

        elif action == 'confirm_delete':
            # The admin confirmed deletion
            community_id = request.POST.get('community_id')
            if not community_id:
                messages.error(request, "No community to delete.")
                return redirect('delete_community_menu')

            try:
                community = Community.objects.get(pk=community_id)
                community.delete()
                messages.success(request, f"Community '{community.name}' deleted successfully.")
            except Community.DoesNotExist:
                messages.error(request, "Community does not exist.")
            
            return redirect('delete_community_menu')

        else:
            # Unknown action, just redirect
            return redirect('delete_community_menu')

    else:
        # GET request: show the dropdown of all communities
        communities = Community.objects.order_by('name')
        return render(request, 'clara_app/admin_delete_community_menu.html', {
            'communities': communities
        })


@login_required
def community_home(request, community_id):
    user = request.user
    community = get_object_or_404(Community, pk=community_id)

    membership = CommunityMembership.objects.filter(
        community=community, user=user
    ).first()

    if not membership:
        # The user is not a member of this community
        raise PermissionDenied

    role = membership.role  # "COORDINATOR" or "MEMBER"
    print(f'role = {role}')

    # Build data to pass to the template
    context = {
        'community': community,
        'user_role': role,
    }

    # Add relevant data, e.g. list of all community projects
    projects = CLARAProject.objects.filter(community=community)
    context['projects'] = projects

    # Possibly link to membership views if user_role == 'CO'
    if role == 'CO':
        # e.g. context['members'] = ...
        pass

    return render(request, 'clara_app/community_home.html', context)


@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)  
def assign_coordinator_to_community(request):
    """
    Admin-only view: Turn a user into COORDINATOR in the selected community.
    """
    if request.method == 'POST':
        form = UserAndCommunityForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            community = form.cleaned_data['community']

            # We create/get the membership and set role = COORDINATOR
            membership, created = CommunityMembership.objects.get_or_create(
                community=community, user=user
            )
            membership.role = 'COORDINATOR'
            membership.save()

            # Redirect or show success message
            return redirect('clara_home_page')  # adapt as needed
    else:
        form = UserAndCommunityForm()

    return render(request, 'clara_app/admin_assign_coordinator.html', {
        'form': form,
    })

@login_required
@user_is_coordinator_of_some_community
def assign_member_to_community(request):
    """
    Only a user who is coordinator in at least one community can access this.
    Lets them pick a (user, community) pair to assign the user as an ordinary member.
    """
    if request.method == 'POST':
        # pass the request.user in as 'coordinator_user' so the form can limit communities
        form = AssignMemberForm(request.POST, coordinator_user=request.user)
        if form.is_valid():
            the_user = form.cleaned_data['user']
            the_community = form.cleaned_data['community']
            
            # check if the requesting user is coordinator of that specific community
            # we do the same membership check as in the form’s queryset logic,
            # but let's be extra safe to avoid tampering
            if not CommunityMembership.objects.filter(
                user=request.user,
                community=the_community,
                role='COORDINATOR'
            ).exists():
                raise PermissionDenied("You are not coordinator of that community.")
            
            # create or update membership
            membership, created = CommunityMembership.objects.get_or_create(
                user=the_user,
                community=the_community
            )
            membership.role = 'MEMBER'
            membership.save()

            messages.success(
                request,
                f"Assigned {the_user.username} as a MEMBER in {the_community.name}."
            )
            return redirect('clara_home_page')  # or wherever you want
    else:
        # GET: just show the form
        form = AssignMemberForm(coordinator_user=request.user)

    return render(request, 'clara_app/assign_member_to_community.html', {
        'form': form,
    })

@login_required
@user_is_project_owner
def project_community(request, project_id):
    """
    Allows a project owner to assign/unassign the project's community.
    """
    project = get_object_or_404(CLARAProject, pk=project_id)

    if request.method == 'POST':
        form = ProjectCommunityForm(request.POST, project=project)
        if form.is_valid():
            community_id_str = form.cleaned_data['community_id']
            try:
                if not community_id_str:
                    # The user chose "No community"
                    project.community = None
                    project.save()
                else:
                    # Assign to a real community
                    community_id = int(community_id_str)
                    community = get_object_or_404(Community, pk=community_id)
                    if project.l2 != community.language:
                        raise ValidationError("Project L2 does not match community language")
                    project.community = community
                    project.save()
                    messages.success(request, f"Assigned project to community '{project.community}'.")
            except (ValueError, ValidationError) as e:
                form.add_error('community_id', str(e))
            else:
                return redirect('project_detail', project_id=project.id)
    else:
        # Pre-select the current community if any
        form = ProjectCommunityForm(project=project, initial={
            'community_id': str(project.community.id) if project.community else ''
        })

    return render(request, 'clara_app/project_community.html', {
        'project': project,
        'form': form,
    })

