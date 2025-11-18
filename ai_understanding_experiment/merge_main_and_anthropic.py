#!/usr/bin/env python3
import csv
from pathlib import Path
from collections import defaultdict

# --- CONFIG: edit these to match your dirs ---
DIR_A = Path("results_woke_2025_11_18")         # first big run (all providers, Anthropic rate-limited)
DIR_B = Path("results_woke_anthropic_2025_11_18")   # second run (Anthropic only)
OUT_DIR = Path("results_woke_2025_11_18_merged")    # new merged directory
SUMMARY_NAME = "summary.csv"
# --------------------------------------------

def read_csv(path):
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows, reader.fieldnames

def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

def merge_summaries():
    path_a = DIR_A / SUMMARY_NAME
    path_b = DIR_B / SUMMARY_NAME
    if not path_a.exists():
        raise FileNotFoundError(f"Missing {path_a}")
    if not path_b.exists():
        raise FileNotFoundError(f"Missing {path_b}")

    rows_a, fields_a = read_csv(path_a)
    rows_b, fields_b = read_csv(path_b)

    # Ensure headers are compatible
    if fields_a != fields_b:
        # simple reconciliation: union of fields, keep order from A then extras from B
        extra = [c for c in fields_b if c not in fields_a]
        fieldnames = fields_a + extra
        print("[WARN] summary.csv headers differ; using union of columns.")
    else:
        fieldnames = fields_a

    # Helper to normalise row keys to full field set
    def normalise_row(row, all_fields):
        return {k: row.get(k, "") for k in all_fields}

    # 1) Keep all non-Anthropic rows from run A
    merged = []
    for r in rows_a:
        if r.get("provider") != "anthropic":
            merged.append(normalise_row(r, fieldnames))

    # 2) Add all Anthropic rows from run B
    for r in rows_b:
        if r.get("provider") == "anthropic":
            merged.append(normalise_row(r, fieldnames))

    # 3) Basic sanity: check for duplicates of (provider, model, question_id, run)
    seen = set()
    dups = []
    for r in merged:
        key = (
            r.get("provider", ""),
            r.get("model", ""),
            r.get("question_id", ""),
            r.get("run", ""),
        )
        if key in seen:
            dups.append(key)
        else:
            seen.add(key)

    if dups:
        print("[WARN] Duplicate (provider, model, question_id, run) combinations found:")
        for k in sorted(set(dups)):
            print("   ", k)
    else:
        print("[INFO] No duplicate (provider, model, question_id, run) combinations detected.")

    # 4) Check for missing combinations: runs per (provider, model, question_id)
    combos = defaultdict(set)
    for r in merged:
        key = (r.get("provider", ""), r.get("model", ""), r.get("question_id", ""))
        try:
            run_idx = int(r.get("run", 0))
        except ValueError:
            # If run is missing or malformed, treat as 0
            run_idx = 0
        combos[key].add(run_idx)

    missing_any = False
    for key, runs in sorted(combos.items()):
        provider, model, qid = key
        if not runs:
            continue
        max_run = max(runs)
        expected = set(range(0, max_run + 1))
        if runs != expected:
            missing_any = True
            missing = sorted(expected - runs)
            if missing:
                print(f"[WARN] Missing runs for provider={provider}, model={model}, question_id={qid}: {missing}")

    if not missing_any:
        print("[INFO] No missing run indices detected for any (provider, model, question_id).")

    # 5) Write merged summary
    out_path = OUT_DIR / SUMMARY_NAME
    write_csv(out_path, merged, fieldnames)
    print(f"[OK] Wrote merged summary to {out_path}")

if __name__ == "__main__":
    merge_summaries()
