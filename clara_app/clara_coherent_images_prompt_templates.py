known_prompt_template_types = [ 'generate_style_description',
                                'generate_style_description_example',
                                'style_example_interpretation',
                                'style_example_evaluation',

                                'generate_element_names',
                                'generate_element_description',
                                'element_interpretation',
                                'element_evaluation',
                                
                                'get_relevant_previous_pages',
                                'get_relevant_elements',
                                'generate_page_description',
                                'correct_page_description',
                                'generate_page_description_for_uploaded_image',
                                'generate_description_for_uploaded_element_image',
                                'page_interpretation',
                                'page_evaluation',
                                'element_image_interpretation',

                                'get_elements_shown_in_image',
                                'get_important_pairs_in_image',
                                'get_elements_descriptions_and_style_in_image',
                                'get_relationship_of_element_pair_in_image',
                                ]

def get_prompt_template(prompt_id, prompt_type):
    
    if not prompt_type in known_prompt_template_types:
        raise ValueError(f"Prompt type '{prompt_type}' not found.")

    if prompt_type == 'generate_style_description' and prompt_id in generate_style_description_prompt_templates:
        return generate_style_description_prompt_templates[prompt_id]
    elif prompt_type == 'generate_style_description_example' and prompt_id in generate_style_description_example_prompt_templates:
        return generate_style_description_example_prompt_templates[prompt_id]
    elif prompt_type == 'style_example_interpretation' and prompt_id in style_example_interpretation_prompt_templates:
        return style_example_interpretation_prompt_templates[prompt_id]
    elif prompt_type == 'style_example_evaluation' and prompt_id in style_example_evaluation_prompt_templates:
        return style_example_evaluation_prompt_templates[prompt_id]

    elif prompt_type == 'generate_element_names' and prompt_id in generate_element_names_prompt_templates:
        return generate_element_names_prompt_templates[prompt_id]
    elif prompt_type == 'generate_element_description' and prompt_id in generate_element_description_prompt_templates:
        return generate_element_description_prompt_templates[prompt_id]
    elif prompt_type == 'element_interpretation' and prompt_id in element_interpretation_prompt_templates:
        return element_interpretation_prompt_templates[prompt_id]
    elif prompt_type == 'element_evaluation' and prompt_id in element_evaluation_prompt_templates:
        return element_evaluation_prompt_templates[prompt_id]

    elif prompt_type == 'get_relevant_previous_pages' and prompt_id in get_relevant_previous_pages_prompt_templates:
        return get_relevant_previous_pages_prompt_templates[prompt_id]
    elif prompt_type == 'get_relevant_elements' and prompt_id in get_relevant_elements_prompt_templates:
        return get_relevant_elements_prompt_templates[prompt_id]
    elif prompt_type == 'generate_page_description' and prompt_id in generate_page_description_prompt_templates:
        return generate_page_description_prompt_templates[prompt_id]
    elif prompt_type == 'correct_page_description' and prompt_id in correct_page_description_prompt_templates:
        return correct_page_description_prompt_templates[prompt_id]
    elif prompt_type == 'generate_page_description_for_uploaded_image' and prompt_id in generate_page_description_for_uploaded_image_prompt_templates:
        return generate_page_description_for_uploaded_image_prompt_templates[prompt_id]
    elif prompt_type == 'generate_description_for_uploaded_element_image' and prompt_id in generate_description_for_uploaded_element_image_prompt_templates:
        return generate_description_for_uploaded_element_image_prompt_templates[prompt_id]
    elif prompt_type == 'page_interpretation' and prompt_id in page_interpretation_prompt_templates:
        return page_interpretation_prompt_templates[prompt_id]
    elif prompt_type == 'element_image_interpretation' and prompt_id in element_image_interpretation_prompt_templates:
        return element_image_interpretation_prompt_templates[prompt_id]
    elif prompt_type == 'page_evaluation' and prompt_id in page_evaluation_prompt_templates:
        return page_evaluation_prompt_templates[prompt_id]

    elif prompt_type == 'get_elements_shown_in_image' and prompt_id in get_elements_shown_in_image_prompt_templates:
        return get_elements_shown_in_image_prompt_templates[prompt_id]
    elif prompt_type == 'get_important_pairs_in_image' and prompt_id in get_important_pairs_in_image_prompt_templates:
        return get_important_pairs_in_image_prompt_templates[prompt_id]
    elif prompt_type == 'get_elements_descriptions_and_style_in_image' and prompt_id in get_elements_descriptions_and_style_in_image_prompt_templates:
        return get_elements_descriptions_and_style_in_image_prompt_templates[prompt_id]
    elif prompt_type == 'get_relationship_of_element_pair_in_image' and prompt_id in get_relationship_of_element_pair_in_image_prompt_templates:
        return get_relationship_of_element_pair_in_image_prompt_templates[prompt_id]
    
    else:
        error = f"Prompt template '{prompt_id}' of type '{prompt_type}' not found."
        print(error)
        raise ValueError(error)

# Style

generate_style_description_prompt_templates = {
    'default': """We are later going to create a set of images to illustrate the following text:

{text}

The intended style in which the images will be produced is briefly described as follows:

{base_description}

{background_text}

For now, please expand the brief style description into a detailed specification that can be used as
part of the prompts later passed to DALL-E-3 to create illustrations for this story and enforce
a uniform appearance.

The expanded style specification should at a minimum include information about the medium and technique, the colour palette,
the line work, and the mood/atmosphere, since these are all critical to maintaining coherence of the images
which will use this style.

The specification needs to be at most 1000 characters long"""
    }

generate_style_description_example_prompt_templates = {
    'default': """We are later going to create a set of images to illustrate the following text:

{text}

The style in which the images will be produced is described as follows:

{expanded_style_description}

For now, please expand the style description into a detailed specification that can be passed to DALL-E-3 to
generate a single image, appropriate to the story, which exemplifies the style. The description must be at
most 3000 characters long to conform to DALL-E-3's constraints."""
    }

style_example_interpretation_prompt_templates = {
    'default': """Please provide as detailed a description as possible of the following image, focussing
on the style. The content is not important.

The image has been generated by DALL-E-3 to test whether the instructions used to produce it exemplify the
intended style, and the information you provide will be used to ascertain how good the match is.
"""
    }

style_example_evaluation_prompt_templates = {
    'default': """Please read the 'style description' and the 'image description' below.

The style description specifies an image exemplifying the style that will be used in a larger set of images.

The image description has been produced by gpt-4o, which was asked to describe the style of the image generated from the style description. 

Compare the style description with the image description and evaluate how well the image matches in terms of style.

Style Description:
{expanded_description}

Image Description:
{image_description}

Score the evaluation as a number fron 0 to 4 according to the following conventions:

4 = excellent
3 = good
2 = clearly accesptable
1 = possibly acceptable
0 = unacceptable

The response will be read by a Python script, so write only the single evaluation score."""
    }

# Elements

generate_element_names_prompt_templates = {
    'default': """We are later going to create a set of images to illustrate the following text:

{text}

{background_text}

As part of the process, we need to identify visual elements that occur multiple times in the text,
e.g. characters, objects and locations. In this step, please write out a JSON-formatted list of these
elements. For example, if the text were the traditional nursery rhyme

Humpty Dumpty sat on a wall
Humpty Dumpty had a great fall
All the King's horses and all the King's men
Couldn't put Humpty Dumpty together again

then a plausible list might be

[ "Humpty Dumpty",
  "the wall",
  "the King's horses",
  "the King's men"
]

Please write out only the JSON-formatted list, since it will be read by a Python script."""
    }

generate_element_description_prompt_templates = {
    'default': """We are going to create a set of images to illustrate the following text:

{text}

{background_text}

The intended style in which the images will be produced is described as follows:

{style_description}

As part of this process, we are first creating detailed descriptions of visual elements that occur multiple times in the text,
such as characters, objects, and locations.

**Your task is to create a detailed specification of the element "{element_text}", in the intended style,
to be passed to DALL-E-3 to generate a single image showing how "{element_text}" will be realized.**

**Please ensure that the specification includes specific physical characteristics. For a human character, these would include:**
- **Apparent age**
- **Gender**
- **Ethnicity**
- **Hair color and style**
- **Eye color**
- **Height and build**
- **Clothing and accessories**
- **Distinctive features or expressions**
- **General demeanour**

**Similarly, for an animal we would require characteristics like:**

- **Size and shape**
- **Colour of fur/scales, markings**
- **Eye color**
- **Distinctive features like wings, tail, horns**
- **General demeanour**

** IMPORTANT **

- Be as precise and detailed as possible to ensure consistency in the generated images.**

- The description should be at most 1000 characters long, as it will later be combined with other descriptions.

- Take account of the following advice from the user about how to realise the image:

{advice_text}"""
    }

element_interpretation_prompt_templates= {
    'default': """Please provide as detailed a description as possible of the following image.
The image has been generated by DALL-E-3 to test whether the instructions used to produce it can
reliably be used to create an image in an illustrated text, and the information you provide
will be used to ascertain how good the match is.

**Please ensure that the specification includes specific physical characteristics.
For a human character, these would include:**
- **Apparent age**
- **Gender**
- **Ethnicity**
- **Hair color and style**
- **Eye color**
- **Height and build**
- **Clothing and accessories**
- **Distinctive features or expressions**
- **General demeanour**

**Similarly, for an animal we would require characteristics like:**

- **Size and shape**
- **Colour of fur/scales, markings**
- **Eye color**
- **Distinctive features like wings, tail, horns**
- **General demeanour**

**Be as precise and detailed as possible.**
"""
    }

element_evaluation_prompt_templates = {
    'default': """Please read the 'element description' and the 'image description' below.

The element description specifies an image exemplifying a visual element that will be used multiple times in a larger set of images.

The image description has been produced by GPT-4, which was asked to describe the image generated from the element description.

**Your task is to compare the element description with the image description and evaluate how well they match,
focusing on specific physical characteristics. For a human character, these would include:**
- **Apparent age**
- **Gender**
- **Ethnicity**
- **Hair color and style**
- **Eye color**
- **Height and build**
- **Clothing and accessories**
- **Distinctive features or expressions**

**Similarly, for an animal, relevant characteristics would include:**

- **Size and shape**
- **Colour of fur/scales, markings**
- **Eye color**
- **Distinctive features like wings, tail, horns**
- **General demeanour**

**Identify any discrepancies between the descriptions for each characteristic.**

Score the evaluation as a number from 0 to 4 according to the following conventions:
- **4 = Excellent:** All key characteristics match precisely.
- **3 = Good:** Minor discrepancies that don't significantly affect consistency.
- **2 = Acceptable:** Some discrepancies, but the overall representation is acceptable.
- **1 = Poor:** Significant discrepancies that affect consistency.
- **0 = Unacceptable:** Major mismatches in critical characteristics.

**Provide the evaluation score, followed by a brief summary of any discrepancies identified.**

Element Description:
{expanded_description}

Image Description:
{image_description}

The response will be read by a Python script, so write only the single evaluation score followed by the summary, separated by a newline.

**Example Response:**
3
The hair color differs; the description mentions blonde hair, but the image shows brown hair."""
    }

# Pages

get_relevant_previous_pages_prompt_templates = {
    'default': """We are generating a set of images to illustrate the following text, which has been divided into numbered pages:

{formatted_story_data}

We are preparing to generate an image for page {page_number}, whose text is

{page_text}

We have already generated detailed descriptions for the previous pages. When we generate the image for page {page_number},
it may be helpful to consult some of these descriptions.

In this step, the task is to write out a JSON-formatted list of the previous pages relevant to page {page_number}.

For example, if the text were the traditional nursery rhyme

[ {{ "page_number": 1, "text": "Humpty Dumpty sat on a wall" }},
  {{ "page_number": 2, "text": "Humpty Dumpty had a great fall" }},
  {{ "page_number": 3, "text": "All the King's horses and all the King's men" }},
  {{ "page_number": 4, "text": "Couldn't put Humpty Dumpty together again" }}
  ]

then a plausible list of relevant previous pages for page 2 would be

[ 1 ]

since we want to appearance of Humpty Dumpty and the wall to be similar in the images of pages 1 and 2.

Please write out only the JSON-formatted list, since it will be read by a Python script.
"""
    }

get_relevant_elements_prompt_templates = {
    'default': """We are generating a set of images to illustrate the following text, which has been divided into numbered pages:

{formatted_story_data}

We are preparing to generate an image for page {page_number}, whose text is

{page_text}

We have already generated detailed descriptions for various elements that occur in more than one page. The list of
elements is the following:

{all_element_texts}

When we later generate the image for page {page_number}, it may be helpful to consult some of these descriptions.

In this step, the task is to write out a JSON-formatted list of the elements relevant to page {page_number}e.

For example, if the text were the traditional nursery rhyme

[ {{ "page_number": 1, "text": "Humpty Dumpty sat on a wall" }},
  {{ "page_number": 2, "text": "Humpty Dumpty had a great fall" }},
  {{ "page_number": 3, "text": "All the King's horses and all the King's men" }},
  {{ "page_number": 4, "text": "Couldn't put Humpty Dumpty together again" }}
  ]

and the list of elements was

[ "Humpty Dumpty",
  "the wall",
  "the King's horses",
  "the King's men"
]

[ 

then a plausible list of relevant elements for page 2 would be

[ "Humpty Dumpty", "the wall"]

since the image on page 2 will contain Humpty Dumpty and the wall, but probably not the King's horses or the King's men.

Please write out only the JSON-formatted list, since it will be read by a Python script.
"""
    }

generate_page_description_prompt_templates = {
    'default': """We are generating a set of images to illustrate the following text, which has been divided into numbered pages:

{formatted_story_data}

{background_text}

The intended style in which the images will be produced is described as follows:

{style_description}

We are about to generate the image for page {page_number}, whose text is

{page_text}

We have already generated detailed specifications for the images on the previous pages and also
for various elements (characters, locations, etc) that occur on more than one page.
Here are the specifications of relevant previous pages and elements:

{previous_page_descriptions_text}

{element_descriptions_text}

In this step, please create a detailed specification of the image on page {page_number}, in the intended style
and also consistent with the relevant previous pages and relevant elements, that can be passed to DALL-E-3 to
generate a single image for page {page_number}.

*IMPORTANT*:

- The specification you write out must be at most 2000 characters long to conform with DALL-E-3's constraints.

- Start the specification with a short, self-contained section entitled "Essential aspects", where you briefly summarise the central
idea of the image and then list the aspects of the image which are essential to the text and must be represented.
This will often include material not mentioned in the text on the current page, which is necessary to maintain continuity,
and must be inferred from text on the other pages or from other background knowledge.

For example, if the text were the traditional nursery rhyme

[ {{ "page_number": 1, "text": "Humpty Dumpty sat on a wall" }},
  {{ "page_number": 2, "text": "Humpty Dumpty had a great fall" }},
  {{ "page_number": 3, "text": "All the King's horses and all the King's men" }},
  {{ "page_number": 4, "text": "Couldn't put Humpty Dumpty together again" }}
  ]

then the "Essential aspects" section for page 2 might read:

"Humpy Dumpty is falling off the wall.
Humpty Dumpty is an anthropomorphic egg. He looks surprised and frightened."

despite the fact that there is no mention of the wall in the page 2 text, and no mention anywhere that Humpty Dumpty is an anthropomorphic egg.

The "Essential aspects" section will be used to check the correctness of the generated image.
If any item listed there fails to match, the image will be rejected, so only include material
in this section which is genuinely essential, as opposed to just desirable.

- Take account of the following advice from the user about how to realise the image:

{advice_text}
"""
    }

correct_page_description_prompt_templates = {
    'default': """We are using DALL-E-3 to generate a set of images to illustrate the following text, which has been divided into numbered pages:

{formatted_story_data}

We tried to generate an image for page {page_number}, whose text is

{page_text}

but when the prompt was passed to DALL-E-3 it produced a content policy violation.
It may well be the case that the prompt is essentially innocuous (it was produced by an OpenAI model),
but the content policy filter is oversensitive.

Your task is to rewrite the prompt in a way that will not trigger the content policy filter,
while making as few changes as possible.

The current text of the prompt is:

{expanded_description}

*IMPORTANT*:

- The prompt you write out must be at most 2000 characters long to conform with DALL-E-3's constraints.

- The prompt must start with a short, self-contained section entitled "Essential aspects", where you briefly summarise the central
idea of the image and then list the aspects of the image which are essential to the text and must be represented.
"""
    }

generate_page_description_for_uploaded_image_prompt_templates = {
    'default': """We are generating a set of images to illustrate the following text, which has been divided into numbered pages:

{formatted_story_data}

The intended style in which the images will be produced is described as follows:

{style_description}

We are about to generate the image for page {page_number}, whose text is

{page_text}

We have already generated detailed specifications for various elements (characters, locations, etc) that occur on more than one page.
Here are the specifications of relevant elements:

{element_descriptions_text}

The user has uploaded an image which they wish to use as inspiration for this one, suitably adapting it by taking
account of the style description and the descriptions of the recurring elements, if there are any. Here is a description
of the uploaded image produced by gpt-4o:

{image_interpretation}

In this step, please create a detailed specification of the image on page {page_number}, based on the user
uploaded image, in the intended style, and consistent with the descriptions of any relevant elements, that can be passed to DALL-E-3 to
generate a single image for page {page_number}.

*IMPORTANT*:

The specification you write out must be at most 2000 characters long to conform with DALL-E-3's constraints.

""",

    'just_style': """We are generating a set of images to illustrate a text.

The intended style in which the images will be produced is described as follows:

{style_description}

We are about to generate the image for a page whose text is

{page_text}

The user has uploaded an image which they wish to use as inspiration for this one, suitably adapting it by taking
account of the style description. Here is a description of the uploaded image produced by gpt-4o:

{image_interpretation}

In this step, please create a detailed specification of the image on this page, based on the user
uploaded image, in the intended style, and consistent with the text, that can be passed to DALL-E-3 to
generate a single image for the page.

*IMPORTANT*:

The specification you write out must be at most 2000 characters long to conform with DALL-E-3's constraints.

"""
    }

generate_description_for_uploaded_element_image_prompt_templates = {
    'default': """We are generating a set of images to illustrate the following text, which has been divided into numbered pages:

{formatted_story_data}

The intended style in which the images will be produced is described as follows:

{style_description}

As part of this process, we are creating detailed specifications for various elements (characters, locations, etc) that occur on more than one page.

The user has uploaded an image which they wish to use as inspiration for the element "{element_text}", suitably adapting it by taking
account of the style description. Here is a description of the uploaded image produced by gpt-4o:

{image_interpretation}

In this step, please create a detailed specification of the image for the element "{element_text}", based on the user
uploaded image, and in the intended style. This will later be used in prompts submitted to DALL-E-3.

*IMPORTANT*:

The specification you write out must be at most 2000 characters long to conform with DALL-E-3's constraints.

"""
    }

element_image_interpretation_prompt_templates = {
   'interpret_uploaded_element_image': """Please provide a description of this image.
The image has been uploaded by the user to provide information that will later help DALL-E-3
create images to illustrate the following text:

{formatted_story_data}

The image is meant to depict the element "{element_text}".

In this step, your task is to create a text description of the image, interpreting it as meaning "{element_text}" from the text.
The description you provide will later be combined with other information to create prompts for DALL-E-3.

**Please ensure that the description includes specific physical characteristics.
For a human character, these would include:**
- **Apparent age**
- **Gender**
- **Ethnicity**
- **Hair color and style**
- **Eye color**
- **Height and build**
- **Clothing and accessories**
- **Distinctive features or expressions**
- **General demeanour**

**Similarly, for an animal we would require characteristics like:**

- **Size and shape**
- **Colour of fur/scales, markings**
- **Eye color**
- **Distinctive features like wings, tail, horns**
- **General demeanour**

**Be as precise and detailed as possible.**
"""
   }

page_interpretation_prompt_templates = {
    'default': """Please provide a description of this image.
The image has been generated by DALL-E-3 as an illustration for page in a text, and the information you provide
will be used to ascertain how good the match is with the material on that page.

**Please ensure that the specification includes specific physical characteristics.
For a human character, these would include:**
- **Apparent age**
- **Gender**
- **Ethnicity**
- **Hair color and style**
- **Eye color**
- **Height and build**
- **Clothing and accessories**
- **Distinctive features or expressions**
- **General demeanour**

**Similarly, for an animal we would require characteristics like:**

- **Size and shape**
- **Colour of fur/scales, markings**
- **Eye color**
- **Distinctive features like wings, tail, horns**
- **General demeanour**

**Be as precise and detailed as possible.**
""",

    'with_context': """Please provide a description of this image.
The image has been generated by DALL-E-3 as an illustration for the following text,
which has been divided into numbered pages:

{formatted_story_data}

The image is meant to be for page {page_number}, which reads as follows

{page_text}

We wish to ascertain how good the match is with the intructions passed to DALL-E-3 to produce the image.
These will have contained more detail than just the text on the page.

**Please ensure that the specification includes specific physical characteristics.
For a human character, these would include:**
- **Apparent age**
- **Gender**
- **Ethnicity**
- **Hair color and style**
- **Eye color**
- **Height and build**
- **Clothing and accessories**
- **Distinctive features or expressions**
- **General demeanour**

**Similarly, for an animal we would require characteristics like:**

- **Size and shape**
- **Colour of fur/scales, markings**
- **Eye color**
- **Distinctive features like wings, tail, horns**
- **General demeanour**

**IMPORTANT**

1. Remember that DALL-E-3 often fails to follow instructions, so the image may not represent the text well.

2. Be as precise and detailed as possible when producing your description of the image.
""",

    'with_context_v2': """Please provide a description of this image.
The image has been generated by DALL-E-3 as an illustration for the following text,
which has been divided into numbered pages:

{formatted_story_data}

The image is meant to be for page {page_number}, which reads as follows

{page_text}

We wish to ascertain how good the match is with the intructions passed to DALL-E-3 to produce the image.
These will have contained more detail than just the text on the page.

Your task is to create a description according to the following guidelines:

1. Provide a summary description of the image as a whole, focussing on the content.

2. Describe the style of the image. 

3. Describe specific physical characteristics of the individual elements.
For a human character, these would include:
- **Apparent age**
- **Gender**
- **Ethnicity**
- **Hair color and style**
- **Eye color**
- **Height and build**
- **Clothing and accessories**
- **Distinctive features or expressions**
- **General demeanour**

Similarly, for an animal we would require characteristics like:

- **Size and shape**
- **Colour of fur/scales, markings**
- **Eye color**
- **Distinctive features like wings, tail, horns**
- **General demeanour**

**IMPORTANT**

A. Remember that DALL-E-3 often fails to follow instructions, so the image may not represent the text well.

B. Be as precise and detailed as possible when producing your description of the image.
""",

    'with_context_v3_objective': """Please provide a description of this image.
The image has been generated by DALL-E-3 as an illustration for the following text,
which has been divided into numbered pages:

{formatted_story_data}

The image is meant to be for page {page_number}, which reads as follows

{page_text}

We wish to ascertain how good the match is with the intructions passed to DALL-E-3 to produce the image.
These will have contained more detail than just the text on the page.

Your task is to create a description according to the following guidelines:

1. Provide a summary description of the image as a whole, focussing on the content.

2. Describe the style of the image. 

3. Describe specific physical characteristics of the individual elements.
For a human character, these would include:
- **Apparent age**
- **Gender**
- **Ethnicity**
- **Hair color and style**
- **Eye color**
- **Height and build**
- **Clothing and accessories**
- **Distinctive features or expressions**
- **General demeanour**

Similarly, for an animal we would require characteristics like:

- **Size and shape**
- **Colour of fur/scales, markings**
- **Eye color**
- **Distinctive features like wings, tail, horns**
- **General demeanour**

**IMPORTANT**

Remember that DALL-E-3 often fails to follow instructions, so the image may not represent the text well.
Consequently, try to describe what you can actually see in the image, as opposed to what you expect to see based on the text.
It may be helpful to focus in turn on pairs of individual elements, describing the precise relationship between them.
""",

    'interpret_uploaded_image': """Please provide a description of this image.
The image has been provided by a user as an illustration for the following text,
which has been divided into numbered pages:

{formatted_story_data}

The image is meant to be for page {page_number}, which reads as follows

{page_text}

We will later combine the description you provide with style information and pass it to
DALL-E-3 to create a new image in a specified style, so make your description as detailed
as possible in terms of content, but not style.
""",
        }

page_evaluation_prompt_templates = {
    'default': """Please read the 'image specification' and the 'image description' below.

The image specification gives the instructions passed to DALL-E-3 to create one of the images illustrating a text.

The image description has been produced by gpt-4o, which was asked to describe the image generated from the image specification. 

Your task is to compare the image specification with the image description and evaluate how well they match.
Compare both the overall image and elements such as people, animals and important objects,
focusing on specific physical characteristics. For a human character, these would include:
- **Apparent age**
- **Gender**
- **Ethnicity**
- **Hair color and style**
- **Eye color**
- **Height and build**
- **Clothing and accessories**
- **Distinctive features or expressions**

Similarly, for an animal, relevant characteristics would include:

- **Size and shape**
- **Colour of fur/scales, markings**
- **Eye color**
- **Distinctive features like wings, tail, horns**
- **General demeanour**

**Identify any discrepancies between the descriptions for each characteristic.**

Score the evaluation as a number from 0 to 4 according to the following conventions:
- **4 = Excellent:** All key characteristics match precisely.
- **3 = Good:** Minor discrepancies that don't significantly affect consistency.
- **2 = Acceptable:** Some discrepancies, but the overall representation is acceptable.
- **1 = Poor:** Significant discrepancies that affect consistency.
- **0 = Unacceptable:** Major mismatches in critical characteristics.

**Provide the evaluation score, followed by a brief summary of any discrepancies identified.**

+Image specification:
{expanded_description}

Image Description:
{image_description}

**IMPORTANT**

A. Look in particular at the section in the specification entitled "Essential aspects".
If any item mentioned in the "Essential aspects" section fails to match the description, then
the match must be scored as 1 ("Poor") or 0 ("Unacceptable").

B. The response will be read by a Python script, so write only the single evaluation score followed by the summary, separated by a newline.

**Example Response:**
3
The hair color of the girl is different; the specification mentions blonde hair, but the image shows brown hair.
""",

    'with_context_lenient': """Please read the 'image specification' and the 'image description' below.

The image specification reproduces the instructions passed to DALL-E-3 to create one of the images illustrating the following text,
which has been divided into numbered pages:

{formatted_story_data}

The image is meant to be for page {page_number}, which reads as follows

{page_text}

Note that the image specification contains more information than is present in the original text. Details have been added to make the
different images consistent with each other, e.g. to depict characters or locations in the same way.

The image description has been produced by gpt-4o, which was asked to describe the image generated from the image specification. 

Your task is to compare the image specification with the image description in the overall context of the text, and evaluate how well they match.

Score the evaluation as a number from 0 to 4 according to the following conventions:
- **4 = Excellent:** All key characteristics match precisely.
- **3 = Good:** Minor discrepancies.
- **2 = Acceptable:** Some discrepancies, but the overall representation is acceptable.
- **1 = Poor:** Significant discrepancies.
- **0 = Unacceptable:** Major mismatches in critical characteristics.

**Provide the evaluation score, followed by a brief summary of any discrepancies identified.**

Image specification:
{expanded_description}

Image Description:
{image_description}

**Example Response:**
3
The hair color of the girl is different; the specification mentions blonde hair, but the image shows brown hair.
""",
    }

# text=text, elements=elements
get_elements_shown_in_image_prompt_templates = {
    'default': """Please look at this image, which has been generated by DALL-E-3 as one of the illustration for the following text:

{text}

Some of the following elements may be present in the image {elements}

Your task is to write out a JSON-formatted list containing only the elements present. It must be a subset of the list given.

Write out only the JSON-formatted list, since it will be read by a Python script.
"""}

# test=text, expanded_description=expanded_description, elements_in_image=elements_in_image
get_important_pairs_in_image_prompt_templates = {
    'default': """We are later going to evaluate the correctness of an image that has been created by DALL-E-3 as one of the illustrations for this text:

{text}

The image was created by this prompt:

{expanded_description}

It should contain representations of these elements:

{elements_in_image}

To determine the correctness of the image, we want to examine the relationships between some pairs of these elements. Your task is to write out
a JSON-formatted list of the important pairs.

For example, if the text were the classic children's rhyme

Humpty Dumpy sat on a wall
Humpty Dumpty had a great fall
All the King's horse and all the King's men
Couldn't put Humpty Dumpty together again

and the image had been created by the prompt

Humpy Dumpty, an anthropomorphic egg wearing a smart suit, has just fallen off the wall he was sitting on.
He looks surprised and frightened and is holding out his hands.

and the list of elements in the image is ["Humpty Dumpty", "the wall", "Humpty Dumpty's hands"]

a plausible list of important pairs would be

[["Humpty Dumpty", "the wall"]]

Write out only the JSON-formatted list, since it will be read by a Python script.

"""}

# text=text, elements_in_image=elements_in_image
get_elements_descriptions_and_style_in_image_prompt_templates = {
    'default': """We are evaluating the correctness of this image, which has been created by DALL-E-3 as one of the illustrations for the following text:

{text}

It should contain representations of these elements:

{elements_in_image}

In this step, your task is to write out a detailed description of each element, and also of the overall style of the image.

**IMPORTANT**

Remember that DALL-E-3 often fails to follow instructions, so the image may not represent the text well.
Consequently, try to describe what you can actually see in the image, as opposed to what you expect to see based on the text.
"""}

# text=text, element1=element1, element2=element2
get_relationship_of_element_pair_in_image_prompt_templates = {
    'default': """We are evaluating the correctness of this image, which has been created by DALL-E-3 as one of the illustrations for the following text:

{text}

It should contain representations of {element1} and {element2}.

In this step, your task is to write out a detailed description of the relationship between {element1} and {element2} shown in the image.

To the extent possible, describe only the relationship between {element1} and {element2}.

**IMPORTANT**

Remember that DALL-E-3 often fails to follow instructions, so the image may not represent the text well.
Consequently, try to describe what you can actually see in the image, as opposed to what you expect to see based on the text.
"""}

