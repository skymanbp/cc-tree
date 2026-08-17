# Cross-preset chaining

> Language: English (canonical). Chinese: [`docs/chaining.zh.md`](chaining.zh.md).

A natural workflow runs several presets in sequence, piping each stage's
best output into the next:

> **brainstorm** (what could we do?) → pick top-K → **design** each into
> concrete options → pick the winner → **attack** the winner before
> committing.

`tree-chain` ([`commands/tree-chain.md`](../commands/tree-chain.md))
automates that pipeline; this document defines the **handoff contract**
each stage relies on, so you can also chain by hand or build your own
pipeline.

## The handoff contract

Every preset writes a **primary deliverable** of `advances`-verdict
leaves (`docs/ENGINE.md` §7.2), sorted by the preset's own declared
ranking key — score desc for `brainstorm` / `design`, severity desc
for `attack`, severity × exploit-likelihood desc for `code-audit`
(each preset's `output_artifacts` comment is authoritative):

| Preset | Primary deliverable | Each entry is a… | Sorted by |
|---|---|---|---|
| brainstorm | `shortlist.md` | research idea / direction | score desc |
| design | `options.md` | design option | score desc |
| attack | `confirmed.md` | confirmed critique | severity desc |
| code-audit | `findings.md` | confirmed finding | severity × exploit-likelihood desc |

How the next stage consumes that file depends on its preset's
`root_kind` — see **Root vs seeds** below. For `topic` /
`design-prompt` stages it's `--seed-from <primary.md>`
(`docs/ENGINE.md` §2.3): each listed item becomes a depth-1 seed node
and is re-expanded.

**An entry is a section, not a line.** A deliverable is a ranked list of
`## <id> — <subject statement>` sections, each carrying the fields that
preset's `output_artifacts` comment promises — not one item per physical
line. Reading a deliverable therefore means splitting on its level-2
headings and taking the subject statement of each; a naive head-N over
lines would slice a single item's body in half.

### Top-K extraction

`tree-chain` takes the **top-K by the deliverable's own ranking key**
from each stage's primary deliverable (default K=3) and carries them
into the next stage. Because each deliverable is sorted by its
declared key, "top-K" is the first K *entries* in that heading order.
The dropped tail is reported (never silently truncated —
`docs/ENGINE.md` §F7 spirit): the chain log states "seeded 3 of 11;
dropped 8 below the cut".

### Language propagation

`tree-chain` resolves `--lang <tag|auto>` exactly once before stage 1. It then
passes the resulting concrete `output_language` tag—not `auto`—to every stage,
per-item sub-run, and framing sub-agent. Omitted `--lang` resolves to `en`;
`auto` uses the first stage's primary invocation/root content and follows the
fallback rules in [`ENGINE.md`](ENGINE.md) §1.0. Later artifacts never trigger a
second detection pass, so one chain cannot drift between languages.

`CHAIN_REPORT.md` records `language_request`, `output_language`, and
`language_source` alongside per-stage status. A resumed chain reuses the
recorded concrete tag. A conflicting explicit tag stops before another stage
runs with `EARLY_STOP=language_mismatch`; legacy chain output without language
metadata is treated as English. Machine keys, statuses, verdict labels,
filenames, paths, and code remain canonical English even when human-readable
stage reports use another language.

### Root vs seeds in the next stage

- **brainstorm → design**: run `design` with `--seed-from
  shortlist.md` (no fresh root needed — `docs/ENGINE.md` §2.3 allows
  a seeded run to start "instead of a fresh root"). Each seeded idea
  enters as a depth-1 seed node and is expanded into concrete
  options; the idea's `predictions` / `assumptions` carry into the
  option nodes' goals/constraints. The design preset's own
  `goal_statement` / `hard_constraints` root fields are **derived
  from the seeds and the prior run's root** in this mode rather than
  triggering `EARLY_STOP=root_underspecified` — see
  [`presets/design.md`](../presets/design.md) §2. Without that
  carve-out the default chain would stop at stage 2.
- **design → attack**: the chosen option file (its `option_<id>.md`,
  with `mechanism` + `trade_offs`) is passed as the attack stage's
  **root artifact** — attack's `root_kind` is `artifact`, so the
  option is the thing under critique, not a seed. (`--seed-from`
  into attack is reserved for seeding *critiques*, e.g. from a prior
  review report via `--from-prior`.)
- **anything → code-audit**: only meaningful when a stage produced
  actual code paths (passed as the `code` root); otherwise skipped
  with a logged reason.

## Worked example

```bash
# 1. Diverge on directions
/cc-tree:brainstorm "ways to cut our API p99 latency" --width 30
#    → brainstorm-out/<ts>__.../shortlist.md  (11 ideas, score-sorted)

# 2. Design the top 3 ideas into concrete options
/cc-tree:design --seed-from brainstorm-out/<ts>__.../shortlist.md
#    → design-out/<ts>__.../options.md

# 3. Attack the single best option before committing
/cc-tree:attack ./design-out/<ts>__.../option_<id>.md
```

`tree-chain` runs those three steps for you, threading the outputs:

```bash
/cc-tree:tree-chain "ways to cut our API p99 latency" \
    --stages brainstorm,design,attack --top-k 3
```

## What chaining is NOT

- **Not** a re-validation pass. Seeds enter as accepted (`advances`);
  the point is the sub-tree grown beneath them, not re-judging them
  (`docs/ENGINE.md` §2.3 + §9 "re-list known issues" anti-pattern).
- **Not** automatic convergence across stages. Each stage converges
  independently (§6); `tree-chain` just sequences them and applies the
  top-K cut between stages.
- **Not** per-stage language detection. The chain resolves once, propagates one
  concrete tag, and records it in `CHAIN_REPORT.md`.
- **Not** lossless. The top-K cut deliberately drops low-score tail
  items. The cut is always logged so the loss is visible.
