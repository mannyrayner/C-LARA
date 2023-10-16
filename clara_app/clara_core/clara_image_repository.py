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

from .clara_classes import Image, InternalCLARAError

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
        if not directory_exists(self.base_dir):
            make_directory(self.base_dir, parents=True, exist_ok=True)

        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()

            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute('''CREATE TABLE IF NOT EXISTS image_metadata
                                  (id INTEGER PRIMARY KEY,
                                   project_id TEXT,
                                   image_name TEXT,
                                   file_path TEXT,
                                   associated_text TEXT,
                                   associated_areas TEXT,
                                   page INTEGER DEFAULT 1,
                                   position TEXT DEFAULT 'bottom',
                                   UNIQUE(project_id, image_name))''')
            else:
                # Assume Postgres, which does auto-incrementing differently
                cursor.execute('''CREATE TABLE IF NOT EXISTS image_metadata
                                  (id SERIAL PRIMARY KEY,
                                   project_id TEXT,
                                   image_name TEXT,
                                   file_path TEXT,
                                   associated_text TEXT,
                                   associated_areas TEXT,
                                   page INTEGER DEFAULT 1,
                                   position TEXT DEFAULT 'bottom',
                                   UNIQUE(project_id, image_name))''')

            connection.commit()
            connection.close()
            post_task_update(callback, f'--- Initialised image repository')

        except Exception as e:
            error_message = f'*** Error when trying to initialise image database: "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Image database inconsistency')

    def delete_entries_for_project(self, project_id, callback=None):
        try:
            project_id = str(project_id)
            post_task_update(callback, f'--- Deleting image repository DB entries for {project_id}')
            connection = connect(self.db_file)
            cursor = connection.cursor()
            cursor.execute(localise_sql_query("DELETE FROM image_metadata WHERE project_id = %s"), (project_id,))
            connection.commit()
            connection.close()
            post_task_update(callback, f'--- DB entries for {project_id} deleted')

            post_task_update(callback, f'--- Deleting image files for {project_id}')
            project_dir = self.get_project_directory(project_id)
            if directory_exists(project_dir):
                remove_directory(project_dir)
            post_task_update(callback, f'--- image files for {project_id} deleted')
            post_task_update(callback, f'finished')
        except Exception as e:
            error_message = f'*** Error when trying to delete image data: "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            post_task_update(callback, f'error')

    def add_entry(self, project_id, image_name, file_path, associated_text='', associated_areas='', page=1, position='bottom', callback=None):
        try:
            post_task_update(callback, f'--- Storing image for project {project_id}: name = {image_name}, file = {file_path}, areas = "{associated_areas}"')
            project_id = str(project_id) # Ensure project_id is a string
            page = str(page)  # Ensure page is a string
            connection = connect(self.db_file)
            cursor = connection.cursor()
            
            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute("INSERT OR REPLACE INTO image_metadata (project_id, image_name, file_path, associated_text, associated_areas, page, position) VALUES (?, ?, ?, ?, ?, ?, ?)",
                               (project_id, image_name, file_path, associated_text, associated_areas, page, position))
            else:  # Assume postgres
                cursor.execute("""INSERT INTO image_metadata (project_id, image_name, file_path, associated_text, associated_areas, page, position) 
                                  VALUES (%(project_id)s, %(image_name)s, %(file_path)s, %(associated_text)s, %(associated_areas)s, %(page)s, %(position)s)
                                  ON CONFLICT (project_id, image_name) 
                                  DO UPDATE SET file_path = %(file_path)s, associated_text = %(associated_text)s, associated_areas = %(associated_areas)s, page = %(page)s, position = %(position)s""",
                               {
                                  'project_id': project_id,
                                  'image_name': image_name,
                                  'file_path': file_path,
                                  'associated_text': associated_text,
                                  'associated_areas': associated_areas,
                                  'page': page,
                                  'position': position
                               })
            
            connection.commit()
            connection.close()
            self.get_current_entry(project_id, callback=callback)
        except Exception as e:
            post_task_update(callback, f'*** Error when inserting "{project_id}/{image_name}/{file_path}" into Image database: "{str(e)}"')
            raise InternalCLARAError(message='Image database inconsistency')

    def store_associated_areas(self, project_id, image_name, associated_areas, callback=None):
        try:
            project_id = str(project_id)
            connection = connect(self.db_file)
            cursor = connection.cursor()
            cursor.execute(localise_sql_query("UPDATE image_metadata SET associated_areas = %s WHERE project_id = %s AND image_name = %s"),
                           (associated_areas, project_id, image_name))
            connection.commit()
            connection.close()
        except Exception as e:
            post_task_update(callback, f'*** Error when updating associated_areas for "{project_id}/{image_name}": "{str(e)}"')
            raise InternalCLARAError(message='Image database inconsistency')

    def get_entry(self, project_id, image_name, callback=None):
        try:
            project_id = str(project_id)
            connection = connect(self.db_file)
            cursor = connection.cursor()
            
            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute("SELECT file_path, associated_text, associated_areas, page, position FROM image_metadata WHERE project_id = ? AND image_name = ?",
                               (project_id, image_name))
            else:
                # Assume postgres
                cursor.execute("""SELECT file_path, associated_text, associated_areas, page, position FROM image_metadata 
                                  WHERE project_id = %(project_id)s 
                                  AND image_name = %(image_name)s""",
                               {
                                  'project_id': project_id,
                                  'image_name': image_name
                               })
            
            result = cursor.fetchone()
            connection.close()
            
            if result:
                if os.getenv('DB_TYPE') == 'sqlite':
                    image = Image(result[0], image_name, result[1], result[2], result[3], result[4])
                else:  # Assuming PostgreSQL
                    image = Image(result['file_path'], image_name, result['associated_text'], 
                                  result['associated_areas'], result['page'], result['position'])
            else:
                image = None
            
            return image
                
        except Exception as e:
            post_task_update(callback, f'*** Error when looking for "{image_name}" in Image database: "{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Image database inconsistency')


    def get_current_entry(self, project_id, callback=None):
        try:
            project_id = str(project_id)
            post_task_update(callback, f'--- Retrieving current image for project {project_id}')
            connection = connect(self.db_file)
            cursor = connection.cursor()
            
            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute("SELECT file_path, image_name, associated_text, associated_areas, page, position FROM image_metadata WHERE project_id = ? LIMIT 1",
                               (project_id,))
            else:
                # Assume postgres
                cursor.execute("""SELECT file_path, image_name, associated_text, associated_areas, page, position FROM image_metadata 
                                  WHERE project_id = %(project_id)s 
                                  LIMIT 1""",
                               {
                                  'project_id': project_id
                               })
            
            result = cursor.fetchone()
            connection.close()
            
            if result:
                if os.getenv('DB_TYPE') == 'sqlite':
                    image = Image(result[0], result[1], result[2], result[3], result[4], result[5])
                else:  # Assuming PostgreSQL
                    image = Image(result['file_path'], result['image_name'], result['associated_text'],
                                  result['associated_areas'], result['page'], result['position'])
            else:
                image = None
            
            return image
            post_task_update(callback, f'--- Current image for project {project_id}: name = {to_return[1]}, file = {to_return[0]}, text = "{to_return[2]}", areas = "{to_return[3]}", page = {to_return[4]}, position = {to_return[5]}')
            return to_return
                    
        except Exception as e:
            post_task_update(callback, f'*** Error when retrieving current entry for project {project_id}: {str(e)}')
            raise InternalCLARAError(message='Image database inconsistency')


    def get_project_directory(self, project_id):
        # Returns the directory path where images for a specific project are stored
        return absolute_file_name(Path(self.base_dir) / str(project_id))

    def store_image(self, project_id, source_file, keep_file_name=True, callback=None):
        project_id = str(project_id)
        project_dir = self.get_project_directory(project_id)
        make_directory(project_dir, parents=True, exist_ok=True)
        file_name = basename(source_file) if keep_file_name else f"{project_id}_{len(list_files_in_directory(project_dir)) + 1}.png"
        destination_path = str(Path(project_dir) / file_name)
        copy_local_file(source_file, destination_path)
        return destination_path

    def remove_entry(self, project_id, image_name, callback=None):
        try:
            project_id = str(project_id)
            post_task_update(callback, f'--- Removing entry for image {image_name} in project {project_id}')
            connection = connect(self.db_file)
            cursor = connection.cursor()
            cursor.execute(localise_sql_query("DELETE FROM image_metadata WHERE project_id = %s AND image_name = %s"),
                           (project_id, image_name))
            connection.commit()
            connection.close()
            post_task_update(callback, f'--- Entry for image {image_name} removed successfully')
        except Exception as e:
            post_task_update(callback, f'*** Error when removing entry for image {image_name}: {str(e)}')
            raise InternalCLARAError(message='Image database inconsistency')

    def get_annotated_image_text(self, project_id, callback=None):
        try:
            project_id = str(project_id)
            post_task_update(callback, f'--- Retrieving annotated image text for project {project_id}')
            connection = connect(self.db_file)
            cursor = connection.cursor()

            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute("SELECT image_name, associated_text, page, position FROM image_metadata WHERE project_id = ?",
                               (project_id,))
            else:
                # Assume postgres
                cursor.execute("""SELECT image_name, associated_text, page, position FROM image_metadata 
                                  WHERE project_id = %(project_id)s""",
                               {
                                  'project_id': project_id
                               })

            results = cursor.fetchall()
            connection.close()

            annotated_image_text = ""
            for result in results:
                if os.getenv('DB_TYPE') == 'sqlite':
                    image_name, associated_text, page, position = result
                else:  # Assuming PostgreSQL
                    image_name = result['image_name']
                    associated_text = result['associated_text']
                    page = result['page']
                    position = result['position']

                annotated_image_text += f"<page img='{image_name}' page='{page}' position='{position}'>\n{associated_text}\n"

            post_task_update(callback, f'--- Annotated image text for project {project_id} generated')
            return annotated_image_text

        except Exception as e:
            post_task_update(callback, f'*** Error when retrieving annotated image text for project {project_id}: {str(e)}')
            raise InternalCLARAError(message='Image database inconsistency')

