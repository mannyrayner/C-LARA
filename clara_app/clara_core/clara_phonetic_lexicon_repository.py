from .clara_database_adapter import connect, localise_sql_query

from .clara_utils import _s3_storage, get_config, absolute_file_name, absolute_local_file_name, file_exists, local_file_exists, copy_local_file, basename
from .clara_utils import make_directory, remove_directory, directory_exists, local_directory_exists, make_local_directory
from .clara_utils import list_files_in_directory, post_task_update

from .clara_classes import InternalCLARAError

from pathlib import Path

import os
import traceback

config = get_config()

class PhoneticLexiconRepository:
    def __init__(self, callback=None):   
        self.db_file = absolute_local_file_name(config.get('phonetic_lexicon_repository', ( 'db_file' if _s3_storage else 'db_file_local' )))
        self._initialize_repository(callback=callback)

    def _initialize_repository(self, callback=None):
        try:
            if os.getenv('DB_TYPE') == 'sqlite':
                # If we're using sqlite, check if db_file exists and if not create it
                db_dir = config.get('phonetic_lexicon_repository', 'base_dir')
                if not local_directory_exists(db_dir):
                    post_task_update(callback, f'--- Creating empty base dir for phonetic lexicon repository, {db_dir}')
                    make_local_directory(db_dir)
                if not local_file_exists(self.db_file):
                    post_task_update(callback, f'--- Creating empty base file for phonetic lexicon repository, {self.db_file}')
                    open(self.db_file, 'a').close()
                    
            connection = connect(self.db_file)
            cursor = connection.cursor()
        
            # Create tables for aligned and plain phonetic lexicon
            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute('''CREATE TABLE IF NOT EXISTS aligned_phonetic_lexicon
                                  (id INTEGER PRIMARY KEY,
                                   word TEXT,
                                   phonemes TEXT,
                                   aligned_graphemes TEXT,
                                   aligned_phonemes TEXT,
                                   language TEXT,
                                   status TEXT)''')
                cursor.execute('''CREATE TABLE IF NOT EXISTS plain_phonetic_lexicon
                                  (id INTEGER PRIMARY KEY,
                                   word TEXT,
                                   phonemes TEXT,
                                   language TEXT,
                                   status TEXT)''')
                cursor.execute('''CREATE TABLE IF NOT EXISTS phonetic_lexicon_history
                                  (id INTEGER PRIMARY KEY,
                                   word TEXT,
                                   modification_date TIMESTAMP,
                                   previous_value JSON,
                                   new_value JSON,
                                   modified_by TEXT,
                                   comments TEXT)''')
            else:  # Assume Postgres
                cursor.execute('''CREATE TABLE IF NOT EXISTS aligned_phonetic_lexicon
                                  (id SERIAL PRIMARY KEY,
                                   word TEXT,
                                   aligned_graphemes TEXT,
                                   aligned_phonemes TEXT,
                                   language TEXT,
                                   status TEXT)''')
                cursor.execute('''CREATE TABLE IF NOT EXISTS plain_phonetic_lexicon
                                  (id SERIAL PRIMARY KEY,
                                   word TEXT,
                                   phonemes TEXT,
                                   language TEXT,
                                   status TEXT)''')
                cursor.execute('''CREATE TABLE IF NOT EXISTS phonetic_lexicon_history
                                  (id SERIAL PRIMARY KEY,
                                   word TEXT,
                                   modification_date TIMESTAMP,
                                   previous_value JSON,
                                   new_value JSON,
                                   modified_by TEXT,
                                   comments TEXT)''')
                
            cursor.execute('''CREATE INDEX IF NOT EXISTS idx_word_aligned ON aligned_phonetic_lexicon (word)''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS idx_word_plain ON plain_phonetic_lexicon (word)''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS idx_word_history ON phonetic_lexicon_history (word)''')

            connection.commit()
            connection.close()
            post_task_update(callback, f'--- Initialised phonetic lexicon repository')
                                   
        except Exception as e:
            error_message = f'*** Error when trying to initialise phonetic lexicon database: "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def add_or_update_aligned_entry(self, word, phonemes, aligned_graphemes, aligned_phonemes, language, status, callback=None):
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()

            # Check if the entry already exists
            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute("SELECT COUNT(*) FROM aligned_phonetic_lexicon WHERE word = ? AND phonemes = ? AND language = ?",
                               (word, phonemes, language))
            else:  # Assume postgres
                cursor.execute("SELECT COUNT(*) FROM aligned_phonetic_lexicon WHERE word = %s AND phonemes = %s AND language = %s",
                               (word, phonemes, language))

            result = cursor.fetchone()
            exists = result[0] > 0 if result is not None else False

            if exists:
                # Update existing entry
                if os.getenv('DB_TYPE') == 'sqlite':
                    cursor.execute("""UPDATE aligned_phonetic_lexicon SET aligned_graphemes = ?, aligned_phonemes = ?, status = ? 
                                      WHERE word = ? AND phonemes = ? AND language = ?""",
                                   (aligned_graphemes, aligned_phonemes, status, word, phonemes, language))
                else:  # Assume postgres
                    cursor.execute("""UPDATE aligned_phonetic_lexicon SET aligned_graphemes = %s, aligned_phonemes = %s, status = %s 
                                      WHERE word = %s AND phonemes = %s AND language = %s""",
                                   (aligned_graphemes, aligned_phonemes, status, word, phonemes, language))
            else:
                # Insert new entry
                if os.getenv('DB_TYPE') == 'sqlite':
                    cursor.execute("INSERT INTO aligned_phonetic_lexicon (word, phonemes, aligned_graphemes, aligned_phonemes, language, status) VALUES (?, ?, ?, ?, ?, ?)",
                                   (word, phonemes, aligned_graphemes, aligned_phonemes, language, status))
                else:  # Assume postgres
                    cursor.execute("INSERT INTO aligned_phonetic_lexicon (word, phonemes, aligned_graphemes, aligned_phonemes, language, status) VALUES (%s, %s, %s, %s, %s, %s)",
                                   (word, phonemes, aligned_graphemes, aligned_phonemes, language, status))

            connection.commit()
            connection.close()
        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepository: error when inserting/updating "{word}; {phonemes}" into aligned phonetic lexicon database:')
            post_task_update(callback, f'"{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

