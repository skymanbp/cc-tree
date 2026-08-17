# cc-tree

[![CI](https://github.com/skymanbp/cc-tree/actions/workflows/ci.yml/badge.svg)](https://github.com/skymanbp/cc-tree/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/skymanbp/cc-tree?color=6aa84f&label=release)](https://github.com/skymanbp/cc-tree/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-8e7cc3)
[![Star on GitHub](https://img.shields.io/github/stars/skymanbp/cc-tree?style=social)](https://github.com/skymanbp/cc-tree/stargazers)

> Language: English (canonical). Chinese: [`README.zh.md`](README.zh.md).

**cc-tree is a Claude Code plugin that turns open-ended thinking into a
tree you can audit.** One universal radial-tree exploration engine, four
swappable presets: divergent brainstorming, adversarial critique,
design-space exploration, and code audit — same engine, different
vocabulary. It is a disciplined, disk-persisted take on tree-of-thoughts
search: every node is derived in full with `file:line` or URL evidence,
`defer / future-work / TODO / NEEDS-MORE-INFO` leaves are hard-banned,
and the run stops on substantive convergence rather than on a node budget.

```bash
claude plugin marketplace add skymanbp/cc-tree
claude plugin install cc-tree@cc-tree
```

> Refactor of [`sci-paper`](https://github.com/skymanbp/sci-paper)'s
> `brainstorm` + `paper-attack-tree` skills, stripped of paper-specific
> anchors and parameterized via presets.

## What it is

cc-tree treats *any* open-ended thinking task as a **phylogenetic tree
growing outward from one root**. The root is your input — a topic, a
document, a code path, a design prompt. Every node is expanded by the
**same 12 framing passes**, each child is fully derived and scored, and
only the high-value (`advances`) leaves get re-expanded, until the tree
reaches **substantive convergence** rather than an arbitrary count.

![cc-tree as a radial phylogenetic tree of thoughts: one ROOT at the
centre, depth as concentric rings growing outward, four coloured clades
for the four presets (brainstorm / attack / design / code-audit). There
is no single winner — a branch can succeed (advances), hit a dead end
(pruned / blocked), or keep branching and be judged again, so several
wins appear at different depths and the branches reach uneven length.
Each tip carries a verdict marker, and the width is the number of
terminal leaves — blocked tips are excluded until they are driven to
completion, so this snapshot is a run still in
flight.](docs/assets/cc-tree-radial-tree.svg)

<sub>Inspired by the radial <em>tree of life</em>. The vocabulary the rest
of this README uses is all in this one picture: <strong>root</strong> (the
input at the centre — topic · artifact · code · design), <strong>node</strong>
(one idea / critique / option / finding, each with the same 12-field
derivation), <strong>depth</strong> (the concentric framing-recursion rings;
branches stop at different rings because only <code>advances</code> leaves
re-expand), <strong>width</strong> (the terminal leaves, wherever they
land — set by convergence, not a hand-picked cap, and never counting a
<code>blocked</code> tip until it is completed, per §0.1), and
<strong>n</strong> (total nodes in the tree). Diagram source:
<a href="tools/gen_radial_tree.py"><code>tools/gen_radial_tree.py</code></a>.</sub>

```
  the tree grows OUTWARD from one root. a branch can WIN, hit a DEAD END, or
  keep BRANCHING and be judged again — no single winner, wins at any depth:

    ROOT ──┬── pruned                      (dead end at depth 1)
           ├── advances                    (a win at depth 1)
           └── advances ──┬── pruned        (this branch keeps going…)
                          └── advances ──┬── advances   (…a deeper win)
                                         └── blocked

  each node → 12 framings (§3.A–§3.L) → 12-field derivation → score → verdict;
  branches that keep advancing grow deeper; pruned / blocked ones stop.
```

## How it works

Five irreducible steps, all specified in [`docs/ENGINE.md`](docs/ENGINE.md)
and binding on every preset.

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

### 1 · Ground the root (§2)

The preset supplies the recipe; the engine enforces that every root field
carries a `file:line`, URL, or command-output citation. An optional
glossary-grill prelude (§2.0) locks the root's technical noun-phrases to
your project's term sheet before a single branch is generated, so the tree
does not spend a hundred leaves solving the wrong problem.

### 2 · Expand every node through 12 framings (§3)

Each node — root first, then every `advances` leaf — is put through all 12
framing passes, each of which must yield at least one child. The set is
fixed so that the model cannot quietly skip the uncomfortable angles.

| Pass | What it forces |
|---|---|
| §3.A First-principles | Strip a load-bearing assumption; see what survives |
| §3.B Inversion | Try the negation, the dual, the boundary where it fails |
| §3.C Cross-disciplinary | Transplant tooling from ≥ 3 other fields |
| §3.D Adversarial / red team | The 3 most damaging counter-arguments |
| §3.E Constraint variation | Relax one constraint; tighten another |
| §3.F Scale extrapolation | 1000× / 0.001× / domain boundary |
| §3.G Substitution | Swap a component and observe the change |
| §3.H Office-hours 6Q | YC-style demand-reality interrogation |
| §3.I Contrarian | Which mainstream consensus might be wrong here? |
| §3.J Failure-driven | Turn a concrete present failure into the next question |
| §3.K High-risk asymmetric | Force ≥ 1 low-probability, paradigm-level branch |
| §3.L Meta self-audit | 7-question audit of the model's own blind spots |

A thirteenth pass, §3.X, runs one external cross-check per node
(`WebSearch` then `WebFetch` of the actual page) unless `--no-online` is
set. Full prompts and per-preset examples:
[`docs/framings.md`](docs/framings.md).

### 3 · Derive every child in 12 fields (§4)

Each child is filled into the preset's 12-field node schema — statement,
parent framing, position, derivation, assumptions, predictions, defense,
alternatives, fix/cost, external check, branch potential, provisional
verdict. Blank, hedged, or deferred fields do not produce a weaker node;
they produce an `INCOMPLETE_FORBIDDEN` node that **blocks termination**
until it is driven to completion.

### 4 · Score, then decide whether to recurse (§5)

Five preset-declared dimensions, each an integer 0–3, summed to a maximum
of 15. `score ≥ 11` (plus any preset-specific gate) → `advances` and the
leaf is re-expanded; `8–10` → `kept`; `≤ 7` → `pruned`; anything dominated
by an unverified claim → `blocked`. Near-duplicate siblings are merged at
cosine similarity ≥ 0.85 (§5.4) so width means coverage, not repetition.

### 5 · Stop only on substantive convergence (§6)

Six conditions must hold **simultaneously**: no incomplete node remains;
the `advances` ratio over the last two rounds has fallen below
`--min-novelty-ratio`; all 12 framings have fired; every `advances` leaf
has been re-expanded and yielded nothing further; at least one fully
derived §3.K high-risk branch exists; and no user cap has tripped. If a
cap trips first, the engine reports `WIDTH_CAP_REACHED` /
`DEPTH_CAP_REACHED` / `ROUNDS_EXHAUSTED` — truthfully, never as
`CONVERGED` — and still completes every in-flight leaf first.

## Why it's different

|  | ad-hoc "brainstorm with me" | cc-tree |
|---|---|---|
| **Coverage** | the 3 obvious angles | 12 fixed framings per node, including contrarian / inversion / high-risk |
| **Completeness** | "we could look at X later" | hard ban on `defer / TODO / future-work` leaves — every leaf derived with `file:line` / URL evidence |
| **When it stops** | when the chat trails off | substantive convergence (6 conditions), not a node count |
| **Output** | a chat log | `tree.md` + `tree.json` + a structured per-preset report on disk |
| **Crash safety** | scroll back and hope | incremental write per node; re-invoke to resume |
| **Reuse** | re-prompt from scratch each time | one engine, 4 presets, chainable (`brainstorm → design → attack`) |

Two reasons, in prose.

**Reason 1: the structure repeats.** Brainstorming, adversarial review,
design exploration, and code audit all share the same skeleton —
*generate candidates from N framings → derive each one completely →
score → recurse on the high-value branches → terminate on stable
convergence, not on running out of patience*. Coding that skeleton once
and parameterizing the rest beats writing four near-duplicate skills.

**Reason 2: the failure modes repeat too.** Every divergent task LLMs do
has the same lazy-equilibrium attractors: defer to future-work, generate
near-duplicate branches with synonym swapping, skip the
high-risk/contrarian framings, declare convergence at the first slow
round. The engine encodes hard bans on all of these (§0.5 forbidden
patterns, §F1–§F8), and they apply equally well to brainstorming a
research direction and to auditing a Python file.

The full design rationale — including why 12 framings and not 7 or 20,
and how cc-tree differs from academic Tree-of-Thoughts and from agent
loops — is in [`docs/EVALUATION.md`](docs/EVALUATION.md).

## Feature reference

### Exploration engine

- **12 framing passes** per node per round (§3.A–§3.L), plus the §3.X
  external cross-check; `--min-frameworks` has a hard floor of 12.
- **12-field derivation** per node (§4), every field non-empty,
  non-hedged, and citation-bearing.
- **5-dimension scoring** (§5.1), integer 0–3 each, max 15, mapped to a
  four-role verdict (§5.2).
- **Sibling merging** at cosine similarity ≥ 0.85 (§5.4), with the merged
  node kept visible and tagged `MERGED_INTO=<id>`.
- **Six-condition convergence test** (§6.1) with an explicit termination
  decision table (§6.2); caps are escape valves, never success.
- **Mandatory sub-agent parallelism** at fan-out ≥ 5 (§8.1), with a
  re-verification contract: the main agent re-checks every citation a
  sub-agent returns before the child counts.

### Presets — 4 shipped, unlimited custom

Each preset ([`presets/`](presets/)) supplies the vocabulary; none of them
may weaken a universal rule (§10).

| Preset | Use when | Root | Verdicts (advances / kept / pruned / blocked) | Primary deliverable |
|---|---|---|---|---|
| `brainstorm` | Divergent ideation; surface unexplored research directions or exhaustive problem-solving paths | topic | `PROMISING / MARGINAL / DEAD-END / NEEDS-MORE-INFO` | `shortlist.md` |
| `attack` | Adversarial critique of a finished artifact (document, argument, proposal) | artifact | `CONFIRMED / MARGINAL / REFUTED / INCOMPLETE_FORBIDDEN` | `confirmed.md` |
| `design` | Design-space exploration; want an option × trade-off × reversibility table | design-prompt | `RECOMMENDED / VIABLE / NOT-RECOMMENDED / NEEDS-MORE-INFO` | `options.md` |
| `code-audit` | Code-flavored adversarial review (security / perf / correctness / contract) | code | `CONFIRMED / MARGINAL / REFUTED / INCOMPLETE_FORBIDDEN` | `findings.md` |

Authoring your own is one `.md` file with the documented frontmatter
schema — see [`docs/presets.md`](docs/presets.md). The schema is
CI-enforced, so a malformed preset fails before it ever runs.

### Commands

| Command | Equivalent to |
|---|---|
| `/cc-tree:tree <root> --preset <name\|path>` | the engine itself; the only command that accepts a custom preset path |
| `/cc-tree:brainstorm <topic>` | `/cc-tree:tree <topic> --preset brainstorm` |
| `/cc-tree:attack <file>` | `/cc-tree:tree <file> --preset attack` |
| `/cc-tree:design <prompt\|file>` | `/cc-tree:tree <prompt> --preset design` |
| `/cc-tree:code-audit <path>` | `/cc-tree:tree <path> --preset code-audit` |
| `/cc-tree:tree-chain <root> --stages …` | several presets in sequence, top-K piped between stages |

The wrappers also change the default output directory (`brainstorm-out/`,
`attack-out/`, …) and carry preset-specific flags such as `attack`'s
`--focus <section|claim|equation>`.

### Quality gates — the 8 forbidden patterns

Violating any of these invalidates the round (§0.5). They are enforced
semantically in every output language, not as an English phrase blocklist.

| Gate | Bans |
|---|---|
| §F1 | Memory-cited claims — every external assertion is verified in the same turn |
| §F2 | Pseudo-divergence — synonym-swapped siblings are one branch, and get merged |
| §F3 | Derivation skipping — no "obvious", no "details omitted"; numbers get a `python` sanity check |
| §F4 | Risk aversion — each pass must fully derive one high-risk branch, whatever its verdict |
| §F5 | Pseudo-convergence — "I'm out of ideas" is not §6 convergence |
| §F6 | Mid-run prompting — full-auto once the root and preset are loaded |
| §F7 | Self-narrowed caps — the engine may not shrink `--width` / `--depth` / `--rounds` on its own |
| §F8 | Deferred leaves — `defer / future work / TODO / 待定 / NEEDS-MORE-INFO` force `INCOMPLETE_FORBIDDEN` |

### Domain weighting — field profiles

`--field <name|path>` loads a **field profile**
([`field-profiles/`](field-profiles/)): four short lists — reviewer
concerns, field consensuses, common failure modes, evidence bar — that
re-prioritize which branches the 12 framings explore first and raise the
citation bar (§2.2). Profiles are preset-agnostic: the same profile
sharpens an `attack` on a paper, a `brainstorm` on research directions,
and a `code-audit` on a simulation. A physics profile
([`field-profiles/physics.md`](field-profiles/physics.md)) ships built-in;
author others from
[`field-profiles/_template.md`](field-profiles/_template.md). A missing
profile warns and continues — weighting is an enhancement, never a
blocker.

### Cross-preset chaining

A natural workflow pipes one preset's best output into the next:
**brainstorm** → pick top-K → **design** each → **attack** the winner.

```bash
/cc-tree:tree-chain "ways to cut our API p99 latency" \
    --stages brainstorm,design,attack --top-k 3
```

Each stage converges independently; the top-K handoff between stages is
always logged, never silently truncated. The substrate is the universal
`--seed-from <primary.md>` flag (alias `--from-prior`), which seeds a run
from a prior run's deliverable, so you can also chain by hand. Contract:
[`docs/chaining.md`](docs/chaining.md).

### Output, resume, and crash-safety

Every node lands on disk the moment its 12 fields are filled (§7.1) —
not batched at the end. If the process is killed, the context window
fills, or you interrupt the run, the on-disk tree is consistent up to the
last completed node. Re-invoke with the same `--out <dir>` and the engine
resumes from the highest-id leaf. `tree.json` is the machine source of
truth; `tree.md` is the human view; `REPORT.md` is the §7.4 final report.

### Bilingual output and documentation

`--lang <tag|auto>` selects the run's human-readable output language
(`en`, `zh`, `zh-Hans`, `zh-Hant`, `fr-CA`, …); `auto` detects the
dominant natural language of the root and falls back to `en` for mixed,
unrecognized, path-only, and code-only input. The **machine skeleton
stays English** in every language: flags, frontmatter and JSON keys,
`root_kind` values, verdict labels, score keys, `node_schema` fields,
framing IDs, status tokens, filenames, and paths. Root text, artifacts,
glossaries, custom-preset prose, citations, and quoted evidence may use
any language, and quotations stay verbatim with a localized explanation
added rather than substituted. One run keeps one language from start
through resume and chaining (§1.0).

The documentation itself follows the same rule: unsuffixed `X.md` files
are canonical English, `X.zh.md` files are maintained Chinese parallels
tracked in [`docs/languages.json`](docs/languages.json), and each
translation records a SHA-256 digest of its English source so a stale
translation fails CI.

### Extensibility

| You want to add | Write | Validated by |
|---|---|---|
| A new exploration mode | one preset `.md` with the frontmatter schema | preset schema check + wrapper-parity check |
| A new domain lens | one field profile `.md` with four `##` sections | field-profile schema check |
| A shorter way to type it | one command `.md` wrapper | command frontmatter + flag-documentation check |
| A new documentation language | a `pairs` entry in `docs/languages.json` | digest, heading, fence, and machine-token parity |

### Engineering guarantees

`tools/validate_plugin.py` runs seven check groups on every pull request and
every push to `main`, across Python 3.11 and 3.13:

| Check | What it fails on |
|---|---|
| manifests | plugin/marketplace version or identity drift |
| skills | a `SKILL.md` without frontmatter, or whose `name` ≠ its directory |
| presets | any of the preset schema rules (§10–§11) |
| commands | a command without a description, or a preset shipped without its wrapper |
| tools | a Python file that does not parse |
| cross-refs | dead `#anchor`s, unresolvable relative links, out-of-bounds example citations, undocumented command flags, malformed field profiles, dead `§N` references |
| i18n | an unregistered document, a stale digest, diverged headings or fences, a thin or English-copy translation, a dropped machine token |

The point is that everything this README claims is either executable or
CI-checked. Drift between the docs, the runtime prompt, and the schema is
the defect class this repository takes most seriously.

## Install

cc-tree is a self-contained directory marketplace. Install it with the
Claude Code plugin CLI:

```bash
# 1. Register this repo as a marketplace (directory or GitHub source)
claude plugin marketplace add skymanbp/cc-tree

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

# Domain-aware reviewer weighting (physics ships built-in; author other
# fields from field-profiles/_template.md)
/cc-tree:attack ./paper.tex --field physics

# Explicit Chinese human-readable output; machine keys/statuses stay English
/cc-tree:attack ./paper.tex --lang zh

# Detect the dominant natural language of the root; ambiguous inputs fall back to en
/cc-tree:brainstorm "如何验证弱引力透镜中的暗物质子结构" --lang auto

# Quick capped run when you want a taste rather than convergence
/cc-tree:brainstorm "topic" --width 20 --depth 2 --no-online
```

A worked, end-to-end example with input and expected output lives in
[`examples/attack/`](examples/attack/README.md).

## Flag reference

Common flags apply to every preset. The authoritative table, with the
per-flag semantics, is in [`skills/tree/SKILL.md`](skills/tree/SKILL.md).

| Flag | Default | Meaning |
|---|---|---|
| `--preset <name\|path>` | *required* | `brainstorm` / `attack` / `design` / `code-audit`, or a path to your own |
| `--lang <tag\|auto>` | `en` | Output language for localized prose; machine tokens stay English |
| `--width N` | ∞ | Cap on final leaf count |
| `--depth N` | ∞ | Cap on tree depth from root |
| `--rounds N` | `conv` | Cap on expansion rounds; `conv` = terminate by §6 convergence |
| `--max-branches N` | ∞ | Cap on new branches per node per round; floor is 12 |
| `--out <dir>` | per-command | Output directory |
| `--glossary <path>` | preset-determined | Term sheet for the §2.0 glossary grill |
| `--field <name\|path>` | none | Field profile for domain-aware weighting |
| `--seed-from <primary.md>` | none | Seed depth-1 from a prior run's deliverable (alias `--from-prior`) |
| `--no-grill` | off | Skip the §2.0 glossary prelude |
| `--no-online` | off | Disable `WebSearch` / `WebFetch` |
| `--min-frameworks N` | 12 | Minimum framings per node; the floor is 12 |
| `--min-novelty-ratio R` | 0.15 | §6.1 convergence threshold on the `advances` ratio |

`tree-chain` adds `--stages <a,b,c>` (default `brainstorm,design,attack`)
and `--top-k N` (default 3). Presets may document their own flags, such as
`attack`'s `--focus <section|claim|equation>`.

## Output layout

Each run writes incrementally to its `--out` directory, which **is** the run
directory — nothing further is appended to a path you pass. The dated segment
is part of the *default* value only: `tree-out/<UTCdate>__<slug>/` for the
engine, and `brainstorm-out/<UTCdate>__<slug>/`, `attack-out/…`,
`design-out/…`, `code-audit-out/…` for the per-preset commands,
`chain-out/…` for `tree-chain`.

```
<out>/
├── tree.md              # outline of every node; primary human view
├── tree.json            # full data for every node; machine source of truth
├── glossary-anchors.md  # §2.0 prelude output (unless --no-grill)
├── <primary>.md         # shortlist.md / confirmed.md / options.md / findings.md
├── <secondary>.md*      # marginal.md / refuted.md / pending.md / …
├── REPORT.md            # §7.4 final report (also echoed to the terminal)
└── nodes/
    └── <id>.md          # spilled when a node's evidence exceeds 100 lines
```

All of these directories are `.gitignore`-d by default — they are your
content, not the plugin's.

## Repository map

```
cc-tree/
├── .claude-plugin/        Plugin + marketplace manifests (fixed location)
├── commands/              Slash-command wrappers, one per preset + tree-chain
├── skills/tree/           The engine skill (SKILL.md) Claude Code loads
├── presets/               The 4 shipped presets — resolved by --preset <name>
├── field-profiles/        Domain lenses — resolved by --field <name>
├── docs/                  Engine spec, framings, authoring guides, rationale
│   ├── assets/            Generated diagrams
│   └── languages.json     Bilingual document manifest + machine-token registry
├── examples/attack/       A worked example: input, expected output, how to rerun
├── tools/                 Repo validators and generators (no runtime dependency)
│   └── tests/             Self-tests for the validator, parser, and i18n contract
└── .github/workflows/     CI: validator + self-tests on Python 3.11 and 3.13
```

Runtime code and content live in `commands/`, `skills/`, `presets/`, and
`field-profiles/`; everything under `docs/`, `examples/`, `tools/`, and
`.github/` exists to specify, demonstrate, or verify them.

## Documentation index

Start at [`docs/README.md`](docs/README.md) for the annotated index. In
short:

| Document | Read it when |
|---|---|
| [`docs/ENGINE.md`](docs/ENGINE.md) | You want the binding contract — §0 through §11 |
| [`docs/framings.md`](docs/framings.md) | You want the 12 framing prompts with per-preset examples |
| [`docs/presets.md`](docs/presets.md) | You are authoring a preset |
| [`docs/chaining.md`](docs/chaining.md) | You are wiring several presets together |
| [`field-profiles/README.md`](field-profiles/README.md) | You are authoring a domain lens |
| [`examples/attack/README.md`](examples/attack/README.md) | You want to see real input and output |
| [`docs/EVALUATION.md`](docs/EVALUATION.md) | You want the design rationale and the alternatives that were rejected |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | You are about to open a pull request |
| [`CHANGELOG.md`](CHANGELOG.md) | You want the per-version history |

Every document above has a maintained Chinese parallel at `X.zh.md`,
except `docs/EVALUATION.md`, `CONTRIBUTING.md`, and `CHANGELOG.md`, which
are canonical-English by declaration in
[`docs/languages.json`](docs/languages.json).

## What cc-tree is not

- **Not a one-shot brainstorm tool.** The engine is recursive and
  convergence-terminated; a real run takes minutes to hours.
- **Not a chat interface.** Once invoked it runs to convergence without
  further prompting (§F6). You steer with flags on the next invocation.
- **Not a substitute for a domain expert.** It produces a cited,
  structured exploration; a human still decides which leaves to act on.
- **Not bundled with a model.** It is pure prompt engineering on top of
  your existing Claude Code model setting.
- **Not a linter.** `code-audit` looks for what a static analyzer cannot:
  threat-model-dependent, contract-level, and cross-file reasoning bugs.

## Related terms

If you arrived searching for one of these, cc-tree is probably what you
want: tree of thoughts (ToT) for Claude Code · structured LLM reasoning ·
recursive exploration agent · AI brainstorming tool · adversarial review /
red-team prompt · reviewer-style paper critique · rebuttal preparation ·
LLM code audit and security review · design-space exploration and
trade-off analysis · architecture decision support · research ideation ·
divergent thinking framework · multi-agent fan-out · convergence criteria
for LLM search · Claude Code plugin, skill, and slash commands ·
bilingual English/Chinese prompt engineering.

## Relationship to sci-paper

[`skymanbp/sci-paper`](https://github.com/skymanbp/sci-paper) was the
original home of this engine, scoped to scientific paper writing and
review. cc-tree is the domain-agnostic extraction; sci-paper keeps its
paper-specific versions independent (no coupling). If you write papers,
use sci-paper. If you want the engine for anything else, use cc-tree.

## Contributing

Issues and pull requests are welcome. [`CONTRIBUTING.md`](CONTRIBUTING.md)
covers the repository layout, the commands that reproduce CI locally, and
the invariants that trip up first-time contributors — among them: presets
are schema-validated, every preset needs its command wrapper, every new
Markdown file must be registered in `docs/languages.json`, and editing an
English document requires refreshing its Chinese parallel's source digest.
(No counts here on purpose: a number in one file and a list in another is
exactly the drift this repository keeps finding in itself.)

## License

[MIT](LICENSE). The code, skills, presets, commands, and docs in this
repository are MIT-licensed. Run-output directories (`tree-out/`,
`brainstorm-out/`, `attack-out/`, `design-out/`, `code-audit-out/`,
`chain-out/`) are user-generated and `.gitignore`-d by default.
