
from .clara_coherent_images_prompt_templates import (
    get_prompt_template,
    )

from .clara_coherent_images_evaluate_prompts import (
    human_evaluation,
    test_prompts_for_interpretation_and_evaluation,
    analyse_human_ai_agreement_for_prompt_test,
    generate_prompt_evaluation_html_report,
    )

from .clara_chatgpt4 import (
    interpret_chat_gpt4_response_as_json,
    )

from .clara_coherent_images_utils import (
    score_for_image_dir,
    score_for_evaluation_file,
    parse_image_evaluation_response,
    get_story_data,
    get_pages,
    get_text,
    get_style_description,
    get_all_element_texts,
    get_element_description,
    get_page_text,
    get_page_description,
    get_page_image,
    get_api_chatgpt4_response_for_task,
    get_api_chatgpt4_image_response_for_task,
    get_api_chatgpt4_interpret_image_response_for_task,
    get_config_info_and_callback_from_params,
    api_calls_to_cost,
    combine_cost_dicts,
    print_cost_dict,
    write_project_cost_file,
    project_pathname,
    make_project_dir,
    read_project_txt_file,
    read_project_json_file,
    write_project_txt_file,
    write_project_json_file,
    ImageGenerationError,
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

# Test with La Fontaine 'Le Corbeau et le Renard'

def test_la_fontaine_style():
    params = { 'project_dir': '$CLARA/coherent_images/LeCorbeauEtLeRenard',
               'n_expanded_descriptions': 3,
               'n_images_per_description': 3,
               'models_for_tasks': { 'default': 'gpt-4o' }
               }
    cost_dict = asyncio.run(process_style(params))
    print_cost_dict(cost_dict)

def test_la_fontaine_style_o1():
    params = { 'project_dir': '$CLARA/coherent_images/LeCorbeauEtLeRenard_o1',
               'n_expanded_descriptions': 3,
               'n_images_per_description': 3,
               'models_for_tasks': { 'default': 'gpt-4o',
                                     'generate_style_description': 'o1-mini' }
               }
    cost_dict = asyncio.run(process_style(params))
    print_cost_dict(cost_dict)


def test_la_fontaine_elements():
    params = { 'project_dir': '$CLARA/coherent_images/LeCorbeauEtLeRenard',
               'n_expanded_descriptions': 2,
               'n_images_per_description': 2,
               'n_elements_to_expand': 'all',
               'keep_existing_elements': True,
               'models_for_tasks': { 'default': 'gpt-4o' }
               }
    cost_dict = asyncio.run(process_elements(params))
    print_cost_dict(cost_dict)

def test_la_fontaine_elements_o1():
    params = { 'project_dir': '$CLARA/coherent_images/LeCorbeauEtLeRenard_o1',
               'n_expanded_descriptions': 2,
               'n_images_per_description': 2,
               'n_elements_to_expand': 'all',
               'keep_existing_elements': True,
               'models_for_tasks': { 'default': 'gpt-4o',
                                     'generate_element_description': 'o1-mini' }
               }
    cost_dict = asyncio.run(process_elements(params))
    print_cost_dict(cost_dict)

def test_la_fontaine_pages():
    params = { 'project_dir': '$CLARA/coherent_images/LeCorbeauEtLeRenard',
               'n_expanded_descriptions': 2,
               'max_description_generation_rounds': 4,
               'n_images_per_description': 3,
               'n_pages': 'all',
               'n_previous_pages': 2,
               'keep_existing_pages': True,
               'models_for_tasks': { 'default': 'gpt-4o' }
               }
    cost_dict = asyncio.run(process_pages(params))
    print_cost_dict(cost_dict)

def test_la_fontaine_pages_o1():
    params = { 'project_dir': '$CLARA/coherent_images/LeCorbeauEtLeRenard_o1',
               'n_expanded_descriptions': 2,
               'max_description_generation_rounds': 1,
               'n_images_per_description': 3,
               'n_pages': 'all',
               'n_previous_pages': 2,
               'keep_existing_pages': True,
               'models_for_tasks': { 'default': 'gpt-4o',
                                     'generate_page_description': 'o1-mini',
                                     'evaluate_page_image': 'o1-mini' }
               }
    cost_dict = asyncio.run(process_pages(params))
    print_cost_dict(cost_dict)

def test_la_fontaine_overview():
    params = { 'project_dir': '$CLARA/coherent_images/LeCorbeauEtLeRenard',
               'title': 'Le Corbeau et le Renard' }
    generate_overview_html(params)

def test_la_fontaine_overview_o1():
    params = { 'project_dir': '$CLARA/coherent_images/LeCorbeauEtLeRenard_o1',
               'title': 'Le Corbeau et le Renard (o1-mini version)' }
    generate_overview_html(params)

def test_la_fontaine_judge_o1(version):
    params = { 'project_dir': f'$CLARA/coherent_images/LeCorbeauEtLeRenard_o1_v{version}',
               'title': 'Le Corbeau et le Renard (o1-mini version)' }
    human_evaluation(params)

def test_la_fontaine_prompts_o1(version, interpretation_prompt_id='default', evaluation_prompt_id='default'):
    params = { 'project_dir': f'$CLARA/coherent_images/LeCorbeauEtLeRenard_o1_v{version}',
               'interpretation_prompt_id': interpretation_prompt_id,
               'evaluation_prompt_id': evaluation_prompt_id,
               'models_for_tasks': { 'default': 'gpt-4o',
                                     'evaluate_page_image': 'o1-mini' } }

    cost_dict = asyncio.run(test_prompts_for_interpretation_and_evaluation(params))
    print_cost_dict(cost_dict)

def test_la_fontaine_prompt_agreement_o1(version, interpretation_prompt_id='default', evaluation_prompt_id='default'):
    params = { 'project_dir': f'$CLARA/coherent_images/LeCorbeauEtLeRenard_o1_v{version}',
               'interpretation_prompt_id': interpretation_prompt_id,
               'evaluation_prompt_id': evaluation_prompt_id }
    analyse_human_ai_agreement_for_prompt_test(params)

def test_la_fontaine_prompt_agreement_html_o1(version, interpretation_prompt_id='default', evaluation_prompt_id='default'):
    params = { 'project_dir': f'$CLARA/coherent_images/LeCorbeauEtLeRenard_o1_v{version}',
               'interpretation_prompt_id': interpretation_prompt_id,
               'evaluation_prompt_id': evaluation_prompt_id }
    generate_prompt_evaluation_html_report(params)

# Test with Lily Goes the Whole Hog

def test_lily_style():
    params = { 'project_dir': '$CLARA/coherent_images/LilyGoesTheWholeHog',
               'n_expanded_descriptions': 2,
               'n_images_per_description': 2,
               'models_for_tasks': { 'default': 'gpt-4o' }
               }
    cost_dict = asyncio.run(process_style(params))
    print_cost_dict(cost_dict)

def test_lily_elements():
    params = { 'project_dir': '$CLARA/coherent_images/LilyGoesTheWholeHog',
               'n_expanded_descriptions': 2,
               'n_images_per_description': 2,
               'n_elements_to_expand': 'all',
               'keep_existing_elements': True,
               'models_for_tasks': { 'default': 'gpt-4o' }
               }
    cost_dict = asyncio.run(process_elements(params))
    print_cost_dict(cost_dict)

def test_lily_pages():
    params = { 'project_dir': '$CLARA/coherent_images/LilyGoesTheWholeHog',
               'n_expanded_descriptions': 2,
               'n_images_per_description': 2,
               'n_pages': 'all',
               'n_previous_pages': 2,
               'keep_existing_pages': True,
               'models_for_tasks': { 'default': 'gpt-4o' }
               }
    cost_dict = asyncio.run(process_pages(params))
    print_cost_dict(cost_dict)

def test_lily_select():
    params = { 'project_dir': '$CLARA/coherent_images/LilyGoesTheWholeHog' }
    select_all_best_expanded_page_descriptions_and_images_for_project(params)

def test_lily_overview():
    params = { 'project_dir': '$CLARA/coherent_images/LilyGoesTheWholeHog',
               'title': 'Lily Goes the Whole Hog' }
    generate_overview_html(params)

# -----------------------------------------------
# Style

async def process_style(params):
    project_dir = params['project_dir']
    n_expanded_descriptions = params['n_expanded_descriptions']
    
    tasks = []
    all_description_dirs = []
    total_cost_dict = {}
    for description_version_number in range(0, n_expanded_descriptions):
        tasks.append(asyncio.create_task(generate_expanded_style_description_and_images(description_version_number, params)))
    results = await asyncio.gather(*tasks)
    for description_dir, cost_dict in results:
        all_description_dirs.append(description_dir)
        total_cost_dict = combine_cost_dicts(total_cost_dict, cost_dict)
    select_best_expanded_style_description_and_image(all_description_dirs, params)
    write_project_cost_file(total_cost_dict, project_dir, f'style/cost.json')
    return total_cost_dict

def select_best_expanded_style_description_and_image(all_description_dirs, params):
    project_dir = params['project_dir']
    
    best_score = 0.0
    best_description_file = None
    typical_image_file = None

    for description_dir in all_description_dirs:
        image_info_file = project_pathname(project_dir, f'{description_dir}/image_info.json')
        description_file = project_pathname(project_dir, f'{description_dir}/expanded_description.txt')

        if file_exists(image_info_file) and file_exists(description_file):
            image_info = read_json_file(image_info_file)
            if image_info['av_score'] > best_score:
                best_description_file = description_file
                typical_image_file = image_info['image']
                typical_image_interpretation = image_info['interpretation']
                typical_image_evaluation = image_info['evaluation']

    if best_description_file and typical_image_file:
        copy_file(best_description_file, project_pathname(project_dir, f'style/expanded_description.txt'))
        copy_file(typical_image_file, project_pathname(project_dir, f'style/image.jpg'))
        copy_file(typical_image_interpretation, project_pathname(project_dir, f'style/interpretation.txt'))
        copy_file(typical_image_evaluation, project_pathname(project_dir, f'style/evaluation.txt'))
            
async def generate_expanded_style_description_and_images(description_version_number, params):
    project_dir = params['project_dir']
    n_expanded_descriptions = params['n_expanded_descriptions']
    
    # Make directory if necessary
    description_directory = f'style/description_v{description_version_number}'
    make_project_dir(project_dir, description_directory)
    
    # Read the base style description
    base_description = read_project_txt_file(project_dir, f'style_description.txt')

    # Get the text of the story
    text = get_text(params)

    total_cost_dict = {}

    try:
        valid_expanded, expanded_style_description, style_cost_dict = await generate_expanded_style_description(description_version_number, params)
        total_cost_dict = combine_cost_dicts(total_cost_dict, style_cost_dict)

        if valid_expanded:
            valid_example, example_description, example_cost_dict = await generate_style_description_example(description_version_number, expanded_style_description, params)
            total_cost_dict = combine_cost_dicts(total_cost_dict, example_cost_dict)
            if valid_example:
                # Create and rate the images
                images_cost_dict = await generate_and_rate_style_images(example_description, description_version_number, params)
                total_cost_dict = combine_cost_dicts(total_cost_dict, images_cost_dict)

        write_project_cost_file(total_cost_dict, project_dir, f'{description_directory}/cost.json')
        return description_directory, total_cost_dict

    except Exception as e:
        error_message = f'"{str(e)}"\n{traceback.format_exc()}'
        write_project_txt_file(error_message, project_dir, f'style/description_v{description_version_number}/error.txt')

    return description_directory, total_cost_dict

async def generate_expanded_style_description(description_version_number, params):
    project_dir = params['project_dir']
    
    total_cost_dict = {}
    
    # Read the base style description
    base_description = read_project_txt_file(project_dir, f'style_description.txt')

    # Get the text of the story
    text = get_text(params)

    # Create the prompt to expand the style description
    prompt_template = get_prompt_template('default', 'generate_style_description')
    prompt = prompt_template.format(text=text, base_description=base_description)

    # Get the expanded description from the AI
    expanded_description = None
    valid_expanded_description_produced = False
    error_message = ''
    tries_left = 5
    max_dall_e_3_prompt_length = 1500
    
    while not valid_expanded_description_produced and tries_left:
        try:
            description_api_call = await get_api_chatgpt4_response_for_task(prompt, 'generate_style_description', params)
            cost_dict = combine_cost_dicts(total_cost_dict, { 'generate_style_description': description_api_call.cost })

            # Save the expanded description
            expanded_description = description_api_call.response
            if len(expanded_description) < max_dall_e_3_prompt_length:
                valid_expanded_description_produced = True
            else:
                error_message += f'-----------\nExpanded style description too long, {len(expanded_description)} chars over limit of {max_dall_e_3_prompt_length} chars'
                tries_left -= 1

        except Exception as e:
            error_message += f'-----------\n"{str(e)}"\n{traceback.format_exc()}'
            tries_left -= 1
        
    if valid_expanded_description_produced:
        write_project_txt_file(expanded_description, project_dir, f'style/description_v{description_version_number}/expanded_description.txt')
    else:
        write_project_txt_file(error_message, project_dir, f'style/description_v{description_version_number}/error.txt')
        
    return valid_expanded_description_produced, expanded_description, total_cost_dict

async def generate_style_description_example(description_version_number, expanded_style_description, params):
    project_dir = params['project_dir']
    
    total_cost_dict = {}
    
    # Get the text of the story
    text = get_text(params)

    # Create the prompt to expand the style description
    prompt_template = get_prompt_template('default', 'generate_style_description_example')
    prompt = prompt_template.format(text=text, expanded_style_description=expanded_style_description)

    # Get the expanded description from the AI
    image_description = None
    valid_image_description_produced = False
    error_message = ''
    tries_left = 5
    max_dall_e_3_prompt_length = 4000
    
        
    while not valid_image_description_produced and tries_left:
        try:
            description_api_call = await get_api_chatgpt4_response_for_task(prompt, 'generate_example_style_description', params)
            cost_dict = combine_cost_dicts(total_cost_dict, { 'generate_style_description': description_api_call.cost })

            # Save the expanded description
            image_description = description_api_call.response
            if len(image_description) < max_dall_e_3_prompt_length:
                valid_image_description_produced = True
            else:
                error_message += f'-----------\nStyle description example too long, {len(expanded_description)} chars over limit of {max_dall_e_3_prompt_length} chars'
                tries_left -= 1
                
        except Exception as e:
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            tries_left -= 1

        if valid_image_description_produced:
            write_project_txt_file(image_description, project_dir, f'style/description_v{description_version_number}/example_image_description.txt')
        else:
            write_project_txt_file(error_message, project_dir, f'style/description_v{description_version_number}/error.txt')

    return valid_image_description_produced, image_description, total_cost_dict

async def generate_and_rate_style_images(description, description_version_number, params):
    project_dir = params['project_dir']
    n_images_per_description = params['n_images_per_description']
    
    description_dir = f'style/description_v{description_version_number}'
    make_project_dir(project_dir, description_dir)
    
    tasks = []
    all_image_dirs = []
    total_cost_dict = {}
    for image_version_number in range(0, n_images_per_description):
        tasks.append(asyncio.create_task(generate_and_rate_style_image(description, description_version_number, image_version_number, params)))
    results = await asyncio.gather(*tasks)
    for image_dir, cost_dict in results:
        all_image_dirs.append(image_dir)
        total_cost_dict = combine_cost_dicts(total_cost_dict, cost_dict)

    score_description_dir_representative(description_dir, all_image_dirs, params)
        
    return total_cost_dict

async def generate_and_rate_style_image(description, description_version_number, image_version_number, params):
    project_dir = params['project_dir']
    
    total_cost_dict = {}
    
    image_dir = f'style/description_v{description_version_number}/image_v{image_version_number}'
    # Make directory if necessary
    make_project_dir(project_dir, image_dir)

    try:
        image_file, generate_cost_dict = await generate_style_image(image_dir, description, params)
        total_cost_dict = combine_cost_dicts(total_cost_dict, generate_cost_dict)

        image_interpretation, interpret_cost_dict = await interpret_style_image(image_dir, image_file, params)
        total_cost_dict = combine_cost_dicts(total_cost_dict, interpret_cost_dict)

        evaluation, evaluation_cost_dict = await evaluate_style_fit(image_dir, description, image_interpretation, params)
        total_cost_dict = combine_cost_dicts(total_cost_dict, evaluation_cost_dict)

    except Exception as e:
        error_message = f'"{str(e)}"\n{traceback.format_exc()}'
        write_project_txt_file(error_message, project_dir, f'{image_dir}/error.txt')
        write_project_txt_file("0", project_dir, f'{image_dir}/evaluation.txt')

    write_project_cost_file(total_cost_dict, project_dir, f'{image_dir}/cost.json')
    return image_dir, total_cost_dict

async def generate_style_image(image_dir, description, params):
    project_dir = params['project_dir']
    
    image_file = project_pathname(project_dir, f'{image_dir}/image.jpg')
    api_call = await get_api_chatgpt4_image_response_for_task(description, image_file, 'generate_style_image', params)

    return image_file, { 'generate_style_image': api_call.cost }

async def interpret_style_image(image_dir, image_file, params):
    project_dir = params['project_dir']

    prompt_template = get_prompt_template('default', 'style_example_interpretation')
    prompt = prompt_template.format()

    api_call = await get_api_chatgpt4_interpret_image_response_for_task(prompt, image_file, 'interpret_style_image', params)

    image_interpretation = api_call.response
    write_project_txt_file(image_interpretation, project_dir, f'{image_dir}/image_interpretation.txt')

    return image_interpretation, { 'interpret_style_image': api_call.cost }

async def evaluate_style_fit(image_dir, expanded_description, image_description, params):
    project_dir = params['project_dir']

    prompt_template = get_prompt_template('default', 'style_example_evaluation')
    prompt = prompt_template.format(expanded_description=expanded_description, image_description=image_description)
    
    api_call = await get_api_chatgpt4_response_for_task(prompt, 'evaluate_style_image', params)

    evaluation = api_call.response

    write_project_txt_file(evaluation, project_dir, f'{image_dir}/evaluation.txt')
    
    return evaluation, { 'evaluate_style_image': api_call.cost }

# -----------------------------------------------

# Elements

async def process_elements(params):
    project_dir = params['project_dir']
    n_elements_to_expand = params['n_elements_to_expand']
    keep_existing_elements = params['keep_existing_elements']
    
    total_cost_dict = {}

    if keep_existing_elements and file_exists(project_pathname(project_dir, f'elements/elements.json')):
        element_list_with_names = read_project_json_file(project_dir, f'elements/elements.json')
    else:
        element_list_with_names, element_names_cost_dict = await generate_element_names(params)
        total_cost_dict = combine_cost_dicts(total_cost_dict, element_names_cost_dict)

    element_list_with_names = element_list_with_names if n_elements_to_expand == 'all' else element_list_with_names[:n_elements_to_expand]

    tasks = []
    for item in element_list_with_names:
        name = item['name']
        text = item['text']
        tasks.append(asyncio.create_task(process_single_element(name, text, params)))
    results = await asyncio.gather(*tasks)
    for element_cost_dict in results:
        total_cost_dict = combine_cost_dicts(total_cost_dict, element_cost_dict)

    write_project_cost_file(total_cost_dict, project_dir, f'elements/cost.json')
    return total_cost_dict

async def generate_element_names(params):
    project_dir = params['project_dir']
    
    # Make directory if necessary
    elements_directory = f'elements'
    make_project_dir(project_dir, elements_directory)
    
    # Get the text of the story
    text = get_text(params)

    total_cost_dict = {}

    # Create the prompt to find the elements
    prompt_template = get_prompt_template('default', 'generate_element_names')
    prompt = prompt_template.format(text=text)

    # Get the expanded description from the AI
    error_messages = ''
    valid_list_produced = False
    tries_left = 5
    
    while not valid_list_produced and tries_left:
        try:
            api_call = await get_api_chatgpt4_response_for_task(prompt, 'generate_element_names', params)
            total_cost_dict = combine_cost_dicts(total_cost_dict, {'generate_element_names': api_call.cost})

            # Save the expanded description
            element_list_txt = api_call.response
            element_list = interpret_chat_gpt4_response_as_json(element_list_txt, object_type='list')
            valid_list_produced = True
            element_list_with_names = add_names_to_element_list(element_list)
            write_project_json_file(element_list_with_names, project_dir, f'elements/elements.json')
            return element_list_with_names, total_cost_dict
        except Exception as e:
            error_messages += f'-------------------\n"{str(e)}"\n{traceback.format_exc()}'
            tries_left -= 1

    # We ran out of tries, log error messages
    write_project_txt_file(error_messages, project_dir, f'elements/error.txt')
    return [], total_cost_dict

def add_names_to_element_list(element_list):
    return [ { 'name': element_phrase_to_name(element), 'text': element } for element in element_list ]

def element_phrase_to_name(element):
    out_str = ''
    for char in element:
        out_str += '_' if char.isspace() or unicodedata.category(char).startswith('P') else char
    return out_str

async def process_single_element(element_name, element_text, params):
    project_dir = params['project_dir']
    n_expanded_descriptions = params['n_expanded_descriptions']
    n_images_per_description = params['n_images_per_description']
    n_elements_to_expand = params['n_elements_to_expand']
    keep_existing_elements = params['keep_existing_elements']
    
    tasks = []
    all_description_dirs = []
    total_cost_dict = {}

    if keep_existing_elements and file_exists(project_pathname(project_dir, f'elements/{element_name}/image.jpg')):
        print(f'Element processing for "{element_text}" already done, skipping')
        return total_cost_dict
    
    for description_version_number in range(0, n_expanded_descriptions):
        tasks.append(asyncio.create_task(generate_expanded_element_description_and_images(element_name, element_text, description_version_number, params)))
    results = await asyncio.gather(*tasks)
    for description_dir, cost_dict in results:
        all_description_dirs.append(description_dir)
        total_cost_dict = combine_cost_dicts(total_cost_dict, cost_dict)
    select_best_expanded_element_description_and_image(element_name, all_description_dirs, params)

    write_project_cost_file(total_cost_dict, project_dir, f'elements/{element_name}/cost.json')
    return total_cost_dict

def select_best_expanded_element_description_and_image(element_name, all_description_dirs, params):
    project_dir = params['project_dir']
    
    best_score = 0.0
    best_description_file = None
    typical_image_file = None

    for description_dir in all_description_dirs:
        image_info_file = project_pathname(project_dir, f'{description_dir}/image_info.json')
        description_file = project_pathname(project_dir, f'{description_dir}/expanded_description.txt')

        if file_exists(image_info_file) and file_exists(description_file):
            image_info = read_json_file(image_info_file)
            if image_info['av_score'] > best_score:
                best_description_file = description_file
                typical_image_file = image_info['image']
                typical_image_interpretation = image_info['interpretation']
                typical_image_evaluation = image_info['evaluation']

    if best_description_file and typical_image_file:
        copy_file(best_description_file, project_pathname(project_dir, f'elements/{element_name}/expanded_description.txt'))
        copy_file(typical_image_file, project_pathname(project_dir, f'elements/{element_name}/image.jpg'))
        copy_file(typical_image_interpretation, project_pathname(project_dir, f'elements/{element_name}/interpretation.txt'))
        copy_file(typical_image_evaluation, project_pathname(project_dir, f'elements/{element_name}/evaluation.txt'))
            
async def generate_expanded_element_description_and_images(element_name, element_text, description_version_number, params):

    project_dir = params['project_dir']
    n_images_per_description = params['n_images_per_description']
    
    # Make directory if necessary
    description_directory = f'elements/{element_name}/description_v{description_version_number}'
    make_project_dir(project_dir, description_directory)
    
    # Get the text of the story and the style description
    text = get_text(params)
    style_description = get_style_description(params)

    total_cost_dict = {}

    # Create the prompt to expand the element description
    prompt_template = get_prompt_template('default', 'generate_element_description')
    prompt = prompt_template.format(text=text, style_description=style_description, element_text=element_text)

    # Get the expanded description from the AI
    try:
        valid_expanded_description_produced = False
        tries_left = 5
        max_dall_e_3_prompt_length = 1250
        
        while not valid_expanded_description_produced and tries_left:
            description_api_call = await get_api_chatgpt4_response_for_task(prompt, 'generate_element_description', params)
            total_cost_dict = combine_cost_dicts(total_cost_dict, { 'generate_element_description': description_api_call.cost })

            # Save the expanded description
            expanded_description = description_api_call.response
            if len(expanded_description) < max_dall_e_3_prompt_length:
                valid_expanded_description_produced = True
            else:
                tries_left -= 1
            
        write_project_txt_file(expanded_description, project_dir, f'elements/{element_name}/description_v{description_version_number}/expanded_description.txt')

        # Create and rate the images
        image_cost_dict = await generate_and_rate_element_images(element_name, expanded_description, description_version_number, params)
        total_cost_dict = combine_cost_dicts(total_cost_dict, image_cost_dict)

        write_project_cost_file(total_cost_dict, project_dir, f'{description_directory}/cost.json')
        return description_directory, total_cost_dict

    except Exception as e:
        error_message = f'"{str(e)}"\n{traceback.format_exc()}'
        write_project_txt_file(error_message, project_dir, f'elements/{element_name}/description_v{description_version_number}/error.txt')

    write_project_cost_file(total_cost_dict, project_dir, f'{description_directory}/cost.json')
    return description_directory, {}

async def generate_and_rate_element_images(element_name, description, description_version_number, params):
    project_dir = params['project_dir']
    n_images_per_description = params['n_images_per_description']
    
    description_dir = f'elements/{element_name}/description_v{description_version_number}'
    make_project_dir(project_dir, description_dir)
    
    tasks = []
    all_image_dirs = []
    total_cost_dict = {}
    for image_version_number in range(0, n_images_per_description):
        tasks.append(asyncio.create_task(generate_and_rate_element_image(element_name, description, description_version_number, image_version_number, params)))
    results = await asyncio.gather(*tasks)
    for image_dir, cost_dict in results:
        all_image_dirs.append(image_dir)
        total_cost_dict = combine_cost_dicts(total_cost_dict, cost_dict)

    score_description_dir_representative(description_dir, all_image_dirs, params)
        
    return total_cost_dict

async def generate_and_rate_element_image(element_name, description, description_version_number, image_version_number, params):
    project_dir = params['project_dir']
    
    total_cost_dict = {}
    
    image_dir = f'elements/{element_name}/description_v{description_version_number}/image_v{image_version_number}'
    # Make directory if necessary
    make_project_dir(project_dir, image_dir)

    try:
        image_file, image_cost_dict = await generate_element_image(image_dir, description, params)
        total_cost_dict = combine_cost_dicts(total_cost_dict, image_cost_dict)

        image_interpretation, interpret_cost_dict = await interpret_element_image(image_dir, image_file, params)
        total_cost_dict = combine_cost_dicts(total_cost_dict, interpret_cost_dict)

        evaluation, evaluation_cost_dict = await evaluate_element_fit(image_dir, description, image_interpretation, params)
        total_cost_dict = combine_cost_dicts(total_cost_dict, evaluation_cost_dict)

    except Exception as e:
        error_message = f'"{str(e)}"\n{traceback.format_exc()}'
        write_project_txt_file(error_message, project_dir, f'{image_dir}/error.txt')
        write_project_txt_file("0", project_dir, f'{image_dir}/evaluation.txt')

    write_project_cost_file(total_cost_dict, project_dir, f'{image_dir}/cost.json')
    return image_dir, total_cost_dict

async def generate_element_image(image_dir, description, params):
    project_dir = params['project_dir']
    
    image_file = project_pathname(project_dir, f'{image_dir}/image.jpg')
    api_call = await get_api_chatgpt4_image_response_for_task(description, image_file, 'generate_element_image', params)

    return image_file, { 'generate_element_image': api_call.cost }

async def interpret_element_image(image_dir, image_file, params):
    project_dir = params['project_dir']

    prompt_template = get_prompt_template('default', 'element_interpretation')
    prompt = prompt_template.format()

    api_call = await get_api_chatgpt4_interpret_image_response_for_task(prompt, image_file, 'interpret_element_image', params)

    image_interpretation = api_call.response
    write_project_txt_file(image_interpretation, project_dir, f'{image_dir}/image_interpretation.txt')

    return image_interpretation, { 'interpret_element_image': api_call.cost }

async def evaluate_element_fit(image_dir, expanded_description, image_description, params):
    project_dir = params['project_dir']

    prompt_template = get_prompt_template('default', 'element_evaluation')
    prompt = prompt_template.format(expanded_description=expanded_description, image_description=image_description)

    api_call = await get_api_chatgpt4_response_for_task(prompt, 'evaluate_element_image', params)

    evaluation = api_call.response

    write_project_txt_file(evaluation, project_dir, f'{image_dir}/evaluation.txt')
    
    return evaluation, { 'evaluate_element_image': api_call.cost }

# -----------------------------------------------

# Pages

async def process_pages(params):
    project_dir = params['project_dir']
    n_pages = params['n_pages']
    
    total_cost_dict = {}
    page_numbers = get_pages(params)
    page_numbers = page_numbers if n_pages == 'all' else page_numbers[:n_pages]

    for page_number in page_numbers:
        cost_dict = await generate_image_for_page(page_number, params)
        total_cost_dict = combine_cost_dicts(total_cost_dict, cost_dict)

    write_project_cost_file(total_cost_dict, project_dir, f'pages/cost.json')
    return total_cost_dict

async def generate_image_for_page(page_number, params):
    project_dir = params['project_dir']
    keep_existing_pages = params['keep_existing_pages']
    
    total_cost_dict = {}

    if keep_existing_pages and file_exists(project_pathname(project_dir, f'pages/page{page_number}/image.jpg')):
        print(f'Page processing for page {page_number} already done, skipping')
        return total_cost_dict
   
    previous_pages, elements, context_cost_dict = await find_relevant_previous_pages_and_elements_for_page(page_number, params)
    total_cost_dict = combine_cost_dicts(total_cost_dict, context_cost_dict)

    generation_cost_dict = await generate_image_for_page_and_context(page_number, previous_pages, elements, params)
    total_cost_dict = combine_cost_dicts(total_cost_dict, generation_cost_dict)

    write_project_cost_file(total_cost_dict, project_dir, f'pages/page{page_number}/cost.json')
    return total_cost_dict

async def find_relevant_previous_pages_and_elements_for_page(page_number, params):
    project_dir = params['project_dir']
    
    total_cost_dict = {}
    
    previous_pages, previous_pages_cost_dict = await find_relevant_previous_pages_for_page(page_number, params)
    total_cost_dict = combine_cost_dicts(total_cost_dict, previous_pages_cost_dict)

    elements, elements_cost_dict = await find_relevant_elements_for_page(page_number, params)
    total_cost_dict = combine_cost_dicts(total_cost_dict, elements_cost_dict)

    info = { 'relevant_previous_pages': previous_pages,'relevant_elements': elements }
    write_project_json_file(info, project_dir, f'pages/page{page_number}/relevant_pages_and_elements.json')
    return previous_pages, elements, total_cost_dict

async def find_relevant_previous_pages_for_page(page_number, params):
    project_dir = params['project_dir']
    n_previous_pages = params['n_previous_pages']

    # Make directory if necessary
    page_number_directory = f'pages/page{page_number}'
    make_project_dir(project_dir, page_number_directory)
    
    # Get the text of the story and the current page
    story_data = get_story_data(params)
    formatted_story_data = json.dumps(story_data, indent=4)

    page_text = get_page_text(page_number, params)

    # Create the prompt
    prompt_template = get_prompt_template('default', 'get_relevant_previous_pages')
    prompt = prompt_template.format(formatted_story_data=formatted_story_data, page_number=page_number, page_text=page_text)

    total_cost_dict = {}
    all_error_messages = ''
    # Get the expanded description from the AI

    tries_left = 5
    
    while tries_left:
        try:
            api_call = await get_api_chatgpt4_response_for_task(prompt, 'find_relevant_previous_pages', params)
            total_cost_dict = combine_cost_dicts(total_cost_dict, { 'find_relevant_previous_pages': api_call.cost })

            # Save the expanded description
            list_text = api_call.response
            list_object = interpret_chat_gpt4_response_as_json(list_text, object_type='list')

            if all([ isinstance(item, ( int )) and item < page_number for item in list_object ]):
                return list_object, total_cost_dict
            else:
                error_message = f'{list_object} contains page number greater than or equal to {page_number}'
                all_error_messages += f'\n-------------------------------\n{error_message}'
                tries_left -= 1
            
        except Exception as e:
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            all_error_messages += f'\n-------------------------------\n{error_message}'
            tries_left -= 1

    # We didn't succeed
    
    write_project_txt_file(all_error_messages, project_dir, f'pages/page{page_number}/error.txt')
    raise ImageGenerationError(message = f'Error when finding  previous pages for page {page_number}')

async def find_relevant_elements_for_page(page_number, params):
    project_dir = params['project_dir']
    
    # Get the text of the story
    story_data = get_story_data(params)
    formatted_story_data = json.dumps(story_data, indent=4)

    page_text = get_page_text(page_number, params)

    all_element_texts = get_all_element_texts(params)

    # Create the prompt
    prompt_template = get_prompt_template('default', 'get_relevant_elements')
    prompt = prompt_template.format(formatted_story_data=formatted_story_data, page_number=page_number, page_text=page_text, all_element_texts=all_element_texts)

    total_cost_dict = {}
    all_error_messages = ''
    # Get the expanded description from the AI

    tries_left = 5
    
    while tries_left:
        try:
            api_call = await get_api_chatgpt4_response_for_task(prompt, 'find_relevant_elements', params)
            total_cost_dict = combine_cost_dicts(total_cost_dict, { 'find_relevant_elements': api_call.cost })

            # Save the expanded description
            list_text = api_call.response
            list_object = interpret_chat_gpt4_response_as_json(list_text, object_type='list')

            if all([ item in all_element_texts for item in list_object ]):
                return list_object, total_cost_dict
            else:
                error_message = f'{list_object} contains element name not in {all_element_texts}'
                all_error_messages += f'\n-------------------------------\n{error_message}'
                tries_left -= 1
            
        except Exception as e:
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            all_error_messages += f'\n-------------------------------\n{error_message}'
            tries_left -= 1

    # We didn't succeed
    
    write_project_txt_file(all_error_messages, project_dir, f'pages/page{page_number}/error.txt')
    raise ImageGenerationError(message = f'Error when finding relevant elements for page {page_number}')

async def generate_image_for_page_and_context(page_number, previous_pages, elements, params):
    
    project_dir = params['project_dir']

    DEFAULT_MAX_DESCRIPTION_GENERATION_ROUNDS = 3

    n_previous_rounds = 0
    n_rounds_left = params['max_description_generation_rounds'] if 'max_description_generation_rounds' in params else DEFAULT_MAX_DESCRIPTION_GENERATION_ROUNDS

    total_cost_dict = {}

    while n_rounds_left > 0:

        # We generate n_expanded_descriptions each round to get the directories.
        # If we're not on the first round, we do all the previous directories, but the old ones will be skipped.
        n_expanded_descriptions = params['n_expanded_descriptions'] * ( 1 + n_previous_rounds )
        
        tasks = []
        all_description_dirs = []
        
        for description_version_number in range(0, n_expanded_descriptions):
            tasks.append(asyncio.create_task(generate_page_description_and_images(page_number, previous_pages, elements, description_version_number, params)))
        results = await asyncio.gather(*tasks)
        for description_dir, cost_dict in results:
            all_description_dirs.append(description_dir)
            total_cost_dict = combine_cost_dicts(total_cost_dict, cost_dict)
        select_best_expanded_page_description_and_image(page_number, all_description_dirs, params)

        if acceptable_page_image_exists(page_number, params):
            # We succeeded. Return the costs
            return total_cost_dict
        else:
            # We failed. Try again, creating n_expanded_descriptions more description directories
            n_rounds_left -= 1
            n_previous_rounds += 1

    # None of the descriptions produced an acceptable image and we're out of lives. Give up.
    return total_cost_dict

def acceptable_page_image_exists(page_number, params):
    project_dir = params['project_dir']

    image_file_exists = file_exists(project_pathname(project_dir, f'pages/page{page_number}/image.jpg'))
    score, comments = score_for_evaluation_file(f'pages/page{page_number}/evaluation.txt', params)

    if image_file_exists and score >= 3:  # 3 = "good"
        return True
    else:
        return False
    

# Only used for cleaning up
def select_all_best_expanded_page_descriptions_and_images_for_project(params):
    project_dir = params['project_dir']
    
    page_numbers = get_pages(params)
    for page_number in page_numbers:
        page_dir = project_pathname(project_dir, f'pages/page{page_number}')
        if directory_exists(page_dir):
            description_dir_names = get_immediate_subdirectories_in_local_directory(page_dir)
            all_description_dirs = [ os.path.join(page_dir, description_dir_name) for description_dir_name in description_dir_names ]
            select_best_expanded_page_description_and_image(page_number, all_description_dirs, params)

def select_best_expanded_page_description_and_image(page_number, all_description_dirs, params):
    project_dir = params['project_dir']
          
    best_score = 0.0
    best_description_file = None
    best_image_file = None
    best_interpretation_file = None
    best_evaluation_file = None

    for description_dir in all_description_dirs:
        image_info_file = project_pathname(project_dir, f'{description_dir}/image_info.json')
        description_file = project_pathname(project_dir, f'{description_dir}/expanded_description.txt')

        if file_exists(image_info_file) and file_exists(description_file):
            image_info = read_json_file(image_info_file)
            if image_info['best_score'] > best_score:
                best_score = image_info['best_score']
                best_description_file = description_file
                best_image_file = image_info['image']
                best_interpretation_file = image_info['interpretation']
                best_evaluation_file = image_info['evaluation']

    if best_description_file and best_image_file and best_interpretation_file:
        copy_file(best_description_file, project_pathname(project_dir, f'pages/page{page_number}/expanded_description.txt'))
        copy_file(best_image_file, project_pathname(project_dir, f'pages/page{page_number}/image.jpg'))
        copy_file(best_interpretation_file, project_pathname(project_dir, f'pages/page{page_number}/interpretation.txt'))
        copy_file(best_evaluation_file, project_pathname(project_dir, f'pages/page{page_number}/evaluation.txt'))
    else:
        print('No best_expanded_page_description_and_image found')
            
async def generate_page_description_and_images(page_number, previous_pages, elements, description_version_number, params):
    project_dir = params['project_dir']

    # Make directory if necessary
    description_directory = f'pages/page{page_number}/description_v{description_version_number}'
    make_project_dir(project_dir, description_directory)

    total_cost_dict = {}

    if file_exists(project_pathname(project_dir, f'{description_directory}/image_info.json')):
        # We've already done this directory
        return description_directory, total_cost_dict
    
    # Get the text of the story, the style description, the relevant previous pages and the relevant element descriptions
    story_data = get_story_data(params)
    formatted_story_data = json.dumps(story_data, indent=4)
    
    page_text = get_page_text(page_number, params)
    style_description = get_style_description(params)
    
    previous_page_descriptions_with_page_numbers = [ ( previous_page_number, get_page_description(previous_page_number, params) )
                                                     for previous_page_number in previous_pages ]
    if not previous_page_descriptions_with_page_numbers:
        previous_page_descriptions_text = f'(No specifications of images on previous pages)'
    else:
        previous_page_descriptions_text = f'Specifications of images on relevant previous pages:\n'
        for previous_page_number, previous_page_description in previous_page_descriptions_with_page_numbers:
            if previous_page_description:
                previous_page_descriptions_text += f'\nPage {previous_page_number}:\n{previous_page_description}'

    element_description_with_element_texts = [ ( element_text, get_element_description(element_text, params) )
                                               for element_text in elements ]
    if not element_description_with_element_texts:
        element_descriptions_text = f'(No specifications of elements)'
    else:
        element_descriptions_text = f'Specifications of relevant elements:\n'
        for element_text, element_description in element_description_with_element_texts:
            element_descriptions_text += f'\nElement "{element_text}":\n{element_description}'

    # Create the prompt
    prompt_template = get_prompt_template('default', 'generate_page_description')
    prompt = prompt_template.format(formatted_story_data=formatted_story_data,
                                    style_description=style_description,
                                    page_number=page_number,
                                    page_text=page_text,
                                    element_descriptions_text=element_descriptions_text,
                                    previous_page_descriptions_text=previous_page_descriptions_text)
    
    # Get the expanded description from the AI
    try:
        valid_expanded_description_produced = False
        tries_left = 5
        #tries_left = 1
        max_dall_e_3_prompt_length = 4000
        
        while not valid_expanded_description_produced and tries_left:
            description_api_call = await get_api_chatgpt4_response_for_task(prompt, 'generate_page_description', params)
            total_cost_dict = combine_cost_dicts(total_cost_dict, { 'generate_page_description': description_api_call.cost })

            # Save the expanded description
            expanded_description = description_api_call.response
            if len(expanded_description) < max_dall_e_3_prompt_length and "essential aspects" in expanded_description.lower():
                valid_expanded_description_produced = True
            else:
                print(f'Length of description = {len(expanded_description)}')
                tries_left -= 1

        write_project_txt_file(expanded_description, project_dir, f'pages/page{page_number}/description_v{description_version_number}/expanded_description.txt')

        if valid_expanded_description_produced:   
        # Create and rate the images
            image_cost_dict = await generate_and_rate_page_images(page_number, expanded_description, description_version_number, params)
        else:
            image_cost_dict = {}
            error_message = f"No generated description was less than {max_dall_e_3_prompt_length} characters long"
            write_project_txt_file(error_message, project_dir, f'pages/page{page_number}/description_v{description_version_number}/error.txt')
            
        total_cost_dict = combine_cost_dicts(total_cost_dict, image_cost_dict)

        write_project_cost_file(total_cost_dict, project_dir, f'{description_directory}/cost.json')
        return description_directory, total_cost_dict

    except Exception as e:
        error_message = f'"{str(e)}"\n{traceback.format_exc()}'
        write_project_txt_file(error_message, project_dir, f'pages/page{page_number}/description_v{description_version_number}/error.txt')
        return description_directory, {}

async def generate_and_rate_page_images(page_number, expanded_description, description_version_number, params):
    project_dir = params['project_dir']
    n_images_per_description = params['n_images_per_description']
                            
    description_dir = f'pages/page{page_number}/description_v{description_version_number}'
    make_project_dir(project_dir, description_dir)
    
    tasks = []
    all_image_dirs = []
    total_cost_dict = {}
    for image_version_number in range(0, n_images_per_description):
        tasks.append(asyncio.create_task(generate_and_rate_page_image(page_number, expanded_description, description_version_number, image_version_number, params)))
    results = await asyncio.gather(*tasks)
    for image_dir, cost_dict in results:
        all_image_dirs.append(image_dir)
        total_cost_dict = combine_cost_dicts(total_cost_dict, cost_dict)

    score_description_dir_best(description_dir, all_image_dirs, params)
        
    return total_cost_dict

async def generate_and_rate_page_image(page_number, description, description_version_number, image_version_number, params):
    project_dir = params['project_dir']
    
    total_cost_dict = {}
    
    image_dir = f'pages/page{page_number}/description_v{description_version_number}/image_v{image_version_number}'
    # Make directory if necessary
    make_project_dir(project_dir, image_dir)

    try:
        image_file, image_cost_dict = await generate_page_image(image_dir, description, page_number, params)
        total_cost_dict = combine_cost_dicts(total_cost_dict, image_cost_dict)

        image_interpretation, interpret_cost_dict = await interpret_page_image(image_dir, image_file, page_number, params)
        total_cost_dict = combine_cost_dicts(total_cost_dict, interpret_cost_dict)

        evaluation, evaluation_cost_dict = await evaluate_page_fit(image_dir, description, image_interpretation, page_number, params)
        total_cost_dict = combine_cost_dicts(total_cost_dict, evaluation_cost_dict)

    except Exception as e:
        error_message = f'"{str(e)}"\n{traceback.format_exc()}'
        write_project_txt_file(error_message, project_dir, f'{image_dir}/error.txt')
        write_project_txt_file("0", project_dir, f'{image_dir}/evaluation.txt')

    write_project_cost_file(total_cost_dict, project_dir, f'{image_dir}/cost.json')
    return image_dir, total_cost_dict

async def generate_page_image(image_dir, description, page_number, params):
    project_dir = params['project_dir']
    
    image_file = project_pathname(project_dir, f'{image_dir}/image.jpg')
    api_call = await get_api_chatgpt4_image_response_for_task(description, image_file, 'generate_page_image', params)

    return image_file, { 'generate_page_image': api_call.cost }

async def interpret_page_image(image_dir, image_file, page_number, params):
    project_dir = params['project_dir']

    story_data = get_story_data(params)
    formatted_story_data = json.dumps(story_data, indent=4)
    
    page_text = get_page_text(page_number, params)

    prompt_template = get_prompt_template('default', 'page_interpretation')

    prompt = prompt_template.format(formatted_story_data=formatted_story_data, page_number=page_number, page_text=page_text)

    api_call = await get_api_chatgpt4_interpret_image_response_for_task(prompt, image_file, 'interpret_page_image', params)

    image_interpretation = api_call.response
    write_project_txt_file(image_interpretation, project_dir, f'{image_dir}/image_interpretation.txt')
    return image_interpretation, { 'interpret_page_image': api_call.cost }

async def evaluate_page_fit(image_dir, expanded_description, image_description, page_number, params):
    project_dir = params['project_dir']

    prompt_template = get_prompt_template('default', 'page_evaluation')

    story_data = get_story_data(params)
    formatted_story_data = json.dumps(story_data, indent=4)
    
    page_text = get_page_text(page_number, params)

    prompt = prompt_template.format(formatted_story_data=formatted_story_data, page_number=page_number, page_text=page_text,
                                    expanded_description=expanded_description, image_description=image_description)
    
    api_call = await get_api_chatgpt4_response_for_task(prompt, 'evaluate_page_image', params)

    evaluation = api_call.response

    write_project_txt_file(evaluation, project_dir, f'{image_dir}/evaluation.txt')
    
    return evaluation, { 'evaluate_page_image': api_call.cost }

# -----------------------------------------------

def generate_overview_html(params):
    project_dir = params['project_dir']
    title = params['title']
    
    # Make project_dir absolute
    project_dir = absolute_file_name(project_dir)

    html_content = f"""
    <html>
    <head>
        <title>{title} - Overview</title>
        <style>
            .wrapped-pre {{
                white-space: pre-wrap;
                word-wrap: break-word;
                max-width: 800px;  /* Adjust the max-width as needed */
            }}
            img {{
                max-width: 600px;
                height: auto;
            }}
        </style>
    </head>
    <body>
    """
    
    html_content += f"<h1>{title} - Project Overview</h1>"

    # Style Section
    html_content += "<h2>Style</h2>"

    # Display the style image
    style_image_path = project_pathname(project_dir, 'style/image.jpg')
    if file_exists(style_image_path):
        relative_style_image_path = os.path.relpath(style_image_path, project_dir)
        html_content += "<h3>Style Image</h3>"
        html_content += f"<img src='{relative_style_image_path}' alt='Style Image' style='max-width:600px;'>"
    else:
        html_content += "<p><em>Style image not found.</em></p>"

    # Display the expanded style description
    try:
        original_style_description = read_project_txt_file(project_dir, 'style_description.txt')
        html_content += "<h3>User-Supplied Style Description</h3>"
        html_content += f"<pre class='wrapped-pre'>{original_style_description}</pre>"
        
        style_description = read_project_txt_file(project_dir, 'style/expanded_description.txt')
        html_content += "<h3>Expanded Style Description</h3>"
        html_content += f"<pre class='wrapped-pre'>{style_description}</pre>"
    except Exception as e:
        html_content += "<p><em>Style description not found.</em></p>"

    # Elements Section
    html_content += "<h2>Elements</h2>"

    elements_json_path = project_pathname(project_dir, 'elements/elements.json')
    if file_exists(elements_json_path):
        # Read the elements from the JSON file
        elements_data = read_project_json_file(project_dir, 'elements/elements.json')
        if elements_data:
            html_content += "<ul>"
            for element in elements_data:
                element_name = element['name']
                element_text = element['text']
                display_name = element_text  # Use the 'text' field for display
                html_content += f"<li><a href='#{element_name}'>{display_name}</a></li>"
            html_content += "</ul>"

            for element in elements_data:
                element_name = element['name']
                element_text = element['text']
                display_name = element_text
                html_content += f"<h3 id='{element_name}'>{display_name}</h3>"
                # Display the element image
                element_image_path = project_pathname(project_dir, f'elements/{element_name}/image.jpg')
                if file_exists(element_image_path):
                    relative_element_image_path = os.path.relpath(element_image_path, project_dir)
                    html_content += "<h4>Element Image</h4>"
                    html_content += f"<img src='{relative_element_image_path}' alt='{display_name}' style='max-width:400px;'>"
                else:
                    html_content += "<p><em>Image not found for this element.</em></p>"
                # Read the element's expanded description
                element_description_path = f'elements/{element_name}/expanded_description.txt'
                try:
                    element_description = read_project_txt_file(project_dir, element_description_path)
                    html_content += "<h4>Expanded Description</h4>"
                    html_content += f"<pre class='wrapped-pre'>{element_description}</pre>"
                except Exception as e:
                    html_content += "<p><em>Expanded description not found for this element.</em></p>"
                # Read the evaluation score
                evaluation_path = f'elements/{element_name}/evaluation.txt'
                if file_exists(project_pathname(project_dir, evaluation_path)):
                    evaluation_response = read_project_txt_file(project_dir, evaluation_path)
                    score, summary = parse_image_evaluation_response(evaluation_response)
                    html_content += f"<p><strong>Average Evaluation Score:</strong> {score}</p>"
                    if summary:
                        html_content += f"<h4>Typical Discrepancies:</h4><pre class='wrapped-pre'>{summary}</pre>"
                else:
                    html_content += "<p><em>Evaluation score not found for this page.</em></p>"
        else:
            html_content += "<p><em>No elements found in elements.json.</em></p>"
    else:
        html_content += "<p><em>elements.json not found.</em></p>"

    # Pages Section
    html_content += "<h2>Pages</h2>"

    # Read the story data
    story_data = read_project_json_file(project_dir, 'story.json')
    if story_data:
        for page in story_data:
            page_number = page['page_number']
            html_content += f"<h3>Page {page_number}</h3>"
            html_content += f"<p><strong>Text</strong></p>"
            page_text = page['text']
            html_content += f"<pre class='wrapped-pre'>{page_text}</pre>"

            # Display the page image
            page_image_path = project_pathname(project_dir, f'pages/page{page_number}/image.jpg')
            if file_exists(page_image_path):
                relative_page_image_path = os.path.relpath(page_image_path, project_dir)
                html_content += "<h4>Page Image</h4>"
                html_content += f"<img src='{relative_page_image_path}' alt='Page {page_number} Image' style='max-width:600px;'>"
            else:
                html_content += "<p><em>Image not found for this page.</em></p>"

            # Read the expanded description (specification)
            expanded_description_path = f'pages/page{page_number}/expanded_description.txt'
            if file_exists(project_pathname(project_dir, expanded_description_path)):
                expanded_description = read_project_txt_file(project_dir, expanded_description_path)
                html_content += "<h4>Expanded Description</h4>"
                html_content += f"<pre class='wrapped-pre'>{expanded_description}</pre>"
            else:
                html_content += "<p><em>Expanded description not found for this page.</em></p>"

            # Read the image interpretation
            interpretation_path = f'pages/page{page_number}/interpretation.txt'
            if file_exists(project_pathname(project_dir, interpretation_path)):
                interpretation = read_project_txt_file(project_dir, interpretation_path)
                html_content += "<h4>Image Interpretation</h4>"
                html_content += f"<pre class='wrapped-pre'>{interpretation}</pre>"
            else:
                html_content += "<p><em>Image interpretation not found for this page.</em></p>"

            # Read the evaluation score
            evaluation_path = f'pages/page{page_number}/evaluation.txt'
            if file_exists(project_pathname(project_dir, evaluation_path)):
                evaluation_response = read_project_txt_file(project_dir, evaluation_path)
                score, summary = parse_image_evaluation_response(evaluation_response)
                html_content += f"<p><strong>Evaluation Score:</strong> {score}</p>"
                if summary:
                    html_content += f"<h4>Discrepancies:</h4><pre class='wrapped-pre'>{summary}</pre>"
            else:
                html_content += "<p><em>Evaluation score not found for this page.</em></p>"

            # Read the relevant pages and elements
            relevant_info_path = f'pages/page{page_number}/relevant_pages_and_elements.json'
            if file_exists(project_pathname(project_dir, relevant_info_path)):
                relevant_info = read_project_json_file(project_dir, relevant_info_path)
                # Display relevant previous pages
                relevant_previous_pages = relevant_info.get('relevant_previous_pages', [])
                if relevant_previous_pages:
                    html_content += "<h4>Relevant Previous Pages</h4>"
                    html_content += "<ul>"
                    for prev_page in relevant_previous_pages:
                        html_content += f"<li>Page {prev_page}</li>"
                    html_content += "</ul>"
                else:
                    html_content += "<p><em>No relevant previous pages found for this page.</em></p>"
                # Display relevant elements
                relevant_elements = relevant_info.get('relevant_elements', [])
                if relevant_elements:
                    html_content += "<h4>Relevant Elements</h4>"
                    html_content += "<ul>"
                    for element in relevant_elements:
                        html_content += f"<li>{element}</li>"
                    html_content += "</ul>"
                else:
                    html_content += "<p><em>No relevant elements found for this page.</em></p>"
            else:
                html_content += "<p><em>Relevant pages and elements data not found for this page.</em></p>"

    else:
        html_content += "<p><em>Story data not found in story.json.</em></p>"

    html_content += "</body></html>"

    # Write the HTML content to a file
    write_project_txt_file(html_content, project_dir, 'overview.html')

# -----------------------------------------------

def score_description_dir_representative(description_dir, image_dirs, params):
    project_dir = params['project_dir']
    
    scores_and_images_dirs = [ ( score_for_image_dir(image_dir, params)[0], image_dir )
                               for image_dir in image_dirs ]
    scores = [ item[0] for item in scores_and_images_dirs ]
    av_score = sum(scores) / len(scores)

    # Find the image most representative of the average score

    closest_match = 10.0
    closest_file = None
    closest_interpretation_file = None
    closest_evaluation_file = None

    for score, image_dir in scores_and_images_dirs:
        image_file = project_pathname(project_dir, f'{image_dir}/image.jpg')
        interpretation_file = project_pathname(project_dir, f'{image_dir}/image_interpretation.txt')
        evaluation_file = project_pathname(project_dir, f'{image_dir}/evaluation.txt')
        if abs(score - av_score ) < closest_match and file_exists(image_file) and file_exists(evaluation_file):
            closest_match = abs(score - av_score )
            closest_image_file = image_file
            closest_interpretation_file = interpretation_file
            closest_evaluation_file = evaluation_file

    description_dir_info = { 'av_score': av_score,
                             'image': closest_image_file,
                             'interpretation': closest_interpretation_file,
                             'evaluation': closest_evaluation_file}
                                                                   
    write_project_json_file(description_dir_info, project_dir, f'{description_dir}/image_info.json')

    if closest_image_file and closest_interpretation_file and closest_evaluation_file:
        copy_file(closest_image_file, project_pathname(project_dir, f'{description_dir}/image.jpg'))
        copy_file(closest_interpretation_file, project_pathname(project_dir, f'{description_dir}/interpretation.txt'))
        copy_file(closest_evaluation_file, project_pathname(project_dir, f'{description_dir}/evaluation.txt'))

def score_description_dir_best(description_dir, image_dirs, params):
    project_dir = params['project_dir']
    
    scores_and_images_dirs = [ ( score_for_image_dir(image_dir, params)[0], image_dir )
                               for image_dir in image_dirs ]

    # Find the image with the best fit

    best_score = 0
    best_image_file = None
    best_interpretation_file = None
    best_evaluation_file = None

    for score, image_dir in scores_and_images_dirs:
        image_file = project_pathname(project_dir, f'{image_dir}/image.jpg')
        interpretation_file = project_pathname(project_dir, f'{image_dir}/image_interpretation.txt')
        evaluation_file = project_pathname(project_dir, f'{image_dir}/evaluation.txt')
        if score > best_score and file_exists(image_file):
            best_score = score
            best_image_file = image_file
            best_interpretation_file = interpretation_file
            best_evaluation_file = evaluation_file

    description_dir_info = { 'best_score': best_score,
                             'image': best_image_file,
                             'interpretation': best_interpretation_file,
                             'evaluation': best_evaluation_file }
                                                                   
    write_project_json_file(description_dir_info, project_dir, f'{description_dir}/image_info.json')

    if best_image_file and best_interpretation_file and best_evaluation_file:
        copy_file(best_image_file, project_pathname(project_dir, f'{description_dir}/image.jpg'))
        copy_file(best_interpretation_file, project_pathname(project_dir, f'{description_dir}/interpretation.txt'))
        copy_file(best_evaluation_file, project_pathname(project_dir, f'{description_dir}/evaluation.txt'))

# -----------------------------------------------



