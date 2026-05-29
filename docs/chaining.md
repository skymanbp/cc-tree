# Cross-preset chaining

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
leaves, sorted by score (`docs/ENGINE.md` §7.2):

| Preset | Primary deliverable | Each line is a… |
|---|---|---|
| brainstorm | `shortlist.md` | research idea / direction |
| design | `options.md` | design option |
| attack | `confirmed.md` | confirmed critique |
| code-audit | `findings.md` | confirmed finding |

The next stage consumes that file via
`--seed-from <primary.md>` (`docs/ENGINE.md` §2.3): each listed item
becomes a depth-1 seed node and is re-expanded. No reformatting is
needed — the deliverables are already line-per-item.

### Top-K extraction

`tree-chain` takes the **top-K by score** from each stage's primary
deliverable (default K=3) and seeds them into the next stage. Because
deliverables are score-sorted, "top-K" is just the first K items. The
dropped tail is reported (never silently truncated — `docs/ENGINE.md`
§F7 spirit): the chain log states "seeded 3 of 11; dropped 8 below the
cut".

### Root vs seeds in the next stage

- **brainstorm → design**: each seeded idea becomes a design *prompt*.
  The chain wraps it as `design`'s `design-prompt` root, carrying the
  idea's `predictions` / `assumptions` as goals/constraints.
- **design → attack**: the chosen option's `options.md` entry (with its
  `mechanism` + `trade_offs`) is the artifact the attack stage targets.
- **anything → code-audit**: only meaningful when a stage produced
  actual code paths; otherwise skipped with a logged reason.

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
- **Not** lossless. The top-K cut deliberately drops low-score tail
  items. The cut is always logged so the loss is visible.
