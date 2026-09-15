"""
Coordinator / Orchestrator — runs the sequential pipeline with one feedback
loop:  intake -> derive -> draft -> [compliance -> reviewer]* -> scorecard.

Plain Python. No framework needed. Emits a step-by-step trace the UI can show.
"""
from __future__ import annotations
import time
from typing import Any

from backend.core.derivations import derive
from backend.core.scorecard import build_scorecard
from . import intake_agent, drafting_agent, compliance_agent, reviewer_agent
from . import llm_client

MAX_LOOPS = 3


def run(raw_input: dict[str, Any]) -> dict[str, Any]:
    trace: list[dict[str, Any]] = []

    def step(agent, kind, detail, **extra):
        trace.append({
            "n": len(trace) + 1, "agent": agent, "kind": kind,
            "detail": detail, "ts": round(time.time() * 1000), **extra,
        })

    llm_on = llm_client.is_available()
    step("Coordinator", "start",
         f"LLM {'ONLINE' if llm_on else 'offline -> template mode'}")

    # 1. INTAKE
    brief = intake_agent.build_brief(raw_input)
    step("Intake Agent", "ai" if llm_on else "template",
         f"Built project brief for '{brief['title']}'")

    # 2. DERIVE (deterministic)
    derived = derive(brief)
    step("Derivation Engine", "code",
         f"EMD={derived['emd_amount']:,} PBG={derived['pbg_amount']:,} "
         f"LD cap={derived['ld_cap_amount']:,} tender={derived['tender_mode']}")

    # 3. DRAFT (first pass — intentionally leaves gaps)
    sections = drafting_agent.draft(brief, derived, first_pass=True)
    step("Drafting Agent", "ai" if llm_on else "template",
         f"Generated {len(sections)} sections (first pass)")

    project = {"brief": brief, "derived": derived, "sections": sections}

    # 4. COMPLIANCE <-> REVIEWER loop
    loops = 0
    findings = compliance_agent.check(project)
    step("Compliance Agent", "code",
         f"{len(findings)} findings "
         f"({sum(1 for f in findings if f['severity']=='mandatory')} mandatory)",
         findings=findings)

    while findings and loops < MAX_LOOPS:
        mandatory = [f for f in findings if f["severity"] == "mandatory"]
        if not mandatory:
            break  # only recommended items left -> stop looping
        result = reviewer_agent.review(project, findings)
        step("Reviewer Agent", "ai" if llm_on else "template",
             f"Fixed {len(result['fixed'])}, escalated {len(result['escalated'])}",
             fixed=[f["rule_id"] for f in result["fixed"]])
        loops += 1
        findings = compliance_agent.check(project)
        step("Compliance Agent", "code",
             f"Re-check: {len(findings)} findings remain", findings=findings)

    # 5. SCORECARD
    scorecard = build_scorecard(findings, doc_type=brief["doc_type"])
    step("Coordinator", "done",
         f"Overall {scorecard['overall_percent']}% · "
         f"{'READY to export' if scorecard['can_finalize'] else 'BLOCKED'}")

    return {
        "brief": brief,
        "derived": derived,
        "sections": sections,
        "findings": findings,
        "scorecard": scorecard,
        "trace": trace,
        "llm_online": llm_on,
    }
