# clara_self_understanding/docstring_metadata.py

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set

from .download_from_repo import ensure_local_copy, ensure_local_copies 
from .openai_utils import create_openai_client, call_model_for_docstring, ModelUsage


# All files for this subsystem live under clara_self_understanding/
SELF_UNDERSTANDING_ROOT = Path(__file__).resolve().parent
DATA_ROOT = SELF_UNDERSTANDING_ROOT / "data"
DOCSTRING_METADATA_FILE = SELF_UNDERSTANDING_ROOT / "docstring_metadata.json"


def _load_docstring_metadata() -> Dict[str, List[Dict]]:
    """
    Load existing docstring metadata from disk.

    Structure:
        {
          "clara_app/export_zipfile_views.py": [
            {
              "created_at": "...",
              "model": "...",
              "usage": {...},
              "analysis": {...}
            },
            ...
          ],
          ...
        }
    """
    if not DOCSTRING_METADATA_FILE.exists():
        return {}
    return json.loads(DOCSTRING_METADATA_FILE.read_text(encoding="utf-8"))


def _save_docstring_metadata(metadata: Dict[str, List[Dict]]) -> None:
    DOCSTRING_METADATA_FILE.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )


def discover_view_modules_from_urls(
    urls_repo_path: str = "clara_app/urls.py",
) -> Set[str]:
    """
    Download urls.py, inspect imports and path() calls, and return a set of
    module names that look like view modules (names ending in '_views').

    Example return value:
        {'export_zipfile_views', 'simple_clara_views', 'annotation_views', ...}
    """
    meta = ensure_local_copy(urls_repo_path)
    urls_path = Path(meta.local_path)
    text = urls_path.read_text(encoding="utf-8")

    view_modules: Set[str] = set()

    for line in text.splitlines():
        line = line.strip()
        # Look for lines like: from . import views, upload_views, simple_clara_views
        if line.startswith("from . import"):
            rest = line[len("from . import") :].strip()
            names = [name.strip() for name in rest.split(",")]
            for name in names:
                if name.endswith("_views"):
                    view_modules.add(name)

        # You could optionally also parse direct references in path() calls,
        # but the import line is usually enough and less fragile.

    return view_modules


def repo_path_for_view_module(module_name: str) -> str:
    """
    Convert a view module name to its repo path.

    E.g. 'export_zipfile_views' -> 'clara_app/export_zipfile_views.py'
    """
    return f"clara_app/{module_name}.py"


def ensure_view_modules_downloaded(module_names: List[str]) -> Dict[str, Path]:
    """
    Ensure local copies of the given view modules exist under data/.

    Returns a dict mapping repo_path -> local Path.
    """
    repo_to_local: Dict[str, Path] = {}
    for module_name in module_names:
        repo_path = repo_path_for_view_module(module_name)
        meta = ensure_local_copy(repo_path)
        repo_to_local[repo_path] = Path(meta.local_path)
    return repo_to_local

def _kb(n: int) -> str:
    return f"{n/1024:.1f} KB"

def generate_docstrings_for_views(
    module_names: List[str],
    model: str = "gpt-5.2",
) -> Dict[str, List[Dict]]:
    """
    For each view module in module_names, download the file (if needed),
    send it to the specified OpenAI model to generate docstring-style
    metadata, and append the results to docstring_metadata.json.

    Returns the updated metadata dict.
    """
    client = create_openai_client()
    existing_metadata = _load_docstring_metadata()

    # Ensure files are downloaded
    repo_to_local = ensure_view_modules_downloaded(module_names)

    total = len(repo_to_local)
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_cost = 0.0

    print(f"[docstrings] Model: {model}")
    print(f"[docstrings] Modules: {total}")

    for i, (repo_path, local_path) in enumerate(repo_to_local.items(), start=1):
        try:
            p = Path(local_path)
            size_bytes = p.stat().st_size if p.exists() else 0
            print(f"[docstrings] ({i}/{total}) {repo_path}  ({_kb(size_bytes)})")

            source_code = p.read_text(encoding="utf-8")

            analysis, usage = call_model_for_docstring(
                client=client,
                model=model,
                repo_path=repo_path,
                source_code=source_code,
            )

            record = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "model": usage.model,
                "usage": asdict(usage),
                "analysis": analysis,
            }

            per_file_list = existing_metadata.get(repo_path, [])
            per_file_list.append(record)
            existing_metadata[repo_path] = per_file_list

            # Save incrementally so you don’t lose everything if something dies later
            _save_docstring_metadata(existing_metadata)

            total_prompt_tokens += usage.prompt_tokens
            total_completion_tokens += usage.completion_tokens
            total_cost += float(usage.estimated_cost_usd)

            print(
                f"[docstrings]    tokens: prompt={usage.prompt_tokens}, "
                f"completion={usage.completion_tokens}, total={usage.total_tokens}  "
                f"cost≈${usage.estimated_cost_usd:.6f}"
            )
            print(
                f"[docstrings]    running: prompt={total_prompt_tokens}, "
                f"completion={total_completion_tokens}, cost≈${total_cost:.4f}"
            )

        except Exception as e:
            # Record the failure (but keep going)
            print(f"[docstrings][ERROR] {repo_path}: {type(e).__name__}: {e}")

            record = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "model": model,
                "usage": {
                    "model": model,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "estimated_cost_usd": 0.0,
                },
                "analysis": {
                    "proposed_docstring": "",
                    "short_summary": "",
                    "key_responsibilities": [],
                    "potential_issues": [f"Exception during docstring generation: {type(e).__name__}: {e}"],
                },
            }

            per_file_list = existing_metadata.get(repo_path, [])
            per_file_list.append(record)
            existing_metadata[repo_path] = per_file_list
            _save_docstring_metadata(existing_metadata)

    print(f"[docstrings] DONE. Estimated total cost≈${total_cost:.4f}")
    return existing_metadata


def generate_docstrings_for_one_view_module(
    module_name: str,
    model: str = "gpt-5.1-codex-max",
) -> Dict[str, List[Dict]]:
    """
    Convenience: generate docstring-style metadata for exactly one *_views module.
    Example module_name: 'simple_clara_views'
    """
    return generate_docstrings_for_views([module_name], model=model)

def generate_docstrings_for_all_discovered_views(
    model: str = "gpt-5.2",
) -> Dict[str, List[Dict]]:
    """
    Convenience function:

    1. Discover all *_views modules from clara_app/urls.py
    2. Generate docstring-style metadata for each of them.

    Useful as a first sweep over the C-LARA view layer.
    """
    module_names = sorted(discover_view_modules_from_urls())
    return generate_docstrings_for_views(module_names, model=model)

def ensure_repo_paths_downloaded(repo_paths: List[str]) -> Dict[str, Path]:
    """
    Ensure local copies of arbitrary repo paths exist under data/.

    Returns a dict mapping repo_path -> local Path.
    """
    repo_to_local: Dict[str, Path] = {}
    # Use bulk download helper for efficiency / clarity
    metas = ensure_local_copies(repo_paths)
    for repo_path, meta in metas.items():
        repo_to_local[repo_path] = Path(meta.local_path)
    return repo_to_local


def generate_docstrings_for_repo_paths(
    repo_paths: List[str],
    model: str = "gpt-5.2",
) -> Dict[str, List[Dict]]:
    """
    Generate docstring metadata for arbitrary repo paths (not just *_views modules).
    Writes into docstring_metadata.json (same schema as existing).
    """
    client = create_openai_client()
    existing_metadata = _load_docstring_metadata()

    repo_to_local = ensure_repo_paths_downloaded(repo_paths)

    total = len(repo_to_local)
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_cost = 0.0

    print(f"[docstrings] Model: {model}")
    print(f"[docstrings] Modules: {total}")

    for i, (repo_path, local_path) in enumerate(repo_to_local.items(), start=1):
        try:
            p = Path(local_path)
            size_bytes = p.stat().st_size if p.exists() else 0
            print(f"[docstrings] ({i}/{total}) {repo_path}  ({_kb(size_bytes)})")

            source_code = p.read_text(encoding="utf-8")

            analysis, usage = call_model_for_docstring(
                client=client,
                model=model,
                repo_path=repo_path,
                source_code=source_code,
            )

            record = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "model": usage.model,
                "usage": asdict(usage),
                "analysis": analysis,
            }

            per_file_list = existing_metadata.get(repo_path, [])
            per_file_list.append(record)
            existing_metadata[repo_path] = per_file_list

            _save_docstring_metadata(existing_metadata)

            total_prompt_tokens += usage.prompt_tokens
            total_completion_tokens += usage.completion_tokens
            total_cost += float(usage.estimated_cost_usd)

            print(
                f"[docstrings]    tokens: prompt={usage.prompt_tokens}, "
                f"completion={usage.completion_tokens}, total={usage.total_tokens}  "
                f"cost≈${usage.estimated_cost_usd:.6f}"
            )
            print(
                f"[docstrings]    running: prompt={total_prompt_tokens}, "
                f"completion={total_completion_tokens}, cost≈${total_cost:.4f}"
            )

        except Exception as e:
            print(f"[docstrings][ERROR] {repo_path}: {type(e).__name__}: {e}")

            record = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "model": model,
                "usage": {
                    "model": model,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "estimated_cost_usd": 0.0,
                },
                "analysis": {
                    "proposed_docstring": "",
                    "short_summary": "",
                    "key_responsibilities": [],
                    "potential_issues": [
                        f"Exception during docstring generation: {type(e).__name__}: {e}"
                    ],
                },
            }

            per_file_list = existing_metadata.get(repo_path, [])
            per_file_list.append(record)
            existing_metadata[repo_path] = per_file_list
            _save_docstring_metadata(existing_metadata)

    print(f"[docstrings] DONE. Estimated total cost≈${total_cost:.4f}")
    return existing_metadata


def generate_docstrings_for_clara_app_from_import_graph(
    model: str = "gpt-5.2",
) -> Dict[str, List[Dict]]:
    """
    Use graphs/module_import_graph.json to generate docstrings for all clara_app modules
    *reachable from the view modules referenced by clara_app/urls.py*.
    """
    graphs_dir = SELF_UNDERSTANDING_ROOT / "graphs"
    graph_path = graphs_dir / "module_import_graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))

    nodes = set(graph.get("nodes", []))
    edges = graph.get("edges", [])

    # Build adjacency: from_path -> {to_path, ...}
    adj: Dict[str, Set[str]] = {}
    for e in edges:
        frm = e.get("from_path")
        to = e.get("to_path")
        if not frm or not to:
            continue
        adj.setdefault(frm, set()).add(to)

    # Seed = view modules discovered from urls.py
    view_modules = discover_view_modules_from_urls()
    seeds = [repo_path_for_view_module(m) for m in view_modules]

    # Keep only seeds that are actually in the graph
    frontier = [p for p in seeds if p in nodes]
    reachable: Set[str] = set(frontier)

    # BFS/DFS over directed edges (imports)
    while frontier:
        cur = frontier.pop()
        for nxt in adj.get(cur, set()):
            if nxt in nodes and nxt not in reachable:
                reachable.add(nxt)
                frontier.append(nxt)

    # Optional hygiene filter: stay in clara_app and skip migrations/tests/not_used
    def ok(p: str) -> bool:
        return (
            p.startswith("clara_app/")
            and "/migrations/" not in p
            and "/not_used/" not in p
            and not p.endswith("/tests.py")
            and "/test_" not in p
        )

    target_paths = sorted(p for p in reachable if ok(p))

    print(f"[docstrings] seeds={len(seeds)} reachable={len(reachable)} kept={len(target_paths)}")
    return generate_docstrings_for_repo_paths(target_paths, model=model)
