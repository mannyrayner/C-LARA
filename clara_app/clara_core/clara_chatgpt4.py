"""
clara_chatgpt4.py

This module provides functionality to interact with OpenAI's ChatGPT-4 model for the CLARA application. It offers methods to send a prompt to the ChatGPT-4 API and return the generated response.

Functions:
- call_chat_gpt4(prompt): Sends a prompt to ChatGPT-4 and returns the response.
- get_api_chatgpt4_response(prompt): Sends a prompt to the ChatGPT-4 API and returns the response.

This module also provides an option to use a manual alternative to the ChatGPT-4 API by setting the USE_API flag to False.
"""

from .clara_classes import *
from . import clara_openai
# Comment this out for now. We haven't used it for ages, and it confuses Heroku.
#from . import clara_chatgpt4_manual
from . import clara_utils

import os
import openai
import requests
import time
from retrying import retry
from openai.error import RateLimitError, Timeout

openai.api_key = os.environ["OPENAI_API_KEY"]

config = clara_utils.get_config()

# Set up OpenAI API client

USE_API = True  # Set to False to use the manual alternative

# Define a function to check if an exception is a timeout or a rate limit error
def is_retryable_exception(exception):
    return isinstance(exception, (Timeout, RateLimitError))

# Specify retry parameters: wait 5 seconds between retries, and retry up to 5 times
@retry(stop_max_attempt_number=5, wait_fixed=5000, retry_on_exception=is_retryable_exception)
def call_chat_gpt4(prompt):
    if USE_API:
        return get_api_chatgpt4_response(prompt)
    else:
        return clara_chatgpt4_manual.get_chatgpt4_response(prompt)

def get_api_chatgpt4_response(prompt):
    start_time = time.time()
    n_prompt_chars = int(config.get('chatgpt4_trace', 'max_prompt_chars_to_show'))
    n_response_chars = int(config.get('chatgpt4_trace', 'max_response_chars_to_show'))
    if n_prompt_chars != 0:
        truncated_prompt = prompt if len(prompt) <= n_prompt_chars else prompt[:n_prompt_chars] + '...'
        clara_utils.print_and_flush(f'--- Sending request to ChatGPT-4: "{truncated_prompt}"')
    messages = [ {"role": "system", "content": "You are a helpful assistant."},
                 {"role": "user", "content": prompt} ]
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=messages,
        max_tokens=4000,
        n=1,
        stop=None,
        temperature=0.9,
    )
    response_string = response.choices[0]['message']['content']
    if n_response_chars != 0:
        truncated_response = response_string if len(response_string) <= n_response_chars else response_string[:n_response_chars] + '...'
        clara_utils.print_and_flush(f'--- Received response from ChatGPT-4: "{truncated_response}"')
    cost = clara_openai.cost_of_gpt4_api_call(messages, response_string)
    elapsed_time = time.time() - start_time
    clara_utils.print_and_flush(f'--- Done (${cost:.2f}; {elapsed_time:.1f} secs)')
    
    # Create an APICall object
    api_call = APICall(
        prompt=prompt,
        response=response_string,
        cost=cost,
        duration=elapsed_time,
        timestamp=start_time,
        retries=0  # We will need to update the way retries are tracked if we want this to be accurate
    )
    
    return api_call
