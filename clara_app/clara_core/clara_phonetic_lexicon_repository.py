from .clara_database_adapter import connect, localise_sql_query

from .clara_utils import _s3_storage, get_config, absolute_file_name, absolute_local_file_name, file_exists, local_file_exists, copy_local_file, basename
from .clara_utils import make_directory, remove_directory, directory_exists, local_directory_exists, make_local_directory, read_json_file
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
                db_dir = config.get('phonetic_lexicon_repository', 'db_dir')
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

    def add_plain_entry(self, word, phonemes, language, status, callback=None):
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()

            # Insert new entry
            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute("INSERT INTO plain_phonetic_lexicon (word, phonemes, language, status) VALUES (?, ?, ?, ?)",
                               (word, phonemes, language, status))
            else:  # Assume postgres
                cursor.execute("INSERT INTO plain_phonetic_lexicon (word, phonemes, language, status) VALUES (%s, %s, %s, %s)",
                               (word, phonemes, language, status))

            connection.commit()
            connection.close()
        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepository: error when inserting "{word}; {phonemes}" into plain phonetic lexicon database:')
            post_task_update(callback, f'"{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def delete_plain_entry(self, word, phonemes, language, callback=None):
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()

            # Delete entry
            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute("DELETE FROM plain_phonetic_lexicon WHERE word = ? AND phonemes = ? AND language = ?",
                               (word, phonemes, language))
            else:  # Assume postgres
                cursor.execute("DELETE FROM plain_phonetic_lexicon WHERE word = %s AND phonemes = %s AND language = %s",
                               (word, phonemes, language))

            connection.commit()
            connection.close()
        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepository: error when deleting "{word}; {phonemes}" from plain phonetic lexicon database:')
            post_task_update(callback, f'"{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def add_history_entry(self, word, modification_date, previous_value, new_value, modified_by, comments, callback=None):
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()

            # Insert new history entry
            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute("INSERT INTO phonetic_lexicon_history (word, modification_date, previous_value, new_value, modified_by, comments) VALUES (?, ?, ?, ?, ?, ?)",
                               (word, modification_date, previous_value, new_value, modified_by, comments))
            else:  # Assume postgres
                cursor.execute("INSERT INTO phonetic_lexicon_history (word, modification_date, previous_value, new_value, modified_by, comments) VALUES (%s, %s, %s, %s, %s, %s)",
                               (word, modification_date, previous_value, new_value, modified_by, comments))

            connection.commit()
            connection.close()
        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepository: error when inserting history entry for "{word}" into phonetic lexicon history database:')
            post_task_update(callback, f'"{str(e)}"\n{traceback.format_exc()}')

    def initialise_aligned_lexicon(self, items, language, callback=None):
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()

            # Clear existing entries for the language
            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute("DELETE FROM aligned_phonetic_lexicon WHERE language = ?", (language,))
            else:  # Assume postgres
                cursor.execute("DELETE FROM aligned_phonetic_lexicon WHERE language = %s", (language,))

            # Batch insert new items
            for entry in items:
                word = entry['word']
                phonemes = entry['phonemes']
                aligned_graphemes = entry['aligned_graphemes']
                aligned_phonemes = entry['aligned_phonemes']
                status = 'uploaded'
                if os.getenv('DB_TYPE') == 'sqlite':
                    cursor.execute("INSERT INTO aligned_phonetic_lexicon (word, phonemes, aligned_graphemes, aligned_phonemes, language, status) VALUES (?, ?, ?, ?, ?, ?)",
                                   (word, phonemes, aligned_graphemes, aligned_phonemes, language, status))
                else:  # Assume postgres
                    cursor.execute("INSERT INTO aligned_phonetic_lexicon (word, phonemes, aligned_graphemes, aligned_phonemes, language, status) VALUES (%s, %s, %s, %s, %s, %s)",
                                   (word, phonemes, aligned_graphemes, aligned_phonemes, language, status))

            connection.commit()
            connection.close()
            post_task_update(callback, f'--- Initialised aligned phonetic lexicon for {language}, {len(items)} entries')
        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepository: error when initialising aligned lexicon for language "{language}": {str(e)}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')


    def initialise_plain_lexicon(self, items, language, callback=None):
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()

            # Clear existing entries for the language
            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute("DELETE FROM plain_phonetic_lexicon WHERE language = ?", (language,))
            else:  # Assume postgres
                cursor.execute("DELETE FROM plain_phonetic_lexicon WHERE language = %s", (language,))

            # Batch insert new items
            for entry in items:
                word = entry['word']
                phonemes = entry['phonemes']
                status = 'uploaded'
                if os.getenv('DB_TYPE') == 'sqlite':
                    cursor.execute("INSERT INTO plain_phonetic_lexicon (word, phonemes, language, status) VALUES (?, ?, ?, ?)",
                                   (word, phonemes, language, status))
                else:  # Assume postgres
                    cursor.execute("INSERT INTO plain_phonetic_lexicon (word, phonemes, language, status) VALUES (%s, %s, %s, %s)",
                                   (word, phonemes, language, status))

            connection.commit()
            connection.close()
            post_task_update(callback, f'--- Initialised plain phonetic lexicon for {language}, {len(items)} entries')
        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepository: error when initialising plain lexicon for language "{language}": {str(e)}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def get_aligned_entries_batch(self, words, language, callback=None):
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()

            # Prepare the query for batch lookup
            if os.getenv('DB_TYPE') == 'sqlite':
                query = "SELECT * FROM aligned_phonetic_lexicon WHERE language = ? AND word IN ({})".format(','.join('?' * len(words)))
                cursor.execute(query, [language] + words)
            else:  # Assume postgres
                query = "SELECT * FROM aligned_phonetic_lexicon WHERE language = %s AND word = ANY(%s)"
                cursor.execute(query, (language, tuple(words)))

            # Fetch all matching records
            records = cursor.fetchall()
            connection.close()

            # Convert records to a list of dicts
            if os.getenv('DB_TYPE') == 'sqlite':
                entries = [{'word': record[1], 'phonemes': record[2], 'aligned_graphemes': record[3],
                            'aligned_phonemes': record[4], 'status': record[6]} for record in records]
            else:  # Assuming PostgreSQL
                entries = [{'word': record['word'], 'phonemes': record['phonemes'], 'aligned_graphemes': record['aligned_graphemes'],
                            'aligned_phonemes': record['aligned_phonemes'], 'status': record['status']}
                           for record in records]

            return entries

        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepository: error when fetching aligned entries batch for language "{language}": {str(e)}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def get_all_aligned_entries_for_language(self, language, callback=None):
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()

            # Fetch all records for the specified language
            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute("SELECT * FROM aligned_phonetic_lexicon WHERE language = ?", (language,))
            else:  # Assume postgres
                cursor.execute("SELECT * FROM aligned_phonetic_lexicon WHERE language = %s", (language,))

            records = cursor.fetchall()
            connection.close()

            # Convert records to a list of dicts
            if os.getenv('DB_TYPE') == 'sqlite':
                entries = [{'word': record[1], 'phonemes': record[2], 'aligned_graphemes': record[3],
                            'aligned_phonemes': record[4], 'status': record[6]} for record in records]
            else:  # Assuming PostgreSQL
                entries = [{'word': record['word'], 'phonemes': record['phonemes'], 'aligned_graphemes': record['aligned_graphemes'],
                            'aligned_phonemes': record['aligned_phonemes'], 'status': record['status']}
                           for record in records]
            
            return entries

        except Exception as e:
            error_message = f'*** Error when retrieving aligned lexicon entries for language "{language}": {str(e)}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')


    def get_plain_entries_batch(self, words, language, callback=None):
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()

            # Prepare the query for batch lookup
            if os.getenv('DB_TYPE') == 'sqlite':
                query = "SELECT * FROM plain_phonetic_lexicon WHERE language = ? AND word IN ({})".format(','.join('?' * len(words)))
                cursor.execute(query, [language] + words)
            else:  # Assume postgres
                query = "SELECT * FROM plain_phonetic_lexicon WHERE language = %s AND word = ANY(%s)"
                cursor.execute(query, (language, tuple(words)))

            # Fetch all matching records
            records = cursor.fetchall()
            connection.close()

            # Convert records to a list of dicts
            if os.getenv('DB_TYPE') == 'sqlite':
                entries = [{'word': record[1], 'phonemes': record[2], 'status': record[3]} for record in records]
            else:  # Assuming PostgreSQL
                entries = [{'word': record['word'], 'phonemes': record['phonemes'], 'status': record['status']}
                           for record in records]
            return entries

        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepository: error when fetching plain entries batch for language "{language}": {str(e)}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')
        

#-----------------------

## Testing

## Contents for aligned file assumed to be in this format:

##{
##    "a": [
##        "a",
##        "æ"
##    ],
##    "about": [
##        "a|b|ou|t",
##        "ɐ|b|a‍ʊ|t"
##    ],
##    "active": [
##        "a|c|t|i|v|e",
##        "æ|k|t|ɪ|v|"
##    ],

def load_and_initialise_aligned_lexicon(repository, file_path, language, callback=None):
    data = read_json_file(file_path)
    items = []
    for word in data:
        aligned_graphemes, aligned_phonemes = data[word]
        items.append({
            'word': word,
            'phonemes': aligned_phonemes.replace('|', ''),  
            'aligned_graphemes': aligned_graphemes,
            'aligned_phonemes': aligned_phonemes,
        })
    repository.initialise_aligned_lexicon(items, language, callback=callback)

## Contents for aligned file assumed to be in this format:

##{
##    "a": "æ",
##    "aah": "ˈɑː",
##    "aardvark": "ˈɑːdvɑːk",
##    "aardvarks": "ˈɑːdvɑːks",
##    "aardwolf": "ˈɑːdwʊlf",
##    "aba": "ɐbˈæ",

def load_and_initialise_plain_lexicon(repository, file_path, language, callback=None):
    data = read_json_file(file_path)
    items = []
    for word in data:
        phonemes = data[word]
        items.append({
            'word': word,
            'phonemes': phonemes,
            }) 
    repository.initialise_plain_lexicon(items, language, callback=callback)
