"""
This module contains a function to estimate the CEFR reading level of a text using ChatGPT4.

The main function is:

1. estimate_reading_level(text, l2_language):
   Takes a text and target language, and returns a tuple where the first element
   is an estimate of the reading level as one of {A1, A2, B1, B2, C1, C2},
   and the second element is a list of APICall instances related to the operation.
"""

from . import clara_chatgpt4

def estimate_cefr_reading_level(text, l2_language, config_info={}, callback=None):
    l2_language = l2_language.capitalize()
    prompt = f"""Read the following {l2_language} text and estimate its reading level.
Use the standard CEFR levels: A1, A2, B1, B2, C1, C2.

Here is the text to annotate:
{text}

Just give the CEFR level and nothing else, since the output will be read by a Python script.
"""
    api_call = clara_chatgpt4.call_chat_gpt4(prompt, config_info=config_info, callback=callback)
    return ( api_call.response, [ api_call ] )
