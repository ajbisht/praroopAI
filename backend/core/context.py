"""Context Builder - flattens the project into variables rules read."""
from __future__ import annotations
from typing import Any


def build_context(project: dict[str, Any]) -> dict[str, Any]:
    brief = project.get("brief", {}); derived = project.get("derived", {})
    sections = project.get("sections", {})
    has = lambda k: bool((sections.get(k) or {}).get("body", "").strip())
    ms = derived.get("milestones", brief.get("milestones", []) or [])
    pay = sum(float(m.get("payment_pct", 0) or 0) for m in ms)
    cost = float(derived.get("project_cost", brief.get("project_cost", 0) or 0))
    thr = derived.get("open_tender_threshold", 5000000)
    return {
        "project_cost": cost,
        "emd_percent": derived.get("emd_percent", 0),
        "pbg_percent": derived.get("pbg_percent", 0),
        "ld_percent": derived.get("ld_percent", 0),
        "uptime_percent": derived.get("uptime_percent", 0),
        "grace_period_days": derived.get("grace_period_days", 0),
        "milestone_payments_sum_ok": abs(pay - 100.0) < 0.01,
        "every_milestone_has_penalty": bool(ms) and all(bool(m.get("has_penalty")) for m in ms),
        "tender_mode_ok": (cost <= thr) or (derived.get("tender_mode") == "Open Tender"),
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
        "penalty_text_ok": penalty_text_ok((sections.get("penalty") or {}).get("body", "")),
    }


def penalty_text_ok(body: str) -> bool:
    """A real LD clause states a rate, a cap, and covers each milestone."""
    b = (body or "").lower()
    if len(b) < 80: return False
    rate = ("%" in b) and any(w in b for w in ("per week","per day","weekly","daily"))
    cap  = any(w in b for w in ("cap","not exceed","maximum"))
    each = any(w in b for w in ("each milestone","every milestone","per milestone","each delivery"))
    return rate and cap and each
