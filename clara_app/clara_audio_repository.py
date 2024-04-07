"""
clara_audio_repository.py

This module implements an audio repository that stores metadata and generated audio files from human voices and various TTS engines.

Classes:
- AudioRepository: Class for managing the audio repository.

The AudioRepository class provides methods for adding entries, retrieving entries, getting the voice directory, and storing mp3 files.

Use clara_database_adapter so that the code works for both sqlite3 and PostgreSQL databases.

SQL templates must be written in PostgreSQL format with %s signifying a parameter placeholder.
The function clara_database_adapter.localise_sql_query converts this to sqlite3 format if necessary.
"""

from .clara_database_adapter import connect, localise_sql_query

from .clara_tts_api import get_tts_engine_types
from .clara_utils import _s3_storage, get_config, absolute_file_name, absolute_local_file_name, file_exists, local_file_exists, copy_local_file, basename
from .clara_utils import make_directory, remove_directory, directory_exists, local_directory_exists, make_local_directory
from .clara_utils import list_files_in_directory, post_task_update

from .clara_classes import InternalCLARAError

from pathlib import Path

import os
import pprint
import traceback

config = get_config()

_trace = False
# _trace = True

class AudioRepository:
    def __init__(self, callback=None):   
        self.db_file = absolute_local_file_name(config.get('audio_repository', ( 'db_file' if _s3_storage else 'db_file_local' )))
        self.base_dir = absolute_file_name(config.get('audio_repository', 'base_dir'))
        self._initialize_repository(callback=callback)

    def _initialize_repository(self, callback=None):
        if not directory_exists(self.base_dir):
            make_directory(self.base_dir, parents=True, exist_ok=True)

        try:
            if os.getenv('DB_TYPE') == 'sqlite':
                # If we're using sqlite, check if db_file exists and if not create it
                db_dir = config.get('audio_repository', 'db_dir')
                if not local_directory_exists(db_dir):
                    post_task_update(callback, f'--- Creating empty DB dir for audio repository, {db_dir}')
                    make_local_directory(db_dir)
                if not local_file_exists(self.db_file):
                    post_task_update(callback, f'--- Creating empty DB file for audio repository, {self.db_file}')
                    open(self.db_file, 'a').close()
                    
            connection = connect(self.db_file)
            cursor = connection.cursor()
        
            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute('''CREATE TABLE IF NOT EXISTS metadata
                                  (id INTEGER PRIMARY KEY,
                                   engine_id TEXT,
                                   language_id TEXT,
                                   voice_id TEXT,
                                   text TEXT,
                                   context TEXT,
                                   file_path TEXT)''')
                cursor.execute('''CREATE INDEX IF NOT EXISTS idx_text ON metadata (text)''')
            # Assume Postgres, which does auto-incrementing differently
            # We need a suitable definition for the primary key
            else:
                cursor.execute('''CREATE TABLE IF NOT EXISTS metadata
                                  (id SERIAL PRIMARY KEY,
                                   engine_id TEXT,
                                   language_id TEXT,
                                   voice_id TEXT,
                                   text TEXT,
                                   context TEXT,
                                   file_path TEXT)''')
                cursor.execute('''CREATE INDEX IF NOT EXISTS idx_text ON metadata (text)''')
                                   
            connection.commit()
            connection.close()
            #post_task_update(callback, f'--- Initialised audio repository')
                                   
        except Exception as e:
            error_message = f'*** Error when trying to initialise TTS database: "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='TTS database inconsistency')

##    def export_audio_metadata(self, callback=None):
##        try:
##            connection = connect(self.db_file)
##            cursor = connection.cursor()
##            cursor.execute("SELECT engine_id, language_id, voice_id, text, context, file_path FROM metadata")
##            entries = cursor.fetchall()
##            exported_data = []
##            for entry in entries:
##                exported_data.append({
##                    'engine_id': entry[0],
##                    'language_id': entry[1],
##                    'voice_id': entry[2],
##                    'text': entry[3],
##                    'context': entry[4] if entry[4] else '',
##                    'file_path': entry[5],
##                })
##            connection.close()
##            return exported_data
##        except Exception as e:
##            post_task_update(callback, f'Error exporting audio metadata: "{str(e)}"\n{traceback.format_exc()}')
##            return []

    def export_audio_metadata(self, callback=None):
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()
            cursor.execute("SELECT engine_id, language_id, voice_id, text, context, file_path FROM metadata")
            entries = cursor.fetchall()
            exported_data = []
            for entry in entries:
                if os.getenv('DB_TYPE') == 'sqlite':
                    # SQLite returns tuples, so you access columns by index
                    data_dict = {
                        'engine_id': entry[0],
                        'language_id': entry[1],
                        'voice_id': entry[2],
                        'text': entry[3],
                        'context': entry[4] if entry[4] else '',
                        'file_path': entry[5],
                    }
                else:
                    # PostgreSQL returns dict-like objects, you can access columns by name
                    data_dict = {
                        'engine_id': entry['engine_id'],
                        'language_id': entry['language_id'],
                        'voice_id': entry['voice_id'],
                        'text': entry['text'],
                        'context': entry['context'] if entry['context'] else '',
                        'file_path': entry['file_path'],
                    }
                exported_data.append(data_dict)
            connection.close()
            return exported_data
        except Exception as e:
            post_task_update(callback, f'Error exporting audio metadata: "{str(e)}"\n{traceback.format_exc()}')
            return []

    def delete_entries_for_language(self, engine_id, language_id, callback=None):
        try:
            post_task_update(callback, f'--- Deleting tts repository DB entries for {language_id}')
            connection = connect(self.db_file)
            cursor = connection.cursor()
            cursor.execute(localise_sql_query("DELETE FROM metadata WHERE language_id = %s"), (language_id,))
            connection.commit()
            connection.close()
            post_task_update(callback, f'--- DB entries for {language_id} deleted')

            post_task_update(callback, f'--- Deleting audio files for {language_id}')
            language_dir = self.get_language_directory(engine_id, language_id)
            if directory_exists(language_dir):
                remove_directory(language_dir)
            post_task_update(callback, f'--- audio files for {engine_id} and {language_id} deleted')
            post_task_update(callback, f'finished')
        except Exception as e:
            error_message = f'*** Error when trying to delete audio data: "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            post_task_update(callback, f'error')

    def add_or_update_entry(self, engine_id, language_id, voice_id, text, file_path, context='', callback=None):
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()

            # Check if the entry already exists
            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute("SELECT COUNT(*) FROM metadata WHERE engine_id = ? AND language_id = ? AND voice_id = ? AND text = ? AND context = ?",
                               (engine_id, language_id, voice_id, text, context))
            else:  # Assume postgres
                cursor.execute("SELECT COUNT(*) FROM metadata WHERE engine_id = %s AND language_id = %s AND voice_id = %s AND text = %s AND context = %s",
                               (engine_id, language_id, voice_id, text, context))

            result = cursor.fetchone()
            if result is not None:
                if os.getenv('DB_TYPE') == 'sqlite':
                    # For SQLite, result is a tuple
                    exists = result[0] > 0
                else:
                    # For PostgreSQL, result is a RealDictRow
                    exists = result['count'] > 0
            else:
                exists = False

            if exists:
                # Update existing entry
                if os.getenv('DB_TYPE') == 'sqlite':
                    cursor.execute("""UPDATE metadata SET file_path = ? WHERE engine_id = ? AND language_id = ? AND voice_id = ? AND text = ? AND context = ?""",
                                   (file_path, engine_id, language_id, voice_id, text, context))
                else:  # Assume postgres
                    cursor.execute("""UPDATE metadata SET file_path = %s WHERE engine_id = %s AND language_id = %s AND voice_id = %s AND text = %s AND context = %s""",
                                   (file_path, engine_id, language_id, voice_id, text, context))
            else:
                # Insert new entry
                if os.getenv('DB_TYPE') == 'sqlite':
                    cursor.execute("INSERT INTO metadata (engine_id, language_id, voice_id, text, file_path, context) VALUES (?, ?, ?, ?, ?, ?)",
                                   (engine_id, language_id, voice_id, text, file_path, context))
                else:  # Assume postgres
                    cursor.execute("INSERT INTO metadata (engine_id, language_id, voice_id, text, file_path, context) VALUES (%s, %s, %s, %s, %s, %s)",
                                   (engine_id, language_id, voice_id, text, file_path, context))

            connection.commit()
            connection.close()
        except Exception as e:
            post_task_update(callback, f'*** AudioRepository: error when inserting/updating "{language_id}; {text}; {file_path}" into audio database:')
            post_task_update(callback, f'"{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='TTS database inconsistency')

    def store_mp3(self, engine_id, language_id, voice_id, source_file, keep_file_name=False, callback=None):
        voice_dir = self.get_voice_directory(engine_id, language_id, voice_id)
        make_directory(voice_dir, parents=True, exist_ok=True)
        file_name = basename(source_file) if keep_file_name else f"{voice_id}_{len(list_files_in_directory(voice_dir)) + 1}.mp3"
        destination_path = str(Path(voice_dir) / file_name)
        copy_local_file(source_file, destination_path)
        return destination_path

    def get_entry(self, engine_id, language_id, voice_id, text, context='', callback=None):
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()
            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute("SELECT file_path FROM metadata WHERE engine_id = ? AND language_id = ? AND voice_id = ? AND text = ? AND context = ?",
                               (engine_id, language_id, voice_id, text, context))
            else:
                # Assume postgres
                cursor.execute("""SELECT file_path FROM metadata 
                                  WHERE engine_id = %(engine_id)s 
                                  AND language_id = %(language_id)s 
                                  AND voice_id = %(voice_id)s 
                                  AND text = %(text)s
                                  AND context = %(context)s""",
                               {
                                  'engine_id': engine_id,
                                  'language_id': language_id,
                                  'voice_id': voice_id,
                                  'text': text,
                                  'context': context,
                               })
            result = cursor.fetchone()
            connection.close()
            if os.getenv('DB_TYPE') == 'sqlite':
                return result[0] if result else None
            else:  # Assuming PostgreSQL
                return result['file_path'] if result else None

        except Exception as e:
            error_message = f'*** Error when looking for "{text}" in TTS database: "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='TTS database inconsistency')

    def get_entry_batch(self, engine_id, language_id, voice_id, text_and_context_items, callback=None):
        if _trace:
            print(f'--- get_entry_batch({engine_id}, {language_id}, {voice_id},')
            pprint.pprint(text_and_context_items)
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()
            results = {}

            for item in text_and_context_items:
                text = item['canonical_text']
                context = item['context']
                if os.getenv('DB_TYPE') == 'sqlite':
                    cursor.execute("SELECT file_path FROM metadata WHERE engine_id = ? AND language_id = ? AND voice_id = ? AND text = ? AND context = ?",
                                   (engine_id, language_id, voice_id, text, context))
                else:
                    # Assume postgres
                    cursor.execute("""SELECT file_path FROM metadata 
                                      WHERE engine_id = %(engine_id)s 
                                      AND language_id = %(language_id)s 
                                      AND voice_id = %(voice_id)s 
                                      AND text = %(text)s
                                      AND context = %(context)s""",
                                   {
                                      'engine_id': engine_id,
                                      'language_id': language_id,
                                      'voice_id': voice_id,
                                      'text': text,
                                      'context': context
                                   })
                result = cursor.fetchone()
            
                if os.getenv('DB_TYPE') == 'sqlite':
                    file_path = result[0] if result else None
                else:  # Assuming PostgreSQL
                    file_path = result['file_path'] if result else None

                results[( text, context )] = file_path

            connection.close()
            if _trace:
                print(f'--- results:')
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

    
    
