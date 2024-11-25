from .clara_coherent_images_utils import (
    get_story_data,
    get_pages,
    get_text,
    get_style_description,
    get_all_element_texts,
    make_root_project_dir,
    get_config_info_from_params,
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
    page_number = int(page_number)
    #print(f'get_page_advice({page_number}, {params})')
    check_valid_page_number(page_number, params)
    result = get_advice_text('page', str(page_number), params)
    #print(f'result = {result}')
    return result

def set_element_advice(advice_text, element_name, params):
    check_valid_element_name(element_name, params)
    set_advice_text(advice_text, 'element', element_name, params)

def set_page_advice(advice_text, page_number, params):
    page_number = int(page_number)
    project_dir = params['project_dir']
    make_project_dir(project_dir, 'pages')
    check_valid_page_number(page_number, params)
    return set_advice_text(advice_text, 'page', str(page_number), params)
 
def get_advice_text(element_or_page, advice_id, params):
    pathname = advice_pathname(element_or_page, params)
    #print(f'get_advice_text({element_or_page}, {advice_id}, {params})')
    #print(f'Reading from {pathname}')
    if file_exists(pathname):
        advice_dict = read_json_file(pathname)
        #pprint.pprint(advice_dict)
        return advice_dict[advice_id] if advice_id in advice_dict else ''
    else:
        return ''

def set_advice_text(advice_text, element_or_page, advice_id, params):
    pathname = advice_pathname(element_or_page, params)
    #print(f'set_advice_text({advice_text}, {element_or_page}, {advice_id}, {params}')
    #print(f'Writing to {pathname}')
    if file_exists(pathname):
        advice_dict = read_json_file(pathname)
    else:
        advice_dict = {}
    advice_dict[advice_id] = advice_text
    #pprint.pprint(advice_dict)
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
    
