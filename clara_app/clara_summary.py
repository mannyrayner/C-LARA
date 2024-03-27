"""
This module contains a function to estimate the CEFR reading level of a text using ChatGPT4.

The main function is:

1. generate_summary(text, l2_language):
   Takes a text and target language, and returns a tuple where the first element
   is a short summary of the text,
   and the second element is a list of APICall instances related to the operation.
"""

from . import clara_chatgpt4

def generate_summary(text, l2_language, config_info={}, callback=None):
    l2_language = l2_language.capitalize()
    prompt = f"""Read the following {l2_language} text and create a short summary in English of 1-2 sentences in length.

Here is the text:

{text}

Just give the summary and nothing else, since the output will be read by a Python script.
"""
    api_call = clara_chatgpt4.call_chat_gpt4(prompt, config_info=config_info, callback=callback)
    return ( api_call.response, [ api_call ] )

def improve_summary(text, old_summary, l2_language, config_info={}, callback=None):
    l2_language = l2_language.capitalize()
    prompt = f"""Read the following {l2_language} text and the short English summary, which should be 1-2 sentences in length.
If possible, try to improve the summary.

Here is the summary to annotate:

{text}

Here is the summary:

{old_summary}

Just give the revised summary and nothing else, since the output will be read by a Python script.
"""
    api_call = clara_chatgpt4.call_chat_gpt4(prompt, config_info=config_info, callback=callback)
    return ( api_call.response, [ api_call ] )
