#!/usr/bin/env python3
"""
Reads ai_assistant/config.toml and emits a tiny Makefile fragment (.config.mk)
with MODEL and API_KEY assignments (no echoing to stdout during normal make).

Usage (from Makefile rule):
  python3 read_config.py --toml config.toml > .config.mk
"""

import argparse, sys

def load_toml(path: str) -> dict:
    # Python 3.11+: tomllib is stdlib. Otherwise try tomli (pip install tomli).
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
            print(f"# WARN: Could not import tomllib/tomli: {e}", file=sys.stderr)
            return {}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--toml", required=True)
    args = ap.parse_args()

    data = load_toml(args.toml) or {}
    openai = data.get("openai", {})
    model = str(openai.get("model", "")).strip()
    api_key = str(openai.get("api_key", "")).strip()

    # Emit a minimal Makefile snippet. We avoid printing secrets elsewhere.
    print(f"MODEL := {model}")
    # Keep API key in a variable, but we’ll pass it to the tool as an env var
    # to avoid showing it in the process args list.
    print(f"API_KEY := {api_key}")

if __name__ == "__main__":
    main()
