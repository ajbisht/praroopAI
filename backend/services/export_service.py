"""Gated DOCX export — refuses while any mandatory finding is open."""
from __future__ import annotations
import io
from typing import Any

from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from backend.core.rule_engine import all_rules


class ExportBlocked(Exception):
    pass


def export_docx(result: dict[str, Any]) -> bytes:
    sc = result["scorecard"]
    if not sc.get("can_finalize"):
        raise ExportBlocked(f"{sc.get('mandatory_open', 0)} mandatory compliance "
                            f"issue(s) still open.")

    brief = result["brief"]
    doc_type = (brief.get("doc_type") or "RFP").upper()
    doc = Document()

    # cover
    h = doc.add_heading(brief.get("title", doc_type), level=0)
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = sub.add_run(f"{doc_type}  ·  Government of Uttarakhand")
    r.bold = True
    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    money = result.get("derived", {}).get("money", {})
    meta.add_run(f"Estimated cost: {money.get('project_cost', '-')}   |   "
                 f"Duration: {brief.get('duration_months', '-')} months   |   "
                 f"Compliance: {sc['overall_percent']}%")
    doc.add_paragraph()

    # body
    for val in result.get("sections", {}).values():
        doc.add_heading(val["title"], level=1)
        for para in str(val["body"]).split("\n"):
            para = para.strip()
            if not para:
                continue
            if para.startswith(("-", "*", "•")):
                doc.add_paragraph(para.lstrip("-*• ").strip(), style="List Bullet")
            else:
                doc.add_paragraph(para)

    # scorecard
    doc.add_page_break()
    doc.add_heading("Compliance Scorecard", level=1)
    t = doc.add_table(rows=1, cols=3)
    t.style = "Light Grid Accent 1"
    hdr = t.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text = "Framework", "Score", "Status"
    for row in sc["rows"]:
        c = t.add_row().cells
        c[0].text = row["framework"]
        c[1].text = f"{row['percent']}% ({row['passed']}/{row['total']})"
        c[2].text = row["status"].upper()

    doc.add_heading("Compliance Basis (Statutory References)", level=2)
    seen = set()
    for r_ in all_rules(doc_type=doc_type):
        key = (r_.get("framework", ""), r_.get("citation", ""))
        if key[1] and key not in seen:
            doc.add_paragraph(f"{key[0]}: {key[1]}", style="List Bullet")
            seen.add(key)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
