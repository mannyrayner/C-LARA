"""
Join publication ingestion output into docstring_metadata.json.

Reads:
  - clara_self_understanding/publications/*.json
  - clara_self_understanding/graphs/views_index.json
  - clara_self_understanding/docstring_metadata.json

Writes:
  - clara_self_understanding/docstring_metadata.json (in-place update)

Strategy:
  - For each ingested publication section, take section.analysis.relevant_views[*].url_name
  - Use views_index.json to map url_name -> module_repo_path (and callable)
  - Attach a "publication_mentions" list into the latest docstring record's "analysis"
    for the relevant module.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SELF_UNDERSTANDING_ROOT = Path(__file__).resolve().parent
DOCSTRING_PATH = SELF_UNDERSTANDING_ROOT / "docstring_metadata.json"
PUBLICATIONS_DIR = SELF_UNDERSTANDING_ROOT / "publications"
VIEWS_INDEX_PATH = SELF_UNDERSTANDING_ROOT / "graphs" / "views_index.json"


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _iter_publication_files(glob_pat: str = "*.json") -> Iterable[Path]:
    if not PUBLICATIONS_DIR.exists():
        return []
    return sorted(PUBLICATIONS_DIR.glob(glob_pat))


@dataclass(frozen=True)
class MentionKey:
    publication_id: str
    section_id: str
    url_name: str


def _existing_mention_keys(existing_mentions: List[Dict[str, Any]]) -> set[MentionKey]:
    keys: set[MentionKey] = set()
    for m in existing_mentions or []:
        pub_id = str(m.get("publication_id", "")).strip()
        sec_id = str(m.get("section_id", "")).strip()
        url_name = str(m.get("url_name", "")).strip()
        if pub_id and sec_id and url_name:
            keys.add(MentionKey(pub_id, sec_id, url_name))
    return keys


def join_publications_into_docstrings(
    publications_glob: str = "*.json",
    dry_run: bool = False,
) -> None:
    # Load indices
    views_index = _load_json(VIEWS_INDEX_PATH, default={})
    url_name_to_entry: Dict[str, Dict[str, Any]] = {}
    for entry in views_index.get("entries", []):
        url = entry.get("url_name")
        if url:
            url_name_to_entry[url] = entry

    docstrings: Dict[str, List[Dict[str, Any]]] = _load_json(DOCSTRING_PATH, default={})

    print(f"[join-pubs] views_index url_names: {len(url_name_to_entry)}")
    print(f"[join-pubs] docstring modules: {len(docstrings)}")
    print(f"[join-pubs] publications glob: {publications_glob}")

    pub_files = list(_iter_publication_files(publications_glob))
    print(f"[join-pubs] publication files: {len(pub_files)}")

    attached = 0
    skipped_no_url = 0
    skipped_no_view = 0
    skipped_no_module = 0
    skipped_no_docstrings = 0
    deduped = 0

    for pub_path in pub_files:
        pub = _load_json(pub_path, default={})
        pub_id = pub.get("publication_id") or pub.get("publication") or pub_path.stem
        pub_id = str(pub_id)

        sections = pub.get("sections", [])
        for sec in sections:
            sec_id = str(sec.get("id") or sec.get("section_id") or "")
            if not sec_id:
                # best-effort stable id if missing
                sec_id = f"{sec.get('level','?')}-{sec.get('number','?')}-{sec.get('title','')}".strip()

            title = sec.get("title") or ""
            level = sec.get("level")
            number = sec.get("number")
            analysis = sec.get("analysis") or {}
            section_summary = (
                analysis.get("section_summary")
                or analysis.get("summary")
                or analysis.get("short_summary")
                or ""
            )
            # This is where ingest script stores links
            relevant_views = analysis.get("relevant_views") or []
            if not isinstance(relevant_views, list):
                continue

            for rv in relevant_views:
                if not isinstance(rv, dict):
                    continue
                url_name = rv.get("url_name") or rv.get("name") or rv.get("url") or ""
                url_name = str(url_name).strip()
                if not url_name:
                    skipped_no_url += 1
                    continue

                view_entry = url_name_to_entry.get(url_name)
                if not view_entry:
                    skipped_no_view += 1
                    continue

                module_repo_path = view_entry.get("module_repo_path")
                callable_ = view_entry.get("callable")
                if not module_repo_path:
                    skipped_no_module += 1
                    continue

                module_records = docstrings.get(module_repo_path)
                if not module_records:
                    skipped_no_docstrings += 1
                    continue

                latest = module_records[-1]
                latest.setdefault("analysis", {})
                if latest["analysis"] is None:
                    latest["analysis"] = {}

                mentions: List[Dict[str, Any]] = latest["analysis"].setdefault(
                    "publication_mentions", []
                )
                existing_keys = _existing_mention_keys(mentions)
                key = MentionKey(pub_id, sec_id, url_name)
                if key in existing_keys:
                    deduped += 1
                    continue

                mention = {
                    "attached_at": datetime.now(timezone.utc).isoformat(),
                    "publication_id": pub_id,
                    "publication_file": str(pub_path.name),
                    "section_id": sec_id,
                    "section_title": title,
                    "section_level": level,
                    "section_number": number,
                    "section_summary": section_summary,
                    "url_name": url_name,
                    "callable": callable_,
                    # Keep any ingest-provided per-view rationale if present:
                    "view_rationale": rv.get("rationale") or rv.get("why") or "",
                    "confidence": rv.get("confidence"),
                }
                mentions.append(mention)
                attached += 1

    print(f"[join-pubs] attached publication_mentions: {attached}")
    print(f"[join-pubs] deduped existing mentions: {deduped}")
    print(f"[join-pubs] skipped (missing url_name): {skipped_no_url}")
    print(f"[join-pubs] skipped (url_name not in views_index): {skipped_no_view}")
    print(f"[join-pubs] skipped (missing module_repo_path): {skipped_no_module}")
    print(f"[join-pubs] skipped (no docstring records for module): {skipped_no_docstrings}")

    if not dry_run:
        _save_json(DOCSTRING_PATH, docstrings)
        print(f"[join-pubs] wrote: {DOCSTRING_PATH}")
    else:
        print("[join-pubs] dry-run: not writing docstring_metadata.json")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--publications-glob",
        default="*.json",
        help="Glob under clara_self_understanding/publications (default: *.json)",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    join_publications_into_docstrings(
        publications_glob=args.publications_glob,
        dry_run=bool(args.dry_run),
    )


if __name__ == "__main__":
    main()
