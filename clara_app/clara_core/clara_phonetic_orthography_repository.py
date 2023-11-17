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

    def save_entry(self, language, text):
        try:
            file = self._pathname_for_language(language)
            write_txt_file(text, file)
            
        except Exception as e:
            post_task_update(callback, f'*** Error when saving phonetic orthography repository entry for "{language}": "{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic orthography repository inconsistency')

    def get_text_entry(self, language):
        try:
            file = self._pathname_for_language(language)
            if file_exists(file):
                return read_txt_file(file)
            else:
                return None
            
        except Exception as e:
            post_task_update(callback, f'*** Error when getting plain phonetic orthography repository entry for "{language}": "{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic orthography repository inconsistency')

    def get_parsed_entry(self, language):
        try:
            text = self.get_text_entry(language)
            if not text:
                return None
            else:
                return self._parse_phonetic_orthography_entry(text)
            
        except Exception as e:
            post_task_update(callback, f'*** Error when getting parsed phonetic orthography repository entry for "{language}": "{str(e)}"\n{traceback.format_exc()}')
            raise InternalCLARAError(message='Phonetic orthography repository inconsistency')

    def _pathname_for_language(self, language):
        return absolute_file_name(Path(self.base_dir) / f'{language}.txt')

    def _parse_phonetic_orthography_entry(self, text):
        lines = text.split('\n')
        parsed_lines = []
        for line in lines:
            parsed_line = line.split()
            if len(parsed_line) != 0:
                parsed_lines += [ parsed_line ]
        return parsed_lines
    


    
