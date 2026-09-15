"""
Deterministic clause builders.

Some sections are not creative writing — they are formulae. The penalty clause,
the SLA schedule and the payment schedule are fully determined by the statutory
config plus the officer's numbers.

A small model frequently fails to write them in a compliant form, which used to
leave PEN-002/PEN-004 open forever and permanently block the export gate. Since
the compliance critic is deterministic, the *repair* for a deterministic rule
should be deterministic too: if the reviewer LLM cannot satisfy the rule, we
synthesise the clause in code from the same figures the critic checks against.

`FINDING_SECTIONS` additionally tells the reviewer which section each finding is
allowed to touch, so the model can never overwrite a section that already passed.
"""
from __future__ import annotations
from typing import Any

from backend.core.derivations import inr


# ── which section does each finding belong to? ──────────────────────
# Used by the reviewer as a whitelist. Covers EVERY rule, including those we
# cannot auto-build, so an unrelated key from the model is always rejected.
FINDING_SECTIONS: dict[str, str] = {
    # penalty
    "PEN-001": "penalty", "PEN-002": "penalty",
    "PEN-003": "penalty", "PEN-004": "penalty",
    # service levels
    "SLA-001": "sla", "SLA-002": "sla", "SLA-003": "sla", "DPR-007": "sla",
    # security
    "SEC-001": "data_security", "SEC-002": "data_security",
    # financial
    "FIN-003": "payment",
    # procurement
    "GFR-001": "scope", "GFR-002": "eligibility", "GFR-004": "evaluation",
    # DPR-only sections
    "DPR-001": "executive_summary", "DPR-002": "background",
    "DPR-003": "technical_design", "DPR-004": "implementation_plan",
    "DPR-005": "risk_analysis", "DPR-006": "outcomes",
}


def penalty_clause(brief: dict[str, Any], derived: dict[str, Any]) -> str:
    """Satisfies PEN-001, PEN-002, PEN-003 and PEN-004 by construction."""
    weekly = derived.get("ld_weekly_pct", 0.5)
    cap_pct = derived.get("ld_percent", 10)
    cap_amt = inr(derived.get("ld_cap_amount", 0))
    grace = derived.get("grace_period_days", 7)
    lines = [
        f"Liquidated damages shall be levied at {weekly}% of the value of the "
        f"delayed milestone for each completed week of delay. The penalty applies "
        f"to EACH delivery milestone separately, as set out below.",
        "",
        "Milestone-wise delay penalty:",
    ]
    for m in derived.get("milestones", []):
        lines.append(f"- {m.get('name')}: {weekly}% of "
                     f"{inr(m.get('payment_amount', 0))} per week of delay")
    lines += [
        "",
        f"The aggregate liquidated damages recoverable under this contract shall "
        f"not exceed a cap of {cap_pct}% of the contract value, i.e. {cap_amt}. "
        f"A grace period of {grace} days shall apply before liquidated damages "
        f"begin to accrue on any milestone. Liquidated damages shall be deducted "
        f"from the next due payment or recovered from the Performance Bank "
        f"Guarantee.",
    ]
    return "\n".join(lines)


def sla_clause(brief: dict[str, Any], derived: dict[str, Any]) -> str:
    """Satisfies SLA-001, SLA-002, SLA-003 and DPR-007."""
    uptime = derived.get("uptime_percent", 99.5)
    return (
        f"The vendor shall maintain a minimum system uptime of {uptime}% measured "
        f"on a calendar-month basis across all deployed components.\n"
        f"\n"
        f"Incident response and resolution:\n"
        f"- Critical (P1): response within 1 hour, resolution within 8 hours\n"
        f"- High (P2): response within 4 hours, resolution within 24 hours\n"
        f"- Medium (P3): response within 8 hours, resolution within 72 hours\n"
        f"\n"
        f"Support shall operate on a 24x7 basis for P1 and P2 incidents. Service "
        f"credits shall apply for every 0.5% shortfall against the committed "
        f"uptime, deductible from the next milestone payment. Sustained breach "
        f"over three consecutive months shall constitute a material default."
    )


def data_security_clause(brief: dict[str, Any], derived: dict[str, Any]) -> str:
    """Satisfies SEC-001 and SEC-002."""
    storage = brief.get("storage", "on-premise")
    retention = brief.get("data_retention_days", 90)
    where = ("within the State Data Centre (on-premise)" if storage == "on-premise"
             else "on a MeitY-empanelled cloud located in India")
    return (
        f"All project data shall be stored {where} and retained for a period of "
        f"{retention} days, after which it shall be securely purged unless "
        f"required for an ongoing investigation or statutory obligation.\n"
        f"\n"
        f"- Access shall be role-based, individually attributable and fully logged\n"
        f"- Data shall be encrypted both at rest and in transit\n"
        f"- No data shall be transferred outside the custody of the Government "
        f"of Uttarakhand without prior written approval\n"
        f"- The department reserves the right to conduct security audits of the "
        f"vendor's systems and processes at any time\n"
        f"\n"
        f"The vendor shall implement reasonable security practices as required "
        f"under Section 43A of the Information Technology Act, 2000 and the "
        f"applicable MeitY guidelines."
    )


def payment_clause(brief: dict[str, Any], derived: dict[str, Any]) -> str:
    """Satisfies FIN-003 - milestone payments summing to the contract value."""
    lines = ["Payments shall be released against verified completion of the "
             "following milestones:", ""]
    for m in derived.get("milestones", []):
        lines.append(f"- {m.get('name')}: {m.get('payment_pct', 0)}% = "
                     f"{inr(m.get('payment_amount', 0))}")
    lines += [
        "",
        f"The total of all milestone payments equals the contract value of "
        f"{inr(derived.get('project_cost', 0))}. Each payment shall be released "
        f"only after written acceptance by the departmental inspection committee. "
        f"A Performance Bank Guarantee of {inr(derived.get('pbg_amount', 0))} "
        f"shall remain valid until 60 days beyond the maintenance period.",
    ]
    return "\n".join(lines)


# rule id -> (section key, builder)  — only rules we can satisfy in code
RULE_FALLBACKS: dict[str, tuple[str, Any]] = {
    "PEN-001": ("penalty", penalty_clause),
    "PEN-002": ("penalty", penalty_clause),
    "PEN-004": ("penalty", penalty_clause),
    "SLA-001": ("sla", sla_clause),
    "SLA-002": ("sla", sla_clause),
    "SLA-003": ("sla", sla_clause),
    "DPR-007": ("sla", sla_clause),
    "SEC-001": ("data_security", data_security_clause),
    "SEC-002": ("data_security", data_security_clause),
    "FIN-003": ("payment", payment_clause),
}


def build_for(rule_ids: list[str], brief: dict[str, Any],
              derived: dict[str, Any]) -> dict[str, str]:
    """Deterministic bodies for whichever of these rules we can satisfy."""
    out: dict[str, str] = {}
    for rid in rule_ids:
        hit = RULE_FALLBACKS.get(rid)
        if hit:
            key, builder = hit
            out.setdefault(key, builder(brief, derived))
    return out
