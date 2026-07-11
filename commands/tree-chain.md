---
description: Cross-preset chaining — run several cc-tree presets in sequence, piping each stage's top-K primary deliverable into the next via --seed-from. The canonical pipeline is brainstorm → design → attack (diverge on directions, design the best into options, attack the winner before committing). Each stage converges independently; the top-K cut between stages is always logged, never silent. 中文触发：跨 preset 串联流水线，把每阶段 top-K 主产物喂给下一阶段。
argument-hint: "<root> [--lang <tag|auto>] [--stages brainstorm,design,attack] [--top-k N] [--width N|∞] [--depth N|∞] [--out <dir>] [--field <name|path>] [--no-online] — `<root>` feeds the FIRST stage; later stages consume the prior stage's primary deliverable (as seeds or as the root artifact, per docs/chaining.md 'Root vs seeds')"
---

Run a chain of `cc-tree` presets, threading each stage's primary
deliverable into the next. Engine spec for the per-stage run is
[`docs/ENGINE.md`](../docs/ENGINE.md); the handoff contract is
[`docs/chaining.md`](../docs/chaining.md).

**Language.** `--lang <tag|auto>` is resolved **once, before stage 1**
(default `en`; per [`docs/ENGINE.md §1.0`](../docs/ENGINE.md#10-output-language-resolution-and-schema-boundary)),
and the resulting concrete `output_language` is forwarded to every
stage, item sub-run, and framing sub-agent — later stages never
re-detect. Machine tokens stay English throughout; the resolved
language is recorded in `CHAIN_REPORT.md`.

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
2. **Each later stage** is wired per the handoff contract's
   "Root vs seeds" section in
   [`docs/chaining.md`](../docs/chaining.md), by the stage preset's
   `root_kind`:
   - **`topic` / `design-prompt` stages** (e.g. `design`): run
     `/cc-tree:tree --preset <stage_i> --seed-from <prev>/<primary>.md`
     — the carried-forward items enter as depth-1 seed nodes
     (`shortlist.md` → design's seeds).
   - **`artifact` / `code` stages** (e.g. `attack`, `code-audit`): run
     `/cc-tree:tree <item-file> --preset <stage_i>` once per
     carried-forward item file (e.g. `option_<id>.md`) — these presets
     critique an artifact, so the item is the **root**, not a seed.
3. Before the hand-off, take the **top-`--top-k` by the deliverable's
   own ranking key** from the prior deliverable (each deliverable is
   sorted by its declared key — see the contract table — so this is
   the first K lines). **Log the cut**: "stage i seeded K of M;
   dropped M−K below the cut" — never truncate silently.
4. If a stage's primary deliverable is empty (prior stage found nothing
   to advance), **stop the chain** and report which stage went dry; do
   not fabricate seeds.

## Output

```
chain-out/<UTCdate>__<slug>/
├── stage1-brainstorm/   # full tree + shortlist.md
├── stage2-design/       # full tree + options.md (seeded from stage1)
├── stage3-attack/       # full tree + confirmed.md (root = stage2's top
│                        #   option file; with --top-k > 1, one sub-run
│                        #   per carried option: stage3-attack/<option_id>/)
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
