from .clara_coherent_images_prompt_templates import (
    get_prompt_template,
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
    get_config_info_from_params,
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
    ImageGenerationError
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

async def interpret_element_image_with_prompt(image_path, description, element_text, formatted_story_data, prompt_id, params, callback=None):
    # Retrieve the prompt template based on prompt_id
    prompt_template = get_prompt_template(prompt_id, 'element_image_interpretation')

    prompt = prompt_template.format(formatted_story_data=formatted_story_data,
                                    element_text=element_text)

    # Perform the API call
    tries_left = params['n_retries'] if 'n_retries' in params else 5
    total_cost = 0
    errors = ''

    while tries_left:
        try:
            api_call = await get_api_chatgpt4_interpret_image_response_for_task(
                prompt,
                image_path,
                'evaluate_page_image',
                params,
                callback=callback
            )
            image_interpretation = api_call.response
            total_cost += api_call.cost
            return image_interpretation, errors, {'interpret_image': total_cost}
        
        except Exception as e:
            error = f'"{str(e)}"\n{traceback.format_exc()}'
            errors += f"""{error}
------------------
"""
            tries_left -= 1

    # We failed
    return None, errors, {'interpret_image': total_cost}

async def interpret_image_with_prompt(image_path, expanded_description, page_number, prompt_id, params, callback=None):
    if prompt_id == 'multiple_questions':
        return await interpret_image_with_prompt_multiple_questions(image_path, expanded_description, page_number, params, callback=callback)
    
    # Retrieve the prompt template based on prompt_id
    prompt_template = get_prompt_template(prompt_id, 'page_interpretation')

    story_data = get_story_data(params)
    formatted_story_data = json.dumps(story_data, indent=4)
    
    page_text = get_page_text(page_number, params)

    prompt = prompt_template.format(formatted_story_data=formatted_story_data,
                                    page_number=page_number,
                                    page_text=page_text)

    # Perform the API call
    tries_left = params['n_retries'] if 'n_retries' in params else 5
    total_cost = 0
    errors = ''

    while tries_left:
        try:
            api_call = await get_api_chatgpt4_interpret_image_response_for_task(
                prompt,
                image_path,
                'evaluate_page_image',
                params,
                callback=callback
            )
            image_interpretation = api_call.response
            total_cost += api_call.cost
            return image_interpretation, errors, {'interpret_image': total_cost}
        
        except Exception as e:
            error = f'"{str(e)}"\n{traceback.format_exc()}'
            errors += f"""{error}
------------------
"""
            tries_left -= 1

    # We failed
    return None, errors, {'interpret_image': total_cost}

async def interpret_image_with_prompt_multiple_questions(image_path, expanded_description, page_number, params, callback=None):
    total_cost = 0
    errors = ''

    try:
        # Find the elements in the image
        elements_in_image, elements_in_image_errors, get_elements_cost = await get_elements_shown_in_image(image_path, params, callback=callback)
        total_cost += get_elements_cost
        errors += elements_in_image_errors
        if not elements_in_image:
            return None, errors, {'interpret_image': total_cost}

        # Get descriptions of the relevant elements and the style
        element_and_style_descriptions, description_errors, descriptions_cost = await get_elements_descriptions_and_style_in_image(image_path, elements_in_image,
                                                                                                                                   params, callback=callback)
        total_cost += descriptions_cost
        errors += description_errors
        if not element_and_style_descriptions:
            return None, errors, {'interpret_image': total_cost}

        # Find the important pairs
        important_pairs, pairs_errors, pairs_cost = await get_important_pairs_in_image(elements_in_image, expanded_description, params, callback=callback)
        total_cost += pairs_cost
        errors += description_errors
        if not important_pairs:
            return None, errors, {'interpret_image': total_cost}

        # Get descriptions of the relationships obtaining for the important pairs
        tasks = []
        for pair in important_pairs:
            tasks.append(get_relationship_of_element_pair_in_image(pair, image_path, params))
        results = await asyncio.gather(*tasks)
        pair_descriptions = [ result[0] for result in results ]
        pair_errors = [ result[1] for result in results ]
        errors += "\n------------------".join(pair_errors)
        pair_description_costs = sum([ result[2] for result in results ])
        total_cost += pair_description_costs

        # Put everything together
        full_description = combine_results_of_multiple_questions(elements_in_image, element_and_style_descriptions, pair_descriptions)
        return full_description, errors, {'interpret_image': total_cost}

    except Exception as e:
        error_message = f'"{str(e)}"\n{traceback.format_exc()}'
        print(error_message)
        errors += error_message
        return None, errors, {'interpret_image': total_cost}
        
async def get_elements_shown_in_image(image_path, params, callback=None):
    # Retrieve the prompt template based on prompt_id
    prompt_template = get_prompt_template('default', 'get_elements_shown_in_image')

    text = get_text(params)

    elements = get_all_element_texts(params)

    prompt = prompt_template.format(text=text, elements=elements)

    # Perform the API call
    tries_left = params['n_retries'] if 'n_retries' in params else 5
    total_cost = 0
    errors = ''

    while tries_left:
        try:
            api_call = await get_api_chatgpt4_interpret_image_response_for_task(
                prompt,
                image_path,
                'evaluate_page_image',
                params,
                callback=callback
            )
            image_interpretation = api_call.response
            total_cost += api_call.cost
            elements_present = interpret_chat_gpt4_response_as_json(image_interpretation, object_type='list')

            if all([ element in elements for element in elements_present ]):
                return elements_present, errors, total_cost
            else:
                errors += f"""
Not all elements in {elements_present} are in {elements}
"""
                tries_left -= 1
        
        except Exception as e:
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            print(error_message)
            errors += error_message
            tries_left -= 1

    # We failed
    return None, errors, total_cost

async def get_important_pairs_in_image(elements_in_image, expanded_description, params, callback=None):
    prompt_template = get_prompt_template('default', 'get_important_pairs_in_image')

    text = get_text(params)

    prompt = prompt_template.format(text=text, 
                                    expanded_description=expanded_description,
                                    elements_in_image=elements_in_image)

    # Perform the API call
    tries_left = params['n_retries'] if 'n_retries' in params else 5
    total_cost = 0
    errors = ''

    while tries_left:
        try:
            api_call = await get_api_chatgpt4_response_for_task(
                prompt,
                'evaluate_page_image',
                params,
                callback=callback
            )
            important_pairs_text = api_call.response
            total_cost += api_call.cost
            important_pairs = interpret_chat_gpt4_response_as_json(important_pairs_text, object_type='list')
            if all([ element1 in elements_in_image and element1 in elements_in_image for (element1, element2) in important_pairs ]):
                return important_pairs, errors, total_cost
            else:
                errors += f"""
Not all elements in {important_pairs} are in {elements_in_image}
"""
                tries_left -= 1
        
        except Exception as e:
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            print(error_message)
            errors += error_message
            tries_left -= 1

    # We failed
    return None, errors, total_cost

async def get_elements_descriptions_and_style_in_image(image_path, elements_in_image, params, callback=None):
    prompt_template = get_prompt_template('default', 'get_elements_descriptions_and_style_in_image')

    text = get_text(params)

    prompt = prompt_template.format(text=text, elements_in_image=elements_in_image)

    # Perform the API call
    tries_left = params['n_retries'] if 'n_retries' in params else 5
    total_cost = 0
    errors = ''

    while tries_left:
        try:
            api_call = await get_api_chatgpt4_interpret_image_response_for_task(
                prompt,
                image_path,
                'evaluate_page_image',
                params,
                callback=callback
            )
            image_interpretation = api_call.response
            total_cost += api_call.cost
            return image_interpretation, errors, total_cost
        
        except Exception as e:
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            print(error_message)
            errors += error_message
            tries_left -= 1

    # We failed
    return None, total_cost

async def get_relationship_of_element_pair_in_image(pair, image_path, params, callback=None):
    prompt_template = get_prompt_template('default', 'get_relationship_of_element_pair_in_image')

    element1, element2 = pair

    text = get_text(params)
    
    prompt = prompt_template.format(text=text, element1=element1, element2=element2)

    # Perform the API call
    tries_left = params['n_retries'] if 'n_retries' in params else 5
    total_cost = 0
    errors = ''

    while tries_left:
        try:
            api_call = await get_api_chatgpt4_interpret_image_response_for_task(
                prompt,
                image_path,
                'evaluate_page_image',
                params,
                callback=callback
            )
            image_interpretation = api_call.response
            total_cost += api_call.cost
            image_interpretation_with_heading = f"""Relationship between '{element1}' and '{element2}':
{image_interpretation}
"""
            return image_interpretation_with_heading, errors, total_cost
        
        except Exception as e:
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            errors += error_message
            print(error_message)
            tries_left -= 1

    # We failed
    return None, total_cost

def combine_results_of_multiple_questions(elements_in_image, element_and_style_descriptions, pair_descriptions):
    text = ''

    text += f"""**Elements found in image**
The following elements were found in the image: {elements_in_image}

"""

    text += f"""{element_and_style_descriptions}

"""

    text += f"""**Descriptions of relationships between some pairs of elements**

"""
    for pair_description in pair_descriptions:
        text += f"""- {pair_description}
"""
    return text

async def evaluate_fit_with_prompt(expanded_description, image_description, prompt_id, page_number, params, callback=None):
    # Retrieve the prompt template based on prompt_id
    prompt_template = get_prompt_template(prompt_id, 'page_evaluation')

    story_data = get_story_data(params)
    formatted_story_data = json.dumps(story_data, indent=4)
    
    page_text = get_page_text(page_number, params)

    prompt = prompt_template.format(formatted_story_data=formatted_story_data, page_number=page_number, page_text=page_text,
                                    expanded_description=expanded_description, image_description=image_description)

    # Perform the API call
    tries_left = params['n_retries'] if 'n_retries' in params else 5
    total_cost = 0
    errors = ''

    while tries_left:
        try:
            api_call = await get_api_chatgpt4_response_for_task(
                prompt,
                'evaluate_page_image',
                params,
                callback=callback
            )
            fit_evaluation = api_call.response
            total_cost += api_call.cost
            return fit_evaluation, errors, {'evaluate_fit': total_cost}
        
        except Exception as e:
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            errors += error_message
            print(error_message)
            tries_left -= 1

    # We failed
    return None, errors, {'evaluate_fit': total_cost}
