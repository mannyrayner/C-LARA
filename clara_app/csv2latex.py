#!/usr/bin/env python3
"""
csv2latex.py  —  Convert image-questionnaire CSV to a LaTeX table.

Usage:
    python csv2latex.py results.csv [format.json]  > table.tex
"""

import csv, json, sys, argparse, textwrap
from collections import defaultdict, OrderedDict

IMAGE_QUESTIONNAIRE_QUESTIONS = [
    {
        "id": 1,
        "text": "How well does the image correspond to the page text?",
    },
    {
        "id": 2,
        "text": "How consistent is the style of the image with the overall style?",
    },
    {
        "id": 3,
        "text": "How consistent is the appearance of elements in the image with their previous appearance?",
    },
    {
        "id": 4,
        "text": "Is the image appropriate to the relevant culture?",
    },
    {
        "id": 5,
        "text": "How visually appealing do you find the image?",
    },
]

def load_format(path):
    if not path:
        return {}, []
    with open(path, encoding="utf-8") as f:
        obj = json.load(f)
    abbrev = obj.get("abbrev", {})
    order  = obj.get("order", [])
    groups  = obj.get("groups", [])
    return abbrev, order, groups

def escape_tex(s):
    return s.replace("&", "\\&").replace("%", "\\%")

def pivot(rows):
    """rows: list of dicts from the CSV reader"""
    table = defaultdict(dict)      # project → {qid: "avg (n)"}
    pages  = {}
    evals  = {}
    questions = set()
    for r in rows:
        proj = r["project"]
        qid  = int(r["question_id"])
        questions.add(qid)
        table[proj][qid] = f"{r['avg_rating']} ({r['num_responses']})"

        # capture once per project
        pages.setdefault(proj, r["pages"])
        evals.setdefault(proj, r["evaluators"])
    return table, pages, evals, sorted(questions)

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

def build_group_map(groups):
    first_of_group = {}                     # short → label (only very first)
    for g in groups:
        label   = g["label"]
        members = g["members"]
        if not members:
            continue
        first_of_group[members[0]] = label  # only the first short code
    return first_of_group

def build_latex(table, pages, evals, questions, abbrev, order, groups):
    projects = row_order(table.keys(), order, abbrev)
    first_trigger = build_group_map(groups)  # groups read from JSON
    qcols = " & ".join([f"Q{q}" for q in questions])
    lines = [
        "\\begin{table*}[h]",
        "\\caption{Image-questionnaire results (Img = number of illustrated pages, Eval = distinct evaluators)}\\label{tab:results}",
        "\\centering",
        f"\\begin{{tabular}}{{l{'c' * ( 2 + len(questions) )}}}",
        "\\toprule",
        f"Project & Img & Eval & {qcols}\\\\"
    ]
    for proj in projects:
        short = abbrev.get(proj, proj)  # DI, SC, etc.
        # Insert group header if this project is first in its group
        if short in first_trigger and first_trigger[short]:
            label = first_trigger.pop(short)
            lines.append(
                r"\midrule")
            lines.append(
                f"\\multicolumn{{{3+len(IMAGE_QUESTIONNAIRE_QUESTIONS)}}}{{c}}{{\\textit{{{label}}}}}\\\\")
            lines.append(
                r"\midrule")
            
        title = escape_tex(abbrev.get(proj, proj))
        cells = [pages[proj], evals[proj]] + [table[proj].get(q, "--") for q in questions]
        #cells = [table[proj].get(q, "--") for q in questions]
        lines.append(f"{title} & " + " & ".join(cells) + "\\\\")
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table*}"]
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", help="CSV produced by image_questionnaire_csv")
    parser.add_argument("fmt", nargs="?", help="Optional JSON for abbrev/order")
    args = parser.parse_args()

    rows = list(csv.DictReader(open(args.csv, newline="", encoding="utf-8")))
    if not rows:
        sys.exit("CSV file is empty or headers missing.")

    abbrev, order, groups = load_format(args.fmt)
    table, pages, evals, questions = pivot(rows)
    latex = build_latex(table, pages, evals, questions, abbrev, order, groups)
    print(latex)

if __name__ == "__main__":
    main()
