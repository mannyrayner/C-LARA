"""
This module contains utility functions for OpenAI functionality.
The functions assume that a valid license key is in the environment variable OPENAI_API_KEY

1. print_openai_models(). Print a list of all OpenAI models available for this license key.
2. cost_of_gpt4_api_call(messages, response). Return the cost in dollars of a gpt-4 API call.
"""

from . import clara_utils

import openai
import tiktoken
import os

config = clara_utils.get_config()

openai.api_key = os.getenv("OPENAI_API_KEY")

def print_openai_models():
    """List all available models"""
    models = openai.Model.list()

    for model in models['data']:
        print(f"Model ID: {model.id}")

def cost_of_gpt4_api_call(messages, response_string, gpt_model='gpt-4'):
    """Returns the cost in dollars of an OpenAI API call, defined by a prompt in the form of a list of messages and a response string"""
    n_message_tokens = ( num_gpt4_tokens_for_messages(messages) / 1000.0 )
    n_response_tokens = ( num_gpt4_tokens_for_string(response_string) / 1000.0 )

    if gpt_model in ( 'gpt-4o' ):
        message_rate = float(config.get('chatgpt4_o_costs', 'prompt_per_thousand_tokens')) 
        response_rate = float(config.get('chatgpt4_o_costs', 'response_per_thousand_tokens'))
    elif gpt_model in ( 'gpt-4-1106-preview', 'gpt-4-turbo' ):
        message_rate = float(config.get('chatgpt4_turbo_costs', 'prompt_per_thousand_tokens')) 
        response_rate = float(config.get('chatgpt4_turbo_costs', 'response_per_thousand_tokens'))
    # Default is gpt-4
    else:
        message_rate = float(config.get('chatgpt4_costs', 'prompt_per_thousand_tokens')) 
        response_rate = float(config.get('chatgpt4_costs', 'response_per_thousand_tokens'))
       
    input_cost = n_message_tokens * message_rate
    response_cost = n_response_tokens * response_rate
    return input_cost + response_cost

def cost_of_gpt4_image_api_call(prompt, gpt_model='dall-e-3', size='1024x1024'):
    if size == '1024x1024':
        return float(config.get('dall_e_3_costs', '1024x1024')) 
    elif size in ( '1024x1792', '1792x1024' ):
        return float(config.get('dall_e_3_costs', '1792x1024')) 
    else:
        # Use most expensive one for anything else
        return float(config.get('dall_e_3_costs', '1792x1024'))

def cost_of_gpt4v_api_call(file_path, prompt, response_string, gpt_model='gpt-4-vision-preview'):
    """Returns the cost in dollars of an OpenAI API call to gpt4v, defined by a prompt in the form of an image and a string, and a response string"""
    (width, height) = clara_utils.get_image_dimensions(file_path)
    n_image_tokens = ( calculate_image_token_cost(width, height, 'high') / 1000.0 )
    n_prompt_tokens = ( num_gpt4_tokens_for_string(prompt) / 1000.0 )
    n_response_tokens = ( num_gpt4_tokens_for_string(response_string) / 1000.0 )
    
    message_rate = float(config.get('chatgpt4_costs', 'prompt_per_thousand_tokens')) 
    response_rate = float(config.get('chatgpt4_costs', 'response_per_thousand_tokens'))

    image_cost = n_image_tokens * message_rate
    prompt_cost = n_prompt_tokens * message_rate
    response_cost = n_response_tokens * response_rate
    return image_cost + prompt_cost + response_cost


def num_gpt4_tokens_for_messages(messages):
  """Returns the number of tokens used by a list of messages.
Adapted from code at https://platform.openai.com/docs/guides/chat/introduction."""
  encoding = tiktoken.encoding_for_model("gpt-4")
  num_tokens = 0
  for message in messages:
      num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
      for key, value in message.items():
          num_tokens += len(encoding.encode(value))
          if key == "name":  # if there's a name, the role is omitted
              num_tokens += -1  # role is always required and always 1 token
  num_tokens += 2  # every reply is primed with <im_start>assistant
  return num_tokens

def num_gpt4_tokens_for_string(response_string):
  """Returns the number of tokens in a plain string, e.g. a response."""
  encoding = tiktoken.encoding_for_model("gpt-4")
  return len(encoding.encode(response_string))

def calculate_image_token_cost(width, height, detail):
    if detail == 'low':
        return 85
    elif detail == 'high':
        # Scale image to fit within a 2048 x 2048 square, maintaining aspect ratio
        if width > 2048 or height > 2048:
            aspect_ratio = width / height
            if width > height:
                width = 2048
                height = int(width / aspect_ratio)
            else:
                height = 2048
                width = int(height * aspect_ratio)
        
        # Scale such that the shortest side is 768px long
        aspect_ratio = width / height
        if width < height:
            width = 768
            height = int(width / aspect_ratio)
        else:
            height = 768
            width = int(height * aspect_ratio)
        
        # Count how many 512px squares the image consists of
        num_squares = (width // 512) * (height // 512)
        if width % 512 != 0:
            num_squares += height // 512
        if height % 512 != 0:
            num_squares += width // 512
        if width % 512 != 0 and height % 512 != 0:
            num_squares += 1
        
        # Each square costs 170 tokens, plus an additional 85 tokens
        token_cost = num_squares * 170 + 85
        
        return token_cost
    else:
        raise ValueError("Detail must be 'low' or 'high'")
 
