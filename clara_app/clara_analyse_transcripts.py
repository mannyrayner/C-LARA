from .clara_chatgpt4 import call_chat_gpt4, interpret_chat_gpt4_response_as_json
from .clara_utils import absolute_file_name, read_txt_file, write_json_to_file_plain_utf8, read_json_file, file_exists
from .clara_utils import make_directory, merge_dicts, post_task_update
from .clara_classes import ChatGPTError

import json
import os
import time
import traceback

_annotated_turns_dir = '$CLARA/ChatGPTTranscripts/annotated_turns'
_max_number_of_preceding_turns = 10

# ---------------------------------------
# Parsing raw transcript files into JSON form

def process_transcripts(directory='$CLARA/ChatGPTTranscripts',
                        outfile='$CLARA/ChatGPTTranscripts/parsed_transcripts.json'):
    abs_directory = absolute_file_name(directory)
    
    transcripts = []
    turn_id = 1
    total_turns = 0
    total_user_words = 0
    total_chatgpt_words = 0

    for filename in os.listdir(abs_directory):
        if filename.endswith(".txt"):  # Assuming transcripts are in .txt files
            file_path = os.path.join(abs_directory, filename)
            turns = parse_transcript_file(file_path)
            for turn in turns:
                n_words = len(turn['text'].split())
                if turn['speaker'] == 'User':
                    total_user_words += n_words
                else:
                    total_chatgpt_words += n_words
                turn['turn_words'] = n_words
                turn['turn_id'] = turn_id
                turn_id += 1
            transcripts.append({"file": filename, "turns": turns})
            total_turns += len(turns)
    
    write_json_to_file_plain_utf8(transcripts, outfile)
    print(f'--- Written parsed transcript ({total_turns} turns) to {outfile}')
    print(f'--- Total User words: {total_user_words}')
    print(f'--- Total ChatGPT words: {total_chatgpt_words}')

def parse_transcript_file(file_path):
    lines = read_txt_file(file_path).split('\n')
    print(f'--- Read transcript file ({len(lines)} lines), {file_path}')

    turns = []
    # A session always starts with the User speaking
    current_speaker = "User"
    current_turn = []

    for line in lines:
        line = line.strip()
        if line in ["ChatGPT", "User"]:
            if current_turn:
                turns.append({"speaker": current_speaker, "text": "\n".join(current_turn)})
                current_turn = []
            current_speaker = "ChatGPT" if line == "ChatGPT" else "User"
        else:
            current_turn.append(line)

    # Add the last turn if any
    if current_turn:
        turns.append({"speaker": current_speaker, "text": "\n".join(current_turn)})

    print(f'--- Parsed transcript file ({len(turns)} turns)')
    return turns

def read_parsed_transcript(parsed_file='$CLARA/ChatGPTTranscripts/parsed_transcripts.json'):
    data = read_json_file(parsed_file)
    transcript_dict = {}
    for file_data in data:
        for turn in file_data['turns']:
            transcript_dict[turn['turn_id']] = turn

    print(f'--- Read transcript file ({len(transcript_dict)} turns) {parsed_file}')
    return transcript_dict

# ---------------------------------------
# Initial GPT-4-based annotation of transcripts

def annotate_multiple_transcripts(first_turn_id, n_turns, config_info={}, callback=None):
    start_time = time.time()
    total_cost = 0.0
    for turn_id in range(first_turn_id, first_turn_id + n_turns):
        post_task_update(callback, f'--------- TURN {turn_id} -------------')
        api_calls = annotate_transcript(turn_id, config_info=config_info, callback=callback)
        total_cost += sum( [ api_call.cost for api_call in api_calls ] )
    elapsed_time = time.time() - start_time
    post_task_update(callback, f'--- Annotated (${total_cost:.2f}; {elapsed_time:.1f} secs)')

def annotate_transcript(turn_id, config_info={}, callback=None):
    try:
        prompt = create_annotation_prompt_for_turn(turn_id)
        annotations, api_calls = call_gpt4_to_get_annotations(prompt, config_info=config_info, callback=callback)
        turn = read_annotated_turn(turn_id)
        store_annotated_turn(turn, annotations)
        return api_calls
    except Exception as e:
        post_task_update(callback, f'*** Warning: error when trying to annotate turn {turn_id}')
        error_message = f'"{str(e)}"\n{traceback.format_exc()}'
        post_task_update(callback, error_message)

def call_gpt4_to_get_annotations(prompt, config_info={}, callback=None):
    api_calls = []
    n_attempts = 0
    limit = 5
    while True:
        if n_attempts >= limit:
            raise ChatGPTError( message=f'*** Giving up, have tried sending this to ChatGPT-4 {limit} times' )
        n_attempts += 1
        post_task_update(callback, f'--- Calling ChatGPT-4 (attempt #{n_attempts}) to annotate turn')
        try:
            api_call = call_chat_gpt4(prompt, config_info=config_info, callback=callback)
            api_calls += [ api_call ]
            annotations = interpret_chat_gpt4_response_as_json(api_call.response, object_type='dict', callback=callback)
            return annotations, api_calls
        except ChatGPTError as e:
            post_task_update(callback, f'*** Warning: unable to parse response from ChatGPT-4')
            post_task_update(callback, e.message)
        except Exception as e:
            post_task_update(callback, f'*** Warning: error when sending request to ChatGPT-4')
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            

def create_annotation_prompt_for_turn(turn_id):
    template = """I am going to show you a small part of a conversation between an instance of ChatGPT-4 and
a human software engineer. The overall theme is a collaboration between the AI and the human to build an online platform,
"C-LARA", that allows users to construct and view multimodal texts in a variety of languages. The project has been running for
about a year and has been very successful.

We want to annotate the conversation so that we better understand the way in which the AI and human partners
have interacted. I am going to give you a turn with some context. Specifically, you will get the following:

a) Annotations for several turns immediately before the current one. 
b) The full text of the immediately preceding turn.
c) The full text of the current turn.

I want you to return JSON annotations for the current turn in the same format as the ones shown, i.e. a summary and a list of
topics with a tag for each topic saying how the turn has changed its status. Typical tags might be "start", "end", "ask question",
"answer question", "provide code" and "give feedback".

When annotating the current turn, please refer to the topics shown as associated with previous turns.
Try to align the current turn's topics with these existing topics where appropriate, using the same topic labels
if the discussion continues or evolves on the same themes. This will help us track how topics develop over the course
of the conversation.

Since the output will be read by a Python script, return only the JSON.

Here are the annotations for the {number_of_preceding_turns} preceding turns:

{annotations}

Here is the immediately preceding turn:

{preceding_turn}

Here is the turn to annotate:

{current_turn}
"""

    formatted_annotations, number_of_preceding_turns = formatted_annotations_for_preceding_turns(turn_id, _max_number_of_preceding_turns)
    preceding_turn = formatted_turn(turn_id - 1)
    current_turn = formatted_turn(turn_id)
    prompt = template.replace('{annotations}', formatted_annotations).replace('{number_of_preceding_turns}', str(number_of_preceding_turns))
    prompt = prompt.replace('{preceding_turn}', preceding_turn).replace('{current_turn}', current_turn)

    return prompt

def formatted_annotations_for_preceding_turns(turn_id, max_number):
    annotations_to_use = []
    for turn_id1 in range(turn_id - (1 + max_number ), turn_id - 1 ):
        annotations = read_annotations_for_turn(turn_id1)
        if annotations:
            annotations_to_use.append(json.dumps(annotations))

    formatted_annotations = '\n\n'.join(annotations_to_use)
    number_of_preceding_turns = len(annotations_to_use)

    return formatted_annotations, number_of_preceding_turns

def formatted_turn(turn_id):
    try:
        turn = read_annotated_turn(turn_id)
        turn_to_display = { 'turn_id': turn['turn_id'],
                            'speaker': turn['speaker'],
                            'text': turn['text']
                            }
        if 'topics' in turn:
            turn_to_display['topics'] = turn['topics']
                            
        return json.dumps(turn_to_display)
    except:
        return f'(Turn {turn_id} not found)'

def store_annotated_turn(turn, annotations):
    make_directory(_annotated_turns_dir, parents=True, exist_ok=True)
    turn_id = turn['turn_id']
    file = stored_turn_pathname(turn_id)
    
    annotated_turn = merge_dicts(turn, annotations)
    write_json_to_file_plain_utf8(annotated_turn, file)
    print(f'--- Written annotated turn {turn_id} to {file}')

def read_annotations_for_turn(turn_id):
    try:
        turn = read_annotated_turn(turn_id)
        return { 'speaker': turn['speaker'],
                 'summary': turn['summary'],
                 'topics': turn['topics'],
                 'turn_id': turn['turn_id']}
    except:
        return None

def read_annotated_turn(turn_id):
    file = stored_turn_pathname(turn_id)
    if file_exists(file):
        return read_json_file(file)
    
    transcript_dict = read_parsed_transcript()
    if turn_id in transcript_dict:
        return transcript_dict[turn_id]
    else:
        return None
    
def stored_turn_pathname(turn_id):
    return f'{_annotated_turns_dir}/turn_{turn_id}.json'
