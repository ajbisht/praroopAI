"""Context Builder — flattens the project into variables rules read."""
from __future__ import annotations
from typing import Any


def build_context(project: dict[str, Any]) -> dict[str, Any]:
    brief = project.get("brief", {})
    derived = project.get("derived", {})
    sections = project.get("sections", {})

    def has(k):
        s = sections.get(k)
        return bool(s and str(s.get("body", "")).strip())

    milestones = derived.get("milestones", brief.get("milestones", []) or [])
    pay_sum = sum(float(m.get("payment_pct", 0) or 0) for m in milestones)
    every_pen = bool(milestones) and all(bool(m.get("has_penalty")) for m in milestones)

    cost = float(derived.get("project_cost", brief.get("project_cost", 0) or 0))
    threshold = derived.get("open_tender_threshold", 5000000)
    tender_ok = (cost <= threshold) or (derived.get("tender_mode") == "Open Tender")

    return {
        "project_cost": cost,
        "emd_percent": derived.get("emd_percent", 0),
        "pbg_percent": derived.get("pbg_percent", 0),
        "ld_percent": derived.get("ld_percent", 0),
        "uptime_percent": derived.get("uptime_percent", 0),
        "grace_period_days": derived.get("grace_period_days", 0),
        "milestone_payments_sum_ok": abs(pay_sum - 100.0) < 0.01,
        "every_milestone_has_penalty": every_pen,
        "tender_mode_ok": tender_ok,
        "data_residency_ok": bool(brief.get("storage")),
        "has_section_scope": has("scope"),
        "has_section_eligibility": has("eligibility"),
        "has_section_evaluation": has("evaluation"),
        "has_section_data_security": has("data_security"),
        "has_section_sla": has("sla"),
        "has_section_payment": has("payment"),
        "has_section_penalty": has("penalty"),
        "has_section_executive_summary": has("executive_summary"),
        "has_section_background": has("background"),
        "has_section_technical_design": has("technical_design"),
        "has_section_implementation_plan": has("implementation_plan"),
        "has_section_risk_analysis": has("risk_analysis"),
        "has_section_outcomes": has("outcomes"),
        "penalty_text_ok": _penalty_ok(sections),
    }


def _penalty_ok(sections: dict[str, Any]) -> bool:
    """A real penalty clause states a rate, a cap, and covers each milestone."""
    body = str((sections.get("penalty") or {}).get("body", "")).lower()
    if len(body) < 80:
        return False
    rate = ("%" in body) and any(w in body for w in
                                ("per week", "per day", "weekly", "daily"))
    cap = any(w in body for w in ("cap", "not exceed", "maximum"))
    each = any(w in body for w in ("each milestone", "every milestone",
                                   "per milestone", "each delivery"))
    return rate and cap and each
