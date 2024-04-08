"""
clara_audio_repository_orm.py

This module implements an audio repository that stores metadata and generated audio files from human voices and various TTS engines.
Data is stored in the Django ORM using the class AudioMetadata

Classes:
- AudioRepositoryORM: Class for managing the audio repository.

The AudioRepositoryORM class provides methods for adding entries, retrieving entries, getting the voice directory, and storing mp3 files.
"""

from django.db.models import Q

from .models import AudioMetadata

from .clara_tts_api import get_tts_engine_types
from .clara_utils import _s3_storage, get_config, absolute_file_name, absolute_local_file_name, file_exists, local_file_exists, copy_local_file, basename
from .clara_utils import make_directory, remove_directory, directory_exists, local_directory_exists, make_local_directory, copy_directory
from .clara_utils import list_files_in_directory, post_task_update, generate_unique_file_name, adjust_file_path_for_imported_data

from .clara_classes import InternalCLARAError

import os
import pprint
import traceback

from pathlib import Path

config = get_config()

_trace = False
#_trace = True

class AudioRepositoryORM:
    #def __init__(self, initialise_from_non_orm=False, callback=None):
    def __init__(self, callback=None):
        self.base_dir = absolute_file_name(config.get('audio_repository', 'base_dir_orm'))

        if not directory_exists(self.base_dir):
            make_directory(self.base_dir, parents=True, exist_ok=True)
            post_task_update(callback, f'--- Created base directory for audio repository, {self.base_dir}')
##            # Performing initialise_from_non_orm_repository copies base_dir from the non-ORM one and also initialises the database        
##            if initialise_from_non_orm:
##                self.initialise_from_non_orm_repository(callback=callback)
##            # Otherwise just create base_dir 
##            else:
##                make_directory(self.base_dir, parents=True, exist_ok=True)
##                post_task_update(callback, f'--- Created base directory for audio repository, {self.base_dir}')
##        elif initialise_from_non_orm:
##            post_task_update(callback, f'--- Audio repository already initialised, {self.base_dir} exists')

##    def initialise_from_non_orm_repository(self, callback=None):
##        from .clara_audio_repository import AudioRepository
##
##        try:
##            non_orm_repository = AudioRepository(callback=callback)
##            exported_data = non_orm_repository.export_audio_metadata()
##
##            if not exported_data:
##                post_task_update(callback, f'--- No data found in non-ORM repository')
##                # We have no directory to copy, so create the base directory
##                make_directory(self.base_dir, parents=True, exist_ok=True)
##                post_task_update(callback, f'--- Created base directory for audio repository, {self.base_dir}')
##                return
##                
##            post_task_update(callback, f'--- Importing {len(exported_data)} items from non-ORM repository')
##            
##            base_dir_non_orm = absolute_file_name(config.get('audio_repository', 'base_dir'))
##            base_dir_orm = absolute_file_name(config.get('audio_repository', 'base_dir_orm'))
##            
##            new_objects = []
##            
##            for data in exported_data:
##                # Adjust the file path
##                new_file_path = adjust_file_path_for_imported_data(data['file_path'], base_dir_non_orm, base_dir_orm, callback=callback) 
##                
##                # Create a new AudioMetadata instance (without saving to DB yet)
##                new_objects.append(AudioMetadata(
##                    engine_id=data['engine_id'],
##                    language_id=data['language_id'],
##                    voice_id=data['voice_id'],
##                    text=data['text'],
##                    context=data['context'],
##                    file_path=new_file_path,
##                ))
##
##            # Use bulk_create to add all new objects to the database in a single query
##            AudioMetadata.objects.bulk_create(new_objects)
##
##            copy_directory(base_dir_non_orm, base_dir_orm)
##
##        except Exception as e:
##            post_task_update(callback, f'Error initialising from non-ORM repository: "{str(e)}"\n{traceback.format_exc()}')
##            return []

    def delete_entries_for_language(self, engine_id, language_id, callback=None):
        try:
            # Delete database entries for the specified engine and language
            entries_deleted = AudioMetadata.objects.filter(engine_id=engine_id, language_id=language_id).delete()
            post_task_update(callback, f'--- Deleted {entries_deleted[0]} DB entries for engine ID {engine_id} and language ID {language_id}')

            # Delete associated audio files from the file system
            language_dir = self.get_language_directory(engine_id, language_id)
            if directory_exists(language_dir):
                remove_directory(language_dir)
                post_task_update(callback, f'--- Audio files for engine ID {engine_id} and language ID {language_id} deleted')
            
            post_task_update(callback, 'Finished deletion process successfully.')

        except Exception as e:
            error_message = f'*** Error when trying to delete audio data for engine ID {engine_id} and language ID {language_id}: "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)

    def add_or_update_entry(self, engine_id, language_id, voice_id, text, file_path, context='', callback=None):
        try:
            # Try to get the existing entry
            audio_metadata, created = AudioMetadata.objects.update_or_create(
                engine_id=engine_id,
                language_id=language_id,
                voice_id=voice_id,
                text=text,
                context=context,
                defaults={'file_path': file_path}
    )

            if created:
                post_task_update(callback, f'--- Inserted new audio metadata entry for {text} in {language_id}')
            else:
                post_task_update(callback, f'--- Updated existing audio metadata entry for {text} in {language_id}')

        except Exception as e:
            error_message = f'*** Error when inserting/updating "{language_id}; {text}; {file_path}" in audio metadata: "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Audio metadata database inconsistency')

    def store_mp3(self, engine_id, language_id, voice_id, source_file, keep_file_name=False, callback=None):
        try:
            if not local_file_exists(source_file):
                error_message = f'*** Error when storing mp3 "{source_file}" in audio repository: file not found'
                post_task_update(callback, error_message)
                raise InternalCLARAError(message='Audio repository error')
            voice_dir = self.get_voice_directory(engine_id, language_id, voice_id)
            make_directory(voice_dir, parents=True, exist_ok=True)
            file_name = basename(source_file) if keep_file_name else generate_unique_file_name(voice_id, extension='mp3')
            destination_path = str(Path(voice_dir) / file_name)
            copy_local_file(source_file, destination_path)
            return destination_path
        except Exception as e:
            error_message = f'*** Error when storing mp3 "{source_file}" in audio repository: "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Audio repository error')

    def get_entry(self, engine_id, language_id, voice_id, text, context='', callback=None):
        try:
            # Use Django ORM to filter the AudioMetadata based on provided parameters
            query_set = AudioMetadata.objects.filter(
                engine_id=engine_id, 
                language_id=language_id, 
                voice_id=voice_id, 
                text=text, 
                context=context
            )

            # Get the first matching entry if it exists
            entry = query_set.first()

            # Return the file_path if an entry was found, otherwise return None
            return entry.file_path if entry else None

        except Exception as e:
            error_message = f'*** Error when looking for "{text}" in TTS database: "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='TTS database inconsistency')

    def get_entry_batch(self, engine_id, language_id, voice_id, text_and_context_items, callback=None):
        if _trace:
            print(f'--- get_entry_batch({engine_id}, {language_id}, {voice_id},')
            pprint.pprint(text_and_context_items)
        try:
            # Check if all contexts are empty
            all_contexts_empty = all(item['context'] == '' for item in text_and_context_items)
            
            if all_contexts_empty:
                # If all contexts are empty, we can filter without using Q objects for each pair
                texts = [item['canonical_text'] for item in text_and_context_items]
                query_set = AudioMetadata.objects.filter(engine_id=engine_id, language_id=language_id, voice_id=voice_id, text__in=texts, context='')

                # Map the results to a dictionary
                results = {(entry.text, entry.context): entry.file_path for entry in query_set}
            else:
                # If contexts are not uniformly empty, use Q objects to match specific (text, context) pairs
                query = Q()
                for item in text_and_context_items:
                    text = item['canonical_text']
                    context = item['context']
                    query |= Q(text=text, context=context, engine_id=engine_id, language_id=language_id, voice_id=voice_id)

                query_set = AudioMetadata.objects.filter(query)
                results = {(entry.text, entry.context): entry.file_path for entry in query_set}

            # Whichever method we chose, add null values for the keys that have no value
            for item in text_and_context_items:
                key = (item['canonical_text'], item['context'])
                if not key in results:
                    results[key] = None

            if _trace:
                print('--- results:')
                pprint.pprint(results)
            return results

        except Exception as e:
            error_message = f'*** Error when performing get_entry_batch in TTS database: "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='TTS database inconsistency')

    def get_language_directory(self, engine_id, language_id):
        return absolute_file_name( Path(self.base_dir) / engine_id / language_id )

    def get_voice_directory(self, engine_id, language_id, voice_id):
        return absolute_file_name( Path(self.base_dir) / engine_id / language_id / voice_id )

