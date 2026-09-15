"""
Section templates for the RFP. The Drafting Agent fills these from the
brief + derived numbers. If an on-prem LLM is available it can polish the
prose; if not, these templates alone produce a complete, valid document.
"""
from __future__ import annotations
from typing import Any

from .derivations import rupees


def scope(brief, d) -> str:
    return (
        f"The bidder shall supply, install, commission and maintain the "
        f"'{brief.get('title', 'project')}' as per specifications. "
        f"Estimated value: {rupees(d['project_cost'])}. "
        f"Contract duration: {d['duration_months']} months, including maintenance."
    )


def eligibility(brief, d) -> str:
    turnover = rupees(d["project_cost"])
    return (
        f"Bidders must have an average annual turnover of at least {turnover} "
        f"in the last three financial years, valid GST & PAN registration, and "
        f"at least two similar completed government projects."
    )


def evaluation(brief, d) -> str:
    return (
        "Bids shall be evaluated on a Quality-and-Cost-Based System (QCBS) "
        "with a 70:30 technical-to-financial weightage."
    )


def payment(brief, d) -> str:
    lines = ["Payments shall be released against the following milestones:"]
    for m in d.get("milestones", []):
        lines.append(
            f"  - {m['name']}: {m.get('payment_pct', 0)}% "
            f"({rupees(m.get('payment_amount', 0))})"
        )
    return "\n".join(lines)


def sla(brief, d) -> str:
    return (
        f"The vendor shall maintain a minimum system uptime of "
        f"{d.get('uptime_percent', 99.5)}%. Incident response within 4 hours "
        f"and resolution within 24 hours. Service credits apply on SLA breach."
    )


def data_security(brief, d) -> str:
    storage = brief.get("storage", "on-premise")
    retention = brief.get("data_retention_days", 90)
    return (
        f"All data shall be stored {storage} within government-controlled "
        f"infrastructure and retained for {retention} days. The department "
        f"reserves the right to conduct security audits of the vendor."
    )


def penalty(brief, d, with_milestone_penalty: bool = False) -> str:
    base = (
        f"Liquidated damages of {d.get('ld_weekly_pct', 0.5)}% of the delayed "
        f"milestone value shall apply per week of delay, capped at "
        f"{d.get('ld_percent', 10)}% of the contract value "
        f"({rupees(d.get('ld_cap_amount', 0))}). "
        f"A grace period of {d.get('grace_period_days', 7)} days applies."
    )
    if with_milestone_penalty:
        base += (
            " A delay penalty is defined for EACH delivery milestone as above."
        )
    return base


# map of section key -> (title, generator)
SECTION_ORDER = [
    ("scope", "1. Scope of Work", scope),
    ("eligibility", "2. Eligibility Criteria", eligibility),
    ("evaluation", "3. Bid Evaluation", evaluation),
    ("payment", "4. Payment Schedule", payment),
    ("sla", "5. Service Levels (SLA)", sla),
    ("data_security", "6. Data Security", data_security),
    ("penalty", "7. Penalty & Liquidated Damages", penalty),
]
