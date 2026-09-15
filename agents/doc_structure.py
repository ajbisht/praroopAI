"""RFP and DPR are different documents with different section sets."""
from __future__ import annotations

RFP_SECTIONS = [
    ("scope", "1. Scope of Work",
     "Describe the goods/services, quantities, locations, standards, and the full "
     "contract duration including maintenance. 2-3 detailed paragraphs."),
    ("eligibility", "2. Eligibility & Qualification Criteria",
     "Minimum average annual turnover, years of experience, similar completed "
     "government projects, mandatory registrations (GST, PAN). Use bullets."),
    ("evaluation", "3. Bid Evaluation Methodology",
     "The evaluation method (QCBS 70:30 or L1), technical scoring parameters with "
     "weightages, and the financial bid opening process."),
    ("payment", "4. Payment Schedule",
     "A milestone-linked payment schedule. For EACH milestone give the deliverable, "
     "the percentage, and the amount in Indian Rupees."),
    ("sla", "5. Service Levels (SLA)",
     "Committed uptime %, incident response time in HOURS, resolution time in HOURS, "
     "support window, and service-credit penalties."),
    ("data_security", "6. Data Security & Confidentiality",
     "Storage location, retention period, access control, encryption, audit rights, "
     "and IT-Act compliance."),
    ("penalty", "7. Penalty & Liquidated Damages",
     "The LD formula, the overall cap (% and amount in Rupees), the grace period, AND "
     "an explicit delay penalty for EACH milestone."),
]

DPR_SECTIONS = [
    ("executive_summary", "1. Executive Summary",
     "What the project is, why it is needed, total cost, duration, expected benefits."),
    ("background", "2. Project Background & Need Analysis",
     "Present situation, the gap addressed, policy context, and why this is needed now."),
    ("scope", "3. Project Objectives & Scope",
     "Specific measurable objectives and the full scope - components, coverage, locations."),
    ("technical_design", "4. Technical Design & Solution Architecture",
     "The technical solution - components, specifications, integration, standards."),
    ("implementation_plan", "5. Implementation Plan & Timeline",
     "Phase-wise implementation with milestones and timelines, and the executing arrangement."),
    ("payment", "6. Cost Estimate & Financial Phasing",
     "Capital cost and milestone-wise financial phasing. For EACH milestone give the "
     "deliverable, percentage and amount in Indian Rupees."),
    ("sla", "7. Operations & Maintenance (O&M) Service Levels",
     "O&M plan: uptime %, response/resolution times in HOURS, maintenance period, credits."),
    ("data_security", "8. Data Security & Governance",
     "Storage, retention, access control, audit, and IT-Act compliance."),
    ("penalty", "9. Penalty & Liquidated Damages",
     "LD formula, cap (% and Rupees), grace period, and a per-milestone delay penalty."),
    ("risk_analysis", "10. Risk Analysis & Mitigation",
     "Key technical, financial, operational and timeline risks, each with a concrete "
     "mitigation measure. Use a list."),
    ("outcomes", "11. Expected Outcomes & Benefits",
     "Tangible and intangible benefits, KPIs/success metrics, and the sustainability plan."),
]

SECTION_SETS = {"RFP": RFP_SECTIONS, "DPR": DPR_SECTIONS}


def sections_for(doc_type: str):
    return SECTION_SETS.get((doc_type or "RFP").upper(), RFP_SECTIONS)


def titles_for(doc_type: str) -> dict[str, str]:
    return {k: t for k, t, _ in sections_for(doc_type)}


def keys_for(doc_type: str) -> list[str]:
    return [k for k, _, _ in sections_for(doc_type)]
