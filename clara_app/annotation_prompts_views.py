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
            elif annotation_type == 'morphology':
                PromptFormSet = forms.formset_factory(MorphologyExampleForm, formset=CustomMorphologyExampleFormSet, extra=1)
            elif annotation_type == 'mwe':
                PromptFormSet = forms.formset_factory(MWEExampleForm, formset=CustomMWEExampleFormSet, extra=1)
            elif annotation_type in ( 'gloss_with_mwe', 'lemma_with_mwe' ):
                PromptFormSet = forms.formset_factory(ExampleWithMWEForm, formset=ExampleWithMWEFormSet, extra=1)
            elif ( operation == 'annotate' or annotation_type in ('presegmented', 'segmented') ):
                PromptFormSet = forms.formset_factory(StringForm, formset=CustomStringFormSet, extra=1)
            else:
                PromptFormSet = forms.formset_factory(StringPairForm, formset=CustomStringPairFormSet, extra=1)
                
            prompt_repo = PromptTemplateRepository(language)

            if request.POST.get('action') == 'Load':
                # Start by trying to get the data from our current language
                try:
                    prompts = prompt_repo.load_template_or_examples(template_or_examples, annotation_type, operation)
                except TemplateError as e1:
                    # If we're editing 'default' and we didn't find anything on the previous step, there's nothing to use, so return blank values
                    if language == 'default':
                        messages.success(request, f"Warning: nothing found, you need to write the default {template_or_examples} from scratch")
                        prompt_repo_default = PromptTemplateRepository('default')
                        prompts = prompt_repo_default.blank_template_or_examples(template_or_examples, annotation_type, operation)
                    # If we're not editing 'default' and the default language is different, try that next
                    elif language != default_language:
                        try:
                            prompt_repo_default_language = PromptTemplateRepository(default_language)
                            prompts = prompt_repo_default_language.load_template_or_examples(template_or_examples, annotation_type, operation)
                        except TemplateError as e2:
                            # If we haven't already done that, try 'default'
                            if default_language != 'default':
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
                elif annotation_type in ( 'morphology', 'mwe' ):
                    initial_data = [{'string1': triple[0], 'string2': triple[1], 'string3': triple[2]} for triple in prompts]
                elif annotation_type in ( 'gloss_with_mwe', 'lemma_with_mwe' ):
                    initial_data = [{'string1': pair[0], 'string2': pair[1]} for pair in prompts]
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
                    elif annotation_type in ( 'morphology', 'mwe' ):
                        new_prompts = [[form.cleaned_data.get('string1'), form.cleaned_data.get('string2'), form.cleaned_data.get('string3')]
                                       for form in prompt_formset]
                        if not new_prompts[-1][0] or not new_prompts[-1][1]:
                            # We didn't use the extra last field
                            new_prompts = new_prompts[:-1]
                    elif annotation_type in ( 'gloss_with_mwe', 'lemma_with_mwe' ):
                        new_prompts = [[form.cleaned_data.get('string1'), form.cleaned_data.get('string2')] for form in prompt_formset]
                        if not new_prompts[-1][0]:
                            # We didn't use the extra last field
                            new_prompts = new_prompts[:-1]
                    elif template_or_examples == 'examples' and (operation == 'annotate' or annotation_type in ( 'presegmented', 'segmented') ):
                        new_prompts = [form.cleaned_data.get('string') for form in prompt_formset]
                        if not new_prompts[-1]:
                            # We didn't use the extra last field
                            new_prompts = new_prompts[:-1]
                    else:
                        new_prompts = [[form.cleaned_data.get('string1'), form.cleaned_data.get('string2')] for form in prompt_formset]
                        if not new_prompts[-1][0] or not new_prompts[-1][1] or not new_prompts[-1][2]:
                            # We didn't use the extra last field
                            new_prompts = new_prompts[:-1]
                    #print(f'new_prompts:')
                    #pprint.pprint(new_prompts)
                    try:
                        prompt_repo.save_template_or_examples(template_or_examples, annotation_type, operation, new_prompts, request.user.username)
                        messages.success(request, "Data saved successfully")
                    except TemplateError as e:
                        messages.error(request, f"{e.message}")
                    
            else:
                raise Exception("Internal error: neither Load nor Save found in POST request to edit_prompt")

            clara_version = get_user_config(request.user)['clara_version']

            return render(request, 'clara_app/edit_prompt.html',
                          {'prompt_selection_form': prompt_selection_form, 'prompt_formset': prompt_formset, 'clara_version': clara_version})

    else:
        prompt_selection_form = PromptSelectionForm(user=request.user)
        prompt_formset = None  # No formset when the page is first loaded

    return render(request, 'clara_app/edit_prompt.html', {'prompt_selection_form': prompt_selection_form, 'prompt_formset': prompt_formset})

