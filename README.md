# cc-tree

A Claude Code plugin: **one universal radial-tree exploration engine, four
swappable presets**. Use it for divergent ideation, adversarial critique,
design-space exploration, or code audit — same engine, different vocabulary.

> Refactor of [`sci-paper`](https://github.com/skymanbp/sci-paper)'s
> `brainstorm` + `paper-attack-tree` skills, stripped of paper-specific
> anchors and parameterized via presets.

## What it ships

### 1 skill

| Skill | What it does |
|---|---|
| `/cc-tree:tree` | Universal radial-tree engine. Loads a preset, builds the §2 baseline, then recursively applies 12 framing passes per node until **stable convergence** (no new high-verdict branches over the last 2 rounds + all 12 framings exercised + all leaves complete). Width × depth default to ∞; resource caps are opt-in. Hard ban on `defer / future-work / TODO / NEEDS-MORE-INFO` leaves. |

### 4 presets (`presets/<name>.md`)

| Preset | Use when | Verdict vocabulary |
|---|---|---|
| `brainstorm` | Divergent ideation; want to surface unexplored research directions or exhaustive problem-solving paths | `PROMISING / MARGINAL / DEAD-END / NEEDS-MORE-INFO` |
| `attack` | Adversarial critique of a finished artifact (document, argument, design proposal); want to surface the most damaging reviewer-style attacks | `CONFIRMED / MARGINAL / REFUTED / DEAD-END` |
| `design` | Design-space exploration; want option × trade-off × reversibility table for a decision | `RECOMMENDED / VIABLE / NOT-RECOMMENDED / NEEDS-MORE-INFO` |
| `code-audit` | Code-flavored adversarial review (security / perf / contract / API-misuse / data-leak) | `CONFIRMED / MARGINAL / REFUTED / DEAD-END` |

### 4 ergonomic slash-commands (`commands/<name>.md`)

`/cc-tree:brainstorm <topic>` ≡ `/cc-tree:tree <topic> --preset brainstorm`
(and likewise `:attack`, `:design`, `:code-audit`). Shorter to type; same
engine underneath.

### Engine spec

The skill itself is ~250 lines of navigation; the full engine is in
[`docs/ENGINE.md`](docs/ENGINE.md). See also
[`docs/framings.md`](docs/framings.md) (the 12 framings with per-preset
examples) and [`docs/presets.md`](docs/presets.md) (how to write your own).

## Install

```bash
# In your Claude Code session:
claude --plugin-dir <path-to-this-repo>

# Reload after edits:
/reload-plugins
```

Skills appear namespaced: `/cc-tree:tree`, `/cc-tree:brainstorm`, etc.

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
```

Each run writes incrementally to `<out>/<UTCdate>__<slug>/` (default
`tree-out/...`; per-preset commands default to `brainstorm-out/`,
`attack-out/`, etc.). The output is a `tree.md` + `tree.json` + a
preset-determined final report (`shortlist.md` for brainstorm,
`confirmed.md` for attack, etc.).

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
