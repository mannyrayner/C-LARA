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

    def __init__(self):
        pass

    def annotate_text(self, text):
        concordance = defaultdict(lambda: {"segments": set(), "frequency": 0})  # Change the default value to a custom dictionary
        page_number = 1
        segment_uid = 1
        segment_id_mapping = {}

        for page in text.pages:
            for segment in page.segments:
                segment.annotations['page_number'] = page_number
                segment.annotations['segment_uid'] = f"seg_{segment_uid}"
                segment_id_mapping[segment.annotations['segment_uid']] = segment
                segment_uid += 1

                for element in segment.content_elements:
                    if element.type == "Word":
                        lemma = element.annotations.get('lemma')
                        if lemma:
                            concordance[lemma]["segments"].add(segment.annotations['segment_uid'])  # Add the segment UID to the set
                            concordance[lemma]["frequency"] += 1

            page_number += 1

        # Convert the sets of segment UIDs back to lists of unique segments
        for lemma, lemma_data in concordance.items():
            unique_segments = [segment_id_mapping[seg_uid] for seg_uid in lemma_data["segments"]]
            concordance[lemma]["segments"] = unique_segments

        text.annotations['concordance'] = dict(concordance)
        return text
