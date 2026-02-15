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
from .clara_classes import ContentElement

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
        process_cloze_exercise_targets(project, text_obj, params, exercise_targets, rng, callback=callback)
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


async def process_cloze_exercise_targets(project, text_obj, params, exercise_targets, rng: random.Random, callback=None):
    tasks = [
        asyncio.create_task(generate_cloze_exercise_item(t, project, text_obj, params, rng, callback=callback))
        for t in exercise_targets
    ]
    results = await asyncio.gather(*tasks)

    items = []
    total_cost = {}

    for item, cost_dict in results:
        items.append(item)
        total_cost = combine_cost_dicts(total_cost, cost_dict)

    return items, total_cost


async def generate_cloze_exercise_item(exercise_target, project, text_obj, params, rng: random.Random, callback=None):
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

    model = params["gpt_model"]
    n_distractors = params["n_distractors"]

    prompt = build_cloze_distractor_prompt(
        segment_text=segment_text,
        segment_text_with_blank=segment_text_with_blank,
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
        "page_index": page_index,
        "segment_index": seg_index,
        "target": {"surface": target_surface, "lemma": lemma, "pos": pos},
        "segment": {
            "text": segment_text,
            "text_with_blank": segment_text_with_blank,
            "context_before": context_before,
            "context_after": context_after,
        },
        "choices": choices,
        "notes": {"generation_model": model, "prompt_version": CLOZE_PROMPT_VERSION},
    }

    cost_dict = { 'exercises_mcq': cost }

    return item, cost_dict

def build_cloze_distractor_prompt(
    *,
    segment_text,
    segment_text_with_blank=None,   # new
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

SEGMENT:
{segment_text}{blank_block}

CONTEXT (optional):
Before: {context_before}
After: {context_after}

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

    all_exercises = clara_project_internal.load_all_exercises()
    if not all_exercises:
        messages.error(request, f"Unable to find any exercises for this project.")
        return redirect("project_detail", project_id=project_id)
    if exercise_type not in all_exercises:
        messages.error(request, f"No exercises of type '{exercise_type}' found.")
        return redirect("project_detail", project_id=project_id)

    exercise_data = all_exercises[exercise_type]
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


