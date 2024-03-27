"""
This module contains functions to internalize a text, converting it into the internal representation used by the
`Text`, `Page`, `Segment`, and `ContentElement` classes defined in `clara_classes.py`. 

The main function is:

1. internalize_text(input_text, l2_language, l1_language, text_type): 
   Takes an input text, its L2 language, L1 language, and the text_type (either 'segmented', 'gloss', 'lemma' or 'lemma_and_gloss'), 
   and returns a `Text` object with the internalized representation.

It also includes helper functions:

1. parse_content_elements(segment_text, type): Parses content elements from a segment string based on the text type.
2. parse_content_elements_segmented(segment_text): Parses content elements for segmented text.
3. parse_content_elements_glossed_or_tagged(segment_text, text_type): Parses content elements for glossed or tagged text.
4. split_escaped(string, delimiter): Splits a string at the specified delimiter, taking into account escaped delimiters.
"""

from .clara_classes import *
from . import clara_utils

import regex
import re
import pprint

def internalize_text(input_text, l2_language, l1_language, text_type):
    # Check if the first page starts with a <page> tag, if not prepend one
    if not input_text.startswith('<page'):
        input_text = '<page>' + input_text

    # Use re.split to also capture the attributes within the <page> tags
    split_text = re.split(r'<page\s*(.*?)>', input_text)
    
    # Remove the first empty string if it exists
    if split_text and not split_text[0]:
        split_text.pop(0)

    #print(f'split_text: {split_text}')

    internalized_pages = []

    for i in range(0, len(split_text), 2):
        page_attributes = split_text[i]
        page_text = split_text[i + 1] if i + 1 < len(split_text) else ''
        
        segments_text = page_text.split("||")
        internalized_segments = []

        for segment_text in segments_text:
            content_elements = parse_content_elements(segment_text, text_type)
            internalized_segments.append(Segment(content_elements))

        # Create a Page object with the internalized_segments and page_attributes
        page = Page(internalized_segments)
        if page_attributes:
            attributes = dict(re.findall(r"(\w+)='(.*?)'", page_attributes))
            page.annotations = attributes

        internalized_pages.append(page)

    internalized_text = Text(internalized_pages, l2_language=l2_language, l1_language=l1_language)
    return internalized_text

def parse_content_elements(segment_text, type):
    if type in ( 'plain', 'summary', 'title', 'cefr_level', 'segmented', 'segmented_title'):
        return parse_content_elements_segmented(segment_text)
    else:
        return parse_content_elements_glossed_or_tagged(segment_text, type)

def parse_content_elements_segmented(segment_text):
    content_elements = []
    pattern = r"(?:@[^@]+@|<\/?\w+>|(?:[^\s\p{P}<]|[#'@])+|\|(?:[^\s\p{P}|[#'@]])+|[\s\p{P}--[@#']]+)"
    words_and_elements = regex.findall(pattern, segment_text, regex.V1)

    for item in words_and_elements:
        if all(c.isspace() or regex.match(r"\p{P}", c) for c in item):
            content_elements.append(ContentElement("NonWordText", content=item, annotations={}))
        elif "@" in item:
            # Multi-word expression
            mwe = item.replace("@", "")
            content_elements.append(ContentElement("Word", content=mwe, annotations={}))
        elif item.startswith("<") and item.endswith(">"):
            # HTML markup
            content_elements.append(ContentElement("Markup", item))
        elif "|" in item:
            # Word with smaller pieces
            pieces = item.split("|")
            for piece in pieces:
                if piece != '':
                    content_elements.append(ContentElement("Word", content=piece, annotations={}))
        else:
            # Regular word
            content_elements.append(ContentElement("Word", content=item, annotations={}))

    return content_elements

def parse_content_elements_glossed_or_tagged(segment_text, text_type):
    #pattern = r"((?:<img[^>]*>|<audio[^>]*>|<\/?\w+>|@[^@]+@#(?:[^#|]|(?<=\\)#)*(?:\|[^#|]|(?<=\\)#)*#|(?:[^\s|#]|(?<=\\)#)*(?:\|[^\s|#]|(?<=\\)#)*#(?:[^#|]|(?<=\\)#)*(?:\|[^#|]|(?<=\\)#)*#|[\s\p{P}--[@#'\\]]+))"
    pattern = r"((?:<img[^>]*>|<audio[^>]*>|<\/?\w+>|@[^@]+@#(?:[^#|]|(?<=\\)#)*(?:\|[^#|]|(?<=\\)#)*#|(?:[^\s|#]|(?<=\\)#)*(?:\|[^\s|#]|(?<=\\)#)*#(?:[^#|]|(?<=\\)#)*(?:\|[^#|]|(?<=\\)#)*#|[\s\p{P}--[@#\\]]+))"
    words_with_annotations = regex.findall(pattern, segment_text, regex.V1)

    check_parsing_of_segment(segment_text, words_with_annotations, pattern)

    content_elements = []
    annotation_key = text_type
    
    for word_with_annotation in words_with_annotations:
        if all(c.isspace() or regex.match(r"\p{P}", c) for c in word_with_annotation):
            content_elements.append(ContentElement("NonWordText", content=word_with_annotation, annotations={}))
        elif "@" in word_with_annotation:
            # Multi-word expression
            word_with_annotation = word_with_annotation.replace("@", "")
            content_element = word_with_annotation_to_content_element(word_with_annotation, annotation_key)
            content_elements.append(content_element)
        elif "|" in word_with_annotation:
            # Word with smaller pieces
            pieces = word_with_annotation.split("|")
            for piece in pieces:
                if len(piece) != 0:
                    content_element = word_with_annotation_to_content_element(piece, annotation_key)
                    content_elements.append(content_element)
        elif word_with_annotation.startswith("<img") or word_with_annotation.startswith("<audio"):
            # Embedded image or audio
            attributes = regex.findall(r'(\w+)=[\'"]([^\'"]*)', word_with_annotation)
            attr_dict = {attr: value for attr, value in attributes}
            content_elements.append(ContentElement("Embedded", attr_dict))
        elif word_with_annotation.startswith("<") and word_with_annotation.endswith(">"):
            # HTML markup
            content_elements.append(ContentElement("Markup", word_with_annotation))
        else:
            # Regular word
            content_element = word_with_annotation_to_content_element(word_with_annotation, annotation_key)
            if content_element:
                content_elements.append(content_element)

    return content_elements

# Raise an InternalisationError exception if the pieces found by the regex don't match the whole string
def check_parsing_of_segment(segment_text, words_with_annotations, pattern):
    parsed_text = ''.join(words_with_annotations)
    # Remove any | boundaries before comparing is maybe safer, since we're discarding them anyway
    if parsed_text.replace('|', '') != segment_text.replace('|', ''):
        reparse_segment_signalling_missing_text(segment_text, pattern)

def reparse_segment_signalling_missing_text(segment_text, pattern):
    words_with_annotations = []
    matches = []
    last_end = 0

    for match in regex.finditer(pattern, segment_text, regex.V1):
        words_with_annotations.append(match[0])
        matches.append((match.start(), match.end()))
        if match.start() > last_end:
            raise InternalisationError(message = f"Unable to internalise '{segment_text}'. Unaccounted text at position {last_end}: '{segment_text[last_end:match.start()]}'")
        last_end = match.end()
    # check for unaccounted text at the end
    if last_end != len(segment_text):
        raise InternalisationError(message = f"Unable to internalise '{segment_text}'. Unaccounted text at end: '{segment_text[last_end:]}'")

def word_with_annotation_to_content_element(word_with_annotation, annotation_key):
    components = split_escaped(word_with_annotation, "#")[:2]
    if len(components) == 0:
        return None
    elif len(components) == 1:
        content, annotation = ( components[0], 'NO_ANNOTATION' )
    else:
        content, annotation = components
    annotation_components = annotation.split('/')
    # Special case: if the text is lemma tagged, an item of the form Word#Lemma/POS# marks both a lemma and a POS tag
    if len(annotation_components) == 2 and annotation_key == 'lemma':
        lemma, pos = annotation_components
        return ContentElement("Word", content, {'lemma': lemma, 'pos': pos})
    elif len(annotation_components) != 3 and annotation_key == 'lemma_and_gloss':
        raise InternalisationError(message = f'Unable to internalise "{word_with_annotation}", not of form "Word#Lemma/POS/Gloss#')
    elif len(annotation_components) == 3 and annotation_key == 'lemma_and_gloss':
        lemma, pos, gloss = annotation_components
        return ContentElement("Word", content, {'lemma': lemma, 'pos': pos, 'gloss': gloss})
    else:
        return ContentElement("Word", content, {annotation_key: annotation})

def split_escaped(string, delimiter):
    parts = []
    current_part = []
    escaped = False

    for char in string:
        if char == delimiter and not escaped:
            parts.append(''.join(current_part))
            current_part = []
        else:
            if char == '\\' and not escaped:
                escaped = True
            else:
                if escaped:
                    escaped = False
                current_part.append(char)

    parts.append(''.join(current_part))

    return parts



