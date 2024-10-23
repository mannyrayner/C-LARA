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
    absolute_file_name,
    file_exists,
    directory_exists,
    copy_file,
    get_immediate_subdirectories_in_local_directory,
    )

import json
import os
import sys
import asyncio
import traceback
import unicodedata
from PIL import Image


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


def get_story_data(params):
    project_dir = params['project_dir']
    
    return read_project_json_file(project_dir, f'story.json')

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

def get_all_element_texts(params):
    project_dir = params['project_dir']
    
    element_list = read_project_json_file(project_dir, f'elements/elements.json')
    return [ item['text'] for item in element_list ]

def get_element_description(element_text, params):
    project_dir = params['project_dir']
    
    element_list = read_project_json_file(project_dir, f'elements/elements.json')
    for item in element_list:
        text = item['text']
        if text == element_text:
            name = item['name']
            return read_project_txt_file(project_dir, f'elements/{name}/expanded_description.txt')
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
    
    return read_project_txt_file(project_dir, f'pages/page{page_number}/image.txt')

# OpenAI calls

async def get_api_chatgpt4_response_for_task(prompt, task_name, params):
    config_info, callback = get_config_info_and_callback_from_params(task_name, params)
    return await get_api_chatgpt4_response(prompt, config_info=config_info, callback=callback)

async def get_api_chatgpt4_image_response_for_task(description, image_file, task_name, params):
    config_info, callback = get_config_info_and_callback_from_params(task_name, params)
    return await get_api_chatgpt4_image_response(description, image_file, config_info=config_info, callback=callback)

async def get_api_chatgpt4_interpret_image_response_for_task(prompt, image_file, task_name, params):
    config_info, callback = get_config_info_and_callback_from_params(task_name, params)
    return await get_api_chatgpt4_interpret_image_response(prompt, image_file, config_info=config_info, callback=callback)

def get_config_info_and_callback_from_params(task_name, params):

    if task_name in params['models_for_tasks']:
        model = params['models_for_tasks'][task_name]
    elif 'default' in params['models_for_tasks']:
        model = params['models_for_tasks']['default']
    else:
        model = None

    config_info = params['config_info'] if 'config_info' in params else {}

    if model:
        config_info['gpt_model'] = model

    callback = params['callback'] if 'callback' in params else None

    return config_info, callback

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

def make_project_dir(project_dir, directory):
    make_directory(project_pathname(project_dir, directory), parents=True, exist_ok=True)

def read_project_txt_file(project_dir, pathname):
    return read_txt_file(project_pathname(project_dir, pathname))

def read_project_json_file(project_dir, pathname):
    return read_json_file(project_pathname(project_dir, pathname))

def write_project_txt_file(text, project_dir, pathname):
    write_txt_file(text, project_pathname(project_dir, pathname))

def write_project_json_file(text, project_dir, pathname):
    write_json_to_file(text, project_pathname(project_dir, pathname))

class ImageGenerationError(Exception):
    def __init__(self, message = 'Image generation error'):
        self.message = message

