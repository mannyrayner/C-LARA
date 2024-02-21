"""
This module contains functions to generate segmented, glossed, and tagged versions of a given text using ChatGPT4.
These functions are used to annotate the text with various annotations, such as pages, segments, glosses, and tags.

The main functions are:

1. generate_segmented_version(text, l2_language):
   Takes a text and target language, and returns a tuple where the first element
   is a segmented version of the text and the second element is a list of APICall instances related to the operation.

2. improve_segmented_version(segmented_text, l2_language):
   Similar to (1), but takes an already segmented text and tries to improve the segmentation.

3. generate_glossed_version(segmented_text, l1_language, l2_language):
   Takes a segmented text, source language, and target language, and returns a tuple where the first element
   is a glossed version of the text and the second element is a list of APICall instances related to the operation.

4. improve_glossed_version(glossed_text, l1_language, l2_language):
   Similar to (3), but takes an already glossed text and tries to improve the glossing.

5. generate_tagged_version(segmented_text, l2_language):
   Takes a segmented text and target language, and returns a tuple where the first element
   is a tagged version of the text and the second element is a list of APICall instances related to the operation.

6. improve_tagged_version(tagged_text, l1_language, l2_language):
   Similar to (3), but takes an already tagged text and tries to improve the tagging.

There are also several utility functions to help with the annotation process.
"""

from . import clara_prompt_templates
from . import clara_chatgpt4
from . import clara_internalise
from . import clara_test

from .clara_utils import get_config, post_task_update
from .clara_classes import *

import json
import regex
import difflib
import traceback

config = get_config()

# Try invoking the template-based prompt generation with trivial text to see if we get an error
def invoke_templates_on_trivial_text(annotate_or_improve, version, l1_language, l2_language):
    if not version in ( 'segmented', 'gloss', 'lemma', 'pinyin', 'lemma_and_gloss' ):
        return True
    if version == 'segmented':
        text = ''
        return segmentation_prompt(annotate_or_improve, text, l2_language)
    if version == 'gloss':
        simplified_elements_json = []
        return glossing_prompt(annotate_or_improve, simplified_elements_json, l1_language, l2_language)
    if version == 'lemma':
        simplified_elements_json = []
        return tagging_prompt(annotate_or_improve, simplified_elements_json, l2_language)
    if version == 'pinyin':
        simplified_elements_json = []
        return pinyin_tagging_prompt(annotate_or_improve, simplified_elements_json, l2_language)
    if version == 'lemma_and_gloss':
        simplified_elements_json = []
        return joint_tagging_and_glossing_prompt(simplified_elements_json, l1_language, l2_language)
    
# Annotate the text with pages and segments
def generate_segmented_version(text, l2_language, config_info={}, callback=None):
    return generate_or_improve_segmented_version('annotate', text, l2_language, config_info=config_info, callback=callback)

# Improve annotation of the text with pages and segments
def improve_segmented_version(text, l2_language, config_info={}, callback=None):
    return generate_or_improve_segmented_version('improve', text, l2_language, config_info=config_info, callback=callback)

# Annotate the text with glosses
def generate_glossed_version(segmented_text, l1_language, l2_language, config_info={}, callback=None):
    return generate_or_improve_annotated_version('annotate', 'gloss', segmented_text, l1_language, l2_language, config_info=config_info, callback=callback)

# Improve annotation of the text with glosses
def improve_glossed_version(glossed_text, l1_language, l2_language, config_info={}, callback=None):
    return generate_or_improve_annotated_version('improve', 'gloss', glossed_text, l1_language, l2_language, config_info=config_info, callback=callback)

# Annotate the text with pinyin
def generate_pinyin_tagged_version(segmented_text, l2_language, config_info={}, callback=None):
    l1_language = 'irrelevant'
    return generate_or_improve_annotated_version('annotate', 'pinyin', segmented_text, l1_language, l2_language, config_info=config_info, callback=callback)

# Improve annotation of the text with pinyin
def improve_pinyin_tagged_version(pinyin_tagged_text, l2_language, config_info={}, callback=None):
    l1_language = 'irrelevant'
    return generate_or_improve_annotated_version('improve', 'pinyin', tagged_text, l1_language, l2_language, config_info=config_info, callback=callback)

# Annotate the text with lemmas
def generate_tagged_version(segmented_text, l2_language, config_info={}, callback=None):
    l1_language = 'irrelevant'
    return generate_or_improve_annotated_version('annotate', 'lemma', segmented_text, l1_language, l2_language, config_info=config_info, callback=callback)

# Improve annotation of the text with lemmas
def improve_tagged_version(tagged_text, l2_language, config_info={}, callback=None):
    l1_language = 'irrelevant'
    return generate_or_improve_annotated_version('improve', 'lemma', tagged_text, l1_language, l2_language, config_info=config_info, callback=callback)

# Improve annotation of the text with lemmas and glosses
def improve_lemma_and_gloss_tagged_version(tagged_text, l1_language, l2_language, config_info={}, callback=None):
    return generate_or_improve_annotated_version('improve', 'lemma_and_gloss', tagged_text, l1_language, l2_language, config_info=config_info, callback=callback)

def generate_or_improve_segmented_version(annotate_or_improve, text, l2_language, config_info={}, callback=None):
    l2_language = l2_language.capitalize()
    annotate_prompt =  segmentation_prompt(annotate_or_improve, text, l2_language)
    api_call = clara_chatgpt4.call_chat_gpt4(annotate_prompt, config_info=config_info, callback=callback)
    return ( api_call.response, [ api_call ] )

def generate_or_improve_annotated_version(annotate_or_improve, gloss_or_lemma_or_pinyin, annotated_text, l1_language, l2_language,
                                          config_info={}, callback=None):

    #post_task_update(callback, f'--- Call generate_or_improve_annotated_version, config_info = {config_info}')
    
    source_version = 'segmented' if annotate_or_improve == 'annotate' else gloss_or_lemma_or_pinyin
    internalised_annotated_text = clara_internalise.internalize_text(annotated_text, l2_language, l1_language, source_version)
    l1_language = l1_language.capitalize()
    l2_language = l2_language.capitalize()

    # Use max_annotation_words from config_info if available, otherwise default to a preset value
    if 'max_annotation_words' in config_info:
        max_elements = config_info['max_annotation_words']
    else:
        max_elements = int(config.get('chatgpt4_annotation', 'max_elements_to_annotate'))

    # Extract a list of Word and NonWordText items 
    elements = internalised_annotated_text.content_elements()

    # Split the elements list into smaller chunks if necessary
    def split_elements(elements, max_elements):
        return [elements[i:i + max_elements] for i in range(0, len(elements), max_elements)]

    chunks = split_elements(elements, max_elements)

    # Annotate each chunk separately and store the results in the annotated_elements list
    annotated_elements = []
    all_api_calls = []
    for chunk in chunks:
        annotated_chunk, api_calls = call_chatgpt4_to_annotate_or_improve_elements(annotate_or_improve, gloss_or_lemma_or_pinyin, chunk,
                                                                                   l1_language, l2_language, config_info=config_info, callback=callback)
        annotated_elements += annotated_chunk
        all_api_calls += api_calls

    # Reassemble the annotated elements back into the segmented_text structure
    index = 0
    for page in internalised_annotated_text.pages:
        for segment in page.segments:
            n_elements_in_segment = len(segment.content_elements)
            segment.content_elements = annotated_elements[index:index+n_elements_in_segment]
            index += n_elements_in_segment

    human_readable_text = internalised_annotated_text.to_text(gloss_or_lemma_or_pinyin)
    return ( human_readable_text, all_api_calls )

def call_chatgpt4_to_annotate_or_improve_elements(annotate_or_improve, gloss_or_lemma_or_pinyin, elements, l1_language, l2_language, config_info={}, callback=None):
    # Remove markup from the elements before passing to GPT-4 to make things easier for the AI
    word_and_non_word_text_elements = [ element for element in elements if element.type in ( 'Word', 'NonWordText' ) ]
    if annotate_or_improve == 'annotate':
        simplified_elements0 = [ simplify_element_to_string(element) for element in word_and_non_word_text_elements ]
    else:
        simplified_elements0 = [ simplify_element_to_list(element, gloss_or_lemma_or_pinyin) for element in word_and_non_word_text_elements ]
    simplified_elements = [ element for element in simplified_elements0 if element != False ]
    text_to_annotate = simplified_element_list_to_text(simplified_elements) 
    simplified_elements_json = json.dumps(simplified_elements)
    n_words = len(simplified_elements)
    l1_language = l1_language.capitalize()
    l2_language = l2_language.capitalize()
    if gloss_or_lemma_or_pinyin == 'gloss':
        annotation_prompt = glossing_prompt(annotate_or_improve, simplified_elements_json, l1_language, l2_language)
    elif gloss_or_lemma_or_pinyin == 'lemma':
        annotation_prompt = tagging_prompt(annotate_or_improve, simplified_elements_json, l2_language)
    elif gloss_or_lemma_or_pinyin == 'pinyin':
        annotation_prompt = pinyin_tagging_prompt(annotate_or_improve, simplified_elements_json, l2_language)
    elif gloss_or_lemma_or_pinyin == 'lemma_and_gloss' and annotate_or_improve == 'improve':
        annotation_prompt = joint_tagging_and_glossing_prompt(simplified_elements_json, l1_language, l2_language)
    else:
        raise InternalCLARAError(message = f'Unsupported combination gloss_or_lemma_or_pinyin = {gloss_or_lemma_or_pinyin} and annotate_or_improve = {annotate_or_improve} in create_annotation' )
    api_calls = []
    n_attempts = 0
    limit = int(config.get('chatgpt4_annotation', 'retry_limit'))
    while True:
        if n_attempts >= limit:
            raise ChatGPTError( message=f'*** Giving up, have tried sending this to ChatGPT-4 {limit} times' )
        n_attempts += 1
        post_task_update(callback, f'--- Calling ChatGPT-4 (attempt #{n_attempts}) to {annotate_or_improve} text ({n_words} words and punctuation marks): "{text_to_annotate}"')
        try:
            api_call = clara_chatgpt4.call_chat_gpt4(annotation_prompt, config_info=config_info, callback=callback)
            api_calls += [ api_call ]
            annotated_simplified_elements = parse_chatgpt_gloss_response(api_call.response, simplified_elements, gloss_or_lemma_or_pinyin, callback=callback)
            nontrivial_annotated_elements = [ unsimplify_element(element, gloss_or_lemma_or_pinyin) for element in annotated_simplified_elements ]
            annotated_elements = merge_elements_and_annotated_elements(elements, nontrivial_annotated_elements, gloss_or_lemma_or_pinyin)
            return ( annotated_elements, api_calls )
        except ChatGPTError as e:
            post_task_update(callback, f'*** Warning: unable to parse response from ChatGPT-4')
            post_task_update(callback, e.message)
        except Exception as e:
            post_task_update(callback, f'*** Warning: error when sending request to ChatGPT-4')
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)

def merge_elements_and_annotated_elements(elements, annotated_elements, gloss_or_lemma_or_pinyin):
    matcher = difflib.SequenceMatcher(None, 
        [element.content.strip() for element in elements], 
        [element.content.strip() for element in annotated_elements])

    # Add a placeholder annotation to all Word elements initially
    for element in elements:
        if element.type == "Word" and gloss_or_lemma_or_pinyin not in element.annotations:
            element.annotations[gloss_or_lemma_or_pinyin] = 'NO_ANNOTATION'

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            # If the contents match, we merge the annotations
            for i, j in zip(range(i1, i2), range(j1, j2)):
                elements[i].annotations.update(annotated_elements[j].annotations)
        elif tag == 'insert':
            # Handle insertions if necessary
            pass
        elif tag == 'delete':
            # Handle deletions if necessary
            pass
        elif tag == 'replace':
            # Handle replacements if necessary
            pass
    return elements

def segmentation_prompt(annotate_or_improve, text, l2_language):
    template, annotated_example_list = get_template_and_annotated_example_list(annotate_or_improve, 'segmented', l2_language)
    examples = segmentation_examples_to_text(annotated_example_list)
    return template.format( l2_language=l2_language,
                            examples=examples,
                            text=text )

def glossing_prompt(annotate_or_improve, simplified_elements_json, l1_language, l2_language):
    template, annotated_example_list = get_template_and_annotated_example_list(annotate_or_improve, 'gloss', l2_language)
    if annotate_or_improve == 'annotate':
        examples = glossing_examples_to_examples_text(annotated_example_list, l1_language, l2_language)
    else:
        examples = reglossing_examples_to_examples_text(annotated_example_list, l1_language, l2_language)
    return template.format( l1_language=l1_language,
                            l2_language=l2_language,
                            examples=examples,
                            simplified_elements_json=simplified_elements_json
                            )

# We only have 'improvement' for 'lemma_and_gloss'
def joint_tagging_and_glossing_prompt(simplified_elements_json, l1_language, l2_language):
    template, annotated_example_list = get_template_and_annotated_example_list('improve', 'lemma_and_gloss', l2_language)
    examples = re_lemma_and_glossing_examples_to_examples_text(annotated_example_list, l1_language, l2_language)
    return template.format( l1_language=l1_language,
                            l2_language=l2_language,
                            examples=examples,
                            simplified_elements_json=simplified_elements_json
                            )

def tagging_prompt(annotate_or_improve, simplified_elements_json, l2_language):
    l1_language = 'irrelevant'
    template, annotated_example_list = get_template_and_annotated_example_list(annotate_or_improve, 'lemma', l2_language)
    if annotate_or_improve == 'annotate':
        examples = tagging_examples_to_examples_text(annotated_example_list, l1_language, l2_language)
    else:
        examples = retagging_examples_to_examples_text(annotated_example_list, l1_language, l2_language)
    return template.format( l2_language=l2_language,
                            examples=examples,
                            simplified_elements_json=simplified_elements_json
                            )

def pinyin_tagging_prompt(annotate_or_improve, simplified_elements_json, l2_language):
    l1_language = 'irrelevant'
    template, annotated_example_list = get_template_and_annotated_example_list(annotate_or_improve, 'pinyin', l2_language)
    if annotate_or_improve == 'annotate':
        examples = pinyin_tagging_examples_to_examples_text(annotated_example_list, l1_language, l2_language)
    else:
        examples = pinyin_retagging_examples_to_examples_text(annotated_example_list, l1_language, l2_language)
    return template.format( l2_language=l2_language,
                            examples=examples,
                            simplified_elements_json=simplified_elements_json
                            )

def get_template_and_annotated_example_list(annotate_or_improve, annotation_type, l2_language):
    l2_language = l2_language.lower()
    try:
        return get_template_and_annotated_example_list_for_language(annotate_or_improve, annotation_type, l2_language)
    except TemplateError as e:
        if l2_language != 'default':
            print(f'--- Unable to find valid prompt template data for "{annotate_or_improve}", "{annotation_type}", "{l2_language}", using default')
            return get_template_and_annotated_example_list_for_language(annotate_or_improve, annotation_type, 'default')
        else:
            raise e

def get_template_and_annotated_example_list_for_language(annotate_or_improve, annotation_type, l2_language):
    prompt_repo = clara_prompt_templates.PromptTemplateRepository(l2_language)
    template = prompt_repo.load_template_or_examples('template', annotation_type, annotate_or_improve)
    annotated_example_list = prompt_repo.load_template_or_examples('examples', annotation_type, annotate_or_improve)
    clara_prompt_templates.check_validity_of_template_and_annotated_example_list(template, annotated_example_list, annotation_type)
    return ( template, annotated_example_list )

def segmentation_examples_to_text(examples):
    return '\n\n'.join([ segmentation_example_to_text(example) for example in examples ])

def segmentation_example_to_text(example):
    example_internalised = clara_internalise.internalize_text(example, 'l2_language', 'l1_language', 'segmented')
    elements = example_internalised.content_elements()
    plain_example = ''.join([ element.content for element in elements ])
    return f'{plain_example} ->\n{example}'

def glossing_examples_to_examples_text(examples_structure, l2_language, l1_language):
    return '\nor\n'.join([ glossing_example_to_example_text(example, l2_language, l1_language) for example in examples_structure ])

def reglossing_examples_to_examples_text(examples_structure, l2_language, l1_language):
    return '\nor\n'.join([ reglossing_example_to_example_text(example, l2_language, l1_language) for example in examples_structure ])

def re_lemma_and_glossing_examples_to_examples_text(examples_structure, l1_language, l2_language):
    return '\nor\n'.join([ re_lemma_and_glossing_example_to_example_text(example, l2_language, l1_language) for example in examples_structure ])

def glossing_example_to_example_text(example, l2_language, l1_language):
    simplified_internalised_example = annotated_string_to_simplified_internalised_form(example, l2_language, l1_language, 'gloss')
    simplified_internalised_example_words = [ pair[0] for pair in simplified_internalised_example ]
    return f'{json.dumps(simplified_internalised_example_words)} as {json.dumps(simplified_internalised_example)}'

def reglossing_example_to_example_text(example, l2_language, l1_language):
    ( first, second ) = example
    simplified_internalised_example1 = annotated_string_to_simplified_internalised_form(first, l2_language, l1_language, 'gloss')
    simplified_internalised_example2 = annotated_string_to_simplified_internalised_form(second, l2_language, l1_language, 'gloss')
    return f'{json.dumps(simplified_internalised_example1)} to {json.dumps(simplified_internalised_example2)}'

def re_lemma_and_glossing_example_to_example_text(example, l2_language, l1_language):
    ( first, second ) = example
    simplified_internalised_example1 = annotated_string_to_simplified_internalised_form(first, l2_language, l1_language, 'lemma_and_gloss')
    simplified_internalised_example2 = annotated_string_to_simplified_internalised_form(second, l2_language, l1_language, 'lemma_and_gloss')
    return f'{json.dumps(simplified_internalised_example1)} to {json.dumps(simplified_internalised_example2)}'

def tagging_examples_to_examples_text(examples_structure, l2_language, l1_language):
    return '\nor\n'.join([ tagging_example_to_example_text(example, l2_language, l1_language) for example in examples_structure ])

def retagging_examples_to_examples_text(examples_structure, l2_language, l1_language):
    return '\nor\n'.join([ retagging_example_to_example_text(example, l2_language, l1_language) for example in examples_structure ])

def pinyin_tagging_examples_to_examples_text(examples_structure, l2_language, l1_language):
    return '\nor\n'.join([ pinyin_tagging_example_to_example_text(example, l2_language, l1_language) for example in examples_structure ])

def pinyin_retagging_examples_to_examples_text(examples_structure, l2_language, l1_language):
    return '\nor\n'.join([ pinyin_retagging_example_to_example_text(example, l2_language, l1_language) for example in examples_structure ])

def tagging_example_to_example_text(example, l2_language, l1_language):
    simplified_internalised_example = annotated_string_to_simplified_internalised_form(example, l2_language, l1_language, 'lemma')
    simplified_internalised_example_words = [ pair[0] for pair in simplified_internalised_example ]
    return f'{json.dumps(simplified_internalised_example_words)} as {json.dumps(simplified_internalised_example)}'

def retagging_example_to_example_text(example, l2_language, l1_language):
    ( first, second ) = example
    simplified_internalised_example1 = annotated_string_to_simplified_internalised_form(first, l2_language, l1_language, 'lemma')
    simplified_internalised_example2 = annotated_string_to_simplified_internalised_form(second, l2_language, l1_language, 'lemma')
    return f'{json.dumps(simplified_internalised_example1)} to {json.dumps(simplified_internalised_example2)}'

def pinyin_tagging_example_to_example_text(example, l2_language, l1_language):
    simplified_internalised_example = annotated_string_to_simplified_internalised_form(example, l2_language, l1_language, 'pinyin')
    simplified_internalised_example_words = [ pair[0] for pair in simplified_internalised_example ]
    return f'{json.dumps(simplified_internalised_example_words)} as {json.dumps(simplified_internalised_example)}'

def pinyin_retagging_example_to_example_text(example, l2_language, l1_language):
    ( first, second ) = example
    simplified_internalised_example1 = annotated_string_to_simplified_internalised_form(first, l2_language, l1_language, 'pinyin')
    simplified_internalised_example2 = annotated_string_to_simplified_internalised_form(second, l2_language, l1_language, 'pinyin')
    return f'{json.dumps(simplified_internalised_example1)} to {json.dumps(simplified_internalised_example2)}'

def annotated_string_to_simplified_internalised_form(example, l2_language, l1_language, gloss_or_lemma_or_pinyin):
    internalised_example = clara_internalise.internalize_text(example, l2_language, l1_language, gloss_or_lemma_or_pinyin)
    elements = internalised_example.content_elements()
    simplified_elements0 = [ simplify_element_to_list(element, gloss_or_lemma_or_pinyin) for element in elements ]
    return [ element for element in simplified_elements0 if element != False ]

def simplify_element_to_string(element):
    content = element.content
    # Return Words as they are
    if element.type == 'Word':
        return content
    # Return NonWordText with the whitespace stripped off, if it's not all whitespace
    elif not content.isspace():
        return content.strip()
    # Discard whitespace strings
    else:
        return False

def simplify_element_to_list(element, gloss_or_lemma_or_pinyin):
    content = element.content
    annotation = element.annotations[gloss_or_lemma_or_pinyin] if gloss_or_lemma_or_pinyin in element.annotations else 'NO_ANNOTATION'
    gloss = element.annotations['gloss'] if 'gloss' in element.annotations else 'NO_GLOSS'
    lemma = element.annotations['lemma'] if 'lemma' in element.annotations else 'NO_LEMMA'
    pos = element.annotations['pos'] if 'pos' in element.annotations else 'NO_POS'
    pinyin = element.annotations['pinyin'] if 'pinyin' in element.annotations else 'NO_PINYIN'
    # Return Words as they are
    if element.type == 'Word':
        if gloss_or_lemma_or_pinyin == 'gloss':
            return [ content, gloss ]
        elif gloss_or_lemma_or_pinyin == 'lemma':
            return [ content, lemma, pos ]
        elif gloss_or_lemma_or_pinyin == 'pinyin':
            return [ content, pinyin ]
        else:
            return [ content, lemma, pos, gloss ]
            
    # Return NonWordText with the whitespace stripped off, if it's not all whitespace
    elif not content.isspace():
        content = content.strip()
        if gloss_or_lemma_or_pinyin == 'gloss':
            return [ content, content ]
        elif gloss_or_lemma_or_pinyin == 'pinyin':
            return [ content, content ]
        elif gloss_or_lemma_or_pinyin == 'lemma':
            return [ content, content, 'PUNC' ]
        else:
            return [ content, content, 'PUNC', content ]
    # Discard whitespace strings
    else:
        return False

# element is
#     a two-item list consisting of content and annotation (gloss)
#     a three-item list consisting of content, annotation and pos (lemma)
#     a four-item list consisting of content, lemma, pos and gloss (lemma_and_gloss)
# Return a ContentElement object with the content and annotation in the right places.
def unsimplify_element(element, gloss_or_lemma_or_pinyin):
    if gloss_or_lemma_or_pinyin in ( 'gloss', 'pinyin' ) and len(element) == 2:
        content, annotation = element
        # String only consists of punctuation marks
        if all(regex.match(r"\p{P}", c) for c in content):
            return ContentElement("NonWordText", content)
        # String is an HTML tag
        elif regex.match(r"<\/?\w+>", content):
            return ContentElement("Markup", content)
        else:
            return ContentElement("Word", content, annotations={ gloss_or_lemma_or_pinyin: annotation })
    elif gloss_or_lemma_or_pinyin == 'lemma' and len(element) == 3:
        content, lemma, pos = element
        # String only consists of punctuation marks
        if all(regex.match(r"\p{P}", c) for c in content):
            return ContentElement("NonWordText", content)
        # String is an HTML tag
        elif regex.match(r"<\/?\w+>", content):
            return ContentElement("Markup", content)
        else:
            return ContentElement("Word", content, annotations={ 'lemma': lemma, 'pos': pos })
    elif gloss_or_lemma_or_pinyin == 'lemma_and_gloss' and len(element) == 4:
        content, lemma, pos, gloss = element
        # String only consists of punctuation marks
        if all(regex.match(r"\p{P}", c) for c in content):
            return ContentElement("NonWordText", content)
        # String is an HTML tag
        elif regex.match(r"<\/?\w+>", content):
            return ContentElement("Markup", content)
        else:
            return ContentElement("Word", content, annotations={ 'lemma': lemma, 'pos': pos, 'gloss': gloss })
    else:
        raise InternalCLARAError(message = f'Bad call: unsimplify_element({element}, {gloss_or_lemma_or_pinyin})')

def parse_chatgpt_gloss_response(response, simplified_elements, gloss_or_lemma_or_pinyin, callback=None):
##    try:
##        response_object = json.loads(response)
##    except:
##        try:
##            response_object = extract_json_list_from_response_string_ignoring_wrappers(response, callback=callback)
##        except:
##            raise ChatGPTError(message = f'Response is not correctly formatted JSON: {response}')
    response_object = clara_chatgpt4.interpret_chat_gpt4_response_as_json(response, object_type='list', callback=callback)
    if not isinstance(response_object, list):
        raise ChatGPTError(message = f'Response is not a list: {response}')
    
    usable_response_object = []
    for element in response_object:
        if not well_formed_element_in_glossing_or_tagging_or_pinyin_response(element, gloss_or_lemma_or_pinyin):
            print(f'*** Warning: bad element {element} in annotation response, discarding')
        else:
            usable_response_object += [ element ]
    original_text = ' '.join([ element if isinstance(element, str) else element[0] for element in simplified_elements ])
    annotated_text = ' '.join([ element[0] for element in usable_response_object ])
    if not original_text == annotated_text:
        warning = f"""*** Warning: original text and annotated text are different.
 Original text: {original_text}
Annotated text: {annotated_text}"""
        post_task_update(callback, warning)
    return usable_response_object

def simplified_element_list_to_text(simplified_elements):
    return ' '.join([ element if isinstance(element, str) else element[0]
                      for element in simplified_elements ])

def well_formed_element_in_glossing_or_tagging_or_pinyin_response(element, gloss_or_lemma_or_pinyin):
    if gloss_or_lemma_or_pinyin in ( 'gloss', 'pinyin' ):
        return isinstance(element, list) and len(element) == 2
    elif gloss_or_lemma_or_pinyin == 'lemma':
        return isinstance(element, list) and len(element) == 3
    elif gloss_or_lemma_or_pinyin == 'lemma_and_gloss':
        return isinstance(element, list) and len(element) == 4

