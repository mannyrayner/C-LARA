AI UNDERSTANDING EXPERIMENT — README
===================================

Purpose
-------
This folder contains the lightweight exploratory experiment reported in:
"Do People Understand Anything? A Counterpoint to the Usual AI Critique".
The experiment probes how different LLM endpoints respond to polarised factual 
claims (support / reject / decline), and collects structured JSON outputs 
(decision, calibrated confidence, citations, short thesis, etc.). 
The pipeline is designed to be reproducible and
auditable.

Repository & paper
------------------
Main repo & experiment folder:
https://github.com/mannyrayner/C-LARA/tree/main/ai_understanding_experiment
(Manuscript draft & summary also archived with the project). :contentReference[oaicite:2]{index=2}

Quick-start summary (dry-run; no API keys)
-----------------------------------------
1) Create a Python 3.9+ virtual environment, then install dependencies:
   pip install pandas numpy requests pyyaml

2) Dry-run (deterministic synthetic responses; good for testing parsing/logging):
   python run_experiment.py --models models_example.yaml \
       --questions questions.yaml --out results --dry-run --runs 2

3) Inspect outputs:
   - results/raw.jsonl   (per-call full JSONL logs)
   - results/summary.csv (one row per call: decision, confidence, thesis)

Full run (requires API keys)
---------------------------
Set appropriate environment variables for configured endpoints (examples):
  export OPENAI_API_KEY=...   # OpenAI-style endpoint
  export DEEPSEEK_API_KEY=... # DeepSeek (if configured)

Then run:
  python run_experiment.py --models models_example.yaml \
      --questions questions.yaml --out full_results --runs 3

Files produced
--------------
- full_results/raw.jsonl
  Raw per-call JSON records with timestamps, model id, question id, run id,
  and the model's JSON output (verbatim). Use this to audit citations.

- full_results/summary.csv
  Compact CSV summary used by analysis scripts.

Files used
--------------

- run_experiment.py
  The code for running the experiment.

- prompt_template.txt
  The exact prompt template used for all models (strict JSON output required).
  This is reproduced in the paper for transparency.
  
- questions.yaml
  The questions to use.

- models_example.yaml
  The AI models to use.

- analysis_script.py
  Parses summary.csv, computes decision distributions, consistency statistics,
  per-model/per-question mean confidence, and writes a human-readable
  analysis_report.txt together with various .csv files.

- generate_latex_tables.py
  Converts the key analysis CSVs into LaTeX fragments (e.g., decision_dist.tex,
  conf-by-question.tex, theses_longtable.tex). These fragments are intended for
  inclusion via `\input{}` into the LaTeX manuscript to avoid transcription errors.

Reproducibility steps (from raw results -> LaTeX tables)
-------------------------------------------------------
1. Run experiment.
2. Run analysis:
   python analysis_script.py full_results/summary.csv full_results
3. Optionally generate LaTeX fragments:
   python generate_latex_tables.py full_results full_results_tex

Notes & troubleshooting
-----------------------
- Dependencies: Python 3.9+, pip packages: pandas, numpy, requests, pyyaml.
- Timeouts: Some endpoints can be slow; the runner supports a timeout parameter, currently set very high.
- JSON schema: Do not alter the output JSON schema in prompt_template.txt
  unless you also update the parser in run_experiment.py / analysis_script.py.

Contact & licensing
-------------------
Authors / maintainers: 
   Manny Rayner (human, mannyrayner@yahoo.com), 
   ChatGPT C-LARA-Instance (AI, chatgptclarainstance@proton.me).
Please cite the repository and the manuscript if you reuse this pipeline.
License: MIT

