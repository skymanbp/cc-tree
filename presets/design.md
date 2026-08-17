---
name: design
description: Design-space exploration tree. Each node is one design option (architecture / API / UX / process); 12 framings probe each option from multiple angles; every leaf resolves to RECOMMENDED (clearly best per stated criteria) / VIABLE (acceptable trade-offs) / NOT-RECOMMENDED (rejected with reasons) / NEEDS-MORE-INFO (must be driven to one of the above before convergence). Produces an options table with cost / reversibility / fit-with-constraints / evidence per option.
use-when: |
  - User says "design" / "design options" / "should we build X this
    way or that" / "trade-off table" / "architecture exploration" /
    "evaluate approaches"
  - User has a problem with multiple plausible solutions and wants
    a systematic comparison
  - User wants to surface "options we hadn't considered" before
    locking in an architecture

root_kind: design-prompt

subject_label: option

verdict_enum:
  advances: RECOMMENDED
  kept:     VIABLE
  pruned:   NOT-RECOMMENDED
  blocked:  NEEDS-MORE-INFO

convergence_metric: advances   # last 2 rounds' RECOMMENDED ratio drops below --min-novelty-ratio

score_dims:
  - {key: V, name: value,             desc: "Magnitude of benefit if this option ships. 0=marginal, 3=transformative."}
  - {key: R, name: reversibility,     desc: "Cost of changing direction later. 0=one-way door, 1=hard but possible, 2=annoying but doable, 3=trivially reversible."}
  - {key: C, name: cost,              desc: "Engineering + operational cost over the relevant time horizon, REVERSE-scored. 0=expensive, 3=cheap."}
  - {key: F, name: fit-with-constraints, desc: "How well does the option satisfy stated hard constraints? 0=violates a hard constraint, 3=satisfies all."}
  - {key: E, name: evidence-strength, desc: "Strength of evidence the option will actually work. 0=untested speculation, 3=already proven in similar context with file:line / URL reference."}

node_schema:
  - option_statement        # 1: ≤ 3 sentences naming the design option
  - parent_framing          # 2: §3.A–§3.L
  - mechanism               # 3: how it works (≥ 5 sentences or pseudocode / diagram-prose); no "implementation detail tbd"
  - assumptions             # 4: ≥ 3 explicit assumptions (about scale / team / dependencies / users)
  - predictions             # 5: ≥ 1 concrete observable consequence ("response p99 < 80ms at 10K req/s")
  - trade_offs              # 6: explicit list — what does this option SACRIFICE? at least 2 named sacrifices
  - prior_art               # 7: ≥ 2 examples of this option used in similar contexts, with URLs; WebFetch required
  - implementation_cost     # 8: engineer-hours estimate (rough but bounded — "1–2 weeks for 1 mid-level engineer", not "moderate")
  - operational_risks       # 9: ≥ 3 risks (data loss / scaling / vendor lockin / on-call burden) tagged
  - migration_path          # 10: how to migrate from current state to this option, in ≥ 3 ordered steps
  - external_dependencies   # 11: §3.X repos / services / specs needed; URLs
  - verdict_provisional     # 12: RECOMMENDED / VIABLE / NOT-RECOMMENDED / NEEDS-MORE-INFO

output_artifacts:
  primary: options.md       # RECOMMENDED options, sorted by score desc; includes the trade-off table
  secondary:
    viable: viable.md       # VIABLE alternatives (worth keeping in pocket)
    rejected: rejected.md   # NOT-RECOMMENDED with reasons (avoid re-proposing later)
    pending: pending.md     # NEEDS-MORE-INFO (should be empty at converged time)

glossary_paths:
  - DESIGN.md
  - CONTEXT.md
  - ADRs/
  - CLAUDE.md
---

# design preset

This preset configures the universal `tree` engine for
**design-space exploration**. Use it when there's a real
engineering / product / process decision with multiple plausible
options and the user wants a systematic option-by-option
comparison with trade-offs surfaced.

## §2 baseline (design-specific)

For each `<root>` (a design prompt — either a string or a `.md`
file with structured goals / constraints / context):

1. **Read the prompt fully.** If file: full `Read`. If string:
   parse for goal verbs, constraint qualifiers ("must / cannot /
   should / nice-to-have"), and audience signals.
2. **Read context.** `Read` (if present) `DESIGN.md`, `CONTEXT.md`,
   `ADRs/*.md`, `CLAUDE.md`. These supply the project's existing
   design language; new options should be expressed in compatible
   terms.
3. **Current state inventory.** `Glob` files relevant to the
   design area (e.g. for an auth-flow design, look for
   `src/auth/*`, `src/middleware/*`); `Read` the most central
   ones; build a "what exists today" picture.
4. **Industry / prior-art baseline.** `WebSearch` "<design area>
   architecture patterns" + "<design area> design tradeoffs"; for
   the top ≥ 3 results, `WebFetch` the actual page.
5. **Root node fields (6):**
   - **goal_statement**: 1 sentence; what's the design supposed
     to achieve, in user-observable terms?
   - **hard_constraints**: ≥ 3 with sources (regulatory, SLO,
     team-skill, budget, etc.)
   - **soft_preferences**: list (e.g. "prefer managed services
     over self-hosted when costs are within 2×")
   - **non_goals**: ≥ 2 explicit non-goals (avoids scope creep
     attacks on options)
   - **current_state_summary**: 1 paragraph with file:line
     evidence of relevant existing code / docs
   - **prior_art_observed**: list of related implementations
     found in baseline step 4 above (the industry / prior-art
     `WebSearch` + `WebFetch` sweep), with URLs

If `goal_statement` or `hard_constraints` are empty, **stop** with
`EARLY_STOP=root_underspecified`. A design exploration without
clear goals or constraints is a fishing expedition; force the user
to sharpen first.

**Seeded runs (`--seed-from`, `docs/ENGINE.md` §2.3) fill these two
fields rather than hard-stopping on them.** This is the stage-2 case
of the shipped `brainstorm,design,attack` chain, which invokes
`/cc-tree:tree --preset design --seed-from <prev>/shortlist.md` with
no fresh `<root>` — an unconditional stop would make the default
pipeline in [`docs/chaining.md`](../docs/chaining.md) unreachable.
Derive `goal_statement` from the seeding run's root subject, and
`hard_constraints` from the seed items' `assumptions` plus the
constraints recorded in the prior run's `REPORT.md`; cite each with
the `file:line` of the seed file it came from. Only if that
derivation still leaves either field empty does the stop apply. The
seed *items* themselves are never re-validated (§2.3) — this fills
the root that frames them.

## §3 framing flavors

Most framings translate directly from the brainstorm flavors, with
design-specific notes:

- **§3.B Inversion.** "What if we did the opposite of the obvious
  approach?" — useful for surfacing build-vs-buy and
  monolithic-vs-distributed alternatives.
- **§3.C Cross-disciplinary.** Look at how other industries solve
  structurally similar problems (e.g. financial settlement systems
  for any "transactional consistency" design).
- **§3.E Constraint variation.** *The* hottest framing for design —
  relaxing or tightening one hard constraint usually opens an
  option that looked impossible.
- **§3.H Office-hours 6Q.** Especially Q4 (minimum wedge) and Q5
  (prior art) — most design exercises fail by over-scoping.
- **§3.K High-risk asymmetric.** Force ≥ 1 "abandon the framing
  and use a managed service / vendor solution / nothing at all"
  candidate per pass. Often the right answer.
- **§3.L Meta.** Specifically: am I avoiding options that require
  organizational change (hiring / re-orging / process changes)
  vs technical change? Design that requires only code change is
  often the wrong answer.

## Verdict mapping detail

- `score ≥ 11` AND no violated hard constraint (F = 0) →
  **RECOMMENDED**
- `8 ≤ score ≤ 10` AND no violated hard constraint → **VIABLE**
- `score ≤ 7` OR any violated hard constraint → **NOT-RECOMMENDED**
  (this preset's `pruned` role; record the reason in the verdict —
  what would need to change to lift this to VIABLE)
- Any field marked `[NEEDS_VERIFICATION]` dominating →
  **NEEDS-MORE-INFO**; the engine must obtain the missing info
  (WebFetch / Read / Bash benchmark / clarify with stakeholder)
  before §6 convergence

## Trade-off table (the primary deliverable)

`options.md` includes a comparison table:

```
| Option | V | R | C | F | E | Total | Cost (hrs) | Reversibility | Top trade-off |
|---|---|---|---|---|---|---|---|---|---|
| Option A | 3 | 2 | 2 | 3 | 3 | 13 | 80–120 | "Easy" | "Higher vendor lock-in" |
| Option B | 2 | 3 | 3 | 3 | 2 | 13 | 40–80  | "Easy" | "Lower V (smaller benefit)" |
| ...
```

Plus per-option `option_<id>.md` files with the full §4 fields.

## Preset anti-patterns (additional)

- ❌ "Option X looks best because it's modern / standard / trendy"
  — `evidence-strength` is 0 unless the option has been used in a
  *similar* context with a citable outcome.
- ❌ Skipping `migration_path` because "we'll figure it out" —
  forces the engine to confront whether the option is actually
  reachable from current state.
- ❌ "Cost: moderate" / "Low effort" — refuse; force bounded
  estimates ("1–2 weeks for 1 mid-level engineer" or "3 engineer-
  months for the platform team").
- ❌ Recommending an option that violates a stated hard constraint
  (engine auto-downgrades to NOT-RECOMMENDED even if score ≥ 11).

## Suggested invocations

```bash
# Design exploration from a string prompt
/cc-tree:design "auth flow for our internal admin tool serving 12 engineers, must integrate with Google Workspace SSO, budget ~2 engineer-weeks"

# From a structured design-prompt file
/cc-tree:design ./docs/auth-design-prompt.md

# Capped run
/cc-tree:design ./prompt.md --width 12 --depth 2
```

## What "done" looks like

- `<out>/options.md` — RECOMMENDED options with the trade-off
  table and per-option detail.
- `<out>/viable.md` — alternatives worth keeping in mind if
  RECOMMENDED ones don't work out.
- `<out>/rejected.md` — NOT-RECOMMENDED options with reasons
  (avoid re-proposing later).
- `<out>/tree.md` / `tree.json` — full exploration tree.
- `REPORT.md` final-report block.
- If `pending.md` (NEEDS-MORE-INFO) is non-empty at termination,
  the run is INVALID — engine continues.
