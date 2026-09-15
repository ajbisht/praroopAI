"""
Drafting Agent — generates the RFP section by section from the brief +
derived numbers. Uses the on-prem LLM to polish prose if available;
otherwise the deterministic templates alone produce a complete document.

To DEMONSTRATE the critique loop, the first draft intentionally leaves two
common real-world gaps (milestone penalties + a thin data-security section)
that the Compliance Agent will catch. Pass first_pass=False to draft fully.
"""
from __future__ import annotations
from typing import Any

from backend.core import templates
from . import llm_client


def _polish(title: str, body: str) -> str:
    """Optionally improve wording with the on-prem LLM (safe fallback)."""
    if not llm_client.is_available():
        return body
    out = llm_client.generate(
        prompt=f"Rewrite this government RFP section more formally, keep all "
               f"numbers and facts identical. Section: {title}\n\n{body}",
        system="You are a precise government procurement drafter. Never invent "
               "numbers. Keep it concise and formal.",
    )
    return out or body


def draft(brief: dict[str, Any], derived: dict[str, Any],
          first_pass: bool = True) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    for key, title, gen in templates.SECTION_ORDER:
        if key == "penalty":
            body = templates.penalty(brief, derived,
                                     with_milestone_penalty=not first_pass)
            if first_pass:
                # mark milestones as lacking an explicit penalty (the gap)
                for m in derived.get("milestones", []):
                    m["has_penalty"] = False
            else:
                for m in derived.get("milestones", []):
                    m["has_penalty"] = True
        elif key == "data_security" and first_pass:
            # intentionally weak/empty on first pass -> Compliance catches it
            body = ""
        else:
            body = gen(brief, derived)
        sections[key] = {"title": title, "body": _polish(title, body)}
    return sections
