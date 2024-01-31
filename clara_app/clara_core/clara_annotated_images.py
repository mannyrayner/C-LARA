# Images with associated text

from .clara_internalise import internalize_text
from .clara_classes import Text, Page, Segment, ContentElement
from .clara_utils import basename, get_image_dimensions

from difflib import SequenceMatcher
import json

def make_uninstantiated_annotated_image_structure(image_id, segmented_text):
    # Initialize the top-level structure
    annotated_image_structure = {
        'image_id': image_id,
        'segments': []
    }
    
    # Internalize the segmented text using existing C-LARA functions
    internalized_text = internalize_text(segmented_text, l2_language=None, l1_language=None, text_type='segmented')
    
    # Loop through each segment in the internalized text
    for page in internalized_text.pages:
        for segment in page.segments:
            # Skip empty segments
            if len(segment.content_elements) == 0:
                continue
            
            # Initialize the second-level structure for each segment
            segment_structure = []
            
            # Loop through each content element in the segment
            for content_element in segment.content_elements:
                # Skip non-words
                if content_element.type != 'Word':
                    continue
                
                # Initialize the third-level structure for each lexical item
                lexical_item_structure = {
                    'item': content_element.content,
                    'coordinates': None
                }
                
                # Add the lexical item structure to the segment structure
                segment_structure.append(lexical_item_structure)
            
            # Add speaker and translation controls to the segment structure
            segment_structure.append({'item': 'SPEAKER-CONTROL', 'coordinates': None})
            segment_structure.append({'item': 'TRANSLATION-CONTROL', 'coordinates': None})
            
            # Add the segment structure to the top-level structure
            annotated_image_structure['segments'].append(segment_structure)
    
    return annotated_image_structure

def add_image_to_text(text_object, image, project_id_internal=None, callback=None):
    target_page_index = image.page - 1  # Assuming page numbers start from 1
    line_break_element = ContentElement("NonWordText", "\n\n")
    image_element = image_to_content_element(image, project_id_internal=project_id_internal, callback=callback)

    # Create new pages if the target page doesn't exist
    while len(text_object.pages) <= target_page_index:
        new_page = Page([Segment([])])
        text_object.pages.append(new_page)
    
    target_page = text_object.pages[target_page_index]

    # If the target page has no segments, add an empty one
    if not target_page.segments:
        target_page.segments.append(Segment([]))
    
    if image.position == 'top':
        # Insert the image element at the beginning of the first segment
        target_segment = target_page.segments[0]
        #target_segment.content_elements.insert(0, line_break_element)
        target_segment.content_elements.insert(0, image_element)
    elif image.position == 'bottom':
        # Insert the image element at the end of the last segment
        target_segment = target_page.segments[-1]
        #target_segment.content_elements.append(line_break_element)
        target_segment.content_elements.append(image_element)

def image_to_content_element(image, project_id_internal=None, callback=None):
    # Check if page_object or associated_areas exists
    #print(f'--- Calling image_to_content_element. page_object = {image.page_object}, associated_areas = {image.associated_areas}')
    width, height = get_image_dimensions(image.image_file_path, callback=callback)
    thumbnail_width, thumbnail_height = get_image_dimensions(image.thumbnail_file_path, callback=callback)
    if not image.page_object or not image.associated_areas:
        transformed_segments = None
    else:
        page_object_segments = image.page_object.segments
        associated_areas_segments = json.loads(image.associated_areas)['segments']
        transformed_segments = []
        for segment, associated_segment in zip(page_object_segments, associated_areas_segments):
            # Remove all non-word ContentElements
            words_only = [ce for ce in segment.content_elements if ce.type == 'Word']
            
            # Add speaker_control and translation_control to words_only for coordinate transfer
            words_only.extend([ContentElement('Word', 'SPEAKER-CONTROL', {}), ContentElement('Word', 'TRANSLATION-CONTROL', {})])
            
            # Use difflib to match words in segment with associated areas
            s = SequenceMatcher(None, [ce.content for ce in words_only], [area['item'] for area in associated_segment])
            for opcode, a0, a1, b0, b1 in s.get_opcodes():
                if opcode == 'equal':
                    for i, j in zip(range(a0, a1), range(b0, b1)):
                        #words_only[i].annotations['coordinates'] = associated_segment[j]['coordinates']
                        coordinates = associated_segment[j]['coordinates']
                        if coordinates:
                            if len(coordinates) == 2:  # Rectangle
                                x1, y1 = coordinates[0]
                                x2, y2 = coordinates[1]
                                words_only[i].annotations['shape'] = 'rectangle'
                                words_only[i].annotations['coordinates'] = {'x': x1, 'y': y1, 'width': x2 - x1, 'height': y2 - y1}
                            else:  # Polygon
                                words_only[i].annotations['shape'] = 'polygon'
                                words_only[i].annotations['coordinates'] = coordinates
            
            # Create a new segment with the transformed words
            transformed_segment = Segment(words_only)
            transformed_segments.append(transformed_segment)
    result = ContentElement('Image', {'src': basename(image.image_file_path),
                                      'project_id_internal': project_id_internal,
                                      'width': width,
                                      'height': height,
                                      'thumbnail_src': basename(image.thumbnail_file_path),
                                      'thumbnail_width': thumbnail_width,
                                      'thumbnail_height': thumbnail_height,
                                      'transformed_segments': transformed_segments})
    #print(f'--- Produced {result}') 
    return result
