"""
clara_tts_annotator.py

This module implements a TTS annotator that can generate and store audio files for words and segments in a given Text object.

Classes:
- TTSAnnotator: Class for handling TTS annotations for a Text object.

Functions:
- canonical_word_for_tts(text): Returns a canonical version of the input text for TTS word processing.
- canonical_text_for_tts(text): Returns a canonical version of the input text for TTS segment processing.

The TTSAnnotator class provides methods for annotating a Text object with audio files generated from a TTS engine. It uses the TTS repository to store and retrieve audio files.
"""

from .clara_classes import Text
from .clara_utils import absolute_local_file_name, make_tmp_file, file_exists, remove_file, post_task_update
from .clara_tts_api import get_tts_engine, get_default_voice, get_language_id, create_tts_engine
from .clara_tts_repository import TTSRepository

import re
import os
import tempfile
import shutil
import uuid

class TTSAnnotator:
    def __init__(self, language, tts_engine_type=None, tts_repository=None):
        self.language = language
        self.tts_engine = create_tts_engine(tts_engine_type) if tts_engine_type else get_tts_engine(language)
        self.engine_id = self.tts_engine.tts_engine_type if self.tts_engine else None
        self.voice_id = get_default_voice(language, self.tts_engine) if self.tts_engine else None
        self.language_id = get_language_id(language, self.tts_engine) if self.tts_engine else None
        self.tts_repository = tts_repository or TTSRepository()

    def annotate_text(self, text_obj, callback=None):
        if self.tts_engine:
        
            missing_words, missing_segments = self._get_missing_audio(text_obj, callback=callback)

            if missing_words:
                post_task_update(callback, f"--- Creating TTS audio for words")
                self._create_and_store_missing_mp3s(missing_words, callback=callback)
                post_task_update(callback, f"--- TTS audio for words created")

            if missing_segments:
                post_task_update(callback, f"--- Creating TTS audio for segments")
                self._create_and_store_missing_mp3s(missing_segments, callback=callback)
                post_task_update(callback, f"--- TTS audio for segments created")

        post_task_update(callback, f"--- All TTS files should be there")
        self._add_tts_annotations(text_obj, callback=callback)

    def _get_missing_audio(self, text_obj, callback=None):
        post_task_update(callback, f"--- Looking for missing words and segments")
        words = set()
        segments = set()
        for page in text_obj.pages:
            for segment in page.segments:
                segment_text = canonical_text_for_tts(segment.to_text())
                segments.add(segment_text)
                for content_element in segment.content_elements:
                    if content_element.type == 'Word':
                        canonical_word = canonical_word_for_tts(content_element.content)
                        words.add(canonical_word)

        missing_words = []
        missing_segments = []

        # We don't want to include trivial strings, so check using strip().
        for word in words:
            #post_task_update(callback, f"Checking TTS file for '{word}'")
            if word.strip() and not self.tts_repository.get_entry(self.engine_id, self.language_id, self.voice_id, word):
                missing_words.append(word)
        post_task_update(callback, f"--- Found {len(missing_words)} words without audio")

        for segment in segments:
            #post_task_update(callback, f"Checking TTS file for '{segment}'")
            if segment.strip() and not self.tts_repository.get_entry(self.engine_id, self.language_id, self.voice_id, segment):
                missing_segments.append(segment)
        post_task_update(callback, f"--- Found {len(missing_segments)} segments without audio")

        return missing_words, missing_segments

    # ASYNCHRONOUS PROCESSING
    def _create_and_store_missing_mp3s(self, missing_audio, callback=None):
        temp_dir = tempfile.mkdtemp()

        for i, audio in enumerate(missing_audio, 1):
            post_task_update(callback, f"--- Creating mp3 for '{audio}' ({i}/{len(missing_audio)})")
            unique_filename = f"{uuid.uuid4()}.mp3"
            temp_file = os.path.join(temp_dir, unique_filename)
            if self.tts_engine.create_mp3(self.language_id, self.voice_id, audio, temp_file):
                file_path = self.tts_repository.store_mp3(self.engine_id, self.language_id, self.voice_id, temp_file)
                self.tts_repository.add_entry(self.engine_id, self.language_id, self.voice_id, audio, file_path)
            else:
                if callback:
                    post_task_update(callback, f"--- Failed to create mp3 for '{audio}'")

        shutil.rmtree(temp_dir)

    def _add_tts_annotations(self, text_obj, callback=None):
        post_task_update(callback, f"--- Adding TTS annotations to internalised text")
        text_obj.voice = self.printname_for_voice()
        
        for page in text_obj.pages:
            for segment in page.segments:
                segment_text = canonical_text_for_tts(segment.to_text())
                segment_file_path = self.tts_repository.get_entry(self.engine_id, self.language_id, self.voice_id, segment_text)
                if not segment_file_path:
                    post_task_update(callback, f"--- Warning: no TTS annotation available for segment '{segment_text}'")
                    #segment_file_path = 'placeholder.mp3'
                else:
                    segment.annotations['tts'] = {
                        "engine_id": self.engine_id,
                        "language_id": self.language_id,
                        "voice_id": self.voice_id,
                        "file_path": segment_file_path,
                    }                   

                for content_element in segment.content_elements:
                    if content_element.type == 'Word':
                        canonical_word = canonical_word_for_tts(content_element.content)
                        file_path = self.tts_repository.get_entry(self.engine_id, self.language_id, self.voice_id, canonical_word)
                        if not file_path:
                            post_task_update(callback, f"--- Warning: no TTS annotation available for word '{canonical_word}'")
                            file_path = 'placeholder.mp3'
                        content_element.annotations['tts'] = {
                            "engine_id": self.engine_id,
                            "language_id": self.language_id,
                            "voice_id": self.voice_id,
                            "file_path": file_path,
                        }
        post_task_update(callback, f"--- TTS annotations added to internalised text")

    def printname_for_voice(self):
        if self.engine_id:
            return '_'.join([ self.engine_id, self.language_id, self.voice_id ])
        else:
            return 'No TTS voice'

def canonical_word_for_tts(text):
    return text.lower()

def canonical_text_for_tts(text):
    # Remove HTML markup
    text = re.sub(r'<[^>]*>', '', text)

    # Consolidate sequences of whitespaces to a single space
    text = re.sub(r'\s+', ' ', text)

    # Trim leading and trailing spaces
    text = text.strip()

    return text
