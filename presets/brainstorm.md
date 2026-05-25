---
name: brainstorm
description: Divergent ideation / research-direction explorer. Builds a phylogenetic tree of ideas from a topic-shaped root, applying 12 framings per node and recursing on PROMISING leaves until §6 substantive convergence. Use for exhaustive exploration of research directions, problem-solving approaches, or "what could we do about X" style questions. Hard ban on "future-work / TODO / NEEDS-MORE-INFO" leaves — every direction must be fully derived.
use-when: |
  - User says "brainstorm" / "发散思考" / "find research directions" /
    "explore options" / "how could we solve X" / "what are all the ways"
  - User wants an exhaustive radial exploration of a problem space
  - Need to surface unexplored research directions before drafting
    a paper / proposal
  - Need to enumerate solution paths to a concrete blocker

root_kind: topic

subject_label: idea

verdict_enum:
  advances: PROMISING
  kept:     MARGINAL
  pruned:   DEAD-END
  blocked:  NEEDS-MORE-INFO

convergence_metric: advances   # last 2 rounds' PROMISING ratio drops below --min-novelty-ratio

score_dims:
  - {key: S, name: scientific-value,  desc: "If this idea succeeded, how much would it move the field? 0=none, 1=incremental, 2=meaningful, 3=paradigm-level."}
  - {key: N, name: novelty,           desc: "How different from existing work? 0=fully done, 1=incremental, 2=meaningfully different, 3=not-yet-attempted."}
  - {key: F, name: feasibility,       desc: "Probability of completion within available resources (data, compute, time, skill). 0=infeasible, 3=already mostly ready."}
  - {key: K, name: falsifiability,    desc: "Clarity of the experimental / computational test that would refute the idea. 0=purely philosophical, 3=sharp predicted observable with error bars."}
  - {key: B, name: branch-potential,  desc: "If this succeeds, how many further sub-directions does it open? 0=dead end, 3=tree-shaped explosion."}

node_schema:
  - idea_statement          # 1: ≤ 3 sentences, single clear hypothesis
  - parent_framing          # 2: §3.A–§3.L (or §3.X / root)
  - derivation              # 3: full math / physics / mechanism chain — no "details omitted"
  - assumptions             # 4: ≥ 3 explicit assumptions the derivation depends on
  - predictions             # 5: ≥ 1 quantitative, falsifiable prediction with magnitude + error
  - falsifiability          # 6: what observation / computation would refute this?
  - novelty_vs_literature   # 7: ≥ 3 real refs with DOI/arXiv, each with a one-line difference statement
  - feasibility             # 8: 4 lines (data / compute / time / skill)
  - risks                   # 9: ≥ 3 risks, each tagged technical / scientific / resource
  - branch_potential        # 10: ≥ 2 sub-question hints for next-round expansion
  - external_resources      # 11: §3.X found repos / plugins / datasets (URLs); --no-online → empty
  - verdict_provisional     # 12: PROMISING / MARGINAL / DEAD-END / NEEDS-MORE-INFO

output_artifacts:
  primary: shortlist.md     # PROMISING leaves sorted by score desc
  secondary:
    pending: pending.md     # NEEDS-MORE-INFO list (should be empty at converged time)
    marginal: marginal.md   # MARGINAL leaves

glossary_paths:
  - FACTS.md
  - KEY_NUMBERS.md
  - glossary.md
  - CLAUDE.md
---

# brainstorm preset

This preset configures the universal `tree` engine for **divergent
ideation**. Use it when the user wants to *generate* new directions
— for research, problem-solving, or any open-ended "what could we
do" question.

## §2 baseline (brainstorm-specific)

Two modes auto-detected from the root:

### §2.A — Research mode

If `<root>` is empty or is an open-ended direction
(e.g. `"unexplored directions in weak gravitational lensing"`):

1. `Read` the current project's `CLAUDE.md`, `README.md` if present.
2. `Glob` `*.tex` / `*.md` drafts; `Read` the 3 most-recently-modified
   in full (smaller files entirely; larger files via offset/limit
   until full coverage); the rest as metadata only.
3. `Read` `references.bib` / `*.bib` if present — know what
   literature the project already cites.
4. `Bash git log --oneline -20` — recent work focus.
5. Synthesize root-node fields:
   - **current_research_topic**: one sentence with file:line evidence
   - **stable_work**: list of what's already done
   - **open_problems**: list of what's blocked or unresolved
   - **implicit_assumptions**: ≥ 5 assumptions extracted via §3.A
     first-principles framing

### §2.B — Problem-solving mode

If `<root>` is a specific problem statement
(e.g. `"how to improve secondary-peak SNR_resolved in low-mass halos"`):

1. Parse modifier words ("must", "cannot", "limited to") to extract
   hard constraints / soft preferences / success criteria.
2. `Grep` project for topic keywords; `Read` ≥ 1 hit per keyword in
   full.
3. `WebSearch` topic + `solution` / `benchmark` / `prior art`; for
   the top ≥ 3 hits, `WebFetch` the actual page.
4. Synthesize root-node fields:
   - **problem_statement**: one sentence with file:line / URL
   - **hard_constraints**: list with sources
   - **soft_preferences**: list
   - **already_tried**: list (project-internal + prior art)
   - **known_failure_modes**: explain *why* prior tries failed
   - **success_criteria**: concrete, verifiable; no "work better"

### Mode coexistence

If the root is both a research direction AND has a specific blocker,
do both bases and synthesize.

## §3 framing flavors

See [`docs/framings.md`](../docs/framings.md) §3.A–§3.L — the
brainstorm flavor examples there are the canonical ones for this
preset.

## Verdict mapping detail

- `score ≥ 11` AND no `[NEEDS VERIFICATION]` dominating → **PROMISING**
- `8 ≤ score ≤ 10` → **MARGINAL** (kept, no re-expand)
- `score ≤ 7` → **DEAD-END** (pruned)
- Any `[NEEDS VERIFICATION]` or `unverified` blocks dominate →
  **NEEDS-MORE-INFO** (= `INCOMPLETE_FORBIDDEN`; engine must
  drive to one of the above before §6 convergence)

## Preset anti-patterns (additional to [`ENGINE.md`](../docs/ENGINE.md) §9)

- ❌ "Branch X is promising, derivation deferred to future work" —
  forbidden by §F8; force completion.
- ❌ Inferring a `novelty_vs_literature` entry without `WebFetch`ing
  the actual arXiv abs or DOI page — `WebSearch` snippets don't
  count.
- ❌ Skipping §3.C cross-disciplinary because "this is a pure-physics
  problem" — pure-physics problems benefit from biology / economics
  / CS framings precisely because the field doesn't usually look
  there.
- ❌ Letting `--no-grill` slip in for a multi-noun root without
  the user explicitly setting it — terminology drift is the most
  common silent failure mode.

## Suggested invocations

```bash
# Research mode (no explicit topic — infer from project)
/cc-tree:brainstorm

# Research mode with explicit topic
/cc-tree:brainstorm "unexplored directions for substructure detection in stage-IV surveys"

# Problem-solving mode
/cc-tree:brainstorm "how to make our reconstruction stable at SNR < 3"

# With explicit caps for a quick run
/cc-tree:brainstorm "topic" --width 30 --depth 3
```

## What "done" looks like

A successful run produces:

- `<out>/tree.md` + `<out>/tree.json` — full tree with all 12 fields per node
- `<out>/shortlist.md` — PROMISING leaves sorted by score, each with a
  proposed first experiment
- `<out>/marginal.md` — MARGINAL leaves (worth revisiting later)
- `<out>/glossary-anchors.md` — root terms locked to glossary
- `REPORT.md` final-report block (also echoed to stdout)

If `pending.md` (NEEDS-MORE-INFO list) is non-empty at termination,
the run is INVALID and the engine must continue.
