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

IMAGE_QUESTIONNAIRE_QUESTIONS = [
    {
        "id": 1,
        "text": "How well does the image correspond to the page text?",
    },
    {
        "id": 2,
        "text": "How consistent is the style of the image with the overall style?",
    },
    {
        "id": 3,
        "text": "How consistent is the appearance of elements in the image with their previous appearance?",
    },
    {
        "id": 4,
        "text": "Is the image appropriate to the relevant culture?",
    },
    {
        "id": 5,
        "text": "How visually appealing do you find the image?",
    },
]

@login_required
def image_questionnaire_project_list(request):
    """
    Lists all projects that have an image questionnaire, applying optional search/filter criteria.
    Each project entry includes a link to start or continue the questionnaire for that project.
    """

    search_form = ProjectSearchForm(request.GET or None)
    query = Q(has_image_questionnaire=True)

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

    # Retrieve matching projects, order by title (case-insensitive)
    projects = CLARAProject.objects.filter(query).order_by(Lower('title'))

    return render(request, 'clara_app/image_questionnaire_project_list.html', {
        'search_form': search_form,
        'projects': projects,
    })

@login_required
def image_questionnaire_start(request, project_id):
    """
    Entry point for the image questionnaire. 
    Retrieves the story pages, stores them in session (or you could do it in memory),
    then redirects the user to the first page.
    """
    project = get_object_or_404(CLARAProject, pk=project_id)

    # Make sure the project actually has a questionnaire
    if not project.has_image_questionnaire:
        messages.error(request, 'This project does not have an image questionnaire enabled.')
        return redirect('clara_home_page')

    # Access the internal structure
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    project_dir = clara_project_internal.coherent_images_v2_project_dir

    # Read the story data
    story_data = read_project_json_file(project_dir, 'story.json') or []

    # We’ll build a global frequency map of elements -> how many pages they appear in
    element_page_count = defaultdict(int)
    
    # Filter out pages that don't have images, if you only want those
    pages_with_images = []
    for page in story_data:
        page_number = page.get('page_number')
        rel_img_path = f'pages/page{page_number}/image.jpg'
        if file_exists(project_pathname(project_dir, rel_img_path)):
            pages_with_images.append(page)

            # read relevant elements for that page
            relevant_info_path = f'pages/page{page_number}/relevant_pages_and_elements.json'
            if file_exists(project_pathname(project_dir, relevant_info_path)):
                relevant_info = read_project_json_file(project_dir, relevant_info_path)
                relevant_elems = relevant_info.get('relevant_elements', [])
                # Count how many pages each element appears in
                # We can track if we haven't incremented for this page yet, but a simpler way is to do
                # sets to avoid multiple increments for the same page.
                for elem in set(relevant_elems):
                    element_page_count[elem] += 1

    if not pages_with_images:
        # No images => no questionnaire needed
        messages.error(request, 'This project does not have any images to evaluate.')
        return redirect('clara_home_page')

    # now see if any element appears in a page
    # that indicates there's a chance of continuity
    has_any_relevant_elements = any(count > 0 for count in element_page_count.values())

    # Store pages in session, plus the boolean
    request.session['image_questionnaire_pages'] = pages_with_images
    request.session['has_any_relevant_elements'] = has_any_relevant_elements
    
    return redirect('image_questionnaire_item', project_id=project.id, index=0)


@login_required
def image_questionnaire_item(request, project_id, index):
    """
    Shows a single page's image, text, and the relevant questions.
    Handles form submission for each question, then goes forward or backward.
    """
    project = get_object_or_404(CLARAProject, pk=project_id)

    if not project.has_image_questionnaire:
        messages.error(request, 'This project does not have an image questionnaire enabled.')
        return redirect('clara_home_page')

    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    project_dir = clara_project_internal.coherent_images_v2_project_dir

    # Retrieve info from session
    pages_with_images = request.session.get('image_questionnaire_pages', [])
    has_any_relevant_elements = request.session.get('has_any_relevant_elements', False)
    
    if not pages_with_images or index < 0 or index >= len(pages_with_images):
        # Index out of range: go to a summary or fallback
        return redirect('image_questionnaire_summary', project_id=project.id)

    current_page = pages_with_images[index]
    page_number = current_page.get('page_number')
    page_text = current_page.get('text', '')
    relative_page_image_path = f'pages/page{page_number}/image.jpg'

    # Decide which questions to show
    # For question #3, we see if there's a relevant previous page
    # that shares an element with the current page
    relevant_elements_current = _get_relevant_elements(project_dir, page_number)
    has_prev_relevant_page, prev_page_num = _find_previous_relevant_page(
        pages_with_images, index, project_dir, relevant_elements_current
    )

    questions_to_show = []
    for q in IMAGE_QUESTIONNAIRE_QUESTIONS:
        if q["id"] == 3:
            # Show Q3 only if:
            #   (a) There's at least one recurring element in the entire text
            #   (b) We are not on the first page
            if has_any_relevant_elements and index > 0:
                questions_to_show.append(q)
        else:
            questions_to_show.append(q)

    if request.method == 'POST':
        # Process the user's Likert-scale answers
        for q in questions_to_show:
            q_key = f"q_{q['id']}"
            c_key = f"c_{q['id']}"

            rating_str = request.POST.get(q_key)
            comment = request.POST.get(c_key, '').strip()

            if rating_str:
                # Save or update the user’s response
                rating = int(rating_str)
                ImageQuestionnaireResponse.objects.update_or_create(
                    project=project,
                    user=request.user,
                    page_number=page_number,
                    question_id=q["id"],
                    defaults={"rating": rating, "comment": comment},
                )

        if "previous" in request.POST:
            return redirect('image_questionnaire_item', project_id=project.id, index=index - 1)
        else:
            # Next button or default
            return redirect('image_questionnaire_item', project_id=project.id, index=index + 1)

    # GET request: Load any existing answers for pre-fill
    existing_answers_raw = ImageQuestionnaireResponse.objects.filter(
    project=project,
    user=request.user,
    page_number=page_number
    )
    answers_by_id = {}
    
    for resp in existing_answers_raw:
        answers_by_id[resp.question_id] = (resp.rating, resp.comment)

    # Then build a structure that’s easy to iterate over in the template:
    question_data_list = []
    for q in questions_to_show:
        q_id = q["id"]
        rating_comment = answers_by_id.get(q_id, (None, ""))
        question_data_list.append({
            "id": q_id,
            "text": q["text"],
            "rating": str(rating_comment[0]),
            "comment": rating_comment[1],
        })

    # If we want to show the previous image for question #3, fetch its path
    previous_image_relpath = None
    if has_prev_relevant_page and prev_page_num is not None:
        previous_image_relpath = f'pages/page{prev_page_num}/image.jpg'
        # You can pass this to the template to display side-by-side

    context = {
        "project": project,
        "index": index,
        "total_pages": len(pages_with_images),
        "page_number": page_number,
        "page_text": page_text,
        "relative_image_path": relative_page_image_path,
        "questions": questions_to_show,
        "question_data_list": question_data_list,
        "show_previous": index > 0,
        "show_next": index < len(pages_with_images) - 1,
        "has_prev_relevant_page": has_prev_relevant_page,
        "previous_page_number": prev_page_num,
        "previous_image_relpath": previous_image_relpath,
    }
    #pprint.pprint(context)
    return render(request, "clara_app/image_questionnaire_item.html", context)


@login_required
def image_questionnaire_summary(request, project_id):
    """
    Show a simple "thank you" and optional stats or final summary.
    """
    project = get_object_or_404(CLARAProject, pk=project_id)
    if not project.has_image_questionnaire:
        messages.error(request, 'This project does not have an image questionnaire enabled.')
        return redirect('clara_home_page')

    # Example: let’s get how many total responses the user gave
    user_responses = ImageQuestionnaireResponse.objects.filter(project=project, user=request.user)
    pages_answered = user_responses.values_list('page_number', flat=True).distinct().count()
    questions_answered = user_responses.count()

    context = {
        "project": project,
        "pages_answered": pages_answered,
        "questions_answered": questions_answered,
    }
    return render(request, "clara_app/image_questionnaire_summary.html", context)

@login_required
def image_questionnaire_all_projects_summary(request):
    """
    Presents the aggregated questionnaire results (average ratings etc.) 
    for *all* projects that have an image questionnaire enabled.
    """
    # Optionally restrict this to superusers or some special role
    # if not request.user.is_superuser:
    #     return HttpResponseForbidden("You do not have permission to view this summary.")

    # Gather all projects that have an image questionnaire
    search_form = ProjectSearchForm(request.GET or None)
    query = Q(has_image_questionnaire=True)

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

    # Prepare a list of summary data, one entry per project
    all_project_summaries = []

    # Pre-build a quick lookup from question_id to question_text
    question_texts = {q["id"]: q["text"] for q in IMAGE_QUESTIONNAIRE_QUESTIONS}

    for proj in projects:
        # Retrieve all responses for this project
        responses = ImageQuestionnaireResponse.objects.filter(project=proj)

        if not responses.exists():
            # No responses yet, just show zeros
            all_project_summaries.append({
                "search_form": search_form,
                "project": proj,
                "distinct_pages": 0,
                "distinct_users": 0,
                "aggregated_data": [],
            })
            continue

        # Count distinct pages and users
        distinct_pages = responses.values_list("page_number", flat=True).distinct().count()
        distinct_users = responses.values_list("user_id", flat=True).distinct().count()

        # Aggregate by question: average rating and how many total responses
        agg_by_question = (
            responses
            .values("question_id")
            .annotate(avg_rating=Avg("rating"), num_responses=Count("id"))
            .order_by("question_id")
        )

        # Convert query results into a list of dicts with question text
        aggregated_data = []
        for row in agg_by_question:
            q_id = row["question_id"]
            aggregated_data.append({
                "question_id": q_id,
                "question_text": question_texts.get(q_id, f"Q{q_id}"),
                "avg_rating": row["avg_rating"],
                "num_responses": row["num_responses"],
            })

        all_project_summaries.append({
            "project": proj,
            "distinct_pages": distinct_pages,
            "distinct_users": distinct_users,
            "aggregated_data": aggregated_data,
        })

    # Pass everything to the template
    return render(request, "clara_app/image_questionnaire_all_projects_summary.html", {
        "search_form": search_form,
        "all_project_summaries": all_project_summaries,
    })

def _get_relevant_elements(project_dir, page_number):
    """
    Reads relevant_pages_and_elements.json for a given page, 
    returns the list of relevant elements (could be characters, objects, etc.).
    """

    relevant_info_path = f'pages/page{page_number}/relevant_pages_and_elements.json'
    full_path = project_pathname(project_dir, relevant_info_path)
    if file_exists(full_path):
        relevant_info = read_project_json_file(project_dir, relevant_info_path)
        return set(relevant_info.get('relevant_elements', []))
    else:
        return set()

def _find_previous_relevant_page(pages_with_images, current_index, project_dir, current_elems):
    """
    Searches backward for any page that shares at least one relevant element
    with the current page. Returns (bool, page_number).
      - bool: True if found a relevant page
      - page_number: the first page_number that shares an element, or None if none
    """
    if not current_elems:
        return (False, None)

    for i in range(current_index - 1, -1, -1):
        prev_page = pages_with_images[i]
        prev_page_num = prev_page.get("page_number")
        prev_elems = _get_relevant_elements(project_dir, prev_page_num)
        if current_elems.intersection(prev_elems):
            return (True, prev_page_num)

    return (False, None)
