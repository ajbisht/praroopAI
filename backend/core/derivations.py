"""
Derivation Engine — computes statutory figures from officer numbers.
Ratios come from config/statutory.yaml. Deterministic: the LLM never
computes money, it only copies the pre-formatted strings produced here.
"""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

CONFIG = Path(__file__).resolve().parents[2] / "config" / "statutory.yaml"


@lru_cache(maxsize=1)
def _cfg() -> dict[str, Any]:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def _indian_group(n: float) -> str:
    n = int(round(n))
    sign = "-" if n < 0 else ""
    s = str(abs(n))
    if len(s) <= 3:
        return sign + s
    last3, rest, parts = s[-3:], s[:-3], []
    while len(rest) > 2:
        parts.insert(0, rest[-2:]); rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return sign + ",".join(parts) + "," + last3


def rupees(n: float) -> str:
    return "\u20b9" + _indian_group(n)


def inr(n: float) -> str:
    """Authoritative money string: '₹20,00,00,000 (₹20.00 crore)'."""
    n = float(n or 0)
    base = rupees(n)
    if abs(n) >= 1_00_00_000:
        return f"{base} (\u20b9{n/1_00_00_000:.2f} crore)"
    if abs(n) >= 1_00_000:
        return f"{base} (\u20b9{n/1_00_000:.2f} lakh)"
    return base


def derive(brief: dict[str, Any]) -> dict[str, Any]:
    c = _cfg()
    cost = float(brief.get("project_cost", 0) or 0)
    duration = int(brief.get("duration_months", 0) or 0)

    milestones = brief.get("milestones") or []
    if not milestones:
        milestones = [{"name": nm, "payment_pct": pct, "has_penalty": False}
                      for nm, pct in zip(["Installation", "Integration", "Go-live"],
                                         c["default_milestone_split"])]
    for m in milestones:
        m["payment_amount"] = round(cost * float(m.get("payment_pct", 0) or 0) / 100)

    emd = round(cost * c["emd_percent"] / 100)
    pbg = round(cost * c["pbg_percent"] / 100)
    ld = round(cost * c["ld_cap_percent"] / 100)

    money = {
        "project_cost": inr(cost),
        "emd_amount": inr(emd),
        "pbg_amount": inr(pbg),
        "ld_cap_amount": inr(ld),
        "milestones": [f"{m['name']}: {m.get('payment_pct', 0)}% = {inr(m.get('payment_amount', 0))}"
                       for m in milestones],
    }

    return {
        "project_cost": cost, "duration_months": duration,
        "milestones": milestones, "money": money,
        "emd_percent": c["emd_percent"], "pbg_percent": c["pbg_percent"],
        "ld_percent": c["ld_cap_percent"], "ld_weekly_pct": c["ld_weekly_percent"],
        "uptime_percent": float(brief.get("uptime_percent", c["default_uptime_percent"])),
        "grace_period_days": int(brief.get("grace_period_days", c["default_grace_days"])),
        "emd_amount": emd, "pbg_amount": pbg, "ld_cap_amount": ld,
        "tender_mode": ("Open Tender" if cost > c["open_tender_threshold"]
                        else "Limited Tender"),
        "open_tender_threshold": c["open_tender_threshold"],
    }
