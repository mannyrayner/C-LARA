"""
clara_image_repository.py

This module implements an image repository that stores image files and associated metadata. The code is based
on the earlier class AudioRepository, defined in clara_audio_repository.py.

Classes:
- ImageRepository: Class for managing the audio repository.

The ImageRepository class provides methods for adding entries, retrieving entries,
getting the image directory, and storing image files.

Use clara_database_adapter so that the code works for both sqlite3 and PostgreSQL databases.

SQL templates must be written in PostgreSQL format with %s signifying a parameter placeholder.
The function clara_database_adapter.localise_sql_query converts this to sqlite3 format if necessary.
"""

from .clara_database_adapter import connect, localise_sql_query

from .clara_utils import _s3_storage, get_config, absolute_file_name, absolute_local_file_name, file_exists, local_file_exists, copy_local_file, basename
from .clara_utils import make_directory, remove_directory, directory_exists, local_directory_exists, make_local_directory
from .clara_utils import list_files_in_directory, post_task_update

from .clara_classes import InternalCLARAError

from pathlib import Path

import os
import traceback

config = get_config()

class ImageRepository:
    def __init__(self, callback=None):   
        self.db_file = absolute_local_file_name(config.get('image_repository', ('db_file' if _s3_storage else 'db_file_local')))
        self.base_dir = absolute_file_name(config.get('image_repository', 'base_dir'))
        self._initialize_repository(callback=callback)

    def _initialize_repository(self, callback=None):
        # Similar initialization logic as AudioRepository
        # ...

    def delete_entries_for_project(self, project_id, callback=None):
        # Logic to delete all images associated with a specific project
        # ...

    def add_entry(self, project_id, image_name, file_path, associated_text=None, associated_areas=None, callback=None):
        # Logic to add an image entry to the repository
        # ...

    def get_entry(self, project_id, image_name, callback=None):
        # Logic to retrieve an image entry from the repository
        # ...

    def get_project_directory(self, project_id):
        # Returns the directory path where images for a specific project are stored
        return absolute_file_name(Path(self.base_dir) / project_id)

    def store_image(self, project_id, source_file, keep_file_name=True):
        # Logic to store an image file in the repository
        # ...
