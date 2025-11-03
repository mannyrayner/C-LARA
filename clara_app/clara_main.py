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
from .clara_merge_glossed_and_tagged import merge_glossed_and_tagged, merge_glossed_and_tagged_with_pinyin
from .clara_merge_glossed_and_tagged import merge_with_translation_annotations, merge_with_mwe_annotations
from .clara_audio_annotator import AudioAnnotator
from .clara_concordance_annotator import ConcordanceAnnotator
from .clara_image_repository_orm import ImageRepositoryORM
from .clara_phonetic_lexicon_repository_orm import PhoneticLexiconRepositoryORM
from .clara_renderer import StaticHTMLRenderer
from .clara_annotated_images import add_image_to_text
from .clara_phonetic_text import segmented_text_to_phonetic_text
from .clara_mwe import simplify_mwe_tagged_text, annotate_mwes_in_text
from .clara_acknowledgements import add_acknowledgements_to_text_object
from .clara_export_import import create_export_zipfile, change_project_id_in_imported_directory, update_multimedia_from_imported_directory
from .clara_export_import import get_global_metadata, rename_files_in_project_dir, update_metadata_file_paths
from .clara_coherent_images import process_style, generate_element_names, process_elements, process_pages
from .clara_coherent_images import generate_overview_html, add_uploaded_page_image, add_uploaded_element_image, create_variant_images_for_page
from .clara_coherent_images import execute_community_requests_list
from .clara_coherent_images import execute_simple_clara_image_requests, execute_simple_clara_element_requests, execute_simple_clara_style_requests
from .clara_coherent_images import delete_element, add_element, delete_page_image
from .clara_coherent_images_community_feedback import get_page_overview_info_for_cm_reviewing
from .clara_coherent_images_advice import set_background_advice, get_background_advice
from .clara_coherent_images_advice import set_style_advice, get_style_advice, get_element_advice, get_page_advice, set_page_advice, set_element_advice
from .clara_coherent_images_alternate import get_project_images_dict, promote_alternate_image, promote_alternate_element_description
from .clara_coherent_images_utils import get_project_params, set_project_params, project_params_for_simple_clara
from .clara_coherent_images_utils import project_pathname, get_pages, make_project_dir, element_name_to_element_text
from .clara_coherent_images_utils import get_story_data, set_story_data_from_numbered_page_list, remove_top_level_element_directory
from .clara_coherent_images_utils import get_style_description, get_all_element_texts, element_text_to_element_name
from .clara_coherent_images_utils import get_element_description, get_page_description
from .clara_coherent_images_utils import style_image_name, element_image_name, page_image_name, overview_file
from .clara_coherent_images_utils import style_directory, element_directory, element_directory_for_element_name, page_directory
from .clara_coherent_images_utils import get_style_image, get_page_image, get_element_image, get_all_page_images, get_all_element_images
from .clara_align_with_segmented import align_segmented_text_with_non_segmented_text, remove_any_empty_pages_at_end
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
import asyncio

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
        self.coherent_images_v2_project_dir = self.project_dir / 'coherent_images_v2_project_dir'
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
        if directory_exists(self.coherent_images_v2_project_dir):
            copy_directory(self.coherent_images_v2_project_dir, new_project.coherent_images_v2_project_dir)
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
        trace_save_text_version = False
        #trace_save_text_version = True
        
##        if trace_save_text_version:
##            print(f'Save text file: {version}')
##            self._check_metadata_file_consistent()
        
        file_path = self._file_path_for_version(version)

        # Reconstruct the metadata file if it is missing or inconsistent
        self._create_metadata_file_if_missing(user)

##        # For downward compatibility, guess metadata for existing files if necessary, assuming they were created by this user.
##        if trace_save_text_version:
##            print(f'Create metadata file if missing (before)')
##            self._check_metadata_file_consistent() 
##        self._create_metadata_file_if_missing(user)
##        if trace_save_text_version:
##            print(f'Create metadata file if missing (after)')
##            self._check_metadata_file_consistent()
        
        # Archive the old version, if it exists
        if file_exists(file_path):
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            archive_dir = self._get_archive_dir()
            make_directory(archive_dir, parents=True, exist_ok=True) 
            archive_path = archive_dir / f'{version}_{timestamp}.txt'
            if not file_exists(archive_path):
                rename_file(file_path, archive_path)
        else:
            archive_path = None

        # Save the new version
        text = make_line_breaks_canonical_n(text)
        write_txt_file(text, file_path)

        # Update the metadata file, transferring the entry for 'file_path' to 'archive_path' and creating a new entry for 'file_path'
        self._update_metadata_file(file_path, archive_path, version, source, user, label, gold_standard)

        if trace_save_text_version:
            print(f'Save metadata file')
            self._check_metadata_file_consistent()
        
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
            try:
                metadata = read_json_file(metadata_file)
                for item in metadata:
                    provenance = item['source'] if item['source'] != "human_revised" else item['source']
                    timestamp = format_timestamp(item['timestamp'])
                    gold_standard = ' (gold standard)' if item['gold_standard'] else ''
                    label = f' {item["label"]} ' if 'label' in item and item["label"] else ''
                    item['description'] = f'{provenance} {timestamp}{label}{gold_standard}'
                return metadata
            except Exception as e:
                return []

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
                    entry = {
                        "file": str(file_path),
                        "version": version,
                        "source": "reconstructed",
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

    def _check_metadata_file_consistent(self):
        trace = False
        #trace = True
        metadata_file = self._get_metadata_file()

        if not local_file_exists(metadata_file):
            if trace: print(f'metadata file does not exist')
            return True
        else:
            try:
                if trace: print(f'metadata file exists')
                metadata = read_json_file(metadata_file)
                if trace: format(f'Read metadata file, {len(metadata)} records')
                return True
            except Exception as e:
                if trace: format(f'Unable to read metadata files')
                return False

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
        #images_text = self.image_repository.get_annotated_image_text(self.id, callback=callback)
        images_text = ''
        segmented_with_images_text = segmented_text + '\n' + images_text
        text_title = self.load_text_version_or_null("segmented_title")
        if text_title != '':
            # We need to put segment breaks around the text_title to get the right interaction with segment audio
            # and if the main text doesn't start with a <page> tag we need to add one.
            separating_page_tag = '' if segmented_with_images_text.startswith('<page') else '<page>'
            segmented_with_images_text = f'<h1>||{text_title}||</h1>{separating_page_tag}\n' + segmented_with_images_text
        return segmented_with_images_text

    # Get text consisting of "segmented" text, plus segmented title if available
    def _create_and_load_segmented_with_title_text(self):
        segmented_text = self.load_text_version("segmented")
        text_title = self.load_text_version_or_null("segmented_title")
        if text_title != '':
            # We need to put segment breaks around the text_title to get the right interaction with segment audio
            # and if the main text doesn't start with a <page> tag we need to add one.
            separating_page_tag = '' if segmented_text.startswith('<page') else '<page>'
            segmented_with_title_text = f'<h1>||{text_title}||</h1>{separating_page_tag}\n' + segmented_text
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

    # Get different versions of the text cut up into pages. If a version doesn't exist, make a dummy version.
    # Raise an exception if there are syntax errors
    def get_page_texts(self):
        trace = False
        #trace = True
        if not self.text_versions["segmented"]:
            raise InternalCLARAError(message = 'No segmented text, unable to produce page texts')

        # Align everything with segmented in case we have alignment errors
        self.align_all_text_versions_with_segmented_and_save()

        page_texts = {}

        segmented_text = self.load_text_version("segmented_with_images")
        internalised_segmented_text = self.internalize_text(segmented_text, "segmented")
        
        segmented_page_objects = internalised_segmented_text.pages
        page_texts['plain'] = [ page_object.to_text(annotation_type="plain").replace('<page>', '')
                                for page_object in segmented_page_objects ]
        page_texts['segmented'] = [ page_object.to_text(annotation_type="segmented").replace('<page>', '')
                                    for page_object in segmented_page_objects ]

        if self.text_versions["mwe"]:
            mwe_text = self.load_text_version("mwe")
            internalised_mwe_text = self.internalize_text(mwe_text, "mwe")
            # Do this so that we get an exception we can report if the MWEs don't match the text
            #annotate_mwes_in_text(internalised_mwe_text)
        else:
            internalised_mwe_text = self.internalize_text(segmented_text, "segmented")
            for page in internalised_mwe_text.pages:
                for segment in page.segments:
                    segment.annotations = { "mwes": [], "analysis": '' }
        mwe_page_objects = internalised_mwe_text.pages
        page_texts['mwe'] = [ page_object.to_text(annotation_type="mwe_minimal").replace('<page>', '')
                              for page_object in mwe_page_objects ]

        if self.text_versions["translated"]:
            translation_text = self.load_text_version("translated")
            internalised_translation_text = self.internalize_text(translation_text, "translated")
        else:
            internalised_translation_text = self.internalize_text(segmented_text, "segmented")
            for page in internalised_translation_text.pages:
                for segment in page.segments:
                    segment.annotations = { "translated": '' }
        translation_page_objects = internalised_translation_text.pages
        page_texts['translated'] = [ page_object.to_text(annotation_type="translated").replace('<page>', '')
                                     for page_object in translation_page_objects ]

        if self.text_versions["lemma"]:
            lemma_text = self.load_text_version("lemma")
            internalised_lemma_text = self.internalize_text(lemma_text, "lemma")
        else:
            internalised_lemma_text = internalize_text(segmented_text, self.l2_language, self.l1_language, "segmented")
            for page in internalised_lemma_text.pages:
                for segment in page.segments:
                    for element in segment.content_elements:
                        element.annotations = { "lemma": element.content, "pos": 'X' }
        lemma_page_objects = internalised_lemma_text.pages
        page_texts['lemma'] = [ page_object.to_text(annotation_type="lemma").replace('<page>', '')
                                for page_object in lemma_page_objects ]

        if self.text_versions["gloss"]:
            gloss_text = self.load_text_version("gloss")
            internalised_gloss_text = self.internalize_text(gloss_text, "gloss")
        else:
            internalised_gloss_text = self.internalize_text(segmented_text, "segmented")
            for page in internalised_lemma_text.pages:
                for segment in page.segments:
                    for element in segment.content_elements:
                        element.annotations = { "gloss": '-' }
        gloss_page_objects = internalised_gloss_text.pages
        page_texts['gloss'] = [ page_object.to_text(annotation_type="gloss").replace('<page>', '')
                                for page_object in gloss_page_objects ]

        # Remove texts for the pages we only use for annotated images
        for key in page_texts:
            page_texts[key] = [ text for text in page_texts[key] if not '<page img=' in text ]

        if trace:
            print(f'page texts')
            pprint.pprint(page_texts)
        return page_texts

    def save_page_texts_multiple(self, types_and_texts, user='', can_use_ai=False, config_info={}, callback=None):
        #print(f'save_page_texts_multiple (clara_main): can_use_ai = {can_use_ai}')
        all_api_calls = []
        for text_type in types_and_texts:
            page_texts = types_and_texts[text_type]
            all_api_calls += self.save_page_texts(text_type, page_texts, user=user, can_use_ai=can_use_ai, config_info=config_info, callback=callback)

        # Align all page texts with segmented in case we've lost alignment
        self.align_all_text_versions_with_segmented_and_save()
        
        return all_api_calls

    def save_page_texts(self, text_type, page_texts, user='', can_use_ai=False, config_info={}, callback=None):
        #print(f'save_page_texts(self, {text_type}, {page_texts}, user={user})')
        #print(f'save_page_texts (clara_main): can_use_ai = {can_use_ai}')
        l2_language = 'irrelevant'
        l1_language = 'irrelevant'
        all_api_calls = []
        if not page_texts:
            return
        elif text_type == 'segmented' and '<h1>' in page_texts[0]:
            # The first element is the segmented title
            segmented_title_text = page_texts[0].replace('<h1>', '').replace('</h1>', '').replace('||', '')
            segmented_text = "\n<page>".join(page_texts[1:])
            # Interalise the text before saving to see if we get an exception
            internalised_title, api_calls = self.internalize_text_maybe_correct_and_save(segmented_title_text, 'segmented_title', can_use_ai=can_use_ai,
                                                                                    config_info=config_info, callback=callback)
            all_api_calls += api_calls
            internalised_segmented, api_calls = self.internalize_text_maybe_correct_and_save(segmented_text, 'segmented', can_use_ai=can_use_ai,
                                                                                        config_info=config_info, callback=callback)
            all_api_calls += api_calls
            return all_api_calls
        else:
            # Concatenate the page texts into a single string, putting <page> tags in between.
            full_text = "\n<page>".join(page_texts)
            internalised_segmented, all_api_calls = self.internalize_text_maybe_correct_and_save(full_text, text_type, can_use_ai=can_use_ai,
                                                                                            config_info=config_info, callback=callback)
            return all_api_calls

    # Create a prompt using null text to see if there is a template error
    def try_to_use_templates(self, generate_or_improve, version):
        return invoke_templates_on_trivial_text(generate_or_improve, version, self.l1_language, self.l2_language)

    # Internalize text. This may raise an internalisation error.
    def internalize_text(self, text, version):
        return internalize_text(text, self.l2_language, self.l1_language, version)

    # Internalize text and try to fix syntax errors if possible
    def internalize_text_maybe_correct_and_save(self, text, version, can_use_ai=False, config_info={}, callback=None):
        try:
            text_object = internalize_text(text, self.l2_language, self.l1_language, version)
            self.save_text_version(version, text, source='human_edited')
##            # Do this so that we get an exception if the MWEs don't match the text
##            if version == 'mwe':
##                annotate_mwes_in_text(text_object)
            api_calls = []
            #print(f'\n\ninternalize_text_maybe_correct_and_save: {version}:')
            #text_object.prettyprint()
            return ( text_object, api_calls )
        except InternalisationError as e:
            if can_use_ai:
                corrected_text, api_calls = correct_syntax_in_string(text, version, self.l2_language, l1=self.l1_language,
                                                                     config_info=config_info, callback=callback)
                #print(f'Corrected "{text}" to "{corrected_text}"')
                text_object = internalize_text(corrected_text, self.l2_language, self.l1_language, version)
                self.save_text_version(version, corrected_text, source='ai_corrected')
                #print(f'\n\ninternalize_text_maybe_correct_and_save: {version}:')
                #text_object.prettyprint()
                return ( text_object, api_calls )
            else:
                raise e
        except Exception as e:
            raise e

    # Try to correct syntax in text and save if successful
    def correct_syntax_and_save(self, text, version, user='Unknown', label='', config_info={}, callback=None):
        corrected_text, api_calls = correct_syntax_in_string(text, version, self.l2_language, l1=self.l1_language,
                                                             config_info=config_info, callback=callback)
        self.save_text_version(version, corrected_text, user=user, label=label, source='ai_corrected')
        return api_calls

    # Align a version with the segmented text if it exists and save the aligned text
    def align_text_version_with_segmented_and_save(self, text_type, create_if_necessary=False, use_words_for_lemmas=False):
        trace = False
        #trace = True
        try:
            segmented_text = self.load_text_version('segmented_with_images')
            if trace:
                print(f'Aligning')
                print(f'segmented_with_images text: "{segmented_text}"')
            
            if self.text_versions[text_type]:
                non_segmented_text = self.load_text_version(text_type)
                if trace:
                    print(f'{text_type} text: {segmented_text}')
            else:
                if create_if_necessary:
                    non_segmented_text = ''
                else:
                    return
                
            aligned_text = align_segmented_text_with_non_segmented_text(segmented_text, non_segmented_text,
                                                                        self.l2_language, self.l1_language,
                                                                        text_type, use_words_for_lemmas=use_words_for_lemmas)
            if trace:
                print(f'aligned text: "{segmented_text}"')
            self.save_text_version(text_type, aligned_text, source='aligned')
            
            api_calls = []
            return api_calls
        except Exception as e:
            error_message = f'Exception when performing alignment against segmented text: "{str(e)}"\n{traceback.format_exc()}'
            raise InternalCLARAError(message = error_message)

    def remove_any_empty_pages_at_end_and_save(self, text_type):
        try:
            text = self.load_text_version(text_type)
            #print(f'Call remove_any_empty_pages_at_end on "{text}"')
            text_without_final_empty_pages = remove_any_empty_pages_at_end(text)
            #print(f'Result = "{text_without_final_empty_pages}"')
            self.save_text_version(text_type, text_without_final_empty_pages, source='aligned')
        except FileNotFoundError:
            pass
        except Exception as e:
            error_message = f'Exception when trying to remove empty pages: "{str(e)}"\n{traceback.format_exc()}'
            raise InternalCLARAError(message = error_message)

    def remove_any_empty_pages_at_end_and_save_for_all_text_versions(self):
        for text_type in ( 'segmented', 'segmented_with_images', 'mwe', 'translated', 'gloss', 'lemma' ):
            self.remove_any_empty_pages_at_end_and_save(text_type)

    # Align all existing versions against segmented and remove any empty pages at end
    def align_all_text_versions_with_segmented_and_save(self):
        for text_type in ( 'mwe', 'translated', 'gloss', 'lemma' ):
            self.align_text_version_with_segmented_and_save(text_type)
        self.remove_any_empty_pages_at_end_and_save_for_all_text_versions()

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
    def create_segmented_text(self, text_type=None, user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
        plain_text = self.load_text_version("plain")
        segmented_text, api_calls = generate_segmented_version(plain_text, self.l2_language,
                                                               text_type=text_type, config_info=config_info, callback=callback)
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
                                                                                 text_type='title', config_info=config_info, callback=callback)
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

    def improve_segmented_text(self, text_type=None, user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
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

    def remove_analyses_from_mwe_tagged_text(self, user='Unknown', label='', config_info={}, callback=None) -> List[APICall]:
        mwe_tagged_text = self.load_text_version("mwe")
        simplified_mwe_tagged_text = simplify_mwe_tagged_text(mwe_tagged_text)
        self.save_text_version("mwe", simplified_mwe_tagged_text, user=user, label=label, source='ai_generated')
        api_calls = []
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
            if self.text_versions["mwe"]:
                mwe_tagged_text = self.load_text_version("mwe")
                internalised_mwe_tagged_text = internalize_text(mwe_tagged_text, self.l2_language, self.l1_language, 'mwe')
                merged_text_with_mwes = merge_with_mwe_annotations(merged_text, internalised_mwe_tagged_text)
                annotate_mwes_in_text(merged_text_with_mwes)
                merged_text = merged_text_with_mwes

            return merged_text

    # Create an internalised version of the text including gloss, lemma, audio and concordance annotations
    # Requires 'gloss' and 'lemma' texts.
    def get_internalised_and_annotated_text(self,
                                            for_questionnaire=False,
                                            title=None,
                                            human_voice_id=None,
                                            audio_type_for_words='tts', audio_type_for_segments='tts',
                                            preferred_tts_engine=None, preferred_tts_voice=None,
                                            acknowledgements_info=None,
                                            phonetic=False, callback=None) -> str:
        post_task_update(callback, f"--- Creating internalised text")
        text_object = self.get_internalised_text(phonetic=phonetic) 
        
        if not text_object:
            return None
        else:
            post_task_update(callback, f"--- Internalised text created")

        if not for_questionnaire and title:
            for page in text_object.pages:
                page.annotations['title'] = title

        if not for_questionnaire:
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
            # We don't want to include null images, style images (both V1 and V2), element images (V2), or image-understanding images (V1)
            if image.image_file_path and not image.image_type in ('style', 'element') and image.request_type != 'image-understanding' and image.page != 0:
                # Find the corresponding Page object, if there is one.
                page_object = text_object.find_page_by_image(image)
                if page_object:
                    # Merge the Page object into the Image object
                    image.merge_page(page_object)
                    # Remove the Page object from the Text object
                    text_object.remove_page(page_object)
                add_image_to_text(text_object, image, project_id_internal=self.id, callback=callback)

        if not for_questionnaire:
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

    def add_project_image(self, image_name, image_file_path, keep_file_name=True, associated_text='', associated_areas='',
                          page=1, position='bottom', style_description='', content_description='', user_prompt='',
                          request_type='image-generation', description_variable='', description_variables=[],
                          image_type='page', advice='', element_name='', 
                          archive=True, callback=None):  
        try:
            project_id = self.id
            
            post_task_update(callback, f"--- Adding image {request_type} item {image_name} (file path = {image_file_path}) to project {project_id}")

            # First archive the current image if there is one, to make sure it doesn't get overwritten
            if archive and image_file_path and file_exists(image_file_path):
                self.image_repository.archive_image_by_name(project_id, image_name, callback=callback)
            
            # Store the new image file 
            if image_file_path and file_exists(image_file_path):
                stored_image_path = self.image_repository.store_image(project_id, image_file_path,
                                                                      keep_file_name=keep_file_name, callback=callback)
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
                                            description_variables=description_variables,
                                            image_type=image_type, advice=advice, element_name=element_name,
                                            callback=callback)
            
            post_task_update(callback, f"--- Image {image_name} added successfully as {stored_image_path}")
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

    def store_image_advice(self, image_name, advice, image_type, callback=None):
        try:
            project_id = self.id
            
            post_task_update(callback, f"--- Storing advice for {image_name}")
            self.image_repository.store_advice(project_id, image_name, advice, image_type, callback=callback)
        except Exception as e:
            post_task_update(callback, f"*** Error storing advice of type {image_type} for {image_name}")
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
        
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
                                       image_type=image.image_type,
                                       advice=image.advice,
                                       element_name=image.element_name,
                                       callback=callback)
            
            post_task_update(callback, f"--- {len(images)} images added successfully")
            return True
        except Exception as e:
            post_task_update(callback, f"*** CLARAProjectInternal: error when copying images to project")
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            # Handle the exception as needed
            return None

    def get_project_images_dict_v2(self):
        project_dir = self.coherent_images_v2_project_dir
        return asyncio.run(get_project_images_dict(project_dir))

    def get_page_overview_info_for_cm_reviewing(self):
        project_dir = self.coherent_images_v2_project_dir
        return get_page_overview_info_for_cm_reviewing(project_dir)

    def get_coherent_images_v2_params(self):
        project_dir = self.coherent_images_v2_project_dir
        return get_project_params(project_dir)

    def get_v2_project_params_for_simple_clara(self):
        project_dir = self.coherent_images_v2_project_dir

        params = project_params_for_simple_clara
        params['project_dir'] = project_dir

        return params

    def save_coherent_images_v2_params(self, params):
        project_dir = self.coherent_images_v2_project_dir
        set_project_params(params, project_dir)

    def set_story_data_from_numbered_page_list_v2(self, numbered_page_list):
        project_dir = self.coherent_images_v2_project_dir
        set_story_data_from_numbered_page_list(numbered_page_list, project_dir)

    def get_story_data_v2(self):
        project_dir = self.coherent_images_v2_project_dir
        params = { 'project_dir': project_dir }
        
        return get_story_data(params)

    def pages_with_missing_story_text_v2(self):
        story_data = self.get_story_data_v2()
        return [ item['page_number'] for item in story_data if 'page_number' in item and 'text' in item and item['text'] == '' ]

    def get_style_image_v2(self):
        project_dir = self.coherent_images_v2_project_dir
        params = { 'project_dir': project_dir }

        #print(f'get_style_image(params) = {get_style_image(params)}')
        return get_style_image(params)

    def get_style_description_v2(self):
        project_dir = self.coherent_images_v2_project_dir
        params = { 'project_dir': project_dir }
        
        return get_style_description(params)

    def get_all_element_texts_v2(self):
        project_dir = self.coherent_images_v2_project_dir
        params = { 'project_dir': project_dir }

        #print(f'get_all_element_images(params) = {get_all_element_images(params)}')
        return get_all_element_texts(params)

    def get_elements_texts_with_no_image_v2(self):
        project_dir = self.coherent_images_v2_project_dir
        params = { 'project_dir': project_dir }
        
        all_element_texts = get_all_element_texts(params)
        output = []
        for element_text in all_element_texts:
            element_image = project_pathname(project_dir, get_element_image(element_text, params))
            if not file_exists(element_image):
                output.append(element_text)

        return output

    def get_all_element_images_v2(self):
        project_dir = self.coherent_images_v2_project_dir
        params = { 'project_dir': project_dir }

        #print(f'get_all_element_images(params) = {get_all_element_images(params)}')
        return get_all_element_images(params)

    def get_all_page_images_v2(self):
        project_dir = self.coherent_images_v2_project_dir
        params = { 'project_dir': project_dir }

        #print(f'get_all_page_images(params) = {get_all_page_images(params)}')
        return get_all_page_images(params)

    def get_pages_with_no_image_v2(self):
        project_dir = self.coherent_images_v2_project_dir
        params = { 'project_dir': project_dir }
        
        all_page_numbers = get_pages(params)
        output = []
        for page_number in all_page_numbers:
            page_image = project_pathname(project_dir, get_page_image(page_number, params))
            if not file_exists(page_image):
                output.append(page_number)

        return output

    def set_background_advice_v2(self, advice):
        project_dir = self.coherent_images_v2_project_dir
        params = { 'project_dir': project_dir }
        
        set_background_advice(advice, params)

    def get_background_advice_v2(self):
        project_dir = self.coherent_images_v2_project_dir
        params = { 'project_dir': project_dir }
        
        advice = get_background_advice(params)
        return advice

    def set_style_advice_v2(self, advice):
        project_dir = self.coherent_images_v2_project_dir
        set_style_advice(advice, project_dir)

        image_name = style_image_name()
        self.store_image_advice(image_name, advice, 'style')

    def get_style_advice_v2(self):
        project_dir = self.coherent_images_v2_project_dir
        params = { 'project_dir': project_dir }
        
        advice = get_style_advice(params)
        return advice

    def set_element_advice_v2(self, advice, element_text):
        project_dir = self.coherent_images_v2_project_dir
        params = { 'project_dir': project_dir }
        set_element_advice(advice, element_text, params)
##        image_name = element_image_name(element_text)
##        self.store_image_advice(image_name, advice, 'element')

    def element_name_to_element_text(self, element_name):
        project_dir = self.coherent_images_v2_project_dir
        params = { 'project_dir': project_dir }
        return element_name_to_element_text(element_name, params)
    
    def get_element_advice_v2(self, element_text):
        project_dir = self.coherent_images_v2_project_dir
        params = { 'project_dir': project_dir }
        return get_element_advice(element_text, params)

    def set_page_advice_v2(self, advice, page_number):
        project_dir = self.coherent_images_v2_project_dir
        params = { 'project_dir': project_dir }
        set_page_advice(advice, page_number, params)

        image_name = page_image_name(page_number)
        self.store_image_advice(image_name, advice, 'page')

    def get_page_advice_v2(self, page_number):
        project_dir = self.coherent_images_v2_project_dir
        params = { 'project_dir': project_dir }
        return get_page_advice(page_number, params)

    def store_v2_style_data(self, params, callback=None):
        project_dir = self.coherent_images_v2_project_dir
        
        image_type = 'style'
        advice = get_style_advice(params)
        image_file_path = project_pathname(project_dir, get_style_image(params))
        image_name = 'style'
        
        self.add_project_image(image_name, image_file_path, image_type=image_type, advice=advice,
                               keep_file_name=False, archive=False, callback=callback)

    def store_v2_element_name_data(self, element_list_with_names, params, callback=None):
        project_dir = self.coherent_images_v2_project_dir
        
##        image_type = 'element'
##        advice = ''
##        image_file_path = None
        for item in element_list_with_names:
##            element_text = item['text']
            element_name = item['name']
##            image_name = f'element_{element_text}'
##            self.add_project_image(image_name, image_file_path, image_type=image_type, advice=advice, element_name=element_name,
##                                   keep_file_name=False, archive=False, callback=callback)
            element_directory = f'elements/{element_name}'
            make_project_dir(project_dir, element_directory)

    def promote_v2_element_description(self, element_name, preferred_description_id, callback=None):
        project_dir = self.coherent_images_v2_project_dir
        params = { 'project_dir': project_dir,
                   'elements_to_generate': [element_name] }
        content_dir = element_directory_for_element_name(element_name, params)
        # Adapt promote_alternate_element_description
        # from promote_alternate_image
        promote_alternate_element_description(content_dir, project_dir, preferred_description_id)

##    def promote_v2_style_image(self, alternate_image_id, callback=None):
##        project_dir = self.coherent_images_v2_project_dir
##        params = { 'project_dir': project_dir }
##        content_dir = style_directory(params)
##        promote_alternate_image(content_dir, project_dir, alternate_image_id)
##        self.store_v2_style_data(params, callback=callback)

    def promote_v2_style_description(self, preferred_description_id, callback=None):
        project_dir = self.coherent_images_v2_project_dir
        params = { 'project_dir': project_dir }
        content_dir = style_directory(params)
        # Adapt promote_alternate_element_description
        # from promote_alternate_image
        promote_alternate_element_description(content_dir, project_dir, preferred_description_id)

##    def promote_v2_element_image(self, element_name, alternate_image_id, callback=None):
##        project_dir = self.coherent_images_v2_project_dir
##        params = { 'project_dir': project_dir,
##                   'elements_to_generate': [element_name] }
##        content_dir = element_directory(element_name, params)
##        promote_alternate_image(content_dir, project_dir, alternate_image_id)
##        self.store_v2_element_data(params, callback=callback)

    def store_v2_element_data(self, params, callback=None):
        project_dir = self.coherent_images_v2_project_dir

        element_names = params['elements_to_generate'] if 'elements_to_generate' in params else get_all_element_texts(params)
        image_type = 'element'
        for element_name in element_names:
            image_name = f'element_{element_name}'
            advice = get_element_advice(element_name, params)
            image_file_path = project_pathname(project_dir, get_element_image(element_name, params))
            self.add_project_image(image_name, image_file_path, image_type=image_type, advice=advice, element_name=element_name,
                                   keep_file_name=False, archive=False, callback=callback)

    def promote_v2_page_image(self, page_number, alternate_image_id, callback=None):
        project_dir = self.coherent_images_v2_project_dir
        params = { 'project_dir': project_dir,
                   'pages_to_generate': [page_number] }
        content_dir = page_directory(page_number, params)
        promote_alternate_image(content_dir, project_dir, alternate_image_id)
        self.store_v2_page_data(params, callback=callback)

    def add_uploaded_page_image_v2(self, image_file_path, page_number, callback=None):
        project_dir = self.coherent_images_v2_project_dir
        params = { 'project_dir': project_dir }
        alternate_image_id = add_uploaded_page_image(image_file_path, page_number, params, callback=callback)
        # Assume that an uploaded image will by default be preferred
        self.promote_v2_page_image(page_number, alternate_image_id, callback=callback)

    def add_uploaded_element_image_v2(self, image_file_path, element_text, callback=None):
        project_dir = self.coherent_images_v2_project_dir
        params = { 'project_dir': project_dir }
        description_id = add_uploaded_element_image(image_file_path, element_text, params, callback=callback)
        # Assume that an uploaded image will by default be preferred
        element_name = element_text_to_element_name(element_text)
        self.promote_v2_element_description(element_name, description_id, callback=callback)

    def store_v2_page_data(self, params, callback=None):
        project_dir = self.coherent_images_v2_project_dir

        #pages_numbers = params['pages_to_generate'] if 'pages_to_generate' in params and params['pages_to_generate'] else get_pages(params)
        pages_numbers = get_pages(params)
        image_type = 'page'
        for page_number in pages_numbers:
            image_name = f'page_{page_number}'
            advice = get_page_advice(page_number, params)
            real_image_file_path = project_pathname(project_dir, get_page_image(page_number, params))
            image_file_path = real_image_file_path if file_exists(real_image_file_path) else None
            self.add_project_image(image_name, image_file_path, image_type=image_type, advice=advice, page=page_number,
                                   keep_file_name=False, archive=False, callback=callback)

    def delete_v2_page_data(self, page_number, params, callback=None):
        project_dir = self.coherent_images_v2_project_dir
        params['project_dir'] = project_dir

        set_page_advice('', page_number, params)
        image_name = f'page_{page_number}'
        self.remove_project_image(self, image_name, callback=callback)

    def create_style_description_and_image_v2(self, params, callback=None):
        project_dir = self.coherent_images_v2_project_dir
        params['project_dir'] = project_dir
        cost_dict = asyncio.run(process_style(params, callback=callback))
        self.store_v2_style_data(params, callback=callback)
        return cost_dict

    def create_element_names_v2(self, params, callback=None):
        try:
            project_dir = self.coherent_images_v2_project_dir
            params['project_dir'] = project_dir

            #self.remove_all_element_information_v2(params)
            element_list_with_names, cost_dict = asyncio.run(generate_element_names(params, callback=callback))
            self.store_v2_element_name_data(element_list_with_names, params, callback=callback)
            return cost_dict
        except Exception as e:
            error_message = f'*** Error when creating element names: "{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)

    def remove_all_element_information_v2(self, params, callback=None):
        try:
            project_id = self.id
            project_dir = self.coherent_images_v2_project_dir
            params['project_dir'] = project_dir

            post_task_update(callback, f"--- Removing all element information from project {project_id}")

            self.image_repository.remove_all_element_entries(project_id, callback=callback)
            remove_top_level_element_directory(params)

            post_task_update(callback, f"--- Element information for {project_id} removed successfully")
        except Exception as e:
            post_task_update(callback, f"*** Error when removing element information: {str(e)}")
        
        
        element_list_with_names, cost_dict = asyncio.run(generate_element_names(params, callback=callback))
        self.store_v2_element_name_data(element_list_with_names, params, callback=callback)
        return cost_dict

    def create_element_descriptions_and_images_v2(self, params, callback=None):
        project_dir = self.coherent_images_v2_project_dir
        params['project_dir'] = project_dir
        cost_dict = asyncio.run(process_elements(params, callback=callback))
        #self.store_v2_element_data(params, callback=callback)
        return cost_dict

    def delete_element_v2(self, params, deleted_element_text):
        project_dir = self.coherent_images_v2_project_dir
        params['project_dir'] = project_dir
        delete_element(deleted_element_text, params)

    # add_element_v2(elements_params, new_element_text, callback=callback)
    def add_element_v2(self, params, new_element_text, callback=None):
        project_dir = self.coherent_images_v2_project_dir
        params['project_dir'] = project_dir
        cost_dict = asyncio.run(add_element(new_element_text, params, callback=callback))
        #self.store_v2_element_data(params, callback=callback)
        return cost_dict

    def create_page_descriptions_and_images_v2(self, params, project_id, callback=None):
        project_dir = self.coherent_images_v2_project_dir
        params['project_dir'] = project_dir
        params['project_id'] = project_id
        cost_dict = asyncio.run(process_pages(params, callback=callback))
        self.store_v2_page_data(params, callback=callback)
        return cost_dict

    def create_variant_images_for_page_v2(self, params, page, alternate_image_id, callback=None):
        project_dir = self.coherent_images_v2_project_dir
        params['project_dir'] = project_dir
        params['pages_to_generate'] = [ page ]
        cost_dict = asyncio.run(create_variant_images_for_page(params, page, alternate_image_id, callback=callback))
        self.store_v2_page_data(params, callback=callback)
        return cost_dict

    def delete_page_image_v2(self, params, deleted_page_number):
        project_dir = self.coherent_images_v2_project_dir
        params['project_dir'] = project_dir
        delete_page_image(deleted_page_number, params)
        image_name = page_image_name(deleted_page_number)
        self.remove_project_image(image_name, callback=None)

    def delete_all_page_images_v2(self, params):
        project_dir = self.coherent_images_v2_project_dir
        params['project_dir'] = project_dir
        all_page_numbers = get_pages(params)
        for page_number in all_page_numbers:
            self.delete_page_image_v2(params, page_number)

    def create_overview_document_v2(self, project):
        project_dir = self.coherent_images_v2_project_dir
        params = { 'project_dir': project_dir,
                   'title': project.title }
        asyncio.run(generate_overview_html(params, mode='server', project_id=project.id))
        asyncio.run(generate_overview_html(params, mode='plain'))

    def overview_document_v2_exists(self):
        project_dir = self.coherent_images_v2_project_dir
        return file_exists(overview_file(project_dir))

    def execute_community_requests_list_v2(self, requests, callback=None):
        project_dir = self.coherent_images_v2_project_dir
        cost_dict = asyncio.run(execute_community_requests_list(project_dir, requests, callback=callback))
        return cost_dict

    def execute_simple_clara_image_requests_v2(self, requests, project_id, callback=None):
        project_dir = self.coherent_images_v2_project_dir
        cost_dict = asyncio.run(execute_simple_clara_image_requests(project_dir, requests, project_id, callback=callback))
        return cost_dict

    def execute_simple_clara_element_requests_v2(self, requests, callback=None):
        project_dir = self.coherent_images_v2_project_dir
        # Adapt execute_simple_clara_element_requests
        # from execute_simple_clara_image_requests_v2
        cost_dict = asyncio.run(execute_simple_clara_element_requests(project_dir, requests, callback=callback))
        return cost_dict

    def execute_simple_clara_style_requests_v2(self, requests, callback=None):
        project_dir = self.coherent_images_v2_project_dir
        # Adapt execute_simple_clara_element_requests
        # from execute_simple_clara_image_requests_v2
        cost_dict = asyncio.run(execute_simple_clara_style_requests(project_dir, requests, callback=callback))
        return cost_dict

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
        #text_object.prettyprint()
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

    def text_available_for_questionnaire_rendering(self, project_id, callback=None):
        text_object = self.get_internalised_and_annotated_text(for_questionnaire=True, callback=callback)
        return True if text_object else False

    def render_text_for_questionnaire(self, project_id, callback=None) -> None:
        post_task_update(callback, f"--- Start rendering text for questionnaire)")
        l2 = self.l2_language
        text_object = self.get_internalised_and_annotated_text(for_questionnaire=True, callback=callback)
 
        post_task_update(callback, f"--- Created internalised and annotated text")
        renderer = StaticHTMLRenderer(project_id, self.id, l2, for_questionnaire=True, callback=callback)
        post_task_update(callback, f"--- Start creating pages")
        renderer.render_text_for_questionnaire(text_object, callback=callback)
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
    def create_export_zipfile(self, simple_clara_type='create_text_and_image',
                              uses_coherent_image_set=False,
                              uses_coherent_image_set_v2=False,
                              use_translation_for_images=False,
                              human_voice_id=None, human_voice_id_phonetic=None,
                              audio_type_for_words='tts', audio_type_for_segments='tts', callback=None):
        global_metadata = { 'simple_clara_type': simple_clara_type,
                            'uses_coherent_image_set': uses_coherent_image_set,
                            'uses_coherent_image_set_v2': uses_coherent_image_set_v2,
                            'use_translation_for_images': use_translation_for_images,
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
