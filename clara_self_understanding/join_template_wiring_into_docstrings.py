# clara_self_understanding/join_template_wiring_into_docstrings.py

from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .download_from_repo import ensure_local_copy

SELF_UNDERSTANDING_ROOT = Path(__file__).resolve().parent
DOCSTRING_METADATA_PATH = SELF_UNDERSTANDING_ROOT / "docstring_metadata.json"
TEMPLATE_WIRING_PATH = SELF_UNDERSTANDING_ROOT / "graphs" / "template_wiring.json"

URLS_REPO_PATH = "clara_app/urls.py"


# ---------------------------
# Utility
# ---------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _repo_path_from_module_name(modname: str) -> str:
    # clara_app.foo.bar -> clara_app/foo/bar.py
    return modname.replace(".", "/") + ".py"


def _is_probably_include_call(call: ast.Call) -> bool:
    # include("...") or include([...])
    fn = call.func
    if isinstance(fn, ast.Name) and fn.id == "include":
        return True
    if isinstance(fn, ast.Attribute) and fn.attr == "include":
        return True
    return False


def _const_str(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _get_kw(call: ast.Call, name: str) -> Optional[ast.AST]:
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _dotted_name(expr: ast.AST) -> Optional[str]:
    """
    Try to turn an expression into a dotted name, e.g.
      views.simple_clara  -> "views.simple_clara"
      simple_clara        -> "simple_clara"
      clara_app.views.foo -> "clara_app.views.foo"
    """
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        base = _dotted_name(expr.value)
        if base:
            return f"{base}.{expr.attr}"
        return expr.attr
    return None


# ---------------------------
# AST-based URL name mapping
# ---------------------------

@dataclass
class UrlTarget:
    url_name: str
    module_name: str          # python module, e.g. clara_app.simple_clara_views
    callable_name: str        # function or class name
    module_repo_path: str     # e.g. clara_app/simple_clara_views.py
    callable_qualname: str    # module_name.callable_name


def build_url_name_to_target_map_from_urls_py(urls_py_text: str) -> Dict[str, UrlTarget]:
    """
    Parse clara_app/urls.py and return url_name -> target info for patterns that
    directly map to a view callable (path/re_path(..., <callable>, name="...")).

    We skip include(...) patterns and patterns where we can't resolve the callable
    to a module in clara_app.
    """
    tree = ast.parse(urls_py_text, filename=URLS_REPO_PATH)

    # Symbol tables to resolve imported names
    # - module_aliases: local alias -> full module name (from `import X as Y`)
    # - imported_objects: local name -> (module, object) (from `from X import Y as Z`)
    module_aliases: Dict[str, str] = {}
    imported_objects: Dict[str, Tuple[str, str]] = {}

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                full = alias.name
                local = alias.asname or full.split(".")[-1]
                module_aliases[local] = full
        elif isinstance(node, ast.ImportFrom):
            # Handle relative imports inside clara_app/urls.py
            #
            # Examples:
            #   from . import home_views            -> module=None, level=1, name=home_views
            #   from .foo import bar as baz         -> module="foo", level=1, name=bar, asname=baz
            #
            # We treat these as coming from the "clara_app" package, since urls.py lives there.
            pkg_prefix = "clara_app"

            if node.level and node.level > 0:
                # Relative import
                if node.module:
                    base_mod = f"{pkg_prefix}.{node.module}"
                else:
                    base_mod = pkg_prefix
            else:
                # Absolute import
                if not node.module:
                    continue
                base_mod = node.module

            for alias in node.names:
                obj = alias.name
                local = alias.asname or obj

                # Special case: "from . import home_views" imports a MODULE, not an object.
                # We want `home_views` usable as a module alias.
                if node.module is None and node.level and node.level > 0:
                    # home_views -> clara_app.home_views
                    module_aliases[local] = f"{pkg_prefix}.{obj}"
                else:
                    # from base_mod import obj as local
                    imported_objects[local] = (base_mod, obj)

    def resolve_callable(expr: ast.AST) -> Optional[Tuple[str, str]]:
        """
        Resolve a callable expression to (module_name, callable_name).
        """
        dn = _dotted_name(expr)
        if not dn:
            return None

        # If expression is a simple name, it might have come from "from X import Y"
        if "." not in dn:
            if dn in imported_objects:
                mod, obj = imported_objects[dn]
                return mod, obj
            # Or it could be a local symbol we can't resolve.
            return None

        # Otherwise, it's dotted: base.attr[.attr...]
        parts = dn.split(".")
        base = parts[0]
        rest = parts[1:]

        # base might be a module alias imported via `import ... as base`
        if base in module_aliases:
            full_base_mod = module_aliases[base]
            # callable could be last segment; module is base + rest[:-1]
            if len(rest) >= 1:
                callable_name = rest[-1]
                module_name = ".".join([full_base_mod] + rest[:-1]) if len(rest) > 1 else full_base_mod
                return module_name, callable_name

        # base might have come from "from X import base" where base itself is a module or object
        if base in imported_objects:
            mod, obj = imported_objects[base]
            # dn = base.rest... means mod.obj.rest...
            if len(rest) >= 1:
                callable_name = rest[-1]
                module_name = ".".join([mod, obj] + rest[:-1]) if len(rest) > 1 else ".".join([mod, obj])
                return module_name, callable_name

        # If it's already fully qualified, accept it (best-effort)
        # e.g. clara_app.export_zipfile_views.bulk_export...
        if dn.startswith("clara_app."):
            callable_name = parts[-1]
            module_name = ".".join(parts[:-1])
            return module_name, callable_name

        return None

    out: Dict[str, UrlTarget] = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        # path(...) or re_path(...)
        fn = node.func
        fn_name = None
        if isinstance(fn, ast.Name):
            fn_name = fn.id
        elif isinstance(fn, ast.Attribute):
            fn_name = fn.attr

        if fn_name not in {"path", "re_path"}:
            continue

        # skip include(...)
        if len(node.args) >= 2 and isinstance(node.args[1], ast.Call) and _is_probably_include_call(node.args[1]):
            continue

        name_node = _get_kw(node, "name")
        url_name = _const_str(name_node) if name_node else None

        # Also support positional `name`:
        # path(route, view, kwargs, name)  -> name is args[3]
        # path(route, view, name) (rare/legacy) -> name is args[2] if it's a string constant
        if not url_name:
            # common case: 4th positional
            if len(node.args) >= 4:
                url_name = _const_str(node.args[3])
            # fallback: if 3rd positional is a string and 4th doesn't exist
            if not url_name and len(node.args) >= 3:
                url_name = _const_str(node.args[2])
        
        if not url_name:
            continue

        # view callable is typically arg[1]
        if len(node.args) < 2:
            continue
        view_expr = node.args[1]

        resolved = resolve_callable(view_expr)
        if not resolved:
            continue
        module_name, callable_name = resolved

        # Restrict to clara_app modules (you can loosen later)
        if not module_name.startswith("clara_app."):
            continue

        module_repo_path = _repo_path_from_module_name(module_name)

        out[url_name] = UrlTarget(
            url_name=url_name,
            module_name=module_name,
            callable_name=callable_name,
            module_repo_path=module_repo_path,
            callable_qualname=f"{module_name}.{callable_name}",
        )

    return out


# ---------------------------
# Join wiring -> docstrings
# ---------------------------

def join_template_wiring_into_docstrings(
    template_wiring_path: Path = TEMPLATE_WIRING_PATH,
    docstring_metadata_path: Path = DOCSTRING_METADATA_PATH,
    urls_repo_path: str = URLS_REPO_PATH,
) -> None:
    # Load docstring metadata
    if not docstring_metadata_path.exists():
        raise FileNotFoundError(docstring_metadata_path)
    doc_meta: Dict[str, List[Dict[str, Any]]] = _load_json(docstring_metadata_path)

    # Load template wiring
    if not template_wiring_path.exists():
        raise FileNotFoundError(template_wiring_path)
    wiring = _load_json(template_wiring_path)

    # Load urls.py text (via ensure_local_copy to match your workflow)
    urls_local = Path(ensure_local_copy(urls_repo_path).local_path)
    urls_text = urls_local.read_text(encoding="utf-8")

    url_map = build_url_name_to_target_map_from_urls_py(urls_text)

    print(f"[join-ui] url_map entries: {len(url_map)}")
    if url_map:
        sample = list(sorted(url_map.keys()))[:15]
        print(f"[join-ui] url_map sample keys: {sample}")
    else:
        print("[join-ui] url_map is EMPTY (likely name= is positional or urls.py structure is unusual)")

    # For each template url ref, attach to module’s latest record
    attached = 0
    skipped_no_urlmap = 0
    skipped_no_docmeta = 0
    missing_examples = []

    # quick sanity: what URL names appear in template wiring?
    wiring_names = []
    for tmpl in wiring.get("templates", []):
        for ref in tmpl.get("url_refs", []):
            if ref.get("url_name"):
                wiring_names.append(ref["url_name"])
    wiring_names = sorted(set(wiring_names))
    print(f"[join-ui] template_wiring unique url_names: {len(wiring_names)}")
    print(f"[join-ui] template_wiring sample url_names: {wiring_names[:15]}")

    for tmpl in wiring.get("templates", []):
        template_repo_path = tmpl.get("template_repo_path")
        for ref in tmpl.get("url_refs", []):
            url_name = ref.get("url_name")
            if not url_name or url_name not in url_map:
                skipped_no_urlmap += 1
                if url_name and len(missing_examples) < 10:
                    missing_examples.append(url_name)
                continue

            target = url_map[url_name]
            repo_path = target.module_repo_path

            if repo_path not in doc_meta or not doc_meta[repo_path]:
                skipped_no_docmeta += 1
                continue

            # Attach to most recent record
            record = doc_meta[repo_path][-1]
            ui_list = record.setdefault("ui_entrypoints", [])

            entry = {
                "attached_at": _now_iso(),
                "url_name": url_name,
                "args_raw": ref.get("args_raw", []),
                "href_expr": ref.get("href_expr"),
                "element": ref.get("element"),
                "attr": ref.get("attr"),
                "title": ref.get("title"),
                "text": ref.get("text"),
                "template_repo_path": template_repo_path,
                "callable": target.callable_qualname,
            }

            # Deduplicate by a stable signature
            sig = (
                entry["url_name"],
                tuple(entry.get("args_raw") or []),
                entry.get("template_repo_path"),
                entry.get("element"),
                entry.get("attr"),
                entry.get("text"),
                entry.get("title"),
            )
            existing_sigs = {
                (
                    e.get("url_name"),
                    tuple(e.get("args_raw") or []),
                    e.get("template_repo_path"),
                    e.get("element"),
                    e.get("attr"),
                    e.get("text"),
                    e.get("title"),
                )
                for e in ui_list
            }
            if sig not in existing_sigs:
                ui_list.append(entry)
                attached += 1

    _save_json(docstring_metadata_path, doc_meta)

    print(f"[join-ui] wrote: {docstring_metadata_path}")
    print(f"[join-ui] attached ui_entrypoints: {attached}")
    print(f"[join-ui] skipped (no url_map match): {skipped_no_urlmap}")
    print(f"[join-ui] skipped (no docstring metadata for module): {skipped_no_docmeta}")
    if missing_examples:
        print(f"[join-ui] examples missing from url_map: {missing_examples}")

def main() -> None:
    join_template_wiring_into_docstrings()


if __name__ == "__main__":
    main()
