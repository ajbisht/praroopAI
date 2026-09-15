"""
Derivation Engine - statutory figures computed in code, never by the LLM.
Also exposes `canonical_amounts()` so text can be validated against the
only money values that are actually legitimate for this project.
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


def _group(n: float) -> str:
    n = int(round(n)); sign = "-" if n < 0 else ""; s = str(abs(n))
    if len(s) <= 3: return sign + s
    last3, rest, parts = s[-3:], s[:-3], []
    while len(rest) > 2:
        parts.insert(0, rest[-2:]); rest = rest[:-2]
    if rest: parts.insert(0, rest)
    return sign + ",".join(parts) + "," + last3


def rupees(n: float) -> str:
    return "\u20b9" + _group(n)


def inr(n: float) -> str:
    """Canonical money string: 'Rs20,00,00,000 (Rs20.00 crore)'."""
    n = float(n or 0); base = rupees(n)
    if abs(n) >= 1_00_00_000: return f"{base} (\u20b9{n/1_00_00_000:.2f} crore)"
    if abs(n) >= 1_00_000:    return f"{base} (\u20b9{n/1_00_000:.2f} lakh)"
    return base


def derive(brief: dict[str, Any]) -> dict[str, Any]:
    c = _cfg()
    cost = float(brief.get("project_cost", 0) or 0)
    duration = int(brief.get("duration_months", 0) or 0)
    milestones = brief.get("milestones") or []
    if not milestones:
        milestones = [{"name": nm, "payment_pct": p, "has_penalty": False}
                      for nm, p in zip(["Installation", "Integration", "Go-live"],
                                       c["default_milestone_split"])]
    for m in milestones:
        m["payment_amount"] = round(cost * float(m.get("payment_pct", 0) or 0) / 100)
    emd = round(cost * c["emd_percent"] / 100)
    pbg = round(cost * c["pbg_percent"] / 100)
    ld  = round(cost * c["ld_cap_percent"] / 100)
    money = {"project_cost": inr(cost), "emd_amount": inr(emd),
             "pbg_amount": inr(pbg), "ld_cap_amount": inr(ld),
             "milestones": [f"{m['name']}: {m.get('payment_pct',0)}% = {inr(m.get('payment_amount',0))}"
                            for m in milestones]}
    return {"project_cost": cost, "duration_months": duration,
            "milestones": milestones, "money": money,
            "emd_percent": c["emd_percent"], "pbg_percent": c["pbg_percent"],
            "ld_percent": c["ld_cap_percent"], "ld_weekly_pct": c["ld_weekly_percent"],
            "uptime_percent": float(brief.get("uptime_percent", c["default_uptime_percent"])),
            "grace_period_days": int(brief.get("grace_period_days", c["default_grace_days"])),
            "emd_amount": emd, "pbg_amount": pbg, "ld_cap_amount": ld,
            "tender_mode": ("Open Tender" if cost > c["open_tender_threshold"] else "Limited Tender"),
            "open_tender_threshold": c["open_tender_threshold"]}


def canonical_amounts(derived: dict[str, Any]) -> list[float]:
    """Every rupee value that may legitimately appear in the document."""
    vals = [derived.get("project_cost", 0), derived.get("emd_amount", 0),
            derived.get("pbg_amount", 0), derived.get("ld_cap_amount", 0)]
    vals += [m.get("payment_amount", 0) for m in derived.get("milestones", [])]
    return [float(v) for v in vals if v]
