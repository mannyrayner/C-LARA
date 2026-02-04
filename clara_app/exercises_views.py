
# clara_app/exercise_views.py

from datetime import datetime, timezone
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

from .models import CLARAProject
from .clara_main import CLARAProjectInternal
from .clara_classes import InternalCLARAError, InternalisationError, MWEError, ImageGenerationError

from .utils import get_user_config, user_has_open_ai_key_or_credit, user_has_open_ai_key_or_credit_warn_if_admin_with_negative_balance, store_api_calls, store_cost_dict, make_asynch_callback_and_report_id
from .utils import user_has_a_project_role
from .utils import get_task_updates

from .clara_utils import get_config, file_exists
from .clara_utils import post_task_update

import asyncio
import json
import random
import logging
import pprint
import traceback

config = get_config()

EXERCISE_TYPES = [
    ("cloze_mcq", "Cloze (multiple choice)"),
]

CLOZE_PROMPT_VERSION = "cloze_distractors_v1"
MODEL_NAME = "gpt-5"


@login_required
@user_has_a_project_role
def generate_exercises(request: HttpRequest, project_id: int, status: str) -> HttpResponse:
    if status == 'finished':
        messages.info("Exercise generation completed normally.")
    elif status == 'error':
        messages.info("Error in exercise generation. Look at the 'Recent task updates' tab for more details.")
    project = get_object_or_404(CLARAProject, pk=project_id)
    clara_project_internal = CLARAProjectInternal(project.internal_id, project.l2, project.l1)

    if request.method == "GET":
        return render(
            request,
            "clara_app/generate_exercises.html",
            {
                "project": project,
                "exercise_types": EXERCISE_TYPES,
                "defaults": {"exercise_type": "cloze_mcq", "n_examples": 20, "n_distractors": 3},
            },
        )

    # POST
    exercise_type = request.POST.get("exercise_type", "cloze_mcq")
    n_examples = int(request.POST.get("n_examples", "20"))
    n_distractors = int(request.POST.get("n_distractors", "3"))
    seed_str = request.POST.get("seed", "").strip()
    seed = int(seed_str) if seed_str else random.randint(1, 10**9)

    if exercise_type not in dict(EXERCISE_TYPES):
        messages.error(request, "Unknown exercise type.")
        return redirect("generate_exercises", project_id=project_id)
    if not (1 <= n_examples <= 200):
        messages.error(request, "Number of examples must be between 1 and 200.")
        return redirect("generate_exercises", project_id=project_id)
    if not (1 <= n_distractors <= 5):
        messages.error(request, "Number of distractors must be between 1 and 5.")
        return redirect("generate_exercises", project_id=project_id)

    # Build internalised/annotated structure (pages -> segments -> content elements)
    text_obj = clara_project_internal.get_internalised_text_exact()

    rng = random.Random(seed)

    callback, report_id = make_asynch_callback_and_report_id(request, 'exercises')
    async_task(create_and_save_exercise_items, project, clara_project_internal, text_obj, exercise_type, n_examples, n_distractors, text_obj, rng, callback=callback)

    return redirect('generate_exercises_monitor', project_id, report_id)

@login_required
@user_has_a_project_role
def generate_exercises_monitor(request, project_id, report_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    
    return render(request, 'clara_app/generate_exercises_monitor.html',
                  {'project_id': project_id, 'project': project, 'report_id': report_id})

@login_required
@user_has_a_project_role
def generate_exercises_status(request, project_id, report_id):
    messages = get_task_updates(report_id)
    print(f'{len(messages)} messages received')
    if 'error' in messages:
        status = 'error'
    elif 'finished' in messages:
        status = 'finished'  
    else:
        status = 'unknown'    
    return JsonResponse({'messages': messages, 'status': status})

def create_and_save_exercise_items(project, clara_project_internal, text_obj, exercise_type, n_examples, n_distractors, rng, callback=None):
    try:
        if exercise_type == 'cloze_mcq':
            create_and_save_cloze_exercise_items(project, clara_project_internal, exercise_type, n_examples, n_distractors, text_obj, rng, callback=callback)
    except Exception as e:
        post_task_update(callback, f"Error when creating exercise items")
        post_task_update(callback, f"Exception: {str(e)}\n{traceback.format_exc()}")
        post_task_update(callback, f"error")


# -------------- Cloze exercises -----------------------

def create_and_save_cloze_exercise_items(project, clara_project_internal, text_obj, exercise_type, n_examples, n_distractors, rng, callback=None):
    exercise_targets = select_random_cloze_targets(text_obj, n_examples, rng)

    # Generate distractors in parallel
    
    params = { 'n_distractors': n_distractors,
               'gpt_model': MODEL_NAME,
               }
    items = asyncio.run(
        process_cloze_exercise_targets(project, clara_project_internal, text_obj, params, exercise_targets, callback=callback)
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

    # Store exercises
    clara_project_internal.save_exercises(exercise_type, payload)
    post_task_update(callback, f"finished")

def select_random_cloze_targets(text_obj, n_examples: int, rng: random.Random):
    """
    Return a list of dict targets with enough info to build prompts.
    internalised is expected to provide pages->segments->content elements with annotations.
    """
    candidates = []
    for p_i, page in enumerate(text_obj.pages):
        for s_i, seg in enumerate(page.segments):
            # only consider segments with at least one eligible content element
            eligible = [ce for ce in seg.content_elements if is_eligible_target(ce)]
            if not eligible:
                continue
            candidates.append((p_i, s_i, seg, eligible))

    rng.shuffle(candidates)

    selected = []
    for (p_i, s_i, seg, eligible) in candidates:
        ce = rng.choice(eligible)
        selected.append({"page_index": p_i,
                         "segment_index": s_i,
                         "segment": seg,
                         "target_ce": ce})
        if len(selected) >= n_examples:
            break
    return selected

def is_eligible_target(content_element) -> bool:
    # V1: avoid punctuation, very short tokens, etc. Adjust as needed.
    if getattr(content_element, "is_punctuation", False):
        return False
    type = content_element.type
    surface = content_element.content.strip()
    if type != 'Word' or len(surface) < 2:
        return False
    # optionally avoid proper nouns etc
    return True

async def process_cloze_exercise_targets(project, clara_project_internal, text_obj, params, exercise_targets, callback=None):
    tasks = []
    for exercise_target in exercise_targets:
        tasks.append(
            asyncio.create_task(
                generate_cloze_exercise_item(exercise_target, project, text_obj, params, callback=callback)
            )
        )

    results = await asyncio.gather(*tasks)

    exercises = []
    total_cost = {}

    for exercise_json, cost_dict in results:
        exercises.append(exercise_json)
        total_cost = combine_cost_dicts(total_cost, cost_dict)

    clara_project_internal.save_exercises(
        exercise_type=params["exercise_type"],
        exercises=exercises,
        source="ai_generated",
        user=params.get("user", "Unknown")
    )

    return total_cost

async def generate_cloze_exercise_item(exercise_target, project, text_obj, params, callback=None):
    seg = exercise_target["segment"]
    ce = exercise_target["target_ce"]

    segment_text = seg.to_text("plain")  # already normalised string
    target_surface = ce.to_text("plain")
    lemma = getattr(ce, "lemma", None)
    pos = getattr(ce, "pos", None)

    page_index = exercise_target["page_index"]
    seg_index = exercise_target["segment_index"]
    segments = text_obj.pages[page_index].segments
    context_before = segments[seg_index - 1].to_text("plain") if seg_index - 1 >= 0 else None
    context_after = segments[seg_index + 1].to_text("plain") if seg_index + 1 <= len(segments) else None

    model = params["model"]

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

    # Expect JSON output
    resp = await get_api_chatgpt4_response(prompt, config_info={'gpt_model': model}, callback=callback)

    choices = normalise_choices(resp, correct=target_surface)

    # Fill in more of this when the basic mechanism is working
    return {
        #"item_id": f"p{target_info['page_index']:02d}_s{target_info['segment_index']:02d}_{getattr(ce,'id','t')}",
        "page_index": target_info["page_index"],
        "segment_index": target_info["segment_index"],
        "target": {
            #"content_element_id": getattr(ce, "id", None),
            "surface": target_surface,
            "lemma": lemma,
            "pos": pos,
            #"mwe_id": mwe_id,
        },
        "segment": {
            "text": segment_text,
            "text_with_blank": blank_out(segment_text, target_surface),
            "context_before": context_before,
            "context_after": context_after,
        },
        "choices": choices,
        "notes": {"generation_model": model, "prompt_version": PROMPT_VERSION},
    }

def build_cloze_distractor_prompt(*, segment_text, target_surface, lemma, pos, 
                                 context_before, context_after, n_distractors, l2):
    # Keep it short but explicit; V1 prompt.
    # Important: ask for distractors that are plausible but clearly wrong in this context.
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
- Distractors must have the same part of speech as the target (or as close as possible).
- Distractors must be plausible to a learner but incorrect in this exact segment.
- Do NOT include the correct answer among distractors.
- Return STRICT JSON in this schema:
{{
  "distractors": [
    {{"form": "....", "reason": "short reason"}},
    ...
  ]
}}
""".strip()

def normalise_choices(resp_json, correct: str):
    distractors = resp_json.get("distractors", []) if isinstance(resp_json, dict) else []
    # dedupe, strip
    forms = []
    for d in distractors:
        f = (d.get("form") or "").strip()
        if f and f.lower() != correct.lower() and f.lower() not in {x.lower() for x in forms}:
            forms.append(f)
    # ensure we have at least something
    forms = forms[:10]

    choices = [{"form": correct, "is_correct": True, "reason": "correct"}]
    for f in forms:
        choices.append({"form": f, "is_correct": False, "reason": "distractor"})
    # If short, you can pad with trivial variants or leave short; up to you.
    return choices


def blank_out(segment_text: str, target_surface: str) -> str:
    # V1: naive replace first occurrence; later use offsets from internalised representation.
    return segment_text.replace(target_surface, "____", 1)

