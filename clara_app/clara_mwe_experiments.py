from .clara_embeddings import get_embedding, cosine_similarity
from .clara_internalise import internalize_text
from .clara_create_annotations import call_chatgpt4_to_annotate_or_improve_elements_async
from .clara_utils import absolute_file_name, read_json_file, post_task_update_async

import re
import json
import asyncio
import pprint
from collections import defaultdict

def convert_speckled_band():
    input_file = '$CLARA/linguistic_data/english/MWEsExperiment/spec-mwe.html'
    output_file = '$CLARA/linguistic_data/english/MWEsExperiment/spec-mwe.json'
    convert_mwe_gold_standard_data(input_file, output_file)

def convert_dancing_men():
    input_file = '$CLARA/linguistic_data/english/MWEsExperiment/danc-mwe.html'
    output_file = '$CLARA/linguistic_data/english/MWEsExperiment/danc-mwe.json'
    convert_mwe_gold_standard_data(input_file, output_file)

def convert_mwe_gold_standard_data(input_file, output_file):
    sentences = parse_gold_standard_mwes(absolute_file_name(input_file))
    print(f"Read {input_file} ({len(sentences)} items).")
    
    json_data = convert_mws_to_json(sentences)
    write_mwes_json_output(json_data, absolute_file_name(output_file))
    
    print(f"Conversion complete. Output saved to {output_file} ({len(json_data)} items).")

def parse_gold_standard_mwes(input_file):
    sentences = []
    with open(input_file, 'r', encoding='utf-8') as file:
        sentence = None
        words = []
        mwes = defaultdict(list)

        for line in file:
            # Start of a new sentence
            if line.startswith("<span class='sent' id="):
                if sentence is not None:
                    # Save the previous sentence
                    sentences.append((sentence, words, mwes))
                # Initialize new sentence
                sentence = re.search(r"id='([^']+)'", line).group(1)
                words = []
                mwes = defaultdict(list)
            elif line.startswith("<span id='w"):
                # Extract word details
                word_id = re.search(r"id='([^']+)'", line).group(1)
                word = re.search(r">(.*?)<", line).group(1)
                lemma = re.search(r"data-lemma = '([^']+)'", line).group(1)
                pos = re.search(r"data-pos='([^']+)'", line).group(1)
                cids = re.findall(r"data-cid = '([^']+)'", line)
                
                # Store word details
                words.append(word)
                for cid in cids:
                    mwes[cid].append(word)

        # Save the last sentence
        if sentence is not None:
            sentences.append((sentence, words, mwes))

    return sentences

def convert_mws_to_json(sentences):
    json_data = []
    for sentence_id, words, mwes in sentences:
        text = " ".join(words)
        # Filter out MWEs with only one word
        mwe_list = [mwe_words for mwe_words in mwes.values() if len(mwe_words) > 1]
        json_obj = {
            "text": text,
            "mwes": mwe_list
        }
        json_data.append(json_obj)
    return json_data

def write_mwes_json_output(json_data, output_file):
    with open(output_file, 'w', encoding='utf-8') as file:
        for entry in json_data:
            json.dump(entry, file)
            file.write('\n')

# ----------------------------------------

def test_mwe_annotate_segments_using_few_shot_examples():
    segment1 = "I think he just made it up."
    segment2 = "It|'s not a big deal."
    l2_language = 'english'
    config_info = config_info={'gpt_model': 'gpt-4o'}
    few_shot_examples_from_repo = read_json_file('$CLARA/prompt_templates/default/mwe_annotate_examples.json')
    segments_and_few_shot_examples = [ ( segment1, few_shot_examples_from_repo ),
                                       ( segment2, few_shot_examples_from_repo ) ]
    result = mwe_annotate_segments_using_few_shot_examples(segments_and_few_shot_examples,
                                                           l2_language, config_info=config_info)

    print(f"result:")
    pprint.pprint(result)

def mwe_annotate_segments_using_few_shot_examples(segments_and_few_shot_examples,
                                                  l2_language, config_info={}, callback=None):

    #print(f'segments_and_few_shot_examples:')
    #pprint.pprint(segments_and_few_shot_examples)
    
    content_elements_and_few_shot_examples = []
    l1_language = 'irrelevant'
    for pair in segments_and_few_shot_examples:
        segment_text, few_shot_examples = pair
        
        internalised_annotated_text = internalize_text(segment_text, l2_language, l1_language, 'segmented')
        content_elements = internalised_annotated_text.content_elements()
        content_elements_and_few_shot_examples.append( ( content_elements, few_shot_examples ) )

    #print(f'segmented_elements_and_few_shot_examples:')
    #pprint.pprint(content_elements_and_few_shot_examples)
    
    annotations, api_calls = asyncio.run(mwe_annotate_segments_using_few_shot_examples_async(content_elements_and_few_shot_examples,
                                                                                             l2_language, config_info=config_info, callback=callback))

    #print(f'annotations:')
    #pprint.pprint(annotations)

    n_segments = len(content_elements_and_few_shot_examples)
    n_annotations = len(annotations)
    if n_segments != n_annotations:
        raise ValueError(f'Mismatch: there are {n_segments} texts but {n_annotations} MWE annotations')
    
    segments_and_few_shot_examples_and_annotations = zip(segments_and_few_shot_examples, annotations)
    segments_and_annotations = [ ( item[0][0], item[1] ) for item in segments_and_few_shot_examples_and_annotations ]
    total_cost = sum([ api_call.cost for api_call in api_calls ])

    reformatted_segments_and_annotations = convert_annotation_results_to_few_shot_format(segments_and_annotations)

    return ( reformatted_segments_and_annotations, total_cost )
    

async def mwe_annotate_segments_using_few_shot_examples_async(content_elements_and_few_shot_examples,
                                                              l2_language, config_info={}, callback=None):
    tasks = []
    for pair in content_elements_and_few_shot_examples:
        content_elements, few_shot_examples = pair
    
        tasks.append(asyncio.create_task(
            call_chatgpt4_to_mwe_annotate_async(content_elements, l2_language, few_shot_examples=few_shot_examples,
                                                config_info=config_info, callback=callback)
        ))

    post_task_update_async(callback, f'--- Running {len(tasks)} async tasks')
    results = await asyncio.gather(*tasks)
    
    all_api_calls = []
    all_annotations_for_segments = []

    for result in results:
        annotations_for_segments, api_calls = result
        all_annotations_for_segments.append(annotations_for_segments)
        all_api_calls.extend(api_calls)

    return all_annotations_for_segments, all_api_calls

async def call_chatgpt4_to_mwe_annotate_async(content_elements, l2_language, few_shot_examples=[],
                                              config_info={}, callback=None):

    annotate_or_improve = 'annotate'
    processing_phase = 'mwe'
    l1_language = 'irrelevant'
    return await call_chatgpt4_to_annotate_or_improve_elements_async(annotate_or_improve, processing_phase,
                                                                     content_elements,
                                                                     l1_language, l2_language,
                                                                     few_shot_examples=few_shot_examples,
                                                                     config_info=config_info, callback=callback)

def convert_annotation_results_to_few_shot_format(annotation_results):
    few_shot_examples = []
    
    for segment, annotation in annotation_results:
        # Extract the text segment
        text_segment = segment.replace('|', '')
        
        # Extract the list of MWEs as a comma-separated string
        mwes = annotation['mwes']
        mwes_str = ','.join([' '.join(mwe) for mwe in mwes])
        
        # Extract the analysis text
        analysis = annotation['analysis']
        
        # Format for few-shot examples
        few_shot_example = [text_segment, mwes_str, analysis]
        few_shot_examples.append(few_shot_example)
    
    return few_shot_examples

