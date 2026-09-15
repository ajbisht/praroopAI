"""
PraroopAI — FastAPI backend. Serves the officer UI and runs the pipeline.

Run:  uvicorn backend.app:app --reload --port 8080
Logs: set LOG_LEVEL=DEBUG (or TRACE) in .env to see every LLM call.
"""
from __future__ import annotations
import io
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.config import settings
from backend.logging_setup import setup_logging, get_logger

# configure logging before anything else imports a logger
_level = setup_logging(settings.log_level)
log = get_logger("app")

from backend.llm import client as llm                    # noqa: E402
from backend.core.rule_engine import load_packs          # noqa: E402
from backend.services.export_service import (            # noqa: E402
    export_docx, ExportBlocked)
from agents.graph import run_pipeline, stream_pipeline, ENGINE  # noqa: E402
from agents import doc_structure                          # noqa: E402

app = FastAPI(title="PraroopAI", version="1.0.0",
              description="AI DPR/RFP Drafting & Compliance Assistant")

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
STORE: dict[str, Any] = {}


class RunInput(BaseModel):
    request: str = ""
    doc_type: str = "RFP"
    title: str = ""
    project_cost: float = 0
    duration_months: int = 0
    funding_source: str = ""
    storage: str = "on-premise"
    data_retention_days: int = 90
    num_milestones: int = 3


@app.on_event("startup")
def _startup():
    h = llm.health()
    log.info("PraroopAI ready | engine=%s | log level=%s", ENGINE, _level)
    log.info("LLM: provider=%s model=%s ok=%s (%s)",
             h["provider"], h["model"], h["ok"], h["detail"])
    n_sections = len(doc_structure.keys_for("RFP"))
    log.info("A run makes ~%d-%d LLM calls (one per section). On a small local "
             "model expect 1-3 minutes.", n_sections + 2,
             n_sections * settings.section_retries + 4)
    if not h["ok"]:
        log.warning("LLM is not reachable/configured - the pipeline will fail. %s",
                    h["detail"])


# ── API ─────────────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status": "ok", "engine": ENGINE, "log_level": _level,
            "llm": llm.health(), "providers": llm.available_providers(),
            "tuning": {"section_retries": settings.section_retries,
                       "min_section_chars": settings.min_section_chars,
                       "max_review_loops": settings.max_review_loops,
                       "request_timeout": settings.timeout}}


@app.get("/api/rulepacks")
def rulepacks():
    return {"packs": [{"pack": p["pack"], "label": p["label"],
                       "version": p["version"], "authority": p["authority"],
                       "rule_count": len(p["rules"])} for p in load_packs()]}


@app.get("/api/structure/{doc_type}")
def structure(doc_type: str):
    return {"doc_type": doc_type.upper(),
            "sections": [{"key": k, "title": t}
                         for k, t, _ in doc_structure.sections_for(doc_type)]}


@app.post("/api/run")
def run(inp: RunInput):
    raw = inp.model_dump()
    request = raw.pop("request", "")
    try:
        result = run_pipeline(request=request, raw_input=raw)
    except Exception as e:
        log.exception("run failed")
        raise HTTPException(502, f"Pipeline error: {e}")
    STORE["last"] = result
    return result


@app.post("/api/run/stream")
def run_stream(inp: RunInput):
    """Server-Sent Events: live step / node / progress / complete events."""
    raw = inp.model_dump()
    request = raw.pop("request", "")

    def gen():
        try:
            for evt in stream_pipeline(request=request, raw_input=raw):
                if evt.get("type") == "complete":
                    STORE["last"] = evt["result"]
                yield f"data: {json.dumps(evt, default=str)}\n\n"
        except Exception as e:
            log.exception("stream failed")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no",
                                      "Connection": "keep-alive"})


@app.post("/api/export")
def export():
    result = STORE.get("last")
    if not result:
        raise HTTPException(400, "Run the pipeline first.")
    try:
        data = export_docx(result)
    except ExportBlocked as e:
        raise HTTPException(423, str(e))
    name = (result["brief"].get("doc_type") or "RFP").upper()
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument."
                   "wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="PraroopAI_{name}.docx"'})


# ── UI + icons ──────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def index():
    return (FRONTEND / "index.html").read_text(encoding="utf-8")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(FRONTEND / "assets" / "favicon.ico")


app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")
