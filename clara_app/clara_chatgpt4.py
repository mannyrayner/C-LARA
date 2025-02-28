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
from .clara_utils import get_config, post_task_update, post_task_update_async, print_and_flush, absolute_local_file_name

import asyncio
import os
import requests
import time
import base64
import json
import traceback
import pprint

from openai import OpenAI
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
        
    #print(f'open_ai_api_key = "{key}" (from {source})')
    return key

def get_deep_seek_api_key(config_info):
    if 'deep_seek_api_key' in config_info and config_info['deep_seek_api_key'] and config_info['deep_seek_api_key'] != 'None':
        key = config_info['deep_seek_api_key']
        source = 'C-LARA config'
    else:
        key = os.environ.get("DEEP_SEEK_API_KEY")
        source = 'env variable DEEP_SEEK_API_KEY'
        
    print(f'deep_seek_api_key = "{key}" (from {source})')
    return key

def call_chat_gpt4(prompt, config_info={}, callback=None):
    return asyncio.run(get_api_chatgpt4_response(prompt, config_info=config_info, callback=callback))

def call_chat_gpt4_image(prompt, image_file, config_info={}, callback=None):
    shortening_api_calls, prompt = shorten_dall_e_3_prompt_if_necessary(prompt, config_info=config_info, callback=callback)
    image_api_call = asyncio.run(get_api_chatgpt4_image_response(prompt, image_file, config_info=config_info, callback=callback))
    return shortening_api_calls + [ image_api_call ]

def shorten_dall_e_3_prompt_if_necessary(prompt, config_info={}, callback=None):
    prompt_length = len(prompt)
    max_prompt_length = int(config.get('dall_e_3', 'max_prompt_length'))
    api_calls = []
    if prompt_length > max_prompt_length:
        shortening_prompt = f"""The following DALL-E-3 prompt, currently {prompt_length} characters long, exceeds the maximum
permitted DALL-E-3 prompt length of {max_prompt_length} characters. Please shorten it to under {max_prompt_length} characters
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
