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

Here is the official definition of each level:

A1: Can understand and use familiar everyday expressions and very basic phrases
aimed at the satisfaction of needs of a concrete type.
Can introduce themselves to others and can ask and answer questions about
personal details such as where they live, people they know and things they have.
Can interact in a simple way provided the other person talks slowly and clearly
and is prepared to help.

A2: Can understand sentences and frequently used expressions related to areas of most immediate relevance
(e.g. very basic personal and family information, shopping, local geography, employment).
Can communicate in simple and routine tasks requiring a simple and direct exchange of information
on familiar and routine matters.
Can describe in simple terms aspects of their background, immediate environment
and matters in areas of immediate need.

B1: Can understand the main points of clear standard input on familiar matters
regularly encountered in work, school, leisure, etc.
Can deal with most situations likely to arise while travelling in an area where the language is spoken.
Can produce simple connected text on topics that are familiar or of personal interest.
Can describe experiences and events, dreams, hopes and ambitions and briefly give
reasons and explanations for opinions and plans.

B2: Can understand the main ideas of complex text on both concrete and abstract topics,
including technical discussions in their field of specialisation.
Can interact with a degree of fluency and spontaneity that makes regular interaction with native speakers
quite possible without strain for either party.
Can produce clear, detailed text on a wide range of subjects and explain a viewpoint on a topical issue
giving the advantages and disadvantages of various options.

C1: Can understand a wide range of demanding, longer clauses and recognise implicit meaning.
Can express ideas fluently and spontaneously without much obvious searching for expressions.
Can use language flexibly and effectively for social, academic and professional purposes.
Can produce clear, well-structured, detailed text on complex subjects, showing controlled use
of organisational patterns, connectors and cohesive devices.

C2: Can understand with ease virtually everything heard or read.
Can summarise information from different spoken and written sources, reconstructing arguments and
accounts in a coherent presentation.
Can express themselves spontaneously, very fluently and precisely, differentiating finer shades of meaning
even in the most complex situations.

Here is the text to annotate:
{text}

Just give the CEFR level and nothing else, since the output will be read by a Python script.
"""
    api_call = clara_chatgpt4.call_chat_gpt4(prompt, config_info=config_info, callback=callback)
    return ( api_call.response, [ api_call ] )
