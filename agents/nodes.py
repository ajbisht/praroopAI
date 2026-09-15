"""
Agent node functions.
  intake / draft / reviewer   -> LLM-driven
  derive / compliance / score -> deterministic (statutory numbers + rules)
Framework-agnostic: graph.py wires them with LangGraph or a fallback runner.
"""
from __future__ import annotations
import json
import re
import time
from typing import Any

from backend.llm import client as llm
from backend.core.derivations import derive
from backend.core.context import build_context
from backend.core.rule_engine import evaluate
from backend.core.scorecard import build_scorecard
from . import prompts, doc_structure

MAX_LOOPS = 3
MIN_SECTION_CHARS = 180


def _step(agent, kind, detail, **extra):
    return {"agent": agent, "kind": kind, "detail": detail,
            "ts": round(time.time() * 1000), **extra}


# ── 1. INTAKE ───────────────────────────────────────────────────────
def intake_node(state):
    raw = state.get("raw_input") or {}
    request = (state.get("request") or "").strip()
    brief = {}
    if request:
        try:
            brief = llm.chat_json(prompts.INTAKE_USER.format(request=request),
                                  system=prompts.INTAKE_SYSTEM)
        except Exception:
            brief = {}
    if not isinstance(brief, dict):
        brief = {}
    for k, v in raw.items():
        if v not in (None, "", 0) or k not in brief:
            brief[k] = v
    brief.setdefault("doc_type", "RFP")
    brief.setdefault("title", "Untitled Project")

    n = int(brief.get("num_milestones", 3) or 3)
    if not brief.get("milestones"):
        base = 100 // n
        split = [base] * n
        split[-1] += 100 - sum(split)
        brief["milestones"] = [
            {"name": f"Milestone {i+1}", "payment_pct": split[i], "has_penalty": False}
            for i in range(n)]
    return {"brief": brief,
            "trace": [_step("Intake Agent", "ai",
                            f"Structured brief for '{brief.get('title')}'")]}


# ── 2. DERIVE ───────────────────────────────────────────────────────
def derive_node(state):
    d = derive(state["brief"])
    return {"derived": d,
            "trace": [_step("Derivation Engine", "code",
                            f"EMD {d['money']['emd_amount']} · PBG {d['money']['pbg_amount']} · "
                            f"{d['tender_mode']}")]}


# ── 3. DRAFT (one section per call) ─────────────────────────────────
def _draft_one(doc_type, title, guide, brief, derived):
    money = derived.get("money", {})
    user = prompts.SECTION_USER.format(
        doc_type=doc_type, title=title, guide=guide,
        brief_json=json.dumps(brief, ensure_ascii=False),
        m_cost=money.get("project_cost", ""), m_emd=money.get("emd_amount", ""),
        m_pbg=money.get("pbg_amount", ""), m_ld=money.get("ld_cap_amount", ""),
        m_milestones="\n".join(f"  - {s}" for s in money.get("milestones", [])),
        duration=derived.get("duration_months", ""),
        uptime=derived.get("uptime_percent", ""),
        retention=brief.get("data_retention_days", 90),
        storage=brief.get("storage", "on-premise"),
        grace=derived.get("grace_period_days", 7),
        ld_weekly=derived.get("ld_weekly_pct", 0.5),
        tender=derived.get("tender_mode", ""))
    system = prompts.SECTION_SYSTEM.format(doc_type=doc_type)
    body = ""
    for attempt in range(2):
        try:
            out = llm.chat(user if attempt == 0 else
                           user + "\n\nYour previous answer was too short. "
                                  "Write a fuller, more detailed section.",
                           system=system)
        except Exception:
            out = ""
        body = _clean(_coerce(out))
        if len(body) >= MIN_SECTION_CHARS:
            break
    return body


def draft_node(state):
    brief, derived = state["brief"], state["derived"]
    doc_type = (brief.get("doc_type") or "RFP").upper()
    sections = {}
    for key, title, guide in doc_structure.sections_for(doc_type):
        body = _repair_amounts(_normalize_currency(
            _draft_one(doc_type, title, guide, brief, derived)))
        if body.strip():
            sections[key] = {"title": title, "body": body.strip()}
    _sync_penalties(derived, sections.get("penalty", {}).get("body", ""))
    total = len(doc_structure.keys_for(doc_type))
    return {"sections": sections,
            "trace": [_step("Drafting Agent", "ai",
                            f"Drafted {len(sections)}/{total} {doc_type} sections")]}


# ── 4. COMPLIANCE (deterministic critic) ────────────────────────────
def compliance_node(state):
    project = {"brief": state["brief"], "derived": state["derived"],
               "sections": state.get("sections", {})}
    findings = evaluate(build_context(project),
                        doc_type=state["brief"].get("doc_type", "RFP"))
    mand = sum(1 for f in findings if f["severity"] == "mandatory")
    return {"findings": findings,
            "trace": [_step("Compliance Agent", "code",
                            f"{len(findings)} findings ({mand} mandatory)",
                            findings=findings)]}


# ── 5. REVIEWER ─────────────────────────────────────────────────────
def reviewer_node(state):
    brief, derived = state["brief"], state["derived"]
    doc_type = (brief.get("doc_type") or "RFP").upper()
    fixable = [f for f in state["findings"] if f["severity"] == "mandatory"]
    try:
        fix_map = llm.chat_json(
            prompts.REVIEW_USER.format(
                doc_type=doc_type,
                brief_json=json.dumps(brief, ensure_ascii=False),
                money_json=json.dumps(derived.get("money", {}), ensure_ascii=False),
                findings_json=json.dumps(fixable, ensure_ascii=False)),
            system=prompts.REVIEW_SYSTEM.format(doc_type=doc_type))
    except Exception:
        fix_map = {}
    if not isinstance(fix_map, dict):
        fix_map = {}

    titles = doc_structure.titles_for(doc_type)
    sections = dict(state.get("sections", {}))
    fixed = []
    for key, val in fix_map.items():
        if key not in titles:
            continue
        body = _repair_amounts(_normalize_currency(_clean(_coerce(val))))
        if body.strip():
            sections[key] = {"title": titles[key], "body": body.strip()}
            fixed.append(key)
    _sync_penalties(derived, sections.get("penalty", {}).get("body", ""))
    return {"sections": sections, "loop_count": state.get("loop_count", 0) + 1,
            "trace": [_step("Reviewer Agent", "ai",
                            f"Fixed: {', '.join(fixed) if fixed else 'none'}")]}


def route_after_compliance(state) -> str:
    mand = sum(1 for f in state.get("findings", []) if f["severity"] == "mandatory")
    if mand > 0 and state.get("loop_count", 0) < MAX_LOOPS:
        return "reviewer"
    return "end"


# ── 6. SCORE ────────────────────────────────────────────────────────
def score_node(state):
    doc_type = (state["brief"].get("doc_type") or "RFP").upper()
    sc = build_scorecard(state.get("findings", []), doc_type=doc_type)
    order = doc_structure.keys_for(doc_type)
    secs = state.get("sections", {})
    ordered = {k: secs[k] for k in order if k in secs}
    return {"sections": ordered, "scorecard": sc,
            "trace": [_step("Coordinator", "done",
                            f"Overall {sc['overall_percent']}% · "
                            f"{'READY' if sc['can_finalize'] else 'BLOCKED'}")]}


# ── helpers ─────────────────────────────────────────────────────────
def _coerce(value, depth=0) -> str:
    """Flatten dict/list model output into readable prose."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    ind = "  " * depth
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, dict):
                for k, v in item.items():
                    lines.append(f"{ind}- {_human(k)}: {_inline(v)}")
            else:
                lines.append(f"{ind}- {_inline(item)}")
        return "\n".join(lines)
    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{ind}- {_human(k)}:\n{_coerce(v, depth+1)}")
            else:
                lines.append(f"{ind}- {_human(k)}: {v}")
        return "\n".join(lines)
    return str(value)


def _inline(v) -> str:
    if isinstance(v, dict):
        return "; ".join(f"{_human(k)}: {x}" for k, x in v.items())
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return str(v)


def _human(k: str) -> str:
    return str(k).replace("_", " ").strip().capitalize()


def _clean(text: str) -> str:
    """Strip code fences, JSON wrappers and echoed headings."""
    if not text:
        return ""
    t = text.strip()
    t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    if t.startswith("{") or t.startswith("["):
        try:
            t = _coerce(json.loads(t))
        except Exception:
            pass
    t = re.sub(r"^\s*#{1,6}\s*.*\n", "", t, count=1)
    return t.strip()


_AMT = re.compile(r"\u20b9\s?([\d,]+)\s*\(\s*\u20b9?\s*([\d.,]+)\s*(crore|lakh)\s*\)",
                  re.IGNORECASE)


def _repair_amounts(text: str) -> str:
    """Recompute any '(₹X crore/lakh)' label from the rupee figure before it."""
    if not text:
        return text

    def fix(m):
        try:
            val = float(m.group(1).replace(",", ""))
        except ValueError:
            return m.group(0)
        if val >= 1_00_00_000:
            return f"\u20b9{m.group(1)} (\u20b9{val/1_00_00_000:.2f} crore)"
        if val >= 1_00_000:
            return f"\u20b9{m.group(1)} (\u20b9{val/1_00_000:.2f} lakh)"
        return f"\u20b9{m.group(1)}"

    return _AMT.sub(fix, text)


_DOLLAR = re.compile(r"\$\s?([\d,]+(?:\.\d+)?)(?:\s+(million|mn|crore|lakh|billion|bn))?",
                     re.IGNORECASE)


def _normalize_currency(text: str) -> str:
    if not text:
        return text

    def repl(m):
        return f"\u20b9{m.group(1)} {m.group(2)}" if m.group(2) else f"\u20b9{m.group(1)}"

    text = _DOLLAR.sub(repl, text)
    text = re.sub(r"\bdollars?\b", "rupees", text, flags=re.IGNORECASE)
    return text.replace("$", "\u20b9")


def _sync_penalties(derived, penalty_text: str) -> None:
    t = (penalty_text or "").lower()
    each = any(w in t for w in ("each milestone", "every milestone",
                                "per milestone", "each delivery"))
    rate = ("%" in t) and any(w in t for w in ("per week", "per day", "weekly", "daily"))
    cap = any(w in t for w in ("cap", "not exceed", "maximum"))
    ok = bool(each and rate and cap and len(t) >= 80)
    for m in derived.get("milestones", []):
        m["has_penalty"] = ok
