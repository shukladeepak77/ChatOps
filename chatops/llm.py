import json
import urllib.request
import urllib.error

from .config import load_config

_DEFAULT_MODELS = {
    "ollama": "llama3.2",
    "groq":   "llama-3.1-70b-versatile",
    "claude": "claude-haiku-4-5-20251001",
}

_VALID_PROVIDERS = ("none", "ollama", "groq", "claude")


def is_configured() -> bool:
    cfg = load_config()
    provider = cfg.get("llm_provider", "none").lower()
    if provider == "none":
        return False
    if provider in ("groq", "claude") and not cfg.get("llm_api_key", "").strip():
        return False
    return True


def ask(prompt: str, system: str = "You are a DevOps assistant. Be concise and technical.") -> str:
    cfg = load_config()
    provider = cfg.get("llm_provider", "none").lower()
    model = cfg.get("llm_model", "").strip() or _DEFAULT_MODELS.get(provider, "")

    if provider == "none":
        return ""
    if provider == "ollama":
        return _ask_ollama(prompt, system, model, cfg.get("ollama_url", "http://localhost:11434"))
    if provider == "groq":
        return _ask_openai_compat(
            prompt, system, model,
            base_url="https://api.groq.com/openai/v1",
            api_key=cfg.get("llm_api_key", ""),
        )
    if provider == "claude":
        return _ask_claude(prompt, system, model, cfg.get("llm_api_key", ""))
    return f"[Unknown LLM provider: {provider}]"


def _ask_ollama(prompt: str, system: str, model: str, base_url: str) -> str:
    payload = {
        "model":  model,
        "prompt": f"{system}\n\n{prompt}" if system else prompt,
        "stream": False,
    }
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{base_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read()).get("response", "").strip()
    except urllib.error.URLError as e:
        return f"[Ollama unreachable: {e.reason}]"
    except Exception as e:
        return f"[Ollama error: {e}]"


def _ask_openai_compat(prompt: str, system: str, model: str, base_url: str, api_key: str) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {"model": model, "messages": messages, "max_tokens": 400}
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        return f"[Groq HTTP {e.code}: {e.reason}]"
    except Exception as e:
        return f"[Groq error: {e}]"


def _ask_claude(prompt: str, system: str, model: str, api_key: str) -> str:
    payload = {
        "model":      model,
        "max_tokens": 400,
        "messages":   [{"role": "user", "content": prompt}],
    }
    if system:
        payload["system"] = system
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=data,
            headers={
                "Content-Type":      "application/json",
                "x-api-key":         api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())["content"][0]["text"].strip()
    except urllib.error.HTTPError as e:
        return f"[Claude HTTP {e.code}: {e.reason}]"
    except Exception as e:
        return f"[Claude error: {e}]"
