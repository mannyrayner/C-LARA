
from .clara_internalise import internalize_text
from .clara_utils import post_task_update
from .clara_classes import MWEError

from itertools import product

def simplify_mwe_tagged_text(mwe_tagged_text):
    ( l2_language, l1_language ) = ( 'irrelevant', 'irrelevant' )
    text_object = internalize_text(mwe_tagged_text, l2_language, l1_language, 'mwe')
    #simplify_mwe_tagged_text_object(text_object)
    return text_object.to_text(annotation_type='mwe_minimal')

def simplify_mwe_tagged_text_object(text_object):
    for page in text_object.pages:
        for segment in page.segments:
            if 'analysis' in segment.annotations:
                segment.annotations['analysis'] = '(removed)'

def annotate_mwes_in_text(text_obj, callback=None):
    mwe_counter = 1
    for page in text_obj.pages:
        for segment in page.segments:
            mwes = segment.annotations.get('mwes', [])
            for mwe in mwes:
                mwe_id = f'mwe_{mwe_counter}'
                mwe_counter += 1
                mwe_text = ""
                mwe_length = len(mwe)
                
                positions = find_mwe_positions_for_segment(segment, mwe, callback=callback)
                
                last_pos = None
                for i, pos in enumerate(positions):
                    element = segment.content_elements[pos]
                    # Check if we need to add a space before the next word
                    if last_pos is not None and last_pos != pos - 1:
                        mwe_text += " "
                    mwe_text += element.content
                    last_pos = pos
                for pos in positions:
                    segment.content_elements[pos].annotations['mwe_id'] = mwe_id
                    segment.content_elements[pos].annotations['mwe_text'] = mwe_text
                    segment.content_elements[pos].annotations['mwe_length'] = mwe_length


def find_mwe_positions_for_segment(segment, mwe, callback=None):
    content_elements = segment.content_elements
    return find_mwe_positions_for_content_elements(content_elements, mwe)

def find_mwe_positions_for_content_elements(content_elements, mwe, callback=None):
    mwe_text = ' '.join(mwe)
    segment_text = ' '.join([ element.to_text(annotation_type='plain') for element in content_elements if element.type == 'Word' ])
    # Find all positions of each word in the MWE
    all_positions = []
    
    for word in mwe:
        positions = [i for i, element in enumerate(content_elements) if element.type == 'Word' and element.content == word]
        if not positions:
            message = f"MWE error: the word '{word}' in the MWE '{mwe_text}' is not one of the words in '{segment_text}'."
            post_task_update(callback, message)
            raise MWEError(message = message)
        all_positions.append(positions)
    
    # Generate all possible combinations of positions and filter out invalid ones
    best_combination = None
    min_distance = float('inf')
    
    for combination in product(*all_positions):
        if all(combination[i] < combination[i+1] for i in range(len(combination) - 1)):
            distance = sum(combination[i+1] - combination[i] for i in range(len(combination) - 1))
            if distance < min_distance:
                min_distance = distance
                best_combination = combination
                
    if best_combination is None:
        message = f"MWE error: unable to find valid combination for MWE '{mwe}' in segment '{segment_text}'."
        post_task_update(callback, message)
        raise MWEError(message = message)
    
    return list(best_combination)


