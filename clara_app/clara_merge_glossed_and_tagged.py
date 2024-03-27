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

def merge_annotations1_and_annotations2(annotations1_text, annotations2_text, operation, dummy_annotations1):
    merged_pages = []

    for annotations1_page, annotations2_page in zip(annotations1_text.pages, annotations2_text.pages):
        merged_segments = []

        for annotations1_segment, annotations2_segment in zip(annotations1_page.segments, annotations2_page.segments):
            matcher = difflib.SequenceMatcher(None, annotations1_segment.content_elements, annotations2_segment.content_elements)

            merged_elements = []

            for operation, i1, i2, j1, j2 in matcher.get_opcodes():
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

            merged_segments.append(Segment(merged_elements))

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
