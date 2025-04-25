
##from .clara_coherent_images_utils import (
##    project_params_for_simple_clara,
##    get_api_chatgpt4_response_for_task,
##    get_api_chatgpt4_image_response_for_task
##    )

from .clara_chatgpt4 import (
    get_api_chatgpt4_response,
    get_api_chatgpt4_image_response
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

import asyncio
import traceback

style_file = '$CLARA/linguistic_data/kok_kaper/language_game_style.txt'

def create_kk_language_game_style():
    prompt = """Create a description of an image style suitable for a language game that will be played by
Aboriginal children at a school in Cape York, Queensland. The style should be inspired by traditional
Aboriginal art and borrow elements from it.
"""
    try:
        api_call = asyncio.run(get_api_chatgpt4_response(prompt))
        style_description = api_call.response
        print(f'Style: {style_description}')    
        write_txt_file(style_description, style_file)
    except Exception as e:
        format(f"Error when trying to create style")
        format(f"Exception: {str(e)}\n{traceback.format_exc()}")

async def create_kk_language_game_images(n_tasks=1000):
    data = read_json_file('$CLARA/linguistic_data/kok_kaper/language_game_animals.json')
    animals = data['animals']
    adjectives = data['adjectives']
    body_parts = data['body_parts']
    tasks = []
    for animal in animals[:n_elements]:
        for adjective in adjectives[:n_elements]:
            for body_part in body_parts[:n_elements]:
                if len(tasks) <= n_tasks:
                    tasks.append(asyncio.create_task(create_kk_language_game_image(animal, adjective, body_part)))
    results = await asyncio.gather(*tasks)

async def create_kk_language_game_image(animal, adjective, body_part):
    style = read_txt_file(style_file)
    image_file = kk_image_file(animal, adjective, body_part)
    prompt = f"""Using the following style:

{style}

create an image matching the description:

{animal} with {adjective} {body_part}

(This has been literally translated from the Aboriginal language Kok Kaper).

Note that incongruous combinations are perfectly acceptable in the context of the game and may even be considered more amusing.
"""
    await get_api_image_response(prompt, image_file)

def kk_image_file(animal, adjective, body_part):
    return f'{animal}_{afjective}_{body_part}.jpg'
               
