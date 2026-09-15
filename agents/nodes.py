"""
Agent node functions.
  intake / draft / reviewer   -> LLM-driven
  derive / compliance / score -> deterministic

Two safeguards keep small models honest:
  * every section is passed through the money sanitiser, so amounts can only
    be the canonical figures the derivation engine computed;
  * if the reviewer LLM cannot clear a deterministic rule, the clause is
    synthesised in code (agents/fallbacks.py) so the hard gate can close.
"""
from __future__ import annotations
import json
import re
import time
from typing import Any

from backend.config import settings
from backend.llm import client as llm
from backend.logging_setup import get_logger
from backend.core.derivations import derive
from backend.core.context import build_context
from backend.core.rule_engine import evaluate
from backend.core.scorecard import build_scorecard
from backend.core.sanitize import (fix_amounts, normalize_currency,
                                   strip_markdown_emphasis)
from . import prompts, doc_structure, progress, fallbacks

log = get_logger("agents")


def _step(agent, kind, detail, **extra):
    return {"agent": agent, "kind": kind, "detail": detail,
            "ts": round(time.time() * 1000), **extra}


def _polish(text: str, derived: dict[str, Any]) -> str:
    """Every LLM-written body goes through this."""
    t = _clean(_coerce(text))
    t = strip_markdown_emphasis(t)
    t = normalize_currency(t)
    t = fix_amounts(t, derived)
    return t.strip()


# ── 1. INTAKE ───────────────────────────────────────────────────────
def intake_node(state):
    raw = state.get("raw_input") or {}
    request = (state.get("request") or "").strip()
    log.info("[intake] start (request=%d chars)", len(request))
    progress.emit(type="progress", stage="intake", detail="Understanding the request…")

    brief: Any = {}
    if request:
        try:
            brief = llm.chat_json(prompts.INTAKE_USER.format(request=request),
                                  system=prompts.INTAKE_SYSTEM, label="intake")
        except Exception as e:
            log.warning("[intake] LLM failed (%s) - using form inputs", e)
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
        brief["milestones"] = [{"name": f"Milestone {i+1}", "payment_pct": split[i],
                                "has_penalty": False} for i in range(n)]
    log.info("[intake] done -> %s '%s'", brief["doc_type"], brief["title"])
    return {"brief": brief,
            "trace": [_step("Intake Agent", "ai",
                            f"Structured brief for '{brief.get('title')}'")]}


# ── 2. DERIVE ───────────────────────────────────────────────────────
def derive_node(state):
    d = derive(state["brief"])
    log.info("[derive] cost=%s emd=%s pbg=%s ld=%s %s",
             d["money"]["project_cost"], d["money"]["emd_amount"],
             d["money"]["pbg_amount"], d["money"]["ld_cap_amount"], d["tender_mode"])
    return {"derived": d,
            "trace": [_step("Derivation Engine", "code",
                            f"EMD {d['money']['emd_amount']} · "
                            f"PBG {d['money']['pbg_amount']} · {d['tender_mode']}")]}


# ── 3. DRAFT (one LLM call per section) ─────────────────────────────
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
    for attempt in range(max(1, settings.section_retries)):
        try:
            out = llm.chat(user if attempt == 0 else
                           user + "\n\nYour previous answer was too short. "
                                  "Write a fuller, more detailed section.",
                           system=system, label=f"draft:{title[:28]}")
        except Exception as e:
            log.error("[draft] '%s' attempt %d failed: %s", title, attempt + 1, e)
            out = ""
        body = _polish(out, derived)
        if len(body) >= settings.min_section_chars:
            break
    return body


def draft_node(state):
    brief, derived = state["brief"], state["derived"]
    doc_type = (brief.get("doc_type") or "RFP").upper()
    spec = doc_structure.sections_for(doc_type)
    total = len(spec)
    log.info("[draft] start - %d %s sections, up to %d LLM calls",
             total, doc_type, total * settings.section_retries)
    progress.emit(type="progress", stage="draft",
                  detail=f"Drafting {total} {doc_type} sections…")

    sections, t_all = {}, time.monotonic()
    for i, (key, title, guide) in enumerate(spec, 1):
        progress.emit(type="progress", stage="draft", current=i, total=total,
                      detail=f"Drafting {i}/{total} — {title}")
        t0 = time.monotonic()
        body = _draft_one(doc_type, title, guide, brief, derived)
        dt = time.monotonic() - t0
        if body.strip():
            sections[key] = {"title": title, "body": body.strip()}
            log.info("[draft] %d/%d %-46s %5.1fs  %d chars", i, total, title, dt, len(body))
            progress.emit(type="progress", stage="draft", current=i, total=total,
                          detail=f"✓ {i}/{total} — {title} ({dt:.0f}s)")
        else:
            log.warning("[draft] %d/%d %-46s %5.1fs  EMPTY", i, total, title, dt)
            progress.emit(type="progress", stage="draft", current=i, total=total,
                          detail=f"⚠ {i}/{total} — {title} came back empty")

    _sync_penalties(derived, sections.get("penalty", {}).get("body", ""))
    log.info("[draft] done - %d/%d sections in %.1fs",
             len(sections), total, time.monotonic() - t_all)
    return {"sections": sections,
            "trace": [_step("Drafting Agent", "ai",
                            f"Drafted {len(sections)}/{total} {doc_type} sections")]}


# ── 4. COMPLIANCE (deterministic critic) ────────────────────────────
def compliance_node(state):
    doc_type = state["brief"].get("doc_type", "RFP")
    progress.emit(type="progress", stage="compliance", detail="Auditing against rule-packs…")
    findings = evaluate(build_context({"brief": state["brief"],
                                       "derived": state["derived"],
                                       "sections": state.get("sections", {})}),
                        doc_type=doc_type)
    mand = sum(1 for f in findings if f["severity"] == "mandatory")
    if findings:
        log.info("[compliance] %d findings (%d mandatory): %s", len(findings), mand,
                 ", ".join(f["rule_id"] for f in findings))
    else:
        log.info("[compliance] clean - no findings")
    return {"findings": findings,
            "trace": [_step("Compliance Agent", "code",
                            f"{len(findings)} findings ({mand} mandatory)",
                            findings=findings)]}


# ── 5. REVIEWER (LLM first, deterministic fallback second) ──────────
def reviewer_node(state):
    brief, derived = state["brief"], state["derived"]
    doc_type = (brief.get("doc_type") or "RFP").upper()
    titles = doc_structure.titles_for(doc_type)
    open_mandatory = [f for f in state["findings"] if f["severity"] == "mandatory"]
    loop = state.get("loop_count", 0) + 1
    log.info("[reviewer] fixing %d mandatory findings (loop %d)",
             len(open_mandatory), loop)
    progress.emit(type="progress", stage="reviewer",
                  detail=f"Fixing {len(open_mandatory)} compliance issue(s)…")

    sections = dict(state.get("sections", {}))
    fixed, via_code = [], []

    # 1) ask the model
    try:
        fix_map = llm.chat_json(
            prompts.REVIEW_USER.format(
                doc_type=doc_type,
                brief_json=json.dumps(brief, ensure_ascii=False),
                money_json=json.dumps(derived.get("money", {}), ensure_ascii=False),
                findings_json=json.dumps(open_mandatory, ensure_ascii=False)),
            system=prompts.REVIEW_SYSTEM.format(doc_type=doc_type), label="reviewer")
    except Exception as e:
        log.error("[reviewer] LLM failed: %s", e)
        fix_map = {}
    if isinstance(fix_map, dict):
        for key, val in fix_map.items():
            if key not in titles:
                continue
            body = _polish(val, derived)
            if body.strip():
                sections[key] = {"title": titles[key], "body": body.strip()}
                fixed.append(key)
    _sync_penalties(derived, sections.get("penalty", {}).get("body", ""))

    # 2) re-check; anything still failing that we can build in code, we build
    still = evaluate(build_context({"brief": brief, "derived": derived,
                                    "sections": sections}), doc_type=doc_type)
    still_mandatory = [f["rule_id"] for f in still if f["severity"] == "mandatory"]
    if still_mandatory:
        built = fallbacks.build_for(still_mandatory, brief, derived)
        for key, body in built.items():
            if key in titles:
                sections[key] = {"title": titles[key], "body": body}
                via_code.append(key)
                if key in fixed:
                    fixed.remove(key)
        if via_code:
            log.warning("[reviewer] model could not satisfy %s - built %s "
                        "deterministically from statutory config",
                        ", ".join(still_mandatory), ", ".join(via_code))
        _sync_penalties(derived, sections.get("penalty", {}).get("body", ""))

    parts = []
    if fixed:
        parts.append(f"{', '.join(fixed)} (AI)")
    if via_code:
        parts.append(f"{', '.join(via_code)} (rule-built)")
    detail = "Fixed: " + ("; ".join(parts) if parts else "none")
    log.info("[reviewer] %s", detail)
    return {"sections": sections, "loop_count": loop,
            "trace": [_step("Reviewer Agent", "ai" if fixed else "code", detail)]}


def route_after_compliance(state) -> str:
    mand = sum(1 for f in state.get("findings", []) if f["severity"] == "mandatory")
    loops = state.get("loop_count", 0)
    if mand > 0 and loops < settings.max_review_loops:
        return "reviewer"
    if mand > 0:
        log.warning("[route] %d mandatory findings remain after %d loops", mand, loops)
    return "end"


# ── 6. SCORE ────────────────────────────────────────────────────────
def score_node(state):
    doc_type = (state["brief"].get("doc_type") or "RFP").upper()
    sc = build_scorecard(state.get("findings", []), doc_type=doc_type)
    order = doc_structure.keys_for(doc_type)
    secs = state.get("sections", {})
    log.info("[score] overall %d%% | mandatory_open=%d | can_finalize=%s",
             sc["overall_percent"], sc["mandatory_open"], sc["can_finalize"])
    return {"sections": {k: secs[k] for k in order if k in secs}, "scorecard": sc,
            "trace": [_step("Coordinator", "done",
                            f"Overall {sc['overall_percent']}% · "
                            f"{'READY' if sc['can_finalize'] else 'BLOCKED'}")]}


# ── helpers ─────────────────────────────────────────────────────────
def _coerce(value, depth=0) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    ind = "  " * depth
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, dict):
                for k, v in item.items():
                    out.append(f"{ind}- {_human(k)}: {_inline(v)}")
            else:
                out.append(f"{ind}- {_inline(item)}")
        return "\n".join(out)
    if isinstance(value, dict):
        out = []
        for k, v in value.items():
            if isinstance(v, (dict, list)):
                out.append(f"{ind}- {_human(k)}:\n{_coerce(v, depth+1)}")
            else:
                out.append(f"{ind}- {_human(k)}: {v}")
        return "\n".join(out)
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
    return re.sub(r"^\s*#{1,6}\s*.*\n", "", t, count=1).strip()


def _sync_penalties(derived, penalty_text: str) -> None:
    from backend.core.context import penalty_text_ok
    ok = penalty_text_ok(penalty_text)
    for m in derived.get("milestones", []):
        m["has_penalty"] = ok
