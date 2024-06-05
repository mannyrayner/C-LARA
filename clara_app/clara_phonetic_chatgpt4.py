
from .clara_chatgpt4 import call_chat_gpt4
from .clara_utils import get_config, post_task_update, remove_duplicates_from_list_of_hashable_items
from .clara_classes import ChatGPTError

import json
import traceback

config = get_config()

def get_phonetic_entries_for_words_using_chatgpt4(words, l2_language, config_info={}, callback=None):

    # Use max_annotation_words from config_info if available, otherwise default to a preset value
    if 'max_annotation_words' in config_info:
        max_words = config_info['max_annotation_words']
    else:
        max_words = int(config.get('chatgpt4_annotation', 'max_elements_to_annotate'))

    # Split the elements list into smaller chunks if necessary
    def split_elements(words, max_words):
        return [words[i:i + max_words] for i in range(0, len(words), max_words)]

    chunks = split_elements(words, max_words)

    annotated_words = []
    all_api_calls = []
    for chunk in chunks:
        annotated_chunk, api_calls = call_chatgpt4_to_get_phonetic_entries(chunk, l2_language,
                                                                           config_info=config_info, callback=callback)
        annotated_words += annotated_chunk
        all_api_calls += api_calls

    annotated_words_dict = { item[0]: item[1] for item in annotated_words }

    post_task_update(callback, f'--- Phonetic entries produced by GPT-4: {annotated_words_dict}')
    return ( annotated_words_dict, all_api_calls )

def call_chatgpt4_to_get_phonetic_entries(words, l2_language, config_info={}, callback=None):
    api_calls = []
    n_attempts = 0
    limit = int(config.get('chatgpt4_annotation', 'retry_limit'))
    annotation_prompt = phonetic_lexical_annotation_prompt(words, l2_language)
    while True:
        if n_attempts >= limit:
            raise ChatGPTError( message=f'*** Giving up, have tried sending this to ChatGPT-4 {limit} times' )
        n_attempts += 1
        post_task_update(callback, f'--- Calling ChatGPT-4 (attempt #{n_attempts}) to get phonetic entries for {len(words)} words): "{words}"')
        try:
            api_call = call_chat_gpt4(annotation_prompt, config_info=config_info, callback=callback)
            api_calls += [ api_call ]
            annotated_words = parse_chatgpt_phonetic_lexicon_response(api_call.response, words)
            return ( annotated_words, api_calls )
        except ChatGPTError as e:
            post_task_update(callback, f'*** Warning: unable to parse response from ChatGPT-4')
            post_task_update(callback, e.message)
        except Exception as e:
            post_task_update(callback, f'*** Warning: error when sending request to ChatGPT-4')
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)

def phonetic_lexical_annotation_prompt(words, l2_language):
    l2_language_specific = make_l2_language_explicit(l2_language)
    advice_and_examples_text = advice_and_examples(l2_language)
    
    return f"""I am going to give you a list of words in {l2_language_specific}, presented in a JSON format.
I want you to add phonetic lexicon entries in what is generally regarded as the standard dialect of {l2_language_specific} in the following way.

The JSON is a list of strings.

Please replace each string with a two-element list in which the first element is the original string and the second is a representation in IPA.
If the word is not a heteronym, make the second element an IPA string representing the pronunciation.
If the word is a heteronym, make the second element a list of IPA strings representing the different pronunciations, putting the most common one first.

{advice_and_examples_text}

Here are the items to gloss:

{words}

Write out just the annotated JSON with no introduction, since it will be processed by a Python script."""

def make_l2_language_explicit(language):
    table = { 'english': 'UK English',
              'french': 'Parisian French'
              }
    if language in table:
        return table[language]
    else:
        return language

def advice_and_examples(language):
    if language == 'english':
        return """Note that the English 'r' sound is usually represented in IPA as 'ɹ'.
Note also that the English hard 'g' sound is usually represented in IPA as 'ɡ'.

For example, you might convert

[ "bright", "car", "course", "grab", "does" ]

into

[ [ "bright", "bɹaɪt" ], [ "car", "kɑːɹ" ], [ "course", "kɔːs" ], [ "grab", "ɡɹæb" ], [ "does", [ "dʌz", "doʊz"] ] ]
"""

    
    elif language == 'french':
        return """Note that the French 'r' sound is usually represented in IPA as 'ʁ'.

For example, you might convert

[ "bon", "défaut", "réussi", "est" ]

into

[ [ "bon", "bɔ̃" ], [ "défaut", "defo" ], [ "réussi", "ʁeysi" ], [ "est", [ "ɛ", "ɛst"] ] ]
"""

    
    elif language == 'dutch':
        return """Note that the Dutch '-en' ending is usually represented in IPA as 'ə'.

For example, you might convert

[ "beiden", "knobelen", "band" ]

into

[ [ "beiden", "bɛidə"], [ "knobelen", "knoːbələ" ], [ "band", [ "bɑnt", "bɛnt" ] ] ]
"""

    
    else:
        """For example, in English you might convert

[ "bright", "car", "course", "grab", "does" ]

into

[ [ "bright", "bɹaɪt" ], [ "car", "kɑːɹ" ], [ "course", "kɔːs" ], [ "grab", "ɡɹæb" ], [ "does", [ "dʌz", "doʊz"] ] ]
"""

def parse_chatgpt_phonetic_lexicon_response(response, words):
    try:
        response_object = json.loads(response)
    except:
        raise ChatGPTError(message = 'Response is not correctly formatted JSON')
    if not isinstance(response_object, list):
        raise ChatGPTError(message = 'Response is not a list')
    usable_response_object = []
    for element in response_object:
        if not well_formed_element_in_phonetic_lexicon_response(element):
            print(f'*** Warning: bad element {element} in annotation response, discarding')
        else:
            usable_response_object += [ element ]
    original_words = ' '.join(words)
    annotated_words = ' '.join([ element[0] for element in usable_response_object ])
    if not words == annotated_words:
        error = f"""*** Warning: original words and annotated words are different.
 Original text: {original_words}
Annotated text: {annotated_words}"""
    return usable_response_object

def well_formed_element_in_phonetic_lexicon_response(element):
    if not isinstance(element, ( list )) and len(element) == 2:
        return False
    else:
        return isinstance(element[0], ( str )) and well_formed_second_element_in_phonetic_lexicon_response(element[1])
        
def well_formed_second_element_in_phonetic_lexicon_response(element):
    if isinstance(element, ( str )):
        return True
    if isinstance(element, ( list, tuple )):
        for item in element:
            if not isinstance(item, ( str )):
                return False
        return True
    return False

