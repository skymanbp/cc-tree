# cc-tree

A Claude Code plugin: **one universal radial-tree exploration engine, four
swappable presets**. Use it for divergent ideation, adversarial critique,
design-space exploration, or code audit — same engine, different vocabulary.

> Refactor of [`sci-paper`](https://github.com/skymanbp/sci-paper)'s
> `brainstorm` + `paper-attack-tree` skills, stripped of paper-specific
> anchors and parameterized via presets.

## The idea — a phylogenetic tree of thoughts

cc-tree treats *any* open-ended thinking task as a **phylogenetic tree
growing outward from one root**. The root is your input (a topic, a
document, a code path, a design prompt). Every node is expanded by the
**same 12 framing passes**, each child is fully derived and scored, and
only the high-value (`advances`) leaves get re-expanded — until the tree
reaches **substantive convergence**, not an arbitrary count.

```
        the tree grows OUTWARD from one root, like a phylogenetic tree

            depth 0           depth 1             depth 2 … (→ ∞)
          ┌────────┐       ┌──────────┐        ┌──────────────┐
          │  ROOT  │──12──▶ │  node    │──12──▶ │  leaf  ✓ adv. │  width =
          │ topic /│  fra-  │ (idea /  │  fra-  │  leaf  ✗ pruned│  # of
          │artifact│  mings │ critique/│  mings │  leaf  ~ kept  │  terminal
          │ / code │        │ option / │        │  leaf  ✓ adv.  │  leaves on
          │/design │──────▶ │ finding) │──────▶ │  leaf  ✗ pruned│  the outer
          └────────┘        └──────────┘        └──────────────┘  arc
                  └─ each node → 12 framings (§3.A–§3.L) → 12-field
                     derivation → score → verdict; only "advances"
                     leaves re-expand; stop on convergence, not on a count.
```

The per-node loop, precisely:

```mermaid
flowchart LR
    R([root<br/>topic · artifact · code · design]) --> F{{12 framing passes<br/>§3.A–§3.L}}
    F --> D[per-node 12-field derivation<br/>evidence · no hedging · no defer]
    D --> S[score 5 dims → verdict]
    S -->|advances| RE((re-expand<br/>this leaf))
    RE --> F
    S -->|kept / pruned| K[keep in tree,<br/>don't re-expand]
    S -->|blocked| B[INCOMPLETE_FORBIDDEN<br/>drive to completion]
    B --> D
    S --> C{§6 convergence?<br/>6 conditions all true}
    C -->|no| RE
    C -->|yes| OUT[/final report +<br/>tree.md · tree.json/]
```

Two properties make this more than "brainstorm in a loop": **(1)** every
leaf is fully derived with `file:line` / URL evidence — a hard ban on
`defer / future-work / TODO / NEEDS-MORE-INFO` leaves (§0.5); **(2)**
termination is *substantive convergence* (six simultaneous conditions),
never "ran out of patience".

## What it ships

### 1 skill

| Skill | What it does |
|---|---|
| `/cc-tree:tree` | Universal radial-tree engine. Loads a preset, builds the §2 baseline, then recursively applies 12 framing passes per node until **stable convergence** (no new high-verdict branches over the last 2 rounds + all 12 framings exercised + all leaves complete). Width × depth default to ∞; resource caps are opt-in. Hard ban on `defer / future-work / TODO / NEEDS-MORE-INFO` leaves. |

### 4 presets (`presets/<name>.md`)

| Preset | Use when | Verdict vocabulary (advances / kept / pruned / blocked) |
|---|---|---|
| `brainstorm` | Divergent ideation; surface unexplored research directions or exhaustive problem-solving paths | `PROMISING / MARGINAL / DEAD-END / NEEDS-MORE-INFO` |
| `attack` | Adversarial critique of a finished artifact (document, argument, design proposal); surface the most damaging reviewer-style attacks | `CONFIRMED / MARGINAL / REFUTED / INCOMPLETE_FORBIDDEN` |
| `design` | Design-space exploration; want an option × trade-off × reversibility table for a decision | `RECOMMENDED / VIABLE / NOT-RECOMMENDED / NEEDS-MORE-INFO` |
| `code-audit` | Code-flavored adversarial review (security / perf / contract / API-misuse / data-leak) | `CONFIRMED / MARGINAL / REFUTED / INCOMPLETE_FORBIDDEN` |

### 5 ergonomic slash-commands (`commands/<name>.md`)

`/cc-tree:brainstorm <topic>` ≡ `/cc-tree:tree <topic> --preset brainstorm`
(and likewise `:attack`, `:design`, `:code-audit`). Shorter to type; same
engine underneath. Plus `/cc-tree:tree-chain` for running several presets
in sequence (see **Cross-preset chaining** below).

### Engine spec & docs

The skill itself is ~250 lines of navigation; the full engine is in
[`docs/ENGINE.md`](docs/ENGINE.md) (中文平行版：[`docs/ENGINE.zh.md`](docs/ENGINE.zh.md)).
See also:

- [`docs/framings.md`](docs/framings.md) — the 12 framings with per-preset
  examples (中文：[`docs/framings.zh.md`](docs/framings.zh.md))
- [`docs/presets.md`](docs/presets.md) — how to author your own preset
  (schema is CI-enforced by `tools/validate_plugin.py`)
- [`docs/chaining.md`](docs/chaining.md) — cross-preset chaining contract
- [`field-profiles/README.md`](field-profiles/README.md) — domain-aware
  reviewer weighting via `--field`

## Install

cc-tree is a self-contained directory marketplace. Install it with the
Claude Code plugin CLI:

```bash
# 1. Register this repo as a marketplace (directory source)
claude plugin marketplace add <path-to-this-repo>

# 2. Install the plugin from it
claude plugin install cc-tree@cc-tree

# (optional) sanity-check the manifests before/after
claude plugin validate <path-to-this-repo>
claude plugin list
```

Restart your Claude Code session to load the plugin (new plugins are
loaded at session start). Skills then appear namespaced: `/cc-tree:tree`,
`/cc-tree:brainstorm`, etc. To pick up later edits, run
`claude plugin update cc-tree` and restart.

## Quick start

```bash
# Divergent ideation
/cc-tree:brainstorm "ways to detect dark-matter substructure with weak lensing"

# Adversarial critique of a finished doc
/cc-tree:attack ./paper.tex

# Design-space exploration
/cc-tree:design "auth flow for our internal admin tool"

# Code audit
/cc-tree:code-audit ./src/api/upload.py

# Use the engine directly with an explicit preset
/cc-tree:tree <root> --preset brainstorm
/cc-tree:tree <file> --preset ./my-custom-preset.md

# Domain-aware reviewer weighting
/cc-tree:attack ./paper.tex --field physics
```

Each run writes incrementally to `<out>/<UTCdate>__<slug>/` (default
`tree-out/...`; per-preset commands default to `brainstorm-out/`,
`attack-out/`, etc.). The output is a `tree.md` + `tree.json` + a
preset-determined final report (`shortlist.md` for brainstorm,
`confirmed.md` for attack, etc.).

## Cross-preset chaining

A natural workflow pipes one preset's best output into the next:
**brainstorm** → pick top-K → **design** each → **attack** the winner.

```bash
/cc-tree:tree-chain "ways to cut our API p99 latency" \
    --stages brainstorm,design,attack --top-k 3
```

Each stage converges independently; the top-K handoff between stages is
always logged (never silently truncated). Contract:
[`docs/chaining.md`](docs/chaining.md). The substrate is the universal
`--seed-from <primary.md>` flag (alias `--from-prior`), which seeds a run
from a prior run's deliverable.

## Why?

Two reasons.

**Reason 1: the structure repeats.** Brainstorming, adversarial review,
design exploration, and code audit all share the same skeleton —
*generate candidates from N framings → derive each one completely →
score → recurse on the high-value branches → terminate on stable
convergence, not on running out of patience*. Coding that skeleton once
and parameterizing the rest beats writing four near-duplicate skills.

**Reason 2: the failure modes repeat too.** Every divergent task LLMs
do has the same lazy-equilibrium attractors: defer to future-work,
generate near-duplicate branches with synonym swapping, skip the
high-risk/contrarian framings, declare convergence at the first slow
round. The engine encodes hard bans on all of these (§0 forbidden
patterns), and they apply equally well to brainstorming a research
direction and to auditing a Python file.

See [`EVALUATION.md`](EVALUATION.md) for the full design rationale.

## Relationship to sci-paper

[`skymanbp/sci-paper`](https://github.com/skymanbp/sci-paper) was the
original home of this engine, scoped to scientific paper writing /
review. cc-tree is the domain-agnostic extraction; sci-paper keeps its
paper-specific versions independent (no coupling). If you write papers,
use sci-paper. If you want the engine for anything else, use cc-tree.

## License

[MIT](LICENSE). The code, skills, presets, commands, and docs in this
repository are MIT-licensed. The `tree-out/` / `brainstorm-out/` /
`attack-out/` / `design-out/` / `code-audit-out/` directories are
user-generated and `.gitignore`-d by default.
