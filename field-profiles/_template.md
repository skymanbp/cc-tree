---
field: _template   # CHANGE THIS to your file's basename — the validator requires field == basename
description: Domain-neutral starting point for a cc-tree field profile. Copy to <your-field>.md and fill in.
---

# `<your-field>` field profile

> A field profile gives the engine domain-aware reviewer weighting
> (loaded via `--field <name|path>`, see
> [`docs/ENGINE.md` §2.2](../docs/ENGINE.md#22-field-profile-optional---field-namepath)).
> It does **not** relax any universal rule — it only re-prioritizes
> which branches the 12 framings explore first. Keep every list short
> and concrete; vague entries ("be rigorous") add no weighting signal.

## Reviewer concerns — feeds §3.C (cross-disciplinary) + §3.D (red team)

What does a senior reviewer in this field reliably attack first? List
the recurring failure-patterns they look for, each phrased as a
checkable concern.

- <e.g. "data leakage across the train/test split">
- <e.g. "multiple-hypothesis testing without correction">
- <e.g. "effect size reported without confidence interval">

## Field consensuses — feeds §3.I (contrarian)

What does the field currently take for granted that a result might
quietly depend on? For each, name the regime where it is known (or
suspected) to break.

- <consensus> — breaks when <regime>
- <consensus> — breaks when <regime>
- <consensus> — breaks when <regime>

## Common failure modes — feeds §3.J (failure-driven)

Concrete, recurring ways work in this field goes wrong in practice
(not hypotheticals).

- <e.g. "pipeline silently drops rows with missing covariates">
- <e.g. "baseline tuned harder than the proposed method">

## Evidence bar — feeds §3.X (external check) + §4 citations

What counts as *strong* evidence in this field, versus weak/anecdotal?
The engine raises its citation standard to match.

- Strong: <e.g. "pre-registered replication on an independent cohort">
- Weak (insufficient on its own): <e.g. "single-run result, no error bars">
