
"""
Code to support the manual audio/text alignment functionality.
"""

from .clara_utils import local_directory_exists, make_local_directory, read_local_json_file, post_task_update
from .clara_classes import InternalCLARAError

import os
import subprocess

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

def process_alignment_metadata(metadata_file: str, audio_file: str, output_dir: str, callback=None) -> list:
    """
    Process the metadata from manual audio/text alignment.

    Parameters:
    - metadata_file: Path to the JSON file containing aligned text, start_time, and end_time.
    - audio_file: Path to the main mp3 file containing audio for the entire document.
    - output_dir: Directory where the extracted audio segments will be saved.

    Returns:
    - A list of dictionaries with 'text' and 'file' for each audio segment.
    """

    # Ensure the output directory exists
    if not local_directory_exists(output_dir):
        make_local_directory(output_dir)

    # Load the metadata from the JSON file
    try:
        alignments = read_local_json_file(metadata_file)
    except Exception as e:
        raise InternalCLARAError( message=f'*** Error: unable to read alignment metadata file "{metadata_file}": {str(e)}')

    new_metadata = []

    for idx, entry in enumerate(alignments):
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
