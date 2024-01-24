"""
This module contains a function to estimate the CEFR reading level of a text using ChatGPT4.

The main function is:

1. generate_title(text, l2_language):
   Takes a text and target language, and returns a tuple where the first element
   is a title appropriate to the text,
   and the second element is a list of APICall instances related to the operation.
"""

from . import clara_chatgpt4

def generate_title(text, l2_language, config_info={}, callback=None):
    l2_language = l2_language.capitalize()
    prompt = f"""Read the following {l2_language} text and create an appropriate title in {l2_language}.

Here is the text:

{text}

Just give the revised title and nothing else, in particular no enclosing quotation marks, explanation or comments, since the output will be read by a Python script.
"""
    api_call = clara_chatgpt4.call_chat_gpt4(prompt, config_info=config_info, callback=callback)
    return ( api_call.response, [ api_call ] )

def improve_title(text, old_title, l2_language, config_info={}, callback=None):
    l2_language = l2_language.capitalize()
    prompt = f"""Read the following {l2_language} text and the title.
If possible, try to improve the title.

Here is the text:

{text}

Here is the current title:

{old_title}

Just give the revised title and nothing else, in particular no enclosing quotation marks, explanation or comments, since the output will be read by a Python script.
"""
    api_call = clara_chatgpt4.call_chat_gpt4(prompt, config_info=config_info, callback=callback)
    return ( api_call.response, [ api_call ] )
