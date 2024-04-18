from . import clara_internalise
from .clara_classes import *
from .clara_utils import absolute_file_name, make_directory, get_file_time, rename_file, file_exists
from .clara_utils import write_json_or_txt_file, read_json_or_txt_file, read_json_file, extension_for_file_path
from .clara_utils import make_line_breaks_canonical_n
from .clara_utils import get_config


import os
import json
from typing import Union
import datetime
from pathlib import Path

config = get_config()

class PromptTemplateRepository:

    # Get the prompt repository for the language in question, creating it if necessary.
    # Each prompt repository has its own directory, containing files and metadata, plus an archive dir.
    def __init__(self, language: str):
        self.language = language
        self.root_dir = Path(absolute_file_name(config.get('prompt_template_repository', 'base_dir')))
        self.language_dir = self.root_dir / self.language
        
        # ensure the language directory exists
        make_directory(self.language_dir, parents=True, exist_ok=True)

    # Return the metadata file. This lists all the files, including the ones in the archive directory.
    def _get_metadata_file(self):
        return self.language_dir / 'metadata.json'

    # Return the archive dir
    def _get_archive_dir(self):
        return self.language_dir / 'archive'

    # Get the path where a file version will be stored.
    def _get_file_path(self, template_or_examples: str, annotation_type: str, operation: str):
        extension = 'txt' if template_or_examples == 'template' else 'json'
        return self.language_dir / f'{annotation_type}_{operation}_{template_or_examples}.{extension}'

    # Return the contents of file version, or None.
    # template_or_examples is one of ( "template", "examples" )
    # annotation_type is one of ( "segmented", "gloss", "lemma", "pinyin", "lemma_and_gloss" )
    # operation is one of ( "annotate", "improve" )
    # Optionally load from a specified archive path probably extracted from the metadata
    def load_template_or_examples(self, template_or_examples: str, annotation_type: str, operation: str, archive_path=None):
        if archive_path:
            file_path = archive_path
        else:
            file_path = self._get_file_path(template_or_examples, annotation_type, operation)
            
        if file_exists(file_path):
            data = read_json_or_txt_file(file_path)
            if isinstance(data, str):
                data = make_line_breaks_canonical_n(data)
        else:
            data = None
            
        check_well_formed_for_loading(data, template_or_examples, annotation_type, operation, self.language)
        return data

    # If we don't even have anything in the default templates and examples, return blank contents so that something can be added
    def blank_template_or_examples(self, template_or_examples: str, annotation_type: str, operation: str):
        if template_or_examples == 'template':
            return ' '
        elif template_or_examples == 'examples' and (operation == 'annotate' or annotation_type == 'segmented'):
            return [ ' ' ]
        else:
            return [ ( ' ', ' ' ) ]

    # Write a file version, archive the old one if necessary, and update the metadata.
    # template_or_examples is one of ( "template", "examples" )
    # annotation_type is one of ( "segmented", "gloss", "lemma", "pinyin", "lemma_and_gloss" )
    # operation is one of ( "annotate", "improve" )
    # data is the data to store
    # user is the userid to put in the metadata
    def save_template_or_examples(self, template_or_examples: str, annotation_type: str, operation: str,
                                  data: Union[str, list], user='Unknown'):
        # Raises exception if data is not well-formed in this context
        check_well_formed_for_saving(data, template_or_examples, annotation_type, operation, self.language)
        
        file_path = self._get_file_path(template_or_examples, annotation_type, operation)
        extension = extension_for_file_path(file_path)
        if isinstance(data, str):
            data = make_line_breaks_canonical_n(data)
        
        # Archive the old version, if it exists
        if file_exists(file_path):
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            archive_dir = self._get_archive_dir()
            make_directory(archive_dir, parents=True, exist_ok=True)
            archive_path = Path(archive_dir) / f'{annotation_type}_{operation}_{template_or_examples}_{timestamp}.{extension}'
            rename_file(file_path, archive_path)
        else:
            archive_path = None

        # Save the new version
        write_json_or_txt_file(data, file_path)

        # Update the metadata file
        self._update_metadata_file(file_path, archive_path, template_or_examples, annotation_type, operation, user)
        
    def _update_metadata_file(self, file_path, archive_path, template_or_examples, annotation_type, operation, user):
        metadata_file = self._get_metadata_file()
        metadata = self.get_metadata()

        # Find the entry for the file_path, if it exists, and update it to be the archive_path
        for entry in metadata:
            if entry['file'] == str(file_path):
                entry['file'] = str(archive_path)  # Transfer the entry to the archive path
                break

        # Create a new entry for the file_path with the updated information
        new_entry = {
            "file": str(file_path),
            "annotation_type": annotation_type,
            "template_or_examples": template_or_examples,
            "operation": operation,
            "user": user,
            # Use file modification timestamp as the timestamp and convert to the right format
            "timestamp": datetime.datetime.fromtimestamp(get_file_time(file_path)).strftime('%Y%m%d%H%M%S')
        }
        metadata.append(new_entry)

        # Write the updated metadata to the file
        write_json_or_txt_file(metadata, metadata_file)

    def get_metadata(self):
        metadata_file = self._get_metadata_file()
        if file_exists(metadata_file):
            metadata = read_json_file(metadata_file)
        else:
            metadata = []
        return metadata

# When we're loading, we only check that the data has the right shape that we can display it,
# e.g. that a template is a string or that gloss examples are a list of pairs of strings.
# If there are other problems, we're probably going to want to fix them by loading the
# data, editing it, and saving it.
def check_well_formed_for_loading(data, template_or_examples, annotation_type, operation, language):
    if template_or_examples == 'template':
        if not data:
            raise TemplateError(message = f'Template is missing for language "{language}"')
        if not isinstance(data, str):
            raise TemplateError(message = f'Templatelanguage "{language}" is not a string')
    elif operation == 'improve' and annotation_type != 'segmented':
        if not data:
            raise TemplateError(message = f'Examples are missing language "{language}"')
        if not is_list_of_n_tuples_of_strings(data, 2):
            raise TemplateError(message = f'Template data {data} for {annotation_type} and {operation} and language "{language}" is not a list of pairs of strings')
    else:
        if not is_list_of_strings(data):
            raise TemplateError(message = f'Template data {data} for {annotation_type} and {operation} and language "{language}" is not a list of strings')
    return True

# When we're saving the data, we carry out a more fine-grained check to try and make sure
# that the result is going to be usable.
def check_well_formed_for_saving(data, template_or_examples, annotation_type, operation, language):
    #print(f'check_well_formed_for_saving({data}, {template_or_examples}, {annotation_type}, {operation}, {language})')
    check_well_formed_for_loading(data, template_or_examples, annotation_type, operation, language)
    if template_or_examples == 'template':
        check_validity_of_template(data, annotation_type)
    elif annotation_type == 'segmented':
        for string in data:
            try:
                elements = string_to_list_of_content_elements(string, 'segmented')
            except:
                raise TemplateError(message = f'Cannot internalise "{string}" as "segmented" data')
    elif annotation_type == 'gloss' and operation == 'annotate':
        for string in data:
            try:
                elements = string_to_list_of_content_elements(string, 'gloss')
                for e in elements:
                    if e.type == 'Word' and not 'gloss' in e.annotations:
                        raise TemplateError(message = f'"{string}" is not good "gloss" "annotate" data')
            except:
                raise TemplateError(message = f'Cannot internalise "{string}" as "gloss" data')
    elif annotation_type == 'pinyin' and operation == 'annotate':
        for string in data:
            try:
                elements = string_to_list_of_content_elements(string, 'pinyin')
                for e in elements:
                    if e.type == 'Word' and not 'pinyin' in e.annotations:
                        raise TemplateError(message = f'"{string}" is not good "pinyin" "annotate" data')
            except:
                raise TemplateError(message = f'Cannot internalise "{string}" as "gloss" data')
    elif annotation_type == 'lemma' and operation == 'annotate':
        for string in data:
            try:
                elements = string_to_list_of_content_elements(string, 'lemma')
                for e in elements:
                    if e.type == 'Word' and ( not 'lemma' in e.annotations or not 'pos' in e.annotations ):
                        raise TemplateError(message = f'"{string}" is not good "lemma" "annotated" data')
            except:
                raise TemplateError(message = f'Cannot internalise "{string}" as "gloss" data')
    elif annotation_type == 'gloss' and operation == 'improve':
        for pair in data:
            for string in pair:
                try:
                    elements = string_to_list_of_content_elements(string, 'gloss')
                    for e in elements:
                        if e.type == 'Word' and not 'gloss' in e.annotations:
                            raise TemplateError(message = f'"{string}" is not good "gloss" "improve" data')
                except:
                    raise TemplateError(message = f'Cannot internalise "{string}" as "gloss" data')
    elif annotation_type == 'pinyin' and operation == 'improve':
        for pair in data:
            for string in pair:
                try:
                    elements = string_to_list_of_content_elements(string, 'pinyin')
                    for e in elements:
                        if e.type == 'Word' and not 'pinyin' in e.annotations:
                            raise TemplateError(message = f'"{string}" is not good "pinyin" "improve" data')
                except:
                    raise TemplateError(message = f'Cannot internalise "{string}" as "gloss" data')
    elif annotation_type == 'lemma' and operation == 'improve':
        for pair in data:
            for string in pair:
                try:
                    elements = string_to_list_of_content_elements(string, 'lemma')
                    for e in elements:
                        if e.type == 'Word' and ( not 'lemma' in e.annotations or not 'pos' in e.annotations ):
                            raise TemplateError(message = f'"{string}" is not good "lemma" "improve" data')
                except:
                    raise TemplateError(message = f'Cannot internalise "{string}" as "lemma" data')
    elif annotation_type == 'lemma_and_gloss' and operation == 'improve':
        for pair in data:
            for string in pair:
                try:
                    elements = string_to_list_of_content_elements(string, 'lemma_and_gloss')
                    for e in elements:
                        if e.type == 'Word' and ( not 'lemma' in e.annotations or not 'pos' in e.annotations or not 'gloss' in e.annotations ):
                            raise TemplateError(message = f'"{string}" is not good "lemma_and_gloss" "improve" data')
                except:
                    raise TemplateError(message = f'Cannot internalise "{string}" as "lemma_and_gloss" data')
    else:
        raise TemplateError(message = f'Cannot check well-formedness of "{data}" as "{annotation_type}" "{operation}" data')

# Check that the template and annotated example list were found,
# and that the template does not have any inappropriate arguments.
# If not, raise a TemplateError exception
def check_validity_of_template_and_annotated_example_list(template, annotated_example_list, annotation_type):
    if not annotated_example_list:
        raise TemplateError(message = 'Unable to find examples')
    check_validity_of_template(template, annotation_type)

def check_validity_of_template(template, annotation_type):
    if not template:
        raise TemplateError(message = 'Unable to find template')
    if annotation_type == 'segmented':
        try:
            result = template.format( l2_language='***l2_language***',
                                      examples='***examples***',
                                      text='***text***' )
            if not '***examples***' in result or not '***text***' in result:
                raise TemplateError(message = """Error in template.
Template must contain the substitution elements {examples} and {text}""")
        except:
            raise TemplateError(message = """Error in template.
Template may not contain any substitution elements except {l2_language}, {examples} and {text}""")
    elif annotation_type == 'lemma':
        try:
            result = template.format( l2_language='***l2_language***',
                                      examples='***examples***',
                                      simplified_elements_json='***simplified_elements_json***' )
            if not '***l2_language***' in result or not '***examples***' in result or not '***simplified_elements_json***' in result:
                raise TemplateError(message = """Error in template.
Template must contain the substitution elements {examples} and {simplified_elements_json}""")
        except Exception:
            raise TemplateError(message = """Error in template.
Template may not contain any substitution elements except {l2_language}, {examples} and {simplified_elements_json}""")
    else:
        try:
            result = template.format( l1_language='***l1_language***',
                                      l2_language='***l2_language***',
                                      examples='***examples***',
                                      simplified_elements_json='***simplified_elements_json***' )
            if not '***examples***' in result or not '***simplified_elements_json***' in result:
                raise TemplateError(message = """Error in template.
Template must contain the substitution elements {examples} and {simplified_elements_json}""")
        except:
            raise TemplateError(message = """Error in template.
Template may not contain any substitution elements except {l1_language}, {l2_language}, {examples} and {simplified_elements_json}""")        

def string_to_list_of_content_elements(string, annotation_type):
    ( l2_language, l1_language ) = ( 'irrelevant', 'irrelevant' )
    internalised = clara_internalise.internalize_text(string, l2_language, l1_language, annotation_type)
    return internalised.content_elements()

def is_list_of_n_tuples_of_strings(data, n):
    if not isinstance( data, ( list, tuple ) ):
        return False
    for elt in data:
        if not isinstance( elt, ( list, tuple ) ) or len(elt) != n:
            return False
        for e in elt:
            if not isinstance( e, str ):
                return False
    return True

def is_list_of_strings(data):
    if not isinstance( data, ( list, tuple ) ):
        return False
    for e in data:
        if not isinstance( e, str ):
            return False
    return True
