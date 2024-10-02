
from .clara_chatgpt4 import (
    get_api_chatgpt4_response,
    get_api_chatgpt4_image_response,
    get_api_chatgpt4_interpret_image_response,
    )
from .clara_utils import (
    read_txt_file,
    write_txt_file,
    read_json_file,
    write_json_to_file,
    make_directory,
    absolute_file_name,
    file_exists,
    copy_file
    )

import json
import os
import asyncio
import traceback 

# Test with Lily Goes the Whole Hog

def test_lily_style():
    project_dir = '$CLARA/coherent_images/LilyGoesTheWholeHog'
    api_calls = asyncio.run(process_style(project_dir, 2, 2))
    cost = sum([api_call.cost for api_call in api_calls])
    print(f'Cost = ${cost:2f}')
    
# Style

async def process_style(project_dir, n_expanded_descriptions, n_images_per_description):
    tasks = []
    all_description_dirs = []
    all_api_calls = []
    for description_version_number in range(0, n_expanded_descriptions):
        tasks.append(asyncio.create_task(generate_expanded_style_description_and_images(project_dir, description_version_number, n_images_per_description)))
    results = await asyncio.gather(*tasks)
    for description_dir, api_calls in results:
        all_description_dirs.append(description_dir)
        all_api_calls.extend(api_calls)
    select_best_expanded_style_description_and_image(project_dir, all_description_dirs)
    return all_api_calls

def select_best_expanded_style_description_and_image(project_dir, all_description_dirs):
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

    if best_description_file and typical_image_file:
        copy_file(best_description_file, project_pathname(project_dir, f'style/expanded_style_description.txt'))
        copy_file(typical_image_file, project_pathname(project_dir, f'style/style_image.jpg'))
            

async def generate_expanded_style_description_and_images(project_dir, description_version_number, n_images_per_description):
    # Make directory if necessary
    description_directory = f'style/description_v{description_version_number}'
    make_project_dir(project_dir, description_directory)
    
    # Read the base style description
    base_description = read_project_txt_file(project_dir, f'style/style_description.txt')

    # Get the text of the story
    text = get_text(project_dir)

    all_api_calls = []

    # Create the prompt to expand the style description
    prompt = f"""We are later going to create a set of images to illustrate the following text:

{text}

The intended style in which the images will be produced is briefly described as follows:

{base_description}

For now, please expand the brief description into a detailed specification that can be passed to DALL-E-3 to
generate a single image, appropriate to the story, which exemplifies the style. The description must be at
most 3000 characters long to conform to DALL-E-3's constraints."""

    # Get the expanded description from the AI
    try:
        valid_expanded_description_produced = False
        tries_left = 5
        max_dall_e_3_prompt_length = 4000
        
        while not valid_expanded_description_produced and tries_left:
            description_api_call = await get_api_chatgpt4_response(prompt)
            all_api_calls.append(description_api_call)

            # Save the expanded description
            expanded_description = description_api_call.response
            if len(expanded_description) < max_dall_e_3_prompt_length:
                valid_expanded_description_produced = True
            else:
                tries_left -= 1
            
        write_project_txt_file(expanded_description, project_dir, f'style/description_v{description_version_number}/expanded_description.txt')

        # Create and rate the images
        image_api_calls = await generate_and_rate_style_images(project_dir, expanded_description, description_version_number, n_images_per_description)
        all_api_calls.extend(image_api_calls)

        return description_directory, all_api_calls

    except Exception as e:
        error_message = f'"{str(e)}"\n{traceback.format_exc()}'
        write_project_txt_file(error_message, project_dir, f'style/description_v{description_version_number}/error.txt')

    return description_directory, []

async def generate_and_rate_style_images(project_dir, description, description_version_number, n_images_per_description):
    description_dir = f'style/description_v{description_version_number}'
    make_project_dir(project_dir, description_dir)
    
    tasks = []
    all_image_dirs = []
    all_api_calls = []
    for image_version_number in range(0, n_images_per_description):
        tasks.append(asyncio.create_task(generate_and_rate_style_image(project_dir, description, description_version_number, image_version_number)))
    results = await asyncio.gather(*tasks)
    for image_dir, api_calls in results:
        all_image_dirs.append(image_dir)
        all_api_calls.extend(api_calls)

    score_description_dir(project_dir, description_dir, all_image_dirs)
        
    return all_api_calls

def score_description_dir(project_dir, description_dir, image_dirs):
    scores_and_images_dirs = [ ( score_for_image_dir(project_dir, image_dir), image_dir )
                               for image_dir in image_dirs ]
    scores = [ item[0] for item in scores_and_images_dirs ]
    av_score = sum(scores) / len(scores)

    # Find the image most representative of the average score

    closest_match = 10.0
    closest_file = None

    for score, image_dir in scores_and_images_dirs:
        image_file = project_pathname(project_dir, f'{image_dir}/image.jpg')
        if abs(score - av_score ) < closest_match and file_exists(image_file):
            closest_match = abs(score - av_score )
            closest_file = image_file

    description_dir_info = { 'av_score': av_score,
                             'image': image_file }
                                                                   
    write_project_json_file(description_dir_info, project_dir, f'{description_dir}/image_info.json')

async def generate_and_rate_style_image(project_dir, description, description_version_number, image_version_number):
    all_api_calls = []
    
    image_dir = f'style/description_v{description_version_number}/image_v{image_version_number}'
    # Make directory if necessary
    make_project_dir(project_dir, image_dir)

    try:
        image_file, image_api_call = await generate_style_image(project_dir, image_dir, description)
        all_api_calls.append(image_api_call)

        image_interpretation, interpret_api_call = await interpret_style_image(project_dir, image_dir, image_file)
        all_api_calls.append(interpret_api_call)

        evaluation, evaluation_api_call = await evaluate_style_fit(project_dir, image_dir, description, image_interpretation)

        all_api_calls.append(evaluation_api_call)

    except Exception as e:
        error_message = f'"{str(e)}"\n{traceback.format_exc()}'
        write_project_txt_file(error_message, project_dir, f'{image_dir}/error.txt')
        write_project_txt_file("0", project_dir, f'{image_dir}/evaluation.txt')

    return image_dir, all_api_calls

async def generate_style_image(project_dir, image_dir, description):
    
    image_file = project_pathname(project_dir, f'{image_dir}/image.jpg')
    api_call = await get_api_chatgpt4_image_response(description, image_file)

    return image_file, api_call

async def interpret_style_image(project_dir, image_dir, image_file):

    prompt = """Please provide as detailed a description as possible of the following image, focussing
on the style. The content is not important.

The image has been generated by DALL-E-3 to test whether the instructions used to produce it exemplify the
intended style, and the information you provide will be used to ascertain how good the match is.
"""
    api_call = await get_api_chatgpt4_interpret_image_response(prompt, image_file)

    image_interpretation = api_call.response
    write_project_txt_file(image_interpretation, project_dir, f'{image_dir}/image_interpretation.txt')

    return image_interpretation, api_call

async def evaluate_style_fit(project_dir, image_dir, expanded_description, image_description):
    
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
    api_call = await get_api_chatgpt4_response(prompt)

    evaluation = api_call.response

    write_project_txt_file(evaluation, project_dir, f'{image_dir}/evaluation.txt')
    
    return evaluation, api_call

def score_for_image_dir(project_dir, image_dir):
    try:
        score = read_project_txt_file(project_dir, f'{image_dir}/evaluation.txt')
        return int(score)
    except Exception as e:
        return 0

def get_pages(project_dir):
    story_data = read_project_json_file(project_dir, f'story.json')

    pages = [ item['page_number'] for item in story_data ]
               
    return pages

def get_text(project_dir):
    story_data = read_project_json_file(project_dir, f'story.json')

    text_content = [ item['text'] for item in story_data ]
               
    return '\n'.join(text_content)

# Utilities

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


##    prompt = """Please provide as detailed a description as possible of the following image.
##In particular, list the people, animals and any other creatures in it, and describe each of them
##separately, including such details as size relative to other elements, colour of hair, fur or eyes,
##clothing if applicable, apparent age and ethnicity if applicable, and general demeanour.
##
##Describe the location and background and what, if anything, appears to be happening in the scene.
##
##The image has been generated by DALL-E-3, and the information you provide will be used to ascertain
##how closely it matches the instructions given.
##"""
