
from . import clara_internalise
from . import clara_merge_glossed_and_tagged
from . import clara_create_story
from . import clara_create_annotations
from . import clara_concordance_annotator
from . import clara_audio_annotator
from .clara_classes import *
from .clara_renderer import StaticHTMLRenderer
from . import clara_utils

import time

test_inputs_small = {
    1: ( "@Bien sûr@#of course#",
         "@Bien sûr@#bien sûr#" ),
    2: ( "l'#the#|avion#plane#",
         "l'#le#|avion#avion#" ),
    3: ( "@Bien sûr@#of course#, c'#it#|est#is# très#very# cher#expensive#.",
         "@Bien sûr@#bien sûr#, c'#ce#|est#être# très#très# cher#cher#." ),
    4: ( "@<i>Dé</i>conseillé@#not advised# cette#this# après-midi#afternoon#",
         "@<i>Dé</i>conseillé@#déconseiller# cette#ce# après-midi#après-midi#"),
    5: ( "@Bien sûr@#of course#, c'#it#|est#is# très#very# cher#expensive#.||@<i>Dé</i>conseillé@#not advised#. <page> これ#this# は#is# 犬#dog# です#is#。",
         "@Bien sûr@#bien sûr#, c'#ce#|est#être# très#très# cher#cher#.||@<i>Dé</i>conseillé@#déconseiller# <page> これ#これ# は#は# 犬#犬# です#です#。" ),
    6: ( "<h1>Le#the# titre#title#</h1>\n||Bien sûr@#of course#, c'#it#|est#is# très#very# cher#expensive#.\n||<img src=\"cat.jpg\"/>",
         "<h1>Le#le# titre#titre#</h1>\n||@Bien sûr@#bien sûr#, c'#ce#|est#être# très#très# cher#cher#.\n||<img src=\"cat.jpg\"/>" )
}

test_stories_file = "$CLARA/clara_content/clara_stories.json"

def test_internalisation_small(id, type):
    if not id in test_inputs_small:
        clara_utils.print_and_flush(f'*** Error: unknown id {id}')
        return
    if not type in ( 'glossed', 'tagged' ):
        clara_utils.print_and_flush(f'*** Error: unknown type of operation {type}')
        return
    test_input = test_inputs_small[id][0 if type == 'gloss' else 1]
    clara_utils.print_and_flush(f"Test {id}: '{test_input}' ({type})\n")

    internalized_pages = clara_internalise.internalize_text(test_input, type)
    prettyprint_internalised_text(internalized_pages)

def test_merge_small(id):
    if not id in test_inputs_small:
        clara_utils.print_and_flush(f'*** Error: unknown id {id}')
        return
    ( glossed_text, tagged_text ) = test_inputs_small[id]
    clara_utils.print_and_flush(f"Test {id}")
    clara_utils.print_and_flush(f"Glossed text: '{glossed_text}'")
    clara_utils.print_and_flush(f" Tagged text: '{tagged_text}'\n")

    glossed_pages = clara_internalise.internalize_text(glossed_text, 'gloss')
    tagged_pages = clara_internalise.internalize_text(tagged_text, 'lemma')
    merged_pages = clara_merge_glossed_and_tagged.merge_glossed_and_tagged(glossed_pages, tagged_pages)
    prettyprint_internalised_text(merged_pages)

def test_create_and_annotate_story(id, l2_language, l1_language):
    story_data = clara_utils.read_json_file(test_stories_file)
    if not story_data:
        return
    if id in story_data:
        clara_utils.print_and_flush(f'*** id "{id}" already exists in story file')
        return
    story_data[id] = { 'l1_language': l1_language,
                       'l2_language': l2_language }
    clara_utils.write_json_to_file_plain_utf8(story_data, test_stories_file)
    
    StartTime = time.time()
    clara_utils.print_and_flush(f'\n+++++++++++++++++++++++++++++++++++++++++\n')
    test_create_story(id)
    clara_utils.print_and_flush(f'\n+++++++++++++++++++++++++++++++++++++++++\n')
    test_annotate_story(id, 'segment')
    clara_utils.print_and_flush(f'\n+++++++++++++++++++++++++++++++++++++++++\n')
    test_annotate_story(id, 'gloss')
    clara_utils.print_and_flush(f'\n+++++++++++++++++++++++++++++++++++++++++\n')
    test_annotate_story(id, 'lemma')
    clara_utils.print_and_flush(f'\n+++++++++++++++++++++++++++++++++++++++++\n')
    ElapsedTime = ( time.time() - StartTime ) / 60.0
    clara_utils.print_and_flush(f'--- All ChatGPT processing completed ({ElapsedTime:.1f} mins)')

def test_chatgpt4_annotate_story(id):
    story_data = clara_utils.read_json_file(test_stories_file)
    if not id in story_data:
        clara_utils.print_and_flush(f'*** id "{id}" not found in story file')
        return

    StartTime = time.time()
    clara_utils.print_and_flush(f'\n+++++++++++++++++++++++++++++++++++++++++\n')
    test_annotate_story(id, 'segment')
    clara_utils.print_and_flush(f'\n+++++++++++++++++++++++++++++++++++++++++\n')
    test_annotate_story(id, 'gloss')
    clara_utils.print_and_flush(f'\n+++++++++++++++++++++++++++++++++++++++++\n')
    test_annotate_story(id, 'lemma')
    clara_utils.print_and_flush(f'\n+++++++++++++++++++++++++++++++++++++++++\n')
    ElapsedTime = ( time.time() - StartTime ) / 60.0
    clara_utils.print_and_flush(f'--- All ChatGPT processing completed ({ElapsedTime:.1f} mins)')

def test_create_story(id):
    story_data = clara_utils.read_json_file(test_stories_file)
    if not story_data:
        return
    if not id in story_data:
        clara_utils.print_and_flush(f'*** Error: unknown id {id}')
        return
    if not 'l2_language' in story_data[id]:
        clara_utils.print_and_flush(f'*** Error: l2_language not defined for {id}')
        return
    l2_language = story_data[id]['l2_language']
    clara_utils.print_and_flush(f"Write text for story '{id}' ({l2_language.capitalize()} language)\n")

    story, api_calls = clara_create_story.generate_story(l2_language)
    store_story_text(id, 'plain', story)
    clara_utils.print_and_flush(f"========================================\nStory:\n\n{story}")

def test_annotate_story(id, annotation_type):
    valid_annotation_types = ( 'segment', 'gloss', 'lemma' )
    if not annotation_type in valid_annotation_types:
        clara_utils.print_and_flush(f'*** Error: unknown annotation type "{annotation_type}". Needs to be one of {valid_annotation_types}')
        return
    story_data = clara_utils.read_json_file(test_stories_file)
    if not story_data:
        return
    if not id in story_data:
        clara_utils.print_and_flush(f'*** Error: unknown id {id}')
        return
    ( l1_language, l2_language ) = ( story_data[id]['l1_language'], story_data[id]['l2_language'] )
    
    clara_utils.print_and_flush(f"Test {id}")    
    if annotation_type == 'segment':
        text = story_data[id]['plain']
        clara_utils.print_and_flush(f"Plain text: '{text}'")
        annotated_text, api_calls = clara_create_annotations.generate_segmented_version(text, l2_language)
        store_story_text(id, 'segmented', annotated_text)
    elif annotation_type == 'gloss':
        text = story_data[id]['segmented']
        clara_utils.print_and_flush(f"Segmented text: '{text}'")
        annotated_text, api_calls = clara_create_annotations.generate_glossed_version(text, l1_language, l2_language)
        store_story_text(id, 'glossed', annotated_text)
    elif annotation_type == 'lemma':
        text = story_data[id]['segmented']
        clara_utils.print_and_flush(f"Segmented text: '{text}'")
        annotated_text, api_calls = clara_create_annotations.generate_tagged_version(text, l2_language)
        store_story_text(id, 'tagged', annotated_text)
        
    clara_utils.print_and_flush(f"========================================\nAnnotated text:'{annotated_text}'")

def test_merge_story(id):
    merged_pages = get_internalised_story(id)
    if merged_pages == None:
        return
    prettyprint_internalised_text(merged_pages)

def test_tts_and_concordance_annotate(id):
    text_object = get_internalised_and_annotated_story(id)
    if not text_object:
        return
    prettyprint_internalised_text(text_object)

def test_render(id, self_contained=False):
    text_object = get_internalised_and_annotated_story(id)
    if not text_object:
        return
    # Create a StaticHTMLRenderer instance
    renderer = StaticHTMLRenderer(id)
    # Render the text as an optionally self-contained directory of HTML pages
    renderer.render_text(text_object, self_contained=self_contained)

def get_internalised_and_annotated_story(id):
    text_object = get_internalised_story(id)
    if text_object == None:
        return None
    l2_language = text_object.l2_language
    audio_annotator = clara_audio_annotator.AudioAnnotator(l2_language)
    audio_annotator.annotate_text(text_object)
    concordance_annotator = clara_concordance_annotator.ConcordanceAnnotator()
    concordance_annotator.annotate_text(text_object)
    return text_object

def get_internalised_story(id):
    story_data = clara_utils.read_json_file(test_stories_file)
    if not story_data:
        return None
    if not id in story_data:
        clara_utils.print_and_flush(f'*** Error: unknown id {id}')
        return None
    ( l1_language, l2_language ) = ( story_data[id]['l1_language'], story_data[id]['l2_language'] )
    ( glossed_text, tagged_text ) = ( story_data[id]['glossed'], story_data[id]['tagged'] )
    clara_utils.print_and_flush(f"Test {id}")
    clara_utils.print_and_flush(f"Glossed text: '{glossed_text}'")
    clara_utils.print_and_flush(f" Tagged text: '{tagged_text}'\n")

    glossed_pages = clara_internalise.internalize_text(glossed_text, l2_language, l1_language, 'gloss')
    tagged_pages = clara_internalise.internalize_text(tagged_text, l2_language, l1_language, 'lemma')
    merged_pages = clara_merge_glossed_and_tagged.merge_glossed_and_tagged(glossed_pages, tagged_pages)
    return merged_pages

def test_internalisation_story(id, type):
    story_data = clara_utils.read_json_file(test_stories_file)
    if not story_data:
        return
    if not id in story_data:
        clara_utils.print_and_flush(f'*** Error: unknown id {id}')
        return
    if not type in ( 'segmented', 'glossed', 'tagged' ):
        clara_utils.print_and_flush(f'*** Error: unknown type of operation {type}')
        return
    test_input = story_data[id][type]
    clara_utils.print_and_flush(f"Test {id}: '{test_input}' ({type})\n")

    internalized_pages = clara_internalise.internalize_text(test_input, type)
    prettyprint_internalised_text(internalized_pages)

def get_story_text(id, type):
    if not type in ( 'plain', 'segmented', 'glossed', 'tagged' ):
        clara_utils.print_and_flush(f'*** Error: unknown type of data {type}')
        return False
    story_data = clara_utils.read_json_file(test_stories_file)
    if not id in story_data:
        clara_utils.print_and_flush(f'*** Error: unknown id {id}')
        return False
    this_story_data = story_data[id]
    if not type in this_story_data:
        clara_utils.print_and_flush(f'*** Error: no "{type}" data for {id}')
        return False
    return this_story_data[type]

def store_story_text(id, type, text):
    if not isinstance(text, str):
        clara_utils.print_and_flush(f'*** Error: argument "{text}" is not a text string')
        return False
    if not type in ( 'plain', 'segmented', 'glossed', 'tagged' ):
        clara_utils.print_and_flush(f'*** Error: unknown type of data {type}')
        return False
    story_data = clara_utils.read_json_file(test_stories_file)
    if not id in story_data:
        clara_utils.print_and_flush(f'*** Error: unknown id {id}')
        return False
    story_data[id][type] = text
    clara_utils.write_json_to_file_plain_utf8(story_data, test_stories_file)
    clara_utils.print_and_flush(f'--- Stored text in "{type}" field of "{id}"')
  
def prettyprint_internalised_text(internalized_text):
    clara_utils.print_and_flush(f"Text Language (L2): {internalized_text.l2_language}, Annotation Language (L1): {internalized_text.l1_language}\n")
    
    for page_number, page in enumerate(internalized_text.pages, start=1):
        clara_utils.print_and_flush(f"  Page {page_number}:")
        
        for segment_number, segment in enumerate(page.segments, start=1):
            clara_utils.print_and_flush(f"    Segment {segment_number}:")

            for element_number, element in enumerate(segment.content_elements, start=1):
                content_to_print = f"'{element.content}'" if isinstance(element.content, (str)) else f"{element.content}"
                clara_utils.print_and_flush(f"      Element {element_number}: Type: '{element.type}', Content: {content_to_print}, Annotations: {element.annotations}")
        
        clara_utils.print_and_flush("===")
