"""
This module contains functions to merge glossed and tagged texts into a single internal representation using the
`Text`, `Page`, `Segment`, and `ContentElement` classes defined in `clara_classes.py`.

The main function is:

1. merge_glossed_and_tagged(glossed_text, tagged_text): 
   Takes a glossed `Text` object and a tagged `Text` object, and returns a merged `Text` object.

It also includes helper functions:

1. merge_elements(glossed_element, tagged_element): Merges two `ContentElement` objects with gloss and tag annotations.
2. find_best_match(tagged_element, glossed_elements): Finds the best matching `ContentElement` in a list of glossed elements for a given tagged element.
"""

from .clara_classes import *

import difflib

def merge_glossed_and_tagged(glossed_text, tagged_text):
    merged_pages = []

    for glossed_page, tagged_page in zip(glossed_text.pages, tagged_text.pages):
        merged_segments = []

        for glossed_segment, tagged_segment in zip(glossed_page.segments, tagged_page.segments):
            matcher = difflib.SequenceMatcher(None, glossed_segment.content_elements, tagged_segment.content_elements)

            merged_elements = []

            for operation, i1, i2, j1, j2 in matcher.get_opcodes():
                if operation == "equal":
                    for glossed_element, tagged_element in zip(glossed_segment.content_elements[i1:i2], tagged_segment.content_elements[j1:j2]):
                        merged_element = merge_elements(glossed_element, tagged_element)
                        merged_elements.append(merged_element)
                elif operation == "replace":
                    for tagged_element in tagged_segment.content_elements[j1:j2]:
                        glossed_element = find_best_match(tagged_element, glossed_segment.content_elements[i1:i2])
                        merged_element = merge_elements(glossed_element, tagged_element)
                        merged_elements.append(merged_element)
                elif operation == "insert":
                    for tagged_element in tagged_segment.content_elements[j1:j2]:
                        dummy_glossed_element = ContentElement("Word", tagged_element.content, {"gloss": "null"})
                        merged_element = merge_elements(dummy_glossed_element, tagged_element)
                        merged_elements.append(merged_element)

            merged_segments.append(Segment(merged_elements))

        merged_pages.append(Page(merged_segments))

    merged_text = Text(merged_pages, glossed_text.l2_language, glossed_text.l1_language)
    return merged_text


def merge_elements(glossed_element, tagged_element):
    annotations = {}
    annotations.update(glossed_element.annotations)
    annotations.update(tagged_element.annotations)

    return ContentElement(tagged_element.type, tagged_element.content, annotations)

def find_best_match(tagged_element, glossed_elements):
    best_match = None
    best_similarity = -1

    for glossed_element in glossed_elements:
        similarity = difflib.SequenceMatcher(None, tagged_element.content, glossed_element.content).ratio()
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = glossed_element

    if best_match is None:
        best_match = ContentElement("Word", tagged_element.content, {"gloss": "null"})

    return best_match
