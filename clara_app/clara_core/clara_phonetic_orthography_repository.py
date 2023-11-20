"""
clara_phonetic_orthography_repository.py


"""


from .clara_utils import get_config, absolute_file_name, absolute_local_file_name, file_exists, write_txt_file, read_txt_file
from .clara_utils import make_directory, directory_exists
from .clara_utils import post_task_update

from .clara_classes import Image, InternalCLARAError

from pathlib import Path

import os
import traceback

config = get_config()

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

    def save_entry(self, language, orthography_text, accents_text, callback=None):
        try:
            orthography_file = self._orthography_pathname_for_language(language)
            accents_file = self._accents_pathname_for_language(language)
            
            write_txt_file(orthography_text, orthography_file)
            write_txt_file(accents_text, accents_file)
            
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

    def get_parsed_entry(self, language, callback=None):
        try:
            orthography_text, accents_text = self.get_text_entry(language)
            if not orthography_text:
                return ( None, None )
            else:
                return ( self._parse_phonetic_orthography_entry(orthography_text),
                         self._parse_accents_entry(accents_text) )
            
        except Exception as e:
            post_task_update(callback, f'*** Error when getting parsed phonetic orthography repository entry for "{language}": "{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic orthography repository inconsistency')

    def _orthography_pathname_for_language(self, language):
        return absolute_file_name(Path(self.base_dir) / f'{language}_orthography.txt')

    def _accents_pathname_for_language(self, language):
        return absolute_file_name(Path(self.base_dir) / f'{language}_accents.txt')

    def _parse_phonetic_orthography_entry(self, text):
        lines = text.split('\n')
        parsed_lines = []
        for line in lines:
            parsed_line = self._parse_phonetic_orthography_line(line)
            if len(parsed_line) != 0:
                parsed_lines += [ parsed_line ]
        return parsed_lines

    def _parse_phonetic_orthography_line(self, line):
        components = line.split()
        return components

    def _parse_accents_entry(self, text):
        lines = text.split('\n')
        accents = []
        for line in lines:
            parsed_line = self._parse_accents_line(line)
            if len(parsed_line) == 1:
                accents += [ parsed_line ]
        return accents
    
    def _parse_accents_line(self, line):
        components = line.split()
        if len(components) == 0:
            return []
        elif len(components) > 1:
            raise InternalCLARAError(message='Bad line in accents file (length greater than 1), "{line}"')
        else:
            return [ self._parse_accents_line_item(components[0]) ]

    def _parse_accents_line_item(self, string):
        if len(string) == 1:
            return string
        elif string.startswith('U+') or unicode_str.startswith('u+'):
            try:
                hex_value = string[2:]
                return str(chr(int(hex_value, 16)))
            except:
                InternalCLARAError(message='Bad item in accents file, "{string}"')
        else:
            raise InternalCLARAError(message='Bad item in accents file, "{string}"')


    
