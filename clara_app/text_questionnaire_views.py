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

from .clara_utils import output_dir_for_project_id, read_txt_file

import csv
from uuid import uuid4
from pathlib import Path

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

##    if request.method == "POST":
##        form = TextQuestionnaireForm(request.POST, instance=tq)
##        if form.is_valid():
##            with transaction.atomic():
##                tq = form.save()  # persists page_level_questions edits
##
##                _sync_links(
##                    tq,
##                    request.POST.getlist("book_ids_checked"),
##                    request.POST.getlist("book_ids_unchecked"),
##                )
##                _sync_questions(tq, form.cleaned_data["questions"])
##
##            messages.success(request, "Questionnaire updated.")
##            return redirect("tq_edit", pk=tq.pk)
##    else:
##        # Prefill 'questions' from existing TQQuestion rows
##        existing_qs = (
##            tq.tqquestion_set.order_by("order").values_list("text", flat=True)
##        )
##        form = TextQuestionnaireForm(
##            instance=tq,
##            initial={"questions": "\n".join(existing_qs)},
##        )

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
##def tq_fill(request, slug, link_id):
##    """Questionnaire runner. If tq.per_page_questions is present, do a page-by-page phase first."""
##    tq   = get_object_or_404(TextQuestionnaire, slug=slug)
##    link = get_object_or_404(TQBookLink, pk=link_id, questionnaire=tq)
##    user = request.user
##
##    # Create/find an in-flight response
##    resp, _ = TQResponse.objects.get_or_create(
##        questionnaire=tq, book_link=link, rater=user, submitted_at__isnull=True
##    )
##
##    # --- Are there per-page questions? --------------------------------
##    page_q_texts = parse_per_page_questions(tq)
##
##    # We can retrieve the CLARA project via the linked content/book:
##    # Adjust attribute names as in your codebase.
##    project = link.book.project if hasattr(link.book, 'project') else link.book.content.project
##
##    if page_q_texts:
##        total_pages = count_questionnaire_pages(project)
##
##        # decide which page we’re on
##        page = request.GET.get('page')
##        if page is None:
##            # jump to the first page with missing answers (or 1)
##            answered_pages = set(
##                TQAnswer.objects.filter(response=resp, page_number__isnull=False)
##                .values_list('page_number', flat=True)
##            )
##            page = next((p for p in range(1, total_pages+1) if p not in answered_pages), None)
##            page = page or 1
##        else:
##            page = int(page)
##
##        # handle POST for a page step
##        if request.method == "POST" and request.POST.get("phase") == "page":
##            for idx, qtext in enumerate(page_q_texts, start=1):
##                field = f"q_pg_{idx}"
##                val = request.POST.get(field)
##                if val:
##                    # We map to a synthetic TQQuestion row if you want book-level later,
##                    # but to keep minimal change, we store under a virtual per-page question
##                    # by creating/using real TQQuestion rows. Easiest: ensure page-scope
##                    # questions exist as TQQuestion objects. 
##                    q_obj, _ = TQQuestion.objects.get_or_create(
##                        questionnaire=tq,
##                        text=qtext,
##                        order=idx,
##                    )
##                    TQAnswer.objects.update_or_create(
##                        response=resp, question=q_obj, page_number=page,
##                        defaults={'likert': int(val)}
##                    )
##
##            # next page or move on to normal (book-level) matrix
##            if page < total_pages:
##                return redirect(f"{request.path}?page={page+1}")
##            else:
##                return redirect(request.path)  # fall through to normal matrix
##
##        # render a page step (GET)
##        existing = {}
##        # pre-fill previously given per-page ratings for this specific page
##        for idx, qtext in enumerate(page_q_texts, start=1):
##            try:
##                q_obj = TQQuestion.objects.get(
##                    questionnaire=tq,
##                    text=qtext,
##                    order=idx
##                )
##                ans = TQAnswer.objects.filter(response=resp, question=q_obj, page_number=page).first()
##                if ans:
##                    existing[idx] = ans.likert
##            except TQQuestion.DoesNotExist:
##                pass
##
##        page_html = load_questionnaire_page_html(project, page)
##
##        return render(request, "clara_app/tq_page_step.html", {
##            "tq": tq, "link": link, "page": page, "total_pages": total_pages,
##            "page_html": page_html, "page_questions": list(enumerate(page_q_texts, start=1)),
##            "existing": existing,
##        })
##
##    # --- No per-page questions → behave like the original tq_fill ------
##    questions = tq.tqquestion_set.all().order_by("order")
##    if request.method == "POST":
##        resp.submitted_at = timezone.now()
##        resp.save(update_fields=['submitted_at'])
##        for q in questions:
##            rating = int(request.POST.get(f"q{q.id}", 0))
##            if rating:
##                TQAnswer.objects.update_or_create(
##                    response=resp, question=q, page_number=None,
##                    defaults={'likert': rating}
##                )
##        return redirect("tq_skimlist", slug=slug)
##
##    return render(request, "clara_app/tq_fill.html",
##                  {"tq": tq, "link": link, "questions": questions})

@login_required
def tq_fill(request, slug, link_id):
    """Run questionnaire: optional per-page phase, then whole-book."""
    tq   = get_object_or_404(TextQuestionnaire, slug=slug)
    link = get_object_or_404(TQBookLink, pk=link_id, questionnaire=tq)
    user = request.user

    print(f'user = {user}')

    # ensure an in-flight response
##    resp, _ = TQResponse.objects.get_or_create(
##        questionnaire=tq, book_link=link, rater=user, submitted_at__isnull=True
##    )

    resp = (TQResponse.objects
           .filter(questionnaire=tq, book_link=link, rater=user, submitted_at__isnull=True)
           .order_by('id')
           .first())
    if not resp:
        resp = TQResponse.objects.create(questionnaire=tq, book_link=link, rater=user, )

    print(f'resp = {resp}')

    # per-page questions (text blob on model)
    page_q_texts = parse_per_page_questions(tq)

    # locate the project to pull rendered page HTML
    project = getattr(link.book, "project", None) or link.book.content.project

    if page_q_texts:
        total_pages = count_questionnaire_pages(project)

        # which pages already done? (answers tied to PAGE scope questions)
        answered_pages = set(
            TQAnswer.objects
                .filter(
                    response=resp,
                    page_number__isnull=False,
                    question__scope=TQQuestion.SCOPE_PAGE
                )
                .values_list("page_number", flat=True)
        )

        print(f'answered_pages = {answered_pages}')

        # if all pages are done, skip straight to whole-book phase
        if len(answered_pages) < total_pages:
            # find current page (first not answered) unless explicit ?page=
            page_param = request.GET.get("page")
            if page_param is None:
                page = next((p for p in range(1, total_pages+1) if p not in answered_pages), 1)
            else:
                page = int(page_param)

            # handle POST (per-page phase)
            if request.method == "POST" and request.POST.get("phase") == "page":
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

                # go to next page or drop into whole-book phase
                if page < total_pages:
                    return redirect(f"{request.path}?page={page+1}")
                else:
                    # all done with pages; fall through to whole-book
                    #answered_pages = set(range(1, total_pages+1))
                    return redirect(request.path)

            # GET render of the current page (or after failed POST)
            page_html = load_questionnaire_page_html(project, page)
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

            return render(
                request, "clara_app/tq_page_step.html",
                {
                    "tq": tq, "link": link,
                    "page": page, "total_pages": total_pages,
                    "page_html": page_html,
                    "page_questions": list(enumerate(page_q_texts, start=1)),
                    "existing": existing,
                },
            )

    # ---- Whole-book phase (LIKERT matrix) ----
    questions = tq.tqquestion_set.filter(scope=TQQuestion.SCOPE_BOOK).order_by("order")
    if request.method == "POST":
        # whole-book submit
        resp.submitted_at = timezone.now()
        resp.save(update_fields=["submitted_at"])
        for q in questions:
            rating = int(request.POST.get(f"q{q.id}", 0))
            if rating:
                TQAnswer.objects.update_or_create(
                    response=resp, question=q, page_number=None,
                    defaults={"likert": rating},
                )
        return redirect("tq_skimlist", slug=slug)

    return render(request, "clara_app/tq_fill.html", {"tq": tq, "link": link, "questions": questions})

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
##@login_required
##def tq_results(request, pk):
##    """
##    Results page that reports BOTH scopes:
##      - Page-level questions (aggregated across pages per book)
##      - Whole-book questions (as before)
##    """
##    tq = get_object_or_404(TextQuestionnaire, pk=pk, owner=request.user)
##
##    # ---------- helpers ----------
##    def _per_question_stats(scope):
##        """
##        Per-question global stats (mean, n), ordered by question.order.
##        For PAGE scope: aggregates across ALL pages (page_number ignored).
##        """
##        qs = (
##            TQAnswer.objects
##            .filter(response__questionnaire=tq, question__scope=scope)
##            .values('question_id', 'question__text', 'question__order')
##            .annotate(mean=Avg('likert'), n=Count('id'))
##            .order_by('question__order')
##        )
##        return qs
##
##    def _matrix_for_scope(scope):
##        """
##        Build a book × question matrix of means.
##        For PAGE scope: aggregate across pages per book (so one cell per book, per question).
##        Returns (rows, q_count), where each row = {
##            "title": str,
##            "cells": [means…],  # aligned to question order
##            "row_mean": float or "—",
##            "pages_rated": int (only for PAGE scope)
##        }
##        """
##        qset = tq.tqquestion_set.filter(scope=scope).order_by("order")
##        q_count = qset.count()
##        if q_count == 0:
##            return [], 0
##
##        # Base queryset: one row per (book, question)
##        # PAGE scope: include page answers, but aggregate them away via Avg.
##        base = (
##            TQAnswer.objects
##            .filter(response__questionnaire=tq, question__scope=scope)
##            .values(
##                'response__book_link__book__title',
##                'question__order'
##            )
##            .annotate(mean=Avg('likert'))
##            .order_by('response__book_link__book__title', 'question__order')
##        )
##
##        from collections import defaultdict
##        tmp = defaultdict(lambda: [None] * q_count)
##
##        # For PAGE scope we’ll also compute how many distinct pages received any ratings for that book
##        pages_rated_map = defaultdict(int)
##        if scope == TQQuestion.SCOPE_PAGE:
##            pages_qs = (
##                TQAnswer.objects
##                .filter(response__questionnaire=tq, question__scope=scope)
##                .values('response__book_link__book__title', 'page_number')
##                .distinct()
##            )
##            for r in pages_qs:
##                if r['page_number'] is not None:
##                    pages_rated_map[r['response__book_link__book__title']] += 1
##
##        for r in base:
##            title = r['response__book_link__book__title']
##            idx   = r['question__order'] - 1
##            tmp[title][idx] = round(r['mean'], 2) if r['mean'] is not None else None
##
##        rows = []
##        for title, cells in tmp.items():
##            numeric = [c for c in cells if c is not None]
##            row_mean = round(sum(numeric) / len(numeric), 2) if numeric else "—"
##            row = {"title": title, "cells": cells, "row_mean": row_mean}
##            if scope == TQQuestion.SCOPE_PAGE:
##                row["pages_rated"] = pages_rated_map.get(title, 0)
##            rows.append(row)
##
##        # optional ordering: ?sort=rowmean (applies to both matrices)
##        if request.GET.get("sort") == "rowmean":
##            rows.sort(key=lambda r: (r["row_mean"] == "—", r["row_mean"]))
##        else:
##            rows.sort(key=lambda r: r["title"].lower())
##
##        return rows, q_count
##
##    # ---------- gather both scopes ----------
##    stats_q_book = _per_question_stats(TQQuestion.SCOPE_BOOK)
##    stats_q_page = _per_question_stats(TQQuestion.SCOPE_PAGE)
##
##    stats_book_matrix, book_q_count = _matrix_for_scope(TQQuestion.SCOPE_BOOK)
##    stats_page_matrix, page_q_count = _matrix_for_scope(TQQuestion.SCOPE_PAGE)
##
##    return render(
##        request,
##        "clara_app/tq_results.html",
##        {
##            "tq": tq,
##            # global per-question summaries
##            "stats_q_book": stats_q_book,
##            "stats_q_page": stats_q_page,
##            # matrices
##            "stats_book_matrix": stats_book_matrix,
##            "stats_page_matrix": stats_page_matrix,
##            "book_q_count": book_q_count,
##            "page_q_count": page_q_count,
##        },
##    )

@login_required
def tq_results(request, pk):
    """
    Results page that reports BOTH scopes:
      - Page-level questions (aggregated across pages per book)
      - Whole-book questions (as before)

    IMPORTANT: Only submitted responses are included.
    """
    tq = get_object_or_404(TextQuestionnaire, pk=pk, owner=request.user)

    # ---------- helpers ----------
    def _per_question_stats(scope):
        """
        Per-question global stats (mean, counts), ordered by question.order.

        For PAGE scope we report:
          - n: total ratings (all raters × all pages that had a rating)
          - n_pages: distinct pages that received at least one rating
        For BOOK scope we report:
          - n: total ratings (all raters × all books)
        """
        qs = (
            TQAnswer.objects
            .filter(
                response__questionnaire=tq,
                response__submitted_at__isnull=False,   # only submitted
                question__scope=scope
            )
            .values('question_id', 'question__text', 'question__order')
            .annotate(
                mean=Avg('likert'),
                n=Count('id'),
                n_pages=Count('page_number', distinct=True)  # harmless for BOOK scope
            )
            .order_by('question__order')
        )
        return qs

    def _per_question_stats(scope):
        """
        Per-question global stats (mean, counts), ordered by question.order.

        BOOK scope:
          - mean over all ratings
          - n = total ratings (answers)
        PAGE scope:
          - mean over all ratings
          - n = distinct pages (count of unique (book, page_number) that received ≥1 rating for that question)
          - n_ratings also available if needed
        """
        base = (
            TQAnswer.objects
            .filter(
                response__questionnaire=tq,
                response__submitted_at__isnull=False,   # only submitted
                question__scope=scope
            )
        )

        if scope == TQQuestion.SCOPE_BOOK:
            # as before
            return (
                base.values('question_id', 'question__text', 'question__order')
                    .annotate(mean=Avg('likert'), n=Count('id'))
                    .order_by('question__order')
            )

        # --- PAGE scope: n should be "distinct pages", robust across multiple books ---
        # 1) Compute mean and total ratings per question (kept in case you want it)
        agg = (
            base.values('question_id', 'question__text', 'question__order')
                .annotate(mean=Avg('likert'), n_ratings=Count('id'))
                .order_by('question__order')
        )

        # 2) Count distinct (book, page) per question
        from collections import defaultdict
        pages_per_q = defaultdict(int)
        distinct_pairs = (
            base.exclude(page_number__isnull=True)
                .values('question_id', 'response__book_link__book_id', 'page_number')
                .distinct()
        )
        for r in distinct_pairs:
            pages_per_q[r['question_id']] += 1

        # 3) Replace n with distinct-pages count; keep n_ratings if you need it
        result = []
        for row in agg:
            row = dict(row)
            row['n'] = pages_per_q.get(row['question_id'], 0)   # <- n = distinct pages
            # row['n_ratings'] remains available if you want to display it
            result.append(row)
        return result

    def _matrix_for_scope(scope):
        """
        Build a book × question matrix of means.

        For PAGE scope: aggregate across pages per book (so one cell per book per question).
        Returns (rows, q_count), where each row = {
            "title": str,
            "cells": [means…],  # aligned to question order
            "row_mean": float or "—",
            "pages_rated": int (only for PAGE scope)
        }
        """
        qset = tq.tqquestion_set.filter(scope=scope).order_by("order")
        q_count = qset.count()
        if q_count == 0:
            return [], 0

        # Base queryset: one row per (book, question) with mean over all ratings.
        base = (
            TQAnswer.objects
            .filter(
                response__questionnaire=tq,
                response__submitted_at__isnull=False,        # only submitted
                question__scope=scope
            )
            .values(
                'response__book_link__book__title',
                'question__order'
            )
            .annotate(mean=Avg('likert'))
            .order_by('response__book_link__book__title', 'question__order')
        )

        from collections import defaultdict
        tmp = defaultdict(lambda: [None] * q_count)

        # For PAGE scope compute how many distinct pages received any ratings for that book.
        pages_rated_map = defaultdict(int)
        if scope == TQQuestion.SCOPE_PAGE:
            pages_qs = (
                TQAnswer.objects
                .filter(
                    response__questionnaire=tq,
                    response__submitted_at__isnull=False,    # only submitted
                    question__scope=scope
                )
                .values('response__book_link__book__title', 'page_number')
                .distinct()
            )
            for r in pages_qs:
                if r['page_number'] is not None:
                    pages_rated_map[r['response__book_link__book__title']] += 1

        for r in base:
            title = r['response__book_link__book__title']
            idx   = r['question__order'] - 1
            tmp[title][idx] = round(r['mean'], 2) if r['mean'] is not None else None

        rows = []
        for title, cells in tmp.items():
            numeric = [c for c in cells if c is not None]
            row_mean = round(sum(numeric) / len(numeric), 2) if numeric else "—"
            row = {"title": title, "cells": cells, "row_mean": row_mean}
            if scope == TQQuestion.SCOPE_PAGE:
                row["pages_rated"] = pages_rated_map.get(title, 0)
            rows.append(row)

        # optional ordering: ?sort=rowmean (applies to both matrices)
        if request.GET.get("sort") == "rowmean":
            rows.sort(key=lambda r: (r["row_mean"] == "—", r["row_mean"]))
        else:
            rows.sort(key=lambda r: r["title"].lower())

        return rows, q_count

    # ---------- gather both scopes ----------
    stats_q_book = _per_question_stats(TQQuestion.SCOPE_BOOK)
    stats_q_page = _per_question_stats(TQQuestion.SCOPE_PAGE)

    stats_book_matrix, book_q_count = _matrix_for_scope(TQQuestion.SCOPE_BOOK)
    stats_page_matrix, page_q_count = _matrix_for_scope(TQQuestion.SCOPE_PAGE)

    return render(
        request,
        "clara_app/tq_results.html",
        {
            "tq": tq,
            # global per-question summaries
            "stats_q_book": stats_q_book,
            "stats_q_page": stats_q_page,
            # matrices
            "stats_book_matrix": stats_book_matrix,
            "stats_page_matrix": stats_page_matrix,
            "book_q_count": book_q_count,
            "page_q_count": page_q_count,
        },
    )

# ------------------------------------------------------------------

@login_required
def tq_export_csv(request, pk):
    tq = get_object_or_404(TextQuestionnaire, pk=pk)

    # owner or admin can export
    if not (request.user == tq.owner or getattr(request.user.userprofile, "is_admin", False)):
        return HttpResponseForbidden()

    questions = list(tq.tqquestion_set.order_by("order").values("id", "order", "text"))

    # Pull responses + answers + book in one go
    responses = (
        tq.tqresponse_set
          .select_related("book_link__book", "rater")
          .prefetch_related("tqanswer_set", "tqanswer_set__question")
          .order_by("book_link__book_id", "rater_id", "id")
    )

    # ---------- RAW CSV ----------
    if request.GET.get("raw") == "1":
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename=tq_{tq.pk}_raw.csv'
        w = csv.writer(resp)
        w.writerow([
            "questionnaire_id", "book_id", "book_title", "book_url",
            "rater_id", "question_id", "question_order", "rating",
        ])
        for r in responses:
            book = r.book_link.book
            #book_url = _public_book_url(request, book)
            book_url = book.get_public_absolute_url()
            for a in r.tqanswer_set.all():
                w.writerow([
                    tq.pk, book.id, book.title, book_url,
                    r.rater_id, a.question_id, a.question.order, a.likert
                ])
        return resp

    # ---------- AGGREGATED (one row per book) ----------
    # Build per-book aggregates: mean per question (by question.order) + overall
    from collections import defaultdict
    q_ids_by_order = {q["order"]: q["id"] for q in questions}

    per_book = {}
    for r in responses:
        book = r.book_link.book
        entry = per_book.setdefault(book.id, {
            "book": book,
            "raters": set(),
            "sum_by_order": defaultdict(float),
            "cnt_by_order": defaultdict(int),
        })
        entry["raters"].add(r.rater_id)
        for a in r.tqanswer_set.all():
            q_order = a.question.order
            entry["sum_by_order"][q_order] += float(a.likert)
            entry["cnt_by_order"][q_order] += 1

    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename=tq_{tq.pk}_summary.csv'

    headers = ["questionnaire_id", "book_id", "book_title", "book_url", "n_eval", "n_responses"]
    headers += [f"q{q['order']}_mean" for q in questions]
    headers += ["overall_mean"]
    w = csv.DictWriter(resp, fieldnames=headers)
    w.writeheader()

    for _, data in per_book.items():
        book = data["book"]
        book_url = book.get_public_absolute_url()
        row = {
            "questionnaire_id": tq.pk,
            "book_id": book.id,
            "book_title": book.title,
            "book_url": book_url,
            "n_eval": len(data["raters"]),
        }
        per_q_means, total_n = [], 0
        for q in questions:
            q_order = q["order"]
            s = data["sum_by_order"].get(q_order, 0.0)
            c = data["cnt_by_order"].get(q_order, 0)
            mean = (s / c) if c else None
            row[f"q{q_order}_mean"] = f"{mean:.2f}" if mean is not None else ""
            if mean is not None:
                per_q_means.append(mean)
                total_n += c
        row["n_responses"] = total_n
        row["overall_mean"] = f"{(sum(per_q_means)/len(per_q_means)):.2f}" if per_q_means else ""
        w.writerow(row)

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

