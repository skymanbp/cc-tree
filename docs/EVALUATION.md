# Why cc-tree, and why this shape

Started: 2026-05-25 · Last updated: 2026-09-03
Author: skymanbp + Claude Opus 4.7

A living design record, not a dated snapshot: the "Open questions" and
"Decision" sections at the end are appended to on each release, so the
range above matters more than any single date.

## The question

Multiple "thinking" workflows — brainstorming, adversarial critique,
design exploration, code audit — feel structurally similar but get
implemented as separate skills in most plugin libraries. Is there a
single primitive that subsumes all of them, or are the differences
load-bearing?

## Short answer

**Yes, a single primitive subsumes them**, and the differences are
small enough to encode as a swappable *preset* on a single engine. The
primitive is a **radial tree** (root → 12-framing expansion → per-node
12-field derivation → score → recurse-on-promising-leaves → terminate
on stable convergence). What varies between use-cases:

1. The **baseline** (what to read / Grep / ask to fill the root node).
2. The **node field schema** (12 fields with names that fit the task).
3. The **scoring dimensions** (5 dims that capture "is this leaf
   worth keeping?").
4. The **verdict vocabulary** (which label means "expand further",
   which means "kept but pruned", which means "incomplete and must be
   driven to completion").
5. The **convergence ratio** (which verdict counts toward the §6.1
   condition-2 "novelty / confirmed / recommended ratio drops below
   0.15" check).
6. The **final report file names** (`shortlist.md` vs `confirmed.md` vs
   `options.md`).

Everything else — including the 12 framing passes, the 8 forbidden
patterns, the 6 convergence conditions, the increment-write-on-each-
node-completion contract — is **identical across use-cases**.

## Path-by-path analysis

### Path 1: ship 4 separate skills, copy-paste the engine

This is what `sci-paper` did initially: `brainstorm.md` and
`paper-attack-tree.md` were both ~450-line files, with ~85% verbatim
overlap and the remaining 15% being domain-specific schema and
vocabulary. The duplication created two pain points:

- Bug fixes (e.g. the §6.2 "user-cap-reached + incomplete leaves not
  allowed" tightening) had to be applied twice.
- New presets (`design`, `code-audit`) would each be another ~450-line
  near-duplicate of the same engine.

This path scales as O(N × engine_size). Rejected.

### Path 2: one mega-skill with `--mode` flags

A single skill that branches internally on `--mode brainstorm` vs
`--mode attack`. Solves the duplication but bloats the skill's
`description:` (which is what Claude reads to decide whether to
auto-invoke). A description listing all four use-cases dilutes the
"Use when..." triggers and degrades auto-invocation accuracy.

Rejected for description-pollution; kept as a fallback if presets turn
out to be brittle.

### Path 3 (chosen): one skill + N preset files + N ergonomic commands

The skill (`/cc-tree:tree`) is the engine. Its `description:` only
needs to say "loads a preset and runs the universal exploration loop";
the *use-when* triggers move into the per-preset slash-commands
(`/cc-tree:brainstorm`, `:attack`, etc.). Each command is ~15 lines and
just dispatches to the skill with a preset preselected.

Benefits:

1. **Engine is one source of truth.** Bug fixes in `docs/ENGINE.md`
   propagate to every preset automatically.
2. **Discoverability is preserved.** A user who types
   `/cc-tree:brainstorm` gets brainstorm semantics without knowing
   about presets. A power user can call `/cc-tree:tree <root> --preset
   ./my-custom.md` and override any slot.
3. **New use-cases are cheap.** Adding a fifth preset (e.g. for
   `architecture-review` or `risk-analysis`) is a single ~150-line
   file; no engine changes needed.
4. **Skill description stays sharp.** The skill's description is one
   short paragraph; the per-preset descriptions in the commands give
   precise "Use when..." triggers.

### Path 4: one skill, no presets, fully user-supplied profile

Skipped. Forces every user to author a preset on first use; high
friction. The four-preset starter set covers the cases I had a
concrete need for, and `docs/presets.md` documents how to author more.

## Architectural choices

### Why 12 framings and not 7 or 20?

Inherited from `sci-paper`'s prior tuning. The 12 are:

| Pass | What it forces |
|---|---|
| §3.A First-principles | Strip an assumption; see what's still true |
| §3.B Inversion | Try the dual / negation / opposite |
| §3.C Cross-disciplinary | Borrow from biology / economics / CS / math / linguistics |
| §3.D Adversarial / red team | What's the fatal counter-argument? |
| §3.E Constraint variation | Relax one constraint; tighten another |
| §3.F Scale extrapolation | 1000× / 0.001× the current scale |
| §3.G Substitution | Replace one component; what happens? |
| §3.H Office-hours 6Q | YC-style demand-reality interrogation |
| §3.I Contrarian | One mainstream consensus might be wrong; which? |
| §3.J Failure-driven | A concrete present failure → next research question |
| §3.K High-risk asymmetric | Force ≥1 high-payoff-if-true branch |
| §3.L Meta self-audit | 7-question audit of LLM blind spots |

Empirically (from sci-paper usage), 12 is enough to escape LLM
generation-distribution attractors but small enough that each one fires
in a reasonable wall-clock budget. 7 leaves visible blind spots;
20 starts hitting redundancy unless the root is unusually rich.

### Why hard-ban "defer / future-work / NEEDS-MORE-INFO" leaves?

This is the single most important behavioral lever. LLMs default to
producing branches like:

> "This direction looks promising but requires a detailed survey of
> existing literature beyond the scope of this analysis. Defer to
> future work."

That's a non-result dressed as a result. The hard ban in §F8 forces
the engine to either (a) actually do the lookup (`WebFetch` / `Read` /
`Bash`) until the branch can be evaluated, or (b) re-route via §3.E
constraint-variation to a related branch that *can* be evaluated with
current resources. Either way, the leaf comes out **complete or
explicitly tagged `INCOMPLETE_FORBIDDEN`** so the recursion can't
mistake it for terminal.

### Why default `--width / --depth / --rounds` to infinity?

Because finite caps give the engine permission to declare success at
the cap regardless of substance. The intended termination is §6's
**stable-convergence** condition: novelty / confirmed / recommended
ratio drops below `--min-novelty-ratio` (default 0.15) across the last
2 rounds, *with* all 12 framings exercised at least once, *with* every
high-verdict leaf re-expanded at least once, *with* §3.K having
produced at least one fully-explored high-risk branch.

Resource caps are kept as escape valves (`--width 50` for a quick
exploration), but they're explicitly *not* the default. When a cap is
hit, the engine still drives every in-flight node to a complete state
before reporting `WIDTH_CAP_REACHED` / `DEPTH_CAP_REACHED` /
`ROUNDS_EXHAUSTED`.

### Why English-canonical multilingual output?

The engine needs a stable machine skeleton across presets, resumes, chained
stages, validators, and downstream tooling. Translating flags, frontmatter or
JSON keys, verdict labels, framing IDs, statuses, or filenames would create
schema forks rather than language support. cc-tree therefore keeps those
identifiers in canonical English while localizing human-readable node prose,
derivations, evidence explanations, warnings, and report narrative through
`--lang <tag|auto>`.

English is the omitted-flag default. `auto` detects the dominant natural
language of the primary invocation/root content and falls back to English for
mixed, unrecognized, path-only, and code-only inputs. The concrete language is
persisted before the root node and cannot change on resume or mid-chain. Input
artifacts, comments, glossaries, profile bodies, custom-preset prose,
citations, and quotations remain language-agnostic; quotations stay verbatim
and receive a localized explanation instead of being silently rewritten.

Documentation uses the same one-skeleton principle. Unsuffixed Markdown is
canonical English, `.zh.md` is the maintained Chinese parallel, and
`docs/languages.json` inventories every pair or canonical-only exception.
Each Chinese file records the LF-normalized source SHA-256, so editing English
makes CI fail until the translation is reviewed and refreshed. Deterministic
checks cover banners, ordered fence-aware heading structure, fenced examples,
Chinese body coverage, and preservation of machine tokens; semantic
translation quality remains a human review responsibility.

### Why incremental write to disk?

So the tree state survives any interruption (process kill, context
overflow, user `^C`, agent crash). Each `<id>.md` lands the moment its
12 fields are filled. Restart-from-where-you-left-off is the default
mode rather than a special feature.

### Why a `glossary grill` prelude (and why optional)?

If the root-node terminology is sloppy, the entire tree solves a
problem that isn't quite what the user meant. The `--glossary <path>`
flag (or `--no-grill` to skip) prompts the engine to lock root-node
nouns to the project's authoritative term sheet before §2 baseline
runs. sci-paper hard-coded `FACTS.md`; cc-tree generalizes to any
path the user supplies (or skips entirely).

## What this plugin is NOT

- Not a one-shot brainstorm tool. The engine is recursive and
  convergence-terminated; expect minutes to hours per run depending on
  width / depth.
- Not a chat interface. It's full-auto by design; the user supplies
  the root and (optionally) flags, then the engine runs to convergence
  without further prompting. Mid-run intervention is via flag overrides
  on the next invocation, not interactive Q&A.
- Not a substitute for a domain expert. The output is a structured
  exploration tree with file:line-cited evidence at every node; a human
  still decides which leaves to act on.
- Not bundled with any model. It uses Claude Code's own model setting;
  the plugin is pure prompt engineering.

## Compared to existing tools

| Tool | Mode | Output shape | Convergence |
|---|---|---|---|
| Generic "brainstorm" prompts | one-shot LLM call | flat list | none |
| Tree-of-Thoughts (academic) | iterative search | tree of partial paths | search-budget |
| LangChain agents | tool-use loop | linear log | tool-call limit |
| `cc-tree` | recursive divergent | full tree (disk-persisted) + final report | stable-convergence (substantive) |

The closest cousin is Tree-of-Thoughts; the key differences are
(a) cc-tree forces 12 specific framings rather than letting the model
pick branches, (b) cc-tree's convergence test is substantive rather
than search-budget-based, (c) cc-tree's nodes have a strict 12-field
schema with per-field validation rules (no "lazy" leaves), and
(d) cc-tree writes the tree incrementally to disk so the run survives
interruption.

## Open questions

1. **Field-agnostic § scoring.** The 5 score dimensions are
   preset-specific. **Resolved in v0.2.0** to the extent that
   `tools/validate_plugin.py` now hard-enforces the structural schema
   (`score_dims` count + each `key`/`name`/`desc`, `node_schema` count,
   `verdict_enum` roles, `convergence_metric`, `root_kind`) with
   behavioral tests in `tools/tests/test_validate.py`. A *semantic*
   "is this scoring scheme self-consistent / are the dims orthogonal?"
   check remains future work — structural validity is enforced;
   judgment of the rubric is not.

2. **Cross-preset chaining.** **Resolved in v0.2.0**: the
   `/cc-tree:tree-chain` command + the universal `--seed-from`
   flag + `docs/chaining.md` handoff contract pipe
   *brainstorm → design → attack* (top-K between stages, always logged).

3. **Per-framing sub-agent dispatch.** **Resolved in v0.2.0**: §8.1 now
   makes sub-agent dispatch **mandatory** at fan-out ≥ 5 (not optional),
   with a precise dispatch + re-verification contract.

4. **Multi-language preset support.** **Resolved in v0.4.0**: one
   English machine skeleton now supports deterministic `--lang <tag|auto>`
   output, run/resume/chain language persistence, arbitrary-language input and
   custom prose, eight maintained English↔Chinese documentation pairs, and a
   manifest + source-digest + structural/token validator. Translation quality
   remains a human review responsibility; freshness and schema preservation
   are CI-enforced.

## Decision

Shipped v0.1.0 as: one skill + four presets + four commands + full
`ENGINE.md` + `framings.md` + `presets.md` + CI + validator.

v0.2.0 closes the v0.1 doc/impl drift (the validator now enforces what
the docs promise) and lands chaining, mandatory parallel dispatch,
`--field` weighting, and the first two bilingual docs, making the plugin
self-contained and CLI-installable.

v0.3.0 is a 26-fix debug sweep plus drift-class hardening: the
frontmatter parser learned block-map list items, and five cross-file
consistency checks (dead anchors, example line bounds, bilingual title
parity, command-flag registry, field-profile schema) turned the defect
classes that sweep found into CI failures.

v0.4.0 completes the language architecture: English is the canonical/default
machine skeleton, human-readable output is selected per run, arbitrary-language
content remains valid input, Chinese public documentation is maintained as
seven explicit pairs, and CI fails closed on version or schema drift.

v0.5.0 is the second debug sweep, done line-by-line over every shipped
file. Two parser defects (a crash on an empty list entry, a misparse of
frontmatter ending at EOF) and 22 contract-drift defects were fixed —
mostly places where the runtime prompt, the engine spec, and a preset's
own declared schema disagreed about a field name, a verdict label, or a
section number. Three more drift classes became CI failures: `§N` prose
references must resolve to a real heading; anchors must live in the link
href, where the validator can see them; and a machine token registered in
a form that matches nothing — which left its i18n parity check silently
vacuous — is caught, with `[NEEDS_VERIFICATION]` normalized and
`root_underspecified` / `tool_blocked` registered.

v0.6.0 is the third sweep, and the first run adversarially by a second
model family: three parallel read-only `gpt-5.6-sol` reviews (55
findings, each acted-on claim reproduced by execution before any fix).
Where the earlier sweeps fixed drift *between* files, this one fixed
the gates themselves: the frontmatter parser stopped silently
recovering from malformed input, the preset validator stopped accepting
non-string values / duplicate identifiers / path-escaping artifact
names, and the i18n checker closed its laundering channels (comments
counted as Chinese prose, exception lists registering translations,
fences rescuing localized inline identifiers). One genuine engine-
contract bug surfaced: ENGINE.md §0.1's terminal-leaf definition
contradicted §5.3/§7.4 on whether `kept`/`pruned` tips count toward
`width`; terminality is now defined by verdict role. Structurally,
`sys.exit` left the check helpers (a typed `ValidationError` boundary
replaces it) — the refactor the complexity scan and both review lenses
independently converged on — while the parser and i18n algorithms were
deliberately left intact.

v0.7.0 restructures the repository and rewrites the README, on the back of
a fourth sweep — a five-dimension multi-agent audit whose findings were put
through an independent refuting pass before any of them was acted on. The
theme this time was *checks that fail open*: running the test suite made the
validator fail (its skip list had been maintained by hand against
`.gitignore`), `pytest` passed unconditionally because the suites recorded
diagnostics into a list only `main()` read, relative links without a
`#fragment` were never resolved, and the run-output heuristic hid the
repository's own showcase fixtures. Structurally: `EVALUATION.md` moved into
`docs/`, the tests moved into `tools/tests/`, and a documentation index and
contributor guide were added.

v0.7.1 closes the last coverage gap that v0.7.0 documented but did not fix.
A trace showed 17 of `validate_plugin.py`'s 35 functions were never entered
by any test — including `main()` and every cross-file sub-check — so
`tools/tests/test_checks.py` now runs all seven check groups against a
synthetic repository and mutates it once per rule. Writing it immediately
found three defects the shipped repository could not surface: deleting
*every* command wrapper passed the wrapper-parity check, `_check_command_flags`
bound `REPO` at def time and so always ignored its argument, and v0.7.0's own
zero-count tripwire was strict enough to reject a legitimate repository. The
same release applies a documentation audit's 14 confirmed findings, 26 having
been rejected by the refuting pass — including one this project's own
maintainer had called confirmed.
