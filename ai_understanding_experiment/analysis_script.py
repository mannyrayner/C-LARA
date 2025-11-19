#!/usr/bin/env python3
"""Detailed analysis of experiment summary.csv

Usage:
  python analysis_script.py /path/to/summary.csv /path/to/output_dir

Produces:
- decision_counts_by_model.csv
- per_question_decisions_wide.csv
- agreement_by_question.csv
- conf_stats_by_model_question.csv
- conf_mean_by_question_model.csv  <-- NEW: full per-model x per-question mean confidences
- avg_conf_by_model.csv
- consistency_by_model_question.csv
- first_thesis_samples.csv
- analysis_report.txt (human-readable summary)
- short_summary.json (concise JSON summary)
"""

import sys, os, json, ast
import pandas as pd, numpy as np
from datetime import datetime

def safe_parse(s):
    if pd.isna(s):
        return {}
    if isinstance(s, dict):
        return s
    try:
        return json.loads(s)
    except Exception:
        try:
            return ast.literal_eval(s)
        except Exception:
            return {}

def main():
    if len(sys.argv) < 3:
        print("Usage: python analysis_script.py /path/to/summary.csv /path/to/output_dir")
        sys.exit(1)
    IN = sys.argv[1]
    OUT_DIR = sys.argv[2]
    os.makedirs(OUT_DIR, exist_ok=True)

    df = pd.read_csv(IN)

    def norm_decision(val):
        """Normalise decision codes to 'a', 'b', 'c' where possible."""
        if pd.isna(val):
            return 'c'  # treat missing as 'c' (no position / refusal)
        s = str(val).strip().lower()
        if s.startswith('a'):
            return 'a'
        if s.startswith('b'):
            return 'b'
        if s.startswith('c'):
            return 'c'
        # fall back to raw string if something unexpected shows up
        return s

# --- Ensure decision column exists and has one of the three permitted values ---
    if 'decision' not in df.columns:
        df['decision'] = 'c'
    df['decision'] = df['decision'].apply(norm_decision)

# --- Ensure confidence is numeric, tolerating "N/A" etc. ---
    if 'confidence' in df.columns:
        df['confidence'] = pd.to_numeric(df['confidence'], errors='coerce')
    else:
        # if for some reason it's missing, create it so later code still works
        df['confidence'] = np.nan

# --- Ensure thesis column exists (textual, so just default to empty string) ---
    if 'thesis' not in df.columns:
        df['thesis'] = ""
    df['thesis'] = df['thesis'].fillna("").astype(str)           

    counts = df.groupby(['model','decision']).size().unstack(fill_value=0)
    counts['total'] = counts.sum(axis=1)

    unique_decisions = df.groupby(['question_id','model'])['decision'].agg(lambda s: ','.join(sorted(set(s)))).reset_index()
    wide = unique_decisions.pivot(index='question_id', columns='model', values='decision').fillna('')

    def models_agree(row):
        """
        Decide whether all models agree, and always return the full
        list of per-model decisions as `value`.

        - `agree` is True iff every non-empty cell has a single code
          (no commas) and all codes are identical.
        - `value` is always the list of raw cell values in row order
          (e.g. ['a', 'b', 'b', 'a', 'a']).
        """
        vals = [v for v in row.tolist() if v != '']
        if not vals:
            return False, []

        # models 'agree' only if:
        #  - no cell contains a comma (i.e. each model had a unique decision),
        #  - and all codes are identical
        simple_vals = [v for v in vals if ',' not in v]
        agree = (len(simple_vals) == len(vals) and len(set(simple_vals)) == 1)

        return agree, vals

    def majority_decision(series):
        # keep only valid decisions
        vals = [d for d in series if d in ('a', 'b', 'c')]
        if not vals:
            return ''
        counts = pd.Series(vals).value_counts()
        top = counts[counts == counts.max()].index.tolist()
        # usually a single element, but if tied we concatenate, e.g. 'ab'
        return ''.join(sorted(top))

    agreement = []
    for q, row in wide.iterrows():
        agree, val = models_agree(row)
        rec = {'question_id': q, 'agree': agree, 'value': val}
        for col in wide.columns:
            rec[col] = row[col]
        agreement.append(rec)
    agreement_df = pd.DataFrame(agreement)

    # --- restrict confidence stats to rows with numeric confidence ---
    conf_df = df.dropna(subset=['confidence']).copy()

    conf_stats = (
        conf_df.groupby(['model', 'question_id'])['confidence']
        .agg(['mean', 'std', 'count'])
        .reset_index()
        .rename(columns={
            'mean': 'mean_confidence',
            'std': 'std_confidence',
            'count': 'n'
        })
    )

    # Majority decision per (model, question_id)
    maj_dec = (
        df.groupby(['model', 'question_id'])['decision']
          .apply(majority_decision)
          .reset_index()
          .rename(columns={'decision': 'majority_decision'})
        )

    # --- Pairwise agreement across models (same majority decision on a question) ---
    maj = maj_dec[['model','question_id','majority_decision']].copy()

    # Normalise majority_decision to {'a','b','c'}; everything else -> '?'
    def norm_abc(x: str) -> str:
        if not isinstance(x, str):
            return '?'
        s = x.strip().lower()
        return s[0] if s and s[0] in {'a','b','c'} else '?'

    maj['majority_decision'] = maj['majority_decision'].apply(norm_abc)

    models = sorted(maj['model'].unique())
    pairs = []
    for i in range(len(models)):
        for j in range(i+1, len(models)):
            mi, mj = models[i], models[j]
            a = maj[maj['model']==mi].set_index('question_id')['majority_decision']
            b = maj[maj['model']==mj].set_index('question_id')['majority_decision']
            joined = a.to_frame('di').join(b.to_frame('dj'), how='inner')
            n = len(joined)
            agree_n = int((joined['di'] == joined['dj']).sum())
            disagree_list = joined[joined['di'] != joined['dj']].reset_index()[['question_id','di','dj']].to_dict('records')
            pairs.append({
                'model_i': mi,
                'model_j': mj,
                'n_compared': n,
                'n_agree': agree_n,
                'agree_rate': (agree_n / n) if n else float('nan'),
                'disagreements': disagree_list
            })

    pairwise_df = pd.DataFrame(pairs).sort_values(['agree_rate','model_i','model_j'], ascending=[False, True, True])

    # Pretty square matrix (Model x Model -> agree_rate), helpful in the report
    matrix = pd.DataFrame(index=models, columns=models, dtype=float)
    for m in models:
        matrix.loc[m,m] = 1.0
    for row in pairs:
        i, j = row['model_i'], row['model_j']
        matrix.loc[i,j] = row['agree_rate']
        matrix.loc[j,i] = row['agree_rate']

    # Attach majority_decision
    conf_stats = conf_stats.merge(maj_dec, on=['model','question_id'], how='left')

    avg_conf_model = (
        conf_df.groupby('model')['confidence']
        .agg(['mean', 'std', 'count'])
        .reset_index()
        .rename(columns={
            'mean': 'mean_confidence',
            'std': 'std_confidence',
            'count': 'n'
        })
    )
    # Pivot to full per-question x per-model mean_confidence table
    conf_pivot = conf_stats.pivot(index='question_id', columns='model', values='mean_confidence').sort_index()
    # fill NaN with empty for nicer CSV/readout
    conf_pivot_filled = conf_pivot.fillna('')

    # Consistency across runs for each model/question
    consistency = df.groupby(['model','question_id'])['decision'].nunique().reset_index().rename(columns={'decision':'unique_decisions'})
    consistency['consistent'] = consistency['unique_decisions']==1
    consistency_summary = consistency.groupby('model')['consistent'].mean().reset_index().rename(columns={'consistent':'prop_consistent'})

    first_thesis = df.sort_values(['model','question_id','run']).groupby(['model','question_id']).first().reset_index()[['model','question_id','thesis']]

    # Majority / collapsed decisions per (model, question)
    # For almost all cells there is only 1 unique decision; where there isn't, we mark it.
    def collapse_decisions(group):
        vals = group['decision'].tolist()
        uniq = sorted(set(vals))
        if len(uniq) == 1:
            return pd.Series({
                'decision_collapsed': uniq[0],
                'unanimous': True
            })
        else:
            # pick the most frequent as the "collapsed" one
            counts = group['decision'].value_counts()
            maj = counts.idxmax()
            return pd.Series({
                'decision_collapsed': maj,
                'unanimous': False
            })

    collapsed = (
        df.groupby(['question_id', 'model'])
          .apply(collapse_decisions)
          .reset_index()
    )

    # pivot to questions x models
    collapsed_wide = collapsed.pivot(
        index='question_id',
        columns='model',
        values='decision_collapsed'
    ).sort_index()

    # also pivot unanimity flags
    unanimity_wide = collapsed.pivot(
        index='question_id',
        columns='model',
        values='unanimous'
    ).sort_index()

    # Per-question agreement across models
    decisions_per_model = (
        df.groupby(['question_id','model'])['decision']
          .apply(lambda s: ''.join(sorted(set(s))))
          .reset_index()
    )

    decisions_pivot = decisions_per_model.pivot(
        index='question_id',
        columns='model',
        values='decision'
    )

    # Preserve the order of models as they appear in the pivot columns
    model_order = list(decisions_pivot.columns)

    agree_flags = []
    values_list = []

    for _, row in decisions_pivot.iterrows():
        # row is indexed by model; we want decisions in the same model order
        vals = [row[m] for m in model_order]
        # normalize missing to ''
        vals = [v if isinstance(v, str) else '' for v in vals]
        non_empty = [v for v in vals if v != '']
        uniq = sorted(set(non_empty))
        if len(uniq) == 1 and len(non_empty) > 0:
            agree_flags.append(True)
        else:
            agree_flags.append(False)
        values_list.append(vals)

    agreement_df = (
        pd.DataFrame({
            'question_id': decisions_pivot.index,
            'agree': agree_flags,
            'value': values_list,
        })
        .reset_index(drop=True)
        .sort_values('question_id')
    )

    # Save outputs
    counts.to_csv(os.path.join(OUT_DIR, 'decision_counts_by_model.csv'))
    wide.reset_index().to_csv(os.path.join(OUT_DIR, 'per_question_decisions_wide.csv'), index=False)
    agreement_df.to_csv(os.path.join(OUT_DIR, 'agreement_by_question.csv'), index=False)
    conf_stats.to_csv(os.path.join(OUT_DIR, 'conf_stats_by_model_question.csv'), index=False)
    conf_pivot_filled.to_csv(os.path.join(OUT_DIR, 'conf_mean_by_question_model.csv'))
    avg_conf_model.to_csv(os.path.join(OUT_DIR, 'avg_conf_by_model.csv'))
    consistency.to_csv(os.path.join(OUT_DIR, 'consistency_by_model_question.csv'), index=False)
    first_thesis.to_csv(os.path.join(OUT_DIR, 'first_thesis_samples.csv'), index=False)
    collapsed_wide.to_csv(os.path.join(OUT_DIR, 'majority_decisions_wide.csv'))
    unanimity_wide.to_csv(os.path.join(OUT_DIR, 'unanimity_wide.csv'))

    report_lines = []
    report_lines.append("Experiment detailed analysis report")
    report_lines.append("Generated: %s UTC" % datetime.utcnow().isoformat())
    report_lines.append("")
    report_lines.append("1) Basic decision counts per model (columns: a, b, c, total):")
    report_lines.append(counts.fillna(0).to_string())
    report_lines.append("")
    report_lines.append("2) Any 'c' (decline) responses across models? %s (total c responses = %d)" % ("Yes" if 'c' in counts.columns and counts['c'].sum()>0 else "No", int(counts.get('c', pd.Series(dtype=int)).sum() if 'c' in counts.columns else 0)))
    report_lines.append("")
    report_lines.append("3) Per-question agreement across models (agree=True means all models gave the same unique decision):")
    report_lines.append(f"Model order in 'value' column: {', '.join(model_order)}")
    report_lines.append(agreement_df.to_string(index=False))
    report_lines.append("")
    report_lines.append("4) Consistency across runs for each model (proportion of question_ids with identical decisions across runs):")
    report_lines.append(consistency_summary.to_string(index=False))
    report_lines.append("")
    report_lines.append("5) Average confidence per model:")
    report_lines.append(avg_conf_model.to_string(index=False))
    report_lines.append("")
    report_lines.append("6) Per-model per-question mean confidence (FULL table):")
    # include the pivoted full table in the report text
    report_lines.append(conf_pivot_filled.to_string())
    report_lines.append("")
    report_lines.append("6b) Questions ordered by mean confidence:")
    low_conf = conf_stats.sort_values('mean_confidence')
    report_lines.append(low_conf.to_string(index=False))
    report_lines.append("")
    # --- Write to report ---
    report_lines.append("\n7a) Pairwise model agreement on majority decisions (proportion of statements):\n")
    report_lines.append(pairwise_df[['model_i','model_j','n_compared','n_agree','agree_rate']].to_string(index=False))

    report_lines.append("\n\n7b) Agreement heat-matrix (rows/cols are models; 1.00 = perfect agreement):\n")
    # format matrix nicely
    matrix_fmt = matrix.applymap(lambda x: f"{x:0.2f}" if pd.notna(x) else "–")
    report_lines.append(matrix_fmt.to_string())
    report_lines.append("")
    report_lines.append("8) Sample of first textual theses per model/question (first 200 chars):")
    sample_texts = first_thesis.copy()
    sample_texts['thesis_short'] = sample_texts['thesis'].fillna('').astype(str).str.replace('\n',' ').str.slice(0,200)
    report_lines.append(sample_texts[['model','question_id','thesis_short']].to_string(index=False))
    report_lines.append("")
    report_lines.append("Files written to %s" % os.path.abspath(OUT_DIR))
    report = "\n".join(report_lines)
    with open(os.path.join(OUT_DIR,'analysis_report.txt'),'w',encoding='utf-8') as f:
        f.write(report)
    print(report)
    print("\nSaved CSV outputs to:", OUT_DIR)
    # also write short json summary
    summary = {
        'n_questions': int(len(wide)),
        'agree_questions': agreement_df[agreement_df['agree']==True]['question_id'].tolist(),
        'disagree_questions': agreement_df[agreement_df['agree']==False]['question_id'].tolist(),
        'counts_by_model': counts.to_dict()
    }
    with open(os.path.join(OUT_DIR,'short_summary.json'),'w',encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

if __name__ == '__main__':
    main()
