# text_questionnaire_views.py
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden

from django.template.loader import render_to_string
#from django.utils.timezone import now, timedelta
from django.db.models.functions import Lower
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count
from django.utils import timezone

from .models import (
    TextQuestionnaire, TQQuestion, TQBookLink, TQResponse, TQAnswer, Content
)
from .forms import TextQuestionnaireForm, ContentSearchForm

from .clara_utils import file_exists, read_txt_file, output_dir_for_project_id, questionnaire_output_dir_for_project_id

from .clara_main import CLARAProjectInternal

from .clara_coherent_images_utils import read_project_json_file, project_pathname

from .clara_images_utils import numbered_page_list_for_coherent_images

import csv
from uuid import uuid4
from pathlib import Path

import pprint, io, zipfile

# --------------------------------------------------
@login_required
def tq_create(request):
    """Create a text questionnaire (with optional per-page questions)."""
    if request.method == "POST":
        form = TextQuestionnaireForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                tq = form.save(commit=False)          # includes page_level_questions
                tq.owner = request.user
                tq.save()

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

    return render(
        request,
        "clara_app/tq_create_or_edit.html",
        {"form": form, "book_picker": book_picker, "tq": tq, "links": links},
    )

# --------------------------------------------------
@login_required
def tq_edit(request, pk):
    tq = get_object_or_404(TextQuestionnaire, pk=pk, owner=request.user)

    if request.method == "POST":
        form = TextQuestionnaireForm(request.POST, instance=tq)
        if form.is_valid():
            with transaction.atomic():
                tq = form.save()  # saves page_level_questions on the model
                _sync_links(
                    tq,
                    request.POST.getlist("book_ids_checked"),
                    request.POST.getlist("book_ids_unchecked"),
                )
                _sync_questions(tq, form.cleaned_data["questions"])  # BOOK only
            messages.success(request, "Questionnaire updated.")
            return redirect("tq_edit", pk=tq.pk)
    else:
        whole_book_lines = list(
            tq.tqquestion_set
              .filter(scope=TQQuestion.SCOPE_BOOK)
              .order_by("order")
              .values_list("text", flat=True)
        )
        form = TextQuestionnaireForm(
            instance=tq,
            initial={"questions": "\n".join(whole_book_lines)},
        )

    preselect = tq.tqbooklink_set.values_list("book_id", flat=True)
    book_picker = _render_book_picker(request, preselect_ids=preselect)
    links = tq.tqbooklink_set.select_related("book")

    return render(
        request,
        "clara_app/tq_create_or_edit.html",
        {"form": form, "book_picker": book_picker, "tq": tq, "links": links},
    )

def _sync_questions(tq, raw_text: str):
    """Replace whole-book questions with the new list (one per line)."""
    lines = [l.strip() for l in (raw_text or "").splitlines() if l.strip()]
    tq.tqquestion_set.all().delete()
    for i, line in enumerate(lines, 1):
        TQQuestion.objects.create(questionnaire=tq, text=line, order=i)

def ensure_q_pages_ready(request, project):
    """
    Make sure rendered questionnaire pages exist for this project.
    Returns (ok: bool, err: Optional[str]).
    """
    cpi = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    project_id = project.id
    try:
        if not cpi.text_available_for_questionnaire_rendering(project_id):
            messages.error(request, "Error creating rendered text pages for questionnaire.")
            messages.error(request, "Text has not been compiled.")
            return False, "text-not-compiled"

        cpi.render_text_for_questionnaire(project_id)

        # Rebuild story data from numbered pages (keeps things in sync)
        numbered = numbered_page_list_for_coherent_images(project, cpi)
        cpi.set_story_data_from_numbered_page_list_v2(numbered)

        return True, None
    except Exception as e:
        messages.error(request, "Error when trying to create rendered text pages for questionnaire.")
        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
        return False, "exception"

def load_q_page_assets(project, page_number: int):
    """
    Return (image_relpath, html_snippet) for a 1-based page_number.
    Falls back to empty strings if not found.
    """
    project_id = project.id
    cpi = CLARAProjectInternal(project.internal_id, project.l2, project.l1)
    project_dir = cpi.coherent_images_v2_project_dir
    story = read_project_json_file(project_dir, "story.json") or []
    # story.json entries are typically { "page_number": N, ... }
    entry = next((p for p in story if p.get("page_number") == page_number), None)

    # Relative image path (served via serve_coherent_images_v2_file)
    image_relpath = f"pages/page{page_number}/image.jpg"

    # Rendered HTML snippet file
    out_dir = questionnaire_output_dir_for_project_id(project_id)
    html_file = f"{out_dir}/page_{page_number}.html"
    html_snippet = read_txt_file(html_file) if file_exists(html_file) else ""

    return image_relpath, html_snippet

# --------------------------------------------------
##def tq_skimlist(request, slug):
##    """Evaluator landing page: list of books + progress."""
##    tq = get_object_or_404(TextQuestionnaire, slug=slug)
##    # if anonymous, create or retrieve lightweight user
##    if not request.user.is_authenticated:
##        user = _get_or_create_anon_user(request)
##    else:
##        user = request.user
##    links = tq.tqbooklink_set.select_related("book").all()
##    done_ids = TQResponse.objects.filter(
##        questionnaire=tq, rater=user
##    ).values_list("book_link_id", flat=True)
##    return render(request, "clara_app/tq_skimlist.html",
##                  {"tq": tq, "links": links, "done": set(done_ids)})

def tq_skimlist(request, slug):
    """Evaluator landing page: list of books + granular progress."""
    tq = get_object_or_404(TextQuestionnaire, slug=slug)

    # if anonymous, create or retrieve lightweight user
    if not request.user.is_authenticated:
        user = _get_or_create_anon_user(request)
    else:
        user = request.user

    links = tq.tqbooklink_set.select_related("book").all()

    # Precompute questionnaire shape
    page_q_texts = parse_per_page_questions(tq) or []
    n_page_q = len(page_q_texts)
    book_qs = list(tq.tqquestion_set.filter(scope=TQQuestion.SCOPE_BOOK).order_by("order"))
    n_book_q = len(book_qs)

    progress = {}  # link.id -> dict(status, answered, required)

    for link in links:
        # Find latest relevant response for this user/book (prefer in-flight; else latest submitted)
        resp = (TQResponse.objects
                .filter(questionnaire=tq, book_link=link, rater=user)
                .order_by('-submitted_at', '-id')
                .first())

        # Work out required counts
        # Need the project to count pages only if there are per-page questions
        if n_page_q:
            project = getattr(link.book, "project", None) or getattr(link.book.content, "project", None)
            total_pages = count_questionnaire_pages(project)
        else:
            total_pages = 0

        required = (n_page_q * total_pages) + n_book_q

        if not resp:
            progress[link.id] = {"status": "none", "answered": 0, "required": required}
            continue

        # Count answers bound to this response
        ans_page = TQAnswer.objects.filter(
            response=resp,
            page_number__isnull=False,
            question__scope=TQQuestion.SCOPE_PAGE
        ).count()

        ans_book = TQAnswer.objects.filter(
            response=resp,
            page_number__isnull=True,
            question__scope=TQQuestion.SCOPE_BOOK
        ).count()

        answered = ans_page + ans_book

        if required == 0:
            # Edge case: no questions defined — treat as complete
            status = "done"
        elif answered == 0:
            status = "none"
        elif answered >= required and (resp.submitted_at or n_page_q == 0 or n_book_q == 0):
            # Mark complete if all required answered; submitted_at preferred but
            # allow completion when all answers present.
            status = "done"
        else:
            status = "partial"

        progress[link.id] = {"status": status, "answered": answered, "required": required}

    return render(
        request,
        "clara_app/tq_skimlist.html",
        {"tq": tq, "links": links, "progress": progress}
    )

# --------------------------------------------------

@login_required
def tq_fill(request, slug, link_id):
    """Run questionnaire: optional per-page phase, then whole-book."""
    tq   = get_object_or_404(TextQuestionnaire, slug=slug)
    link = get_object_or_404(TQBookLink, pk=link_id, questionnaire=tq)
    user = request.user

    # Is there a response that hasn't yet been submitted? If so, use that.
    resp = (TQResponse.objects
           .filter(questionnaire=tq, book_link=link, rater=user, submitted_at__isnull=True)
           .order_by('id')
           .first())
    # Are there submitted responses? If so, use the most recent one.
    if not resp:
        resp = (TQResponse.objects
                .filter(questionnaire=tq, book_link=link, rater=user)
                .order_by('-submitted_at', '-id')
                .first())
    # Create a new response
    if not resp:
        resp = TQResponse.objects.create(questionnaire=tq, book_link=link, rater=user, )

    # check if this user has already started (any answers exist)
    has_answers = TQAnswer.objects.filter(response=resp).exists()

    # per-page questions (text blob on model)
    page_q_texts = parse_per_page_questions(tq)
    book_qs = tq.tqquestion_set.filter(scope=TQQuestion.SCOPE_BOOK)

    n_page_q      = len(page_q_texts)
    n_book_q      = book_qs.count()

    print(f'n_page_q = {n_page_q}')
    print(f'n_book_q = {n_book_q}')

    phase = request.POST.get("phase")

    # We need project to count pages (only if there are per-page questions)
    project = getattr(link.book, "project", None) or getattr(link.book.content, "project", None)
    total_pages = count_questionnaire_pages(project) if n_page_q else 0

    print(f'total_pages = {total_pages}')

    # ▶ Compute completion (all required answers present) ----------------------
    # Count page answers and book answers for this response
    ans_page_cnt = (TQAnswer.objects
                    .filter(response=resp, page_number__isnull=False,
                            question__scope=TQQuestion.SCOPE_PAGE)
                    .count())
    ans_book_cnt = (TQAnswer.objects
                    .filter(response=resp, page_number__isnull=True,
                            question__scope=TQQuestion.SCOPE_BOOK)
                    .count())

    print(f'ans_page_cnt = {ans_page_cnt}')
    print(f'ans_book_cnt = {ans_book_cnt}')

    required = (n_page_q * total_pages) + n_book_q
    answered = ans_page_cnt + ans_book_cnt

    print(f'required = {required}')
    print(f'answered = {answered}')

    # Reopen a previously-submitted response if new questions were added
    if resp.submitted_at and required > answered:
        resp.submitted_at = None
        resp.save(update_fields=["submitted_at"])

    # If fully complete and GET, bounce to skim list
    is_complete = bool(resp.submitted_at) or (required > 0 and answered >= required)
    if is_complete and request.method == "GET":
        return redirect("tq_skimlist", slug=slug)

    # Consider “complete” when explicitly submitted OR (answered >= required and required>0)
    is_complete = bool(resp.submitted_at) or (required > 0 and answered >= required)

    # ▶ If complete and GET, don’t show empty forms again; go back to skim list
    if is_complete and request.method == "GET":
        return redirect("tq_skimlist", slug=slug)

    # --- intro screen if no answers yet ---
    if not has_answers and request.method == "GET":
        return render(
            request,
            "clara_app/tq_intro.html",
            {
                "tq": tq,
                "link": link,
                "has_page_questions": bool(page_q_texts),
                "has_book_questions": bool(book_qs),
            },
        )

    # locate the project to pull rendered page HTML
    project = getattr(link.book, "project", None) or link.book.content.project

    if page_q_texts:
        total_pages = count_questionnaire_pages(project)

        n_page_q = len(page_q_texts)

        # Count answers per page for this response
        ans_counts = (
            TQAnswer.objects
            .filter(
                response=resp,
                page_number__isnull=False,
                question__scope=TQQuestion.SCOPE_PAGE,
            )
            .values("page_number")
            .annotate(cnt=Count("id"))
        )

        answered_count_by_page = {row["page_number"]: row["cnt"] for row in ans_counts}

        # A page is complete only if it has answers for ALL per-page questions
        incomplete_pages = [
            p for p in range(1, total_pages + 1)
            if answered_count_by_page.get(p, 0) < n_page_q
        ]
        
        # if all pages are done, skip straight to whole-book phase
        if incomplete_pages:
            # find current page (first not answered)
            page = incomplete_pages[0]

            # handle POST (per-page phase)
            if request.method == "POST" and phase == "page":
                for idx, qtext in enumerate(page_q_texts, start=1):
                    val = request.POST.get(f"q_pg_{idx}")
                    if val:
                        # ensure a PAGE-scope TQQuestion for this prompt/index
                        q_obj, _ = TQQuestion.objects.get_or_create(
                            questionnaire=tq, scope=TQQuestion.SCOPE_PAGE,
                            order=idx, defaults={"text": qtext}
                        )
                        # update the text if it ever changes
                        if q_obj.text != qtext:
                            q_obj.text = qtext
                            q_obj.save(update_fields=["text"])

                        TQAnswer.objects.update_or_create(
                            response=resp, question=q_obj, page_number=page,
                            defaults={"likert": int(val)}
                        )

                # go to next incomplete page or drop into whole-book phase
                return redirect('tq_fill', slug=slug, link_id=link_id)

            # GET render of the current page (or after failed POST)
            page_html = load_questionnaire_page_html(project, page)

            ok, _err = ensure_q_pages_ready(request, project) 
            if not ok:
                return redirect('clara_home_page')
            image_relpath, html_snippet = load_q_page_assets(project, page)
            
            existing = {}
            for idx, qtext in enumerate(page_q_texts, start=1):
                q_obj = TQQuestion.objects.filter(
                    questionnaire=tq, scope=TQQuestion.SCOPE_PAGE, order=idx
                ).first()
                if not q_obj:
                    continue
                ans = TQAnswer.objects.filter(
                    response=resp, question=q_obj, page_number=page
                ).first()
                if ans:
                    existing[idx] = ans.likert

            context = { "tq": tq,
                        "link": link,
                        "page": page,
                        "total_pages": total_pages,
                        "image_relpath": image_relpath,
                        "html_snippet": html_snippet,
                        "page_questions": list(enumerate(page_q_texts, start=1)),
                        "existing": existing
                        }

            print(f'context:')
            pprint.pprint(context)

            return render(
                request, "clara_app/tq_page_step.html",
                context
            )

    # ---- Whole-book phase (LIKERT matrix) ----
    book_qs_qs = tq.tqquestion_set.filter(scope=TQQuestion.SCOPE_BOOK).order_by("order")

    # Map of {question_id: likert} for THIS response
    answered_book = {
        qid: likert
        for (qid, likert) in TQAnswer.objects.filter(
            response=resp,
            page_number__isnull=True,
            question__scope=TQQuestion.SCOPE_BOOK
        ).values_list("question_id", "likert")
    }

    if request.method == "POST" and phase == "book":
        # Upsert only questions that were posted; untouched radios keep their prior values.
        for q in book_qs_qs:
            raw = request.POST.get(f"q{q.id}")
            if raw:
                TQAnswer.objects.update_or_create(
                    response=resp, question=q, page_number=None,
                    defaults={"likert": int(raw)}
                )

        # Mark submitted if all book questions now have answers AND per-page (if any) is complete
        # (You already computed n_page_q, total_pages, etc. above)
        ans_page_cnt = TQAnswer.objects.filter(
            response=resp, page_number__isnull=False,
            question__scope=TQQuestion.SCOPE_PAGE
        ).count()
        ans_book_cnt = TQAnswer.objects.filter(
            response=resp, page_number__isnull=True,
            question__scope=TQQuestion.SCOPE_BOOK
        ).count()
        required = (n_page_q * total_pages) + book_qs_qs.count()

        if required == 0 or (ans_page_cnt + ans_book_cnt) >= required:
            resp.submitted_at = timezone.now()
            resp.save(update_fields=["submitted_at"])

        return redirect("tq_skimlist", slug=slug)

    # If there are NO book questions and per-page already complete, finish.
    if book_qs_qs.count() == 0 and n_page_q > 0 and request.method == "GET":
        if not resp.submitted_at:
            resp.submitted_at = timezone.now()
            resp.save(update_fields=["submitted_at"])
        return redirect("tq_skimlist", slug=slug)

    # Render whole-book with existing preselected
    return render(
        request,
        "clara_app/tq_fill.html",
        {"tq": tq, "link": link, "questions": list(book_qs_qs), "answered_book": answered_book},
    )

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

def _tq_analytics(tq, *, sort_by_rowmean: bool = False):
    """
    Compute the exact structures shown on the results page, re-usable by CSV export.

    Returns:
      {
        "stats_q_book":  list of {question_id, question__text, question__order, mean, n}
        "stats_q_page":  list of {question_id, question__text, question__order, mean, n_pages, n_ratings}
        "stats_book_matrix": list of rows {title, book_url, cells:[...], row_mean}
        "stats_page_matrix": list of rows {title, book_url, cells:[...], row_mean, pages_rated}
        "book_q_count": int,
        "page_q_count": int,
      }
    """
    # ---- per-question stats (BOOK / PAGE) ----
    base = TQAnswer.objects.filter(
        response__questionnaire=tq,
        response__submitted_at__isnull=False
    )

    # BOOK scope
    stats_q_book = (
        base.filter(question__scope=TQQuestion.SCOPE_BOOK)
            .values('question_id', 'question__text', 'question__order')
            .annotate(mean=Avg('likert'), n=Count('id'))
            .order_by('question__order')
    )

    # PAGE scope
    page_base = base.filter(question__scope=TQQuestion.SCOPE_PAGE)
    agg_page = (
        page_base.values('question_id', 'question__text', 'question__order')
                 .annotate(mean=Avg('likert'), n_ratings=Count('id'))
                 .order_by('question__order')
    )
    from collections import defaultdict
    pages_per_q = defaultdict(int)
    for r in (page_base.exclude(page_number__isnull=True)
              .values('question_id', 'response__book_link__book_id', 'page_number')
              .distinct()):
        pages_per_q[r['question_id']] += 1
    stats_q_page = []
    for row in agg_page:
        d = dict(row)
        d['n_pages'] = pages_per_q.get(d['question_id'], 0)
        stats_q_page.append(d)

    # ---- matrices (BOOK / PAGE) ----
    def _matrix(scope):
        qset = tq.tqquestion_set.filter(scope=scope).order_by("order")
        q_count = qset.count()
        if q_count == 0:
            return [], 0

        base_q = (
            base.filter(question__scope=scope)
                .values('response__book_link__book__title',
                        'response__book_link__book__id',
                        'question__order')
                .annotate(mean=Avg('likert'))
                .order_by('response__book_link__book__title', 'question__order')
        )

        # build title -> cells
        from collections import defaultdict
        cells_map = defaultdict(lambda: [None]*q_count)
        for r in base_q:
            title = r['response__book_link__book__title']
            idx = r['question__order'] - 1
            cells_map[(title, r['response__book_link__book__id'])][idx] = (
                round(r['mean'], 2) if r['mean'] is not None else None
            )

        # pages rated per book (PAGE scope)
        pages_rated_map = defaultdict(int)
        if scope == TQQuestion.SCOPE_PAGE:
            for r in (page_base
                      .values('response__book_link__book__title',
                              'response__book_link__book__id',
                              'page_number')
                      .distinct()):
                if r['page_number'] is not None:
                    pages_rated_map[(r['response__book_link__book__title'],
                                     r['response__book_link__book__id'])] += 1

        # assemble rows
        rows = []
        for (title, book_id), cells in cells_map.items():
            numeric = [c for c in cells if c is not None]
            row_mean = round(sum(numeric)/len(numeric), 2) if numeric else "—"
            book = Content.objects.get(pk=book_id)  # safe: we just aggregated over it
            row = {
                "title": title,
                "book_url": book.get_public_absolute_url(),
                "cells": cells,
                "row_mean": row_mean,
            }
            if scope == TQQuestion.SCOPE_PAGE:
                row["pages_rated"] = pages_rated_map.get((title, book_id), 0)
            rows.append(row)

        if sort_by_rowmean:
            rows.sort(key=lambda r: (r["row_mean"] == "—", r["row_mean"]))
        else:
            rows.sort(key=lambda r: r["title"].lower())

        return rows, q_count

    stats_book_matrix, book_q_count = _matrix(TQQuestion.SCOPE_BOOK)
    stats_page_matrix, page_q_count = _matrix(TQQuestion.SCOPE_PAGE)

    return {
        "stats_q_book": list(stats_q_book),
        "stats_q_page": stats_q_page,
        "stats_book_matrix": stats_book_matrix,
        "stats_page_matrix": stats_page_matrix,
        "book_q_count": book_q_count,
        "page_q_count": page_q_count,
    }

@login_required
def tq_results(request, pk):
    """
    Results page that reports BOTH scopes; only submitted responses included.
    """
    tq = get_object_or_404(TextQuestionnaire, pk=pk, owner=request.user)
    sort_flag = (request.GET.get("sort") == "rowmean")
    data = _tq_analytics(tq, sort_by_rowmean=sort_flag)

    return render(
        request,
        "clara_app/tq_results.html",
        {
            "tq": tq,
            "stats_q_book":  data["stats_q_book"],
            "stats_q_page":  data["stats_q_page"],
            "stats_book_matrix": data["stats_book_matrix"],
            "stats_page_matrix": data["stats_page_matrix"],
            "book_q_count": data["book_q_count"],
            "page_q_count": data["page_q_count"],
        },
    )

# ------------------------------------------------------------------

@login_required
def tq_export_csv(request, pk):
    """
    Download CSV (or ZIP of CSVs) for the exact tables shown in tq_results.

    Query params:
      kind = book_stats | page_stats | book_matrix | page_matrix | all   (default: book_matrix)
      sort = rowmean     # optional; affects the two matrix kinds (as in UI)
    """
    tq = get_object_or_404(TextQuestionnaire, pk=pk)

    # owner or admin can export
    if not (request.user == tq.owner or getattr(request.user.userprofile, "is_admin", False)):
        return HttpResponseForbidden()

    sort_flag = (request.GET.get("sort") == "rowmean")
    data = _tq_analytics(tq, sort_by_rowmean=sort_flag)

    kind = (request.GET.get("kind") or "book_matrix").lower()

    def _csv_response(filename, header, rows_iter):
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename={filename}'
        w = csv.writer(resp)
        w.writerow(header)
        for row in rows_iter:
            w.writerow(row)
        return resp

    if kind == "book_stats":
        header = ["question_order", "question_text", "mean", "n_ratings"]
        rows = (
            (r["question__order"], r["question__text"], f'{r["mean"]:.2f}' if r["mean"] is not None else "", r["n"])
            for r in data["stats_q_book"]
        )
        return _csv_response(f"tq_{tq.pk}_book_stats.csv", header, rows)

    if kind == "page_stats":
        header = ["question_order", "question_text", "mean", "n_pages", "n_ratings"]
        rows = (
            (r["question__order"], r["question__text"],
             f'{r["mean"]:.2f}' if r["mean"] is not None else "",
             r.get("n_pages", 0), r.get("n_ratings", 0))
            for r in data["stats_q_page"]
        )
        return _csv_response(f"tq_{tq.pk}_page_stats.csv", header, rows)

    if kind == "book_matrix":
        qn = data["book_q_count"]
        header = ["book_title", "book_url"] + [f"Q{i}" for i in range(1, qn+1)] + ["Avg"]
        def rows():
            for row in data["stats_book_matrix"]:
                cells = [f"{c:.2f}" if c is not None else "" for c in row["cells"]]
                yield [row["title"], row["book_url"], *cells, row["row_mean"]]
        return _csv_response(f"tq_{tq.pk}_book_matrix.csv", header, rows())

    if kind == "page_matrix":
        qn = data["page_q_count"]
        header = ["book_title", "book_url"] + [f"Q{i}" for i in range(1, qn+1)] + ["Avg", "pages_rated"]
        def rows():
            for row in data["stats_page_matrix"]:
                cells = [f"{c:.2f}" if c is not None else "" for c in row["cells"]]
                yield [row["title"], row["book_url"], *cells, row["row_mean"], row.get("pages_rated", 0)]
        return _csv_response(f"tq_{tq.pk}_page_matrix.csv", header, rows())

    # kind == all → ZIP with 4 CSVs
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # book_stats
        with io.StringIO() as s:
            w = csv.writer(s); w.writerow(["question_order","question_text","mean","n_ratings"])
            for r in data["stats_q_book"]:
                w.writerow([r["question__order"], r["question__text"],
                            f'{r["mean"]:.2f}' if r["mean"] is not None else "", r["n"]])
            zf.writestr(f"tq_{tq.pk}_book_stats.csv", s.getvalue())

        # page_stats
        with io.StringIO() as s:
            w = csv.writer(s); w.writerow(["question_order","question_text","mean","n_pages","n_ratings"])
            for r in data["stats_q_page"]:
                w.writerow([r["question__order"], r["question__text"],
                            f'{r["mean"]:.2f}' if r["mean"] is not None else "",
                            r.get("n_pages", 0), r.get("n_ratings", 0)])
            zf.writestr(f"tq_{tq.pk}_page_stats.csv", s.getvalue())

        # book_matrix
        with io.StringIO() as s:
            qn = data["book_q_count"]
            w = csv.writer(s); w.writerow(["book_title","book_url", *[f"Q{i}" for i in range(1, qn+1)], "Avg"])
            for row in data["stats_book_matrix"]:
                cells = [f"{c:.2f}" if c is not None else "" for c in row["cells"]]
                w.writerow([row["title"], row["book_url"], *cells, row["row_mean"]])
            zf.writestr(f"tq_{tq.pk}_book_matrix.csv", s.getvalue())

        # page_matrix
        with io.StringIO() as s:
            qn = data["page_q_count"]
            w = csv.writer(s); w.writerow(["book_title","book_url", *[f"Q{i}" for i in range(1, qn+1)], "Avg", "pages_rated"])
            for row in data["stats_page_matrix"]:
                cells = [f"{c:.2f}" if c is not None else "" for c in row["cells"]]
                w.writerow([row["title"], row["book_url"], *cells, row["row_mean"], row.get("pages_rated", 0)])
            zf.writestr(f"tq_{tq.pk}_page_matrix.csv", s.getvalue())

    resp = HttpResponse(buf.getvalue(), content_type="application/zip")
    resp["Content-Disposition"] = f'attachment; filename=tq_{tq.pk}_results.zip'
    return resp

# ------------------------------------------------------------------

@login_required
def tq_export_csv_raw(request, pk):
    """
    Download RAW CSV: one row per answer (no aggregation).
    Includes questionnaire, response, rater, book, question, page_number, likert.
    """
    tq = get_object_or_404(TextQuestionnaire, pk=pk)

    # owner or admin can export
    if not (request.user == tq.owner or getattr(request.user.userprofile, "is_admin", False)):
        return HttpResponseForbidden()

    # Pull answers joined to the relevant objects in one go
    # Only include submitted responses (to align with results pages),
    # but flip to all responses if you want in-flight ones too.
    answers = (
        TQAnswer.objects
        .select_related(
            "response",
            "response__rater",
            "response__questionnaire",
            "response__book_link",
            "response__book_link__book",
            "question",
        )
        .filter(response__questionnaire=tq, response__submitted_at__isnull=False)
        .order_by("response__book_link__book_id", "response_id", "question__scope", "question__order", "id")
    )

    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename=tq_{tq.pk}_raw.csv'
    w = csv.writer(resp)

    # Column schema (wide enough for immediate spreadsheet use)
    w.writerow([
        "questionnaire_id",
        "questionnaire_title",
        "response_id",
        "submitted_at_iso",
        "rater_id",
        "rater_username",
        "book_id",
        "book_title",
        "book_url",
        "question_id",
        "question_scope",       # BOOK or PAGE
        "question_order",       # 1..N (within scope)
        "question_text",
        "page_number",          # null for BOOK-scope answers
        "likert"                # 1..5 (or 0 for NOT APPLICABLE in your choices)
    ])

    for a in answers:
        resp_obj   = a.response
        book_obj   = getattr(resp_obj.book_link, "book", None)
        q_obj      = a.question
        # BOOK vs PAGE scope — model uses constants on TQQuestion
        scope_name = "BOOK" if q_obj.scope == TQQuestion.SCOPE_BOOK else "PAGE"
        book_url   = book_obj.get_public_absolute_url() if book_obj else ""

        w.writerow([
            resp_obj.questionnaire_id,
            tq.title,
            resp_obj.id,
            resp_obj.submitted_at.isoformat() if resp_obj.submitted_at else "",
            resp_obj.rater_id,
            getattr(resp_obj.rater, "username", ""),
            getattr(book_obj, "id", ""),
            getattr(book_obj, "title", ""),
            book_url,
            q_obj.id,
            scope_name,
            q_obj.order,
            q_obj.text,
            a.page_number if a.page_number is not None else "",
            a.likert if a.likert is not None else "",
        ])

    return resp

# ------------------------------------------------------------------
@login_required
@require_POST
def tq_delete(request, pk):
    tq = get_object_or_404(TextQuestionnaire, pk=pk, owner=request.user)
    tq.delete()
    messages.success(request, "Questionnaire deleted.")
    return redirect("tq_my_list")

# ------------------------------------------------------------------
@login_required
@user_passes_test(lambda u: u.userprofile.is_admin)
def tq_delete_all_data(request):
    try:
        # Delete in dependency order to avoid FK errors
        TQAnswer.objects.all().delete()
        TQResponse.objects.all().delete()
        TQQuestion.objects.all().delete()
        TQBookLink.objects.all().delete()
        TextQuestionnaire.objects.all().delete()

        return redirect("tq_my_list")
    except Exception as e:
        messages.error(request, f"Error when trying to delete TQ data")
        messages.error(request, f"Exception: {str(e)}\n{traceback.format_exc()}")
        return redirect('clara_home_page')

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
            days_ago = now() - timezone.timedelta(days=int(time_period))
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


##def _sync_questions(tq, raw_text):
##    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
##    tq.tqquestion_set.all().delete()
##    for i, line in enumerate(lines, 1):
##        TQQuestion.objects.create(questionnaire=tq, text=line, order=i)

def _sync_questions(tq, raw_text: str):
    lines = [l.strip() for l in (raw_text or "").splitlines() if l.strip()]
    tq.tqquestion_set.filter(scope=TQQuestion.SCOPE_BOOK).delete()
    for i, line in enumerate(lines, 1):
        TQQuestion.objects.create(
            questionnaire=tq, text=line, order=i, scope=TQQuestion.SCOPE_BOOK
        )

def _get_or_create_anon_user(request):
    key = request.session.get("anon_uid")
    if key:
        return User.objects.get(pk=key)
    user = User.objects.create(username=f"anon_{uuid4().hex[:8]}")
    request.session["anon_uid"] = user.pk
    return user

def parse_per_page_questions(tq):
    raw = (tq.per_page_questions or "").strip()
    if not raw:
        return []
    return [ln.strip() for ln in raw.splitlines() if ln.strip()]

def load_questionnaire_page_html(project, page_number: int) -> str:
    base = Path(output_dir_for_project_id(project.id, 'normal'))
    html_path = base / f"page_{page_number}.html"
    return read_txt_file(html_path) if html_path.exists() else "<em>Missing page</em>"

def count_questionnaire_pages(project) -> int:
    base = Path(output_dir_for_project_id(project.id, 'normal'))
    return len(list(base.glob("page_*.html")))

