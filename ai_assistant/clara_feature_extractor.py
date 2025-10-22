#!/usr/bin/env python3
# tools/clara_feature_extractor.py
import argparse, ast, os, re, sys, yaml
import shutil, subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from ai_assistant.ai_assistant_utils import _maybe_cygpath

URL_TAG_RE = re.compile(r"""\{%\s*url\s+'([^']+)'\s*([^%}]*)%\}""")
A_TAG_RE   = re.compile(r"""<a[^>]*href=['"]\s*\{%\s*url\s+'([^']+)'[^%}]*%\}\s*['"][^>]*>(.*?)</a>""", re.I|re.S)
CAPITALIZED = re.compile(r"\b([A-Z][A-Za-z0-9_]*)\s*\.objects\b")

def load_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def parse_urls_py(urls_text: str) -> Tuple[Dict[str, Tuple[str,str]], Dict[str,str]]:
    """
    Returns:
      routes: {route_name: (module.function, path_pattern|'' if unknown)}
      modules: {alias: module_import_path}
    """
    modules = {}
    # from . import manipulate_project_views, content_views as cv
    for m in re.finditer(r"from\s+\.?\s*([a-zA-Z0-9_\.]*)\s+import\s+([a-zA-Z0-9_\s,]+(?:\s+as\s+[a-zA-Z0-9_]+)?)", urls_text):
        imported = m.group(2)
        for item in re.split(r"\s*,\s*", imported.strip()):
            if not item: continue
            parts = item.split()
            if len(parts) == 1:
                alias = parts[0]
            elif len(parts) == 3 and parts[1] == "as":
                alias = parts[2]
            else:
                continue
            # assume relative import => clara_app.<alias>
            modules[alias] = f"clara_app.{alias}"

    # path('route/', module.view, name='route_name')
    routes = {}
    # naive capture; good enough for v0
    for m in re.finditer(r"path\(\s*([^\)]*?)\)", urls_text, re.S):
        call = m.group(1)
        # name='X'
        name_m = re.search(r"name\s*=\s*'([^']+)'", call)
        name = name_m.group(1) if name_m else None
        # view like foo.bar or foo.bar.baz
        view_m = re.search(r",\s*([a-zA-Z_][\w\.]+)\s*(?:,|\))", call)
        view = view_m.group(1) if view_m else None
        # path string
        path_m = re.search(r"^[r]?'([^']+)'", call.strip())
        route_path = path_m.group(1) if path_m else ""
        if name and view:
            routes[name] = (view, route_path)
    # qualify views with clara_app if they’re module-relative
    qualified = {}
    for name,(view,route_path) in routes.items():
        if "." in view:
            head = view.split(".")[0]
            if head in modules:
                qualified[name] = (view if view.startswith("clara_app.") else view.replace(head, modules[head], 1), route_path)
            else:
                qualified[name] = (view, route_path)
        else:
            qualified[name] = (view, route_path)
    return qualified, modules

def extract_menu_labels(template_text: str) -> Dict[str,str]:
    """Return {route_name: label} using <a href="{% url 'name' %}">Label</a> if available, else blank label."""
    mapping = {}
    for m in A_TAG_RE.finditer(template_text):
        route, label = m.group(1), re.sub(r"\s+"," ",m.group(2)).strip()
        mapping[route] = label
    # fallback: find bare {% url 'name' %} without label
    for m in URL_TAG_RE.finditer(template_text):
        route = m.group(1)
        mapping.setdefault(route, "")
    return mapping

class ViewAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.templates = set()
        self.helpers = set()
        self.models = set()
    def visit_Call(self, node: ast.Call):
        # render(request, "template.html", ...)
        try:
            if isinstance(node.func, ast.Name) and node.func.id == "render":
                if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str):
                    self.templates.add(node.args[1].value)
        except Exception: pass
        # dotted helper calls like clara_app.images.foo()
        try:
            if isinstance(node.func, ast.Attribute):
                dotted = []
                cur = node.func
                while isinstance(cur, ast.Attribute):
                    dotted.append(cur.attr)
                    cur = cur.value
                if isinstance(cur, ast.Name):
                    dotted.append(cur.id)
                dotted_full = ".".join(reversed(dotted))
                if dotted_full.startswith("clara_app."):
                    self.helpers.add(dotted_full)
        except Exception: pass
        self.generic_visit(node)
    def visit_Attribute(self, node: ast.Attribute):
        # capture Model.objects usage: Foo.objects
        try:
            if isinstance(node.value, ast.Name) and node.attr == "objects" and node.value.id[:1].isupper():
                self.models.add(node.value.id)
        except Exception: pass
        self.generic_visit(node)

def analyze_view_function(py_text: str, func_name: str) -> Tuple[List[str], List[str], List[str]]:
    """
    Returns (templates, helpers, models)
    """
    try:
        tree = ast.parse(py_text)
    except Exception:
        return [],[],[]
    target = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            target = node
            break
    if not target:
        return [],[],[]
    va = ViewAnalyzer()
    va.visit(target)
    return sorted(va.templates), sorted(va.helpers), sorted(va.models)

def write_yaml_card(out_dir: Path, card: dict):
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{card['id']}.yaml"
    with (out_dir / fname).open("w", encoding="utf-8") as f:
        yaml.safe_dump(card, f, sort_keys=False, allow_unicode=True)

def main():
    ap = argparse.ArgumentParser(description="C-LARA static functionality map extractor (v0)")
    ap.add_argument("--repo", required=True, help="Path to local C-LARA repo root")
    ap.add_argument("--pubs", required=False, default=None, help="Path to local publications folder (optional)")
    ap.add_argument("--out", required=True, help="Output knowledge folder (e.g., /path/to/repo/knowledge)")
    args = ap.parse_args()

    repo = Path(_maybe_cygpath(args.repo))
    out = Path(_maybe_cygpath(args.out))
    knowledge_map_dir = out / "feature_map"
    publications_out = out / "publications_index.yaml"

    urls_py = repo / "clara_app" / "urls.py"
    base_html = repo / "clara_app" / "templates" / "clara_app" / "base.html"
    proj_html = repo / "clara_app" / "templates" / "clara_app" / "project_detail.html"

    urls_text = load_text(urls_py)
    if not urls_text:
        print(f"ERROR: cannot read {urls_py}", file=sys.stderr); sys.exit(1)

    routes, modules = parse_urls_py(urls_text)
    base_map = extract_menu_labels(load_text(base_html)) if base_html.exists() else {}
    proj_map = extract_menu_labels(load_text(proj_html)) if proj_html.exists() else {}

    # Build feature entries from menus (global + per-project)
    feature_entries = []
    def add_feature(route_name: str, label_hint: str, scope: str):
        if route_name not in routes: return
        view_ref, route_path = routes[route_name]
        # view_ref like clara_app.module.func
        module_path, func_name = view_ref.rsplit(".", 1) if "." in view_ref else (view_ref, "")
        file_rel = Path(*module_path.split("."))  # e.g., clara_app/export_zipfile_views
        py_file = repo / (str(file_rel) + ".py")
        templates, helpers, models = analyze_view_function(load_text(py_file), func_name)

        # Guess pattern by heuristics
        pattern = "crud_workflow"
        if "export" in route_name or "zip" in route_name:
            pattern = "single_shot_builder"
        if "render" in route_name:
            pattern = "render_and_publish_pipeline"
        if "edit_images" in route_name or "images" in module_path:
            pattern = "multi_stage_wizard_parallel"
        if "segment" in route_name:
            pattern = "batch_per_segment_annotation"

        card = {
            "id": route_name,
            "feature": label_hint or route_name,
            "pattern": pattern,
            "user_entry": {
                "template": f"clara_app/templates/clara_app/{'base.html' if scope=='global' else 'project_detail.html'}",
                "label": label_hint
            },
            "route": {"name": route_name, "path": route_path or None, "args": None},
            "entry_view": view_ref,
            "templates": templates,
            "forms": [],
            "models": models,
            "helpers": helpers,
            "ai_calls": [],
            "async": {"fanout": bool("edit_images" in route_name or "segment" in route_name or "render" in route_name),
                      "tracker": "clara_app.task_update_views" if ("segment" in route_name or "render" in route_name or "images" in route_name) else None},
            "artifacts_out": [],
            "side_effects": [],
            "permissions": "project_member",
            "metrics": [],
            # AI fields initially empty (to be generated later)
            "main_processing": [],
            "description_of_functionality": "",
            "description_of_processing": "",
            "ai_meta": {"sources_used": [f"{py_file.relative_to(repo)}"], "confidence": 0.5, "last_updated": None},
            "status": "draft"
        }
        feature_entries.append(card)

    for r, lbl in base_map.items():
        add_feature(r, lbl, scope="global")
    for r, lbl in proj_map.items():
        add_feature(r, lbl, scope="project")

    # Deduplicate by route name (prefer project-scoped labels if present)
    uniq = {}
    for c in feature_entries:
        uniq[c["id"]] = c
    feature_entries = list(uniq.values())

    # Write cards + index
    for card in feature_entries:
        write_yaml_card(knowledge_map_dir, card)
    index = {"count": len(feature_entries), "features": [c["id"] for c in feature_entries]}
    (out / "feature_index.yaml").write_text(yaml.safe_dump(index, sort_keys=False), encoding="utf-8")

    # Publications (filenames only for now)
    if args.pubs:
        pubs_path = Path(_maybe_cygpath(args.pubs))
        pubs = []
        for p in sorted(pubs_path.glob("*")):
            if p.suffix.lower() in {".pdf", ".md", ".html"}:
                pubs.append({"file": str(p), "title_guess": p.stem.replace("_"," ").replace("-"," ")})
        publications_out.write_text(yaml.safe_dump({"publications": pubs}, sort_keys=False), encoding="utf-8")

    print(f"✓ Wrote {len(feature_entries)} feature cards to {knowledge_map_dir}")
    if args.pubs:
        print(f"✓ Wrote publications index to {publications_out}")

if __name__ == "__main__":
    main()
