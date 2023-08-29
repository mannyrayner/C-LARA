"""Diff two Text objects of the same type and return information as required.

Main function: diff_text_objects(internalised_text1, internalised_text2, version, required)

- internalised_text1 and internalised_text2 are Text objects
- version is one of ( "plain", "summary", "segmented", "gloss", "lemma" )
- required is a list specifying the types of information to return.
  Currently supported options are { 'error_rate', 'details' }.
  'error_rate' gives a simple error rate.
  'details' gives a string with a formatted version of the text showing highlighted differences.

Returns a dict indexed by the elements of "required"
"""

from .clara_classes import *
from typing import List, Dict, Tuple, Optional, Union

import difflib
import re
import regex
import json

def diff_text_objects(internalised_text1: Text, internalised_text2: Text, version: str, required: List[str]) -> Dict[str, Union[float, str]]:
    diff_elements1 = text_to_diff_elements(internalised_text1, version)
    diff_elements2 = text_to_diff_elements(internalised_text2, version)

    diff_elements = diff_diff_elements(diff_elements1, diff_elements2)

    response = {}
    if 'error_rate' in required:
        response['error_rate'] = diff_elements_to_error_rate(diff_elements, version)
    if 'details' in required:
        response['details'] = diff_elements_to_details(diff_elements)
    return response

# Linearise a Text object as a list of DiffElements.
# Add DiffElements to represent the word, segment and page boundaries, placing them after the relevant segments and pages.
# Only add word boundaries where they're relevant, i.e. between two ContentElements of type Word.
# Don't add boundaries if we have a "plain" version, since the text is meant to be unannotated.
# In 'gloss' or 'lemma' mode, the # signs separate.
def text_to_diff_elements(text: Text, version: str) -> List[DiffElement]:
    # Remove the POS information before diffing, since it's both unreliable and often irrelevant
    def remove_pos_from_annotations(annotations):
        return { key: annotations[key] for key in annotations if key != 'pos' }
    
    diff_elements = []

    for page in text.pages:
        for segment in page.segments:
            last_type = None
            for element in segment.content_elements:
                this_type = element.type
                if version == 'segmented' and last_type == 'Word' and this_type == 'Word':
                    diff_elements.append(DiffElement('ContentElement', '|', {}))
                diff_elements.append(DiffElement('ContentElement',
                                                 element.content,
                                                 remove_pos_from_annotations(element.annotations)))
                last_type = this_type
            if version != 'plain':
                diff_elements.append(DiffElement('ContentElement', '||', {}))
        if version != 'plain':
            diff_elements.append(DiffElement('ContentElement', '\n[page]\n', {}))
        
    return diff_elements

# Use difflib to create a diff of two DiffElement lists as a third DiffElement list.
def diff_diff_elements(elements1: List[DiffElement], elements2: List[DiffElement]) -> List[DiffElement]:
    diff_elements = []

    # Align on the content fields of the DiffElement objects
    content1 = [el.content for el in elements1]
    content2 = [el.content for el in elements2]
    matcher = difflib.SequenceMatcher(None, content1, content2, autojunk = False)

    for operation, i1, i2, j1, j2 in matcher.get_opcodes():
        # We align just on the content field, so an 'equal' doesn't means
        # that the annotation fields are necessarily the same
        if operation == 'equal' or ( operation == 'replace' and i2 - i1 == j2 - j1 ):
            for ( element1, element2 ) in zip(elements1[i1:i2], elements2[j1:j2]):
                diff_elements.append(diff_element_for_replace(element1, element2))
        elif operation == 'replace':
            for element in elements1[i1:i2]:
                diff_elements.append(DiffElement('DeletedElement', element.content, element.annotations))
            for element in elements2[j1:j2]:
                diff_elements.append(DiffElement('InsertedElement', element.content, element.annotations))
        elif operation == 'delete':
            for element in elements1[i1:i2]:
                diff_elements.append(DiffElement('DeletedElement', element.content, element.annotations))
        elif operation == 'insert':
            for element in elements2[j1:j2]:
                diff_elements.append(DiffElement('InsertedElement', element.content, element.annotations))

    return diff_elements

# Create a DiffElement to represent a replace operation.
# Handle the important case where the content is the same and the annotations have the same keys.
# Move the diff information into the annotations.
def diff_element_for_replace(element1, element2):
    ( content1, annotations1, keys1 ) = ( element1.content, element1.annotations, list(element1.annotations.keys()) )
    ( content2, annotations2, keys2 ) = ( element2.content, element2.annotations, list(element2.annotations.keys()) )

    if content1 == content2 and annotations1 == annotations2:
        return DiffElement('ContentElement', content1, annotations1)
    elif content1 == content2 and keys1 == keys2:
        annotations12 = {}
        for key in keys1:
            if annotations1[key] == annotations2[key]:
                value = annotations1[key]
            else:
                value = f'[deleted]{annotations1[key]}[/deleted][inserted]{annotations2[key]}[/inserted]'
            annotations12[key] = value
##        annotations12 = { key: f'[deleted]{annotations1[key]}[/deleted][inserted]{annotations2[key]}[/inserted]'
##                          for key in keys1 }
        return DiffElement('ContentElementWithSubstitution', content1, annotations12)
    else:
        return DiffElement('SubstitutedElement', '', { 'element1': element1, 'element2': element2 })

def diff_elements_to_error_rate(diff_elements: List[DiffElement], version: str) -> float:
    # Ignore whitespaces when calculating error rate. 
    diff_elements = [ e for e in diff_elements if not e.content.isspace() or e.type == 'SubstitutedElement' ]
    # Except in 'segmented' mode, we also ignore layout and punctuation.
    if version != 'segmented':
        diff_elements = [ e for e in diff_elements if not diff_element_is_only_punctuation_spaces_and_separators(e) ]
    error_diff_elements = [ e for e in diff_elements if e.type != 'ContentElement' ]
    total_elements = len(diff_elements)
    error_elements = len(error_diff_elements)

    #print(f'# total elements: {total_elements}')
    #print(f'# total elements: {[ e.content for e in diff_elements ]}')
    #print(f'error elements: {[ e.content for e in error_diff_elements ]}')

    if total_elements == 0:
        return 0.0

    # Return a percentage
    return 100.0 * error_elements / total_elements

def diff_element_is_only_punctuation_spaces_and_separators(e):
    if e.type == 'SubstitutedElement':
        return diff_element_is_only_punctuation_spaces_and_separators(e.annotations['element1']) and \
               diff_element_is_only_punctuation_spaces_and_separators(e.annotations['element2'])
    else:
        return string_is_only_punctuation_spaces_and_separators(e.content)

def string_is_only_punctuation_spaces_and_separators(s):
    s = s.replace('[page]', '')
    return all(regex.match(r"[\p{P} \n|]", c) for c in s)

def diff_elements_to_details(diff_elements: List[DiffElement]) -> str:
    details = []

    for element in diff_elements:
        details += single_diff_element_to_details(element)

    details_text = ''.join(details) if details != [] else ''
    # Condense any sequence of more than two line breaks into a double line break.
    # This means that some delete/insert pairs become trivial, so remove them.
    details_text = re.sub(r'\n{3,}', '\n\n', details_text)
    details_text = details_text.replace('[deleted]\n\n[/deleted][inserted]\n\n[/inserted]', '\n\n')
    details_text = re.sub(r'\n{3,}', '\n\n', details_text)
    #print(f'--- details_text: {json.dumps(details_text)}')
    return details_text 

def single_diff_element_to_details(element: DiffElement) -> str:
    #print(f'--- single_diff_element_to_details(DiffElement type = {element.type}, content = {element.content}, annotations = {element.annotations}')
    if element.type == 'SubstitutedElement':
        element1 = element.annotations['element1']
        element2 = element.annotations['element2']
        details1 = single_diff_element_to_details(DiffElement('DeletedElement', element1.content, element1.annotations))
        details2 = single_diff_element_to_details(DiffElement('InsertedElement', element2.content, element2.annotations))
        # Catch the special case where we have a diff of two NonWordTexts differing only by whitespace.
        # This messes up the formatting of the diff
        if element1.content.strip() == element2.content.strip() and element1.annotations == {} and element2.annotations == {}:
            result = details2
        else:
            result = details1 + details2
    else:                                         
        element_str = diff_element_content_and_annotations_to_str(element)
        if element.type in ( 'ContentElement', 'ContentElementWithSubstitution' ):
            result = [ element_str ]
        elif element.type == 'DeletedElement':
            result = [ f'[deleted]{element_str}[/deleted]' ]
        elif element.type == 'InsertedElement':
            result = [ f'[inserted]{element_str}[/inserted]' ]
    #print(f'--- Result: {result}')
    return result
    
def diff_element_content_and_annotations_to_str(element: DiffElement) -> str:
    content = element.content
    annotations = element.annotations
    if annotations == {}:
        return content
    else:
        formatted_annotations = '/'.join([ annotations[key] for key in annotations ])
        return f'{content}#{formatted_annotations}#'
