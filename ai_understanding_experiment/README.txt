
AI Understanding Experiment
===========================

Files created:
- questions.yaml
- prompt_template.txt
- run_experiment.py
- models_example.yaml

Quick start (dry run):
  python run_experiment.py --models models_example.yaml --questions questions.yaml --out results --dry-run --runs 2

Real run (requires API keys):
  export OPENAI_API_KEY=...   # for gpt5 (or any OpenAI-compatible model)
  export DEEPSEEK_API_KEY=...
  python run_experiment.py --models models_example.yaml --questions questions.yaml --out results --runs 3

Outputs:
- results/raw.jsonl  : raw per-call records (JSONL)
- results/summary.csv: table with decision, confidence, thesis

You can add or edit questions in questions.yaml and models in models_example.yaml.
