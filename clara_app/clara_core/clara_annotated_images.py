from .clara_internalise import internalize_text

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
