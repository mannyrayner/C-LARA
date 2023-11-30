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
    def __init__(self, language, tts_engine_type=None, human_voice_id=None, audio_type_for_words='tts', audio_type_for_segments='tts', callback=None):
        self.language = language
        # For TTS
        self.tts_engine = create_tts_engine(tts_engine_type) if tts_engine_type else get_tts_engine(language, callback=callback)
        self.engine_id = self.tts_engine.tts_engine_type if self.tts_engine else None
        self.voice_id = get_default_voice(language, self.tts_engine) if self.tts_engine else None
        self.language_id = get_language_id(language, self.tts_engine) if self.tts_engine else None
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

        # Set word- and segment-based engine, language, and voice IDs based on audio types
        if self.audio_type_for_words == 'tts':
            self.word_engine_id = self.engine_id
            self.word_language_id = self.language_id
            self.word_voice_id = self.voice_id
        else:
            self.word_engine_id = 'human_voice'
            self.word_language_id = self.language
            self.word_voice_id = self.human_voice_id

        if self.audio_type_for_segments == 'tts':
            self.segment_engine_id = self.engine_id
            self.segment_language_id = self.language_id
            self.segment_voice_id = self.voice_id
        else:
            self.segment_engine_id = 'human_voice'
            self.segment_language_id = self.language
            self.segment_voice_id = self.human_voice_id

        post_task_update(callback, f"--- Using AudioAnnotator object with TTS voice of type '{self.engine_id}' and human voice '{self.human_voice_id}'")


    def delete_entries_for_language(self, callback=None):
        self.audio_repository.delete_entries_for_language(self.engine_id, self.language_id, callback=callback)

    def annotate_text(self, text_obj, phonetic=False, callback=None):
        if self.tts_engine:
        
            missing_words, missing_segments = self._get_missing_audio(text_obj, phonetic=phonetic, callback=callback)

            if missing_words and self.audio_type_for_words == 'tts':
                # Don't try to use TTS for phonetic words, it is not likely to work
                if phonetic:
                    post_task_update(callback, f"--- Do not try to use TTS to create audio for phonetic items")
                else:
                    post_task_update(callback, f"--- Creating TTS audio for words")
                    self._create_and_store_missing_mp3s(missing_words, callback=callback)
                    post_task_update(callback, f"--- TTS audio for words created")

            if missing_segments and self.audio_type_for_segments == 'tts':
                post_task_update(callback, f"--- Creating TTS audio for segments")
                self._create_and_store_missing_mp3s(missing_segments, callback=callback)
                post_task_update(callback, f"--- TTS audio for segments created")

        post_task_update(callback, f"--- All TTS files should be there")
        self._add_audio_annotations(text_obj, phonetic=phonetic, callback=callback)

    def _get_all_audio_data(self, text_obj, phonetic=False, callback=None):
        post_task_update(callback, f"--- Getting all audio data")
        words_data = []
        segments_data = []
        words_cache = {}
        count = 0
        for page in text_obj.pages:
            for segment in page.segments:
                segment_text = canonical_text_for_audio(segment.to_text())
                if not string_has_no_audio_content(segment_text):
                    file_segment = self.audio_repository.get_entry(self.segment_engine_id, self.segment_language_id, self.segment_voice_id, segment_text, callback=callback)
                    segments_data.append([segment_text, file_segment])
                    count += 1
                    if count % 50 == 0:
                        post_task_update(callback, f"--- Checked {count} text items")
                
                for content_element in segment.content_elements:
                    if content_element.type == 'Word':
                        if phonetic and 'phonetic' in content_element.annotations:
                            audio_word = content_element.annotations['phonetic']
                        elif not phonetic:
                            audio_word = content_element.content
                        else:
                            audio_word = None
                        if audio_word and not string_has_no_audio_content(audio_word):
                            canonical_word = canonical_word_for_audio(audio_word)
                            if canonical_word in words_cache:
                                file_word = words_cache[canonical_word]
                            else:
                                file_word = self.audio_repository.get_entry(self.word_engine_id, self.word_language_id, self.word_voice_id, canonical_word, callback=callback)
                            words_data.append([canonical_word, file_word])    
                            count += 1
                            if count % 50 == 0:
                                post_task_update(callback, f"--- Checked {count} text items")

        return words_data, segments_data

    def _get_missing_audio(self, text_obj, phonetic=False, callback=None):
        words_data, segments_data = self._get_all_audio_data(text_obj, phonetic=phonetic, callback=callback)

        # We don't want to include trivial strings, so check using strip().
        missing_words = [word_data[0] for word_data in words_data if not word_data[1] and word_data[0].strip()]
        missing_segments = [segment_data[0] for segment_data in segments_data if not segment_data[1] and segment_data[0].strip()]

        post_task_update(callback, f"--- Found {len(missing_words)} words without audio")
        post_task_update(callback, f"--- Found {len(missing_segments)} segments without audio")

        return missing_words, missing_segments

    def generate_audio_metadata(self, text_obj, type='default', format='default', phonetic=False, callback=None):
        words_data, segments_data = self._get_all_audio_data(text_obj, phonetic=phonetic, callback=callback)

        # Reformat the data as lists of dictionaries.
        words_metadata = [{"word": word_data[0], "file": word_data[1]} for word_data in words_data if word_data[0]]
        segments_metadata = [{"segment": segment_data[0], "file": segment_data[1]} for segment_data in segments_data if segment_data[0]]

        
        words_metadata = remove_duplicates_general(words_metadata)
        if phonetic:
            segments_metadata = remove_duplicates_general(segments_metadata)

        if format != 'default':
            words_metadata = [ format_audio_metadata_item(item, format, 'words') for item in words_metadata ]
            segments_metadata = [ format_audio_metadata_item(item, format, 'segments') for item in segments_metadata ]

        if type == 'words':
            return words_metadata
        elif type == 'segments':
            return segments_metadata
        else:
            return { 'words': words_metadata, 'segments': segments_metadata }

    def _create_and_store_missing_mp3s(self, missing_audio, callback=None):
        temp_dir = tempfile.mkdtemp()

        for i, audio in enumerate(missing_audio, 1):
            post_task_update(callback, f"--- Creating mp3 for '{audio}' ({i}/{len(missing_audio)})")
            try:
                unique_filename = f"{uuid.uuid4()}.mp3"
                temp_file = os.path.join(temp_dir, unique_filename)
                result = self.tts_engine.create_mp3(self.language_id, self.voice_id, audio, temp_file, callback=callback)
                if result:
                    file_path = self.audio_repository.store_mp3(self.engine_id, self.language_id, self.voice_id, temp_file)
                    self.audio_repository.add_or_update_entry(self.engine_id, self.language_id, self.voice_id, audio, file_path)
                else:
                    post_task_update(callback, f"--- Failed to create mp3 for '{audio}'")
            except Exception as e:
                post_task_update(callback, f"*** Error creating TTS file: {str(e)}")
                
        shutil.rmtree(temp_dir)

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

    def _add_audio_annotations(self, text_obj, phonetic=False, callback=None):
        post_task_update(callback, f"--- Adding audio annotations to internalised text")
        text_obj.voice = self.printname_for_voice()
        word_cache = {}
        
        for page in text_obj.pages:
            for segment in page.segments:
                segment_text = canonical_text_for_audio(segment.to_text())
                segment_file_path = self.audio_repository.get_entry(self.segment_engine_id, self.segment_language_id, self.segment_voice_id, segment_text)
                if not segment_file_path:
                    #post_task_update(callback, f"--- Warning: no audio annotation available for segment '{segment_text}'")
                    #segment_file_path = 'placeholder.mp3'
                    pass
                if string_has_no_audio_content(segment_text):
                    pass
                else:
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
                            canonical_word = canonical_word_for_audio(audio_word)
                            if canonical_word in word_cache:
                                file_path = word_cache[canonical_word]
                            else:
                                file_path = self.audio_repository.get_entry(self.word_engine_id, self.word_language_id, self.word_voice_id, canonical_word)
                                word_cache[canonical_word] = file_path
                        else:
                            file_path = None
                            
                        if not file_path:
                            #post_task_update(callback, f"--- Warning: no audio annotation available for word '{canonical_word}'")
                            file_path = 'placeholder.mp3'
                        if string_has_no_audio_content(canonical_word):
                            pass
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

