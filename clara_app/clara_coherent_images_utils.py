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

from .clara_classes import (
    ImageGenerationError,
    )

from .constants import (
    SUPPORTED_MODELS_FOR_COHERENT_IMAGES_V2,
    SUPPORTED_MODELS_FOR_COHERENT_IMAGES_V2_WITH_DEFAULT,
    SUPPORTED_PAGE_INTERPRETATION_PROMPTS_FOR_COHERENT_IMAGES_V2,
    SUPPORTED_PAGE_EVALUATION_PROMPTs_FOR_COHERENT_IMAGES_V2,

    PLACEHOLDER_TEXT_FOR_UPLOADED_IMAGE_DESCRIPTION,
    PLACEHOLDER_TEXT_FOR_UPLOADED_IMAGE_EVALUATION,
    PLACEHOLDER_TEXT_FOR_UPLOADED_IMAGE_INTERPRETATION,
    )

import json
import os
import glob
import sys
import asyncio
import traceback
import unicodedata
from pathlib import Path
from PIL import Image

# Params files

project_params_for_simple_clara = { 'n_expanded_descriptions': 1,
                                    'n_images_per_description': 3,
                                    'n_previous_pages': 0,
                                    'max_description_generation_rounds': 1,

                                    'ai_checking_of_images': 'off',
                                    'text_language': 'english',

                                    'page_interpretation_prompt': 'with_context_v3_objective',
                                    'page_evaluation_prompt': 'with_context_lenient',

                                    'default_model': 'gpt-4o',
                                    'generate_element_names_model': 'gpt-4o',
                                    'generate_description_model': 'gpt-4o',
                                    'example_evaluation_model': 'gpt-4o' }

default_params = project_params_for_simple_clara

def get_project_params(project_dir):
    params_file = project_params_file(project_dir)
    try:
        return read_json_file(params_file)
    except Exception as e:
        return default_params

def set_project_params(params, project_dir):
    check_valid_project_params(params)
    params['project_dir'] = absolute_file_name(project_dir)
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

    if not 'ai_checking_of_images' in params or not params['ai_checking_of_images'] in ( 'on', 'off' ):
        raise ImageGenerationError(message=f'bad params {params}: ai_checking_of_images')

    if not 'page_interpretation_prompt' in params or not params['page_interpretation_prompt'] in supported_page_interpretation_prompts:
        raise ImageGenerationError(message=f'bad params {params}: page_interpretation_prompt')
    if not 'page_evaluation_prompt' in params or not params['page_evaluation_prompt'] in supported_page_evaluation_prompts:
        raise ImageGenerationError(message=f'bad params {params}: page_evaluation_prompt')

    if not 'default_model' in params or not params['default_model'] in supported_models:
        raise ImageGenerationError(message=f'bad params {params}: default_model')
    if not 'generate_element_names_model' in params or not params['generate_element_names_model'] in supported_models:
        raise ImageGenerationError(message=f'bad params {params}: generate_element_names_model')
    if not 'generate_description_model' in params or not params['generate_description_model'] in supported_models:
        raise ImageGenerationError(message=f'bad params {params}: generate_description_model')
    if not 'example_evaluation_model' in params or not params['example_evaluation_model'] in supported_models:
        raise ImageGenerationError(message=f'bad params {params}: example_evaluation_model')

def get_style_params_from_project_params(params):
    style_params = {
        'n_expanded_descriptions': params['n_expanded_descriptions'],
        'n_images_per_description': params['n_images_per_description'],
        'ai_checking_of_images': params['ai_checking_of_images'] if 'ai_checking_of_images' in params else 'on',
        'text_language': params['text_language'] if 'text_language' in params else 'english',
        'models_for_tasks': { 'default': params['default_model'],
                              'generate_style_description': params['generate_description_model'],
                              'style_example_evaluation': params['example_evaluation_model']}
                     }
    return style_params

def get_element_names_params_from_project_params(params):
    if 'generate_element_names_model' in params:
        generate_element_names_model = params['generate_element_names_model']
    else:
        generate_element_names_model = default_params['generate_element_names_model']
    element_params = {
        'models_for_tasks': { 'default': params['default_model'],
                              'generate_element_names':generate_element_names_model}
        }
    return element_params

def get_element_descriptions_params_from_project_params(params, elements_to_generate=None):
    element_params = {
        'n_expanded_descriptions': params['n_expanded_descriptions'],
        'n_images_per_description': params['n_images_per_description'],
        'ai_checking_of_images': params['ai_checking_of_images'] if 'ai_checking_of_images' in params else 'on',
        'text_language': params['text_language'] if 'text_language' in params else 'english',
        'models_for_tasks': { 'default': params['default_model'],
                              'generate_element_names': params['generate_element_names_model'],
                              'generate_element_description': params['generate_description_model'],
                              'evaluate_element_image': params['example_evaluation_model']}
        }

    if elements_to_generate:
        element_params['elements_to_generate'] = elements_to_generate
        
    return element_params

def get_page_params_from_project_params(params, pages_to_generate=None):
    page_params = {
        'n_expanded_descriptions': params['n_expanded_descriptions'],
        'n_images_per_description': params['n_images_per_description'],
        'n_previous_pages': params['n_previous_pages'],
        'max_description_generation_rounds': params['max_description_generation_rounds'],

        'ai_checking_of_images': params['ai_checking_of_images'] if 'ai_checking_of_images' in params else 'on',
        'text_language': params['text_language'] if 'text_language' in params else 'english',
        
        'page_interpretation_prompt': params['page_interpretation_prompt'],
        'page_evaluation_prompt': params['page_evaluation_prompt'],
        
        'models_for_tasks': { 'default': params['default_model'],
                              'generate_page_description': params['generate_description_model'],
                              'evaluate_page_image': params['example_evaluation_model']}
             }
    if pages_to_generate:
        page_params['pages_to_generate'] = pages_to_generate
    
    return page_params

def no_ai_checking_of_images(params):
    return 'ai_checking_of_images' in params and params['ai_checking_of_images'] == 'off'

NULL_IMAGE_INTERPRETATION = """No image interpretation produced, AI checking is switched off.
"""

NULL_IMAGE_EVALUATION = """1
No image evaluation produced, AI checking is switched off.
"""

def existing_description_version_directories_and_first_unused_number_for_style(params):
    project_dir = params['project_dir']

    description_version_number = 0
    existing_description_directories = []
    
    while True:
        description_directory = f'style/description_v{description_version_number}'
        if not directory_exists(project_pathname(project_dir, description_directory)):
            return existing_description_directories, description_version_number
        else:
            existing_description_directories.append(description_directory)
            description_version_number += 1

def existing_description_version_directories_and_first_unused_number_for_element(element_name, params):
    project_dir = params['project_dir']

    description_version_number = 0
    existing_description_directories = []
    
    while True:
        description_directory = f'elements/{element_name}/description_v{description_version_number}'
        if not directory_exists(project_pathname(project_dir, description_directory)):
            return existing_description_directories, description_version_number
        else:
            existing_description_directories.append(description_directory)
            description_version_number += 1

def existing_description_version_directories_and_first_unused_number_for_page(page_number, params):
    project_dir = params['project_dir']

    description_version_number = 0
    existing_description_directories = []
    
    while True:
        description_directory = f'pages/page{page_number}/description_v{description_version_number}'
        if not directory_exists(project_pathname(project_dir, description_directory)):
            return existing_description_directories, description_version_number
        else:
            existing_description_directories.append(description_directory)
            description_version_number += 1

def score_for_image_dir(image_dir, params):
    return score_for_evaluation_file(f'{image_dir}/evaluation.txt', params)

def image_dir_shows_content_policy_violation(image_dir, params):
    project_dir = params['project_dir']
    
    error_file = project_pathname(project_dir, f'{image_dir}/error.txt')
    
    if not file_exists(error_file):
        return False

    error_file_content = read_project_txt_file(project_dir, error_file)

    return 'content_policy_violation' in error_file_content

def description_dir_shows_only_content_policy_violations(description_dir, params):
    """
    Returns True if *every* image_v* subdirectory under `description_dir`
    indicates a content policy violation. If at least one subdirectory
    does not show a violation (or if there are no image_v* directories),
    returns False.
    """
    project_dir = params['project_dir']

    # Find all subdirectories named image_v*
    # e.g. pages/page3/image_v2, elements/cat/image_v3, etc.
    pattern = os.path.join(project_dir, description_dir, "image_v*")
    candidate_dirs = glob.glob(pattern)

##    print(f'{description_dir}: candidate_dirs: {candidate_dirs}')

    # If there aren't any image_v* subdirectories at all, we can decide:
    # - Return False, meaning "not purely policy-violating," or
    # - Return True. Usually it's more helpful to say False in that case,
    #   since "no images" is different from "images exist but are all violating."
    if not candidate_dirs:
        return False

    for subdir in candidate_dirs:
        if os.path.isdir(subdir):
            # Convert absolute path back to a project-relative path
            rel_subdir = os.path.relpath(subdir, project_dir)
            # If ANY subdir does NOT show a violation => overall return False
            if not image_dir_shows_content_policy_violation(rel_subdir, params):
##                print(f'{rel_subdir}: no content policy violation')
                return False
##            else:
##                print(f'{rel_subdir}: content policy violation')

    # If we get here, all image_v* subdirs existed and show violation
    return True

def content_dir_shows_only_content_policy_violations(content_dir, params):
    """
    For a given content directory (e.g. pages/page2 or elements/The_virtuous_narrator),
    check if every 'description_v*' subdirectory there is flagged as showing
    content policy violations. If all of them show policy violations, return True;
    otherwise, return False.

    If there are no 'description_v*' subdirectories at all, return False.
    """
    project_dir = params['project_dir']
    
    # Find subdirectories named description_v*
    pattern = os.path.join(project_dir, content_dir, "description_v*")
    candidate_dirs = glob.glob(pattern)

    # If no description_v* subdirectories exist, decide how to handle
    if not candidate_dirs:
        return False  # By default, "no subdirs" is not "all are violating."

    for subdir in candidate_dirs:
        if os.path.isdir(subdir):
            # Convert absolute path to relative for your existing function
            rel_subdir = os.path.relpath(subdir, project_dir)
            if not description_dir_shows_only_content_policy_violations(rel_subdir, params):
                # If any subdir is NOT purely policy-violating => overall False
                return False

    # If all description_v* subdirs exist and show policy violations, return True
    return True

# -----------------------------------------------

def score_description_dir_representative(description_dir, image_dirs, params):
    project_dir = params['project_dir']
    
    scores_and_images_dirs = [ ( score_for_image_dir(image_dir, params)[0], image_dir )
                               for image_dir in image_dirs ]
    scores = [ item[0] for item in scores_and_images_dirs ]
    av_score = sum(scores) / len(scores)

    # Find the image most representative of the average score

    closest_match = 10.0
    closest_image_file = None
    closest_interpretation_file = None
    closest_evaluation_file = None

    for score, image_dir in scores_and_images_dirs:
        image_file = project_pathname(project_dir, f'{image_dir}/image.jpg')
        interpretation_file = project_pathname(project_dir, f'{image_dir}/image_interpretation.txt')
        evaluation_file = project_pathname(project_dir, f'{image_dir}/evaluation.txt')
        if abs(score - av_score ) < closest_match and file_exists(image_file) and file_exists(evaluation_file):
            closest_match = abs(score - av_score )
##            closest_image_file = image_file
##            closest_interpretation_file = interpretation_file
##            closest_evaluation_file = evaluation_file
            closest_image_file = f'{image_dir}/image.jpg'
            closest_interpretation_file = f'{image_dir}/image_interpretation.txt'
            closest_evaluation_file = f'{image_dir}/evaluation.txt'

    description_dir_info = { 'av_score': av_score,
                             'image': closest_image_file,
                             'interpretation': closest_interpretation_file,
                             'evaluation': closest_evaluation_file}
                                                                   
    image_info_file = f'{description_dir}/image_info.json'
    write_project_json_file(description_dir_info, project_dir, image_info_file)
    #print(f"write_project_json_file({description_dir_info}, {project_dir}, {image_info_file})")

    if closest_image_file and closest_interpretation_file and closest_evaluation_file:
        copy_file(project_pathname(project_dir, closest_image_file), project_pathname(project_dir, f'{description_dir}/image.jpg'))
        copy_file(project_pathname(project_dir, closest_interpretation_file), project_pathname(project_dir, f'{description_dir}/interpretation.txt'))
        copy_file(project_pathname(project_dir, closest_evaluation_file), project_pathname(project_dir, f'{description_dir}/evaluation.txt'))

def score_description_dir_best(description_dir, image_dirs, params):
    project_dir = params['project_dir']
    
    scores_and_images_dirs = [ ( score_for_image_dir(image_dir, params)[0], image_dir )
                               for image_dir in image_dirs ]

    # Find the image with the best fit

    best_score = -1
    best_image_file = None
    best_interpretation_file = None
    best_evaluation_file = None

    for score, image_dir in scores_and_images_dirs:
        image_file = project_pathname(project_dir, f'{image_dir}/image.jpg')
        interpretation_file = project_pathname(project_dir, f'{image_dir}/image_interpretation.txt')
        evaluation_file = project_pathname(project_dir, f'{image_dir}/evaluation.txt')
        if score > best_score and file_exists(image_file):
            best_score = score
##            best_image_file = image_file
##            best_interpretation_file = interpretation_file
##            best_evaluation_file = evaluation_file
            best_image_file = image_file
            best_interpretation_file = interpretation_file
            best_evaluation_file = evaluation_file

    description_dir_info = { 'best_score': best_score,
                             'image': best_image_file,
                             'interpretation': best_interpretation_file,
                             'evaluation': best_evaluation_file }
                                                                   
    write_project_json_file(description_dir_info, project_dir, f'{description_dir}/image_info.json')

    if best_image_file and best_interpretation_file and best_evaluation_file:
        copy_file(project_pathname(project_dir, best_image_file), project_pathname(project_dir, f'{description_dir}/image.jpg'))
        copy_file(project_pathname(project_dir, best_interpretation_file), project_pathname(project_dir, f'{description_dir}/interpretation.txt'))
        copy_file(project_pathname(project_dir, best_evaluation_file), project_pathname(project_dir, f'{description_dir}/evaluation.txt'))

def element_score_for_description_dir(description_dir, params):
    project_dir = params['project_dir']
    image_info_file = project_pathname(project_dir, f'{description_dir}/image_info.json')
    if file_exists(image_info_file):
        return read_json_file(image_info_file)['av_score']
    else:
        return 0.0

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

    try:
        return read_project_json_file(project_dir, f'story.json')
    except Exception as e:
        return []


def set_story_data_from_numbered_page_list(numbered_page_list, project_dir):
    make_root_project_dir(project_dir)
    write_project_json_file(numbered_page_list, project_dir, f'story.json')

def get_pages(params):
    story_data = get_story_data(params)

    try:
        pages = [ item['page_number'] for item in story_data ]   
        return pages
    except Exception as e:
        return []

def get_text(params):
    try:
        story_data = get_story_data(params)
        text_content = [ item['text'] for item in story_data ]      
        return '\n'.join(text_content)
    except Exception as e:
        return ''

def get_text_language(params):
    return params['text_language'] if 'text_language' in params else 'english'

def get_style_description(params):
    project_dir = params['project_dir']

    try:
        return read_project_txt_file(project_dir, f'style/expanded_description.txt')
    except Exception as e:
        return ''

def get_style_image(params):
    project_dir = params['project_dir']

    return f'style/image.jpg'

def overview_file(project_dir):
    return project_pathname(project_dir, 'overview.html')

def element_text_to_element_name(element_text):
    out_str = ''
    for char in element_text:
        out_str += '_' if char.isspace() or unicodedata.category(char).startswith('P') else char
    return out_str

##def element_text_to_element_name(element_text, params):
##    project_dir = params['project_dir']
##    
##    element_list = read_project_json_file(project_dir, f'elements/elements.json')
##    for item in element_list:
##        text = item['text']
##        if text == element_text:
##            name = item['name']
##            return name
##    raise ImageGenerationError(message=f'Unable to find element "{element_text}"')

def element_name_to_element_text(element_name, params):
    project_dir = params['project_dir']
    
    element_list = read_project_json_file(project_dir, f'elements/elements.json')
    for item in element_list:
        name = item['name']
        if name == element_name:
            text = item['text']
            return text
    raise ImageGenerationError(message=f'Unable to find element with name "{element_name}"')
    
def get_all_element_names_and_texts(params):
    project_dir = params['project_dir']
    
    if file_exists(project_pathname(project_dir, f'elements/elements.json')):
        return read_project_json_file(project_dir, f'elements/elements.json')
    else:
        return []

def get_all_element_texts(params):
    return [ item['text'] for item in get_all_element_names_and_texts(params) ]

def remove_element_name_from_list_of_elements(element_text, params):
    project_dir = params['project_dir']
    
    element_list = read_project_json_file(project_dir, f'elements/elements.json')
    element_list1 = [ item for item in element_list if item['text'] != element_text ]
    write_project_json_file(element_list1, project_dir, f'elements/elements.json')

def add_element_name_to_list_of_elements(element_text, params):
    project_dir = params['project_dir']
    element_name = element_text_to_element_name(element_text)

    element_list = get_all_element_names_and_texts(params)
    element_list.append({ 'text': element_text, 'name': element_name })
    write_project_json_file(element_list, project_dir, f'elements/elements.json')

def get_element_description(element_text, params):
    project_dir = params['project_dir']
    
    name = element_text_to_element_name(element_text)
    return read_project_txt_file(project_dir, f'elements/{name}/expanded_description.txt')

def get_element_image(element_text, params):
    project_dir = params['project_dir']
    
    name = element_text_to_element_name(element_text)
    return f'elements/{name}/image.jpg'

def get_all_element_images(params):
    element_texts = get_all_element_texts(params)

    return [ get_element_image(element_text, params) for element_text in element_texts ]

def remove_top_level_element_directory(params):
    project_dir = params['project_dir']
    
    remove_project_dir(project_dir, f'elements')

def remove_element_directory(element_text, params):
    project_dir = params['project_dir']
    
    #name = element_text_to_element_name(element_text, params)
    name = element_text_to_element_name(element_text)
    remove_project_dir(project_dir, f'elements/{name}')

def style_image_name():
    return 'style'

def element_image_name(element_name):
    return f'element_{element_name}'

def page_image_name(page_number):
    return f'page_{page_number}'

def get_expanded_description_text_for_page_version(project_dir, page_number, d_idx):
    rel_pathname = f'pages/page{page_number}/description_v{d_idx}/expanded_description.txt'
    try:
        return read_project_txt_file(project_dir, rel_pathname)
    except Exception as e:
        return ''

def style_directory(params):
    project_dir = params['project_dir']
    return project_pathname(project_dir, 'style')

def relative_style_directory(params):
    return 'style'

def element_directory(element_text, params):
    project_dir = params['project_dir']
    #element_name = element_text_to_element_name(element_text, params)
    element_name = element_text_to_element_name(element_text)
    return project_pathname(project_dir, f'elements/{element_name}')

def relative_element_directory(element_text, params):
    element_name = element_text_to_element_name(element_text)
    return f'elements/{element_name}'

def element_directory_for_element_name(element_name, params):
    project_dir = params['project_dir']
    return project_pathname(project_dir, f'elements/{element_name}')

def page_directory(page_number, params):
    project_dir = params['project_dir']
    return project_pathname(project_dir, f'pages/page{page_number}')

def relative_page_directory(page_number, params):
    return f'pages/page{page_number}'

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

def get_all_page_images(params):
    page_numbers = get_pages(params)

    return [ get_page_image(page_number, params) for page_number in page_numbers ]

def get_relative_page_image(page_number):    
    return f'pages/page{page_number}/image.jpg'

def get_all_relative_page_images(params):
    page_numbers = get_pages(params)

    return [ get_relative_page_image(page_number) for page_number in page_numbers ]

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

def sanitize_path(project_dir, pathname):
    """
    Sanitize a pathname read from a JSON file, ensuring it is relative to project_dir.

    Args:
        project_dir (str or Path): The path to the project directory.
        pathname (str or Path): The pathname to sanitize.

    Returns:
        Path: The sanitized path.
    """
    project_dir = Path(project_dir)
    pathname = Path(pathname)

    # If pathname is absolute, make it relative to project_dir or 'coherent_images_v2_project_dir'
    if pathname.is_absolute():
        try:
            relative_path = pathname.relative_to(project_dir)
            return str(relative_path.as_posix())
        except ValueError:
            # Attempt to find 'coherent_images_v2_project_dir' in the path
            coherent_images_dir_name = 'coherent_images_v2_project_dir'
            parts = pathname.parts
            if coherent_images_dir_name in parts:
                index = parts.index(coherent_images_dir_name)
                relative_parts = parts[(index + 1):]
                return str(Path(*relative_parts).as_posix())
            else:
                raise ValueError(f"Cannot sanitize path: {pathname}")
    else:
        return pathname

def project_pathname(project_dir, pathname):
    project_dir = str(project_dir) #In case it's a Path
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

