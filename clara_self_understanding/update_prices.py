# clara_self_understanding/update_prices.py
"""
Update clara_self_understanding/prices.json by scraping OpenAI's pricing page HTML.

Why this exists:
- https://platform.openai.com/docs/pricing is often JS-rendered; fetching it with requests may
  not include the full pricing table.
- This script supports reading a local HTML snapshot (recommended for reproducibility) and
  also supports fetching the live URL (best-effort).

Usage:
  # Recommended: parse a local HTML snapshot
  python -m clara_self_understanding.update_prices --html OpenAIPricingInfoDowloaded.html

  # Best-effort: fetch live page
  python -m clara_self_understanding.update_prices

Output:
  clara_self_understanding/prices.json

Schema:
{
  "updated_at": "...",
  "source": "...",
  "units": "USD per 1M tokens",
  "models": {
    "gpt-5.2": {
      "standard": {"input": 3.50, "cached_input": 0.35, "output": 28.00},
      "priority": {"input": 0.875, "cached_input": 0.0875, "output": 7.00}
    },
    ...
  }
}

Notes:
- The pricing page contains multiple tables (Standard, Priority, Batch). The HTML snapshot you
  saved may contain hidden tables; we parse them too.
- We infer table tier ("standard", "priority", "batch") by looking at nearby headings.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests
from bs4 import BeautifulSoup, Tag

SELF_DIR = Path(__file__).resolve().parent
PRICES_FILE = SELF_DIR / "prices.json"
PRICING_URL = "https://platform.openai.com/docs/pricing"

# Accept model families we care about; broaden later if desired.
MODEL_PREFIXES = ("gpt-", "o", "chatgpt-", "gpt_image", "gpt-image", "whisper", "tts", "text-embedding", "omni")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_money(cell_text: str) -> Optional[float]:
    """
    Parse '$3.50', '3.50', '$0.0875', '-' into float or None.
    """
    t = cell_text.strip()
    if not t or t == "-":
        return None
    # Remove commas, $ and whitespace
    t = t.replace(",", "").replace("$", "").strip()
    # Sometimes the cell may contain things like "Free" or "Included"
    try:
        return float(t)
    except ValueError:
        return None


def _normalize_model_name(name: str) -> str:
    return name.strip()


def _looks_like_model_name(name: str) -> bool:
    n = name.strip()
    if not n:
        return False
    # Fast path: most models start with gpt-
    if n.startswith("gpt-"):
        return True
    # Allow other known prefixes, but avoid obvious non-model words
    return n.startswith(MODEL_PREFIXES) and " " not in n and "/" not in n


def _infer_tier_for_table(table: Tag) -> str:
    """
    Infer whether this table is Standard / Priority / Batch by inspecting nearby headings.

    We walk backwards from the table looking for text that contains 'Standard', 'Priority', or 'Batch'.
    If not found, default to 'unknown'.
    """
    # Look at up to N previous elements for a heading-like label
    current: Optional[Tag] = table
    for _ in range(80):
        if current is None:
            break
        current = current.find_previous()
        if current is None:
            break

        # Ignore giant blocks like script/style
        if current.name in ("script", "style"):
            continue

        text = current.get_text(" ", strip=True).lower()
        if not text:
            continue

        # Prefer short-ish text blobs
        if len(text) > 80:
            continue

        if "priority" in text:
            return "priority"
        if "standard" in text:
            return "standard"
        if "batch" in text:
            return "batch"

    return "unknown"


def _extract_pricing_rows(table: Tag) -> Dict[str, Dict[str, Optional[float]]]:
    """
    Extract model rows from a pricing table.

    Expected header columns (order may vary slightly, but typical is):
      Model | Input | Cached input | Output

    We accept rows with >= 4 columns and read the first 4.
    """
    rows: Dict[str, Dict[str, Optional[float]]] = {}

    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue

        model = _normalize_model_name(tds[0].get_text(" ", strip=True))
        if not _looks_like_model_name(model):
            continue

        input_price = _parse_money(tds[1].get_text(" ", strip=True))
        cached_input_price = _parse_money(tds[2].get_text(" ", strip=True))
        output_price = _parse_money(tds[3].get_text(" ", strip=True))

        # Only keep rows where we found at least one numeric price
        if input_price is None and cached_input_price is None and output_price is None:
            continue

        rows[model] = {
            "input": input_price,
            "cached_input": cached_input_price,
            "output": output_price,
        }

    return rows


def parse_pricing_html(html: str) -> Tuple[Dict[str, Dict[str, Dict[str, float]]], int]:
    """
    Parse pricing HTML and return:
      models -> {model_name: {tier: {input/cached_input/output}}}
    and number of (model, tier) entries harvested.
    """
    soup = BeautifulSoup(html, "html.parser")
    models: Dict[str, Dict[str, Dict[str, float]]] = {}
    entries = 0

    tables = soup.find_all("table")
    for table in tables:
        tier = _infer_tier_for_table(table)
        rows = _extract_pricing_rows(table)
        if not rows:
            continue

        for model, prices in rows.items():
            # Convert Optional[float] to float only for values we found
            cleaned: Dict[str, float] = {}
            for k, v in prices.items():
                if v is not None:
                    cleaned[k] = float(v)

            if not cleaned:
                continue

            if model not in models:
                models[model] = {}

            # If tier is unknown, store under 'unknown'; still useful.
            models[model][tier] = cleaned
            entries += 1

    return models, entries


def update_prices_file(html_path: Optional[str] = None) -> Dict:
    """
    Update prices.json using either a local HTML file or live fetch (best-effort).
    """
    if html_path:
        source_desc = f"file:{html_path}"
        html = Path(html_path).read_text(encoding="utf-8", errors="replace")
    else:
        source_desc = PRICING_URL
        resp = requests.get(PRICING_URL, timeout=30)
        resp.raise_for_status()
        html = resp.text

    models, n_entries = parse_pricing_html(html)

    data = {
        "updated_at": _now_iso(),
        "source": source_desc,
        "canonical_source": PRICING_URL,
        "units": "USD per 1M tokens",
        "models": dict(sorted(models.items(), key=lambda kv: kv[0])),
        "entries_harvested": n_entries,
    }

    PRICES_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape OpenAI pricing into prices.json (BeautifulSoup).")
    parser.add_argument(
        "--html",
        dest="html_path",
        default=None,
        help="Path to a locally saved pricing HTML file (recommended).",
    )
    args = parser.parse_args()

    out = update_prices_file(html_path=args.html_path)
    print(f"Updated {PRICES_FILE} with {len(out.get('models', {}))} models "
          f"({out.get('entries_harvested', 0)} model-tier entries) from {out.get('source')}.")


if __name__ == "__main__":
    main()
