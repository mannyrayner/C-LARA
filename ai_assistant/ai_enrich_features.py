#!/usr/bin/env python3
"""
AI post-processor for functionality cards.

Reads YAML cards from ai_assistant/knowledge/feature_map/*.yaml,
opens the entry view + 1-hop helpers, prompts the model via C-LARA's
clara_chatgpt4, and writes back AI fields & metadata.

Usage:
  python ai_enrich_features.py --repo /path/to/C-LARA \
                               --out  /path/to/C-LARA/ai_assistant/knowledge \
                               [--limit 20] [--only export_zipfile,edit_images_v2]
"""

import argparse, os, sys, json, time, yaml, re, importlib.util
from pathlib import Path
from datetime import datetime

from ai_assistant.ai_assistant_utils import _maybe_cygpath

# --- Robust import of C-LARA client  -----------------------------------------
# We prefer: from clara_app import clara_chatgpt4 as chat
# but fall back to plain import if the module is placed differently.

def _import_chat_module(repo_root: Path):
    repo_norm = Path(_maybe_cygpath(str(repo_root)))
    
    # 1) Try normal package import with repo_root on sys.path
    sys.path.insert(0, str(repo_norm))
    try:
        from clara_app import clara_chatgpt4 as chat  # type: ignore
        return chat
    except Exception:
        pass

    # 2) Try plain import if script is next to us (unlikely, but harmless)
    try:
        import clara_chatgpt4 as chat  # type: ignore
        return chat
    except Exception:
        pass

    # 3) Load by absolute file path (works regardless of PYTHONPATH / package layout)
    candidate = repo_norm / "clara_app" / "clara_chatgpt4.py"
    if candidate.exists():
        spec = importlib.util.spec_from_file_location("clara_chatgpt4", str(candidate))
        if spec and spec.loader:
            chat = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(chat)  # type: ignore
            return chat

    raise RuntimeError(
        f"Could not import clara_chatgpt4. Tried package import and direct file load at: {candidate}"
    )
# --- Tiny helpers -------------------------------------------------------------
def load_yaml(p: Path) -> dict:
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def dump_yaml(p: Path, data: dict):
    with p.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def file_from_module(repo: Path, dotted: str) -> Path:
    # "clara_app.export_zipfile_views.make_export_zipfile" -> repo/clara_app/export_zipfile_views.py
    mod = ".".join(dotted.split(".")[:-1]) if "." in dotted else dotted
    return repo / Path(*mod.split(".")) .with_suffix(".py")

def func_name(dotted: str) -> str:
    return dotted.split(".")[-1] if "." in dotted else dotted

def snippet(text: str, func: str, max_chars=2000) -> str:
    # naive slice around "def func("
    pattern = rf"def\s+{re.escape(func)}\s*\("
    m = re.search(pattern, text)
    if not m:
        return text[:max_chars]
    start = max(0, m.start() - 400)
    end = min(len(text), m.end() + max_chars)
    return text[start:end]

# --- Prompt -------------------------------------------------------------------
PROMPT_TEMPLATE = """You are documenting a Django-based research platform (C-LARA).
Given code snippets and metadata for a *single feature*, produce a concise JSON object with:

- main_processing: array of 2–6 fully-qualified Python callables (module.func) that do the *main work*.
- description_of_functionality: 2–4 sentences for non-engineers: what the feature does.
- description_of_processing: 3–6 sentences for engineers: how it works end-to-end (routing → view → helpers/templates/models, async/AI if relevant).
- confidence: float 0..1 for how confident you are.

IMPORTANT:
- Use ONLY functions you saw in the snippets/metadata; prefer entry view + its helpers.
- If something is unclear, say so briefly in the processing description.
- Output JSON ONLY (no markdown, no prose), with keys exactly as in the schema.

METADATA
--------
feature: {feature}
route_name: {route_name}
entry_view: {entry_view}
templates: {templates}
helpers_1hop: {helpers}
models: {models}

ENTRY VIEW SNIPPET
------------------
{entry_view_snippet}

HELPER SNIPPETS
---------------
{helper_snippets}
"""

def build_prompt(card: dict, repo: Path) -> tuple[str, list[str]]:
    entry = card.get("entry_view", "")
    helpers = card.get("helpers", [])[:6]  # cap to keep prompt small
    templates = card.get("templates", [])
    models = card.get("models", [])
    route = card.get("route", {}).get("name", "")
    feature = card.get("feature", card.get("id"))

    # entry view code
    ev_path = file_from_module(repo, entry)
    ev_text = read_text(ev_path)
    ev_snip = snippet(ev_text, func_name(entry))

    # helper code (1-hop)
    helper_snips = []
    sources = [str(ev_path.relative_to(repo))] if ev_path.exists() else []
    for h in helpers:
        hp = file_from_module(repo, h)
        ht = read_text(hp)
        helper_snips.append(f"# Helper: {h}\n{snippet(ht, func_name(h))}\n")
        if hp.exists():
            sources.append(str(hp.relative_to(repo)))

    prompt = PROMPT_TEMPLATE.format(
        feature=feature,
        route_name=route,
        entry_view=entry,
        templates=templates,
        helpers=helpers,
        models=models,
        entry_view_snippet=ev_snip or "(entry view not found)",
        helper_snippets="\n".join(helper_snips) if helper_snips else "(no helpers detected)"
    )
    return prompt, sources

# --- Main ---------------------------------------------------------------------
def main():
    # --- in main() args ---
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", type=str, default="")
    ap.add_argument("--gpt-model", type=str, default=None, help="Override model (e.g., gpt-4o, o1-mini)")
    ap.add_argument("--api-key", type=str, default=None, help="Override OpenAI API key (else env OPENAI_API_KEY)")
    args = ap.parse_args()

    repo = Path(_maybe_cygpath(args.repo))
    out = Path(_maybe_cygpath(args.out))

    chat = _import_chat_module(repo)

    # Build config_info for clara_chatgpt4
    config_info = {}
    if args.gpt_model:
        config_info["gpt_model"] = args.gpt_model
    if args.api_key:
        config_info["open_ai_api_key"] = args.api_key
    # (If either is omitted, clara_chatgpt4 uses defaults: DEFAULT_GPT_4_MODEL = 'gpt-4o'
    #  and env var OPENAI_API_KEY.)  # see clara_chatgpt4.get_open_ai_api_key & DEFAULT_GPT_4_MODEL

    repo = Path(args.repo)
    out = Path(args.out)
    map_dir = out / "feature_map"
    index = (out / "feature_index.yaml")
    if not map_dir.exists():
        print(f"Missing feature_map at: {map_dir}", file=sys.stderr); sys.exit(1)

    chat = _import_chat_module(repo)  # uses clara_chatgpt4 API  :contentReference[oaicite:1]{index=1}

    cards = sorted(map_dir.glob("*.yaml"))
    if args.only:
        allow = set(s.strip() for s in args.only.split(","))
        cards = [p for p in cards if p.stem in allow]
    if args.limit and len(cards) > args.limit:
        cards = cards[:args.limit]

    updated = 0
    for i, p in enumerate(cards, 1):
        card = load_yaml(p)
        prompt, sources = build_prompt(card, repo)

        # Call model via C-LARA helper (includes tracing/costs)  :contentReference[oaicite:2]{index=2}
        api = chat.call_chat_gpt4(prompt, config_info={}, callback=None)
        # Parse JSON robustly using your helper
        try:
            intro, obj = chat.interpret_chat_gpt4_response_as_intro_and_json(api.response, object_type='dict', callback=None)  # :contentReference[oaicite:3]{index=3}
        except Exception:
            # Fallback: raw json loads
            obj = json.loads(api.response)

        # Merge into card
        card["main_processing"] = obj.get("main_processing", [])[:10]
        card["description_of_functionality"] = obj.get("description_of_functionality", "").strip()
        card["description_of_processing"] = obj.get("description_of_processing", "").strip()
        meta = card.get("ai_meta", {}) or {}
        meta.update({
            "sources_used": sorted(set((meta.get("sources_used") or []) + sources)),
            "confidence": float(obj.get("confidence", 0.6)),
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d")
        })
        card["ai_meta"] = meta
        dump_yaml(p, card)
        print(f"[{i}/{len(cards)}] updated {p.name}")
        updated += 1

    # touch index updated time
    if index.exists():
        idx = load_yaml(index)
        idx["last_enriched"] = datetime.utcnow().isoformat()
        dump_yaml(index, idx)

    print(f"✓ Enriched {updated} feature cards")

if __name__ == "__main__":
    main()
