# cc-tree

[![CI](https://github.com/skymanbp/cc-tree/actions/workflows/ci.yml/badge.svg)](https://github.com/skymanbp/cc-tree/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/skymanbp/cc-tree?color=6aa84f&label=release)](https://github.com/skymanbp/cc-tree/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-8e7cc3)
[![Star on GitHub](https://img.shields.io/github/stars/skymanbp/cc-tree?style=social)](https://github.com/skymanbp/cc-tree/stargazers)

> Language: English (canonical). Chinese: [`README.zh.md`](README.zh.md).

**cc-tree is a Claude Code plugin that turns open-ended thinking into a tree you can audit.**
One universal radial-tree exploration engine, four swappable presets: divergent brainstorming,
adversarial critique, design-space exploration, and code audit — same engine, different
vocabulary. It is a disciplined, disk-persisted take on tree-of-thoughts search: every node is
derived in full with `file:line` or URL evidence, `defer / future-work / TODO / NEEDS-MORE-INFO`
leaves are hard-banned, and the run stops on substantive convergence rather than on a node budget.

```bash
claude plugin marketplace add skymanbp/cc-tree
claude plugin install cc-tree@cc-tree
```

> Refactor of [`sci-paper`](https://github.com/skymanbp/sci-paper)'s `brainstorm` +
> `paper-attack-tree` skills, stripped of paper-specific anchors and parameterized via presets.

## 1 · The problem, and what cc-tree does about it

### 1.1 The problem it targets

Ask any LLM to *brainstorm*, *review this critically*, *compare these designs*, or *audit this
file*, and the same five failure modes come back every time. They are not model bugs; they are
the lazy equilibria of free-form generation.

| Failure mode | What it looks like in practice |
|---|---|
| **Shallow coverage** | the three most obvious angles, then a summary |
| **Deferred leaves** | "promising, but needs a deeper survey — future work": a non-result dressed as a result |
| **Pseudo-divergence** | six branches that are one branch with the nouns swapped |
| **Convenient convergence** | "that about covers it" — arriving exactly when new ideas get expensive |
| **Unverifiable output** | a chat log: nothing cites a line, nothing survives the scroll-back |

The target effect is the inverse of every row: **fixed-breadth coverage, no deferrals,
deduplicated branches, a convergence test you can check, and every claim carrying a `file:line`
or a URL.**

### 1.2 What it does — five capabilities

| # | Capability | Invoke | What it yields |
|---|---|---|---|
| **1** | **Exhaustive divergent exploration** — grows research directions or solution paths outward from one topic until new high-value branches stop appearing, not until the chat trails off | `/cc-tree:brainstorm` | `shortlist.md` |
| **2** | **Adversarial critique of a finished artifact** — reviewer-style attack on a document, argument, or proposal; every leaf resolves to `CONFIRMED` / `MARGINAL` / `REFUTED`, carrying the position it attacks and whatever defense the artifact already mounts | `/cc-tree:attack` | `confirmed.md` |
| **3** | **Design-space exploration** — options × trade-offs × reversibility × cost × fit-with-constraints, ending in a comparison table and a `RECOMMENDED` short-list | `/cc-tree:design` | `options.md` |
| **4** | **Code audit** — the findings a static linter structurally cannot produce: threat-model-dependent, contract-level, and cross-file reasoning bugs, each with `file:line` evidence and a proposed fix | `/cc-tree:code-audit` | `findings.md` |
| **5** | **Chaining the four** — pipes one stage's top-K deliverable into the next: **brainstorm → design → attack**, diverging on directions, designing the best into options, attacking the winner before you commit | `/cc-tree:tree-chain` | per-stage, plus the handoff log |

All five are the *same engine*. A preset changes the vocabulary, never the loop — §10 of
[`docs/ENGINE.md`](docs/ENGINE.md) is the exact extension surface.

### 1.3 Working scope — what cc-tree is not

- **Not a one-shot brainstorm tool.** The engine is recursive and convergence-terminated; a real
  run takes minutes to hours.
- **Not a chat interface.** Once invoked it runs to convergence without further prompting (§F6).
  You steer with flags on the next invocation.
- **Not a substitute for a domain expert.** It produces a cited, structured exploration; a human
  still decides which leaves to act on.
- **Not bundled with a model.** It is pure prompt engineering on top of your existing Claude Code
  model setting.
- **Not a linter.** `code-audit` looks for what a static analyzer cannot: threat-model-dependent,
  contract-level, and cross-file reasoning bugs.

## 2 · How it works

### 2.1 The shape — one root, growing outward

cc-tree treats *any* open-ended thinking task as a **phylogenetic tree growing outward from one
root**. The root is your input — a topic, a document, a code path, a design prompt. Every node is
expanded by the **same 12 framing passes**, each child is fully derived and scored, and only the
high-value (`advances`) leaves get re-expanded, until the tree reaches **substantive convergence**
rather than an arbitrary count.

![cc-tree as a radial phylogenetic tree of thoughts: one ROOT at the centre, depth as concentric
rings growing outward, four coloured clades for the four presets (brainstorm / attack / design /
code-audit). There is no single winner — a branch can succeed (advances), hit a dead end (pruned /
blocked), or keep branching and be judged again, so several wins appear at different depths and the
branches reach uneven length. Each tip carries a verdict marker, and the width is the number of
terminal leaves — blocked tips are excluded until they are driven to completion, so this snapshot
is a run still in flight.](docs/assets/cc-tree-radial-tree.svg)

<sub>Inspired by the radial <em>tree of life</em>. The vocabulary the rest of this README uses is
all in this one picture: <strong>root</strong> (the input at the centre — topic · artifact · code ·
design), <strong>node</strong> (one idea / critique / option / finding, each with the same 12-field
derivation), <strong>depth</strong> (the concentric framing-recursion rings; branches stop at
different rings because only <code>advances</code> leaves re-expand), <strong>width</strong> (the
terminal leaves, wherever they land — set by convergence, not a hand-picked cap, and never counting
a <code>blocked</code> tip until it is completed, per §0.1), and <strong>n</strong> (total nodes in
the tree). Diagram source:
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

### 2.2 The five irreducible steps

All five are specified in [`docs/ENGINE.md`](docs/ENGINE.md) and binding on every preset.

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

#### Step 1 — Ground the root (§2)

The preset supplies the recipe; the engine enforces that every root field carries a `file:line`,
URL, or command-output citation. An optional glossary-grill prelude (§2.0) locks the root's
technical noun-phrases to your project's term sheet before a single branch is generated, so the
tree does not spend a hundred leaves solving the wrong problem.

#### Step 2 — Expand every node through 12 framings (§3)

Each node — root first, then every `advances` leaf — is put through all 12 framing passes, each of
which must yield at least one child. The set is fixed so that the model cannot quietly skip the
uncomfortable angles.

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

A thirteenth pass, §3.X, runs one external cross-check per node (`WebSearch` then `WebFetch` of the
actual page) unless `--no-online` is set. Full prompts and per-preset examples:
[`docs/framings.md`](docs/framings.md).

#### Step 3 — Derive every child in 12 fields (§4)

Each child is filled into the preset's 12-field node schema — statement, parent framing, position,
derivation, assumptions, predictions, defense, alternatives, fix/cost, external check, branch
potential, provisional verdict. Blank, hedged, or deferred fields do not produce a weaker node;
they produce an `INCOMPLETE_FORBIDDEN` node that **blocks termination** until it is driven to
completion.

#### Step 4 — Score, then decide whether to recurse (§5)

Five preset-declared dimensions, each an integer 0–3, summed to a maximum of 15. `score ≥ 11`
(plus any preset-specific gate) → `advances` and the leaf is re-expanded; `8–10` → `kept`;
`≤ 7` → `pruned`; anything dominated by an unverified claim → `blocked`. Near-duplicate siblings
are merged at cosine similarity ≥ 0.85 (§5.4) so width means coverage, not repetition.

#### Step 5 — Stop only on substantive convergence (§6)

Six conditions must hold **simultaneously**: no incomplete node remains; the `advances` ratio over
the last two rounds has fallen below `--min-novelty-ratio`; all 12 framings have fired; every
`advances` leaf has been re-expanded and yielded nothing further; at least one fully derived §3.K
high-risk branch exists; and no user cap has tripped. If a cap trips first, the engine reports
`WIDTH_CAP_REACHED` / `DEPTH_CAP_REACHED` / `ROUNDS_EXHAUSTED` — truthfully, never as `CONVERGED`
— and still completes every in-flight leaf first.

### 2.3 Engine invariants a preset may not weaken

| Invariant | Contract |
|---|---|
| 12 framing passes per node per round | §3.A–§3.L plus the §3.X external cross-check; `--min-frameworks` has a hard floor of 12 |
| 12-field derivation per node | §4, every field non-empty, non-hedged, and citation-bearing |
| 5-dimension scoring | §5.1, integer 0–3 each, max 15, mapped to a four-role verdict (§5.2) |
| Sibling merging | §5.4 at cosine similarity ≥ 0.85; the merged node stays visible, tagged `MERGED_INTO=<id>` |
| Six-condition convergence test | §6.1, with the explicit termination decision table of §6.2; caps are escape valves, never success |
| Mandatory sub-agent parallelism | §8.1 at fan-out ≥ 5 — always true of the root, whose 12 framings fan out to ≥ 12 children — and the main agent re-verifies every citation a sub-agent returns before the child counts |

### 2.4 The eight quality gates

Violating any of these invalidates the round (§0.5). They are enforced semantically in every output
language, not as an English phrase blocklist, and each answers a specific row of section 1.1.

| Gate | Bans | Failure mode it kills |
|---|---|---|
| §F1 | Memory-cited claims — every external assertion is verified in the same turn | unverifiable output |
| §F2 | Pseudo-divergence — synonym-swapped siblings are one branch, and get merged | pseudo-divergence |
| §F3 | Derivation skipping — no "obvious", no "details omitted"; numbers get a `python` sanity check | shallow coverage |
| §F4 | Risk aversion — each pass must fully derive one high-risk branch, whatever its verdict | shallow coverage |
| §F5 | Pseudo-convergence — "I'm out of ideas" is not §6 convergence | convenient convergence |
| §F6 | Mid-run prompting — full-auto once the root and preset are loaded | convenient convergence |
| §F7 | Self-narrowed caps — the engine may not shrink `--width` / `--depth` / `--rounds` on its own | convenient convergence |
| §F8 | Deferred leaves — `defer / future work / TODO / 待定 / NEEDS-MORE-INFO` force `INCOMPLETE_FORBIDDEN` | deferred leaves |

### 2.5 Why it's different

|  | ad-hoc "brainstorm with me" | cc-tree |
|---|---|---|
| **Coverage** | the 3 obvious angles | 12 fixed framings per node, including contrarian / inversion / high-risk |
| **Completeness** | "we could look at X later" | hard ban on `defer / TODO / future-work` leaves — every leaf derived with `file:line` / URL evidence |
| **When it stops** | when the chat trails off | substantive convergence (6 conditions), not a node count |
| **Output** | a chat log | `tree.md` + `tree.json` + a structured per-preset report on disk |
| **Crash safety** | scroll back and hope | incremental write per node; re-invoke to resume |
| **Reuse** | re-prompt from scratch each time | one engine, 4 presets, chainable (`brainstorm → design → attack`) |

Two reasons, in prose. **Reason 1: the structure repeats.** Brainstorming, adversarial review,
design exploration, and code audit all share the same skeleton — *generate candidates from N
framings → derive each one completely → score → recurse on the high-value branches → terminate on
stable convergence, not on running out of patience*. Coding that skeleton once and parameterizing
the rest beats writing four near-duplicate skills.

**Reason 2: the failure modes repeat too.** Every divergent task LLMs do has the same
lazy-equilibrium attractors: defer to future-work, generate near-duplicate branches with synonym
swapping, skip the high-risk/contrarian framings, declare convergence at the first slow round. The
engine encodes hard bans on all of these (§0.5 forbidden patterns, §F1–§F8), and they apply equally
well to brainstorming a research direction and to auditing a Python file.

The full design rationale — including why 12 framings and not 7 or 20, and how cc-tree differs from
academic Tree-of-Thoughts and from agent loops — is in [`docs/EVALUATION.md`](docs/EVALUATION.md).

## 3 · What a run actually produces

The example below is this repository's own showcase fixture,
[`examples/attack/`](examples/attack/README.md) — a real capped run (`--width 3 --depth 1
--no-online --no-grill`), hand-trimmed to the root and its `CONFIRMED` leaves. A real run also
carries the `MARGINAL` / `REFUTED` branches and a full 12-field derivation per node.

### 3.1 Before → after

```
BEFORE — examples/attack/sample-claim.md, five plausible-sounding lines
  3. Therefore the API is 10× faster for all users in production.
  4. The cache never returns stale data, because entries expire after 60 seconds.
  5. We tested with one concurrent user and saw no errors, so the cache is production-ready.

AFTER  — /cc-tree:attack ./sample-claim.md  →  confirmed.md, 3 findings
  C1  §3.F scale extrapolation  score 13  "10× for all users" generalizes a p50
                                          measured on one dev laptop
  C2  §3.A first-principles     score 12  "never stale" is refuted by the 60 s TTL
                                          in the same sentence
  C3  §3.D red team             score 11  "production-ready" rests on a
                                          single-concurrent-user test
```

Note which framings caught what: scale extrapolation found the laptop-to-production leap,
first-principles found the sentence that refutes itself, red team found the concurrency assumption.
None is the *obvious* objection a free-form review returns first — and none was chosen by the
model, because the framing set is fixed and all twelve had to be attempted.

### 3.2 The deliverable, in full

`confirmed.md` is the file you act on. Each finding carries the position, the evidence, the defense
the artifact does or does not mount, and a fix
([`examples/attack/expected-out/confirmed.md`](examples/attack/expected-out/confirmed.md)):

```markdown
## C2 — "never returns stale data" is contradicted by the 60 s TTL in the same sentence (S=3)

- **artifact_position**: ../sample-claim.md:7-8 —
  "never returns stale data, because entries expire after 60 seconds."
- **evidence**: A 60 s TTL *is* a staleness window — a row updated in the
  DB at t=0 is served from cache as stale until its entry expires (up to
  60 s later). "Never stale" and "expires after 60 s" are mutually
  exclusive: the justifying clause refutes the claim it justifies.
- **artifact_defense**: none — read all of lines 1-10; no write-through
  or invalidation-on-write mechanism is described that would close the
  window.
- **proposed_fix**: replace "never returns stale data" with "may serve
  data up to 60 s stale", or add write-through invalidation if true
  freshness is required.
```

`artifact_defense` is what separates this from a review comment: the engine must go looking for the
artifact's *own* rebuttal and report what it found, so a finding cannot score high merely because
the reviewer stopped reading early. The node view with all 12 fields and the score breakdown is in
[`examples/attack/expected-out/tree.md`](examples/attack/expected-out/tree.md).

### 3.3 What lands on disk

Each run writes incrementally to its `--out` directory, which **is** the run directory — nothing
further is appended to a path you pass. The dated segment is part of the *default* value only:
`tree-out/<UTCdate>__<slug>/` for the engine, `brainstorm-out/<UTCdate>__<slug>/`, `attack-out/…`,
`design-out/…`, `code-audit-out/…` for the per-preset commands, `chain-out/…` for `tree-chain`.

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

All of these directories are `.gitignore`-d by default — they are your content, not the plugin's.

### 3.4 Crash-safety and resume

Every node lands on disk the moment its 12 fields are filled (§7.1) — not batched at the end. If
the process is killed, the context window fills, or you interrupt the run, the on-disk tree is
consistent up to the last completed node. Re-invoke with the same `--out <dir>` and the engine
resumes from the highest-id leaf.

## 4 · Verification dashboard

### 4.1 What is measured, and what is not

cc-tree ships no latency or accuracy benchmark, and inventing one would be dishonest: the runtime
is a prompt contract executed by whatever model your Claude Code session is set to, so wall-clock
and answer quality are properties of that model, not of this repository. What *is* measurable — and
what this dashboard reports — is the **integrity of the specification and its gates**: whether the
engine spec, the runtime prompt, the four presets, the commands, the examples, and both
documentation languages still agree with each other, and whether the checks asserting that can
themselves fail.

### 4.2 Gate coverage

`tools/validate_plugin.py` runs seven check groups on every pull request and every push to `main`,
across Python 3.11 and 3.13:

| Check group | Fails on |
|---|---|
| manifests | plugin/marketplace version or identity drift |
| skills | a `SKILL.md` without frontmatter, or whose `name` ≠ its directory |
| presets | any of the preset schema rules (§10–§11) |
| commands | a command without a description, or a preset shipped without its wrapper |
| tools | a Python file that does not parse |
| cross-refs | dead `#anchor`s, unresolvable relative links, out-of-bounds example citations, undocumented command flags, malformed field profiles, dead `§N` references |
| i18n | an unregistered document, a stale digest, diverged headings or fences, a thin or English-copy translation, a dropped machine token |

Three self-test suites back them, plus a CI step that regenerates the radial diagram and diffs it,
so the committed SVG cannot drift from [`tools/gen_radial_tree.py`](tools/gen_radial_tree.py):

| Suite | Covers |
|---|---|
| [`tools/tests/test_validate.py`](tools/tests/test_validate.py) | preset schema validator + frontmatter parser, positive and negative cases |
| [`tools/tests/test_i18n.py`](tools/tests/test_i18n.py) | the multilingual contract: pairs, digests, structural parity, negative cases |
| [`tools/tests/test_checks.py`](tools/tests/test_checks.py) | all seven check groups against a synthetic repository, one mutation per rule |

Reproduce the whole gate locally — this is what CI runs. Snapshot at HEAD, 2026-09-03; the
per-run counts move with the corpus, so they are reported, never asserted:

```
$ python tools/validate_plugin.py
  [ok] manifests OK (version 0.7.1, metadata paired, changelog present)
  [ok] skills OK (1 skills)
  [ok] presets OK (4 presets, frontmatter schema)
  [ok] commands OK (5 commands, 4 preset wrappers)
  [ok] tools/**/*.py syntax OK (7 files)
  [ok] cross-refs OK (238 links / 13 anchors, 9 example citations, 42 command flags, 1 field profiles, 404 section refs)
  [ok] i18n OK (8 pairs, 22 canonical-only docs, 8 digests, 171 aligned sections, 514 machine-token checks)
validate_plugin: all checks passed

$ python -m pytest tools/tests -q
22 passed
```

### 4.3 The adversarial-sweep record

Four whole-corpus adversarial sweeps since v0.3.0 (v0.3.0, v0.5.0, v0.6.0, v0.7.0), plus v0.7.1's
documentation audit — from v0.6.0 onward run by a *different* model family, and by an independent
refuting pass that rejects findings before any is acted on. The confirmed/rejected split is the
honest metric this project has, so it is published rather than smoothed:

| Release | Method | Findings | What it changed |
|---|---|---|---|
| v0.3.0 | first line-by-line sweep | 26 confirmed defects across 20 files | 5 cross-file consistency checks became CI failures |
| v0.5.0 | second sweep, line-by-line over every shipped file | 24 defects across 18 files | dead `§N` pointers, anchors outside the link href, and machine tokens registered in a form that matched nothing became CI failures |
| v0.6.0 | 3 parallel read-only reviews by a second model family (`gpt-5.6-sol`, xhigh) | 55 numbered findings; 26 reproduced by execution before any fix (26/26 confirmed) | closed the *gates'* own false-pass channels |
| v0.7.0 | 5-dimension multi-agent audit + independent refuting pass | 32 confirmed, 6 rejected | fixed the checks that failed open |
| v0.7.1 | full-corpus documentation audit + refuting pass | 14 confirmed, 26 rejected | validator function coverage 18/35 → 35/35 |

Two rows deserve a second read. In v0.7.1 the new behavioural suite immediately found three defects
the shipped repository could not surface: deleting *every* command wrapper passed the
wrapper-parity check, `_check_command_flags` ignored its argument, and v0.7.0's own zero-count
tripwire rejected a legitimate repository. And in v0.7.1 the refuting pass overturned a finding
the maintainer had already called confirmed. Per-release detail: [`CHANGELOG.md`](CHANGELOG.md).

## 5 · Install and quick start

### 5.1 Install

cc-tree is a self-contained directory marketplace. Install it with the Claude Code plugin CLI:

```bash
# 1. Register this repo as a marketplace (directory or GitHub source)
claude plugin marketplace add skymanbp/cc-tree
# 2. Install the plugin from it
claude plugin install cc-tree@cc-tree
# (optional) sanity-check the manifests before/after
claude plugin validate <path-to-this-repo>
claude plugin list
```

Restart your Claude Code session to load the plugin (new plugins are loaded at session start).
Skills then appear namespaced: `/cc-tree:tree`, `/cc-tree:brainstorm`, etc. To pick up later edits,
run `claude plugin update cc-tree` and restart.

### 5.2 Quick start

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

## 6 · Reference

### 6.1 Presets — 4 shipped, unlimited custom

Each preset ([`presets/`](presets/)) supplies the vocabulary; none of them may weaken a universal
rule (§10).

| Preset | Use when | Root | Verdicts (advances / kept / pruned / blocked) | Primary deliverable |
|---|---|---|---|---|
| `brainstorm` | Divergent ideation; surface unexplored research directions or exhaustive problem-solving paths | topic | `PROMISING / MARGINAL / DEAD-END / NEEDS-MORE-INFO` | `shortlist.md` |
| `attack` | Adversarial critique of a finished artifact (document, argument, proposal) | artifact | `CONFIRMED / MARGINAL / REFUTED / INCOMPLETE_FORBIDDEN` | `confirmed.md` |
| `design` | Design-space exploration; want an option × trade-off × reversibility table | design-prompt | `RECOMMENDED / VIABLE / NOT-RECOMMENDED / NEEDS-MORE-INFO` | `options.md` |
| `code-audit` | Code-flavored adversarial review (security / perf / correctness / contract) | code | `CONFIRMED / MARGINAL / REFUTED / INCOMPLETE_FORBIDDEN` | `findings.md` |

Authoring your own is one `.md` file with the documented frontmatter schema — see
[`docs/presets.md`](docs/presets.md). The schema is CI-enforced, so a malformed preset fails before
it ever runs.

### 6.2 Commands

| Command | Equivalent to |
|---|---|
| `/cc-tree:tree <root> --preset <name\|path>` | the engine itself; the only command that accepts a custom preset path |
| `/cc-tree:brainstorm <topic>` | `/cc-tree:tree <topic> --preset brainstorm` |
| `/cc-tree:attack <file>` | `/cc-tree:tree <file> --preset attack` |
| `/cc-tree:design <prompt\|file>` | `/cc-tree:tree <prompt> --preset design` |
| `/cc-tree:code-audit <path>` | `/cc-tree:tree <path> --preset code-audit` |
| `/cc-tree:tree-chain <root> --stages …` | several presets in sequence, top-K piped between stages |

The wrappers also change the default output directory (`brainstorm-out/`, `attack-out/`, …) and
carry preset-specific flags such as `attack`'s `--focus <section|claim|equation>`.

### 6.3 Flags

Common flags apply to every preset. The authoritative table, with the per-flag semantics, is in
[`skills/tree/SKILL.md`](skills/tree/SKILL.md).

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

`tree-chain` adds `--stages <a,b,c>` (default `brainstorm,design,attack`) and `--top-k N`
(default 3). Presets may document their own flags, such as `attack`'s
`--focus <section|claim|equation>`.

### 6.4 Domain weighting — field profiles

`--field <name|path>` loads a **field profile** ([`field-profiles/`](field-profiles/)): four short
lists — reviewer concerns, field consensuses, common failure modes, evidence bar — that
re-prioritize which branches the 12 framings explore first and raise the citation bar (§2.2).
Profiles are preset-agnostic: the same profile sharpens an `attack` on a paper, a `brainstorm` on
research directions, and a `code-audit` on a simulation. A physics profile
([`field-profiles/physics.md`](field-profiles/physics.md)) ships built-in; author others from
[`field-profiles/_template.md`](field-profiles/_template.md). A missing profile warns and continues
— weighting is an enhancement, never a blocker.

### 6.5 Cross-preset chaining

A natural workflow pipes one preset's best output into the next: **brainstorm** → pick top-K →
**design** each → **attack** the winner.

```bash
/cc-tree:tree-chain "ways to cut our API p99 latency" \
    --stages brainstorm,design,attack --top-k 3
```

Each stage converges independently; the top-K handoff between stages is always logged, never
silently truncated. The substrate is the universal `--seed-from <primary.md>` flag (alias
`--from-prior`), which seeds a run from a prior run's deliverable, so you can also chain by hand.
Contract: [`docs/chaining.md`](docs/chaining.md).

### 6.6 Bilingual output and documentation

`--lang <tag|auto>` selects the run's human-readable output language (`en`, `zh`, `zh-Hans`,
`zh-Hant`, `fr-CA`, …); `auto` detects the dominant natural language of the root and falls back to
`en` for mixed, unrecognized, path-only, and code-only input. The **machine skeleton stays English**
in every language: flags, frontmatter and JSON keys, `root_kind` values, verdict labels, score keys,
`node_schema` fields, framing IDs, status tokens, filenames, and paths. Root text, artifacts,
glossaries, custom-preset prose, citations, and quoted evidence may use any language, and
quotations stay verbatim with a localized explanation added rather than substituted. One run keeps
one language from start through resume and chaining (§1.0).

The documentation itself follows the same rule: unsuffixed `X.md` files are canonical English,
`X.zh.md` files are maintained Chinese parallels tracked in
[`docs/languages.json`](docs/languages.json), and each translation records a SHA-256 digest of its
English source so a stale translation fails CI.

### 6.7 Extensibility

| You want to add | Write | Validated by |
|---|---|---|
| A new exploration mode | one preset `.md` with the frontmatter schema | preset schema check + wrapper-parity check |
| A new domain lens | one field profile `.md` with four `##` sections | field-profile schema check |
| A shorter way to type it | one command `.md` wrapper | command frontmatter + flag-documentation check |
| A new documentation language | a `pairs` entry in `docs/languages.json` | digest, heading, fence, and machine-token parity |

## 7 · Tech stack, design decisions, and philosophy

### 7.1 Tech stack

There is deliberately very little of one. cc-tree is a **prompt-engineering artifact**, not an
application: the runtime is Markdown, and the Python exists only to keep that Markdown honest.

| Layer | What it is | Runtime dependency |
|---|---|---|
| Runtime | Markdown — one skill ([`skills/tree/SKILL.md`](skills/tree/SKILL.md)), 4 presets, 5 command wrappers, field profiles | none beyond Claude Code |
| Specification | [`docs/ENGINE.md`](docs/ENGINE.md) §0–§11, the binding contract every preset inherits | none |
| Verification | Python 3.11+ standard library only — validator, frontmatter parser, i18n checker, diagram generator, 3 test suites | not shipped to the runtime |
| Distribution | Claude Code plugin marketplace (`.claude-plugin/`), installable straight from GitHub | none |
| CI | GitHub Actions, Python 3.11 and 3.13 | none |

No third-party packages, no lockfile, no build step, no vector database, no model API of its own.
The validator imports nothing outside the standard library, which is why
`python tools/validate_plugin.py` works on a clean checkout.

### 7.2 The load-bearing design decisions

Each was a real fork with a rejected alternative; the full argument is in
[`docs/EVALUATION.md`](docs/EVALUATION.md).

- **One engine + swappable presets, not four skills.** Four near-duplicate ~450-line skills cost
  O(N × engine_size) to maintain, and the earlier sci-paper version proved it: the same §6.2 fix
  had to be applied twice. A single mega-skill with `--mode` flags was rejected too — it pollutes
  the `description:` Claude reads when deciding auto-invocation.
- **Caps default to ∞.** A finite default gives the engine permission to declare success at the
  cap. Convergence must be earned by substance; caps remain escape valves that report themselves.
- **Deferred leaves are banned, not discouraged.** The highest-leverage behavioural rule here. A
  branch must either be driven to evaluability with real tool calls, or re-routed via §3.E to one
  that *can* be evaluated now.
- **Incremental write, not batched output.** The tree survives a process kill, a context overflow,
  or a `^C`; resume is the default mode.
- **English-canonical machine skeleton.** Translating flags, JSON keys, verdict labels, or
  filenames would fork the schema instead of supporting a language. Prose localizes; identifiers
  do not.
- **Structural validation, not semantic.** CI enforces that the schema is well-formed and the
  corpus agrees with itself. Whether a scoring rubric is *good* stays a human judgment, and the
  project says so rather than implying the checker knows.

### 7.3 Project philosophy

**Everything this README claims is either executable or CI-checked.** Drift between the docs, the
runtime prompt, and the schema is the defect class this repository takes most seriously — every
sweep since v0.3.0 has converted a class of found drift into a CI failure, so the same mistake
cannot be made twice quietly.

**A gate that cannot fail is not a gate.** Recent sweeps kept finding checks that passed *because*
they were broken: a skip list that had drifted from `.gitignore`, a suite whose diagnostics only
`main()` read, a wrapper-parity check that accepted the deletion of every wrapper. The response to
each was a test that constructs a repository where the check *must* reject.

**Findings are refuted before they are fixed**, and the rejection count is published beside the
confirmation count — including the occasion where the refuting pass overturned the maintainer.
**Termination is truthful**: the engine may not report `CONVERGED` when a cap tripped, may not
narrow its own caps, and may not call running out of ideas a convergence. Those rules are why the
output can be read as a coverage claim at all.

## 8 · Repository map and documentation index

### 8.1 Repository map

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
│   └── tests/             Self-tests: preset schema, frontmatter parser,
│                          i18n contract, and every check group
└── .github/workflows/     CI: validator + self-tests on Python 3.11 and 3.13
```

Runtime code and content live in `commands/`, `skills/`, `presets/`, and `field-profiles/`;
everything under `docs/`, `examples/`, `tools/`, and `.github/` exists to specify, demonstrate, or
verify them.

### 8.2 Documentation index

Start at [`docs/README.md`](docs/README.md) for the annotated index. In short:

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

Every document above has a maintained Chinese parallel at `X.zh.md`, except
`docs/EVALUATION.md`, `CONTRIBUTING.md`, and `CHANGELOG.md`, which are canonical-English by
declaration in [`docs/languages.json`](docs/languages.json).

## 9 · Roadmap, limitations, and the rest

### 9.1 Roadmap — what is still open

Open questions with no committed dates. The design rationale for the first one is in
[`docs/EVALUATION.md`](docs/EVALUATION.md); the ones with a concrete work item are tracked as
[open issues](https://github.com/skymanbp/cc-tree/issues) and linked per bullet. Everything else
on the original list has shipped: chaining and `--seed-from` in v0.2.0, mandatory sub-agent
dispatch in v0.2.0, multi-language output in v0.4.0.

- **Semantic validation of a scoring rubric.** The structural schema is hard-enforced — five
  dimensions, each with `key` / `name` / `desc`, and a `convergence_metric` naming a real verdict.
  Whether those dimensions are *orthogonal*, or the rubric self-consistent, is a human judgment.
  Rationale: [`docs/EVALUATION.md`](docs/EVALUATION.md), "Open questions" item 1.
- **More shipped presets.** Four cover the cases with a concrete need; `architecture-review` and
  `risk-analysis` are the obvious next two, each one ~150-line file with no engine change.
  Tracking: [#1](https://github.com/skymanbp/cc-tree/issues/1), a `research` / literature-review
  preset.
- **More field profiles.** Only `physics` ships. The template and its schema check are in place;
  the profiles themselves are content. Tracking:
  [#2](https://github.com/skymanbp/cc-tree/issues/2) — security, ML, frontend, distributed systems.
- **More documentation languages.** The manifest, digest, and parity machinery is
  language-agnostic; only `en` and `zh` are registered today.
- **A diagram export for `tree.json`.** Graphviz, Mermaid, or interactive HTML rendered from the
  run's own JSON. Tracking: [#3](https://github.com/skymanbp/cc-tree/issues/3).
- **A showcase gallery.** Real runs published under `docs/`, so the output can be judged before
  installing. Tracking: [#4](https://github.com/skymanbp/cc-tree/issues/4).
- **Long-run ergonomics.** A progress summary while a long run is in flight, and a resume path
  that reports what it picked up. Tracking: [#5](https://github.com/skymanbp/cc-tree/issues/5).

### 9.2 Known limitations

- **No output benchmark.** See section 4.1. Run quality tracks your model setting; this repository
  measures its own consistency, not the model's reasoning.
- **CI validates the repository, not a run.** `tools/validate_plugin.py` checks the corpus on disk;
  it cannot inspect a live exploration. In-run compliance rests on the engine's §11 audit checklist
  and the §7.4 report's self-audit sections.
- **Unbounded by default.** With `--width` / `--depth` / `--rounds` at ∞, a rich root can run for
  hours and consume a large number of tokens. Caps exist for exactly this; use them for a first
  pass.
- **Translation freshness is enforced; translation quality is not.** A stale digest fails CI, but
  no checker can tell you the Chinese is *good*.
- **`--no-online` narrows the evidence bar.** §3.X external cross-checks are skipped, so leaves
  rest on local evidence only. The run stays valid — it is simply less externally grounded.
- **Sub-agent fan-out costs re-verification.** The main agent re-checks every citation a sub-agent
  returns (§8.1). That is the point, but it means parallelism buys wall-clock, not total tokens.

### 9.3 Related terms

If you arrived searching for one of these, cc-tree is probably what you want: tree of thoughts
(ToT) for Claude Code · structured LLM reasoning · recursive exploration agent · AI brainstorming
tool · adversarial review / red-team prompt · reviewer-style paper critique · rebuttal preparation
· LLM code audit and security review · design-space exploration and trade-off analysis ·
architecture decision support · research ideation · divergent thinking framework · multi-agent
fan-out · convergence criteria for LLM search · Claude Code plugin, skill, and slash commands ·
bilingual English/Chinese prompt engineering.

### 9.4 Relationship to sci-paper

[`skymanbp/sci-paper`](https://github.com/skymanbp/sci-paper) was the original home of this engine,
scoped to scientific paper writing and review. cc-tree is the domain-agnostic extraction;
sci-paper keeps its paper-specific versions independent (no coupling). If you write papers, use
sci-paper. If you want the engine for anything else, use cc-tree.

### 9.5 Contributing

Issues and pull requests are welcome. [`CONTRIBUTING.md`](CONTRIBUTING.md) covers the repository
layout, the commands that reproduce CI locally, and the invariants that trip up first-time
contributors — among them: presets are schema-validated, every preset needs its command wrapper,
every new Markdown file must be registered in `docs/languages.json`, and editing an English
document requires refreshing its Chinese parallel's source digest. (No counts here on purpose: a
number in one file and a list in another is exactly the drift this repository keeps finding in
itself.)

### 9.6 License

[MIT](LICENSE). The code, skills, presets, commands, and docs in this repository are MIT-licensed.
Run-output directories (`tree-out/`, `brainstorm-out/`, `attack-out/`, `design-out/`,
`code-audit-out/`, `chain-out/`) are user-generated and `.gitignore`-d by default.
