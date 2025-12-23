# clara_self_understanding/import_graph.py
"""
Build a module import graph for $CLARA/clara_app.

We treat each Python file in clara_app as a "module node" identified by repo-relative
path, e.g. "clara_app/export_zipfile_views.py".

We add an edge A -> B if A imports B (restricted to imports that resolve to another
file in clara_app).

Output:
  clara_self_understanding/graphs/module_import_graph.json

Schema:
{
  "created_at": "...",
  "root": "clara_app",
  "nodes": ["clara_app/a.py", ...],
  "edges": [
    {"from": "clara_app/a.py", "to": "clara_app/b.py", "import": "from clara_app.b import x"},
    ...
  ]
}
"""

from __future__ import annotations

import ast
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


@dataclass(frozen=True)
class Edge:
    from_path: str
    to_path: str
    import_stmt: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clara_root() -> Path:
    """
    Repo root: assume this file lives at <repo>/clara_self_understanding/import_graph.py
    """
    return Path(__file__).resolve().parent.parent


def _iter_py_files_under(root_dir: Path) -> List[Path]:
    out: List[Path] = []
    for p in root_dir.rglob("*.py"):
        # Skip obvious junk
        if "__pycache__" in p.parts:
            continue
        out.append(p)
    return sorted(out)


def _to_repo_path(repo_root: Path, abs_path: Path) -> str:
    return abs_path.relative_to(repo_root).as_posix()


def _module_name_for_repo_path(repo_path: str) -> str:
    # clara_app/foo/bar.py -> clara_app.foo.bar
    if not repo_path.endswith(".py"):
        raise ValueError(repo_path)
    return repo_path[:-3].replace("/", ".")


def _repo_path_for_module_name(module: str) -> Optional[str]:
    # clara_app.foo.bar -> clara_app/foo/bar.py
    if not module.startswith("clara_app."):
        return None
    return module.replace(".", "/") + ".py"


def _resolve_import_to_repo_path(
    *,
    current_repo_path: str,
    imported_module: Optional[str],
    imported_name: Optional[str],
    level: int,
) -> Optional[str]:
    """
    Resolve an import (ast.Import or ast.ImportFrom) to a clara_app repo path if possible.
    Restrict resolution to clara_app/*.

    Rules:
      - import clara_app.x.y      -> clara_app/x/y.py
      - from clara_app.x import y -> clara_app/x/y.py (best-effort)
      - from . import y           -> sibling module y.py
      - from .x import y          -> .x.py
    """
    # current module package path like clara_app/foo/bar.py -> clara_app/foo
    cur_dir = Path(current_repo_path).parent.as_posix()

    # Relative imports
    if level and level > 0:
        # compute base package directory by moving up 'level' packages
        # e.g. from .x import y in clara_app/a/b.py has level=1, base is clara_app/a
        base_dir = Path(cur_dir)
        for _ in range(level - 1):
            base_dir = base_dir.parent

        if imported_module:
            # from .x.y import z  -> base_dir/x/y.py
            rel = imported_module.replace(".", "/")
            candidate = (base_dir / rel).as_posix() + ".py"
            if candidate.startswith("clara_app/"):
                return candidate

        if imported_name:
            # from . import y -> base_dir/y.py
            candidate = (base_dir / imported_name).as_posix() + ".py"
            if candidate.startswith("clara_app/"):
                return candidate

        return None

    # Absolute imports
    if imported_module:
        # import clara_app.x.y
        rp = _repo_path_for_module_name(imported_module)
        if rp and rp.startswith("clara_app/"):
            return rp

        # from clara_app.x import y  (imported_module is clara_app.x, imported_name is y)
        if imported_module.startswith("clara_app") and imported_name:
            candidate = imported_module + "." + imported_name
            rp2 = _repo_path_for_module_name(candidate)
            if rp2 and rp2.startswith("clara_app/"):
                return rp2

    return None


def build_module_import_graph() -> Dict:
    repo_root = _clara_root()
    clara_app_dir = repo_root / "clara_app"

    py_files = _iter_py_files_under(clara_app_dir)
    nodes: Set[str] = { _to_repo_path(repo_root, p) for p in py_files }

    edges: List[Edge] = []

    for abs_path in py_files:
        repo_path = _to_repo_path(repo_root, abs_path)
        try:
            src = abs_path.read_text(encoding="utf-8")
        except Exception:
            # best-effort: skip unreadable files
            continue

        try:
            tree = ast.parse(src, filename=repo_path)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_module = alias.name
                    target = _resolve_import_to_repo_path(
                        current_repo_path=repo_path,
                        imported_module=imported_module,
                        imported_name=None,
                        level=0,
                    )
                    if target and target in nodes:
                        edges.append(Edge(repo_path, target, f"import {imported_module}"))
            elif isinstance(node, ast.ImportFrom):
                imported_module = node.module  # may be None for "from . import x"
                level = int(getattr(node, "level", 0) or 0)
                for alias in node.names:
                    imported_name = alias.name
                    target = _resolve_import_to_repo_path(
                        current_repo_path=repo_path,
                        imported_module=imported_module,
                        imported_name=imported_name,
                        level=level,
                    )
                    # Also try resolving "from clara_app.x import y" to clara_app/x.py
                    # (importing names from a module, not necessarily submodules)
                    if target is None and imported_module:
                        rp = _repo_path_for_module_name(imported_module)
                        if rp and rp.startswith("clara_app/") and rp in nodes:
                            target = rp

                    if target and target in nodes:
                        stmt = f"from {'.'*level}{imported_module or ''} import {imported_name}".strip()
                        edges.append(Edge(repo_path, target, stmt))

    graph = {
        "created_at": _now_iso(),
        "root": "clara_app",
        "nodes": sorted(nodes),
        "edges": [asdict(e) for e in edges],
    }
    return graph


def save_module_import_graph(graph: Dict) -> Path:
    out_dir = Path(__file__).resolve().parent / "graphs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "module_import_graph.json"
    out_path.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    return out_path


def main() -> None:
    g = build_module_import_graph()
    out = save_module_import_graph(g)
    print(f"[import-graph] nodes={len(g['nodes'])} edges={len(g['edges'])}")
    print(f"[import-graph] wrote {out}")


if __name__ == "__main__":
    main()
