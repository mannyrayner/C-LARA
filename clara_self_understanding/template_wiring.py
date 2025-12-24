# clara_self_understanding/template_wiring.py
"""
Extract "wiring" information from key Django templates.

Currently focuses on:
  - {% url ... %} occurrences (URL name + raw args)
  - anchor text near the URL (best-effort)
  - tooltip/title text (high-signal description)
  - { % extends % } and { % include % } relationships between templates

Inputs:
  - A list of template repo paths (default: base.html and project_detail.html)

Output:
  clara_self_understanding/graphs/template_wiring.json

Schema (v1):
{
  "created_at": "...",
  "templates": [
     {
       "template_repo_path": "...",
       "local_path": "...",
       "extends": ["..."],
       "includes": ["..."],
       "url_refs": [
         {
           "url_name": "simple_clara",
           "args_raw": ["0", "'initial'"],
           "href_expr": "{% url ... %}",
           "title": "Create a new C-LARA project using Simple-C-LARA.",
           "anchor_text": "Create new C-LARA project using Simple-C-LARA",
           "line": 123
         },
         ...
       ]
     },
     ...
  ]
}

Notes:
  - Parsing is intentionally lightweight (regex + small heuristics).
  - This file is intended to be extended iteratively (forms, POST actions, JS fetch, etc.)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .download_from_repo import ensure_local_copy

SELF_UNDERSTANDING_ROOT = Path(__file__).resolve().parent


# ----------------------------
# Regex patterns (lightweight)
# ----------------------------

# {% url 'name' arg1 arg2 %}
URL_TAG_RE = re.compile(
    r"""{%\s*url\s+(?P<q>['"])(?P<name>[^'"]+)(?P=q)\s*(?P<args>.*?)\s*%}"""
)

# {% extends "path/to.html" %} or {% extends '...' %}
EXTENDS_RE = re.compile(r"""{%\s*extends\s+(?P<q>['"])(?P<path>[^'"]+)(?P=q)\s*%}""")

# {% include "path/to.html" %} or {% include '...' %}
INCLUDE_RE = re.compile(r"""{%\s*include\s+(?P<q>['"])(?P<path>[^'"]+)(?P=q)\s*%}""")

# title="..."
TITLE_RE = re.compile(r"""title\s*=\s*(?P<q>['"])(?P<title>.*?)(?P=q)""", re.IGNORECASE)

# Best-effort anchor text: <a ...>TEXT</a>
ANCHOR_TEXT_RE = re.compile(r"""<a\b[^>]*>(?P<text>.*?)</a>""", re.IGNORECASE | re.DOTALL)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _split_args_raw(args_str: str) -> List[str]:
    """
    Very lightweight splitter for url tag args. We keep raw tokens because
    Django template expressions can be complex.

    Example:
      "0 'initial'" -> ["0", "'initial'"]
    """
    args_str = (args_str or "").strip()
    if not args_str:
        return []

    # Split on whitespace, but preserve quoted literals as single tokens.
    # Good enough for v1; we can replace later with a proper template lexer if needed.
    tokens: List[str] = []
    buf = []
    in_quote: Optional[str] = None

    for ch in args_str:
        if in_quote:
            buf.append(ch)
            if ch == in_quote:
                in_quote = None
            continue

        if ch in ("'", '"'):
            buf.append(ch)
            in_quote = ch
            continue

        if ch.isspace():
            if buf:
                tokens.append("".join(buf).strip())
                buf = []
            continue

        buf.append(ch)

    if buf:
        tokens.append("".join(buf).strip())

    return [t for t in tokens if t]


def _nearest_title_and_anchor(lines: List[str], idx: int, window: int = 6) -> Tuple[Optional[str], Optional[str]]:
    """
    Look around the line with the {% url ... %} for:
      - title="..."
      - <a ...> ... </a> anchor text
    """
    start = max(0, idx - window)
    end = min(len(lines), idx + window + 1)
    chunk = "\n".join(lines[start:end])

    title = None
    m = TITLE_RE.search(chunk)
    if m:
        title = m.group("title").strip()

    anchor_text = None
    m2 = ANCHOR_TEXT_RE.search(chunk)
    if m2:
        # strip tags inside anchor text, collapse whitespace
        raw = m2.group("text")
        raw = re.sub(r"<[^>]+>", "", raw)
        raw = re.sub(r"\s+", " ", raw).strip()
        if raw:
            anchor_text = raw

    return title, anchor_text


@dataclass
class UrlRef:
    url_name: str
    args_raw: List[str]
    href_expr: str
    title: Optional[str]
    anchor_text: Optional[str]
    line: int


@dataclass
class TemplateWiring:
    template_repo_path: str
    local_path: str
    extends: List[str]
    includes: List[str]
    url_refs: List[UrlRef]


def extract_wiring_from_template(repo_path: str) -> TemplateWiring:
    meta = ensure_local_copy(repo_path)
    local_path = Path(meta.local_path)

    text = local_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    extends = [m.group("path") for m in EXTENDS_RE.finditer(text)]
    includes = [m.group("path") for m in INCLUDE_RE.finditer(text)]

    url_refs: List[UrlRef] = []

    for i, line in enumerate(lines):
        for m in URL_TAG_RE.finditer(line):
            url_name = m.group("name")
            args_str = m.group("args") or ""
            args_raw = _split_args_raw(args_str)
            href_expr = m.group(0)

            title, anchor_text = _nearest_title_and_anchor(lines, i)

            url_refs.append(
                UrlRef(
                    url_name=url_name,
                    args_raw=args_raw,
                    href_expr=href_expr,
                    title=title,
                    anchor_text=anchor_text,
                    line=i + 1,
                )
            )

    return TemplateWiring(
        template_repo_path=repo_path,
        local_path=str(local_path),
        extends=extends,
        includes=includes,
        url_refs=url_refs,
    )


def extract_template_wiring(
    template_repo_paths: Optional[List[str]] = None,
) -> Dict[str, Any]:
    if template_repo_paths is None:
        template_repo_paths = [
            "clara_app/templates/clara_app/base.html",
            "clara_app/templates/clara_app/project_detail.html",
        ]

    templates: List[TemplateWiring] = []
    for rp in template_repo_paths:
        print(f"[template-wiring] extracting {rp}")
        templates.append(extract_wiring_from_template(rp))

    out = {
        "created_at": _now_iso(),
        "templates": [asdict(t) for t in templates],
    }
    return out


def save_template_wiring(out: Dict[str, Any]) -> Path:
    out_path = SELF_UNDERSTANDING_ROOT / "graphs" / "template_wiring.json"
    _write_json(out_path, out)
    return out_path


def main() -> None:
    out = extract_template_wiring()
    path = save_template_wiring(out)

    n_templates = len(out.get("templates", []))
    n_urls = sum(len(t.get("url_refs", [])) for t in out.get("templates", []))
    print(f"[template-wiring] templates={n_templates} url_refs={n_urls}")
    print(f"[template-wiring] wrote {path}")


if __name__ == "__main__":
    main()
