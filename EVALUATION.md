# Why cc-tree, and why this shape

Date: 2026-05-25
Author: skymanbp + Claude Opus 4.7

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
5. The **convergence ratio** (which verdict counts toward the §6.2
   "novelty / confirmed / recommended ratio drops below 0.15" check).
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

- Bug fixes (e.g. the §6.6 "user-cap-reached + incomplete leaves not
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

That's a non-result dressed as a result. The hard ban in §0.8 forces
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
   preset-specific. A user-supplied preset can override them, but
   there's no metric yet for "is this scoring scheme self-consistent?"
   May add a `tools/validate_preset.py` in v0.2.

2. **Cross-preset chaining.** A natural workflow is *brainstorm →
   pick top-3 → run design on each → pick winner → run attack on the
   winner*. Currently each invocation is independent; a `tree-chain`
   command could pipe outputs. Deferred to v0.3.

3. **Per-framing sub-agent dispatch.** The skill currently runs the
   12 framings sequentially in the main agent. When width ≥ 5,
   parallelizing via `Agent(Explore)` is mentioned in §8 but not
   automated. v0.2 candidate.

4. **Multi-language preset support.** Preset frontmatter and bodies
   are language-agnostic; the engine prose in `docs/ENGINE.md` is
   currently English-primary with Chinese mixed in selected places
   (inherited from sci-paper). A full bilingual version is a v0.4
   stretch.

## Decision

Ship v0.1.0 as: one skill + four presets + four commands + full
`ENGINE.md` + `framings.md` + `presets.md` + CI + validator.
Defer parallelization, chaining, and per-preset validators to v0.2+.
