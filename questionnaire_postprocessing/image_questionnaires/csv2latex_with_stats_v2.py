#!/usr/bin/env python3
"""
csv2latex_with_stats.py  –  build LaTeX results table
1. read *raw* ratings CSV  (cols: project,page,question_id,rater,rating)
2. compute per-project means  + ICC(2,1)  + Krippendorff α (ordinal)
3. output LaTeX table

Usage:
    python csv2latex_with_stats_v2.py raw.csv  [fmt.json]  > table.tex
"""
import argparse, json, sys
from collections import defaultdict

import pandas as pd
import krippendorff                     # pip install krippendorff
from pingouin import intraclass_corr    # pip install pingouin

Q_IDS  = [1, 2, 3, 4, 5]
COLS   = "project page question_id rater rating".split()

# ----------------------------------------------------------------------
def load_format(path):
    """Return (abbrev_map, ordering, groups) from optional JSON."""
    if not path:
        return {}, [], []
    with open(path, encoding="utf-8") as f:
        obj = json.load(f)
    return (obj.get("abbrev", {}),
            obj.get("order",  []),
            obj.get("groups", []))

def order_projects(keys, order_hint, abbrev):
    short2full = {s: f for f, s in abbrev.items()}
    seen, out  = set(), []
    for short in order_hint:
        full = short2full.get(short)
        if full in keys and full not in seen:
            out.append(full);  seen.add(full)
    out += sorted(k for k in keys if k not in seen)
    return out

def group_headers(groups):
    """Return {first_short: group_label}."""
    first = {}
    for g in groups:
        if g.get("members"):
            first[g["members"][0]] = g["label"]
    return first

# ----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("fmt", nargs="?")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    missing = [c for c in COLS if c not in df.columns]
    if missing:
        sys.exit(f"ERROR: CSV missing columns: {missing}")

    abbrev, ordering, groups = load_format(args.fmt)
    projects   = order_projects(df.project.unique(), ordering, abbrev)
    group_map  = group_headers(groups)

    header_q = " & ".join([f"Q{q}" for q in Q_IDS])
    lines = [
        r"\begin{table*}[h]",
        r"\caption{Image–questionnaire results "
        r"(\#p = \#pages, \#r = \#raters, "
        #r"ICC = intraclass correlation coefficient (2,1), "
        #r"$\alpha$ = Krippendorff’s $\alpha$, "
        r" Q1--5 as in Table~\ref{Table:ImageQuestions}: "
        r"Q1 = correspond, Q2 = style, Q3 = coherent, Q4 = appropriate, Q5 = appealing. "
        r"Mean score out of 5 for each question)}\label{tab:results}",
        r"\centering",
        #rf"\begin{{tabular}}{{lccc{'c'*len(Q_IDS)}}}",
        rf"\begin{{tabular}}{{lc{'c'*len(Q_IDS)}}}",
        r"\toprule",
        #rf"Project & \#p & \#r & ICC & $\alpha$ & {header_q} \\",
        rf"Project & \#p & \#r & {header_q} \\",
    ]

    # ------------------------------------------------------------
    for proj in projects:
        sub = df[df.project == proj]
        n_pages  = sub.page.nunique()
        n_raters = sub.rater.nunique()

        # ---------- Krippendorff α (ordinal, all questions pooled) ---
        mat = sub.pivot_table(index='rater',
                              columns=['page', 'question_id'],
                              values='rating')
        alpha = ""
        if mat.shape[0] > 1 and mat.nunique().to_numpy().sum() > 1:
            alpha_val = krippendorff.alpha(mat.to_numpy(),
                                           level_of_measurement='ordinal')
            alpha = f"{alpha_val:.2f}"

        # --- ICC(2,1) -------------------------------------------------
        pivot = (
            sub.pivot_table(index='page', columns='rater', values='rating')
            .dropna()        # pair-wise complete
        )

        if pivot.shape[1] > 1 and pivot.shape[0] > 1:
            icc_res = intraclass_corr(data=pivot.reset_index().melt('page'),
                                         targets='page', raters='rater',
                                         ratings='value')
            row_icc = icc_res.query("Type=='ICC2k'")  # average-measurement
            icc = f"{row_icc['ICC'].iloc[0]:.2f}"
        else:
            icc = ""

        # ---------- means per question -------------------------------
        means = []
        for q in Q_IDS:
            q_scores = sub.loc[sub.question_id == q, 'rating']
            means.append(f"{q_scores.mean():.2f}" if not q_scores.empty else "--")

        # ---------- group header if needed ---------------------------
        short = abbrev.get(proj, False)               # e.g. "DI"
        if short:
            if short in group_map:
                label = group_map.pop(short)
                lines += [
                    r"\midrule",
                    rf"\multicolumn{{{3+len(Q_IDS)}}}{{c}}"
                    rf"{{\textit{{{label}}}}} \\",
                    r"\midrule"
                ]

            #row = [short, n_pages, n_raters, icc, alpha] + means
            row = [short, n_pages, n_raters] + means
            lines.append(" & ".join(map(str, row)) + r"\\")

    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
    print("\n".join(lines))

if __name__ == "__main__":
    main()
