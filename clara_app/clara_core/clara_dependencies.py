

from .clara_utils import absolute_file_name, remove_duplicates_from_list_of_hashable_items

import traceback

_processing_phases = [
    "plain",                # Plain text
                            # Accessible from CLARAProjectInternal object
    
    "summary",              # Typically AI-generated summary
                            # Accessible from CLARAProjectInternal object
    
    "cefr_level",           # Typically AI-generated estimate of CEFR level
                            # Accessible from CLARAProjectInternal object 
    
    "segmented",            # Typically AI-generated segmented version of text
                            # Accessible from CLARAProjectInternal object
    
    "images",               # Typically AI-generated images
                            # Accessible from CLARAProjectInternal object
    
    "phonetic",             # Typically AI-generated phonetic version of text
                            # Only possible for languages with phonetic lexicon resources
                            # Accessible from CLARAProjectInternal object
    
    "gloss",                # Typically AI-generated glossed version of text
                            # Accessible from CLARAProjectInternal object
    
    "lemma",                # Typically AI-generated lemma-tagged version of text
                            # Accessible from CLARAProjectInternal object
    
    "audio",                # Declarations for how to attach audio to normal text
                            # If human-recorded audio is specified, the relevant audio files
                            # Accessible from CLARAProject object

    "audio_phonetic",       # Declarations for how to attach audio to phonetic text
                            # If human-recorded audio is specified, the relevant audio files
                            # Accessible from CLARAProject object
    
    "format_preferences",   # Declarations for formatting, e.g. font and text alignment
                            # Accessible from CLARAProject object
    
    "render",               # Rendered version of normal text
                            # Accessible from CLARAProjectInternal object

    "render_phonetic",      # Rendered version of phonetic text
                            # Accessible from CLARAProjectInternal object
    
    "social_network",       # Social network page if text is posted there
                            # Accessible from CLARAProject object
    ]

_immediate_dependencies = {
    "plain": [],
    
    "summary": [ "plain" ],
    
    "cefr_level": [ "plain" ],
    
    "segmented": [ "plain" ],
    
    "images": [ "segmented" ],
    
    "phonetic": [ "segmented" ],
    
    "gloss": [ "segmented" ],
    
    "lemma": [ "segmented" ],
    
    "audio": [ "segmented" ],
    
    "format_preferences": [ "segmented" ],
    
    "render": [ "gloss", "lemma", "images", "audio", "format_preferences" ],

    "render_phonetic": [ "phonetic", "images", "audio", "format_preferences" ],
    
    "social_network": [ "render", "render_phonetic", "summary", "cefr_level" ],
    }

def get_dependencies(processing_phase_id):
    all_dependencies = []
    
    if not processing_phase_id in _immediate_dependencies:
        return []
    
    for phase in _immediate_dependencies[processing_phase_id]:
        all_dependencies += get_dependencies[phase]
        
    return remove_duplicates_from_list_of_hashable_items(all_dependencies)

