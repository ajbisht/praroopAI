# Troubleshooting

## "It looks stuck after step 2 (Derive)"

It is almost certainly **not stuck — it is drafting**.

PraroopAI makes **one LLM call per section** because small models produce far
better output on narrow, focused tasks. That means:

| Document | Sections | LLM calls (worst case) |
|---|---|---|
| RFP | 7 | 1 intake + 14 draft + 3 review ≈ **18** |
| DPR | 11 | 1 intake + 22 draft + 3 review ≈ **26** |

On `qwen2.5:1.5b` each call is a few seconds, so a full run is typically
**1–3 minutes**. The UI now shows a **progress bar**, a **Live Log tab** and an
**elapsed timer**, so you can see exactly which section is being written.

### Make it faster

```ini
# .env
SECTION_RETRIES=1        # halves the worst case (default 2)
LLM_MAX_TOKENS=900       # shorter sections generate quicker
MAX_REVIEW_LOOPS=2       # fewer critique rounds
```

Or start with an **RFP** (7 sections) rather than a DPR (11) while testing.

---

## Turning on logs

```ini
# .env
LOG_LEVEL=DEBUG
```

| Level | Shows |
|---|---|
| `TRACE` | everything, **including full prompts and full model replies** |
| `DEBUG` | every LLM call with timing, sizes and a response preview |
| `INFO` | pipeline milestones (default) |
| `WARNING` | only problems |

`DEBUG` output looks like this:

```
10:29:19 INFO  praroopai.agents  [draft] start - 7 RFP sections, up to 14 LLM calls
10:29:19 INFO  praroopai.llm     -> draft:1. Scope of Work | ollama/qwen2.5:1.5b | prompt 1446 chars
10:29:19 INFO  praroopai.llm     <- draft:1. Scope of Work | 0.5s | 359 chars
10:29:19 INFO  praroopai.agents  [draft] 1/7 1. Scope of Work    0.5s  359 chars
```

Use `TRACE` when a section comes out wrong and you need to see the exact prompt.

---

## Common problems

### Badge shows a red/grey dot next to the model name

`GET /api/health` tells you why. The usual causes:

* **Ollama not running** → start it, then reload the page.
* **Model not pulled** → health reports
  `Model 'qwen2.5:7b' not found in Ollama. Run: ollama pull qwen2.5:7b`.
* **Wrong provider key** → e.g. `OPENAI_API_KEY missing`.

### A section is empty / "came back empty" in the Live Log

The model returned nothing for that section. The compliance critic will flag it
and the reviewer will usually write it — that is the loop working as designed.
If it happens for many sections, the model is too small or `LLM_MAX_TOKENS` is
too low.

### `LLM TIMEOUT after 120s`

Raise the limit or use a smaller model:

```ini
LLM_REQUEST_TIMEOUT=300
```

### Document quality is thin

`qwen2.5:1.5b` runs but writes shallow prose. For documents that read like real
government drafts use **`qwen2.5:7b`** or **`14b`**:

```bash
ollama pull qwen2.5:14b
```
```ini
LLM_MODEL=qwen2.5:14b
LLM_MAX_TOKENS=2000
```

### `UnicodeDecodeError` on Windows

Your `.env` was saved in a non-UTF-8 encoding. Either recreate it with
`copy .env.example .env`, or in VS Code use *Save with Encoding → UTF-8*.
(The loader already tolerates stray bytes, so this should not recur.)

---

## Useful endpoints

```bash
curl http://localhost:8080/api/health      # engine, provider, model, tuning, call stats
curl http://localhost:8080/api/rulepacks   # active rule-packs and versions
curl http://localhost:8080/api/structure/DPR
```

`/api/health` also returns cumulative LLM stats (`calls`, `errors`,
`total_seconds`) which is the quickest way to confirm the model is responding.
