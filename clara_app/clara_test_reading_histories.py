
from .clara_main import CLARAProjectInternal

from .clara_reading_histories import ReadingHistoryInternal

from .clara_utils import post_task_update, absolute_file_name

import traceback

def test(test_id):
    if test_id == 1:
        mary_project = CLARAProjectInternal.from_directory('$CLARA/clara_content/Mary_had_a_little_lamb_37')
        jack_project = CLARAProjectInternal.from_directory('$CLARA/clara_content/Jack_and_Jill_114')
        component_projects = [ mary_project, jack_project ]
        reading_history_project = CLARAProjectInternal('Reading_history_test_1000', 'english', 'french')
        project_id = '1000'

        reading_history = ReadingHistoryInternal(project_id, reading_history_project, component_projects)
        reading_history.create_combined_text_object()
        reading_history.render_combined_text_object()
    else:
        print(f'*** Unknown ID: {test_id}')

        
        
        
