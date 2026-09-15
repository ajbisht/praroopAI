"""Provider adapters — native REST via httpx, no vendor SDKs."""
from __future__ import annotations
import httpx

from backend.config import settings
from backend.logging_setup import get_logger

log = get_logger("llm.provider")


class LLMError(RuntimeError):
    pass


def _split_system(messages):
    system, rest = "", []
    for m in messages:
        if m["role"] == "system":
            system += m["content"] + "\n"
        else:
            rest.append(m)
    return system.strip(), rest


def call_ollama(messages, **kw) -> str:
    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    body = {"model": settings.model, "messages": messages, "stream": False,
            "options": {"temperature": kw.get("temperature", settings.temperature),
                        "num_predict": kw.get("max_tokens", settings.max_tokens)}}
    log.debug("POST %s model=%s timeout=%ss", url, settings.model, settings.timeout)
    r = httpx.post(url, json=body, timeout=settings.timeout)
    r.raise_for_status()
    data = r.json()
    # ollama reports token counts - very useful for spotting slow models
    if "eval_count" in data:
        log.debug("ollama tokens in=%s out=%s eval_ms=%s",
                  data.get("prompt_eval_count"), data.get("eval_count"),
                  round(data.get("eval_duration", 0) / 1e6))
    return data["message"]["content"]


def _openai_like(base_url, api_key, messages, **kw) -> str:
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    body = {"model": settings.model, "messages": messages,
            "temperature": kw.get("temperature", settings.temperature),
            "max_tokens": kw.get("max_tokens", settings.max_tokens)}
    log.debug("POST %s model=%s", url, settings.model)
    r = httpx.post(url, json=body, headers=headers, timeout=settings.timeout)
    r.raise_for_status()
    data = r.json()
    if "usage" in data:
        u = data["usage"]
        log.debug("tokens in=%s out=%s", u.get("prompt_tokens"), u.get("completion_tokens"))
    return data["choices"][0]["message"]["content"]


def call_openai(m, **kw):
    if not settings.openai_api_key:
        raise LLMError("OPENAI_API_KEY is empty in .env")
    return _openai_like(settings.openai_base_url, settings.openai_api_key, m, **kw)


def call_openrouter(m, **kw):
    if not settings.openrouter_api_key:
        raise LLMError("OPENROUTER_API_KEY is empty in .env")
    return _openai_like(settings.openrouter_base_url, settings.openrouter_api_key, m, **kw)


def call_compat(m, **kw):
    return _openai_like(settings.compat_base_url, settings.compat_api_key, m, **kw)


def call_anthropic(messages, **kw) -> str:
    if not settings.anthropic_api_key:
        raise LLMError("ANTHROPIC_API_KEY is empty in .env")
    system, rest = _split_system(messages)
    url = f"{settings.anthropic_base_url.rstrip('/')}/v1/messages"
    headers = {"x-api-key": settings.anthropic_api_key,
               "anthropic-version": settings.anthropic_version,
               "content-type": "application/json"}
    body = {"model": settings.model,
            "max_tokens": kw.get("max_tokens", settings.max_tokens),
            "temperature": kw.get("temperature", settings.temperature),
            "system": system, "messages": rest}
    log.debug("POST %s model=%s", url, settings.model)
    r = httpx.post(url, json=body, headers=headers, timeout=settings.timeout)
    r.raise_for_status()
    data = r.json()
    if "usage" in data:
        u = data["usage"]
        log.debug("tokens in=%s out=%s", u.get("input_tokens"), u.get("output_tokens"))
    return "".join(p.get("text", "") for p in data.get("content", []))


PROVIDERS = {"ollama": call_ollama, "openai": call_openai,
             "openrouter": call_openrouter, "anthropic": call_anthropic,
             "openai_compatible": call_compat}
