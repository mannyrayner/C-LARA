
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
import os, sys, json, csv, time, argparse, hashlib, random, datetime, pathlib, base64, pprint
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

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

# ---------- run a single task ----------

def run_single_task(task, prompt_template, system_prompt, timeout, dry_run=False):
    mq = task["model"]
    q = task["question"]
    r = task["run_idx"]

    claim_text = q["claim"]

    # 1) build prompt from template + question
    user_prompt = prompt_template.format(claim_text=claim_text)

    # 2) call provider
    if dry_run:
        parsed_response = simulate_response(mq["name"], claim_text)
        usage = {}
        
    else:
        content, usage = call_model_provider(mq["provider"], mq["chat_url"], mq["api_key"], mq["model"], system_prompt, user_prompt, timeout)
        # Try to parse model JSON; if it sent text, attempt to extract JSON substring
        try:
            parsed_response = json.loads(content)
        except Exception:
            # crude extraction
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                parsed_response = json.loads(content[start:end+1])
            else:
                parsed_response = {"decision":"", "thesis":"", "argument":content, "key_evidence":[], "citations":[], "counterpoints":[], "rebuttals":[], "confidence":""}

    # 3) normalise 
    out = {
        "ts": datetime.datetime.utcnow().isoformat(),
        "model": mq["name"],
        "provider": mq["provider"],
        "question_id": q["id"],
        "topic": q["topic"],
        "claim": claim_text,
        "run": r,
        "parsed_response": parsed_response,
        "usage": usage
    }

    return out

def call_model_provider(provider: str, chat_url: str, api_key: str, model: str, system_prompt: str, user_prompt: str, timeout: int=60) -> str:
    try:
        if provider == "openai":
            out = call_openai(chat_url, api_key, model, system_prompt, user_prompt, timeout=timeout)
        elif provider == "deepseek":
            out = call_deepseek(chat_url, api_key, model, system_prompt, user_prompt, timeout=timeout)
        elif provider == "anthropic":
            out = call_anthropic(chat_url, api_key, model, system_prompt, user_prompt, timeout=timeout)
        elif provider == "xai":
            out = call_openai(chat_url, api_key, model, system_prompt, user_prompt, timeout=timeout)
        elif provider == "google":
            out = call_gemini(chat_url, api_key, model, system_prompt, user_prompt, timeout=timeout)
        else:
            raise Exception(f"[ERROR] Unknown provider: {provider}")
        return out
    except Exception as e:
        print(f"[ERROR] (provider): {e}")

def compute_cost_for_usage(model_cfg: dict, usage: dict) -> float:
    """
    Map provider-specific usage fields to the generic pricing fields in the model config.
    Returns a dollar float.
    """
    if not usage:
        return 0.0
    pricing = model_cfg.get("pricing") or {}
    cost = 0.0

    # OpenAI / xAI / deepseek style
    # openai/xai give: prompt_tokens, completion_tokens, total_tokens
    # deepseek adds prompt_cache_hit_tokens / prompt_cache_miss_tokens
    if "prompt_tokens" in usage or "completion_tokens" in usage:
        prompt = usage.get("prompt_tokens", 0)
        completion = usage.get("completion_tokens", 0)
        # if there is cache info and you want to bill only cache *misses*, do that here:
        miss = usage.get("prompt_cache_miss_tokens", 0)
        # choose one of these strategies:

        # simplest: bill on prompt_tokens as-is
        billable_prompt = prompt

        # compute
        cost += (billable_prompt / 1000.0) * pricing.get("input_per_1k", 0.0)
        cost += (completion / 1000.0) * pricing.get("output_per_1k", 0.0)
        return cost

    # Anthropic style
    if "input_tokens" in usage or "output_tokens" in usage:
        inp = usage.get("input_tokens", 0)
        out = usage.get("output_tokens", 0)
        cost += (inp / 1000.0) * pricing.get("input_per_1k", 0.0)
        cost += (out / 1000.0) * pricing.get("output_per_1k", 0.0)
        return cost

    # Google Gemini style
    # usageMetadata: promptTokenCount, candidatesTokenCount, totalTokenCount, thoughtsTokenCount
    if "promptTokenCount" in usage or "candidatesTokenCount" in usage:
        prompt = usage.get("promptTokenCount", 0)
        out = usage.get("candidatesTokenCount", 0)
        thoughts = usage.get("thoughtsTokenCount", 0)
        cost += (prompt / 1000.0) * pricing.get("input_per_1k", 0.0)
        cost += (out / 1000.0) * pricing.get("output_per_1k", 0.0)
        cost += (thoughts / 1000.0) * pricing.get("thoughts_per_1k", 0.0)
        return cost

    # fallback: nothing billable
    return 0.0

# ---------- provider-specific callers ----------

def call_openai(chat_url: str, api_key: str, model: str, system_prompt: str, user_prompt: str, timeout: int=60) -> str:
    if requests is None:
        raise RuntimeError("The 'requests' package is required to call APIs. Install it with 'pip install requests'.")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}]    }
    resp = requests.post(chat_url, headers=headers, json=payload, timeout=timeout)
    # DEBUG: print status and body to help diagnose 400/401/403
    print("[DEBUG] OpenAI request -> status:", resp.status_code)
    try:
        # try to pretty-print JSON error if present
        print("[DEBUG] OpenAI response body:", resp.json())
    except Exception:
        print("[DEBUG] OpenAI response text:", resp.text[:2000])
    resp.raise_for_status()
    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return content, usage
    except Exception as e:
        raise RuntimeError(f"Unexpected API response structure: {data}") from e
    
def call_deepseek(chat_url: str, api_key: str, model: str, system_prompt: str, user_prompt: str, timeout: int=60) -> str:
    # DeepSeek is OpenAI-compatible in many SDKs; keep separate in case of differences.
    return call_openai(chat_url, api_key, model, system_prompt, user_prompt, timeout)

def call_anthropic(chat_url: str, api_key: str, model: str, system_prompt: str, user_prompt: str, timeout: int = 60) -> str:
    """
    Anthropic messages endpoint.
    We send system + user as two separate messages; we ask for a single text output.
    """
    if requests is None:
        raise RuntimeError("The 'requests' package is required to call APIs. Install it with 'pip install requests'.")
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 2048,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_prompt},
        ],
    }
    resp = requests.post(chat_url, headers=headers, json=payload, timeout=timeout)
    print("[DEBUG] Anthropic request -> status:", resp.status_code)
    try:
        print("[DEBUG] Anthropic response body:", resp.json())
    except Exception:
        print("[DEBUG] Anthropic response text:", resp.text[:2000])
    resp.raise_for_status()
    data = resp.json()
    # Anthropic returns content as a list of blocks
    try:
        blocks = data.get("content", [])
        text_parts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
        usage = data.get("usage", {})
        return "\n".join(text_parts).strip(), usage
    except Exception as e:
        raise RuntimeError(f"Unexpected Anthropic response structure: {data}") from e


def call_gemini(chat_url: str, api_key: str, model: str, system_prompt: str, user_prompt: str, timeout: int = 60) -> str:
    """
    Google Generative Language API (Gemini) - basic REST call.
    We'll concatenate system + user into one prompt to preserve behaviour.
    """
    if requests is None:
        raise RuntimeError("The 'requests' package is required to call APIs. Install it with 'pip install requests'.")
    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    url = f"{chat_url}?key={api_key}"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": full_prompt}],
            }
        ],
        # keep it simple; if you need temperature/topP, add here
    }
    resp = requests.post(url, json=payload, timeout=timeout)
    print("[DEBUG] Gemini request -> status:", resp.status_code)
    try:
        print("[DEBUG] Gemini response body:", resp.json())
    except Exception:
        print("[DEBUG] Gemini response text:", resp.text[:2000])
    resp.raise_for_status()
    data = resp.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        return text, usage
    except Exception as e:
        raise RuntimeError(f"Unexpected Gemini response structure: {data}") from e

def parse_models(models_cfg: Dict[str, Any]):
    """
    models.yaml example:
    - name: gpt5
      provider: openai
      model: gpt-5
      chat_url: https://api.openai.com/v1/chat/completions
      env_key: OPENAI_API_KEY

    - name: deepseek
      provider: deepseek
      model: deepseek-chat
      chat_url: https://api.deepseek.com/v1/chat/completions
      env_key: DEEPSEEK_API_KEY
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
            "pricing": m["pricing"],
        })
    return models

def test_providers(models_cfg: List[Dict[str, Any]], timeout: int = 60):
    """
    Quick connectivity test: call each model once with a trivial prompt.
    """
    system_prompt = "You are a helpful assistant."
    user_prompt = "Say hello and identify yourself in one sentence."
    for mq in models_cfg:
        if not mq["api_key"]:
            print(f"[SKIP] {mq['name']} ({mq['provider']}) – no API key in env.")
            continue
        print(f"[TEST] Calling {mq['name']} ({mq['provider']}) ...")
        try:
            out = call_model_provider(mq["provider"], mq["chat_url"], mq["api_key"], mq["model"], system_prompt, user_prompt, timeout)
            print(f"[OK] {mq['name']} -> {out[:200]!r}")
        except Exception as e:
            print(f"[ERROR] {mq['name']} ({mq['provider']}): {e}")

def main():
    start_time = time.time()
    provider_usage = {}
    provider_costs = {}
    
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True, help="Path to models.yaml")
    ap.add_argument("--questions", required=False, help="Path to questions.yaml")
    ap.add_argument("--prompt", default="prompt_template.txt", help="Prompt template path")
    ap.add_argument("--runs", type=int, default=3, help="Repeat count per (model, question)")
    ap.add_argument("--timeout", type=int, default=3000, help="Read timeout for API calls (seconds)")
    ap.add_argument("--out", required=False, help="Output directory")
    ap.add_argument("--workers", type=int, default=5, help="Max parallel API calls")
    ap.add_argument("--dry-run", action="store_true", help="Do not call APIs; simulate outputs deterministically")
    ap.add_argument("--test-providers", action="store_true", help="Call each provider once with a tiny prompt and exit")
    args = ap.parse_args()

    models_cfg_raw = load_yaml(args.models)
    # populate api_key from environment variables specified by env_key
    models_cfg = parse_models(models_cfg_raw)
    model_cfg_by_name = {m["name"]: m for m in models_cfg}

    if args.test_providers:
        test_providers(models_cfg, timeout=args.timeout)
        return
    
    ensure_dir(args.out)
    questions = load_yaml(args.questions)
    system_prompt = """You are an evidence-focused assistant. You do not hedge unnecessarily, 
but you disclose uncertainty honestly. Your goal is to evaluate claims using publicly availableevidence, citing sources precisely."""
    prompt_template = read_file(args.prompt)

    max_workers = getattr(args, "workers", 5)  
    
    # Outputs
    jsonl_path = os.path.join(args.out, "raw.jsonl")
    csv_path = os.path.join(args.out, "summary.csv")
    with open(jsonl_path, "w", encoding="utf-8") as jf, open(csv_path, "w", newline="", encoding="utf-8") as cf:
        cw = csv.writer(cf)
        cw.writerow(["ts","model","provider","question_id","topic","claim","run","decision","confidence","thesis"])

        tasks = []
        for mq in models_cfg:
            if not mq["api_key"]:
                print(f"[SKIP] {mq['name']} ({mq['provider']}) – no API key in env.")
                continue
            for q in questions: 
                for run_idx in range(args.runs):
                    tasks.append({
                        "model": mq,
                        "question": q,
                        "run_idx": run_idx
                    })

        #pprint.pprint(tasks)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {}
            for t in tasks:
                fut = executor.submit(
                    run_single_task,
                    t,
                    prompt_template,
                    system_prompt,
                    args.timeout,
                    args.dry_run
                )
                future_to_task[fut] = t

            for fut in as_completed(future_to_task):
                task = future_to_task[fut]
                record = fut.result()
                parsed_response = record["parsed_response"]

                usage = record.get("usage", {}) or {}
                prov = record["provider"]
                if prov not in provider_usage:
                    provider_usage[prov] = {}
                # add whatever numeric fields we got
                for k, v in usage.items():
                    if isinstance(v, (int, float)):
                        provider_usage[prov][k] = provider_usage[prov].get(k, 0) + v

                # cost accumulation
                # we need the full model config to read pricing
                model_cfg = model_cfg_by_name[record["model"]]  # create this dict once after parsing
                call_cost = compute_cost_for_usage(model_cfg, usage)
                if prov not in provider_costs:
                    provider_costs[prov] = 0.0
                provider_costs[prov] += call_cost
                
                jf.write(json.dumps(record, ensure_ascii=False) + "\n")
                cw.writerow([record["ts"],
                             record["model"],
                             record["provider"],
                             record["question_id"],
                             record["topic"],
                             record["claim"],
                             record["run"],
                             parsed_response.get("decision","c"),
                             parsed_response.get("confidence","0"),
                             parsed_response.get("thesis","")])
                cf.flush()

    print(f"Done. Wrote:\n- {jsonl_path}\n- {csv_path}")
    elapsed = time.time() - start_time
    print(f"Total elapsed time: {elapsed:.1f}s")
    
    print("Usage totals by provider:")
    for prov, stats in provider_usage.items():
        pretty = ", ".join(f"{k}={v}" for k, v in stats.items())
        cost = provider_costs.get(prov, 0.0)
        print(f"  {prov}: {pretty}, cost=${cost:.4f}")

    total_cost = sum(provider_costs.values())
    print(f"Total cost: ${total_cost:.4f}")
    
if __name__ == "__main__":
    main()
