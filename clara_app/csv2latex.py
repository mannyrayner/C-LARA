#!/usr/bin/env python3
"""
csv2latex.py  —  Convert image-questionnaire CSV to a LaTeX table.

Usage:
    python csv2latex.py results.csv [format.json]  > table.tex
"""

import csv, json, sys, argparse, textwrap
from collections import defaultdict, OrderedDict

def load_format(path):
    if not path:
        return {}, []
    with open(path, encoding="utf-8") as f:
        obj = json.load(f)
    abbrev = obj.get("abbrev", {})
    order  = obj.get("order", [])
    return abbrev, order

def escape_tex(s):
    return s.replace("&", "\\&").replace("%", "\\%")

def pivot(rows):
    """rows: list of dicts from the CSV reader"""
    table = defaultdict(dict)      # project → {qid: "avg (n)"}
    questions = set()
    for r in rows:
        proj = r["project"]
        qid  = int(r["question_id"])
        questions.add(qid)
        table[proj][qid] = f"{r['avg_rating']} ({r['num_responses']})"
    return table, sorted(questions)

def row_order(table_keys, order_hint, abbrev_map):
    """
    order_hint is a list of SHORT codes.
    Convert them to full titles via abbrev_map before ordering.
    """
    # Build reverse map: SHORT -> Full
    rev = {short: full for full, short in abbrev_map.items()}

    explicit = []
    seen = set()
    for short in order_hint:
        full = rev.get(short)
        if full and full in table_keys and full not in seen:
            explicit.append(full)
            seen.add(full)

    # Append any projects not mentioned, in alpha order
    for k in sorted(table_keys):
        if k not in seen:
            explicit.append(k)
    return explicit


def build_latex(table, questions, abbrev, order):
    projects = row_order(table.keys(), order, abbrev)
    qcols = " & ".join([f"Q{q}" for q in questions])
    lines = [
        "\\begin{table}[h]",
        "\\caption{Image-questionnaire results}\\label{tab:results}",
        "\\centering",
        f"\\begin{{tabular}}{{l{'r' * len(questions)}}}",
        "\\toprule",
        f"Project & {qcols}\\\\",
        "\\midrule",
    ]
    for proj in projects:
        title = escape_tex(abbrev.get(proj, proj))
        cells = [table[proj].get(q, "--") for q in questions]
        lines.append(f"{title} & " + " & ".join(cells) + "\\\\")
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table}"]
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", help="CSV produced by image_questionnaire_csv")
    parser.add_argument("fmt", nargs="?", help="Optional JSON for abbrev/order")
    args = parser.parse_args()

    rows = list(csv.DictReader(open(args.csv, newline="", encoding="utf-8")))
    if not rows:
        sys.exit("CSV file is empty or headers missing.")

    abbrev, order = load_format(args.fmt)
    table, questions = pivot(rows)
    latex = build_latex(table, questions, abbrev, order)
    print(latex)

if __name__ == "__main__":
    main()
