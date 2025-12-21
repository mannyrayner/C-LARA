# clara_self_understanding/harness.py

import hashlib
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict

import requests  # you’ll need this in your environment

# --- Config ------------------------------------------------------------------

REPO_OWNER = "mannyrayner"
REPO_NAME = "C-LARA"
REPO_BRANCH = "main"

BASE_RAW_URL = (
    f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{REPO_BRANCH}"
)

# All data for this subsystem lives under this directory in the repo
SELF_UNDERSTANDING_ROOT = Path(__file__).resolve().parent
DATA_ROOT = SELF_UNDERSTANDING_ROOT / "data"
INDEX_FILE = SELF_UNDERSTANDING_ROOT / "file_index.json"


# --- Metadata model ----------------------------------------------------------

@dataclass
class FileMetadata:
    repo_path: str          # e.g. "clara_app/export_zipfile_views.py"
    local_path: str         # path relative to repo root (for humans) or absolute
    downloaded_at: str      # ISO timestamp
    sha256: str             # content hash, useful to detect changes
    size_bytes: int         # just for convenience

    @staticmethod
    def from_content(repo_path: str, local_path: Path, content: bytes) -> "FileMetadata":
        now = datetime.now(timezone.utc).isoformat()
        sha = hashlib.sha256(content).hexdigest()
        return FileMetadata(
            repo_path=repo_path,
            local_path=str(local_path),
            downloaded_at=now,
            sha256=sha,
            size_bytes=len(content),
        )


# --- Index handling ----------------------------------------------------------

def load_index() -> Dict[str, FileMetadata]:
    if not INDEX_FILE.exists():
        return {}
    raw = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    return {
        k: FileMetadata(**v)
        for k, v in raw.items()
    }


def save_index(index: Dict[str, FileMetadata]) -> None:
    serialised = {k: asdict(v) for k, v in index.items()}
    INDEX_FILE.write_text(json.dumps(serialised, indent=2), encoding="utf-8")


# --- Core: download files from GitHub ----------------------------------------

def raw_url_for_repo_path(repo_path: str) -> str:
    # repo_path is relative, e.g. "clara_app/export_zipfile_views.py"
    if repo_path.startswith("/"):
        repo_path = repo_path[1:]
    return f"{BASE_RAW_URL}/{repo_path}"


def download_file(repo_path: str) -> bytes:
    url = raw_url_for_repo_path(repo_path)
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.content


def ensure_local_copy(repo_path: str) -> FileMetadata:
    """
    Download a single repo-relative file from GitHub raw and store it under
    clara_self_understanding/data, updating the index.

    Returns the FileMetadata describing the local copy.
    """
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    index = load_index()

    content = download_file(repo_path)
    # Mirror the repo path under data/, so structure stays recognisable
    local_path = DATA_ROOT / repo_path
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(content)

    meta = FileMetadata.from_content(repo_path, local_path, content)
    index[repo_path] = meta
    save_index(index)
    return meta


def ensure_local_copies(repo_paths: List[str]) -> Dict[str, FileMetadata]:
    """
    Convenience wrapper: download a list of repo-relative files.
    Returns a dict {repo_path: FileMetadata}.
    """
    result: Dict[str, FileMetadata] = {}
    for path in repo_paths:
        result[path] = ensure_local_copy(path)
    return result
