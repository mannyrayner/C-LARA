from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Q
from django.db.models.functions import Lower
from .models import CLARAProject, ProjectPermissions, CLARAProjectAction, Community, CommunityMembership
from django.contrib.auth.models import User
from .forms import AddProjectMemberForm
from .forms import UpdateProjectTitleForm, UpdateCoherentImageSetForm, ProjectCommunityAndPictureGlossingForm
from .forms import ProjectSearchForm
from .utils import get_user_config
from .utils import get_project_api_cost, get_project_operation_costs, get_project_api_duration, get_project_operation_durations
from .utils import user_is_project_owner, user_has_a_project_role
from .utils import get_phase_up_to_date_dict
from .utils import is_ai_enabled_language

from .clara_main import CLARAProjectInternal
from .clara_phonetic_utils import phonetic_resources_are_available
from .exercises_views import exercises_exist_for_project
from .clara_chinese import is_chinese_language
from .clara_utils import get_config
from .clara_utils import is_chinese_language
import logging

config = get_config()
logger = logging.getLogger(__name__)

def _communities_user_can_attach_to(user, l2):
    return Community.objects.filter(
        language=l2,
        memberships__user=user
    ).distinct()

# Manage the users associated with a project. Users can have the roles 'Owner', 'Annotator' or 'Viewer'
@login_required
@user_is_project_owner
def manage_project_members(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    permissions = ProjectPermissions.objects.filter(project=project)

    if request.method == 'POST':
        form = AddProjectMemberForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            role = form.cleaned_data['role']
            user = get_object_or_404(User, username=user)
            if ProjectPermissions.objects.filter(user=user, project=project).exists():
                messages.error(request, 'This user already has permissions for this project.')
            else:
                ProjectPermissions.objects.create(user=user, project=project, role=role)
                messages.success(request, 'User added successfully!')
                return redirect('manage_project_members', project_id=project_id)
        else:
            messages.error(request, 'Invalid form data. Please try again.')
    else:
        form = AddProjectMemberForm()

    clara_version = get_user_config(request.user)['clara_version']

    context = {
        'project': project,
        'permissions': permissions,
        'form': form,
        'clara_version': clara_version,
    }
    
    return render(request, 'clara_app/manage_project_members.html', context)

# Remove a member from a project
@login_required
def remove_project_member(request, permission_id):
    permission = get_object_or_404(ProjectPermissions, pk=permission_id)
    
    if request.method == 'POST':
        permission.delete()
        messages.success(request, 'User removed successfully!')
    else:
        messages.error(request, 'Invalid request.')
    
    return redirect('manage_project_members', project_id=permission.project.id)
      
# List projects on which the user has a role    
@login_required
def project_list(request, clara_version):
    user = request.user
    search_form = ProjectSearchForm(request.GET or None)
    query = Q((Q(user=user) | Q(projectpermissions__user=user)))

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
    
    project_data = {}
    for project in projects:
        role = 'OWNER' if project.user == user else ProjectPermissions.objects.get(user=user, project=project).role
        project_data[project] = {
            'role': role,  
        }

    paginator = Paginator(list(project_data.items()), 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Display the project using this version of C-LARA
    clara_version_to_access_with = clara_version
    # Display the menus using this version of C-LARA
    clara_version_for_menus = get_user_config(request.user)['clara_version']

    return render(request, 'clara_app/project_list.html',
                  {'search_form': search_form,
                   'page_obj': page_obj,
                   'clara_version_to_access_with': clara_version_to_access_with,
                   'clara_version': clara_version_for_menus})

# Delete a project
@login_required
@user_is_project_owner
def delete_project(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    if request.method == 'POST':
        project.delete()
        clara_project_internal.delete()
        return redirect('project_list', 'normal')
    else:
        
        clara_version = get_user_config(request.user)['clara_version']
        
        return render(request, 'clara_app/confirm_delete.html', {'project': project, 'clara_version': clara_version})

# Display information and functionalities associated with a project     
@login_required
@user_has_a_project_role
def project_detail(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    ai_enabled_l2 = is_ai_enabled_language(project.l2)
    ai_enabled_l1 = is_ai_enabled_language(project.l1)
    text_versions = clara_project_internal.text_versions
    up_to_date_dict = get_phase_up_to_date_dict(project, clara_project_internal, request.user)

    attachable_communities = _communities_user_can_attach_to(request.user, project.l2)

    user_is_member_of_project_community = (
        project.community is not None and
        CommunityMembership.objects.filter(community=project.community, user=request.user).exists()
    )

    can_show_picture_glossing_controls = bool(project.community) and user_is_member_of_project_community

    can_create_segmented_text = clara_project_internal.text_versions["plain"]
    can_create_segmented_title = clara_project_internal.text_versions["title"]
    can_create_phonetic_text = clara_project_internal.text_versions["segmented"] and phonetic_resources_are_available(project.l2)
    can_create_glossed_and_lemma_text = clara_project_internal.text_versions["segmented"]
    can_create_glossed_text_from_lemma = clara_project_internal.text_versions["lemma"]
    can_create_pinyin_text = clara_project_internal.text_versions["segmented"] and is_chinese_language(project.l2) 
    can_render_normal = clara_project_internal.text_versions["gloss"] and clara_project_internal.text_versions["lemma"]
    can_picture_gloss = can_render_normal
    can_create_exercises = can_render_normal
    picture_glossing_enabled = bool(project.uses_picture_glossing)
    can_render_phonetic = clara_project_internal.text_versions["phonetic"] 
    rendered_html_exists = clara_project_internal.rendered_html_exists(project_id)
    rendered_phonetic_html_exists = clara_project_internal.rendered_phonetic_html_exists(project_id)
    images = clara_project_internal.get_all_project_images()
    images_exist = len(images) != 0
    exercises_exist = exercises_exist_for_project(project_id)
    api_cost = get_project_api_cost(request.user, project)
    
    if request.method == 'POST':
        title_form = UpdateProjectTitleForm(request.POST, prefix="title")
        image_set_form = UpdateCoherentImageSetForm(request.POST, prefix="image_set")

        community_form = ProjectCommunityAndPictureGlossingForm(
            request.POST,
            prefix="community",
            communities=attachable_communities
        )

        if 'submit_title' in request.POST and title_form.is_valid() and title_form.cleaned_data['new_title']:
            project.title = title_form.cleaned_data['new_title']
            project.save()
            messages.success(request, "Project title updated")

        elif 'submit_image_set' in request.POST and image_set_form.is_valid():
            project.uses_coherent_image_set = image_set_form.cleaned_data['uses_coherent_image_set']
            project.uses_coherent_image_set_v2 = image_set_form.cleaned_data['uses_coherent_image_set_v2']
            project.use_translation_for_images = image_set_form.cleaned_data['use_translation_for_images']
            project.has_image_questionnaire = image_set_form.cleaned_data['has_image_questionnaire']
            project.save()
            messages.success(request, "Project information updated")

        elif 'submit_community' in request.POST and community_form.is_valid():
            # Attach community (only if user is a member)
            community_id = community_form.cleaned_data.get('community') or ''
            if community_id:
                community = get_object_or_404(Community, id=int(community_id), language=project.l2)
                # verify membership
                if not CommunityMembership.objects.filter(community=community, user=request.user).exists():
                    messages.error(request, "You are not a member of that community.")
                else:
                    project.community = community
            # Toggle picture glossing only if project is attached
            if project.community:
                project.uses_picture_glossing = bool(community_form.cleaned_data.get('uses_picture_glossing'))
                project.picture_gloss_style = community_form.cleaned_data.get('picture_gloss_style') or 'any'
                # If picture glossing was turned off, you may want to blank style; optional.
            else:
                # If not attached, force picture glossing off
                project.uses_picture_glossing = False
                project.picture_gloss_style = ''
            project.save()
            messages.success(request, "Community / picture glossing settings updated")

    else:
        title_form = UpdateProjectTitleForm(prefix="title")
        image_set_form = UpdateCoherentImageSetForm(prefix="image_set",
                                                    initial={'uses_coherent_image_set': project.uses_coherent_image_set,
                                                             'uses_coherent_image_set_v2': project.uses_coherent_image_set_v2,
                                                             'use_translation_for_images': project.use_translation_for_images,
                                                             'has_image_questionnaire': project.has_image_questionnaire
                                                             })
        community_form = ProjectCommunityAndPictureGlossingForm(prefix="community",
                                                                communities=attachable_communities,
                                                                initial={'community': str(project.community.id) if project.community else '',
                                                                         'uses_picture_glossing': project.uses_picture_glossing,
                                                                         'picture_gloss_style': project.picture_gloss_style or 'any'
                                                                         }
                                                                )

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/project_detail.html', 
                  { 'project': project,
                    'ai_enabled_l2': ai_enabled_l2,
                    'ai_enabled_l1': ai_enabled_l1,
                    'title_form': title_form,
                    'image_set_form': image_set_form,
                    'api_cost': api_cost,
                    'text_versions': text_versions,
                    'images_exist': images_exist,
                    'up_to_date_dict': up_to_date_dict,
                    'can_create_segmented_text': can_create_segmented_text,
                    'can_create_segmented_title': can_create_segmented_title,
                    'can_create_phonetic_text': can_create_phonetic_text,
                    'can_create_glossed_and_lemma_text': can_create_glossed_and_lemma_text,
                    'can_create_glossed_text_from_lemma': can_create_glossed_text_from_lemma,
                    'can_create_pinyin_text': can_create_pinyin_text,
                    'can_render_normal': can_render_normal,
                    'can_render_phonetic': can_render_phonetic,
                    'community_form': community_form,
                    'attachable_communities_exist': attachable_communities.exists(),
                    'user_is_member_of_project_community': user_is_member_of_project_community,
                    'can_show_picture_glossing_controls': can_show_picture_glossing_controls,
                    'can_picture_gloss': can_picture_gloss,
                    'can_create_exercises': can_create_exercises,
                    'exercises_exist': exercises_exist,
                    'picture_glossing_enabled': bool(project.uses_picture_glossing),
                    'rendered_html_exists': rendered_html_exists,
                    'rendered_phonetic_html_exists': rendered_phonetic_html_exists,
                    'clara_version': clara_version,
                    }
                    )

# Display the history of updates to project files 
@login_required
@user_has_a_project_role
def project_history(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    actions = CLARAProjectAction.objects.filter(project=project).order_by('-timestamp')

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/project_history.html', {'project': project, 'actions': actions, 'clara_version': clara_version})
