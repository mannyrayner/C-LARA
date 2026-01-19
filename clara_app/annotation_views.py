from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from .models import Acknowledgements
from .models import CLARAProject, CLARAProjectAction, FormatPreferences

from django_q.tasks import async_task
from .forms import AcknowledgementsForm
from .forms import CreatePlainTextForm, CreateTitleTextForm, CreateSegmentedTitleTextForm, CreateSummaryTextForm, CreateCEFRTextForm, CreateSegmentedTextForm
from .forms import CreateTranslatedTextForm, CreatePhoneticTextForm, CreateGlossedTextForm, CreateLemmaTaggedTextForm, CreateMWETaggedTextForm
from .forms import CreatePinyinTaggedTextForm, CreateLemmaAndGlossTaggedTextForm
from .forms import FormatPreferencesForm
from .utils import get_user_config, user_has_open_ai_key_or_credit, user_has_open_ai_key_or_credit_warn_if_admin_with_negative_balance, store_api_calls, make_asynch_callback_and_report_id
from .utils import user_has_a_project_role, user_has_a_named_project_role
from .utils import get_task_updates

from .clara_main import CLARAProjectInternal

from .clara_internalise import internalize_text
from .clara_conventional_tagging import fully_supported_treetagger_language
from .clara_chinese import is_chinese_language
from .clara_mwe import annotate_mwes_in_text
from .clara_classes import InternalCLARAError, InternalisationError, MWEError
from .clara_utils import get_config, read_txt_file
from .clara_utils import post_task_update, is_rtl_language, is_chinese_language
import logging
import traceback

config = get_config()
logger = logging.getLogger(__name__)

# Generic code for the operations which support creating, annotating, improving and editing text,
# to produce and edit the "plain", "title", "summary", "cefr", "segmented", "gloss", "lemma" and "mwe" versions.
# It is also possible to retrieve archived versions of the files if they exist.
#
# The argument 'this_version' is the version we are currently creating/editing.
# The argument 'previous_version' is the version it is created from. E.g. "gloss" is created from "segmented".
# The argument 'template' is the HTML template we will use for rendering the form
#
# Most of the operations are common to all these types of text, but there are some small divergences
# which have to be treated specially:
#
# - When creating the initial "plain" version, we pass an optional prompt.
# - In the "lemma" version, we may have the additional option of using TreeTagger.
def create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template, text_choices_info=None):
    print(f'create_annotated_text_of_right_type({request}, {project_id}, {this_version}, {previous_version}, {template})')
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
    prompt = clara_project_internal.load_text_version_or_null('prompt') if this_version == 'plain' else None
    action = None

    if request.method == 'POST':
        form = CreateAnnotationTextFormOfRightType(this_version, request.POST, prompt=prompt,
                                                   archived_versions=archived_versions,
                                                   tree_tagger_supported=tree_tagger_supported, jieba_supported=jieba_supported, is_rtl_language=rtl_language)
        if form.is_valid():
            text_choice = form.cleaned_data['text_choice']
            if text_choice == 'generate_gloss_from_lemma':
                text_choice = 'generate'
                previous_version = 'lemma'
            
            label = form.cleaned_data['label']
            gold_standard = form.cleaned_data['gold_standard']
            username = request.user.username
            # We have an optional prompt when creating or improving the initial text.
            prompt = form.cleaned_data['prompt'] if this_version == 'plain' else None
            text_type = form.cleaned_data['text_type'] if this_version == 'segmented' else None
            if not text_choice in ( 'manual', 'load_archived', 'correct', 'generate', 'improve', 'trivial', 'placeholders', 'mwe_simplify',
                                    'tree_tagger', 'jieba', 'pypinyin', 'delete' ):
                raise InternalCLARAError(message = f'Unknown text_choice type in create_annotated_text_of_right_type: {text_choice}')
            # We're deleting the current version         
            elif text_choice == 'delete':
                annotated_text = ''
                clara_project_internal.save_text_version(this_version, annotated_text, user=username)
                messages.success(request, "File deleted")

                action = 'edit'                                         
                current_version = clara_project_internal.get_file_description(this_version, 'current')
            # We're saving an edited version of a file
            elif text_choice == 'manual':
                if not user_has_a_named_project_role(request.user, project_id, ['OWNER', 'ANNOTATOR']):
                    raise PermissionDenied("You don't have permission to save edited text.")
                annotated_text = form.cleaned_data['text']
                # Check that text is well-formed before trying to save it. If it's not well-formed, we get an InternalisationError
                try:
                    text_object = internalize_text(annotated_text, clara_project_internal.l2_language, clara_project_internal.l1_language, this_version)
                    # Do this so that we get an exception if the MWEs don't match the text
                    if this_version == 'mwe':
                        annotate_mwes_in_text(text_object)
                    clara_project_internal.save_text_version(this_version, annotated_text, 
                                                             user=username, label=label, gold_standard=gold_standard)
                    messages.success(request, "File saved")
                except InternalisationError as e:
                    messages.error(request, e.message)
                except MWEError as e:
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
            #elif text_choice in ( 'generate', 'correct', 'improve' ) and not request.user.userprofile.credit > 0:
            #elif text_choice in ( 'generate', 'correct', 'improve' ) and not user_has_open_ai_key_or_credit(request.user):
            elif text_choice in ( 'generate', 'correct', 'improve' ) and not user_has_open_ai_key_or_credit_warn_if_admin_with_negative_balance(request):
                messages.error(request, f"Sorry, you need a registered OpenAI API key or money in your account to perform this operation")
                annotated_text = ''
                text_choice = 'manual'
            elif text_choice in ( 'generate', 'correct', 'improve', 'trivial', 'placeholders', 'tree_tagger', 'mwe_simplify', 'jieba', 'pypinyin' ):
                if not user_has_a_named_project_role(request.user, project_id, ['OWNER']):
                    raise PermissionDenied("You don't have permission to change the text.")
                try:
                    # Create a unique ID to tag messages posted by this task, and a callback
                    task_type = f'{text_choice}_{this_version}'
                    callback, report_id = make_asynch_callback_and_report_id(request, task_type)

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
                                   request.user, label, previous_version=previous_version, prompt=prompt, text_type=text_type, callback=callback)
                        print(f'--- Started generation task, callback = {callback}')
                        #Redirect to the monitor view, passing the task ID and report ID as parameters
                        return redirect('generate_text_monitor', project_id, this_version, report_id)
                    # We are improving the text using the AI
                    elif text_choice == 'improve':
                        # We want to get a possible template error here rather than in the asynch process
                        clara_project_internal.try_to_use_templates('improve', this_version)
                        async_task(perform_improve_operation_and_store_api_calls, this_version, project, clara_project_internal,
                                   request.user, label, prompt=prompt, text_type=text_type, callback=callback)
                        print(f'--- Started improvement task')
                        #Redirect to the monitor view, passing the task ID and report ID as parameters
                        return redirect('generate_text_monitor', project_id, this_version, report_id)
                    # We are creating the text using trivial tagging. This operation is only possible with lemma tagging
                    elif text_choice == 'trivial':
                        action, api_calls = ( 'generate', clara_project_internal.create_lemma_tagged_text_with_trivial_tags(user=username, label=label) )
                        # These operations are handled elsewhere for generation and improvement, due to asynchrony
                        store_api_calls(api_calls, project, request.user, this_version)
                        annotated_text = clara_project_internal.load_text_version(this_version)
                        text_choice = 'manual'
                        success_message = f'Created {this_version} text with trivial tags'
                        print(f'--- {success_message}')
                        messages.success(request, success_message)
                        current_version = clara_project_internal.get_file_description(this_version, 'current')
                    # We are adding placeholders to the text, creating it if it doesn't already exist
                    elif text_choice == 'placeholders':
                        action, api_calls = ( 'generate', clara_project_internal.align_text_version_with_segmented_and_save(this_version,
                                                                                                                            create_if_necessary=True,
                                                                                                                            use_words_for_lemmas=True) )
                        # These operations are handled elsewhere for generation and improvement, due to asynchrony
                        store_api_calls(api_calls, project, request.user, this_version)
                        annotated_text = clara_project_internal.load_text_version(this_version)
                        text_choice = 'manual'
                        success_message = f'Created {this_version} text with trivial tags'
                        print(f'--- {success_message}')
                        messages.success(request, success_message)
                        current_version = clara_project_internal.get_file_description(this_version, 'current')

                    # We are creating the text using TreeTagger. This operation is only possible with lemma tagging
                    elif text_choice == 'tree_tagger':
                        action, api_calls = ( 'generate', clara_project_internal.create_lemma_tagged_text_with_treetagger(user=username, label=label) )
                        store_api_calls(api_calls, project, request.user, this_version)
                        annotated_text = clara_project_internal.load_text_version(this_version)
                        text_choice = 'manual'
                        success_message = f'Created {this_version} text using TreeTagger'
                        print(f'--- {success_message}')
                        messages.success(request, success_message)
                        current_version = clara_project_internal.get_file_description(this_version, 'current')
                    # We are removing MWE analyses. This operation is only possible with MWE tagging
                    elif text_choice == 'mwe_simplify':
                        action, api_calls = ( 'generate', clara_project_internal.remove_analyses_from_mwe_tagged_text(user=username, label=label) )
                        store_api_calls(api_calls, project, request.user, this_version)
                        annotated_text = clara_project_internal.load_text_version('mwe')
                        text_choice = 'manual'
                        success_message = f'Removed CoT traces from {this_version} text'
                        print(f'--- {success_message}')
                        messages.success(request, success_message)
                        current_version = clara_project_internal.get_file_description('mwe', 'current')
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
                    # We are creating the text using pypinyin. This operation is only possible with pinyin-annotation
                    elif text_choice == 'pypinyin':
                        action, api_calls = ( 'generate', clara_project_internal.create_pinyin_tagged_text_using_pypinyin(user=username, label=label) )
                        # These operations are handled elsewhere for generation and improvement, due to asynchrony
                        store_api_calls(api_calls, project, request.user, this_version)
                        annotated_text = clara_project_internal.load_text_version(this_version)
                        text_choice = 'manual'
                        success_message = f'Created {this_version} text using pypinyin'
                        print(f'--- {success_message}')
                        messages.success(request, success_message)
                        current_version = clara_project_internal.get_file_description(this_version, 'current')
                except InternalisationError as e:
                    messages.error(request, f"Something appears to be wrong with a prompt example. Error details: {e.message}")
                    annotated_text = ''
                except Exception as e:
                    raise e
                    messages.error(request, f"An error occurred while producing the text. Error details: {str(e)}\n{traceback.format_exc()}")
                    annotated_text = ''
            # If something happened, log it. We don't much care if this fails.
            if action:
                try:
                    CLARAProjectAction.objects.create(
                        project=project,
                        action=action,
                        text_version=this_version,
                        user=request.user
                    )
                except:
                    pass
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
                                               prompt=prompt, archived_versions=archived_versions,
                                               current_version=current_version, previous_version=previous_version,
                                               tree_tagger_supported=tree_tagger_supported, jieba_supported=jieba_supported, is_rtl_language=rtl_language)

    #print(f'text_choices_info: {text_choices_info}')
    clara_version = get_user_config(request.user)['clara_version']

    return render(request, template, {'form': form, 'project': project, 'text_choices_info': text_choices_info, 'clara_version': clara_version})

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
            messages.error(request, f"Something went wrong when creating {version} text. Try looking at the 'Recent task updates' view")
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
        prompt = clara_project_internal.load_text_version_or_null('prompt') if version == 'plain' else None

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
                                               prompt=prompt, archived_versions=archived_versions,
                                               current_version=current_version, previous_version=previous_version,
                                               tree_tagger_supported=tree_tagger_supported, jieba_supported=jieba_supported, is_rtl_language=rtl_language)

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, template, {'form': form, 'project': project, 'clara_version': clara_version})

def CreateAnnotationTextFormOfRightType(version, *args, **kwargs):
    if version == 'plain':
        return CreatePlainTextForm(*args, **kwargs)
    elif version == 'title':
        return CreateTitleTextForm(*args, **kwargs)
    elif version == 'segmented_title':
        return CreateSegmentedTitleTextForm(*args, **kwargs)
    elif version == 'summary':
        return CreateSummaryTextForm(*args, **kwargs)
    elif version == 'cefr_level':
        return CreateCEFRTextForm(*args, **kwargs)
    elif version == 'segmented':
        return CreateSegmentedTextForm(*args, **kwargs)
    elif version == 'translated':
        return CreateTranslatedTextForm(*args, **kwargs)
    elif version == 'phonetic':
        return CreatePhoneticTextForm(*args, **kwargs)
    elif version == 'gloss':
        return CreateGlossedTextForm(*args, **kwargs)
    elif version == 'lemma':
        return CreateLemmaTaggedTextForm(*args, **kwargs)
    elif version == 'mwe':
        return CreateMWETaggedTextForm(*args, **kwargs)
    elif version == 'pinyin':
        return CreatePinyinTaggedTextForm(*args, **kwargs)
    elif version == 'lemma_and_gloss':
        return CreateLemmaAndGlossTaggedTextForm(*args, **kwargs)
    else:
        raise InternalCLARAError(message = f'Unknown first argument in CreateAnnotationTextFormOfRightType: {version}')

def perform_correct_operation_and_store_api_calls(annotated_text, version, project, clara_project_internal,
                                                  user_object, label, callback=None):
    try:
        config_info = get_user_config(user_object)
        operation, api_calls = perform_correct_operation(annotated_text, version, clara_project_internal, user_object.username, label, 
                                                         config_info=config_info, callback=callback)
        store_api_calls(api_calls, project, user_object, version)
        post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        #raise e
        post_task_update(callback, f"error")

def perform_correct_operation(annotated_text, version, clara_project_internal, user, label, config_info={}, callback=None):
    #print(f'clara_project_internal.correct_syntax_and_save({annotated_text}, {version}, user={user}, label={label}, callback={callback})')
    return ( 'correct', clara_project_internal.correct_syntax_and_save(annotated_text, version, user=user, label=label,
                                                                       config_info=config_info, callback=callback) )

def perform_generate_operation_and_store_api_calls(version, project, clara_project_internal,
                                                   user_object, label, previous_version='default', prompt=None, text_type=None, callback=None):
    #post_task_update(callback, f'perform_generate_operation_and_store_api_calls({version}, {project}, {clara_project_internal}, {user_object}, {label}, {previous_version}, {prompt}, {callback})')
    try:
        config_info = get_user_config(user_object)
        operation, api_calls = perform_generate_operation(version, clara_project_internal, user_object.username, label,
                                                          previous_version=previous_version, prompt=prompt, text_type=text_type, 
                                                          config_info=config_info, callback=callback)
        #print(f'perform_generate_operation_and_store_api_calls: total cost = {sum([ api_call.cost for api_call in api_calls ])}')
        store_api_calls(api_calls, project, user_object, version)
        post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Exception in perform_generate_operation_and_store_api_calls({version}, ...): {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")
    
def perform_generate_operation(version, clara_project_internal, user, label, previous_version=None, prompt=None, text_type=None, config_info={}, callback=None):
    if version == 'plain':
        return ( 'generate', clara_project_internal.create_plain_text(prompt=prompt, user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'title':
        return ( 'generate', clara_project_internal.create_title(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'segmented_title':
        return ( 'generate', clara_project_internal.create_segmented_title(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'summary':
        return ( 'generate', clara_project_internal.create_summary(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'cefr_level':
        return ( 'generate', clara_project_internal.get_cefr_level(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'segmented':
        return ( 'generate', clara_project_internal.create_segmented_text(text_type=text_type, user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'translated':
        return ( 'generate', clara_project_internal.create_translated_text(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'phonetic':
        return ( 'generate', clara_project_internal.create_phonetic_text(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'gloss':
        return ( 'generate', clara_project_internal.create_glossed_text(previous_version=previous_version,
                                                                        user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'lemma':
        return ( 'generate', clara_project_internal.create_lemma_tagged_text(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'mwe':
        return ( 'generate', clara_project_internal.create_mwe_tagged_text(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'pinyin':
        return ( 'generate', clara_project_internal.create_pinyin_tagged_text(user=user, label=label, config_info=config_info, callback=callback) )
    # There is no generate operation for lemma_and_gloss, since we make it by merging lemma and gloss
    else:
        raise InternalCLARAError(message = f'Unknown first argument in perform_generate_operation: {version}')

def perform_improve_operation_and_store_api_calls(version, project, clara_project_internal,
                                                   user_object, label, prompt=None, text_type=None, callback=None):
    try:
        config_info = get_user_config(user_object)
        operation, api_calls = perform_improve_operation(version, clara_project_internal, user_object.username, label,
                                                         prompt=prompt, text_type=text_type, config_info=config_info, callback=callback)
        store_api_calls(api_calls, project, user_object, version)
        post_task_update(callback, f"finished")
    except Exception as e:
        post_task_update(callback, f"Exception in perform_improve_operation_and_store_api_calls({version},...): {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")
 
def perform_improve_operation(version, clara_project_internal, user, label, prompt=None, text_type=None, config_info={}, callback=None):
    if version == 'plain':
        return ( 'generate', clara_project_internal.improve_plain_text(prompt=prompt, user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'title':
        return ( 'generate', clara_project_internal.improve_title(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'summary':
        return ( 'generate', clara_project_internal.improve_summary(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'segmented':
        return ( 'generate', clara_project_internal.improve_segmented_text(text_type=text_type, user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'gloss':
        return ( 'generate', clara_project_internal.improve_glossed_text(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'lemma':
        return ( 'generate', clara_project_internal.improve_lemma_tagged_text(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'pinyin':
        return ( 'generate', clara_project_internal.improve_pinyin_tagged_text(user=user, label=label, config_info=config_info, callback=callback) )
    elif version == 'lemma_and_gloss':
        return ( 'generate', clara_project_internal.improve_lemma_and_gloss_tagged_text(user=user, label=label, config_info=config_info, callback=callback) )
    else:
        raise InternalCLARAError(message = f'Unknown first argument in perform_improve_operation: {version}')

def previous_version_and_template_for_version(this_version, previous_version=None):
    if this_version == 'plain':
        return ( 'plain', 'clara_app/create_plain_text.html' )
    elif this_version == 'title':
        return ( 'plain', 'clara_app/create_title.html' )
    elif this_version == 'segmented_title':
        return ( 'title', 'clara_app/create_segmented_title.html' )
    elif this_version == 'summary':
        return ( 'plain', 'clara_app/create_summary.html' )
    elif this_version == 'cefr_level':
        return ( 'plain', 'clara_app/get_cefr_level.html' )
    elif this_version == 'segmented':
        return ( 'plain', 'clara_app/create_segmented_text.html' )
    elif this_version == 'translated':
        return ( 'segmented_with_images', 'clara_app/create_translated_text.html' )
    elif this_version == 'phonetic':
        return ( 'segmented_with_images', 'clara_app/create_phonetic_text.html' )
    elif this_version == 'gloss':
        if previous_version == 'lemma':
            return ( 'lemma', 'clara_app/create_glossed_text_from_lemma.html' )
        else:
            return ( 'segmented_with_images', 'clara_app/create_glossed_text.html' )
    elif this_version == 'lemma':
        return ( 'segmented_with_images', 'clara_app/create_lemma_tagged_text.html' )
    elif this_version == 'mwe':
        return ( 'segmented_with_images', 'clara_app/create_mwe_tagged_text.html' )
    elif this_version == 'pinyin':
        return ( 'segmented_with_images', 'clara_app/create_pinyin_tagged_text.html' )
    elif this_version == 'lemma_and_gloss':
        return ( 'lemma_and_gloss', 'clara_app/create_lemma_and_gloss_tagged_text.html' )
    else:
        raise InternalCLARAError(message = f'Unknown first argument in previous_version_and_template_for_version: {this_version}')

# Create or edit "plain" version of the text        
@login_required
@user_has_a_project_role
def create_plain_text(request, project_id):
    this_version = 'plain'
    previous_version, template = previous_version_and_template_for_version(this_version)
    text_choices_info = {
        'generate': "Generate text using AI. Select this option. Type your request into the 'Prompt' box, for example 'Write a short poem about why kittens are cute'. Then press the 'Create' button at the bottom.",
        'improve': "Improve existing text using AI: this only makes sense if there already is text. Select this option. Then press the 'Improve' button at the bottom.",
        'manual': "Manually enter/edit text. Select this option, then type whatever you want into the text box. Then press the 'Save' button at the bottom.",
        'load_archived': "Load archived version. Select this option and also select something from the 'Archived version' menu. Then press the 'Load' button at the bottom."
    }
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template, text_choices_info=text_choices_info)

#Create or edit title for the text     
@login_required
@user_has_a_project_role
def create_title(request, project_id):
    this_version = 'title'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

#Create or edit title for the text     
@login_required
@user_has_a_project_role
def create_segmented_title(request, project_id):
    this_version = 'segmented_title'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

#Create or edit "summary" version of the text     
@login_required
@user_has_a_project_role
def create_summary(request, project_id):
    this_version = 'summary'
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
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Create or edit "translated" version of the text     
@login_required
@user_has_a_project_role
def create_translated_text(request, project_id):
    this_version = 'translated'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Create or edit "phonetic" version of the text     
@login_required
@user_has_a_project_role
def create_phonetic_text(request, project_id):
    this_version = 'phonetic'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Create or edit "glossed" version of the text, using the segmented_with_images version as input     
@login_required
@user_has_a_project_role
def create_glossed_text(request, project_id):
    this_version = 'gloss'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Create or edit "glossed" version of the text, using the lemma version as input      
@login_required
@user_has_a_project_role
def create_glossed_text_from_lemma(request, project_id):
    this_version = 'gloss'
    previous_version = 'lemma'
    previous_version, template = previous_version_and_template_for_version(this_version, previous_version=previous_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Create or edit "lemma-tagged" version of the text 
@login_required
@user_has_a_project_role
def create_lemma_tagged_text(request, project_id):
    this_version = 'lemma'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Create or edit "mwe" version of the text 
@login_required
@user_has_a_project_role
def create_mwe_tagged_text(request, project_id):
    this_version = 'mwe'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Create or edit "pinyin-tagged" version of the text 
@login_required
@user_has_a_project_role
def create_pinyin_tagged_text(request, project_id):
    this_version = 'pinyin'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

# Create or edit "lemma-and-glossed" version of the text 
@login_required
@user_has_a_project_role
def create_lemma_and_gloss_tagged_text(request, project_id):
    this_version = 'lemma_and_gloss'
    previous_version, template = previous_version_and_template_for_version(this_version)
    return create_annotated_text_of_right_type(request, project_id, this_version, previous_version, template)

@login_required
@user_has_a_project_role
def edit_acknowledgements(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    try:
        acknowledgements = project.acknowledgements
    except Acknowledgements.DoesNotExist:
        acknowledgements = None

    if request.method == 'POST':
        form = AcknowledgementsForm(request.POST, instance=acknowledgements)
        if form.is_valid():
            ack = form.save(commit=False)
            ack.project = project
            ack.save()
            return redirect('project_detail', project_id=project.id)
    else:
        form = AcknowledgementsForm(instance=acknowledgements)

    return render(request, 'clara_app/edit_acknowledgements.html', {'form': form, 'project': project})

@login_required
@user_has_a_project_role
def set_format_preferences(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    preferences, created = FormatPreferences.objects.get_or_create(project=project)

    if request.method == 'POST':
        form = FormatPreferencesForm(request.POST, instance=preferences)
        if form.is_valid():
            form.save()
            messages.success(request, "Format preferences updated successfully.")
            return redirect('set_format_preferences', project_id=project_id)
    else:
        form = FormatPreferencesForm(instance=preferences)

    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/set_format_preferences.html', {'form': form, 'project': project, 'clara_version': clara_version})
