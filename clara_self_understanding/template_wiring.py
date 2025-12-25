# clara_self_understanding/template_wiring.py

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup  # pip install beautifulsoup4
from .download_from_repo import ensure_local_copy

SELF_UNDERSTANDING_ROOT = Path(__file__).resolve().parent

URL_TAG_RE = re.compile(
    r"""{%\s*url\s+(?P<q>['"])(?P<name>[^'"]+)(?P=q)\s*(?P<args>.*?)\s*%}"""
)
EXTENDS_RE = re.compile(r"""{%\s*extends\s+(?P<q>['"])(?P<path>[^'"]+)(?P=q)\s*%}""")
INCLUDE_RE = re.compile(r"""{%\s*include\s+(?P<q>['"])(?P<path>[^'"]+)(?P=q)\s*%}""")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _split_args_raw(args_str: str) -> List[str]:
    """
    Keep args as raw template tokens. This is fine; resolution comes later.
    """
    s = (args_str or "").strip()
    if not s:
        return []
    # cheap tokeniser preserving quoted strings
    out: List[str] = []
    buf: List[str] = []
    q: Optional[str] = None
    for ch in s:
        if q:
            buf.append(ch)
            if ch == q:
                q = None
            continue
        if ch in ("'", '"'):
            buf.append(ch)
            q = ch
            continue
        if ch.isspace():
            if buf:
                out.append("".join(buf).strip())
                buf = []
            continue
        buf.append(ch)
    if buf:
        out.append("".join(buf).strip())
    return [t for t in out if t]


def _parse_url_tag(expr: str) -> Optional[Dict[str, Any]]:
    """
    If expr contains a Django {% url ... %} tag, return parsed fields.
    """
    m = URL_TAG_RE.search(expr or "")
    if not m:
        return None
    return {
        "url_name": m.group("name"),
        "args_raw": _split_args_raw(m.group("args") or ""),
        "href_expr": m.group(0),
    }


@dataclass
class UrlRef:
    url_name: str
    args_raw: List[str]
    href_expr: str
    element: str                 # "a" or "form" etc
    attr: str                    # "href" or "action"
    title: Optional[str]
    text: Optional[str]


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

    raw = local_path.read_text(encoding="utf-8", errors="replace")

    # Keep extends/includes from raw text; they're not HTML.
    extends = [m.group("path") for m in EXTENDS_RE.finditer(raw)]
    includes = [m.group("path") for m in INCLUDE_RE.finditer(raw)]

    soup = BeautifulSoup(raw, "html.parser")

    url_refs: List[UrlRef] = []

    # Anchor links
    for a in soup.find_all("a"):
        href = a.get("href")
        parsed = _parse_url_tag(href or "")
        if not parsed:
            continue
        title = a.get("title")
        text = a.get_text(" ", strip=True) or None
        url_refs.append(
            UrlRef(
                url_name=parsed["url_name"],
                args_raw=parsed["args_raw"],
                href_expr=parsed["href_expr"],
                element="a",
                attr="href",
                title=title,
                text=text,
            )
        )

    # Forms posting to URLs
    for form in soup.find_all("form"):
        action = form.get("action")
        parsed = _parse_url_tag(action or "")
        if not parsed:
            continue
        title = form.get("title")  # uncommon, but harmless
        # Use a compact textual descriptor for the form: first button text, else None
        btn = form.find(["button", "input"])
        form_text = None
        if btn:
            if btn.name == "button":
                form_text = btn.get_text(" ", strip=True) or None
            elif btn.name == "input":
                form_text = btn.get("value") or None

        url_refs.append(
            UrlRef(
                url_name=parsed["url_name"],
                args_raw=parsed["args_raw"],
                href_expr=parsed["href_expr"],
                element="form",
                attr="action",
                title=title,
                text=form_text,
            )
        )

    return TemplateWiring(
        template_repo_path=repo_path,
        local_path=str(local_path),
        extends=extends,
        includes=includes,
        url_refs=url_refs,
    )


def extract_template_wiring(template_repo_paths: Optional[List[str]] = None) -> Dict[str, Any]:
    if template_repo_paths is None:
        template_repo_paths = [
            "clara_app/templates/clara_app/base.html",
            "clara_app/templates/clara_app/project_detail.html",
        ]

    templates: List[TemplateWiring] = []
    for rp in template_repo_paths:
        print(f"[template-wiring] extracting {rp}")
        templates.append(extract_wiring_from_template(rp))

    return {
        "created_at": _now_iso(),
        "templates": [asdict(t) for t in templates],
    }


def main() -> None:
    out = extract_template_wiring()
    out_path = SELF_UNDERSTANDING_ROOT / "graphs" / "template_wiring.json"
    _write_json(out_path, out)

    n_templates = len(out.get("templates", []))
    n_urls = sum(len(t.get("url_refs", [])) for t in out.get("templates", []))
    print(f"[template-wiring] templates={n_templates} url_refs={n_urls}")
    print(f"[template-wiring] wrote {out_path}")


if __name__ == "__main__":
    main()
