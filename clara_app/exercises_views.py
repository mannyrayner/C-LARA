# clara_app/exercises_views.py

from datetime import datetime, timezone
import asyncio
import csv
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
    user_has_any_named_project_role,
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
    theme = request.POST.get("theme", "none").strip()
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
        theme=theme,
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
    theme: str = "none",
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
                theme=theme,
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
    theme: str = "none",
    callback=None,
):
    exercise_set_id = uuid.uuid4().hex

    exercise_targets = select_random_cloze_targets(text_obj, n_examples, rng)

    params = {
        "n_distractors": n_distractors,
        "gpt_model": MODEL_FOR_EXERCISE_GENERATION,
    }

    items, cost_dict = asyncio.run(
        process_cloze_exercise_targets(project, text_obj, params, exercise_targets, rng,
                                       learner_level=learner_level, theme=theme,
                                       callback=callback)
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
        "theme": theme,
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


async def process_cloze_exercise_targets(project, text_obj, params, exercise_targets, rng: random.Random,
                                         learner_level="intermediate", theme="none", callback=None):
    tasks = [
        asyncio.create_task(generate_cloze_exercise_item(t, project, text_obj, params, rng,
                                                         learner_level=learner_level, theme=theme,
                                                         callback=callback))
        for t in exercise_targets
    ]
    results = await asyncio.gather(*tasks)

    items = []
    total_cost = {}

    for item, cost_dict in results:
        items.append(item)
        total_cost = combine_cost_dicts(total_cost, cost_dict)

    return items, total_cost


async def generate_cloze_exercise_item(exercise_target, project, text_obj, params, rng: random.Random,
                                       learner_level="intermediate", theme="none",
                                       callback=None):
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
        theme=theme,
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
        "theme": theme,
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

def theme_guidance_block(theme: str) -> str:
    if theme == "vocabulary":
        return """
THEME: vocabulary

Theme requirement:
- The distractors should primarily test vocabulary knowledge.
- Prefer lexical alternatives: different words, near-meaning confusions, collocationally wrong words,
  semantically related words, or similar-looking/similar-sounding words.
- Avoid distractors that are merely different inflected forms of the target, unless no better vocabulary-based option is available.
- In general, do NOT solve this task by changing only tense, agreement, number, or case.
"""
    elif theme == "grammar":
        return """
THEME: grammar

Theme requirement:
- The distractors should primarily test grammar.
- Prefer grammatical confusions such as:
  article/determiner choice,
  pronoun form,
  agreement,
  tense/aspect,
  auxiliary choice,
  preposition choice,
  function-word misuse.
- Inflectional changes are acceptable if they clearly target a grammatical contrast.
- Do not primarily test lexical knowledge.
"""
    elif theme == "morphology":
        return """
THEME: morphology

Theme requirement:
- The distractors should primarily test morphology.
- Prefer inflectional or derivational confusions:
  wrong endings,
  wrong agreement forms,
  wrong tense/person/number/case forms,
  or closely related morphological variants.
- Using the same lemma in the wrong form is often appropriate here.
- Do not primarily test lexical choice unless it supports a clear morphological contrast.
"""
    else:
        return """
THEME: none

Theme requirement:
- Generate good general-purpose distractors.
- Use the most natural kind of learner error for this target.
"""

def theme_pos_guidance_block(theme: str) -> str:
    if theme == "vocabulary":
        return """
Grammatical category guidance for vocabulary theme:
- Distractors will usually have the same POS as the target.
- Closely related POS changes are acceptable only if they reflect a plausible learner confusion.
- The main goal is lexical plausibility, not inflectional variation.
"""
    elif theme == "grammar":
        return """
Grammatical category guidance for grammar theme:
- Distractors may have the same POS as the target or a closely related grammatical category,
  if that reflects a plausible grammatical learner error.
- Examples:
  pronoun vs determiner,
  noun phrase determiner substitutions,
  auxiliary/verb confusions,
  preposition/function-word substitutions.
"""
    elif theme == "morphology":
        return """
Grammatical category guidance for morphology theme:
- Distractors will usually stay within the same grammatical category as the target.
- Different inflected forms of the same lemma are often appropriate.
- Closely related categories are acceptable only if the confusion is morphologically plausible.
"""
    else:
        return """
Grammatical category guidance:
- Distractors should usually belong to the same grammatical category (POS) as the target.
- However, a distractor may come from a closely related category if it reflects a typical learner error.
- The key requirement is that the distractor should plausibly attract a learner’s attention at first glance.
"""

def theme_error_guidance_block(theme: str, learner_level: str) -> str:
    advanced_block = """
For advanced learners:
- Distractors may involve subtler semantic or pragmatic distinctions,
  but there must still be only one clearly correct answer.
"""

    if theme == "vocabulary":
        non_advanced = """
For beginner, low-intermediate, and intermediate learners:
- Distractors should normally be incorrect for clear lexical reasons:
  * wrong word choice
  * wrong collocation
  * semantically related but contextually wrong words
  * similar-looking or similar-sounding words
- Avoid distractors that are wrong only because of morphology or grammar,
  unless that is unavoidable.
- Avoid distractors whose incorrectness depends only on subtle pragmatic or discourse considerations.
"""
        prefer = """
Prefer these vocabulary-type distractors:
- wrong collocation
- semantically related but contextually wrong words
- near-meaning confusions
- similar-looking or similar-sounding words
- lexical substitutions a learner might plausibly choose
"""
    elif theme == "grammar":
        non_advanced = """
For beginner, low-intermediate, and intermediate learners:
- Distractors should normally be incorrect for clear grammatical reasons:
  * agreement
  * tense/aspect mismatch
  * article/determiner choice
  * pronoun form
  * auxiliary choice
  * function word misuse
  * preposition confusion
- Avoid distractors that are primarily lexical confusions.
- Avoid distractors whose incorrectness depends only on subtle pragmatic or discourse considerations.
"""
        prefer = """
Prefer these grammar-type distractors:
- wrong article/determiner choice
- agreement errors
- pronoun reference/form confusion
- tense/aspect mismatch
- auxiliary or function-word misuse
- preposition confusion
"""
    elif theme == "morphology":
        non_advanced = """
For beginner, low-intermediate, and intermediate learners:
- Distractors should normally be incorrect for clear morphological reasons:
  * wrong inflection
  * wrong ending
  * wrong agreement form
  * wrong person/number/case form
  * wrong derivational form
- Avoid distractors that are primarily lexical substitutions.
- Avoid distractors whose incorrectness depends only on subtle pragmatic or discourse considerations.
"""
        prefer = """
Prefer these morphology-type distractors:
- wrong inflected forms
- wrong endings
- wrong agreement forms
- closely related morphological variants
- derivational confusions
"""
    else:
        non_advanced = """
For beginner, low-intermediate, and intermediate learners:
- Distractors should normally be incorrect for clear linguistic reasons:
  * morphology
  * grammar
  * vocabulary choice
  * collocation
  * agreement
  * function word misuse
- Avoid distractors that are wrong only because of subtle pragmatic or discourse considerations.
"""
        prefer = """
Prefer these types of learner-error distractors:
- wrong collocation
- wrong article/determiner choice
- agreement errors
- pronoun reference confusion
- tense/aspect mismatch
- overgeneralized rule application
- similar-looking or similar-sounding words
- preposition confusion
- incorrect but plausible function word swaps
"""

    avoid = """
Avoid:
- true synonyms or paraphrases that a teacher might reasonably accept as correct
- distractors that make the sentence equally acceptable
- distractors whose incorrectness depends only on subtle pragmatic interpretation
  (unless learner level is advanced)
"""

    return "\n".join([non_advanced, advanced_block, avoid, prefer])

def build_cloze_distractor_prompt(
    *,
    learner_level,
    theme,
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

    theme_guidance = theme_guidance_block(theme)
    pos_guidance = theme_pos_guidance_block(theme)
    error_guidance = theme_error_guidance_block(theme, learner_level)

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

{theme_guidance}

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

{pos_guidance}

Incorrectness requirements:
- Distractors must be clearly incorrect in this specific context.
- They should represent mistakes a learner might realistically make.

{error_guidance}

The sentence should usually remain grammatical,
but sound wrong, unnatural, or semantically incorrect to a fluent speaker.

THEME CHECK:
- The reason for each distractor must explicitly explain why the distractor fits the requested theme.
- If theme = vocabulary, explain the lexical confusion.
- If theme = grammar, explain the grammatical confusion.
- If theme = morphology, explain the morphological confusion.
- If theme = none, explain the general learner-error rationale.

Before returning your answer:
For each distractor, ask yourself:
1. Would a teacher accept this as correct?
2. Does this distractor clearly fit the requested theme?
If the answer to either question is no, discard it and generate a new one.

Return STRICT JSON in this schema (no extra keys, no prose):

{{
  "distractors": [
    {{"form": ".", "reason": "short reason explaining both why it is wrong and why it fits the requested theme"}},
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

    exercise_type = request.GET.get("type") or request.POST.get("type") or "cloze_mcq"
    selected_set_id = request.GET.get("set_id") or request.POST.get("set_id") or ""
    item_index = int(request.GET.get("item", request.POST.get("item", "0")))

    all_exercises = clara_project_internal.load_all_exercises()
    if not all_exercises:
        messages.error(request, "Unable to find any exercises for this project.")
        return redirect("project_detail", project_id=project_id)

    exercise_type_data = all_exercises.get(exercise_type)
    if not exercise_type_data:
        messages.error(request, f"No exercises of type '{exercise_type}' found.")
        return redirect("project_detail", project_id=project_id)

    # New format: exercise_type -> {"sets": {...}} ; fallback to old single-set format
    if isinstance(exercise_type_data, dict) and "sets" in exercise_type_data:
        sets_dict = exercise_type_data.get("sets", {}) or {}
    else:
        pseudo_id = exercise_type_data.get("exercise_set_id", "default")
        sets_dict = {pseudo_id: exercise_type_data}

    if not sets_dict:
        messages.error(request, "No exercise sets available.")
        return redirect("project_detail", project_id=project_id)

    # newest first by created_at if available
    def _sort_key(kv):
        set_id, payload = kv
        return payload.get("created_at", "")

    sorted_sets = sorted(sets_dict.items(), key=_sort_key, reverse=True)

    if not selected_set_id:
        selected_set_id = sorted_sets[0][0]

    exercise_data = sets_dict.get(selected_set_id)
    if not exercise_data:
        messages.error(request, f"No exercise set '{selected_set_id}' found.")
        return redirect("project_detail", project_id=project_id)

    items = exercise_data.get("items", [])
    if not items:
        messages.error(request, "No exercise items available.")
        return redirect("project_detail", project_id=project_id)

    # clamp index
    item_index = max(0, min(item_index, len(items) - 1))
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
            wrong = next((c for c in item["choices"] if c["form"] == selected), None)
            feedback = {
                "correct": False,
                "message": "Incorrect.",
                "reason": wrong.get("reason", "") if wrong else "",
                "correct_form": correct_choice["form"],
                "correct_reason": correct_choice.get("reason", "")
            }

    next_index = item_index + 1 if item_index + 1 < len(items) else None

    # human-readable set labels
    exercise_sets = []
    for set_id, payload in sorted_sets:
        created_at = payload.get("created_at", "")
        theme = payload.get("theme", "none")
        learner_level = payload.get("learner_level", "")
        n_items = len(payload.get("items", []))

        created_label = created_at[:16].replace("T", " ") if created_at else set_id
        theme_label = "No theme" if theme == "none" else theme

        label = f"{created_label} — {theme_label} — {n_items} items"
        if learner_level:
            label += f" — {learner_level}"

        exercise_sets.append({
            "set_id": set_id,
            "label": label,
        })

    return render(
        request,
        "clara_app/run_exercises.html",
        {
            "project": project,
            "exercise_type": exercise_type,
            "exercise_sets": exercise_sets,
            "selected_set_id": selected_set_id,
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
    selected_set_id = request.GET.get("set_id", "")
    item_index = int(request.GET.get("item", "0"))
    show_answers = request.GET.get("show", "") == "answers"

    all_exercises = clara_project_internal.load_all_exercises()
    if not all_exercises:
        messages.error(request, "Unable to find any exercises for this project.")
        return redirect("project_detail", project_id=project_id)

    exercise_type_data = all_exercises.get(exercise_type)
    if not exercise_type_data:
        messages.error(request, f"No exercises of type '{exercise_type}' found.")
        return redirect("project_detail", project_id=project_id)

    # New format: exercise_type -> {"sets": {...}} ; fallback to old single-set format
    if isinstance(exercise_type_data, dict) and "sets" in exercise_type_data:
        sets_dict = exercise_type_data.get("sets", {}) or {}
    else:
        # backward compatibility: treat the single payload as one pseudo-set
        pseudo_id = exercise_type_data.get("exercise_set_id", "default")
        sets_dict = {pseudo_id: exercise_type_data}

    if not sets_dict:
        messages.error(request, "No exercise sets available.")
        return redirect("project_detail", project_id=project_id)

    # newest first by created_at if available
    def _sort_key(kv):
        set_id, payload = kv
        return payload.get("created_at", "")

    sorted_sets = sorted(sets_dict.items(), key=_sort_key, reverse=True)

    if not selected_set_id:
        selected_set_id = sorted_sets[0][0]

    exercise_data = sets_dict.get(selected_set_id)
    if not exercise_data:
        messages.error(request, f"No exercise set '{selected_set_id}' found.")
        return redirect("browse_exercises", project_id=project_id)

    items = exercise_data.get("items", [])
    if not items:
        messages.error(request, "No exercise items available.")
        return redirect("project_detail", project_id=project_id)

    # clamp item index
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

    # Build human-readable menu labels
    exercise_sets = []
    for set_id, payload in sorted_sets:
        created_at = payload.get("created_at", "")
        theme = payload.get("theme", "none")
        learner_level = payload.get("learner_level", "")
        n_items = len(payload.get("items", []))

        created_label = created_at[:16].replace("T", " ") if created_at else set_id
        theme_label = theme if theme else "none"

        label = f"{created_label} — {theme_label} — {n_items} items"
        if learner_level:
            label += f" — {learner_level}"

        exercise_sets.append({
            "set_id": set_id,
            "label": label,
        })

    return render(
        request,
        "clara_app/browse_exercises.html",
        {
            "project": project,
            "exercise_types": EXERCISE_TYPES,
            "exercise_type": exercise_type,

            "exercise_sets": exercise_sets,
            "selected_set_id": selected_set_id,

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

@login_required
@user_has_any_named_project_role(['OWNER'])
def ai_panel_judge_exercises(request, project_id, status="start"):

    """
    Main page: show form (GET) or queue async generation (POST).
    status is used only to show a one-shot message after monitor redirect.
    """
    if status == "finished":
        messages.info(request, "Exercise judging completed normally.")
    elif status == "error":
        messages.error(request, "Error in exercise judging. See 'Recent task updates' for details.")

    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    all_exercises = clara_project_internal.load_all_exercises()

    if not all_exercises or not isinstance(all_exercises, dict):
        messages.error(request, "Error: no valid exercises to evaluate.")
        return redirect("project_detail", project_id=project_id)

    exercise_types = list(all_exercises.keys())
    if not exercise_types:
        messages.error(request, "Error: no valid exercises to evaluate.")
        return redirect("project_detail", project_id=project_id)

    # For now, still assume one exercise type unless user specifies otherwise
    exercise_type = request.GET.get("type") or request.POST.get("type") or exercise_types[0]

    exercise_type_data = all_exercises.get(exercise_type)
    if not exercise_type_data:
        messages.error(request, f"No exercises of type '{exercise_type}' found.")
        return redirect("project_detail", project_id=project_id)

    # New format: exercise_type -> {"sets": {...}} ; fallback to old single-set format
    if isinstance(exercise_type_data, dict) and "sets" in exercise_type_data:
        sets_dict = exercise_type_data.get("sets", {}) or {}
    else:
        pseudo_id = exercise_type_data.get("exercise_set_id", "default")
        sets_dict = {pseudo_id: exercise_type_data}

    if not sets_dict:
        messages.error(request, "Error: no valid exercise sets to evaluate.")
        return redirect("project_detail", project_id=project_id)

    # newest first by created_at if available
    def _sort_key(kv):
        set_id, payload = kv
        return payload.get("created_at", "")

    sorted_sets = sorted(sets_dict.items(), key=_sort_key, reverse=True)

    selected_set_id = request.GET.get("set_id") or request.POST.get("exercise_set_id") or sorted_sets[0][0]
    exercise_set = sets_dict.get(selected_set_id)

    if not exercise_set or "items" not in exercise_set:
        messages.error(request, "Error: no valid exercises to evaluate.")
        return redirect("ai_panel_judge_exercises", project_id, "initial")

    exercise_items = exercise_set.get("items", [])

    # Build human-readable labels for set menu
    exercise_sets = []
    for set_id, payload in sorted_sets:
        created_at = payload.get("created_at", "")
        theme = payload.get("theme", "none")
        learner_level = payload.get("learner_level", "")
        n_items = len(payload.get("items", []))

        created_label = created_at[:16].replace("T", " ") if created_at else set_id
        theme_label = "No theme" if theme == "none" else theme

        label = f"{created_label} — {theme_label} — {n_items} items"
        if learner_level:
            label += f" — {learner_level}"

        exercise_sets.append({
            "set_id": set_id,
            "label": label,
        })

    if request.method == "GET":
        return render(
            request,
            "clara_app/ai_panel_judge_exercises.html",
            {
                "project": project,
                "exercise_type": exercise_type,
                "exercise_items": exercise_items,
                "exercise_sets": exercise_sets,
                "selected_set_id": selected_set_id,
                "available_models": get_available_judge_models(),
            },
        )

    # POST: submit judging job
    item_ids = request.POST.getlist("item_ids")
    judge_models = request.POST.getlist("judge_models")
    if not item_ids:
        messages.error(request, "Select at least one exercise item.")
        return redirect("ai_panel_judge_exercises", project_id, "initial")
    if not judge_models:
        messages.error(request, "Select at least one judge model.")
        return redirect("ai_panel_judge_exercises", project_id, "initial")

    callback, report_id = make_asynch_callback_and_report_id(request, "ai_panel_judge_exercises")

    messages.info(request, f"Submitting exercises for AI judging")

    async_task(
        create_and_save_ai_panel_judgements,
        project,
        clara_project_internal,
        exercise_type,
        selected_set_id,
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
    # Load the requested exercise set, not just the latest set for the type
    all_exercises = clara_project_internal.load_all_exercises()
    if not all_exercises:
        post_task_update(callback, f"Error: no exercises found for type '{exercise_type}'")
        post_task_update(callback, "error")
        return

    exercise_type_data = all_exercises.get(exercise_type)
    if not exercise_type_data:
        post_task_update(callback, f"Error: no exercises found for type '{exercise_type}'")
        post_task_update(callback, "error")
        return

    # New format: exercise_type -> {"sets": {...}} ; fallback to old single-set format
    if isinstance(exercise_type_data, dict) and "sets" in exercise_type_data:
        sets_dict = exercise_type_data.get("sets", {}) or {}
    else:
        pseudo_id = exercise_type_data.get("exercise_set_id", "default")
        sets_dict = {pseudo_id: exercise_type_data}

    exercises_payload = sets_dict.get(exercise_set_id)
    if not exercises_payload:
        post_task_update(
            callback,
            f"Error: no exercise set '{exercise_set_id}' found for type '{exercise_type}'"
        )
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
    available_models = get_available_judge_models()
    model_cfg_by_name = {m["value"]: m["cfg"] for m in available_models}

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
            "theme": item.get("theme", "none"),
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
                "rating": "unparsed",
                "summary": f"exception: {r}",
                "issues": [{"distractor": "", "problem": f"exception: {r}", "suggestion": ""}],
                "raw": "",
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
    text_with_blank = item["segment"]["text_with_blank"].strip()

    await post_task_update_async(callback, f"Making AI judging call to {model} for '{text_with_blank}'")

    try:
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
        await post_task_update_async(callback, f"AI judging call succeeded ({model}) for '{text_with_blank}'")
    except Exception as e:
        await post_task_update_async(callback, f"AI judging call failed ({model}) for '{text_with_blank}': {e}")
        resule = {
            "raw_text": "",
            "parsed": "",
            "provider": provider,
            "model": model,
            "rating": 0,
            "summary": "",
            "issues": "",
            "raw": "",
        }
        usage = {}
        cost = 0.0
        return result, (usage or {}), cost

    parsed = _json_from_model_output(content)

    rating = parsed.get("rating", "unparsed")
    if isinstance(rating, str):
        try:
            rating = int(rating)
        except Exception:
            rating = "unparsed"
    if rating not in (1, 2, 3, 4, 5, "unparsed"):
        rating = "unparsed"

    summary = parsed.get("summary", "")
    if not isinstance(summary, str):
        summary = ""

    issues = parsed.get("issues")
    if not isinstance(issues, list):
        issues = []

    result = {
        "raw_text": content,
        "parsed": parsed,
        "provider": provider,
        "model": model,
        "rating": rating,
        "summary": summary,
        "issues": issues,
        "raw": content[:2000],
    }

    try:
        cost = compute_cost_for_usage(model_cfg, usage or {})
    except Exception:
        cost = 0.0

    return result, (usage or {}), cost

def build_cloze_judging_prompt(item: dict) -> Tuple[str, str]:
    seg = item.get("segment") or {}
    target = item.get("target") or {}
    choices = item.get("choices") or []
    learner_level = item.get("learner_level") or "intermediate"
    theme = item.get("theme") or "none"

    correct = [c for c in choices if c.get("is_correct")]
    distractors = [c for c in choices if not c.get("is_correct")]

    distractor_lines = []
    for d in distractors:
        distractor_lines.append(
            f"- {d.get('form')} :: rationale = {d.get('reason')}"
        )

    full_text = item.get("full_text") or {}
    if isinstance(full_text, dict):
        full_text_content = full_text.get("content") or ""
    else:
        full_text_content = ""

    rubric_text = get_cloze_judging_rubric_text(learner_level, theme)

    system_prompt = (
        "You are a careful and fair CALL evaluation assistant. "
        "You evaluate cloze multiple-choice items designed by a competent CALL researcher. "
        "Assume good faith and pedagogical intent. "
        "Your task is to judge how suitable the distractors are for teaching purposes."
    )

    user_prompt = f"""
{rubric_text}

SEGMENT (with blank):
{seg.get("text_with_blank") or ""}

CONTEXT:
Before: {seg.get("context_before") or ""}
After: {seg.get("context_after") or ""}

FULL TEXT (target segment highlighted):
{full_text_content or "(missing full text)"}

TARGET:
surface = {target.get("surface")}
lemma = {target.get("lemma")}
pos = {target.get("pos")}

CORRECT ANSWER:
{[c.get("form") for c in correct]}

DISTRACTORS (with intended rationale):
{chr(10).join(distractor_lines)}

Return STRICT JSON ONLY (no markdown, no explanations outside JSON):

{{
  "rating": 1 | 2 | 3 | 4 | 5,
  "summary": "brief overall explanation",
  "issues": [
    {{
      "distractor": "...",
      "problem": "...",
      "suggestion": "..."
    }}
  ]
}}
""".strip()

    return system_prompt, user_prompt

def judging_theme_guidance_block(theme: str) -> str:
    if theme == "vocabulary":
        return """
THEME: vocabulary

Theme-sensitive evaluation:
- Judge whether the distractors primarily test vocabulary knowledge.
- Good vocabulary distractors are usually lexical alternatives:
  different words, near-meaning confusions, collocationally wrong words,
  semantically related words, or similar-looking/similar-sounding words.
- Mere inflectional variants of the target are usually weak vocabulary distractors,
  unless no better lexical option is available.
- Do not reward the item for mainly testing grammar or morphology when the requested theme is vocabulary.
"""
    elif theme == "grammar":
        return """
THEME: grammar

Theme-sensitive evaluation:
- Judge whether the distractors primarily test grammar.
- Good grammar distractors typically involve grammatical confusions such as:
  article/determiner choice,
  pronoun form,
  agreement,
  tense/aspect,
  auxiliary choice,
  preposition choice,
  or function-word misuse.
- Inflectional changes are appropriate only if they clearly realise a grammatical contrast.
- Do not reward the item for mainly testing vocabulary knowledge when the requested theme is grammar.
"""
    elif theme == "morphology":
        return """
THEME: morphology

Theme-sensitive evaluation:
- Judge whether the distractors primarily test morphology.
- Good morphology distractors typically involve:
  wrong endings,
  wrong agreement forms,
  wrong tense/person/number/case forms,
  derivational confusions,
  or closely related morphological variants.
- Different inflected forms of the same lemma are often appropriate here.
- Do not reward the item for mainly testing vocabulary choice when the requested theme is morphology.
"""
    else:
        return """
THEME: none

Theme-sensitive evaluation:
- Judge the distractors as general-purpose learner distractors.
- Use the most natural pedagogical criterion for this target and context.
"""

def judging_theme_pos_guidance_block(theme: str) -> str:
    if theme == "vocabulary":
        return """
Grammatical-category guidance for vocabulary theme:
- Distractors will usually have the same POS as the target.
- Closely related POS changes are acceptable only if they reflect a plausible learner lexical confusion.
- The main question is lexical plausibility, not inflectional variation.
"""
    elif theme == "grammar":
        return """
Grammatical-category guidance for grammar theme:
- Distractors may have the same POS as the target or a closely related grammatical category,
  if that reflects a plausible grammatical learner error.
- Examples:
  pronoun vs determiner,
  auxiliary/verb confusions,
  preposition/function-word substitutions,
  noun-phrase determiner substitutions.
"""
    elif theme == "morphology":
        return """
Grammatical-category guidance for morphology theme:
- Distractors will usually stay within the same grammatical category as the target.
- Different inflected forms of the same lemma are often appropriate.
- Closely related categories are acceptable only if the confusion is morphologically plausible.
"""
    else:
        return """
General grammatical-category guidance:
- Distractors should usually belong to the same grammatical category as the target,
  or to a closely related category if that reflects a plausible learner confusion.
- The key requirement is that the distractor should plausibly attract a learner’s attention at first glance.
"""

def judging_theme_error_guidance_block(theme: str, learner_level: str) -> str:
    advanced_block = """
For advanced learners:
- It is acceptable for distractors to involve subtler semantic or pragmatic distinctions,
  but there must still be only one clearly correct answer.
"""

    if theme == "vocabulary":
        non_advanced = """
For beginner, low-intermediate, and intermediate learners:
- Distractors should normally be incorrect for clear lexical reasons:
  * wrong word choice
  * wrong collocation
  * semantically related but contextually wrong words
  * similar-looking or similar-sounding words
- Distractors that are mainly wrong because of morphology or grammar are weaker here,
  unless that is unavoidable for this target.
- Avoid rewarding distractors whose incorrectness depends mainly on subtle pragmatic or discourse considerations.
"""
        prefer = """
Prefer these vocabulary-oriented properties:
- lexical substitution rather than mere inflectional variation
- lexical confusions a learner might plausibly make
- word-choice mistakes that remain pedagogically clear
"""
    elif theme == "grammar":
        non_advanced = """
For beginner, low-intermediate, and intermediate learners:
- Distractors should normally be incorrect for clear grammatical reasons:
  * agreement
  * tense/aspect mismatch
  * article/determiner choice
  * pronoun form
  * auxiliary choice
  * function-word misuse
  * preposition confusion
- Distractors that are mainly lexical substitutions are weaker here.
- Avoid rewarding distractors whose incorrectness depends mainly on subtle pragmatic or discourse considerations.
"""
        prefer = """
Prefer these grammar-oriented properties:
- article/determiner errors
- agreement errors
- pronoun-form confusions
- tense/aspect mistakes
- auxiliary and function-word misuse
- preposition confusion
"""
    elif theme == "morphology":
        non_advanced = """
For beginner, low-intermediate, and intermediate learners:
- Distractors should normally be incorrect for clear morphological reasons:
  * wrong inflection
  * wrong ending
  * wrong agreement form
  * wrong person/number/case form
  * wrong derivational form
- Distractors that are mainly lexical substitutions are weaker here.
- Avoid rewarding distractors whose incorrectness depends mainly on subtle pragmatic or discourse considerations.
"""
        prefer = """
Prefer these morphology-oriented properties:
- wrong inflected forms
- wrong endings
- wrong agreement forms
- closely related morphological variants
- derivational confusions
"""
    else:
        non_advanced = """
For beginner, low-intermediate, and intermediate learners:
- Distractors should normally be incorrect for clear linguistic reasons:
  * morphology
  * grammar
  * vocabulary choice
  * collocation
  * agreement
  * function-word misuse
- Avoid rewarding distractors whose incorrectness depends mainly on subtle pragmatic or discourse considerations.
"""
        prefer = """
Prefer these general learner-error properties:
- wrong collocation
- wrong article/determiner choice
- agreement errors
- pronoun-form confusion
- tense/aspect mismatch
- overgeneralised rule application
- similar-looking or similar-sounding words
- preposition confusion
- incorrect but plausible function-word swaps
"""

    avoid = """
Avoid rewarding distractors that:
- a teacher might reasonably accept as correct
- make the sentence equally acceptable
- fit the wrong theme better than the requested theme
- depend mainly on subtle pragmatic interpretation (unless learner level is advanced)
"""

    return "\n".join([non_advanced, advanced_block, avoid, prefer])

def get_cloze_judging_rubric_text(learner_level: str, theme: str) -> str:
    theme_guidance = judging_theme_guidance_block(theme)
    pos_guidance = judging_theme_pos_guidance_block(theme)
    error_guidance = judging_theme_error_guidance_block(theme, learner_level)

    return f"""
Evaluate the distractors for the following cloze multiple-choice item.

LEARNER LEVEL: {learner_level}

IMPORTANT ORIENTATION:
- Assume the item was designed by a competent CALL researcher.
- The goal is to evaluate how suitable the distractors are for teaching and assessment.
- Judge the item as a teacher would judge it.
- Do not nitpick minor stylistic issues.

{theme_guidance}

General criteria:
1. Each distractor should be a single token.
2. The provided "reason" explains the intended pedagogical function of the distractor.
   Judge whether the distractor successfully fulfills that intended function.
3. Distractors should be plausible enough to tempt a learner, but still be clearly incorrect in the context.
4. The distractor set should reflect the requested theme strongly and coherently, not just incidentally.

{pos_guidance}

{error_guidance}

Use the following 5-point rating scale:

1 = very poor
    The distractors are clearly unsuitable for teaching purposes and/or fail badly to realise the requested theme.
2 = rather poor
    The distractors have substantial weaknesses and realise the requested theme only weakly or inconsistently.
3 = acceptable
    The distractors are usable and broadly fit the requested theme, though not especially well.
4 = good
    The distractors work well for the intended purpose and fit the requested theme clearly.
5 = very good
    The distractors are very well designed for the intended purpose and fit the requested theme strongly and consistently.

When deciding the rating, take the requested theme seriously.
A distractor set that is good in general but does not really satisfy the requested theme should not receive a very high rating.
""".strip()

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
    selected_exercise_type = request.GET.get("exercise_type") or (exercise_types[0] if exercise_types else "")

    sets_dict = jud.get(selected_exercise_type, {}) if selected_exercise_type else {}

    def _set_created_at(set_id):
        runs_for_set = sets_dict.get(set_id, {}) or {}
        if not runs_for_set:
            return ""
        first_run_id = sorted(runs_for_set.keys(), reverse=True)[0]
        first_run = runs_for_set.get(first_run_id, {}) or {}
        return first_run.get("created_at", "")

    exercise_set_ids = sorted(
        sets_dict.keys(),
        key=lambda sid: _set_created_at(sid),
        reverse=True
    )

    requested_exercise_set_id = request.GET.get("exercise_set_id")
    if requested_exercise_set_id in exercise_set_ids:
        selected_exercise_set_id = requested_exercise_set_id
    else:
        selected_exercise_set_id = exercise_set_ids[0] if exercise_set_ids else ""

    runs_dict = sets_dict.get(selected_exercise_set_id, {}) if selected_exercise_set_id else {}
    run_ids = sorted(runs_dict.keys(), reverse=True)

    requested_run_id = request.GET.get("judge_run_id")
    if requested_run_id in run_ids:
        selected_run_id = requested_run_id
    else:
        selected_run_id = run_ids[0] if run_ids else ""
    
    run_payload = runs_dict.get(selected_run_id, {}) if selected_run_id else {}
    items = (run_payload.get("items") or {}) if isinstance(run_payload, dict) else {}

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

    def _norm_rating(v):
        if isinstance(v, int) and v in (1, 2, 3, 4, 5):
            return v
        if isinstance(v, str):
            try:
                v = int(v)
                if v in (1, 2, 3, 4, 5):
                    return v
            except Exception:
                pass
        return "unparsed"

    # ---------- build human-readable exercise-set labels ----------
    exercise_set_options = []
    for set_id in exercise_set_ids:
        runs_for_set = sets_dict.get(set_id, {}) or {}

        # Try to recover set metadata from one of the runs' snapshots
        created_at = ""
        theme = "none"
        learner_level = "intermediate"
        n_items = 0

        if runs_for_set:
            first_run_id = sorted(runs_for_set.keys(), reverse=True)[0]
            first_run = runs_for_set.get(first_run_id, {}) or {}
            created_at = first_run.get("created_at", "")

            first_items = first_run.get("items", {}) or {}
            n_items = len(first_items)

            if first_items:
                first_item_payload = next(iter(first_items.values()))
                first_snapshot = first_item_payload.get("item_snapshot", {}) if isinstance(first_item_payload, dict) else {}
                theme = first_snapshot.get("theme", "none")
                learner_level = first_snapshot.get("learner_level", "intermediate")

        created_label = created_at[:16].replace("T", " ") if created_at else set_id
        theme_label = "No theme" if theme == "none" else theme

        label = f"{created_label} — {theme_label} — {n_items} items"
        if learner_level:
            label += f" — {learner_level}"

        exercise_set_options.append({
            "value": set_id,
            "label": label,
        })

    # ---------- build human-readable judging-run labels ----------
    judge_run_options = []
    for rid in run_ids:
        payload = runs_dict.get(rid, {}) or {}
        created_at = payload.get("created_at", "")
        models = payload.get("models", []) or []

        created_label = created_at[:16].replace("T", " ") if created_at else rid
        if models:
            label = f"{created_label} — {len(models)} models"
        else:
            label = created_label

        judge_run_options.append({
            "value": rid,
            "label": label,
        })

    # ---------- build judged rows ----------
    judged_rows = []
    for item_id in items:
        item_payload = items[item_id]
        snapshot = item_payload.get("item_snapshot", {}) if isinstance(item_payload, dict) else {}
        model_map = item_payload.get("models", {}) if isinstance(item_payload, dict) else {}

        rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, "unparsed": 0}

        total = 0
        n = 0
        for model_name, r in model_map.items():
            rating = _norm_rating(r.get("rating"))
            rating_counts[rating] = rating_counts.get(rating, 0) + 1
            if isinstance(rating, int):
                total += rating
                n += 1

        mean_rating = round(total / n, 2) if n > 0 else None

        judged_rows.append({
            "item_id": item_id,
            "snapshot": snapshot,
            "model_map": model_map,
            "rating_counts": rating_counts,
            "mean_rating": mean_rating,
        })

    judged_rows.sort(key=lambda r: r["item_id"])

    if request.GET.get("format") == "csv":
        header = [
            "exercise_type", "exercise_set_id", "judge_run_id",
            "judge_type", "judge_id",
            "learner_level", "theme", "item_id",
            "text_with_blank", "correct", "distractors",
            "rating", "summary", "issues"
        ]
        rows = []
        for row in judged_rows:
            snap = row["snapshot"]
            model_map = row["model_map"]

            text_with_blank = snap.get("text_with_blank", "")
            learner_level = snap.get("learner_level", "intermediate")
            theme = snap.get("theme", "none")
            correct = ""
            distractors = []
            for c in (snap.get("choices") or []):
                if c.get("is_correct"):
                    correct = c.get("form", "")
                else:
                    distractors.append(c.get("form", ""))

            distractors_str = "|".join(distractors)

            for model_name, r in (model_map or {}).items():
                issues = r.get("issues", [])
                rows.append([
                    selected_exercise_type,
                    selected_exercise_set_id,
                    selected_run_id,
                    "ai",
                    model_name,
                    learner_level,
                    theme,
                    row["item_id"],
                    text_with_blank,
                    correct,
                    distractors_str,
                    r.get("rating", ""),
                    r.get("summary", ""),
                    json.dumps(issues, ensure_ascii=False),
                ])

        filename = f"{project.internal_id}_{selected_exercise_type}_{selected_exercise_set_id}_{selected_run_id}_ai_judgements.csv"
        return _as_csv_response(filename, header, rows)

    context = {
        "project": project,
        "exercise_types": exercise_types,
        "selected_exercise_type": selected_exercise_type,

        "exercise_set_ids": exercise_set_ids,
        "selected_exercise_set_id": selected_exercise_set_id,
        "exercise_set_options": exercise_set_options,

        "run_ids": run_ids,
        "selected_run_id": selected_run_id,
        "judge_run_options": judge_run_options,

        "run_payload": run_payload,
        "judged_items": items,
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
@user_has_any_named_project_role(['OWNER', 'ANNOTATOR'])
def human_judge_exercises(request, project_id):

    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    all_exercises = clara_project_internal.load_all_exercises()
    if not all_exercises:
        messages.error(request, "No exercises available.")
        return redirect("project_detail", project_id=project_id)

    exercise_types = list(all_exercises.keys())
    if not exercise_types:
        messages.error(request, "No exercises available.")
        return redirect("project_detail", project_id=project_id)

    # For now, still assume one exercise type unless explicitly specified
    exercise_type = request.GET.get("type") or request.POST.get("type") or exercise_types[0]

    exercise_type_data = all_exercises.get(exercise_type)
    if not exercise_type_data:
        messages.error(request, f"No exercises of type '{exercise_type}' found.")
        return redirect("project_detail", project_id=project_id)

    # New format: exercise_type -> {"sets": {...}} ; fallback to old single-set format
    if isinstance(exercise_type_data, dict) and "sets" in exercise_type_data:
        sets_dict = exercise_type_data.get("sets", {}) or {}
    else:
        pseudo_id = exercise_type_data.get("exercise_set_id", "default")
        sets_dict = {pseudo_id: exercise_type_data}

    if not sets_dict:
        messages.error(request, "No exercise sets available.")
        return redirect("project_detail", project_id=project_id)

    # newest first by created_at if available
    def _sort_key(kv):
        set_id, payload = kv
        return payload.get("created_at", "")

    sorted_sets = sorted(sets_dict.items(), key=_sort_key, reverse=True)

    selected_set_id = request.GET.get("set_id") or request.POST.get("exercise_set_id") or sorted_sets[0][0]
    exercise_payload = sets_dict.get(selected_set_id)

    if not exercise_payload:
        messages.error(request, f"No exercise set '{selected_set_id}' found.")
        return redirect("human_judge_exercises", project_id=project_id)

    exercise_set_id = exercise_payload.get("exercise_set_id", selected_set_id)
    learner_level = exercise_payload.get("learner_level", "intermediate")
    theme = exercise_payload.get("theme", "none")
    items = exercise_payload.get("items", [])
    rubric_text = get_cloze_judging_rubric_text(learner_level, theme)

    # Build human-readable labels for set menu
    exercise_sets = []
    for set_id, payload in sorted_sets:
        created_at = payload.get("created_at", "")
        set_theme = payload.get("theme", "none")
        set_level = payload.get("learner_level", "")
        n_items = len(payload.get("items", []))

        created_label = created_at[:16].replace("T", " ") if created_at else set_id
        theme_label = "No theme" if set_theme == "none" else set_theme

        label = f"{created_label} — {theme_label} — {n_items} items"
        if set_level:
            label += f" — {set_level}"

        exercise_sets.append({
            "set_id": set_id,
            "label": label,
        })

    if request.method == "GET":
        return render(
            request,
            "clara_app/human_judge_exercises.html",
            {
                "project": project,
                "exercise_type": exercise_type,
                "exercise_set_id": exercise_set_id,
                "exercise_sets": exercise_sets,
                "selected_set_id": selected_set_id,
                "learner_level": learner_level,
                "theme": theme,
                "items": items,
                "rubric_text": rubric_text,
            },
        )

    # ---------------- POST: Save/overwrite human run ----------------

    d = load_exercise_human_judgements_dict(clara_project_internal)
    jud = d["human_judgements"]

    jud.setdefault(exercise_type, {})
    jud[exercise_type].setdefault(exercise_set_id, {})

    # Stable run id: one run per user per exercise set
    human_run_id = request.user.username

    run_blob = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "user": request.user.username,
        "learner_level": learner_level,
        "theme": theme,
        "rubric_version": "cloze_judging_v2",
        "items": {}
    }

    for item in items:
        item_id = item["item_id"]

        rating = request.POST.get(f"rating_{item_id}")
        comment = request.POST.get(f"comment_{item_id}", "")

        if not rating:
            continue  # skip untouched items

        try:
            rating = int(rating)
        except Exception:
            rating = ""

        snapshot = {
            "learner_level": learner_level,
            "theme": item.get("theme", theme),
            "text_with_blank": item.get("segment", {}).get("text_with_blank"),
            "context_before": item.get("segment", {}).get("context_before"),
            "context_after": item.get("segment", {}).get("context_after"),
            "full_text": item.get("full_text"),
            "target": item.get("target"),
            "choices": item.get("choices"),
        }

        run_blob["items"][item_id] = {
            "item_snapshot": snapshot,
            "rating": rating,
            "issues": [],  # V1 simple; can extend later
            "comment": comment,
        }

    # Overwrite any previous run by this user for this exercise set
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

    def _set_created_at(set_id):
        runs_for_set = sets_dict.get(set_id, {}) or {}
        if not runs_for_set:
            return ""
        first_run_id = sorted(runs_for_set.keys(), reverse=True)[0]
        first_run = runs_for_set.get(first_run_id, {}) or {}
        return first_run.get("created_at", "")

    exercise_set_ids = sorted(
        sets_dict.keys(),
        key=lambda sid: _set_created_at(sid),
        reverse=True
    )

    requested_exercise_set_id = request.GET.get("exercise_set_id")
    if requested_exercise_set_id in exercise_set_ids:
        selected_exercise_set_id = requested_exercise_set_id
    else:
        selected_exercise_set_id = exercise_set_ids[0] if exercise_set_ids else ""

    runs_dict = sets_dict.get(selected_exercise_set_id, {}) if selected_exercise_set_id else {}
    run_ids = sorted(runs_dict.keys(), reverse=True)  # newest first

    # ---------- build human-readable exercise-set labels ----------
    exercise_set_options = []
    for set_id in exercise_set_ids:
        runs_for_set = sets_dict.get(set_id, {}) or {}

        created_at = ""
        theme = "none"
        learner_level = "intermediate"
        n_items = 0

        if runs_for_set:
            first_run_id = sorted(runs_for_set.keys(), reverse=True)[0]
            first_run = runs_for_set.get(first_run_id, {}) or {}
            created_at = first_run.get("created_at", "")
            theme = first_run.get("theme", "none")
            learner_level = first_run.get("learner_level", "intermediate")

            first_items = first_run.get("items", {}) or {}
            n_items = len(first_items)

            # if needed, fall back to snapshot
            if first_items:
                first_item_payload = next(iter(first_items.values()))
                first_snapshot = first_item_payload.get("item_snapshot", {}) if isinstance(first_item_payload, dict) else {}
                theme = first_run.get("theme") or first_snapshot.get("theme", theme)
                learner_level = first_run.get("learner_level") or first_snapshot.get("learner_level", learner_level)

        created_label = created_at[:16].replace("T", " ") if created_at else set_id
        theme_label = "No theme" if theme == "none" else theme

        label = f"{created_label} — {theme_label} — {n_items} items"
        if learner_level:
            label += f" — {learner_level}"

        exercise_set_options.append({
            "value": set_id,
            "label": label,
        })

    # ---------- aggregate across ALL runs ----------
    items_agg = {}  # item_id -> {snapshot, judges{run_id: payload}, rating_counts, mean_rating}
    judge_meta = []  # list of (run_id, user, created_at)

    def _norm_rating(v):
        if isinstance(v, int) and v in (1, 2, 3, 4, 5):
            return v
        if isinstance(v, str):
            try:
                v = int(v)
                if v in (1, 2, 3, 4, 5):
                    return v
            except Exception:
                pass
        return "unparsed"

    for rid in run_ids:
        run_payload = runs_dict.get(rid, {}) or {}
        judge_meta.append((rid, run_payload.get("user"), run_payload.get("created_at")))

        items = (run_payload.get("items") or {})
        for item_id, payload in items.items():
            snap = (payload.get("item_snapshot") or {})
            entry = items_agg.setdefault(item_id, {
                "item_id": item_id,
                "snapshot": snap,
                "judges": {},   # rid -> payload (rating, summary, comment, ...)
                "rating_counts": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, "unparsed": 0},
                "mean_rating": None,
            })

            rating = _norm_rating(payload.get("rating"))
            entry["judges"][rid] = payload
            entry["rating_counts"][rating] = entry["rating_counts"].get(rating, 0) + 1

    # compute mean rating after counting
    judged_rows = []
    for item_id, entry in items_agg.items():
        total = 0
        n = 0
        for rating in (1, 2, 3, 4, 5):
            count = entry["rating_counts"].get(rating, 0)
            total += rating * count
            n += count
        entry["mean_rating"] = round(total / n, 2) if n > 0 else None
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
                "r": judges_map.get(rid),
            })
        row["judge_cells"] = cells

    judged_rows.sort(key=lambda r: r["item_id"])

    # ---------------- CSV export (long format: one row per item × human judge/run) ----------------
    if request.GET.get("format") == "csv":
        header = [
            "exercise_type",
            "exercise_set_id",
            "judge_run_id",
            "judge_type",
            "judge_id",
            "learner_level",
            "theme",
            "rubric_version",
            "item_id",
            "text_with_blank",
            "correct",
            "distractors",
            "rating",
            "summary",
            "issues",
            "comment",
        ]

        rows = []
        for row in judged_rows:
            snap = row.get("snapshot") or {}
            item_id = row.get("item_id", "")

            learner_level = snap.get("learner_level") or ""
            theme = snap.get("theme") or "none"
            text_with_blank = snap.get("text_with_blank") or ""

            correct = ""
            distractors = []
            for c in (snap.get("choices") or []):
                form = c.get("form", "")
                if c.get("is_correct"):
                    correct = form
                else:
                    distractors.append(form)
            distractors_str = "|".join(distractors)

            for cell in (row.get("judge_cells") or []):
                r = cell.get("r")
                if not r:
                    continue

                rating = r.get("rating", "")
                summary = r.get("summary", "")
                issues = r.get("issues", [])
                comment = r.get("comment", "")

                rid = cell.get("rid", "")
                run_payload = runs_dict.get(rid, {}) or {}
                judge_id = run_payload.get("user") or cell.get("user") or ""
                rubric_version = run_payload.get("rubric_version") or ""
                run_level = run_payload.get("learner_level") or learner_level

                rows.append([
                    selected_exercise_type,
                    selected_exercise_set_id,
                    rid,
                    "human",
                    judge_id,
                    run_level,
                    theme,
                    rubric_version,
                    item_id,
                    text_with_blank,
                    correct,
                    distractors_str,
                    rating,
                    summary,
                    json.dumps(issues, ensure_ascii=False),
                    comment,
                ])

        filename = f"{project.internal_id}_{selected_exercise_type}_{selected_exercise_set_id}_human_judgements.csv"
        return _as_csv_response(filename, header, rows)

    return render(
        request,
        "clara_app/browse_human_exercise_judgements.html",
        {
            "project": project,
            "exercise_types": exercise_types,
            "selected_exercise_type": selected_exercise_type,

            "exercise_set_ids": exercise_set_ids,
            "selected_exercise_set_id": selected_exercise_set_id,
            "exercise_set_options": exercise_set_options,

            "run_ids": run_ids,
            "judge_meta": judge_meta,

            "judged_rows": judged_rows,
        },
    )

def human_exercise_judgements_exist_for_project(project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    d = load_exercise_human_judgements_dict(clara_project_internal)

    return False if not d else True

def _as_csv_response(filename: str, header: list[str], rows: list[list[str]]):
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    w = csv.writer(resp)
    w.writerow(header)
    w.writerows(rows)
    return resp

# Admin view

@login_required
@user_has_any_named_project_role(['OWNER'])
def maintain_exercise_files(request: HttpRequest, project_id: int) -> HttpResponse:
    """
    Maintenance/debugging view for exercise-related project files.
    Shows whether the files exist, whether they parse, and allows resetting them.
    """

    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    file_specs = [
        {
            "key": "exercises",
            "label": "Exercises",
            "empty_value": {},
        },
        {
            "key": "exercise_judgements",
            "label": "AI-panel judgements",
            "empty_value": {
                "schema_version": "1.0",
                "judgements": {}
            },
        },
        {
            "key": "exercise_human_judgements",
            "label": "Human judgements",
            "empty_value": {
                "schema_version": "1.0",
                "human_judgements": {}
            },
        },
    ]

    if request.method == "POST":
        file_key = request.POST.get("file_key")
        action = request.POST.get("action")

        spec = next((s for s in file_specs if s["key"] == file_key), None)
        if not spec:
            messages.error(request, "Unknown file type.")
            return redirect("maintain_exercise_files", project_id=project_id)

        if action == "clear":
            text = json.dumps(spec["empty_value"], indent=2, ensure_ascii=False) + "\n"
            clara_project_internal.save_text_version(
                file_key,
                text,
                source="human_revised",
                user=request.user.username,
                label="reset_by_maintenance_view",
            )
            messages.info(request, f"Reset {spec['label']} file.")
            return redirect("maintain_exercise_files", project_id=project_id)

        messages.error(request, "Unknown action.")
        return redirect("maintain_exercise_files", project_id=project_id)

    file_infos = []
    for spec in file_specs:
        key = spec["key"]
        label = spec["label"]

        file_path = Path(clara_project_internal._file_path_for_version(key))
        exists = file_path.exists()

        raw_text = clara_project_internal.load_text_version_or_null(key)
        size_bytes = len(raw_text.encode("utf-8")) if raw_text else 0

        parses = False
        non_trivial = False
        summary = ""
        parsed = None

        if raw_text:
            try:
                parsed = json.loads(raw_text)
                parses = True
                non_trivial = _is_non_trivial_exercise_data(key, parsed)
                summary = _summarise_exercise_data(key, parsed)
            except Exception as e:
                summary = f"JSON parse error: {e}"

        file_infos.append({
            "key": key,
            "label": label,
            "exists": exists,
            "path": str(file_path),
            "size_bytes": size_bytes,
            "parses": parses,
            "non_trivial": non_trivial,
            "summary": summary,
        })

    return render(
        request,
        "clara_app/maintain_exercise_files.html",
        {
            "project": project,
            "file_infos": file_infos,
        },
    )


def _is_non_trivial_exercise_data(file_key: str, parsed) -> bool:
    """
    Heuristic: does the parsed JSON appear to contain meaningful content?
    """
    if not parsed:
        return False

    if file_key == "exercises":
        if not isinstance(parsed, dict):
            return False
        for exercise_type, payload in parsed.items():
            if not payload:
                continue
            if isinstance(payload, dict):
                if "sets" in payload and isinstance(payload["sets"], dict) and payload["sets"]:
                    return True
                if "items" in payload and isinstance(payload["items"], list) and payload["items"]:
                    return True
        return False

    if file_key == "exercise_judgements":
        jud = parsed.get("judgements", {}) if isinstance(parsed, dict) else {}
        return bool(jud)

    if file_key == "exercise_human_judgements":
        jud = parsed.get("human_judgements", {}) if isinstance(parsed, dict) else {}
        return bool(jud)

    return False


def _summarise_exercise_data(file_key: str, parsed) -> str:
    """
    Short human-readable summary of the parsed content.
    """
    try:
        if file_key == "exercises":
            if not isinstance(parsed, dict):
                return "Not a JSON object."

            n_types = len(parsed)
            n_sets = 0
            n_items = 0

            for exercise_type, payload in parsed.items():
                if not isinstance(payload, dict):
                    continue
                if "sets" in payload and isinstance(payload["sets"], dict):
                    n_sets += len(payload["sets"])
                    for set_payload in payload["sets"].values():
                        if isinstance(set_payload, dict):
                            n_items += len(set_payload.get("items", []))
                elif "items" in payload and isinstance(payload["items"], list):
                    n_sets += 1
                    n_items += len(payload["items"])

            return f"{n_types} exercise type(s), {n_sets} set(s), {n_items} item(s)"

        if file_key == "exercise_judgements":
            if not isinstance(parsed, dict):
                return "Not a JSON object."

            jud = parsed.get("judgements", {})
            n_types = len(jud)
            n_sets = 0
            n_runs = 0
            n_items = 0

            for exercise_type, sets_dict in jud.items():
                if not isinstance(sets_dict, dict):
                    continue
                n_sets += len(sets_dict)
                for set_id, runs_dict in sets_dict.items():
                    if not isinstance(runs_dict, dict):
                        continue
                    n_runs += len(runs_dict)
                    for run_payload in runs_dict.values():
                        if isinstance(run_payload, dict):
                            n_items += len((run_payload.get("items") or {}))

            return f"{n_types} exercise type(s), {n_sets} set(s), {n_runs} AI judging run(s), {n_items} judged item entries"

        if file_key == "exercise_human_judgements":
            if not isinstance(parsed, dict):
                return "Not a JSON object."

            jud = parsed.get("human_judgements", {})
            n_types = len(jud)
            n_sets = 0
            n_runs = 0
            n_items = 0

            for exercise_type, sets_dict in jud.items():
                if not isinstance(sets_dict, dict):
                    continue
                n_sets += len(sets_dict)
                for set_id, runs_dict in sets_dict.items():
                    if not isinstance(runs_dict, dict):
                        continue
                    n_runs += len(runs_dict)
                    for run_payload in runs_dict.values():
                        if isinstance(run_payload, dict):
                            n_items += len((run_payload.get("items") or {}))

            return f"{n_types} exercise type(s), {n_sets} set(s), {n_runs} human judging run(s), {n_items} judged item entries"

    except Exception as e:
        return f"Summary error: {e}"

    return "No summary available."

