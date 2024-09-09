# clara_align_with_segmented.py

from .clara_internalise import internalize_text
from .clara_classes import Text, Page, Segment, ContentElement, DiffElement

from typing import List
import difflib
import pprint

def align_segmented_text_with_non_segmented_text(segmented: str, non_segmented: str, l2_language: str, l1_language: str, text_type: str) -> str:
    """
    Aligns the segmented text with a non-segmented version, ensuring structural consistency.

    Parameters:
    - segmented: str, the segmented text string.
    - non_segmented: str, the non-segmented text string to be aligned..
    - l2_language: str, the target language (L2).
    - l1_language: str, the annotation language (L1).
    - text_type: str, the type of non-segmented text ('mwe', 'translated', 'lemma', 'gloss').

    Returns:
    - str: The realigned non-segmented text string.
    """

    #print(f'segmented = {segmented}')
    #print(f'non_segmented = {non_segmented}')
    
    # Step 1: Convert both texts to DiffElements
    segmented_diff = text_to_diff_elements_full(segmented, l2_language, l1_language, 'segmented')
    non_segmented_diff = text_to_diff_elements_full(non_segmented, l2_language, l1_language, text_type)

    #print(f'segmented_diff = ')
    #pprint.pprint(segmented_diff)
    #print(f'non_segmented_diff = ')
    #pprint.pprint(non_segmented_diff)

    # Step 2: Extract content for difflib
    segmented_content = [de.content for de in segmented_diff]
    non_segmented_content = [de.content for de in non_segmented_diff]

    # Step 3: Compute the diff
    diff = difflib.SequenceMatcher(None, segmented_content, non_segmented_content)

    aligned_non_segmented = []
    for tag, i1, i2, j1, j2 in diff.get_opcodes():
        if tag == 'equal':
            aligned_non_segmented.extend(non_segmented_diff[j1:j2])
        elif tag == 'insert':
            # B1: Discard inserts in non-segmented text
            pass  # Do nothing
        elif tag == 'delete':
            # B2: Add placeholders for deletes in segmented text
            for index in range(i1, i2):
                content = segmented_diff[index].content
                placeholder_annotations = get_placeholder_annotations(content, text_type)
                aligned_non_segmented.append(DiffElement('ContentElement', content, placeholder_annotations))
        elif tag == 'replace':
            # Handle replacements as delete + insert
            for index in range(i1, i2):
                content = segmented_diff[index].content
                placeholder_annotations = get_placeholder_annotations(content, text_type)
                aligned_non_segmented.append(DiffElement('ContentElement', content, placeholder_annotations))

    # Step 4: Convert aligned DiffElements back to Text object
    #print(f'aligned_non_segmented = ')
    #pprint.pprint(aligned_non_segmented)
    
    aligned_text = diff_elements_to_text(aligned_non_segmented, l2_language, l1_language, text_type)

    #print(f'aligned_text = {aligned_text}')

    return aligned_text

def get_placeholder_annotations(content: str, text_type: str) -> dict:
    """
    Generates placeholder annotations based on the content and version type.

    Parameters:
    - text_type: str, the type of non-segmented text.

    Returns:
    - dict: A dictionary of placeholder annotations.
    """
    placeholders = {
        'mwe': {'mwe': {'mwes': [], 'analysis': ''}},
        'translated': {'translated': ''},
        'lemma': {'lemma': '-', 'pos': 'X'},
        'gloss': {'gloss': '-'},
    }

    # mwe and translated have annotations on the closing segment boundary but not on content elements
    if text_type in ( 'mwe', 'translated' ):
        if content == '</segment>':
            return placeholders.get(text_type, {})
        else:
            return {}
    # Otherwise we don't have annotations on segment boundaries
    elif content in ( '<segment>', '</segment>', '<page>', '</page>' ):
        return {}
    else:
        return placeholders.get(text_type, {})

def text_to_diff_elements_full(text: str, l2_language: str, l1_language: str, text_type: str) -> List[DiffElement]:
 
    """
    Converts a text string into a list of DiffElements, preserving all annotations and structural information.

    Parameters:
    - text: str, the input text string to be converted.
    - l2_language: str, the target language (L2).
    - l1_language: str, the annotation language (L1).
    - text_type: str, the type of text (e.g., 'segmented', 'mwe', 'translated', 'gloss', 'lemma').

    Returns:
    - List[DiffElement]: A list of DiffElements representing the text structure and content.
    """
    # Step 1: Internalize the text
    internal_text = internalize_text(text, l2_language, l1_language, text_type)

    diff_elements = []

    for page in internal_text.pages:

        #Add page boundary
        diff_elements.append(DiffElement('Tag', '<page>', {}))
        
        for segment in page.segments:

            # Add segment boundary
            diff_elements.append(DiffElement('Tag', '<segment>', {}))
            
            for element in segment.content_elements:
                
                # Create the DiffElement
                diff_element = DiffElement(element.type, element.content, element.annotations)
                diff_elements.append(diff_element)
            
            # Add segment boundary
            diff_elements.append(DiffElement('Tag', '</segment>', segment.annotations))
        
        # Add page boundary
        diff_elements.append(DiffElement('Tag', '</page>', {}))
    
    return diff_elements

def diff_elements_to_text(diff_elements: List[DiffElement], l2_language: str, l1_language: str, text_type: str) -> str:
    """
    Converts a list of DiffElements back into a text string by first building a Text object.

    Parameters:
    - diff_elements: List[DiffElement], the list of DiffElements representing the text structure and content.
    - l2_language: str, the target language (L2).
    - l1_language: str, the annotation language (L1).
    - text_type: str, the type of text (e.g., 'segmented', 'mwe', 'translated', 'gloss', 'lemma').

    Returns:
    - str: The reconstructed text string.
    """
    # Stage 1: Build the Text object
    text_object = diff_elements_to_text_object(diff_elements, l2_language, l1_language)
    
    # Stage 2: Convert the Text object to a string using the to_text method
    return text_object.to_text(annotation_type=text_type)

def diff_elements_to_text_object(diff_elements: List[DiffElement], l2_language: str, l1_language: str) -> Text:
    """
    Convert a list of DiffElements back into a Text object, preserving all annotations and structural information.

    Parameters:
    - diff_elements: List[DiffElement], the list of DiffElements representing the text structure and content.
    - l2_language: str, the target language (L2).
    - l1_language: str, the annotation language (L1).

    Returns:
    - Text: The reconstructed Text object.
    """
    pages = []
    current_page = []
    current_segment = []
    
    for element in diff_elements:
        if element.content == '<page>':
            current_page = []
        elif element.content == '</page>':
            # Add the current page to the list of pages
            pages.append(Page(current_page))
        elif element.content == '<segment>':
            current_segment = []
        elif element.content == '</segment>':
            # Create a Segment object with content elements
            segment_annotations = element.annotations
            current_page.append(Segment(current_segment, annotations=segment_annotations))
        else:
            # Add ContentElement to the current segment
            current_segment.append(ContentElement(element.type, element.content, annotations=element.annotations))
    
    # Create and return the Text object
    return Text(pages=pages, l2_language=l2_language, l1_language=l1_language)

