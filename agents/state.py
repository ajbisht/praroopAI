"""Shared graph state. `trace` uses an additive reducer so nodes append steps."""
from __future__ import annotations
import operator
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict, total=False):
    request: str
    raw_input: dict[str, Any]
    brief: dict[str, Any]
    derived: dict[str, Any]
    sections: dict[str, Any]
    findings: list[dict[str, Any]]
    scorecard: dict[str, Any]
    loop_count: int
    trace: Annotated[list[dict[str, Any]], operator.add]
