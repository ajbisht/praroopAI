"""Unified LLM client. The rest of the app calls only this."""
from __future__ import annotations
import json
import re
from typing import Any

import httpx

from backend.config import settings
from .providers import PROVIDERS, LLMError


def available_providers() -> list[str]:
    return list(PROVIDERS.keys())


def health() -> dict[str, Any]:
    prov = settings.provider
    info = {"provider": prov, "model": settings.model, "ok": False, "detail": ""}
    if prov not in PROVIDERS:
        info["detail"] = f"Unknown provider '{prov}'"
        return info
    try:
        if prov == "ollama":
            r = httpx.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags", timeout=3)
            info["ok"] = r.status_code == 200
            info["detail"] = "Ollama reachable" if info["ok"] else "Ollama not reachable"
        elif prov == "anthropic":
            info["ok"] = bool(settings.anthropic_api_key)
            info["detail"] = "key set" if info["ok"] else "ANTHROPIC_API_KEY missing"
        elif prov == "openai":
            info["ok"] = bool(settings.openai_api_key)
            info["detail"] = "key set" if info["ok"] else "OPENAI_API_KEY missing"
        elif prov == "openrouter":
            info["ok"] = bool(settings.openrouter_api_key)
            info["detail"] = "key set" if info["ok"] else "OPENROUTER_API_KEY missing"
        else:
            info["ok"] = True
            info["detail"] = "configured"
    except Exception as e:
        info["detail"] = str(e)
    return info


def chat(user: str, system: str = "", **kw) -> str:
    prov = settings.provider
    if prov not in PROVIDERS:
        raise LLMError(f"Unknown LLM_PROVIDER '{prov}'. Choose: {', '.join(PROVIDERS)}")
    msgs = ([{"role": "system", "content": system}] if system else []) + \
           [{"role": "user", "content": user}]
    return PROVIDERS[prov](msgs, **kw).strip()


def chat_json(user: str, system: str = "", **kw) -> Any:
    return _extract_json(chat(user, system=system, **kw))


def _extract_json(text: str) -> Any:
    t = text.strip()
    t = re.sub(r"^```(json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    try:
        return json.loads(t)
    except Exception:
        pass
    m = re.search(r"(\{.*\}|\[.*\])", t, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    raise LLMError(f"Could not parse JSON from model output:\n{t[:300]}")
