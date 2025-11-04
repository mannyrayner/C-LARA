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
    if 'response' in df.columns:
        parsed = df['response'].apply(safe_parse)
        if 'decision' not in df.columns:
            df['decision'] = parsed.apply(lambda r: (r.get('decision') or '').strip() if isinstance(r, dict) else '')
        if 'confidence' not in df.columns:
            def parse_conf(x):
                try:
                    return float(x)
                except Exception:
                    return np.nan
            df['confidence'] = parsed.apply(lambda r: parse_conf(r.get('confidence') if isinstance(r, dict) else None))
        if 'thesis' not in df.columns:
            df['thesis'] = parsed.apply(lambda r: r.get('thesis') if isinstance(r, dict) else '')

    df['decision'] = df['decision'].fillna('').astype(str)

    def norm_decision(s):
        s = s.strip().lower()
        if s.startswith('a'):
            return 'a'
        if s.startswith('b'):
            return 'b'
        if s.startswith('c'):
            return 'c'
        return s

    df['decision_norm'] = df['decision'].apply(norm_decision)

    counts = df.groupby(['model','decision_norm']).size().unstack(fill_value=0)
    counts['total'] = counts.sum(axis=1)

    unique_decisions = df.groupby(['question_id','model'])['decision_norm'].agg(lambda s: ','.join(sorted(set(s)))).reset_index()
    wide = unique_decisions.pivot(index='question_id', columns='model', values='decision_norm').fillna('')

    def models_agree(row):
        vals = [v for v in row.tolist() if v!='']
        if len(vals)==0:
            return False, None
        indiv = []
        for v in vals:
            if ',' in v:
                return False, False
            indiv.append(v)
        if all(x==indiv[0] for x in indiv):
            return True, indiv[0]
        else:
            return False, indiv

    agreement = []
    for q, row in wide.iterrows():
        agree, val = models_agree(row)
        rec = {'question_id': q, 'agree': agree, 'value': val}
        for col in wide.columns:
            rec[col] = row[col]
        agreement.append(rec)
    agreement_df = pd.DataFrame(agreement)

    # Per-model per-question confidence stats (mean, std, n)
    conf_stats = df.groupby(['model','question_id'])['confidence'].agg(['mean','std','count']).reset_index().rename(columns={'mean':'mean_confidence','std':'std_confidence','count':'n'})
    avg_conf_model = df.groupby('model')['confidence'].agg(['mean','std','count']).reset_index().rename(columns={'mean':'mean_confidence','std':'std_confidence','count':'n'})

    # Pivot to full per-question x per-model mean_confidence table
    conf_pivot = conf_stats.pivot(index='question_id', columns='model', values='mean_confidence').sort_index()
    # fill NaN with empty for nicer CSV/readout
    conf_pivot_filled = conf_pivot.fillna('')

    # Consistency across runs for each model/question
    consistency = df.groupby(['model','question_id'])['decision_norm'].nunique().reset_index().rename(columns={'decision_norm':'unique_decisions'})
    consistency['consistent'] = consistency['unique_decisions']==1
    consistency_summary = consistency.groupby('model')['consistent'].mean().reset_index().rename(columns={'consistent':'prop_consistent'})

    first_thesis = df.sort_values(['model','question_id','run']).groupby(['model','question_id']).first().reset_index()[['model','question_id','thesis']]

    # Majority / collapsed decisions per (model, question)
    # For almost all cells there is only 1 unique decision; where there isn't, we mark it.
    def collapse_decisions(group):
        vals = group['decision_norm'].tolist()
        uniq = sorted(set(vals))
        if len(uniq) == 1:
            return pd.Series({
                'decision_collapsed': uniq[0],
                'unanimous': True
            })
        else:
            # pick the most frequent as the "collapsed" one
            counts = group['decision_norm'].value_counts()
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
    report_lines.append(agreement_df[['question_id','agree','value']].to_string(index=False))
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
    report_lines.append("7) Sample of first textual theses per model/question (first 200 chars):")
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
