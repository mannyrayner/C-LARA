
from .clara_renderer import StaticHTMLRenderer
from .clara_classes import Text, ReadingHistoryError
from .clara_utils import post_task_update

import traceback

class ReadingHistoryInternal:

    # Initialise
    def __init__(self, project_id, clara_project_internal, component_clara_project_internals):
        # The CLARAproject id that this reading history corresponds to, for creating directories
        self.project_id = project_id
        # The CLARAprojectInternal that this reading history corresponds to, for creating directories
        self.clara_project_internal = clara_project_internal
        # The list of component CLARAProjectInternal objects
        self.component_clara_project_internals = component_clara_project_internals

    # Extract the saved annotated text object from each of the component_clara_project_internals,
    # glue them together, and save the result in the clara_project_internal
    def create_combined_text_object(self, phonetic=False, callback=None):
        text_objects = []
        for clara_project in self.component_clara_project_internals:
            text_object = clara_project.get_saved_internalised_and_annotated_text(phonetic=phonetic)
            if not text_object:
                post_task_update(callback, f"*** Error: no internalised text (phonetic={phonetic}) found for '{clara_project.id}'")
                raise ReadingHistoryError
            else:
                text_objects.append(text_object)
        try:
            combined_text_object = combine_text_objects(text_objects, phonetic=phonetic, callback=callback)
            self.clara_project_internal.save_internalised_and_annotated_text(combined_text_object, phonetic=phonetic)
        except Exception as e:
            post_task_update(callback, f'*** Error when trying to create combined text (phonetic={phonetic}) for reading history')
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise ReadingHistoryError

    # Extract the saved annotated text object from the clara_project_internal and the new component project,
    # glue them together, and save the result in the clara_project_internal
    def add_component_project_and_create_combined_text_object(self, new_component_project, phonetic=False, callback=None):
        try:
            old_combined_object = clara_project_internal.get_saved_internalised_and_annotated_text(phonetic=phonetic)
            new_text_object = new_component_project.get_saved_internalised_and_annotated_text(phonetic=phonetic)
            new_combined_text_object = combine_text_objects([ old_combined_object, new_text_object ])
            self.clara_project_internal.save_internalised_and_annotated_text(new_combined_text_object, phonetic=phonetic)
        except Exception as e:
            post_task_update(callback, f'*** Error when trying to update combined text for reading history')
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise ReadingHistoryError

    # Extract the saved annotated text object from the clara_project_internal and render it
    def render_combined_text_object(self, phonetic=False, callback=None):
        try:
            text_object = self.clara_project_internal.get_saved_internalised_and_annotated_text(phonetic=phonetic)
            if not text_object:
                post_task_update(callback, f'*** Unable to render reading history (phonetic={phonetic}), no text found')
                raise ReadingHistoryError
            normal_html_exists = self.clara_project_internal.get_saved_internalised_and_annotated_text(phonetic=True)
            phonetic_html_exists = self.clara_project_internal.get_saved_internalised_and_annotated_text(phonetic=False)
            renderer = StaticHTMLRenderer(self.project_id, self.clara_project_internal.id,
                                          phonetic=phonetic,
                                          # Try to find a way to get format_preferences if possible
                                          format_preferences_info=None,
                                          normal_html_exists=normal_html_exists, phonetic_html_exists=phonetic_html_exists,
                                          callback=callback)
            post_task_update(callback, f"--- Start creating pages (phonetic={phonetic})")
            renderer.render_text(text_object, self_contained=True, callback=callback)
        except Exception as e:
            post_task_update(callback, f'*** Error when trying to render combined text for reading history')
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise ReadingHistoryError


def combine_text_objects(text_objects, phonetic=False, callback=None):
    if not text_objects:
        post_task_update(callback, f'*** Error when trying to create reading history, empty list of texts')
        raise ReadingHistoryError

    l1_language = text_objects[0].l1_language
    l2_language = text_objects[0].l2_language
    pages = []
    concordance = {}

    for new_text_object in text_objects:
        new_pages = new_text_object.pages
        new_concordance = new_text_object.annotations['concordance'] if 'concordance' in new_text_object.annotations else {}
        pages += new_pages
        add_to_concordance(concordance, new_concordance)
    
    return Text(pages, l2_language, l1_language, annotations={'concordance': concordance} )

# The concordance is a lemma-indexed dict, where the values are dicts with key ( 'segments', 'frequency' )
def add_to_concordance(concordance, new_concordance):
    for lemma in new_concordance:
        if not lemma in concordance:
            concordance[lemma] = new_concordance[lemma]
        else:
            entry = concordance[lemma]
            entry_to_add = new_concordance[lemma]
            entry['segments'] += entry_to_add['segments']
            entry['frequency'] += entry_to_add['frequency']
