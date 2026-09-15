# PraroopAI — 3-Minute Demo Script (for judges)

**Goal:** show that PraroopAI turns a one-line request into a *compliant, cited,
audit-ready* RFP — and that it **cannot** be finalized while non-compliant.

---

## 0:00 — The hook (15s)
> "Preparing a government RFP means satisfying dozens of mandatory rules —
> financial, procurement, security, SLA, penalty. Miss one clause and the
> tender gets rejected or flagged in audit. PraroopAI makes that impossible."

## 0:15 — Intake (30s)
1. Open the officer UI.
2. Point to the pre-filled example: **CCTV Surveillance — Dehradun, ₹2 Cr, 36 months, 3 milestones.**
3. Say: *"The officer just enters the numbers — no legal expertise needed."*
4. Click **⚡ Generate & Check Compliance**.

## 0:45 — Watch the agents work (45s)
As the trace animates, narrate each step:
- **Derivation Engine (code):** *"It auto-computes EMD ₹4,00,000, PBG ₹10,00,000, and the penalty cap — derived from cost, not guessed."*
- **Drafting Agent (AI):** *"It writes all 7 sections."*
- **Compliance Agent (code):** *"Now the inspector runs every rule-pack and finds 3 issues, 2 mandatory — a missing milestone penalty and a thin data-security section."*
- **Reviewer Agent:** *"It auto-fixes them and sends the draft BACK for re-check."*
- **Compliance again:** *"Zero issues remain."*

> Key line: **"The AI just caught and fixed its own mistakes — exactly what a rushed officer would miss."**

## 1:30 — The Scorecard (45s)
1. Point to the right panel: **100% overall**, every framework green.
2. Say: *"Every green bar is a deterministic rule check — not an AI opinion. So it never hallucinates compliance."*
3. Hover a finding earlier to show it **cites the exact rule id** (e.g. `PEN-002`).

## 2:15 — The hard gate (30s)
1. Change **Estimated cost to 0** and re-run.
2. Scorecard drops to **94%**, Financial framework turns **red**, `FIN-004` appears.
3. Point to the **🔒 Export RFP (locked)** button.
4. Say: *"You physically cannot finalize a non-compliant document. This is the difference between a chatbot and a governance tool."*

## 2:45 — Close (15s)
> "Grounded, not open-ended. Numbers drive the document. Compliance is a hard gate.
> It runs on-prem, so government data never leaves the State Data Centre. That's PraroopAI."

---

## Backup facts (if asked)
- **Where's the knowledge?** 5 public YAML rule-packs, versioned — not a document corpus.
- **Does it need a big dataset?** No. That's the point — it's fast and explainable.
- **Does it need internet / a cloud LLM?** No. Optional local Ollama/vLLM; runs offline in template mode.
- **How many AI calls?** ~2–4 per document; compliance is pure code.
- **DPR?** Phase 2 — same engine, different templates + rule-packs.
