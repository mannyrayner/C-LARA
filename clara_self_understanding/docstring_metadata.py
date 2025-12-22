# clara_self_understanding/docstring_metadata.py

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set

from .download_from_repo import ensure_local_copy  # your renamed harness
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

    for repo_path, local_path in repo_to_local.items():
        source_code = local_path.read_text(encoding="utf-8")

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
