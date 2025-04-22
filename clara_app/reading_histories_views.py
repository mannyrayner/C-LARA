from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, FileResponse, JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.conf import settings
from django import forms
from django.db import transaction
from django.db.models import Count, Avg, Q, Max, F, Case, Value, When, IntegerField, Sum
from django.db.models.functions import Lower
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, FileResponse, JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.conf import settings
from django import forms
from django.db import transaction
from django.db.models import Count, Avg, Q, Max, F, Case, Value, When, IntegerField, Sum
from django.db.models.functions import Lower
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.http import unquote
from django.urls import reverse

from .models import UserProfile, FriendRequest, UserConfiguration, LanguageMaster, Content, ContentAccess, TaskUpdate, Update, ReadingHistory
from .models import SatisfactionQuestionnaire, FundingRequest, Acknowledgements, Activity, ActivityRegistration, ActivityComment, ActivityVote, CurrentActivityVote
from .models import CLARAProject, HumanAudioInfo, PhoneticHumanAudioInfo, ProjectPermissions, CLARAProjectAction, Comment, Rating, FormatPreferences
from .models import Community, CommunityMembership, ImageQuestionnaireResponse
from django.contrib.auth.models import User

from django_q.tasks import async_task
from django_q.models import Task

from .forms import RegistrationForm, UserForm, UserSelectForm, UserProfileForm, FriendRequestForm, AdminPasswordResetForm, ProjectSelectionFormSet, UserConfigForm
from .forms import AssignLanguageMasterForm, AddProjectMemberForm, FundingRequestForm, FundingRequestSearchForm, ApproveFundingRequestFormSet, UserPermissionsForm
from .forms import ContentSearchForm, ContentRegistrationForm, AcknowledgementsForm, UnifiedSearchForm
from .forms import ProjectCommunityForm, CreateCommunityForm, UserAndCommunityForm, ProjectCommunityForm, AssignMemberForm
from .forms import ActivityForm, ActivitySearchForm, ActivityRegistrationForm, ActivityCommentForm, ActivityVoteForm, ActivityStatusForm, ActivityResolutionForm
from .forms import AIActivitiesUpdateForm, DeleteContentForm
from .forms import ProjectCreationForm, UpdateProjectTitleForm, UpdateCoherentImageSetForm
from .forms import SimpleClaraForm, ProjectImportForm, ProjectSearchForm, AddCreditForm, ConfirmTransferForm
from .forms import DeleteTTSDataForm, AudioMetadataForm, InitialiseORMRepositoriesForm
from .forms import HumanAudioInfoForm, LabelledSegmentedTextForm, AudioItemFormSet, PhoneticHumanAudioInfoForm
from .forms import CreatePlainTextForm, CreateTitleTextForm, CreateSegmentedTitleTextForm, CreateSummaryTextForm, CreateCEFRTextForm, CreateSegmentedTextForm
from .forms import CreateTranslatedTextForm, CreatePhoneticTextForm, CreateGlossedTextForm, CreateLemmaTaggedTextForm, CreateMWETaggedTextForm
from .forms import CreatePinyinTaggedTextForm, CreateLemmaAndGlossTaggedTextForm
from .forms import MakeExportZipForm, RenderTextForm, RegisterAsContentForm, RatingForm, CommentForm, DiffSelectionForm
from .forms import TemplateForm, PromptSelectionForm, StringForm, StringPairForm, CustomTemplateFormSet, CustomStringFormSet, CustomStringPairFormSet
from .forms import MorphologyExampleForm, CustomMorphologyExampleFormSet, MWEExampleForm, CustomMWEExampleFormSet, ExampleWithMWEForm, ExampleWithMWEFormSet
from .forms import ImageForm, ImageFormSet, ImageDescriptionForm, ImageDescriptionFormSet, StyleImageForm, ImageSequenceForm 
from .forms import PhoneticLexiconForm, PlainPhoneticLexiconEntryFormSet, AlignedPhoneticLexiconEntryFormSet
from .forms import L2LanguageSelectionForm, AddProjectToReadingHistoryForm, RequirePhoneticTextForm, SatisfactionQuestionnaireForm
from .forms import GraphemePhonemeCorrespondenceFormSet, AccentCharacterFormSet, FormatPreferencesForm
from .forms import ImageFormV2, ImageFormSetV2, CoherentImagesV2ParamsForm
from .utils import get_user_config, user_has_open_ai_key_or_credit, create_internal_project_id, store_api_calls, store_cost_dict, make_asynch_callback_and_report_id
from .utils import get_user_api_cost, get_project_api_cost, get_project_operation_costs, get_project_api_duration, get_project_operation_durations
from .utils import user_is_project_owner, user_has_a_project_role, user_has_a_named_project_role, language_master_required
from .utils import post_task_update_in_db, get_task_updates, has_saved_internalised_and_annotated_text
from .utils import uploaded_file_to_file, create_update, current_friends_of_user, get_phase_up_to_date_dict
from .utils import send_mail_or_print_trace, get_zoom_meeting_start_date, get_previous_week_start_date
from .utils import user_is_community_member, user_is_community_coordinator, community_role_required, user_is_coordinator_of_some_community
from .utils import is_ai_enabled_language

from .clara_main import CLARAProjectInternal
#from .clara_audio_repository import AudioRepository
from .clara_audio_repository_orm import AudioRepositoryORM
from .clara_image_repository_orm import ImageRepositoryORM
from .clara_audio_annotator import AudioAnnotator
#from .clara_phonetic_lexicon_repository import PhoneticLexiconRepository
from .clara_phonetic_lexicon_repository_orm import PhoneticLexiconRepositoryORM
from .clara_prompt_templates import PromptTemplateRepository
from .clara_dependencies import CLARADependencies
from .clara_reading_histories import ReadingHistoryInternal
from .clara_phonetic_orthography_repository import PhoneticOrthographyRepository, phonetic_orthography_resources_available
from .clara_phonetic_utils import phonetic_resources_are_available

from .clara_community import assign_project_to_community

from .clara_coherent_images_utils import get_style_params_from_project_params, get_element_names_params_from_project_params, project_params_for_simple_clara
from .clara_coherent_images_utils import get_element_names_params_from_project_params, get_element_descriptions_params_from_project_params
from .clara_coherent_images_utils import get_page_params_from_project_params, default_params, style_image_name, element_image_name, page_image_name, get_element_image
from .clara_coherent_images_utils import remove_element_directory, remove_page_directory, remove_element_name_from_list_of_elements, project_pathname
from .clara_coherent_images_utils import read_project_json_file, project_pathname
from .clara_coherent_images_utils import image_dir_shows_content_policy_violation
from .clara_coherent_images_utils import description_dir_shows_only_content_policy_violations
from .clara_coherent_images_utils import content_dir_shows_only_content_policy_violations
from .clara_coherent_images_utils import style_directory, element_directory, page_directory
from .clara_coherent_images_utils import relative_style_directory, relative_element_directory, relative_page_directory

from .clara_coherent_images_alternate import get_alternate_images_json, set_alternate_image_hidden_status

from .clara_coherent_images_export import create_images_zipfile

from .clara_coherent_images_community_feedback import (load_community_feedback, save_community_feedback,
                                                       register_cm_image_vote, register_cm_element_vote, register_cm_style_vote,
                                                       register_cm_image_variants_request,
                                                       register_cm_page_advice,  get_cm_page_advice,
                                                       get_page_overview_info_for_cm_reviewing,
                                                       get_page_description_info_for_cm_reviewing,
                                                       get_element_description_info_for_cm_reviewing,
                                                       get_style_description_info_for_cm_reviewing,
                                                       update_ai_votes_in_feedback, update_ai_votes_for_element_in_feedback, update_ai_votes_for_style_in_feedback,
                                                       determine_preferred_image,
                                                       get_all_cm_requests_for_page, set_cm_request_status,
                                                       get_all_cm_requests)

from .clara_dall_e_3_image import ( create_and_add_dall_e_3_image_for_whole_text,
                                    create_and_add_dall_e_3_image_for_style )

from .save_page_texts_multiple_utils import save_page_texts_multiple

from .clara_images_utils import numbered_page_list_for_coherent_images

from .clara_internalise import internalize_text
from .clara_grapheme_phoneme_resources import grapheme_phoneme_resources_available
from .clara_conventional_tagging import fully_supported_treetagger_language
from .clara_chinese import is_chinese_language
from .clara_mwe import annotate_mwes_in_text
from .clara_annotated_images import make_uninstantiated_annotated_image_structure
from .clara_tts_api import tts_engine_type_supports_language
from .clara_chatgpt4 import call_chat_gpt4, interpret_chat_gpt4_response_as_json, call_chat_gpt4_image, call_chat_gpt4_interpret_image
from .clara_classes import TemplateError, InternalCLARAError, InternalisationError, MWEError, ImageGenerationError
from .clara_utils import _s3_storage, _s3_bucket, s3_file_name, get_config, absolute_file_name, file_exists, local_file_exists, read_txt_file, remove_file, basename
from .clara_utils import copy_local_file_to_s3, copy_local_file_to_s3_if_necessary, copy_s3_file_to_local_if_necessary, generate_s3_presigned_url
from .clara_utils import robust_read_local_txt_file, read_json_or_txt_file, check_if_file_can_be_read
from .clara_utils import output_dir_for_project_id, image_dir_for_project_id, post_task_update, is_rtl_language, is_chinese_language
from .clara_utils import make_mp3_version_of_audio_file_if_necessary

from .constants import SUPPORTED_LANGUAGES, SUPPORTED_LANGUAGES_AND_DEFAULT, SUPPORTED_LANGUAGES_AND_OTHER, SIMPLE_CLARA_TYPES
from .constants import ACTIVITY_CATEGORY_CHOICES, ACTIVITY_STATUS_CHOICES, ACTIVITY_RESOLUTION_CHOICES, DEFAULT_RECENT_TIME_PERIOD
from .constants import TTS_CHOICES

from pathlib import Path
from decimal import Decimal
from urllib.parse import unquote
from datetime import timedelta
from ipware import get_client_ip
from collections import defaultdict

import os
import re
import json
import zipfile
import shutil
import mimetypes
import logging
import pprint
import uuid
import traceback
import tempfile
import pandas as pd
import asyncio

config = get_config()
logger = logging.getLogger(__name__)

# Show link to reading history for user and l2_language
# There are controls to change the l2 and add a project to the reading history
# The 'status' argument is used to display a completion message when we redirect back here after updating the history
@login_required
def reading_history(request, l2_language, status):
    user = request.user
    reading_history, created = ReadingHistory.objects.get_or_create(user=user, l2=l2_language)
    require_phonetic_text = reading_history.require_phonetic_text

    if created:
        create_project_and_project_internal_for_reading_history(reading_history, user, l2_language)

    clara_project = reading_history.project
    project_id = clara_project.id
    clara_project_internal = CLARAProjectInternal(clara_project.internal_id, clara_project.l2, clara_project.l1)

    if request.method == 'POST':
        action = request.POST.get('action')

        # Changing the reading history language
        if action == 'select_language':
            l2_language =  request.POST['l2']
            messages.success(request, f"Now on reading history for {l2_language}.")
            return redirect('reading_history', l2_language, 'init')

        # Deleting the reading history for the currently selected language
        elif action == 'delete_reading_history':
            reading_history.delete()
            clara_project.delete()
            clara_project_internal.delete_rendered_html(project_id)
            clara_project_internal.delete()
            messages.success(request, "Reading history deleted successfully.")
            return redirect('reading_history', l2_language, 'init')

        # Changing the status of the require_phonetic_text field for the reading history
        elif action == 'update_phonetic_preference':
            require_phonetic_text = True if 'require_phonetic_text' in request.POST and request.POST['require_phonetic_text'] == 'on' else False
            reading_history.require_phonetic_text = require_phonetic_text
            reading_history.save()
            messages.success(request, "Your preference for phonetic texts has been updated.")
            return redirect('reading_history', l2_language, 'init')

        # Adding a project to the end of the reading history     
        elif action == 'add_project':
            if reading_history:
                try:
                    new_project_id = request.POST['project_id']

                    task_type = f'update_reading_history'
                    callback, report_id = make_asynch_callback_and_report_id(request, task_type)

                    async_task(update_reading_history, reading_history, clara_project_internal, project_id, new_project_id, l2_language,
                               require_phonetic_text=require_phonetic_text, callback=callback)

                    # Redirect to the monitor view, passing the task ID and report ID as parameters
                    return redirect('update_reading_history_monitor', l2_language, report_id)
                        
                except Exception as e:
                    messages.error(request, "Something went wrong when updating the reading history. Try looking at the 'Recent task updates' view")
                    print(f"Exception: {str(e)}\n{traceback.format_exc()}")
                    return redirect('reading_history', l2_language, 'error')
            else:
                messages.error(request, f"Unable to add project to reading history")
            return redirect('reading_history', l2_language, 'error')

    # GET request
    # Display the language, the current reading history projects, a link to the compiled reading history, and controls.
    # If 'status' is 'finished' or 'error', i.e. we got here from a redirect after adding a text, display a suitable message.
    else:
        if status == 'finished':
            messages.success(request, f'Reading history successfully updated')
        elif status == 'error':
            messages.error(request, "Something went wrong when updating the reading history. Try looking at the 'Recent task updates' view")

        phonetic_resources_available = phonetic_resources_are_available(l2_language)
        languages_available = l2s_in_posted_content(require_phonetic_text=require_phonetic_text)
        projects_in_history = reading_history.get_ordered_projects()
        projects_available = projects_available_for_adding_to_history(l2_language, projects_in_history, require_phonetic_text=require_phonetic_text)
        
        l2_form = L2LanguageSelectionForm(languages_available=languages_available, l2=l2_language)
        add_project_form = AddProjectToReadingHistoryForm(projects_available=projects_available)
        require_phonetic_text_form = RequirePhoneticTextForm(initial={ 'require_phonetic_text': require_phonetic_text } )
        rendered_html_exists = clara_project_internal.rendered_html_exists(project_id)

    clara_version = get_user_config(request.user)['clara_version']

    return render(request, 'clara_app/reading_history.html', {
        'l2_form': l2_form,
        'add_project_form': add_project_form,
        'require_phonetic_text_form': require_phonetic_text_form,
        'phonetic_resources_available': phonetic_resources_available,
        'projects_in_history': projects_in_history,
        # project_id is used to construct the link to the compiled reading history
        'project_id': project_id,
        'rendered_html_exists': rendered_html_exists,
        'projects_available': projects_available,
        'clara_version': clara_version
    })

# Function to call in asynch process. Update and render the CLARAProjectInternal associated with the reading history
def update_reading_history(reading_history, clara_project_internal, project_id, new_project_id, l2_language,
                           require_phonetic_text=False, callback=None):
    try:
        project = get_object_or_404(CLARAProject, pk=project_id)
        new_project = get_object_or_404(CLARAProject, pk=new_project_id)
        
        reading_history.add_project(new_project)
        reading_history.save()

        projects_in_history = reading_history.get_ordered_projects()
        
        internal_projects_in_history = [ CLARAProjectInternal(project.internal_id, project.l2, project.l1)
                                         for project in projects_in_history ]
        reading_history_internal = ReadingHistoryInternal(project_id, clara_project_internal, internal_projects_in_history)
        new_project_internal = CLARAProjectInternal(new_project.internal_id, new_project.l2, new_project.l1)
        original_number_of_component_projects = len(reading_history_internal.component_clara_project_internals)
        
        reading_history_internal.add_component_project_and_create_combined_text_object(new_project_internal, phonetic=False)
        reading_history_internal.render_combined_text_object(phonetic=False)

        if require_phonetic_text:
            reading_history_internal.add_component_project_and_create_combined_text_object(new_project_internal, phonetic=True)
            reading_history_internal.render_combined_text_object(phonetic=True)
            # If this is the first time we're compiling this reading history,
            # recompile with phonetic=False to get a link from phonetic=False version to the phonetic=True version
            if original_number_of_component_projects == 0:
                reading_history_internal.render_combined_text_object(phonetic=False)

        post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Something went wrong when trying to add project to reading history.")
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        
        post_task_update(callback, f"error")

@login_required
def update_reading_history_status(request, l2_language, report_id):
    messages = get_task_updates(report_id)
    print(f'{len(messages)} messages received')
    if 'error' in messages:
        status = 'error'
    elif 'finished' in messages:
        status = 'finished'  
    else:
        status = 'unknown'    
    return JsonResponse({'messages': messages, 'status': status})

# Render the monitoring page, which will use JavaScript to poll the task status API
@login_required
def update_reading_history_monitor(request, l2_language, report_id):

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/update_reading_history_monitor.html',
                  {'l2_language':l2_language, 'report_id': report_id, 'clara_version':clara_version})


# Create associated CLARAProject and CLARAProjectInternal
def create_project_and_project_internal_for_reading_history(reading_history, user, l2_language):
    title = f"{user}_reading_history_for_{l2_language}"
    l1_language = 'No L1 language'
    # Create a new CLARAProject, associated with the current user
    clara_project = CLARAProject(title=title, user=user, l2=l2_language, l1=l1_language)
    clara_project.save()
    internal_id = create_internal_project_id(title, clara_project.id)
    # Update the CLARAProject with the internal_id
    clara_project.internal_id = internal_id
    clara_project.save()
    # Create a new CLARAProjectInternal
    clara_project_internal = CLARAProjectInternal(internal_id, l2_language, l1_language)
    reading_history.project = clara_project
    reading_history.internal_id = internal_id
    reading_history.save()

# Find the L2s such that
#   - they are the L2 of a piece of posted content
#   - whose project has a saved internalised text
def l2s_in_posted_content(require_phonetic_text=False):
    # Get all Content objects that are linked to a CLARAProject
    contents_with_projects = Content.objects.exclude(project=None)
    l2_languages = set()

    for content in contents_with_projects:
        # Check if the associated project has saved internalized text
        if not require_phonetic_text:
            #if content.project.has_saved_internalised_and_annotated_text():
            if has_saved_internalised_and_annotated_text(content.project):
                l2_languages.add(content.l2)
        else:
            #if content.project.has_saved_internalised_and_annotated_text() and content.project.has_saved_internalised_and_annotated_text(phonetic=True):
            if has_saved_internalised_and_annotated_text(content.project) and has_saved_internalised_and_annotated_text(content.project, phonetic=True):
                l2_languages.add(content.l2)

    return list(l2_languages)

# Find the projects that
#   - have the right l2,
#   - have been posted as content,
#   - have a saved internalised text,
#   - are not already in the history
def projects_available_for_adding_to_history(l2_language, projects_in_history, require_phonetic_text=False):
    # Get all projects that have been posted as content with the specified L2 language
    projects = CLARAProject.objects.filter(
        l2=l2_language,
        related_content__isnull=False
    ).distinct()

    available_projects = []

    for project in projects:
        # Check if the project has the required saved internalized text and is not already in the history
        if not require_phonetic_text:
            #if project.has_saved_internalised_and_annotated_text() and project not in projects_in_history:
            if has_saved_internalised_and_annotated_text(project) and project not in projects_in_history:
                available_projects.append(project)
        else:
            #if project.has_saved_internalised_and_annotated_text() and project.has_saved_internalised_and_annotated_text(phonetic=True) \
            if has_saved_internalised_and_annotated_text(project) and has_saved_internalised_and_annotated_text(project, phonetic=True) \
               and project not in projects_in_history:
                available_projects.append(project)

    return available_projects
