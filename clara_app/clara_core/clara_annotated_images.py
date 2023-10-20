# Images with associated text

from .clara_internalise import internalize_text
from .clara_classes import Text, Page, Segment, ContentElement
from .clara_utils import basename

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

def add_image_to_text(text_object, image):
    target_page_index = image.page - 1  # Assuming page numbers start from 1
    line_break_element = ContentElement("NonWordText", "\n\n")
    image_element = ContentElement("Image", {'src': basename(image.image_file_path)})

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
        target_segment.content_elements.insert(0, line_break_element)
        target_segment.content_elements.insert(0, image_element)
    elif image.position == 'bottom':
        # Insert the image element at the end of the last segment
        target_segment = target_page.segments[-1]
        target_segment.content_elements.append(line_break_element)
        target_segment.content_elements.append(image_element)
