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
#from .clara_utils import _use_orm_repositories
from .clara_utils import get_config, absolute_local_file_name, basename, make_tmp_file, file_exists, remove_file, read_json_local_file, unzip_file, post_task_update
from .clara_utils import canonical_word_for_audio, canonical_text_for_audio, remove_duplicates_general, absolute_file_name
from .clara_tts_api import get_tts_engine, get_default_voice, get_language_id, create_tts_engine
#from .clara_audio_repository import AudioRepository
from .clara_audio_repository_orm import AudioRepositoryORM
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
import pprint
import subprocess

config = get_config()

class AudioAnnotator:
    def __init__(self, language, tts_engine_type=None,
                 human_voice_id=None,
                 audio_type_for_words='tts', audio_type_for_segments='tts', use_context=False,
                 preferred_tts_engine=None, preferred_tts_voice=None,
                 phonetic=False, callback=None):
        self.language = language
        # TTS for words
        self.tts_engine = create_tts_engine(tts_engine_type) if tts_engine_type else get_tts_engine(language, words_or_segments='words', phonetic=False, callback=callback)
        self.engine_id = self.tts_engine.tts_engine_type if self.tts_engine else None
        self.voice_id = get_default_voice(language, preferred_tts_voice, 'words', self.tts_engine) if self.tts_engine else None
        self.language_id = get_language_id(language, self.tts_engine) if self.tts_engine else None

        # TTS for segments
        if tts_engine_type:
            self.segment_tts_engine = create_tts_engine(tts_engine_type)
        # If phonetic=False, then 'segments' really does mean segments, and we pass in preferred_tts_engine if we have it
        # because it's relevant
        elif not phonetic:
            self.segment_tts_engine = get_tts_engine(language, words_or_segments='segments', preferred_tts_engine=preferred_tts_engine,
                                                     phonetic=False, callback=callback)
        # If phonetic=True, then 'segments' actually means 'words', so preferred_tts_engine isn't relevant
        # and we want the TTS engine we'd use for words with phonetic=False.
        else:
            self.segment_tts_engine = get_tts_engine(language, words_or_segments='words', 
                                                     phonetic=False, callback=callback)
        self.segment_engine_id = self.segment_tts_engine.tts_engine_type if self.segment_tts_engine else None

        if not phonetic:
            self.segment_voice_id = get_default_voice(language, preferred_tts_voice, 'sentences', self.segment_tts_engine) if self.segment_tts_engine else None
        else:
            self.segment_voice_id = get_default_voice(language, preferred_tts_voice, 'words', self.segment_tts_engine) if self.segment_tts_engine else None
            
        self.segment_language_id = get_language_id(language, self.segment_tts_engine) if self.segment_tts_engine else None

        # TTS for phonemes
        self.phonetic_tts_engine = get_tts_engine(language, phonetic=True, callback=callback) if phonetic else None
        self.phonetic_engine_id = self.phonetic_tts_engine.tts_engine_type if self.phonetic_tts_engine else None
        self.phonetic_voice_id = get_default_voice(language, preferred_tts_voice, 'phonemes', self.phonetic_tts_engine) if self.phonetic_tts_engine else None
        self.phonetic_language_id = get_language_id(language, self.phonetic_tts_engine) if self.phonetic_tts_engine else None
        
        # For human audio
        self.human_voice_id = human_voice_id
        # Common
        self.audio_repository = AudioRepositoryORM(callback=callback)
        #self.audio_repository = AudioRepositoryORM(callback=callback) if _use_orm_repositories else AudioRepository(callback=callback) 
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

        # We only use context with human audio and not in phonetic text
        if self.audio_type_for_segments != 'tts' and not phonetic:
            self.use_context = use_context
            self.max_context_length = int(config.get('audio_repository', 'max_context_length'))
        else:
            self.use_context = False
            self.max_context_length = 0

        post_task_update(callback, f"--- Using AudioAnnotator object with TTS voice of type '{self.engine_id}' and human voice '{self.human_voice_id}'")
        #print(f'--- constructor: max_context_length = {self.max_context_length}')

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

        if not phonetic: 
            page_data = self._get_page_audio_data(text_obj, updated_segments_data, phonetic=False, callback=callback)
            updated_page_data = self._generate_missing_page_audio(page_data, callback=None)
        else:
            updated_page_data = []

        post_task_update(callback, f"--- All TTS files should be there")
        self._add_audio_annotations(text_obj, updated_words_data, updated_segments_data, updated_page_data, phonetic=phonetic, callback=callback)

    def _get_all_audio_data(self, text_obj, phonetic=False, callback=None):
        post_task_update(callback, f"--- Getting all audio data")
        words_data = []
        segments_data = []
        previous_canonical_text = ''
        previous_canonical_texts = []
        for page in text_obj.pages:
            for segment in page.segments:
                segment_text_plain = segment.to_text()
                segment_text_canonical = canonical_text_for_audio(segment_text_plain, phonetic=phonetic)
                #print(f'--- _get_all_audio_data: max_context_length = {self.max_context_length}')
                start_of_context = -1 * self.max_context_length
                #print(f'--- _get_all_audio_data: start_of_context = {start_of_context}')
                context = '' if not self.use_context else previous_canonical_text[start_of_context:]
                if not string_has_no_audio_content(segment_text_canonical):
                    segments_data.append({ 'text': segment_text_plain, 'canonical_text': segment_text_canonical, 'context': context })
                    previous_canonical_texts.append(segment_text_canonical)
                    previous_canonical_text = ' '.join(previous_canonical_texts) 
                
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
                            words_data.append({ 'text': audio_word_plain, 'canonical_text': audio_word_canonical, 'context': '' })    

        segment_file_paths = self.audio_repository.get_entry_batch(self.segment_engine_id, self.segment_language_id, self.segment_voice_id,
                                                                   segments_data, callback=callback)
        word_file_paths = self.audio_repository.get_entry_batch(self.word_engine_id, self.word_language_id, self.word_voice_id,
                                                                words_data, callback=callback)

        for item in segments_data:
            item['file_path'] = segment_file_paths[( item['canonical_text'], item['context'] )]

        for item in words_data:
            item['file_path'] = word_file_paths[( item['canonical_text'], item['context'] )]

        words_data = remove_duplicates_general(words_data)
        if phonetic:
            segments_data = remove_duplicates_general(segments_data)

        #print(f'--- _get_all_audio_data output: words_data = {words_data}')
        #print(f'--- _get_all_audio_data output: segments_data = {segments_data}')
        
        return words_data, segments_data

    def _get_page_audio_data(self, text_obj, segments_data, phonetic=False, callback=None):
        post_task_update(callback, f"--- Getting page audio data")
        segment_cache = { ( item['text'], item['context'] ): item['file_path'] for item in segments_data }
        
        page_data = []
        previous_canonical_text = ''
        previous_canonical_texts = []
        
        for page in text_obj.pages:
            segment_audio_files = []
            start_of_context = -1 * self.max_context_length
            page_context = '' if not self.use_context else previous_canonical_text[start_of_context:]
            for segment in page.segments:
                segment_text_plain = segment.to_text()
                segment_text_canonical = canonical_text_for_audio(segment_text_plain, phonetic=phonetic)
                context = '' if not self.use_context else previous_canonical_text[(-1 * self.max_context_length):]
                segment_file_path = segment_cache.get((segment_text_plain, context), None)
                if segment_file_path and not string_has_no_audio_content(segment_text_plain):
                    segment_audio_files.append(segment_file_path)
                    previous_canonical_texts.append(segment_text_canonical)
                    previous_canonical_text = ' '.join(previous_canonical_texts) 
            
            page_text = page.to_text()
            page_text_canonical = canonical_text_for_audio(page_text, phonetic=phonetic)
            page_audio_file = self.audio_repository.get_entry(self.segment_engine_id, self.segment_language_id, self.segment_voice_id,
                                                              page_text_canonical, context=page_context, callback=callback)
            
            page_data.append({
                'text': page_text,
                'canonical_text': page_text_canonical,
                'context': page_context,
                'segment_audio_files': segment_audio_files,
                'file_path': page_audio_file
            })
        
        return page_data


    def _get_missing_audio(self, words_data, segments_data, phonetic=False, callback=None):

        #print(f'--- _get_missing_audio input: words_data = {words_data}')
        #print(f'--- _get_missing_audio input: segments_data = {segments_data}')
        
        missing_words = [word_data['text'] for word_data in words_data if not word_data['file_path']]
        missing_segments = [segment_data['text'] for segment_data in segments_data if not segment_data['file_path']]

        post_task_update(callback, f"--- Found {len(missing_words)} words without audio")
        post_task_update(callback, f"--- Found {len(missing_segments)} segments without audio")

        #print(f'--- _get_missing_audio output: missing_words = {missing_words}')
        #print(f'--- _get_missing_audio output: missing_segments = {missing_segments}')

        return missing_words, missing_segments

    def generate_audio_metadata(self, text_obj, type='default', format='default', phonetic=False, callback=None):
        words_data, segments_data = self._get_all_audio_data(text_obj, phonetic=phonetic, callback=callback)

##        if format != 'default':
##            words_metadata = [ format_audio_metadata_item(item, format, 'words') for item in words_metadata ]
##            segments_metadata = [ format_audio_metadata_item(item, format, 'segments') for item in segments_metadata ]

        if type == 'words':
            return words_data
        elif type == 'segments':
            return segments_data
        else:
            return { 'words': words_data, 'segments': segments_data }

    def _create_and_store_missing_mp3s(self, text_items, words_or_segments, phonetic=False, callback=None):
        #print(f"_create_and_store_missing_mp3s({text_items}, {words_or_segments}, phonetic={phonetic})")
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
            canonical_text = canonical_text_for_audio(text, phonetic=phonetic) if words_or_segments == 'segments' else canonical_word_for_audio(text)
            post_task_update(callback, f"--- Creating mp3 for '{canonical_text}' ({i}/{len(text_items)})")
            try:
                unique_filename = f"{uuid.uuid4()}.mp3"
                temp_file = os.path.join(temp_dir, unique_filename)

                result = tts_engine_to_use.create_mp3(language_id_to_use, voice_id_to_use, canonical_text, temp_file, callback=callback)
                if result:
                    file_path = self.audio_repository.store_mp3(engine_id_to_use, language_id_to_use, voice_id_to_use, temp_file, callback=callback)
                    # Context is irrelevant in TTS audio, since it currently can't affect the audio generated
                    self.audio_repository.add_or_update_entry(engine_id_to_use, language_id_to_use, voice_id_to_use, canonical_text, file_path, context='')
                else:
                    file_path = None
                    post_task_update(callback, f"--- Failed to create mp3 for '{text}'")
                text_file_paths.append({'text': text, 'canonical_text': canonical_text, 'context': '', 'file_path': file_path})
            except Exception as e:
                post_task_update(callback, f"*** Error creating TTS file: '{str(e)}'\n{traceback.format_exc()}")
                
        shutil.rmtree(temp_dir)
        return text_file_paths

    def _generate_missing_page_audio(self, page_audio_data, callback=None):
        engine_id = self.segment_engine_id
        language_id = self.segment_language_id
        voice_id = self.segment_voice_id

        temp_dir = tempfile.mkdtemp()
            
        for page_data in page_audio_data:
            try:
                if not page_data['file_path'] and page_data['segment_audio_files']:
                    canonical_text = page_data['canonical_text']
                    context = page_data['context']
                    segment_audio_files = page_data['segment_audio_files']
                    
                    unique_mp3_filename = f"{uuid.uuid4()}.mp3"
                    unique_txt_filename = f"{uuid.uuid4()}.txt"
                    temp_page_mp3 = os.path.join(temp_dir, unique_mp3_filename)
                    temp_page_txt = os.path.join(temp_dir, unique_txt_filename)
                    concatenate_audio_files(segment_audio_files, temp_page_txt, temp_page_mp3)
                    
                    file_path = self.audio_repository.store_mp3(engine_id, language_id, voice_id, temp_page_mp3, callback=callback)
                    self.audio_repository.add_or_update_entry(engine_id, language_id, voice_id, canonical_text, file_path, context=context)
                    page_data['file_path'] = file_path      
            except Exception as e:
                post_task_update(callback, f"*** Error creating page file: '{str(e)}'\n{traceback.format_exc()}")

        shutil.rmtree(temp_dir)
        return page_audio_data


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
    def _store_existing_human_audio_mp3s(self, metadata, temp_dir, words_or_segments='segments', callback=None):
        post_task_update(callback, f'--- Calling _store_existing_human_audio_mp3s with {len(metadata)} metadata items and audio dir = {temp_dir}')
        #print(f'--- metadata:')
        #pprint.pprint(metadata)
        previous_canonical_text = ''
        previous_canonical_texts = []
        #i = 0
         
        for i, metadata_item in enumerate(metadata, 1):
        #for metadata_item in metadata:
            try:
                text = metadata_item['text']
                file = metadata_item['file']
                text_canonical = canonical_text_for_audio(text)
                start_of_context = -1 * self.max_context_length
                context = '' if ( not self.use_context or words_or_segments == 'words' ) else previous_canonical_text[start_of_context:]
                if file:
                    post_task_update(callback, f"--- Adding mp3 to repository for '{text}', ({i}/{len(metadata)})")
                    temp_file = os.path.join(temp_dir, file)
                    file_path = self.audio_repository.store_mp3('human_voice', self.language, self.human_voice_id, temp_file, keep_file_name=False)
                    self.audio_repository.add_or_update_entry('human_voice', self.language, self.human_voice_id, text_canonical, file_path, context=context)
                    previous_canonical_texts.append(text_canonical)
                    previous_canonical_text = ' '.join(previous_canonical_texts) 
            except Exception as e:
                post_task_update(callback, f"*** Error trying to process metadata item {metadata_item}: {str(e)}")

    def _add_audio_annotations(self, text_obj, words_data, segments_data, page_data, phonetic=False, callback=None):
        post_task_update(callback, f"--- Adding audio annotations to internalised text")
        text_obj.voice = self.printname_for_voice()

        previous_canonical_text = ''
        previous_canonical_texts = []
        
        word_cache = { item['text']: item['file_path'] for item in words_data }
        segment_cache = { ( item['text'], item['context'] ): item['file_path'] for item in segments_data }
        page_cache = { ( item['text'], item['context'] ): item['file_path'] for item in page_data }
        
        for page in text_obj.pages:
            if not phonetic:
                page_text_plain = page.to_text()
                page_text_canonical = canonical_text_for_audio(page_text_plain, phonetic=False)
                start_of_context = -1 * self.max_context_length
                page_context = '' if not self.use_context else previous_canonical_text[start_of_context:]

                if ( page_text_plain, page_context ) in page_cache and page_cache[( page_text_plain, page_context )]:
                    absolute_page_file_path = absolute_file_name(page_cache[( page_text_plain, page_context )])
                    #google\en-GB\en-GB-News-J\en-GB-News-J_20240805_033226_a5c481e3-7641-408a-8541-c29e32467e28.mp3"
                    absolute_page_file_path_components = absolute_page_file_path.split('/')
                    base_name = absolute_page_file_path_components[-1]
                    voice_id = absolute_page_file_path_components[-2]
                    language_id = absolute_page_file_path_components[-3]
                    engine_id = absolute_page_file_path_components[-4]
                    page.annotations['tts'] = {
                        "engine_id": engine_id,
                        "language_id": language_id,
                        "voice_id": voice_id,
                        "file_path": base_name,
                        }
            
            for segment in page.segments:
                segment_text_plain = segment.to_text()
                segment_text_canonical = canonical_text_for_audio(segment_text_plain, phonetic=phonetic)
                context = '' if not self.use_context else previous_canonical_text[(-1 * self.max_context_length):]
                
                segment_file_path = segment_cache[( segment_text_plain, context )] if ( segment_text_plain, context ) in segment_cache else 'placeholder.mp3'
                if segment_file_path and not string_has_no_audio_content(segment_text_plain):
                    segment.annotations['tts'] = {
                        "engine_id": self.segment_engine_id,
                        "language_id": self.segment_language_id,
                        "voice_id": self.segment_voice_id,
                        "file_path": segment_file_path,
                    }
                if not string_has_no_audio_content(segment_text_plain):
                    previous_canonical_texts.append(segment_text_canonical)
                    previous_canonical_text = ' '.join(previous_canonical_texts) 

                for content_element in segment.content_elements:
                    if content_element.type == 'Word':
                        if phonetic and 'phonetic' in content_element.annotations:
                            audio_word = content_element.annotations['phonetic']
                        elif not phonetic:
                            audio_word = content_element.content
                        else:
                            audio_word = None

                        if not audio_word:
                            file_path = None
                        elif phonetic and audio_word == '(silent)':
                            file_path = None
                        elif audio_word in word_cache:
                            file_path = word_cache[audio_word]
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

# String has no audio content if it's just HTML tags, punctuation marks and separators
def string_has_no_audio_content(s):
    s1 = regex.sub(r"<\/?\w+>", '', s)
    return not s1 or all(regex.match(r"[\p{P} \n|]", c) for c in s1)

def concatenate_audio_files(segment_audio_files, tmp_text_file, output_file):
    # Create a temporary text file with the list of segment audio files
    with open(tmp_text_file, 'w') as f:
        for audio_file in segment_audio_files:
            f.write(f"file '{audio_file}'\n")
    
    # Use ffmpeg to concatenate the audio files
    command = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', tmp_text_file,
        '-c', 'copy',
        output_file
    ]
    subprocess.run(command)
