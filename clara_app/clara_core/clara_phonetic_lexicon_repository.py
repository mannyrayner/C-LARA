from .clara_database_adapter import connect, localise_sql_query

from .clara_utils import _s3_storage, get_config, absolute_file_name, absolute_local_file_name, file_exists, local_file_exists, basename, extension_for_file_path
from .clara_utils import make_directory, directory_exists, local_directory_exists, make_local_directory
from .clara_utils import read_json_file, read_txt_file, read_local_json_file, read_local_txt_file
from .clara_utils import post_task_update

from .clara_classes import InternalCLARAError

from pathlib import Path

import os
import traceback
import pprint

config = get_config()

class PhoneticLexiconRepository:
    def __init__(self, callback=None):   
        self.db_file = absolute_local_file_name(config.get('phonetic_lexicon_repository', ( 'db_file' if _s3_storage else 'db_file_local' )))
        self.possible_encodings = ( 'ipa', 'arpabet_like' )
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
        
            # Create tables for aligned and plain phonetic lexicon, etc
            cursor.execute('''CREATE TABLE IF NOT EXISTS phonetic_encoding
                              (language TEXT PRIMARY KEY,
                               encoding TEXT)''')
            
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
                                   phonemes TEXT,
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
            #post_task_update(callback, f'--- Initialised phonetic lexicon repository')
                                   
        except Exception as e:
            error_message = f'*** Error when trying to initialise phonetic lexicon database: "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def set_encoding_for_language(self, language, encoding, callback=None):
        try:
            if not encoding in self.possible_encodings:
                post_task_update(callback, f'*** PhoneticLexiconRepository: error when setting encoding for "{language}": illegal value "{encoding}"')
                raise InternalCLARAError(message='Phonetic lexicon database inconsistency')
            
            connection = connect(self.db_file)
            cursor = connection.cursor()

            if os.getenv('DB_TYPE') == 'sqlite':
                # SQLite upsert syntax
                cursor.execute("INSERT INTO phonetic_encoding (language, encoding) VALUES (?, ?) ON CONFLICT(language) DO UPDATE SET encoding = excluded.encoding",
                               (language, encoding))
            else:  # Assume postgres
                # PostgreSQL upsert syntax
                cursor.execute("INSERT INTO phonetic_encoding (language, encoding) VALUES (%s, %s) ON CONFLICT(language) DO UPDATE SET encoding = EXCLUDED.encoding",
                               (language, encoding))

            connection.commit()
            connection.close()
        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepository: error when setting encoding for "{language}": {str(e)}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def get_encoding_for_language(self, language, callback=None):
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()

            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute("SELECT encoding FROM phonetic_encoding WHERE language = ?", (language,))
            else:  # Assume postgres
                cursor.execute("SELECT encoding FROM phonetic_encoding WHERE language = %s", (language,))

            result = cursor.fetchone()
            connection.close()
            
            if result is not None:
                if os.getenv('DB_TYPE') == 'sqlite':
                    # For SQLite, result is a tuple
                    return result[0] 
                else:
                    # For PostgreSQL, result is a RealDictRow
                    return result['encoding']
            else:
                return 'ipa'
                
        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepository: error when getting encoding for "{language}": "{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def aligned_entries_exist_for_language(self, language, callback=None):
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()

            # Check if the entry already exists
            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute("SELECT COUNT(*) FROM aligned_phonetic_lexicon WHERE language = ?",
                               (language,))
            else:  # Assume postgres
                cursor.execute("SELECT COUNT(*) FROM aligned_phonetic_lexicon WHERE language = %s",
                               (language,))

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


            connection.commit()
            connection.close()
            
            return exists
        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepository: error when checking for aligned entries "{language}":')
            post_task_update(callback, f'"{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def plain_phonetic_entries_exist_for_language(self, language, callback=None):
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()

            # Check if the entry already exists
            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute("SELECT COUNT(*) FROM plain_phonetic_lexicon WHERE language = ?",
                               (language,))
            else:  # Assume postgres
                cursor.execute("SELECT COUNT(*) FROM plain_phonetic_lexicon WHERE language = %s",
                               (language,))

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

            connection.commit()
            connection.close()
            
            return exists
        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepository: error when checking for plain phonetic entries "{language}":')
            post_task_update(callback, f'"{str(e)}"\n{traceback.format_exc()}')
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

    def delete_aligned_entry(self, word, phonemes, language, callback=None):
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()

            # Delete entry
            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute("DELETE FROM aligned_phonetic_lexicon WHERE word = ? AND phonemes = ? AND language = ?",
                               (word, phonemes, language))
            else:  # Assume postgres
                cursor.execute("DELETE FROM aligned_phonetic_lexicon WHERE word = %s AND phonemes = %s AND language = %s",
                               (word, phonemes, language))

            connection.commit()
            connection.close()
        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepository: error when deleting "{word}; {phonemes}" from aligned phonetic lexicon database:')
            post_task_update(callback, f'"{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')


    def add_or_update_plain_entry(self, word, phonemes, language, status, callback=None):
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()

            # Check if the entry already exists
            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute("SELECT COUNT(*) FROM plain_phonetic_lexicon WHERE word = ? AND phonemes = ? AND language = ?",
                               (word, phonemes, language))
            else:  # Assume postgres
                cursor.execute("SELECT COUNT(*) FROM plain_phonetic_lexicon WHERE word = %s AND phonemes = %s AND language = %s",
                               (word, phonemes, language))

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
                    cursor.execute("""UPDATE plain_phonetic_lexicon SET status = ? 
                                      WHERE word = ? AND phonemes = ? AND language = ?""",
                                   (status, word, phonemes, language))
                else:  # Assume postgres
                    cursor.execute("""UPDATE plain_phonetic_lexicon SET status = %s 
                                      WHERE word = %s AND phonemes = %s AND language = %s""",
                                   (status, word, phonemes, language))
            else:
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
            post_task_update(callback, f'*** PhoneticLexiconRepository: error when inserting/updating "{word}; {phonemes}" into plain phonetic lexicon database:')
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

            # Clear existing 'uploaded' entries for the language
            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute("DELETE FROM aligned_phonetic_lexicon WHERE language = ? AND status = ?", (language, 'uploaded'))
            else:  # Assume postgres
                cursor.execute("DELETE FROM aligned_phonetic_lexicon WHERE language = %s AND status = %s", (language, 'uploaded'))

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
            post_task_update(callback, f'*** PhoneticLexiconRepository: error when initialising aligned lexicon for language "{language}": "{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')


    def initialise_plain_lexicon(self, items, language, callback=None):
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()

            # Clear existing 'uploaded' entries for the language
            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute("DELETE FROM plain_phonetic_lexicon WHERE language = ? AND status = ?", (language, 'uploaded'))
            else:  # Assume postgres
                cursor.execute("DELETE FROM plain_phonetic_lexicon WHERE language = %s AND status = %s", (language, 'uploaded'))

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
            post_task_update(callback, f'*** PhoneticLexiconRepository: error when initialising plain lexicon for language "{language}": "{str(e)}"\n{traceback.format_exc()}')
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
                cursor.execute(query, (language, words))

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
            post_task_update(callback, f'*** PhoneticLexiconRepository: error when fetching aligned entries batch for language "{language}": "{str(e)}"\n{traceback.format_exc()}')
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
            error_message = f'*** Error when retrieving aligned lexicon entries for language "{language}": "{str(e)}"\n{traceback.format_exc()}'
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
                cursor.execute(query, (language, words))

            # Fetch all matching records
            records = cursor.fetchall()
            connection.close()

            # Convert records to a list of dicts
            if os.getenv('DB_TYPE') == 'sqlite':
                entries = [{'word': record[1], 'phonemes': record[2], 'language': record[3], 'status': record[4]} for record in records]
            else:  # Assuming PostgreSQL
                entries = [{'word': record['word'], 'phonemes': record['phonemes'], 'language': record['language'], 'status': record['status']}
                           for record in records]
            return entries

        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepository: error when fetching plain entries batch for language "{language}": "{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')
        
    def record_guessed_plain_entries(self, plain_entries, language, callback=None):
        self.record_plain_entries(plain_entries, language, 'generated', callback=None)

    def record_reviewed_plain_entries(self, plain_entries, language, callback=None):
        self.record_plain_entries(plain_entries, language, 'reviewed', callback=None)

    def record_plain_entries(self, plain_entries, language, status, callback=None):
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()

            for entry in plain_entries:
                word = entry['word']
                phonemes = entry['phonemes']

                # Delete existing entry if it exists, then insert new entry
                if os.getenv('DB_TYPE') == 'sqlite':
                    cursor.execute("DELETE FROM plain_phonetic_lexicon WHERE word = ? AND phonemes = ? AND language = ?", (word, phonemes, language))
                    cursor.execute("INSERT INTO plain_phonetic_lexicon (word, phonemes, language, status) VALUES (?, ?, ?, ?)", (word, phonemes, language, status))
                else:  # Assume postgres
                    cursor.execute("DELETE FROM plain_phonetic_lexicon WHERE word = %s AND phonemes = %s AND language = %s", (word, phonemes, language))
                    cursor.execute("INSERT INTO plain_phonetic_lexicon (word, phonemes, language, status) VALUES (%s, %s, %s, %s)", (word, phonemes, language, status))

            connection.commit()
            connection.close()
        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepository: error when recording plain entries for language "{language}": "{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def delete_plain_entries(self, plain_entries, language, callback=None):
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()

            for entry in plain_entries:
                word = entry['word']
                phonemes = entry['phonemes']

                if os.getenv('DB_TYPE') == 'sqlite':
                    cursor.execute("DELETE FROM plain_phonetic_lexicon WHERE word = ? AND phonemes = ? AND language = ?", (word, phonemes, language))
                else:  # Assume postgres
                    cursor.execute("DELETE FROM plain_phonetic_lexicon WHERE word = %s AND phonemes = %s AND language = %s", (word, phonemes, language))

            connection.commit()
            connection.close()
        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepository: error when deleting plain entries for language "{language}": "{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def record_guessed_aligned_entries(self, aligned_entries, language, callback=None):
        self.record_aligned_entries(aligned_entries, language, 'generated', callback=None)

    def record_reviewed_aligned_entries(self, aligned_entries, language, callback=None):
        self.record_aligned_entries(aligned_entries, language, 'reviewed', callback=None)

    def record_aligned_entries(self, aligned_entries, language, status, callback=None):
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()

            for entry in aligned_entries:
                word = entry['word']
                aligned_graphemes = entry['aligned_graphemes']
                aligned_phonemes = entry['aligned_phonemes']
                # The 'phonemes' field is in fact redundant. Create it from the 'aligned_phonemes' field if it's missing.
                phonemes = entry['phonemes'] if 'phonemes' in entry else aligned_phonemes.replace('|', '')

                # Delete existing entry if it exists, then insert new entry
                if os.getenv('DB_TYPE') == 'sqlite':
                    cursor.execute("DELETE FROM aligned_phonetic_lexicon WHERE word = ? AND phonemes = ? AND language = ?", (word, phonemes, language))
                    cursor.execute("INSERT INTO aligned_phonetic_lexicon (word, phonemes, aligned_graphemes, aligned_phonemes, language, status) VALUES (?, ?, ?, ?, ?, ?)",
                                   (word, phonemes, aligned_graphemes, aligned_phonemes, language, status))

                else:  # Assume postgres
                    cursor.execute("DELETE FROM aligned_phonetic_lexicon WHERE word = %s AND phonemes = %s AND language = %s", (word, phonemes, language))
                    cursor.execute("INSERT INTO aligned_phonetic_lexicon (word, phonemes, aligned_graphemes, aligned_phonemes, language, status) VALUES (%s, %s, %s, %s, %s, %s)",
                                   (word, phonemes, aligned_graphemes, aligned_phonemes, language, status))

            connection.commit()
            connection.close()
        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepository: error when recording guessed aligned entries for language "{language}": "{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def delete_aligned_entries(self, aligned_entries, language, callback=None):
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()

            for entry in aligned_entries:
                word = entry['word']
                aligned_graphemes = entry['aligned_graphemes']
                aligned_phonemes = entry['aligned_phonemes']
                # The 'phonemes' field is in fact redundant. Create it from the 'aligned_phonemes' field if it's missing.
                phonemes = entry['phonemes'] if 'phonemes' in entry else aligned_phonemes.replace('|', '')

                if os.getenv('DB_TYPE') == 'sqlite':
                    cursor.execute("DELETE FROM aligned_phonetic_lexicon WHERE word = ? AND phonemes = ? AND language = ?", (word, phonemes, language))

                else:  # Assume postgres
                    cursor.execute("DELETE FROM aligned_phonetic_lexicon WHERE word = %s AND phonemes = %s AND language = %s", (word, phonemes, language))

            connection.commit()
            connection.close()
        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepository: error when recording deleting aligned entries for language "{language}": "{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def get_generated_plain_entries(self, language, callback=None):
        return self.get_plain_entries_with_given_status(language, 'generated', callback=None)

    def get_reviewed_plain_entries(self, language, callback=None):
        return self.get_plain_entries_with_given_status(language, 'reviewed', callback=None)

    def get_plain_entries_with_given_status(self, language, status, callback=None):
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()

            # Retrieve all generated plain entries for the specified language
            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute("SELECT word, phonemes FROM plain_phonetic_lexicon WHERE language = ? AND status = ?", (language, status))
            else:  # Assume postgres
                cursor.execute("SELECT word, phonemes FROM plain_phonetic_lexicon WHERE language = %s AND status = %s", (language, status))

            records = cursor.fetchall()
            connection.close()

            # Convert records to a list of dicts
            if os.getenv('DB_TYPE') == 'sqlite':
                entries = [{'word': record[0], 'phonemes': record[1]} for record in records]
            else: # Assume postgres
                entries = [{'word': record['word'], 'phonemes': record['phonemes']} for record in records]
            return entries

        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepository: error when fetching plain entries for language "{language}": "{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def get_generated_aligned_entries(self, language, callback=None):
        return self.get_aligned_entries_with_status(language, 'generated', callback=None)

    def get_reviewed_aligned_entries(self, language, callback=None):
        return self.get_aligned_entries_with_status(language, 'reviewed', callback=None)

    def get_aligned_entries_with_status(self, language, status, callback=None):
        try:
            connection = connect(self.db_file)
            cursor = connection.cursor()

            # Retrieve all generated aligned entries for the specified language
            if os.getenv('DB_TYPE') == 'sqlite':
                cursor.execute("SELECT word, phonemes, aligned_graphemes, aligned_phonemes FROM aligned_phonetic_lexicon WHERE language = ? AND status = ?", (language, status))
            else:  # Assume postgres
                cursor.execute("SELECT word, phonemes, aligned_graphemes, aligned_phonemes FROM aligned_phonetic_lexicon WHERE language = %s AND status = %s", (language, status))

            records = cursor.fetchall()
            connection.close()

            # Convert records to a list of dicts
            if os.getenv('DB_TYPE') == 'sqlite':
                entries = [{'word': record[0], 'phonemes': record[1], 'aligned_graphemes': record[2], 'aligned_phonemes': record[3]} for record in records]
            else:  # Assume postgres
                entries = [{'word': record['word'], 'phonemes': record['phonemes'], 'aligned_graphemes': record['aligned_graphemes'], 'aligned_phonemes': record['aligned_phonemes']}
                           for record in records]
            return entries

        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepository: error when fetching generated aligned entries for language "{language}": "{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')



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

    def load_and_initialise_aligned_lexicon(self, file_path, language, callback=None):
        try:
            data = read_local_json_file(file_path)
        except:
            return ( 'error', 'unable to read file' )
        items = []
        try:
            for word in data:
                aligned_graphemes, aligned_phonemes = data[word]
                #print(f'--- Uploading {word}: {aligned_graphemes}/{aligned_phonemes}')
                items.append({
                    'word': word,
                    'phonemes': aligned_phonemes.replace('|', ''),  
                    'aligned_graphemes': aligned_graphemes,
                    'aligned_phonemes': aligned_phonemes,
                })
            self.initialise_aligned_lexicon(items, language, callback=callback)
            return ( 'success', f'{len(items)} items loaded' )
        except Exception as e:
            return ( 'error', 'something went wrong in internalising aligned lexicon: {str(e)}\n{traceback.format_exc()}' )

# Initialise from text taken from the orthography definition.
#
# Typical lines will look like this:
#
# hng | ng  
#
# hny | gn 
# 
# ng | ng
# 
# ny | gn 
# 
# hl | l

    def load_and_initialise_aligned_lexicon_from_orthography_data(self, grapheme_phoneme_data, language, callback=None):
        try:
            items = []
            for grapheme_phoneme_item in grapheme_phoneme_data:
                graphemes = grapheme_phoneme_item['grapheme_variants'].split()
                phoneme = grapheme_phoneme_item['phonemes']
                for grapheme in graphemes:
                    items.append({
                        'word': grapheme,
                        'phonemes': phoneme,  # Assuming phoneme is already in the desired format, which could be IPA or ARPAbet-like
                        'aligned_graphemes': grapheme,  
                        'aligned_phonemes': phoneme,
                    })

            self.initialise_aligned_lexicon(items, language, callback=callback)
            return ('success', f'{len(items)} items loaded')
        except Exception as e:
            return ('error', f'Something went wrong in internalising aligned lexicon from orthography data: {str(e)}\n{traceback.format_exc()}')

## Contents for plain lexicon JSON file assumed to be in this format:

##{
##    "a": "æ",
##    "aah": "ˈɑː",
##    "aardvark": "ˈɑːdvɑːk",
##    "aardvarks": "ˈɑːdvɑːks",
##    "aardwolf": "ˈɑːdwʊlf",
##    "aba": "ɐbˈæ",

    def load_and_initialise_plain_lexicon(self, file_path, language, callback=None):

        # Read the file based on its extension
        try: 
            file_extension = extension_for_file_path(file_path)
        
            if file_extension == 'json':
                data = read_plain_json_lexicon(file_path)
            elif file_extension == 'txt':
                data = read_plain_text_lexicon(file_path)
            else:
                return ('error', 'Unsupported file format')
        except Exception as e:
            return ('error', f'Error reading file: {str(e)}\n{traceback.format_exc()}')

        # Initialise the lexicon
        try:
            if not check_consistent_plain_lexicon_data(data, callback=callback):
                return ('error', f'Something went wrong in internalisation: generated lexicon data was not consistent')
            self.initialise_plain_lexicon(data, language, callback=callback)
            return ('success', f'{len(data)} items loaded')
        except Exception as e:
            return ('error', f'Something went wrong in internalisation: {str(e)}\n{traceback.format_exc()}')

    # Return two values: ( consistent, error_message )
    def consistent_aligned_phonetic_lexicon_entry(self, word, phonemes, aligned_graphemes, aligned_phonemes):
        if word != aligned_graphemes.replace('|', ''):
            return ( False, f"'{word}' is not consistent with '{aligned_graphemes}'" )
        elif phonemes != aligned_phonemes.replace('|', ''):
            return ( False, f"'{phonemes}' is not consistent with '{aligned_phonemes}'" )
        elif len(aligned_graphemes.split('|')) != len(aligned_phonemes.split('|')):
            return ( False, f"'{aligned_graphemes}' and '{aligned_phonemes}' have different numbers of components" )
        else:
            return ( True, '' )



        

def check_consistent_plain_lexicon_data(data, callback=None):
    if not isinstance(data, list):
        post_task_update(callback, f'*** PhoneticLexiconRepository: generated data was not a list')
        return False
    for item in data:
        try:
            word = item['word']
            phonemes = item['phonemes']
        except:
            post_task_update(callback, f'*** PhoneticLexiconRepository: error: bad item {item} in generated data')
            return False
    return True

def read_plain_json_lexicon(file_path):
    data0 = read_local_json_file(file_path)

    data = [ { 'word': key, 'phonemes': [ data0[key] ] }
             for key in data0 ]

    return data

def read_plain_text_lexicon(file_path):
    data = []
    lines = read_local_txt_file(file_path).split('\n')
    
    for line in lines:
        word, phonemes_list = parse_phonetic_lexicon_line(line)
        if word:
            for phonemes in phonemes_list:
                data += [ { 'word': word, 'phonemes': phonemes } ]
                
    return data

def parse_phonetic_lexicon_line(line):
    if line.count('/') >= 2:
        return parse_ipa_dict_phonetic_lexicon_line(line)
    else:
        return parse_arpabet_like_phonetic_lexicon_line(line)

## Contents for ipa-dict plain lexicon file can have single or multiple entries:
##     
## astasieret	/astaˈziːʁət/
## Astats	/asˈtaːt͡s/, /aˈstaːt͡s/

def parse_ipa_dict_phonetic_lexicon_line(line):
    parts = [ part.strip() for part in line.split('/')
              if part.replace(',', '').strip() != '' ]
        
    if len(parts) < 2:
        return ( None, None )  # Skip empty and malformed lines

    # The German ipa-dict preserves casing, but we discard it.
    word = parts[0].lower()
    
    if ' ' in word:
        return ( None, None )  # Skip entries for multi word expressions

    phonemes_list = parts[1:]
    return word, phonemes_list

## Contents for ARPAbet plain lexicon txt file assumed to be in this format:
##
## drösinöe dZeu s i n euille
## föe f euille
## sinöe s i n euille
## ixöe i KH euille

def parse_arpabet_like_phonetic_lexicon_line(line):
    parts = line.strip().split()
    if len(parts) < 2:
        return ( None, None )  # Skip empty and malformed lines

    word = parts[1]
    phonemes = ' '.join(parts[1:])
    
    return word, [ phonemes ]

### ipa-dict entries for some languages:
### Icelandic: brunnið	/prʏnɪð/
### Romanian: aanicăi	/aanikəj/
##
##def clean_up_ipa_dict_entry(phonetic_str):
##    return phonetic_str.replace('/', '')


