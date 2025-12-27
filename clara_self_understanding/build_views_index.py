# clara_self_understanding/build_views_index.py

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .download_from_repo import ensure_local_copy
from .join_template_wiring_into_docstrings import (
    build_url_name_to_target_map_from_urls_py,
    URLS_REPO_PATH,
    DOCSTRING_METADATA_PATH,
)

SELF_UNDERSTANDING_ROOT = Path(__file__).resolve().parent
OUT_PATH = SELF_UNDERSTANDING_ROOT / "graphs" / "views_index.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _latest_analysis_for_module(doc_meta: Dict[str, List[Dict[str, Any]]], module_repo_path: str) -> Dict[str, Any]:
    """
    Return the latest analysis payload for a given module repo path, if available.
    """
    records = doc_meta.get(module_repo_path) or []
    if not records:
        return {}
    rec = records[-1]
    analysis = rec.get("analysis") or {}
    # also keep ui_entrypoints if present
    ui = rec.get("ui_entrypoints") or []
    return {"analysis": analysis, "ui_entrypoints": ui, "usage": rec.get("usage"), "model": rec.get("model")}


def build_views_index(
    docstring_metadata_path: Path = DOCSTRING_METADATA_PATH,
    urls_repo_path: str = URLS_REPO_PATH,
    out_path: Path = OUT_PATH,
) -> None:
    if not docstring_metadata_path.exists():
        raise FileNotFoundError(docstring_metadata_path)
    doc_meta: Dict[str, List[Dict[str, Any]]] = _load_json(docstring_metadata_path)

    urls_local = Path(ensure_local_copy(urls_repo_path).local_path)
    urls_text = urls_local.read_text(encoding="utf-8")
    url_map = build_url_name_to_target_map_from_urls_py(urls_text)

    entries: List[Dict[str, Any]] = []

    for url_name, target in sorted(url_map.items(), key=lambda kv: kv[0]):
        module_repo_path = target.module_repo_path
        latest = _latest_analysis_for_module(doc_meta, module_repo_path)
        analysis = latest.get("analysis", {})

        entry = {
            "url_name": url_name,
            "callable": target.callable_qualname,
            "module_repo_path": module_repo_path,
            "short_summary": analysis.get("short_summary", ""),
            "proposed_docstring": analysis.get("proposed_docstring", ""),
            "key_responsibilities": analysis.get("key_responsibilities", []),
            "potential_issues": analysis.get("potential_issues", []),
            "ui_entrypoints": latest.get("ui_entrypoints", []),
            "last_model": latest.get("model"),
            "last_usage": latest.get("usage"),
        }
        entries.append(entry)

    out_obj = {
        "created_at": _now_iso(),
        "root": "clara_app",
        "count": len(entries),
        "entries": entries,
    }
    _save_json(out_path, out_obj)

    print(f"[views-index] urls mapped: {len(entries)}")
    print(f"[views-index] wrote: {out_path}")


def main() -> None:
    build_views_index()


if __name__ == "__main__":
    main()
