from .clara_classes import InternalCLARAError
from .clara_utils import absolute_local_file_name, basename, make_tmp_file, make_local_directory, remove_local_directory
from .clara_utils import read_json_local_file, make_zipfile, unzip_file, post_task_update
from .clara_audio_annotator import AudioAnnotator
from .clara_audio_repository import AudioRepository
from .clara_image_repository import ImageRepository

import os
import tempfile
import traceback

def create_export_zipfile(project_directory, audio_metadata, image_metadata, zipfile, callback=None):
    try:
        tmp_dir = tempfile.mkdtemp()
        copy_project_directory_to_tmp_dir(project_directory, tmp_dir, callback=callback)
        copy_audio_data_to_tmp_dir(audio_metadata, tmp_dir, callback=callback)
        copy_image_data_to_tmp_dir(image_metadata, tmp_dir, callback=callback)
        make_zipfile(tmp_dir, zipfile, callback=callback)
        return True
    except Exception as e:
        post_task_update(callback, f'*** Error when trying to create zipfile for project')
        error_message = f'"{str(e)}"\n{traceback.format_exc()}'
        post_task_update(callback, error_message)
        return False
    finally:
        # Remove the tmp dir once we've used it
        if local_directory_exists(tmp_dir):
            remove_local_directory(tmp_dir)

def copy_project_directory_to_tmp_dir(project_directory, tmp_dir, callback=None):
    tmp_project_dir = os.path.join(tmp_dir, 'project_dir')
    tmp_sub_project_dir = os.path.join(tmp_project_dir, 'sub_project_dir')
    copy_directory_to_local_directory(project_directory, tmp_sub_project_dir)

def copy_audio_data_to_tmp_dir(audio_metadata, tmp_dir, callback=None):
    return

def copy_image_data_to_tmp_dir(image_metadata, tmp_dir, callback=None):
    return
