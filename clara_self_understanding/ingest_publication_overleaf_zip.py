from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
import hashlib
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# PDF libraries not needed here
try:
    from openai import OpenAI
except Exception as e:
    raise RuntimeError("Missing dependency: openai. Install with: pip install openai") from e


SELF_UNDERSTANDING_ROOT = Path(__file__).resolve().parent
VIEWS_INDEX_PATH = SELF_UNDERSTANDING_ROOT / "graphs" / "views_index.json"
PRICES_PATH = SELF_UNDERSTANDING_ROOT / "prices.json"
PUBLICATIONS_DIR = SELF_UNDERSTANDING_ROOT / "publications"
OVERLEAF_ZIPS_DIR = SELF_UNDERSTANDING_ROOT / "data" / "overleaf_zips"

# -----------------------------
# Pricing / cost estimation
# -----------------------------

def _load_prices() -> Dict[str, Any]:
    if not PRICES_PATH.exists():
        return {"models": {}}
    return json.loads(PRICES_PATH.read_text(encoding="utf-8"))

def estimate_cost_usd(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    tier: str = "standard",
) -> float:
    prices = _load_prices().get("models", {})
    model_info = prices.get(model)
    if not model_info:
        return 0.0

    # Pick the requested tier, else fall back sensibly
    tier_info = model_info.get(tier) or model_info.get("standard") or model_info.get("unknown")
    if not tier_info:
        return 0.0

    in_rate = tier_info.get("input") or tier_info.get("prompt") or 0.0
    out_rate = tier_info.get("output") or tier_info.get("completion") or 0.0

    return (prompt_tokens * float(in_rate) + completion_tokens * float(out_rate)) / 1_000_000.0


# -----------------------------
# OpenAI calling helpers
# -----------------------------

def is_responses_only_model(model: str) -> bool:
    m = model.lower()
    return m.startswith("gpt-5") or m.startswith("o") or m.startswith("gpt-4.1")


@dataclass
class ModelUsage:
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float


def create_openai_client() -> OpenAI:
    return OpenAI()


# -----------------------------
# Views index: candidate selection
# -----------------------------

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-]{2,}")


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in _WORD_RE.findall(text or "")]


def build_view_search_docs(views_index: Dict[str, Any]) -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []
    for v in views_index.get("entries", []):
        ui_text = " ".join(
            [(ep.get("text") or "") + " " + (ep.get("title") or "") for ep in (v.get("ui_entrypoints") or [])]
        )
        blob = " ".join(
            [
                v.get("url_name", ""),
                v.get("callable", ""),
                v.get("short_summary", ""),
                v.get("proposed_docstring", ""),
                ui_text,
            ]
        )
        docs.append(
            {
                "url_name": v.get("url_name"),
                "callable": v.get("callable"),
                "module_repo_path": v.get("module_repo_path"),
                "short_summary": v.get("short_summary", ""),
                "proposed_docstring": v.get("proposed_docstring", ""),
                "ui_entrypoints": v.get("ui_entrypoints", []),
                "_tokens": set(tokenize(blob)),
            }
        )
    return docs


def select_candidate_views(text: str, view_docs: List[Dict[str, Any]], top_k: int = 25) -> List[Dict[str, Any]]:
    q = set(tokenize(text))
    if not q:
        return view_docs[:top_k]
    scored: List[Tuple[int, Dict[str, Any]]] = []
    for d in view_docs:
        overlap = len(q & d["_tokens"])
        if overlap > 0:
            scored.append((overlap, d))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [d for _, d in scored[:top_k]]
    return top if top else view_docs[:top_k]


# -----------------------------
# LaTeX handling (Overleaf zip)
# -----------------------------

DOCCLASS_RE = re.compile(r"\\documentclass(\[.*?\])?\{.*?\}")
BEGIN_DOC_RE = re.compile(r"\\begin\{document\}")
INCLUDE_RE = re.compile(r"\\(include|input)\{([^}]+)\}")
COMMENT_RE = re.compile(r"(^|[^\\])%.*$")  # rough: strip comments not preceded by backslash

TITLE_SEP = " > "

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()




def resolve_overleaf_zip(zip_arg: str) -> Path:
    """
    Resolve a zip argument to a real path.
    - If zip_arg is an existing path, use it.
    - Otherwise, treat it as a filename under data/overleaf_zips/.
    """
    p = Path(zip_arg).expanduser()
    if p.exists():
        return p.resolve()

    candidate = (OVERLEAF_ZIPS_DIR / zip_arg).resolve()
    if candidate.exists():
        return candidate

    raise FileNotFoundError(
        f"Overleaf zip not found: {zip_arg}\n"
        f"Tried: {p.resolve()} and {candidate}"
    )


def unzip_overleaf(zip_path: Path, dest_dir: Path) -> None:
    """
    Unzip an Overleaf project zip into dest_dir.
    Assumes Overleaf zips are stored under data/overleaf_zips by convention.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)

def detect_root_tex(src_dir: Path) -> Path:
    """
    Pick the tex file that looks like the main document:
      - contains \documentclass AND \begin{document}
    If multiple, pick the largest file (often main).
    """
    candidates: List[Path] = []
    for p in src_dir.rglob("*.tex"):
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if DOCCLASS_RE.search(txt) and BEGIN_DOC_RE.search(txt):
            candidates.append(p)

    if not candidates:
        raise RuntimeError(f"No root .tex found in {src_dir} (no file contains both \\documentclass and \\begin{{document}})")

    candidates.sort(key=lambda p: p.stat().st_size, reverse=True)
    return candidates[0]


def _resolve_tex_path(src_dir: Path, include_arg: str) -> Optional[Path]:
    """
    Resolve \input{foo} / \include{foo} to an actual file path.
    Overleaf usually omits the .tex extension in include args.
    """
    arg = include_arg.strip()
    # allow paths like sections/intro
    candidates = []
    p1 = (src_dir / arg)
    candidates.append(p1)
    if not p1.suffix:
        candidates.append(src_dir / (arg + ".tex"))
    # if arg already has suffix but not .tex, still try .tex
    if p1.suffix and p1.suffix != ".tex":
        candidates.append(src_dir / (arg + ".tex"))

    for c in candidates:
        if c.exists() and c.is_file():
            return c
    return None

def _add_hierarchical_titles(sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Add a stable hierarchical display title to each section to disambiguate repeated titles
    like 'Study 1' occurring under multiple parents.

    Produces:
      - path_titles: list[str] of titles from level 1..level
      - display_title: string joined by TITLE_SEP
      - title_uniq: display_title with a numeric suffix if duplicates still occur
    """
    # stack indexed by level (1..3); keep last seen title at each level
    stack: Dict[int, str] = {}
    seen: Dict[str, int] = defaultdict(int)

    out: List[Dict[str, Any]] = []
    for sec in sections:
        level = int(sec.get("level", 0) or 0)
        title = (sec.get("title") or "").strip()

        if level <= 0:
            # "doc" / no headings case
            base_disp = title or "Document"
            key = base_disp
            seen[key] += 1
            disp = base_disp if seen[key] == 1 else f"{base_disp} ({seen[key]})"
            sec["path_titles"] = [disp]
            sec["display_title"] = disp
            sec["title_uniq"] = disp
            out.append(sec)
            continue

        # update stack at this level, drop deeper levels
        stack[level] = title
        for deeper in [l for l in list(stack.keys()) if l > level]:
            del stack[deeper]

        path_titles = [stack[l] for l in sorted(stack.keys()) if 1 <= l <= level]
        base_disp = TITLE_SEP.join(path_titles) if path_titles else title

        # still allow for duplicates within same parent/title (rare but possible)
        seen[base_disp] += 1
        disp = base_disp if seen[base_disp] == 1 else f"{base_disp} ({seen[base_disp]})"

        sec["path_titles"] = path_titles
        sec["display_title"] = base_disp
        sec["title_uniq"] = disp
        out.append(sec)

    return out

def strip_comments(tex: str) -> str:
    # line-wise strip, but keep escaped \% cases
    out_lines = []
    for line in tex.splitlines():
        m = COMMENT_RE.search(line)
        if m:
            # keep the char before % (group 1) and strip rest
            prefix = line[: m.start() + len(m.group(1))]
            out_lines.append(prefix.rstrip())
        else:
            out_lines.append(line)
    return "\n".join(out_lines)


def flatten_includes(
    src_dir: Path,
    root_tex: Path,
    max_depth: int = 25,
) -> str:
    """
    Recursively inline \input/\include.
    Keeps the outer document preamble as-is.
    """
    seen: set[Path] = set()

    def _inline_file(path: Path, depth: int) -> str:
        if depth > max_depth:
            return f"\n% [flatten] MAX DEPTH reached at {path}\n"
        if path in seen:
            return f"\n% [flatten] SKIP already included: {path}\n"
        seen.add(path)

        txt = path.read_text(encoding="utf-8", errors="ignore")
        txt = strip_comments(txt)

        def repl(m: re.Match) -> str:
            include_arg = m.group(2)
            resolved = _resolve_tex_path(src_dir, include_arg)
            if not resolved:
                return f"\n% [flatten] MISSING include/input: {include_arg}\n"
            return "\n% [flatten] BEGIN " + str(resolved.relative_to(src_dir)) + "\n" + _inline_file(resolved, depth + 1) + "\n% [flatten] END " + str(resolved.relative_to(src_dir)) + "\n"

        return INCLUDE_RE.sub(repl, txt)

    return _inline_file(root_tex, 0)


SECTION_CMD_RE = re.compile(r"\\(section|subsection|subsubsection)\*?\{([^}]*)\}")
LABEL_RE = re.compile(r"\\label\{([^}]+)\}")


def latex_to_plain_text(tex: str) -> str:
    """
    Very lightweight normalization:
      - remove most commands but keep their argument text
      - keep paragraph breaks
    We can improve later.
    """
    # Remove common formatting commands but keep content in {...}
    tex = re.sub(r"\\textbf\{([^}]*)\}", r"\1", tex)
    tex = re.sub(r"\\textit\{([^}]*)\}", r"\1", tex)
    tex = re.sub(r"\\emph\{([^}]*)\}", r"\1", tex)

    # Replace \cite{...}, \ref{...} with bracketed placeholders
    tex = re.sub(r"\\cite[t|p]?\{([^}]*)\}", r"[CITE:\1]", tex)
    tex = re.sub(r"\\ref\{([^}]*)\}", r"[REF:\1]", tex)

    # Drop remaining commands like \command or \command[...]{...} crudely
    tex = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?", "", tex)

    # Remove braces
    tex = tex.replace("{", "").replace("}", "")

    # Normalize whitespace
    tex = re.sub(r"[ \t]+", " ", tex)
    tex = re.sub(r"\n{3,}", "\n\n", tex)
    return tex.strip()


def split_into_sections(flat_tex: str) -> List[Dict[str, Any]]:
    """
    Parse a flat tex string into a list of section records.
    We treat each (sub)section heading as starting a new record.
    """
    matches = list(SECTION_CMD_RE.finditer(flat_tex))
    if not matches:
        # One big "document" section
        return [{
            "section_id": "doc",
            "level": 0,
            "title": "Document",
            "label": None,
            "tex": flat_tex,
            "plain_text": latex_to_plain_text(flat_tex),
        }]

    sections: List[Dict[str, Any]] = []
    for idx, m in enumerate(matches):
        cmd = m.group(1)  # section/subsection/...
        title = m.group(2).strip()
        level = {"section": 1, "subsection": 2, "subsubsection": 3}.get(cmd, 1)

        start = m.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(flat_tex)
        body = flat_tex[start:end]

        # find first \label within the section body (if any)
        lab_m = LABEL_RE.search(body)
        label = lab_m.group(1) if lab_m else None

        # deterministic ID
        base = (label or f"{cmd}:{title}").encode("utf-8", errors="ignore")
        section_id = hashlib.sha256(base).hexdigest()[:16]

        sections.append({
            # section_id filled after we compute hierarchical titles
            "section_id": None,
            "level": level,
            "title": title,
            "label": label,
            "tex": body,
            "plain_text": latex_to_plain_text(body),
        })

    # Add hierarchical disambiguation fields before final IDs
    sections = _add_hierarchical_titles(sections)

    # deterministic IDs: prefer label; otherwise use hierarchical unique title
    for s in sections:
        label = s.get("label")
        cmd_title = f"{s.get('title_uniq')}"
        base = (label or cmd_title).encode("utf-8", errors="ignore")
        s["section_id"] = hashlib.sha256(base).hexdigest()[:16]

    return sections


# -----------------------------
# Model linking step
# -----------------------------

def call_model_link_section(
    client: OpenAI,
    model: str,
    publication_id: str,
    section: Dict[str, Any],
    candidate_views: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], ModelUsage]:
    system_prompt = (
        "You are C-LARA's self-understanding indexer.\n"
        "Given a section of a publication and a list of candidate C-LARA Django view endpoints, "
        "you will (a) summarise the section, (b) select relevant endpoints, and (c) tag concepts.\n"
        "Return ONLY valid JSON."
    )

    candidates_str = json.dumps(
        [
            {
                "url_name": v.get("url_name"),
                "callable": v.get("callable"),
                "short_summary": (v.get("short_summary") or "")[:400],
                "ui_labels": [
                    ((ep.get("text") or "") + " / " + (ep.get("title") or ""))[:160]
                    for ep in (v.get("ui_entrypoints") or [])
                ][:2],
            }
            for v in candidate_views
        ],
        ensure_ascii=False,
        indent=2,
    )

    text = section["plain_text"]
    if len(text) > 35_000:
        text = text[:35_000] + "\n\n[TRUNCATED]"

    user_prompt = (
        f"Publication: {publication_id}\n"
        f"Section: {section.get('title_uniq') or section.get('title')} (label={section.get('label')}, level={section.get('level')})\n\n"
        "Candidate view endpoints:\n"
        f"{candidates_str}\n\n"
        "Section text:\n"
        f"{text}\n\n"
        "Return JSON with keys:\n"
        "  - section_summary: string\n"
        "  - relevant_views: list of {url_name, confidence (0..1), rationale}\n"
        "  - concept_tags: list of strings\n"
        "If none match, relevant_views should be []."
    )

    if is_responses_only_model(model):
        resp = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        text_out = getattr(resp, "output_text", "") or ""
        usage = getattr(resp, "usage", None)
        prompt_tokens = int(getattr(usage, "input_tokens", 0) or 0) if usage else 0
        completion_tokens = int(getattr(usage, "output_tokens", 0) or 0) if usage else 0
        total_tokens = prompt_tokens + completion_tokens
    else:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
        )
        text_out = (resp.choices[0].message.content or "").strip()
        usage = getattr(resp, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0
        total_tokens = int(getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or (prompt_tokens + completion_tokens)) if usage else (prompt_tokens + completion_tokens)

    try:
        analysis = json.loads(text_out or "{}")
    except json.JSONDecodeError:
        analysis = {
            "section_summary": text_out,
            "relevant_views": [],
            "concept_tags": ["parse_error"],
        }

    cost = estimate_cost_usd(model, prompt_tokens, completion_tokens)
    usage_obj = ModelUsage(
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=cost,
    )
    return analysis, usage_obj


# -----------------------------
# Main ingestion entrypoint
# -----------------------------

def _load_existing_publication_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _existing_section_ids(existing: Optional[Dict[str, Any]]) -> set[str]:
    if not existing:
        return set()
    sec_list = existing.get("sections", []) or []
    out: set[str] = set()
    for s in sec_list:
        sid = s.get("section_id")
        if isinstance(sid, str) and sid:
            out.add(sid)
    return out

def ingest_overleaf_zip(
    zip_path: Path,
    publication_id: str,
    model: str,
    candidate_top_k: int = 25,
    max_sections: Optional[int] = None,
    dry_run: bool = False,
    resume: bool = False,
) -> Path:
    if not VIEWS_INDEX_PATH.exists():
        raise FileNotFoundError(f"Missing views index: {VIEWS_INDEX_PATH}. Run: make views-index")

    views_index = json.loads(VIEWS_INDEX_PATH.read_text(encoding="utf-8"))
    view_docs = build_view_search_docs(views_index)

    pub_dir = PUBLICATIONS_DIR / publication_id
    src_dir = pub_dir / "overleaf_src"
    pub_dir.mkdir(parents=True, exist_ok=True)
    PUBLICATIONS_DIR.mkdir(parents=True, exist_ok=True)

    # Extract zip
    unzip_overleaf(zip_path, src_dir)

    # Detect root + flatten
    root_tex = detect_root_tex(src_dir)
    flat = flatten_includes(src_dir, root_tex)
    flat_path = pub_dir / "flattened.tex"
    flat_path.write_text(flat, encoding="utf-8")

    # Parse structure
    sections = split_into_sections(flat)

    if max_sections is not None:
        sections = sections[:max_sections]

    zip_bytes = zip_path.read_bytes()
    zip_sha = sha256_bytes(zip_bytes)

    # Output path + resume loading MUST happen before resume logic uses existing_obj
    out_json_path = PUBLICATIONS_DIR / f"{publication_id}.json"
    existing_obj = _load_existing_publication_json(out_json_path) if resume else None
    already_done = _existing_section_ids(existing_obj)
    if resume and existing_obj:
        print(f"[ingest-zip] RESUME: found existing output with {len(already_done)} sections already ingested")

    base_obj: Dict[str, Any] = {
        "publication_id": publication_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_zip": str(zip_path),
        "source_zip_sha256": zip_sha,
        "root_tex": str(root_tex.relative_to(src_dir)),
        "flattened_tex": str(flat_path),
        "model": model,
        "sections_count": len(sections),
        "candidate_top_k": candidate_top_k,
        "sections": [],
        "usage_totals": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
        },
    }

    if resume and existing_obj:
        out_obj = existing_obj
        # Update a few top-level fields to reflect current run
        out_obj["source_zip"] = base_obj["source_zip"]
        out_obj["source_zip_sha256"] = base_obj["source_zip_sha256"]
        out_obj["root_tex"] = base_obj["root_tex"]
        out_obj["flattened_tex"] = base_obj["flattened_tex"]
        out_obj["model"] = model
        out_obj["sections_count"] = len(sections)
        out_obj["candidate_top_k"] = candidate_top_k
        out_obj.setdefault("sections", [])
        out_obj.setdefault("usage_totals", base_obj["usage_totals"])
    else:
        out_obj = base_obj


    client = create_openai_client()

    totals = (out_obj.get("usage_totals") or {}) if resume else {}
    running_prompt = int(totals.get("prompt_tokens", 0) or 0)
    running_completion = int(totals.get("completion_tokens", 0) or 0)
    running_cost = float(totals.get("estimated_cost_usd", 0.0) or 0.0)

    print(f"[ingest-zip] publication_id={publication_id}")
    print(f"[ingest-zip] zip={zip_path}")
    print(f"[ingest-zip] root_tex={root_tex.relative_to(src_dir)}")
    print(f"[ingest-zip] sections={len(sections)} model={model} dry_run={dry_run}")

    for i, sec in enumerate(sections, start=1):
        plain = sec["plain_text"]
        candidates = select_candidate_views(plain, view_docs, top_k=candidate_top_k)

        disp = (sec.get("title_uniq") or sec.get("title") or "")[:80]
        print(f"[ingest-zip] ({i}/{len(sections)}) level={sec['level']} title={disp!r} candidates={len(candidates)}")

        if dry_run:
            analysis = {"section_summary": "", "relevant_views": [], "concept_tags": []}
            usage = ModelUsage(model=model, prompt_tokens=0, completion_tokens=0, total_tokens=0, estimated_cost_usd=0.0)
        elif resume and sec["section_id"] in already_done:
            print(f"[ingest-zip]    SKIP already ingested section_id={sec['section_id']}")
            continue
        else:
            analysis, usage = call_model_link_section(
                client=client,
                model=model,
                publication_id=publication_id,
                section=sec,
                candidate_views=candidates,
            )

        running_prompt += usage.prompt_tokens
        running_completion += usage.completion_tokens
        running_cost += usage.estimated_cost_usd

        out_obj["sections"].append({
            "section_id": sec["section_id"],
            "level": sec["level"],
            "title": sec["title"],
            "label": sec["label"],
            "plain_text_len": len(sec["plain_text"]),
            "plain_text_excerpt": sec["plain_text"][:900] + ("…" if len(sec["plain_text"]) > 900 else ""),
            "analysis": analysis,
            "usage": asdict(usage),
            # Keep paths to raw sources for future debugging (do NOT inline full tex here; too big)
            "has_tex": True,
        })

        out_obj["usage_totals"] = {
            "prompt_tokens": running_prompt,
            "completion_tokens": running_completion,
            "total_tokens": running_prompt + running_completion,
            "estimated_cost_usd": round(running_cost, 6),
        }

        # Incremental write
        out_json_path.write_text(json.dumps(out_obj, indent=2, ensure_ascii=False), encoding="utf-8")

        if not dry_run:
            print(
                f"[ingest-zip]    tokens: prompt={usage.prompt_tokens} completion={usage.completion_tokens} "
                f"total={usage.total_tokens} cost≈${usage.estimated_cost_usd:.6f} running≈${running_cost:.4f}"
            )

    print(f"[ingest-zip] DONE wrote: {out_json_path}")
    print(f"[ingest-zip] Estimated total cost≈${running_cost:.4f}")
    return out_json_path

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", required=True, help="Path to Overleaf zip")
    ap.add_argument("--publication-id", required=True, help="e.g. education_sciences_2025")
    ap.add_argument("--model", default="gpt-5.1-codex-max")
    ap.add_argument("--candidate-top-k", type=int, default=25)
    ap.add_argument("--max-sections", type=int, default=None, help="For quick sanity tests")
    ap.add_argument("--resume", action="store_true", help="Skip sections already present in publications/<pub_id>.json")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    zip_path = resolve_overleaf_zip(args.zip)
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)

    ingest_overleaf_zip(
        zip_path=zip_path,
        publication_id=args.publication_id,
        model=args.model,
        candidate_top_k=args.candidate_top_k,
        max_sections=args.max_sections,
        dry_run=args.dry_run,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()
