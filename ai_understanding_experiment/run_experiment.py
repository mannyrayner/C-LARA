
#!/usr/bin/env python3
"""
Run a small, repeatable experiment querying multiple LLMs about polarised claims.
- Reads questions.yaml
- Supports multiple model adapters (OpenAI-compatible, DeepSeek)
- Saves a CSV summary and JSONL raw responses
- Offers --dry-run to simulate outputs deterministically for pipeline testing

Usage:
  python run_experiment.py --models models.yaml --questions questions.yaml --runs 3 --out outdir
"""
import os, sys, json, csv, time, argparse, hashlib, random, datetime, pathlib, base64
from typing import Dict, Any, List

try:
    import requests  # type: ignore
except Exception:
    requests = None

def sha_seed(*parts: str) -> int:
    h = hashlib.sha256("::".join(parts).encode()).hexdigest()
    return int(h[:8], 16)

def load_yaml(path: str):
    import yaml  # lazy import
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def ensure_dir(path: str):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)

def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def simulate_response(model_name: str, claim: str) -> Dict[str, Any]:
    # Deterministic pseudo-output for --dry-run
    seed = sha_seed(model_name, claim)
    rng = random.Random(seed)
    decision = rng.choice(["a","b","a","b","a","b","c"])  # bias toward a/b
    conf = round(rng.uniform(0.55, 0.95), 2) if decision in ("a","b") else round(rng.uniform(0.3, 0.7), 2)
    thesis = ("The claim is true." if decision=="a" else ("The claim is false." if decision=="b" else "Declining to answer."))
    arg_pts = [f"Point {i}: synthetic justification." for i in range(1, rng.randint(4,7))]
    cites = [f"https://example.org/source/{rng.randint(100,999)}" for _ in range(rng.randint(2,4))]
    return {
        "decision": decision,
        "thesis": thesis,
        "argument": "\n".join(f"- {p}" for p in arg_pts),
        "key_evidence": [f"Source {i}" for i in range(1, len(cites)+1)],
        "citations": cites,
        "counterpoints": ["Strongest counterpoint (synthetic)"],
        "rebuttals": ["Brief rebuttal (synthetic)"],
        "confidence": conf,
        "notes": ""
    }

def call_openai(chat_url: str, api_key: str, model: str, system_prompt: str, user_prompt: str, temperature: float=0.2, timeout: int=60) -> str:
    if requests is None:
        raise RuntimeError("The 'requests' package is required to call APIs. Install it with 'pip install requests'.")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}],
        "temperature": temperature
    }
    resp = requests.post(chat_url, headers=headers, data=json.dumps(payload), timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    # OpenAI-style response parsing
    try:
        content = data["choices"][0]["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"Unexpected API response: {data}") from e
    return content

def call_deepseek(chat_url: str, api_key: str, model: str, system_prompt: str, user_prompt: str, temperature: float=0.2, timeout: int=60) -> str:
    # DeepSeek is OpenAI-compatible in many SDKs; keep separate in case of differences.
    return call_openai(chat_url, api_key, model, system_prompt, user_prompt, temperature, timeout)

def parse_models(models_cfg: Dict[str, Any]):
    """
    models.yaml example:
    - name: gpt5
      provider: openai
      model: gpt-5
      chat_url: https://api.openai.com/v1/chat/completions
      env_key: OPENAI_API_KEY
      temperature: 0.2

    - name: deepseek
      provider: deepseek
      model: deepseek-chat
      chat_url: https://api.deepseek.com/v1/chat/completions
      env_key: DEEPSEEK_API_KEY
      temperature: 0.2
    """
    models = []
    for m in models_cfg:
        env = os.environ.get(m.get("env_key",""))
        models.append({
            "name": m["name"],
            "provider": m["provider"],
            "model": m["model"],
            "chat_url": m["chat_url"],
            "api_key": env,
            "temperature": float(m.get("temperature", 0.2)),
        })
    return models

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True, help="Path to models.yaml")
    ap.add_argument("--questions", required=True, help="Path to questions.yaml")
    ap.add_argument("--prompt", default="prompt_template.txt", help="Prompt template path")
    ap.add_argument("--runs", type=int, default=3, help="Repeat count per (model, question)")
    ap.add_argument("--out", required=True, help="Output directory")
    ap.add_argument("--dry-run", action="store_true", help="Do not call APIs; simulate outputs deterministically")
    args = ap.parse_args()

    ensure_dir(args.out)
    models_cfg = load_yaml(args.models)
    questions = load_yaml(args.questions)
    system_prompt = "You are an evidence-focused assistant. Follow the user instruction carefully and return strict JSON."
    user_tmpl = read_file(args.prompt)

    # Outputs
    jsonl_path = os.path.join(args.out, "raw.jsonl")
    csv_path = os.path.join(args.out, "summary.csv")
    with open(jsonl_path, "w", encoding="utf-8") as jf, open(csv_path, "w", newline="", encoding="utf-8") as cf:
        cw = csv.writer(cf)
        cw.writerow(["ts","model","provider","question_id","topic","claim","run","decision","confidence","thesis"])

        for mq in models_cfg:
            if not args.dry_run and not mq["api_key"]:
                print(f"[WARN] Skipping model {mq['name']} (missing API key in env).")
                continue
            for q in questions:
                for r in range(1, args.runs+1):
                    claim_text = q["claim"]
                    user_prompt = user_tmpl.format(claim_text=claim_text)

                    if args.dry_run:
                        parsed = simulate_response(mq["name"], claim_text)
                    else:
                        if mq["provider"] == "openai":
                            content = call_openai(mq["chat_url"], mq["api_key"], mq["model"], system_prompt, user_prompt, mq["temperature"])
                        elif mq["provider"] == "deepseek":
                            content = call_deepseek(mq["chat_url"], mq["api_key"], mq["model"], system_prompt, user_prompt, mq["temperature"])
                        else:
                            raise ValueError(f"Unknown provider: {mq['provider']}")

                        # Try to parse model JSON; if it sent text, attempt to extract JSON substring
                        try:
                            parsed = json.loads(content)
                        except Exception:
                            # crude extraction
                            start = content.find("{")
                            end = content.rfind("}")
                            if start != -1 and end != -1 and end > start:
                                parsed = json.loads(content[start:end+1])
                            else:
                                parsed = {"decision":"", "thesis":"", "argument":content, "key_evidence":[], "citations":[], "counterpoints":[], "rebuttals":[], "confidence":""}

                    record = {
                        "ts": datetime.datetime.utcnow().isoformat(),
                        "model": mq["name"],
                        "provider": mq["provider"],
                        "question_id": q["id"],
                        "topic": q["topic"],
                        "claim": claim_text,
                        "run": r,
                        "response": parsed
                    }
                    jf.write(json.dumps(record, ensure_ascii=False) + "\n")

                    cw.writerow([record["ts"], record["model"], record["provider"], q["id"], q["topic"], claim_text, r, parsed.get("decision",""), parsed.get("confidence",""), parsed.get("thesis","")])
                    cf.flush()
                    time.sleep(0.1)

    print(f"Done. Wrote:\n- {jsonl_path}\n- {csv_path}")

if __name__ == "__main__":
    main()
