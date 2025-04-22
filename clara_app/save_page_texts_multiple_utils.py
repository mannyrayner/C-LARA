
from .utils import store_api_calls
from .clara_utils import post_task_update

# Async function
def save_page_texts_multiple(project, clara_project_internal, types_and_texts, username, config_info={}, callback=None):
    try:
        api_calls = clara_project_internal.save_page_texts_multiple(types_and_texts, user=username, can_use_ai=True, config_info=config_info, callback=callback)
        store_api_calls(api_calls, project, project.user, 'correct')
        post_task_update(callback, f'--- Corrected texts')
        post_task_update(callback, f"finished")

    except Exception as e:
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")
