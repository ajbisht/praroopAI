"""
Text sanitisers applied to every LLM-written section.

Small models get money wrong in two ways:
  1. magnitude errors  - "Rs200 crore" when the project is Rs2 crore
  2. malformed labels  - "Rs6,60,00,000 (Rs66 crore)"

`fix_amounts` rewrites every money mention to the *canonical* string produced
by the derivation engine, so the document can only ever contain amounts the
code itself computed. Anything that cannot be matched to a canonical value is
left untouched (we never invent a figure).
"""
from __future__ import annotations
import re
from typing import Any

from .derivations import inr, canonical_amounts

R = "\u20b9"

# ONE combined pattern, alternatives ordered longest-first. A single re.sub
# pass never rescans its own output, which avoids cascading replacements.
_NUM = r"[\d][\d,]*(?:\s?\.\s?\d+)?"
_MONEY = re.compile(
    rf"{R}\s?(?P<n1>{_NUM})\s*(?P<u1>crore|lakh)?"      # leading amount (+unit)
    rf"(?:\s*\(\s*{R}?\s*(?P<n2>{_NUM})\s*(?P<u2>crore|lakh)?\s*\))?",  # optional (…)
    re.IGNORECASE)

_MULT = {"crore": 1_00_00_000, "lakh": 1_00_000}
# magnitude slips a small model makes
_FACTORS = (1, 10, 100, 1000, 0.1, 0.01, 0.001)


def _num(s: str) -> float | None:
    try:
        return float(s.replace(",", "").replace(" ", ""))
    except ValueError:
        return None


def _match_canonical(value: float, canon: list[float], tol: float = 0.02) -> float | None:
    """Exact-ish match, else a clean power-of-ten slip of a canonical value."""
    if not value or not canon:
        return None
    for c in canon:
        if c and abs(value - c) <= tol * c:
            return c
    for c in canon:
        for f in _FACTORS:
            if c and abs(value - c * f) <= tol * c * f:
                return c
    return None


def fix_amounts(text: str, derived: dict[str, Any]) -> str:
    """Rewrite money mentions to canonical strings; leave unknowns alone."""
    if not text:
        return text
    canon = canonical_amounts(derived)
    if not canon:
        return text

    def repl(m):
        # try the leading figure, then the parenthetical, and emit the single
        # canonical string for whichever resolves.
        for num, unit in ((m.group("n1"), m.group("u1")),
                          (m.group("n2"), m.group("u2"))):
            if num is None:
                continue
            v = _num(num)
            if v is None:
                continue
            if unit:
                v *= _MULT[unit.lower()]
            c = _match_canonical(v, canon)
            if c is not None:
                return inr(c)
        return m.group(0)

    return _MONEY.sub(repl, text)


_DOLLAR = re.compile(r"\$\s?([\d,]+(?:\.\d+)?)(?:\s+(million|mn|crore|lakh|billion|bn))?",
                     re.IGNORECASE)


def normalize_currency(text: str) -> str:
    """Convert stray dollar amounts to rupees."""
    if not text:
        return text
    text = _DOLLAR.sub(
        lambda m: f"{R}{m.group(1)} {m.group(2)}" if m.group(2) else f"{R}{m.group(1)}", text)
    text = re.sub(r"\bdollars?\b", "rupees", text, flags=re.IGNORECASE)
    return text.replace("$", R)


def strip_markdown_emphasis(text: str) -> str:
    """
    Remove **bold** / __bold__ markers that leak into section bodies.

    The UI renders markdown bold, but models frequently emit malformed runs
    (e.g. '**Total Cost**:' inside a bullet) which read badly in the exported
    DOCX. Stripping at ingestion keeps both surfaces clean and identical.
    """
    if not text:
        return text
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"__(.+?)__", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"(?<!\*)\*(?!\s)([^*\n]+?)(?<!\s)\*(?!\*)", r"\1", text)
    # leftover stray markers
    text = text.replace("**", "")
    return text
