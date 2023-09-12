from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, FileResponse, JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.core.paginator import Paginator
from django.contrib import messages
from django.conf import settings
from django import forms
from django.db.models import Avg, Q
from django.db.models.functions import Lower
from django.core.exceptions import PermissionDenied

# Remove custom User
#from .models import User, UserProfile, LanguageMaster, Content, CLARAProject, ProjectPermissions, CLARAProjectAction, Comment, Rating
from .models import UserProfile, LanguageMaster, Content, CLARAProject, ProjectPermissions, CLARAProjectAction, Comment, Rating
from django.contrib.auth.models import User

# ASYNCHRONOUS PROCESSING
from django_q.tasks import async_task
from django_q.models import Task

from .forms import RegistrationForm, UserForm, UserProfileForm, AssignLanguageMasterForm, AddProjectMemberForm, ContentRegistrationForm
from .forms import ProjectCreationForm, UpdateProjectTitleForm, AddCreditForm, DeleteTTSDataForm, AudioMetadataForm
from .forms import CreatePlainTextForm, CreateSummaryTextForm, CreateCEFRTextForm, CreateSegmentedTextForm
from .forms import CreateGlossedTextForm, CreateLemmaTaggedTextForm, CreateLemmaAndGlossTaggedTextForm
from .forms import RenderTextForm, RegisterAsContentForm, RatingForm, CommentForm, DiffSelectionForm
from .forms import TemplateForm, PromptSelectionForm, StringForm, StringPairForm, CustomTemplateFormSet, CustomStringFormSet, CustomStringPairFormSet
from .utils import create_internal_project_id, store_api_calls
from .utils import get_user_api_cost, get_project_api_cost, get_project_operation_costs, get_project_api_duration, get_project_operation_durations
from .utils import user_is_project_owner, user_has_a_project_role, user_has_a_named_project_role, language_master_required
from .utils import post_task_update_in_db, get_task_updates, delete_all_tasks

from .clara_core.clara_main import CLARAProjectInternal
from .clara_core.clara_internalise import internalize_text
from .clara_core.clara_prompt_templates import PromptTemplateRepository
from .clara_core.clara_audio_annotator import AudioAnnotator
from .clara_core.clara_conventional_tagging import fully_supported_treetagger_language
from .clara_core.clara_chinese import is_chinese_language
from .clara_core.clara_classes import TemplateError, InternalCLARAError, InternalisationError
from .clara_core.clara_utils import _s3_storage, _s3_bucket, absolute_file_name, file_exists, read_txt_file, output_dir_for_project_id, post_task_update, is_rtl_language

from pathlib import Path
from decimal import Decimal
from urllib.parse import unquote
import re
import json
import zipfile
import shutil
import mimetypes
import logging
import pprint
import uuid

# Create a new account    
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()  # This will save username and password.
            user.email = form.cleaned_data.get('email')  # This will save email.
            user.save()  # Save the user object again.
            
            # Create the UserProfile instance and associate it with the new user.
            UserProfile.objects.create(user=user)

            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'clara_app/register.html', {'form': form})


# Welcome screen
def home(request):
    return HttpResponse("Welcome to C-LARA!")

# Show user profile
@login_required
def profile(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'clara_app/profile.html', {'profile': profile, 'email': request.user.email})
    
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

    context = {
        'u_form': u_form,
        'p_form': p_form
    }

    return render(request, 'clara_app/edit_profile.html', context)
    
# Credit balance for money spent on API calls    
@login_required
def credit_balance(request):
    total_cost = get_user_api_cost(request.user)
    credit_balance = request.user.userprofile.credit - total_cost  
    return render(request, 'clara_app/credit_balance.html', {'credit_balance': credit_balance})
    
# Remove custom User
# Add credit to account
@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def add_credit(request):
    if request.method == 'POST':
        form = AddCreditForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            credit = form.cleaned_data['credit']
            user.userprofile.credit += credit
            user.userprofile.save()
            messages.success(request, "Credit added successfully")
    else:
        form = AddCreditForm()
    return render(request, 'clara_app/add_credit.html', {'form': form})

def delete_tts_data_for_language(language, callback=None):
    post_task_update(callback, f"--- Starting delete task for language {language}")
    tts_annotator = AudioAnnotator(language, callback=callback)
    tts_annotator.delete_entries_for_language(callback=callback)

# Delete cached TTS data for language   
@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def delete_tts_data(request):
    if request.method == 'POST':
        form = DeleteTTSDataForm(request.POST)
        if form.is_valid():
            language = form.cleaned_data['language']
            
            # Create a unique ID to tag messages posted by this task, and a callback
            report_id = uuid.uuid4()
            callback = [post_task_update_in_db, report_id]

            async_task(delete_tts_data_for_language, language, callback=callback)
            print(f'--- Started delete task {language}')
            #Redirect to the monitor view, passing the task ID and report ID as parameters
            return redirect('delete_tts_data_monitor', language, report_id)

    else:
        form = DeleteTTSDataForm()
    return render(request, 'clara_app/delete_tts_data.html', {
        'form': form,
    })

# This is the API endpoint that the JavaScript will poll
@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def delete_tts_data_status(request, report_id):
    messages = get_task_updates(report_id)
    print(f'{len(messages)} messages received')
    if 'error' in messages:
        status = 'error'
    elif 'finished' in messages:
        status = 'finished'  
    else:
        status = 'unknown'    
    return JsonResponse({'messages': messages, 'status': status})

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def delete_tts_data_monitor(request, language, report_id):
    return render(request, 'clara_app/delete_tts_data_monitor.html',
                  {'language': language, 'report_id': report_id})

@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def delete_tts_data_complete(request, language, status):
    if request.method == 'POST':
        form = DeleteTTSDataForm(request.POST)
        if form.is_valid():
            language = form.cleaned_data['language']
            
            # Create a unique ID to tag messages posted by this task, and a callback
            report_id = uuid.uuid4()
            callback = [post_task_update_in_db, report_id]

            async_task(delete_tts_data_for_language, language, callback=callback)
            print(f'--- Started delete task for {language}')
            #Redirect to the monitor view, passing the task ID and report ID as parameters
            return redirect('delete_tts_data_monitor', language, report_id)
    else:
        if status == 'error':
            messages.error(request, f'Something went wrong when deleting TTS data for {language}')
        else:
            messages.success(request, f'Deleted TTS data for {language}')

        form = DeleteTTSDataForm()

        return render(request, 'clara_app/delete_tts_data.html',
                      { 'form': form, } )

# Manage users declared as 'language masters', adding or withdrawing the 'language master' privilege   
@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def manage_language_masters(request):
    language_masters = LanguageMaster.objects.all()
    if request.method == 'POST':
        form = AssignLanguageMasterForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            language = form.cleaned_data['language']
            LanguageMaster.objects.get_or_create(user=user, language=language)
            return redirect('manage_language_masters')
    else:
        form = AssignLanguageMasterForm()
    return render(request, 'clara_app/manage_language_masters.html', {
        'language_masters': language_masters,
        'form': form,
    })

# Remove someone as a language master, asking for confirmation first
@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def remove_language_master(request, pk):
    language_master = get_object_or_404(LanguageMaster, pk=pk)
    if request.method == 'POST':
        language_master.delete()
        return redirect('manage_language_masters')
    else:
        return render(request, 'clara_app/remove_language_master_confirm.html', {'language_master': language_master})
##
# Allow a language master to edit templates and examples
@login_required
@language_master_required
def edit_prompt(request):
    if request.method == 'POST':
        prompt_selection_form = PromptSelectionForm(request.POST, user=request.user)
        if prompt_selection_form.is_valid():
            language = prompt_selection_form.cleaned_data['language']
            default_language = prompt_selection_form.cleaned_data['default_language']
            template_or_examples = prompt_selection_form.cleaned_data['template_or_examples']
            # Assume the template is in English, i.e. an ltr language, but the examples are in "language"
            rtl_language = False if template_or_examples == 'template' else is_rtl_language(language) 
            operation = prompt_selection_form.cleaned_data['operation']
            annotation_type = prompt_selection_form.cleaned_data['annotation_type']
            if template_or_examples == 'template':
                PromptFormSet = forms.formset_factory(TemplateForm, formset=CustomTemplateFormSet, extra=0)
            elif template_or_examples == 'examples' and (operation == 'annotate' or annotation_type == 'segmented'):
                PromptFormSet = forms.formset_factory(StringForm, formset=CustomStringFormSet, extra=1)
            else:
                PromptFormSet = forms.formset_factory(StringPairForm, formset=CustomStringPairFormSet, extra=1)
                
            prompt_repo = PromptTemplateRepository(language)

            if request.POST.get('action') == 'Load':
                # Start by trying to get the data from our current language
                try:
                    prompts = prompt_repo.load_template_or_examples(template_or_examples, annotation_type, operation)
                except TemplateError as e1:
                    # If the default language is different, try that next
                    if language != default_language:
                        try:
                            prompt_repo_default_language = PromptTemplateRepository(default_language)
                            prompts = prompt_repo_default_language.load_template_or_examples(template_or_examples, annotation_type, operation)
                        except TemplateError as e2:
                            # If we haven't already done that, try 'default'
                            if language != 'default' and default_language != 'default':
                                try:
                                    prompt_repo_default = PromptTemplateRepository('default')
                                    prompts = prompt_repo_default.load_template_or_examples(template_or_examples, annotation_type, operation)
                                except TemplateError as e3:
                                    messages.error(request, f"{e3.message}")
                                    prompt_formset = None  # No formset because we couldn't get the data
                                    return render(request, 'clara_app/edit_prompt.html', {'prompt_selection_form': prompt_selection_form, 'prompt_formset': prompt_formset})
                            else:
                                messages.error(request, f"{e2.message}")
                                prompt_formset = None  # No formset because we couldn't get the data
                                return render(request, 'clara_app/edit_prompt.html', {'prompt_selection_form': prompt_selection_form, 'prompt_formset': prompt_formset})
                    else:
                        messages.error(request, f"{e1.message}")
                        prompt_formset = None  # No formset because we couldn't get the data
                        return render(request, 'clara_app/edit_prompt.html', {'prompt_selection_form': prompt_selection_form, 'prompt_formset': prompt_formset})

                # Prepare data
                if template_or_examples == 'template':
                    initial_data = [{'template': prompts}]
                elif template_or_examples == 'examples' and (operation == 'annotate' or annotation_type == 'segmented'):
                    initial_data = [{'string': example} for example in prompts]
                else:
                    initial_data = [{'string1': pair[0], 'string2': pair[1]} for pair in prompts]

                prompt_formset = PromptFormSet(initial=initial_data, prefix='prompts', rtl_language=rtl_language)

            elif request.POST.get('action') == 'Save':
                prompt_formset = PromptFormSet(request.POST, prefix='prompts', rtl_language=rtl_language)
                if prompt_formset.is_valid():
                    # Prepare data for saving
                    if template_or_examples == 'template':
                        new_prompts = prompt_formset[0].cleaned_data.get('template')
                    elif template_or_examples == 'examples' and (operation == 'annotate' or annotation_type == 'segmented'):
                        new_prompts = [form.cleaned_data.get('string') for form in prompt_formset]
                        if not new_prompts[-1]:
                            # We didn't use the extra last field
                            new_prompts = new_prompts[:-1]
                    else:
                        new_prompts = [[form.cleaned_data.get('string1'), form.cleaned_data.get('string2')] for form in prompt_formset]
                        if not new_prompts[-1][0] or not new_prompts[-1][1]:
                            # We didn't use the extra last field
                            new_prompts = new_prompts[:-1]
                    try:
                        prompt_repo.save_template_or_examples(template_or_examples, annotation_type, operation, new_prompts, request.user.username)
                        messages.success(request, "Data saved successfully")
                    except TemplateError as e:
                        messages.error(request, f"{e.message}")
                    
            else:
                raise Exception("Internal error: neither Load nor Save found in POST request to edit_prompt")

            return render(request, 'clara_app/edit_prompt.html', {'prompt_selection_form': prompt_selection_form, 'prompt_formset': prompt_formset})

    else:
        prompt_selection_form = PromptSelectionForm(user=request.user)
        prompt_formset = None  # No formset when the page is first loaded

    return render(request, 'clara_app/edit_prompt.html', {'prompt_selection_form': prompt_selection_form, 'prompt_formset': prompt_formset})

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
    return render(request, 'clara_app/register_content.html', {'form': form})

# Confirm that content has been registered
def content_success(request):
    return render(request, 'clara_app/content_success.html')
   
# List currently registered content
@login_required
def content_list(request):
    content_list = Content.objects.all().order_by(Lower('title'))
    paginator = Paginator(content_list, 10)  # Show 10 content items per page

    page = request.GET.get('page')
    contents = paginator.get_page(page)
    
    return render(request, 'clara_app/content_list.html', {'contents': contents})

# Show a piece of registered content. Users can add ratings and comments.    
@login_required
def content_detail(request, content_id):
    content = get_object_or_404(Content, id=content_id)
    comments = Comment.objects.filter(content=content).order_by('timestamp')
    rating = Rating.objects.filter(content=content, user=request.user).first()
    average_rating = Rating.objects.filter(content=content).aggregate(Avg('rating'))

    if request.method == 'POST':
        if 'submit_rating' in request.POST:
            rating_form = RatingForm(request.POST)
            if rating_form.is_valid():
                new_rating = rating_form.save(commit=False)
                new_rating.user = request.user
                new_rating.content = content
                if rating:
                    rating.rating = new_rating.rating
                    rating.save()
                else:
                    new_rating.save()
            comment_form = CommentForm()  # initialize empty comment form
        elif 'submit_comment' in request.POST:
            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                new_comment = comment_form.save(commit=False)
                new_comment.user = request.user
                new_comment.content = content
                new_comment.save()
            rating_form = RatingForm()  # initialize empty rating form
        return redirect('content_detail', content_id=content_id)
    else:
        rating_form = RatingForm()
        comment_form = CommentForm()

    return render(request, 'clara_app/content_detail.html', {
        'content': content,
        'rating_form': rating_form,
        'comment_form': comment_form,
        'comments': comments,
        'average_rating': average_rating['rating__avg'],
    })

# Create a new project
@login_required
def create_project(request):
    if request.method == 'POST':
        form = ProjectCreationForm(request.POST)
        if form.is_valid():
            # Extract the validated data from the form
            title = form.cleaned_data['title']
            l2_language = form.cleaned_data['l2']
            l1_language = form.cleaned_data['l1']
            # Create a new project in Django's database, associated with the current user
            clara_project = CLARAProject(title=title, user=request.user, l2=l2_language, l1=l1_language)
            clara_project.save()
            internal_id = create_internal_project_id(title, clara_project.id)
            # Update the Django project with the internal_id
            clara_project.internal_id = internal_id
            clara_project.save()
            # Create a new internal project in the C-LARA framework
            clara_project_internal = CLARAProjectInternal(internal_id, l2_language, l1_language)
            return redirect('project_detail', project_id=clara_project.id)
        else:
            # The form data was invalid. Re-render the form with error messages.
            return render(request, 'clara_app/create_project.html', {'form': form})
    else:
        # This is a GET request, so create a new blank form
        form = ProjectCreationForm()
        return render(request, 'clara_app/create_project.html', {'form': form})

# Create a clone of a project        
@login_required
@user_has_a_project_role
def clone_project(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    if request.method == 'POST':
        form = ProjectCreationForm(request.POST)
        if form.is_valid():
            # Extract the title and the new L2 and L1 language selections
            new_title = form.cleaned_data['title']
            new_l2 = form.cleaned_data['l2']
            new_l1 = form.cleaned_data['l1']

            # Created the cloned project with the new language selections
            new_project = CLARAProject(title=new_title, user=request.user, l2=new_l2, l1=new_l1)
            new_project.save()
            new_internal_id = create_internal_project_id(new_title, new_project.id)
            # Update the Django project with the internal_id
            new_project.internal_id = new_internal_id
            new_project.save()
            # Create a new internal project 
            new_project_internal = CLARAProjectInternal(new_internal_id, new_l2, new_l1)
            # Copy any relevant files from the old project
            project_internal.copy_files_to_newly_cloned_project(new_project_internal)

            # Redirect the user to the cloned project detail page or show a success message
            return redirect('project_detail', project_id=new_project.id)
    else:
        # Prepopulate the form with the copied title and the current language selections as defaults
        new_title = project.title + " - copy"
        form = ProjectCreationForm(initial={'title': new_title, 'l2': project.l2, 'l1': project.l1})

    return render(request, 'clara_app/create_cloned_project.html', {'form': form, 'project': project})

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

    context = {
        'project': project,
        'permissions': permissions,
        'form': form,
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
def project_list(request):
    user = request.user
    projects = CLARAProject.objects.filter(Q(user=user) | Q(projectpermissions__user=user)).order_by(Lower('title'))
    
    project_data = {}
    for project in projects:
        role = 'OWNER' if project.user == user else ProjectPermissions.objects.get(user=user, project=project).role
        project_data[project] = {
            'role': role,
            'cost': get_project_api_cost(user=user, project=project),
            'operation_costs': get_project_operation_costs(user=user, project=project),
            'duration': get_project_api_duration(user=user, project=project),  
            'operation_durations': get_project_operation_durations(user=user, project=project),  
        }

    paginator = Paginator(list(project_data.items()), 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'clara_app/project_list.html', {'page_obj': page_obj})

# Delete a project
@login_required
@user_is_project_owner
def delete_project(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    if request.method == 'POST':
        project.delete()
        clara_project_internal.delete()
        return redirect('project_list')
    else:
        return render(request, 'clara_app/confirm_delete.html', {'project': project})

# Display information and functionalities associated with a project     
@login_required
@user_has_a_project_role
def project_detail(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    can_create_segmented_text = clara_project_internal.text_versions["plain"]
    can_create_glossed_and_lemma_text = clara_project_internal.text_versions["segmented"]
    can_render = clara_project_internal.text_versions["gloss"] and clara_project_internal.text_versions["lemma"]
    rendered_html_exists = clara_project_internal.rendered_html_exists(project_id)
    api_cost = get_project_api_cost(request.user, project)
    if request.method == 'POST':
        form = UpdateProjectTitleForm(request.POST)
        if form.is_valid():
            project.title = form.cleaned_data['new_title']
            project.save()
    else:
        form = UpdateProjectTitleForm()
    return render(request, 'clara_app/project_detail.html', 
                  { 'project': project, 'form': form, 'api_cost': api_cost, 
                    'can_create_segmented_text': can_create_segmented_text, 
                    'can_create_glossed_and_lemma_text': can_create_glossed_and_lemma_text,
                    'can_render': can_render,
                    'rendered_html_exists': rendered_html_exists }
                    )

@login_required
@user_has_a_project_role
def get_audio_metadata_view(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    
    audio_metadata = clara_project_internal.get_audio_metadata()

    # Convert the metadata to JSON (or similar formatted string)
    audio_metadata_str = json.dumps(audio_metadata, indent=4)
    
    if request.method == 'POST':
        # Handle POST logic if any (like saving the metadata somewhere)
        pass
    else:
        form = AudioMetadataForm(initial={'metadata': audio_metadata_str})
    
    return render(request, 'clara_app/audio_metadata.html', 
                  { 'project': project, 'form': form })


# Get metadata for a version of a text (internal use only)
@login_required
@user_has_a_project_role                    
def get_metadata_for_version(request, project_id, version):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    metadata = clara_project_internal.get_metadata()

    # Filter metadata by version
    metadata_for_version = [data for data in metadata if data['version'] == version]
    
    return JsonResponse(metadata_for_version, safe=False)
 
# Compare two versions of a project file 
@login_required
@user_has_a_project_role
def compare_versions(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    if request.method == 'POST':
        form = DiffSelectionForm(request.POST)
        # Can't get form validation to work, perhaps something to do with dynamically populating the form?
        #if form.is_valid():
        # version = form.cleaned_data['version']
        # file1 = form.cleaned_data['file1']
        # file2 = form.cleaned_data['file2']
        # required = form.cleaned_data['required']
        version = request.POST['version']
        file1 = request.POST['file1']
        file2 = request.POST['file2']
        required = request.POST.getlist('required')  # getlist is used for fields with multiple values
        
        form1 = DiffSelectionForm(initial={'version': version, 'file1': file1, 'file2': file2})
        metadata = clara_project_internal.get_metadata()
        metadata_for_version = [(data['file'], data['description']) for data in metadata if data['version'] == version]
        form1.fields['file1'].choices = metadata_for_version
        form1.fields['file2'].choices = metadata_for_version

        # This is where the diff is computed
        try:
            diff_result = clara_project_internal.diff_editions_of_text_version(file1, file2, version, required)
        except InternalisationError as e:
            messages.error(request, f'{e.message}')
            return render(request, 'clara_app/diff_and_diff_result.html', {'form': form1, 'project': project})
        
        # Convert markup to HTML
        if 'details' in diff_result:
            diff_result['details'] = diff_result['details'].replace('[inserted]', '<span class="inserted">').replace('[/inserted]', '</span>')
            diff_result['details'] = diff_result['details'].replace('[deleted]', '<span class="deleted">').replace('[/deleted]', '</span>')
            diff_result['details'] = diff_result['details'].replace('[page]', '&lt;page&gt;')

        #return render(request, 'clara_app/diff_result.html', {'diff_result': diff_result, 'project': project})
        return render(request, 'clara_app/diff_and_diff_result.html', {'diff_result': diff_result, 'form': form1, 'project': project})

    else:
        # Initially populate with data for comparing 'plain' files
        metadata = clara_project_internal.get_metadata()
        metadata_for_plain = [(data['file'], data['description']) for data in metadata if data['version'] == 'plain']
        form = DiffSelectionForm(initial={'version': 'plain'})
        form.fields['file1'].choices = metadata_for_plain
        form.fields['file2'].choices = metadata_for_plain

    #return render(request, 'clara_app/diff.html', {'form': form, 'project': project})
    return render(request, 'clara_app/diff_and_diff_result.html', {'form': form, 'project': project})

# Generic code for the operations which support creating, annotating, improving and editing text,
# to produce and edit the "plain", "summary", "cefr", "segmented", "gloss" and "lemma" versions.
# It is also possible to retrieve archived versions of the files if they exist.
#
# The argument 'this_version' is the version we are currently creating/editing.
# The argument 'previous_version' is the version it is created from. E.g. "gloss" is created from "segmented".
#
# Most of the operations are common to all five types of text, but there are some small divergences
# which have to be treated specially:
#
# - When creating the initial "plain" version, we pass an optional prompt.
# - In the "lemma" version, we may have the additional option of using TreeTagger.
def create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    tree_tagger_supported = fully_supported_treetagger_language(project.l2)
    jieba_supported = is_chinese_language(project.l2)
    # The summary and cefr are in English, so always left-to-right even if the main text is right-to-left
    rtl_language=is_rtl_language(project.l2) if not this_version in ( 'summary', 'cefr_level' ) else False
    metadata = clara_project_internal.get_metadata()
    current_version = clara_project_internal.get_file_description(this_version, 'current')
    archived_versions = [(data['file'], data['description']) for data in metadata if data['version'] == this_version]
    text_choice = 'generate' if archived_versions == [] else 'manual'
    prompt = None
    action = None

    if request.method == 'POST':
        form = CreateAnnotationTextFormOfRightType(this_version, request.POST, prompt=prompt,
                                                   archived_versions=archived_versions,
                                                   tree_tagger_supported=tree_tagger_supported, jieba_supported=jieba_supported, is_rtl_language=rtl_language)
        if form.is_valid():
            text_choice = form.cleaned_data['text_choice']
            label = form.cleaned_data['label']
            gold_standard = form.cleaned_data['gold_standard']
            username = request.user.username
            # We have an optional prompt when creating the initial text.
            prompt = form.cleaned_data['prompt'] if this_version == 'plain' else None
            if not text_choice in ( 'manual', 'load_archived', 'correct', 'generate', 'improve', 'tree_tagger', 'jieba' ):
                raise InternalCLARAError(message = f'Unknown text_choice type in create_annotated_text_of_right_type: {text_choice}')
            # We're saving an edited version of a file
            elif text_choice == 'manual':
                if not user_has_a_named_project_role(request.user, project_id, ['OWNER', 'ANNOTATOR']):
                    raise PermissionDenied("You don't have permission to save edited text.")
                annotated_text = form.cleaned_data['text']
                # Check that text is well-formed before trying to save it. If it's not well-formed, we get an InternalisationError
                try:
                    internalize_text(annotated_text, clara_project_internal.l2_language, clara_project_internal.l1_language, this_version)
                    clara_project_internal.save_text_version(this_version, annotated_text, 
                                                             user=username, label=label, gold_standard=gold_standard)
                    messages.success(request, "File saved")
                except InternalisationError as e:
                    messages.error(request, e.message)
                
                action = 'edit'                                         
                text_choice = 'manual'
                current_version = clara_project_internal.get_file_description(this_version, 'current')
            # We're loading an archived version of a file
            elif text_choice == 'load_archived':
                try:
                    archived_file = form.cleaned_data['archived_version']
                    annotated_text = read_txt_file(archived_file)
                    text_choice = 'manual'
                    current_version = clara_project_internal.get_file_description(this_version, archived_file)
                    messages.success(request, f"Loaded archived file {archived_file}")
                except FileNotFoundError:
                    messages.error(request, f"Unable to find archived file {archived_file}")
                    try:
                        annotated_text = clara_project_internal.load_text_version(previous_version)
                        text_choice = 'manual'
                    except FileNotFoundError:
                        annotated_text = ""
                        text_choice = 'generate'
                    current_version = ""
            # We're using the AI or a tagger to create a new version of a file
            elif text_choice in ( 'generate', 'correct', 'improve' ) and not request.user.userprofile.credit > 0:
                messages.error(request, f"Sorry, you need money in your account to perform this operation")
                annotated_text = ''
                text_choice = 'manual'
            elif text_choice in ( 'generate', 'correct', 'improve', 'tree_tagger', 'jieba' ):
                if not user_has_a_named_project_role(request.user, project_id, ['OWNER']):
                    raise PermissionDenied("You don't have permission to create text by calling the AI.")
                try:
                    # Create a unique ID to tag messages posted by this task, and a callback
                    report_id = uuid.uuid4()
                    callback = [post_task_update_in_db, report_id]

                    # We are correcting the text using the AI and then saving it
                    if text_choice == 'correct':
                        annotated_text = form.cleaned_data['text']
                        async_task(perform_correct_operation_and_store_api_calls, annotated_text, this_version, project, clara_project_internal,
                                   request.user, label, callback=callback)
                        print(f'--- Started correction task')
                        #Redirect to the monitor view, passing the task ID and report ID as parameters
                        return redirect('generate_text_monitor', project_id, this_version, report_id)
                    # We are creating the text using the AI
                    elif text_choice == 'generate':
                        # We want to get a possible template error here rather than in the asynch process
                        clara_project_internal.try_to_use_templates('annotate', this_version)
                        async_task(perform_generate_operation_and_store_api_calls, this_version, project, clara_project_internal,
                                   request.user, label, prompt=prompt, callback=callback)
                        print(f'--- Started generation task')
                        #Redirect to the monitor view, passing the task ID and report ID as parameters
                        return redirect('generate_text_monitor', project_id, this_version, report_id)
                    # We are improving the text using the AI
                    elif text_choice == 'improve':
                        # We want to get a possible template error here rather than in the asynch process
                        clara_project_internal.try_to_use_templates('improve', this_version)
                        async_task(perform_improve_operation_and_store_api_calls, this_version, project, clara_project_internal,
                                   request.user, label, callback=callback)
                        print(f'--- Started improvement task')
                        #Redirect to the monitor view, passing the task ID and report ID as parameters
                        return redirect('generate_text_monitor', project_id, this_version, report_id)
                    # We are creating the text using TreeTagger. This operation is only possible with lemma tagging
                    elif text_choice == 'tree_tagger':
                        action, api_calls = ( 'generate', clara_project_internal.create_lemma_tagged_text_with_treetagger(user=username, label=label) )
                        # These operations are handled elsewhere for generation and improvement, due to asynchrony
                        store_api_calls(api_calls, project, request.user, this_version)
                        annotated_text = clara_project_internal.load_text_version(this_version)
                        text_choice = 'manual'
                        success_message = f'Created {this_version} text using TreeTagger'
                        print(f'--- {success_message}')
                        messages.success(request, success_message)
                        current_version = clara_project_internal.get_file_description(this_version, 'current')
                    # We are creating the text using Jieba. This operation is only possible with segmentation
                    elif text_choice == 'jieba':
                        action, api_calls = ( 'generate', clara_project_internal.create_segmented_text_using_jieba(user=username, label=label) )
                        # These operations are handled elsewhere for generation and improvement, due to asynchrony
                        store_api_calls(api_calls, project, request.user, this_version)
                        annotated_text = clara_project_internal.load_text_version(this_version)
                        text_choice = 'manual'
                        success_message = f'Created {this_version} text using Jieba'
                        print(f'--- {success_message}')
                        messages.success(request, success_message)
                        current_version = clara_project_internal.get_file_description(this_version, 'current')
                except InternalisationError as e:
                    messages.error(request, f"Something appears to be wrong with a prompt example. Error details: {e.message}")
                    annotated_text = ''
                except Exception as e:
                    raise e
                    messages.error(request, f"An error occurred while producing the text. Error details: {str(e)}")
                    annotated_text = ''
            # If something happened, log it
            if action:
                CLARAProjectAction.objects.create(
                    project=project,
                    action=action,
                    text_version=this_version,
                    user=request.user
                )
    # We're displaying the current version of the file, or as close as we can get
    else:
        try:
            annotated_text = clara_project_internal.load_text_version(this_version)
            text_choice = 'manual'
        except FileNotFoundError:
            try:
                annotated_text = clara_project_internal.load_text_version(previous_version)
            except FileNotFoundError:
                annotated_text = ""
            text_choice = 'generate'
        current_version = clara_project_internal.get_file_description(this_version, 'current')

    # The archived versions will have changed if we created a new file
    metadata = clara_project_internal.get_metadata()
    archived_versions = [(data['file'], data['description']) for data in metadata if data['version'] == this_version]
    form = CreateAnnotationTextFormOfRightType(this_version, initial={'text': annotated_text, 'text_choice': text_choice},
                                               prompt=prompt, archived_versions=archived_versions, current_version=current_version,
                                               tree_tagger_supported=tree_tagger_supported, jieba_supported=jieba_supported, is_rtl_language=rtl_language)

    return render(request, template, {'form': form, 'project': project})

# This is the API endpoint that the JavaScript will poll
@login_required
@user_has_a_project_role
def generate_text_status(request, project_id, report_id):
    messages = get_task_updates(report_id)
    print(f'{len(messages)} messages received')
    if 'error' in messages:
        status = 'error'
    elif 'finished' in messages:
        status = 'finished' 
    else: 
        status = 'unknown'    
    return JsonResponse({'messages': messages, 'status': status})

@login_required
@user_has_a_project_role
def generate_text_monitor(request, project_id, version, report_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    return render(request, 'clara_app/generate_text_monitor.html',
                  {'version': version, 'report_id': report_id, 'project_id': project_id, 'project': project})

# Display the final result of rendering
@login_required
@user_has_a_project_role
def generate_text_complete(request, project_id, version, status):

    previous_version, template = previous_version_and_template_for_version(version)

    # We are making a new request in this view
    if request.method == 'POST':
        return create_annotated_text_of_right_type(request, project_id, version, previous_version, template)
    # We got here from the monitor view
    else:
        if status == 'error':
            messages.error(request, f'Something went wrong when creating {version} text')
        else:
            messages.success(request, f'Created {version} text')
        
        project = get_object_or_404(CLARAProject, pk=project_id)
        clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
        tree_tagger_supported = fully_supported_treetagger_language(project.l2)
        jieba_supported = is_chinese_language(project.l2)
        metadata = clara_project_internal.get_metadata()
        current_version = clara_project_internal.get_file_description(version, 'current')
        archived_versions = [(data['file'], data['description']) for data in metadata if data['version'] == version]
        text_choice = 'generate' if archived_versions == [] else 'manual'
        prompt = None

        try:
            annotated_text = clara_project_internal.load_text_version(version)
            text_choice = 'manual'
        except FileNotFoundError:
            try:
                annotated_text = clara_project_internal.load_text_version(previous_version)
            except FileNotFoundError:
                annotated_text = ""
            text_choice = 'generate'
        current_version = clara_project_internal.get_file_description(version, 'current')

    # The archived versions will have changed if we created a new file
    metadata = clara_project_internal.get_metadata()
    archived_versions = [(data['file'], data['description']) for data in metadata if data['version'] == version]
    rtl_language=is_rtl_language(project.l2)
    form = CreateAnnotationTextFormOfRightType(version, initial={'text': annotated_text, 'text_choice': text_choice},
                                               prompt=prompt, archived_versions=archived_versions, current_version=current_version,
                                               tree_tagger_supported=tree_tagger_supported, jieba_supported=jieba_supported, is_rtl_language=rtl_language)

    return render(request, template, {'form': form, 'project': project})

def CreateAnnotationTextFormOfRightType(version, *args, **kwargs):
    if version == 'plain':
        return CreatePlainTextForm(*args, **kwargs)
    elif version == 'summary':
        return CreateSummaryTextForm(*args, **kwargs)
    elif version == 'cefr_level':
        return CreateCEFRTextForm(*args, **kwargs)
    elif version == 'segmented':
        return CreateSegmentedTextForm(*args, **kwargs)
    elif version == 'gloss':
        return CreateGlossedTextForm(*args, **kwargs)
    elif version == 'lemma':
        return CreateLemmaTaggedTextForm(*args, **kwargs)
    elif version == 'lemma_and_gloss':
        return CreateLemmaAndGlossTaggedTextForm(*args, **kwargs)
    else:
        raise InternalCLARAError(message = f'Unknown first argument in CreateAnnotationTextFormOfRightType: {version}')

def perform_correct_operation_and_store_api_calls(annotated_text, version, project, clara_project_internal,
                                                  user_object, label, callback=None):
    try:                                               
        operation, api_calls = perform_correct_operation(annotated_text, version, clara_project_internal, user_object.username, label, callback=callback)
        store_api_calls(api_calls, project, user_object, version)
        post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}")
        #raise e
        post_task_update(callback, f"error")

def perform_correct_operation(annotated_text, version, clara_project_internal, user, label, callback=None):
    #print(f'clara_project_internal.correct_syntax_and_save({annotated_text}, {version}, user={user}, label={label}, callback={callback})')
    return ( 'correct', clara_project_internal.correct_syntax_and_save(annotated_text, version, user=user, label=label, callback=callback) )

def perform_generate_operation_and_store_api_calls(version, project, clara_project_internal,
                                                   user_object, label, prompt=None, callback=None):
    try:                                               
        operation, api_calls = perform_generate_operation(version, clara_project_internal, user_object.username, label, prompt=prompt, callback=callback)
        store_api_calls(api_calls, project, user_object, version)
        post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}")
        post_task_update(callback, f"error")
    
def perform_generate_operation(version, clara_project_internal, user, label, prompt=None, callback=None):
    if version == 'plain':
        return ( 'generate', clara_project_internal.create_plain_text(prompt=prompt, user=user, label=label, callback=callback) )
    elif version == 'summary':
        return ( 'generate', clara_project_internal.create_summary(user=user, label=label, callback=callback) )
    elif version == 'cefr_level':
        return ( 'generate', clara_project_internal.get_cefr_level(user=user, label=label, callback=callback) )
    elif version == 'segmented':
        return ( 'generate', clara_project_internal.create_segmented_text(user=user, label=label, callback=callback) )
    elif version == 'gloss':
        return ( 'generate', clara_project_internal.create_glossed_text(user=user, label=label, callback=callback) )
    elif version == 'lemma':
        return ( 'generate', clara_project_internal.create_lemma_tagged_text(user=user, label=label, callback=callback) )
    # There is no generate operation for lemma_and_gloss, since we make it by merging lemma and gloss
    else:
        raise InternalCLARAError(message = f'Unknown first argument in perform_generate_operation: {version}')

def perform_improve_operation_and_store_api_calls(version, project, clara_project_internal,
                                                   user_object, label, callback=None):
    try:                                               
        operation, api_calls = perform_improve_operation(version, clara_project_internal, user_object.username, label, callback=callback)
        store_api_calls(api_calls, project, user_object, version)
        post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}")
        post_task_update(callback, f"error")
 
def perform_improve_operation(version, clara_project_internal, user, label, callback=None):
    if version == 'plain':
        return ( 'generate', clara_project_internal.improve_plain_text(user=user, label=label, callback=callback) )
    if version == 'summary':
        return ( 'generate', clara_project_internal.improve_summary(user=user, label=label, callback=callback) )
    elif version == 'segmented':
        return ( 'generate', clara_project_internal.improve_segmented_text(user=user, label=label, callback=callback) )
    elif version == 'gloss':
        return ( 'generate', clara_project_internal.improve_glossed_text(user=user, label=label, callback=callback) )
    elif version == 'lemma':
        return ( 'generate', clara_project_internal.improve_lemma_tagged_text(user=user, label=label, callback=callback) )
    elif version == 'lemma_and_gloss':
        return ( 'generate', clara_project_internal.improve_lemma_and_gloss_tagged_text(user=user, label=label, callback=callback) )
    else:
        raise InternalCLARAError(message = f'Unknown first argument in perform_improve_operation: {version}')

def previous_version_and_template_for_version(this_version):
    if this_version == 'plain':
        return ( 'plain', 'clara_app/create_plain_text.html' )
    elif this_version == 'summary':
        return ( 'plain', 'clara_app/create_summary.html' )
    elif this_version == 'cefr_level':
        return ( 'plain', 'clara_app/get_cefr_level.html' )
    elif this_version == 'segmented':
        return ( 'plain', 'clara_app/create_segmented_text.html' )
    elif this_version == 'gloss':
        return ( 'segmented', 'clara_app/create_glossed_text.html' )
    elif this_version == 'lemma':
        return ( 'segmented', 'clara_app/create_lemma_tagged_text.html' )
    elif this_version == 'lemma_and_gloss':
        return ( 'lemma_and_gloss', 'clara_app/create_lemma_and_gloss_tagged_text.html' )
    else:
        raise InternalCLARAError(message = f'Unknown first argument in previous_version_and_template_for_version: {this_version}')

# Create or edit "plain" version of the text        
@login_required
@user_has_a_project_role
def create_plain_text(request, project_id):
    this_version = 'plain'
    #previous_version = 'plain'
    #template = 'clara_app/create_plain_text.html'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

    
#Create or edit "summary" version of the text     
@login_required
@user_has_a_project_role
def create_summary(request, project_id):
    this_version = 'summary'
    #previous_version = 'plain'
    #template = 'clara_app/create_summary.html'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

#Create or edit "cefr_level" version of the text     
@login_required
@user_has_a_project_role
def create_cefr_level(request, project_id):
    this_version = 'cefr_level'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Create or edit "segmented" version of the text     
@login_required
@user_has_a_project_role
def create_segmented_text(request, project_id):
    this_version = 'segmented'
    #previous_version = 'plain'
    #template = 'clara_app/create_segmented_text.html'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Create or edit "glossed" version of the text     
@login_required
@user_has_a_project_role
def create_glossed_text(request, project_id):
    this_version = 'gloss'
    #previous_version = 'segmented'
    #template = 'clara_app/create_glossed_text.html'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Create or edit "lemma-tagged" version of the text 
@login_required
@user_has_a_project_role
def create_lemma_tagged_text(request, project_id):
    this_version = 'lemma'
    #previous_version = 'segmented'
    #template = 'clara_app/create_lemma_tagged_text.html'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Create or edit "lemma-and-glossed" version of the text 
@login_required
@user_has_a_project_role
def create_lemma_and_gloss_tagged_text(request, project_id):
    this_version = 'lemma_and_gloss'
    #previous_version = 'lemma_and_gloss'
    #template = 'clara_app/create_lemma_and_gloss_tagged_text.html'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Display the history of updates to project files 
@login_required
@user_has_a_project_role
def project_history(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    actions = CLARAProjectAction.objects.filter(project=project).order_by('-timestamp')
    return render(request, 'clara_app/project_history.html', {'project': project, 'actions': actions})

# Render the internal representation to create a directory of static HTML files
##@login_required
##@user_has_a_project_role
##def render_text(request, project_id):
##    project = get_object_or_404(CLARAProject, pk=project_id)
##    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
##
##    # Check that the required text versions exist
##    if "gloss" not in clara_project_internal.text_versions or "lemma" not in clara_project_internal.text_versions:
##        messages.error(request, "Glossed and lemma-tagged versions of the text must exist to render it.")
##        return redirect('project_detail', project_id=project.id)
##
##    if request.method == 'POST':
##        form = RenderTextForm(request.POST)
##        if form.is_valid():
##            # Call the render_text method to generate the HTML files
##            clara_project_internal.render_text(project_id, self_contained=True)
##            
##            # Define URLs for the first page of content and the zip file
##            content_url = (settings.STATIC_URL + f"rendered_texts/{project.id}/page_1.html").replace('\\', '/')
##            # Put back zipfile later
##            #zipfile_url = (settings.STATIC_URL + f"rendered_texts/{project.id}.zip").replace('\\', '/')
##            zipfile_url = None
##
##            # Create the form for registering the project content
##            register_form = RegisterAsContentForm()
##            
##            return render(request, 'clara_app/render_text.html', {'content_url': content_url, 'zipfile_url': zipfile_url, 'project': project, 'register_form': register_form})
## 
##    else:
##        form = RenderTextForm()
##
##        return render(request, 'clara_app/render_text.html', {'form': form, 'project': project})

def clara_project_internal_render_text(clara_project_internal, project_id, self_contained=False, callback=None):
    try:
        clara_project_internal.render_text(project_id, self_contained=self_contained, callback=callback)
        post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}")
        post_task_update(callback, f"error")

# Start the async process that will do the rendering
@login_required
@user_has_a_project_role
def render_text_start(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    if "gloss" not in clara_project_internal.text_versions or "lemma" not in clara_project_internal.text_versions:
        messages.error(request, "Glossed and lemma-tagged versions of the text must exist to render it.")
        return redirect('project_detail', project_id=project.id)

    if request.method == 'POST':
        form = RenderTextForm(request.POST)
        if form.is_valid():
            # Remove any outstanding tasks, this should be the only one running
            #delete_all_tasks() 
            
            # Create a unique ID to tag messages posted by this task
            report_id = uuid.uuid4()

            # Define a callback as list of the callback function and the first argument
            # We can't use a lambda function or a closure because async_task can't apply pickle to them
            callback = [post_task_update_in_db, report_id]
        
            # Enqueue the render_text task
            self_contained = True
            # First check that we can internalise and merge the gloss and lemma files, and give an error if we can't
            try:
                internalised_text = clara_project_internal.get_internalised_text()
                task_id = async_task(clara_project_internal_render_text, clara_project_internal, project_id, self_contained=self_contained, callback=callback)
                print(f'--- Started task: task_id = {task_id}, self_contained={self_contained}')

                # Redirect to the monitor view, passing the task ID and report ID as parameters
                return redirect('render_text_monitor', project_id, task_id, report_id)
            except InternalisationError as e:
                messages.error(request, f'{e.message}')
                form = RenderTextForm()
                return render(request, 'clara_app/render_text_start.html', {'form': form, 'project': project})
            except Exception as e:
                messages.error(request, f"An internal error occurred in rendering. Error details: {str(e)}")
                form = RenderTextForm()
                return render(request, 'clara_app/render_text_start.html', {'form': form, 'project': project})
    else:
        form = RenderTextForm()
        return render(request, 'clara_app/render_text_start.html', {'form': form, 'project': project})

# This is the API endpoint that the JavaScript will poll
@login_required
@user_has_a_project_role
def render_text_status(request, project_id, task_id, report_id):
    messages = get_task_updates(report_id)
    print(f'{len(messages)} messages received')
    #if len(messages) != 0:
    #    pprint.pprint(messages)
    if 'error' in messages:
        status = 'error'
    elif 'finished' in messages:
        status = 'finished'  
    else:
        status = 'unknown'    
    return JsonResponse({'messages': messages, 'status': status})

# Render the monitoring page, which will use JavaScript to poll the task status API
@login_required
@user_has_a_project_role
def render_text_monitor(request, project_id, task_id, report_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    return render(request, 'clara_app/render_text_monitor.html',
                  {'task_id': task_id, 'report_id': report_id, 'project_id': project_id, 'project': project})

# Display the final result of rendering
@login_required
@user_has_a_project_role
def render_text_complete(request, project_id, status):
    project = get_object_or_404(CLARAProject, pk=project_id)
    if status == 'error':
        succeeded = False
    else:
        succeeded = True
    
    if succeeded:
        # Define URLs for the first page of content and the zip file
        content_url = (settings.STATIC_URL + f"rendered_texts/{project.id}/page_1.html").replace('\\', '/')
        # Put back zipfile later
        #zipfile_url = (settings.STATIC_URL + f"rendered_texts/{project.id}.zip").replace('\\', '/')
        zipfile_url = None
        # Create the form for registering the project content
        register_form = RegisterAsContentForm()
        messages.success(request, f'Rendered text found')
    else:
        content_url = None
        zipfile_url = None
        register_form = None
        messages.error(request, "Rendered text not found")
        
    return render(request, 'clara_app/render_text_complete.html',
                  {'content_url': content_url, 'zipfile_url': zipfile_url,
                   'project': project, 'register_form': register_form})

@login_required
@user_has_a_project_role
def offer_to_register_content(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    
    succeeded = clara_project_internal.rendered_html_exists(project_id)

    if succeeded:
        # Define URLs for the first page of content and the zip file
        content_url = (settings.STATIC_URL + f"rendered_texts/{project.id}/page_1.html").replace('\\', '/')
        # Put back zipfile later
        #zipfile_url = (settings.STATIC_URL + f"rendered_texts/{project.id}.zip").replace('\\', '/')
        zipfile_url = None
        # Create the form for registering the project content
        register_form = RegisterAsContentForm()
        messages.success(request, f'Rendered text found')
    else:
        content_url = None
        zipfile_url = None
        register_form = None
        messages.error(request, "Rendered text not found")
        
    return render(request, 'clara_app/render_text_complete.html',
                  {'content_url': content_url, 'zipfile_url': zipfile_url,
                   'project': project, 'register_form': register_form})

# Register content produced by rendering from a project        
@login_required
@user_has_a_project_role
def register_project_content(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    
    word_count0 = clara_project_internal.get_word_count()
    voice0 = clara_project_internal.get_voice()
    # CEFR level and summary are not essential, just continue if they're not available
    try:
        cefr_level0 = clara_project_internal.load_text_version("cefr_level")
    except Exception as e:
        cefr_level0 = None
    try:
        summary0 = clara_project_internal.load_text_version("summary")
    except Exception as e:
        summary0 = None
    word_count = 0 if not word_count0 else word_count0 # Dummy value if real one unavailable
    voice = "Unknown" if not voice0 else voice0 # Dummy value if real one unavailable
    cefr_level = "Unknown" if not cefr_level0 else cefr_level0 # Dummy value if real one unavailable
    summary = "Unknown" if not summary0 else summary0 # Dummy value if real one unavailable

    if request.method == 'POST':
        form = RegisterAsContentForm(request.POST)
        if form.is_valid() and form.cleaned_data.get('register_as_content'):
            if not user_has_a_named_project_role(request.user, project_id, ['OWNER']):
                raise PermissionDenied("You don't have permission to register a text.")
            content, created = Content.objects.get_or_create(
                                    project = project,  
                                    defaults = {
                                        'title': project.title,  
                                        'l2': project.l2,  
                                        'l1': project.l1,
                                        'length_in_words': word_count,  
                                        'author': project.user.username,  
                                        'voice': voice,  
                                        'annotator': project.user.username,  
                                        'difficulty_level': cefr_level,  
                                        'summary': summary
                                        }
                                    )
            # Update any fields that might have changed
            if not created:
                content.title = project.title
                content.l2 = project.l2
                content.l1 = project.l1
                content.length_in_words = word_count  
                content.author = project.user.username
                content.voice = voice 
                content.annotator = project.user.username
                content.difficulty_level = cefr_level
                content.summary = summary
                content.save()
            return redirect(content.get_absolute_url())

    # If the form was not submitted or was not valid, redirect back to the project detail page.
    return redirect('project_detail', project_id=project.id)
        
@xframe_options_sameorigin
def serve_rendered_text(request, project_id, filename):
    file_path = absolute_file_name(Path(output_dir_for_project_id(project_id)) / f"{filename}")
    if file_exists(file_path):
        content_type, _ = mimetypes.guess_type(unquote(str(file_path)))
        if _s3_storage:
            s3_file = _s3_bucket.Object(key=file_path).get()
            return HttpResponse(s3_file['Body'].read(), content_type=content_type)
        else:
            return HttpResponse(open(file_path, 'rb'), content_type=content_type)
    else:
        raise Http404

def serve_rendered_text_static(request, project_id, filename):
    file_path = absolute_file_name(Path(output_dir_for_project_id(project_id)) / f"static/{filename}")
    if file_exists(file_path):
        content_type, _ = mimetypes.guess_type(unquote(str(file_path)))
        if _s3_storage:
            s3_file = _s3_bucket.Object(key=file_path).get()
            return HttpResponse(s3_file['Body'].read(), content_type=content_type)
        else:
            return HttpResponse(open(file_path, 'rb'), content_type=content_type)
    else:
        raise Http404

def serve_rendered_text_multimedia(request, project_id, filename):
    file_path = absolute_file_name(Path(output_dir_for_project_id(project_id)) / f"multimedia/{filename}")
    if file_exists(file_path):
        content_type, _ = mimetypes.guess_type(unquote(str(file_path)))
        if _s3_storage:
            s3_file = _s3_bucket.Object(key=file_path).get()
            return HttpResponse(s3_file['Body'].read(), content_type=content_type)
        else:
            return HttpResponse(open(file_path, 'rb'), content_type=content_type)
    else:
        raise Http404

# Serve up self-contained zipfile of HTML pages created from a project
@login_required
def serve_zipfile(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    web_accessible_dir = Path(settings.STATIC_ROOT) / f"rendered_texts/{project.id}"
    zip_filepath = Path(settings.STATIC_ROOT) / f"rendered_texts/{project.id}.zip"

    if not zip_filepath.exists():
        raise Http404("Zipfile does not exist")

    return FileResponse(open(zip_filepath, 'rb'), as_attachment=True)

