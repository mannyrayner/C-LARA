# clara_self_understanding/openai_utils.py

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore


# -----------------------------------------------------------------------------
# Pricing
# -----------------------------------------------------------------------------

SELF_DIR = Path(__file__).resolve().parent
PRICES_FILE = SELF_DIR / "prices.json"


def load_prices() -> Dict[str, Any]:
    if not PRICES_FILE.exists():
        return {"models": {}}
    return json.loads(PRICES_FILE.read_text(encoding="utf-8"))


def estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Estimate USD cost using prices.json (USD per 1M tokens).

    prices.json schema:
      models[model][tier]['input'/'output'/'cached_input'] = float

    We choose a tier preference order: standard -> priority -> batch -> unknown.
    """
    prices = load_prices()
    tiers = (prices.get("models") or {}).get(model)
    if not tiers or not isinstance(tiers, dict):
        return 0.0

    entry = (
        tiers.get("standard")
        or tiers.get("priority")
        or tiers.get("batch")
        or tiers.get("unknown")
    )
    if not entry or not isinstance(entry, dict):
        return 0.0

    in_per_1m = float(entry.get("input", 0.0))
    out_per_1m = float(entry.get("output", 0.0))

    return (prompt_tokens / 1_000_000.0) * in_per_1m + (completion_tokens / 1_000_000.0) * out_per_1m


# -----------------------------------------------------------------------------
# Usage model
# -----------------------------------------------------------------------------

@dataclass
class ModelUsage:
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float


# -----------------------------------------------------------------------------
# Model selection / endpoints
# -----------------------------------------------------------------------------

def _is_responses_only_model(model: str) -> bool:
    """
    Heuristic: Codex models are Responses-API-only (e.g. gpt-5.1-codex-max). :contentReference[oaicite:1]{index=1}
    """
    return "codex" in (model or "").lower()


def create_openai_client() -> Any:
    if OpenAI is None:
        raise RuntimeError(
            "openai package not installed. Please `pip install openai` "
            "in the environment where you run this script."
        )
    return OpenAI()


def _extract_usage_tokens(usage_obj: Any) -> Tuple[int, int, int]:
    """
    Normalize usage token fields across endpoints.

    Chat Completions commonly provides:
      usage.prompt_tokens, usage.completion_tokens, usage.total_tokens

    Responses commonly provides:
      usage.input_tokens, usage.output_tokens, usage.total_tokens
    """
    if usage_obj is None:
        return (0, 0, 0)

    # Attribute-style objects
    pt = getattr(usage_obj, "prompt_tokens", None)
    ct = getattr(usage_obj, "completion_tokens", None)
    tt = getattr(usage_obj, "total_tokens", None)
    if pt is not None and ct is not None:
        pt_i, ct_i = int(pt), int(ct)
        return (pt_i, ct_i, int(tt) if tt is not None else pt_i + ct_i)

    it = getattr(usage_obj, "input_tokens", None)
    ot = getattr(usage_obj, "output_tokens", None)
    tt2 = getattr(usage_obj, "total_tokens", None)
    if it is not None and ot is not None:
        it_i, ot_i = int(it), int(ot)
        return (it_i, ot_i, int(tt2) if tt2 is not None else it_i + ot_i)

    # Dict fallback
    if isinstance(usage_obj, dict):
        if "prompt_tokens" in usage_obj and "completion_tokens" in usage_obj:
            pt_i = int(usage_obj.get("prompt_tokens", 0))
            ct_i = int(usage_obj.get("completion_tokens", 0))
            return (pt_i, ct_i, int(usage_obj.get("total_tokens", pt_i + ct_i)))
        if "input_tokens" in usage_obj and "output_tokens" in usage_obj:
            it_i = int(usage_obj.get("input_tokens", 0))
            ot_i = int(usage_obj.get("output_tokens", 0))
            return (it_i, ot_i, int(usage_obj.get("total_tokens", it_i + ot_i)))

    return (0, 0, 0)


# -----------------------------------------------------------------------------
# Prompt builder + response parser
# -----------------------------------------------------------------------------

def build_docstring_prompts(repo_path: str, source_code: str) -> Tuple[str, str]:
    system_prompt = (
        "You are C-LARA's self-understanding assistant. You analyse Django view "
        "modules and produce high-level documentation suitable as a top-of-file "
        "docstring. Focus on:\n"
        "- What the module is responsible for\n"
        "- Key entry points and workflows\n"
        "- How it interacts with async tasks / models / templates\n"
        "- Any notable caveats a maintainer should know\n\n"
        "Your output MUST be valid JSON."
    )

    user_prompt = (
        f"Repo path: {repo_path}\n\n"
        "Here is the full source code of a Django views module. "
        "Analyse it and produce a JSON object with the following fields:\n"
        "  - proposed_docstring: A module-level docstring as a single string, "
        "written in natural language (no surrounding triple quotes).\n"
        "  - short_summary: 2–4 sentence summary of what this module does.\n"
        "  - key_responsibilities: A short list of bullet points (strings).\n"
        "  - potential_issues: A short list of potential bugs, edge cases or "
        "design caveats (strings). If you are not sure, include your best-guess "
        "suspicions anyway.\n\n"
        "Return ONLY the JSON object, nothing else.\n\n"
        f"Source code:\n{source_code}"
    )

    return system_prompt, user_prompt


def parse_docstring_response(content: str) -> Dict[str, Any]:
    """
    Parse model output as JSON, falling back to a wrapper dict.
    """
    content = content or "{}"
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {
            "proposed_docstring": content,
            "short_summary": "",
            "key_responsibilities": [],
            "potential_issues": ["Model response was not valid JSON; stored raw text."],
        }


# -----------------------------------------------------------------------------
# Endpoint-specific call
# -----------------------------------------------------------------------------

def _call_openai_model(
    client: Any,
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> Tuple[str, Any]:
    """
    Make the OpenAI call using the correct endpoint for the model.

    Returns (text_content, usage_obj).
    """
    if _is_responses_only_model(model):
        # Responses API (Codex family). :contentReference[oaicite:2]{index=2}
        resp = client.responses.create(
            model=model,
            instructions=system_prompt,
            input=user_prompt,
            # temperature for Responses differs by model; omit unless needed.
        )
        text = getattr(resp, "output_text", "") or ""
        usage_obj = getattr(resp, "usage", None)
        return text, usage_obj

    # Chat Completions API
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
    )
    text = resp.choices[0].message.content or ""
    usage_obj = getattr(resp, "usage", None)
    return text, usage_obj


# -----------------------------------------------------------------------------
# Public API used by docstring_metadata.py
# -----------------------------------------------------------------------------

def call_model_for_docstring(
    client: Any,
    model: str,
    repo_path: str,
    source_code: str,
) -> Tuple[Dict[str, Any], ModelUsage]:
    """
    Generate docstring-style metadata for a source file and return (analysis, usage).
    Chooses the correct OpenAI endpoint based on model name.
    """
    system_prompt, user_prompt = build_docstring_prompts(repo_path, source_code)
    content, usage_obj = _call_openai_model(client, model, system_prompt, user_prompt)

    analysis = parse_docstring_response(content)

    prompt_tokens, completion_tokens, total_tokens = _extract_usage_tokens(usage_obj)
    cost = estimate_cost_usd(model, prompt_tokens, completion_tokens)

    usage = ModelUsage(
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=cost,
    )
    return analysis, usage
