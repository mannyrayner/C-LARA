# text_questionnaire_views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden

from django.template.loader import render_to_string
from django.utils.timezone import now, timedelta
from django.db.models.functions import Lower
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count

from .models import (
    TextQuestionnaire, TQQuestion, TQBookLink, TQResponse, TQAnswer, Content
)
from .forms import TextQuestionnaireForm, ContentSearchForm

import csv

# --------------------------------------------------
@login_required
def tq_create(request):
    """Create or save a draft text‐questionnaire."""
    if request.method == "POST":
        form = TextQuestionnaireForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                tq = form.save(commit=False)
                tq.owner = request.user
                tq.save()
                #_sync_links(tq, request.POST.getlist("book_ids"))
                _sync_links(
                    tq,
                    request.POST.getlist("book_ids_checked"),
                    request.POST.getlist("book_ids_unchecked"),
                )
                _sync_questions(tq, form.cleaned_data["questions"])
            messages.success(request, "Questionnaire saved.")
            return redirect("tq_edit", pk=tq.pk)
        else:
            tq = None
    else:
        form = TextQuestionnaireForm()
        tq = None
    book_picker = _render_book_picker(request)
    links = tq.tqbooklink_set.select_related("book") if tq else []
    return render(request, "clara_app/tq_create_or_edit.html",
                  {"form": form,
                   "book_picker": book_picker,
                   "tq": tq,
                   "links": links})

# --------------------------------------------------
@login_required
def tq_edit(request, pk):
    tq = get_object_or_404(TextQuestionnaire, pk=pk, owner=request.user)
    if request.method == "POST":
        form = TextQuestionnaireForm(request.POST, instance=tq)
        if form.is_valid():
            with transaction.atomic():
                tq = form.save()
                #_sync_links(tq, request.POST.getlist("book_ids"))
                _sync_links(
                    tq,
                    request.POST.getlist("book_ids_checked"),
                    request.POST.getlist("book_ids_unchecked"),
                )
                _sync_questions(tq, form.cleaned_data["questions"])
            messages.success(request, "Questionnaire updated.")
            return redirect("tq_edit", pk=tq.pk)
    else:
        form = TextQuestionnaireForm(instance=tq)
    book_picker = _render_book_picker(request, preselect_ids=tq.tqbooklink_set.values_list("book_id", flat=True))
    links = tq.tqbooklink_set.select_related("book") if tq else []
    return render(request, "clara_app/tq_create_or_edit.html",
                  {"form": form,
                   "book_picker": book_picker,
                   "tq": tq,
                   "links": links})

# --------------------------------------------------
def tq_skimlist(request, slug):
    """Evaluator landing page: list of books + progress."""
    tq = get_object_or_404(TextQuestionnaire, slug=slug)
    # if anonymous, create or retrieve lightweight user
    if not request.user.is_authenticated:
        user = _get_or_create_anon_user(request)
    else:
        user = request.user
    links = tq.tqbooklink_set.select_related("book").all()
    done_ids = TQResponse.objects.filter(
        questionnaire=tq, rater=user
    ).values_list("book_link_id", flat=True)
    return render(request, "clara_app/tq_skimlist.html",
                  {"tq": tq, "links": links, "done": set(done_ids)})

# --------------------------------------------------
def tq_fill(request, slug, link_id):
    """Single‐book questionnaire page (Likert matrix)."""
    tq = get_object_or_404(TextQuestionnaire, slug=slug)
    link = get_object_or_404(TQBookLink, pk=link_id, questionnaire=tq)
    if not request.user.is_authenticated:
        user = _get_or_create_anon_user(request)
    else:
        user = request.user

    questions = tq.tqquestion_set.all().order_by("order")

    if request.method == "POST":
        resp = TQResponse.objects.create(
            questionnaire=tq, book_link=link, rater=user)
        for q in questions:
            rating = int(request.POST.get(f"q{q.id}", 0))
            TQAnswer.objects.create(response=resp, question=q, likert=rating)
        return redirect("tq_skimlist", slug=slug)

    return render(request, "clara_app/tq_fill.html",
                  {"tq": tq, "link": link, "questions": questions})

# --------------------------------------------------
@login_required
def tq_remove(request, link_id):
    link = get_object_or_404(TQBookLink, pk=link_id,
                             questionnaire__owner=request.user)
    link.delete()
    return JsonResponse({"ok": True})

# --------------------------------------------------
def tq_public_list(request):
    """Public landing page: all posted questionnaires with links to skim view."""
    tqs = TextQuestionnaire.objects.order_by("-created_at")
    return render(request, "clara_app/tq_public_list.html", {"tqs": tqs})

# --------------------------------------------------
@login_required
def tq_my_list(request):
    """List questionnaires owned by the current user with edit links."""
    my_tqs = TextQuestionnaire.objects.filter(owner=request.user).order_by("-created_at")
    return render(request, "clara_app/tq_my_list.html", {"tqs": my_tqs})

# ------------------------------------------------------------------
@login_required
def tq_results(request, pk):
    """Summary table: mean score and N for each question."""
    tq = get_object_or_404(TextQuestionnaire, pk=pk, owner=request.user)

    # Aggregate answers: {q_id: {'mean': …, 'n': …}}
    stats = (
        TQAnswer.objects
        .filter(response__questionnaire=tq)
        .values('question_id', 'question__text')
        .annotate(mean=Avg('likert'), n=Count('id'))
        .order_by('question_id')
    )

    return render(request, "clara_app/tq_results.html",
                  {"tq": tq, "stats": stats})

# ------------------------------------------------------------------
@login_required
def tq_export_csv(request, pk):
    """Download raw responses as CSV (one row per answer)."""
    tq = get_object_or_404(TextQuestionnaire, pk=pk, owner=request.user)

    response = HttpResponse(content_type="text/csv")
    response['Content-Disposition'] = f'attachment; filename=tq_{pk}_answers.csv'

    writer = csv.writer(response)
    writer.writerow(["book_id", "rater_id", "question_id", "likert"])

    queryset = (
        TQAnswer.objects
        .filter(response__questionnaire=tq)
        .values_list(
            'response__book_link__book_id',
            'response__rater_id',
            'question_id',
            'likert'
        )
    )
    for row in queryset:
        writer.writerow(row)

    return response

# ===== helper utilities ======================================
def _render_book_picker(request, preselect_ids=None):
    """
    Renders the searchable book list with check-boxes.
    Returns ready-to-insert HTML.
    """
    preselect_ids = set(preselect_ids or [])
    search_form = ContentSearchForm(request.GET or None)
    query = Q()  

    # ----- filter logic (verbatim from public_content_list) -----
    if search_form.is_valid():
        l2 = search_form.cleaned_data.get("l2")
        l1 = search_form.cleaned_data.get("l1")
        title = search_form.cleaned_data.get("title")
        time_period = search_form.cleaned_data.get("time_period")

        if l2:
            query &= Q(l2__icontains=l2)
        if l1:
            query &= Q(l1__icontains=l1)
        if title:
            query &= Q(title__icontains=title)
        if time_period:
            days_ago = now() - timedelta(days=int(time_period))
            query &= Q(updated_at__gte=days_ago)

    content_qs = Content.objects.filter(query)

    # ----- ordering (same as public_content_list) -----
    order_by = request.GET.get("order_by")
    if order_by == "title":
        content_qs = content_qs.order_by(Lower("title"))
    elif order_by == "age":
        content_qs = content_qs.order_by("-updated_at")
    elif order_by == "accesses":
        content_qs = content_qs.order_by("-unique_access_count")
    else:
        content_qs = content_qs.order_by(Lower("title"))

    paginator = Paginator(content_qs, 10)  # 10 per page
    page_obj = paginator.get_page(request.GET.get("page"))

    # ----- render partial -----
    qs = request.GET.copy()
    qs.pop("page", None)          # remove any existing page param
    querystring = qs.urlencode()  # '' when no other params

    return render_to_string(
        "clara_app/partials/tq_book_picker.html",
        {
            "page_obj": page_obj,
            "search_form": search_form,
            "preselected": preselect_ids,
            "qs": "&" + querystring if querystring else "",  # prepend & if non-empty
        },
        request=request,
    )

def _sync_links(tq, checked_ids, unchecked_ids):
    checked   = set(map(int, checked_ids))
    unchecked = set(map(int, unchecked_ids))

    # 1. ADD any newly checked books that are not already linked
    to_add = checked - set(tq.tqbooklink_set.values_list("book_id", flat=True))
    for bid in to_add:
        TQBookLink.objects.create(questionnaire=tq, book_id=bid, order=0)

    # 2. DELETE only the unchecked books that are currently linked
    tq.tqbooklink_set.filter(book_id__in=unchecked).delete()


def _sync_questions(tq, raw_text):
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    tq.tqquestion_set.all().delete()
    for i, line in enumerate(lines, 1):
        TQQuestion.objects.create(questionnaire=tq, text=line, order=i)

def _get_or_create_anon_user(request):
    key = request.session.get("anon_uid")
    if key:
        return User.objects.get(pk=key)
    user = User.objects.create(username=f"anon_{uuid4().hex[:8]}")
    request.session["anon_uid"] = user.pk
    return user
