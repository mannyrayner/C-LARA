# clara_self_understanding/download_from_repo.py

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional

import requests


# --- Config ------------------------------------------------------------------

REPO_OWNER = "mannyrayner"
REPO_NAME = "C-LARA"
REPO_BRANCH = "main"

BASE_RAW_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{REPO_BRANCH}"

# All data for this subsystem lives under this directory in the repo
SELF_UNDERSTANDING_ROOT = Path(__file__).resolve().parent
DATA_ROOT = SELF_UNDERSTANDING_ROOT / "data"
INDEX_FILE = SELF_UNDERSTANDING_ROOT / "file_index.json"


# --- Errors ------------------------------------------------------------------

class RepoDownloadError(RuntimeError):
    def __init__(self, repo_path: str, url: str, msg: str):
        super().__init__(f"Failed to download {repo_path} from {url}: {msg}")
        self.repo_path = repo_path
        self.url = url
        self.msg = msg


# --- Metadata model ----------------------------------------------------------

@dataclass
class FileMetadata:
    repo_path: str          # e.g. "clara_app/export_zipfile_views.py"
    local_path: str         # absolute path to cached file
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
    return {k: FileMetadata(**v) for k, v in raw.items()}


def save_index(index: Dict[str, FileMetadata]) -> None:
    serialised = {k: asdict(v) for k, v in index.items()}
    INDEX_FILE.write_text(json.dumps(serialised, indent=2), encoding="utf-8")


# --- Core: download files from GitHub ----------------------------------------

def raw_url_for_repo_path(repo_path: str) -> str:
    if repo_path.startswith("/"):
        repo_path = repo_path[1:]
    return f"{BASE_RAW_URL}/{repo_path}"


def download_file(
    repo_path: str,
    *,
    timeout: float = 15.0,
    retries: int = 2,
) -> bytes:
    """
    Download raw file contents from GitHub.

    Raises RepoDownloadError with helpful context on failure.
    """
    url = raw_url_for_repo_path(repo_path)
    last_exc: Optional[Exception] = None

    headers = {"User-Agent": "c-lara-self-understanding/1.0"}

    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, timeout=timeout, headers=headers)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            last_exc = e

    raise RepoDownloadError(repo_path, url, str(last_exc) if last_exc else "unknown error")


def ensure_local_copy(
    repo_path: str,
    *,
    force_download: bool = False,
    allow_stale: bool = True,
    timeout: float = 15.0,
    retries: int = 2,
    verbose: bool = False,
) -> FileMetadata:
    """
    Ensure a cached local copy exists under clara_self_understanding/data.

    Default behaviour:
      - If cached file exists (and not force_download): return it without network.
      - Otherwise try to download.
      - If download fails and allow_stale is True and a cached file exists: return cached file.
      - If download fails and no cached file exists: raise RepoDownloadError.

    This makes the whole pipeline robust when offline / DNS flaky.
    """
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    index = load_index()

    # Where the cached file *should* live
    local_path = DATA_ROOT / repo_path
    local_path.parent.mkdir(parents=True, exist_ok=True)

    # Fast path: cached copy already exists and we’re not forcing a refresh
    if not force_download and local_path.exists():
        # Prefer index metadata if present; otherwise reconstruct minimal metadata.
        meta = index.get(repo_path)
        if meta and Path(meta.local_path).exists():
            return meta

        # Rebuild metadata from on-disk file (index might be missing/out-of-date)
        content = local_path.read_bytes()
        meta = FileMetadata.from_content(repo_path, local_path, content)
        index[repo_path] = meta
        save_index(index)
        return meta

    # Need download attempt
    try:
        content = download_file(repo_path, timeout=timeout, retries=retries)
        local_path.write_bytes(content)
        meta = FileMetadata.from_content(repo_path, local_path, content)
        index[repo_path] = meta
        save_index(index)
        return meta
    except RepoDownloadError as e:
        if allow_stale and local_path.exists():
            if verbose:
                print(f"[download_from_repo][WARN] {e}. Using cached copy at {local_path}")
            # Ensure index entry exists / refreshed from disk
            content = local_path.read_bytes()
            meta = FileMetadata.from_content(repo_path, local_path, content)
            index[repo_path] = meta
            save_index(index)
            return meta
        raise


def ensure_local_copies(
    repo_paths: List[str],
    *,
    force_download: bool = False,
    allow_stale: bool = True,
    timeout: float = 15.0,
    retries: int = 2,
    verbose: bool = False,
) -> Dict[str, FileMetadata]:
    """
    Convenience wrapper: ensure local copies of a list of repo-relative files.
    Returns {repo_path: FileMetadata}.
    """
    result: Dict[str, FileMetadata] = {}
    for path in repo_paths:
        result[path] = ensure_local_copy(
            path,
            force_download=force_download,
            allow_stale=allow_stale,
            timeout=timeout,
            retries=retries,
            verbose=verbose,
        )
    return result
