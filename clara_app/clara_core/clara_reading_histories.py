"""
Implements the ReadingHistoryInternal class. The purpose of this class is to combine together 
two or more CLARAProjectInternal objects into a single virtual project which represents their concatenation.
The implementation uses the pickled representations of the internalised text created when performing the
render_text operation in CLARAProjectInternal.

A ReadingHistoryInternal has the following instance variables, supplied in the constructor:

- project_id.

A number representing the id of a Django-level CLARAproject. The ReadingHistory will be rendered
as though it were the text associated with this project.

- clara_project_internal.

A CLARAProjectInternal object which acts as though it were the CLARAProjectInternal
associated with the Django-level CLARAproject.

- component_clara_project_internals.

A list of component CLARAProjectInternal objects.

Methods:

- create_combined_text_object(self, phonetic=False, callback=None)

Extract the saved annotated text object from each of the component_clara_project_internals,
glue them together, and save the result in the clara_project_internal

- add_component_project_and_create_combined_text_object(self, new_component_project, phonetic=False, callback=None)

Extract the saved annotated text object from the clara_project_internal and the new component project,
glue them together, and save the result in the clara_project_internal.

- render_combined_text_object(self, phonetic=False, callback=None)

Extract the saved annotated text object from the clara_project_internal and render it into the directory
associated with project_id.
"""

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
        post_task_update(callback, f"--- Adding '{new_component_project.id}' (phonetic={phonetic}) to reading history")
        try:
            # If we perform this operation for both the normal and the phonetic versions,
            # we only want to add the new project once to self.component_clara_project_internals
            if not new_component_project in self.component_clara_project_internals:
                self.component_clara_project_internals.append(new_component_project)
            new_text_object = new_component_project.get_saved_internalised_and_annotated_text(phonetic=phonetic)
            if not new_text_object:
                post_task_update(callback, f"*** Error: no internalised text (phonetic={phonetic}) found for project '{new_component_project.id}'")
                raise ReadingHistoryError
            combined_text_object = self.clara_project_internal.get_saved_internalised_and_annotated_text(phonetic=phonetic)
            if combined_text_object:
                # There is an existing reading history text object, combine with the new one
                new_combined_text_object = combine_text_objects([ combined_text_object, new_text_object ])
            else:
                # There is no existing reading history text object, the new one becomes the initial reading history text object 
                new_combined_text_object = new_text_object
            self.clara_project_internal.save_internalised_and_annotated_text(new_combined_text_object, phonetic=phonetic)
        except Exception as e:
            post_task_update(callback, f'*** Error when trying to update combined text for reading history')
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise ReadingHistoryError

    # Extract the saved annotated text object from the clara_project_internal and render it
    def render_combined_text_object(self, phonetic=False, callback=None):
        post_task_update(callback, f"--- Rendering reading history (phonetic={phonetic})")
        try:
            text_object = self.clara_project_internal.get_saved_internalised_and_annotated_text(phonetic=phonetic)
            if not text_object:
                post_task_update(callback, f'*** Unable to render reading history (phonetic={phonetic}), no text found')
                raise ReadingHistoryError
            normal_html_exists = self.clara_project_internal.get_saved_internalised_and_annotated_text(phonetic=True)
            phonetic_html_exists = self.clara_project_internal.get_saved_internalised_and_annotated_text(phonetic=False)
            renderer = StaticHTMLRenderer(self.project_id, self.clara_project_internal.id, self.clara_project_internal.l2_language,
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

    def delete_rendered_text(self, phonetic=False, callback=None):
        renderer = StaticHTMLRenderer(self.project_id, self.clara_project_internal.id, phonetic=phonetic)
        renderer.delete_rendered_html_directory()

    def rendered_html_exists(phonetic=False, callback=None):
        if phonetic == False:
            return self.clara_project_internal.rendered_html_exists(self, self.project_id)
        else:
            return self.clara_project_internal.rendered_phonetic_html_exists(self, self.project_id)

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
