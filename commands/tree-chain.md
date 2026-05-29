---
description: Cross-preset chaining — run several cc-tree presets in sequence, piping each stage's top-K primary deliverable into the next via --seed-from. The canonical pipeline is brainstorm → design → attack (diverge on directions, design the best into options, attack the winner before committing). Each stage converges independently; the top-K cut between stages is always logged, never silent.
argument-hint: "<root> [--stages brainstorm,design,attack] [--top-k N] [--width N|∞] [--depth N|∞] [--out <dir>] [--field <name|path>] [--no-online] — `<root>` seeds the FIRST stage; later stages are seeded from the prior stage's primary deliverable"
---

Run a chain of `cc-tree` presets, threading each stage's primary
deliverable into the next. Engine spec for the per-stage run is
[`docs/ENGINE.md`](../docs/ENGINE.md); the handoff contract is
[`docs/chaining.md`](../docs/chaining.md).

## Defaults

- `--stages` defaults to `brainstorm,design,attack`.
- `--top-k` defaults to `3` (how many `advances` leaves carry forward
  between stages).
- `--out` defaults to `chain-out/<UTCdate>__<slug>/`, with each stage
  written to a `stageN-<preset>/` subdirectory.

## Procedure

For stage `i` in `--stages` (in order):

1. **Stage 1** runs `/cc-tree:tree <root> --preset <stage1>` with the
   shared flags (`--width` / `--depth` / `--field` / `--no-online` /
   `--out chain-out/.../stage1-<preset>/`).
2. **Each later stage** runs
   `/cc-tree:tree --preset <stage_i> --seed-from <prev>/<primary>.md`
   where `<primary>` is the prior stage's deliverable
   (`shortlist.md` → design's seed; `options.md` → attack's seed; see
   the table in [`docs/chaining.md`](../docs/chaining.md)).
3. Before seeding, take the **top-`--top-k` by score** from the prior
   deliverable (it is already score-sorted, so this is the first K
   lines). **Log the cut**: "stage i seeded K of M; dropped M−K below
   the cut" — never truncate silently.
4. If a stage's primary deliverable is empty (prior stage found nothing
   to advance), **stop the chain** and report which stage went dry; do
   not fabricate seeds.

## Output

```
chain-out/<UTCdate>__<slug>/
├── stage1-brainstorm/   # full tree + shortlist.md
├── stage2-design/       # full tree + options.md (seeded from stage1)
├── stage3-attack/       # full tree + confirmed.md (seeded from stage2)
└── CHAIN_REPORT.md      # per-stage status, top-K cuts, final deliverable
```

`CHAIN_REPORT.md` lists, per stage: termination status (CONVERGED /
cap), leaf count, the top-K carried forward, and the dropped tail.

## Example

```
/cc-tree:tree-chain "ways to cut our API p99 latency" --stages brainstorm,design,attack --top-k 3
```

This is a thin orchestration wrapper: each stage is a normal
`/cc-tree:tree` run and obeys every engine rule (§0–§9). Chaining adds
only the sequencing and the logged top-K handoff — it never relaxes a
per-stage convergence or completeness rule.
