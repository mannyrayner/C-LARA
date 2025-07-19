from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404

from .models import CLARAProject
from .utils import user_has_a_project_role, get_task_updates

@login_required
@user_has_a_project_role
def save_page_texts_multiple_status(request, project_id, report_id):
    messages = get_task_updates(report_id)
    print(f'{len(messages)} messages received')
    if 'error' in messages:
        status = 'error'
    elif 'finished' in messages:
        status = 'finished'  
    else:
        status = 'unknown'    
    return JsonResponse({'messages': messages, 'status': status})

@login_required
@user_has_a_project_role
def save_page_texts_multiple_monitor(request, project_id, report_id):
    project = get_object_or_404(CLARAProject, pk=project_id)

    return render(request, 'clara_app/save_page_texts_multiple_monitor.html',
                  {'project_id': project_id, 'project': project, 'report_id': report_id})
