from .clara_chatgpt4 import (
    get_api_chatgpt4_response,
    get_api_chatgpt4_image_response,
    get_api_chatgpt4_interpret_image_response,
    interpret_chat_gpt4_response_as_json,
    )

from .clara_utils import (
    read_txt_file,
    write_txt_file,
    read_json_file,
    write_json_to_file,
    make_directory,
    remove_directory,
    absolute_file_name,
    file_exists,
    directory_exists,
    copy_file,
    get_immediate_subdirectories_in_local_directory,
    )

from .constants import (
    SUPPORTED_MODELS_FOR_COHERENT_IMAGES_V2,
    SUPPORTED_PAGE_INTERPRETATION_PROMPTS_FOR_COHERENT_IMAGES_V2,
    SUPPORTED_PAGE_EVALUATION_PROMPTs_FOR_COHERENT_IMAGES_V2,
    )

import json
import os
import sys
import asyncio
import traceback
import unicodedata
from PIL import Image

# Params files

default_params = { 'n_expanded_descriptions': 1,
                   'n_images_per_description': 1,
                   'n_previous_pages': 1,
                   'max_description_generation_rounds': 1,
                   
                   'page_interpretation_prompt': 'default',
                   'page_evaluation_prompt': 'default',
                   
                   'default_model': 'gpt-4o',
                   'generate_description_model': 'gpt-4o',
                   'example_evaluation_model': 'gpt-4o' }

def get_project_params(project_dir):
    params_file = project_params_file(project_dir)
    try:
        return read_json_file(params_file)
    except Exception as e:
        return default_params

def set_project_params(params, project_dir):
    check_valid_project_params(params)
    params_file = project_params_file(project_dir)
    make_root_project_dir(project_dir)
    write_json_to_file(params, params_file)

def project_params_file(project_dir):
    return project_pathname(project_dir, 'params.json')

def check_valid_project_params(params):
    supported_models = [ item[0] for item in SUPPORTED_MODELS_FOR_COHERENT_IMAGES_V2 ]
    
    supported_page_interpretation_prompts = [ item[0] for item in SUPPORTED_PAGE_INTERPRETATION_PROMPTS_FOR_COHERENT_IMAGES_V2 ]
    
    supported_page_evaluation_prompts = [ item[0] for item in SUPPORTED_PAGE_EVALUATION_PROMPTs_FOR_COHERENT_IMAGES_V2 ]
                                                   
    if not isinstance(params, (dict)):
        raise ImageGenerationError(message=f'bad params {params}')
    
    if not 'n_expanded_descriptions' in params or not isinstance(params['n_expanded_descriptions'], (int)):
        raise ImageGenerationError(message=f'bad params {params}: n_expanded_descriptions')
    if not 'n_images_per_description' in params or not isinstance(params['n_images_per_description'], (int)):
        raise ImageGenerationError(message=f'bad params {params}: n_images_per_description')
    if not 'n_previous_pages' in params or not isinstance(params['n_previous_pages'], (int)):
        raise ImageGenerationError(message=f'bad params {params}: n_previous_pages')
    if not 'max_description_generation_rounds' in params or not isinstance(params['max_description_generation_rounds'], (int)):
        raise ImageGenerationError(message=f'bad params {params}: max_description_generation_rounds')

    if not 'page_interpretation_prompt' in params or not params['page_interpretation_prompt'] in supported_page_interpretation_prompts:
        raise ImageGenerationError(message=f'bad params {params}: page_interpretation_prompt')
    if not 'page_evaluation_prompt' in params or not params['page_evaluation_prompt'] in supported_page_evaluation_prompts:
        raise ImageGenerationError(message=f'bad params {params}: page_evaluation_prompt')

    if not 'default_model' in params or not params['default_model'] in supported_models:
        raise ImageGenerationError(message=f'bad params {params}: default_model')
    if not 'generate_description_model' in params or not params['generate_description_model'] in supported_models:
        raise ImageGenerationError(message=f'bad params {params}: generate_description_model')
    if not 'example_evaluation_model' in params or not params['example_evaluation_model'] in supported_models:
        raise ImageGenerationError(message=f'bad params {params}: example_evaluation_model')

def get_style_params_from_project_params(params):
    style_params = {
        'n_expanded_descriptions': params['n_expanded_descriptions'],
        'n_images_per_description': params['n_images_per_description'],
        'models_for_tasks': { 'default': params['default_model'],
                              'generate_style_description': params['generate_description_model'],
                              'style_example_evaluation': params['example_evaluation_model']}
                     }
    return style_params

def get_element_names_params_from_project_params(params):
    element_params = {
        'models_for_tasks': { 'default': params['default_model']}
        }
    return element_params

def get_element_descriptions_params_from_project_params(params, elements_to_generate=None):
    element_params = {
        'n_expanded_descriptions': params['n_expanded_descriptions'],
        'n_images_per_description': params['n_images_per_description'],
        'models_for_tasks': { 'default': params['default_model'],
                              'generate_element_description': params['generate_description_model'],
                              'evaluate_element_image': params['example_evaluation_model']}
        }

    if elements_to_generate:
        element_params['elements_to_generate'] = elements_to_generate
        
    return element_params

def get_page_params_from_project_params(params, pages_to_generate=None):
    page_params = {
        'pages_to_generate': pages_to_generate,
        'n_expanded_descriptions': params['n_expanded_descriptions'],
        'n_images_per_description': params['n_images_per_description'],
        'n_previous_pages': params['n_previous_pages'],
        'max_description_generation_rounds': params['max_description_generation_rounds'],
        
        'page_interpretation_prompt': params['page_interpretation_prompt'],
        'page_evaluation_prompt': params['page_evaluation_prompt'],
        
        'models_for_tasks': { 'default': params['default_model'],
                              'generate_page_description': params['generate_description_model'],
                              'evaluate_page_image': params['example_evaluation_model']}
             }
    if pages_to_generate:
        page_params['pages_to_generate'] = pages_to_generate
    
    return page_params

def score_for_image_dir(image_dir, params):
    return score_for_evaluation_file(f'{image_dir}/evaluation.txt', params)

def score_for_evaluation_file(project_file, params):
    project_dir = params['project_dir']
    
    try:
        evaluation_response = read_project_txt_file(project_dir, project_file)
        score, summary = parse_image_evaluation_response(evaluation_response)
        return score, summary
    except Exception as e:
        return 0, ''

def parse_image_evaluation_response(response):
    lines = response.strip().split('\n')
    score_line = lines[0]
    summary_lines = lines[1:]
    try:
        score = int(score_line)
    except ValueError:
        score = 0  # Default to 0 if parsing fails
    summary = '\n'.join(summary_lines)
    return score, summary                                

def get_style_advice(params):
    project_dir = params['project_dir']
    
    return read_project_txt_file(project_dir, f'style_description.txt')

def set_style_advice(text, project_dir):
    make_root_project_dir(project_dir)
    return write_project_txt_file(text, project_dir, f'style_description.txt')

def get_story_data(params):
    project_dir = params['project_dir']
    
    return read_project_json_file(project_dir, f'story.json')

def set_story_data_from_numbered_page_list(numbered_page_list, project_dir):
    make_root_project_dir(project_dir)
    write_project_json_file(numbered_page_list, project_dir, f'story.json')

def get_pages(params):
    story_data = get_story_data(params)

    pages = [ item['page_number'] for item in story_data ]
               
    return pages

def get_text(params):
    story_data = get_story_data(params)

    text_content = [ item['text'] for item in story_data ]
               
    return '\n'.join(text_content)

def get_style_description(params):
    project_dir = params['project_dir']
    
    return read_project_txt_file(project_dir, f'style/expanded_description.txt')

def get_style_image(params):
    project_dir = params['project_dir']
    
    return f'style/image.jpg'

def overview_file(project_dir):
    return project_pathname(project_dir, 'overview.html')

def get_all_element_texts(params):
    project_dir = params['project_dir']

    if file_exists(project_pathname(project_dir, f'elements/elements.json')):
        element_list = read_project_json_file(project_dir, f'elements/elements.json')
        return [ item['text'] for item in element_list ]
    else:
        return []

def remove_element_name_from_list_of_elements(element_name, params):
    project_dir = params['project_dir']
    
    element_list = read_project_json_file(project_dir, f'elements/elements.json')
    element_list1 = [ item for item in element_list if item['text'] != element_name ]
    write_project_json_file(element_list1, project_dir, f'elements/elements.json')

def get_element_description(element_text, params):
    project_dir = params['project_dir']
    
    name = element_text_to_element_name(element_text, params)
    return read_project_txt_file(project_dir, f'elements/{name}/expanded_description.txt')

def get_element_image(element_text, params):
    project_dir = params['project_dir']
    
    name = element_text_to_element_name(element_text, params)
    return f'elements/{name}/image.jpg'

def remove_top_level_element_directory(params):
    project_dir = params['project_dir']
    
    remove_project_dir(project_dir, f'elements')

def remove_element_directory(element_text, params):
    project_dir = params['project_dir']
    
    name = element_text_to_element_name(element_text, params)
    remove_project_dir(project_dir, f'elements/{name}')

def style_image_name():
    return 'style'

def element_image_name(element_name):
    return f'element_{element_name}'

def page_image_name(page_number):
    return f'page_{page_number}'

def element_text_to_element_name(element_text, params):
    project_dir = params['project_dir']
    
    element_list = read_project_json_file(project_dir, f'elements/elements.json')
    for item in element_list:
        text = item['text']
        if text == element_text:
            name = item['name']
            return name
    raise ImageGenerationError(message=f'Unable to find element "{element_text}"')

def get_page_text(page_number, params):
    story_data = get_story_data(params)
    for item in story_data:
        if page_number == item['page_number']:
            text = item['text']
            return text
    raise ImageGenerationError(message=f'Unable to find page "{page_number}"')

def get_page_description(page_number, params):
    project_dir = params['project_dir']
    
    try:
        return read_project_txt_file(project_dir, f'pages/page{page_number}/expanded_description.txt')
    except Exception as e:
        return None

def get_page_image(page_number, params):
    project_dir = params['project_dir']
    
    return project_pathname(project_dir, f'pages/page{page_number}/image.jpg')

def remove_page_directory(page_number, params):
    project_dir = params['project_dir']
    
    remove_project_dir(project_dir, f'pages/page{page_number}')

# OpenAI calls

async def get_api_chatgpt4_response_for_task(prompt, task_name, params, callback=None):
    config_info = get_config_info_from_params(task_name, params)
    return await get_api_chatgpt4_response(prompt, config_info=config_info, callback=callback)

async def get_api_chatgpt4_image_response_for_task(description, image_file, task_name, params, callback=None):
    config_info = get_config_info_from_params(task_name, params)
    return await get_api_chatgpt4_image_response(description, image_file, config_info=config_info, callback=callback)

async def get_api_chatgpt4_interpret_image_response_for_task(prompt, image_file, task_name, params, callback=None):
    config_info = get_config_info_from_params(task_name, params)
    return await get_api_chatgpt4_interpret_image_response(prompt, image_file, config_info=config_info, callback=callback)

def get_config_info_from_params(task_name, params):

    if task_name in params['models_for_tasks']:
        model = params['models_for_tasks'][task_name]
    elif 'default' in params['models_for_tasks']:
        model = params['models_for_tasks']['default']
    else:
        model = None

    config_info = params['config_info'] if 'config_info' in params else {}

    if model:
        config_info['gpt_model'] = model

    return config_info

# Costs

def api_calls_to_cost(api_calls):
    return sum([ api_call.cost for api_call in api_calls ])

def combine_cost_dicts(*dicts):
    """
    Combine multiple cost dictionaries by summing the values for matching keys.

    Parameters:
    *dicts: Variable number of dictionaries with task names as keys and costs as values.

    Returns:
    A single dictionary with the combined costs.
    """
    combined_dict = {}
    for d in dicts:
        for key, value in d.items():
            if key in combined_dict:
                combined_dict[key] += value
            else:
                combined_dict[key] = value
    return combined_dict

def print_cost_dict(cost_dict):
    if not 'total' in cost_dict:
        cost_dict['total'] = sum([ cost_dict[key] for key in cost_dict ])
    for key in cost_dict:
        print(f'{key}: {cost_dict[key]:2f}')
        
def write_project_cost_file(cost_dict, project_dir, pathname):
    if not 'total' in cost_dict:
        cost_dict['total'] = sum([ cost_dict[key] for key in cost_dict ])
    write_project_json_file(cost_dict, project_dir, pathname)



# Project files etc

def project_pathname(project_dir, pathname):
    return absolute_file_name(os.path.join(project_dir, pathname))

def make_root_project_dir(project_dir):
    make_directory(project_dir, parents=True, exist_ok=True)

def make_project_dir(project_dir, directory):
    make_directory(project_pathname(project_dir, directory), parents=True, exist_ok=True)

def remove_project_dir(project_dir, directory):
    remove_directory(project_pathname(project_dir, directory))

def read_project_txt_file(project_dir, pathname):
    return read_txt_file(project_pathname(project_dir, pathname))

def read_project_json_file(project_dir, pathname):
    return read_json_file(project_pathname(project_dir, pathname))

def write_project_txt_file(text, project_dir, pathname):
    write_txt_file(text, project_pathname(project_dir, pathname))

def write_project_json_file(data, project_dir, pathname):
    write_json_to_file(data, project_pathname(project_dir, pathname))

class ImageGenerationError(Exception):
    def __init__(self, message = 'Image generation error'):
        self.message = message

