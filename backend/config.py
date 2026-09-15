"""Central configuration. Loads .env once into a typed Settings object."""
from __future__ import annotations
import os
from pathlib import Path
from dataclasses import dataclass

ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    # tolerant decode: utf-8-sig strips a Notepad BOM; ignore stray bytes
    text = env.read_bytes().decode("utf-8-sig", errors="ignore")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        v = v.split(" #")[0].strip().strip('"').strip("'")
        os.environ.setdefault(k.strip(), v)


_load_dotenv()


def _g(k: str, d: str = "") -> str:
    return os.environ.get(k, d)


@dataclass
class Settings:
    provider: str = _g("LLM_PROVIDER", "ollama").lower()
    model: str = _g("LLM_MODEL", "qwen2.5:7b")
    temperature: float = float(_g("LLM_TEMPERATURE", "0.2") or 0.2)
    max_tokens: int = int(_g("LLM_MAX_TOKENS", "1600") or 1600)
    timeout: float = float(_g("LLM_REQUEST_TIMEOUT", "120") or 120)

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

    port: int = int(_g("PRAROOP_PORT", "8080") or 8080)


settings = Settings()
