"""
clara_concordance_annotator.py

This module implements a Concordance annotator that can create a concordance annotation for a given Text object.

Classes:
- ConcordanceAnnotator: Class for handling concordance annotations for a Text object.

The ConcordanceAnnotator class provides a method for annotating a Text object with a concordance. The concordance is a dictionary containing lemma frequencies and segment references.
"""

import re
from collections import defaultdict

class ConcordanceAnnotator:

    def __init__(self, concordance_id=None):
        self.concordance_id = concordance_id

    def annotate_text(self, text, phonetic=False):
        concordance = defaultdict(lambda: {"segments": set(), "frequency": 0})
        page_number = 1
        segment_uid = 1
        segment_id_mapping = {}

        for page in text.pages:
            for segment in page.segments:
                segment.annotations['page_number'] = page_number
                segment.annotations['segment_uid'] = f"seg_{segment_uid}" if not self.concordance_id else f"seg_{self.concordance_id}_{segment_uid}"
                segment_id_mapping[segment.annotations['segment_uid']] = segment
                segment_uid += 1

                for element in segment.content_elements:
                    if element.type == "Word":
                        key = element.annotations.get('phonetic') if phonetic else element.annotations.get('lemma')
                        if key:
                            concordance[key]["segments"].add(segment.annotations['segment_uid'])
                            concordance[key]["frequency"] += 1
                    elif not phonetic and element.type == "Image" and 'transformed_segments' in element.content and element.content['transformed_segments']:
                        image_segments = element.content['transformed_segments']
                        for image_segment in image_segments:
                            for image_element in image_segment.content_elements:
                                if image_element.type == "Word":
                                    image_key = image_element.annotations.get('lemma')
                                    if image_key:
                                        concordance[image_key]["segments"].add(segment.annotations['segment_uid'])
                                        concordance[image_key]["frequency"] += 1

            page_number += 1

        for lemma, lemma_data in concordance.items():
            unique_segments = [segment_id_mapping[seg_uid] for seg_uid in lemma_data["segments"]]
            concordance[lemma]["segments"] = unique_segments

        text.annotations['concordance'] = dict(concordance)
        return text
