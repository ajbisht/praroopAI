"""
On-prem LLM client. Talks to Ollama / vLLM if reachable; otherwise it
signals unavailable so agents fall back to deterministic templates.

This keeps PraroopAI fully runnable with NO LLM (for demos / offline),
while using a real on-prem model when one is present.
"""
from __future__ import annotations
import os

try:
    import httpx
except Exception:  # pragma: no cover
    httpx = None

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
LLM_MODEL = os.environ.get("PRAROOP_MODEL", "qwen2.5:1.5b")


def is_available() -> bool:
    if httpx is None:
        return False
    try:
        r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=1.5)
        return r.status_code == 200
    except Exception:
        return False


def generate(prompt: str, system: str = "", timeout: float = 30.0) -> str | None:
    """Return the model's text, or None if the LLM is unavailable/errors."""
    if httpx is None:
        return None
    try:
        r = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": LLM_MODEL,
                "prompt": prompt,
                "system": system,
                "stream": False,
            },
            timeout=timeout,
        )
        if r.status_code == 200:
            return r.json().get("response", "").strip()
    except Exception:
        return None
    return None
