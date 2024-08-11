
from .clara_internalise import internalize_text

from itertools import product

def simplify_mwe_tagged_text(mwe_tagged_text):
    ( l2_language, l1_language ) = ( 'irrelevant', 'irrelevant' )
    text_object = internalize_text(mwe_tagged_text, l2_language, l1_language, 'mwe')
    simplify_mwe_tagged_text_object(text_object)
    return text_object.to_text(annotation_type='mwe')

def simplify_mwe_tagged_text_object(text_object):
    for page in text_object.pages:
        for segment in page.segments:
            if 'analysis' in segment.annotations:
                segment.annotations['analysis'] = '(removed)'

##def annotate_mwes_in_text(text):
##    mwe_counter = 1
##    
##    for page in text.pages:
##        for segment in page.segments:
##            mwes = segment.annotations.get('mwes', [])
##            
##            for mwe in mwes:
##                mwe_id = f'mwe_{mwe_counter}'
##                mwe_counter += 1
##                mwe_text = ' '.join(mwe)
##                
##                match_positions = find_mwe_positions(segment.content_elements, mwe)
##                
##                for i, position in enumerate(match_positions):
##                    content_element = segment.content_elements[position]
##                    content_element.annotations['mwe_id'] = mwe_id
##                    content_element.annotations['mwe_text'] = mwe_text

def annotate_mwes_in_text(text_obj):
    mwe_counter = 1
    for page in text_obj.pages:
        for segment in page.segments:
            mwes = segment.annotations.get('mwes', [])
            for mwe in mwes:
                mwe_id = f'mwe_{mwe_counter}'
                mwe_counter += 1
                mwe_text = ""
                
                positions = find_mwe_positions(segment, mwe)
                
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


def find_mwe_positions(segment, mwe):
    content_elements = segment.content_elements
    segment_text = segment.to_text(annotation_type='segmented')
    # Find all positions of each word in the MWE
    all_positions = []
    
    for word in mwe:
        positions = [i for i, element in enumerate(content_elements) if element.type == 'Word' and element.content == word]
        if not positions:
            raise ValueError(f"Unable to find word '{word}' in segment '{segment_text}'.")
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
        raise ValueError(f"Unable to find valid combination for MWE '{mwe}' in segment '{segment_text}'.")
    
    return list(best_combination)


