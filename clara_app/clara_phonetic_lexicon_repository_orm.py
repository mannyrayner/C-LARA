
from .models import PhoneticEncoding, PlainPhoneticLexicon, AlignedPhoneticLexicon

#from .clara_utils import _use_orm_repositories
from .clara_utils import _s3_storage, get_config, absolute_file_name, absolute_local_file_name
from .clara_utils import file_exists, local_file_exists, basename, extension_for_file_path
from .clara_utils import make_directory, directory_exists, local_directory_exists, make_local_directory
from .clara_utils import read_json_file, read_txt_file, read_local_json_file, read_local_txt_file
from .clara_utils import post_task_update

from .clara_classes import InternalCLARAError

from pathlib import Path

import os
import traceback
import pprint

config = get_config()

class PhoneticLexiconRepositoryORM:
    #def __init__(self, initialise_from_non_orm=False, callback=None):
    def __init__(self, callback=None):
        self.possible_encodings = ( 'ipa', 'arpabet_like' )
##        if initialise_from_non_orm:
##            self.initialise_from_non_orm_repository(callback=callback)

##    def initialise_from_non_orm_repository(self, callback=None):
##        from .clara_phonetic_lexicon_repository import PhoneticLexiconRepository
##        
##        non_orm_repository = PhoneticLexiconRepository(callback=callback)
##        exported_data = non_orm_repository.export_phonetic_lexicon_data(callback)
##
##        # Handle phonetic encoding data using bulk_create
##        encoding_instances = [
##            PhoneticEncoding(language=data['language'], encoding=data['encoding'])
##            for data in exported_data['encoding']
##        ]
##        PhoneticEncoding.objects.bulk_create(encoding_instances, ignore_conflicts=True)
##        post_task_update(callback, f'--- Imported phonetic encoding for {len(exported_data["encoding"])} languages')
##
##        # Handle aligned lexicon entries using bulk_create
##        aligned_instances = [
##            AlignedPhoneticLexicon(
##                word=data['word'],
##                phonemes=data['phonemes'],
##                aligned_graphemes=data['aligned_graphemes'],
##                aligned_phonemes=data['aligned_phonemes'],
##                language=data['language'],
##                status=data['status']
##            ) for data in exported_data['aligned']
##        ]
##        AlignedPhoneticLexicon.objects.bulk_create(aligned_instances, ignore_conflicts=True)
##        post_task_update(callback, f'--- Imported {len(exported_data["aligned"])} aligned lexicon entries')
##
##        # Handle plain lexicon entries using bulk_create
##        plain_instances = [
##            PlainPhoneticLexicon(
##                word=data['word'],
##                phonemes=data['phonemes'],
##                language=data['language'],
##                status=data['status']
##            ) for data in exported_data['plain']
##        ]
##        # batch_size to mitigate issues with database locking interfering with DjangoQ
##        PlainPhoneticLexicon.objects.bulk_create(plain_instances, ignore_conflicts=True, batch_size=1000)  
##        post_task_update(callback, f'--- Imported {len(exported_data["plain"])} plain lexicon entries')

    def set_encoding_for_language(self, language, encoding, callback=None):
        try:
            if encoding not in self.possible_encodings:
                post_task_update(callback, f'*** PhoneticLexiconRepositoryORM: error when setting encoding for "{language}": illegal value "{encoding}"')
                raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

            # Using update_or_create to either update an existing entry or create a new one
            PhoneticEncoding.objects.update_or_create(
                language=language,
                defaults={'encoding': encoding},
            )
            post_task_update(callback, f'Encoding for "{language}" set to "{encoding}" successfully.')
            
        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepositoryORM: error when setting encoding for "{language}": {str(e)}\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def get_encoding_for_language(self, language, callback=None):
        try:
            # Attempt to retrieve the encoding setting for the specified language
            encoding = PhoneticEncoding.objects.filter(language=language).first()
            
            if encoding:
                return encoding.encoding
            else:
                # Default to 'ipa' if no specific encoding is found
                return 'ipa'
                
        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepositoryORM: error when getting encoding for "{language}": "{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def aligned_entries_exist_for_language(self, language, callback=None):
        try:
            # Using the Django ORM to count entries for the specified language
            exists = AlignedPhoneticLexicon.objects.filter(language=language).exists()
            return exists
        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepositoryORM: error when checking for aligned entries "{language}": {str(e)}\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def plain_phonetic_entries_exist_for_language(self, language, callback=None):
        try:
            # Using the Django ORM to count entries for the specified language
            exists = PlainPhoneticLexicon.objects.filter(language=language).exists()
            return exists
        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepositoryORM: error when checking for plain phonetic entries "{language}": {str(e)}\n{traceback.format_exc()}')
        raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def add_or_update_aligned_entry(self, word, phonemes, aligned_graphemes, aligned_phonemes, language, status, callback=None):
        try:
            # Get or create a new entry; this method automatically checks if an entry exists
            obj, created = AlignedPhoneticLexicon.objects.update_or_create(
                word=word, phonemes=phonemes, language=language,
                defaults={
                    'aligned_graphemes': aligned_graphemes,
                    'aligned_phonemes': aligned_phonemes,
                    'status': status
                }
            )
            if created:
                post_task_update(callback, f'--- Created new aligned entry for word "{word}" in language "{language}"')
            else:
                post_task_update(callback, f'--- Updated existing aligned entry for word "{word}" in language "{language}"')
        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepositoryORM: error when inserting/updating aligned entry "{word}; {phonemes}" in phonetic lexicon database: {str(e)}\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def add_or_update_plain_entry(self, word, phonemes, language, status, callback=None):
        try:
            # Get or create a new entry; this method automatically checks if an entry exists
            obj, created = PlainPhoneticLexicon.objects.update_or_create(
                word=word, phonemes=phonemes, language=language,
                defaults={'status': status}
            )
            if created:
                post_task_update(callback, f'--- Created new plain entry for word "{word}" in language "{language}"')
            else:
                post_task_update(callback, f'--- Updated existing plain entry for word "{word}" in language "{language}"')
        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepositoryORM: error when inserting/updating plain entry "{word}; {phonemes}" in phonetic lexicon database: {str(e)}\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def delete_aligned_entry(self, word, phonemes, language, callback=None):
        try:
            # Delete the entry using Django ORM's filter and delete methods
            deleted_count, _ = AlignedPhoneticLexicon.objects.filter(word=word, phonemes=phonemes, language=language).delete()
            if deleted_count > 0:
                post_task_update(callback, f'--- Deleted "{deleted_count}" aligned entry(ies) for "{word}; {phonemes}" in language "{language}"')
            else:
                post_task_update(callback, '--- No aligned entries found to delete')
        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepositoryORM: error when deleting aligned entry "{word}; {phonemes}" from phonetic lexicon database: {str(e)}\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def delete_plain_entry(self, word, phonemes, language, callback=None):
        try:
            # Delete the entry using Django ORM's filter and delete methods
            deleted_count, _ = PlainPhoneticLexicon.objects.filter(word=word, phonemes=phonemes, language=language).delete()
            if deleted_count > 0:
                post_task_update(callback, f'--- Deleted "{deleted_count}" plain entry(ies) for "{word}; {phonemes}" in language "{language}"')
            else:
                post_task_update(callback, '--- No plain entries found to delete')
        except Exception as e:
            post_task_update(callback, f'*** PhoneticLexiconRepositoryORM: error when deleting plain entry "{word}; {phonemes}" from phonetic lexicon database: {str(e)}\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def get_all_aligned_entries_for_language(self, language, callback=None):
        try:
            # Fetch all records for the specified language using Django ORM's filter method
            records = AlignedPhoneticLexicon.objects.filter(language=language).values('word', 'phonemes', 'aligned_graphemes', 'aligned_phonemes', 'status')

            # Convert QuerySet to a list of dicts
            entries = list(records)

            post_task_update(callback, f'--- Retrieved {len(entries)} aligned phonetic lexicon entries for language "{language}"')

            return entries
        except Exception as e:
            error_message = f'*** Error when retrieving aligned lexicon entries for language "{language}": "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def get_aligned_entries_batch(self, words, language, callback=None):
        try:
            # Use Django ORM's __in lookup to fetch matching records for a list of words
            records = AlignedPhoneticLexicon.objects.filter(language=language, word__in=words).values('word', 'phonemes', 'aligned_graphemes', 'aligned_phonemes', 'status')

            entries = list(records)

            post_task_update(callback, f'--- Retrieved {len(entries)} aligned phonetic lexicon entries batch for language "{language}"')

            return entries
        except Exception as e:
            error_message = f'*** Error when fetching aligned entries batch for language "{language}": "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def get_plain_entries_batch(self, words, language, callback=None):
        try:
            # Use Django ORM's __in lookup to fetch matching records for a list of words
            records = PlainPhoneticLexicon.objects.filter(language=language, word__in=words).values('word', 'phonemes', 'status')

            entries = list(records)

            post_task_update(callback, f'--- Retrieved {len(entries)} plain phonetic lexicon entries batch for language "{language}"')

            return entries
        except Exception as e:
            error_message = f'*** Error when fetching plain entries batch for language "{language}": "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def initialise_aligned_lexicon(self, items, language, callback=None):
        try:
            # Clear existing 'uploaded' entries for the language
            AlignedPhoneticLexicon.objects.filter(language=language, status='uploaded').delete()

            # Prepare new objects for bulk insertion
            new_objects = [AlignedPhoneticLexicon(
                word=item['word'],
                phonemes=item['phonemes'],
                aligned_graphemes=item['aligned_graphemes'],
                aligned_phonemes=item['aligned_phonemes'],
                language=language,
                status='uploaded'
            ) for item in items]

            # Use bulk_create to insert all new objects in a single operation
            AlignedPhoneticLexicon.objects.bulk_create(new_objects)

            post_task_update(callback, f'--- Initialised aligned phonetic lexicon for {language}, {len(items)} entries')
        except Exception as e:
            error_message = f'*** Error when initialising aligned lexicon for language "{language}": "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def initialise_plain_lexicon(self, items, language, callback=None):
        try:
            # Clear existing 'uploaded' entries for the language
            PlainPhoneticLexicon.objects.filter(language=language, status='uploaded').delete()

            # Prepare new objects for bulk insertion
            new_objects = [PlainPhoneticLexicon(
                word=item['word'],
                phonemes=item['phonemes'],
                language=language,
                status='uploaded'
            ) for item in items]

            # Use bulk_create to insert all new objects in a single operation
            PlainPhoneticLexicon.objects.bulk_create(new_objects)

            post_task_update(callback, f'--- Initialised plain phonetic lexicon for {language}, {len(items)} entries')
        except Exception as e:
            error_message = f'*** Error when initialising plain lexicon for language "{language}": "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def record_guessed_plain_entries(self, plain_entries, language, callback=None):
        self.record_plain_entries(plain_entries, language, 'generated', callback)

    def record_reviewed_plain_entries(self, plain_entries, language, callback=None):
        self.record_plain_entries(plain_entries, language, 'reviewed', callback)

    def record_plain_entries(self, plain_entries, language, status, callback=None):
        try:
            # Start by deleting any existing records that may conflict
            self.delete_plain_entries(plain_entries, language, callback=callback)
            
            # Prepare new objects for bulk insertion
            new_objects = [PlainPhoneticLexicon(
                word=entry['word'],
                phonemes=entry['phonemes'],
                language=language,
                status=status
            ) for entry in plain_entries]

            # Use bulk_create to insert all new objects in a single operation, ignoring conflicts
            PlainPhoneticLexicon.objects.bulk_create(new_objects, ignore_conflicts=True)

            post_task_update(callback, f'--- Recorded {len(plain_entries)} plain phonetic entries for language {language} with status {status}')
        except Exception as e:
            error_message = f'*** Error when recording plain entries for language "{language}": "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def delete_plain_entries(self, plain_entries, language, callback=None):
        try:
            # Delete specified entries
            for entry in plain_entries:
                PlainPhoneticLexicon.objects.filter(
                    word=entry['word'], 
                    phonemes=entry['phonemes'], 
                    language=language
                ).delete()

            post_task_update(callback, f'--- Deleted specified plain phonetic entries for language {language}')
        except Exception as e:
            error_message = f'*** Error when deleting plain entries for language "{language}": "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def record_guessed_aligned_entries(self, aligned_entries, language, callback=None):
        self.record_aligned_entries(aligned_entries, language, 'generated', callback)

    def record_reviewed_aligned_entries(self, aligned_entries, language, callback=None):
        self.record_aligned_entries(aligned_entries, language, 'reviewed', callback)

    def record_aligned_entries(self, aligned_entries, language, status, callback=None):
        try:
            # Start by deleting any existing records that may conflict
            self.delete_aligned_entries(aligned_entries, language, callback=callback)
            
            new_objects = []
            for entry in aligned_entries:
                # The 'phonemes' field is constructed from 'aligned_phonemes' if it's missing
                phonemes = entry.get('phonemes', entry.get('aligned_phonemes').replace('|', ''))
                new_objects.append(AlignedPhoneticLexicon(
                    word=entry['word'],
                    phonemes=phonemes,
                    aligned_graphemes=entry['aligned_graphemes'],
                    aligned_phonemes=entry['aligned_phonemes'],
                    language=language,
                    status=status
                ))

            # Use bulk_create for efficient batch insertion, ignoring conflicts
            AlignedPhoneticLexicon.objects.bulk_create(new_objects, ignore_conflicts=True)

            post_task_update(callback, f'--- Recorded {len(aligned_entries)} aligned phonetic entries for language {language} with status {status}')
        except Exception as e:
            error_message = f'*** Error when recording aligned entries for language "{language}": "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def delete_aligned_entries(self, aligned_entries, language, callback=None):
        try:
            for entry in aligned_entries:
                phonemes = entry.get('phonemes', entry.get('aligned_phonemes').replace('|', ''))
                AlignedPhoneticLexicon.objects.filter(
                    word=entry['word'], 
                    phonemes=phonemes, 
                    language=language
                ).delete()

            post_task_update(callback, f'--- Deleted specified aligned phonetic entries for language {language}')
        except Exception as e:
            error_message = f'*** Error when deleting aligned entries for language "{language}": "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def record_guessed_aligned_entries(self, aligned_entries, language, callback=None):
        self.record_aligned_entries(aligned_entries, language, 'generated', callback)

    def record_reviewed_aligned_entries(self, aligned_entries, language, callback=None):
        self.record_aligned_entries(aligned_entries, language, 'reviewed', callback)

    def record_aligned_entries(self, aligned_entries, language, status, callback=None):
        try:
            # Delete existing entries to avoid uniqueness constraint violations
            self.delete_aligned_entries(aligned_entries, language, callback)

            # Prepare new objects for batch creation
            new_objects = []
            for entry in aligned_entries:
                phonemes = entry.get('phonemes', entry.get('aligned_phonemes').replace('|', ''))
                new_objects.append(AlignedPhoneticLexicon(
                    word=entry['word'],
                    phonemes=phonemes,
                    aligned_graphemes=entry['aligned_graphemes'],
                    aligned_phonemes=entry['aligned_phonemes'],
                    language=language,
                    status=status
                ))

            # Use bulk_create for efficient batch insertion, ignoring conflicts
            AlignedPhoneticLexicon.objects.bulk_create(new_objects, ignore_conflicts=True)
            post_task_update(callback, f'--- Recorded {len(aligned_entries)} aligned phonetic entries for language {language} with status {status}')
        except Exception as e:
            error_message = f'*** Error when recording aligned entries for language "{language}": "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def delete_aligned_entries(self, aligned_entries, language, callback=None):
        try:
            for entry in aligned_entries:
                phonemes = entry.get('phonemes', entry.get('aligned_phonemes').replace('|', ''))
                AlignedPhoneticLexicon.objects.filter(
                    word=entry['word'], 
                    phonemes=phonemes, 
                    language=language
                ).delete()

            post_task_update(callback, f'--- Deleted specified aligned phonetic entries for language {language}')
        except Exception as e:
            error_message = f'*** Error when deleting aligned entries for language "{language}": "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def get_generated_plain_entries(self, language, callback=None):
        return self.get_plain_entries_with_status(language, 'generated', callback)

    def get_reviewed_plain_entries(self, language, callback=None):
        return self.get_plain_entries_with_status(language, 'reviewed', callback)

    def get_plain_entries_with_status(self, language, status, callback=None):
        try:
            entries = PlainPhoneticLexicon.objects.filter(language=language, status=status).values('word', 'phonemes')
            return list(entries)
        except Exception as e:
            error_message = f'*** Error when fetching plain entries for language "{language}" with status "{status}": "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

    def get_generated_aligned_entries(self, language, callback=None):
        return self.get_aligned_entries_with_status(language, 'generated', callback)

    def get_reviewed_aligned_entries(self, language, callback=None):
        return self.get_aligned_entries_with_status(language, 'reviewed', callback)

    def get_aligned_entries_with_status(self, language, status, callback=None):
        try:
            entries = AlignedPhoneticLexicon.objects.filter(language=language, status=status).values('word', 'phonemes', 'aligned_graphemes', 'aligned_phonemes')
            return list(entries)
        except Exception as e:
            error_message = f'*** Error when fetching aligned entries for language "{language}" with status "{status}": "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Phonetic lexicon database inconsistency')

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
