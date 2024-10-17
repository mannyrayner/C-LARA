
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
import asyncio
import traceback
import unicodedata

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
               'n_images_per_description': 2,
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
               'n_images_per_description': 2,
               'n_pages': 'all',
               'n_previous_pages': 2,
               'keep_existing_pages': True,
               'models_for_tasks': { 'default': 'gpt-4o',
                                     'generate_page_description': 'o1-mini' }
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
            else:
                error_message = f'Unable to create example image'
                write_project_txt_file(error_message, project_dir, f'style/description_v{description_version_number}/error.txt')
        else:
            error_message = f'Unable to create expanded style description'
            write_project_txt_file(error_message, project_dir, f'style/description_v{description_version_number}/error.txt')

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
    prompt = f"""We are later going to create a set of images to illustrate the following text:

{text}

The intended style in which the images will be produced is briefly described as follows:

{base_description}

For now, please expand the brief style description into a detailed specification that can be used as
part of the prompts later passed to DALL-E-3 to create illustrations for this story and enforce
a uniform appearance.

The expanded style specification should at a minimum include information about the medium and technique, the colour palette,
the line work, and the mood/atmosphere, since these are all critical to maintaining coherence of the images
which will use this style.

The specification needs to be at most 1000 characters long"""

    # Get the expanded description from the AI
    try:
        expanded_description = None
        valid_expanded_description_produced = False
        tries_left = 5
        max_dall_e_3_prompt_length = 1500
        
        while not expanded_description and tries_left:
            description_api_call = await get_api_chatgpt4_response_for_task(prompt, 'generate_style_description', params)
            cost_dict = combine_cost_dicts(total_cost_dict, { 'generate_style_description': description_api_call.cost })

            # Save the expanded description
            expanded_description = description_api_call.response
            if len(expanded_description) < max_dall_e_3_prompt_length:
                valid_expanded_description_produced = True
            else:
                tries_left -= 1
            
        write_project_txt_file(expanded_description, project_dir, f'style/description_v{description_version_number}/expanded_description.txt')

    except Exception as e:
        
        error_message = f'"{str(e)}"\n{traceback.format_exc()}'
        write_project_txt_file(error_message, project_dir, f'style/description_v{description_version_number}/error.txt')

    return valid_expanded_description_produced, expanded_description, total_cost_dict

async def generate_style_description_example(description_version_number, expanded_style_description, params):
    project_dir = params['project_dir']
    
    total_cost_dict = {}
    
    # Get the text of the story
    text = get_text(params)

    # Create the prompt to expand the style description
    prompt = f"""We are later going to create a set of images to illustrate the following text:

{text}

The style in which the images will be produced is described as follows:

{expanded_style_description}

For now, please expand the style description into a detailed specification that can be passed to DALL-E-3 to
generate a single image, appropriate to the story, which exemplifies the style. The description must be at
most 3000 characters long to conform to DALL-E-3's constraints."""

    # Get the expanded description from the AI
    try:
        image_description = None
        valid_image_description_produced = False
        tries_left = 5
        max_dall_e_3_prompt_length = 4000
        
        while not valid_image_description_produced and tries_left:
            description_api_call = await get_api_chatgpt4_response_for_task(prompt, 'generate_example_style_description', params)
            cost_dict = combine_cost_dicts(total_cost_dict, { 'generate_style_description': description_api_call.cost })

            # Save the expanded description
            image_description = description_api_call.response
            if len(image_description) < max_dall_e_3_prompt_length:
                valid_image_description_produced = True
            else:
                tries_left -= 1
            
        write_project_txt_file(image_description, project_dir, f'style/description_v{description_version_number}/example_image_description.txt')

    except Exception as e:
        
        error_message = f'"{str(e)}"\n{traceback.format_exc()}'
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

    prompt = """Please provide as detailed a description as possible of the following image, focussing
on the style. The content is not important.

The image has been generated by DALL-E-3 to test whether the instructions used to produce it exemplify the
intended style, and the information you provide will be used to ascertain how good the match is.
"""
    api_call = await get_api_chatgpt4_interpret_image_response_for_task(prompt, image_file, 'interpret_style_image', params)

    image_interpretation = api_call.response
    write_project_txt_file(image_interpretation, project_dir, f'{image_dir}/image_interpretation.txt')

    return image_interpretation, { 'interpret_style_image': api_call.cost }

async def evaluate_style_fit(image_dir, expanded_description, image_description, params):
    project_dir = params['project_dir']
    
    prompt = f"""Please read the 'style description' and the 'image description' below.

The style description specifies an image exemplifying the style that will be used in a larger set of images.

The image description has been produced by gpt-4o, which was asked to describe the style of the image generated from the style description. 

Compare the style description with the image description and evaluate how well the image matches in terms of style.

Style Description:
{expanded_description}

Image Description:
{image_description}

Score the evaluation as a number fron 0 to 4 according to the following conventions:

4 = excellent
3 = good
2 = clearly accesptable
1 = possibly acceptable
0 = unacceptable

The response will be read by a Python script, so write only the single evaluation score."""
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
    prompt = f"""We are later going to create a set of images to illustrate the following text:

{text}

As part of the process, we need to identify visual elements that occur multiple times in the text,
e.g. characters, objects and locations. In this step, please write out a JSON-formatted list of these
elements. For example, if the text were the traditional nursery rhyme

Humpty Dumpty sat on a wall
Humpty Dumpty had a great fall
All the King's horses and all the King's men
Couldn't put Humpty Dumpty together again

then a plausible list might be

[ "Humpty Dumpty",
  "the wall",
  "the King's horses",
  "the King's men"
]

Please write out only the JSON-formatted list, since it will be read by a Python script."""

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

    prompt = f"""We are going to create a set of images to illustrate the following text:

{text}

The intended style in which the images will be produced is described as follows:

{style_description}

As part of this process, we are first creating detailed descriptions of visual elements that occur multiple times in the text, such as characters, objects, and locations.

**Your task is to create a detailed specification of the element "{element_text}", in the intended style,
to be passed to DALL-E-3 to generate a single image showing how "{element_text}" will be realized.**

**Please ensure that the specification includes specific physical characteristics. For a human character, these would include:**
- **Apparent age**
- **Gender**
- **Ethnicity**
- **Hair color and style**
- **Eye color**
- **Height and build**
- **Clothing and accessories**
- **Distinctive features or expressions**
- **General demeanour**

**Similarly, for an animal we would require characteristics like:**

- **Size and shape**
- **Colour of fur/scales, markings**
- **Eye color**
- **Distinctive features like wings, tail, horns**
- **General demeanour**

**Be as precise and detailed as possible to ensure consistency in the generated images.**

The description should be at most 1000 characters long, as it will later be combined with other descriptions."""

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

    prompt = """Please provide as detailed a description as possible of the following image.
The image has been generated by DALL-E-3 to test whether the instructions used to produce it can
reliably be used to create an image in an illustrated text, and the information you provide
will be used to ascertain how good the match is.

**Please ensure that the specification includes specific physical characteristics.
For a human character, these would include:**
- **Apparent age**
- **Gender**
- **Ethnicity**
- **Hair color and style**
- **Eye color**
- **Height and build**
- **Clothing and accessories**
- **Distinctive features or expressions**
- **General demeanour**

**Similarly, for an animal we would require characteristics like:**

- **Size and shape**
- **Colour of fur/scales, markings**
- **Eye color**
- **Distinctive features like wings, tail, horns**
- **General demeanour**

**Be as precise and detailed as possible.**
"""
    api_call = await get_api_chatgpt4_interpret_image_response_for_task(prompt, image_file, 'interpret_element_image', params)

    image_interpretation = api_call.response
    write_project_txt_file(image_interpretation, project_dir, f'{image_dir}/image_interpretation.txt')

    return image_interpretation, { 'interpret_element_image': api_call.cost }

async def evaluate_element_fit(image_dir, expanded_description, image_description, params):
    project_dir = params['project_dir']
    
    prompt = f"""Please read the 'element description' and the 'image description' below.

The element description specifies an image exemplifying a visual element that will be used multiple times in a larger set of images.

The image description has been produced by GPT-4, which was asked to describe the image generated from the element description.

**Your task is to compare the element description with the image description and evaluate how well they match,
focusing on specific physical characteristics. For a human character, these would include:**
- **Apparent age**
- **Gender**
- **Ethnicity**
- **Hair color and style**
- **Eye color**
- **Height and build**
- **Clothing and accessories**
- **Distinctive features or expressions**

**Similarly, for an animal, relevant characteristics would include:**

- **Size and shape**
- **Colour of fur/scales, markings**
- **Eye color**
- **Distinctive features like wings, tail, horns**
- **General demeanour**

**Identify any discrepancies between the descriptions for each characteristic.**

Score the evaluation as a number from 0 to 4 according to the following conventions:
- **4 = Excellent:** All key characteristics match precisely.
- **3 = Good:** Minor discrepancies that don't significantly affect consistency.
- **2 = Acceptable:** Some discrepancies, but the overall representation is acceptable.
- **1 = Poor:** Significant discrepancies that affect consistency.
- **0 = Unacceptable:** Major mismatches in critical characteristics.

**Provide the evaluation score, followed by a brief summary of any discrepancies identified.**

Element Description:
{expanded_description}

Image Description:
{image_description}

The response will be read by a Python script, so write only the single evaluation score followed by the summary, separated by a newline.

**Example Response:**
3
The hair color differs; the description mentions blonde hair, but the image shows brown hair."""

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
    
    # Get the text of the story
    story_data = get_story_data(params)

    # Create the prompt
    prompt = f"""We are generating a set of images to illustrate the following text, which has been divided into numbered pages:

{json.dumps(story_data, indent=4)}

We are preparing to generate an image for page {page_number}, whose text is

{get_page_text(page_number, params)}

We have already generated detailed descriptions for the previous pages. When we generate the image for page {page_number},
it may be helpful to consult some of these descriptions.

In this step, the task is to write out a JSON-formatted list of the previous pages relevant to page {page_number}.

For example, if the text were the traditional nursery rhyme

[ {{ "page_number": 1, "text": "Humpty Dumpty sat on a wall" }},
  {{ "page_number": 2, "text": "Humpty Dumpty had a great fall" }},
  {{ "page_number": 3, "text": "All the King's horses and all the King's men" }},
  {{ "page_number": 4, "text": "Couldn't put Humpty Dumpty together again" }}
  ]

then a plausible list of relevant previous pages for page 2 would be

[ 1 ]

since we want to appearance of Humpty Dumpty and the wall to be similar in the images of pages 1 and 2.

Please write out only the JSON-formatted list, since it will be read by a Python script.
"""

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

    all_element_texts = get_all_element_texts(params)

    # Create the prompt
    prompt = f"""We are generating a set of images to illustrate the following text, which has been divided into numbered pages:

{json.dumps(story_data, indent=4)}

We are preparing to generate an image for page {page_number}, whose text is

{get_page_text(page_number, params)}

We have already generated detailed descriptions for various elements that occur in more than one page. The list of
elements is the following:

{all_element_texts}

When we later generate the image for page {page_number}, it may be helpful to consult some of these descriptions.

In this step, the task is to write out a JSON-formatted list of the elements relevant to page {page_number}e.

For example, if the text were the traditional nursery rhyme

[ {{ "page_number": 1, "text": "Humpty Dumpty sat on a wall" }},
  {{ "page_number": 2, "text": "Humpty Dumpty had a great fall" }},
  {{ "page_number": 3, "text": "All the King's horses and all the King's men" }},
  {{ "page_number": 4, "text": "Couldn't put Humpty Dumpty together again" }}
  ]

and the list of elements was

[ "Humpty Dumpty",
  "the wall",
  "the King's horses",
  "the King's men"
]

[ 

then a plausible list of relevant elements for page 2 would be

[ "Humpty Dumpty", "the wall"]

since the image on page 2 will contain Humpty Dumpty and the wall, but probably not the King's horses or the King's men.

Please write out only the JSON-formatted list, since it will be read by a Python script.
"""

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

async def generate_image_for_page_and_context(page_number, previous_pages, elements, params, tries_left=3, previous_cost_dict={}):
    project_dir = params['project_dir']
    
    if not tries_left:
        return previous_cost_dict

    n_expanded_descriptions = params['n_expanded_descriptions']
    
    tasks = []
    all_description_dirs = []
    total_cost_dict = previous_cost_dict
    for description_version_number in range(0, n_expanded_descriptions):
        tasks.append(asyncio.create_task(generate_page_description_and_images(page_number, previous_pages, elements, description_version_number, params)))
    results = await asyncio.gather(*tasks)
    for description_dir, cost_dict in results:
        all_description_dirs.append(description_dir)
        total_cost_dict = combine_cost_dicts(total_cost_dict, cost_dict)
    select_best_expanded_page_description_and_image(page_number, all_description_dirs, params)

    # We succeeded
    if file_exists(project_pathname(project_dir, f'pages/page{page_number}/image.jpg')):
        return total_cost_dict
    # None of the descriptions produced a valid image, keep trying
    else:
        return await generate_image_for_page_and_context(page_number, previous_pages, elements, params, tries_left=tries_left-1, previous_cost_dict=total_cost_dict)

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
    
    # Get the text of the story, the style description, the relevant previous pages and the relevant element descriptions
    story_data = get_story_data(params)
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

    total_cost_dict = {}

    # Create the prompt 
    prompt = f"""We are generating a set of images to illustrate the following text, which has been divided into numbered pages:

{json.dumps(story_data, indent=4)}

The intended style in which the images will be produced is described as follows:

{style_description}

We are about to generate the image for page {page_number}, whose text is

{page_text}

We have already generated detailed specifications for the images on the previous pages and also
for various elements (characters, locations, etc) that occur on more than one page.
Here are the specifications of relevant previous pages and elements:

{previous_page_descriptions_text}

{element_descriptions_text}

In this step, please create a detailed specification of the image on page {page_number}, in the intended style
and also consistent with the relevant previous pages and relevant elements, that can be passed to DALL-E-3 to
generate a single image for page {page_number}.

*IMPORTANT*: the specification you write out must be at most 2000 characters long to conform with DALL-E-3's constraints.
"""

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
            if len(expanded_description) < max_dall_e_3_prompt_length:
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
        image_file, image_cost_dict = await generate_page_image(image_dir, description, params)
        total_cost_dict = combine_cost_dicts(total_cost_dict, image_cost_dict)

        image_interpretation, interpret_cost_dict = await interpret_page_image(image_dir, image_file, params)
        total_cost_dict = combine_cost_dicts(total_cost_dict, interpret_cost_dict)

        evaluation, evaluation_cost_dict = await evaluate_page_fit(image_dir, description, image_interpretation, params)
        total_cost_dict = combine_cost_dicts(total_cost_dict, evaluation_cost_dict)

    except Exception as e:
        error_message = f'"{str(e)}"\n{traceback.format_exc()}'
        write_project_txt_file(error_message, project_dir, f'{image_dir}/error.txt')
        write_project_txt_file("0", project_dir, f'{image_dir}/evaluation.txt')

    write_project_cost_file(total_cost_dict, project_dir, f'{image_dir}/cost.json')
    return image_dir, total_cost_dict

async def generate_page_image(image_dir, description, params):
    project_dir = params['project_dir']
    
    image_file = project_pathname(project_dir, f'{image_dir}/image.jpg')
    api_call = await get_api_chatgpt4_image_response_for_task(description, image_file, 'generate_page_image', params)

    return image_file, { 'generate_page_image': api_call.cost }

async def interpret_page_image(image_dir, image_file, params):
    project_dir = params['project_dir']

    prompt = """Please provide as detailed a description as possible of the following image.
The image has been generated by DALL-E-3 from a specification produced by gpt-4o, and the information you provide
will be used to ascertain how good the match is between the specification and the image.

Describe the overall appearance of the image and add detailed descriptions of elements such as people, animals and important objects.
Make sure that these descriptions includes specific physical characteristics. 
For a human character, these characteristic would include:
- **Apparent age**
- **Gender**
- **Ethnicity**
- **Hair color and style**
- **Eye color**
- **Height and build**
- **Clothing and accessories**
- **Distinctive features or expressions**
- **General demeanour**

**Similarly, for an animal we would require characteristics like:**

- **Size and shape**
- **Colour of fur/scales, markings**
- **Eye color**
- **Distinctive features like wings, tail, horns**
- **General demeanour**

**Be as precise and detailed as possible.**
"""
    api_call = await get_api_chatgpt4_interpret_image_response_for_task(prompt, image_file, 'interpret_page_image', params)

    image_interpretation = api_call.response
    write_project_txt_file(image_interpretation, project_dir, f'{image_dir}/image_interpretation.txt')

    return image_interpretation, { 'interpret_page_image': api_call.cost }

async def evaluate_page_fit(image_dir, expanded_description, image_description, params):
    project_dir = params['project_dir']
    
    prompt = f"""Please read the 'image specification' and the 'image description' below.

The image specification gives the instructions passed to DALL-E-3 to create one of the images illustrating a text.

The image description has been produced by gpt-4o, which was asked to describe the image generated from the image specification. 

**Your task is to compare the image specification with the image description and evaluate how well they match.
Compare both the overall image and elements such as people, animals and important objects,
focusing on specific physical characteristics. For a human character, these would include:**
- **Apparent age**
- **Gender**
- **Ethnicity**
- **Hair color and style**
- **Eye color**
- **Height and build**
- **Clothing and accessories**
- **Distinctive features or expressions**

**Similarly, for an animal, relevant characteristics would include:**

- **Size and shape**
- **Colour of fur/scales, markings**
- **Eye color**
- **Distinctive features like wings, tail, horns**
- **General demeanour**

**Identify any discrepancies between the descriptions for each characteristic.**

Score the evaluation as a number from 0 to 4 according to the following conventions:
- **4 = Excellent:** All key characteristics match precisely.
- **3 = Good:** Minor discrepancies that don't significantly affect consistency.
- **2 = Acceptable:** Some discrepancies, but the overall representation is acceptable.
- **1 = Poor:** Significant discrepancies that affect consistency.
- **0 = Unacceptable:** Major mismatches in critical characteristics.

**Provide the evaluation score, followed by a brief summary of any discrepancies identified.**

+Image specification:
{expanded_description}

Image Description:
{image_description}

The response will be read by a Python script, so write only the single evaluation score followed by the summary, separated by a newline.

**Example Response:**
3
The hair color of the girl is different; the specification mentions blonde hair, but the image shows brown hair."""
    
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
            page_text = page['text']
            page_text_lines = page_text.split('\\n')
            html_content += f"<h3>Page {page_number}</h3>"
            html_content += f"<p><strong>Text</strong></p>"
            for page_text_line in page_text_lines:
                html_content += f"<p>{page_text_line}</p>"

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
            closest_file = image_file
            closest_interpretation_file = interpretation_file
            closest_evaluation_file = evaluation_file

    description_dir_info = { 'av_score': av_score,
                             'image': closest_file,
                             'interpretation': closest_interpretation_file,
                             'evaluation': closest_evaluation_file}
                                                                   
    write_project_json_file(description_dir_info, project_dir, f'{description_dir}/image_info.json')

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

# -----------------------------------------------

def score_for_image_dir(image_dir, params):
    project_dir = params['project_dir']
    
    try:
        evaluation_response = read_project_txt_file(project_dir, f'{image_dir}/evaluation.txt')
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


# Utilities

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

