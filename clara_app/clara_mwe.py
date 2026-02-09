from .clara_internalise import internalize_text
from .clara_utils import post_task_update, post_task_update_async
from .clara_classes import MWEError

from itertools import product

import asyncio

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
                try:
                    positions = find_mwe_positions_for_segment(segment, mwe, callback=callback)
                    mwe_id = f'mwe_{mwe_counter}'
                    mwe_counter += 1
                    mwe_text = ""
                    mwe_length = len(mwe)
                    
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
                except MWEError as e:
                    continue


def find_mwe_positions_for_segment(segment, mwe, callback=None):
    content_elements = segment.content_elements
    return find_mwe_positions_for_content_elements(content_elements, mwe)

def find_mwe_positions_for_content_elements(content_elements, mwe, callback=None):
    #segment_text = ' '.join([ element.to_text(annotation_type='plain') for element in content_elements if element.type == 'Word' ])
    content_string_list = [ element.content for element in content_elements ]
    return find_mwe_positions_for_content_string_list(content_string_list, mwe, callback=callback)

def find_mwe_positions_for_content_string_list(content_string_list, mwe, callback=None):
    full_text = ' '.join(content_string_list)
    mwe_text = ' '.join(mwe)
    # Find all positions of each word in the MWE
    all_positions = []
    
    for word in mwe:
        positions = [i for i, element in enumerate(content_string_list) if element == word]
        if not positions:
            message = f"MWE error: the word '{word}' in the MWE '{mwe_text}' is not one of the words in '{full_text}'."
            #post_task_update(callback, message)
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
        message = f"MWE error: unable to find valid combination for MWE '{mwe_text}' in segment '{full_text}'."
        #post_task_update(callback, message)
        raise MWEError(message = message)
    
    return list(best_combination)

async def check_mwes_are_consistently_annotated(content_elements, mwes, processing_phase, callback=None):
    content_elements = [ content_element for content_element in content_elements if content_element.type in ( 'Word', 'NonWordText' ) ]
    #await post_task_update_async(callback, f'check_mwes_are_consistently_annotated({content_elements}, {mwes}, {processing_phase})')
    for mwe in mwes:
        positions = find_mwe_positions_for_content_elements(content_elements, mwe)
        annotations = [ annotation_for_processing_phase(content_elements[position], processing_phase) for position in positions ]
        if not all(annotation == annotations[0] for annotation in annotations) or annotations[0] == '-':
            message = f"MWE error: MWE '{mwe}' inconsistently annotated in '{content_elements}'."
            await post_task_update_async(callback, message)
            raise MWEError(message = message)

def annotation_for_processing_phase(content_element, processing_phase):
    annotations = content_element.annotations
    if processing_phase == 'gloss':
        return annotations['gloss'] if 'gloss' in annotations else '-'
    elif processing_phase == 'lemma':
        # We don't want to fail because POS is wrong
        return annotations['lemma'] if 'lemma' in annotations else '-'
    else:
        return None
    
