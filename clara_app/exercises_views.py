# clara_app/exercises_views.py

from datetime import datetime, timezone
import asyncio
import json
import random
import traceback
import uuid
import hashlib
from typing import Tuple
import yaml
import os
import pprint
import html
from pathlib import Path
import re

from django.contrib import messages
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django_q.tasks import async_task

from .models import CLARAProject
from .clara_main import CLARAProjectInternal
from .clara_classes import ContentElement

from .clara_chatgpt4 import get_api_chatgpt4_response
from .call_ai_providers import call_model_provider, compute_cost_for_usage

from .utils import (
    user_has_a_project_role,
    make_asynch_callback_and_report_id,
    get_task_updates,
    store_cost_dict,
)
from .clara_utils import post_task_update, post_task_update_async, get_config, absolute_file_name, file_exists
from .clara_coherent_images_utils import combine_cost_dicts

config = get_config()

EXERCISE_TYPES = [
    ("cloze_mcq", "Cloze (multiple choice)"),
]

MODEL_FOR_EXERCISE_GENERATION = 'gpt-5.2'

CLOZE_PROMPT_VERSION = "cloze_distractors_v1"

MODELS_YAML_PATH = absolute_file_name("$CLARA/clara_app/ai_provider_models.yaml")

TIMEOUT_IN_SECONDS = 300

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
    default_learner_level = "intermediate"
    
    exercise_type = request.POST.get("exercise_type", "cloze_mcq").strip()
    learner_level = request.POST.get("learner_level", default_learner_level).strip()
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
    # This version fails if there are any inconsistencies.
    #text_obj = clara_project_internal.get_internalised_text_exact()
    # This version is more robust to small inconsistencies but can in bad cases produce weird results
    text_obj = clara_project_internal.get_internalised_text()
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
        learner_level=learner_level, 
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
    learner_level: str = "intermediate",
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
                learner_level=learner_level,
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
    learner_level: str = "intermediate",
    callback=None,
):
    exercise_set_id = uuid.uuid4().hex

    exercise_targets = select_random_cloze_targets(text_obj, n_examples, rng)

    params = {
        "n_distractors": n_distractors,
        "gpt_model": MODEL_FOR_EXERCISE_GENERATION,
    }

    items, cost_dict = asyncio.run(
        process_cloze_exercise_targets(project, text_obj, params, exercise_targets, rng, learner_level=learner_level, callback=callback)
    )

    # Assign stable item_ids
    for item in items:
        raw_key = (
            f"{item['page_index']}|"
            f"{item['segment_index']}|"
            f"{item['target']['surface']}|"
            f"{item['segment']['text_with_blank']}"
        )
        item["item_id"] = hashlib.sha1(raw_key.encode("utf-8")).hexdigest()[:12]

    payload = {
        "exercise_set_id": exercise_set_id,
        "schema_version": "1.0",
        "exercise_type": exercise_type,
        "learner_level": learner_level,
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
    candidates = []
    for p_i, page in enumerate(getattr(text_obj, "pages", [])):
        for s_i, seg in enumerate(getattr(page, "segments", [])):
            eligible_idxs = [
                idx for idx, ce in enumerate(getattr(seg, "content_elements", []))
                if is_eligible_target(ce)
            ]
            if eligible_idxs:
                candidates.append((p_i, s_i, seg, eligible_idxs))

    rng.shuffle(candidates)

    selected = []
    for (p_i, s_i, seg, eligible_idxs) in candidates:
        ce_idx = rng.choice(eligible_idxs)
        ce = seg.content_elements[ce_idx]
        selected.append(
            {
                "page_index": p_i,
                "segment_index": s_i,
                "segment": seg,
                "target_ce": ce,
                "target_ce_index": ce_idx,
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


async def process_cloze_exercise_targets(project, text_obj, params, exercise_targets, rng: random.Random, learner_level="intermediate", callback=None):
    tasks = [
        asyncio.create_task(generate_cloze_exercise_item(t, project, text_obj, params, rng, learner_level=learner_level, callback=callback))
        for t in exercise_targets
    ]
    results = await asyncio.gather(*tasks)

    items = []
    total_cost = {}

    for item, cost_dict in results:
        items.append(item)
        total_cost = combine_cost_dicts(total_cost, cost_dict)

    return items, total_cost


async def generate_cloze_exercise_item(exercise_target, project, text_obj, params, rng: random.Random, learner_level="intermediate", callback=None):
    seg = exercise_target["segment"]
    ce = exercise_target["target_ce"]
    ce_index = exercise_target["target_ce_index"]

    segment_text = seg.to_text("plain")
    target_surface = ce.to_text("plain")

    segment_text_with_blank = blank_out_segment(seg, ce_index)

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

    full_context_html = full_text_with_highlighted_segment_text(text_obj, page_index, seg_index)

    model = params["gpt_model"]
    n_distractors = params["n_distractors"]

    prompt = build_cloze_distractor_prompt(
        learner_level=learner_level,
        segment_text=segment_text,
        segment_text_with_blank=segment_text_with_blank,
        segment_text_with_blank_and_full_context=full_context_html,
        target_surface=target_surface,
        lemma=lemma,
        pos=pos,
        context_before=context_before,
        context_after=context_after,
        n_distractors=n_distractors,
        l2=project.l2,
    )

    api_call_obj = await get_api_chatgpt4_response(prompt, config_info={"gpt_model": model}, callback=callback)

    resp_str = api_call_obj.response
    cost = api_call_obj.cost

    resp_json = coerce_json_dict(resp_str)
    choices = normalise_choices(resp_json, rng, correct=target_surface)

    item = {
        "learner_level": learner_level,
        "page_index": page_index,
        "segment_index": seg_index,
        "target": {"surface": target_surface, "lemma": lemma, "pos": pos},
        "segment": {
            "text": segment_text,
            "text_with_blank": segment_text_with_blank,
            "context_before": context_before,
            "context_after": context_after,
        },
        "full_text": {"format": "html",
                      "content": full_context_html},
        "choices": choices,
        "notes": {"generation_model": model, "prompt_version": CLOZE_PROMPT_VERSION},
    }

    cost_dict = { 'exercises_mcq': cost }

    return item, cost_dict

def full_text_with_highlighted_segment_text(text_obj, page_index, seg_index):
    parts = []
    pages = getattr(text_obj, "pages", []) or []

    for p_i, page in enumerate(pages):
        segments = getattr(page, "segments", []) or []
        for s_i, segment in enumerate(segments):
            escaped_segment = html.escape(segment.to_text("plain"))
            if p_i == page_index and s_i == seg_index:
                # Wrap in mark
                marked = f"<mark>{escaped_segment}</mark>"
                parts.append(marked)
            else:
                parts.append(escaped_segment)

        parts.append("")  # blank line between pages (later becomes <br><br>)

    # Turn newlines into <br> so it displays naturally in HTML
    text = "\n".join(parts).strip()

    # Collapse any run of 3+ newlines to exactly 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    return text.replace("\n", "<br>\n")

def build_cloze_distractor_prompt(
    *,
    learner_level,
    segment_text,
    segment_text_with_blank=None,
    segment_text_with_blank_and_full_context=None,
    target_surface,
    lemma,
    pos,
    context_before,
    context_after,
    n_distractors,
    l2,
):
    blank_block = ""
    if segment_text_with_blank:
        blank_block = f"\nSEGMENT_WITH_BLANK:\n{segment_text_with_blank}\n"

    return f"""
You are generating distractors for a language-learning cloze multiple-choice question.

Language: {l2}
Task: Provide EXACTLY {n_distractors} distractors for the TARGET token in the SEGMENT below.

LEARNER LEVEL: {learner_level}

Guidance by level:
- beginner: prefer very common words; avoid rare vocabulary and subtle semantic distinctions
- low_intermediate: common words; allow simple contrasts; avoid idioms/rare senses
- intermediate: allow moderate vocabulary; distractors can be slightly subtler
- advanced: allow nuanced near-misses; still ensure only one clearly correct answer

SEGMENT:
{segment_text}{blank_block}

CONTEXT:
Before: {context_before}
After: {context_after}

FULL TEXT (for context; the target segment is highlighted):
{segment_text_with_blank_and_full_context}

TARGET:
surface = {target_surface}
lemma = {lemma}
pos = {pos}

Rules:
- Output EXACTLY {n_distractors} distractors.
- Each distractor must be a SINGLE TOKEN (no spaces). Keep punctuation only if TARGET is punctuation.
- Do NOT include the correct answer (surface form) among distractors.

- Match the TARGET’s grammatical behavior as closely as possible:
  * If pos is VERB: match the same verb form (e.g., bare form vs -ing vs past vs 3sg).
  * If pos is NOUN: match number (sing/pl) and typical countability feel.
  * If pos is PRON or DET: match pronoun/determiner type (e.g., possessive determiner vs object pronoun),
    and match person/number as closely as possible.
  * If pos is ADP (preposition): choose other common prepositions that are plausible in similar frames.

- Distractors must be CLEARLY INCORRECT in this specific context.
  They should be tempting mistakes a learner might choose,
  NOT alternative correct paraphrases.

- Avoid true synonyms or near-synonyms that a teacher could reasonably accept as correct.
  If a native speaker might judge the distractor as acceptable,
  DO NOT use it.

- Prefer these types of learner-error distractors:
  * wrong collocation ("reflect about" instead of "reflect on")
  * wrong article/determiner choice
  * agreement errors
  * pronoun reference confusion
  * tense/aspect mismatch
  * overgeneralized rule application
  * similar-looking or similar-sounding words
  * preposition confusion
  * incorrect but plausible function word swaps

- The sentence should usually remain grammatical,
  but sound wrong, unnatural, or semantically incorrect to a fluent speaker.

- Before returning your answer:
  For each distractor, ask:
  "Would a teacher accept this as correct?"
  If yes, discard it and generate a new one.

- Return STRICT JSON in this schema (no extra keys, no prose):
{{
  "distractors": [
    {{"form": ".", "reason": "short reason"}},
    ...
  ]
}}
""".strip()

def coerce_json_dict(resp_json):
    """
    get_api_chatgpt4_response often returns a JSON *string*.
    Convert it to a dict, stripping code-fences if needed.
    """
    if isinstance(resp_json, dict):
        return resp_json

    if isinstance(resp_json, str):
        s = resp_json.strip()

        # Remove ```json fences if the model adds them
        if s.startswith("```"):
            s = s.strip("`")
            # if it begins with 'json\n', drop that prefix
            if s.lower().startswith("json"):
                s = s[4:].lstrip()

        # Try direct JSON parse
        try:
            return json.loads(s)
        except Exception:
            # Last-resort: try to extract the first {...} block
            start = s.find("{")
            end = s.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(s[start : end + 1])
                except Exception:
                    pass

    # Give up: return empty dict so downstream behaves safely
    return {}

def normalise_choices(resp_json, rng: random.Random, correct: str):
    distractors = resp_json.get("distractors", []) if isinstance(resp_json, dict) else []

    choices = [{"form": correct, "is_correct": True, "reason": "correct"}]

    seen = {correct.lower()}
    for d in distractors:
        f = (d.get("form") or "").strip()
        r = (d.get("reason") or "distractor").strip()
        if not f:
            continue
        if f.lower() in seen:
            continue
        seen.add(f.lower())
        choices.append({"form": f, "is_correct": False, "reason": r})

    rng.shuffle(choices)

    return choices

def blank_out_segment(seg, target_idx: int) -> str:
    seg_copy = seg.clone()

    seg_copy.content_elements[target_idx] = ContentElement(
        "Word",
        "____",
        {}
    )

    return seg_copy.to_text("plain")

# ---------------- Runtime ----------------

@login_required
def run_exercises(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    exercise_type = request.GET.get("type", "cloze_mcq")
    item_index = int(request.GET.get("item", "0"))

    all_exercises = clara_project_internal.load_exercises(exercise_type)
    if not all_exercises:
        messages.error(request, f"Unable to find any exercises for this project.")
        return redirect("project_detail", project_id=project_id)

    exercise_data = clara_project_internal.load_exercises(exercise_type)

    if not exercise_data:
        messages.error(request, f"No exercises of type '{exercise_type}' found.")

    items = exercise_data.get("items", [])

    if not items:
        messages.error(request, "No exercise items available.")
        return redirect("project_detail", project_id=project_id)

    # clamp index
    if item_index < 0:
        item_index = 0
    if item_index >= len(items):
        item_index = len(items) - 1

    item = items[item_index]

    feedback = None
    selected = None

    if request.method == "POST":
        selected = request.POST.get("choice")
        correct_choice = next(c for c in item["choices"] if c["is_correct"])

        if selected == correct_choice["form"]:
            feedback = {
                "correct": True,
                "message": "Correct!",
                "reason": correct_choice.get("reason", "")
            }
        else:
            wrong = next(c for c in item["choices"] if c["form"] == selected)
            feedback = {
                "correct": False,
                "message": "Incorrect.",
                "reason": wrong.get("reason", ""),
                "correct_form": correct_choice["form"],
                "correct_reason": correct_choice.get("reason", "")
            }

    next_index = item_index + 1 if item_index + 1 < len(items) else None

    return render(
        request,
        "clara_app/run_exercises.html",
        {
            "project": project,
            "exercise_type": exercise_type,
            "item_index": item_index,
            "item": item,
            "feedback": feedback,
            "selected": selected,
            "next_index": next_index,
            "total_items": len(items),
        }
    )

@login_required
def browse_exercises(request: HttpRequest, project_id: int) -> HttpResponse:
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    exercise_type = request.GET.get("type", "cloze_mcq")
    item_index = int(request.GET.get("item", "0"))
    show_answers = request.GET.get("show", "") == "answers"

    all_exercises = clara_project_internal.load_all_exercises()
    if not all_exercises:
        messages.error(request, "Unable to find any exercises for this project.")
        return redirect("project_detail", project_id=project_id)

    exercise_data = clara_project_internal.load_exercises(exercise_type)

    if not exercise_data:
        messages.error(request, f"No exercises of type '{exercise_type}' found.")
        return redirect("project_detail", project_id=project_id)
    
    items = exercise_data.get("items", [])
    if not items:
        messages.error(request, "No exercise items available.")
        return redirect("project_detail", project_id=project_id)

    # clamp
    item_index = max(0, min(item_index, len(items) - 1))
    item = items[item_index]

    prev_index = item_index - 1 if item_index > 0 else None
    next_index = item_index + 1 if item_index + 1 < len(items) else None

    # convenience for template
    correct_form = None
    if show_answers:
        try:
            correct_form = next(c["form"] for c in item.get("choices", []) if c.get("is_correct"))
        except StopIteration:
            correct_form = None

    return render(
        request,
        "clara_app/browse_exercises.html",
        {
            "project": project,
            "exercise_types": EXERCISE_TYPES,   # already defined at top :contentReference[oaicite:1]{index=1}
            "exercise_type": exercise_type,
            "item_index": item_index,
            "total_items": len(items),
            "item": item,
            "prev_index": prev_index,
            "next_index": next_index,
            "show_answers": show_answers,
            "correct_form": correct_form,
            "exercise_meta": {k: v for k, v in exercise_data.items() if k != "items"},
        },
    )

def exercises_exist_for_project(project_id: int):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    all_exercises = clara_project_internal.load_all_exercises()
    if not all_exercises:
        return False
    else:
        return True
    
# ------------------------------------------------------------------
# AI Panel: Judge Exercises
# ------------------------------------------------------------------

def ai_panel_judge_exercises(request, project_id, status="start"):

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

    # exercise_sets is expected to be dict: {exercise_set_id: payload}
    # If you currently only store one payload per exercise_type, make it a dict here:
    # exercise_sets = {payload["exercise_set_id"]: payload} if payload else {}

    all_exercises = clara_project_internal.load_all_exercises()

    if not all_exercises or not isinstance(all_exercises, dict):
        messages.error(request, "Error: no valid exercises to evaluate.")

    exercise_types = list(all_exercises.keys())

    # ---- Selection (nullable) ----

    # In this first version, we only have one kind of exercise
    exercise_type = exercise_types[0]

    exercise_set = clara_project_internal.load_exercises(exercise_type)
    exercise_set_id = clara_project_internal.get_current_exercise_set_id(exercise_type)

    if not "items" in exercise_set:
         messages.error(request, "Error: no valid exercises to evaluate.")
         return redirect('ai_panel_judge_exercises', project_id, "initial")
    
    exercise_items = exercise_set.get("items", [])

    if request.method == "GET":
        return render(
            request,
            "clara_app/ai_panel_judge_exercises.html",
            {
                "project": project,
                "exercise_type": exercise_type,
                "exercise_items": exercise_items,     # list or []
                "available_models": get_available_judge_models(), 
            },
        )

    # POST: submit judging job (requires a selected set)

    item_ids = request.POST.getlist("item_ids")
    judge_models = request.POST.getlist("judge_models")
    if not item_ids:
        messages.error(request, "Select at least one exercise item.")
        return redirect('ai_panel_judge_exercises', project_id, "initial")
    if not judge_models:
        messages.error(request, "Select at least one judge model.")
        return redirect('ai_panel_judge_exercises', project_id, "initial")

    callback, report_id = make_asynch_callback_and_report_id(request, "ai_panel_judge_exercises")

    async_task(
        create_and_save_ai_panel_judgements,   # your async fan-out/fan-in
        project,
        clara_project_internal,
        exercise_type,
        exercise_set_id,
        item_ids,
        judge_models,
        callback=callback,
    )

    return redirect("ai_panel_judge_exercises_monitor", project_id, report_id)

@login_required
def ai_panel_judge_exercises_monitor(request, project_id, report_id):
    project = get_object_or_404(CLARAProject, pk=project_id)

    context = {
        "project": project,
        "report_id": report_id,
    }

    return render(request, "clara_app/ai_panel_judge_exercises_monitor.html", context)

@login_required
def ai_panel_judge_exercises_status(request, project_id, report_id):
    msgs = get_task_updates(report_id)

    if "error" in msgs:
        status = "error"
    elif "finished" in msgs:
        status = "finished"
    else:
        status = "unknown"

    return JsonResponse({"messages": msgs, "status": status})

def create_and_save_ai_panel_judgements(
    project,
    clara_project_internal,
    exercise_type: str,
    exercise_set_id: str,
    selected_item_ids: list[str],
    selected_models: list[str],
    callback=None,
):
    # Load the exercise set
    exercises_payload = clara_project_internal.load_exercises(exercise_type)
    if not exercises_payload:
        post_task_update(callback, f"Error: no exercises found for type '{exercise_type}'")
        post_task_update(callback, "error")
        return

    items = exercises_payload.get("items", [])
    items_by_id = {it.get("item_id"): it for it in items if it.get("item_id")}

    # Filter to selected items (defensive)
    target_items = [items_by_id[iid] for iid in selected_item_ids if iid in items_by_id]
    if not target_items:
        post_task_update(callback, "Error: no valid items selected")
        post_task_update(callback, "error")
        return

    judge_run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    post_task_update(callback, f"Judging run: {judge_run_id}")
    post_task_update(callback, f"Items: {len(target_items)}; Models: {len(selected_models)}")

    # ---- Fan-out/fan-in ----
    # Build cfg map from what the UI offered (so values match)
    available_models = get_available_judge_models()
    model_cfg_by_name = {m["value"]: m["cfg"] for m in available_models}

    # Fan-out/fan-in
    post_task_update(callback, "Submitting judging calls...")
    run_results, cost_dict = asyncio.run(
        process_ai_panel_judging_targets(
            target_items,
            selected_models,
            model_cfg_by_name,
            timeout=TIMEOUT_IN_SECONDS,
            callback=callback
        )
    )

    wrapped_results = {}

    for item in target_items:
        item_id = item["item_id"]

        snapshot = {
            "learner_level": item.get("learner_level"),
            "text_with_blank": item.get("segment", {}).get("text_with_blank"),
            "full_text": item.get("full_text"),
            "context_before": item.get("segment", {}).get("context_before"),
            "context_after": item.get("segment", {}).get("context_after"),
            "target": item.get("target"),
            "choices": item.get("choices"),
        }

        wrapped_results[item_id] = {
            "item_snapshot": snapshot,
            "models": run_results.get(item_id, {})
        }

    # Merge into stored judgements blob
    d = load_exercise_judgements_dict(clara_project_internal)
    jud = d["judgements"]

    jud.setdefault(exercise_type, {})
    jud[exercise_type].setdefault(exercise_set_id, {})
    jud[exercise_type][exercise_set_id][judge_run_id] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "models": selected_models,
        "items": wrapped_results,
        "cost": cost_dict,
    }

    save_exercise_judgements_dict(clara_project_internal, d, user=project.user.username)

    # Optional: also store cost via your existing store_cost_dict() if you want it in the main cost logs
    # store_cost_dict(cost_dict, project, project.user)

    post_task_update(callback, "Finished judging.")
    post_task_update(callback, "finished")

async def process_ai_panel_judging_targets(
    target_items: list[dict],
    selected_models: list[str],
    model_cfg_by_name: dict,
    timeout: int = 60,
    callback=None
) -> Tuple[dict, dict]:
    """
    Fan-out/fan-in across (item, model).
    Returns:
      - run_results: item_id -> model_name -> result
      - cost_dict: aggregated usage+cost
    """
    tasks = []
    metas = []  # (item_id, model_name, cfg)

    for item in target_items:
        item_id = item.get("item_id")
        for model_name in selected_models:
            cfg = model_cfg_by_name.get(model_name)
            if not cfg:
                continue
            metas.append((item_id, model_name, cfg))
            tasks.append(
                asyncio.create_task(
                    _judge_one_item_with_one_model(item, cfg, timeout, callback=callback)
                )
            )

    results = await asyncio.gather(*tasks, return_exceptions=True)

    run_results = {}   # item_id -> model_name -> result
    usage_totals = {}  # provider -> dict of numeric usage fields
    cost_totals = {}   # provider -> float

    for (item_id, model_name, cfg), r in zip(metas, results):
        run_results.setdefault(item_id, {})

        if isinstance(r, Exception):
            run_results[item_id][model_name] = {
                "provider": cfg.get("provider"),
                "model": cfg.get("model"),
                "verdict": "needs_fix",
                "confidence": 0.0,
                "issues": [{"distractor": "", "problem": f"exception: {r}", "suggestion": ""}],
                "raw_text": "",
                "parsed": {},
            }
            continue

        result_dict, usage, cost = r
        run_results[item_id][model_name] = result_dict

        prov = cfg.get("provider")
        usage_totals.setdefault(prov, {})
        for k, v in (usage or {}).items():
            if isinstance(v, (int, float)):
                usage_totals[prov][k] = usage_totals[prov].get(k, 0) + v
        cost_totals[prov] = cost_totals.get(prov, 0.0) + float(cost or 0.0)

    cost_dict = {"usage": usage_totals, "cost": cost_totals}
    return run_results, cost_dict

async def _judge_one_item_with_one_model(
    item: dict,
    model_cfg: dict,
    timeout: int,
    callback=None
) -> Tuple[dict, dict, float]:
    """
    Returns (result_dict, usage_dict, cost_float).
    Uses asyncio.to_thread because provider calls are requests-based.
    """
    system_prompt, user_prompt = build_cloze_judging_prompt(item)

    provider = model_cfg["provider"]
    chat_url = model_cfg["chat_url"]
    api_key = model_cfg["api_key"]
    model = model_cfg["model"]

    content, usage = await asyncio.to_thread(
        call_model_provider,
        provider,
        chat_url,
        api_key,
        model,
        system_prompt,
        user_prompt,
        timeout
    )

    parsed = _json_from_model_output(content)

    # normalize result
    verdict = parsed.get("verdict", "unparsed")
    if verdict not in ("ok", "minor_suggestion", "needs_fix", "unparsed"):
        verdict = "needs_fix" 

    conf = parsed.get("confidence", "unparsed")
    try:
        conf = float(conf)
    except Exception:
        conf = 0.0

    issues = parsed.get("issues")
    if not isinstance(issues, list):
        issues = []

    result = {
        "raw_text": content,
        "parsed": parsed,
        "provider": provider,
        "model": model,
        "verdict": verdict,
        "confidence": conf,
        "issues": issues,
        "raw": content[:2000],  # small debug window, optional
    }

    # cost (optional; safe if pricing is missing/zero)
    try:
        cost = compute_cost_for_usage(model_cfg, usage or {})
    except Exception:
        cost = 0.0

    return result, (usage or {}), cost


def build_cloze_judging_prompt(item: dict) -> Tuple[str, str]:
    seg = item.get("segment") or {}
    target = item.get("target") or {}

    full_text = item.get("full_text", {})
    full_html = full_text.get("content") if isinstance(full_text, dict) else None
    
    choices = item.get("choices") or []
    learner_level = item.get("learner_level") or "intermediate"

    correct = [c for c in choices if c.get("is_correct")]
    distractors = [c for c in choices if not c.get("is_correct")]

    # Format distractors with rationale
    distractor_lines = []
    for d in distractors:
        distractor_lines.append(
            f"- {d.get('form')} :: rationale = {d.get('reason')}"
        )

    system_prompt = (
    "You are a careful and fair CALL evaluation assistant. "
    "You evaluate cloze multiple-choice items designed by a competent CALL researcher. "
    "Assume good faith and pedagogical intent. "
    "Your task is not to search for minor flaws, but to determine whether each distractor "
    "successfully fulfills its stated pedagogical purpose."
    )

    cloze_evaluation_rubric = get_cloze_judging_rubric_text(learner_level)

    user_prompt = user_prompt = f"""
{cloze_evaluation_rubric}

SEGMENT (with blank):
{seg.get("text_with_blank") or ""}

CONTEXT:
Before: {seg.get("context_before") or ""}
After: {seg.get("context_after") or ""}

FULL TEXT (target segment highlighted):
{full_html or "(missing full text)"}

TARGET:
surface = {target.get("surface")}
lemma = {target.get("lemma")}
pos = {target.get("pos")}

CORRECT ANSWER:
{[c.get("form") for c in correct]}

DISTRACTORS (with intended rationale):
{chr(10).join(distractor_lines)}

Verdict guidelines:

- "ok" → All distractors fulfill their intended pedagogical function.
- "minor_suggestion" → The item works pedagogically, but there are small improvements possible.
- "needs_fix" → At least one distractor has a clear and substantive flaw.

Return STRICT JSON ONLY (no markdown, no explanations outside JSON):

{{
  "verdict": "ok" | "minor_suggestion" | "needs_fix",
  "confidence": 0.0-1.0,
  "summary": "brief one-sentence overall explanation",
  "issues": [
    {{
      "distractor": "...",
      "problem": "...",
      "suggestion": "...",
      "severity": "major" | "minor"
    }}
  ]
}}
""".strip()

    return system_prompt, user_prompt

def get_cloze_judging_rubric_text(learner_level: str) -> str:
    return f"""
Evaluate the distractors for the following cloze multiple-choice item.

LEARNER LEVEL: {learner_level}

Guidance by level:
- beginner: be tolerant of simpler/less subtle distractors; only flag clearly misleading or invalid ones
- low_intermediate: similar tolerance; avoid requiring nuanced semantic distinctions
- intermediate: moderate subtlety is fine
- advanced: allow nuanced near-misses; still must be clearly wrong in context

IMPORTANT ORIENTATION:
- Assume the item was designed by a competent CALL researcher.
- The goal is to VALIDATE design intent, not to nitpick.
- Only flag issues that are clearly pedagogically significant.
- Minor improvements should be classified as "minor_suggestion".
- Reserve "needs_fix" for clear and substantive problems.
  If you are uncertain whether an issue rises to a substantive pedagogical flaw, prefer "minor_suggestion" over "needs_fix".

Evaluation criteria:

1. Each distractor must be a SINGLE TOKEN.
2. Each distractor should have similar grammatical behavior (POS/form) as the target.
3. The provided "reason" explains the intended pedagogical function.
   Judge whether the distractor SUCCESSFULLY fulfills this intended function in context.
4. Distractors should be plausible near-misses but clearly incorrect in THIS specific context.
5. Do NOT penalize minor stylistic issues.
6. Only classify as "needs_fix" if there is a clear and substantive pedagogical problem
   (e.g., ambiguity making it potentially correct, wrong POS, nonsensical form,
   or clear failure to match its stated rationale).
"""

def load_exercise_judgements_dict(clara_project_internal):
    raw = clara_project_internal.load_text_version_or_null("exercise_judgements")
    if not raw:
        return {"schema_version": "1.0", "judgements": {}}
    try:
        d = json.loads(raw)
        if not isinstance(d, dict):
            return {"schema_version": "1.0", "judgements": {}}
        d.setdefault("schema_version", "1.0")
        d.setdefault("judgements", {})
        return d
    except Exception:
        return {"schema_version": "1.0", "judgements": {}}

def save_exercise_judgements_dict(clara_project_internal, d, *, user):
    text = json.dumps(d, indent=2, ensure_ascii=False) + "\n"
    clara_project_internal.save_text_version(
        "exercise_judgements",
        text,
        source="ai_generated",
        user=user,
    )
    
def _json_from_model_output(text: str) -> dict:
    if not text:
        return {}
    s = text.strip()

    # Strip ```...``` fences
    if s.startswith("```"):
        s = s.strip("`").strip()
        if s.lower().startswith("json"):
            s = s[4:].lstrip()

    # Direct parse
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        pass

    # Extract first {...} block
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            obj = json.loads(s[start:end+1])
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}

    return {}

# Viewing panel of AI judges results
@login_required
def browse_exercise_judgements(request, project_id):
    """
    Human-friendly browser for the exercise_judgements blob:
      schema_version: "1.0"
      judgements[exercise_type][exercise_set_id][judge_run_id] = {
        created_at, models, items, cost, ...
      }
    """
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    d = load_exercise_judgements_dict(clara_project_internal)
    jud = (d or {}).get("judgements", {}) or {}

    # ---------- available selectors ----------
    exercise_types = sorted(jud.keys())

    # defaults
    selected_exercise_type = request.GET.get("exercise_type") or (exercise_types[0] if exercise_types else "")
    sets_dict = jud.get(selected_exercise_type, {}) if selected_exercise_type else {}
    exercise_set_ids = sorted(sets_dict.keys())

    selected_exercise_set_id = request.GET.get("exercise_set_id") or (exercise_set_ids[0] if exercise_set_ids else "")
    runs_dict = sets_dict.get(selected_exercise_set_id, {}) if selected_exercise_set_id else {}
    # run ids look like timestamps; descending is usually nicest
    run_ids = sorted(runs_dict.keys(), reverse=True)

    selected_run_id = request.GET.get("judge_run_id") or (run_ids[0] if run_ids else "")

    run_payload = runs_dict.get(selected_run_id, {}) if selected_run_id else {}
    items = (run_payload.get("items") or {}) if isinstance(run_payload, dict) else {}

    # Also load the exercise set, so we can show extra context if needed
    # (and/or show correct answer, segment text, etc.)
    exercises_payload = clara_project_internal.load_exercises(selected_exercise_type) if selected_exercise_type else {}
    judged_rows = []
    # items is a dict indexed by item_id
    for item_id in items:
        exercises_payload = items[item_id]
        snapshot = exercises_payload.get("item_snapshot", {}) if isinstance(exercises_payload, dict) else {}
        model_map = exercises_payload.get("models", {}) if isinstance(exercises_payload, dict) else {}
        judged_rows.append({
            "item_id": item_id,
            "snapshot": snapshot,
            "model_map": model_map,
        })

    # optional: stable order
    judged_rows.sort(key=lambda r: r["item_id"])

    if not exercise_types:
        messages.info(request, "No AI-panel judgements found yet for this project.")
        return render(
            request,
            "clara_app/browse_exercise_judgements.html",
            {
                "project": project,
                "exercise_types": [],
            },
        )

    context = {
        "project": project,

        "exercise_types": exercise_types,
        "selected_exercise_type": selected_exercise_type,

        "exercise_set_ids": exercise_set_ids,
        "selected_exercise_set_id": selected_exercise_set_id,

        "run_ids": run_ids,
        "selected_run_id": selected_run_id,

        "run_payload": run_payload,     # created_at, models, cost...
        "judged_items": items,          # item_id -> model_name -> result
        "judged_rows": judged_rows,
    }

    return render(request, "clara_app/browse_exercise_judgements.html", context)

def exercise_judgements_exist_for_project(project_id: int):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    all_exercise_judgements = load_exercise_judgements_dict(clara_project_internal)
    if not all_exercise_judgements:
        return False
    else:
        return True

def _judge_model_cfg_by_value(available_models: list[dict]) -> dict:
    return {m["value"]: m for m in available_models}

def get_available_judge_models():
    """
    Load models from shared models.yaml.
    Only return models with valid API keys.
    Structure matches existing template expectations.
    """
    if not file_exists(MODELS_YAML_PATH):
        return []

    models_cfg_raw = load_yaml(MODELS_YAML_PATH)
    models_cfg = parse_models(models_cfg_raw)

    #print(f'models_cfg')
    #pprint.pprint(models_cfg)

    available = []

    for m in models_cfg:
        if not m["api_key"]:
            # skip models without env key present
            continue

        available.append({
            "value": m["name"],              # used in checkbox
            "label": f"{m['provider']} / {m['model']}",
            "cfg": m,                        # full cfg for later lookup
        })

    #print(f'available_judge_models')
    #pprint.pprint(available)

    return available

def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_models(models_cfg_raw):
    """
    Same semantics as run_experiment.py
    """
    models = []
    for m in models_cfg_raw:
        env = os.environ.get(m.get("env_key", ""))
        models.append({
            "name": m["name"],
            "provider": m["provider"],
            "model": m["model"],
            "chat_url": m["chat_url"],
            "api_key": env,
            "pricing": m.get("pricing", {}),
        })
    return models

# ------------------------------------------------------------------
# Human Panel: Judge Exercises
# ------------------------------------------------------------------

def load_exercise_human_judgements_dict(clara_project_internal):
    raw = clara_project_internal.load_text_version_or_null("exercise_human_judgements")
    if not raw:
        return {"schema_version": "1.0", "human_judgements": {}}
    try:
        d = json.loads(raw)
        if not isinstance(d, dict):
            return {"schema_version": "1.0", "human_judgements": {}}
        d.setdefault("schema_version", "1.0")
        d.setdefault("human_judgements", {})
        return d
    except Exception:
        return {"schema_version": "1.0", "human_judgements": {}}


def save_exercise_human_judgements_dict(clara_project_internal, d, *, user):
    text = json.dumps(d, indent=2, ensure_ascii=False) + "\n"
    clara_project_internal.save_text_version(
        "exercise_human_judgements",
        text,
        source="human_evaluation",
        user=user,
    )

@login_required
@user_has_a_project_role
def human_judge_exercises(request, project_id):

    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    all_exercises = clara_project_internal.load_all_exercises()
    if not all_exercises:
        messages.error(request, "No exercises available.")
        return redirect("project_detail", project_id=project_id)

    exercise_type = list(all_exercises.keys())[0]
    exercise_payload = clara_project_internal.load_exercises(exercise_type)

    exercise_set_id = exercise_payload.get("exercise_set_id")
    learner_level = exercise_payload.get("learner_level", "intermediate")
    items = exercise_payload.get("items", [])
    rubric_text = get_cloze_judging_rubric_text(learner_level)

    if request.method == "GET":
        return render(
            request,
            "clara_app/human_judge_exercises.html",
            {
                "project": project,
                "exercise_type": exercise_type,
                "exercise_set_id": exercise_set_id,
                "learner_level": learner_level,
                "items": items,
                "rubric_text": rubric_text,
            },
        )

    # ---------------- POST: Save human run ----------------

    human_run_id = request.POST.get("human_run_id")
    if not human_run_id:
        human_run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + request.user.username

    d = load_exercise_human_judgements_dict(clara_project_internal)
    jud = d["human_judgements"]

    jud.setdefault(exercise_type, {})
    jud[exercise_type].setdefault(exercise_set_id, {})

    run_blob = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "user": request.user.username,
        "learner_level": learner_level,
        "rubric_version": "cloze_judging_v2",
        "items": {}
    }

    for item in items:
        item_id = item["item_id"]

        verdict = request.POST.get(f"verdict_{item_id}")
        confidence = request.POST.get(f"confidence_{item_id}")
##        summary = request.POST.get(f"summary_{item_id}", "")
        comment = request.POST.get(f"comment_{item_id}", "")

        if not verdict:
            continue  # skip untouched items

        try:
            confidence = float(confidence)
        except Exception:
            confidence = 0.0

        snapshot = {
            "learner_level": "intermediate",
            "text_with_blank": item.get("segment", {}).get("text_with_blank"),
            "context_before": item.get("segment", {}).get("context_before"),
            "context_after": item.get("segment", {}).get("context_after"),
            "full_text": item.get("full_text"),
            "target": item.get("target"),
            "choices": item.get("choices"),
        }

        run_blob["items"][item_id] = {
            "item_snapshot": snapshot,
            "verdict": verdict,
##            "confidence": confidence,
##            "summary": summary,
            "issues": [],  # V1 simple; can extend later
            "comment": comment,
        }

    jud[exercise_type][exercise_set_id][human_run_id] = run_blob

    save_exercise_human_judgements_dict(clara_project_internal, d, user=request.user.username)

    messages.info(request, "Human evaluation saved.")
    return redirect("browse_human_exercise_judgements", project_id=project_id)

@login_required
def browse_human_exercise_judgements(request, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    d = load_exercise_human_judgements_dict(clara_project_internal)
    jud = d.get("human_judgements", {}) or {}

    exercise_types = sorted(jud.keys())
    selected_exercise_type = request.GET.get("exercise_type") or (exercise_types[0] if exercise_types else "")

    sets_dict = jud.get(selected_exercise_type, {}) if selected_exercise_type else {}
    exercise_set_ids = sorted(sets_dict.keys())
    selected_exercise_set_id = request.GET.get("exercise_set_id") or (exercise_set_ids[0] if exercise_set_ids else "")

    runs_dict = sets_dict.get(selected_exercise_set_id, {}) if selected_exercise_set_id else {}
    run_ids = sorted(runs_dict.keys(), reverse=True)  # newest first

    # ---------- aggregate across ALL runs ----------
    items_agg = {}  # item_id -> {snapshot, judges{run_id: payload}, counts, majority}
    judge_meta = [] # list of (run_id, user, created_at)

    def _norm_verdict(v):
        return v if v in ("ok", "minor_suggestion", "needs_fix") else "unparsed"

    def _majority(counts):
        # simple majority; tie-break: needs_fix > minor_suggestion > ok (conservative)
        order = ["needs_fix", "minor_suggestion", "ok", "unparsed"]
        best = None
        best_n = -1
        for k in order:
            n = counts.get(k, 0)
            if n > best_n:
                best = k
                best_n = n
        return best

    for rid in run_ids:
        run_payload = runs_dict.get(rid, {}) or {}
        judge_meta.append((rid, run_payload.get("user"), run_payload.get("created_at")))

        items = (run_payload.get("items") or {})
        for item_id, payload in items.items():
            snap = (payload.get("item_snapshot") or {})
            entry = items_agg.setdefault(item_id, {
                "item_id": item_id,
                "snapshot": snap,
                "judges": {},     # rid -> payload (verdict, confidence, summary, comment, ...)
                "counts": {"ok": 0, "minor_suggestion": 0, "needs_fix": 0, "unparsed": 0},
                "majority": None,
            })

            verdict = _norm_verdict(payload.get("verdict"))
            entry["judges"][rid] = payload
            entry["counts"][verdict] = entry["counts"].get(verdict, 0) + 1

    # compute majority after counting
    judged_rows = []
    for item_id, entry in items_agg.items():
        entry["majority"] = _majority(entry["counts"])
        judged_rows.append(entry)

    # Add per-row aligned judge cells so the template doesn't need dict dynamic lookup
    for row in judged_rows:
        cells = []
        judges_map = row.get("judges", {}) or {}
        for rid, user, created_at in judge_meta:
            cells.append({
                "rid": rid,
                "user": user,
                "created_at": created_at,
                "r": judges_map.get(rid),   # <-- this is the important part
            })
        row["judge_cells"] = cells

    judged_rows.sort(key=lambda r: r["item_id"])

##    print('judge_meta')
##    pprint.pprint(judge_meta)
##
##    print('judged_rows')
##    pprint.pprint(judged_rows)

    return render(
        request,
        "clara_app/browse_human_exercise_judgements.html",
        {
            "project": project,
            "exercise_types": exercise_types,
            "selected_exercise_type": selected_exercise_type,
            "exercise_set_ids": exercise_set_ids,
            "selected_exercise_set_id": selected_exercise_set_id,

            # we still show runs, but now informational / for future filtering
            "run_ids": run_ids,
            "judge_meta": judge_meta,

            # NEW: aggregated rows (one per item)
            "judged_rows": judged_rows,
        },
    )

def human_exercise_judgements_exist_for_project(project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    d = load_exercise_human_judgements_dict(clara_project_internal)

    return False if not d else True


