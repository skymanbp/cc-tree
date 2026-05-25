---
name: attack
description: Adversarial critique tree for a finished artifact (document / argument / proposal / design). Each node is one critique; 12 framings attack the artifact from multiple reviewer perspectives; every leaf resolves to CONFIRMED (file:line evidence + concrete fix) / REFUTED (file:line of artifact's defense) / MARGINAL (depends on interpretation). Hard ban on NEEDS-MORE-INFO leftover; engine must drive every blocked critique to one of the three terminal verdicts.
use-when: |
  - User says "attack" / "adversarial review" / "find what's wrong"
    / "what would a reviewer pick at" / "audit this" / "rebuttal prep"
  - User has a finished artifact (paper / proposal / design doc /
    argument) and wants to surface the strongest counter-arguments
    before submission
  - User wants to find open-ended issues a static checklist would
    miss

root_kind: artifact

subject_label: critique

verdict_enum:
  advances: CONFIRMED
  kept:     MARGINAL
  pruned:   REFUTED
  blocked:  INCOMPLETE_FORBIDDEN

convergence_metric: advances   # last 2 rounds' CONFIRMED ratio drops below --min-novelty-ratio (note: REFUTED nodes are *good*, not bad)

score_dims:
  - {key: S, name: severity,           desc: "If this critique holds, how badly does it hurt the artifact? 0=cosmetic, 1=minor, 2=substantive, 3=fatal (central claim invalid)."}
  - {key: P, name: specificity,        desc: "Critique localization precision. 0=vague 'the paper is unclear', 1=section-level, 2=paragraph-level, 3=file:line + concrete substitution."}
  - {key: R, name: reproducibility,    desc: "Could another reviewer independently arrive at this critique? 0=pure subjective, 1=requires reading style, 2=clear from text, 3=mechanically reproducible (grep + arithmetic)."}
  - {key: F, name: fixability,         desc: "If CONFIRMED, how hard is the fix? 0=requires rewriting whole sections, 3=change one line / add one sentence."}
  - {key: B, name: sub-critique-fan-out, desc: "If this critique holds, how many sub-critiques does it open? 0=isolated, 3=systemic (touches multiple chapters)."}

node_schema:
  - critique_statement      # 1: ≤ 3 sentences, one specific attack
  - parent_framing          # 2: §3.A–§3.L
  - artifact_position       # 3: file:line + Read-verified quoted excerpt
  - evidence                # 4: full argument chain + ≥ 1 of (artifact quote / external ref / data check)
  - assumptions             # 5: ≥ 2 explicit premises the critique depends on
  - predictions             # 6: if critique holds, where does the artifact self-contradict / fail to reproduce / disagree with prior?
  - artifact_defense        # 7: Grep+Read across ≥ 5 sections; "no defense found in §X, §Y, §Z" is acceptable but must explicitly list sections checked
  - alternative_interpretations # 8: ≥ 2 "I might be misreading" paths; each tested against text
  - proposed_fix            # 9: concrete change (specific line / equation / new clarification) — no "author should reconsider"
  - external_check          # 10: §3.X repro / data verification / literature confirm; --no-online may leave partial
  - sub_critique_potential  # 11: ≥ 2 hints for next-round expansion
  - verdict_provisional     # 12: CONFIRMED / MARGINAL / REFUTED / INCOMPLETE_FORBIDDEN

output_artifacts:
  primary: confirmed.md     # CONFIRMED critiques, sorted by severity desc (the actionable list)
  secondary:
    marginal: marginal.md   # MARGINAL critiques (author judgment needed)
    refuted: refuted.md     # REFUTED critiques (positive record — artifact already handles this attack angle; useful for rebuttal prep)

glossary_paths:
  - FACTS.md
  - glossary.md
  - CLAUDE.md
---

# attack preset

This preset configures the universal `tree` engine for
**adversarial critique** of a finished artifact. Use when an
artifact is ready and the user wants to surface the strongest
reviewer-style attacks before they hit a real review.

## §2 baseline (attack-specific)

For each `<root>` (a file path to the artifact):

1. **Full read.** `Read` the entire artifact. If > 2000 lines, use
   `offset` / `limit` chunks until the whole file has been read —
   no skim, no sampling. Critique is a global+local property.
2. **Focus narrowing (if `--focus <id>`).** `Grep + Read` to narrow
   root to the named section / claim / equation; retain ± 20 lines
   of context so the engine can detect "the artifact addresses
   this critique elsewhere".
3. **Project context.** `Read` `CLAUDE.md` + `README.md` if present
   → know the domain / project background; informs §3.C (cross-
   disciplinary reviewer perspectives) and §3.I (contrarian, which
   field-mainstream assumptions are at stake).
4. **Domain reference base.** `Read` the artifact's `references.bib`
   (if it has one) — the literature it knows about. Useful for §3.D
   "does the artifact cite the work it should be reacting to?" and
   §3.G substitution attacks.
5. **`--from-prior <path>` (optional).** If supplied: `Read` the
   prior review report; extract any items marked CONFIRMED as
   *seed critiques* at depth-1; recurse on each with full §3 to
   find sub-critiques. Don't re-validate already-CONFIRMED items.
6. **Root node fields (5):**
   - **central_claim**: 1 sentence with file:line evidence; extract
     by triangulating abstract / introduction / conclusion.
   - **method_skeleton**: 1 sentence with file:line.
   - **key_evidence**: list of core figures / tables / equations
     with file:line.
   - **explicit_assumptions**: ≥ 3, each with file:line.
   - **implicit_assumptions**: ≥ 5 (the fertile ground for
     critiques); extracted via §3.A first-principles framing.

If any of the 5 root fields can't be filled, **stop** and report
`EARLY_STOP=root_underspecified` (artifact too short / format
broken / claim unclear). Do not synthesize.

## §3 framing flavors

See [`docs/framings.md`](../docs/framings.md) §3.A–§3.L — the
attack flavor examples there are the canonical ones.

Notable preset-specific notes:

- **§3.D (adversarial red team)** is the hottest pass for this preset
  — the 3 most damaging counter-arguments per node are the standard
  expectation, not a stretch.
- **§3.K (high-risk fatal critique)** must produce ≥ 1 "if true, this
  is a retraction-level problem" candidate per pass. Most will land
  at REFUTED after derivation — that's the point.

## Verdict mapping detail

- **REFUTED first.** If the engine finds `artifact_defense` content
  that adequately addresses the critique, the verdict is REFUTED
  **regardless of severity score**. This is *valuable* — a REFUTED
  critique documents that the artifact handles a possible attack
  angle, useful for rebuttal preparation.
- Otherwise:
  - `score ≥ 11` AND `artifact_defense = empty/insufficient` →
    **CONFIRMED**
  - `8 ≤ score ≤ 10` AND `artifact_defense` partially addresses →
    **MARGINAL** (author-judgment list)
  - `score ≤ 7` → effectively DEAD-END; greyed; not in `refuted.md`
    (since the artifact's "defense" wasn't even tested) but kept in
    `tree.md` for non-duplication.
- Any field with `[NEEDS VERIFICATION]` dominating →
  **INCOMPLETE_FORBIDDEN** (engine must drive to one of the above).
  NEEDS-MORE-INFO is NOT a permitted terminal state for attack
  (differs from brainstorm).

## CONFIRMED-without-fix is impossible

A CONFIRMED critique must have a concrete `proposed_fix`. Without it,
the verdict downgrades to MARGINAL. A CONFIRMED node is by definition
an actionable item; "author should reconsider this" is not actionable.

## Preset anti-patterns (additional)

- ❌ Vague critique like "the paper's logic is unclear" — must point
  to a specific premise → conclusion link that fails.
- ❌ Reporting a critique without checking `paper_defense` across ≥ 5
  major sections — many critiques are actually REFUTED by something
  the engine just hadn't read yet.
- ❌ Discarding REFUTED nodes as "noise" — they're a positive record;
  keep them in `refuted.md`.
- ❌ Re-listing already-CONFIRMED items from `--from-prior <report>`
  as new critiques — the point of `--from-prior` is sub-critique
  expansion, not duplication.
- ❌ "Defer NEEDS-MORE-INFO; let the author respond" — forbidden for
  this preset (engine must terminate every node).

## Suggested invocations

```bash
# Audit a paper
/cc-tree:attack ./paper.tex

# Audit one section / claim
/cc-tree:attack ./paper.tex --focus "Section 4.2"

# Audit + join with an existing static review
/cc-tree:attack ./paper.tex --from-prior ./paper-review-report.md

# Cap the run for time-sensitivity
/cc-tree:attack ./paper.tex --width 30 --depth 3
```

## What "done" looks like

- `<out>/confirmed.md` — primary deliverable; CONFIRMED critiques
  with severity / position / proposed fix, sorted by severity desc.
  This is the to-fix list.
- `<out>/marginal.md` — author-judgment list.
- `<out>/refuted.md` — positive record (rebuttal-prep gold).
- `<out>/tree.md` / `tree.json` — full evidence trail.
- `REPORT.md` final-report block (with §0.8 self-audit confirming
  zero `INCOMPLETE_FORBIDDEN` nodes).
