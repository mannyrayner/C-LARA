"""
This module contains a function to generate a text in the specified language using ChatGPT4.

The main function is:

1. generate_story(language, prompt=None):
   Takes a language and an optional prompt, and returns a tuple where the first element
   is a generated short news story using Clara ChatGPT4, and the second element is a list
   of APICall instances related to the operation.
   
The default prompt is:
"Write a short, quirky news story in {language.capitalize()} suitable for use in an intermediate language class."

2. improve_story(language, current_version)
   Take the text in 'current_version' and try to fix any errors.

"""

from . import clara_chatgpt4

def generate_story(language, prompt=None, config_info={}, callback=None):
    if not prompt:
        introduction = ''
        prompt = f"Write a short, quirky news story in {language.capitalize()} suitable for use in an intermediate language class."
    else:
        introduction = f"Write a text in {language.capitalize()}, using the following instructions.\n\n"

    clarification = f""" Since the output will be processed by a Python script, write only the {language.capitalize()} text.
Do not include any introduction, translation, explanation or similar."""

    full_prompt = introduction + prompt + clarification
    api_call = clara_chatgpt4.call_chat_gpt4(full_prompt, config_info=config_info, callback=callback)
    return ( api_call.response, [ api_call ] )

def improve_story(language, current_version, improvement_prompt=None, config_info={}, callback=None):
    if not improvement_prompt:
        prompt = f"""Please read through the following {language.capitalize()} text and reproduce it, correcting any mistakes you may find.
Here is the text:

{current_version}

"""
    else:
        prompt = f"""Please read through the following {language.capitalize()} text and try to rewrite it, taking into account the following advice:

{improvement_prompt}

Here is the text:

{current_version}

"""
            
    clarification = f"""Since the output will be processed by a Python script, write only the {language.capitalize()} text.
Do not include any introduction, translation, explanation or similar."""

    full_prompt = prompt + clarification
    api_call = clara_chatgpt4.call_chat_gpt4(full_prompt, config_info=config_info, callback=callback)
    return ( api_call.response, [ api_call ] )

