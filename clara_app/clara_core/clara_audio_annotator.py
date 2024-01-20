"""
clara_audio_annotator.py

This module implements an Audio annotator that can generate and store audio files for words and segments in a given Text object.

Classes:
- AudioAnnotator: Class for handling Audio annotations for a Text object.

Functions:
- canonical_word_for_audio(text): Returns a canonical version of the input text for Audio word processing.
- canonical_text_for_audio(text): Returns a canonical version of the input text for Audio segment processing.

The AudioAnnotator class provides methods for annotating a Text object with audio files.
It uses the audio repository to store and retrieve audio files.
"""

from .clara_classes import Text, InternalCLARAError
from .clara_utils import absolute_local_file_name, basename, make_tmp_file, file_exists, remove_file, read_json_local_file, unzip_file, post_task_update
from .clara_utils import canonical_word_for_audio, canonical_text_for_audio, remove_duplicates_general
from .clara_tts_api import get_tts_engine, get_default_voice, get_language_id, create_tts_engine
from .clara_audio_repository import AudioRepository
from .clara_ldt import convert_ldt_data_to_mp3
from .clara_manual_audio_align import process_alignment_metadata

import re
import os
import tempfile
import shutil
import uuid
import json
import traceback
import regex

class AudioAnnotator:
    def __init__(self, language, tts_engine_type=None,
                 human_voice_id=None,
                 audio_type_for_words='tts', audio_type_for_segments='tts',
                 preferred_tts_engine=None, preferred_tts_voice=None,
                 phonetic=False, callback=None):
        self.language = language
        # TTS for words
        self.tts_engine = create_tts_engine(tts_engine_type) if tts_engine_type else get_tts_engine(language, words_or_segments='words', phonetic=False, callback=callback)
        self.engine_id = self.tts_engine.tts_engine_type if self.tts_engine else None
        self.voice_id = get_default_voice(language, preferred_tts_voice, self.tts_engine) if self.tts_engine else None
        self.language_id = get_language_id(language, self.tts_engine) if self.tts_engine else None

        # TTS for segments
        if tts_engine_type:
            self.segment_tts_engine = create_tts_engine(tts_engine_type)
        else:
            self.segment_tts_engine = get_tts_engine(language, words_or_segments='segments', preferred_tts_engine=preferred_tts_engine,
                                                     phonetic=False, callback=callback)
        self.segment_engine_id = self.segment_tts_engine.tts_engine_type if self.segment_tts_engine else None
        self.segment_voice_id = get_default_voice(language, preferred_tts_voice, self.segment_tts_engine) if self.segment_tts_engine else None
        self.segment_language_id = get_language_id(language, self.segment_tts_engine) if self.segment_tts_engine else None

        # TTS for phonemes
        self.phonetic_tts_engine = get_tts_engine(language, phonetic=True, callback=callback) if phonetic else None
        self.phonetic_engine_id = self.phonetic_tts_engine.tts_engine_type if self.phonetic_tts_engine else None
        self.phonetic_voice_id = get_default_voice(language, preferred_tts_voice, self.phonetic_tts_engine) if self.phonetic_tts_engine else None
        self.phonetic_language_id = get_language_id(language, self.phonetic_tts_engine) if self.phonetic_tts_engine else None
        
        # For human audio
        self.human_voice_id = human_voice_id
        # Common
        self.audio_repository = AudioRepository(callback=callback)
        self.audio_type_for_words = audio_type_for_words
        self.audio_type_for_segments = audio_type_for_segments

        # Validations
        valid_audio_types = ['tts', 'human']
        if self.audio_type_for_words not in valid_audio_types:
            raise InternalCLARAError(message = f"Invalid audio type for words: {self.audio_type_for_words}. Expected one of {valid_audio_types}.")

        if self.audio_type_for_segments not in valid_audio_types:
            raise InternalCLARAError(message = f"Invalid audio type for segments: {self.audio_type_for_segments}. Expected one of {valid_audio_types}.")
        
        if self.audio_type_for_segments == 'human' and not self.human_voice_id:
            raise InternalCLARAError(message = "Human audio type specified for segments, but no human_voice_id provided.")
        
        if self.audio_type_for_words == 'human' and not self.human_voice_id:
            raise InternalCLARAError(message = "Human audio type specified for words, but no human_voice_id provided.")

        # Set word- and segment-based engine, language, and voice IDs based on audio types and whether or not it's a phonetic text
        # If it's a phonetic text, we may be using the phonetic TTS engine to create phoneme audio
        if self.audio_type_for_words == 'tts':
            self.word_tts_engine = self.phonetic_tts_engine if phonetic else self.tts_engine
            self.word_engine_id = self.phonetic_engine_id if phonetic else self.engine_id
            self.word_language_id = self.phonetic_language_id if phonetic else self.language_id
            self.word_voice_id = self.phonetic_voice_id if phonetic else self.voice_id
        else:
            self.word_tts_engine = None
            self.word_engine_id = 'human_voice'
            self.word_language_id = self.language
            self.word_voice_id = self.human_voice_id

        # If we're using TTS for segments, we've already set this higher up
        if self.audio_type_for_segments != 'tts':
            self.segment_tts_engine = None
            self.segment_engine_id = 'human_voice'
            self.segment_language_id = self.language
            self.segment_voice_id = self.human_voice_id

        post_task_update(callback, f"--- Using AudioAnnotator object with TTS voice of type '{self.engine_id}' and human voice '{self.human_voice_id}'")


    def delete_entries_for_language(self, callback=None):
        self.audio_repository.delete_entries_for_language(self.engine_id, self.language_id, callback=callback)

    def annotate_text(self, text_obj, phonetic=False, callback=None):
        words_data, segments_data = self._get_all_audio_data(text_obj, phonetic=phonetic, callback=callback)
        missing_words, missing_segments = self._get_missing_audio(words_data, segments_data, phonetic=phonetic, callback=callback)

        if self.audio_type_for_words == 'tts' and self.word_engine_id and missing_words and self.audio_type_for_words == 'tts':
            external_name_for_words = 'phonemes' if phonetic else 'words'
            post_task_update(callback, f"--- Creating TTS audio for {external_name_for_words}")
            new_words_data = self._create_and_store_missing_mp3s(missing_words, 'words', phonetic=phonetic, callback=callback)
            post_task_update(callback, f"--- TTS audio for words created")
        else:
            new_words_data = []

        if self.audio_type_for_segments == 'tts' and self.segment_engine_id and missing_segments and self.audio_type_for_segments == 'tts':
            external_name_for_segments = 'words' if phonetic else 'segments'
            post_task_update(callback, f"--- Creating TTS audio for {external_name_for_segments}")
            new_segments_data = self._create_and_store_missing_mp3s(missing_segments, 'segments', phonetic=phonetic, callback=callback)
            post_task_update(callback, f"--- TTS audio for {external_name_for_segments} created")
        else:
            new_segments_data = []

        updated_words_data = words_data + new_words_data
        updated_segments_data = segments_data + new_segments_data

        post_task_update(callback, f"--- All TTS files should be there")
        self._add_audio_annotations(text_obj, updated_words_data, updated_segments_data, phonetic=phonetic, callback=callback)

    def _get_all_audio_data(self, text_obj, phonetic=False, callback=None):
        post_task_update(callback, f"--- Getting all audio data")
        words_data = []
        segments_data = []
        for page in text_obj.pages:
            for segment in page.segments:
                segment_text_plain = segment.to_text()
                segment_text_canonical = canonical_text_for_audio(segment_text_plain)
                if not string_has_no_audio_content(segment_text_canonical):
                    segments_data.append([segment_text_plain, segment_text_canonical])
                
                for content_element in segment.content_elements:
                    if content_element.type == 'Word':
                        if phonetic and 'phonetic' in content_element.annotations:
                            audio_word_plain = content_element.annotations['phonetic']
                        elif not phonetic:
                            audio_word_plain = content_element.content
                        else:
                            audio_word_plain = None
                            
                        if audio_word_plain and not string_has_no_audio_content(audio_word_plain):
                            audio_word_canonical = canonical_word_for_audio(audio_word_plain)
                            words_data.append([audio_word_plain, audio_word_canonical])    

        segment_texts_canonical = [ item[1] for item in segments_data ]
        word_texts_canonical = [ item[1] for item in words_data ]

        segment_file_paths = self.audio_repository.get_entry_batch(self.segment_engine_id, self.segment_language_id, self.segment_voice_id, segment_texts_canonical, callback=callback)
        word_file_paths = self.audio_repository.get_entry_batch(self.word_engine_id, self.word_language_id, self.word_voice_id, word_texts_canonical, callback=callback)

        segments_and_file_paths = [ [ item[0], segment_file_paths[item[1]] ] for item in segments_data ]
        words_and_file_paths = [ [ item[0], word_file_paths[item[1]] ] for item in words_data ]

        words_and_file_paths = remove_duplicates_general(words_and_file_paths)
        if phonetic:
            segments_and_file_paths = remove_duplicates_general(segments_and_file_paths)

        #print(f'--- words_and_file_paths = {words_and_file_paths}')
        
        return words_and_file_paths, segments_and_file_paths

    def _get_missing_audio(self, words_data, segments_data, phonetic=False, callback=None):
        
        missing_words = [word_data[0] for word_data in words_data if not word_data[1]]
        missing_segments = [segment_data[0] for segment_data in segments_data if not segment_data[1]]

        post_task_update(callback, f"--- Found {len(missing_words)} words without audio")
        post_task_update(callback, f"--- Found {len(missing_segments)} segments without audio")

        return missing_words, missing_segments

    def generate_audio_metadata(self, text_obj, type='default', format='default', phonetic=False, callback=None):
        words_data, segments_data = self._get_all_audio_data(text_obj, phonetic=phonetic, callback=callback)

        # Reformat the data as lists of dictionaries.
        words_metadata = [{"word": canonical_word_for_audio(word_data[0]), "file": word_data[1]}
                          for word_data in words_data
                          if word_data[0]]
        segments_metadata = [{"segment": canonical_text_for_audio(segment_data[0]), "file": segment_data[1]}
                             for segment_data in segments_data
                             if segment_data[0]]

        # Do this earlier in _get_all_audio_data
        #words_metadata = remove_duplicates_general(words_metadata)
        #if phonetic:
        #    segments_metadata = remove_duplicates_general(segments_metadata)

        if format != 'default':
            words_metadata = [ format_audio_metadata_item(item, format, 'words') for item in words_metadata ]
            segments_metadata = [ format_audio_metadata_item(item, format, 'segments') for item in segments_metadata ]

        if type == 'words':
            return words_metadata
        elif type == 'segments':
            return segments_metadata
        else:
            return { 'words': words_metadata, 'segments': segments_metadata }

    def _create_and_store_missing_mp3s(self, text_items, words_or_segments, phonetic=False, callback=None):
        if words_or_segments == 'words':
            tts_engine_to_use = self.word_tts_engine
            engine_id_to_use = self.word_engine_id
            language_id_to_use = self.word_language_id
            voice_id_to_use = self.word_voice_id
        else:
            tts_engine_to_use = self.segment_tts_engine
            engine_id_to_use = self.segment_engine_id
            language_id_to_use = self.segment_language_id
            voice_id_to_use = self.segment_voice_id
        
        post_task_update(callback, f"--- For {words_or_segments}, using tts_engine={engine_id_to_use}, language_id={language_id_to_use}, voice_id={voice_id_to_use}")
        
        temp_dir = tempfile.mkdtemp()
        text_file_paths = []

        for i, text in enumerate(text_items, 1):
            canonical_text = canonical_text_for_audio(text) if words_or_segments == 'segments' else canonical_word_for_audio(text)
            post_task_update(callback, f"--- Creating mp3 for '{canonical_text}' ({i}/{len(text_items)})")
            try:
                unique_filename = f"{uuid.uuid4()}.mp3"
                temp_file = os.path.join(temp_dir, unique_filename)

                result = tts_engine_to_use.create_mp3(language_id_to_use, voice_id_to_use, canonical_text, temp_file, callback=callback)
                if result:
                    file_path = self.audio_repository.store_mp3(engine_id_to_use, language_id_to_use, voice_id_to_use, temp_file)
                    self.audio_repository.add_or_update_entry(engine_id_to_use, language_id_to_use, voice_id_to_use, canonical_text, file_path)
                else:
                    file_path = None
                    post_task_update(callback, f"--- Failed to create mp3 for '{text}'")
                text_file_paths.append([text, file_path])
            except Exception as e:
                post_task_update(callback, f"*** Error creating TTS file: '{str(e)}'\n{traceback.format_exc()}")
                
        shutil.rmtree(temp_dir)
        return text_file_paths

    # Process a zipfile received from LiteDevTools. This should contain .wav files and metadata
    def process_lite_dev_tools_zipfile(self, zipfile, callback=None):
        try:
            post_task_update(callback, f'--- Entered process_lite_dev_tools_zipfile: zipfile = {zipfile}')
            temp_ldt_dir = tempfile.mkdtemp()
            temp_mp3_dir = tempfile.mkdtemp()
            post_task_update(callback, f'--- Trying to unzip {zipfile} to {temp_ldt_dir}')
            unzip_file(zipfile, temp_ldt_dir)
            post_task_update(callback, f'--- Unzipped {zipfile} to {temp_ldt_dir}')
            # For historical reasons, the LDT metadata file is called metadata_help.json
            metadata_file = os.path.join(temp_ldt_dir, 'metadata_help.json')
            ldt_metadata = read_json_local_file(metadata_file)
            ldt_metadata = convert_ldt_data_to_mp3(ldt_metadata, temp_ldt_dir, temp_mp3_dir, callback=callback)
            self._store_existing_human_audio_mp3s(ldt_metadata, temp_mp3_dir, callback=callback)
            return True
        except Exception as e:
            post_task_update(callback, f'*** Error when trying to install LDT audio {zipfile}')
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            return False
        finally:
            # Remove the tmp dirs once we've used them
            if os.path.exists(temp_ldt_dir):
                shutil.rmtree(temp_ldt_dir)
            if os.path.exists(temp_mp3_dir):
                shutil.rmtree(temp_mp3_dir)

    # Process an audio file and alignment data received from the manual audio/text aligner
    def process_manual_alignment(self, metadata, audio_file, callback=None):
        try:
            post_task_update(callback, f'--- Entered process_manual_alignment: audio_file = {audio_file}, {len(metadata)} items of metadata')
            
            temp_mp3_dir = tempfile.mkdtemp()
            
            alignment_metadata = process_alignment_metadata(metadata, audio_file, temp_mp3_dir, callback=callback)
            self._store_existing_human_audio_mp3s(alignment_metadata, temp_mp3_dir, callback=callback)
            
            return True
        except Exception as e:
            post_task_update(callback, f'*** Error when trying to process manual alignment audio {audio_file}')
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            return False
        finally:
            # Remove the tmp dir once we've used it
            if os.path.exists(temp_mp3_dir):
                shutil.rmtree(temp_mp3_dir)


    # We have metadata as a list of items of the form { 'text': text, 'file': file } where file is the basename of a file in temp_dir.
    # The files are copied into the appropriate directory and the metadata is used to update the DB
    def _store_existing_human_audio_mp3s(self, metadata, temp_dir, callback=None):
        post_task_update(callback, f'--- Calling _store_existing_mp3s with {len(metadata)} metadata items and audio dir = {temp_dir}')
        for i, metadata_item in enumerate(metadata, 1):
            try:
                text = metadata_item['text']
                file = metadata_item['file']
                if file:
                    post_task_update(callback, f"--- Adding mp3 to repository for '{text}', ({i}/{len(metadata)})")
                    temp_file = os.path.join(temp_dir, file)
                    file_path = self.audio_repository.store_mp3('human_voice', self.language, self.human_voice_id, temp_file, keep_file_name=True)
                    self.audio_repository.add_or_update_entry('human_voice', self.language, self.human_voice_id, text, file_path)
            except Exception as e:
                post_task_update(callback, f"*** Error trying to process metadata item {metadata_item}: {str(e)}")

    def _add_audio_annotations(self, text_obj, words_data, segments_data, phonetic=False, callback=None):
        post_task_update(callback, f"--- Adding audio annotations to internalised text")
        text_obj.voice = self.printname_for_voice()
        
        word_cache = { item[0]: item[1] for item in words_data }
        segment_cache = { item[0]: item[1] for item in segments_data }
        
        for page in text_obj.pages:
            for segment in page.segments:
                segment_text = segment.to_text()
                segment_file_path = segment_cache[segment_text] if segment_text in segment_cache else 'placeholder.mp3'
                if segment_file_path and not string_has_no_audio_content(segment_text):
                    segment.annotations['tts'] = {
                        "engine_id": self.segment_engine_id,
                        "language_id": self.segment_language_id,
                        "voice_id": self.segment_voice_id,
                        "file_path": segment_file_path,
                    }

                for content_element in segment.content_elements:
                    if content_element.type == 'Word':
                        if phonetic and 'phonetic' in content_element.annotations:
                            audio_word = content_element.annotations['phonetic']
                        elif not phonetic:
                            audio_word = content_element.content
                        else:
                            audio_word = None

                        if audio_word:
                            #file_path = self.audio_repository.get_entry(self.word_engine_id, self.word_language_id, self.word_voice_id, canonical_word)
                            file_path = word_cache[audio_word] if audio_word in word_cache else None
                        else:
                            file_path = None
                            
                        if not string_has_no_audio_content(audio_word):
                            if not file_path:
                                file_path = 'placeholder.mp3'
                            content_element.annotations['tts'] = {
                                "engine_id": self.word_engine_id,
                                "language_id": self.word_language_id,
                                "voice_id": self.word_voice_id,
                                "file_path": file_path,
                            }
        post_task_update(callback, f"--- Audio annotations added to internalised text")

    def printname_for_voice(self):
        segment_voice_str = None
        word_voice_str = None

        if self.audio_type_for_segments == 'tts' and self.segment_engine_id:
            segment_voice_str = '_'.join([self.segment_engine_id, self.segment_language_id, self.segment_voice_id]) + " (segments)"
        elif self.audio_type_for_segments == 'human':
            segment_voice_str = f"human_{self.segment_language_id}_{self.human_voice_id} (segments)"

        if self.audio_type_for_words == 'tts' and self.word_engine_id:
            word_voice_str = '_'.join([self.word_engine_id, self.word_language_id, self.word_voice_id]) + " (words)"
        elif self.audio_type_for_words == 'human':
            word_voice_str = f"human_{self.word_language_id}_{self.human_voice_id} (words)"

        if segment_voice_str and word_voice_str:
            return f"{segment_voice_str}, {word_voice_str}"
        elif segment_voice_str:
            return segment_voice_str
        elif word_voice_str:
            return word_voice_str
        else:
            return 'No audio voice'

def format_audio_metadata_item(item, format, words_or_segments):
    try:
        if format == 'text_and_full_file':
            file = item['file'] if isinstance(item['file'], ( str )) else ''
            text = item['word'] if words_or_segments == 'words' else item['segment']
            return { 'text': text, 'full_file': file }
        elif format == 'lite_dev_tools':
            file = basename(item['file']) if isinstance(item['file'], ( str )) else ''
            text = item['word'] if words_or_segments == 'words' else item['segment']
            return { 'text': text, 'file': file }
        else:
            raise InternalCLARAError(message = f'Bad call: unknown format {format} in call to clara_audio.annotator.format_audio_metadata_item')
        
    except:
        raise InternalCLARAError(message = f'Bad call: clara_audio_annotator.format_audio_metadata_item({item}, {format}, {words_or_segments})')

# String has no audio content if it's just punctuation marks and separators
def string_has_no_audio_content(s):
    return not s or all(regex.match(r"[\p{P} \n|]", c) for c in s)

