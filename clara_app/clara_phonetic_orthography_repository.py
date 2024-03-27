"""
clara_phonetic_orthography_repository.py


"""


from .clara_utils import get_config, absolute_file_name, absolute_local_file_name, file_exists, write_txt_file, read_txt_file
from .clara_utils import make_directory, directory_exists
from .clara_utils import post_task_update, remove_blank_lines

from .clara_classes import InternalCLARAError

from pathlib import Path

import os
import traceback

config = get_config()

def phonetic_orthography_resources_available(language):
    repo = PhoneticOrthographyRepository()
    orthography, accents = repo.get_text_entry(language)
    return orthography

class PhoneticOrthographyRepository:
    def __init__(self, callback=None):   
        self.base_dir = absolute_file_name(config.get('phonetic_orthography_repository', 'base_dir'))
        self._initialize_repository(callback=callback)

    def _initialize_repository(self, callback=None):
        try:
            if not directory_exists(self.base_dir):
                make_directory(self.base_dir, parents=True, exist_ok=True)

        except Exception as e:
            error_message = f'*** Error when trying to initialise phonetic orthography repository: "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise InternalCLARAError(message='Phonetic orthography repository inconsistency')

    def save_structured_data(self, language, orthography_data, accents_data, callback=None):
        try:
            orthography_text = self._orthography_data_to_text(orthography_data, callback=callback)
            accents_text = self._accents_data_to_text(accents_data, callback=callback)
            
            self.save_entry(language, orthography_text, accents_text, callback=callback)
            
        except Exception as e:
            post_task_update(callback, f'*** Error when saving phonetic orthography data for "{language}": "{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic orthography repository inconsistency')

    def save_entry(self, language, orthography_text, accents_text, callback=None):
        try:
            orthography_file = self._orthography_pathname_for_language(language)
            accents_file = self._accents_pathname_for_language(language)
            
            write_txt_file(remove_blank_lines(orthography_text), orthography_file)
            write_txt_file(remove_blank_lines(accents_text), accents_file)
            
        except Exception as e:
            post_task_update(callback, f'*** Error when saving phonetic orthography repository entry for "{language}": "{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic orthography repository inconsistency')

    def get_text_entry(self, language, callback=None):
        try:
            orthography_file = self._orthography_pathname_for_language(language)
            accents_file = self._accents_pathname_for_language(language)
            
            if file_exists(orthography_file) and file_exists(accents_file):
                return ( read_txt_file(orthography_file), read_txt_file(accents_file) )
            else:
                return ( None, None )
            
        except Exception as e:
            post_task_update(callback, f'*** Error when getting plain phonetic orthography repository entry for "{language}": "{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic orthography repository inconsistency')

    def get_parsed_entry(self, language, formatting='default', callback=None):
        try:
            orthography_text, accents_text = self.get_text_entry(language)
            if not orthography_text:
                return ( None, None )
            else:
                return ( self._parse_phonetic_orthography_entry(orthography_text, formatting=formatting),
                         self._parse_accents_entry(accents_text, formatting=formatting) )
            
        except Exception as e:
            post_task_update(callback, f'*** Error when getting parsed phonetic orthography repository entry for "{language}": "{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic orthography repository inconsistency')

    def _orthography_pathname_for_language(self, language):
        return absolute_file_name(Path(self.base_dir) / f'{language}_orthography.txt')

    def _accents_pathname_for_language(self, language):
        return absolute_file_name(Path(self.base_dir) / f'{language}_accents.txt')

    def _parse_phonetic_orthography_entry(self, text, formatting='default'):
        lines = text.split('\n')
        parsed_lines = []
        for line in lines:
            parsed_line = self._parse_phonetic_orthography_line(line, formatting=formatting)
            if parsed_line:
                parsed_lines += [ parsed_line ]
        return parsed_lines

    # An orthography line is a list of letter variants, optionally terminated by | and a display form.
    # If the "|" is not present, the first letter variant is the display form.
    def _parse_phonetic_orthography_line(self, line, formatting='default'):
        components = line.split('|')
        if len(components) == 0:
            return None
        if len(components) > 2:
            print(f'Bad phonetic orthography line, "{line}"')
            #return None
            raise InternalCLARAError(message='Bad phonetic orthography line, "{line}"')
        letter_variants = components[0].split()
        if len(letter_variants) == 0:
            return None
        display_form = components[1].strip() if len(components) == 2 else letter_variants[0]
        if formatting == 'default':
            return { 'letter_variants': letter_variants, 'display_form': display_form }
        else:
            return { 'grapheme_variants': ' '.join(letter_variants), 'phonemes': display_form }

    def _parse_accents_entry(self, text, formatting='default'):
        lines = text.split('\n')
        accents = []
        for line in lines:
            parsed_line = self._parse_accents_line(line, formatting=formatting)
            accents += parsed_line 
        return accents
    
    def _parse_accents_line(self, line, formatting='default'):
        components = line.split()
        if len(components) == 0:
            return []
        elif len(components) > 1:
            raise InternalCLARAError(message='Bad line in accents file (length greater than 1): "{line}"')
        else:
            return [ self._parse_accents_line_item(components[0], formatting=formatting) ]

    def _parse_accents_line_item(self, string, formatting='default'):
        if len(string) == 1:
            return string
        elif string.startswith('U+') or string.startswith('u+'):
            try:
                hex_value = string[2:]
                if formatting == 'default':
                    return str(chr(int(hex_value, 16)))
                else:
                    return { 'unicode_value': string }
            except:
                raise InternalCLARAError(message='Bad item in accents file, "{string}"')
        else:
            raise InternalCLARAError(message='Bad item in accents file, "{string}"')


    def _orthography_data_to_text(self, orthography_data, callback=None):
        lines = [ self._orthography_item_to_text(item)
                  for item in orthography_data
                  if not self._null_orthography_item(item)
                  ]
        return '\n'.join(lines)

    def _orthography_item_to_text(self, item):
        grapheme_variants = item['grapheme_variants']
        phonemes = item['phonemes']
        return f'{grapheme_variants} | {phonemes}'

    def _null_orthography_item(self, item):
        return not item['grapheme_variants'].strip() and not item['phonemes'].strip()

    # Return ( consistent, error_message )
    def consistent_orthography_item(self, item):
        if not isinstance(item, ( dict )) or not 'grapheme_variants' in item or not 'phonemes' in item:
            return ( False, f'Error: orthography item {item} is not in correct format' )

        grapheme_variants0 = item['grapheme_variants']
        phonemes0 = item['phonemes']

        # Treat null values as consistent, though we will discard them
        if not grapheme_variants0 and not grapheme_variants0:
            return True

        grapheme_variants = grapheme_variants0.strip() if isinstance(grapheme_variants0, ( str ) ) else ''
        phonemes = phonemes0.strip() if isinstance(phonemes0, ( str ) ) else ''
        
        if not grapheme_variants:
            return ( False, f'Error: no grapheme variants specified for "{phonemes}"' )
        elif not phonemes:
            return ( False, f'Error: no phonemes specified for "{grapheme_variants}"' )
        else:
            return ( True, '' )
    
    def _accents_data_to_text(self, accents_data, callback=None):
        lines = [ _accents_item_to_text(item)
                  for item in accents_data
                  if not _null_accents_item(item)
                  ]
        return '\n'.join(lines)

    def _null_accents_item(self, item):
        unicode_value = item['unicode_value']
        return not unicode_value.strip()

    def _accents_item_to_text(item):
        unicode_value = item['unicode_value']
        return unicode_value.strip()

    # Return ( consistent, error_message )
    def consistent_accents_item(self, item):
        if not isinstance(item, ( dict )) or not 'unicode_value' in item:
            return ( False, f'Error: accents item {item} is not in correct format' )
        else:
            unicode_value0 = item['unicode_value']

        # Treat null values as consistent, though we will discard them
        if not unicode_value0:
            return True
        else:
            unicode_value = unicode_value0.strip()

        if not unicode_value.startswith('U+') or unicode_value.startswith('u+'):
            return ( False, f'Error: accents item {item} does not start with "U+" or "u+"' )
        else:
            try:
                hex_value = unicode_value[2:]
                char = chr(int(hex_value, 16))
                return ( True, '' )
            except:
                return ( False, f'Error: accents item {item} is not of form "U+<hex_number>"' )
