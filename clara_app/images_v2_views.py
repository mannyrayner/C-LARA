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


#_edit_images_v2_trace = True
_edit_images_v2_trace = False

# Version of edit_images for uses_coherent_image_set_v2
@login_required
@user_has_a_project_role
def edit_images_v2(request, project_id, status):
    actions_requiring_openai = ( 'create_style_description_and_image',
                                 'create_element_names',
                                 'add_v2_element',
                                 'create_element_descriptions_and_images',
                                 'create_page_descriptions_and_images',
                                 'generate_variant_images' )
    user = request.user
    can_use_ai = user_has_open_ai_key_or_credit(user)
    config_info = get_user_config(user)
    username = user.username
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    clara_version = get_user_config(request.user)['clara_version']
    inconsistent = False
    style_exists = False
    element_names_exist = False
    elements_exist = False
    pages_exist = False

    try:
        project_dir = clara_project_internal.coherent_images_v2_project_dir
        # Retrieve the stored params
        params = clara_project_internal.get_coherent_images_v2_params()
    except Exception as e:
        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
        params = default_params
        inconsistent = True

    try:
        overview_file_exists = clara_project_internal.overview_document_v2_exists()
    except Exception as e:
        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
        overview_file_exists = False
        inconsistent = True   
    
    try:
        # Don't try to correct syntax errors here, there should not be any.
        all_page_texts = clara_project_internal.get_page_texts()
        if _edit_images_v2_trace:
            print(f'all_page_texts:')
            pprint.pprint(all_page_texts)
        page_texts = all_page_texts['plain']
        segmented_texts = all_page_texts['segmented']
        translated_texts = all_page_texts['translated']
        mwe_texts = all_page_texts['mwe']
        lemma_texts = all_page_texts['lemma']
        gloss_texts = all_page_texts['gloss']
        try:
            mwe_text = clara_project_internal.load_text_version("mwe")
            internalised_mwe_text = clara_project_internal.internalize_text(mwe_text, "mwe")
            # Do this so that we get an exception we can report if the MWEs don't match the text
            annotate_mwes_in_text(internalised_mwe_text)
        except FileNotFoundError as e:
            pass
        except MWEError as e:
             messages.error(request, f"{e.message}")
    except InternalisationError as e:
        messages.error(request, f"{e.message}")
        inconsistent = True
    except InternalCLARAError as e:
        messages.error(request, f"{e.message}")
        inconsistent = True
    except Exception as e:
        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
        inconsistent = True
   
    # Retrieve existing images for pages, elements and style
    try:
        images = clara_project_internal.get_project_images_dict_v2()
        if _edit_images_v2_trace:
            print(f'images:')
            pprint.pprint(images)
    except Exception as e:
        messages.error(request, f"Unable to retrieve image information")
        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
        style_data = []
        element_data = []
        indexed_page_data = []
        inconsistent = True

    background_advice = images['background']

    try:    
        style_data = [ images['style'] ] if images['style'] else []

        # Add a blank style record if we don't already have one, so that we can start
        if len(style_data) == 0:
            style_data = [{'relative_file_path': None,
                           'alternate_images': [],
                           'advice': '' }]
    except Exception as e:
        messages.error(request, f"Unable to get style information")
        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
        style_data = []
        inconsistent = True

    element_data = []
    try:
        indexed_element_data = images['elements']
        for element_text in indexed_element_data:
            item = indexed_element_data[element_text]
            element_data.append({ 'element_text': element_text,
                                  'element_name': item['element_name'],
                                  'relative_file_path': item['relative_file_path'],
                                  'advice': item['advice'],
                                  'alternate_images': item['alternate_images'] })
    except Exception as e:
        messages.error(request, f"Unable to get element information")
        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
        inconsistent = True

    try:
        indexed_page_data = images['pages']
    except Exception as e:
        messages.error(request, f"Unable to get page information")
        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
        indexed_page_data = {}
        inconsistent = True

    # Since we are displaying text and annotated text data for each page, add it here. 
    # We also need to create entries for the pages that currently have no image.
    try:
        page_data = []
        for index in range(0, len(page_texts)):
            page = index + 1
            item = { 'page': page,
                     'page_text': page_texts[index],
                     'segmented_text': segmented_texts[index],
                     'translated_text': translated_texts[index],
                     'mwe_text': mwe_texts[index],
                     'lemma_text': lemma_texts[index],
                     'gloss_text': gloss_texts[index],
                     'relative_file_path': indexed_page_data[page]['relative_file_path'] if page in indexed_page_data else None,
                     'position': 'top',
                     'advice': indexed_page_data[page]['advice'] if page in indexed_page_data else None,
                     'alternate_images': indexed_page_data[page]['alternate_images'] if page in indexed_page_data else None
                     }
            page_data.append(item)
    except Exception as e:
        messages.error(request, f"Unable to get page information")
        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
        page_data = []
        inconsistent = True

    try:
        style_exists = len(clara_project_internal.get_style_description_v2()) != 0
        element_names_exist = len(clara_project_internal.get_all_element_texts_v2()) != 0
        elements_exist = len(clara_project_internal.get_all_element_images_v2()) != 0
        pages_exist = len(clara_project_internal.get_all_page_images_v2()) != 0
    except Exception as e:
        messages.error(request, f"Unable to get information about existence of element names, elements and page images")
        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
        page_data = []
        inconsistent = True

    if inconsistent:
        return render(request, 'clara_app/edit_images_v2.html', { 'params_form': None,
                                                                  'style_formset': None,
                                                                  'element_formset': None,
                                                                  'page_formset': None,
                                                                  'project': project,
                                                                  'clara_version': clara_version,
                                                                  'overview_file_exists': overview_file_exists,
                                                                  'style_exists': style_exists,
                                                                  'element_names_exist': element_names_exist,
                                                                  'elements_exist': elements_exist,
                                                                  'pages_exist': pages_exist,
                                                                  'errors': None,
                                                                  })
    
    if request.method == 'POST':
        errors = None
        if 'action' in request.POST: 
            action = request.POST['action']
            print(f'--- action = {action}')
            if action == 'save_params':
                params_form = CoherentImagesV2ParamsForm(request.POST, prefix='params')
                if not params_form.is_valid():
                    errors = params_form.errors
                else:
                    # Get the params from the params_form and save them
                    default_model = params_form.cleaned_data['default_model']
                    params_form.cleaned_data['generate_description_model']
                    generate_description_model0 = params_form.cleaned_data['generate_description_model']
                    example_evaluation_model0 = params_form.cleaned_data['example_evaluation_model']
                    generate_element_names_model0 = params_form.cleaned_data['generate_element_names_model']
                    
                    params = { 'n_expanded_descriptions': params_form.cleaned_data['n_expanded_descriptions'],
                               'n_images_per_description': params_form.cleaned_data['n_images_per_description'],
                               'n_previous_pages': params_form.cleaned_data['n_previous_pages'],
                               'max_description_generation_rounds': params_form.cleaned_data['max_description_generation_rounds'],

                               'ai_checking_of_images': params_form.cleaned_data['ai_checking_of_images'],
                               'text_language': params_form.cleaned_data['text_language'],

                               'page_interpretation_prompt': params_form.cleaned_data['page_interpretation_prompt'],
                               'page_evaluation_prompt': params_form.cleaned_data['page_evaluation_prompt'],

                               'image_generation_model': params_form.cleaned_data['image_generation_model'],

                               'default_model': default_model,
                               'generate_element_names_model': default_model if generate_element_names_model0 == 'default' else generate_element_names_model0,
                               'generate_description_model': default_model if generate_description_model0 == 'default' else generate_description_model0,
                               'example_evaluation_model': default_model if example_evaluation_model0 == 'default' else example_evaluation_model0,
                               }
                    try:
                        clara_project_internal.save_coherent_images_v2_params(params)
                    except ImageGenerationError as e:
                        messages.error(request, f"{e.message}")
                    except Exception as e:
                        messages.error(request, f"Error when trying to save parameters")
                        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
            elif action == 'create_overview':
                try:
                    clara_project_internal.create_overview_document_v2(project)
                    if clara_project_internal.overview_document_v2_exists():
                        messages.success(request, "Overview created")
                    else:
                        messages.error(request, f"Error when trying to create overview")
                except Exception as e:
                        messages.error(request, f"Error when trying to create overview")
                        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
                return redirect('edit_images_v2', project_id=project_id, status='none')
            elif action == 'download_images_zip':
                try:
                    params = {
                        'project_dir': clara_project_internal.coherent_images_v2_project_dir,
                        'title': project.title
                    }
                    zip_bytes = create_images_zipfile(params)

                    # Create an HttpResponse to return the in-memory zip as a download
                    response = HttpResponse(zip_bytes, content_type='application/zip')
                    # You can customize the downloaded filename as you like:
                    filename = f"{project.title}_images.zip".replace(' ', '_')
                    response['Content-Disposition'] = f'attachment; filename="{filename}"'
                    return response
                except Exception as e:
                    messages.error(request, f"Error when trying to create images ZIP")
                    messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
                    return redirect('edit_images_v2', project_id=project_id, status='none')
            elif action == 'delete_v2_element':
                try:
                    deleted_element_text = request.POST.get('deleted_element_text')
                    if _edit_images_v2_trace:
                        print(f'Deleting element: {deleted_element_text}')
                    # Delete the element
                    elements_params = get_element_descriptions_params_from_project_params(params)
                    clara_project_internal.delete_element_v2(elements_params, deleted_element_text)
                    messages.success(request, f'Deleted element: {deleted_element_text}')
                    return redirect('edit_images_v2', project_id=project.id, status='none')
                except Exception as e:
                    messages.error(request, f"Error when trying to delete element")
                    messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
                    return redirect('edit_images_v2', project_id=project.id, status='none')
            elif action == 'delete_v2_page':
                try:
                    deleted_page_number = int(request.POST.get('deleted_page_number'))
                    if _edit_images_v2_trace:
                        print(f'Deleting image information for page: {deleted_page_number}')
                    # Delete 
                    page_params = get_page_params_from_project_params(params)
                    clara_project_internal.delete_page_image_v2(page_params, deleted_page_number)
                    messages.success(request, f'Deleted images and descriptions for page {deleted_page_number}')
                    return redirect('edit_images_v2', project_id=project.id, status='none')
                except Exception as e:
                    messages.error(request, f"Error when trying to delete page images")
                    messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
                    return redirect('edit_images_v2', project_id=project.id, status='none')
            elif action == 'delete_all_page_descriptions_and_images':
                print('Deleting all page images (views)') 
                try:
                    # Delete 
                    page_params = get_page_params_from_project_params(params)
                    clara_project_internal.delete_all_page_images_v2(page_params)
                    messages.success(request, f'Deleted images and descriptions for all pages')
                    return redirect('edit_images_v2', project_id=project.id, status='none')
                except Exception as e:
                    messages.error(request, f"Error when trying to delete all page images")
                    messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
                    return redirect('edit_images_v2', project_id=project.id, status='none')
            elif action == 'save_background_advice':
                background_advice_text = request.POST.get('background_advice_text', '').strip()
                print(f'background_advice_text read = "{background_advice_text}"')
                clara_project_internal.set_background_advice_v2(background_advice_text)
                messages.success(request, f'Saved background advice')
                return redirect('edit_images_v2', project_id=project.id, status='none')
            elif action in ( 'save_style_advice', 'create_style_description_and_image'):
                style_formset = ImageFormSetV2(request.POST, request.FILES, prefix='style')
                if not style_formset.is_valid():
                    errors = style_formset.errors
                else:
                    # If we have a style image line, save the advice
                    if len(style_formset) != 0:
                        form = style_formset[0]
                        style_advice = form.cleaned_data.get('advice')
                        style_data[0]['advice'] = style_advice
                        clara_project_internal.set_style_advice_v2(style_advice)
            elif action in ( 'save_element_advice', 'create_element_descriptions_and_images'):
                element_formset = ImageFormSetV2(request.POST, prefix='elements')
                if not element_formset.is_valid():
                    errors = element_formset.errors
                else:
                    # Go through the element items in the form.
                    # Collect material to save
                    for i in range(0, len(element_formset)):
                        form = element_formset[i]
                        element_text = form.cleaned_data['element_text']
                        advice = form.cleaned_data['advice']
                        clara_project_internal.set_element_advice_v2(advice, element_text)
            elif action == 'save_page_texts':
                page_formset = ImageFormSetV2(request.POST, request.FILES, prefix='pages')
                if not page_formset.is_valid():
                    errors = page_formset.errors
                else:
                    # Go through the page items in the form.
                    # Collect material to save 
                    
                    new_plain_texts = []
                    new_segmented_texts = []
                    new_translated_texts = []
                    new_mwe_texts = []
                    new_lemma_texts = []
                    new_gloss_texts = []
                    
                    for i in range(0, len(page_formset)):
                        form = page_formset[i]
                        page_number = i + 1
                        advice = form.cleaned_data['advice']
                        clara_project_internal.set_page_advice_v2(advice, page_number)

                        new_plain_texts.append(form.cleaned_data['page_text'])
                        new_segmented_texts.append(form.cleaned_data['segmented_text'])
                        new_translated_texts.append(form.cleaned_data['translated_text'])
                        new_mwe_texts.append(form.cleaned_data['mwe_text'])
                        new_lemma_texts.append(form.cleaned_data['lemma_text'])
                        new_gloss_texts.append(form.cleaned_data['gloss_text'])
                                    
                    # Save the texts back to the project
                    try:
                        types_and_texts = { 'plain': new_plain_texts,
                                            'segmented': new_segmented_texts,
                                            'translated': new_translated_texts,
                                            'mwe': new_mwe_texts,
                                            'lemma': new_lemma_texts,
                                            'gloss': new_gloss_texts }
                        # First try saving without the option of using the AI
                        api_calls = clara_project_internal.save_page_texts_multiple(types_and_texts, user=username, can_use_ai=False, config_info=config_info)
                        store_api_calls(api_calls, project, project.user, 'correct')
                    except ( InternalisationError, MWEError ) as e:
                        if not can_use_ai:
                            messages.error(request, f"There appears to be an inconsistency. Error details: {e.message}")
                            return redirect('edit_images_v2', project_id=project_id, status='none')
                        else:
                            # There was some kind of inconsistency, so now try doing it again using the AI.
                            task_type = f'correct_syntax'
                            callback, report_id = make_asynch_callback_and_report_id(request, task_type)

                            print(f'--- About to start syntax correction task')
                            async_task(save_page_texts_multiple, project, clara_project_internal, types_and_texts, username,
                                       config_info=config_info, callback=callback)
                            print(f'--- Started syntax correction task')
                            #Redirect to the monitor view, passing the project ID and report ID as parameters
                            return redirect('save_page_texts_multiple_monitor', project_id, report_id)

            # If we have errors, pass them to the template and return
            if errors:
                params_form = CoherentImagesV2ParamsForm(initial=params, prefix='params')
                page_formset = ImageFormSetV2(initial=page_data, prefix='pages')
                element_formset = ImageFormSetV2(initial=element_data, prefix='elements')
                style_formset = ImageFormSetV2(initial=style_data, prefix='style')
                return render(request, 'clara_app/edit_images_v2.html', {
                    'params_form': params_form,
                    'background_advice': background_advice,
                    'page_formset': page_formset,
                    'element_formset': element_formset,
                    'style_formset': style_formset,
                    'project': project,
                    'clara_version': clara_version,
                    'overview_file_exists': overview_file_exists,
                    'style_exists': style_exists,
                    'element_names_exist': element_names_exist,
                    'elements_exist': elements_exist,
                    'pages_exist': pages_exist,
                    'errors': errors,
                })

            # We should have saved everything and have translations, so we can get the story data from the project
            try:
                numbered_page_list = numbered_page_list_for_coherent_images(project, clara_project_internal)
                clara_project_internal.set_story_data_from_numbered_page_list_v2(numbered_page_list)
            except Exception as e:
                messages.error(request, f"Error when trying to update story data")
                messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
                return redirect('edit_images_v2', project_id=project.id, status='none')
                                                                                     
            # If we've got one of the AI actions, again we should have everything saved so we can execute it as an async and return
            if action in actions_requiring_openai:
                if not can_use_ai:
                    messages.error(request, f"Sorry, you need a registered OpenAI API key or money in your account to create images")
                    return redirect('edit_images_v2', project_id=project_id, status='none')

                if project.use_translation_for_images:
                    pages_with_missing_text = clara_project_internal.pages_with_missing_story_text_v2()
                    if pages_with_missing_text:
                        pages_with_missing_text_str = ', '.join([str(page_number) for page_number in pages_with_missing_text])
                        messages.error(request, f"Cannot create images.")
                        messages.error(request, f"Project is marked as using translations to create images, but pages are missing translations: {pages_with_missing_text_str}")
                        return redirect('edit_images_v2', project_id=project_id, status='none')

                callback, report_id = make_asynch_callback_and_report_id(request, action)

                if action == 'create_style_description_and_image':
                    async_task(create_style_description_and_image, project, clara_project_internal, params, callback=callback)
                elif action == 'add_v2_element':
                    try:
                        new_element_text = request.POST.get('new_element_text').strip()
                    except Exception as e:
                        messages.error(request, f"Error when trying to get new element name")
                        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
                        return redirect('edit_images_v2', project_id=project.id, status='none')
                    if not new_element_text:
                        messages.error(request, f"Error, new element name not provided")
                        return redirect('edit_images_v2', project_id=project.id, status='none')
                    async_task(add_v2_element, new_element_text, project, clara_project_internal, params, callback=callback)
                elif action == 'create_element_names':
                    async_task(create_element_names, project, clara_project_internal, params, callback=callback)
                elif action == 'create_element_descriptions_and_images':
                    elements_to_generate = clara_project_internal.get_elements_texts_with_no_image_v2()
                    if _edit_images_v2_trace:
                        print(f'Generating images for elements: {elements_to_generate}')
                    async_task(create_element_descriptions_and_images, project, clara_project_internal, params, elements_to_generate, callback=callback)
                elif action == 'create_page_descriptions_and_images':
                    pages_to_generate = clara_project_internal.get_pages_with_no_image_v2()
                    try:
                        number_of_pages = int(request.POST.get('number_of_pages_to_generate'))
                    except Exception:
                        number_of_pages = 'all'
                    if number_of_pages != 'all':
                        pages_to_generate = pages_to_generate[:number_of_pages]
                    if _edit_images_v2_trace:
                        print(f'Generating images for pages: {pages_to_generate}')
                    async_task(create_page_descriptions_and_images, project, clara_project_internal, params, pages_to_generate, callback=callback)

                print(f'--- Started async "{action}" task')
                #Redirect to the monitor view, passing the task ID and report ID as parameters
                return redirect('coherent_images_v2_monitor', project_id, report_id)
            else:
                # We had a save action
                params_for_project_dir = { 'project_dir': project_dir }
     
                if action == 'save_params':
                    messages.success(request, "Parameter data updated")
                elif action == 'save_style_advice':
                    messages.success(request, "Style advice updated")
                elif action == 'save_element_advice':
                    messages.success(request, "Element advice updated")
                elif action == 'save_page_texts':
                    messages.success(request, "Page text updated")
                return redirect('edit_images_v2', project_id=project_id, status='none')
            
    else:
        # GET
        params_form = CoherentImagesV2ParamsForm(initial=params, prefix='params')
        page_formset = ImageFormSetV2(initial=page_data, prefix='pages')
        element_formset = ImageFormSetV2(initial=element_data, prefix='elements')
        style_formset = ImageFormSetV2(initial=style_data, prefix='style')

        #pprint.pprint(style_data)
        
        # If 'status' is something we got after returning from an async call, display a suitable message
        if status == 'finished':
            messages.success(request, "Image task successfully completed")
        elif status == 'error':
            messages.error(request, "Something went wrong when performing this image task. Look at the 'Recent task updates' view for further information.")
        elif status == 'finished_syntax_correction':
            messages.success(request, "There was an error in the syntax. This has been corrected and the text has been saved")
        elif status == 'error_syntax_correction':
            messages.error(request, "There was an error in the syntax, and something went wrong when trying to fix it. Look at the 'Recent task updates' view for further information.")

    return render(request, 'clara_app/edit_images_v2.html', {'params_form': params_form,
                                                             'background_advice': background_advice,
                                                             'style_formset': style_formset,
                                                             'element_formset': element_formset,
                                                             'page_formset': page_formset,
                                                             'project': project,
                                                             'clara_version': clara_version,
                                                             'overview_file_exists': overview_file_exists,
                                                             'style_exists': style_exists,
                                                             'element_names_exist': element_names_exist,
                                                             'elements_exist': elements_exist,
                                                             'pages_exist': pages_exist,
                                                             'errors': []})

@login_required
@user_has_a_project_role
def coherent_images_v2_status(request, project_id, report_id):
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
def coherent_images_v2_monitor(request, project_id, report_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    
    return render(request, 'clara_app/coherent_images_v2_monitor.html',
                  {'project_id': project_id, 'project': project, 'report_id': report_id})

def create_style_description_and_image(project, clara_project_internal, params, callback=None):
    try:
        style_params = get_style_params_from_project_params(params)
        cost_dict = clara_project_internal.create_style_description_and_image_v2(style_params, callback=callback)
        store_cost_dict(cost_dict, project, project.user)
        content_dir = relative_style_directory(style_params)
        if content_dir_shows_only_content_policy_violations(content_dir, style_params):
            post_task_update(callback, f"Error: policy content violation when creating style")
            post_task_update(callback, f"error")
        else:
            post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Error when creating style")
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")

def create_element_names(project, clara_project_internal, params, callback=None):
    try:
        element_params = get_element_names_params_from_project_params(params)
        cost_dict = clara_project_internal.create_element_names_v2(element_params, callback=callback)
        store_cost_dict(cost_dict, project, project.user)
        post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Error when creating element names")
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")

def add_v2_element(new_element_text, project, clara_project_internal, params, callback=None):
    try:
        elements_params = get_element_descriptions_params_from_project_params(params)
        cost_dict = clara_project_internal.add_element_v2(elements_params, new_element_text, callback=callback)
        store_cost_dict(cost_dict, project, project.user)
        content_dir = relative_element_directory(new_element_text, elements_params)
        if file_exists(project_pathname(clara_project_internal.coherent_images_v2_project_dir, get_element_image(new_element_text, elements_params))):
            post_task_update(callback, f"Created description and image for '{new_element_text}'")
            post_task_update(callback, f"finished")
        elif content_dir_shows_only_content_policy_violations(content_dir, elements_params):
            post_task_update(callback, f"Error: policy content violation when creating new element")
            post_task_update(callback, f"error")
        else:
            post_task_update(callback, f"Something went wrong when creating description and image for '{new_element_text}'")
            post_task_update(callback, f"error")                   
    except Exception as e:
        post_task_update(callback, f"Error when trying to add element")
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")

# Async functions for coherent images v2

def create_element_descriptions_and_images(project, clara_project_internal, params, elements_to_generate, callback=None):
    try:
        element_params = get_element_descriptions_params_from_project_params(params)
        element_params['elements_to_generate'] = elements_to_generate
        cost_dict = clara_project_internal.create_element_descriptions_and_images_v2(element_params, callback=callback)
        store_cost_dict(cost_dict, project, project.user)
        bad_elements = get_elements_with_content_violations(elements_to_generate, element_params)
        if bad_elements:
            bad_elements_str = ", ".join(bad_elements)
            post_task_update(callback, f"Error: policy content violation when creating elements: {bad_elements_str}")
            post_task_update(callback, f"error")
        else:
            post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Error when creating element descriptions and images")
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")

def get_elements_with_content_violations(element_texts, params):
    bad_elements = []
    for element_text in element_texts:
        content_dir = relative_element_directory(element_text, params)
        if content_dir_shows_only_content_policy_violations(content_dir, params):
            bad_elements.append(element_text)
    return bad_elements

def create_page_descriptions_and_images(project, clara_project_internal, params, pages_to_generate, callback=None):
    try:
        page_params = get_page_params_from_project_params(params)
        page_params['pages_to_generate'] = pages_to_generate
        cost_dict = clara_project_internal.create_page_descriptions_and_images_v2(page_params, project.id, callback=callback)
        store_cost_dict(cost_dict, project, project.user)
        bad_pages = get_pages_with_content_violations(pages_to_generate, page_params)
        if bad_pages:
            bad_pages_str = ", ".join([ str(bad_page) for bad_page in bad_pages ])
            post_task_update(callback, f"Error: policy content violation when creating page: {bad_pages_str}")
            post_task_update(callback, f"error")
        else:
            post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Error when creating page images")
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")

def get_pages_with_content_violations(page_numbers, params):
    bad_pages = []
    for page_number in page_numbers:
        content_dir = relative_page_directory(page_number, params)
        if content_dir_shows_only_content_policy_violations(content_dir, params):
            bad_pages.append(page_number)
    return bad_pages

def create_variant_images(project, clara_project_internal, params, content_type, content_identifier, alternate_image_id, callback=None):
    if content_type != 'page':
        post_task_update(callback, f"Cannot yet create variant images for {content_type}")
        post_task_update(callback, f"error")
    else:
        try:
            page_params = get_page_params_from_project_params(params)
            page = content_identifier
            cost_dict = clara_project_internal.create_variant_images_for_page_v2(page_params, page, alternate_image_id, callback=callback)
            store_cost_dict(cost_dict, project, project.user)
            post_task_update(callback, f"finished")
        except Exception as e:
            post_task_update(callback, f"Error when creating variant page images")
            post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
            post_task_update(callback, f"error")
