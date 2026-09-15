"""
Intake Agent — turns a vague request into a structured Project Brief.

In a live system it asks the officer clarifying questions. For the API/demo
it accepts the answers directly and normalises them into a brief, filling
sensible defaults for anything missing.
"""
from __future__ import annotations
from typing import Any

# the questions the intake agent would ask (surfaced by the UI)
QUESTIONS = [
    {"key": "funding_source", "q": "What is the funding source?"},
    {"key": "storage", "q": "On-premise or cloud storage?"},
    {"key": "data_retention_days", "q": "Data retention period (days)?"},
    {"key": "warranty_months", "q": "Warranty / maintenance period (months)?"},
    {"key": "num_milestones", "q": "How many delivery milestones?"},
]


def build_brief(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalise raw officer input into a structured brief."""
    milestones = raw.get("milestones")
    if not milestones:
        n = int(raw.get("num_milestones", 3) or 3)
        # even-ish default split adding to 100
        base = 100 // n
        split = [base] * n
        split[-1] += 100 - sum(split)
        milestones = [
            {"name": f"Milestone {i+1}", "payment_pct": split[i],
             "has_penalty": False}
            for i in range(n)
        ]

    brief = {
        "doc_type": raw.get("doc_type", "RFP"),
        "title": raw.get("title", "Untitled Project"),
        "project_cost": float(raw.get("project_cost", 0) or 0),
        "duration_months": int(raw.get("duration_months", 0) or 0),
        "funding_source": raw.get("funding_source", "State Budget"),
        "storage": raw.get("storage", "on-premise"),
        "data_retention_days": int(raw.get("data_retention_days", 90) or 90),
        "warranty_months": int(raw.get("warranty_months", 0) or 0),
        "uptime_percent": float(raw.get("uptime_percent", 99.5) or 99.5),
        "grace_period_days": int(raw.get("grace_period_days", 7) or 7),
        "milestones": milestones,
    }
    return brief
