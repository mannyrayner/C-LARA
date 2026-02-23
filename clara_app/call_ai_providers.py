
#!/usr/bin/env python3
"""
Run a prompt against a specified model provider.
"""
import os, sys, json, csv, time, argparse, hashlib, random, datetime, pathlib, base64, pprint
import requests
from typing import Dict, Any, List

def call_model_provider(
    provider: str,
    chat_url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    timeout: int = 60,
    max_retries: int = 3,
    backoff_seconds: int = 5,
):
    """
    Dispatch to the appropriate provider-specific caller.

    Always returns a tuple (content, usage_dict), even on failure.
    On repeated failure, content is an empty string and usage is {}.
    """
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            if provider == "openai":
                return call_openai(chat_url, api_key, model, system_prompt, user_prompt, timeout)
            elif provider == "deepseek":
                return call_deepseek(chat_url, api_key, model, system_prompt, user_prompt, timeout)
            elif provider == "anthropic":
                return call_anthropic(chat_url, api_key, model, system_prompt, user_prompt, timeout)
            elif provider == "xai":
                # xAI is OpenAI-compatible
                return call_openai(chat_url, api_key, model, system_prompt, user_prompt, timeout)
            elif provider == "google":
                return call_gemini(chat_url, api_key, model, system_prompt, user_prompt, timeout)
            else:
                raise RuntimeError(f"[ERROR] Unknown provider: {provider}")
        except Exception as e:
            last_error = e
            print(f"[ERROR] {provider} attempt {attempt}/{max_retries}: {e}")
            if attempt < max_retries:
                # brief backoff before retrying
                time.sleep(backoff_seconds)
            else:
                print(f"[ERROR] {provider}: giving up after {max_retries} attempts.")
                # Fall through to return a safe default

    # If we get here, all retries failed
    # Return empty content and empty usage so callers can still proceed
    return "", {}


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




