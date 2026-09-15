"""LangGraph wiring + threaded streaming so long nodes report live."""
from __future__ import annotations
import queue, threading, time
from typing import Any
from backend.logging_setup import get_logger
from . import nodes, progress
from .state import AgentState

log = get_logger("graph")
try:
    from langgraph.graph import StateGraph, END
    _HAS_LANGGRAPH = True
except Exception:
    _HAS_LANGGRAPH = False


def build_graph():
    if not _HAS_LANGGRAPH: raise RuntimeError("langgraph is not installed")
    g = StateGraph(AgentState)
    for n, fn in [("intake", nodes.intake_node), ("derive", nodes.derive_node),
                  ("draft", nodes.draft_node), ("compliance", nodes.compliance_node),
                  ("reviewer", nodes.reviewer_node), ("score", nodes.score_node)]:
        g.add_node(n, fn)
    g.set_entry_point("intake")
    g.add_edge("intake", "derive"); g.add_edge("derive", "draft")
    g.add_edge("draft", "compliance")
    g.add_conditional_edges("compliance", nodes.route_after_compliance,
                            {"reviewer": "reviewer", "end": "score"})
    g.add_edge("reviewer", "compliance"); g.add_edge("score", END)
    return g.compile()


_GRAPH = build_graph() if _HAS_LANGGRAPH else None
ENGINE = "LangGraph" if _HAS_LANGGRAPH else "fallback"
log.info("pipeline engine: %s", ENGINE)


def _merge(state, update):
    for k, v in update.items():
        if k == "trace": state["trace"] = state.get("trace", []) + v
        else: state[k] = v


def _finalize(state):
    for i, s in enumerate(state.get("trace", []), 1): s["n"] = i
    return {"brief": state.get("brief", {}), "derived": state.get("derived", {}),
            "sections": state.get("sections", {}), "findings": state.get("findings", []),
            "scorecard": state.get("scorecard", {}), "trace": state.get("trace", []),
            "engine": ENGINE}


def _run_sequential(state):
    _merge(state, nodes.intake_node(state)); _merge(state, nodes.derive_node(state))
    _merge(state, nodes.draft_node(state));  _merge(state, nodes.compliance_node(state))
    while nodes.route_after_compliance(state) == "reviewer":
        _merge(state, nodes.reviewer_node(state)); _merge(state, nodes.compliance_node(state))
    _merge(state, nodes.score_node(state)); return state


def run_pipeline(request: str = "", raw_input: dict[str, Any] | None = None):
    init = {"request": request or "", "raw_input": raw_input or {}, "loop_count": 0, "trace": []}
    t0 = time.monotonic(); log.info("=== pipeline start (engine=%s) ===", ENGINE)
    out = _finalize(_GRAPH.invoke(init)) if _HAS_LANGGRAPH else _finalize(_run_sequential(dict(init)))
    log.info("=== pipeline done in %.1fs ===", time.monotonic()-t0)
    return out


def stream_pipeline(request: str = "", raw_input: dict[str, Any] | None = None):
    """Yields step / node / progress / ping / complete / error events."""
    init = {"request": request or "", "raw_input": raw_input or {}, "loop_count": 0, "trace": []}
    q: "queue.Queue[dict[str, Any]]" = queue.Queue()
    state: dict[str, Any] = {"trace": []}
    emitted = 0; t0 = time.monotonic()

    def worker():
        progress.bind(q)
        try:
            log.info("=== pipeline start (engine=%s, streaming) ===", ENGINE)
            if _HAS_LANGGRAPH:
                for chunk in _GRAPH.stream(init, stream_mode="updates"):
                    for name, up in chunk.items():
                        q.put({"__node": name, "__update": up})
            else:
                s = dict(init)
                for fn, name in [(nodes.intake_node,"intake"), (nodes.derive_node,"derive"),
                                 (nodes.draft_node,"draft"), (nodes.compliance_node,"compliance")]:
                    up = fn(s); _merge(s, up); q.put({"__node": name, "__update": up})
                while nodes.route_after_compliance(s) == "reviewer":
                    up = nodes.reviewer_node(s); _merge(s, up); q.put({"__node":"reviewer","__update":up})
                    up = nodes.compliance_node(s); _merge(s, up); q.put({"__node":"compliance","__update":up})
                up = nodes.score_node(s); _merge(s, up); q.put({"__node":"score","__update":up})
        except Exception as e:
            log.exception("pipeline failed"); q.put({"__error": str(e)})
        finally:
            progress.bind(None); q.put({"__done": True})

    threading.Thread(target=worker, daemon=True).start()

    def flush():
        nonlocal emitted
        for s in state.get("trace", [])[emitted:]:
            s.setdefault("n", emitted+1); yield {"type":"step","step":s}; emitted += 1

    error = None
    while True:
        try: item = q.get(timeout=1.0)
        except queue.Empty:
            yield {"type":"ping","elapsed":round(time.monotonic()-t0,1)}; continue
        if item.get("__done"): break
        if "__error" in item: error = item["__error"]; continue
        if "__node" in item:
            _merge(state, item["__update"]); yield from flush()
            yield {"type":"node","name":item["__node"]}; continue
        yield item

    if error:
        yield {"type":"error","message":error}; return
    log.info("=== pipeline done in %.1fs (streaming) ===", time.monotonic()-t0)
    yield {"type":"complete","result":_finalize(state)}
