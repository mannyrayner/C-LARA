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
import re

POSSIBLE_TAG_SEGMENT_OR_CONTENT_ELEMENT_PAIRS = [ ( 'lemma', 'content_elements' ),
                                                  ( 'gloss', 'content_elements' ),
                                                  ( 'pinyin', 'content_elements' ),
                                                  ( 'translated', 'segments' ),
                                                  ( 'mwes', 'segments' ),
                                                  ]

# text1, text2 should both be Text objects. Copy in values of the annotation 'tag' from text2 to text1.
# Throw an error if the texts are incompatible
def merge_text_object_with_other_text_object_exact(text1, text2, tag, segments_or_content_elements):
    if not isinstance(text1, Text):
        raise ValueError(f'First arg to merge_text_object_with_other_text_object not a Text: {text1}')
    if not isinstance(text2, Text):
        raise ValueError(f'Second arg to merge_text_object_with_other_text_object not a Text: {text2}')
    if not ( tag, segments_or_content_elements) in POSSIBLE_TAG_SEGMENT_OR_CONTENT_ELEMENT_PAIRS:
        raise ValueError(f'Impossible third and fourth args to merge_text_object_with_other_text_object: {tag}, {segments_or_content_elements}')

    pages1 = text1.pages
    pages2 = text2.pages
    if len(pages1) != len(pages2):
        Error = f"""Texts in call to merge_text_object_with_other_text_object have different numbers of pages:
tag = {tag}, len1 = {len(pages1)}, len2 = {len(pages2)}, first_page1 = {pages1[0]}, first_page2 = {pages2[0]},"""
        raise ValueError(Error)

    for page_index in range(0, len(pages1)):
        page1 = pages1[page_index]
        page2 = pages2[page_index]
        segments1 = page1.segments
        segments2 = page2.segments

        if len(segments1) != len(segments1):
            raise ValueError(f'Pages {page_index} in call to merge_text_object_with_other_text_object have different numbers of segments: {segments1}, {segments2}')

        for segment_index in range(0, len(segments1)):
            segment1 = segments1[segment_index]
            segment2 = segments2[segment_index]
            content_elements1 = segment1.content_elements
            content_elements2 = segment2.content_elements

            if len(content_elements1) != len(content_elements2):
                ErrorMessage = f"""Segments page = {page_index}, segment = {segment_index} in call to merge_text_object_with_other_text_object
have different numbers of content elements: {content_elements1}, {content_elements2}"""
                raise ValueError(ErrorMessage)
            
            if segments_or_content_elements == 'segments' and tag in segment2.annotations:
                seg_annotations1 = segment1.annotations
                seg_annotations1[tag] = segment2.annotations[tag]
                segment1.annotations = seg_annotations1

            if segments_or_content_elements == 'content_elements':
                for content_element_index in range(0, len(content_elements1)):
                    content_element1 = content_elements1[content_element_index]
                    content_element2 = content_elements2[content_element_index]

                    print(f'--- Merging {content_element1} and {content_element2}')

                    if content_element1.content != content_element2.content or content_element1.type != content_element2.type :
                        ErrorMessage = f"""Content elements page = {page_index}, segment = {segment_index} element = {content_element_index}
in call to merge_text_object_with_other_text_object have different content or type: {content_element1}, {content_element2}"""
                        raise ValueError(ErrorMessage)

                    content_annotations1 = content_element1.annotations
                    if tag in content_element2.annotations:
                        content_annotations1[tag] = content_element2.annotations[tag]
                    if tag == 'lemma' and 'pos' in content_element2.annotations:
                        content_annotations1['pos'] = content_element2.annotations['pos']
                    content_element1.annotations = content_annotations1

                    print(f'--- Result: {content_element1}')

    return text1                         

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

    #merge_annotations_charwise_trace = False
    merge_annotations_charwise_trace = True

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
            if merge_annotations_charwise_trace:
                print('-------------')
                print(f'equal: "{join_char_list(original_chars[i1:i2])}"')
                print(f'extend: "{join_char_list(original_chars[i1:i2])}"')

        elif tag == "delete":
            # GPT removed something from the original.
            # We keep the original text as is, so copy the "delete" region from the original.
            merged_chars.extend(original_chars[i1:i2])
            if merge_annotations_charwise_trace:
                print('-------------')
                print(f'delete: "{join_char_list(original_chars[i1:i2])}"')
                print(f'extend: "{join_char_list(original_chars[i1:i2])}"')

        elif tag == "insert":
            # GPT inserted something new. We ignore normal chars, only insert known markup.
##            to_insert = annotated_chars[j1:j2]
##            # We can parse these inserted chars to see if they contain tokens like "<page>" or "||"
##            # E.g. do a small while-loop scanning for markup tokens
##            merged_chars.extend(extract_markup_token(to_insert, phase))

            merged_chars.extend(extract_markup_tokens(annotated_chars[j1:j2], phase))
            if merge_annotations_charwise_trace:
                print('-------------')
                print(f'insert: "{join_char_list(annotated_chars[j1:j2])}"')
                print(f'extend: "{join_char_list(extract_markup_tokens(annotated_chars[j1:j2], phase))}"')

        elif tag == "replace":
            # GPT replaced some region of original with something else.
            # We want to preserve the original region plus any recognized markup from GPT's replacement.
            # So we copy the original text:
            merged_chars.extend(original_chars[i1:i2])

            # Then also look for new markup tokens from the annotated region
            to_insert = annotated_chars[j1:j2]
            merged_chars.extend(extract_markup_tokens(to_insert, phase))

            if merge_annotations_charwise_trace:
                print('-------------')
                print(f'replace: "{join_char_list(original_chars[i1:i2])}/{join_char_list(annotated_chars[j1:j2])}"')
                print(f'insert: "{join_char_list(annotated_chars[j1:j2])}"')
                print(f'extend: "{join_char_list(extract_markup_tokens(annotated_chars[j1:j2], phase))}"')
   
    return "".join(merged_chars)

def join_char_list(l):
    return ''.join(l)

##def extract_markup_token(chars: list[str], phase: str) -> list[str]:
##    """
##    Extract a possible markup token, depending on the phase.
##
##    We exploit the structure of the markup: we only ever need one token, since consecutive tokens are never useful.
##    """
##
##    if not phase in ( 'presegmentation', 'segmentation' ):
##        raise ValueError(f"Unknown second argument {phase} in call to extract_markup_token. Must be 'presegmentation' or 'segmentation'")
##
##    marked_up_string = ''.join(chars)
##
##    # Default is no markup material to add.
##    token_string = ''
##    
##    if phase == 'presegmentation':
##        if '<page>' in marked_up_string:
##            # In presegmentation mode, if we have a <page>, then a preceding or following || is possible but irrelevant.
##            token_string = '<page>'
##        elif '||' in marked_up_string:
##            # In presegmentation mode, a || with no <page> cannot meaninfully be combined with other material.
##            token_string = '||'
##    elif phase == 'segmentation':
##        if '@' in marked_up_string:
##            # In segmentation mode, if we have a @, then a preceding or following | is possible but irrelevant.
##            token_string = '@'
##        elif '|' in marked_up_string:
##            # In segmentation mode, a | with no @ cannot meaninfully be combined with other material.
##            token_string = '|'
##        
##
##    return list(token_string)


_PRESEG_TOKENS = re.compile(r'(?:<page>|\|\|)')
_SEG_TOKENS    = re.compile(r'(?:@|\|)')  # will match each '|' individually

def extract_markup_tokens(chars: list[str], phase: str) -> list[str]:
    if phase not in ('presegmentation', 'segmentation'):
        raise ValueError(f"Unknown phase {phase}")

    s = ''.join(chars)
    if phase == 'presegmentation':
        toks = [m.group(0) for m in _PRESEG_TOKENS.finditer(s)]
    else:
        toks = [m.group(0) for m in _SEG_TOKENS.finditer(s)]

    # Return as a flat list of characters for the caller’s extend()
    return list(''.join(toks))
