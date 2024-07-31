"""
Define the CLARAProjectInternal class. An object in this class collects together the data
required to build a multimodal C-LARA text out of a plain text, using ChatGPT to perform
text generation and annotation, and third-party resources like TTS engines to add
other information.

Each CLARAProjectInternal object is associated with a directory, which contains the various
text representations related to the object. These texts are kept as files since they
can be very large. We have seven types of text, as follows:

"prompt". The prompt, if there is one.
"plain". The initial unformatted text.
"segmented". Text with segmentation annotations added.
"summary". English summary of text.
"cefr_level". CEFR level of text (one of A1, A2, B1, B2, C1, C2).
"gloss". Text with segmentation annotations plus a gloss annotations for each word.
"lemma". Text with segmentation annotations plus a lemma annotation for each word.
"pinyin". Text with segmentation annotations plus a pinyin annotation for each word.
"lemma_and_gloss". Text with segmentation annotations plus a lemma, gloss and POS annotation for each word.
"mwe". Text with segmentation annotations plus a mwe annotation for each segment.

The main methods are the following:

- CLARAProjectInternal(id, l2_language, l1_language). Constructor. Creates necessary directories for
an initial empty project.

- from_directory(directory) [classmethod]. Creates a CLARAProjectInternal from its associated directory.

- copy_files_to_new_project(new_project) Copy relevant files from this project
to a newly created clone of it.

- save_text_version(version, text). Saves one of the associated texts. "version" is one
of ( "prompt", "plain", "summary", "cefr_level", "segmented", "gloss", "lemma", "lemma_and_gloss", "pinyin" ).

- delete_text_version(version). Deletes one of the associated texts. "version" is one
of ( "prompt", "plain", "summary", "cefr_level", "segmented", "gloss", "lemma", "lemma_and_gloss", "pinyin" ).

- delete_text_versions(versions). Deleted several associated texts. "version" is a list of strings
from ( "prompt", "plain", "summary", "cefr_level", "segmented", "gloss", "lemma", "lemma_and_gloss", "pinyin" ).

- load_text_version(version). Retrieves one of the associated texts. "version" is one
of ( "prompt", "plain", "summary", "cefr_level", "segmented", "gloss", "lemma", "lemma_and_gloss", "pinyin" ).

- delete(). Delete project's associated directory.

- get_metadata()
Returns list of metadata references for files holding different updates of text versions.
Metadata reference is dict with keys ( "file", "version", "source", "user", "timestamp", "gold_standard", "description" )
  - file: absolute pathname for file, as str
  - version: one of ( "prompt", "plain", "summary", "cefr_level", "segmented", "gloss", "lemma", "lemma_and_gloss", "pinyin" )
  - source: one of ( "ai_generated", "ai_revised", "human_revised" )
  - user: username for account on which file was created
  - timestamp: time when file was posted, in format '%Y%m%d%H%M%S'
  - gold_standard: whether or not file should be considered gold standard. One of ( True, False )
  - description: human-readable text describing the file

- get_file_description(version, file)
Returns the metadata "description" field for a file or "" if the file does not exist.
- version: one of ( "prompt", "plain", "summary", "cefr_level", "segmented", "gloss", "lemma", "lemma_and_gloss", "pinyin" )
- file: either the pathname for an archived file, or "current", referring to the most recent file of this type

- diff_editions_of_text_version(file_path1, file_path2, version, required. Diff two versions
of the same kind of file and return information as specified.
"version" is one of ( "prompt", "plain", "summary", "segmented", "gloss", "lemma", "lemma_and_gloss", "pinyin" ).
"required" is a list containing a subset of ( "error_rate", "details" )

- create_plain_text(prompt=None). Calls ChatGPT-4 to create the initial plain text in l2_language.
Returns a list of APICall instances related to the operation.

- improve_plain_text(). Calls ChatGPT-4 to try to improve current text in l2_language.
Returns a list of APICall instances related to the operation.

- create_summary(). Calls ChatGPT-4 to create a summary the "plain" version and saves the result
as the "summary" version.
Requires "plain" version to exist. Returns a list of APICall instances related to the operation.

- improve_summary(). Calls ChatGPT-4 to try to improve the "summary" version.
Requires "summary" version to exist. Returns a list of APICall instances related to the operation.

- get_cefr_level(). Calls ChatGPT-4 to estimate the CEFR level or uses a cached value, and returns
a tuple where the first element is a string representing the CEFR level,
and the second element is a list of APICall instances related to the operation.

- create_segmented_text(). Calls ChatGPT-4 to annotate the "plain" version with
segmentation annotations and saves the result as the "segmented" version.
Requires "plain" version to exist. Returns a list of APICall instances related to the operation.

- improve_segmented_text(). Calls ChatGPT-4 to try to improve the "segmented" version.
Requires "segmented" version to exist. Returns a list of APICall instances related to the operation.

- create_glossed_text(). Calls ChatGPT-4 to annotate the "segmented" version with
gloss annotations in l1_language and saves the result as the "gloss" version.
Requires "segmented" version to exist. Returns a list of APICall instances related to the operation.

- improve_glossed_text(). Calls ChatGPT-4 to try to improve the "glossed" version.
Requires "glossed" version to exist. Returns a list of APICall instances related to the operation.

- create_lemma_tagged_text_with_treetagger(). Calls TreeTagger to annotate the "segmented" version with
lemma annotations in l1_language and saves the result as the "lemma" version.
Requires "segmented" version to exist. Returns an empty list for consistency with create_lemma_tagged_text above.

- create_lemma_tagged_text(). Calls ChatGPT-4 to annotate the "segmented" version with
lemma annotations in l1_language and saves the result as the "lemma" version.
Requires "segmented" version to exist. Returns a list of APICall instances related to the operation.

- improve_lemma_tagged_text(). Calls ChatGPT-4 to try to improve the "lemma" version.
Requires "lemma" version to exist. Returns a list of APICall instances related to the operation.

- create_pinyin_tagged_text(). Calls ChatGPT-4 to annotate the "segmented" version with
pinyin annotations in l1_language and saves the result as the "pinyin" version.
Requires "segmented" version to exist. Returns a list of APICall instances related to the operation.

- improve_pinyin_tagged_text(). Calls ChatGPT-4 to try to improve the "pinyin" version.
Requires "pinyin" version to exist. Returns a list of APICall instances related to the operation.

- improve_lemma_and_gloss_tagged_text(). Calls ChatGPT-4 to try to improve the "lemma_and_gloss" version.
Requires "lemma" and "gloss" versions to exist. Returns a list of APICall instances related to the operation.

- get_internalised_and_annotated_text(). Returns a Text object, defined in clara_classes.py,
representing the text together with all annotations (segmentation, gloss, lemma, audio, concordance, pinyin if relevant).
TTS files are generated as needed.
Requires "gloss" and "lemma" versions to exist.

- render_text(project_id, self_contained=False). Render the text as an optionally self-contained directory
of HTML pages. "Self-contained" means that it includes all the multimedia files referenced.
Requires "gloss" and "lemma" versions to exist.

- get_word_count(). Get the word-count as a number, or 'Unknown' if the information is not available.

- get_voice(). Get the voice as a string, or 'Unknown' if the information is not available.
"""

from .clara_classes import *
from .clara_create_annotations import invoke_templates_on_trivial_text
from .clara_create_annotations import generate_glossed_version, generate_segmented_version, generate_tagged_version
from .clara_create_annotations import improve_glossed_version, improve_segmented_version, improve_tagged_version
from .clara_create_annotations import generate_pinyin_tagged_version, improve_pinyin_tagged_version
from .clara_create_annotations import improve_lemma_and_gloss_tagged_version, generate_mwe_tagged_version, generate_translated_version
from .clara_conventional_tagging import generate_tagged_version_with_treetagger, generate_tagged_version_with_trivial_tags
from .clara_create_story import generate_story, improve_story
from .clara_cefr import estimate_cefr_reading_level
from .clara_summary import generate_summary, improve_summary
from .clara_create_title import generate_title
from .clara_manual_audio_align import add_indices_to_segmented_text, annotated_segmented_data_and_label_file_data_to_metadata
from .clara_internalise import internalize_text
from .clara_correct_syntax import correct_syntax_in_string
from .clara_chinese import segment_text_using_jieba, pinyin_tag_text_using_pypinyin
from .clara_diff import diff_text_objects
from .clara_merge_glossed_and_tagged import merge_glossed_and_tagged, merge_glossed_and_tagged_with_pinyin, merge_with_translation_annotations
from .clara_audio_annotator import AudioAnnotator
from .clara_concordance_annotator import ConcordanceAnnotator
#from .clara_image_repository import ImageRepository
from .clara_image_repository_orm import ImageRepositoryORM
#from .clara_phonetic_lexicon_repository import PhoneticLexiconRepository
from .clara_phonetic_lexicon_repository_orm import PhoneticLexiconRepositoryORM
from .clara_renderer import StaticHTMLRenderer
from .clara_annotated_images import add_image_to_text
from .clara_phonetic_text import segmented_text_to_phonetic_text
from .clara_acknowledgements import add_acknowledgements_to_text_object
from .clara_export_import import create_export_zipfile, change_project_id_in_imported_directory, update_multimedia_from_imported_directory
from .clara_export_import import get_global_metadata, rename_files_in_project_dir, update_metadata_file_paths
#from .clara_utils import _use_orm_repositories
from .clara_utils import absolute_file_name, absolute_local_file_name
from .clara_utils import read_json_file, write_json_to_file, read_txt_file, write_txt_file, read_local_txt_file, robust_read_local_txt_file
from .clara_utils import rename_file, remove_file, get_file_time, file_exists, local_file_exists, basename, output_dir_for_project_id
from .clara_utils import make_directory, remove_directory, directory_exists, copy_directory, list_files_in_directory
from .clara_utils import local_directory_exists, remove_local_directory
from .clara_utils import get_config, make_line_breaks_canonical_n, make_line_breaks_canonical_linesep, format_timestamp, get_file_time
from .clara_utils import unzip_file, post_task_update, convert_to_timezone_aware

from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union

import re
import datetime
import logging
import pprint
import traceback
import tempfile
import pickle

config = get_config()

class CLARAProjectInternal:
    BASE_DIR = Path(absolute_file_name(config.get('CLARA_projects', 'project_dir')))

    def __init__(self, id: str, l2_language: str, l1_language: str) -> None: 
        self.id = id
        self.l2_language = l2_language
        self.l1_language = l1_language
        self.cefr_level = None
        self.project_dir = self.BASE_DIR / self.id
        self.text_versions = {
            "prompt": None,
            "plain": None,
            "title": None,
            "segmented_title": None,
            "summary": None,
            "cefr_level": None,
            "segmented": None,
            "segmented_with_images": None,
            "translated": None,
            "phonetic": None,
            "gloss": None,
            "lemma": None,
            "lemma_and_gloss": None,
            "pinyin": None,
            "mwe": None,
            "image_request_sequence": None
        }
        self.internalised_and_annotated_text_path = self.project_dir / 'internalised_and_annotated_text.pickle'
        self.internalised_and_annotated_text_path_phonetic = self.project_dir / 'internalised_and_annotated_text_phonetic.pickle'
        self.image_repository = ImageRepositoryORM()
        #self.image_repository = ImageRepositoryORM() if _use_orm_repositories else ImageRepository()
        self._ensure_directories()
        self._store_information_in_dir()
        self._load_existing_text_versions()

    def get_internalised_and_annotated_text_path(self, phonetic=False):
        if not phonetic:
            return self.internalised_and_annotated_text_path
        else:
            return self.internalised_and_annotated_text_path_phonetic

    def _ensure_directories(self) -> None:
        make_directory(self.project_dir, parents=True, exist_ok=True)
        for version in self.text_versions:
            make_directory(self.project_dir / version, exist_ok=True)

    # Save information in a file so we can reconstitute a CLARAProjectInternal object
    # from its associated directory
    def _store_information_in_dir(self)-> None:
        stored_file = str(self.project_dir / 'stored_data.json')
        stored_data = { 'id': self.id,
                        'l2_language': self.l2_language,
                        'l1_language': self.l1_language
                        }
        write_json_to_file(stored_data, stored_file)

    # Delete the project. We remove its directory to clean things up.
    def delete(self):
        if directory_exists(self.project_dir):
            remove_directory(self.project_dir)

    # Reconstitute a CLARAProjectInternal from its associated directory
    @classmethod
    def from_directory(cls, directory: str) -> 'CLARAProjectInternal':
        directory = Path(absolute_file_name(directory))
        stored_data = cls._load_stored_data(directory)
        abs_existing_dir = absolute_file_name(str(directory))
        abs_new_dir = absolute_file_name(str(cls.BASE_DIR / stored_data['id']))
        # If the directory is not in the canonical place, copy it there
        if abs_existing_dir != abs_new_dir:
            copy_directory(abs_existing_dir, abs_new_dir)
        project = cls(stored_data['id'], stored_data['l2_language'], stored_data['l1_language'])
        project._load_existing_text_versions()
        return project

    # Reconstitute a CLARAProjectInternal from an export zipfile
    @classmethod
    def create_CLARAProjectInternal_from_zipfile(cls, zipfile: str, new_id: str, callback=None) -> 'CLARAProjectInternal':
        try:
            tmp_dir = tempfile.mkdtemp()
            unzip_file(zipfile, tmp_dir)
            post_task_update(callback, '--- Unzipped import file')
            change_project_id_in_imported_directory(tmp_dir, new_id)
            tmp_project_dir = os.path.join(tmp_dir, 'project_dir')
            rename_files_in_project_dir(tmp_project_dir, new_id)
            project = cls.from_directory(tmp_project_dir)
            update_metadata_file_paths(project, project.project_dir, callback=callback)
            update_multimedia_from_imported_directory(project, tmp_dir, callback=callback)
            global_metadata = get_global_metadata(tmp_dir)
            return ( project, global_metadata )
        except Exception as e:
            post_task_update(callback, f'*** Error when trying to import zipfile {zipfile}')
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            return ( None, None )
        finally:
            # Remove the tmp dir once we've used it
            if local_directory_exists(tmp_dir):
                remove_local_directory(tmp_dir)
            
    # If there are already files in the associated directory, update self.text_versions
    def _load_existing_text_versions(self) -> None:
        for version in self.text_versions:
            file_path = self._file_path_for_version(version)
            if file_exists(file_path):
                self.text_versions[version] = str(file_path)

    # Copy relevant files from this project to a newly created clone of it.
    def copy_files_to_new_project(self, new_project: 'CLARAProjectInternal') -> None:
        # Always copy the prompt and plain text file if available.
        # Even not directly useable, we may want to transform them in some way
        self._copy_text_version_if_it_exists("prompt", new_project)
        self._copy_text_version_if_it_exists("plain", new_project)
        # If the L2 is the same, the title CEFR, summary, segmented, lemma and pinyin files will by default be valid
        if self.l2_language == new_project.l2_language:
            self._copy_text_version_if_it_exists("title", new_project)
            self._copy_text_version_if_it_exists("segmented_title", new_project)
            self._copy_text_version_if_it_exists("cefr_level", new_project)
            self._copy_text_version_if_it_exists("summary", new_project)
            self._copy_text_version_if_it_exists("segmented", new_project)
            self._copy_text_version_if_it_exists("translated", new_project)
            self._copy_text_version_if_it_exists("phonetic", new_project)
            self._copy_text_version_if_it_exists("lemma", new_project)
            self._copy_text_version_if_it_exists("mwe", new_project)
            self._copy_text_version_if_it_exists("pinyin", new_project)
            self._copy_text_version_if_it_exists("image_request_sequence", new_project)
        # If the L1 is the same, the gloss file will by default be valid
        if self.l1_language == new_project.l1_language:
            self._copy_text_version_if_it_exists("gloss", new_project)
        # Copy over any images we may have (it's possible we will choose to delete them later)
        images = self.get_all_project_images()
        if images:
            new_project.copy_image_objects_to_project(images)
        image_descriptions = self.get_all_project_image_descriptions()
        if image_descriptions:
            new_project.copy_image_description_objects_to_project(image_descriptions)

    # Copy a text version to another project if it exists
    def _copy_text_version_if_it_exists(self, version: str, other_project: 'CLARAProjectInternal') -> None:
        try:
            text = self.load_text_version(version)
            other_project.save_text_version(version, text)
        except FileNotFoundError:
            return
        except Exception as e:
            # Here we log the unexpected exception.
            logging.error(f"Unexpected error in _copy_text_version_if_it_exists: {e}")
            raise 

    @staticmethod
    def _load_stored_data(directory: Path) -> Dict[str, str]:
        stored_data_file = directory / 'stored_data.json'
        if not file_exists(stored_data_file):
            raise FileNotFoundError(f"{stored_data_file} not found.")
        stored_data = read_json_file(str(stored_data_file))
        return stored_data

    def _file_path_for_version(self, version: str) -> Path:
        return self.project_dir / version / f"{self.id}_{version}.txt"

    # Save one of the text files associated with the object.
    # If necessary archive the old one.
    # Update the metadata file, first creating it if it doesn't exist.
    def save_text_version(self, version: str, text: str, source='human_revised', user='Unknown', label='', gold_standard=False) -> None:
        file_path = self._file_path_for_version(version)

        # For downward compatibility, guess metadata for existing files if necessary, assuming they were created by this user.
        self._create_metadata_file_if_missing(user)
        
        # Archive the old version, if it exists
        if file_exists(file_path):
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            archive_dir = self._get_archive_dir()
            make_directory(archive_dir, parents=True, exist_ok=True)
            archive_path = archive_dir / f'{version}_{timestamp}.txt'
            rename_file(file_path, archive_path)
        else:
            archive_path = None

        # Save the new version
        text = make_line_breaks_canonical_n(text)
        write_txt_file(text, file_path)

        # Update the metadata file, transferring the entry for 'file_path' to 'archive_path' and creating a new entry for 'file_path'
        self._update_metadata_file(file_path, archive_path, version, source, user, label, gold_standard)
        
        self.text_versions[version] = str(file_path)

    def get_file_description(self, version, file):
        metadata = self.get_metadata()
        relevant_metadata = [ item for item in metadata if item['version'] == version ]
        if relevant_metadata == []:
            result = ""
        elif file == 'current':
            result = relevant_metadata[-1]['description']
        else:
            metadata_for_file = [ item for item in metadata if item['file'] == file ]
            if metadata_for_file == []:
                result = ""
            else:
                result = metadata_for_file[0]['description']
        return result

    def get_metadata(self):
        metadata_file = self._get_metadata_file()
        if not file_exists(metadata_file):
            return []
        else:
            metadata = read_json_file(metadata_file)
            for item in metadata:
                provenance = item['source'] if item['source'] != "human_revised" else item['source']
                timestamp = format_timestamp(item['timestamp'])
                gold_standard = ' (gold standard)' if item['gold_standard'] else ''
                label = f' {item["label"]} ' if 'label' in item and item["label"] else ''
                item['description'] = f'{provenance} {timestamp}{label}{gold_standard}'
            return metadata

    def _get_metadata_file(self):
        return self.project_dir / 'metadata.json'

    def _get_archive_dir(self):
        return self.project_dir / 'archive'

    # Metadata file is JSON list of metadata references.
    # Metadata reference is dict with keys ( "file", "version", "source", "user", "timestamp", "gold_standard" )
    #
    #   - file: absolute pathname for file, as str
    #   - version: one of ( "prompt", "plain", "segmented_title", "title", "summary", "cefr_level", "segmented", "gloss", "lemma", "pinyin" )
    #   - source: one of ( "ai_generated", "ai_revised", "human_revised" )
    #   - user: username for account on which file was created
    #   - timestamp: time when file was posted, in format '%Y%m%d%H%M%S'
    #   - whether or not file should be considered gold standard. One of ( True, False )

    # For downward compatibility, guess metadata based on existing files where necessary.
    # Files referenced:
    #   - self._file_path_for_version(version) for version in
    #     ( "prompt", "plain", "segmented_title", "title", "summary", "cefr_level", "segmented", "gloss", "lemma", "pinyin" )
    #     when file exists
    #   - Everything in self._get_archive_dir()
    # Get timestamps from the file ages.
    # Assume they were created by the specified user.
    # Assume that earliest file for a given version is source=ai_generated and others are source=human_revised.
    # Assume that all files are gold_standard=False
    def _create_metadata_file_if_missing(self, user):
        metadata_file = self._get_metadata_file()
        metadata = self.get_metadata()

        versions = ["prompt", "plain", "title", "segmented_title", "summary", "cefr_level", "segmented", "translated", "phonetic", "gloss", "lemma",
                    "pinyin", "mwe", "image_request_sequence"]

        # Check if any metadata entries are missing for the existing files
        for version in versions:
            file_path = self._file_path_for_version(version)
            if file_exists(file_path):
                # Check if metadata entry exists for the file
                if not any(entry['file'] == str(file_path) for entry in metadata):
                    # Assume the earliest file is source=ai_generated and the rest are source=human_revised
                    source = "ai_generated" if version == versions[0] else "human_revised"
                    entry = {
                        "file": str(file_path),
                        "version": version,
                        "source": source,
                        "user": user,
                        # Use file modification timestamp as the timestamp and convert to the right format
                        "timestamp": datetime.datetime.fromtimestamp(get_file_time(file_path)).strftime('%Y%m%d%H%M%S'),
                        "gold_standard": False
                    }
                    metadata.append(entry)

        # Process the files in the archive directory
        archive_dir = self._get_archive_dir()
        if directory_exists(archive_dir):
            for filename in list_files_in_directory(archive_dir):
                file_path = archive_dir / filename
                if not any(entry['file'] == str(file_path) for entry in metadata):
                    # Extract version and timestamp from the filename
                    version, timestamp = filename.split("_", 1)
                    source = "human_revised"
                    entry = {
                        "file": str(file_path),
                        "version": version,
                        "source": source,
                        "user": user,
                        "timestamp": timestamp[:-4],  # Remove the file extension
                        "gold_standard": False
                    }
                    metadata.append(entry)

        # Sort the metadata entries by timestamp
        metadata.sort(key=lambda entry: entry['timestamp'])

        # Assign source=ai_generated to the earliest file for each version
        versions_processed = set()
        for entry in metadata:
            version = entry['version']
            if version not in versions_processed:
                entry['source'] = 'ai_generated'
                versions_processed.add(version)

        # Write the updated metadata to the file
        write_json_to_file(metadata, metadata_file)

    # Update the metadata file, transferring the entry for 'file_path' to 'archive_path' and creating a new entry for 'file_path'
    def _update_metadata_file(self, file_path, archive_path, version, source, user, label, gold_standard):
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
            "version": version,
            "source": source,
            "user": user,
            # Use file modification timestamp as the timestamp and convert to the right format
            "timestamp": datetime.datetime.fromtimestamp(get_file_time(file_path)).strftime('%Y%m%d%H%M%S'),
            "label": label,
            "gold_standard": gold_standard
        }
        metadata.append(new_entry)

        # Write the updated metadata to the file
        write_json_to_file(metadata, metadata_file)

    # Delete one of the text files associated with the object
    def delete_text_version(self, version: str) -> None:
        if self.text_versions[version] == None:
            return
        
        file_path = self._file_path_for_version(version)

        # Check if the file exists before deleting it
        if file_exists(file_path):
            remove_file(file_path)

        # Remove the version from the text_versions dictionary
        self.text_versions[version] = None

    # Delete several text files associated with the object
    def delete_text_versions(self, versions: List[str]) -> None:
        for version in versions:
            self.delete_text_version(version)

    # Read one of the text files associated with the object
    def load_text_version(self, version: str) -> str:
        if version == 'segmented_with_images':
            return self._create_and_load_segmented_with_images_text()
        elif version == 'segmented_with_title':
            return self._create_and_load_segmented_with_title_text()
        elif version == 'segmented_with_title_for_labelled':
            return self._create_and_load_segmented_with_title_for_labelled_text()
        elif version == 'lemma_and_gloss':
                return self._create_and_load_lemma_and_gloss_file()
        else:
            file_path = self.text_versions[version]
            if not file_path or not file_exists(Path(file_path)):
                raise FileNotFoundError(f"'{version}' text not found.")
            text = read_txt_file(file_path)
            text = make_line_breaks_canonical_n(text)
            return text

    def load_text_version_or_null(self, version: str) -> str:
        try:
            return self.load_text_version(version)
        except FileNotFoundError:
            return ''

    # Get text consisting of "segmented" text, plus segmented title if available, plus suitably tagged segmented text for any images that may be present
    def _create_and_load_segmented_with_images_text(self, callback=None):
        segmented_text = self.load_text_version("segmented")
        images_text = self.image_repository.get_annotated_image_text(self.id, callback=callback)
        segmented_with_images_text = segmented_text + '\n' + images_text
        text_title = self.load_text_version_or_null("segmented_title")
        if text_title != '':
            # We need to put segment breaks around the text_title to get the right interaction with segment audio
            segmented_with_images_text = f'<h1>||{text_title}||</h1><page>\n' + segmented_with_images_text
        return segmented_with_images_text

    # Get text consisting of "segmented" text, plus segmented title if available
    def _create_and_load_segmented_with_title_text(self):
        segmented_text = self.load_text_version("segmented")
        text_title = self.load_text_version_or_null("segmented_title")
        if text_title != '':
            # We need to put segment breaks around the text_title to get the right interaction with segment audio
            segmented_with_title_text = f'<h1>||{text_title}||</h1><page>\n' + segmented_text
        else:
            segmented_with_title_text = segmented_text
        return segmented_with_title_text

    def _create_and_load_segmented_with_title_for_labelled_text(self):
        segmented_with_title_text = self._create_and_load_segmented_with_title_text()
        text_object = internalize_text(segmented_with_title_text, self.l2_language, self.l1_language, 'segmented')
        return text_object.to_text(annotation_type='segmented_for_labelled')

    # The "lemma_and_gloss" version is initially a merge of the "lemma" and "gloss" versions
    def _create_and_load_lemma_and_gloss_file(self) -> str:
        internalised_lemma_and_gloss_text = self.get_internalised_text()
        lemma_and_gloss_text = internalised_lemma_and_gloss_text.to_text(annotation_type='lemma_and_gloss')
        self.save_text_version('lemma_and_gloss', lemma_and_gloss_text, source='merged', user='system')
        return lemma_and_gloss_text

    # Diff two versions of the same kind of file and return information as specified
    def diff_editions_of_text_version(self, file_path1: str, file_path2: str, version: str, required: List[str]) -> Dict[str, Union[str, float]]:
        text1 = read_txt_file(file_path1)
        text1 = make_line_breaks_canonical_n(text1)
        internalised_text1 = internalize_text(text1, self.l2_language, self.l1_language, version)
        
        text2 = read_txt_file(file_path2)
        text2 = make_line_breaks_canonical_n(text2)
        internalised_text2 = internalize_text(text2, self.l2_language, self.l1_language, version)

        return diff_text_objects(internalised_text1, internalised_text2, version, required)

    # Create a prompt using null text to see if there is a template error
    def try_to_use_templates(self, generate_or_improve, version):
        return invoke_templates_on_trivial_text(generate_or_improve, version, self.l1_language, self.l2_language)

    # Try to correct syntax in text and save if successful
    def correct_syntax_and_save(self, text, version, user='Unknown', label='', config_info={}, callback=None):
        corrected_text, api_calls = correct_syntax_in_string(text, version, self.l2_language, l1=self.l1_language,
                                                             config_info=config_info, callback=callback)
        self.save_text_version(version, corrected_text, user=user, label=label, source='ai_corrected')
        return api_calls
        
    # Call ChatGPT-4 to create a story based on the given prompt
    def create_plain_text(self, prompt: Optional[str] = None, user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
        plain_text, api_calls = generate_story(self.l2_language, prompt, config_info=config_info, callback=callback)
        self.save_text_version('prompt', prompt if prompt else '', user=user, label=label, source='human_input')
        self.save_text_version('plain', plain_text, user=user, label=label, source='ai_generated')
        return api_calls

    # Call ChatGPT-4 to try to improve a text
    def improve_plain_text(self, prompt='', user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
        try:
            stored_prompt = self.load_text_version("prompt")
            current_version = self.load_text_version("plain")
            improvement_prompt = prompt if prompt and prompt != stored_prompt else None
            plain_text, api_calls = improve_story(self.l2_language, current_version, improvement_prompt=improvement_prompt, config_info=config_info, callback=callback)
            self.save_text_version("plain", plain_text, user=user, label=label, source='ai_revised')
            return api_calls
        except:
            return []

    # Call ChatGPT-4 to create a title for the text
    def create_title(self, user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
        try:
            plain_text = self.load_text_version("plain")
            title, api_calls = generate_title(plain_text, self.l2_language, config_info=config_info, callback=callback)
            self.save_text_version("title", title, user=user, label=label, source='ai_generated')
            return api_calls
        except:
            return []

    # Call ChatGPT-4 to try to improve the title for the text
    def improve_title(self, user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
        try:
            plain_text = self.load_text_version("plain")
            old_title = self.load_text_version("title")
            title, api_calls = improve_title(plain_text, old_title, self.l2_language, config_info=config_info, callback=callback)
            self.save_text_version("title", title, user=user, label=label, source='ai_revised')
            return api_calls
        except:
            return []

    # Call ChatGPT-4 to create a short summary of the text
    def create_summary(self, user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
        try:
            plain_text = self.load_text_version("plain")
            summary_text, api_calls = generate_summary(plain_text, self.l2_language, config_info=config_info, callback=callback)
            self.save_text_version("summary", summary_text, user=user, label=label, source='ai_generated')
            return api_calls
        except:
            return []

    # Call ChatGPT-4 to try to improve the summary of the text
    def improve_summary(self, user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
        try:
            plain_text = self.load_text_version("plain")
            old_summary_text = self.load_text_version("summary")
            summary_text, api_calls = improve_summary(plain_text, old_summary_text, self.l2_language, config_info=config_info, callback=callback)
            self.save_text_version("summary", summary_text, user=user, label=label, source='ai_revised')
            return api_calls
        except:
            return []

    # Call ChatGPT-4 to estimate the reading level or use the cached version
    def get_cefr_level(self, user='Unknown', label='', config_info={}, callback=None)-> Tuple[Union[str, None], List[APICall]]:
        if self.cefr_level:
            return []
        try:
            plain_text = self.load_text_version("plain")
            cefr_level, api_calls = estimate_cefr_reading_level(plain_text, self.l2_language, config_info=config_info, callback=callback)
            self.save_text_version("cefr_level", cefr_level, user=user, label=label, source='ai_generated')
            return api_calls
        except:
            return []

    # Call ChatGPT-4 to create versions of the text and title (if available) with segmentation annotations
    def create_segmented_text(self, user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
        plain_text = self.load_text_version("plain")
        segmented_text, api_calls = generate_segmented_version(plain_text, self.l2_language, config_info=config_info, callback=callback)
        self.save_text_version("segmented", segmented_text, user=user, label=label, source='ai_generated')

        # If we have a title, which is a separate piece of text, segment that too and save it as "segmented_title"
        title_api_calls = self.create_segmented_title(user=user, label=label, config_info=config_info, callback=callback)
        api_calls += title_api_calls
            
        return api_calls

    # Call ChatGPT-4 to create version of the title (if available) with segmentation annotations
    def create_segmented_title(self, user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
        title_text = self.load_text_version_or_null("title")
        if title_text:
            all_api_calls = []
            n_tries = 0
            max_tries = 5
            while n_tries < max_tries:
                try:
                    segmented_title_text, api_calls = generate_segmented_version(title_text, self.l2_language,
                                                                                 config_info=config_info, callback=callback)
                    all_api_calls += api_calls
                    # We want the title to be a single segment
                    segmented_title_text_cleaned = segmented_title_text.replace('<page>', '').replace('||', '').strip()
                    # Check for gross differences in length between segmented and original title text.
                    # Sometimes the AI adds a lot of material for no obvious reason
                    segmented_title_text_cleaned_plain = segmented_title_text_cleaned.replace('|', '')
                    if abs(len(segmented_title_text_cleaned_plain) - len(title_text)) > 10:
                        print(f'Error: segmented title length: {len(segmented_title_text_cleaned_plain)} chars; original title length: {len(title_text)} chars')
                        raise ValueError("Bad segmented title")
                    self.save_text_version("segmented_title", segmented_title_text_cleaned, user=user,
                                           label=label, source='ai_generated')
                    return all_api_calls
                except Exception as e:
                    n_tries += 1
            # We tried several times, but nothing worked
            return []
        else:
            return []

    # Call Jieba to create a version of the text with segmentation annotations
    def create_segmented_text_using_jieba(self, user='Unknown', label='') -> List[APICall]:
        plain_text = self.load_text_version("plain")
        segmented_text = segment_text_using_jieba(plain_text)
        self.save_text_version("segmented", segmented_text, user=user, label=label, source='jieba_generated')
        api_calls = []
        return api_calls

    # Get "labelled segmented" version of text, used for manual audio/text alignment
    def get_labelled_segmented_text(self) -> str:
        segmented_text = self.load_text_version("segmented_with_title_for_labelled")
        return add_indices_to_segmented_text(segmented_text)

    # Call ChatGPT-4 to improve existing segmentation annotations
##    def improve_segmented_text(self, user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
##        segmented_text = self.load_text_version("segmented")
##        new_segmented_text, api_calls = improve_segmented_version(segmented_text, self.l2_language, config_info=config_info, callback=callback)
##        self.save_text_version("segmented", new_segmented_text, user=user, label=label, source='ai_revised')
##        return api_calls

    def improve_segmented_text(self, user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
        segmented_text = self.load_text_version("segmented")
        new_segmented_text, api_calls = improve_morphology_in_segmented_version(segmented_text, self.l2_language, config_info=config_info, callback=callback)
        self.save_text_version("segmented", new_segmented_text, user=user, label=label, source='ai_revised')
        return api_calls

    # Call ChatGPT-4 to create version of the text with translation annotations
    def create_translated_text(self, user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
        segmented_text = self.load_text_version("segmented_with_images")
        translated_text, api_calls = generate_translated_version(segmented_text, self.l2_language, self.l1_language,
                                                                 config_info=config_info, callback=callback)
        self.save_text_version("translated", translated_text, user=user, label=label, source='ai_generated')
            
        return api_calls

    # Create a "phonetic" version of the text 
    def create_phonetic_text(self, user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
        segmented_text = self.load_text_version("segmented_with_images")
        #print(f'--- Input to create_phonetic_text: "{segmented_text}"')
        
        phonetic_text_result = segmented_text_to_phonetic_text(segmented_text, self.l2_language, config_info=config_info, callback=callback)
        phonetic_text = phonetic_text_result['text']
        guessed_plain_entries = phonetic_text_result['guessed_plain_entries']
        guessed_aligned_entries = phonetic_text_result['guessed_aligned_entries']
        api_calls = phonetic_text_result['api_calls']
        
        self.save_text_version("phonetic", phonetic_text, user=user, label=label, source='generated')
        repository = PhoneticLexiconRepositoryORM(callback=callback)
        #repository = PhoneticLexiconRepositoryORM(callback=callback) if _use_orm_repositories else PhoneticLexiconRepository(callback=callback)
        repository.record_guessed_plain_entries(guessed_plain_entries, self.l2_language, callback=callback)
        repository.record_guessed_aligned_entries(guessed_aligned_entries, self.l2_language, callback=callback)
        return api_calls

    # Call ChatGPT-4 to create a version of the text with gloss annotations
    def create_glossed_text(self, previous_version='segmented_with_images',
                            user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
        print(f'create_glossed_text(previous_version={previous_version})')
        if previous_version == 'lemma':
            segmented_text = self.load_text_version("lemma")
            mwe = False
        elif self.text_versions['mwe']:
            segmented_text = self.load_text_version("mwe")
            mwe = True
        else:
            segmented_text = self.load_text_version("segmented_with_images")
            mwe = False
        current_glossed_text = self.load_text_version("gloss") if self.text_versions['gloss'] else None
        current_translated_text = self.load_text_version("translated") if self.text_versions['translated'] else None 
        glossed_text, api_calls = generate_glossed_version(segmented_text, self.l1_language, self.l2_language,
                                                           previous_version=previous_version, mwe=mwe,
                                                           current_glossed_text=current_glossed_text,
                                                           current_translated_text=current_translated_text,
                                                           config_info=config_info, callback=callback)
        self.save_text_version("gloss", glossed_text, user=user, label=label, source='ai_generated')
        return api_calls

    # Call ChatGPT-4 to improve existing gloss annotations
    def improve_glossed_text(self, user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
        glossed_text = self.load_text_version("gloss")
        new_glossed_text, api_calls = improve_glossed_version(glossed_text, self.l1_language, self.l2_language,
                                                              config_info=config_info, callback=callback)
        self.save_text_version("gloss", new_glossed_text, user=user, label=label, source='ai_revised')
        return api_calls

    # Call Treetagger to create a version of the text with lemma annotations
    def create_lemma_tagged_text_with_treetagger(self, user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
        segmented_text = self.load_text_version("segmented_with_images")
        print(f'--- Calling generate_tagged_version_with_treetagger')
        lemma_tagged_text = generate_tagged_version_with_treetagger(segmented_text, self.l2_language)
        print(f'--- Result = {lemma_tagged_text}')
        self.save_text_version("lemma", lemma_tagged_text, user=user, label=label, source='tagger_generated')
        api_calls = []
        return api_calls

    # Create a version where each word is tagged with its surface form
    def create_lemma_tagged_text_with_trivial_tags(self, user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
        segmented_text = self.load_text_version("segmented_with_images")
        lemma_tagged_text = generate_tagged_version_with_trivial_tags(segmented_text)
        self.save_text_version("lemma", lemma_tagged_text, user=user, label=label, source='trivial')
        api_calls = []
        return api_calls

    # Call ChatGPT-4 to create a version of the text with lemma annotations
    def create_lemma_tagged_text(self, user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
        if self.text_versions['mwe']:
            segmented_text = self.load_text_version("mwe")
            mwe = True
        else:
            segmented_text = self.load_text_version("segmented_with_images")
            mwe = False

        current_lemma_tagged_text = self.load_text_version("lemma") if self.text_versions['lemma'] else None 
        lemma_tagged_text, api_calls = generate_tagged_version(segmented_text, self.l2_language,
                                                               mwe=mwe,
                                                               current_lemma_tagged_text=current_lemma_tagged_text,
                                                               config_info=config_info, callback=callback)
        self.save_text_version("lemma", lemma_tagged_text, user=user, label=label, source='ai_generated')
        return api_calls

    # Call ChatGPT-4 to improve existing lemma annotations
    def improve_lemma_tagged_text(self, user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
        lemma_tagged_text = self.load_text_version("lemma")
        new_lemma_tagged_text, api_calls = improve_tagged_version(lemma_tagged_text, self.l2_language,
                                                                  config_info=config_info, callback=callback)
        self.save_text_version("lemma", new_lemma_tagged_text, user=user, label=label, source='ai_revised')
        return api_calls

    # Call ChatGPT-4 to create a version of the text with MWE annotations
    def create_mwe_tagged_text(self, user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
        segmented_text = self.load_text_version("segmented_with_images")
        current_mwe_tagged_text = self.load_text_version("mwe") if self.text_versions['mwe'] else None 
        mwe_tagged_text, api_calls = generate_mwe_tagged_version(segmented_text, self.l2_language,
                                                                 current_mwe_tagged_text=current_mwe_tagged_text,
                                                                 config_info=config_info, callback=callback)
        self.save_text_version("mwe", mwe_tagged_text, user=user, label=label, source='ai_generated')
        return api_calls

     # Call pypinyin to create a version of the text with pinyin annotations
    def create_pinyin_tagged_text_using_pypinyin(self, user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
        segmented_text = self.load_text_version("segmented_with_images")
        pinyin_tagged_text = pinyin_tag_text_using_pypinyin(segmented_text)
        self.save_text_version("pinyin", pinyin_tagged_text, user=user, label=label, source='ai_generated')
        api_calls = []
        return api_calls

    # Call ChatGPT-4 to create a version of the text with pinyin annotations
    def create_pinyin_tagged_text(self, user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
        segmented_text = self.load_text_version("segmented_with_images")
        pinyin_tagged_text, api_calls = generate_pinyin_tagged_version(segmented_text, self.l2_language,
                                                                       config_info=config_info, callback=callback)
        self.save_text_version("pinyin", pinyin_tagged_text, user=user, label=label, source='ai_generated')
        return api_calls

    # Call ChatGPT-4 to improve existing pinyin annotations
    def improve_pinyin_tagged_text(self, user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
        pinyin_tagged_text = self.load_text_version("pinyin")
        new_pinyin_tagged_text, api_calls = improve_pinyin_tagged_version(pinyin_tagged_text, self.l2_language,
                                                                          config_info=config_info, callback=callback)
        self.save_text_version("pinyin", new_pinyin_tagged_text, user=user, label=label, source='ai_revised')
        return api_calls

    # Call ChatGPT-4 to improve existing lemma_and_gloss annotations
    def improve_lemma_and_gloss_tagged_text(self, user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
        lemma_and_gloss_tagged_text = self.load_text_version("lemma_and_gloss")
        new_lemma_and_gloss_tagged_text, api_calls = improve_lemma_and_gloss_tagged_version(lemma_and_gloss_tagged_text, self.l1_language, self.l2_language,
                                                                                            config_info=config_info, callback=callback)
        self.save_text_version("lemma_and_gloss", new_lemma_and_gloss_tagged_text, user=user, label=label, source='ai_revised')
        return api_calls

    # Do any ChatGPT-4 annotation that hasn't already been done
##    def do_all_chatgpt4_annotation(self) -> List[APICall]:
##        all_api_calls = []
##        if not self.text_versions['segmented']:
##            all_api_calls += self.create_segmented_text()
##        if not self.text_versions['gloss']:
##            all_api_calls += self.create_glossed_text()
##        if not self.text_versions['lemma']:
##            all_api_calls += self.create_lemma_tagged_text()
##        return all_api_calls

    # Create an internalised version of the text including gloss and lemma annotations 
    # Requires 'gloss' and 'lemma' texts
    # If we are processing phonetic text, we just internalise that.
    def get_internalised_text(self, phonetic=False) -> str:
        if phonetic:
            if not self.text_versions["phonetic"]:
                return None
            phonetic_text = self.load_text_version("phonetic")
            internalised_phonetic_text = internalize_text(phonetic_text, self.l2_language, self.l1_language, 'phonetic')
            return internalised_phonetic_text
        else:
            if not self.text_versions["gloss"] or not self.text_versions["lemma"]:
                return None
            glossed_text = self.load_text_version("gloss")
            lemma_tagged_text = self.load_text_version("lemma")
            internalised_glossed_text = internalize_text(glossed_text, self.l2_language, self.l1_language, 'gloss')
            internalised_tagged_text = internalize_text(lemma_tagged_text, self.l2_language, self.l1_language, 'lemma')
            merged_text = merge_glossed_and_tagged(internalised_glossed_text, internalised_tagged_text)
            if self.text_versions["pinyin"]:
                pinyin_tagged_text = self.load_text_version("pinyin")
                internalised_pinyin_text = internalize_text(pinyin_tagged_text, self.l2_language, self.l1_language, 'pinyin')
                merged_text_with_pinyin = merge_glossed_and_tagged_with_pinyin(merged_text, internalised_pinyin_text)
                merged_text = merged_text_with_pinyin
            if self.text_versions["translated"]:
                translated_tagged_text = self.load_text_version("translated")
                internalised_translated_text = internalize_text(translated_tagged_text, self.l2_language, self.l1_language, 'translated')
                merged_text_with_translations = merge_with_translation_annotations(merged_text, internalised_translated_text)
                merged_text = merged_text_with_translations
            
            return merged_text

    # Create an internalised version of the text including gloss, lemma, audio and concordance annotations
    # Requires 'gloss' and 'lemma' texts.
    def get_internalised_and_annotated_text(self,
                                            title=None,
                                            human_voice_id=None,
                                            audio_type_for_words='tts', audio_type_for_segments='tts',
                                            preferred_tts_engine=None, preferred_tts_voice=None,
                                            acknowledgements_info=None,
                                            phonetic=False, callback=None) -> str:
        post_task_update(callback, f"--- Creating internalised text")
        text_object = self.get_internalised_text(phonetic=phonetic) 
        post_task_update(callback, f"--- Internalised text created")
        if not text_object:
            return None

        if title:
            for page in text_object.pages:
                page.annotations['title'] = title
        
        post_task_update(callback, f"--- Adding audio annotations")
        audio_annotator = AudioAnnotator(self.l2_language, 
                                         human_voice_id=human_voice_id,
                                         audio_type_for_words=audio_type_for_words, audio_type_for_segments=audio_type_for_segments,
                                         preferred_tts_engine=preferred_tts_engine, preferred_tts_voice=preferred_tts_voice,
                                         phonetic=phonetic, callback=callback)
        audio_annotator.annotate_text(text_object, phonetic=phonetic, callback=callback)
        post_task_update(callback, f"--- Audio annotations done")

        # Add acknowledgements after audio annotation, because we don't want audio on them
        if acknowledgements_info:
            add_acknowledgements_to_text_object(text_object, acknowledgements_info)

        images = self.get_all_project_images()
        post_task_update(callback, f"--- Found {len(images)} images")
        for image in images:
            if image.request_type != 'image-understanding' and image.page != 0:
                # Find the corresponding Page object, if there is one.
                page_object = text_object.find_page_by_image(image)
                if page_object:
                    # Merge the Page object into the Image object
                    image.merge_page(page_object)
                    # Remove the Page object from the Text object
                    text_object.remove_page(page_object)
                add_image_to_text(text_object, image, project_id_internal=self.id, callback=callback)
        
        post_task_update(callback, f"--- Adding concordance annotations")
        concordance_annotator = ConcordanceAnnotator(concordance_id=self.id)
        concordance_annotator.annotate_text(text_object, phonetic=phonetic)
        post_task_update(callback, f"--- Concordance annotations done")
##        self.internalised_and_annotated_text = text_object
        self.save_internalised_and_annotated_text(text_object, phonetic=phonetic, callback=callback)
        return text_object

    def save_internalised_and_annotated_text(self, text_object, phonetic=False, callback=None):
        try:
            path = absolute_local_file_name(self.get_internalised_and_annotated_text_path(phonetic=phonetic))
            with open(path, 'wb') as file:
                pickle.dump(text_object, file)
            post_task_update(callback, f"--- Saved internalised form to {path}")
            return True
        except Exception as e:
            post_task_update(callback, f'*** Error when trying to save internalised form to {path}')
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            return False

    def get_saved_internalised_and_annotated_text(self, phonetic=False, callback=None):
        try:
            path = absolute_local_file_name(self.get_internalised_and_annotated_text_path(phonetic=phonetic))
            if not local_file_exists(path):
                return None
            
            with open(path, 'rb') as file:
                text_object = pickle.load(file)
            post_task_update(callback, f"--- Read internalised form from {path}")
            return text_object
            
        except Exception as e:
            post_task_update(callback, f'*** Error when trying to read internalised form from {path}')
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            return None

    # Get audio metadata for the project.
    #
    # audio_type_for_words and audio_type_for_segments can have values 'tts' or 'human'.
    # type can have values 'words', 'segments' or 'all'.
    # format can have values 'default' or 'lite_dev_tools'.
    # phonetic can have values True or False
    #
    # This is mostly useful for getting human voice metadata.
    # Typically we will call this with type = 'words' or 'segments',
    # audio_type_for_words or audio_type_for_segments (whichever one matches the value of type) set to 'human'
    # and format = 'lite_dev_tools'.
    #
    # The 'phonetic' parameter distinguishes between normal and phonetic versions of the text.
    # With phonetic = True, 'words' actually means letter-groups, and 'segments' actually means words.
    def get_audio_metadata(self, tts_engine_type=None, human_voice_id=None,
                           audio_type_for_words='tts', audio_type_for_segments='tts', use_context=False, 
                           type='all', phonetic=False, callback=None):
        post_task_update(callback, f"--- Getting audio metadata (phonetic = {phonetic})")
        text_object = self.get_internalised_text(phonetic=phonetic)

        if text_object:
            post_task_update(callback, f"--- Internalised text created")
            audio_annotator = AudioAnnotator(self.l2_language, tts_engine_type=tts_engine_type, human_voice_id=human_voice_id,
                                             audio_type_for_words=audio_type_for_words, audio_type_for_segments=audio_type_for_segments, 
                                             use_context=use_context, phonetic=phonetic, callback=callback)
            return audio_annotator.generate_audio_metadata(text_object, type=type, phonetic=phonetic, callback=callback)
        else:
            post_task_update(callback, f"--- Cannot create internalised text (phonetic = {phonetic})")
            return []

    # Unzip a zipfile received from LiteDevTools, which will include human audio files and metadata.
    # Use the metadata to install the files in the audio repository 
    def process_lite_dev_tools_zipfile(self, zipfile, human_voice_id, callback=None):
        post_task_update(callback, f"--- Trying to install LDT zipfile {zipfile} with human voice ID {human_voice_id}")
        if not local_file_exists(zipfile):
            post_task_update(callback, f'*** Error: unable to find {zipfile}')
            return False
        else:
            post_task_update(callback, f'--- {zipfile} found')
        try:
            audio_annotator = AudioAnnotator(self.l2_language, human_voice_id=human_voice_id, phonetic=False, callback=callback)
            post_task_update(callback, f'--- Calling process_lite_dev_tools_zipfile')
            return audio_annotator.process_lite_dev_tools_zipfile(zipfile, callback=callback)
        except Exception as e:
            post_task_update(callback, f'*** Error when trying to install LDT zipfile {zipfile}')
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            return False

    # Process content of a metadata file and audio file received from manual audio/text alignment.
    # The content of the metadata file can be a list (JSON metadata file) or a string (Audacity label file)
    # Use the metadata to extract audio segments and store them in the audio repository.
    def process_manual_alignment(self, audio_file, metadata_or_audacity_label_data, human_voice_id, use_context=True, callback=None):
        post_task_update(callback, f"--- Trying to process manual alignment with audio_file {audio_file} and human voice ID {human_voice_id}")
        
        if not local_file_exists(audio_file):
            post_task_update(callback, f'*** Error: unable to find {audio_file}')
            return False
        else:
            post_task_update(callback, f'--- {audio_file} found')
        
        try:
            # If the metadata is the contents of an Audacity label file, convert it to JSON form.
            annotated_segment_data = self.get_labelled_segmented_text()
            post_task_update(callback, f'--- Found labelled segmented text')

            if isinstance(metadata_or_audacity_label_data, ( str )):
                # It's Audacity label data
                metadata = annotated_segmented_data_and_label_file_data_to_metadata(annotated_segment_data, metadata_or_audacity_label_data, callback=callback)
            else:
                # It's JSON metadata
                metadata = metadata_or_audacity_label_data
                
            audio_annotator = AudioAnnotator(self.l2_language, human_voice_id=human_voice_id, phonetic=False, use_context=use_context, callback=callback)
            post_task_update(callback, f'--- Calling process_manual_alignment')
            return audio_annotator.process_manual_alignment(metadata, audio_file, callback=callback)
        except Exception as e:
            post_task_update(callback, f'*** Error when trying to install manual alignments for {audio_file}')
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            return False

    def add_project_image(self, image_name, image_file_path, associated_text='', associated_areas='',
                          page=1, position='bottom', style_description='', content_description='', user_prompt='',
                          request_type='image-generation', description_variable='',
                          description_variables=[], callback=None):  # New field
        try:
            project_id = self.id
            
            post_task_update(callback, f"--- Adding image {request_type} item {image_name} (file path = {image_file_path}) to project {project_id}")            
            
            # Store the image in the repository
            if image_file_path:
                stored_image_path = self.image_repository.store_image(project_id, image_file_path, callback=callback)
            else:
                stored_image_path = ''
            
            # Logic to add the image entry to the repository
            self.image_repository.add_entry(project_id, image_name, stored_image_path,
                                            associated_text=associated_text, associated_areas=associated_areas,
                                            page=page, position=position,
                                            style_description=style_description,
                                            content_description=content_description,
                                            user_prompt=user_prompt,
                                            request_type=request_type,
                                            description_variable=description_variable,
                                            description_variables=description_variables,  # New field
                                            callback=callback)
            
            post_task_update(callback, f"--- Image {image_name} added successfully")
            return stored_image_path
        except Exception as e:
            post_task_update(callback, f"*** CLARAProjectInternal: error when adding/updating image {image_name}")
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            # Handle the exception as needed
            return None
    
    # Retrieves the image associated with the project
    def get_project_image(self, image_name, callback=None):
        try:
            project_id = self.id
            
            post_task_update(callback, f"--- Retrieving image {image_name} for project {project_id}")
            
            # Logic to get the image entry from the repository
            image = self.image_repository.get_entry(project_id, image_name, callback=callback)
            
            post_task_update(callback, f"--- Image retrieved successfully")
            return image
        except Exception as e:
            post_task_update(callback, f"*** Error when retrieving image: {str(e)}")
            # Handle the exception as needed
            return None

    def get_generated_project_image_by_position(self, page, position, callback=None):
        try:
            project_id = self.id
            
            image =  self.image_repository.get_generated_entry_by_position(project_id, page, position, callback=None)

            return image
        except Exception as e:
            post_task_update(callback, f"*** Error when retrieving image by position: {str(e)}")
            # Handle the exception as needed
            return None

    # Removes an image from the ImageRepository associated with the project
    def remove_project_image(self, image_name, callback=None):
        try:
            project_id = self.id
            
            post_task_update(callback, f"--- Removing image {image_name} from project {project_id}")

            # Logic to remove the image entry from the repository
            self.image_repository.remove_entry(project_id, image_name, callback=callback)

            post_task_update(callback, f"--- Image {image_name} removed successfully")
        except Exception as e:
            post_task_update(callback, f"*** Error when removing image: {str(e)}")
            # Handle the exception as needed

    # Removes all images associated with the project from the ImageRepository 
    def remove_all_project_images(self, callback=None):
        try:
            project_id = self.id
            
            post_task_update(callback, f"--- Removing all images from project {project_id}")

            # Logic to remove the image entries from the repository
            self.image_repository.delete_entries_for_project(project_id, callback=callback)

            post_task_update(callback, f"--- Images for {project_id} removed successfully")
        except Exception as e:
            post_task_update(callback, f"*** Error when removing image: {str(e)}")
            # Handle the exception as needed

    def remove_all_project_images_except_style_images(self, callback=None):
        try:
            project_id = self.id
            
            post_task_update(callback, f"--- Removing all images except style image from project {project_id}")

            # Logic to remove the image entries from the repository
            self.image_repository.remove_all_entries_except_style_images(project_id, callback=callback)

            post_task_update(callback, f"--- Images for {project_id} removed successfully")
        except Exception as e:
            post_task_update(callback, f"*** Error when removing image: {str(e)}")
            # Handle the exception as needed

    # Retrieves all images associated with the project
    def get_all_project_images(self, callback=None):
        try:
            project_id = self.id
            
            post_task_update(callback, f"--- Retrieving all images for project {project_id}")

            # Logic to get all image entries from the repository
            all_images = self.image_repository.get_all_entries(project_id)

            post_task_update(callback, f"--- All images retrieved successfully, total: {len(all_images)}")
            return all_images
        except Exception as e:
            post_task_update(callback, f"*** Error when retrieving images: {str(e)}")
            # Handle the exception as needed
            return None

    def add_project_image_description(self, description_variable, explanation, callback=None):
        try:
            project_id = self.id

            post_task_update(callback, f"--- Adding image description {description_variable} to project {project_id}")
            
            self.image_repository.add_description(project_id, description_variable, explanation, callback=callback)

            post_task_update(callback, f"--- Image description {description_variable} added successfully")
        except Exception as e:
            post_task_update(callback, f"*** Error when adding/updating image description {description_variable}")
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)

    def get_project_image_description(self, description_variable, formatting='objects', callback=None):
        try:
            project_id = self.id

            post_task_update(callback, f"--- Retrieving image description {description_variable} for project {project_id}")

            description = self.image_repository.get_description(project_id, description_variable, formatting=formatting, callback=callback)

            post_task_update(callback, f"--- Image description retrieved successfully")
            return description
        except Exception as e:
            post_task_update(callback, f"*** Error when retrieving image description: {str(e)}")
            return None

    def remove_project_image_description(self, description_variable, callback=None):
        try:
            project_id = self.id

            post_task_update(callback, f"--- Removing image description {description_variable} from project {project_id}")

            self.image_repository.remove_description(project_id, description_variable, callback=callback)

            post_task_update(callback, f"--- Image description {description_variable} removed successfully")
        except Exception as e:
            post_task_update(callback, f"*** Error when removing image description: {str(e)}")

    def remove_all_project_image_descriptions(self, callback=None):
        try:
            project_id = self.id

            post_task_update(callback, f"--- Removing all image descriptions from project {project_id}")

            self.image_repository.delete_descriptions_for_project(project_id, callback=callback)

            post_task_update(callback, f"--- Image descriptions for {project_id} removed successfully")
        except Exception as e:
            post_task_update(callback, f"*** Error when removing image descriptions: {str(e)}")

    def get_all_project_image_descriptions(self, formatting='objects', callback=None):
        try:
            project_id = self.id

            post_task_update(callback, f"--- Retrieving all image descriptions for project {project_id}")

            all_descriptions = self.image_repository.get_all_descriptions(project_id, formatting=formatting, callback=callback)

            post_task_update(callback, f"--- All image descriptions retrieved successfully, total: {len(all_descriptions)}")
            return all_descriptions
        except Exception as e:
            post_task_update(callback, f"*** Error when retrieving image descriptions: {str(e)}")
            return None

    def copy_image_description_objects_to_project(self, image_descriptions, callback=None):
        try:
            project_id = self.id
            
            post_task_update(callback, f"--- Adding {len(image_descriptions)} image descriptions to project {project_id}")            
            
            for image_description in image_descriptions:
                self.add_project_image_description(image_description.description_variable,
                                                   image_description.explanation,
                                                   callback=callback)
            
            post_task_update(callback, f"--- {len(image_description)} image descriptions added successfully")
            return True
        except Exception as e:
            post_task_update(callback, f"*** CLARAProjectInternal: error when copying image descriptions to project")
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            # Handle the exception as needed
            return None
        
    def store_image_understanding_result(self, description_variable, result,
                                         image_name=None, page=None, position=None, user_prompt=None,
                                         callback=None):
        try:
            project_id = self.id
            
            post_task_update(callback, f"--- Storing understanding result for {description_variable}")
            self.image_repository.store_understanding_result(project_id, description_variable, result,
                                                             image_name=image_name,
                                                             page=page, position=position,
                                                             user_prompt=user_prompt,
                                                             callback=callback)
            post_task_update(callback, f"--- Understanding result stored")
        except Exception as e:
            post_task_update(callback, f"*** Error storing understanding result for {description_variable}")
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)

    def get_image_understanding_result(self, description_variable, callback=None):
        try:
            project_id = self.id
            
            post_task_update(callback, f"--- Retrieving understanding result for {description_variable}")
            result = self.image_repository.get_understanding_result(project_id, description_variable, callback=callback)
            post_task_update(callback, f"--- Understanding result retrieved")
            return result
        except Exception as e:
            post_task_update(callback, f"*** Error retrieving understanding result for {description_variable}")
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            return None

    def instantiate_image_description_variables_in_prompt(self, prompt, callback=None):
        description_variables = description_variables_in_prompt(prompt)
        instantiated_prompt = prompt
        for description_variable in description_variables:
            description = self.get_image_understanding_result(description_variable, callback=callback)
            if not description:
                error_message = f"*** Error: description variable '{description_variable}' uninstantiated in prompt '{prompt}'"
                post_task_update(callback, error_message)
                raise ImageGenerationError(message=error_message)
            else:
                instantiated_prompt = instantiated_prompt.replace(f'{{{description_variable}}}', description)
        return instantiated_prompt

    def copy_image_objects_to_project(self, images, callback=None):
        project_id = self.id
        
        try:
            post_task_update(callback, f"--- Adding {len(images)} images to project {project_id}")            
            
            for image in images:
                self.add_project_image(image.image_name,
                                       image.image_file_path,
                                       associated_text=image.associated_text,
                                       associated_areas=image.associated_areas,
                                       page=image.page,
                                       position=image.position,
                                       style_description=image.style_description,
                                       content_description=image.content_description,
                                       user_prompt=image.user_prompt,
                                       request_type=image.request_type,
                                       description_variable=image.description_variable,
                                       description_variables=image.description_variables,
                                       callback=callback)
            
            post_task_update(callback, f"--- {len(images)} images added successfully")
            return True
        except Exception as e:
            post_task_update(callback, f"*** CLARAProjectInternal: error when copying images to project")
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            # Handle the exception as needed
            return None

    # Render the text as an optionally self-contained directory of HTML pages
    # "Self-contained" means that it includes all the multimedia files referenced.
    # First create an internalised version of the text including gloss, lemma, audio and concordance annotations.
    # Requires 'gloss' and 'lemma' texts.
    def render_text(self, project_id, self_contained=False,
                    preferred_tts_engine=None, preferred_tts_voice=None,
                    human_voice_id=None,
                    audio_type_for_words='tts', audio_type_for_segments='tts',
                    format_preferences_info=None, acknowledgements_info=None,
                    phonetic=False, callback=None) -> None:
        post_task_update(callback, f"--- Start rendering text (phonetic={phonetic}, preferred_tts_voice={preferred_tts_voice})")
        l2 = self.l2_language
        title = self.load_text_version_or_null("title")
        text_object = self.get_internalised_and_annotated_text(title=title,
                                                               preferred_tts_engine=preferred_tts_engine, preferred_tts_voice=preferred_tts_voice,
                                                               human_voice_id=human_voice_id,
                                                               audio_type_for_words=audio_type_for_words,
                                                               audio_type_for_segments=audio_type_for_segments,
                                                               acknowledgements_info=acknowledgements_info,
                                                               phonetic=phonetic, callback=callback)
 
        post_task_update(callback, f"--- Created internalised and annotated text")
        text_object.prettyprint()
        # Pass both Django-level and internal IDs
        normal_html_exists = self.rendered_html_exists(project_id)
        post_task_update(callback, f"--- normal_html_exists: {normal_html_exists}")
        phonetic_html_exists = self.rendered_phonetic_html_exists(project_id)
        post_task_update(callback, f"--- phonetic_html_exists: {phonetic_html_exists}")
        renderer = StaticHTMLRenderer(project_id, self.id, l2,
                                      phonetic=phonetic, format_preferences_info=format_preferences_info,
                                      normal_html_exists=normal_html_exists, phonetic_html_exists=phonetic_html_exists, callback=callback)
        post_task_update(callback, f"--- Start creating pages")
        renderer.render_text(text_object, self_contained=self_contained, callback=callback)
        post_task_update(callback, f"finished")
        return renderer.output_dir

    def delete_rendered_html(self, project_id, phonetic=False):
        renderer = StaticHTMLRenderer(project_id, self.id, phonetic=phonetic)
        renderer.delete_rendered_html_directory()

    # Determine whether the rendered HTML has been created
    def rendered_html_exists(self, project_id):
        return file_exists(self.rendered_html_page_1_file(project_id))

    def rendered_html_timestamp(self, project_id, time_format='float', debug=False):
        page1 = self.rendered_html_page_1_file(project_id)
        result = None if not file_exists(page1) else get_file_time(page1, time_format=time_format)
        if debug:
            print(f'rendered_html_timestamp: {result}')
        return result

    def rendered_html_page_1_file(self, project_id):
        output_dir = output_dir_for_project_id(project_id, 'normal')
        page_1_file = str( Path(output_dir) / 'page_1.html' )
        return page_1_file

    # Determine whether the rendered HTML has been created
    def rendered_phonetic_html_exists(self, project_id):
        return file_exists(self.rendered_phonetic_html_page_1_file(project_id))

    def rendered_phonetic_html_timestamp(self, project_id, time_format='float', debug=False):
        page1 = self.rendered_phonetic_html_page_1_file(project_id)
        result = None if not file_exists(page1) else get_file_time(page1, time_format=time_format)
        if debug:
            print(f'rendered_phonetic_html_timestamp: {result}')
        return result

    def rendered_phonetic_html_page_1_file(self, project_id):
        output_dir = output_dir_for_project_id(project_id, 'phonetic')
        page_1_file = str( Path(output_dir) / 'page_1.html' )
        return page_1_file

    # Get the word-count
    def get_word_count(self, phonetic=False) -> int:
        text_object = self.get_internalised_text(phonetic=phonetic)
        return None if not text_object else text_object.word_count(phonetic=phonetic)

    # Get the voice
    def get_voice(self, human_voice_id=None, audio_type_for_words='tts', audio_type_for_segments='tts') -> str:
        audio_annotator = AudioAnnotator(self.l2_language, human_voice_id=human_voice_id,
                                         audio_type_for_words=audio_type_for_words, audio_type_for_segments=audio_type_for_segments)
        return None if not audio_annotator else audio_annotator.printname_for_voice()

    # Make a zipfile for exporting the project and other metadata
    def create_export_zipfile(self, simple_clara_type='create_text_and_image', uses_coherent_image_set=False,
                              human_voice_id=None, human_voice_id_phonetic=None,
                              audio_type_for_words='tts', audio_type_for_segments='tts', callback=None):
        global_metadata = { 'simple_clara_type': simple_clara_type,
                            'uses_coherent_image_set': uses_coherent_image_set,
                            'human_voice_id': human_voice_id,
                            'human_voice_id_phonetic': human_voice_id_phonetic,
                            'audio_type_for_words': audio_type_for_words,
                            'audio_type_for_segments': audio_type_for_segments }
        project_directory = self.project_dir
        audio_metadata = self.get_audio_metadata(tts_engine_type=None,
                                                 human_voice_id=human_voice_id, 
                                                 audio_type_for_words=audio_type_for_words,
                                                 audio_type_for_segments=audio_type_for_segments,
                                                 type='all', 
                                                 phonetic=False, callback=callback)
        if self.text_versions['phonetic'] and human_voice_id_phonetic:
            audio_metadata_phonetic = self.get_audio_metadata(tts_engine_type=None,
                                                              human_voice_id=human_voice_id_phonetic,
                                                              audio_type_for_words='human',
                                                              audio_type_for_segments=audio_type_for_words,
                                                              type='all', 
                                                              phonetic=True, callback=callback)
        else:
            audio_metadata_phonetic = None
        image_metadata = self.get_all_project_images(callback=callback)
        image_description_metadata = self.get_all_project_image_descriptions(callback=callback)
        zipfile = self.export_zipfile_pathname()
        result = create_export_zipfile(global_metadata, project_directory, audio_metadata, audio_metadata_phonetic,
                                       image_metadata, image_description_metadata,
                                       zipfile, callback=callback)
        if result:
            return zipfile
        else:
            post_task_update(callback, f"error")
            return False

    def export_zipfile_pathname(self):
        return absolute_file_name(f"$CLARA/tmp/{self.id}_zipfile.zip")
