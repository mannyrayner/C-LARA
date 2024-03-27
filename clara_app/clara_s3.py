
from .clara_utils import copy_directory_to_s3, copy_directory_from_s3

def sync_prompt_templates_to_s3():
    copy_directory_to_s3('$CLARA/prompt_templates')

def sync_prompt_templates_from_s3():
    copy_directory_from_s3('$CLARA/prompt_templates')
