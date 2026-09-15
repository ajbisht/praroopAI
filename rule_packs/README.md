# Rule-Packs — the bounded "knowledge" of PraroopAI

Small, public, **versioned YAML** files. The source of truth for what makes an
RFP/DPR compliant. Not a document corpus — each entry is a check both the
Compliance Agent and the deterministic validators evaluate.

## Anatomy of a rule
```yaml
- id: PEN-001                 # stable id (cited in findings)
  title: "..."               # human title
  applies_to: [RFP, DPR]     # which document types
  check: "ld_percent <= 10"  # boolean expression over the project context
  severity: mandatory        # mandatory = hard gate | recommended
  message: "..."             # shown when the check fails
  fix_hint: "..."            # how the Reviewer/officer can fix it
```

## Adding / updating a pack
1. Add or edit a `*.yaml` file here.
2. Bump the `version`.
3. Add a test in `tests/test_pipeline.py`.
4. Never reuse an `id` — findings cite it.

## Available context variables (checks can reference)
project_cost, emd_percent, pbg_percent, ld_percent, uptime_percent,
grace_period_days, milestone_payments_sum_ok, every_milestone_has_penalty,
tender_mode_ok, data_residency_ok, has_section_scope, has_section_eligibility,
has_section_evaluation, has_section_data_security, has_section_sla,
has_section_payment, has_section_penalty
