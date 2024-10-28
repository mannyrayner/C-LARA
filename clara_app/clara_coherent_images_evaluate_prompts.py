from .clara_coherent_images_prompt_templates import (
    get_prompt_template,
    )

from .clara_chatgpt4 import (
    interpret_chat_gpt4_response_as_json,
    )

from .clara_coherent_images_utils import (
    score_for_image_dir,
    score_for_evaluation_file,
    parse_image_evaluation_response,
    get_story_data,
    get_pages,
    get_text,
    get_style_description,
    get_all_element_texts,
    get_element_description,
    get_page_text,
    get_page_description,
    get_page_image,
    get_api_chatgpt4_response_for_task,
    get_api_chatgpt4_image_response_for_task,
    get_api_chatgpt4_interpret_image_response_for_task,
    get_config_info_and_callback_from_params,
    api_calls_to_cost,
    combine_cost_dicts,
    print_cost_dict,
    write_project_cost_file,
    project_pathname,
    make_project_dir,
    read_project_txt_file,
    read_project_json_file,
    write_project_txt_file,
    write_project_json_file,
    ImageGenerationError
    )

from .clara_utils import (
    read_txt_file,
    write_txt_file,
    read_json_file,
    write_json_to_file,
    make_directory,
    absolute_file_name,
    file_exists,
    directory_exists,
    copy_file,
    get_immediate_subdirectories_in_local_directory,
    )

import json
import os
import sys
import asyncio
import traceback
import unicodedata
from PIL import Image

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import mean_absolute_error, cohen_kappa_score, confusion_matrix

from jinja2 import Environment, FileSystemLoader

def human_evaluation(params):
    project_dir = params['project_dir']
    project_dir = absolute_file_name(project_dir)

    # Read the story data
    story_data = get_story_data(params)

    # Path to the evaluations file
    evaluations_path = project_pathname(project_dir, f'human_evaluations.json')

    # Initialize a list to store evaluations
    evaluations = []

    # If the evaluations file exists, read it and build a set of already evaluated images
    evaluated_images = set()
    if file_exists(evaluations_path):
        try:
            evaluations = read_json_file(evaluations_path)
            # Build a set of tuples to identify already evaluated images
            for eval in evaluations:
                key = (eval['page_number'], eval['description_version'], eval['image_version'])
                evaluated_images.add(key)
            print(f"Resuming from existing evaluations file. {len(evaluations)} evaluations loaded.")
        except Exception as e:
            print(f"Error reading evaluations file: {e}")
            return

    # Iterate over each page in the story
    for page in story_data:
        page_number = page['page_number']
        page_text = page['text']

        print(f"\nPage {page_number}:")
        print(f"Text:\n{page_text}\n")

        # Path to the page directory
        page_dir = project_pathname(project_dir, f'pages/page{page_number}')

        # Check if the page directory exists
        if not directory_exists(page_dir):
            print(f"Directory not found for page {page_number}. Skipping this page.")
            continue

        # Collect all image paths under description_v*/image_v*/image.jpg
        image_infos = []
        for description_dir_name in get_immediate_subdirectories_in_local_directory(page_dir):
            description_dir_path = project_pathname(page_dir, description_dir_name)
            if directory_exists(description_dir_path) and description_dir_name.startswith('description_v'):
                for image_dir_name in get_immediate_subdirectories_in_local_directory(description_dir_path):
                    image_dir_path = project_pathname(description_dir_path, image_dir_name)
                    if directory_exists(image_dir_path) and image_dir_name.startswith('image_v'):
                        image_file_path = os.path.join(image_dir_path, 'image.jpg')
                        if file_exists(image_file_path):
                            image_info = {
                                'page_number': page_number,
                                'description_version': description_dir_name,
                                'image_version': image_dir_name,
                                'image_path': image_file_path,
                                'text': page_text
                            }
                            image_infos.append(image_info)

        # If no images found, skip this page
        if not image_infos:
            print(f"No images found for page {page_number}. Skipping this page.")
            continue

        # Iterate over all collected images for this page
        for idx, image_info in enumerate(image_infos):
            key = (image_info['page_number'], image_info['description_version'], image_info['image_version'])

            # Skip if already evaluated
            if key in evaluated_images:
                print(f"Skipping already evaluated image: Page {image_info['page_number']}, "
                      f"{image_info['description_version']}, {image_info['image_version']}")
                continue

            print(f"\nEvaluating image {idx + 1} of {len(image_infos)} for page {page_number}:")
            print(f"Description version: {image_info['description_version']}, Image version: {image_info['image_version']}")

            # Open and display the image using PIL
            try:
                image = Image.open(image_info['image_path'])
                image.show()
            except Exception as e:
                print(f"Error opening image for page {page_number}: {e}")
                continue

            # Prompt the user for a score between 0 and 4, or 'p' to pause
            while True:
                score_input = input("Please rate how well the image matches the text (0-4), or 'p' to pause: ")
                if score_input.lower() == 'p':
                    # Write evaluations to file and exit
                    try:
                        write_json_to_file(evaluations, evaluations_path)
                        print(f"\nEvaluations saved to {evaluations_path}")
                    except Exception as e:
                        print(f"Error writing evaluations to file: {e}")
                    print("Evaluation paused by user.")
                    return
                try:
                    score = int(score_input)
                    if 0 <= score <= 4:
                        break
                    else:
                        print("Score must be an integer between 0 and 4.")
                except ValueError:
                    print("Invalid input. Please enter an integer between 0 and 4, or 'p' to pause.")

            # Optionally, collect comments
            comments = input("Optional: Enter any comments about this image (or press Enter to skip): ")

            # Store the evaluation data
            evaluation = {
                'page_number': image_info['page_number'],
                'description_version': image_info['description_version'],
                'image_version': image_info['image_version'],
                'score': score,
                'comments': comments,
                'text': image_info['text'],
                'image_path': image_info['image_path']
            }
            evaluations.append(evaluation)
            evaluated_images.add(key)

            # Close the image display
            image.close()

    # All evaluations completed, write to file
    try:
        write_json_to_file(evaluations, evaluations_path)
        print(f"\nAll evaluations completed and saved to {evaluations_path}")
    except Exception as e:
        print(f"Error writing evaluations to file: {e}")

# -----------------------------------------------

async def test_prompts_for_interpretation_and_evaluation(params):
    project_dir = params['project_dir']
    project_dir = absolute_file_name(project_dir)
    
    interpretation_prompt_id = params['interpretation_prompt_id']
    evaluation_prompt_id = params['evaluation_prompt_id']
    
    # Read human evaluations
    evaluations_path = project_pathname(project_dir, 'human_evaluations.json')
    if not file_exists(evaluations_path):
        print(f"Human evaluations file not found at {evaluations_path}")
        return

    evaluations = read_json_file(evaluations_path)

    if 'n_images' in params and params['n_images'] != 'all':
        evaluations = evaluations[:params['n_images']]
    
    # Prepare tasks for asyncio
    tasks = []
    for evaluation in evaluations:
        tasks.append(interpret_and_evaluate_single_image(evaluation, params))
    
    # Run tasks in parallel
    results = await asyncio.gather(*tasks)
    
    # Collect results and save
    augmented_evaluations = [result for result in results if result is not None]
    augmented_evaluations_path = project_pathname(project_dir, f'automated_evaluations_{interpretation_prompt_id}_{evaluation_prompt_id}.json')
    write_json_to_file(augmented_evaluations, augmented_evaluations_path)
    print(f"Automated evaluations saved to {augmented_evaluations_path}")

    total_cost_dict = {}
    for result in augmented_evaluations:
        if 'cost_info' in result:
            total_cost_dict = combine_cost_dicts(total_cost_dict, result['cost_info'])
    return total_cost_dict
                                                                         
async def interpret_and_evaluate_single_image(evaluation, params):
    project_dir = params['project_dir']
    
    page_number = evaluation['page_number']
    description_version = evaluation['description_version']
    image_version = evaluation['image_version']
    image_path = evaluation['image_path']
    text = evaluation['text']
    
    # Retrieve the expanded description
    expanded_description_path = project_pathname(
        project_dir,
        f'pages/page{page_number}/{description_version}/expanded_description.txt'
    )
    if not file_exists(expanded_description_path):
        print(f"Expanded description not found for page {page_number}, {description_version}")
        return None

    expanded_description = read_txt_file(expanded_description_path)

    # Interpret the image
    try:
        image_interpretation, interpret_cost = await interpret_image_with_prompt(
            image_path,
            expanded_description,
            page_number,
            params['interpretation_prompt_id'],
            params
        )
    except Exception as e:
        print(f'Error interpreting image {image_path}: "{str(e)}"\n{traceback.format_exc()}"')
        return None

    # Evaluate the fit
    if image_interpretation:
        try:
            fit_evaluation, evaluate_cost = await evaluate_fit_with_prompt(
                expanded_description,
                image_interpretation,
                params['evaluation_prompt_id'],
                page_number,
                params
            )
        except Exception as e:
            print(f'Error evaluating fit for image {image_path}: "{str(e)}"\n{traceback.format_exc()}"')
            return None

        fit_score, fit_comments = parse_image_evaluation_response(fit_evaluation)
    else:
        fit_score, fit_comments, evaluate_cost = ( None, '', {} )

    # Combine cost information
    total_cost = combine_cost_dicts(interpret_cost, evaluate_cost)

    # Augment the evaluation data
    augmented_evaluation = evaluation.copy()
    augmented_evaluation.update({
        'expanded_description': expanded_description,
        'image_interpretation': image_interpretation,
        'fit_score': fit_score,
        'fit_comments': fit_comments,
        'interpretation_prompt_id': params['interpretation_prompt_id'],
        'evaluation_prompt_id': params['evaluation_prompt_id'],
        'cost_info': total_cost
    })

    return augmented_evaluation

async def interpret_image_with_prompt(image_path, expanded_description, page_number, prompt_id, params):
    if prompt_id == 'multiple_questions':
        return await interpret_image_with_prompt_multiple_questions(image_path, expanded_description, page_number, params)
    
    # Retrieve the prompt template based on prompt_id
    prompt_template = get_prompt_template(prompt_id, 'page_interpretation')

    story_data = get_story_data(params)
    formatted_story_data = json.dumps(story_data, indent=4)
    
    page_text = get_page_text(page_number, params)

    prompt = prompt_template.format(formatted_story_data=formatted_story_data, page_number=page_number, page_text=page_text)

    # Perform the API call
    tries_left = params['n_retries'] if 'n_retries' in params else 5
    total_cost = 0

    while tries_left:
        try:
            api_call = await get_api_chatgpt4_interpret_image_response_for_task(
                prompt,
                image_path,
                'evaluate_page_image',
                params
            )
            image_interpretation = api_call.response
            total_cost += api_call.cost
            return image_interpretation, {'interpret_image': total_cost}
        
        except Exception as e:
            tries_left -= 1

    # We failed
    return None, {'interpret_image': total_cost}

async def interpret_image_with_prompt_multiple_questions(image_path, expanded_description, page_number, params):
    total_cost = 0

    try:
        # Find the elements in the image
        elements_in_image, get_elements_cost = await get_elements_shown_in_image(image_path, params)
        total_cost += get_elements_cost
        if not elements_in_image:
            return None, {'interpret_image': total_cost}

        # Get descriptions of the relevant elements and the style
        element_and_style_descriptions, descriptions_cost = await get_elements_descriptions_and_style_in_image(image_path, elements_in_image, params)
        total_cost += descriptions_cost
        if not element_and_style_descriptions:
            return None, {'interpret_image': total_cost}

        # Find the important pairs
        important_pairs, pairs_cost = await get_important_pairs_in_image(elements_in_image, expanded_description, params)
        total_cost += pairs_cost
        if not important_pairs:
            return None, {'interpret_image': total_cost}

        # Get descriptions of the relationships obtaining for the important pairs
        tasks = []
        for pair in important_pairs:
            tasks.append(get_relationship_of_element_pair_in_image(pair, image_path, params))
        results = await asyncio.gather(*tasks)
        pair_descriptions = [ result[0] for result in results ]
        pair_description_costs = sum([ result[1] for result in results ])
        total_cost += pair_description_costs

        # Put everything together
        full_description = combine_results_of_multiple_questions(elements_in_image, element_and_style_descriptions, pair_descriptions)
        return full_description, {'interpret_image': total_cost}

    except Exception as e:
        error_message = f'"{str(e)}"\n{traceback.format_exc()}'
        print(error_message)
        return None, {'interpret_image': total_cost}
        
async def get_elements_shown_in_image(image_path, params):
    # Retrieve the prompt template based on prompt_id
    prompt_template = get_prompt_template('default', 'get_elements_shown_in_image')

    text = get_text(params)

    elements = get_all_element_texts(params)

    prompt = prompt_template.format(text=text, elements=elements)

    # Perform the API call
    tries_left = params['n_retries'] if 'n_retries' in params else 5
    total_cost = 0

    while tries_left:
        try:
            api_call = await get_api_chatgpt4_interpret_image_response_for_task(
                prompt,
                image_path,
                'evaluate_page_image',
                params
            )
            image_interpretation = api_call.response
            total_cost += api_call.cost
            elements_present = interpret_chat_gpt4_response_as_json(image_interpretation, object_type='list')

            if all([ element in elements for element in elements_present ]):
                return elements_present, total_cost
            else:
                tries_left -= 1
        
        except Exception as e:
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            print(error_message)
            tries_left -= 1

    # We failed
    return None, total_cost

async def get_important_pairs_in_image(elements_in_image, expanded_description, params):
    prompt_template = get_prompt_template('default', 'get_important_pairs_in_image')

    text = get_text(params)

    prompt = prompt_template.format(text=text, 
                                    expanded_description=expanded_description,
                                    elements_in_image=elements_in_image)

    # Perform the API call
    tries_left = params['n_retries'] if 'n_retries' in params else 5
    total_cost = 0

    while tries_left:
        try:
            api_call = await get_api_chatgpt4_response_for_task(
                prompt,
                'evaluate_page_image',
                params
            )
            important_pairs_text = api_call.response
            total_cost += api_call.cost
            important_pairs = interpret_chat_gpt4_response_as_json(important_pairs_text, object_type='list')
            if all([ element1 in elements_in_image and element1 in elements_in_image for (element1, element2) in important_pairs ]):
                return important_pairs, total_cost
            else:
                tries_left -= 1
        
        except Exception as e:
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            print(error_message)    
            tries_left -= 1

    # We failed
    return None, total_cost

async def get_elements_descriptions_and_style_in_image(image_path, elements_in_image, params):
    prompt_template = get_prompt_template('default', 'get_elements_descriptions_and_style_in_image')

    text = get_text(params)

    prompt = prompt_template.format(text=text, elements_in_image=elements_in_image)

    # Perform the API call
    tries_left = params['n_retries'] if 'n_retries' in params else 5
    total_cost = 0

    while tries_left:
        try:
            api_call = await get_api_chatgpt4_interpret_image_response_for_task(
                prompt,
                image_path,
                'evaluate_page_image',
                params
            )
            image_interpretation = api_call.response
            total_cost += api_call.cost
            return image_interpretation, total_cost
        
        except Exception as e:
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            print(error_message)
            tries_left -= 1

    # We failed
    return None, total_cost

async def get_relationship_of_element_pair_in_image(pair, image_path, params):
    prompt_template = get_prompt_template('default', 'get_relationship_of_element_pair_in_image')

    element1, element2 = pair

    text = get_text(params)
    
    prompt = prompt_template.format(text=text, element1=element1, element2=element2)

    # Perform the API call
    tries_left = params['n_retries'] if 'n_retries' in params else 5
    total_cost = 0

    while tries_left:
        try:
            api_call = await get_api_chatgpt4_interpret_image_response_for_task(
                prompt,
                image_path,
                'evaluate_page_image',
                params
            )
            image_interpretation = api_call.response
            total_cost += api_call.cost
            image_interpretation_with_heading = f"""Relationship between '{element1}' and '{element2}':
{image_interpretation}
"""
            return image_interpretation_with_heading, total_cost
        
        except Exception as e:
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            print(error_message)
            tries_left -= 1

    # We failed
    return None, total_cost

def combine_results_of_multiple_questions(elements_in_image, element_and_style_descriptions, pair_descriptions):
    text = ''

    text += f"""**Elements found in image**
The following elements were found in the image: {elements_in_image}

"""

    text += f"""{element_and_style_descriptions}

"""

    text += f"""**Descriptions of relationships between some pairs of elements**

"""
    for pair_description in pair_descriptions:
        text += f"""- {pair_description}
"""
    return text

async def evaluate_fit_with_prompt(expanded_description, image_description, prompt_id, page_number, params):
    # Retrieve the prompt template based on prompt_id
    prompt_template = get_prompt_template(prompt_id, 'page_evaluation')

    story_data = get_story_data(params)
    formatted_story_data = json.dumps(story_data, indent=4)
    
    page_text = get_page_text(page_number, params)

    prompt = prompt_template.format(formatted_story_data=formatted_story_data, page_number=page_number, page_text=page_text,
                                    expanded_description=expanded_description, image_description=image_description)

    # Perform the API call
    tries_left = params['n_retries'] if 'n_retries' in params else 5
    total_cost = 0

    while tries_left:
        try:
            api_call = await get_api_chatgpt4_response_for_task(
                prompt,
                'evaluate_page_image',
                params
            )
            fit_evaluation = api_call.response
            total_cost += api_call.cost
            return fit_evaluation, {'evaluate_fit': total_cost}
        
        except Exception as e:
                tries_left -= 1

    # We failed
    return None, {'evaluate_fit': total_cost}

# -----------------------------------------------

def analyse_human_ai_agreement_for_prompt_test(params):
    project_dir = params['project_dir']
    interpretation_prompt_id = params['interpretation_prompt_id']
    evaluation_prompt_id = params['evaluation_prompt_id']
    augmented_evaluations = read_project_json_file(project_dir, f'automated_evaluations_{interpretation_prompt_id}_{evaluation_prompt_id}.json')
    
    human_scores = [ e['score'] for e in augmented_evaluations if e['fit_score'] ]
    ai_scores = [ e['fit_score'] for e in augmented_evaluations if e['fit_score'] ]

    # Pearson Correlation
    pearson_corr, _ = pearsonr(human_scores, ai_scores)
    print(f"Pearson Correlation: {pearson_corr:.2f}")

    # Spearman Correlation
    spearman_corr, _ = spearmanr(human_scores, ai_scores)
    print(f"Spearman Correlation: {spearman_corr:.2f}")

    # Mean Absolute Error
    mae = mean_absolute_error(human_scores, ai_scores)
    print(f"Mean Absolute Error: {mae:.2f}")

    # Cohen's Kappa
    kappa = cohen_kappa_score(human_scores, ai_scores)
    print(f"Cohen's Kappa: {kappa:.2f}")

    # Confusion Matrix
    cm = confusion_matrix(human_scores, ai_scores, labels=[0, 1, 2, 3, 4])
    print("Confusion Matrix:")
    print(cm)

    # Scatter Plot
    plt.scatter(human_scores, ai_scores, alpha=0.6)
    plt.xlabel('Human Scores')
    plt.ylabel('AI Scores')
    plt.title('Human vs AI Scores')
    plt.grid(True)
    plt.show()


# -----------------------------------------------

def generate_prompt_evaluation_html_report(params):
    project_dir = params['project_dir']
    project_dir = absolute_file_name(project_dir)
    
    interpretation_prompt_id = params['interpretation_prompt_id']
    evaluation_prompt_id = params['evaluation_prompt_id']
    
    # Path to the augmented evaluations JSON file
    augmented_evaluations_path = project_pathname(
        project_dir,
        f'automated_evaluations_{interpretation_prompt_id}_{evaluation_prompt_id}.json'
    )
    
    if not file_exists(augmented_evaluations_path):
        print(f"Augmented evaluations file not found at {augmented_evaluations_path}")
        return
    
    # Read the augmented evaluations data
    augmented_evaluations = read_json_file(augmented_evaluations_path)
    
    # Prepare the HTML content using a template
    env = Environment(loader=FileSystemLoader('.'))
    template = env.from_string(html_template)
    
    # Render the template with the data
    html_content = template.render(evaluations=augmented_evaluations, title=params.get('title', 'Evaluation Report'))
    
    # Write the HTML content to a file
    html_output_path = project_pathname(
        project_dir,
        f'evaluation_report_{interpretation_prompt_id}_{evaluation_prompt_id}.html'
    )
    with open(html_output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"HTML report generated at {html_output_path}")

# Define the HTML template using Jinja2 templating
html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
    <style>
        .evaluation {
            border: 1px solid #ccc;
            padding: 15px;
            margin-bottom: 20px;
        }
        .image {
            max-width: 600px;
            height: auto;
        }
        .wrapped-pre {
            white-space: pre-wrap;
            word-wrap: break-word;
            max-width: 800px;
        }
        .scores {
            font-weight: bold;
        }
    </style>
</head>
<body>
    <h1>{{ title }}</h1>
    {% for eval in evaluations %}
    <div class="evaluation">
        <h2>Page {{ eval.page_number }} - Description {{ eval.description_version }} - Image {{ eval.image_version }}</h2>
        <p><strong>Text:</strong></p>
        <pre class="wrapped-pre">{{ eval.text }}</pre>
        
        {% if eval.image_path %}
        <img src="{{ eval.image_path }}" alt="Image for Page {{ eval.page_number }}" class="image">
        {% else %}
        <p><em>Image not found.</em></p>
        {% endif %}
        
        <p class="scores">
            Human Score: {{ eval.score }}{% if eval.comments %} - Comments: {{ eval.comments }}{% endif %}<br>
            AI Fit Score: {{ eval.fit_score }}{% if eval.fit_comments %} - AI Comments: {{ eval.fit_comments }}{% endif %}
        </p>
        
        <h3>Expanded Description</h3>
        <pre class="wrapped-pre">{{ eval.expanded_description }}</pre>
        
        <h3>Image Interpretation</h3>
        <pre class="wrapped-pre">{{ eval.image_interpretation }}</pre>
        
        <h3>Cost Information</h3>
        <pre class="wrapped-pre">{{ eval.cost_info }}</pre>
    </div>
    {% endfor %}
</body>
</html>
"""


