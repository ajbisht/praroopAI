"""Unified LLM client with call logging and timing."""
from __future__ import annotations
import json, re, time
from typing import Any
import httpx
from backend.config import settings
from backend.logging_setup import get_logger
from .providers import PROVIDERS, LLMError

log = get_logger("llm")
STATS = {"calls": 0, "errors": 0, "total_seconds": 0.0}
available_providers = lambda: list(PROVIDERS.keys())


def health() -> dict[str, Any]:
    p = settings.provider
    info: dict[str, Any] = {"provider": p, "model": settings.model, "ok": False,
                            "detail": "", "stats": dict(STATS)}
    if p not in PROVIDERS:
        info["detail"] = f"Unknown provider '{p}'"; return info
    try:
        if p == "ollama":
            r = httpx.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags", timeout=3)
            info["ok"] = r.status_code == 200
            if info["ok"]:
                names = [m.get("name","") for m in r.json().get("models", [])]
                info["detail"] = "Ollama reachable"; info["installed_models"] = names
                if names and not any(settings.model.split(":")[0] in n for n in names):
                    info["ok"] = False
                    info["detail"] = (f"Model '{settings.model}' not found in Ollama. "
                                      f"Run: ollama pull {settings.model}")
                    log.warning(info["detail"])
            else: info["detail"] = "Ollama not reachable"
        elif p == "anthropic":
            info["ok"] = bool(settings.anthropic_api_key)
            info["detail"] = "key set" if info["ok"] else "ANTHROPIC_API_KEY missing"
        elif p == "openai":
            info["ok"] = bool(settings.openai_api_key)
            info["detail"] = "key set" if info["ok"] else "OPENAI_API_KEY missing"
        elif p == "openrouter":
            info["ok"] = bool(settings.openrouter_api_key)
            info["detail"] = "key set" if info["ok"] else "OPENROUTER_API_KEY missing"
        else:
            info["ok"] = True; info["detail"] = "configured"
    except Exception as e:
        info["detail"] = str(e); log.warning("health check failed: %s", e)
    return info


def chat(user: str, system: str = "", label: str = "llm", **kw) -> str:
    p = settings.provider
    if p not in PROVIDERS:
        raise LLMError(f"Unknown LLM_PROVIDER '{p}'. Choose: {', '.join(PROVIDERS)}")
    msgs = ([{"role":"system","content":system}] if system else []) + [{"role":"user","content":user}]
    log.info("-> %s | %s/%s | prompt %d chars", label, p, settings.model, len(user))
    log.trace("--- %s SYSTEM ---\n%s", label, system)
    log.trace("--- %s USER ---\n%s", label, user)
    t0 = time.monotonic(); STATS["calls"] += 1
    try:
        out = PROVIDERS[p](msgs, **kw).strip()
    except httpx.TimeoutException:
        STATS["errors"] += 1
        log.error("<- %s TIMEOUT after %.1fs (LLM_REQUEST_TIMEOUT=%s)",
                  label, time.monotonic()-t0, settings.timeout)
        raise
    except Exception as e:
        STATS["errors"] += 1
        log.error("<- %s FAILED after %.1fs: %s", label, time.monotonic()-t0, e); raise
    dt = time.monotonic()-t0; STATS["total_seconds"] += dt
    log.info("<- %s | %.1fs | %d chars", label, dt, len(out))
    log.debug("   preview: %s", out[:160].replace("\n"," ") + ("…" if len(out)>160 else ""))
    log.trace("--- %s RESPONSE ---\n%s", label, out)
    return out


def chat_json(user: str, system: str = "", label: str = "llm", **kw) -> Any:
    raw = chat(user, system=system, label=label, **kw)
    try: return _extract_json(raw)
    except LLMError:
        log.warning("%s returned unparseable JSON (%d chars)", label, len(raw)); raise


def _extract_json(text: str) -> Any:
    t = re.sub(r"```$", "", re.sub(r"^```(json)?", "", text.strip()).strip()).strip()
    try: return json.loads(t)
    except Exception: pass
    m = re.search(r"(\{.*\}|\[.*\])", t, re.DOTALL)
    if m:
        try: return json.loads(m.group(1))
        except Exception: pass
    raise LLMError(f"Could not parse JSON from model output:\n{t[:300]}")
