# clara_app/exercises_views.py

from datetime import datetime, timezone
import asyncio
import json
import random
import traceback

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django_q.tasks import async_task

from .models import CLARAProject
from .clara_main import CLARAProjectInternal
from .clara_chatgpt4 import get_api_chatgpt4_response

from .utils import (
    user_has_a_project_role,
    make_asynch_callback_and_report_id,
    get_task_updates,
    store_cost_dict,
)
from .clara_utils import post_task_update, get_config
from .clara_coherent_images_utils import combine_cost_dicts

config = get_config()

EXERCISE_TYPES = [
    ("cloze_mcq", "Cloze (multiple choice)"),
]

CLOZE_PROMPT_VERSION = "cloze_distractors_v1"
MODEL_NAME = "gpt-5"


# ---------------- Top-level views ----------------

@login_required
@user_has_a_project_role
def generate_exercises(request: HttpRequest, project_id: int, status: str = "start") -> HttpResponse:
    """
    Main page: show form (GET) or queue async generation (POST).
    status is used only to show a one-shot message after monitor redirect.
    """
    if status == "finished":
        messages.info(request, "Exercise generation completed normally.")
    elif status == "error":
        messages.error(request, "Error in exercise generation. See 'Recent task updates' for details.")

    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    if request.method == "GET":
        return render(
            request,
            "clara_app/generate_exercises.html",
            {
                "project": project,
                "exercise_types": EXERCISE_TYPES,
                "defaults": {"exercise_type": "cloze_mcq", "n_examples": 20, "n_distractors": 3, "seed": ""},
            },
        )

    # POST
    exercise_type = request.POST.get("exercise_type", "cloze_mcq").strip()
    n_examples = int(request.POST.get("n_examples", "20"))
    n_distractors = int(request.POST.get("n_distractors", "3"))
    seed_str = request.POST.get("seed", "").strip()
    seed = int(seed_str) if seed_str else random.randint(1, 10**9)

    if exercise_type not in dict(EXERCISE_TYPES):
        messages.error(request, "Unknown exercise type.")
        return redirect("generate_exercises", project_id=project_id, status="start")
    if not (1 <= n_examples <= 200):
        messages.error(request, "Number of examples must be between 1 and 200.")
        return redirect("generate_exercises", project_id=project_id, status="start")
    if not (1 <= n_distractors <= 5):
        messages.error(request, "Number of distractors must be between 1 and 5.")
        return redirect("generate_exercises", project_id=project_id, status="start")

    # Build internalised/annotated structure (pages -> segments -> content elements)
    text_obj = clara_project_internal.get_internalised_text_exact()
    rng = random.Random(seed)

    callback, report_id = make_asynch_callback_and_report_id(request, "exercises")

    async_task(
        create_and_save_exercise_items,
        project,
        clara_project_internal,
        text_obj,
        exercise_type,
        n_examples,
        n_distractors,
        seed,
        rng,
        callback=callback,
    )

    return redirect("generate_exercises_monitor", project_id, report_id)


@login_required
@user_has_a_project_role
def generate_exercises_monitor(request: HttpRequest, project_id: int, report_id: str) -> HttpResponse:
    project = get_object_or_404(CLARAProject, pk=project_id)
    return render(
        request,
        "clara_app/generate_exercises_monitor.html",
        {"project_id": project_id, "project": project, "report_id": report_id},
    )


@login_required
@user_has_a_project_role
def generate_exercises_status(request: HttpRequest, project_id: int, report_id: str) -> JsonResponse:
    msgs = get_task_updates(report_id)

    if "error" in msgs:
        status = "error"
    elif "finished" in msgs:
        status = "finished"
    else:
        status = "unknown"

    return JsonResponse({"messages": msgs, "status": status})


# ---------------- Async worker entrypoint ----------------

def create_and_save_exercise_items(
    project,
    clara_project_internal,
    text_obj,
    exercise_type: str,
    n_examples: int,
    n_distractors: int,
    seed: int,
    rng: random.Random,
    callback=None,
):
    try:
        if exercise_type == "cloze_mcq":
            create_and_save_cloze_exercise_items(
                project,
                clara_project_internal,
                text_obj,
                exercise_type,
                n_examples,
                n_distractors,
                seed,
                rng,
                callback=callback,
            )
        else:
            post_task_update(callback, f"Error: unsupported exercise type {exercise_type}")
            post_task_update(callback, "error")
            return
    except Exception as e:
        post_task_update(callback, "Error when creating exercise items")
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, "error")


# ---------------- Cloze MCQ generation ----------------

def create_and_save_cloze_exercise_items(
    project,
    clara_project_internal,
    text_obj,
    exercise_type: str,
    n_examples: int,
    n_distractors: int,
    seed: int,
    rng: random.Random,
    callback=None,
):
    exercise_targets = select_random_cloze_targets(text_obj, n_examples, rng)

    params = {
        "n_distractors": n_distractors,
        "gpt_model": MODEL_NAME,
    }

    items, cost_dict = asyncio.run(
        process_cloze_exercise_targets(project, text_obj, params, exercise_targets, callback=callback)
    )

    payload = {
        "schema_version": "1.0",
        "exercise_type": exercise_type,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "selection_method": "random",
        "language": {"l2": project.l2, "gloss": project.l1},
        "params": {"n_examples": n_examples, "n_distractors": n_distractors, "seed": seed},
        "items": items,
    }

    # Store exercises + costs
    clara_project_internal.save_exercises(exercise_type, payload)
    store_cost_dict(cost_dict, project, project.user)

    post_task_update(callback, "finished")


def select_random_cloze_targets(text_obj, n_examples: int, rng: random.Random):
    """
    Return list of dict targets containing enough info to build prompts.
    Stores actual segment and CE object references for V1 convenience.
    """
    candidates = []
    for p_i, page in enumerate(getattr(text_obj, "pages", [])):
        for s_i, seg in enumerate(getattr(page, "segments", [])):
            eligible = [ce for ce in getattr(seg, "content_elements", []) if is_eligible_target(ce)]
            if eligible:
                candidates.append((p_i, s_i, seg, eligible))

    rng.shuffle(candidates)

    selected = []
    for (p_i, s_i, seg, eligible) in candidates:
        ce = rng.choice(eligible)
        selected.append(
            {
                "page_index": p_i,
                "segment_index": s_i,
                "segment": seg,
                "target_ce": ce,
            }
        )
        if len(selected) >= n_examples:
            break

    return selected


def is_eligible_target(content_element) -> bool:
    # V1: avoid punctuation, very short tokens, etc.
    if getattr(content_element, "is_punctuation", False):
        return False
    ce_type = getattr(content_element, "type", None)
    surface = (getattr(content_element, "content", "") or "").strip()
    if ce_type != "Word" or len(surface) < 2:
        return False
    return True


async def process_cloze_exercise_targets(project, text_obj, params, exercise_targets, callback=None):
    tasks = [
        asyncio.create_task(generate_cloze_exercise_item(t, project, text_obj, params, callback=callback))
        for t in exercise_targets
    ]
    results = await asyncio.gather(*tasks)

    items = []
    total_cost = {}

    for item, cost_dict in results:
        items.append(item)
        total_cost = combine_cost_dicts(total_cost, cost_dict)

    return items, total_cost


async def generate_cloze_exercise_item(exercise_target, project, text_obj, params, callback=None):
    seg = exercise_target["segment"]
    ce = exercise_target["target_ce"]

    segment_text = seg.to_text("plain")
    target_surface = ce.to_text("plain")

    # annotations might be dict or object; handle both
    ann = getattr(ce, "annotations", {}) or {}
    if isinstance(ann, dict):
        lemma = ann.get("lemma")
        pos = ann.get("pos")
    else:
        lemma = getattr(ann, "lemma", None)
        pos = getattr(ann, "pos", None)

    page_index = exercise_target["page_index"]
    seg_index = exercise_target["segment_index"]
    segments = text_obj.pages[page_index].segments

    context_before = segments[seg_index - 1].to_text("plain") if seg_index - 1 >= 0 else None
    context_after = segments[seg_index + 1].to_text("plain") if seg_index + 1 < len(segments) else None

    model = params["gpt_model"]
    n_distractors = params["n_distractors"]

    prompt = build_cloze_distractor_prompt(
        segment_text=segment_text,
        target_surface=target_surface,
        lemma=lemma,
        pos=pos,
        context_before=context_before,
        context_after=context_after,
        n_distractors=n_distractors,
        l2=project.l2,
    )

    resp = await get_api_chatgpt4_response(prompt, config_info={"gpt_model": model}, callback=callback)

    # Some wrappers return (json, cost_dict). Handle both.
    cost_dict = {}
    if isinstance(resp, (list, tuple)) and len(resp) == 2 and isinstance(resp[1], dict):
        resp_json, cost_dict = resp[0], resp[1]
    else:
        resp_json = resp

    choices = normalise_choices(resp_json, correct=target_surface)

    item = {
        "page_index": page_index,
        "segment_index": seg_index,
        "target": {"surface": target_surface, "lemma": lemma, "pos": pos},
        "segment": {
            "text": segment_text,
            "text_with_blank": blank_out(segment_text, target_surface),
            "context_before": context_before,
            "context_after": context_after,
        },
        "choices": choices,
        "notes": {"generation_model": model, "prompt_version": CLOZE_PROMPT_VERSION},
    }

    return item, cost_dict


def build_cloze_distractor_prompt(
    *,
    segment_text,
    target_surface,
    lemma,
    pos,
    context_before,
    context_after,
    n_distractors,
    l2,
):
    return f"""
You are generating distractors for a language-learning cloze multiple-choice question.

Language: {l2}
Task: Provide {n_distractors} distractors for the TARGET token in the SEGMENT below.

SEGMENT:
{segment_text}

CONTEXT (optional):
Before: {context_before}
After: {context_after}

TARGET:
surface = {target_surface}
lemma = {lemma}
pos = {pos}

Rules:
- Distractors should match the target POS (or as close as possible).
- Distractors must be plausible to a learner but incorrect in this exact segment/context.
- Do NOT include the correct answer among distractors.
- Return STRICT JSON in this schema:
{{
  "distractors": [
    {{"form": ".", "reason": "short reason"}},
    ...
  ]
}}
""".strip()


def normalise_choices(resp_json, correct: str):
    distractors = resp_json.get("distractors", []) if isinstance(resp_json, dict) else []

    forms = []
    for d in distractors:
        f = (d.get("form") or "").strip()
        if not f:
            continue
        if f.lower() == correct.lower():
            continue
        if f.lower() in {x.lower() for x in forms}:
            continue
        forms.append(f)

    choices = [{"form": correct, "is_correct": True, "reason": "correct"}]
    for f in forms:
        choices.append({"form": f, "is_correct": False, "reason": "distractor"})

    # If we got too few distractors, we just ship fewer in V1 (fine for now).
    return choices


def blank_out(segment_text: str, target_surface: str) -> str:
    # V1: naive replace first occurrence.
    return segment_text.replace(target_surface, "____", 1)
