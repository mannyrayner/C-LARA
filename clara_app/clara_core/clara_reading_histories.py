
from .clara_classes import Text, Page, Segment, ContentElement, ReadingHistoryError

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
    def create_combined_text_object(self, callback=None):
        text_objects = []
        for clara_project in self.component_clara_project_internals:
            text_object = clara_project.get_saved_internalised_and_annotated_text()
            if not text_object:
                post_task_update(callback, f"*** Error: no internalised text found for '{clara_project.id}'")
                raise ReadingHistoryError
            else:
                text_objects.append(text_object)
        try:
            combined_text_object = combine_text_objects(text_objects)
            self.clara_project_internal.save_internalised_and_annotated_text(combined_text_object)
        except Exception as e:
            post_task_update(callback, f'*** Error when trying to create combined text for reading history')
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise ReadingHistoryError

    # Extract the saved annotated text object from the clara_project_internal and the new component project,
    # glue them together, and save the result in the clara_project_internal
    def add_component_project_and_create_combined_text_object(self, new_component_project):
        try:
            old_combined_object = clara_project_internal.get_saved_internalised_and_annotated_text()
            new_text_object = new_component_project..get_saved_internalised_and_annotated_text()
            new_combined_text_object = combine_text_objects([ old_combined_object, new_text_object ])
            self.clara_project_internal.save_internalised_and_annotated_text(new_combined_text_object)
        except Exception as e:
            post_task_update(callback, f'*** Error when trying to update combined text for reading history')
            error_message = f'"{str(e)}"\n{traceback.format_exc()}'
            post_task_update(callback, error_message)
            raise ReadingHistoryError

    # Extract the saved annotated text object from the clara_project_internal and render it
    def render_combined_text_object(self):
        return


def combine_text_objects(text_objects):
    return

