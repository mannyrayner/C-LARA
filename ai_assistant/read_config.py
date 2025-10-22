#!/usr/bin/env python3
"""
Reads ai_assistant/config.toml and emits a tiny Makefile fragment (.config.mk)
with MODEL and API_KEY assignments.

Usage:
  python3 read_config.py --toml config.toml > .config.mk
"""
import argparse, sys, os, shutil, subprocess

from ai_assistant.ai_assistant_utils import _maybe_cygpath

def load_toml(path: str) -> dict:
    # Python 3.11+: tomllib is stdlib. Otherwise try tomli.
    try:
        import tomllib  # type: ignore
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        try:
            import tomli  # type: ignore
            with open(path, "rb") as f:
                return tomli.load(f)
        except Exception as e:
            print(f"# WARN: Could not import/parse TOML via tomllib/tomli: {e}", file=sys.stderr)
            return {}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--toml", required=True)
    args = ap.parse_args()

    toml_path = _maybe_cygpath(args.toml)  # <<< normalize for Windows Python
    data = load_toml(toml_path) or {}
    openai = data.get("openai", {})
    model = str(openai.get("model", "")).strip()
    api_key = str(openai.get("api_key", "")).strip()

    # Emit a minimal Makefile snippet
    print(f"MODEL := {model}")
    print(f"API_KEY := {api_key}")

if __name__ == "__main__":
    main()
