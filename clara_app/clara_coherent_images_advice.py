from .clara_coherent_images_utils import (
    get_story_data,
    get_pages,
    get_text,
    get_style_description,
    get_all_element_texts,
    get_config_info_and_callback_from_params,
    project_pathname,
    read_project_txt_file,
    read_project_json_file,
    write_project_txt_file,
    write_project_json_file,
    ImageGenerationError
    )

from .clara_utils import (
    read_json_file,
    write_json_to_file,
    absolute_file_name,
    file_exists,
    directory_exists,
    copy_file,
    )

import json
import os
import sys
import traceback

def get_element_advice(element_name, params):
    check_valid_element_name(element_name, params)
    return get_advice_text('element', element_name, params)

def get_page_advice(page_number, params):
    check_valid_page_number(page_number, params)
    return get_advice_text('page', page_number, params)

def set_element_advice(advice_text, element_name, params):
    check_valid_element_name(element_name, params)
    set_advice_text(advice_text, 'element', element_name, params)

def set_page_advice(advice_text, page_number, params):
    check_valid_page_number(page_number, params)
    return set_advice_text(advice_text, 'page', page_number, params)
 


def get_advice_text(element_or_page, advice_id, params):
    pathname = advice_pathname(element_or_page, params)
    if file_exists(pathname):
        advice_dict = read_json_file(pathname)
        return advice_dict[advice_id] if advice_id in advice_dict else None
    else:
        return None

def set_advice_text(advice_text, element_or_page, advice_id, params):
    pathname = advice_pathname(element_or_page, params)
    if file_exists(pathname):
        advice_dict = read_json_file(pathname)
    else:
        advice_dict = {}
    advice_dict[advice_id] = advice_text
    write_json_to_file(advice_dict, pathname)


def check_valid_element_name(element_name, params):
    element_names = get_all_element_texts(params)
    if not element_name in element_names:
        raise ValueError(f'Unknown element name "{element_name}"')

def check_valid_page_number(page_number, params):
    page_numbers = get_pages(params)
    if not page_number in page_numbers:
        raise ValueError(f'Unknown page number "{page_number}"')

def advice_pathname(element_or_page, params):
    valid_types = ( 'element', 'page' )
    if not element_or_page in valid_types:
        raise ValueError(f'Unknown first argument "{element_or_page}" in advice_pathname, must be one of {valid_types}')

    project_dir = params['project_dir']
    if element_or_page == 'element':
        return project_pathname(project_dir, f'elements/advice.json')
    elif element_or_page == 'page':
        return project_pathname(project_dir, f'pages/advice.json')
    
