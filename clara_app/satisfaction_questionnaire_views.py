from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.db.models import Count, Avg, Q
from django.utils import timezone
from .models import SatisfactionQuestionnaire
from .models import CLARAProject
from django.contrib.auth.models import User
from .forms import SatisfactionQuestionnaireForm
from .clara_utils import get_config
import logging
import pandas as pd

config = get_config()
logger = logging.getLogger(__name__)

# Show a satisfaction questionnaire
@login_required
def satisfaction_questionnaire(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    user = request.user

    # Try to get an existing questionnaire response for this project and user
    try:
        existing_questionnaire = SatisfactionQuestionnaire.objects.get(project=project, user=user)
    except SatisfactionQuestionnaire.DoesNotExist:
        existing_questionnaire = None
    
    if request.method == 'POST':
        if existing_questionnaire:
            # If an existing questionnaire is found, update it
            form = SatisfactionQuestionnaireForm(request.POST, instance=existing_questionnaire)
        else:
            # No existing questionnaire, so create a new instance
            form = SatisfactionQuestionnaireForm(request.POST)
            
        if form.is_valid():
            questionnaire = form.save(commit=False)
            questionnaire.project = project
            questionnaire.user = request.user 
            questionnaire.save()
            messages.success(request, 'Thank you for your feedback!')
            return redirect('project_detail', project_id=project.id)
    else:
        if existing_questionnaire:
            form = SatisfactionQuestionnaireForm(instance=existing_questionnaire)
        else:
            form = SatisfactionQuestionnaireForm()

    return render(request, 'clara_app/satisfaction_questionnaire.html', {'form': form, 'project': project})

# Just show the questionnaire without allowing any editing
@login_required
def show_questionnaire(request, project_id, user_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    user = get_object_or_404(User, pk=user_id)
    
    # Retrieve the existing questionnaire response for this project and user
    questionnaire = get_object_or_404(SatisfactionQuestionnaire, project=project, user=user)

    return render(request, 'clara_app/show_questionnaire.html', {'questionnaire': questionnaire, 'project': project})

@login_required
@user_passes_test(lambda u: u.userprofile.is_questionnaire_reviewer)
def manage_questionnaires(request):
    if request.method == 'POST':
        if 'export' in request.POST:
            # Convert questionnaire data to a pandas DataFrame
            qs = SatisfactionQuestionnaire.objects.all().values()
            
            df = pd.DataFrame(qs)
            
            # Convert timezone-aware 'created_at' to timezone-naive
            df['created_at'] = df['created_at'].apply(lambda x: timezone.make_naive(x) if x is not None else x)

            # Convert DataFrame to Excel file
            response = HttpResponse(content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = 'attachment; filename="questionnaires.xlsx"'

            with pd.ExcelWriter(response, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)

            return response
        elif 'delete' in request.POST:
            # Handle the deletion of selected questionnaire responses
            selected_ids = request.POST.getlist('selected_responses')
            if selected_ids:
                SatisfactionQuestionnaire.objects.filter(id__in=selected_ids).delete()
                messages.success(request, "Selected responses have been deleted.")
                return redirect('manage_questionnaires')

    questionnaires = SatisfactionQuestionnaire.objects.all()
    return render(request, 'clara_app/manage_questionnaires.html', {'questionnaires': questionnaires})

def aggregated_questionnaire_results(request):
    # Aggregate data for each Likert scale question
    ratings = SatisfactionQuestionnaire.objects.aggregate(
        grammar_correctness_avg=Avg('grammar_correctness', filter=Q(grammar_correctness__gt=0)),
        vocabulary_appropriateness_avg=Avg('vocabulary_appropriateness', filter=Q(vocabulary_appropriateness__gt=0)),
        style_appropriateness_avg=Avg('style_appropriateness', filter=Q(style_appropriateness__gt=0)),
        content_appropriateness_avg=Avg('content_appropriateness', filter=Q(content_appropriateness__gt=0)),
        cultural_elements_avg=Avg('cultural_elements', filter=Q(cultural_elements__gt=0)),
        text_engagement_avg=Avg('text_engagement', filter=Q(text_engagement__gt=0)),
        image_match_avg=Avg('image_match', filter=Q(image_match__gt=0)),
        count=Count('id')
    )
    
    # For choices questions (time spent, shared intent, etc.), it might be useful to calculate the distribution
    # For example, how many selected each time range for correction_time_text
    correction_time_text_distribution = SatisfactionQuestionnaire.objects.values('correction_time_text').annotate(total=Count('correction_time_text')).order_by('correction_time_text')
    correction_time_annotations_distribution = SatisfactionQuestionnaire.objects.values('correction_time_annotations').annotate(total=Count('correction_time_annotations')).order_by('correction_time_annotations')
    image_editing_time_distribution = SatisfactionQuestionnaire.objects.values('image_editing_time').annotate(total=Count('image_editing_time')).order_by('image_editing_time')

    generated_by_ai_distribution = SatisfactionQuestionnaire.objects.values('generated_by_ai').annotate(total=Count('generated_by_ai')).order_by('generated_by_ai')
    shared_intent_distribution = SatisfactionQuestionnaire.objects.values('shared_intent').annotate(total=Count('shared_intent')).order_by('shared_intent')
    text_type_distribution = SatisfactionQuestionnaire.objects.values('text_type').annotate(total=Count('text_type')).order_by('text_type')
    
    # For open-ended questions, fetching the latest 50 responses for illustration
    purpose_texts = SatisfactionQuestionnaire.objects.values_list('purpose_text', flat=True).order_by('-created_at')[:50]
    functionality_suggestions = SatisfactionQuestionnaire.objects.values_list('functionality_suggestion', flat=True).order_by('-created_at')[:50]
    ui_improvement_suggestions = SatisfactionQuestionnaire.objects.values_list('ui_improvement_suggestion', flat=True).order_by('-created_at')[:50]

    context = {
        'ratings': ratings,
        'correction_time_text_distribution': correction_time_text_distribution,
        'correction_time_annotations_distribution': correction_time_annotations_distribution,
        'image_editing_time_distribution': image_editing_time_distribution,
        'generated_by_ai_distribution': generated_by_ai_distribution,
        'shared_intent_distribution': shared_intent_distribution,
        'text_type_distribution': text_type_distribution,
        'purpose_texts': list(purpose_texts),
        'functionality_suggestions': list(functionality_suggestions),
        'ui_improvement_suggestions': list(ui_improvement_suggestions),
    }

    return render(request, 'clara_app/aggregated_questionnaire_results.html', context)

