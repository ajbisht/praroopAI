"""Central configuration from .env."""
from __future__ import annotations
import os
from pathlib import Path
from dataclasses import dataclass

ROOT = Path(__file__).resolve().parents[1]


def _load():
    env = ROOT / ".env"
    if not env.exists(): return
    for line in env.read_bytes().decode("utf-8-sig", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.split(" #")[0].strip().strip('"').strip("'"))


_load()
_g = lambda k, d="": os.environ.get(k, d)
def _i(k, d):
    try: return int(_g(k, str(d)) or d)
    except ValueError: return d
def _f(k, d):
    try: return float(_g(k, str(d)) or d)
    except ValueError: return d


@dataclass
class Settings:
    log_level: str = _g("LOG_LEVEL", "INFO").upper()
    provider: str = _g("LLM_PROVIDER", "ollama").lower()
    model: str = _g("LLM_MODEL", "qwen2.5:7b")
    temperature: float = _f("LLM_TEMPERATURE", 0.2)
    max_tokens: int = _i("LLM_MAX_TOKENS", 1600)
    timeout: float = _f("LLM_REQUEST_TIMEOUT", 120)
    section_retries: int = _i("SECTION_RETRIES", 2)
    min_section_chars: int = _i("MIN_SECTION_CHARS", 180)
    max_review_loops: int = _i("MAX_REVIEW_LOOPS", 3)
    ollama_base_url: str = _g("OLLAMA_BASE_URL", "http://localhost:11434")
    openai_api_key: str = _g("OPENAI_API_KEY")
    openai_base_url: str = _g("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openrouter_api_key: str = _g("OPENROUTER_API_KEY")
    openrouter_base_url: str = _g("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    anthropic_api_key: str = _g("ANTHROPIC_API_KEY")
    anthropic_base_url: str = _g("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    anthropic_version: str = _g("ANTHROPIC_VERSION", "2023-06-01")
    compat_api_key: str = _g("OPENAI_COMPATIBLE_API_KEY")
    compat_base_url: str = _g("OPENAI_COMPATIBLE_BASE_URL", "http://localhost:8001/v1")
    port: int = _i("PRAROOP_PORT", 8000)
    draft_concurrency: int = _i("DRAFT_CONCURRENCY", 3)


settings = Settings()
