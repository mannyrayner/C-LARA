"""
Call ChatGPT-4 to try to fix non-well-formed annotated text. Typically this will be a question of missing or superfluous
hashtags or slashes in glossed or lemma-tagged text.
"""

from .clara_chatgpt4 import call_chat_gpt4
from .clara_internalise import parse_content_elements
from .clara_utils import get_config, post_task_update
from .clara_classes import InternalCLARAError, ChatGPTError

config = get_config()

def correct_syntax_in_string(text, text_type, l2, l1=None, config_info={}, callback=None):
    if not text_type in ( 'segmented', 'gloss', 'lemma' ):
        raise InternalCLARAError(message = f'Unknown text_type "{text_type}" in correct_syntax_in_string' )
    segments = text.split('||')
    segments_out = []
    all_api_calls = []
    for segment in segments:
        segment_out, api_calls = correct_syntax_in_segment(segment, text_type, l2, l1=l1, config_info=config_info, callback=callback)
        all_api_calls += api_calls
        segments_out += [ segment_out ]
    return ( '||'.join(segments_out), all_api_calls )

def correct_syntax_in_segment(segment_text, text_type, l2, l1=None, config_info={}, callback=None):
    try:
        parse_content_elements(segment_text, text_type)
        # We didn't raise an exception, so it's okay. Return the original text with null API calls
        api_calls = []
        return ( segment_text, api_calls )
    except:
        # We did get an exception, so try to fix it
        return call_chatgpt4_to_correct_syntax_in_segment(segment_text, text_type, l2, l1=l1, config_info=config_info, callback=callback)

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
                post_task_update(callback, f'--- Corrected to "{corrected_segment_text}", now well-formed')
                return ( corrected_segment_text, api_calls )
            except:
                post_task_update(callback, f'--- Corrected to "{corrected_segment_text}", but this is still not well-formed')
        except Exception as e:
            post_task_update(callback, f'*** Warning: error when sending request to ChatGPT-4')
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)

def prompt_to_correct_syntax_in_segment(segment_text, text_type, l2, l1=None):
    if text_type == 'segmented':
        return prompt_to_correct_segmented_syntax_in_segment(segment_text, l2)
    elif text_type == 'gloss':
        return prompt_to_correct_gloss_syntax_in_segment(segment_text, l2, l1)
    else:
        return prompt_to_correct_lemma_syntax_in_segment(segment_text, l2)

def prompt_to_correct_segmented_syntax_in_segment(segment_text, l2):
    return f"""I am going to give you a piece of {l2.capitalize()} text, which has been marked up so that compound words
are separated into components using vertical bars. For example, in English the word "fir-tree" might be marked up as "fir-|tree".
The annotation is not well-formed, perhaps because one or more vertical bar have been inadvertently added or removed. Please correct,
only changing vertical bar annotations and not the words themselves. Here is the annotated text:

{segment_text}

The outut will be read by a Python script, so return only the corrected annotated text without any introduction, explanation or postscript."""

def prompt_to_correct_gloss_syntax_in_segment(segment_text, l2, l1):
    return f"""I am going to give you a piece of {l2.capitalize()} text, which should have been marked up so that each word is
followed by a {l1.capitalize()} gloss enclosed in hashtags. For example, glossing French in English, a correctly glossed piece of
text might look like this: "le#the# chien#dog#".

The annotation in this case is not well-formed, perhaps because one or more hashtags have been inadvertently added or removed.
Please correct, if possible only changing the hashtags and not the words or glosses themselves. Here is the annotated text:

{segment_text}

The outut will be read by a Python script, so return only the corrected annotated text without any introduction, explanation or postscript."""

def prompt_to_correct_lemma_syntax_in_segment(segment_text, l2):
    return f"""I am going to give you a piece of {l2.capitalize()} text, which should have been marked up so that each word is
followed by a lemma form and a Universal Dependencies v2 part of speech tag enclosed in hashtags and separated by a slash.
For example, glossing French in English, a correctly glossed piece of text might look like this:

les#les/DET# femmes#femme/NOUN# travaillent#travailler/VERB#

The annotation in this case is not well-formed, perhaps because one or more hashtags or slashes have been inadvertently added or removed.
Please correct, if possible only changing the hashtags and not the words or glosses themselves. Here is the annotated text:

{segment_text}

The outut will be read by a Python script, so return only the corrected annotated text without any introduction, explanation or postscript."""
