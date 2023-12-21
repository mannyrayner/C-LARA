from .clara_classes import InternalCLARAError
from .clara_utils import absolute_local_file_name, file_exists, local_file_exists, basename, copy_local_file, copy_to_local_file, remove_local_file
from .clara_utils import make_local_directory, copy_directory_to_local_directory, local_directory_exists, remove_local_directory
from .clara_utils import get_immediate_subdirectories_in_local_directory, get_files_in_local_directory, rename_file
from .clara_utils import make_tmp_file, write_json_to_local_file, read_json_local_file, make_zipfile, unzip_file, post_task_update
from .clara_audio_annotator import AudioAnnotator
from .clara_audio_repository import AudioRepository
from .clara_image_repository import ImageRepository

import os
import tempfile
import traceback

def create_export_zipfile(global_metadata, project_directory, audio_metadata, audio_metadata_phonetic,
                          image_metadata, zipfile, callback=None):
    try:
        tmp_dir = tempfile.mkdtemp()
        tmp_zipfile = make_tmp_file('project_zip', 'zip')

        write_global_metadata_to_tmp_dir(global_metadata, tmp_dir, callback=callback)
        copy_project_directory_to_tmp_dir(project_directory, tmp_dir, callback=callback)
        copy_audio_data_to_tmp_dir(audio_metadata, tmp_dir, phonetic=False, callback=callback)
        copy_audio_data_to_tmp_dir(audio_metadata_phonetic, tmp_dir, phonetic=True, callback=callback)
        copy_image_data_to_tmp_dir(image_metadata, tmp_dir, callback=callback)
        
        make_zipfile(tmp_dir, tmp_zipfile, callback=callback)
        copy_local_file(tmp_zipfile, zipfile)
        post_task_update(callback, f'--- Zipfile created and copied to {zipfile}')
        return True
    except Exception as e:
        post_task_update(callback, f'*** Error when trying to create zipfile for project')
        error_message = f'"{str(e)}"\n{traceback.format_exc()}'
        post_task_update(callback, error_message)
        return False
    finally:
        # Remove the tmp dir and tmp zipfile once we've used them
        if local_directory_exists(tmp_dir):
            remove_local_directory(tmp_dir)
        if local_file_exists(tmp_zipfile):
            remove_local_file(tmp_zipfile)

def write_global_metadata_to_tmp_dir(global_metadata, tmp_dir, callback=None):
    global_metadata_file = f'{tmp_dir}/metadata.json'
    write_json_to_local_file(global_metadata, global_metadata_file)
    post_task_update(callback, f'--- Written global metadata')

def copy_project_directory_to_tmp_dir(project_directory, tmp_dir, callback=None):
    tmp_project_dir = os.path.join(tmp_dir, 'project_dir')

    post_task_update(callback, f'--- Copying project directory')
    copy_directory_to_local_directory(project_directory, tmp_project_dir)
    post_task_update(callback, f'--- Project directory copied')

## Format looks like this:
##
##  {
##    "words": [
##        {
##            "word": "once",
##            "file": "C:\\cygwin64\\home\\github\\c-lara\\audio\\tts_repository\\google\\en\\default\\default_311.mp3"
##        },
##        ...
##     "segments": [
##        {
##            "segment": "Once upon a time there were four little Rabbits, and their names were\u2014 Flopsy, Mopsy, Cotton-tail, and Peter.",
##            "file": "C:\\cygwin64\\home\\github\\c-lara\\audio\\tts_repository\\google\\en\\default\\default_356.mp3"
##        },
##        ...

def copy_audio_data_to_tmp_dir(audio_metadata, tmp_dir, phonetic=False, callback=None):
    if not audio_metadata:
        return
    tmp_audio_dir = os.path.join(tmp_dir, 'audio' if not phonetic else 'phonetic_audio') 
    make_local_directory(tmp_audio_dir)
    file = f'{tmp_audio_dir}/metadata.json'

    for words_or_segments in ( 'words', 'segments' ):
        if words_or_segments in audio_metadata:
            sub_metadata = audio_metadata[words_or_segments]
            if len(sub_metadata) != 0:
                count = 0
                if phonetic and words_or_segments == 'words':
                    printform_for_words_or_segments = 'phonemes'
                else:
                    printform_for_words_or_segments = words_or_segments
                post_task_update(callback, f'--- Copying {len(sub_metadata)} audio files for {printform_for_words_or_segments}')
                for item in audio_metadata[words_or_segments]:
                    if 'file' in item and item['file'] and file_exists(item['file']):
                        pathname = item['file']
                        zipfile_pathname = os.path.join(tmp_audio_dir, basename(pathname))
                        copy_to_local_file(pathname, zipfile_pathname)
                        item['file'] = basename(pathname)
                        count += 1
                        if count % 10 == 0:
                            post_task_update(callback, f'--- Copied {count}/{len(sub_metadata)} files for {printform_for_words_or_segments}')
    
    write_json_to_local_file(audio_metadata, file)
    post_task_update(callback, f'--- Copied all audio files (phonetic = {phonetic})')

## Format looks like this:
##
## [
##    {
##        "image_file_path": "C:\\cygwin64\\home\\github\\c-lara\\images\\image_repository\\Peter_Rabbit_small_18\\tmp1i2yu_18.jpg",
##        "thumbnail_file_path": "C:\\cygwin64\\home\\github\\c-lara\\images\\image_repository\\Peter_Rabbit_small_18\\tmp1i2yu_18_thumbnail.jpg",
##        "image_name": "01VeryBigFirTree",
##        "associated_text": "",
##        "associated_areas": "",
##        "page": 1,
##        "position": "bottom"
##    },
    
def copy_image_data_to_tmp_dir(image_metadata, tmp_dir, callback=None):
    tmp_image_dir = os.path.join(tmp_dir, 'images')
    make_local_directory(tmp_image_dir)
    file = f'{tmp_image_dir}/metadata.json'
    
    image_metadata_as_json = [ image.to_json() for image in image_metadata ]

    if len(image_metadata_as_json) != 0:
        count = 0
        post_task_update(callback, f'--- Copying {len(image_metadata_as_json)} image files')
        
        for item in image_metadata_as_json:
            for key in ( 'image_file_path', 'thumbnail_file_path' ):
                if key in item:
                    pathname = item[key]
                    zipfile_pathname = os.path.join(tmp_image_dir, basename(pathname))
                    copy_to_local_file(pathname, zipfile_pathname)
                    item[key] = basename(pathname)
                    count += 1
                    if count % 10 == 0:
                        post_task_update(callback, f'--- Copied {count}/{len(image_metadata_as_json)} image files')
    
    write_json_to_local_file(image_metadata_as_json, file)
    post_task_update(callback, f'--- Copied all image files')

# ===========================================

def change_project_id_in_imported_directory(tmp_dir, new_id):
    tmp_project_dir = os.path.join(tmp_dir, 'project_dir')
    if not local_directory_exists(tmp_project_dir):
        post_task_update(callback, f'--- Unable to find project_dir subdirectory in unzipped directory')
        raise FileNotFoundError(f"project_dir not found in unzipped directory")
    stored_data_file = os.path.join(tmp_project_dir, 'stored_data.json')
    if not local_file_exists(stored_data_file):
        post_task_update(callback, f'--- Unable to find stored_data file in unzipped directory')
        raise FileNotFoundError(f"stored_data.json not found in unzipped directory")
    stored_data = read_json_local_file(stored_data_file)
    stored_data['id'] = new_id
    write_json_to_local_file(stored_data, stored_data_file)

# Go through the project dir and rename the text and annotated text files to be canonical wrt the new project id
def rename_files_in_project_dir(tmp_project_dir, new_id):
    abs_dir = absolute_local_file_name(tmp_project_dir)
    subdirs = get_immediate_subdirectories_in_local_directory(abs_dir)
    for subdir in subdirs:
        files = get_files_in_local_directory(os.path.join(abs_dir, subdir))
        for file in files:
            if file.endswith(f'{subdir}.txt'):
                rename_file(os.path.join(abs_dir, subdir, file),
                            os.path.join(abs_dir, subdir, f'{new_id}_{subdir}.txt'))

def update_multimedia_from_imported_directory(project, temp_dir, callback=None):
    update_images_from_imported_directory(project, temp_dir, callback=callback)
    update_regular_audio_from_imported_directory(project, temp_dir, callback=callback)
    update_phonetic_audio_from_imported_directory(project, temp_dir, callback=callback)

## Typical items in image metadata look like this:
##
##    {
##        "image_file_path": "tmp1i2yu_18.jpg",
##        "thumbnail_file_path": "tmp1i2yu_18_thumbnail.jpg",
##        "image_name": "01VeryBigFirTree",
##        "associated_text": "",
##        "associated_areas": "",
##        "page": 1,
##        "position": "bottom"
##    },
    
def update_images_from_imported_directory(project, tmp_dir, callback=None):
    image_dir = absolute_local_file_name(os.path.join(tmp_dir, 'images'))
    metadata_file = os.path.join(image_dir, 'metadata.json')
    if not local_file_exists(metadata_file):
        # There are no images in this zipfile
        return
    metadata = read_json_local_file(metadata_file)
    for item in metadata:
        # Note that we don't use "thumbnail_file_path", add_project_image generates the thumbnail on the fly.
        project.add_project_image(item['image_name'],
                                  os.path.join(image_dir, item['image_file_path']),
                                  associated_text=item['associated_text'],
                                  associated_areas=item['associated_areas'],
                                  page=item['page'],
                                  position=item['position'],
                                  callback=callback)

## Global meta data looks like this:
##
##    {
##    "human_voice_id": "mannyrayner",
##    "human_voice_id_phonetic": "mannyrayner",
##    "audio_type_for_words": "human",
##    "audio_type_for_segments": "tts"
## }
##
## Audio metadata looks like this:
##
## {
##    "words": [
##        {
##            "word": "once",
##            "file": null
##        },
##        (...)
##
##    ],
##    "segments": [
##        {
##            "segment": "Once upon a time there were four little Rabbits, and their names were\u2014 Flopsy, Mopsy, Cotton-tail, and Peter.",
##            "file": "default_356.mp3"
##        },
##        (...)
##    ]
## }

## Only import human audio, we can recreate TTS audio

def update_regular_audio_from_imported_directory(project, tmp_dir, callback=None):
    audio_dir = absolute_local_file_name(os.path.join(tmp_dir, 'audio'))
    global_metadata = get_global_metadata(tmp_dir)
    if not local_directory_exists(audio_dir) or not global_metadata or not global_metadata['human_voice_id']:
        return
    language = project.l2_language
    annotator = AudioAnnotator(language,
                               tts_engine_type=None,
                               human_voice_id=global_metadata['human_voice_id'],
                               audio_type_for_words=global_metadata['audio_type_for_words'],
                               audio_type_for_segments=global_metadata['audio_type_for_segments'],
                               callback=callback)
    audio_metadata = get_normal_audio_metadata(tmp_dir)
    if not audio_metadata or not isinstance(audio_metadata, (dict)) or not 'words' in audio_metadata or not 'segments' in audio_metadata:
        return
    
    if global_metadata['audio_type_for_words'] == 'human':
        words_metadata_for_update = [ { 'text': item['word'], 'file': item['file'] }
                                      for item in audio_metadata['words'] ]
        post_task_update(callback, 'Storing human audio for words ({len(words_metadata_for_update)} items)')
        annotator._store_existing_human_audio_mp3s(words_metadata_for_update, audio_dir, callback=callback)
    if global_metadata['audio_type_for_segments'] == 'human':
        segments_metadata_for_update = [ { 'text': item['segment'], 'file': item['file'] }
                                      for item in audio_metadata['segments'] ]
        post_task_update(callback, 'Storing human audio for segments ({len(segments_metadata_for_update)} items)')
        annotator._store_existing_human_audio_mp3s(segments_metadata_for_update, audio_dir, callback=callback)
                                         
def update_phonetic_audio_from_imported_directory(project, tmp_dir, callback=None):
    audio_dir = absolute_local_file_name(os.path.join(tmp_dir, 'phonetic_audio'))
    global_metadata = get_global_metadata(tmp_dir)
    if not local_directory_exists(audio_dir) or not global_metadata or not global_metadata['human_voice_id_phonetic']:
        return
    language = project.l2_language
    annotator = AudioAnnotator(language,
                               tts_engine_type=None,
                               human_voice_id=global_metadata['human_voice_id_phonetic'],
                               audio_type_for_words='human',
                               audio_type_for_segments='tts',
                               callback=callback)
    audio_metadata = get_phonetic_audio_metadata(tmp_dir)
    if not audio_metadata or not isinstance(audio_metadata, (dict)) or not 'words' in audio_metadata:
        return

    phonemes_metadata_for_update = [ { 'text': item['word'], 'file': item['file'] }
                                     for item in audio_metadata['words'] ]
    post_task_update(callback, 'Storing human audio for phonemes ({len(phonemes_metadata_for_update)} items)')
    annotator._store_existing_human_audio_mp3s(phonemes_metadata_for_update, audio_dir, callback=callback)

def get_global_metadata(tmp_dir):
    metadata_file = absolute_local_file_name(os.path.join(tmp_dir, 'metadata.json'))
    if not local_file_exists(metadata_file):
        return None
    else:
        return read_json_local_file(metadata_file)

def get_normal_audio_metadata(tmp_dir):
    metadata_file = absolute_local_file_name(os.path.join(tmp_dir, 'audio' 'metadata.json'))
    metadata_file = absolute_local_file_name(os.path.join(tmp_dir, 'phonetic_audio' 'metadata.json'))
    if not local_file_exists(metadata_file):
        return None
    else:
        return read_json_local_file(metadata_file)

def get_phonetic_audio_metadata(tmp_dir):
    metadata_file = absolute_local_file_name(os.path.join(tmp_dir, 'phonetic_audio' 'metadata.json'))
    if not local_file_exists(metadata_file):
        return None
    else:
        return read_json_local_file(metadata_file)
