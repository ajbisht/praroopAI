"""
LangGraph wiring.

  intake -> derive -> draft -> compliance --(mandatory)--> reviewer --+
                                   |  ^                               |
                                   |  +-------------------------------+
                                   +--(clean)--> score -> END

If langgraph is installed a real StateGraph is used; otherwise an identical
fallback runner executes the same nodes in the same order.
"""
from __future__ import annotations
from typing import Any

from . import nodes
from .state import AgentState

try:
    from langgraph.graph import StateGraph, END
    _HAS_LANGGRAPH = True
except Exception:
    _HAS_LANGGRAPH = False


def build_graph():
    if not _HAS_LANGGRAPH:
        raise RuntimeError("langgraph is not installed")
    g = StateGraph(AgentState)
    g.add_node("intake", nodes.intake_node)
    g.add_node("derive", nodes.derive_node)
    g.add_node("draft", nodes.draft_node)
    g.add_node("compliance", nodes.compliance_node)
    g.add_node("reviewer", nodes.reviewer_node)
    g.add_node("score", nodes.score_node)
    g.set_entry_point("intake")
    g.add_edge("intake", "derive")
    g.add_edge("derive", "draft")
    g.add_edge("draft", "compliance")
    g.add_conditional_edges("compliance", nodes.route_after_compliance,
                            {"reviewer": "reviewer", "end": "score"})
    g.add_edge("reviewer", "compliance")
    g.add_edge("score", END)
    return g.compile()


_GRAPH = build_graph() if _HAS_LANGGRAPH else None
ENGINE = "LangGraph" if _HAS_LANGGRAPH else "fallback"


def _merge(state: dict[str, Any], update: dict[str, Any]) -> None:
    for k, v in update.items():
        if k == "trace":
            state["trace"] = state.get("trace", []) + v
        else:
            state[k] = v


def _finalize(state: dict[str, Any]) -> dict[str, Any]:
    for i, s in enumerate(state.get("trace", []), 1):
        s["n"] = i
    return {"brief": state.get("brief", {}), "derived": state.get("derived", {}),
            "sections": state.get("sections", {}), "findings": state.get("findings", []),
            "scorecard": state.get("scorecard", {}), "trace": state.get("trace", []),
            "engine": ENGINE}


def run_pipeline(request: str = "", raw_input: dict[str, Any] | None = None):
    initial = {"request": request or "", "raw_input": raw_input or {},
               "loop_count": 0, "trace": []}
    if _HAS_LANGGRAPH:
        return _finalize(_GRAPH.invoke(initial))
    state = dict(initial)
    _merge(state, nodes.intake_node(state))
    _merge(state, nodes.derive_node(state))
    _merge(state, nodes.draft_node(state))
    _merge(state, nodes.compliance_node(state))
    while nodes.route_after_compliance(state) == "reviewer":
        _merge(state, nodes.reviewer_node(state))
        _merge(state, nodes.compliance_node(state))
    _merge(state, nodes.score_node(state))
    return _finalize(state)


def stream_pipeline(request: str = "", raw_input: dict[str, Any] | None = None):
    """Yields {'type':'step'|'node'|'complete'} events as nodes fire."""
    initial = {"request": request or "", "raw_input": raw_input or {},
               "loop_count": 0, "trace": []}
    state: dict[str, Any] = {"trace": []}
    emitted = 0

    def flush():
        nonlocal emitted
        steps = state.get("trace", [])
        for s in steps[emitted:]:
            s.setdefault("n", emitted + 1)
            yield {"type": "step", "step": s}
            emitted += 1

    if _HAS_LANGGRAPH:
        for chunk in _GRAPH.stream(initial, stream_mode="updates"):
            for node_name, update in chunk.items():
                _merge(state, update)
                yield from flush()
                yield {"type": "node", "name": node_name}
    else:
        _merge(state, dict(initial))
        for fn, name in [(nodes.intake_node, "intake"), (nodes.derive_node, "derive"),
                         (nodes.draft_node, "draft"), (nodes.compliance_node, "compliance")]:
            _merge(state, fn(state))
            yield from flush()
            yield {"type": "node", "name": name}
        while nodes.route_after_compliance(state) == "reviewer":
            _merge(state, nodes.reviewer_node(state))
            yield from flush()
            yield {"type": "node", "name": "reviewer"}
            _merge(state, nodes.compliance_node(state))
            yield from flush()
            yield {"type": "node", "name": "compliance"}
        _merge(state, nodes.score_node(state))
        yield from flush()
        yield {"type": "node", "name": "score"}

    yield {"type": "complete", "result": _finalize(state)}
