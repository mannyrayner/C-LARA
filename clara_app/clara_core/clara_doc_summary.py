from . import clara_utils

import ast
from .clara_utils import read_txt_file

file_names = [
    "$CLARA/clara_core/clara_chatgpt4.py",
    "$CLARA/clara_core/clara_classes.py",
    "$CLARA/clara_core/clara_concordance_annotator.py",
    "$CLARA/clara_core/clara_create_annotations.py",
    "$CLARA/clara_core/clara_create_story.py",
    "$CLARA/clara_core/clara_internalise.py",
    "$CLARA/clara_core/clara_merge_glossed_and_tagged.py",
    "$CLARA/clara_core/clara_renderer.py",
    "$CLARA/clara_core/clara_tts_annotator.py",
    "$CLARA/clara_core/clara_tts_api.py",
    "$CLARA/clara_core/clara_tts_repository.py",
    "$CLARA/clara_core/clara_utils.py",
    ]

def extract_docstring(file_name):
    abs_file_name = clara_utils.absolute_file_name(file_name)
    #with open(abs_file_name, "r", encoding="utf-8") as f:
    #    source = f.read()
    source = read_txt_file(abs_file_name)
    tree = ast.parse(source)
    return ast.get_docstring(tree)

def generate_summary():
    for file_name in file_names:
        docstring = extract_docstring(file_name)
        print(f"=======================================\n{file_name}:\n\n{docstring}\n")

if __name__ == "__main__":
    generate_summary()
