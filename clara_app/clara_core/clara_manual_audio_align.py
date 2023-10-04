
"""
Code to support the manual audio/text alignment functionality.
"""

from .clara_utils import local_directory_exists, make_local_directory, read_local_json_file, post_task_update
from .clara_classes import InternalCLARAError

import os
import subprocess
import traceback
import re

def add_indices_to_segmented_text(segmented_text):
    """
    Transform normal segmented text into a version with numbered breaks
    """
    # Split the text based on the segment delimiter '||'
    segments = segmented_text.split('||')
    
    # Initialize an empty string for the annotated text
    annotated_text = "|0|"
    
    # Iterate over the segments and append the annotated segment to the annotated_text
    for idx, segment in enumerate(segments, start=1):
        annotated_text += segment + f"|{idx}|"
    
    return annotated_text

def process_alignment_metadata(metadata, audio_file, output_dir, callback=None):
    """
    Process the metadata from manual audio/text alignment.

    Parameters:
    - metadata: list of dicts containing aligned text, start_time, and end_time.
    - audio_file: Path to the main mp3 file containing audio for the entire document.
    - output_dir: Directory where the extracted audio segments will be saved.

    Returns:
    - A list of dictionaries with 'text' and 'file' for each audio segment.
    """

    # Ensure the output directory exists
    if not local_directory_exists(output_dir):
        make_local_directory(output_dir)

    new_metadata = []

    for idx, entry in enumerate(metadata):
        # Extract the audio segment using ffmpeg
        segment_file = os.path.join(output_dir, f"segment_{idx}.mp3")
        try:
            text = entry['text']
            start_time = entry["start_time"]
            end_time = entry["end_time"]
            duration = float(end_time) - float(start_time)
        except Exception as e:
            raise InternalCLARAError( message=f'*** Error: bad entry in alignment metadata file: {entry}: {str(e)}')

        cmd = [
            "ffmpeg",
            "-i", audio_file,
            "-ss", str(start_time),
            "-t", str(duration),
            "-q:a", "0",  # Best quality
            segment_file
        ]
        
        try:
            subprocess.run(cmd, check=True)
            post_task_update(callback, f'--- Extracted audio for "{text}"')
        except Exception as e:
            post_task_update(callback, f'--- Error when trying to extract audio for "{text}": {str(e)}')
            raise InternalCLARAError( message=f'*** Error: something went wrong when trying to extract audio for "{text}"') 
            
        # Add to the new metadata
        new_metadata.append({
            'text': text,
            'file': segment_file
        })

    return new_metadata

def annotated_segmented_data_and_label_file_data_to_metadata(segmented_file_content, audacity_label_content, callback=None):
    post_task_update(callback, f'--- Calling annotated_segmented_data_and_label_file_data_to_metadata')

    try:        
        # Parse the annotated segmented file using regex
        segments = re.findall(r'\|\d+\|([^|]+)', segmented_file_content)
        segments = [segment.strip() for segment in segments]

        post_task_update(callback, f'--- Found {len(segments)} segments')

        # Parse the Audacity label file
        times = []
        for line in audacity_label_content.split("\n"):
            if line:
                start_time, end_time, _ = line.split("\t")
                times.append((float(start_time), float(end_time)))

        post_task_update(callback, f'--- Found {len(times)} Audacity labels')

        # Combine the two to produce the metadata
        metadata = []
        for i, text in enumerate(segments):
            if i < len(times):
                metadata.append({
                    'text': text,
                    'start_time': times[i][0],
                    'end_time': times[i][1]
            })

        post_task_update(callback, f'--- Created {len(metadata)} alignment metadata items')
        return metadata

    except Exception as e:
        post_task_update(callback, f'*** Error when trying to create text/audio alignment metadata')
        error_message = f'"{str(e)}"\n{traceback.format_exc()}'
        post_task_update(callback, error_message)
        raise InternalCLARAError( message='Error when creating text/audio alignment metadata')
