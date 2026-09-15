"""
Compliance Agent — the INDEPENDENT CRITIC.

It does NOT trust the drafting model. It builds a flat context from the
project and runs every rule-pack against it (pure deterministic code),
emitting evidence-backed findings. This is why compliance never hallucinates.
"""
from __future__ import annotations
from typing import Any

from backend.core.context import build_context
from backend.core.rule_engine import evaluate


def check(project: dict[str, Any]) -> list[dict[str, Any]]:
    ctx = build_context(project)
    doc_type = project.get("brief", {}).get("doc_type", "RFP")
    findings = evaluate(ctx, doc_type=doc_type)
    return findings
