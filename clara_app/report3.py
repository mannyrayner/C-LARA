import os
import shutil

def copy_pitjantjatjara_audio():
    # Mapping of new filenames to source filenames
    file_map = {
        "sentence1": "extracted_file_ch17_4422.mp3",
        "sentence2": "extracted_file_ch17_4424.mp3",
        "sentence3": "extracted_file_ch17_4426.mp3",
        "apu": "extracted_file_ch14_3205.mp3",
        "kutu": "extracted_file_word_kutu.mp3",
        "mai": "extracted_file_ch17_4232.mp3",
        "minyma": "extracted_file_ch11_2484.mp3",
        "ngura": "extracted_file_ch14_3202.mp3",
        "nguṟu": "extracted_file_word_nguṟu.mp3",
        "nyinangi": "extracted_file_ch17_4154.mp3",
        "papa": "extracted_file_ch12c2_2743.mp3",
        "pitjangi": "extracted_file_ch17_4156.mp3",  
        "tjara": "extracted_file_word_tjara.mp3",    
        "tjitji": "extracted_file_ch17_4307.mp3",
        "tjuṯa": "extracted_file_ch17_4234.mp3",
        "wirtjapakalpai": "extracted_file_ch17_4305.mp3",
        "pitjantjatjara": "extracted_file_word_pitjantjatjara.mp3"
    }

    # Source and destination directories
    source_dir = r"C:/cygwin64/home/sf/callector-lara-svn/trunk/Content/pitjantjatjara_course/audio/pitjantjatjara_voice_trimmed_normalised"
    destination_dir = r"C:/cygwin64/home/publications/ChatGPT/ProgressReport-3/PitjantjaraExample/Audio"

    # Ensure destination directory exists
    os.makedirs(destination_dir, exist_ok=True)

    # Copy and rename files
    for new_name, source_filename in file_map.items():
        src_path = os.path.join(source_dir, source_filename)
        dst_path = os.path.join(destination_dir, f"{new_name}.mp3")
        try:
            shutil.copyfile(src_path, dst_path)
            print(f"Copied {source_filename} → {new_name}.mp3")
        except FileNotFoundError:
            print(f"WARNING: Source file not found: {src_path}")

    print("Done.")
