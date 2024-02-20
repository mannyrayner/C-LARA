from .clara_chatgpt4 import call_chat_gpt4
from .clara_utils import absolute_file_name, read_txt_file, write_json_to_file_plain_utf8, read_json_file, file_exists
from .clara_utils import make_directory, merge_dicts

import json
import os

_annotated_turns_dir = '$CLARA/ChatGPTTranscripts/annotated_turns'

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

def store_annotated_turn(turn, annotations):
    make_directory(_annotated_turns_dir, parents=True, exist_ok=True)
    turn_id = turn['turn_id']
    file = stored_turn_pathname(turn_id)
    
    annotated_turn = merge_dicts(turn, annotations)
    write_json_to_file_plain_utf8(annotated_turn, file)
    print(f'--- Written annotated turn {turn_id} to {file}')

def read_annotated_turn(turn_id):
    file = stored_turn_pathname(turn_id)
    if not file_exists(file):
        return None
    else:
        return read_json_file(file)

def stored_turn_pathname(turn_id):
    return f'{_annotated_turns_dir}/turn_{turn_id}.json'
