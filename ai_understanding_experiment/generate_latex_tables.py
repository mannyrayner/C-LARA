#!/usr/bin/env python3
# Script to generate LaTeX table fragments from analysis CSV outputs.
# It will read CSV files produced by analysis_script.py in a given input directory
# and produce LaTeX fragment files in an output directory.
#
# Usage (from shell):
#   python generate_latex_tables.py /path/to/analysis_outputs /path/to/output_tex
#
# The script creates files:
#   decision_dist.tex
#   agreement.tex
#   avg_conf.tex
#   conf_by_question.tex
#   theses_longtable.tex
#
# These fragments can be included in your LaTeX source with \input{path/to/file.tex}.
# Note: the longtable fragment generated for thesis excerpts is a non-float environment
# (longtable/ltablex style) and must not be wrapped inside a table float.
#
# The script is intentionally conservative about LaTeX escaping; it escapes common special chars.
# If you need additional customization (fonts, column widths), edit the script accordingly.

import sys
import os
import pandas as pd
import argparse

def latex_escape(s: str) -> str:
    if pd.isna(s):
        return ''
    s = str(s)
    # Basic LaTeX escaping
    replacements = {
        '\\': r'\textbackslash{}',
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
        '<': r'\textless{}',
        '>': r'\textgreater{}',
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    # Collapse multiple spaces to a single space
    s = " ".join(s.split())
    return s

def write_decision_dist(counts_csv, out_path):
    df = pd.read_csv(counts_csv, index_col=0)
    for col in ['a','b','c','total']:
        if col not in df.columns:
            df[col] = 0
    lines = []
    lines.append(r'\begin{table}[h]')
    lines.append(r'\centering')
    lines.append(r'\caption{Decision distribution by model (counts). Numbers reproduced from the analysis report.}')
    lines.append(r'\label{tab:decision-dist}')
    lines.append(r'\begin{tabular}{lrrrr}')
    lines.append(r'\hline')
    lines.append(r'Model & \#calls & \#a (support) & \#b (reject) & \#c (decline) \\')
    lines.append(r'\hline')
    for model, row in df.iterrows():
        a = int(row.get('a',0))
        b = int(row.get('b',0))
        c = int(row.get('c',0))
        total = int(row.get('total', a+b+c))
        lines.append(f"{latex_escape(model)} & {total} & {a} & {b} & {c} \\\\")
    lines.append(r'\hline')
    lines.append(r'\end{tabular}')
    lines.append(r'\end{table}')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    print("Wrote", out_path)

def write_agreement(agreement_csv, out_path):
    df = pd.read_csv(agreement_csv)
    lines = []
    lines.append(r'\begin{table}[h]')
    lines.append(r'\centering')
    lines.append(r'\caption{Per-question agreement summary (each row indicates whether all models agreed on that question).}')
    lines.append(r'\label{tab:agreement}')
    lines.append(r'\begin{tabular}{llr}')
    lines.append(r'\hline')
    lines.append(r'question\_id & agree & value \\')
    lines.append(r'\hline')
    for _, row in df.iterrows():
        q = latex_escape(row.get('question_id',''))
        agree = str(row.get('agree',''))
        val = row.get('value','')
        val_str = latex_escape(val)
        lines.append(f"{q} & {agree} & {val_str} \\\\")
    lines.append(r'\hline')
    lines.append(r'\end{tabular}')
    lines.append(r'\end{table}')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    print("Wrote", out_path)

def write_avg_conf(avg_conf_csv, out_path):
    df = pd.read_csv(avg_conf_csv)
    lines = []
    lines.append(r'\begin{table}[h]')
    lines.append(r'\centering')
    lines.append(r'\caption{Average reported confidence by model (mean $\pm$ std, $n$ calls).}')
    lines.append(r'\label{tab:avg-conf}')
    lines.append(r'\begin{tabular}{lccc}')
    lines.append(r'\hline')
    lines.append(r'Model & mean(confidence) & std(confidence) & n \\')
    lines.append(r'\hline')
    for _, row in df.iterrows():
        model = latex_escape(row['model']) if 'model' in row else latex_escape(row.name)
        mean = f"{row.get('mean_confidence', ''):.4f}" if pd.notna(row.get('mean_confidence', None)) else ''
        std = f"{row.get('std_confidence', ''):.4f}" if pd.notna(row.get('std_confidence', None)) else ''
        n = int(row.get('n', 0)) if pd.notna(row.get('n', None)) else 0
        lines.append(f"{model} & {mean} & {std} & {n} \\\\")
    lines.append(r'\hline')
    lines.append(r'\end{tabular}')
    lines.append(r'\end{table}')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    print("Wrote", out_path)

def write_conf_by_question(conf_csv, out_path):
    df = pd.read_csv(conf_csv, index_col=0)
    models = list(df.columns)
    lines = []
    lines.append(r'\begin{table}[h]')
    lines.append(r'\centering')
    lines.append(r'\caption{Per-model, per-question mean reported confidence (values reproduced from the analysis report).}')
    lines.append(r'\label{tab:conf-by-question}')
    col_spec = 'l' + 'c' * len(models)
    lines.append(r'\begin{tabular}{' + col_spec + r'}')
    lines.append(r'\hline')
    header = 'question\\_id & ' + ' & '.join([latex_escape(m) for m in models]) + r' \\'
    lines.append(header)
    lines.append(r'\hline')
    for q, row in df.iterrows():
        vals = []
        for m in models:
            v = row[m]
            if pd.isna(v):
                vals.append('')
            else:
                vals.append(f"{float(v):.2f}")
        line = latex_escape(q) + ' & ' + ' & '.join(vals) + r' \\'
        lines.append(line)
    lines.append(r'\hline')
    lines.append(r'\end{tabular}')
    lines.append(r'\end{table}')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    print("Wrote", out_path)

def write_majority_matrix(decisions_csv, unanimity_csv, out_path):
    dec = pd.read_csv(decisions_csv, index_col=0)
    uni = pd.read_csv(unanimity_csv, index_col=0)

    models = list(dec.columns)

    lines = []
    lines.append(r'\begin{table}[h]')
    lines.append(r'\centering')
    lines.append(r'\caption{Per-question majority decision by model. A star ($^\ast$) marks cells where runs were not unanimous for that model/question.}')
    lines.append(r'\label{tab:majority-matrix}')
    col_spec = 'l' + 'c' * len(models)
    lines.append(r'\begin{tabular}{' + col_spec + r'}')
    lines.append(r'\hline')
    header = 'question\\_id & ' + ' & '.join([latex_escape(m) for m in models]) + r' \\'
    lines.append(header)
    lines.append(r'\hline')
    for q, row in dec.iterrows():
        cells = []
        for m in models:
            val = row[m]
            if pd.isna(val):
                cells.append('')
            else:
                mark = ''
                try:
                    if not bool(uni.loc[q, m]):
                        mark = r'$^\ast$'
                except Exception:
                    pass
                cells.append(latex_escape(val) + mark)
        lines.append(latex_escape(q) + ' & ' + ' & '.join(cells) + r' \\')
    lines.append(r'\hline')
    lines.append(r'\end{tabular}')
    lines.append(r'\end{table}')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    print("Wrote", out_path)

def write_theses_longtable(theses_csv, out_path):
    df = pd.read_csv(theses_csv)
    lines = []
    lines.append(r'\small')
    lines.append(r'\begin{longtable}{@{} l l p{0.64\linewidth} @{} }')
    lines.append(r'\caption[Thesis excerpts (short)]{Representative short thesis excerpts (per model \& claim). Entries show the first $\approx$200 characters of the thesis field; full outputs are in the JSONL logs.}')
    lines.append(r'\label{tab:theses} \\')
    lines.append('')
    lines.append(r'\toprule')
    lines.append(r'question\_id & model & thesis\_short \\')
    lines.append(r'\midrule')
    lines.append(r'\endfirsthead')
    lines.append('')
    lines.append(r'\multicolumn{3}{@{}l}{\textbf{Table \ref{tab:theses} (continued)}}\\[0.5ex]')
    lines.append(r'\toprule')
    lines.append(r'question\_id & model & thesis\_short \\')
    lines.append(r'\midrule')
    lines.append(r'\endhead')
    lines.append('')
    lines.append(r'\midrule \multicolumn{3}{r}{\textit{(continued on next page)}} \\')
    lines.append(r'\endfoot')
    lines.append('')
    lines.append(r'\bottomrule')
    lines.append(r'\endlastfoot')
    lines.append('')
    df_sorted = df.sort_values(['question_id','model'])
    for _, row in df_sorted.iterrows():
        q = latex_escape(row.get('question_id',''))
        model = latex_escape(row.get('model',''))
        thesis = row.get('thesis','') if pd.notna(row.get('thesis','')) else ''
        thesis_short = thesis.replace('\n',' ').strip()[:200]
        thesis_short = latex_escape(thesis_short)
        lines.append(f"{q} & {model} & {thesis_short} \\\\ [0.6ex]")
    lines.append('')
    lines.append(r'\end{longtable}')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    print("Wrote", out_path)

def main():
    parser = argparse.ArgumentParser(description='Generate LaTeX table fragments from analysis CSV outputs.')
    parser.add_argument('in_dir', help='Directory containing CSV outputs from analysis_script.py')
    parser.add_argument('out_dir', help='Directory to write LaTeX fragments to')
    args = parser.parse_args()
    IN = args.in_dir
    OUT = args.out_dir
    os.makedirs(OUT, exist_ok=True)
    files = {
        'counts': os.path.join(IN, 'decision_counts_by_model.csv'),
        'agreement': os.path.join(IN, 'agreement_by_question.csv'),
        'avg_conf': os.path.join(IN, 'avg_conf_by_model.csv'),
        'conf_pivot': os.path.join(IN, 'conf_mean_by_question_model.csv'),
        'theses': os.path.join(IN, 'first_thesis_samples.csv'),
    }
    missing = [k for k,v in files.items() if not os.path.exists(v)]
    if missing:
        print("Error: missing expected input files:", missing)
        sys.exit(2)
    write_decision_dist(files['counts'], os.path.join(OUT, 'decision_dist.tex'))
    write_agreement(files['agreement'], os.path.join(OUT, 'agreement.tex'))
    write_avg_conf(files['avg_conf'], os.path.join(OUT, 'avg_conf.tex'))
    write_conf_by_question(files['conf_pivot'], os.path.join(OUT, 'conf_by_question.tex'))
    maj_decisions = os.path.join(IN, 'majority_decisions_wide.csv')
    
    unanimity = os.path.join(IN, 'unanimity_wide.csv')
    if os.path.exists(maj_decisions) and os.path.exists(unanimity):
        write_majority_matrix(maj_decisions, unanimity, os.path.join(OUT, 'majority_matrix.tex'))
        
    write_theses_longtable(files['theses'], os.path.join(OUT, 'theses_longtable.tex'))
    print("All LaTeX fragments written to", os.path.abspath(OUT))

if __name__ == '__main__':
    main()
