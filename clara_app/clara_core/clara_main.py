"""
Define the CLARAProjectInternal class. An object in this class collects together the data
required to build a multimodal C-LARA text out of a plain text, using ChatGPT to perform
text generation and annotation, and third-party resources like TTS engines to add
other information.

Each CLARAProjectInternal object is associated with a directory, which contains the various
text representations related to the object. These texts are kept as files since they
can be very large. We have seven types of text, as follows:

"plain". The initial unformatted text.
"segmented". Text with segmentation annotations added.
"summary". English summary of text.
"cefr_level". CEFR level of text (one of A1, A2, B1, B2, C1, C2).
"gloss". Text with segmentation annotations plus a gloss annotations for each word.
"lemma". Text with segmentation annotations plus a lemma annotation for each word.
"lemma_and_gloss". Text with segmentation annotations plus a lemma, gloss and POS annotation for each word.

The main methods are the following:

- CLARAProjectInternal(id, l2_language, l1_language). Constructor. Creates necessary directories for
an initial empty project.

- from_directory(directory) [classmethod]. Creates a CLARAProjectInternal from its associated directory.

- copy_files_to_newly_cloned_project(new_project) Copy relevant files from this project
to a newly created clone of it.

- save_text_version(version, text). Saves one of the associated texts. "version" is one
of ( "plain", "summary", "cefr_level", "segmented", "gloss", "lemma", "lemma_and_gloss" ).

- delete_text_version(version). Deletes one of the associated texts. "version" is one
of ( "plain", "summary", "cefr_level", "segmented", "gloss", "lemma", "lemma_and_gloss" ).

- delete_text_versions(versions). Deleted several associated texts. "version" is a list of strings
from ( "plain", "summary", "cefr_level", "segmented", "gloss", "lemma", "lemma_and_gloss" ).

- load_text_version(version). Retrieves one of the associated texts. "version" is one
of ( "plain", "summary", "cefr_level", "segmented", "gloss", "lemma", "lemma_and_gloss" ).

- delete(). Delete project's associated directory.

- get_metadata()
Returns list of metadata references for files holding different updates of text versions.
Metadata reference is dict with keys ( "file", "version", "source", "user", "timestamp", "gold_standard", "description" )
  - file: absolute pathname for file, as str
  - version: one of ( "plain", "summary", "cefr_level", "segmented", "gloss", "lemma", "lemma_and_gloss" )
  - source: one of ( "ai_generated", "ai_revised", "human_revised" )
  - user: username for account on which file was created
  - timestamp: time when file was posted, in format '%Y%m%d%H%M%S'
  - gold_standard: whether or not file should be considered gold standard. One of ( True, False )
  - description: human-readable text describing the file

- get_file_description(version, file)
Returns the metadata "description" field for a file or "" if the file does not exist.
- version: one of ( "plain", "summary", "cefr_level", "segmented", "gloss", "lemma", "lemma_and_gloss" )
- file: either the pathname for an archived file, or "current", referring to the most recent file of this type

- diff_editions_of_text_version(file_path1, file_path2, version, required. Diff two versions
of the same kind of file and return information as specified.
"version" is one of ( "plain", "summary", "segmented", "gloss", "lemma", "lemma_and_gloss" ).
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

- create_lemma_tagged_text(). Calls ChatGPT-4 to annotate the "segmented" version with
lemma annotations in l1_language and saves the result as the "lemma" version.
Requires "segmented" version to exist. Returns a list of APICall instances related to the operation.

- create_lemma_tagged_text_with_treetagger(). Calls TreeTagger to annotate the "segmented" version with
lemma annotations in l1_language and saves the result as the "lemma" version.
Requires "segmented" version to exist. Returns an empty list for consistency with create_lemma_tagged_text above.

- improve_lemma_tagged_text(). Calls ChatGPT-4 to try to improve the "lemma" version.
Requires "lemma" version to exist. Returns a list of APICall instances related to the operation.

- improve_lemma_and_gloss_tagged_text(). Calls ChatGPT-4 to try to improve the "lemma_and_gloss" version.
Requires "lemma" and "gloss" versions to exist. Returns a list of APICall instances related to the operation.

- get_internalised_and_annotated_text(). Returns a Text object, defined in clara_classes.py,
representing the text together with all annotations (segmentation, gloss, lemma, audio, concordance).
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
from .clara_create_annotations import improve_lemma_and_gloss_tagged_version
from .clara_conventional_tagging import generate_tagged_version_with_treetagger
from .clara_create_story import generate_story, improve_story
from .clara_cefr import estimate_cefr_reading_level
from .clara_summary import generate_summary, improve_summary
from .clara_manual_audio_align import add_indices_to_segmented_text, annotated_segmented_data_and_label_file_data_to_metadata
from .clara_internalise import internalize_text
from .clara_correct_syntax import correct_syntax_in_string
from .clara_chinese import segment_text_using_jieba
from .clara_diff import diff_text_objects
from .clara_merge_glossed_and_tagged import merge_glossed_and_tagged
from .clara_audio_annotator import AudioAnnotator
from .clara_concordance_annotator import ConcordanceAnnotator
from .clara_renderer import StaticHTMLRenderer
from .clara_utils import absolute_file_name, read_json_file, write_json_to_file, read_txt_file, write_txt_file, read_local_txt_file
from .clara_utils import rename_file, remove_file, get_file_time, file_exists, local_file_exists, output_dir_for_project_id
from .clara_utils import make_directory, remove_directory, directory_exists, copy_directory, list_files_in_directory
from .clara_utils import get_config, make_line_breaks_canonical_n, make_line_breaks_canonical_linesep, format_timestamp
from .clara_utils import post_task_update

from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union
import datetime
import logging
import pprint

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
            "plain": None,
            "summary": None,
            "cefr_level": None,
            "segmented": None,
            "gloss": None,
            "lemma": None,
            "lemma_and_gloss": None,
        }
        self.internalised_and_annotated_text = None
        self._ensure_directories()
        self._store_information_in_dir()
        self._load_existing_text_versions()

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

    # If there are already files in the associated directory, update self.text_versions
    def _load_existing_text_versions(self) -> None:
        for version in self.text_versions:
            file_path = self._file_path_for_version(version)
            if file_exists(file_path):
                self.text_versions[version] = str(file_path)

    # Copy relevant files from this project to a newly created clone of it.
    def copy_files_to_newly_cloned_project(self, new_project: 'CLARAProjectInternal') -> None:
        # Always copy the plain text file if it's there.
        # Even if it's not directly useable, we may want to transform it in some way
        self._copy_text_version_if_it_exists("plain", new_project)
        # If the L2 is the same, the CEFR, summary, segmented and lemma files will by default be valid
        if self.l2_language == new_project.l2_language:
            self._copy_text_version_if_it_exists("cefr_level", new_project)
            self._copy_text_version_if_it_exists("summary", new_project)
            self._copy_text_version_if_it_exists("segmented", new_project)
            self._copy_text_version_if_it_exists("lemma", new_project)
        # If the L1 is the same, the gloss file will by default be valid
        if self.l1_language == new_project.l1_language:
            self._copy_text_version_if_it_exists("gloss", new_project)

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
    #   - version: one of ( "plain", "summary", "cefr_level", "segmented", "gloss", "lemma" )
    #   - source: one of ( "ai_generated", "ai_revised", "human_revised" )
    #   - user: username for account on which file was created
    #   - timestamp: time when file was posted, in format '%Y%m%d%H%M%S'
    #   - whether or not file should be considered gold standard. One of ( True, False )

    # For downward compatibility, guess metadata based on existing files where necessary.
    # Files referenced:
    #   - self._file_path_for_version(version) for version in ( "plain", "summary", "cefr_level", "segmented", "gloss", "lemma" )
    #     when file exists
    #   - Everything in self._get_archive_dir()
    # Get timestamps from the file ages.
    # Assume they were created by the specified user.
    # Assume that earliest file for a given version is source=ai_generated and others are source=human_revised.
    # Assume that all files are gold_standard=False
    def _create_metadata_file_if_missing(self, user):
        metadata_file = self._get_metadata_file()
        metadata = self.get_metadata()

        versions = ["plain", "summary", "cefr_level", "segmented", "gloss", "lemma"]

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
        file_path = self.text_versions[version]
        if not file_path or not file_exists(Path(file_path)):
            if version == 'lemma_and_gloss':
                return self._create_and_load_lemma_and_gloss_file()
            else:    
                raise FileNotFoundError(f"'{version}' text not found.")
        text = read_txt_file(file_path)
        text = make_line_breaks_canonical_n(text)
        return text

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
    def correct_syntax_and_save(self, text, version, user='Unknown', label='', callback=None):
        corrected_text, api_calls = correct_syntax_in_string(text, version, self.l2_language, l1=self.l1_language, callback=callback)
        self.save_text_version(version, corrected_text, user=user, label=label, source='ai_corrected')
        return api_calls
        
    # Call ChatGPT-4 to create a story based on the given prompt
    def create_plain_text(self, prompt: Optional[str] = None, user='Unknown', label='', callback=None) -> List[APICall]:
        plain_text, api_calls = generate_story(self.l2_language, prompt, callback=callback)
        self.save_text_version('plain', plain_text, user=user, label=label, source='ai_generated')
        return api_calls

    # Call ChatGPT-4 to try to improve a text
    def improve_plain_text(self, user='Unknown', label='', callback=None) -> List[APICall]:
        try:
            current_version = self.load_text_version("plain")
            plain_text, api_calls = improve_story(self.l2_language, current_version, callback=callback)
            self.save_text_version("plain", plain_text, user=user, label=label, source='ai_revised')
            return api_calls
        except:
            return []

    # Call ChatGPT-4 to create a short summary of the text
    def create_summary(self, user='Unknown', label='', callback=None) -> List[APICall]:
        try:
            plain_text = self.load_text_version("plain")
            summary_text, api_calls = generate_summary(plain_text, self.l2_language, callback=callback)
            self.save_text_version("summary", summary_text, user=user, label=label, source='ai_generated')
            return api_calls
        except:
            return []

    # Call ChatGPT-4 to try to improve the summary of the text
    def improve_summary(self, user='Unknown', label='', callback=None) -> List[APICall]:
        try:
            plain_text = self.load_text_version("plain")
            old_summary_text = self.load_text_version("summary")
            summary_text, api_calls = improve_summary(plain_text, old_summary_text, self.l2_language, callback=callback)
            self.save_text_version("summary", summary_text, user=user, label=label, source='ai_revised')
            return api_calls
        except:
            return []

    # Call ChatGPT-4 to estimate the reading level or use the cached version
    def get_cefr_level(self, user='Unknown', label='', callback=None)-> Tuple[Union[str, None], List[APICall]]:
        if self.cefr_level:
            return []
        try:
            plain_text = self.load_text_version("plain")
            cefr_level, api_calls = estimate_cefr_reading_level(plain_text, self.l2_language, callback=callback)
            self.save_text_version("cefr_level", cefr_level, user=user, label=label, source='ai_generated')
            return api_calls
        except:
            return []

    # Call ChatGPT-4 to create a version of the text with segmentation annotations
    def create_segmented_text(self, user='Unknown', label='', callback=None) -> List[APICall]:
        plain_text = self.load_text_version("plain")
        segmented_text, api_calls = generate_segmented_version(plain_text, self.l2_language, callback=callback)
        self.save_text_version("segmented", segmented_text, user=user, label=label, source='ai_generated')
        return api_calls

    # Call Jieba to create a version of the text with segmentation annotations
    def create_segmented_text_using_jieba(self, user='Unknown', label='') -> List[APICall]:
        plain_text = self.load_text_version("plain")
        segmented_text = segment_text_using_jieba(plain_text)
        self.save_text_version("segmented", segmented_text, user=user, label=label, source='jieba_generated')
        api_calls = []
        return api_calls

    # Get "labelled segmented" version of text, used for manual audio/text alignment
    def get_labelled_segmented_text(self) -> str:
        segmented_text = self.load_text_version("segmented")
        return add_indices_to_segmented_text(segmented_text)

    # Call ChatGPT-4 to improve existing segmentation annotations
    def improve_segmented_text(self, user='Unknown', label='', callback=None) -> List[APICall]:
        segmented_text = self.load_text_version("segmented")
        new_segmented_text, api_calls = improve_segmented_version(segmented_text, self.l2_language, callback=callback)
        self.save_text_version("segmented", new_segmented_text, user=user, label=label, source='ai_revised')
        return api_calls

    # Call ChatGPT-4 to create a version of the text with gloss annotations
    def create_glossed_text(self, user='Unknown', label='', callback=None) -> List[APICall]:
        segmented_text = self.load_text_version("segmented")
        glossed_text, api_calls = generate_glossed_version(segmented_text, self.l1_language, self.l2_language, callback=callback)
        self.save_text_version("gloss", glossed_text, user=user, label=label, source='ai_generated')
        return api_calls

    # Call ChatGPT-4 to improve existing gloss annotations
    def improve_glossed_text(self, user='Unknown', label='', callback=None) -> List[APICall]:
        glossed_text = self.load_text_version("gloss")
        new_glossed_text, api_calls = improve_glossed_version(glossed_text, self.l1_language, self.l2_language, callback=callback)
        self.save_text_version("gloss", new_glossed_text, user=user, label=label, source='ai_revised')
        return api_calls

    # Call Treetagger to create a version of the text with lemma annotations
    def create_lemma_tagged_text_with_treetagger(self, user='Unknown', label='', callback=None) -> List[APICall]:
        segmented_text = self.load_text_version("segmented")
        lemma_tagged_text = generate_tagged_version_with_treetagger(segmented_text, self.l2_language, callback=callback)
        self.save_text_version("lemma", lemma_tagged_text, user=user, label=label, source='tagger_generated')
        api_calls = []
        return api_calls

    # Call ChatGPT-4 to create a version of the text with lemma annotations
    def create_lemma_tagged_text(self, user='Unknown', label='', callback=None) -> List[APICall]:
        segmented_text = self.load_text_version("segmented")
        lemma_tagged_text, api_calls = generate_tagged_version(segmented_text, self.l2_language, callback=callback)
        self.save_text_version("lemma", lemma_tagged_text, user=user, label=label, source='ai_generated')
        return api_calls

    # Call ChatGPT-4 to improve existing lemma annotations
    def improve_lemma_tagged_text(self, user='Unknown', label='', callback=None) -> List[APICall]:
        lemma_tagged_text = self.load_text_version("lemma")
        new_lemma_tagged_text, api_calls = improve_tagged_version(lemma_tagged_text, self.l2_language, callback=callback)
        self.save_text_version("lemma", new_lemma_tagged_text, user=user, label=label, source='ai_revised')
        return api_calls

    # Call ChatGPT-4 to improve existing lemma_and_gloss annotations
    def improve_lemma_and_gloss_tagged_text(self, user='Unknown', label='', callback=None) -> List[APICall]:
        lemma_and_gloss_tagged_text = self.load_text_version("lemma_and_gloss")
        new_lemma_and_gloss_tagged_text, api_calls = improve_lemma_and_gloss_tagged_version(lemma_and_gloss_tagged_text, self.l1_language, self.l2_language, callback=callback)
        self.save_text_version("lemma_and_gloss", new_lemma_and_gloss_tagged_text, user=user, label=label, source='ai_revised')
        return api_calls

    # Do any ChatGPT-4 annotation that hasn't already been done
    def do_all_chatgpt4_annotation(self) -> List[APICall]:
        all_api_calls = []
        if not self.text_versions['segmented']:
            all_api_calls += self.create_segmented_text()
        if not self.text_versions['gloss']:
            all_api_calls += self.create_glossed_text()
        if not self.text_versions['lemma']:
            all_api_calls += self.create_lemma_tagged_text()
        return all_api_calls

    # Create an internalised version of the text including gloss and lemma annotations 
    # Requires 'gloss' and 'lemma' texts 
    def get_internalised_text(self) -> str:
        glossed_text = self.load_text_version("gloss")
        lemma_tagged_text = self.load_text_version("lemma")
        internalised_glossed_text = internalize_text(glossed_text, self.l2_language, self.l1_language, 'gloss')
        internalised_tagged_text = internalize_text(lemma_tagged_text, self.l2_language, self.l1_language, 'lemma')
        merged_text = merge_glossed_and_tagged(internalised_glossed_text, internalised_tagged_text)
        return merged_text

    # Create an internalised version of the text including gloss, lemma, audio and concordance annotations
    # Requires 'gloss' and 'lemma' texts.
    # Caches the internalised version.
    def get_internalised_and_annotated_text(self, tts_engine_type=None, human_voice_id=None,
                                            audio_type_for_words='tts', audio_type_for_segments='tts', callback=None) -> str:
        if self.internalised_and_annotated_text:
            return self.internalised_and_annotated_text
        post_task_update(callback, f"--- Creating internalised text")
        text_object = self.get_internalised_text()
        post_task_update(callback, f"--- Internalised text created")
        
        post_task_update(callback, f"--- Adding audio annotations")
        audio_annotator = AudioAnnotator(self.l2_language, tts_engine_type=tts_engine_type, human_voice_id=human_voice_id,
                                         audio_type_for_words=audio_type_for_words, audio_type_for_segments=audio_type_for_segments, callback=callback)
        audio_annotator.annotate_text(text_object, callback=callback)
        post_task_update(callback, f"--- Audio annotations done")
        
        post_task_update(callback, f"--- Adding concordance annotations")
        concordance_annotator = ConcordanceAnnotator()
        concordance_annotator.annotate_text(text_object)
        post_task_update(callback, f"--- Concordance annotations done")
        self.internalised_and_annotated_text = text_object
        return text_object

    def get_audio_metadata(self, tts_engine_type=None, human_voice_id=None,
                           audio_type_for_words='tts', audio_type_for_segments='tts', type='all', format='default', callback=None):
        post_task_update(callback, f"--- Getting audio metadata")
        text_object = self.get_internalised_text()
        post_task_update(callback, f"--- Internalised text created")
        
        audio_annotator = AudioAnnotator(self.l2_language, tts_engine_type=tts_engine_type, human_voice_id=human_voice_id,
                                         audio_type_for_words=audio_type_for_words, audio_type_for_segments=audio_type_for_segments, callback=callback)
        return audio_annotator.generate_audio_metadata(text_object, type=type, format=format, callback=callback)

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
            audio_annotator = AudioAnnotator(self.l2_language, human_voice_id=human_voice_id, callback=callback)
            post_task_update(callback, f'--- Calling process_lite_dev_tools_zipfile')
            return audio_annotator.process_lite_dev_tools_zipfile(zipfile, callback=callback)
        except:
            return False

    # Process a metadata file and audio file received from manual audio/text alignment.
    # Use the metadata to extract audio segments and store them in the audio repository.
    def process_manual_alignment(self, metadata_file, audio_file, human_voice_id, callback=None):
        post_task_update(callback, f"--- Trying to process manual alignment with metadata_file {metadata_file}, audio_file {audio_file}, and human voice ID {human_voice_id}")
        
        if not local_file_exists(metadata_file) or not local_file_exists(audio_file):
            post_task_update(callback, f'*** Error: unable to find {metadata_file} or {audio_file}')
            return False
        else:
            post_task_update(callback, f'--- {metadata_file} and {audio_file} found')
        
        try:
            # During initial testing, the metadata file is an Audacity label file. Temporary code to convert it to the real form.
            annotated_segment_data = self.get_labelled_segmented_text()
            post_task_update(callback, f'--- Found labelled segmented text')
            
            audacity_label_data = read_local_txt_file(metadata_file)
            post_task_update(callback, f'--- Read metadata file')
            
            metadata = annotated_segmented_data_and_label_file_data_to_metadata(annotated_segment_data, audacity_label_data)
            # This is what we will do in the final version
            #metadata = read_local_json_file(metadata_file)
                
            audio_annotator = AudioAnnotator(self.l2_language, human_voice_id=human_voice_id, callback=callback)
            post_task_update(callback, f'--- Calling process_manual_alignment')
            return audio_annotator.process_manual_alignment(metadata, audio_file, callback=callback)
        except:
            return False


    # Render the text as an optionally self-contained directory of HTML pages
    # "Self-contained" means that it includes all the multimedia files referenced.
    # First create an internalised version of the text including gloss, lemma, audio and concordance annotations.
    # Requires 'gloss' and 'lemma' texts.
    def render_text(self, project_id, self_contained=False, tts_engine_type=None, human_voice_id=None,
                    audio_type_for_words='tts', audio_type_for_segments='tts', callback=None) -> None:
        post_task_update(callback, f"--- Start rendering text")
        text_object = self.get_internalised_and_annotated_text(tts_engine_type=tts_engine_type, human_voice_id=human_voice_id,
                                                               audio_type_for_words=audio_type_for_words, audio_type_for_segments=audio_type_for_segments,
                                                               callback=callback)
        post_task_update(callback, f"--- Created internalised and annotated text")
        renderer = StaticHTMLRenderer(project_id)
        post_task_update(callback, f"--- Start creating pages")
        renderer.render_text(text_object, self_contained=self_contained, callback=callback)
        post_task_update(callback, f"finished")
        return renderer.output_dir

    # Determine whether the rendered HTML has been created
    def rendered_html_exists(self, project_id):
        output_dir = output_dir_for_project_id(project_id)
        page_1_file = str( Path(output_dir) / 'page_1.html' )
        print(f'--- Checking first page of rendered text: {page_1_file}')
        # If the first page exists, at least some HTML has been created
        return file_exists(page_1_file)

    # Get the word-count
    def get_word_count(self) -> int:
        text_object = self.get_internalised_text()
        return None if not text_object else text_object.word_count()

    # Get the voice
    def get_voice(self, human_voice_id=None, audio_type_for_words='tts', audio_type_for_segments='tts') -> str:
        audio_annotator = AudioAnnotator(self.l2_language, human_voice_id=human_voice_id,
                                         audio_type_for_words=audio_type_for_words, audio_type_for_segments=audio_type_for_segments)
        return None if not audio_annotator else audio_annotator.printname_for_voice()

    
            
