"""
Call ChatGPT-4 to try to fix non-well-formed annotated text. Typically this will be a question of missing or superfluous
hashtags or slashes in glossed or lemma-tagged text.
"""

from .clara_chatgpt4 import call_chat_gpt4
from .clara_internalise import parse_segment_text
from .clara_utils import get_config, post_task_update
from .clara_classes import InternalCLARAError, ChatGPTError

config = get_config()

def correct_syntax_in_string(text, text_type, l2, l1=None, config_info={}, callback=None):
    if not text_type in ( 'segmented', 'segmented_title', 'gloss', 'lemma', 'translated', 'mwe' ):
        raise InternalCLARAError(message = f'Unknown text_type "{text_type}" in correct_syntax_in_string' )
    
    all_api_calls = []
    total_corrected = 0
    pages = text.split('<page>')
    pages_out = []
    for page in pages:
        segments = page.split('||')
        segments_out = []
        for segment in segments:
            segment_out, api_calls, n_corrected = correct_syntax_in_segment(segment, text_type, l2, l1=l1, config_info=config_info, callback=callback)
            all_api_calls += api_calls
            segments_out += [ segment_out ]
            total_corrected += n_corrected
        page_out = '||'.join(segments_out)
        pages_out += [ page_out ]
    if total_corrected == 0:
        post_task_update(callback, f'Did not find anything to correct')
    else:
        post_task_update(callback, f'Corrected {total_corrected} segments')
    return ( '<page>'.join(pages_out), all_api_calls )

def correct_syntax_in_segment(segment_text, text_type, l2, l1=None, config_info={}, callback=None):
    try:
        parse_segment_text(segment_text, text_type)
        # We didn't raise an exception, so it's okay. Return the original text with null API calls
        api_calls = []
        return ( segment_text, api_calls, 0 )
    except:
        # We did get an exception, so try to fix it
        ( corrected_segment_text, api_calls ) = call_chatgpt4_to_correct_syntax_in_segment(segment_text, text_type, l2, l1=l1,
                                                                                           config_info=config_info, callback=callback)
        return ( corrected_segment_text, api_calls, 1 )

def call_chatgpt4_to_correct_syntax_in_segment(segment_text, text_type, l2, l1=None, config_info={}, callback=None):
    prompt = prompt_to_correct_syntax_in_segment(segment_text, text_type, l2, l1=l1)
    n_attempts = 0
    api_calls = []
    limit = int(config.get('chatgpt4_syntax_correction', 'retry_limit'))
    while True:
        if n_attempts >= limit:
            raise ChatGPTError( message=f'*** Unable to correct text after {limit} attempts' )
        n_attempts += 1
        post_task_update(callback, f'--- Calling ChatGPT-4 to try to correct syntax in "{segment_text}" considered as {text_type} text (attempt {n_attempts})')
        try:
            api_call = call_chat_gpt4(prompt, config_info=config_info, callback=callback)
            api_calls += [ api_call ]
            corrected_segment_text = api_call.response
            try:
                parse_segment_text(corrected_segment_text, text_type)
                post_task_update(callback, f'--- Corrected "{segment_text}" to "{corrected_segment_text}", now well-formed')
                return ( corrected_segment_text, api_calls )
            except:
                post_task_update(callback, f'--- Corrected "{segment_text}" to "{corrected_segment_text}", but this is still not well-formed')
        except Exception as e:
            post_task_update(callback, f'*** Warning: error when sending request to ChatGPT-4')
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)

def prompt_to_correct_syntax_in_segment(segment_text, text_type, l2, l1=None):
    if not text_type in ( 'segmented', 'segmented_title', 'gloss', 'lemma', 'translated', 'mwe' ):
        raise InternalCLARAError(message = f'Unknown text_type "{text_type}" in correct_syntax_in_string' )
    if text_type in ( 'segmented', 'segmented_title' ):
        return prompt_to_correct_segmented_syntax_in_segment(segment_text, l2)
    elif text_type == 'gloss':
        return prompt_to_correct_gloss_syntax_in_segment(segment_text, l2, l1)
    elif text_type == 'lemma':
        return prompt_to_correct_lemma_syntax_in_segment(segment_text, l2)
    elif text_type == 'translated':
        return prompt_to_correct_translated_syntax_in_segment(segment_text, l2, l1)
    elif text_type == 'mwe':
        return prompt_to_correct_mwe_syntax_in_segment(segment_text, l2)

def prompt_to_correct_segmented_syntax_in_segment(segment_text, l2):
    return f"""I am going to give you a piece of {l2.capitalize()} text, which has been marked up so that compound words
are separated into components using vertical bars. For example, in English the word "fir-tree" might be marked up as "fir-|tree".
The annotation is not well-formed, perhaps because one or more vertical bar have been inadvertently added or removed. Please correct,
only changing vertical bar annotations and not the words themselves. Here is the annotated text:

{segment_text}

The output will be read by a Python script, so return only the corrected annotated text without any introduction, explanation or postscript."""

def prompt_to_correct_translated_syntax_in_segment(segment_text, l2, l1):
    return f"""I am going to give you a piece of {l2.capitalize()} text, which may have been annotated to include an {l1.capitalize()} translation.
If there is a translation, it should be included between hashtags at the end of the text. For example, if we were adding a French translation
to an English text, a well-formed example might be

I will go there tomorrow#J'y irai demain#

The annotation is not well-formed, perhaps because one or more hashtag has been inadvertently added or removed. Please correct,
only changing hash characters and not the words themselves. Here is the annotated text:

{segment_text}

The output will be read by a Python script, so return only the corrected annotated text without any introduction, explanation or postscript."""

def prompt_to_correct_mwe_syntax_in_segment(segment_text, l2):
    return f"""I am going to give you a piece of {l2.capitalize()} text, which has been annotated to show the multi-word expressions (MWEs).
The MWEs should be included between hashtags at the end of the text, with commas separating MWEs if there is more than one.
For example, if we were annotating MWEs in an English text, a well-formed example might be

We have run out of jelly beans.#run out,jelly beans#

The annotation is not well-formed, perhaps because a) one or more hashtag or comma has been inadvertently added or removed or
b) the words in a claimed MWE do not occur in the text or do not occur in the order give. Please correct, only changing the MWE annotation
and not the main text. Here is the annotated text:

{segment_text}

The output will be read by a Python script, so return only the corrected annotated text without any introduction, explanation or postscript."""

def prompt_to_correct_gloss_syntax_in_segment(segment_text, l2, l1):
    return f"""I am going to give you a piece of {l2.capitalize()} text, which should have been marked up so that each word is
followed by a {l1.capitalize()} gloss enclosed in hashtags. For example, glossing French in English, a correctly glossed piece of
text might look like this: "le#the# chien#dog#".

The annotation in this case is not well-formed, perhaps because one or more hashtags have been inadvertently added or removed.
Please correct, if possible only changing the hashtags and not the words or glosses themselves. Here is the annotated text:

{segment_text}

The output will be read by a Python script, so return only the corrected annotated text without any introduction, explanation or postscript."""

def prompt_to_correct_lemma_syntax_in_segment(segment_text, l2):
    return f"""I am going to give you a piece of {l2.capitalize()} text, which should have been marked up so that each word is
followed by a lemma form and a Universal Dependencies v2 part of speech tag enclosed in hashtags and separated by a slash.
For example, glossing French in English, a correctly glossed piece of text might look like this:

les#les/DET# femmes#femme/NOUN# travaillent#travailler/VERB#

The annotation in this case is not well-formed, perhaps because one or more hashtags or slashes have been inadvertently added or removed.
Please correct, if possible only changing the hashtags and not the words or glosses themselves. Here is the annotated text:

{segment_text}

The output will be read by a Python script, so return only the corrected annotated text without any introduction, explanation or postscript."""
