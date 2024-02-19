from .clara_chatgpt4 import call_chat_gpt4
from .clara_utils import absolute_file_name, read_txt_file, write_json_to_file_plain_utf8

import json
import os

def process_transcripts(directory='$CLARA/ChatGPTTranscripts',
                        outfile='$CLARA/ChatGPTTranscripts/parsed_transcripts.json'):
    abs_directory = absolute_file_name(directory)
    
    transcripts = []
    total_turns = 0

    for filename in os.listdir(abs_directory):
        if filename.endswith(".txt"):  # Assuming transcripts are in .txt files
            file_path = os.path.join(abs_directory, filename)
            turns = parse_transcript_file(file_path)
            transcripts.append({"file": filename, "turns": turns})
            total_turns += len(turns)
    
    write_json_to_file_plain_utf8(transcripts, outfile)
    print(f'--- Written parsed transcript ({total_turns} turns) to {outfile}')

def parse_transcript_file(file_path):
    lines = read_txt_file(file_path).split('\n')
    print(f'--- Read transcript file ({len(lines)} lines), {file_path}')

    turns = []
    current_speaker = None
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

