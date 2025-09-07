# All this material moved to content_views.py

##from django.contrib.auth.decorators import login_required
##from django.shortcuts import render, redirect, get_object_or_404
##from django.contrib import messages
##from django.core.exceptions import PermissionDenied
##
##from .models import Content
##from .models import CLARAProject, HumanAudioInfo, PhoneticHumanAudioInfo
##from .forms import RegisterAsContentForm
##from .utils import get_user_config
##from .utils import user_has_a_project_role, user_has_a_named_project_role
##from .utils import create_update
##
##from .clara_main import CLARAProjectInternal
##from .clara_registering_utils import register_project_content_helper
##from .clara_utils import get_config
##from .clara_utils import post_task_update
##import logging
##import traceback
##
##config = get_config()
##logger = logging.getLogger(__name__)
##
##@login_required
##@user_has_a_project_role
##def offer_to_register_content_normal(request, project_id):
##    return offer_to_register_content(request, 'normal', project_id)
##
##@login_required
##@user_has_a_project_role
##def offer_to_register_content_phonetic(request, project_id):
##    return offer_to_register_content(request, 'phonetic', project_id)
##
##def offer_to_register_content(request, phonetic_or_normal, project_id):
##    project = get_object_or_404(CLARAProject, pk=project_id)
##    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
##
##    if phonetic_or_normal == 'normal':
##        succeeded = clara_project_internal.rendered_html_exists(project_id)
##    else:
##        succeeded = clara_project_internal.rendered_phonetic_html_exists(project_id)
##
##    if succeeded:
##        # Define URLs for the first page of content and the zip file
##        content_url = True
##        # Put back zipfile later
##        #zipfile_url = True
##        zipfile_url = None
##        # Create the form for registering the project content
##        register_form = RegisterAsContentForm()
##        messages.success(request, f'Rendered text found')
##    else:
##        content_url = None
##        zipfile_url = None
##        register_form = None
##        messages.error(request, "Rendered text not found")
##
##    clara_version = get_user_config(request.user)['clara_version']
##        
##    return render(request, 'clara_app/render_text_complete.html',
##                  {'phonetic_or_normal': phonetic_or_normal,
##                   'content_url': content_url, 'zipfile_url': zipfile_url,
##                   'project': project, 'register_form': register_form, 'clara_version': clara_version})
##
### Register content produced by rendering from a project        
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
##            # Main processing happens in the helper function, which is shared with simple-C-LARA
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
##
