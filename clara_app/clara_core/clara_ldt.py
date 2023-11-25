"""
Temporary code for testing human audio processing using LiteDevTools.
Converts LDT output into a suitable form, converting the .wav files to .mp3
"""

from .clara_utils import post_task_update, file_exists, directory_exists, local_file_exists

import subprocess
import os
import traceback

def convert_ldt_data_to_mp3(ldt_metadata, temp_ldt_dir, temp_mp3_dir, callback=None):
    try:
        if not directory_exists(temp_ldt_dir):
            post_task_update(callback, f'*** Error in wav to mp3 conversion: wav directory {temp_ldt_dir} not found')
            return []
        if not directory_exists(temp_mp3_dir):
            post_task_update(callback, f'*** Error in wav to mp3 conversion: mp3 directory {temp_mp3_dir} not found')
            return []
        for entry in ldt_metadata:
            if not entry["file"]:
                continue
            
            # Extract the filename without extension
            base_name = os.path.splitext(entry["file"])[0]
            
            # Construct the full path for the source .wav file and the destination .mp3 file
            source_wav_path = os.path.join(temp_ldt_dir, entry["file"])
            dest_mp3_path = os.path.join(temp_mp3_dir, f"{base_name}.mp3")
            
            # Check if the source .wav file exists
            if not local_file_exists(source_wav_path):
                post_task_update(callback, f'*** Error in wav to mp3 conversion: Source .wav file not found: {source_wav_path}')
                continue

            post_task_update(callback, f'--- Converting {source_wav_path} to {dest_mp3_path}')
            
            # Use ffmpeg to convert .wav to .mp3 and capture its output

            if local_file_exists(dest_mp3_path):
                post_task_update(callback, f'--- target .mp3 file already exists: {dest_mp3_path}')
            else:
                result = subprocess.run(["ffmpeg", "-i", source_wav_path, dest_mp3_path], capture_output=True, text=True)

                if not local_file_exists(dest_mp3_path):
                    post_task_update(callback, f'*** Error in wav to mp3 conversion: Target .mp3 file not found: {dest_mp3_path}')
                    continue
                else:
                    post_task_update(callback, f'--- Created {dest_mp3_path}')
            
            # Log ffmpeg output for diagnostics
            #post_task_update(callback, f'--- ffmpeg stdout: {result.stdout}')
            #post_task_update(callback, f'--- ffmpeg stderr: {result.stderr}')
            
            # Update the metadata entry to refer to the .mp3 file
            entry["file"] = f"{base_name}.mp3"

        post_task_update(callback, f'--- Converted LDT data')
        return ldt_metadata
    except Exception as e:
        post_task_update(callback, f'*** Error when trying to convert LDT data')
        error_message = f'"{str(e)}"\n{traceback.format_exc()}'
        post_task_update(callback, error_message)
        return []
