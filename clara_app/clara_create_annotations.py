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

from .clara_merge_glossed_and_tagged import merge_annotations_charwise
from .clara_mwe import find_mwe_positions_for_content_elements, find_mwe_positions_for_content_string_list, check_mwes_are_consistently_annotated
from .clara_utils import get_config, post_task_update, post_task_update_async, is_list_of_lists_of_strings, find_between_tags
from .clara_classes import *

import asyncio
import json
import re
import regex
import difflib
import traceback
import copy
import pprint
import unicodedata

from typing import Any, Dict, List, Tuple

config = get_config()

ASYNC = True

# Try invoking the template-based prompt generation with trivial text to see if we get an error
def invoke_templates_on_trivial_text(annotate_or_improve, version, l1_language, l2_language):
    if not version in ( 'presegmented', 'segmented', 'gloss', 'lemma', 'pinyin', 'lemma_and_gloss' ):
        return True
    if version == 'segmented':
        text = ''
        return segmentation_prompt(annotate_or_improve, text, l2_language)
    if version == 'presegmented':
        text = ''
        return presegmentation_prompt(annotate_or_improve, text, l2_language)
    if version == 'gloss':
        simplified_elements_json = []
        return glossing_prompt(annotate_or_improve, simplified_elements_json, l1_language, l2_language)
    if version == 'lemma':
        simplified_elements_json = []
        return tagging_prompt(annotate_or_improve, simplified_elements_json, l2_language)
    if version == 'mwe':
        simplified_elements_json = []
        return mwe_prompt(annotate_or_improve, simplified_elements_json, l2_language)
    if version == 'pinyin':
        simplified_elements_json = []
        return pinyin_tagging_prompt(annotate_or_improve, simplified_elements_json, l2_language)
    if version == 'lemma_and_gloss':
        simplified_elements_json = []
        return joint_tagging_and_glossing_prompt(simplified_elements_json, l1_language, l2_language)
    
# Annotate the text with pages and segments
def generate_segmented_version(text, l2_language, text_type=None, config_info={}, callback=None):
    #return generate_or_improve_segmented_version('annotate', text, l2_language, config_info=config_info, callback=callback)
    return generate_or_improve_segmented_version_two_phase('annotate', text, l2_language, text_type=text_type, config_info=config_info, callback=callback)

# Improve annotation of the text with pages and segments
def improve_segmented_version(text, l2_language, text_type=None, config_info={}, callback=None):
    #return generate_or_improve_segmented_version('improve', text, l2_language, config_info=config_info, callback=callback)
    return generate_or_improve_segmented_version_two_phase('improve', text, l2_language, text_type=text_type, config_info=config_info, callback=callback)

# Improve annotation of the text with pages and segments
def improve_morphology_in_segmented_version(text, l2_language, config_info={}, callback=None):
    return generate_or_improve_annotated_version('annotate', 'segmented', segmented_text, l1_language, l2_language,
                                                 previous_version='segmented', 
                                                 config_info=config_info, callback=callback)

# Annotate the text with glosses
def generate_glossed_version(segmented_text, l1_language, l2_language, previous_version='segmented_with_images', mwe=False,
                             current_glossed_text=None, current_translated_text=None, config_info={}, callback=None):
    return generate_or_improve_annotated_version('annotate', 'gloss', segmented_text, l1_language, l2_language,
                                                 previous_version=previous_version, mwe=mwe,
                                                 current_annotated_text=current_glossed_text,
                                                 current_translated_text=current_translated_text,
                                                 config_info=config_info, callback=callback)

# Annotate the text with translations
def generate_translated_version(segmented_text, l2_language, l1_language, config_info={}, callback=None):
    return generate_or_improve_annotated_version('annotate', 'translated', segmented_text, l1_language, l2_language, config_info=config_info, callback=callback)

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
def generate_tagged_version(segmented_text, l2_language, mwe=False,
                            current_lemma_tagged_text=None, config_info={}, callback=None):
    l1_language = 'irrelevant'
    return generate_or_improve_annotated_version('annotate', 'lemma', segmented_text, l1_language, l2_language,
                                                 mwe=mwe, current_annotated_text=current_lemma_tagged_text,
                                                 config_info=config_info, callback=callback)

# Improve annotation of the text with lemmas
def improve_tagged_version(tagged_text, l2_language, config_info={}, callback=None):
    l1_language = 'irrelevant'
    return generate_or_improve_annotated_version('improve', 'lemma', tagged_text, l1_language, l2_language, config_info=config_info, callback=callback)

# Annotate the text with MWEs
def generate_mwe_tagged_version(segmented_text, l2_language,
                                current_mwe_tagged_text=None, config_info={}, callback=None):
    l1_language = 'irrelevant'
    return generate_or_improve_annotated_version('annotate', 'mwe', segmented_text, l1_language, l2_language,
                                                 current_annotated_text=current_mwe_tagged_text, config_info=config_info, callback=callback)


# Improve annotation of the text with lemmas and glosses
def improve_lemma_and_gloss_tagged_version(tagged_text, l1_language, l2_language, config_info={}, callback=None):
    return generate_or_improve_annotated_version('improve', 'lemma_and_gloss', tagged_text, l1_language, l2_language, config_info=config_info, callback=callback)

def generate_or_improve_segmented_version(annotate_or_improve, text, l2_language, config_info={}, callback=None):
    l2_language = l2_language.capitalize()
    annotate_prompt =  segmentation_prompt(annotate_or_improve, text, l2_language)
    api_call = clara_chatgpt4.call_chat_gpt4(annotate_prompt, config_info=config_info, callback=callback)
    return ( api_call.response, [ api_call ] )

def generate_or_improve_segmented_version_two_phase(annotate_or_improve, text, l2_language,
                                                    text_type=None, config_info={}, callback=None):
    trace_segmentation_two_phase = False
    #trace_segmentation_two_phase = True
    
    if annotate_or_improve != 'annotate':
        raise ValueError('Improvement of segmented text not currently supported')
    all_api_calls = []
    l1_language = 'irrelevant'
    l2_language = l2_language.capitalize()
    
    if len(text.split('\n')) < 2 and len(text) < 100:
        #If we only have one shortish line, the AI may be confused by a presegmentation request              
        presegmented_text = text
    else:
        presegment_prompt =  presegmentation_prompt(annotate_or_improve, text, l2_language, text_type=text_type)

        if trace_segmentation_two_phase:
            print('presegment_prompt:')
            print(f"""{presegment_prompt}""")
            
        n_attempts = 0
        valid_presegmentation_found = False
        limit = int(config.get('chatgpt4_annotation', 'retry_limit'))
        while not valid_presegmentation_found:
            if n_attempts >= limit:
                raise ChatGPTError( message=f'*** Giving up, have tried sending this to AI {limit} times' )
            n_attempts += 1
            post_task_update(callback, f'--- Calling AI (attempt #{n_attempts}) to presegment text')
            try:
                presegment_api_call = clara_chatgpt4.call_chat_gpt4(presegment_prompt, config_info=config_info, callback=callback)
                presegmented_text0 = presegment_api_call.response

                if trace_segmentation_two_phase:
                   print('Raw presegmented_text:')
                   print(f"""{presegmented_text0}""") 
                        
                # The template should tell the AI to return the answer enclosed between the tags "<startoftext>", "<endoftext>",
                # but sometimes these don't come out quite right
                presegmented_text = find_between_tags(presegmented_text0, "text", "text")

                preseg_s = sanitize_preseg(presegmented_text)

                valid_presegmentation_found, ratio = is_preseg_close_enough(text, preseg_s, rel_tol=0.01, abs_tol=15)
                if valid_presegmentation_found:
                    presegmented_text = preseg_s

                all_api_calls.append(presegment_api_call)
                        
            except ValueError as e:
                post_task_update(callback, f'*** Warning: error when performing presegmentation')
                error_message = f'"{str(e)}"'
                post_task_update(callback, error_message)
            except Exception as e:
                post_task_update(callback, f'*** Warning: error when performing presegmentation')
                error_message = f'"{str(e)}"\n{traceback.format_exc()}'
                post_task_update(callback, error_message)

    segmented_text, segmented_api_calls = generate_or_improve_annotated_version('annotate', 'segmented', presegmented_text, l1_language, l2_language,
                                                                                previous_version='presegmented', config_info=config_info, callback=callback)
    segmented_text = clean_up_segment_breaks_in_text(segmented_text)

    segmented_text = remove_empty_pages(segmented_text)
    
    all_api_calls.extend(segmented_api_calls)
    return ( segmented_text, all_api_calls )

# Checking whether presegmentation is acceptable

_PAGE = "<page>"
_SEG  = "||"

def _unicode_simplify(s: str) -> str:
    """NFKC + normalise common punctuation/whitespace variants."""
    s = unicodedata.normalize("NFKC", s)
    # Map curly quotes & nbspace to simple forms
    s = s.replace("\u00A0", " ")
    s = s.replace("’", "'").replace("“", '"').replace("”", '"')
    return s

def sanitize_preseg(preseg: str) -> str:
    """
    - Keep <page> and '||'
    - Remove stray single '|' and any '@' tokens (from later stages)
    - Tidy spacing around markers (optional)
    """
    s = _unicode_simplify(preseg)

    # Remove single pipes that aren't part of '||'
    s = re.sub(r"(?<!\|)\|(?!\|)", "", s)

    # Drop any stray '@' (morph tags belong to segmentation, not preseg)
    s = s.replace("@", "")

    # Optional: normalise spaces around markers (not required, but nice)
    s = re.sub(r"\s*<page>\s*", f"\n{_PAGE}\n", s)   # put pages on their own line
    s = re.sub(r"\s*\|\|\s*", f" {_SEG} ", s)       # space-pad segments

    return s

def _canon_for_compare(s: str) -> str:
    """
    Build a comparison string that ignores *all* whitespace and our markup.
    We also ignore single '|' just in case.
    """
    s = _unicode_simplify(s)
    s = s.replace(_PAGE, "").replace(_SEG, "")
    s = s.replace("|", "")  # any remaining single pipes
    s = s.replace("@", "")  # any stray morph marker
    # remove all whitespace
    s = re.sub(r"\s+", "", s)
    return s

def is_preseg_close_enough(original: str, preseg: str,
                           rel_tol: float = 0.01, abs_tol: int = 15) -> tuple[bool, float]:
    """
    Return (ok, ratio). Uses difflib ratio on canonicalised strings and
    also enforces an absolute edit budget via opcodes.
    rel_tol ≈ allowed relative edits (1%); abs_tol ≈ minimum absolute slack.
    """
    a = _canon_for_compare(original)
    b = _canon_for_compare(preseg)

    # Quick path: identical canon
    if a == b:
        return True, 1.0

    # Compute rough absolute diff count via opcodes
    sm = difflib.SequenceMatcher(None, a, b)
    edits = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        # Count the larger side as the “edit mass”
        edits += max(i2 - i1, j2 - j1)

    budget = max(abs_tol, int(rel_tol * max(len(a), 1)))
    ratio  = sm.ratio()

    ok = edits <= budget
    return ok, ratio

def clean_up_segment_breaks_in_text(text: str) -> str:
    text1 = add_segment_break_before_page(text)
    return move_segment_break_before_line_break(text1)

def add_segment_break_before_page(text: str) -> str:
    """
    Insert '||' before <page> whenever <page> is preceded by whitespace
    that does not already have '||' immediately before it.

    Args:
        text (str): The input text to process.

    Returns:
        str: The processed text with '||' inserted appropriately.
    """
    # Pattern to match one or more whitespace characters followed by '<page>'
    pattern = r'([ \t\r\n]+)(<page>)'
    
    # Find all matches of the pattern in the text
    matches = list(re.finditer(pattern, text))
    
    # Process matches from end to start to avoid index shifting
    for match in reversed(matches):
        start, end = match.span()
        whitespace = match.group(1)
        page_tag = match.group(2)
        
        # Determine the position just before the whitespace starts
        preceding_text_end = start
        preceding_text_start = max(start - 2, 0)  # Ensure we don't go below index 0
        preceding_text = text[preceding_text_start:preceding_text_end]
        
        # Check if '||' is immediately before the whitespace
        if preceding_text.endswith('||'):
            # '||' is already present; do nothing
            continue
        else:
            # Insert '||' before the whitespace
            # This preserves existing whitespace and adds '||' before it
            insertion = '||' + whitespace
            text = text[:start] + insertion + page_tag + text[end:]
    
    return text

def move_segment_break_before_line_break(text: str) -> str:
    return text.replace('\n||', '||\n')

_EMPTY_PAGE_RE = re.compile(r'^(?:\s+|\|\|)+$')  # only whitespace and/or ||

def remove_empty_pages(preseg_text: str) -> str:
    """
    Drop pages that contain no actual content (only whitespace and/or '||').
    Reconstructs the text with <page> prefixes for the remaining pages.
    """
    # Split on <page>. If the string starts with <page>, the first chunk is ''.
    chunks = re.split(r'<page>', preseg_text)
    keep = []
    for chunk in chunks:
        # Keep pages that are not empty
        if chunk and not _EMPTY_PAGE_RE.match(chunk):
            keep.append(chunk)

    if not keep:
        # Nothing left—return original (or raise). Safer to return original.
        return preseg_text

    return ''.join('<page>' + c for c in keep)

def generate_or_improve_annotated_version(annotate_or_improve, processing_phase, annotated_text, l1_language, l2_language,
                                          previous_version='default', mwe=False,
                                          current_annotated_text=None, current_translated_text=None,
                                          config_info={}, callback=None):

    print(f"""generate_or_improve_annotated_version({annotate_or_improve}, {processing_phase}, {annotated_text}, {l1_language}, {l2_language},
                                          previous_version={previous_version}, mwe={mwe},
                                          current_annotated_text={current_annotated_text}, current_translated_text={current_translated_text},
                                          config_info={config_info}, callback=callback)
""")

    if previous_version == 'presegmented':
        source_version = 'presegmented'
    elif previous_version == 'lemma':
        source_version = 'lemma'
    elif mwe:
        source_version = 'mwe'
    elif annotate_or_improve == 'annotate':
        source_version = 'segmented'
    else:
        source_version = processing_phase
    l1_language = l1_language.capitalize()
    l2_language = l2_language.capitalize()
    
    if processing_phase == 'segmented' and previous_version == 'segmented':
        internalised_annotated_text = clara_internalise.internalize_text(annotated_text, l2_language, l1_language, 'plain')
    else:
        internalised_annotated_text = clara_internalise.internalize_text(annotated_text, l2_language, l1_language, source_version)

    print(f'Internalised "{annotated_text}" as "{source_version}":')
    pprint.pprint(internalised_annotated_text)

    if processing_phase == 'gloss':
        context = internalised_annotated_text.to_text(annotation_type='plain')
    else:
        context = None
        
    if current_annotated_text and annotate_or_improve == 'annotate' and processing_phase == 'gloss':
        internalised_current_annotated_text = clara_internalise.internalize_text(current_annotated_text, l2_language, l1_language, 'gloss')
    elif current_annotated_text and annotate_or_improve == 'annotate' and processing_phase == 'lemma':
        internalised_current_annotated_text = clara_internalise.internalize_text(current_annotated_text, l2_language, l1_language, 'lemma')
    elif current_annotated_text and annotate_or_improve == 'annotate' and processing_phase == 'mwe':
        internalised_current_annotated_text = clara_internalise.internalize_text(current_annotated_text, l2_language, l1_language, 'mwe')
    elif current_annotated_text and annotate_or_improve == 'annotate' and processing_phase == 'translated':
        internalised_current_annotated_text = clara_internalise.internalize_text(current_annotated_text, l2_language, l1_language, 'translated')
    elif processing_phase == 'segmented' and previous_version == 'segmented':
        internalised_current_annotated_text = clara_internalise.internalize_text(current_annotated_text, l2_language, l1_language, 'plain')
    else:
        internalised_current_annotated_text = None

    # Use max_annotation_words from config_info if available, otherwise default to a preset value
    if 'max_annotation_words' in config_info:
        max_elements = config_info['max_annotation_words']
    else:
        max_elements = int(config.get('chatgpt4_annotation', 'max_elements_to_annotate'))

    # segmented_elements is a list of lists of elements, each one corresponding to a segment in the internalised text
    segmented_elements = internalised_annotated_text.segmented_elements()

    # Annotate each chunk separately and store the results in the annotated_elements list
    annotated_elements = []
    # If we are doing MWE tagging or translation, we are returning annotations for each segment
    annotations_for_segments = []
    all_api_calls = []

    segmented_elements_mwe_dict = None
    segmented_elements_translations_dict = None
    segments = internalised_annotated_text.segments()
    
    if mwe:
        segmented_elements_mwe_dict = segments_to_segmented_elements_mwe_dict(segments)

    if processing_phase == 'translated':
        segmented_elements_translations_dict = segments_to_translations_dict(segments)
    elif processing_phase == 'gloss' and mwe and current_translated_text:
        internalised_translated_text = clara_internalise.internalize_text(current_translated_text, l2_language, l1_language, 'translated')
        translated_segments = internalised_translated_text.segments()
        segmented_elements_translations_dict = segments_to_translations_dict(translated_segments)

    #print(f'segmented_elements_translations_dict: {segmented_elements_translations_dict}')

    if internalised_current_annotated_text:
        if mwe or processing_phase in ( 'mwe', 'translated' ):
            current_segments = internalised_current_annotated_text.segments()
            current_segmented_elements_dict = segments_to_annotations_dict(current_segments)
        elif processing_phase == 'segmented' and previous_version == 'segmented':
            current_segmented_elements_dict = None
        else:
            current_segmented_elements = internalised_current_annotated_text.segmented_elements() if internalised_current_annotated_text else None
            current_segmented_elements_dict = segmented_elements_to_dict(current_segmented_elements)
    else:
        current_segmented_elements_dict = None
   
    if processing_phase == 'mwe' or mwe or ( processing_phase == 'gloss' and previous_version == 'lemma' ) or \
       processing_phase == 'segmented' and previous_version in ( 'presegmented', 'segmented'):
        # Do tagging involving MWEs, gloss-from-lemma, segmentation and morphology improvement one segment at a time
        chunks = segmented_elements
        process_segments_singly = True
    elif processing_phase == 'translated':
        chunks = [ [ segment ] for segment in segmented_elements ]
        process_segments_singly = False
    else:
        #chunks = split_elements_by_segments(segmented_elements, max_elements, processing_phase)
        #process_segments_singly = False
        # Try always splitting elements by segments, since it seems to be the better strategy and isn't really very expensive
        chunks = segmented_elements
        process_segments_singly = True

    annotations_for_segments, annotated_elements, all_api_calls = call_process_annotations_async(chunks, process_segments_singly,
                                                                                                 segmented_elements_mwe_dict, segmented_elements_translations_dict,
                                                                                                 annotate_or_improve, processing_phase, l1_language, l2_language,
                                                                                                 previous_version, mwe,
                                                                                                 context=context, config_info=config_info, callback=callback)

##    print(f'annotations_for_segments')
##    pprint.pprint(annotations_for_segments)
##
##    print(f'annotated_elements')
##    pprint.pprint(annotated_elements)
    
    # Reassemble the annotated elements back into the segmented_text structure
    index = 0
    #print(f'annotations_for_segments = {annotations_for_segments}')
    for page in internalised_annotated_text.pages:
        for segment in page.segments:
            # If we are doing segmentation, the "annotations" are the segmented_text
            if processing_phase == 'segmented':
                segmented_text = annotations_for_segments[index]
                segment.content_elements = clara_internalise.parse_segment_text(segmented_text, 'segmented').content_elements
                #segment.content_elements = [ ContentElement('Word', segmented_text) ]
                index += 1
            # If we are doing MWE, add the annotations to the segment
            elif processing_phase == 'mwe':
                segment.annotations = annotations_for_segments[index]
                index += 1
##            # If we are doing segment translation, add the annotations to the segment
##            # but only if the translation input was non-null, since we are discarding the null inputs
##            elif processing_phase == 'translated':
##                if segment_elements_to_segment_translation_input(segment.content_elements):
##                    segment.annotations = annotations_for_segments[index]
##                    index += 1
            elif processing_phase == 'translated':
                segment.annotations = annotations_for_segments[index]
                index += 1
            # Otherwise, we replace elements with annotated elements
            else:
                n_elements_in_segment = len(segment.content_elements)
                segment.content_elements = annotated_elements[index:index+n_elements_in_segment]
                index += n_elements_in_segment

    #print(f'internalised_annotated_text: {internalised_annotated_text}')

    #processing_phase1 = 'presegmented' if processing_phase == 'segmented' else processing_phase
    #human_readable_text = internalised_annotated_text.to_text(annotation_type=processing_phase1)
    human_readable_text = internalised_annotated_text.to_text(annotation_type=processing_phase)
    
    return ( human_readable_text, all_api_calls )

def call_process_annotations_async(chunks, process_segments_singly,
                                   segmented_elements_mwe_dict, segmented_elements_translations_dict,
                                   annotate_or_improve, processing_phase, l1_language, l2_language,
                                   previous_version, mwe,
                                   context=None, config_info={}, callback=None):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # No event loop running
        loop = None

    if loop and loop.is_running():
        # If we're already in an event loop, we should use `await` directly
        return asyncio.ensure_future(process_annotations_async(chunks, process_segments_singly,
                                                               segmented_elements_mwe_dict, segmented_elements_translations_dict,
                                                               annotate_or_improve, processing_phase, l1_language, l2_language,
                                                               previous_version, mwe,
                                                               context=context, config_info=config_info, callback=callback))
    else:
        # If not in an event loop, we can use asyncio.run
        return asyncio.run(process_annotations_async(chunks, process_segments_singly,
                                                     segmented_elements_mwe_dict, segmented_elements_translations_dict,
                                                     annotate_or_improve, processing_phase, l1_language, l2_language,
                                                     previous_version, mwe,
                                                     context=context, config_info=config_info, callback=callback))
    
async def process_annotations_async(chunks, process_segments_singly, segmented_elements_mwe_dict,
                                    segmented_elements_translations_dict, annotate_or_improve, processing_phase,
                                    l1_language, l2_language, previous_version, mwe,
                                    context=None, config_info={}, callback=None):
    
    max_chunks_to_annotate_in_parallel = int(config.get('chatgpt4_annotation', 'max_chunks_to_annotate_in_parallel'))

    results = []
    while chunks:
        initial_chunks = chunks[:max_chunks_to_annotate_in_parallel]
        chunks = chunks[max_chunks_to_annotate_in_parallel:]
    
        tasks = []
        for chunk in initial_chunks:
            if process_segments_singly:
                key = key_for_segment_elements(chunk)
                mwes_for_segment = segmented_elements_mwe_dict[key] if segmented_elements_mwe_dict and key in segmented_elements_mwe_dict else []
                translation_for_segment = segmented_elements_translations_dict[key] if segmented_elements_translations_dict and key in segmented_elements_translations_dict else None
            else:
                mwes_for_segment = []
                translation_for_segment = None
            
            tasks.append(asyncio.create_task(
                call_chatgpt4_to_annotate_or_improve_elements_async(annotate_or_improve, processing_phase, chunk,
                                                                    l1_language, l2_language, previous_version,
                                                                    mwe, mwes_for_segment, translation_for_segment,
                                                                    context=context, config_info=config_info, callback=callback)
            ))

        await post_task_update_async(callback, f'--- Running {len(tasks)} async tasks')
        initial_results = await asyncio.gather(*tasks)

        results += initial_results

        print(f'{len(initial_results)} new results for async tasks, {len(results)} results total')
        
    all_api_calls = []
    annotations_for_segments = []
    annotated_elements = []

    for result in results:
        annotated_chunk_or_segment_annotation, api_calls = result
        if processing_phase == 'segmented' and previous_version == 'presegmented':
            annotations_for_segments.append(annotated_chunk_or_segment_annotation)
        elif processing_phase == 'mwe':
            annotations_for_segments.append(annotated_chunk_or_segment_annotation)
        elif processing_phase == 'translated':
            annotations_for_segments += annotated_chunk_or_segment_annotation
        else:
            annotated_elements += annotated_chunk_or_segment_annotation
        all_api_calls += api_calls

    #print(f'process_annotations_async: total cost = {sum([ api_call.cost for api_call in all_api_calls ])}')
    return annotations_for_segments, annotated_elements, all_api_calls

# We index on tuples consisting of the content of each element.
# Typically we have not more than a hundred segments in a text and a few dozen content elements in a segment, so this is acceptably efficient
def key_for_segment_elements(elements):
    return tuple([ element.content for element in elements ])

# Index MWEs on the key given above
def segments_to_segmented_elements_mwe_dict(segments):
    return { key_for_segment_elements(segment.content_elements): ( segment.annotations['mwes'] if 'mwes' in segment.annotations else [] )
             for segment in segments }

# Index translations on the key given above
def segments_to_translations_dict(segments):
    return { key_for_segment_elements(segment.content_elements): ( segment.annotations['translated'] if 'translated' in segment.annotations else None )
             for segment in segments }

# Index a list of segmented elements on the key given above
def segmented_elements_to_dict(segmented_elements):
    if not segmented_elements:
        return None
    
    return { key_for_segment_elements(elements): elements for elements in segmented_elements }

# Index annotations for segmented elements on the key given above
def segments_to_annotations_dict(segments):
    if not segments:
        return None
    
    return { key_for_segment_elements(segment.content_elements): segment.annotations for segment in segments }

### Find how many segments aren't in the previous version and compare with the limit
##def few_enough_segments_changed_to_use_saved_annotations(segmented_elements, current_segmented_elements_dict, processing_phase, mwe, config_info):
##    if not current_segmented_elements_dict:
##        return False
##
##    # If MWE tagging is involved, we do it one segment at a time, so always reuse saved annotations if possible
##    if processing_phase == 'mwe' or mwe:
##        return True
##    
##    limit = int(config.get('chatgpt4_annotation', 'max_segments_to_reannotate_separately'))
##    new_segments = [ key_for_segment_elements(elements) for elements in segmented_elements
##                     if not key_for_segment_elements(elements) in current_segmented_elements_dict \
##                     and len(word_items_in_element_list(elements)) > 0 ]
##    #print(f'--- Limit = {limit}. {len(new_segments)} new segments:')
##    #pprint.pprint(new_segments)
##    return len(new_segments) <= limit

def word_and_non_word_text_items_in_element_list(elements):
    return [ element for element in elements if element.type in ( 'Word', 'NonWordText' ) ]

def word_items_in_element_list(elements):
    word_items = []
    for element in elements:
        if isinstance(element, ( list, tuple )):
            word_items.extend(word_items_in_element_list(element))
        elif element.type in ( 'Word' ):
            word_items.append(element)
                              
    return word_items

def split_elements_by_segments(segmented_elements, max_elements, processing_phase):
    chunks = []
    current_chunk = []
    current_count = 0

    for segment0 in segmented_elements:
        segment = copy.copy(segment0)   # Copy the segment, since we don't want to modify it in the 'extend' line
        segment_length = len(segment)
        if current_count + segment_length > max_elements:
            if current_chunk:  # if the current chunk is not empty, push it to chunks
                chunks.append(current_chunk)
                current_chunk = []
                current_count = 0
            # If a single segment is larger than max_elements, split it using the stupid method
            # Keeping it unsplit can easily confuse GPT-4
            if segment_length > max_elements and processing_phase != 'translated':
                #chunks.append(segment)
                split_segment = [segment[i:i + max_elements] for i in range(0, segment_length, max_elements)]
                chunks += split_segment
            else:
                current_chunk = segment if processing_phase != 'translated' else [ segment ]
                current_count = segment_length
        else:
            if processing_phase == 'translated':
                current_chunk.append(segment)
            else:
                current_chunk.extend(segment)
            current_count += segment_length

    if current_chunk:  # Don't forget to add the last chunk if it exists
        chunks.append(current_chunk)

    return chunks

def call_chatgpt4_to_annotate_or_improve_elements(annotate_or_improve, processing_phase, elements,
                                                  l1_language, l2_language,
                                                  previous_version='default',
                                                  mwe=False, mwes=[], translation=None,
                                                  context=None, config_info={}, callback=None):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # No event loop running
        loop = None

    if loop and loop.is_running():
        # If we're already in an event loop, we should use `await` directly
        return asyncio.ensure_future(call_chatgpt4_to_annotate_or_improve_elements_async(
            annotate_or_improve, processing_phase, elements,
            l1_language, l2_language,
            previous_version, mwe, mwes, translation,
            context=context, config_info=config_info, callback=callback
        ))
    else:
        # If not in an event loop, we can use asyncio.run
        return asyncio.run(call_chatgpt4_to_annotate_or_improve_elements_async(
            annotate_or_improve, processing_phase, elements,
            l1_language, l2_language,
            previous_version, mwe, mwes, translation,
            context=context, config_info=config_info, callback=callback
        ))


async def call_chatgpt4_to_annotate_or_improve_elements_async(annotate_or_improve, processing_phase, elements,
                                                              l1_language, l2_language,
                                                              previous_version='default',
                                                              mwe=False, mwes=[], translation=None,
                                                              few_shot_examples=[],
                                                              context=None,
                                                              config_info={},
                                                              always_succeed=False,
                                                              callback=None):
    word_elements = word_items_in_element_list(elements)
    n_words = len(word_elements)
    # If there are no words in the input, handle specially to avoid making an AI call
    if n_words == 0:
        # If we're doing MWE, return empty list
        if processing_phase == 'mwe':
            return ( [], [] )
        # If we're doing segmentation, return the surface content
        elif processing_phase == 'segmented':
            return ( ''.join([element.content for element in elements]), [] )
        # If we're doing translation, return null translation for each element
        elif processing_phase == 'translated':
            return ( ['' for element in elements], [] )
        # Otherwise, return the elements unchanged
        else:
            return ( elements, [] )

    l1_language = l1_language.capitalize()
    l2_language = l2_language.capitalize()
    if processing_phase == 'segmented' and previous_version == 'presegmented':
        text_to_annotate = content_elements_to_segmentation_input(elements)
        annotation_prompt = segmentation_prompt(annotate_or_improve, text_to_annotate, l2_language)
    else:
        # Remove markup from the elements before passing to GPT-4 to make things easier for the AI
        if processing_phase == 'translated':
            simplified_elements0 = []
            for segment_elements in elements:
                segment_text = segment_elements_to_segment_translation_input(segment_elements)
                # Don't include null segments, as they can confuse gpt-4
                if segment_text:
                    simplified_elements0.append(segment_text)
        else:
            word_and_non_word_text_elements = word_and_non_word_text_items_in_element_list(elements)
            
            if annotate_or_improve == 'annotate' and previous_version == 'lemma':
                simplified_elements0 = [ simplify_element_to_list(element, 'lemma') for element in word_and_non_word_text_elements ]
            elif annotate_or_improve == 'annotate':
                simplified_elements0 = [ simplify_element_to_string(element) for element in word_and_non_word_text_elements ]
            else:
                simplified_elements0 = [ simplify_element_to_list(element, processing_phase) for element in word_and_non_word_text_elements ]
        simplified_elements = [ element for element in simplified_elements0 if element != False ]
        text_to_annotate = simplified_element_list_to_text(simplified_elements) 
        simplified_elements_json = json.dumps(simplified_elements)
        #n_words = len(simplified_elements)
        if processing_phase == 'translated':
            annotation_prompt = translation_prompt(annotate_or_improve, simplified_elements_json, l1_language, l2_language)
        elif processing_phase == 'segmented':
            annotation_prompt = morphology_prompt(simplified_elements_json, l2_language)
        elif processing_phase == 'gloss':
            # Note that in this case we pass simplified_elements rather than simplified_elements_json, since we need to manipulate the elements
            annotation_prompt = glossing_prompt(annotate_or_improve, simplified_elements, l1_language, l2_language,
                                                previous_version=previous_version, mwe=mwe, mwes=mwes, translation=translation, context=context)
        elif processing_phase == 'lemma':
            # Note that in this case we pass simplified_elements rather than simplified_elements_json, since we need to manipulate the elements
            annotation_prompt = tagging_prompt(annotate_or_improve, simplified_elements, l2_language, mwe=mwe, mwes=mwes)
        elif processing_phase == 'mwe':
            annotation_prompt = mwe_tagging_prompt(annotate_or_improve, simplified_elements_json, l2_language, few_shot_examples=few_shot_examples)
        elif processing_phase == 'pinyin':
            annotation_prompt = pinyin_tagging_prompt(annotate_or_improve, simplified_elements_json, l2_language)
        elif processing_phase == 'lemma_and_gloss' and annotate_or_improve == 'improve':
            annotation_prompt = joint_tagging_and_glossing_prompt(simplified_elements_json, l1_language, l2_language)
        else:
            message = f'Unsupported combination processing_phase = {processing_phase} and annotate_or_improve = {annotate_or_improve} in create_annotation'
            #print(message)
            raise InternalCLARAError(message = message )
    api_calls = []
    n_attempts = 0
    limit = int(config.get('chatgpt4_annotation', 'retry_limit'))
    while True:
        if n_attempts >= limit:
            if always_succeed:
                return ( '*FAILED*', api_calls )
            else:
                raise ChatGPTError( message=f'*** Giving up, have tried sending this to ChatGPT-4 {limit} times' )
        n_attempts += 1
        await post_task_update_async(callback, f'--- Calling ChatGPT-4 (attempt #{n_attempts}) to {annotate_or_improve} text ({n_words} words and punctuation marks): "{text_to_annotate}"')
        try:
            # Original sync call
            #api_call = clara_chatgpt4.call_chat_gpt4(annotation_prompt, config_info=config_info, callback=callback)
            # Async call
            api_call = await clara_chatgpt4.get_api_chatgpt4_response(annotation_prompt, config_info=config_info, callback=callback)
            api_calls += [ api_call ]
            if processing_phase == 'mwe':
                mwe_parse_response = await parse_chatgpt_annotation_response(api_call.response, simplified_elements, 'mwe',
                                                                             config_info=config_info, callback=callback)
                
                analysis = mwe_parse_response['analysis']
                mwes = mwe_parse_response['mwes']
                api_calls += mwe_parse_response['api_calls']

                # Call find_mwe_positions_for_content_elements because we'll get an exception of the mwe can't be found in the segment.
                # If so, we need to retry.
                correct_mwes = []
                for mwe in mwes:
                    try:
                        find_mwe_positions_for_content_elements(elements, mwe)
                        correct_mwes.append(mwe)
                    except MWEError as e:
                        # Try again if possible, otherwise discard the MWE so that we don't fail
                        if n_attempts < limit:
                            raise e
                mwes_and_analysis = { 'mwes': correct_mwes, 'analysis': analysis }
                return ( mwes_and_analysis, api_calls )
            elif processing_phase == 'segmented' and previous_version == 'presegmented':
                segmented_text0 = api_call.response
                # The template should tell the AI to return the answer enclosed between the tags "<startoftext>", "<endoftext>", but sometimes these don't come out quite right
                segmented_text = find_between_tags(segmented_text0, "text", "text")
                # Try to correct if we have a mismatch 
                if text_to_annotate != segmented_text.replace('|', '').replace('@', ''):
                    segmented_text = merge_annotations_charwise(text_to_annotate, segmented_text, 'segmentation')
                return ( segmented_text, api_calls )
            elif processing_phase == 'translated':
                translation_parse_response = await parse_chatgpt_annotation_response(api_call.response, simplified_elements, processing_phase,
                                                                                     previous_version=previous_version,
                                                                                     config_info=config_info, callback=callback)
                api_calls += translation_parse_response['api_calls']
                return ( translation_parse_response['items'], api_calls )
            else:
                if processing_phase in ( 'gloss', 'lemma' ):
                    simplified_elements1 = substitute_mwes_in_content_string_list(simplified_elements, mwes)
                else:
                    simplified_elements1 = simplified_elements
                    
                gloss_or_lemma_parse_response = await parse_chatgpt_annotation_response(api_call.response, simplified_elements1, processing_phase,
                                                                                        previous_version=previous_version,
                                                                                        config_info=config_info, callback=callback)

                api_calls += gloss_or_lemma_parse_response['api_calls']
                annotated_simplified_elements = gloss_or_lemma_parse_response['items']
                nontrivial_annotated_elements = [ unsimplify_element(element, processing_phase, previous_version=previous_version)
                                                  for element in annotated_simplified_elements ]
                annotated_elements = merge_elements_and_annotated_elements(elements, nontrivial_annotated_elements, processing_phase)
                if n_attempts < limit: #Don't give up if MWEs are not consistently annotated
                    await check_mwes_are_consistently_annotated(elements, mwes, processing_phase, callback=callback)
                return ( annotated_elements, api_calls )
                
        except MWEError as e:
            await post_task_update_async(callback, f'*** Warning: {e.message}')
        except ChatGPTError as e:
            await post_task_update_async(callback, f'*** Warning: bad response from ChatGPT-4')
            await post_task_update_async(callback, e.message)
        except Exception as e:
            await post_task_update_async(callback, f'*** Warning: error when sending request to ChatGPT-4')
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            await post_task_update_async(callback, error_message)

def content_elements_to_segmentation_input(content_elements):
    segment_text = ''.join([ element.content for element in content_elements ])
    return segment_text

def segment_elements_to_segment_translation_input(segment_elements):
    print(f'segment_elements_to_segment_translation_input: input: {segment_elements}')
    word_and_non_word_text_elements = word_and_non_word_text_items_in_element_list(segment_elements)
    segment_text = ''.join([ element.content for element in word_and_non_word_text_elements if element.type in ( 'Word', 'NonWordText' ) ])
    result = segment_text.replace('\n', ' ').strip()
    #print(f'segment_elements_to_segment_translation_input: output: {result}')
    return result

def merge_elements_and_annotated_elements(elements, annotated_elements, processing_phase):
    #print(f'merge_elements_and_annotated_elements({elements}, {annotated_elements}, {processing_phase})')
    matcher = difflib.SequenceMatcher(None, 
        [element.content.strip() for element in elements], 
        [element.content.strip() for element in annotated_elements])

    # Add a placeholder annotation to all Word elements initially
    for element in elements:
        if element.type == "Word" and processing_phase not in element.annotations:
            element.annotations[processing_phase] = 'NO_ANNOTATION'

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
            # If the replacement covers the same number of elements, guess the annotations are correct and the words have been changed
            if i2 - i1 == j2 - j1:
                for i, j in zip(range(i1, i2), range(j1, j2)):
                    elements[i].annotations.update(annotated_elements[j].annotations)
    #print(f'result = {elements}')
    return elements

def segmentation_prompt(annotate_or_improve, text, l2_language):
    template, annotated_example_list = get_template_and_annotated_example_list(annotate_or_improve, 'segmented', l2_language)
    examples = segmentation_examples_to_text(annotated_example_list)
    return template.format( l2_language=l2_language,
                            examples=examples,
                            text=text )

def presegmentation_prompt(annotate_or_improve, text, l2_language, text_type=None):
    if annotate_or_improve != 'annotate':
        raise ValueError('Cannot currently improve presegmentation')
    template, annotated_example_list = get_template_and_annotated_example_list(annotate_or_improve, 'presegmented', l2_language)
    examples = segmentation_examples_to_text(annotated_example_list)
    text_type_advice = make_text_type_advice(text_type)
    return template.format( l2_language=l2_language,
                            examples=examples,
                            text=text,
                            text_type_advice=text_type_advice )

def make_text_type_advice(text_type):
    if text_type == 'prose':
        return 'The text is probably a piece of prose like a story or essay'
    if text_type == 'poem':
        return 'The text is probably a poem or song'
    if text_type == 'dictionary':
        return 'The text is probably some kind of dictionary'
    else:
        return ''

def morphology_prompt(simplified_elements_json, l2_language):
    template, annotated_example_list = get_template_and_example_list(annotate_or_improve, 'morphology', l2_language)
    if annotate_or_improve == 'annotate':
        examples = morphology_examples_to_examples_text(example_list, l2_language)
    return template.format( l1_language=l1_language,
                            l2_language=l2_language,
                            examples=examples,
                            simplified_elements_json=simplified_elements_json
                            )

def translation_prompt(annotate_or_improve, simplified_elements_json, l1_language, l2_language):
    template, annotated_example_list = get_template_and_annotated_example_list(annotate_or_improve, 'translated', l2_language)
    if annotate_or_improve == 'annotate':
        examples = translation_examples_to_examples_text(annotated_example_list, l1_language, l2_language)
    else:
        examples = retranslation_examples_to_examples_text(annotated_example_list, l1_language, l2_language)
    return template.format( l1_language=l1_language,
                            l2_language=l2_language,
                            examples=examples,
                            simplified_elements_json=simplified_elements_json
                            )


def glossing_prompt(annotate_or_improve, simplified_elements, l1_language, l2_language,
                    previous_version='segmented_with_images', mwe=False, mwes=[], translation=None, context=None):
    if previous_version == 'lemma':
        template_and_examples_version = 'gloss_with_lemma'
        simplified_elements_to_show = simplified_elements
    elif mwe:
        template_and_examples_version = 'gloss_with_mwe'
        simplified_elements_to_show = substitute_mwes_in_content_string_list(simplified_elements, mwes)
    else:
        template_and_examples_version = 'gloss'
        simplified_elements_to_show = simplified_elements
        
    template, annotated_example_list = get_template_and_annotated_example_list(annotate_or_improve, template_and_examples_version, l2_language)
    if annotate_or_improve == 'annotate':
        examples = glossing_examples_to_examples_text(annotated_example_list, l1_language, l2_language, previous_version=previous_version,
                                                      mwe=mwe, mwes=mwes, translation=translation)
    else:
        examples = reglossing_examples_to_examples_text(annotated_example_list, l1_language, l2_language)

    simplified_elements_json = json.dumps(simplified_elements_to_show)
    mwes_json = json.dumps(mwes)
    context_text = f'The text to gloss occurs in the context of the following piece of text: "{context}"' if context else ''
    return template.format( l1_language=l1_language,
                            l2_language=l2_language,
                            examples=examples,
                            simplified_elements_json=simplified_elements_json,
                            mwes=mwes_json,
                            context_text=context_text
                            )

def tagging_prompt(annotate_or_improve, simplified_elements, l2_language, mwe=False, mwes=[]):
    l1_language = 'irrelevant'
    if mwe:
        template_and_examples_version = 'lemma_with_mwe'
        simplified_elements_to_show = substitute_mwes_in_content_string_list(simplified_elements, mwes)
    else:
        template_and_examples_version = 'lemma'
        simplified_elements_to_show = simplified_elements
    template, annotated_example_list = get_template_and_annotated_example_list(annotate_or_improve, template_and_examples_version, l2_language)
    if annotate_or_improve == 'annotate':
        examples = tagging_examples_to_examples_text(annotated_example_list, l2_language, mwe=mwe, mwes=mwes)
    else:
        examples = retagging_examples_to_examples_text(annotated_example_list, l2_language, mwe=mwe, mwes=mwes)
    simplified_elements_json = json.dumps(simplified_elements_to_show)
    mwes_json = json.dumps(mwes)
    return template.format( l2_language=l2_language,
                            examples=examples,
                            simplified_elements_json=simplified_elements_json,
                            mwes=mwes_json
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

def mwe_tagging_prompt(annotate_or_improve, simplified_elements_json, l2_language, few_shot_examples=[]):
    l1_language = 'irrelevant'
    template, annotated_example_list_from_repo = get_template_and_annotated_example_list(annotate_or_improve, 'mwe', l2_language)
    annotated_example_list = few_shot_examples if few_shot_examples else annotated_example_list_from_repo
    if annotate_or_improve == 'annotate':
        examples = mwe_tagging_examples_to_examples_text(annotated_example_list, l1_language, l2_language)
    else:
        examples = mwe_retagging_examples_to_examples_text(annotated_example_list, l1_language, l2_language)
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
    #print(f'get_template_and_annotated_example_list_for_language({annotate_or_improve}, {annotation_type}, {l2_language})')
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

def translation_examples_to_examples_text(examples, l1_language, l2_language):
    return '\n\n'.join([ translation_example_to_text(example, l1_language, l2_language) for example in examples ])

def translation_example_to_text(example, l1_language, l2_language):
    example_internalised = clara_internalise.internalize_text(example, l2_language, l1_language, 'translated')
    segments = example_internalised.segments()
    source_texts = [ segment.to_text(annotation_type='plain')
                     for segment in segments ]
    source_and_target_texts = [ [ segment.to_text(annotation_type='plain'), segment.annotations['translated'] ]
                                for segment in segments ]
    return f'Input: {source_texts}\nOutput: {source_and_target_texts}'

def glossing_examples_to_examples_text(examples_structure, l2_language, l1_language, previous_version='segmented_with_images', mwe=False, mwes=[], translation=None):
    #print(f'--- glossing_examples_to_examples_text({examples_structure}, {l2_language}, {l1_language}, mwe={mwe}, mwes={mwes}, translation={translation}')
    # 1) We're using the lemma-tagged version as the input
    if previous_version == 'lemma':
        return '\n\n'.join([ glossing_example_to_example_text(example, l2_language, l1_language, previous_version='lemma') for example in examples_structure ])
    # 2) We aren't using MWEs at all
    elif not mwe:
        return '\n\n'.join([ glossing_example_to_example_text(example, l2_language, l1_language) for example in examples_structure ])
    # 3) We are using MWEs, and we might add a translation to the end. Two subcases:
    # 3a) This particular text doesn't have any MWEs, so we use only examples with no MWEs
    elif not mwes:
        examples_to_use = [ example for example in examples_structure
                            if example[1].strip() == '' ]
        intro = 'Here are some examples:'
        examples_text = '\n\n'.join([ glossing_example_with_mwes_to_example_text(example, l2_language, l1_language) for example in examples_to_use ])
        intro_and_examples_text = f'{intro}\n\n{examples_text}'
    # 3b) We are using MWEs, and this particular text has MWEs, so we use only examples with MWEs
    else:
        examples_to_use = [ example for example in examples_structure
                            if example[1].strip() != '' ]
        intro = 'Here are some examples:'
        examples_text = '\n\n'.join([ glossing_example_with_mwes_to_example_text(example, l2_language, l1_language) for example in examples_to_use ])
        intro_and_examples_text = f'{intro}\n\n{examples_text}'

    if not translation:
        return intro_and_examples_text
    else:
        translations_text = f'\n\nHere is a translation of the whole passage:\n\n"{translation}"\n\nIt may be useful to include words from it when glossing.'
        return intro_and_examples_text + translations_text

def tagging_examples_to_examples_text(examples_structure, l2_language, mwe=False, mwes=[]):
    #print(f'--- tagging_examples_to_examples_text({examples_structure}, {l2_language}, mwe={mwe}, mwes={mwes})')
    # We aren't using MWEs at all
    if not mwe:
        return '\n\n'.join([ tagging_example_to_example_text(example, l2_language) for example in examples_structure ])
    # We are using MWEs, but this particular text doesn't have any, so we use only examples with no MWEs
    elif not mwes:
        examples_to_use = [ example for example in examples_structure
                            if example[1].strip() == '' ]
        intro = 'Here are some examples:'
        examples_text = '\n\n'.join([ tagging_example_with_mwes_to_example_text(example, l2_language) for example in examples_to_use ])
        return f'{intro}\n\n{examples_text}'
    # We are using MWEs, and this particular text has MWEs, so we use only examples with MWEs
    else:
        examples_to_use = [ example for example in examples_structure
                            if example[1].strip() != '' ]
        mwes_text = mwes_to_json_string(mwes)
        intro = 'Here are some examples:'
        examples_text = '\n\n'.join([ tagging_example_with_mwes_to_example_text(example, l2_language) for example in examples_to_use ])
        return f'{intro}\n\n{examples_text}'

##def tagging_examples_to_examples_text(examples_structure, l2_language, l1_language):
##    return '\nor\n'.join([ tagging_example_to_example_text(example, l2_language, l1_language) for example in examples_structure ])

def reglossing_examples_to_examples_text(examples_structure, l2_language, l1_language):
    return '\nor\n'.join([ reglossing_example_to_example_text(example, l2_language, l1_language) for example in examples_structure ])

def re_lemma_and_glossing_examples_to_examples_text(examples_structure, l1_language, l2_language):
    return '\nor\n'.join([ re_lemma_and_glossing_example_to_example_text(example, l2_language, l1_language) for example in examples_structure ])

def glossing_example_to_example_text(example, l2_language, l1_language, previous_version='segmented_with_images'):
    if previous_version == 'lemma':
        simplified_internalised_example = annotated_string_to_simplified_internalised_form(example, l2_language, l1_language, 'lemma_and_gloss_for_gloss')
        simplified_internalised_example_words_and_lemmas = [ triple[:2] for triple in simplified_internalised_example ]
        return f'Input: {json.dumps(simplified_internalised_example_words_and_lemmas)}\nOutput: {json.dumps(simplified_internalised_example)}'
    else:
        simplified_internalised_example = annotated_string_to_simplified_internalised_form(example, l2_language, l1_language, 'gloss')
        simplified_internalised_example_words = [ pair[0] for pair in simplified_internalised_example ]
        return f'Input: {json.dumps(simplified_internalised_example_words)}\nOutput: {json.dumps(simplified_internalised_example)}'

def glossing_example_with_mwes_to_example_text(example_pair, l2_language, l1_language):
    example, mwes = example_pair
    simplified_internalised_example = annotated_string_to_simplified_internalised_form(example, l2_language, l1_language, 'gloss')
    simplified_internalised_example_words = [ pair[0] for pair in simplified_internalised_example ]
    if not mwes.strip():
        return f'Input: {json.dumps(simplified_internalised_example_words)}\nOutput: {json.dumps(simplified_internalised_example)}'
    else:
        #return f'Input: {json.dumps(simplified_internalised_example_words)}\nMWES:{json.dumps(mwes)}\nOutput: {json.dumps(simplified_internalised_example)}'
        mwes_lists = mwes_string_to_mwes_lists(mwes)
        simplified_internalised_example_words_with_mwe_substitution = substitute_mwes_in_content_string_list(simplified_internalised_example_words, mwes_lists)
        return f'Input: {json.dumps(simplified_internalised_example_words_with_mwe_substitution)}\nMWES:{json.dumps(mwes_lists)}\nOutput: {json.dumps(simplified_internalised_example)}'

def tagging_example_to_example_text(example, l2_language):
    l1_language = 'irrelevant'
    simplified_internalised_example = annotated_string_to_simplified_internalised_form(example, l2_language, l1_language, 'lemma')
    simplified_internalised_example_words = [ pair[0] for pair in simplified_internalised_example ]
    return f'{json.dumps(simplified_internalised_example_words)} as {json.dumps(simplified_internalised_example)}'

def tagging_example_with_mwes_to_example_text(example_pair, l2_language):
    example, mwes = example_pair
    l1_language = 'irrelevant'
    simplified_internalised_example = annotated_string_to_simplified_internalised_form(example, l2_language, l1_language, 'lemma')
    simplified_internalised_example_words = [ pair[0] for pair in simplified_internalised_example ]
    mwes_lists = mwes_string_to_mwes_lists(mwes)
    simplified_internalised_example_words_with_mwe_substitution = substitute_mwes_in_content_string_list(simplified_internalised_example_words, mwes_lists)
    if not mwes.strip():
        return f'Input: {json.dumps(simplified_internalised_example_words_with_mwe_substitution)}\nOutput: {json.dumps(simplified_internalised_example)}'
    else:
        #return f'Input: {json.dumps(simplified_internalised_example_words)}\nMWES:{json.dumps(mwes)}\nOutput: {json.dumps(simplified_internalised_example)}'
        return f'Input: {json.dumps(simplified_internalised_example_words_with_mwe_substitution)}\nMWES:{json.dumps(mwes_lists)}\nOutput: {json.dumps(simplified_internalised_example)}'

def mwes_string_to_mwes_lists(all_mwes_string):
    mwe_strings = all_mwes_string.strip().split(',')
    return [ mwe_string.split() for mwe_string in mwe_strings ]

def substitute_mwes_in_content_string_list(simplified_internalised_example_words, mwes_lists):
    output = [ [ item, None ] for item in simplified_internalised_example_words ]
    for mwe_list in mwes_lists:
        mwe_text = ' '.join(mwe_list)
        mwe_indices = find_mwe_positions_for_content_string_list(simplified_internalised_example_words, mwe_list)
        for index in mwe_indices:
            output[index][1] = mwe_text
    return output 

def mwes_to_json_string(mwes):
    return json.dumps(mwes)

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

def morphology_examples_to_examples_text(examples_structure, l2_language):
    return '\n\n'.join([ morphology_example_to_example_text(example, l2_language) for example in examples_structure ])

def mwe_tagging_examples_to_examples_text(examples_structure, l2_language, l1_language):
    #print(f'MWE examples: {examples_structure}')
    return '\n\n'.join([ mwe_tagging_example_to_example_text(example, l2_language, l1_language) for example in examples_structure ])

def retagging_examples_to_examples_text(examples_structure, l2_language, l1_language):
    return '\nor\n'.join([ retagging_example_to_example_text(example, l2_language, l1_language) for example in examples_structure ])

def pinyin_tagging_examples_to_examples_text(examples_structure, l2_language, l1_language):
    return '\nor\n'.join([ pinyin_tagging_example_to_example_text(example, l2_language, l1_language) for example in examples_structure ])

def pinyin_retagging_examples_to_examples_text(examples_structure, l2_language, l1_language):
    return '\nor\n'.join([ pinyin_retagging_example_to_example_text(example, l2_language, l1_language) for example in examples_structure ])

def mwe_tagging_example_to_example_text(mwe_example, l2_language, l1_language):
    # example_text is a string with the example
    # mwes_text is a comma-separated list of MWEs
    #
    # example_text =  "She must have thrown it out on Boxing Day morning.",
    # mwes_text = "thrown out, Boxing Day"
    # analysis = "- 'thrown out' is a form of a phrasal verb hence an MWE.
    #             'Boxing Day' is a set expression whose meaning is not deducible from its component words, hence an MWE'"
    example_text, mwes_text, analysis = mwe_example
    simplified_internalised_example_words = annotated_string_to_simplified_internalised_form(example_text, l2_language, l1_language, 'segmented')
    #mwes = [ mwe.strip() for mwe in mwes_text.split(',') ]
    mwes = [ mwe.strip().split() for mwe in mwes_text.split(',') ]
    return f'Input: {json.dumps(simplified_internalised_example_words)}\nAnalysis: {analysis}\nOutput: {json.dumps(mwes)}'

def morphology_example_to_example_text(morphology_example, l2_language):
    l1_language = 'irrelevant'     
    example_text, improved_example_text, analysis = morphology_example
    # Final arg is 'plain' because we don't want to split up words including vertical bars
    simplified_internalised_example_words = annotated_string_to_simplified_internalised_form(example_text, l2_language, l1_language, 'plain')
    simplified_internalised_improved_example_words = annotated_string_to_simplified_internalised_form(improved_example_text, l2_language, l1_language, 'plain')
    simplified_internalised_example_pairs = [ [ segmented_word.replace('|', ''), segmented_word ] for segmented_word in simplified_internalised_example_words ]
    simplified_internalised_improved_example_pairs = [ [ segmented_word.replace('|', ''), segmented_word ] for segmented_word in simplified_internalised_improved_example_words ]
    return f'Input: {json.dumps(simplified_internalised_example_pairs)}\nAnalysis: {analysis}\nOutput: {json.dumps(simplified_internalised_improved_example_pairs)}'
                                       
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

def annotated_string_to_simplified_internalised_form(example, l2_language, l1_language, processing_phase):
    internalised_example = clara_internalise.internalize_text(example, l2_language, l1_language, processing_phase)
    elements = internalised_example.content_elements()
    if processing_phase == 'segmented':
        return [ element.content.strip() for element in elements
                 if element.type in ( 'Word', 'NonWordText' ) and element.content.strip() ]
    else:
        simplified_elements0 = [ simplify_element_to_list(element, processing_phase) for element in elements ]
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

def simplify_element_to_list(element, processing_phase):
    content = element.content
    annotation = element.annotations[processing_phase] if processing_phase in element.annotations else 'NO_ANNOTATION'
    gloss = element.annotations['gloss'] if 'gloss' in element.annotations else 'NO_GLOSS'
    lemma = element.annotations['lemma'] if 'lemma' in element.annotations else 'NO_LEMMA'
    pos = element.annotations['pos'] if 'pos' in element.annotations else 'NO_POS'
    pinyin = element.annotations['pinyin'] if 'pinyin' in element.annotations else 'NO_PINYIN'
    # Return Words as they are
    if element.type == 'Word':
        if processing_phase == 'gloss':
            return [ content, gloss ]
        elif processing_phase == 'lemma':
            return [ content, lemma, pos ]
        elif processing_phase == 'lemma_and_gloss_for_gloss':
            return [ content, lemma, gloss ]
        elif processing_phase == 'pinyin':
            return [ content, pinyin ]
        else:
            return [ content, lemma, pos, gloss ]
            
    # Return NonWordText with the whitespace stripped off, if it's not all whitespace
    elif not content.isspace():
        content = content.strip()
        if processing_phase == 'gloss':
            return [ content, content ]
        elif processing_phase == 'pinyin':
            return [ content, content ]
        elif processing_phase == 'lemma':
            return [ content, content, 'PUNC' ]
        elif processing_phase == 'lemma_and_gloss_for_gloss':
            return [ content, lemma, content ]
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
def unsimplify_element(element, processing_phase, previous_version='default'):
    if processing_phase in ( 'gloss', 'pinyin' ) and previous_version != 'lemma' and len(element) == 2:
        content, annotation = element
        # String only consists of punctuation marks
        if all(regex.match(r"\p{P}", c) for c in content):
            # This can be relevant if the punctuation mark is part of an MWE
            return ContentElement("NonWordText", content, annotations={ processing_phase: annotation })
        # String is an HTML tag
        elif regex.match(r"<\/?\w+>", content):
            return ContentElement("Markup", content)
        else:
            return ContentElement("Word", content, annotations={ processing_phase: annotation })
    elif processing_phase == 'gloss' and previous_version == 'lemma' and len(element) == 3:
        content, lemma, gloss = element
        # String only consists of punctuation marks
        if all(regex.match(r"\p{P}", c) for c in content):
            return ContentElement("NonWordText", content)
        # String is an HTML tag
        elif regex.match(r"<\/?\w+>", content):
            return ContentElement("Markup", content)
        else:
            return ContentElement("Word", content, annotations={ 'gloss': gloss })
    elif processing_phase == 'segmented' and previous_version == 'segmented' and len(element) == 3:
        word, segmented_word = element
        # String only consists of punctuation marks
        if all(regex.match(r"\p{P}", c) for c in content):
            return ContentElement("NonWordText", content)
        # String is an HTML tag
        elif regex.match(r"<\/?\w+>", content):
            return ContentElement("Markup", content)
        else:
            return ContentElement("Word", segmented_word)
    elif processing_phase == 'lemma' and len(element) == 3:
        content, lemma, pos = element
        # String only consists of punctuation marks
        if all(regex.match(r"\p{P}", c) for c in content):
            # This can be relevant if the punctuation mark is part of an MWE
            return ContentElement("NonWordText", content, annotations={ 'lemma': lemma, 'pos': pos })
        # String is an HTML tag
        elif regex.match(r"<\/?\w+>", content):
            return ContentElement("Markup", content)
        else:
            return ContentElement("Word", content, annotations={ 'lemma': lemma, 'pos': pos })
    elif processing_phase == 'lemma_and_gloss' and len(element) == 4:
        content, lemma, pos, gloss = element
        # String only consists of punctuation marks
        if all(regex.match(r"\p{P}", c) for c in content):
            return ContentElement("NonWordText", content)
        # String is an HTML tag
        elif regex.match(r"<\/?\w+>", content):
            return ContentElement("Markup", content)
        else:
            return ContentElement("Word", content, annotations={ 'lemma': lemma, 'pos': pos, 'gloss': gloss })
    elif processing_phase == 'translated' and len(element) == 2:
        source, target = element
        return target
    else:
        message = f'Bad call: unsimplify_element({element}, {processing_phase}, previous_version={previous_version})'
        print(message)
        raise InternalCLARAError(message = message)


##async def parse_chatgpt_annotation_response(response, simplified_elements, processing_phase, previous_version='default',
##                                            config_info={}, callback=None):
##    print(f'parse_chatgpt_annotation_response("""{response}""", {simplified_elements}, "{processing_phase}", ...')
##    if processing_phase == 'mwe':
##        # Extract the initial analysis text and the JSON list
##        intro, response_object = clara_chatgpt4.interpret_chat_gpt4_response_as_intro_and_json(response, object_type='list', callback=callback)
##        if is_list_of_lists_of_strings(response_object):
##            print(f'Well-formed MWE response: {response_object}')
##            mwes = response_object
##            # Return a structure containing both the analysis and the list of MWEs
##            return {'analysis': intro, 'mwes': mwes}
##        else:
##            message = f'Response is not a list of lists of strings: {response_object}'
##            print(message)
##            await post_task_update_async(callback, message)
##            raise ChatGPTError(message=message)
##        
##    if processing_phase == 'translated':
##        response_object = clara_chatgpt4.interpret_chat_gpt4_response_as_json(response, object_type='list', callback=callback)
##        #print(f'response_object for translation: {response_object}')
##        if not isinstance(response_object, list):
##            raise ChatGPTError(message=f'Response is not a list: {response}')
##
##        if len(response_object) != len(simplified_elements):
##            raise ChatGPTError(message=f'Wrong number of elements in reponse list (should have been {len(simplified_elements)}): {response}')
##
##        for element in response_object:
##            if not well_formed_element_in_annotation_response(element, 'translated'):
##                raise ChatGPTError(message=f'Bad element in response: {element}')
##
##        return [ { 'translated': element[1] } for element in response_object ]
##
##    else:
##        # Handle other processing phases (non-MWE)
##        response_object = clara_chatgpt4.interpret_chat_gpt4_response_as_json(response, object_type='list', callback=callback)
##        if not isinstance(response_object, list):
##            raise ChatGPTError(message=f'Response is not a list: {response}')
##
##        usable_response_object = []
##        for element in response_object:
##            if not well_formed_element_in_annotation_response(element, processing_phase, previous_version=previous_version,):
##                await post_task_update_async(callback, f'*** Warning: bad element {element} in annotation response, discarding')
##            else:
##                usable_response_object.append(element)
##
##        original_text = ' '.join([element if isinstance(element, str) else element[0] for element in simplified_elements])
##        annotated_text = ' '.join([element[0] for element in usable_response_object])
##        if original_text != annotated_text:
##            warning = f"""*** Warning: original text and annotated text are different.
##     Original text: {original_text}
##    Annotated text: {annotated_text}"""
##            await post_task_update_async(callback, warning)
##
##        return usable_response_object

#----------------------------------------
# New AI-written version

JSON_FENCE_RE = re.compile(
    r"(?:```(?:json)?\s*)(\[.*?\])\s*```",
    flags=re.DOTALL | re.IGNORECASE,
)

BRACKETED_LIST_RE = re.compile(
    r"(\[[\s\S]*\])\s*\Z",  # last [...] in the string
    flags=re.DOTALL,
)

SMART_APOS = "\u2019\u02BC\u2032\uFF07"  # curly/right/single-prime/fullwidth

trace_annotation_response = False
#trace_annotation_response = True

def print_if_trace(s):
    if trace_annotation_response:
        print(s)

def _norm_apostrophes(s: str) -> str:
    if not s:
        return s
    for ch in SMART_APOS:
        s = s.replace(ch, "'")
    return s

def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def _extract_json_list_block(text: str) -> Tuple[str, str]:
    """
    Return (intro_text, json_block_str). Tries code fences first, then last [...] block.
    Raises ValueError if nothing plausible found.
    """
    m = JSON_FENCE_RE.search(text)
    if m:
        intro = text[:m.start()].strip()
        return intro, m.group(1).strip()

    m = BRACKETED_LIST_RE.search(text)
    if m:
        intro = text[:m.start()].strip()
        return intro, m.group(1).strip()

    # A final, gentle 'Output:' heuristic
    out_idx = text.lower().rfind("output:")
    if out_idx >= 0:
        after = text[out_idx+7:].strip()
        mm = BRACKETED_LIST_RE.search(after)
        if mm:
            intro = text[:out_idx].strip()
            return intro, mm.group(1).strip()

    raise ValueError("No JSON list block found")

def _json_load_loose(s: str) -> Any:
    """
    Strict json.loads, with a very light fallback: normalize smart quotes/apostrophes.
    Avoids risky global single→double conversions.
    """
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        s2 = _norm_apostrophes(s)
        if s2 != s:
            return json.loads(s2)  # may still raise
        print_if_trace(f'Error in _json_load_loose({s}')
        raise

def _is_list_of_lists_of_strings(x: Any) -> bool:
    return (
        isinstance(x, list)
        and all(isinstance(row, list) for row in x)
        and all(all(isinstance(tok, str) for tok in row) for row in x)
    )

def _validate_mwe_vocab(mwe_list: List[List[str]], tokens: List[str]) -> Tuple[List[List[str]], List[Tuple[List[str], str]]]:
    """
    Ensure every string in every MWE is a member of 'tokens' (after simple normalization).
    Returns (kept_mwes, dropped_with_reason).
    """
    # Build a normalized vocabulary → original-token(s) map (handles smart apostrophes)
    norm2orig = {}
    for t in tokens:
        key = _norm_apostrophes(t)
        norm2orig.setdefault(key, set()).add(t)

    kept = []
    dropped = []

    for row in mwe_list:
        ok = True
        fixed_row = []
        for tok in row:
            nt = _norm_apostrophes(tok)
            if nt in norm2orig:
                # Prefer original spelling identical to nt if present, else any
                if tok in norm2orig[nt]:
                    fixed_row.append(tok)
                else:
                    fixed_row.append(sorted(norm2orig[nt], key=lambda s: (s != nt, s))[0])
            else:
                ok = False
                dropped.append((row, f"Token '{tok}' not in segment vocabulary"))
                break
        if ok:
            kept.append(fixed_row)

    return kept, dropped

def _mismatch_report(original_tokens: List[str], mwe_list: List[List[str]]) -> str:
    return (
        "Segment tokens:\n"
        f"{original_tokens}\n\n"
        "Provided MWEs:\n"
        f"{mwe_list}"
    )

async def _repair_mwe_with_gpt(raw_response: str,
                               tokens: List[str],
                               config_info: dict,
                               callback=None) -> Tuple[List[List[str]], List[Any], str]:
    """
    Ask GPT to emit ONLY valid JSON (list of lists of strings) with vocabulary limited to 'tokens'.
    Returns (mwes, api_calls, analysis_text_used).
    """
    api_calls = []

    system_hint = (
        "You will repair a JSON list of multi-word expressions (MWEs) for one tokenized segment.\n"
        "Rules:\n"
        "1) Output VALID JSON only: a list of lists of strings (e.g., [[\"give\",\"up\"], [\"might\",\"as\",\"well\"]]).\n"
        "2) Each string MUST be EXACTLY one token from the provided vocabulary (case sensitive), no new tokens.\n"
        "3) No commentary, no code fences, no backticks—JSON only.\n"
        "4) MWEs need not be contiguous in the original segment, but tokens must come from it.\n"
        "5) If unsure, omit the questionable MWE rather than inventing tokens.\n"
    )
    user_prompt = (
        "Here is the original assistant output you need to repair, followed by the segment's tokens.\n\n"
        f"--- Original assistant output ---\n{raw_response}\n\n"
        f"--- Token vocabulary (exactly these strings allowed) ---\n{tokens}\n\n"
        "Return ONLY JSON as specified—no prose."
    )

    # One shot; you said you'll track costs—keep this cheap. You can add retries if desired.
    api = await clara_chatgpt4.get_api_chatgpt4_response(
        prompt=f"{system_hint}\n\n{user_prompt}",
        config_info=config_info,
        callback=callback
    )
    api_calls.append(api)

    try:
        repaired = _json_load_loose(api.response)
    except Exception as e:
        # Final attempt: strip everything before/after a [] block
        try:
            _, block = _extract_json_list_block(api.response)
            repaired = _json_load_loose(block)
        except Exception:
            raise ChatGPTError(message=f"Repair failed: model did not return valid JSON. Raw:\n{api.response}") from e

    if not _is_list_of_lists_of_strings(repaired):
        raise ChatGPTError(message=f"Repair failed: JSON not a list of lists of strings. Got: {type(repaired)}")

    # Tight vocab check
    kept, dropped = _validate_mwe_vocab(repaired, tokens)
    if dropped:
        # We deliberately do NOT iterate further—your policy was to keep moving quickly.
        if callback:
            await post_task_update_async(callback, f"Repair dropped {len(dropped)} MWEs for OOV tokens.")
    return kept, api_calls, ""  # analysis is not meaningful on repair

def _tokens_and_mwe_map(simplified_elements):
    """
    Accepts:
      - ['If', 'we', ...] OR
      - [['If', None], ['get','get out'], ...]
    Returns:
      tokens: [str, ...]
      mwe_labels: [str|None, ...]  (parallel to tokens)
    """
    tokens, labels = [], []
    for el in simplified_elements:
        if isinstance(el, str):
            tokens.append(_norm_apostrophes(el)); labels.append(None)
        elif isinstance(el, (list, tuple)) and len(el) >= 1:
            tok = el[0]
            lab = el[1] if len(el) > 1 else None
            tokens.append(_norm_apostrophes(str(tok)))
            labels.append(str(lab) if lab not in (None, "") else None)
        else:
            # very defensive
            tokens.append(_norm_apostrophes(str(el)))
            labels.append(None)
    return tokens, labels

def _group_indices_by_label(labels):
    """
    {'get out': [4,6], 'might as well':[9,10,11], None:[...]} but we drop None group.
    """
    groups = {}
    for i, lab in enumerate(labels):
        if lab is None:
            continue
        groups.setdefault(lab, []).append(i)
    return groups

# --- LEMMA / GLOSS validators & repair ---

def _valid_lemma_shape(obj, n_tokens):
    if not isinstance(obj, list) or len(obj) != n_tokens:
        print_if_trace(f'Failed _valid_lemma_shape({obj}, {n_tokens}): length')
        return False
    for row in obj:
        if not isinstance(row, list):
            print_if_trace(f'Failed _valid_lemma_shape({obj}, {n_tokens}): bad row {row}')
            return False
        if len(row) not in (2,3):
            print_if_trace(f'Failed _valid_lemma_shape({obj}, {n_tokens}): bad row {row}')
            return False
        if not (isinstance(row[0], str) and isinstance(row[1], str)):
            print_if_trace(f'Failed _valid_lemma_shape({obj}, {n_tokens}): bad row {row}')
            return False
        if len(row) == 3 and not isinstance(row[2], str):
            print_if_trace(f'Failed _valid_lemma_shape({obj}, {n_tokens}): bad row {row}')
            return False
    return True

def _valid_gloss_shape(obj, n_tokens):
    if not isinstance(obj, list) or len(obj) != n_tokens:
        print_if_trace(f'Failed _valid_gloss_shape({obj}, {n_tokens}): length')
        return False
    for row in obj:
        if not (isinstance(row, list) and len(row) == 2 and isinstance(row[0], str) and isinstance(row[1], str)):
            print_if_trace(f'Failed _valid_gloss_shape({obj}, {n_tokens}): bad row {row}')
            return False
    return True

def _enforce_token_match(obj_rows, simplified_elements):
    """
    First column MUST match token word form exactly (after apostrophe normalization).
    Returns (ok:bool, mismatches:[(i, expected, got)])
    """
    mismatches = []
    for i, row in enumerate(obj_rows):
        got = _norm_apostrophes(row[0])
        exp = simplified_elements[i][0]
        if got != exp:
            mismatches.append((i, exp, row[0]))
            print_if_trace(f'Failed _enforce_token_match({obj_rows}, {tokens}): bad row {row}')
    return len(mismatches) == 0, mismatches

def _check_mwe_uniform_value(obj_rows, labels, col_idx):
    """
    For lemma/gloss, enforce same value across tokens that share the same MWE label.
    col_idx = 1 (lemma or gloss column).
    Returns (ok:bool, offenders: {label: set(values)})
    """
    groups = _group_indices_by_label(labels)
    offenders = {}
    for lab, idxs in groups.items():
        values = {obj_rows[i][col_idx] for i in idxs if i < len(obj_rows)}
        if len(values) > 1:
            offenders[lab] = values
            print_if_trace(f'Failed _check_mwe_uniform_value({obj_rows}, {labels}, {col_idx}): lab = {lab}, values = {values}')
    return (len(offenders) == 0), offenders

def _retry_limit_from_config(config_info, default=2):
    try:
        return int(config_info.get('chatgpt4_annotation', {}).get('retry_limit', default))
    except Exception:
        return default

async def _repair_lemma_with_gpt(raw_response, tokens, labels, config_info, callback=None, attempts=2):
    """
    Ask GPT to output ONLY JSON list where each item is:
      [token, lemma]  OR  [token, lemma, UPOS]
    Constraints:
      - length == len(tokens), in the SAME ORDER
      - row[0] == token (exact)
      - for tokens sharing the same non-null MWE label, row[1] must be IDENTICAL across the group
      - JSON only, no prose/fences
    Returns (rows, api_calls)
    """
    api_calls = []
    sys_msg = (
        "Repair lemma output for a tokenized segment.\n"
        "Rules:\n"
        "1) Output VALID JSON ONLY: a list with one item per token, in the same order as given.\n"
        "2) Each item is either [token, lemma] OR [token, lemma, UPOS].\n"
        "3) The first element MUST equal the provided token exactly.\n"
        "4) For tokens that share the same MWE label, the lemma (second element) MUST be identical across those tokens.\n"
        "5) No commentary, no code fences, no extra text—JSON only."
    )
    mwe_info = {lab: _group_indices_by_label(labels)[lab] for lab in _group_indices_by_label(labels)}
    user_msg_base = (
        "Original assistant output to repair:\n"
        f"{raw_response}\n\n"
        "Tokens (in order):\n"
        f"{tokens}\n\n"
        "MWE labels aligned to tokens (None if not in an MWE):\n"
        f"{labels}\n\n"
        "Return ONLY the JSON array as specified."
    )
    last_error = None
    for _ in range(max(1, attempts)):
        api = await clara_chatgpt4.get_api_chatgpt4_response(
            prompt=f"{sys_msg}\n\n{user_msg_base}",
            config_info=config_info,
            callback=callback
        )
        api_calls.append(api)
        try:
            obj = _json_load_loose(api.response)
        except Exception as e:
            # try bracket extract
            try:
                _, block = _extract_json_list_block(api.response)
                obj = _json_load_loose(block)
            except Exception as e2:
                last_error = e2
                continue

        if not _valid_lemma_shape(obj, len(tokens)):
            last_error = ValueError("Shape invalid after repair")
            continue
        ok_tok, mm = _enforce_token_match(obj, tokens)
        if not ok_tok:
            last_error = ValueError(f"Token mismatch at {mm[:3]}…")
            continue
        ok_mwe, off = _check_mwe_uniform_value(obj, labels, 1)
        if not ok_mwe:
            last_error = ValueError(f"MWE uniformity failed: {list(off.keys())[:3]}…")
            continue
        return obj, api_calls
    raise ChatGPTError(message=f"Lemma repair failed after {attempts} attempts: {last_error}")

async def _repair_gloss_with_gpt(raw_response, tokens, labels, config_info, callback=None, attempts=2):
    """
    Ask GPT to output ONLY JSON list of [token, gloss] with same constraints as lemma re MWE uniformity.
    """
    api_calls = []
    sys_msg = (
        "Repair gloss output for a tokenized segment.\n"
        "Rules:\n"
        "1) Output VALID JSON ONLY: a list with one item per token, in the same order as given.\n"
        "2) Each item is [token, gloss].\n"
        "3) The first element MUST equal the provided token exactly.\n"
        "4) For tokens that share the same MWE label, the gloss (second element) MUST be identical across those tokens.\n"
        "5) No commentary or code fences—JSON only."
    )
    user_msg_base = (
        "Original assistant output to repair:\n"
        f"{raw_response}\n\n"
        "Tokens (in order):\n"
        f"{tokens}\n\n"
        "MWE labels aligned to tokens (None if not in an MWE):\n"
        f"{labels}\n\n"
        "Return ONLY the JSON array as specified."
    )
    last_error = None
    for _ in range(max(1, attempts)):
        api = await clara_chatgpt4.get_api_chatgpt4_response(
            prompt=f"{sys_msg}\n\n{user_msg_base}",
            config_info=config_info,
            callback=callback
        )
        api_calls.append(api)
        try:
            obj = _json_load_loose(api.response)
        except Exception as e:
            try:
                _, block = _extract_json_list_block(api.response)
                obj = _json_load_loose(block)
            except Exception as e2:
                last_error = e2
                continue

        if not _valid_gloss_shape(obj, len(tokens)):
            last_error = ValueError("Shape invalid after repair")
            continue
        ok_tok, mm = _enforce_token_match(obj, tokens)
        if not ok_tok:
            last_error = ValueError(f"Token mismatch at {mm[:3]}…")
            continue
        ok_mwe, off = _check_mwe_uniform_value(obj, labels, 1)
        if not ok_mwe:
            last_error = ValueError(f"MWE uniformity failed: {list(off.keys())[:3]}…")
            continue
        return obj, api_calls
    raise ChatGPTError(message=f"Gloss repair failed after {attempts} attempts: {last_error}")

async def parse_chatgpt_annotation_response(
    response: str,
    simplified_elements: List[Any],
    processing_phase: str,
    previous_version='default',
    config_info: dict = {},
    callback=None,
) -> Dict[str, Any]:
    """
    Robust parse for annotation phases. Returns a dict that always includes:
      - 'api_calls': [APICall, ...]  (possibly empty)
    Plus, depending on phase:
      - 'analysis' and 'mwes' for 'mwe'
      - 'items' for 'translated'  (list of {'translated': ...})
      - 'elements' for other phases (your original usable_response_object)

    Failure policy:
      * Try strict parse → local normalization → GPT repair (for 'mwe' and 'translated').
      * If still failing, raise ChatGPTError.
    """
    print(f'parse_chatgpt_annotation_response("""{response}""", {simplified_elements}, ...')
    # derive tokens + MWE labels once
    tokens, labels = _tokens_and_mwe_map(simplified_elements)
    retry_limit = _retry_limit_from_config(config_info, default=2)
    api_calls: List[Any] = []

    # PHASE: MWE ---------------------------------------------------------
    if processing_phase == 'mwe':
        # 1) Try your existing helper (best case: keeps original intro/analysis).
        try:
            intro, obj = clara_chatgpt4.interpret_chat_gpt4_response_as_intro_and_json(
                response, object_type='list', callback=callback
            )
        except Exception:
            intro, obj = None, None

        # 2) Fallback: tolerant extraction + JSON load
        if obj is None:
            try:
                intro2, block = _extract_json_list_block(response)
                obj = _json_load_loose(block)
                intro = intro or intro2
            except Exception:
                # 3) Ask GPT to repair (no analysis preserved)
                kept, calls, _ = await _repair_mwe_with_gpt(response, [str(x) if not isinstance(x,str) else x for x in simplified_elements], config_info, callback)
                api_calls.extend(calls)
                return {'analysis': "", 'mwes': kept, 'api_calls': api_calls}

        # 4) Validate basic shape
        if not _is_list_of_lists_of_strings(obj):
            # Try GPT repair
            kept, calls, _ = await _repair_mwe_with_gpt(
                json.dumps(obj, ensure_ascii=False),  # show model what it tried
                [str(x) if not isinstance(x,str) else x for x in simplified_elements],
                config_info, callback
            )
            api_calls.extend(calls)
            return {'analysis': intro or "", 'mwes': kept, 'api_calls': api_calls}

        # 5) Enforce vocabulary
        seg_tokens = [e if isinstance(e, str) else e[0] for e in simplified_elements]
        seg_tokens = [_norm_apostrophes(t) for t in seg_tokens]

        kept, dropped = _validate_mwe_vocab(obj, seg_tokens)
        if dropped and callback:
            await post_task_update_async(
                callback,
                f"*** Warning: {len(dropped)} MWEs discarded (token not in segment).\n" +
                _mismatch_report(seg_tokens, [d[0] for d in dropped])
            )

        return {'analysis': intro or "", 'mwes': kept, 'api_calls': api_calls}

    # PHASE: translated --------------------------------------------------
    if processing_phase == 'translated':
        # Expect a list of [src, translated] pairs (per your current contract).
        try:
            response_object = clara_chatgpt4.interpret_chat_gpt4_response_as_json(
                response, object_type='list', callback=callback
            )
        except Exception:
            response_object = None

        def _valid_translated(obj: Any) -> bool:
            if not isinstance(obj, list):
                return False
            return all(isinstance(el, list) and len(el) >= 2 and isinstance(el[1], str) for el in obj)

        if not _valid_translated(response_object) or len(response_object) != len(simplified_elements):
            # Ask GPT to repair to the exact length
            tokens = [e if isinstance(e, str) else e[0] for e in simplified_elements]
            system = (
                "You will convert assistant output into a JSON list of translation pairs.\n"
                "Rules:\n"
                "1) Output VALID JSON only: a list of lists. Each inner list is [source_token, translated_string].\n"
                f"2) The output MUST have exactly {len(tokens)} items, one per source_token, IN THIS ORDER.\n"
                "3) Use the source token verbatim for the first element of each pair; do not change it.\n"
                "4) If you cannot translate a token, copy it as the translation rather than deleting it.\n"
                "5) No commentary, no code fences—JSON only."
            )
            user = (
                "Original assistant output to repair:\n"
                f"{response}\n\n"
                "Here is the exact sequence of source tokens:\n"
                f"{tokens}\n\n"
                "Return ONLY the JSON array as specified."
            )
            api = await clara_chatgpt4.get_api_chatgpt4_response(
                prompt=f"{system}\n\n{user}",
                config_info=config_info,
                callback=callback
            )
            api_calls.append(api)

            try:
                response_object = _json_load_loose(api.response)
            except Exception as e:
                try:
                    _, block = _extract_json_list_block(api.response)
                    response_object = _json_load_loose(block)
                except Exception:
                    raise ChatGPTError(message="Repair failed: could not coerce translation list to valid JSON.") from e

            if not _valid_translated(response_object) or len(response_object) != len(simplified_elements):
                raise ChatGPTError(message="Repair failed: translation list still invalid length/shape.")

        # Final validation and projection
        out = [{'translated': el[1]} for el in response_object]
        return {'items': out, 'api_calls': api_calls}

    # PHASE: lemma ---------------------------------------------------------
    if processing_phase == 'lemma':
        # Expect list of [token, lemma] or [token, lemma, UPOS] aligned to tokens
        try:
            obj = clara_chatgpt4.interpret_chat_gpt4_response_as_json(
                response, object_type='list', callback=callback
            )
        except Exception:
            obj = None

        def _passes_all(o):
            return (
                _valid_lemma_shape(o, len(simplified_elements)) and
                _enforce_token_match(o, simplified_elements)[0] and
                _check_mwe_uniform_value(o, labels, 1)[0]
            )

        if not _passes_all(obj):
            # Try tolerant extraction quickly
            if obj is None:
                try:
                    _, block = _extract_json_list_block(response)
                    obj = _json_load_loose(block)
                except Exception:
                    obj = None
            if obj is None or not _passes_all(obj):
                # GPT repair with retries
                fixed, calls = await _repair_lemma_with_gpt(
                    raw_response=response, tokens=tokens, labels=labels,
                    config_info=config_info, callback=callback, attempts=retry_limit
                )
                api_calls.extend(calls)
                obj = fixed

        # warn if any uniformity issue (shouldn’t happen post-repair)
        ok_mwe, offenders = _check_mwe_uniform_value(obj, labels, 1)
        if not ok_mwe and callback:
            await post_task_update_async(callback, f"*** Warning (lemma): non-uniform MWE lemmas {list(offenders.keys())[:5]}…")

        return {'items': obj, 'api_calls': api_calls}

    # PHASE: gloss ---------------------------------------------------------
    if processing_phase == 'gloss':
        # Expect list of [token, gloss] aligned to tokens
        try:
            obj = clara_chatgpt4.interpret_chat_gpt4_response_as_json(
                response, object_type='list', callback=callback
            )
        except Exception:
            obj = None

        def _passes_all(o):
            return (
                _valid_gloss_shape(o, len(simplified_elements)) and
                _enforce_token_match(o, simplified_elements)[0] and
                _check_mwe_uniform_value(o, labels, 1)[0]
            )

        if not _passes_all(obj):
            if obj is None:
                try:
                    _, block = _extract_json_list_block(response)
                    obj = _json_load_loose(block)
                except Exception:
                    obj = None
            if obj is None or not _passes_all(obj):
                fixed, calls = await _repair_gloss_with_gpt(
                    raw_response=response, tokens=tokens, labels=labels,
                    config_info=config_info, callback=callback, attempts=retry_limit
                )
                api_calls.extend(calls)
                obj = fixed

        ok_mwe, offenders = _check_mwe_uniform_value(obj, labels, 1)
        if not ok_mwe and callback:
            await post_task_update_async(callback, f"*** Warning (gloss): non-uniform MWE glosses {list(offenders.keys())[:5]}…")

        return {'items': obj, 'api_calls': api_calls}

##    if not isinstance(response_object, list):
##        raise ChatGPTError(message=f"Response is not a list: {response}")
##
##    usable = []
##    for element in response_object:
##        if not well_formed_element_in_annotation_response(element, processing_phase, previous_version=previous_version):
##            await post_task_update_async(callback, f'*** Warning: bad element {element} in annotation response, discarding')
##        else:
##            usable.append(element)
##
##    original_text = ' '.join([el if isinstance(el, str) else el[0] for el in simplified_elements])
##    annotated_text = ' '.join([el[0] for el in usable if isinstance(el, (list, tuple)) and el])
##    if _norm_ws(_norm_apostrophes(original_text)) != _norm_ws(_norm_apostrophes(annotated_text)):
##        warning = (
##            "*** Warning: original text and annotated text are different.\n"
##            f" Original text: {original_text}\n"
##            f"Annotated text: {annotated_text}"
##        )
##        await post_task_update_async(callback, warning)
##
##    return {'elements': usable, 'api_calls': api_calls}

#----------------------------------------

def simplified_element_list_to_text(simplified_elements):
    return ' '.join([ element if isinstance(element, str) else element[0]
                      for element in simplified_elements ])

def well_formed_element_in_annotation_response(element, processing_phase, previous_version='default'):
    if processing_phase == 'gloss' and previous_version == 'lemma':
        return isinstance(element, list) and len(element) == 3
    elif processing_phase == 'gloss':
        return isinstance(element, list) and len(element) == 2
    elif processing_phase == 'lemma':
        return isinstance(element, list) and len(element) == 3
    elif processing_phase == 'lemma_and_gloss':
        return isinstance(element, list) and len(element) == 4
    elif processing_phase == 'pinyin':
        return isinstance(element, list) and len(element) == 2
    elif processing_phase == 'translated':
        return isinstance(element, list) and len(element) == 2
    elif processing_phase == 'mwe':
        return isinstance(element, str) 

