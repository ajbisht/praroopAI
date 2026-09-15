"""
Reviewer Agent — resolves fixable findings, then hands the draft back to the
Compliance Agent for a re-check (the feedback loop). Findings that need a
human decision are escalated to the officer instead of being auto-fixed.
"""
from __future__ import annotations
from typing import Any

from backend.core import templates

# which rule ids the reviewer knows how to auto-fix
AUTO_FIXABLE = {
    "PEN-002": "add_milestone_penalties",
    "SEC-001": "add_data_security",
    "SEC-002": "add_data_security",
    "SLA-002": "add_sla",
    "SLA-003": "add_sla",
    "GFR-004": "add_evaluation",
}


def review(project: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    brief = project["brief"]
    derived = project["derived"]
    sections = project["sections"]
    fixed, escalated = [], []

    for f in findings:
        action = AUTO_FIXABLE.get(f["rule_id"])
        if not action:
            escalated.append(f)
            continue

        if action == "add_milestone_penalties":
            for m in derived.get("milestones", []):
                m["has_penalty"] = True
            sections["penalty"] = {
                "title": "7. Penalty & Liquidated Damages",
                "body": templates.penalty(brief, derived, with_milestone_penalty=True),
            }
        elif action == "add_data_security":
            sections["data_security"] = {
                "title": "6. Data Security",
                "body": templates.data_security(brief, derived),
            }
        elif action == "add_sla":
            sections["sla"] = {
                "title": "5. Service Levels (SLA)",
                "body": templates.sla(brief, derived),
            }
        elif action == "add_evaluation":
            sections["evaluation"] = {
                "title": "3. Bid Evaluation",
                "body": templates.evaluation(brief, derived),
            }
        fixed.append(f)

    return {"fixed": fixed, "escalated": escalated}
