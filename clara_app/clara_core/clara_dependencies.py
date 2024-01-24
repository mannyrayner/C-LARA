

from .clara_utils import absolute_file_name, remove_duplicates_from_list_of_hashable_items, get_file_time

import traceback

_processing_phases = [
    "plain",                # Plain text
                            # Accessible from CLARAProjectInternal object
    
    "summary",              # Typically AI-generated summary
                            # Accessible from CLARAProjectInternal object
    
    "cefr_level",           # Typically AI-generated estimate of CEFR level
                            # Accessible from CLARAProjectInternal object

    "title",                # Typically AI-generated title for first page of text
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

    "title": [ "plain" ],
    
    "segmented": [ "plain" ],
    
    "images": [ "segmented" ],
    
    "phonetic": [ "segmented", "title" ],
    
    "gloss": [ "segmented", "title" ],
    
    "lemma": [ "segmented", "title" ],
    
    "audio": [ "segmented" ],
    
    "format_preferences": [ "segmented" ],
    
    "render": [ "title", "gloss", "lemma", "images", "audio", "format_preferences" ],

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

def timestamp_for_phase(clara_project_internal, project_id, processing_phase_id,
                        human_audio_info=None, format_preference=None):
    if processing_phase_id in [ "plain", "summary", "cefr_level", "title",
                                "segmented", "phonetic", "gloss", "lemma" ]:
        try:
            file = clara_project_internal.load_text_version(processing_phase_id)
            return get_file_time(file)
        except FileNotFoundError:
            return None
    elif processing_phase_id == 'images':
            images = clara_project_internal.get_all_project_images()
            timestamps = [ get_file_time(image.image_file_path) for image in images ]
            return latest_timestamp(timestamps)
    elif processing_phase_id == 'audio':
        if not human_audio_info:
            return None
        human_voice_id = human_audio_info.voice_talent_id
        metadata = []
        if human_audio_info.use_for_words:
            metadata += clara_project_internal.get_audio_metadata(human_voice_id=human_voice_id,
                                                                  audio_type_for_words='human', type='words',
                                                                  format='text_and_full_file')
        if human_audio_info.use_for_segments:
            metadata += clara_project_internal.get_audio_metadata(human_voice_id=human_voice_id,
                                                                  audio_type_for_segments='human', type='segments',
                                                                  format='text_and_full_file')
        timestamps = [ timestamp_for_file(item['full_file']) for item in metadata ]

        if human_audio_info.updated_at:
            timestamps.append(human_audio_info.updated_at)
        
        return latest_timestamp(timestamps)
    elif processing_phase_id == 'format_preferences':
        if not format_preference:
            return None
        else:
            return format_preference.updated_at
    elif processing_phase_id == 'render':
        
            
