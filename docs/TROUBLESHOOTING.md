# Troubleshooting

## "It looks stuck after step 2 (Derive)"

It is drafting, not stuck. PraroopAI makes **one LLM call per section** because
small models produce far better output on narrow tasks.

| Document | Sections | LLM calls (worst case) |
|---|---|---|
| RFP | 7 | ~18 |
| DPR | 11 | ~26 |

On `qwen2.5:1.5b` a full run is typically **1-3 minutes**. The UI shows a
progress bar, a **Live Log** tab and an elapsed timer.

Make it faster:

```ini
SECTION_RETRIES=1        # halves the worst case
LLM_MAX_TOKENS=900
MAX_REVIEW_LOOPS=2
```

---

## Turning on logs

```ini
LOG_LEVEL=DEBUG          # or TRACE for full prompts + replies
```

```
[draft] start - 7 RFP sections, up to 14 LLM calls
-> draft:1. Scope of Work | ollama/qwen2.5:7b | prompt 1446 chars
<- draft:1. Scope of Work | 0.5s | 359 chars
[draft] 1/7 1. Scope of Work    0.5s  359 chars
```

---

## Document quality problems

### Literal `**bold**` markers in the text
Fixed. Section bodies pass through `strip_markdown_emphasis()` before storage,
so both the UI and the exported DOCX are clean.

### Wrong amounts, e.g. "Rs200 crore" on a Rs2 crore project
Fixed. Every section passes through `fix_amounts()`, which rewrites money
mentions to the **canonical** figures computed by the derivation engine. A
power-of-ten slip is detected and corrected; an amount that matches nothing
canonical is left untouched (we never invent a figure).

### Compliance stuck at 88% with PEN-002 / PEN-004 open
Fixed. Some clauses are formulae, not prose. If the reviewer LLM cannot satisfy
a deterministic rule, the clause is **built in code** from the statutory config
(`agents/fallbacks.py`). The trace shows the attribution honestly:

```
Fixed: risk_analysis, outcomes (AI); sla, penalty, data_security (rule-built)
```

Sections that can be rule-built: `penalty`, `sla`, `data_security`, `payment`.

### Prose is thin
`qwen2.5:1.5b` runs but writes shallow text. Use a bigger model:

```bash
ollama pull qwen2.5:14b
```
```ini
LLM_MODEL=qwen2.5:14b
LLM_MAX_TOKENS=2000
```

---

## Other

**Red/grey LLM dot** — `GET /api/health` says why. Usually Ollama is not
running, or the model is not pulled (health reports the exact `ollama pull`
command), or a provider key is missing.

**`LLM TIMEOUT after 120s`** — raise `LLM_REQUEST_TIMEOUT=300` or use a
smaller model.

**`UnicodeDecodeError` on Windows** — your `.env` was saved in a non-UTF-8
encoding. Recreate it with `copy .env.example .env`.

```bash
curl http://localhost:8000/api/health     # engine, provider, model, LLM call stats
curl http://localhost:8000/api/rulepacks
```
