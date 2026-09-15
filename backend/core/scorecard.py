"""Scorecard - findings to per-framework RAG status + the hard gate."""
from __future__ import annotations
from typing import Any
from .rule_engine import all_rules


def build_scorecard(findings, doc_type="RFP", directory=None) -> dict[str, Any]:
    fw: dict[str, dict[str, Any]] = {}
    for r in all_rules(directory, doc_type):
        fw.setdefault(r["framework"], {"total":0,"failed":0,"mandatory_failed":0,"pack":r["pack"]})["total"] += 1
    for f in findings:
        d = fw.setdefault(f["framework"], {"total":0,"failed":0,"mandatory_failed":0,"pack":f["pack"]})
        d["failed"] += 1
        if f["severity"] == "mandatory": d["mandatory_failed"] += 1
    rows = []
    for name, d in fw.items():
        passed = d["total"] - d["failed"]
        pct = round(100*passed/d["total"]) if d["total"] else 100
        status = "red" if d["mandatory_failed"] else ("amber" if d["failed"] else "green")
        rows.append({"framework":name,"pack":d["pack"],"passed":passed,
                     "total":d["total"],"percent":pct,"status":status})
    total = sum(d["total"] for d in fw.values()); failed = len(findings)
    mand = sum(1 for f in findings if f["severity"] == "mandatory")
    return {"rows": sorted(rows, key=lambda r: r["framework"]),
            "overall_percent": round(100*(total-failed)/total) if total else 100,
            "mandatory_open": mand, "can_finalize": mand == 0, "findings": findings}
