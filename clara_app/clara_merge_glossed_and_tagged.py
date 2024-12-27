"""
This module contains functions to merge two differently annotated texts into a single internal representation using the
`Text`, `Page`, `Segment`, and `ContentElement` classes defined in `clara_classes.py`.

The main functions are:

1. merge_glossed_and_tagged(glossed_text, tagged_text): 
   Takes a glossed `Text` object and a tagged `Text` object,
   and returns a merged glossed and tagged `Text` object.

2. merge_glossed_and_tagged_with_pinyin(glossed_and_tagged_text, pinyin_annotated_text): 
   Takes a glossed and tagged `Text` object and a pinyin-tagged `Text` object,
   and returns a merged `Text` object with all three types of annotations.

"""

from .clara_classes import *

import difflib

def merge_glossed_and_tagged(glossed_text, tagged_text):
    return merge_annotations1_and_annotations2(glossed_text, tagged_text,
                                               'glossed_with_tagged', {"gloss": "null"})

def merge_glossed_and_tagged_with_pinyin(glossed_and_tagged_text, pinyin_annotated_text):
    return merge_annotations1_and_annotations2(glossed_and_tagged_text, pinyin_annotated_text,
                                               'glossed_and_tagged_with_pinyin', {"gloss": "null", "lemma": "null", "pos": "null"})

def merge_with_translation_annotations(original_text, translated_text):
    return merge_annotations1_and_annotations2(original_text, translated_text,
                                               'merge_with_translation_annotations', {"gloss": "null", "lemma": "null", "pos": "null"})

def merge_with_mwe_annotations(original_text, mwe_tagged_text):
    return merge_annotations1_and_annotations2(original_text, mwe_tagged_text,
                                               'merge_with_mwe_annotations', {"gloss": "null", "lemma": "null", "pos": "null"})

def merge_annotations1_and_annotations2(annotations1_text, annotations2_text, operation, dummy_annotations1):
    merged_pages = []

    for annotations1_page, annotations2_page in zip(annotations1_text.pages, annotations2_text.pages):
        merged_segments = []

        for annotations1_segment, annotations2_segment in zip(annotations1_page.segments, annotations2_page.segments):
            #matcher = difflib.SequenceMatcher(None, annotations1_segment.content_elements, annotations2_segment.content_elements)
            annotations1_strings = [ el.content for el in annotations1_segment.content_elements ]
            annotations2_strings = [ el.content for el in annotations2_segment.content_elements ]
            matcher = difflib.SequenceMatcher(None, annotations1_strings, annotations2_strings)

            merged_elements = []

            for operation, i1, i2, j1, j2 in matcher.get_opcodes():
                #print(f'operation = {operation}, i1 = {i1}, i2 = {i2}, j1 = {j1}, j2 = {j2}')
                if operation == "equal":
                    for annotations1_element, annotations2_element in zip(annotations1_segment.content_elements[i1:i2], annotations2_segment.content_elements[j1:j2]):
                        merged_element = merge_elements(annotations1_element, annotations2_element)
                        merged_elements.append(merged_element)
                elif operation == "replace":
                    for annotations2_element in annotations2_segment.content_elements[j1:j2]:
                        annotations1_element = find_best_match(annotations2_element, annotations1_segment.content_elements[i1:i2], dummy_annotations1)
                        merged_element = merge_elements(annotations1_element, annotations2_element)
                        merged_elements.append(merged_element)
                elif operation == "insert":
                    for annotations2_element in annotations2_segment.content_elements[j1:j2]:
                        dummy_annotations1_element = ContentElement("Word", annotations2_element.content, dummy_annotations1)
                        merged_element = merge_elements(dummy_annotations1_element, annotations2_element)
                        merged_elements.append(merged_element)

            # Merge segment-level annotations
            merged_annotations = annotations1_segment.annotations.copy()
            merged_annotations.update(annotations2_segment.annotations)
            
            merged_segments.append(Segment(merged_elements, annotations=merged_annotations))

        # Assume that annotations1_page and annotations2_page have the same annotations
        merged_pages.append(Page(merged_segments, annotations=annotations1_page.annotations))

    merged_text = Text(merged_pages, annotations1_text.l2_language, annotations1_text.l1_language)
    return merged_text


def merge_elements(annotations1_element, annotations2_element):
    annotations = {}
    annotations.update(annotations1_element.annotations)
    annotations.update(annotations2_element.annotations)

    return ContentElement(annotations2_element.type, annotations2_element.content, annotations)

def find_best_match(annotations2_element, annotations1_elements, dummy_annotations1):
    best_match = None
    best_similarity = -1

    for annotations1_element in annotations1_elements:
        similarity = difflib.SequenceMatcher(None, annotations2_element.content, annotations1_element.content).ratio()
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = annotations1_element

    if best_match is None:
        best_match = ContentElement("Word", annotations2_element.content, dummy_annotations1)

    return best_match

def merge_annotations_charwise(original_text: str, annotated_text: str, phase: str) -> str:
    """
    Merge GPT-4's newly inserted markup tokens into 'original_text',
    preserving exactly the original text for all non-markup characters.

    phase is either 'presegmentation' or 'segmentation'
    """

    if not phase in ( 'presegmentation', 'segmentation' ):
        raise ValueError(f"Unknown third argument {phase} in call to merge_annotations_charwise. Must be 'presegmentation' or 'segmentation'")

    original_chars = list(original_text)
    annotated_chars = list(annotated_text)

    matcher = difflib.SequenceMatcher(None, original_chars, annotated_chars)
    merged_chars = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        # The slices:
        #   original slice -> original_chars[i1:i2]
        #   annotated slice -> annotated_chars[j1:j2]

        if tag == "equal":
            # Nothing has changed in this region => copy original
            merged_chars.extend(original_chars[i1:i2])

        elif tag == "delete":
            # GPT removed something from the original.
            # We keep the original text as is, so copy the "delete" region from the original.
            merged_chars.extend(original_chars[i1:i2])

        elif tag == "insert":
            # GPT inserted something new. We ignore normal chars, only insert known markup.
            to_insert = annotated_chars[j1:j2]
            # We can parse these inserted chars to see if they contain tokens like "<page>" or "||"
            # E.g. do a small while-loop scanning for markup tokens
            merged_chars.extend(extract_markup_token(to_insert, phase))

        elif tag == "replace":
            # GPT replaced some region of original with something else.
            # We want to preserve the original region plus any recognized markup from GPT's replacement.
            # So we copy the original text:
            merged_chars.extend(original_chars[i1:i2])

            # Then also look for new markup tokens from the annotated region
            to_insert = annotated_chars[j1:j2]
            merged_chars.extend(extract_markup_token(to_insert, phase))

    return "".join(merged_chars)


def extract_markup_token(chars: list[str], phase: str) -> list[str]:
    """
    Extract a possible markup token, depending on the phase.

    We exploit the structure of the markup: we only ever need one token, since consecutive tokens are never useful.
    """

    if not phase in ( 'presegmentation', 'segmentation' ):
        raise ValueError(f"Unknown second argument {phase} in call to extract_markup_token. Must be 'presegmentation' or 'segmentation'")

    marked_up_string = ''.join(chars)

    # Default is no markup material to add.
    token_string = ''
    
    if phase == 'presegmentation':
        if '<page>' in marked_up_string:
            # In presegmentation mode, if we have a <page>, then a preceding or following || is possible but irrelevant.
            token_string = '<page>'
        elif '||' in marked_up_string:
            # In presegmentation mode, a || with no <page> cannot meaninfully be combined with other material.
            token_string = '||'
    elif phase == 'segmentation':
        if '|' in marked_up_string:
            # In segmentation mode, a | cannot meaninfully be combined with other material.
            token_string = '|'

    return list(token_string)



