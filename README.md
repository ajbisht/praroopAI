<div align="center">

<img src="docs/media/logo.png" width="110" alt="PraroopAI logo" />

# प्रारूप · PraroopAI

### AI DPR/RFP Drafting &amp; Compliance Assistant

*Draft it right the first time.*

**UKIS 2026 · ITDA, Government of Uttarakhand**

![engine](https://img.shields.io/badge/engine-LangGraph-6C4AB6?style=flat-square)
![llm](https://img.shields.io/badge/LLM-Ollama%20%7C%20OpenAI%20%7C%20OpenRouter%20%7C%20Claude-2B6CB0?style=flat-square)
![deploy](https://img.shields.io/badge/deploy-on--prem-1F9254?style=flat-square)
![tests](https://img.shields.io/badge/tests-28%20passing-1F9254?style=flat-square)
![license](https://img.shields.io/badge/license-MIT-6B7689?style=flat-square)

</div>

---

## What is PraroopAI?

Preparing a government **DPR** or **RFP** means satisfying dozens of mandatory rules —
financial norms, procurement/GFR guidelines, security requirements, service levels and
penalty clauses. Miss one clause and the tender is rejected or flagged in audit.

**PraroopAI** is a **LangGraph multi-agent system** that drafts the document with an LLM,
then hands it to a **deterministic compliance critic** that audits it against public
government rule-packs. Compliance is a **hard gate** — the document *cannot* be exported
while a mandatory check is failing.

![PraroopAI](docs/media/screenshot.png)

---

## The design principle

> **The LLM writes prose. Code owns the facts.**

Small models are unreliable with numbers and formulaic clauses, so those are never left
to the model:

| Concern | Owner | Guarantee |
|---|---|---|
| Section prose | LLM | readable, project-specific text |
| Every money figure | `core/derivations.py` | amounts are computed, and `core/sanitize.py` rewrites any model-written amount to the canonical figure |
| Compliance verdict | `core/rule_engine.py` | pure code — a "100%" verdict is a fact, not an opinion |
| Formulaic clauses | `agents/fallbacks.py` | if the model cannot satisfy a deterministic rule, the clause is **built from statutory config** so the gate can always close honestly |

The trace attributes every repair:

```
Fixed: risk_analysis, outcomes (AI); sla, penalty, data_security (rule-built)
```

---

## Features

| | |
|---|---|
| 🤖 **Multi-agent pipeline** | intake → derive → draft → compliance → reviewer, with a real feedback loop |
| 📡 **Live progress** | progress bar, per-section streaming and a Live Log tab — never a silent wait |
| 🔍 **Real logging** | `LOG_LEVEL=TRACE\|DEBUG\|INFO\|WARNING` shows every LLM call with timing |
| 🧮 **Code owns the maths** | EMD, PBG, penalty caps and milestone amounts computed in Python |
| 🛡️ **Deterministic compliance** | rules run in code, so compliance can never hallucinate |
| 🧰 **Deterministic repair** | formulaic clauses are rule-built when the model fails |
| 📖 **Citation-grade** | every finding cites its basis (GFR 2017, IT Act, MeitY model RFP) |
| 🔒 **Hard gate** | export returns **HTTP 423** while any mandatory finding is open |
| 🔌 **Any LLM provider** | switch by editing one line of `.env` |

---

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt

cp .env.example .env               # Windows: copy .env.example .env
ollama pull qwen2.5:7b

./run.sh                           # Windows: run.bat
```

Open **<http://localhost:8000>** — the backend serves the UI, so there is
**nothing separate to start**.

> 💡 `qwen2.5:1.5b` runs but writes thin prose. Use **`qwen2.5:7b` or `14b`** for
> documents that read like real government drafts.

See **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** if anything looks stuck.

---

## Switching LLM providers

Change **one line** in `.env`. No code edits, no redeploy.

```ini
LLM_PROVIDER=ollama          # ollama | openai | openrouter | anthropic | openai_compatible
LLM_MODEL=qwen2.5:7b
```

| `LLM_PROVIDER` | Example `LLM_MODEL` | Needs |
|---|---|---|
| `ollama` | `qwen2.5:7b`, `llama3.1:8b` | local Ollama (on-prem) |
| `openai` | `gpt-4o-mini` | `OPENAI_API_KEY` |
| `openrouter` | `anthropic/claude-3.5-sonnet` | `OPENROUTER_API_KEY` |
| `anthropic` | `claude-3-5-sonnet-20241022` | `ANTHROPIC_API_KEY` |
| `openai_compatible` | any | vLLM / LM Studio / Together / Groq |

Providers use each vendor's **native REST API** via `httpx` — no vendor SDKs.

---

## How it works

```
             ┌──────────── mandatory findings ────────────┐
             ▼                                            │
intake ──► derive ──► draft ──► compliance ──► reviewer ───┘
 (LLM)      (code)     (LLM)      (code)      (LLM + code)
                                     │
                                     └── clean ──► score ──► END
```

The only cycle is **compliance ⇄ reviewer**. The reviewer asks the LLM first; anything
still failing a deterministic rule is then built in code.

---

## The knowledge = bounded rule-packs

Small, public, versioned **YAML** — *not* a document corpus. 6 packs, 24 rules.

| Pack | Covers | Example citation |
|---|---|---|
| `financial.yaml` | EMD, PBG, milestone payments | GFR 2017, Rule 170 / 171 |
| `procurement_gfr.yaml` | Scope, eligibility, tender mode | GFR 2017, Rule 161 / 173 |
| `security.yaml` | Data security, retention, audit | IT Act 2000, Sec 43A |
| `sla.yaml` | Uptime, response, service credits | MeitY Model RFP |
| `penalty.yaml` | Liquidated damages, per-milestone penalty | GFR 2017, Rule 175 |
| `dpr_completeness.yaml` | DPR-only sections (need analysis, risk, outcomes) | MoSPI DPR guidelines |

Statutory ratios live in [`config/statutory.yaml`](config/statutory.yaml).

---

## API

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/health` | engine, provider, model, tuning, LLM call stats |
| `GET` | `/api/rulepacks` | active packs and versions |
| `GET` | `/api/structure/{doc_type}` | section outline for RFP or DPR |
| `POST` | `/api/run` | run the pipeline (single JSON response) |
| `POST` | `/api/run/stream` | **SSE** — `step` / `node` / `progress` / `ping` / `complete` |
| `POST` | `/api/export` | DOCX — **HTTP 423** if a mandatory finding is open |

---

## Project structure

```
praroopai/
├── .env.example              ← provider, log level, pipeline tuning
├── config/statutory.yaml     ← statutory ratios (EMD/PBG/LD)
├── backend/
│   ├── app.py                ← FastAPI: serves the UI + API
│   ├── logging_setup.py      ← TRACE/DEBUG/INFO logging
│   ├── llm/                  ← provider-agnostic client (+ call timing)
│   └── core/
│       ├── derivations.py    ← money computed here, plus canonical_amounts()
│       ├── sanitize.py       ← markdown strip + money correction
│       ├── rule_engine.py    ← YAML rules, safe evaluator
│       ├── context.py        ← the variables rules read
│       └── scorecard.py      ← RAG status + hard gate
├── agents/
│   ├── graph.py              ← LangGraph StateGraph + threaded streaming
│   ├── nodes.py              ← the six node functions
│   ├── fallbacks.py          ← deterministic clause builders
│   ├── progress.py           ← live progress bus
│   └── doc_structure.py      ← RFP (7) vs DPR (11) section sets
├── rule_packs/*.yaml
├── frontend/                 ← no-build UI + icons
└── tests/                    ← 28 tests + a mock LLM server
```

---

## Tests

```bash
python tests/test_pipeline.py    # 18 — maths, sanitisers, fallbacks, hard gate
python tests/test_providers.py   #  5 — all provider adapters
python tests/test_logging.py     #  5 — log levels and the progress bus
MOCK_STUBBORN=1 python tests/run_e2e.py
```

The E2E run uses a **deliberately stubborn mock model** that writes markdown, gets
amounts wrong by 100×, and refuses to fix its penalty clause — and asserts the document
still reaches 100% with no markdown or bad amounts leaking through.

---

<div align="center">

**PraroopAI (प्रारूप)** — *Built for Uttarakhand.* · MIT Licensed

</div>
