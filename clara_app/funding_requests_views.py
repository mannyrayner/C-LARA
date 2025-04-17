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

@login_required
def funding_request(request):
    if request.method == 'POST':
        form = FundingRequestForm(request.POST)
        if form.is_valid():
            funding_request = form.save(commit=False)
            funding_request.user = request.user
            funding_request.save()
            messages.success(request, 'Your funding request has been submitted.')
            return redirect('profile')  
    else:
        form = FundingRequestForm()

    return render(request, 'clara_app/funding_request.html', {'form': form})

@login_required
@user_passes_test(lambda u: u.userprofile.is_funding_reviewer)
def review_funding_requests(request):
    own_credit_balance = request.user.userprofile.credit
    
    search_form = FundingRequestSearchForm(request.GET or None)
    query = Q()

    if search_form.is_valid():
        language = search_form.cleaned_data.get('language')
        native_or_near_native = search_form.cleaned_data.get('native_or_near_native')
        text_type = search_form.cleaned_data.get('text_type')
        purpose = search_form.cleaned_data.get('purpose')
        status = search_form.cleaned_data.get('status')

        if language and language != '':
            query &= Q(language=language)
        if native_or_near_native and native_or_near_native != '':
            query &= Q(native_or_near_native=native_or_near_native)
        if text_type and text_type != '':
            query &= Q(text_type=text_type)
        if purpose and purpose != '':
            query &= Q(purpose=purpose)
        if status and status != '':
            query &= Q(status=status)
    
    if request.method == 'POST':
        formset = ApproveFundingRequestFormSet(request.POST)
        n_filtered_requests = len(formset)
        #print(f'--- Found {n_filtered_requests} requests')
        transfers = []
        total_amount = 0
        for form in formset:
            if not form.is_valid():
                print(f'--- Invalid form data: {form}')
            else:
                request_id = int(form.cleaned_data.get('id'))
                status = form.cleaned_data.get('status')
                credit_assigned = int(form.cleaned_data.get('credit_assigned')) if form.cleaned_data.get('credit_assigned') else 0.0
                #print(f'--- id: {id}, status: {status}, credit_assigned: {credit_assigned}')
                #if status != 'Submitted' and credit_assigned >= 0.01:
                #    messages.error(request, f'Request {request_id}: not meaningful to fund a request with status "{status}"')
                if status == 'Submitted' and credit_assigned >= 0.01:
                    total_amount += credit_assigned
                    transfers.append({
                        'funding_request_id': request_id,
                        'amount': credit_assigned
                    })
        #print(f'--- total_amount = {total_amount}')
        if total_amount == 0:
            messages.error(request, 'No requests to approve.')
        elif total_amount > request.user.userprofile.credit:
            messages.error(request, 'Insufficient funds for these approvals.')
        else:
            confirmation_code = str(uuid.uuid4())
            request.session['funding_transfers'] = {
                'transfers': transfers,
                'total_amount': total_amount,
                'confirmation_code': confirmation_code,
            }
            # Send an email to the reviewer for confirmation
            recipient_email = request.user.email
            send_mail_or_print_trace('Confirm Funding Approvals',
                                     f'Please confirm your funding approvals totaling USD {total_amount:.2f} using this code: {confirmation_code}',
                                     'clara-no-reply@unisa.edu.au',
                                     [ recipient_email ],
                                     fail_silently=False)
            anonymised_email = recipient_email[0:3] + '*' * ( len(recipient_email) - 10 ) + recipient_email[-7:]
            messages.info(request, f'A confirmation email has been sent to {anonymised_email}. Please check your email to complete the approvals.')
            return redirect('confirm_funding_approvals')            

    else:
        # Populate the formset based on the search criteria etc
        filtered_requests = FundingRequest.objects.filter(query)
        n_filtered_requests = len(filtered_requests)
        initial_data = [{'id': fr.id,
                         'user': fr.user.username,
                         'language_native_or_near_native': f'{dict(SUPPORTED_LANGUAGES_AND_OTHER)[fr.language]}/{"Yes" if fr.native_or_near_native else "No"}',
                         'text_type': dict(FundingRequest.CONTENT_TYPE_CHOICES)[fr.text_type],
                         'purpose': dict(FundingRequest.PURPOSE_CHOICES)[fr.purpose],
                         'other_purpose': fr.other_purpose[:500],
                         'status': dict(FundingRequest.STATUS_CHOICES)[fr.status],
                         'credit_assigned': fr.credit_assigned,
                         }
                        for fr in filtered_requests]
        #print(f'--- initial_data from filtered_requests')
        #pprint.pprint(initial_data)
        formset = ApproveFundingRequestFormSet(initial=initial_data)

    return render(request, 'clara_app/review_funding_requests.html',
                  {'own_credit_balance': own_credit_balance, 'n_filtered_requests': n_filtered_requests,
                   'formset': formset, 'search_form': search_form})

@login_required
@user_passes_test(lambda u: u.userprofile.is_funding_reviewer)
def confirm_funding_approvals(request):
    if request.method == 'POST':
        form = ConfirmTransferForm(request.POST)  
        if form.is_valid():
            confirmation_code = form.cleaned_data['confirmation_code']
            session_data = request.session.get('funding_transfers')

            if not session_data:
                messages.error(request, 'No transfers found.')
            elif not confirmation_code == session_data['confirmation_code']:
                messages.error(request, 'Invalid confirmation code.')
            else:
                for transfer in session_data['transfers']:
                    # Update the funding_request
                    funding_request = FundingRequest.objects.get(id=transfer['funding_request_id'])
                    funding_request.status = 'accepted'
                    funding_request.credit_assigned = Decimal(transfer['amount'])
                    funding_request.decision_made_at = timezone.now()
                    funding_request.funder = request.user
                    funding_request.save()
                    # Perform the credit transfer
                    #print(f'Old requester credit ({funding_request.user.username}): {funding_request.user.userprofile.credit}')
                    #print(f'Old funder credit ({request.user.username}): {request.user.userprofile.credit}')
                    if funding_request.user != request.user:
                        funding_request.user.userprofile.credit += Decimal(transfer['amount'])
                        funding_request.user.userprofile.save()
                        request.user.userprofile.credit -= Decimal(transfer['amount'])
                        request.user.userprofile.save()
                    #print(f'New requester credit ({funding_request.user.username}): {funding_request.user.userprofile.credit}')
                    #print(f'New funder credit ({request.user.username}): {request.user.userprofile.credit}')
                    # Send an email to the requester to let them know the request has been approved
                    send_mail_or_print_trace('Your C-LARA funding request has been approved',
                                             f'Your C-LARA funding request was approved, and USD {transfer["amount"]:.2f} has been added to your account balance.',
                                             'clara-no-reply@unisa.edu.au',
                                             [ funding_request.user.email ],
                                             fail_silently=False)
                del request.session['funding_transfers']
                messages.success(request, 'Funding approvals confirmed and funds transferred.')
                return redirect('review_funding_requests')
    # GET request            
    else:
        form = ConfirmTransferForm()

    return render(request, 'clara_app/confirm_funding_approvals.html', {'form': form})
