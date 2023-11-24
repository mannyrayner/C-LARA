
from . import clara_internalise
from . import clara_universal_dependencies
from .clara_classes import *
from .clara_utils import make_tmp_file, get_config, remove_file, local_file_exists
from .clara_utils import write_json_or_txt_file, read_json_or_txt_file, absolute_file_name, absolute_local_file_name

import difflib
import subprocess

config = get_config()

def test(ID):
    if ID == 1:
        text = 'Mary had a little lamb, its fleece was white as snow.'
        language = 'english'
        input_file = '$CLARA/tmp/treetagger_input_file.txt'
        output_file = '$CLARA/tmp/treetagger_output_file.txt'

        write_json_or_txt_file(text, input_file)
        call_treetagger_using_files(language, input_file, output_file)
        return read_json_or_txt_file(output_file)
    elif ID == 2:
        text = 'Mary had a little lamb, its fleece was white as snow.'
        language = 'english'

        return tag_text_with_treetagger(text, language)
    elif ID == 3:
        text = """Mary had a little lamb,
Its fleece was white as snow.
And everywhere that Mary went
That lamb was sure to go"""
        l2_language = 'english'
        l1_language = 'irrelevant'

        internalised_text = clara_internalise.internalize_text(text, l2_language, l1_language, 'segmented')
        tag_internalised_text_with_treetagger(internalised_text)

        return internalised_text.to_text('lemma')
    elif ID == 4:
        text = """Mary had a little lamb,
Its fleece was white as snow.
And everywhere that Mary went
That lamb was sure to go"""
        l2_language = 'english'

        return generate_tagged_version_with_treetagger(text, l2_language)
    else:
        print('*** Error: unknown ID: {ID}')
        return

# Tag each word with its surface form
def generate_tagged_version_with_trivial_tags(segmented_text):
    l1_language = 'irrelevant'
    l2_language = 'irrelevant'
    internalised_text = clara_internalise.internalize_text(segmented_text, l2_language, l1_language, 'segmented')
    tag_internalised_text_with_trivial_tags(internalised_text)
    return internalised_text.to_text('lemma')

def tag_internalised_text_with_trivial_tags(internalised_text):
    for page in internalised_text.pages:
        for segment in page.segments:
            for content_element in segment.content_elements:
                if content_element.type == 'Word':
                    content_element.annotations['lemma'] = content_element.content.lower()
                    content_element.annotations['pos'] = 'X'

def generate_tagged_version_with_treetagger(segmented_text, l2_language):
    l1_language = 'irrelevant'
    internalised_text = clara_internalise.internalize_text(segmented_text, l2_language, l1_language, 'segmented')
    tag_internalised_text_with_treetagger(internalised_text)
    return internalised_text.to_text('lemma')

def tag_internalised_text_with_treetagger(internalised_text):
    # Get the sequence of content elements
    content_elements = internalised_text.content_elements()
    word_content_elements = [ elem for elem in content_elements if elem.type == "Word" ]

    # Initially mark every element as having no POS and lemma
    for elem in word_content_elements:
        elem.annotations["pos"] = "NO_ANNOTATION"
        elem.annotations["lemma"] = "NO_ANNOTATION"

    # Get the plain text, separated by newlines since we're passing it to TreeTagger without preprocessing
    plain_text = '\n'.join([ elem.content for elem in content_elements if elem.type in ( "Word", "NonWordText" ) ])

    # Tag the plain text with TreeTagger
    tagged_text = tag_text_with_treetagger(plain_text, internalised_text.l2_language, preprocessed=True)

    # Align the sequence of content elements with the tagged text
    word_seq = [ elem.content for elem in word_content_elements ]
    tagged_word_seq = [ word for word, _, _ in tagged_text ]
    seq_matcher = difflib.SequenceMatcher(None, word_seq, tagged_word_seq)
    alignments = seq_matcher.get_opcodes()

    # Use the alignment to insert the POS and Lemma information into the content elements
    for tag, i1, i2, j1, j2 in alignments:
        if tag == "equal":
            for i, j in zip(range(i1, i2), range(j1, j2)):
                word_content_elements[i].annotations["pos"] = tagged_text[j][1]
                word_content_elements[i].annotations["lemma"] = tagged_text[j][2]

    return clara_universal_dependencies.convert_tags_to_ud_v2_in_internalised_text(internalised_text)

def tag_text_with_treetagger(text, language, preprocessed=False):
    #temp_input_file = f"$CLARA/tmp/treetagger_temp_input_{uuid.uuid4()}.txt"
    #temp_output_file = f"$CLARA/tmp/treetagger_temp_output_{uuid.uuid4()}.txt"
    temp_input_file = make_tmp_file('treetagger_temp_input', 'txt')
    temp_output_file = make_tmp_file('treetagger_temp_output', 'txt')

    # Write the input text to a temporary file
    write_json_or_txt_file(text, temp_input_file)

    # Invoke TreeTagger
    try:
        call_treetagger_using_files(language, temp_input_file, temp_output_file, preprocessed)

        # Read the output from TreeTagger
        raw_output = read_json_or_txt_file(temp_output_file)

        # Parse the raw output into a list of (Word, POS, Lemma) tuples
        tagged_text = []
        for line in raw_output.split("\n"):
            if line:  # Ignore empty lines
                word, pos, lemma = line.split("\t")
                tagged_text.append((word, pos, lemma))
    finally:
        # Clean up the temporary files
        remove_file(temp_input_file)
        remove_file(temp_output_file)

    # Return the tagged text
    return tagged_text


# Try to invoke TreeTagger for 'language', taking input from 'input_file' and writing output to 'output_file'.
# Raise a TreeTaggerError if something goes wrong.
def call_treetagger_using_files(language, input_file, output_file, preprocessed=False):
    if not fully_supported_treetagger_language(language):
        raise TreeTaggerError(message = f'Attempt to call TreeTagger with unsupported language "{language}"')
    abs_input_file = absolute_local_file_name(input_file)
    abs_output_file = absolute_local_file_name(output_file)
    invocation = treetagger_invocation(language, abs_input_file, abs_output_file, preprocessed)
    try:
        status = execute_treetagger_invocation(invocation)
    except Exception as e:
        raise TreeTaggerError(message = f'Exception during TreeTagger call: "{str(e)}"')
    if status == 0 and local_file_exists(abs_output_file):
        return
    elif status != 0:
        raise TreeTaggerError(message = f'TreeTagger call failed (status {status}): "{invocation}"')
    else:
        raise TreeTaggerError(message = f'TreeTagger call failed (output file not found): "{invocation}"')

treetagger_root = '$TREETAGGER'

tokenize_script = absolute_local_file_name('$CLARA/perl/clara_utf8-tokenize.perl')

treetagger_common_options = '-token -lemma -sgml -no-unknown -quiet'

# The TreeTagger invocation patterns for the languages we cover
# These have all been tested in LARA
treetagger_invocation_templates = {
    'english': 'perl {tokenize_script} -e -a {treetagger_root}/lib/english-abbreviations {input_file} | {treetagger_root}/bin/tree-tagger {treetagger_root}/lib/english-bnc.par {treetagger_common_options} > {output_file}',
    'french': 'perl {tokenize_script} -f -a {treetagger_root}/lib/french-abbreviations {input_file} | {treetagger_root}/bin/tree-tagger {treetagger_root}/lib/french.par {treetagger_common_options} > {output_file}',
    'german': 'perl {tokenize_script} -a {treetagger_root}/lib/german-abbreviations {input_file} | {treetagger_root}/bin/tree-tagger {treetagger_root}/lib/german.par {treetagger_common_options} > {output_file}',
    'middle-high-german': 'perl {tokenize_script} {input_file} | {treetagger_root}/bin/tree-tagger {treetagger_root}/lib/middle-high-german.par {treetagger_common_options} > {output_file}',
    'italian': 'perl {tokenize_script} -i -a {treetagger_root}/lib/italian-abbreviations {input_file} | {treetagger_root}/bin/tree-tagger {treetagger_root}/lib/italian.par {treetagger_common_options} > {output_file}',
    'spanish': 'perl {tokenize_script} -a {treetagger_root}/lib/spanish-abbreviations {input_file} | {treetagger_root}/bin/tree-tagger {treetagger_root}/lib/spanish.par {treetagger_common_options} > {output_file}',
    'dutch': 'perl {tokenize_script} -a {treetagger_root}/lib/dutch-abbreviations {input_file} | {treetagger_root}/bin/tree-tagger {treetagger_root}/lib/dutch.par {treetagger_common_options} > {output_file}',
    'russian': 'perl {tokenize_script} {input_file} | {treetagger_root}/bin/tree-tagger {treetagger_root}/lib/russian.par {treetagger_common_options} > {output_file}',
    'czech': 'perl {tokenize_script} {input_file} | {treetagger_root}/bin/tree-tagger {treetagger_root}/lib/czech.par {treetagger_common_options} > {output_file}',
    'danish': 'perl {tokenize_script} {input_file} | {treetagger_root}/bin/tree-tagger {treetagger_root}/lib/danish.par {treetagger_common_options} > {output_file}',
    'finnish': 'perl {tokenize_script} {input_file} | {treetagger_root}/bin/tree-tagger {treetagger_root}/lib/finnish.par {treetagger_common_options} > {output_file}',
    'greek': 'perl {tokenize_script} {input_file} | {treetagger_root}/bin/tree-tagger {treetagger_root}/lib/greek.par {treetagger_common_options} > {output_file}',
    'korean': 'perl {tokenize_script} {input_file} | {treetagger_root}/bin/tree-tagger {treetagger_root}/lib/korean.par {treetagger_common_options} > {output_file}',
    'norwegian': 'perl {tokenize_script} {input_file} | {treetagger_root}/bin/tree-tagger {treetagger_root}/lib/norwegian.par {treetagger_common_options} > {output_file}',
    'polish': 'perl {tokenize_script} {input_file} | {treetagger_root}/bin/tree-tagger {treetagger_root}/lib/polish.par {treetagger_common_options} > {output_file}',
    'portuguese': 'perl {tokenize_script} {input_file} | {treetagger_root}/bin/tree-tagger {treetagger_root}/lib/portuguese.par {treetagger_common_options} > {output_file}',
    'romanian': 'perl {tokenize_script} {input_file} | {treetagger_root}/bin/tree-tagger {treetagger_root}/lib/romanian.par {treetagger_common_options} > {output_file}',
    'slovak': 'perl {tokenize_script} {input_file} | {treetagger_root}/bin/tree-tagger {treetagger_root}/lib/slovak2.par {treetagger_common_options} > {output_file}',
    'slovenian': 'perl {tokenize_script} {input_file} | {treetagger_root}/bin/tree-tagger {treetagger_root}/lib/slovenian.par {treetagger_common_options} > {output_file}',
    'swahili': 'perl {tokenize_script} {input_file} | {treetagger_root}/bin/tree-tagger {treetagger_root}/lib/swahili.par {treetagger_common_options} > {output_file}',
    'swedish': 'perl {tokenize_script} {input_file} | {treetagger_root}/bin/tree-tagger {treetagger_root}/lib/swedish.par {treetagger_common_options} > {output_file}',
    'catalan': 'perl {tokenize_script} -c {input_file} | {treetagger_root}/bin/tree-tagger {treetagger_root}/lib/catalan.par {treetagger_common_options} > {output_file}'
    }

# Checks if language is supported by TreeTagger
def fully_supported_treetagger_language(language):
    return treetagger_parameter_file_installed_for_language(language) and clara_universal_dependencies.language_with_conversion_function(language)

def treetagger_parameter_file_installed_for_language(language):
    if not language in treetagger_invocation_templates:
        return False
    invocation = treetagger_invocation_templates[language]
    main_part = invocation.split('|')[1]
    parameters_file = main_part.split()[1]
    parameters_file_full = parameters_file.format( treetagger_root = treetagger_root )
    return local_file_exists(absolute_local_file_name(parameters_file_full))

# Returns an invocation to call TreeTagger for a given language, input file and output file.
def treetagger_invocation(language, input_file, output_file, preprocessed=False):
    template = treetagger_invocation_templates[language]
    if preprocessed:
        template = modify_template_for_preprocessed_text(template)
    return template.format( treetagger_root = treetagger_root,
                            tokenize_script = tokenize_script,
                            input_file = input_file,
                            treetagger_common_options = treetagger_common_options,
                            output_file = output_file )

# If the text has been preprocessed, probably using ChatGPT-4's segmentation.
# then we need to skip the first part of the invocation and instead take input directly from the tokenized file.
def modify_template_for_preprocessed_text(template):
    components = template.split('|')
    if len(components) != 2:
        raise TreeTaggerError(message = f'Unable to use invocation template: "template"')
    preprocessing, main = components
    return '< {input_file}' + main

# Use cygwin's bash to execute the command. Get the path through the config file.
def execute_treetagger_invocation(invocation):
    try:
        print(f'--- Execute {invocation}')
        path_to_bash_excutable = config.get('paths', 'bash')
        process = subprocess.run([path_to_bash_excutable, '-c', invocation], check=True)
        code = process.returncode
        print(f'--- Done, return code = {code}')
        return code
    except subprocess.CalledProcessError as e:
        raise TreeTaggerError(message = f'Exception during TreeTagger call: "{str(e)}"')
                          
