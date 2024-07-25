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

from openai import OpenAI
from PIL import Image
from io import BytesIO

config = get_config()

def get_open_ai_api_key(config_info):
    if 'open_ai_api_key' in config_info and config_info['open_ai_api_key'] and config_info['open_ai_api_key'] != 'None':
        key = config_info['open_ai_api_key']
        source = 'C-LARA config'
    else:
        key = os.environ.get("OPENAI_API_KEY")
        source = 'env variable OPENAI_API_KEY'
        
    #print(f'open_ai_api_key = "{key}" (from {source})')
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
    gpt_model = config_info['gpt_model'] if 'gpt_model' in config_info else 'gpt-4-1106-preview'
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
    gpt_model = config_info['gpt_model'] if 'gpt_model' in config_info else 'gpt-4-1106-preview'
    n_prompt_chars = int(config.get('chatgpt4_trace', 'max_prompt_chars_to_show'))
    n_response_chars = int(config.get('chatgpt4_trace', 'max_response_chars_to_show'))
    if n_prompt_chars != 0:
        truncated_prompt = prompt if len(prompt) <= n_prompt_chars else prompt[:n_prompt_chars] + '...'
        await post_task_update_async(callback, f'--- Sending request to {gpt_model}: "{truncated_prompt}"')
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

    response_string = response.choices[0].message.content
    if n_response_chars != 0:
        truncated_response = response_string if len(response_string) <= n_response_chars else response_string[:n_response_chars] + '...'
        await post_task_update_async(callback, f'--- Received response from {gpt_model}: "{truncated_response}"')
    cost = clara_openai.cost_of_gpt4_api_call(messages, response_string, gpt_model=gpt_model)
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

    save_openai_response_image(response_url, image_file)

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
def save_openai_response_image(url, image_file):
    abs_image_file = absolute_local_file_name(image_file)
    response = requests.get(url)
    image = Image.open(BytesIO(response.content))
    # 512x512 is more convenient for C-LARA
    image = image.resize((512, 512), Image.Resampling.LANCZOS)
    image.convert("RGB").save(abs_image_file)

# Quite often, JSON responses come back wrapped in some text, usually
#
#   json```<CorrectJSON>```
#
# Try stripping off the wrapper, assuming there is a JSON string of the right type, and try again
def interpret_chat_gpt4_response_as_json(response, object_type='list', callback=None):
    try:
        return json.loads(response)
    except:
        try:
            return extract_json_list_from_response_string_ignoring_wrappers(response, object_type=object_type, callback=callback)
        except:
            raise ChatGPTError(message = f'Response is not correctly formatted JSON: {response}')

def extract_json_list_from_response_string_ignoring_wrappers(response, object_type='list', callback=None):
    _valid_object_types = ( 'list', 'dict' )
    if not object_type in _valid_object_types:
        raise ChatGPTError(message = f'object_type argument {object_type} in call to extract_json_list_from_response_string_ignoring_wrappers not one of {_valid_object_types}')
    start_char = '[' if object_type == 'list' else '{'
    end_char = ']' if object_type == 'list' else '}'
    # Attempt to find the start and end of the JSON object
    start_index = response.find(start_char)
    end_index = response.rfind(end_char) + 1  # Include the closing bracket

    if start_index != -1 and end_index != -1:
        # Extract the JSON string
        json_str = response[start_index:end_index]
        # Parse the JSON string into a Python object
        result = json.loads(json_str)
        post_task_update(callback, f'--- Removed "{response[:start_index]}" from start of response and "{response[end_index:]}" from end')
        return result
    else:
        raise ValueError("Valid JSON list not found in response")
