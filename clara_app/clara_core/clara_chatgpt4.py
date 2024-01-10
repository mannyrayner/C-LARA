"""
clara_chatgpt4.py

This module provides functionality to interact with OpenAI's ChatGPT-4 model for the CLARA application. It offers methods to send a prompt to the ChatGPT-4 API and return the generated response.

Functions:
- call_chat_gpt4(prompt): Sends a prompt to ChatGPT-4 and returns the response.
- get_api_chatgpt4_response(prompt): Sends a prompt to the ChatGPT-4 API and returns the response.

"""

from .clara_classes import *
from . import clara_openai
from .clara_utils import get_config, post_task_update, post_task_update_async, print_and_flush, absolute_local_file_name

import asyncio
import os
import requests
import time

from openai import OpenAI
from PIL import Image
from io import BytesIO

config = get_config()

def call_chat_gpt4(prompt, config_info={}, callback=None):
    gpt_model = config_info['gpt_model'] if 'gpt_model' in config_info else 'gpt-4'
    return asyncio.run(get_api_chatgpt4_response(prompt, gpt_model=gpt_model, callback=callback))

def call_chat_gpt4_image(prompt, image_file, config_info={}, callback=None):
    return asyncio.run(get_api_chatgpt4_image_response(prompt, image_file, callback=callback))

def call_openai_api(messages, gpt_model):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    chat_completion = client.chat.completions.create(
        messages=messages,
        model=gpt_model
        )
    return chat_completion

def call_openai_api_image(prompt, gpt_model, size):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    response = client.images.generate(
        model=gpt_model,
        prompt=prompt,
        size=size,
        quality="standard",
        n=1,
        )
    return response

async def get_api_chatgpt4_response(prompt, gpt_model='gpt-4-1106-preview', callback=None):
    start_time = time.time()
    n_prompt_chars = int(config.get('chatgpt4_trace', 'max_prompt_chars_to_show'))
    n_response_chars = int(config.get('chatgpt4_trace', 'max_response_chars_to_show'))
    if n_prompt_chars != 0:
        truncated_prompt = prompt if len(prompt) <= n_prompt_chars else prompt[:n_prompt_chars] + '...'
        await post_task_update_async(callback, f'--- Sending request to {gpt_model}: "{truncated_prompt}"')
    messages = [ {"role": "system", "content": "You are a helpful assistant."},
                 {"role": "user", "content": prompt} ]
    
    loop = asyncio.get_event_loop()

    # Start the API call in a separate thread to not block the event loop
    api_task = loop.run_in_executor(None, call_openai_api, messages, gpt_model)

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
async def get_api_chatgpt4_image_response(prompt, image_file, callback=None):
    gpt_model = 'dall-e-3'
    size='1024x1024'
    
    start_time = time.time()
    n_prompt_chars = int(config.get('chatgpt4_trace', 'max_prompt_chars_to_show'))
    if n_prompt_chars != 0:
        truncated_prompt = prompt if len(prompt) <= n_prompt_chars else prompt[:n_prompt_chars] + '...'
        await post_task_update_async(callback, f'--- Sending request to {gpt_model} (size={size}): "{truncated_prompt}"')
    
    loop = asyncio.get_event_loop()

    # Start the API call in a separate thread to not block the event loop
    api_task = loop.run_in_executor(None, call_openai_api_image, prompt, gpt_model, size)

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

# Download the image from the url and save it as a 512x512 jpg
def save_openai_response_image(url, image_file):
    abs_image_file = absolute_local_file_name(image_file)
    response = requests.get(url)
    image = Image.open(BytesIO(response.content))
    # 512x512 is more convenient for C-LARA
    image = image.resize((512, 512), Image.Resampling.LANCZOS)
    image.convert("RGB").save(abs_image_file)
    
