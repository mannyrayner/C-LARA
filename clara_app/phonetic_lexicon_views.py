from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages

from django_q.tasks import async_task
from .forms import PhoneticLexiconForm, PlainPhoneticLexiconEntryFormSet, AlignedPhoneticLexiconEntryFormSet
from .forms import GraphemePhonemeCorrespondenceFormSet, AccentCharacterFormSet
from .utils import get_user_config, make_asynch_callback_and_report_id
from .utils import language_master_required
from .utils import get_task_updates
from .utils import uploaded_file_to_file
#from .clara_phonetic_lexicon_repository import PhoneticLexiconRepository
from .clara_phonetic_lexicon_repository_orm import PhoneticLexiconRepositoryORM
from .clara_phonetic_orthography_repository import PhoneticOrthographyRepository, phonetic_orthography_resources_available
from .clara_utils import get_config, remove_file
from .clara_utils import copy_local_file_to_s3_if_necessary
from .clara_utils import post_task_update
import logging
import traceback

config = get_config()
logger = logging.getLogger(__name__)

# Allow a language master to edit a phonetic lexicon
@login_required
@language_master_required
def edit_phonetic_lexicon(request):
    orthography_repo = PhoneticOrthographyRepository()
    phonetic_lexicon_repo = PhoneticLexiconRepositoryORM()
    #phonetic_lexicon_repo = PhoneticLexiconRepositoryORM() if _use_orm_repositories else PhoneticLexiconRepository()
    plain_lexicon_formset = None
    aligned_lexicon_formset = None
    grapheme_phoneme_formset = None
    accents_formset = None
    if request.method == 'POST':
        form = PhoneticLexiconForm(request.POST, user=request.user)
        grapheme_phoneme_formset = GraphemePhonemeCorrespondenceFormSet(request.POST, prefix='grapheme_phoneme')
        accents_formset = AccentCharacterFormSet(request.POST, prefix='accents')
        plain_lexicon_formset = PlainPhoneticLexiconEntryFormSet(request.POST, prefix='plain')
        aligned_lexicon_formset = AlignedPhoneticLexiconEntryFormSet(request.POST, prefix='aligned')
        if not form.is_valid():
            messages.error(request, f"Error in form: {form.errors}")
        else:
            action = request.POST.get('action')
            language = form.cleaned_data['language']
            encoding = form.cleaned_data['encoding']
            display_grapheme_to_phoneme_entries = form.cleaned_data['display_grapheme_to_phoneme_entries']
            display_new_plain_lexicon_entries = form.cleaned_data['display_new_plain_lexicon_entries']
            display_new_aligned_lexicon_entries = form.cleaned_data['display_new_aligned_lexicon_entries']
            display_approved_plain_lexicon_entries = form.cleaned_data['display_approved_plain_lexicon_entries']
            display_approved_aligned_lexicon_entries = form.cleaned_data['display_approved_aligned_lexicon_entries']
            if action == 'Refresh':
                if language:
                    encoding = phonetic_lexicon_repo.get_encoding_for_language(language)
                    #letter_groups, accents = orthography_repo.get_text_entry(language)
                    messages.success(request, f"Current data for {language} loaded")
            if action == 'Save':
                if encoding and encoding != phonetic_lexicon_repo.get_encoding_for_language(language):
                    phonetic_lexicon_repo.set_encoding_for_language(language, encoding)
                    messages.success(request, "Language encoding saved")
                if display_grapheme_to_phoneme_entries:
                    grapheme_phoneme_data = []
                    accents_data = []
                    n_orthography_errors = 0
                    for grapheme_phoneme_form in grapheme_phoneme_formset:
                        if grapheme_phoneme_form.is_valid():
                            grapheme_variants = grapheme_phoneme_form.cleaned_data.get('grapheme_variants')
                            phonemes = grapheme_phoneme_form.cleaned_data.get('phonemes')
                            # Ignore null items
                            if grapheme_variants or phonemes:
                                grapheme_phoneme_item = { 'grapheme_variants': grapheme_variants, 'phonemes': phonemes }
                                consistent, error_message = orthography_repo.consistent_orthography_item(grapheme_phoneme_item)
                                if consistent:
                                    grapheme_phoneme_data += [ grapheme_phoneme_item ]
                                else:
                                    messages.error(request, f"Error when trying to save grapheme/phoneme data: {error_message}")
                                    n_orthography_errors += 1
                    for accents_form in accents_formset:
                         if accents_form.is_valid():
                            accent = accents_form.cleaned_data.get('unicode_value')
                            # Ignore null items
                            if accent:
                                accent_item = { 'unicode_value': accent }
                                consistent, error_message = orthography_repo.consistent_accent_item(accent_item)
                                if consistent:
                                    accents_data += [ accent_item ]
                                else:
                                    messages.error(request, f"Error when trying to save grapheme/phoneme data: {error_message}")
                                    n_orthography_errors += 1
                    if n_orthography_errors == 0:
                        orthography_repo.save_structured_data(language, grapheme_phoneme_data, accents_data)
                        messages.success(request, f"Saved grapheme/phoneme data: {len(grapheme_phoneme_data)} grapheme/phoneme items, {len(accents_data)} accent items")
                        orthography_result, orthography_details = phonetic_lexicon_repo.load_and_initialise_aligned_lexicon_from_orthography_data(grapheme_phoneme_data, language)
                        #print(f'orthography_result = {orthography_result}, orthography_details = {orthography_details}')
                        if orthography_result == 'error':
                            messages.error(request, f"Error when converting grapheme/phoneme data into aligned lexicon: {orthography_details}")
                        else:
                            messages.success(request, f"Grapheme/phoneme data also converted into aligned lexicon: {orthography_details}")
                    else:
                        messages.error(request, f"No grapheme/phoneme data saved")
                plain_words_to_save = []
                plain_words_saved = []
                plain_words_to_delete = []
                plain_words_deleted = []
                for lexicon_form in plain_lexicon_formset:
                    if lexicon_form.is_valid():
                        approve = lexicon_form.cleaned_data.get('approve')
                        delete = lexicon_form.cleaned_data.get('delete')
                        word = lexicon_form.cleaned_data.get('word')
                        phonemes = lexicon_form.cleaned_data.get('phonemes')
                        record = { 'word': word, 'phonemes': phonemes }
                        if approve:
                            plain_words_to_save.append(record) 
                        elif delete:
                            plain_words_to_delete.append(record)
                if len(plain_words_to_save) != 0:
                    phonetic_lexicon_repo.record_reviewed_plain_entries(plain_words_to_save, language)
                    plain_words_saved = [ item['word'] for item in plain_words_to_save ]
                    messages.success(request, f"{len(plain_words_saved)} plain lexicon entries saved: {', '.join(plain_words_saved)}")
                if len(plain_words_to_delete) != 0:
                    phonetic_lexicon_repo.delete_plain_entries(plain_words_to_delete, language)
                    plain_words_deleted = [ item['word'] for item in plain_words_to_delete ]
                    messages.success(request, f"{len(plain_words_deleted)} plain lexicon entries deleted: {', '.join(plain_words_deleted)}")
                    
                aligned_words_to_save = []
                aligned_words_saved = []
                aligned_words_to_delete = []
                aligned_words_deleted = []
                for aligned_lexicon_form in aligned_lexicon_formset:
                    if aligned_lexicon_form.is_valid():
                        approve = aligned_lexicon_form.cleaned_data.get('approve')
                        delete = aligned_lexicon_form.cleaned_data.get('delete')
                        word = aligned_lexicon_form.cleaned_data.get('word')
                        phonemes = aligned_lexicon_form.cleaned_data.get('phonemes')
                        aligned_graphemes = aligned_lexicon_form.cleaned_data.get('aligned_graphemes')
                        aligned_phonemes = aligned_lexicon_form.cleaned_data.get('aligned_phonemes')
                        record = { 'word': word, 'phonemes': phonemes, 'aligned_graphemes': aligned_graphemes, 'aligned_phonemes': aligned_phonemes }
                        if approve:
                            consistent, error_message = phonetic_lexicon_repo.consistent_aligned_phonetic_lexicon_entry(word, phonemes, aligned_graphemes, aligned_phonemes)
                            if not consistent:
                                messages.error(request, f"Error when trying to save data for '{word}': {error_message}")
                            else:
                                aligned_words_to_save.append(record) 
                        elif delete:
                            aligned_words_to_delete.append(record)
                if len(aligned_words_to_save) != 0:
                    phonetic_lexicon_repo.record_reviewed_aligned_entries(aligned_words_to_save, language)
                    aligned_words_saved = [ item['word'] for item in aligned_words_to_save ]
                    messages.success(request, f"{len(aligned_words_saved)} aligned lexicon entries saved: {', '.join(aligned_words_saved)}")
                if len(aligned_words_to_delete) != 0:
                    phonetic_lexicon_repo.delete_aligned_entries(aligned_words_to_delete, language)
                    aligned_words_deleted = [ item['word'] for item in aligned_words_to_delete ]
                    messages.success(request, f"{len(aligned_words_deleted)} aligned lexicon entries deleted: {', '.join(aligned_words_deleted)}")
                    
                if ( display_new_plain_lexicon_entries or display_new_aligned_lexicon_entries ) and \
                   len(plain_words_saved) == 0 and len(aligned_words_saved) == 0 and len(plain_words_deleted) == 0 and len(aligned_words_deleted) == 0:
                    messages.error(request, f"Warning: found no entries marked as approved or deleted, did not save anything")
            elif action == 'Upload':
                if 'aligned_lexicon_file' in request.FILES:
                    aligned_file_path = uploaded_file_to_file(request.FILES['aligned_lexicon_file'])
                    aligned_result, aligned_details = phonetic_lexicon_repo.load_and_initialise_aligned_lexicon(aligned_file_path, language)
                    if aligned_result == 'error':
                        messages.error(request, f"Error when uploading aligned phonetic lexicon: {aligned_details}")
                    else:
                        messages.success(request, f"Aligned phonetic lexicon uploaded successfully: {aligned_details}")
                if 'plain_lexicon_file' in request.FILES:
                    plain_file_path = uploaded_file_to_file(request.FILES['plain_lexicon_file'])
                    # If we're on Heroku, we need to copy the zipfile to S3 so that the worker process can get it
                    copy_local_file_to_s3_if_necessary(plain_file_path)

                    task_type = f'import_phonetic_lexicon'
                    callback, report_id = make_asynch_callback_and_report_id(request, task_type)

                    async_task(upload_and_install_plain_phonetic_lexicon, plain_file_path, language, callback=callback)

                    # Redirect to the monitor view, passing the language and report ID as parameters
                    return redirect('import_phonetic_lexicon_monitor', language, report_id)
                        
            if not language:
                form = None
                grapheme_phoneme_correspondence_formset = None
                accents_formset = None
                plain_lexicon_formset = None
                display_plain_lexicon_entries = False
                display_aligned_lexicon_entries = False
            else:
                grapheme_phoneme_correspondence_entries_exist = 'YES' if phonetic_orthography_resources_available(language) else 'NO'
                plain_phonetic_lexicon_entries_exist = 'YES' if phonetic_lexicon_repo.plain_phonetic_entries_exist_for_language(language) else 'NO'
                aligned_phonetic_lexicon_entries_exist = 'YES' if phonetic_lexicon_repo.aligned_entries_exist_for_language(language) else 'NO'
                form = PhoneticLexiconForm(user=request.user, initial = { 'language': language,
                                                                          'encoding': encoding,
                                                                          'grapheme_phoneme_correspondence_entries_exist': grapheme_phoneme_correspondence_entries_exist,
                                                                          'plain_phonetic_lexicon_entries_exist': plain_phonetic_lexicon_entries_exist,
                                                                          'aligned_phonetic_lexicon_entries_exist': aligned_phonetic_lexicon_entries_exist,
                                                                          'display_grapheme_to_phoneme_entries': display_grapheme_to_phoneme_entries,
                                                                          'display_new_plain_lexicon_entries': display_new_plain_lexicon_entries,
                                                                          'display_approved_plain_lexicon_entries': display_approved_plain_lexicon_entries,
                                                                          'display_new_aligned_lexicon_entries': display_new_aligned_lexicon_entries,
                                                                          'display_approved_aligned_lexicon_entries': display_approved_aligned_lexicon_entries,
                                                                          })
                grapheme_phoneme_data, accents_data = orthography_repo.get_parsed_entry(language, formatting='new')

                max_entries_to_show = int(config.get('phonetic_lexicon_repository', 'max_entries_to_show'))
                
                plain_lexicon_data = []
                if display_new_plain_lexicon_entries:
                    plain_lexicon_data += phonetic_lexicon_repo.get_generated_plain_entries(language)[:max_entries_to_show]
                if display_approved_plain_lexicon_entries:
                    plain_lexicon_data += phonetic_lexicon_repo.get_reviewed_plain_entries(language)[:max_entries_to_show]

                aligned_lexicon_data = []
                if display_new_aligned_lexicon_entries:
                    aligned_lexicon_data += phonetic_lexicon_repo.get_generated_aligned_entries(language)[:max_entries_to_show]
                if display_approved_aligned_lexicon_entries:
                    aligned_lexicon_data += phonetic_lexicon_repo.get_reviewed_aligned_entries(language)[:max_entries_to_show]
                #print(f'--- edit_phonetic_lexicon found {len(plain_lexicon_data)} plain lexicon entries to review')
                #print(f'--- edit_phonetic_lexicon found {len(aligned_lexicon_data)} aligned lexicon entries to review')
                
                grapheme_phoneme_formset = GraphemePhonemeCorrespondenceFormSet(initial=grapheme_phoneme_data, prefix='grapheme_phoneme')
                #print(f'grapheme_phoneme_formset length: {len(grapheme_phoneme_formset)}')
                #print(f'accents_formset length: {len(accents_formset)}')
                accents_formset = AccentCharacterFormSet(initial=accents_data, prefix='accents')
                plain_lexicon_formset = PlainPhoneticLexiconEntryFormSet(initial=plain_lexicon_data, prefix='plain')
                aligned_lexicon_formset = AlignedPhoneticLexiconEntryFormSet(initial=aligned_lexicon_data, prefix='aligned') 
    else:
        form = PhoneticLexiconForm(user=request.user)
        plain_lexicon_formset = None
        if form.fields['language'].initial:
            current_encoding = phonetic_lexicon_repo.get_encoding_for_language(form.fields['language'].initial)
            form.fields['encoding'].initial = current_encoding

    clara_version = get_user_config(request.user)['clara_version']

    return render(request, 'clara_app/edit_phonetic_lexicon.html',
                  {'form': form,
                   'grapheme_phoneme_formset': grapheme_phoneme_formset,
                   'accents_formset': accents_formset,
                   'plain_lexicon_formset': plain_lexicon_formset,
                   'aligned_lexicon_formset': aligned_lexicon_formset,
                   'clara_version': clara_version
                   })

def upload_and_install_plain_phonetic_lexicon(file_path, language, callback=None):
    post_task_update(callback, f"--- Installing phonetic lexicon for {language}")

    try:
        phonetic_lexicon_repo = PhoneticLexiconRepositoryORM()
        #phonetic_lexicon_repo = PhoneticLexiconRepositoryORM() if _use_orm_repositories else PhoneticLexiconRepository() 

        result, details = phonetic_lexicon_repo.load_and_initialise_plain_lexicon(file_path, language, callback=callback)
        
        if result == 'error':
            post_task_update(callback, f"Error when uploading phonetic lexicon for {language}: {details}")
            post_task_update(callback, f"error")
        else:
            post_task_update(callback, f"Phonetic lexicon for {language} uploaded successfully: {details}")
            post_task_update(callback, f"finished")

    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")
    finally:
        # remove_file removes the S3 file if we're in S3 mode (i.e. Heroku) and the local file if we're in local mode.
        remove_file(file_path)

@login_required
@language_master_required
def import_phonetic_lexicon_status(request, language, report_id):
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
@language_master_required
def import_phonetic_lexicon_monitor(request, language, report_id):
    clara_version = get_user_config(request.user)['clara_version']
    
    return render(request, 'clara_app/import_phonetic_lexicon_monitor.html',
                  {'report_id': report_id, 'language': language, 'clara_version': clara_version})

# Confirm the final result of importing the lexicon
@login_required
@language_master_required
def import_phonetic_lexicon_complete(request, language, status):
    if status == 'error':
        messages.error(request, f"Something went wrong when importing the phonetic lexicon for {language}. Try looking at the 'Recent task updates' view")
        return redirect('edit_phonetic_lexicon')
    else:
        messages.success(request, f"Phonetic lexicon for {language} imported successfully")
        return redirect('edit_phonetic_lexicon')

