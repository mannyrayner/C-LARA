from .clara_coherent_images_utils import (
    get_all_element_names_and_texts,
    project_pathname,
    )

from .clara_coherent_images_advice import (
    get_background_advice,
    get_style_advice,
    get_element_advice,
    get_page_advice,
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
    post_task_update_async,
    post_task_update,
    )

import asyncio
import os
import json
from pathlib import Path
import pprint

async def get_alternate_images_json(content_dir, project_dir, force_remake=False, callback=None):
    """
    Retrieve the alternate_images.json data from the specified content directory.
    If the file does not exist, create it first.

    Args:
        content_dir (str or Path): The path to the content directory.
        project_dir (str or Path): The path to the top-level coherent images v2 directory for the project.
        callback (function, optional): A callback function for task updates.

    Returns:
        list: A list of dictionaries representing the alternate images.
    """
    FORCE_REMAKE = True
    #FORCE_REMAKE = False
    
    content_dir = Path(absolute_file_name(content_dir))
    alternate_images_json_path = content_dir / 'alternate_images.json'
 
    # Check if the alternate_images.json file exists
    if FORCE_REMAKE or not file_exists(alternate_images_json_path):
        # Create the alternate_images.json file
        await create_alternate_images_json(content_dir, project_dir, callback)

    # Read the alternate_images.json file if it could be created, else return an empty list
    if file_exists(alternate_images_json_path):
        alternate_images = read_json_file(alternate_images_json_path)
        return alternate_images
    else:
        return []

async def create_alternate_images_json(content_dir, project_dir, callback=None):
    """
    Create an alternate_images.json file in the specified content directory.
    
    Args:
        content_dir (str): The path to the content directory.
        project_dir (str): The path to the top level coherent images v2 directory for the project.
    """
    content_dir = Path(absolute_file_name(content_dir))
    project_dir = Path(absolute_file_name(project_dir))
    alternate_images = []
    id_counter = 1  # Initialize an ID counter for alternate images

    # Check if the content directory exists
    if not directory_exists(content_dir):
        post_task_update_async(callback, f"Content directory {content_dir} does not exist or is not a directory.")
        return

    # Iterate over description directories (e.g., description_v0, description_v1, ...)
    for description_dir in sorted(content_dir.glob('description_v*')):
        if directory_exists(description_dir):
            description_index = int(description_dir.name.split('_v')[-1])  # Get the version index
            # Paths to expanded description, interpretation, and evaluation
            expanded_description_path = description_dir / 'expanded_description.txt'
            interpretation_path = description_dir / 'interpretation.txt'
            evaluation_path = description_dir / 'evaluation.txt'

            # Iterate over image directories within the description directory
            for image_dir in sorted(description_dir.glob('image_v*')):
                if directory_exists(image_dir):
                    image_index = int(image_dir.name.split('_v')[-1]) 
                    image_path = image_dir / 'image.jpg'
                    image_interpretation_path = image_dir / 'image_interpretation.txt'
                    image_evaluation_path = image_dir / 'evaluation.txt'

                    if file_exists(image_path):
                        
                        # Build the relative paths (relative to the content directory)
                        relative_image_path = image_path.relative_to(project_dir).as_posix()
                        relative_expanded_description_path = expanded_description_path.relative_to(project_dir) if expanded_description_path.exists() else None
                        relative_interpretation_path = interpretation_path.relative_to(project_dir) if interpretation_path.exists() else None
                        relative_evaluation_path = evaluation_path.relative_to(project_dir) if evaluation_path.exists() else None
                        relative_image_interpretation_path = image_interpretation_path.relative_to(project_dir) if image_interpretation_path.exists() else None
                        relative_image_evaluation_path = image_evaluation_path.relative_to(project_dir) if image_evaluation_path.exists() else None

                        # Get the hidden status
                        hidden_status = get_alternate_image_hidden_status(content_dir, description_index, image_index)

                        # Create the alternate image record
                        alternate_image = {
                            'id': id_counter,
                            'description_index': description_index,
                            'image_index': image_index,
                            'image_path': str(relative_image_path),
                            'expanded_description_path': str(relative_expanded_description_path) if relative_expanded_description_path else None,
                            'image_interpretation_path': str(relative_image_interpretation_path) if relative_image_interpretation_path else None,
                            'image_evaluation_path': str(relative_image_evaluation_path) if relative_image_evaluation_path else None,
                            'hidden': hidden_status,
                        }

                        alternate_images.append(alternate_image)
                        id_counter += 1

    # Write the alternate_images.json file
    alternate_images_json_path = content_dir / 'alternate_images.json'
    write_json_to_file(alternate_images, alternate_images_json_path)

    post_task_update_async(callback, f"Created alternate_images.json in {content_dir}")

def promote_alternate_image(content_dir, project_dir, alternate_image_id):
    """
    Promote an alternate image to be the primary image.

    Args:
        content_dir (str or Path): The path to the content directory.
        project_dir (str or Path): The path to the project directory.
        alternate_image_id (int): The ID of the alternate image to promote.
    """
    content_dir = Path(content_dir)
    project_dir = Path(project_dir)
    
    # Read the alternate_images.json file
    alternate_images = read_json_file(content_dir / 'alternate_images.json')

    # Find the alternate image with the given ID
    for alt_image in alternate_images:
        if alt_image['id'] == alternate_image_id:
            # Copy the relevant files to the top-level content directory
            if alt_image['image_path']:
                copy_file(project_dir / alt_image['image_path'], content_dir / 'image.jpg')
            if alt_image['expanded_description_path']:
                copy_file(project_dir / alt_image['expanded_description_path'], content_dir / 'expanded_description.txt')
            if alt_image['image_interpretation_path']:           
                copy_file(project_dir / alt_image['image_interpretation_path'], content_dir / 'interpretation.txt')
            if alt_image['image_evaluation_path']:
                copy_file(project_dir / alt_image['image_evaluation_path'], content_dir / 'evaluation.txt')

            return True  # Indicate success

    return False  # Indicate failure if ID not found

def promote_alternate_element_description(content_dir, project_dir, preferred_description_id):
    """
    Promote an alternate description to be the primary description.

    Args:
        content_dir (str or Path): The path to the content directory.
        project_dir (str or Path): The path to the project directory.
        alternate_description_id (int): The ID of the alternate description to promote.
    """
    content_dir = Path(content_dir)
    project_dir = Path(project_dir)
    
    # Get the preferred_description_dir
    preferred_description_dir = content_dir / f'description_v{preferred_description_id}'

    if not directory_exists(preferred_description_dir):
        raise ValueError(f'Directory {preferred_description_dir} not found in promote_alternate_element_description')

    # Read the alternate_images.json file
    alternate_images = read_json_file(content_dir / 'alternate_images.json')

    # Find the alternate image with the given ID
    for alt_image in alternate_images:
        if alt_image['description_index'] == preferred_description_id:
            # Copy the relevant files to the top-level content directory
            if alt_image['image_path']:
                copy_file(project_dir / alt_image['image_path'], content_dir / 'image.jpg')
            if alt_image['expanded_description_path']:
                copy_file(project_dir / alt_image['expanded_description_path'], content_dir / 'expanded_description.txt')
            if alt_image['image_interpretation_path']:           
                copy_file(project_dir / alt_image['image_interpretation_path'], content_dir / 'interpretation.txt')
            if alt_image['image_evaluation_path']:
                copy_file(project_dir / alt_image['image_evaluation_path'], content_dir / 'evaluation.txt')

            return True  # Indicate success

def set_alternate_image_hidden_status(content_dir, description_index, image_index, hidden=True):
    """
    Set the hidden status of an alternate image by creating or removing a 'hidden' marker file.

    Args:
        content_dir (str): Path to the content directory.
        description_index (int): Index of the description.
        image_index (int): Index of the image within the description.
        hidden (bool): Whether to hide (True) or unhide (False) the image.

    Returns:
        None
    """
    image_dir = Path(content_dir) / f"description_v{description_index}/image_v{image_index}"
    hidden_file = image_dir / "hidden"

    if hidden:
        hidden_file.touch()  # Create the hidden marker file
    else:
        if hidden_file.exists():
            hidden_file.unlink()  # Remove the hidden marker file

def get_alternate_image_hidden_status(content_dir, description_index, image_index):
    """
    Get the hidden status of an alternate image by checking for the presence of a 'hidden' marker file.

    Args:
        content_dir (str): Path to the content directory.
        description_index (int): Index of the description.
        image_index (int): Index of the image within the description.

    Returns:
        bool: True if the image is hidden, False otherwise.
    """
    image_dir = Path(content_dir) / f"description_v{description_index}/image_v{image_index}"
    hidden_file = image_dir / "hidden"
    return hidden_file.exists()

def test_get_project_images_dict(id):
    print(f'id = "{id}"')
    if id == 'boy_meets_girl':
        project_dir = '$CLARA/clara_content/Boy_Meets_Girl_v3_307/coherent_images_v2_project_dir'
    elif id == 'icelandic':
        project_dir = '$CLARA/clara_content/Icelandic_picture_dictionary_314/coherent_images_v2_project_dir'
    elif id == 'kok_kaper':
        project_dir = '$CLARA/clara_content/Kok_Kaper_10_words_dot_painting_cartoon_None/coherent_images_v2_project_dir'
    else:
        print(f'Unknown id: {id}')
        return

    result = asyncio.run(get_project_images_dict(project_dir))
    pprint.pprint(result)

async def get_project_images_dict(project_dir):
    project_dir = Path(absolute_file_name(project_dir))
    params = { 'project_dir': project_dir }
    images_dict = {
        'background': '',
        'style': None,
        'elements': {},
        'pages': {}
    }

    # Background
    background = get_background_advice(params)
    images_dict['background'] = background

    # Style Image
    style_dir = project_dir / 'style'
    if style_dir.exists():
        style_image_path = style_dir / 'image.jpg'
        advice = get_style_advice(params)
        alternate_images = await get_alternate_images_info_for_get_project_images_dict(style_dir, project_dir)

        style_data = {
            'relative_file_path': str(style_image_path.relative_to(project_dir).as_posix()) if style_image_path.exists() else None,
            'advice': advice,
            'alternate_images': alternate_images
        }

        images_dict['style'] = style_data

    # Elements
    elements_dir = project_dir / 'elements'
    element_names_and_texts = get_all_element_names_and_texts(params)
    for item in element_names_and_texts:
        element_name = item['name']
        element_text = item['text']
        element_dir = elements_dir / element_name
        if element_dir.is_dir():
            image_path = element_dir / 'image.jpg'
            advice = get_element_advice(element_text, params)
            alternate_images = await get_alternate_images_info_for_get_project_images_dict(element_dir, project_dir)

            element_data = {
                'element_name': element_name,
                'element_text': element_text,
                'relative_file_path': str(image_path.relative_to(project_dir).as_posix()) if image_path.exists() else None,
                'advice': advice,
                'alternate_images': alternate_images
            }

            images_dict['elements'][element_text] = element_data

    # Pages
    pages_dir = project_dir / 'pages'
    if pages_dir.exists():
        for page_dir in pages_dir.iterdir():
            if page_dir.is_dir() and page_dir.name.startswith('page'):
                page_number = int(page_dir.name.replace('page', ''))
                image_path = page_dir / 'image.jpg'
                advice = get_page_advice(page_number, params)
                alternate_images = await get_alternate_images_info_for_get_project_images_dict(page_dir, project_dir)

                page_data = {
                    'relative_file_path': str(image_path.relative_to(project_dir).as_posix()) if image_path.exists() else None,
                    'advice': advice,
                    'alternate_images': alternate_images
                }

                images_dict['pages'][page_number] = page_data

    return images_dict

async def get_alternate_images_info_for_get_project_images_dict(content_dir, project_dir):
    alternate_images_info = await get_alternate_images_json(content_dir, project_dir)
    return [ { 'id': item['id'],
               'description_index': item['description_index'],
               'image_index': item['image_index'],
               'relative_file_path': item['image_path'],
               'hidden': item['hidden']
               }
             for item in alternate_images_info ]

async def alternate_image_id_for_description_index(project_dir, page_number, description_index):
    content_dir = f'{project_dir}/pages/page{page_number}'
    alternate_images_info = await get_alternate_images_json(content_dir, project_dir)
    for item in alternate_images_info:
        if item['description_index'] == description_index:
            return item['id']
    raise ValueError(f'Cannot find description_index {description_index} for page {page_number}')


    
