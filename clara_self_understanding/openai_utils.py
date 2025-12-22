# clara_self_understanding/openai_utils.py

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from pathlib import Path

SELF_DIR = Path(__file__).resolve().parent
PRICES_FILE = SELF_DIR / "prices.json"

try:
    from openai import OpenAI  # new-style OpenAI client
except ImportError:  # fallback for older client installs
    OpenAI = None  # type: ignore


@dataclass
class ModelUsage:
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float


def load_prices() -> Dict[str, Any]:
    if not PRICES_FILE.exists():
        return {"models": {}}
    return json.loads(PRICES_FILE.read_text(encoding="utf-8"))


def estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    prices = load_prices()
    tiers = (prices.get("models") or {}).get(model)
    if not tiers:
        return 0.0

    # Prefer standard, then priority, then batch, then unknown
    entry = (
        tiers.get("standard")
        or tiers.get("priority")
        or tiers.get("batch")
        or tiers.get("unknown")
    )
    if not entry:
        return 0.0

    in_per_1m = float(entry.get("input", 0.0))
    out_per_1m = float(entry.get("output", 0.0))

    return (prompt_tokens / 1_000_000.0) * in_per_1m + (completion_tokens / 1_000_000.0) * out_per_1m

def create_openai_client() -> Any:
    """
    Create an OpenAI client instance.

    Requires that the OPENAI_API_KEY env var is set (standard convention for the
    newer OpenAI Python client).
    """
    if OpenAI is None:
        raise RuntimeError(
            "openai package not installed. Please `pip install openai` "
            "in the environment where you run this script."
        )
    return OpenAI()


def call_model_for_docstring(
    client: Any,
    model: str,
    repo_path: str,
    source_code: str,
) -> Tuple[Dict[str, Any], ModelUsage]:
    """
    Ask an OpenAI chat model to generate docstring-style metadata for a source file.

    Returns:
        (analysis_dict, usage)
        where analysis_dict is a JSON-like dict with keys like:
            - 'proposed_docstring'
            - 'short_summary'
            - 'key_responsibilities'
            - 'potential_issues'
        and usage contains token counts and cost estimate.
    """
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

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
    )

    content = resp.choices[0].message.content or "{}"

    try:
        analysis = json.loads(content)
    except json.JSONDecodeError:
        # Fall back to a simple wrapper if the model returned plain text
        analysis = {
            "proposed_docstring": content,
            "short_summary": "",
            "key_responsibilities": [],
            "potential_issues": ["Model response was not valid JSON; stored raw text."],
        }

    usage = getattr(resp, "usage", None)

    if usage is None:
        # Some tools/models might not populate usage; default to 0s.
        usage_obj = ModelUsage(
            model=model,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            estimated_cost_usd=0.0,
        )
    else:
        prompt_tokens = usage.prompt_tokens or 0
        completion_tokens = usage.completion_tokens or 0
        total_tokens = usage.total_tokens or (prompt_tokens + completion_tokens)
        cost = estimate_cost_usd(model, prompt_tokens, completion_tokens)
        usage_obj = ModelUsage(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=cost,
        )

    return analysis, usage_obj
