from .clara_pos_tag_similarity import pos_based_similarity
from .clara_embeddings import embeddings_based_similarity
from .clara_internalise import internalize_text
from .clara_create_annotations import call_chatgpt4_to_annotate_or_improve_elements_async
from .clara_utils import absolute_file_name, make_directory, read_json_file, write_json_to_file, post_task_update_async

import toml
import re
import json
import asyncio
import pprint
from collections import defaultdict
from pathlib import Path

def convert_speckled_band():
    input_file = '$CLARA/linguistic_data/english/MWEsExperiment/spec-mwe.html'
    toml_file = '$CLARA/linguistic_data/english/MWEsExperiment/spec-split.toml'
    output_dir = '$CLARA/linguistic_data/english/MWEsExperiment/spec'
    convert_mwe_gold_standard_data(input_file, toml_file, output_dir)

def convert_dancing_men():
    input_file = '$CLARA/linguistic_data/english/MWEsExperiment/danc-mwe.html'
    toml_file = '$CLARA/linguistic_data/english/MWEsExperiment/danc-split.toml'
    output_dir = '$CLARA/linguistic_data/english/MWEsExperiment/danc'
    convert_mwe_gold_standard_data(input_file, toml_file, output_dir)

def convert_mwe_gold_standard_data(input_file, toml_file, output_dir):
    # Read split indices from the TOML file
    train_indices, dev_indices, test_indices = read_split_indices(absolute_file_name(toml_file))
    
    # Parse sentences and assign them to train, dev, and test sets
    train_sentences, dev_sentences, test_sentences = parse_gold_standard_mwes(absolute_file_name(input_file),
                                                                              train_indices, dev_indices, test_indices)
    
    # Convert each set of sentences to JSON format
    train_json = convert_mws_to_json(train_sentences)
    dev_json = convert_mws_to_json(dev_sentences)
    test_json = convert_mws_to_json(test_sentences)

    # Write output files
    abs_output_dir = absolute_file_name(output_dir)
    make_directory(abs_output_dir, parents=True, exist_ok=True)
    
    write_mwes_json_output(train_json, Path(abs_output_dir) / 'train.json')
    write_mwes_json_output(dev_json, Path(abs_output_dir) / 'dev.json')
    write_mwes_json_output(test_json, Path(abs_output_dir) / 'test.json')

    print(f"Conversion complete. Train set: {len(train_json)} items, Dev set: {len(dev_json)} items, Test set: {len(test_json)} items.")

def read_split_indices(toml_file):
    """Read the train, dev, and test split indices from the .toml file."""
    with open(toml_file, 'r') as file:
        data = toml.load(file)
    
    train_indices = (data['train']['first'], data['train']['last'])
    dev_indices = (data['dev']['first'], data['dev']['last'])
    test_indices = (data['test']['first'], data['test']['last'])
    
    return train_indices, dev_indices, test_indices

def parse_gold_standard_mwes(input_file, train_indices, dev_indices, test_indices):
    train_sentences = []
    dev_sentences = []
    test_sentences = []

    with open(input_file, 'r', encoding='utf-8') as file:
        sentence_id = None
        words = []
        mwes = defaultdict(list)

        for line in file:
            # Start of a new sentence
            if line.startswith("<span class='sent' id="):
                if sentence_id is not None:
                    # Determine the split based on the previous sentence ID
                    if train_indices[0] <= sentence_id <= train_indices[1]:
                        train_sentences.append((sentence_id, words, mwes))
                    elif dev_indices[0] <= sentence_id <= dev_indices[1]:
                        dev_sentences.append((sentence_id, words, mwes))
                    elif test_indices[0] <= sentence_id <= test_indices[1]:
                        test_sentences.append((sentence_id, words, mwes))
                # Get the new sentence ID and initialize new sentence
                sentence_id = int(re.search(r'\d+', line).group())
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
        if sentence_id is not None:
            if train_indices[0] <= sentence_id <= train_indices[1]:
                train_sentences.append((sentence_id, words, mwes))
            elif dev_indices[0] <= sentence_id <= dev_indices[1]:
                dev_sentences.append((sentence_id, words, mwes))
            elif test_indices[0] <= sentence_id <= test_indices[1]:
                test_sentences.append((sentence_id, words, mwes))

    return train_sentences, dev_sentences, test_sentences

def convert_mws_to_json(sentences):
    json_data = []
    for sentence_id, words, mwes in sentences:
        text = " ".join(words)
        # Filter out MWEs with only one word
        mwe_list = [mwe_words for mwe_words in mwes.values() if len(mwe_words) > 1]
        # Convert MWE lists to a string format, where MWEs are comma-separated
        mwe_string = ",".join([" ".join(mwe_words) for mwe_words in mwe_list])
        json_obj = {
            "text": text,
            "mwes": mwe_string  # Store MWEs as a single string
        }
        json_data.append(json_obj)
    return json_data


def write_mwes_json_output(json_data, output_file):
    write_json_to_file(json_data, output_file)

# ----------------------------------------

def test_mwe_annotate_segments_using_few_shot_examples():
    segment1 = "I think he just made it up, the thing makes no sense."
    segment2 = "It|'s not a big deal, I|'ll get over it."
    l2_language = 'english'
    config_info = {'gpt_model': 'gpt-4o'}
    few_shot_examples_from_repo = read_json_file('$CLARA/prompt_templates/default/mwe_annotate_examples.json')
    segments_and_few_shot_examples = [ ( segment1, few_shot_examples_from_repo ),
                                       ( segment2, few_shot_examples_from_repo ) ]
    result = mwe_annotate_segments_using_few_shot_examples(segments_and_few_shot_examples,
                                                           l2_language, config_info=config_info)

    print(f"result:")
    pprint.pprint(result)

def annotate_sag_et_al_examples():
    """
    Annotate the examples adapted from Sag et al to create the initial pool for the MWE experiments.
    We are going to edit the ones that come out wrong, so set keep_incorrect_records = True.
    """
    texts_mwes_pairs = read_json_file('$CLARA/linguistic_data/english/MWEsExperiment/sag_et_al/sag_et_al_examples.json')
    few_shot_examples_pool = read_json_file('$CLARA/prompt_templates/default/mwe_annotate_examples.json')
    l2_language='english'
    n = 4
    similarity_metric='pos'
    keep_incorrect_records = True
    config_info = {'gpt_model': 'gpt-4o'}
    annotated_records = annotate_texts_using_closest_few_shot_examples(texts_mwes_pairs,
                                                                       few_shot_examples_pool,
                                                                       l2_language=l2_language,
                                                                       n=n,
                                                                       similarity_metric=similarity_metric,
                                                                       keep_incorrect_records=True,
                                                                       config_info=config_info)
    write_json_to_file(annotated_records,
                       '$CLARA/linguistic_data/english/MWEsExperiment/sag_et_al/annotated_sag_et_al_examples.json')

def annotate_texts_using_closest_few_shot_examples(texts_mwes_pairs, few_shot_examples_pool,
                                                   l2_language='english', n=3,
                                                   similarity_metric='pos', keep_incorrect_records=False, config_info={}):
    """
    Annotates a list of text/MWE pairs using the closest few-shot examples from a pool based on embeddings/POS similarity.

    Parameters:
    - texts_mwes_pairs: list of dicts, each dict containing 'text' and 'mwes' as keys.
    - few_shot_examples_pool: list of lists, the pool of few-shot examples in the format [text_string, mwes_string, analysis].
    - l2_language: str, the language of the texts being annotated.
    - n: int, the number of closest few-shot examples to use for each annotation.
    - keep_incorrect_records: bool, whether to keep records of incorrect annotations. Default is False.
    - config_info: dict, configuration information for the annotation process.

    Returns:
    - A tuple (filtered_annotations, total_cost) where:
      - filtered_annotations: list of lists of the form [ text, mwes_string, CoT_analysis ].
        If keep_incorrect_records=True, incorrect results have an mwe_string field of the form { 'identified': identified, 'correct': correct }
      - total_cost: float, the total cost of API calls for annotations.
    """
    segments_and_few_shot_examples = []

    # For each text, find the top n closest few-shot examples
    for pair in texts_mwes_pairs:
        text = pair['text']
        correct_mwes = pair['mwes']

        closest_examples = get_top_n_similar_few_shot_examples(text, few_shot_examples_pool, n=n, similarity_metric=similarity_metric)
        segments_and_few_shot_examples.append((text, closest_examples, correct_mwes))

    # Annotate the texts using the selected few-shot examples
    annotations, total_cost = mwe_annotate_segments_using_few_shot_examples(
        [(text, examples) for text, examples, _ in segments_and_few_shot_examples], l2_language, config_info=config_info
    )

    filtered_annotations = []

    # Filter annotations based on whether they match the correct MWEs
    for (text, _, correct_mwes), annotation in zip(segments_and_few_shot_examples, annotations):
        identified_mwes = annotation[1]
        if make_mwes_canonical(correct_mwes) == make_mwes_canonical(identified_mwes):
            filtered_annotations.append( [ text, correct_mwes, annotation[2] ] )
        elif keep_incorrect_records:
            # Append incorrect records with correct MWEs to permit editing
            filtered_annotations.append( [ text, { 'identified': identified_mwes, 'correct': correct_mwes}, annotation[2] ] )

    return filtered_annotations, total_cost

def get_top_n_similar_few_shot_examples(text, few_shot_examples, n=3, similarity_metric='embeddings'):
    """
    Returns the top n most similar few-shot examples for a given text based on the specified similarity metric.
    
    Parameters:
    - text: str, the input text string for which we want to find similar few-shot examples.
    - few_shot_examples: list of lists, where each sublist contains [text_string, mwes_string, analysis].
    - n: int, the number of most similar few-shot examples to return.
    - similarity_metric: str, the similarity metric to use ('pos' for POS-based or 'embeddings' for embeddings-based).

    Returns:
    - list of the top n few-shot examples most similar to the input text.
    """
    if similarity_metric == 'embeddings':
        # Calculate similarities based on embeddings
        similarities = [
            (example, embeddings_based_similarity(text, example[0])) for example in few_shot_examples
        ]
    elif similarity_metric == 'pos':
        # Calculate similarities based on POS tags
        similarities = [
            (example, pos_based_similarity(text, example[0])) for example in few_shot_examples
        ]
    else:
        raise ValueError(f"Unsupported similarity metric: {similarity_metric}")

    # Sort by similarity in descending order and select the top n examples
    top_n_similar_examples = sorted(similarities, key=lambda x: x[1], reverse=True)[:n]

    # Return just the examples, not the similarity scores
    return [example[0] for example in top_n_similar_examples]



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

def make_mwes_canonical(mwes_string):
    """
    Converts an MWE string into a canonical form where MWEs are alphabetically sorted.
    
    Parameters:
    - mwes_string: str, MWEs as a comma-separated string (e.g., "going to, ended up, spilling the beans").

    Returns:
    - str: Canonical form of the MWEs (e.g., "ended up, going to, spilling the beans").
    """
    mwes_list = mwes_string.split(",")
    canonical_mwes = ",".join(sorted(mwes_list))
    return canonical_mwes


