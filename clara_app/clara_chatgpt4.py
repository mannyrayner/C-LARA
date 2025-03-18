"""
clara_chatgpt4.py

This module provides functionality to interact with OpenAI's GPT-4 and other models for the CLARA application.

Functions:

- call_chat_gpt4(prompt, config_info={}, callback=None)
Sends a prompt to ChatGPT-4 and returns an APICall object including the response

- call_chat_gpt4_image(prompt, image_file, config_info={}, callback=None)
Sends a prompt to DALL-E-3, saves the resulting image in image_file, and returns an APICall object

- call_chat_gpt4_interpret_image(prompt, image_file, config_info={}, callback=None):
Sends a prompt to ChatGPT-4V asking to interpret the image in image_file according to the instructions
in prompt, and returns an APICall object including the response

"""

from .clara_classes import *
from . import clara_openai
from .clara_utils import get_config, post_task_update, post_task_update_async, print_and_flush, absolute_file_name, absolute_local_file_name

import asyncio
import os
import requests
import time
import base64
import json
import traceback
import pprint

from openai import OpenAI
from google import genai
from google.genai import types

from PIL import Image
from io import BytesIO

config = get_config()

DEFAULT_GPT_4_MODEL = 'gpt-4o'

def get_api_key_and_provider_for_config(config_info):
    model = config_info['gpt_model'] if 'gpt_model' in config_info else DEFAULT_GPT_4_MODEL
    
    provider = provider_for_model(model)
    if not provider:
        raise ValueError(f'Unable to find provider for model: {model}')

    if provider == openai:
        return get_open_ai_api_key(config_info), provider
    elif provider == deep_seek:
        return get_deep_seek_api_key(config_info), provider
    else:
        raise ValueError(f'Unknown provider declared for model "{model}": {provider}')
            
def get_open_ai_api_key(config_info):
    if 'open_ai_api_key' in config_info and config_info['open_ai_api_key'] and config_info['open_ai_api_key'] != 'None':
        key = config_info['open_ai_api_key']
        source = 'C-LARA config'
    else:
        key = os.environ.get("OPENAI_API_KEY")
        source = 'env variable OPENAI_API_KEY'
        
    #print(f'open_ai_api_key = "{key}" (from {source})\n')
    return key

def get_gemini_api_key(config_info):
    """
    Either read from config_info or fallback to environment variable
    """
    if 'gemini_api_key' in config_info and config_info['gemini_api_key']:
        return config_info['gemini_api_key']
    return os.environ.get('GEMINI_API_KEY', None)

def get_deep_seek_api_key(config_info):
    if 'deep_seek_api_key' in config_info and config_info['deep_seek_api_key'] and config_info['deep_seek_api_key'] != 'None':
        key = config_info['deep_seek_api_key']
        source = 'C-LARA config'
    else:
        key = os.environ.get("DEEP_SEEK_API_KEY")
        source = 'env variable DEEP_SEEK_API_KEY'
        
    #print(f'deep_seek_api_key = "{key}" (from {source})')
    return key

def call_chat_gpt4(prompt, config_info={}, callback=None):
    return asyncio.run(get_api_chatgpt4_response(prompt, config_info=config_info, callback=callback))

def call_chat_gpt4_image(prompt, image_file, config_info={}, callback=None):
    if 'image_model' in config_info and config_info['image_model'] == 'imagen_3':
        shortening_api_calls, prompt = shorten_imagen_3_prompt_if_necessary(prompt, config_info={'gpt_model': DEFAULT_GPT_4_MODEL}, callback=callback)
        image_api_call = asyncio.run(get_api_gemini_image_response(prompt, image_file, config_info=config_info, callback=callback))
    else:
        shortening_api_calls, prompt = shorten_dall_e_3_prompt_if_necessary(prompt, config_info=config_info, callback=callback)
        image_api_call = asyncio.run(get_api_chatgpt4_image_response(prompt, image_file, config_info=config_info, callback=callback))

    return shortening_api_calls + [ image_api_call ]

def shorten_dall_e_3_prompt_if_necessary(prompt, config_info={}, callback=None):
    return shorten_image_generation_prompt_if_necessary(prompt, 'dall_e_3', config_info={}, callback=None)

def shorten_imagen_3_prompt_if_necessary(prompt, config_info={}, callback=None):
    return shorten_image_generation_prompt_if_necessary(prompt, 'imagen_3', config_info={}, callback=None)

def shorten_image_generation_prompt_if_necessary(prompt, image_generation_model, config_info={}, callback=None):
    api_calls = []
    if image_generation_model == 'dall_e_3':
        prompt_length_in_characters = len(prompt)
        prompt_length = prompt_length_in_characters
        max_prompt_length_in_characters = int(config.get('dall_e_3', 'max_prompt_length'))
        
        prompt_is_too_long = ( prompt_length_in_characters > max_prompt_length_in_characters )
        
        prompt_length_unit_for_shortening = 'characters'
        prompt_length_for_shortening = prompt_length_in_characters
        max_prompt_length_for_shortening = max_prompt_length_in_characters
    elif image_generation_model == 'imagen_3':
        WORDS_TO_TOKENS_CONVERSION_FACTOR = 0.75
        prompt_length_in_words = len(prompt.split())
        prompt_length = prompt_length_in_words
        estimated_prompt_length_in_tokens = int(prompt_length_in_words / WORDS_TO_TOKENS_CONVERSION_FACTOR )
        max_prompt_length_in_tokens = int(config.get('imagen_3', 'max_prompt_length'))
        max_prompt_length_in_words = max_prompt_length_in_tokens * WORDS_TO_TOKENS_CONVERSION_FACTOR
        
        prompt_is_too_long = ( estimated_prompt_length_in_tokens > max_prompt_length_in_tokens )
        
        prompt_length_unit_for_shortening = 'words'
        prompt_length_for_shortening = prompt_length_in_words
        max_prompt_length_for_shortening = max_prompt_length_in_words
    else:
        raise ValueError(f'Unknow image generation model name: {image_generation_model}')
    
    if prompt_is_too_long:
        shortening_prompt = f"""The following image generation prompt, currently {prompt_length_for_shortening}
{prompt_length_unit_for_shortening} long, exceeds the maximum permitted prompt length of {max_prompt_length_for_shortening}
{prompt_length_unit_for_shortening}. Please shorten it to under {max_prompt_length_for_shortening} {prompt_length_unit_for_shortening}
while retaining the essential details. Ensure the prompt is still clear and provides enough information for an artist to
create a detailed image.

Here is the prompt:
__________

{prompt}
__________

Return only the shortened prompt, since the result will be read by a Python script.

"""      
        post_task_update(callback, f'--- Shortening DALL-E-3 prompt')
        shortening_api_call = call_chat_gpt4(shortening_prompt, config_info=config_info, callback=callback)
        api_calls.append(shortening_api_call)
        shortened_prompt = shortening_api_call.response
        shortened_prompt_length = len(shortened_prompt)
        post_task_update(callback, f'--- Shortened DALL-E-3 prompt from {prompt_length} to {shortened_prompt_length} chars')
    else:
        shortened_prompt = prompt
        
    return ( api_calls, shortened_prompt )

def call_chat_gpt4_interpret_image(prompt, image_file, config_info={}, callback=None):
    return asyncio.run(get_api_chatgpt4_interpret_image_response(prompt, image_file, config_info=config_info, callback=callback))

def call_openai_api(messages, config_info):
    gpt_model = config_info['gpt_model'] if 'gpt_model' in config_info else DEFAULT_GPT_4_MODEL
    api_key = get_open_ai_api_key(config_info)
    client = OpenAI(api_key=api_key)
    chat_completion = client.chat.completions.create(
        messages=messages,
        model=gpt_model
        )
    return chat_completion

def call_openai_api_image(prompt, gpt_model, size, config_info):
    api_key = get_open_ai_api_key(config_info)
    client = OpenAI(api_key=api_key)
    response = client.images.generate(
        model=gpt_model,
        prompt=prompt,
        size=size,
        quality="standard",
        n=1,
        )
    return response

def call_google_gemini_image(prompt, gemini_model, number_of_images, config_info):
    """
    Synchronous function that calls Gemini with the given prompt.
    Returns a list of raw image bytes or some structured info.
    """
    gemini_api_key = get_gemini_api_key(config_info)
    client = genai.Client(api_key=gemini_api_key)

    # Make the call
    response = client.models.generate_images(
        model=gemini_model,
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=number_of_images
            # Possibly more config (dimensions, style, etc.) if available
        )
    )

    # Return the images (or data) so the async wrapper can write them, etc.
    return response.generated_images

def call_openai_api_interpret_image_url(prompt, image_url, gpt_model, max_tokens, config_info):
    api_key = get_open_ai_api_key(config_info)
    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
      model=gpt_model,
      messages=[
        {
          "role": "user",
          "content": [
            {"type": "text",
             "text": prompt},
            {
              "type": "image_url",
              "image_url": {
                "url": image_url,
                "detail": "high"
              },
            },
          ],
        }
      ],
      max_tokens=max_tokens,
    )

    return response

def call_openai_api_interpret_image(prompt, image_path, gpt_model, max_tokens, config_info):
    api_key = get_open_ai_api_key(config_info)
    client = OpenAI(api_key=api_key)

    # Function to encode the image
    def encode_image(image_path):
      with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

    base64_image = encode_image(image_path)

    headers = {
      "Content-Type": "application/json",
      "Authorization": f"Bearer {api_key}"
    }

    payload = {
      "model": gpt_model,
      "messages": [
        {
          "role": "user",
          "content": [
            {
              "type": "text",
              "text": prompt
            },
            {
              "type": "image_url",
              "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}",
                "detail": "high"
              }
            }
          ]
        }
      ],
      "max_tokens": max_tokens
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    return response

async def get_api_chatgpt4_response(prompt, config_info={}, callback=None):
    start_time = time.time()
    gpt_model = config_info['gpt_model'] if 'gpt_model' in config_info else DEFAULT_GPT_4_MODEL
    n_prompt_chars = int(config.get('chatgpt4_trace', 'max_prompt_chars_to_show'))
    n_response_chars = int(config.get('chatgpt4_trace', 'max_response_chars_to_show'))
    if n_prompt_chars != 0:
        truncated_prompt = prompt if len(prompt) <= n_prompt_chars else prompt[:n_prompt_chars] + '...'
        await post_task_update_async(callback, f'--- Sending request to {gpt_model}: "{truncated_prompt}"')
    if gpt_model in ( 'o1-preview', 'o1-mini' ):
        # o1 does not yet support the 'system' role
        messages = [ {"role": "user", "content": prompt} ]
    else:
        messages = [ {"role": "system", "content": "You are a helpful assistant."},
                     {"role": "user", "content": prompt} ]
    
    loop = asyncio.get_event_loop()

    # Start the API call in a separate thread to not block the event loop
    api_task = loop.run_in_executor(None, call_openai_api, messages, config_info)

    time_waited = 0
    while not api_task.done():
        # This loop serves as a heartbeat mechanism
        await post_task_update_async(callback, f"Waiting for OpenAI response ({time_waited}s elapsed)...")
        
        # Sleep for a short while before checking again
        await asyncio.sleep(5)

        time_waited += 5
    
    # Once the API call is done:
    response = api_task.result()

##    print(f'response:')
##    pprint.pprint(response)

    response_string = response.choices[0].message.content
    if n_response_chars != 0:
        truncated_response = response_string if len(response_string) <= n_response_chars else response_string[:n_response_chars] + '...'
        await post_task_update_async(callback, f'--- Received response from {gpt_model}: "{truncated_response}"')

    # Extract reasoning tokens using attribute access, handling cases where they may not exist
    if hasattr(response.usage, 'completion_tokens_details') and isinstance(response.usage.completion_tokens_details, dict):
        reasoning_tokens = response.usage.completion_tokens_details.get('reasoning_tokens', 0)
    else:
        reasoning_tokens = 0
    
    cost = clara_openai.cost_of_gpt4_api_call(messages, response_string,
                                              gpt_model=gpt_model, reasoning_tokens=reasoning_tokens)
    elapsed_time = time.time() - start_time
    await post_task_update_async(callback, f'--- Done (${cost:.2f}; {elapsed_time:.1f} secs)')
    
    # Create an APICall object
    api_call = APICall(
        prompt=prompt,
        response=response_string,
        cost=cost,
        duration=elapsed_time,
        timestamp=start_time,
        retries=0  
    )
    
    return api_call

async def get_api_image_response(prompt, image_file, config_info={}, callback=None):
    if 'image_model' in config_info and config_info['image_model'] == 'imagen_3':
        return await get_api_gemini_image_response(prompt, image_file, config_info=config_info, callback=callback)
    else:
        return await get_api_chatgpt4_image_response(prompt, image_file, config_info=config_info, callback=callback)

# Version of get_api_chatgpt4_response for creating DALL-E-3 images
async def get_api_chatgpt4_image_response(prompt, image_file, config_info={}, callback=None):
    gpt_model = 'dall-e-3'
    size='1024x1024'
    
    start_time = time.time()
    n_prompt_chars = int(config.get('chatgpt4_trace', 'max_prompt_chars_to_show'))
    if n_prompt_chars != 0:
        truncated_prompt = prompt if len(prompt) <= n_prompt_chars else prompt[:n_prompt_chars] + '...'
        await post_task_update_async(callback, f'--- Sending request to {gpt_model} (size={size}): "{truncated_prompt}"')
    
    loop = asyncio.get_event_loop()

    # Start the API call in a separate thread to not block the event loop
    api_task = loop.run_in_executor(None, call_openai_api_image, prompt, gpt_model, size, config_info)

    time_waited = 0
    while not api_task.done():
        # This loop serves as a heartbeat mechanism
        await post_task_update_async(callback, f"Waiting for OpenAI response ({time_waited}s elapsed)...")
        
        # Sleep for a short while before checking again
        await asyncio.sleep(5)

        time_waited += 5
    
    # Once the API call is done:
    response = api_task.result()

    response_url = response.data[0].url

    await save_openai_response_image(response_url, image_file, callback=callback)

    cost = clara_openai.cost_of_gpt4_image_api_call(prompt, gpt_model=gpt_model, size=size)
    elapsed_time = time.time() - start_time
    await post_task_update_async(callback, f'--- Done (${cost:.2f}; {elapsed_time:.1f} secs)')
    
    # Create an APICall object
    api_call = APICall(
        prompt=prompt,
        response=response_url,
        cost=cost,
        duration=elapsed_time,
        timestamp=start_time,
        retries=0  
    )
    
    return api_call

async def get_api_gemini_image_response(prompt, image_file, config_info={}, callback=None):
    """
    Async wrapper that calls Gemini in a run_in_executor, waits,
    writes the image(s) to disk, returns an APICall-like object.
    """
    gemini_model = 'imagen-3.0-generate-002'
    number_of_images = 1  # Create one image for now to make it like DALL-E-3
    start_time = time.time()

    loop = asyncio.get_event_loop()

    # Possibly show a "Sending request" update:
    truncated_prompt = (prompt[:100] + '...') if len(prompt) > 100 else prompt
    await post_task_update_async(callback, f'--- Sending request to Gemini model={gemini_model}: "{truncated_prompt}"')

    # Run the synchronous call in executor
    api_task = loop.run_in_executor(
        None,
        call_google_gemini_image,
        prompt,
        gemini_model,
        number_of_images,
        config_info
    )

    time_waited = 0
    while not api_task.done():
        await post_task_update_async(callback, f"Waiting for Gemini response ({time_waited}s elapsed)...")
        await asyncio.sleep(5)
        time_waited += 5

    generated_images = api_task.result()  # Should be a list of generated images

    # If you requested multiple images, handle them in a loop
    # If only one, just handle the single item
    # We'll assume you only do n=1 for the example
    if not generated_images:
        # No images returned, handle gracefully
        await post_task_update_async(callback, "--- No images returned by Gemini.")
        # Optionally return an APICall with empty response
        return APICall(
            prompt=prompt,
            response="",
            cost=0.0,
            duration=time.time() - start_time,
            timestamp=start_time,
            retries=0
        )

    generated_image = generated_images[0]
    # The "image_bytes" from google.genai library
    image_data = generated_image.image.image_bytes

    # Save the image to disk at image_file
    await save_gemini_response_image(image_data, image_file, callback=callback)

    elapsed_time = time.time() - start_time
    await post_task_update_async(callback, f'--- Done in {elapsed_time:.1f} secs')

    cost = float(config.get('imagen_3_costs', 'image'))
    
    # Create an APICall object
    api_call = APICall(
        prompt=prompt,
        response=image_file,  # Or some text for the image info
        cost=cost,
        duration=elapsed_time,
        timestamp=start_time,
        retries=0
    )
    return api_call

async def save_gemini_response_image(image_data, image_file, callback=None):
    """
    Takes raw image bytes from Gemini, saves to disk as `image_file`.
    """
    # If you want user feedback:
    await post_task_update_async(callback, f"Saving Gemini image to {image_file}...")

    decoded_data = base64.b64decode(image_data)
    # Save the image using PIL
    img = Image.open(BytesIO(decoded_data))
    img.save(image_file, format="JPEG")  # or PNG

async def get_api_chatgpt4_interpret_image_response(prompt, file_path, gpt_model='gpt-4o', config_info={}, callback=None):
    max_tokens = int(config.get('chatgpt4v', 'max_tokens_to_produce'))
    
    start_time = time.time()
    n_prompt_chars = int(config.get('chatgpt4_trace', 'max_prompt_chars_to_show'))
    n_response_chars = int(config.get('chatgpt4_trace', 'max_response_chars_to_show'))
    if n_prompt_chars != 0:
        truncated_prompt = prompt if len(prompt) <= n_prompt_chars else prompt[:n_prompt_chars] + '...'
        await post_task_update_async(callback, f'--- Sending request to {gpt_model}: "{truncated_prompt}"')
    
    loop = asyncio.get_event_loop()

    # Start the API call in a separate thread to not block the event loop
    api_task = loop.run_in_executor(None, call_openai_api_interpret_image, prompt, file_path, gpt_model, max_tokens, config_info)

    time_waited = 0
    while not api_task.done():
        # This loop serves as a heartbeat mechanism
        await post_task_update_async(callback, f"Waiting for OpenAI response ({time_waited}s elapsed)...")
        
        # Sleep for a short while before checking again
        await asyncio.sleep(5)

        time_waited += 5
    
    # Once the API call is done:
    response = api_task.result()

    #response_string = response.choices[0].message.content
    response_string = response.json()['choices'][0]['message']['content']
    if n_response_chars != 0:
        truncated_response = response_string if len(response_string) <= n_response_chars else response_string[:n_response_chars] + '...'
        await post_task_update_async(callback, f'--- Received response from {gpt_model}: "{truncated_response}"')
    cost = clara_openai.cost_of_gpt4v_api_call(file_path, prompt, response_string, gpt_model=gpt_model)
    elapsed_time = time.time() - start_time
    await post_task_update_async(callback, f'--- Done (${cost:.2f}; {elapsed_time:.1f} secs)')
    
    # Create an APICall object
    api_call = APICall(
        prompt=f'{prompt}: {file_path}',
        response=response_string,
        cost=cost,
        duration=elapsed_time,
        timestamp=start_time,
        retries=0  
    )
    
    return api_call

# Download the image from the url and save it as a 512x512 jpg
async def save_openai_response_image(url, image_file, callback=None):
    try:
        abs_image_file = absolute_local_file_name(image_file)
        await post_task_update_async(callback, f'--- Trying to download image from "{url}"')
        response = requests.get(url)
        await post_task_update_async(callback, f'--- Image downloaded')
        image = Image.open(BytesIO(response.content))
        # 512x512 is more convenient for C-LARA
        image = image.resize((512, 512), Image.Resampling.LANCZOS)
        image.convert("RGB").save(abs_image_file)
    except Exception as e:
        await post_task_update_async(callback, f"Exception when downloading image: {str(e)}\n{traceback.format_exc()}")
        raise ChatGPTError(message = f'Unable to download image from {url}')

# Quite often, JSON responses come back wrapped in some text, usually
#
#   json```<CorrectJSON>```
#
# Try stripping off the wrapper, assuming there is a JSON string of the right type.
# Also, when we're doing Chain of Thought, we typically ask for a piece of "think aloud" analysis, followed by some JSON.
# In both cases, we want the JSON, and in the second one also the text intro.
def interpret_chat_gpt4_response_as_json(response, object_type='list', callback=None):
    ( intro, json ) = extract_intro_and_json_list_from_response_string(response, object_type=object_type, callback=callback)
    return json

def interpret_chat_gpt4_response_as_intro_and_json(response, object_type='list', callback=None):
    try:
        return ( '', json.loads(response) )
    except:
        try:
            return extract_intro_and_json_list_from_response_string(response, object_type=object_type, callback=callback)
        except:
            raise ChatGPTError(message = f'Response is not correctly formatted JSON: {response}')


def extract_intro_and_json_list_from_response_string(response, object_type='list', callback=None):
    # If we find the string "json" or "``" in the response, only take the part after it
    skipped_intro = ''
    if "json" in response:
        components = response.split("json")
        response = components[-1]
        skipped_intro = "json".join(components[:-1])
    elif "``" in response:
        components = response.split("``")
        response = components[-1]
        skipped_intro = "``".join(components[:-1])
        
    _valid_object_types = ( 'list', 'dict' )
    if not object_type in _valid_object_types:
        raise ChatGPTError(message = f'object_type argument {object_type} in call to extract_json_list_from_response_string not one of {_valid_object_types}')
    start_char = '[' if object_type == 'list' else '{'
    end_char = ']' if object_type == 'list' else '}'
    # Attempt to find the start and end of the JSON object
    start_index = response.find(start_char)
    end_index = response.rfind(end_char) + 1  # Include the closing bracket

    if start_index != -1 and end_index != -1:
        # Extract the JSON string
        json_str = response[start_index:end_index]
        # Parse the JSON string into a Python object
        intro = skipped_intro + response[:start_index]
        result = json.loads(json_str)
        #post_task_update(callback, f'--- Intro = "{response[:start_index]}", removed "{response[end_index:]}" from end')
        return ( intro, result )
    else:
        print("Valid JSON list not found in response")
        raise ValueError("Valid JSON list not found in response")
