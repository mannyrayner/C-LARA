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
                                'page_interpretation',
                                'page_evaluation'
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
    elif prompt_type == 'page_interpretation' and prompt_id in page_interpretation_prompt_templates:
        return page_interpretation_prompt_templates[prompt_id]
    elif prompt_type == 'page_evaluation' and prompt_id in page_evaluation_prompt_templates:
        return page_evaluation_prompt_templates[prompt_id]
    else:
        raise ValueError(f"Prompt template '{prompt_id}' of type '{prompt_type}' not found.")

# Style

generate_style_description_prompt_templates = {
    'default': """We are later going to create a set of images to illustrate the following text:

{text}

The intended style in which the images will be produced is briefly described as follows:

{base_description}

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

**Be as precise and detailed as possible to ensure consistency in the generated images.**

The description should be at most 1000 characters long, as it will later be combined with other descriptions."""
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

A. The specification you write out must be at most 2000 characters long to conform with DALL-E-3's constraints.

B. Start the specification with a short, self-contained section entitled "Essential aspects", where you briefly summarise the central
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
"""
    }

page_interpretation_prompt_templates = {
    'default': """Please provide a description of this image.
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
    }

