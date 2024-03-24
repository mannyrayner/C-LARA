"""
clara_audio_repository_orm.py

This module implements an audio repository that stores metadata and generated audio files from human voices and various TTS engines.
Data is stored in the Django ORM using the class AudioMetadata

Classes:
- AudioRepositoryORM: Class for managing the audio repository.

The AudioRepositoryORM class provides methods for adding entries, retrieving entries, getting the voice directory, and storing mp3 files.
"""

from .clara_tts_api import get_tts_engine_types
from .clara_utils import _s3_storage, get_config, absolute_file_name, absolute_local_file_name, file_exists, local_file_exists, copy_local_file, basename
from .clara_utils import make_directory, remove_directory, directory_exists, local_directory_exists, make_local_directory, copy_directory
from .clara_utils import list_files_in_directory, post_task_update

from .clara_classes import InternalCLARAError

from pathlib import Path

import os
import pprint
import traceback

config = get_config()

_trace = False
# _trace = True

class AudioRepositoryORM:
    def __init__(self, initialise_from_non_orm=False, callback=None):
        self.base_dir = absolute_file_name(config.get('audio_repository', 'base_dir_orm'))
        
        # Create base_dir if it doesn't exist
        if not directory_exists(self.base_dir):
            make_directory(self.base_dir, parents=True, exist_ok=True)
            post_task_update(callback, f'--- Created base directory for audio repository, {self.base_dir}')

            if initialise_from_non_orm:
                self.initialise_from_non_orm_repository(callback=callback)

    def initialise_from_non_orm_repository(self, callback=None):
        from .clara_audio_repository import AudioRepository
        
        non_orm_repository = AudioRepository(callback=callback)
        exported_data = non_orm_repository.export_audio_metadata()

        if not exported_data:
            post_task_update(callback, f'--- No data found in non-ORM repository')
            return
            
        post_task_update(callback, f'--- Importing {len(exported_data)} items from non-ORM repository')
        
        base_dir_non_orm = absolute_file_name(config.get('audio_repository', 'base_dir'))
        base_dir_orm = absolute_file_name(config.get('audio_repository', 'base_dir_orm'))

        copy_directory(base_dir_non_orm, base_dir_orm)
        
        new_objects = []
        
        for data in exported_data:
            # Adjust the file path
            new_file_path = data['file_path'].replace(str(base_dir_non_orm), str(base_dir_orm))
            
            # Create a new AudioMetadata instance (without saving to DB yet)
            new_objects.append(AudioMetadata(
                engine_id=data['engine_id'],
                language_id=data['language_id'],
                voice_id=data['voice_id'],
                text=data['text'],
                context=data['context'],
                file_path=new_file_path,
            ))

        # Use bulk_create to add all new objects to the database in a single query
        AudioMetadata.objects.bulk_create(new_objects)

