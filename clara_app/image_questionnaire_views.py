from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Avg, Q
from django.db.models.functions import Lower
from django.http import HttpResponse

from .models import CLARAProject
from .models import ImageQuestionnaireResponse
from .forms import ProjectSearchForm

from .clara_main import CLARAProjectInternal
from .clara_coherent_images_utils import project_pathname
from .clara_coherent_images_utils import read_project_json_file, project_pathname
from .clara_images_utils import numbered_page_list_for_coherent_images
from .clara_utils import get_config, file_exists, read_txt_file, questionnaire_output_dir_for_project_id
from .utils import localise, FALLBACK_LANG 
from collections import defaultdict
import logging
import pprint
import csv
import traceback

config = get_config()
logger = logging.getLogger(__name__)

IMAGE_QUESTIONNAIRE_QUESTIONS = [
    {
        "id": 1,
        "text": "How well does the image correspond to the page text?",
    },
    {
        "id": 2,
        "text": "How consistent is the style of the image with the overall style?",
    },
    {
        "id": 3,
        "text": "How consistent is the appearance of elements in the image with their previous appearance?",
    },
    {
        "id": 4,
        "text": "Is the image appropriate to the relevant culture?",
    },
    {
        "id": 5,
        "text": "How visually appealing do you find the image?",
    },
    {
        "id": 6,
        "text": "How much do you like the text itself?",
    },
    {
        "id": 7,
        "text": "How useful do you find the glosses and translations?",
    }
]

UI_LANG_KEY = "ui_lang"

def get_ui_lang(request):
    # priority:  ?ui=XX  →  session  →  english
    lang = request.GET.get("ui")
    if not lang:
        lang = request.session.get(UI_LANG_KEY)
    if not lang:
        lang = "english"
    request.session["ui_lang"] = lang      # remember for next page
    return lang

@login_required
def image_questionnaire_project_list(request):
    """
    Lists all projects that have an image questionnaire, applying optional search/filter criteria.
    Each project entry includes a link to start or continue the questionnaire for that project.
    """

    search_form = ProjectSearchForm(request.GET or None)
    query = Q(has_image_questionnaire=True)

    if search_form.is_valid():
        title = search_form.cleaned_data.get('title')
        l2 = search_form.cleaned_data.get('l2')
        l1 = search_form.cleaned_data.get('l1')

        if title:
            query &= Q(title__icontains=title)
        if l2:
            query &= Q(l2__icontains=l2)
        if l1:
            query &= Q(l1__icontains=l1)

    # Retrieve matching projects, order by title (case-insensitive)
    projects = CLARAProject.objects.filter(query).order_by(Lower('title'))

    return render(request, 'clara_app/image_questionnaire_project_list.html', {
        'search_form': search_form,
        'projects': projects,
    })

@login_required
def image_only_questionnaire_start(request, project_id):
    request.session['include_text_in_image_and_text_questionnare'] = False
    
    return redirect('image_questionnaire_start', project_id=project_id)

@login_required
def image_and_text_questionnaire_start(request, project_id):
    request.session['include_text_in_image_and_text_questionnare'] = True
    
    return redirect('image_questionnaire_start', project_id=project_id)

@login_required
def image_questionnaire_start(request, project_id):
    """
    Entry point for the image questionnaire. 
    Retrieves the story pages, stores them in session (or you could do it in memory),
    then redirects the user to the first page.
    """
    project = get_object_or_404(CLARAProject, pk=project_id)

    # Make sure the project actually has a questionnaire
    if not project.has_image_questionnaire:
        messages.error(request, 'This project does not have an image questionnaire enabled.')
        return redirect('clara_home_page')

    # Access the internal structure
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    project_dir = clara_project_internal.coherent_images_v2_project_dir

    # Create the for-questionnaire rendered text pages
    try:
        clara_project_internal.render_text_for_questionnaire(project_id)
    except Exception as e:
        messages.error(request, f"Error when trying to create rendered text pages for questionnaire")
        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
        return redirect('clara_home_page')

    # Read the story data. Regenerate first in case it has changed.
    # We should have saved everything and have translations, so we can get the story data from the project
    try:
        numbered_page_list = numbered_page_list_for_coherent_images(project, clara_project_internal)
        #pprint.pprint(numbered_page_list)
        clara_project_internal.set_story_data_from_numbered_page_list_v2(numbered_page_list)
    except Exception as e:
        messages.error(request, f"Error when trying to update story data")
        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
        return redirect('clara_home_page')
    story_data = read_project_json_file(project_dir, 'story.json') or []

    # We’ll build a global frequency map of elements -> how many pages they appear in
    element_page_count = defaultdict(int)
    
    # Filter out pages that don't have images, if you only want those
    pages_with_images = []
    for page in story_data:
        page_number = page.get('page_number')
        rel_img_path = f'pages/page{page_number}/image.jpg'
        if file_exists(project_pathname(project_dir, rel_img_path)):
            pages_with_images.append(page)

            # read relevant elements for that page
            relevant_info_path = f'pages/page{page_number}/relevant_pages_and_elements.json'
            if file_exists(project_pathname(project_dir, relevant_info_path)):
                relevant_info = read_project_json_file(project_dir, relevant_info_path)
                relevant_elems = relevant_info.get('relevant_elements', [])
                # Count how many pages each element appears in
                # We can track if we haven't incremented for this page yet, but a simpler way is to do
                # sets to avoid multiple increments for the same page.
                for elem in set(relevant_elems):
                    element_page_count[elem] += 1

    if not pages_with_images:
        # No images => no questionnaire needed
        messages.error(request, 'This project does not have any images to evaluate.')
        return redirect('clara_home_page')

    # now see if any element appears in a page
    # that indicates there's a chance of continuity
    has_any_relevant_elements = any(count > 0 for count in element_page_count.values())

    # Store pages in session, plus the boolean
    request.session['image_questionnaire_pages'] = pages_with_images
    request.session['has_any_relevant_elements'] = has_any_relevant_elements
    
    return redirect('image_questionnaire_item', project_id=project.id, index=0)


@login_required
def image_questionnaire_item(request, project_id, index):
    """
    Shows a single page's image, text, and the relevant questions.
    Handles form submission for each question, then goes forward or backward.
    """
    project = get_object_or_404(CLARAProject, pk=project_id)

    if not project.has_image_questionnaire:
        messages.error(request, 'This project does not have an image questionnaire enabled.')
        return redirect('clara_home_page')

    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    project_dir = clara_project_internal.coherent_images_v2_project_dir

    # Retrieve info from session
    include_text_questions = request.session.get('include_text_in_image_and_text_questionnare', False)
    pages_with_images = request.session.get('image_questionnaire_pages', [])
    has_any_relevant_elements = request.session.get('has_any_relevant_elements', False)

    lang = get_ui_lang(request)
    bundle = "image_questionnaire"
    bundle2 = "image_questionnaire2"

    ui = { key: localise(bundle2, key, lang)
            for key in ("title", "page", "page_image_and_text", "previous_relevant_image",
                        "questions_1_equals_worst", "not_clear_which_images_are_relevant",
                        "next_btn", "prev_btn", "submit_btn")}

    #pprint.pprint(ui)
    
    if not pages_with_images or index < 0 or index >= len(pages_with_images):
        # Index out of range: go to a summary or fallback
        return redirect('image_questionnaire_summary', project_id=project.id)

    current_page = pages_with_images[index]
    page_number = current_page.get('page_number')
    page_text = current_page.get('text', '')
    translated_page_text = current_page.get('translated_text', '')
    relative_page_image_path = f'pages/page{page_number}/image.jpg'

    questionnaire_html_file = f'{questionnaire_output_dir_for_project_id(project_id)}/page_{page_number}.html'
    html_snippet = read_txt_file(questionnaire_html_file) if file_exists(questionnaire_html_file) else ''
    
    # Decide which questions to show
    # For question #3, we see if there's a relevant previous page
    # that shares an element with the current page
    relevant_elements_current = _get_relevant_elements(project_dir, page_number)
    has_prev_relevant_page, prev_page_num = _find_previous_relevant_page(
        pages_with_images, index, project_dir, relevant_elements_current
    )

    questions_to_show = []
    for q in IMAGE_QUESTIONNAIRE_QUESTIONS:
        if q["id"] == 3:
            # Show Q3 only if:
            #   (a) There's at least one recurring element in the entire text
            #   (b) We are not on the first page
            if has_any_relevant_elements and index > 0:
                questions_to_show.append(q)
        elif q["id"] in [6, 7]:
            # Show Q6 and Q7 only if we are including the text questions
            if include_text_questions:
                questions_to_show.append(q)
        else:
            questions_to_show.append(q)

    if request.method == 'POST':
        # Process the user's Likert-scale answers
        for q in questions_to_show:
            q_key = f"q_{q['id']}"
            c_key = f"c_{q['id']}"

            rating_str = request.POST.get(q_key)
            comment = request.POST.get(c_key, '').strip()

            if rating_str:
                # Save or update the user’s response
                rating = int(rating_str)
                ImageQuestionnaireResponse.objects.update_or_create(
                    project=project,
                    user=request.user,
                    page_number=page_number,
                    question_id=q["id"],
                    defaults={"rating": rating, "comment": comment},
                )

        if "previous" in request.POST:
            return redirect('image_questionnaire_item', project_id=project.id, index=index - 1)
        else:
            # Next button or default
            return redirect('image_questionnaire_item', project_id=project.id, index=index + 1)

    # GET request: Load any existing answers for pre-fill
    existing_answers_raw = ImageQuestionnaireResponse.objects.filter(
    project=project,
    user=request.user,
    page_number=page_number
    )
    answers_by_id = {}
    
    for resp in existing_answers_raw:
        answers_by_id[resp.question_id] = (resp.rating, resp.comment)

    # Then build a structure that’s easy to iterate over in the template:
    question_data_list = []
    for q in questions_to_show:
        q_id = q["id"]
        key = str(q_id)
        text = localise(bundle, key, lang)    
        rating_comment = answers_by_id.get(q_id, (None, ""))
        question_data_list.append({
            "id": q_id,
            "text": text,
            "rating": str(rating_comment[0]),
            "comment": rating_comment[1],
        })

    # If we want to show the previous image for question #3, fetch its path
    previous_image_relpath = None
    if has_prev_relevant_page and prev_page_num is not None:
        previous_image_relpath = f'pages/page{prev_page_num}/image.jpg'
        # You can pass this to the template to display side-by-side

    context = {
        "project": project,
        "ui_lang": lang,
        "ui": ui,
        "index": index,
        "total_pages": len(pages_with_images),
        "page_number": page_number,
        "page_text": page_text,
        "translated_page_text": translated_page_text,
        "relative_image_path": relative_page_image_path,
        "html_snippet": html_snippet,
        "questions": questions_to_show,
        "question_data_list": question_data_list,
        "show_previous": index > 0,
        "show_next": index < len(pages_with_images) - 1,
        "has_prev_relevant_page": has_prev_relevant_page,
        "previous_page_number": prev_page_num,
        "previous_image_relpath": previous_image_relpath,
    }
    #pprint.pprint(context)
    return render(request, "clara_app/image_questionnaire_item.html", context)


@login_required
def image_questionnaire_summary(request, project_id):
    """
    Show a simple "thank you" and optional stats or final summary.
    """
    project = get_object_or_404(CLARAProject, pk=project_id)
    if not project.has_image_questionnaire:
        messages.error(request, 'This project does not have an image questionnaire enabled.')
        return redirect('clara_home_page')

    # Example: let’s get how many total responses the user gave
    user_responses = ImageQuestionnaireResponse.objects.filter(project=project, user=request.user)
    pages_answered = user_responses.values_list('page_number', flat=True).distinct().count()
    questions_answered = user_responses.count()

    context = {
        "project": project,
        "pages_answered": pages_answered,
        "questions_answered": questions_answered,
    }
    return render(request, "clara_app/image_questionnaire_summary.html", context)

@login_required
def image_questionnaire_all_projects_summary(request):
    """
    Presents the aggregated questionnaire results (average ratings etc.) 
    for *all* projects that have an image questionnaire enabled.
    """
    # Optionally restrict this to superusers or some special role
    # if not request.user.is_superuser:
    #     return HttpResponseForbidden("You do not have permission to view this summary.")

    # Gather all projects that have an image questionnaire
    search_form = ProjectSearchForm(request.GET or None)
    query = Q(has_image_questionnaire=True)

    if search_form.is_valid():
        title = search_form.cleaned_data.get('title')
        l2 = search_form.cleaned_data.get('l2')
        l1 = search_form.cleaned_data.get('l1')

        if title:
            query &= Q(title__icontains=title)
        if l2:
            query &= Q(l2__icontains=l2)
        if l1:
            query &= Q(l1__icontains=l1)

    projects = CLARAProject.objects.filter(query).order_by(Lower('title'))

    # Prepare a list of summary data, one entry per project
    all_project_summaries = []

    # Pre-build a quick lookup from question_id to question_text
    question_texts = {q["id"]: q["text"] for q in IMAGE_QUESTIONNAIRE_QUESTIONS}

    for proj in projects:
        # Retrieve all responses for this project
        responses = ImageQuestionnaireResponse.objects.filter(project=proj)

        if not responses.exists():
            # No responses yet, just show zeros
            all_project_summaries.append({
                "search_form": search_form,
                "project": proj,
                "distinct_pages": 0,
                "distinct_users": 0,
                "aggregated_data": [],
            })
            continue

        # Count distinct pages and users
        distinct_pages = responses.values_list("page_number", flat=True).distinct().count()
        distinct_users = responses.values_list("user_id", flat=True).distinct().count()

        # Aggregate by question: average rating and how many total responses
        agg_by_question = (
            responses
            .values("question_id")
            .annotate(avg_rating=Avg("rating"), num_responses=Count("id"))
            .order_by("question_id")
        )

        # Convert query results into a list of dicts with question text
        aggregated_data = []
        for row in agg_by_question:
            q_id = row["question_id"]
            aggregated_data.append({
                "question_id": q_id,
                "question_text": question_texts.get(q_id, f"Q{q_id}"),
                "avg_rating": row["avg_rating"],
                "num_responses": row["num_responses"],
            })

        all_project_summaries.append({
            "project": proj,
            "distinct_pages": distinct_pages,
            "distinct_users": distinct_users,
            "aggregated_data": aggregated_data,
        })

    # Pass everything to the template
    return render(request, "clara_app/image_questionnaire_all_projects_summary.html", {
        "search_form": search_form,
        "all_project_summaries": all_project_summaries,
        "request": request
    })

##@login_required
##def image_questionnaire_summary_csv(request):
##    """
##    Same filters as the HTML summary, but outputs one CSV row per
##    (project × question_id) with averaged data.
##    """
##    # --- reuse the same search form logic --------------------------
##    search_form = ProjectSearchForm(request.GET or None)
##    query = Q(has_image_questionnaire=True)
##    if search_form.is_valid():
##        for field in ("title", "l2", "l1"):
##            val = search_form.cleaned_data.get(field)
##            if val:
##                query &= Q(**{f"{field}__icontains": val})
##    projects = CLARAProject.objects.filter(query)
##
##    # --- assemble rows ---------------------------------------------
##    rows = []
##    question_texts = {q["id"]: q["text"] for q in IMAGE_QUESTIONNAIRE_QUESTIONS}
##    for proj in projects:
##        responses = ImageQuestionnaireResponse.objects.filter(project=proj)
##        if not responses.exists():
##            continue
##
##        # NEW: counts shared by all rows of this project
##        pages = responses.values_list("page_number", flat=True).distinct().count()
##        evals = responses.values_list("user_id", flat=True).distinct().count()
##        
##        agg = (
##            responses.values("question_id")
##            .annotate(avg=Avg("rating"), n=Count("id"))
##            .order_by("question_id")
##        )
##        for r in agg:
##            rows.append({
##                "project": proj.title,
##                "pages": pages,              # NEW column
##                "evaluators": evals,         # NEW column
##                "question_id": r["question_id"],
##                "question_text": question_texts.get(r["question_id"]),
##                "avg_rating": f"{r['avg']:.2f}",
##                "num_responses": r["n"],
##            })
##
##    # --- stream as CSV ---------------------------------------------
##    response = HttpResponse(content_type="text/csv")
##    response["Content-Disposition"] = "attachment; filename=image_summary.csv"
##    writer = csv.DictWriter(
##        response,
##        fieldnames=["project", "pages", "evaluators",
##                    "question_id", "question_text",
##                    "avg_rating", "num_responses"],
##    )
##    writer.writeheader()
##    writer.writerows(rows)
##    return response

@login_required
def image_questionnaire_summary_csv(request):
    """Dump every image-questionnaire rating (one row per rater × page × question)."""
    search_form = ProjectSearchForm(request.GET or None)
    query = Q(has_image_questionnaire=True)
    if search_form.is_valid():
        for f in ("title", "l2", "l1"):
            val = search_form.cleaned_data.get(f)
            if val:
                query &= Q(**{f"{f}__icontains": val})
    projects = CLARAProject.objects.filter(query)

    rows = []
    for p in projects:
        for r in ImageQuestionnaireResponse.objects.filter(project=p):
            rows.append({
                "project"     : p.title,
                "page"        : r.page_number,
                "question_id" : r.question_id,
                "rater"       : r.user_id,
                "rating"      : r.rating,
            })

    #
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=image_raw.csv"
    writer = csv.DictWriter(response,
        fieldnames=["project","page","question_id","rater","rating"])
    writer.writeheader(); writer.writerows(rows)
    return response

def _get_relevant_elements(project_dir, page_number):
    """
    Reads relevant_pages_and_elements.json for a given page, 
    returns the list of relevant elements (could be characters, objects, etc.).
    """

    relevant_info_path = f'pages/page{page_number}/relevant_pages_and_elements.json'
    full_path = project_pathname(project_dir, relevant_info_path)
    if file_exists(full_path):
        relevant_info = read_project_json_file(project_dir, relevant_info_path)
        return set(relevant_info.get('relevant_elements', []))
    else:
        return set()

def _find_previous_relevant_page(pages_with_images, current_index, project_dir, current_elems):
    """
    Searches backward for any page that shares at least one relevant element
    with the current page. Returns (bool, page_number).
      - bool: True if found a relevant page
      - page_number: the first page_number that shares an element, or None if none
    """
    if not current_elems:
        return (False, None)

    for i in range(current_index - 1, -1, -1):
        prev_page = pages_with_images[i]
        prev_page_num = prev_page.get("page_number")
        prev_elems = _get_relevant_elements(project_dir, prev_page_num)
        if current_elems.intersection(prev_elems):
            return (True, prev_page_num)

    return (False, None)
