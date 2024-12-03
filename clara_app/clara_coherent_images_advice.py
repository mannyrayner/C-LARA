from .clara_coherent_images_utils import (
    get_story_data,
    get_pages,
    get_text,
    get_style_description,
    get_all_element_texts,
    make_root_project_dir,
    get_config_info_from_params,
    element_text_to_element_name,
    project_pathname,
    make_project_dir,
    read_project_txt_file,
    read_project_json_file,
    write_project_txt_file,
    write_project_json_file,
    ImageGenerationError
    )

from .clara_utils import (
    read_json_file,
    write_json_to_file,
    read_txt_file,
    write_txt_file,
    absolute_file_name,
    file_exists,
    directory_exists,
    copy_file,
    )

import json
import os
import sys
import traceback
import pprint

def get_style_advice(params):
    project_dir = params['project_dir']
    
    return read_project_txt_file(project_dir, f'style_description.txt')

def set_style_advice(text, project_dir):
    make_root_project_dir(project_dir)
    return write_project_txt_file(text, project_dir, f'style_description.txt')

def get_element_advice(element_name, params):
    check_valid_element_name(element_name, params)
    return get_advice_text('element', element_name, params)

def get_page_advice(page_number, params):
    page_number = page_number
    check_valid_page_number(page_number, params)
    result = get_advice_text('page', page_number, params)
    return result

def set_element_advice(advice_text, element_name, params):
    check_valid_element_name(element_name, params)
    set_advice_text(advice_text, 'element', element_name, params)

def set_page_advice(advice_text, page_number, params):
    page_number = int(page_number)
    project_dir = params['project_dir']
    make_project_dir(project_dir, 'pages')
    check_valid_page_number(page_number, params)
    return set_advice_text(advice_text, 'page', page_number, params)
 
def get_advice_text(element_or_page, advice_id, params):
    project_dir = params['project_dir']
    pathname = project_pathname(project_dir, advice_pathname(advice_id, element_or_page, params))
    if file_exists(pathname):
        advice_text = read_txt_file(pathname)
        #print(f'Read advice text "{advice_text}" from {pathname}')
        return advice_text
    else:
        return ''

def set_advice_text(advice_text, element_or_page, advice_id, params):
    project_dir = params['project_dir']
    directory = advice_dir(advice_id, element_or_page, params)
    file = advice_pathname(advice_id, element_or_page, params)

    make_project_dir(project_dir, directory)
    write_project_txt_file(advice_text, project_dir, file)
    #print(f'Written advice text "{advice_text}" to {pathname}')


def check_valid_element_name(element_name, params):
    element_names = get_all_element_texts(params)
    if not element_name in element_names:
        raise ValueError(f'Unknown element name "{element_name}"')

def check_valid_page_number(page_number, params):
    page_numbers = get_pages(params)
    if not page_number in page_numbers:
        raise ValueError(f'Unknown page number "{page_number}"')

def advice_pathname(advice_id, element_or_page, params):
    directory = advice_dir(advice_id, element_or_page, params)
    return f'{directory}/advice.txt'
    
def advice_dir(advice_id, element_or_page, params):
    valid_types = ( 'element', 'page' )
    if not element_or_page in valid_types:
        raise ValueError(f'Unknown first argument "{element_or_page}" in advice_dir, must be one of {valid_types}')

    if element_or_page == 'element':
        element_name = element_text_to_element_name(advice_id, params)
        return f'elements/{element_name}'
    elif element_or_page == 'page':
        return f'pages/page{advice_id}'
