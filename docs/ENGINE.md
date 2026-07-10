# cc-tree ENGINE specification

> 🌐 中文平行版：[`ENGINE.zh.md`](ENGINE.zh.md)（this English file is canonical).

> This document is the **engine contract**. The `/cc-tree:tree` skill
> reads this file at session start (along with the active preset and
> `framings.md`) and treats every section as binding. Presets supply
> *vocabulary* (verdict names, node-field names, score-dim names) but
> may **not** weaken any rule below — they extend, they don't override.

The engine is a recursive radial-tree generator with substantive
convergence as its primary termination criterion. The mental picture
is a phylogenetic tree growing outward from one root:

- **root** (centre) = the input the user supplied — a topic, an
  artifact (file/document), a problem statement, or a design prompt.
  The preset's `root_kind` field determines which.
- **depth** (concentric rings) = how many framing-recursion rounds
  away from root a node sits.
- **node** (any point) = one *idea* / *critique* / *option* /
  *audit-finding* — whatever the preset's `subject_label` calls them.
  Every node has the same 12-field schema (§4).
- **width** (the outermost arc) = the final number of terminal leaves
  delivered. Width is decided by §6 convergence, not by a hand-picked
  cap.

**The five irreducible primitives**:

1. **§2 baseline** — the root must be grounded in real, verified
   inputs (Read files, Grep symbols, WebFetch references, glossary
   lock). Presets supply the recipe; the engine enforces "no
   undocumented field".
2. **§3 12 framings** — every node, every round, gets exposed to
   all 12 framing passes. Each pass produces ≥ 1 child. Skipping a
   framing voids the pass.
3. **§4 12-field derivation** — every child must have all 12 fields
   filled with non-hedged, evidence-bearing content before it counts.
   Hedge words and `defer/future-work/TODO`-style placeholders force
   the node to `INCOMPLETE_FORBIDDEN`.
4. **§5 score → verdict → recurse decision** — sum 5 score-dim scores
   (each 0–3, max 15); map to preset's verdict_enum; only the
   `advances` verdict triggers another round of §3 on that node.
5. **§6 convergence** — 6 simultaneous conditions, all of which must
   hold for `CONVERGED` status. Otherwise terminate via user-specified
   cap (with all leaves still complete) or keep going.

The remaining sections (§7 output, §8 tools, §9 anti-patterns) are
*how* the above five are executed and reported.

---

## 0. Data model and growth criterion

### 0.1 Tree growth rule

A node spawns children when:
- §3 has been run on it (all 12 framings) — produces ≥ 12 child
  candidates (one per framing), plus any additional ones the framing
  prompt itself generates;
- AND at least one child passes §4 + §5 with `verdict = advances`.

A node is a **terminal leaf** (counts toward final `width`) when:
- §3 has been run on it AND
- no framing pass produced a child that survived §4 + §5 AND
- the node itself has score ≥ pruning threshold (else it's `DEAD-END`
  not a final leaf).

A node tagged `INCOMPLETE_FORBIDDEN` **never** counts as a terminal
leaf — it must be driven to a complete state (every field non-empty,
non-hedged, no defer-language) before recursion can finish.

### 0.2 Identity, persistence, and incremental write

Every node gets a stable `id` of the form `<depth>.<width>.<framing>`
or similar (the preset's choice; the engine guarantees uniqueness
within one tree-out directory). The node is written to disk **the
moment its §4 fields are filled** — not batched at the end. This
makes restarts from interruption trivial: re-invoke with the same
`--out <dir>` and the engine resumes from the highest-id node already
on disk.

`tree.json` is the source of truth; `tree.md` is the human view; both
get appended atomically per node.

---

## 0.5 Top-level forbidden patterns (violation → round invalid)

These eight patterns universally degrade exploration. They apply to
every preset — presets may add more, but cannot remove any.

### F1. No memory-cited claims

Every external assertion (file contents, API signatures, library
features, prior work, dataset properties, version numbers, error
messages, theorem statements) **must be verified in the same turn**
via `Read` / `Grep` / `Bash` / `WebFetch`. Unverifiable claims must be
tagged `[NEEDS VERIFICATION]` and the node downgraded; they may **not**
be used as a premise for any downstream node.

Forbidden phrases anywhere outside an `assumptions` field (which is
where guesses are *explicitly* documented as guesses):

> 应该 / 大概 / 我相信 / 通常 / 可能 / 也许 / 或许 / probably / maybe /
> I recall / I believe / typically / usually / in my experience

### F2. No pseudo-divergence

Two child branches that differ only in synonym substitution or
sentence reordering are **the same branch**. Merge them and keep the
higher-scored side; tag the other `MERGED_INTO=<id>`. The merge
threshold is cosine similarity ≥ 0.85 on the subject statement, but
human judgment overrides — if two statements describe the same
underlying mechanism, they merge regardless of similarity score.

A new branch must offer **at least one** of:
- a different testable prediction or observable consequence,
- a different falsification / failure path,
- a different resource profile (data / compute / time / personnel).

### F3. No derivation skipping

"This direction looks interesting" is not a verdict. Every node must
have a full §4 derivation chain (math / mechanism / dependency-trace —
preset-determined). The `derivation` field cannot contain `details
omitted`, `easy to show`, `obvious`, `略`, `自明`, or equivalent.

For numerical claims the engine **must** run a one-shot `python
(sympy/numpy)` sanity check via `Bash` and paste the output into the
field. Failed or unrunnable checks downgrade the verdict at most one
step below CONFIRMED / PROMISING / RECOMMENDED.

### F4. No risk aversion (each framing pass must include 1 high-risk branch)

Some framing passes (especially §3.K asymmetric-payoff) exist to
force exploration of high-risk / high-reward branches. Skipping or
dismissing the high-risk slot ("too speculative", "out of scope")
voids the pass. The high-risk branch must be **fully** derived
(§4 12 fields) even if it lands at `DEAD-END` — the value is in the
derivation, not the verdict.

### F5. No pseudo-convergence

"I'm not generating new ideas" is not §6 convergence. Convergence has
six simultaneous conditions (§6); all six must hold. In particular,
the engine must have:
- exercised every §3.A–§3.L framing at least once on the root,
- re-expanded every `advances`-verdict leaf at least once,
- produced ≥ 1 fully-explored high-risk branch (§3.K),
- driven every `INCOMPLETE_FORBIDDEN` node to a complete state,
- watched the `convergence_metric` ratio drop below
  `--min-novelty-ratio` (default 0.15) across the last 2 rounds.

### F6. No user-interrupt decisions (full-auto contract)

Once `/cc-tree:tree` is invoked with a parsed root and a loaded
preset, the engine runs to convergence (or cap-trip) without further
user prompting. Ambiguity is resolved by **picking the
information-densest branch** and proceeding. Stop only when:
- a §0.7 user-specified cap is reached **and** all in-flight nodes
  are complete,
- §2 baseline cannot be built because the root is unparseable (report
  `EARLY_STOP=root_unparseable`),
- a tool DENY from cc-enslaver or sandbox policy blocks an essential
  read (report what's blocked; do not silently switch strategies).

### F7. Resource caps default to ∞; can only narrow via flags

Default `--width / --depth / --rounds / --max-branches` are all ∞ or
`conv`. The engine **may not** internally narrow these. When a user
sets a finite cap and it's reached, the engine still drives every
in-flight node to a complete §4 state before reporting the cap-trip
status — the visible leaf set is **always complete**.

### F8. Hard ban on deferred / incomplete leaves

Any node whose §4 fields contain any of the following phrasings has
its status forced to `INCOMPLETE_FORBIDDEN`:

> defer / deferred / 待定 / 留后 / 待确认
> 因成本限制 / 因算力限制 / 因时间限制 / 时间不够 / 算力不够
> future work / 留作 future work / TODO / FIXME
> 暂不展开 / 略 / details omitted / 省略 / 暂略
> 应该 / 大概 / 我相信 / 通常 / 可能（in non-`assumptions` fields)
> NEEDS-MORE-INFO 永久挂起 / 无法判定 / 看作者意思 / 得问作者

If the field genuinely needs external resources to fill, the engine
**must** acquire them in the same turn via `WebFetch` / `Read` /
`Bash` / `WebSearch`. If acquisition fails, the node is rerouted via
§3.E (constraint-variation) into a sibling that *can* be filled with
available resources, and the original node remains `INCOMPLETE_FORBIDDEN`
until completion.

This is the engine's single biggest behavioral lever; without it,
every exploration degenerates into "10 promising directions; details
left to future work."

---

## 1. Invocation

```
/cc-tree:tree <root> --preset <name|path> [flags]
```

### 1.1 Root resolution

`<root>` is interpreted per the preset's `root_kind`:

| `root_kind` | `<root>` interpretation |
|---|---|
| `topic` | A string. Used verbatim as the root-node "subject" line. |
| `artifact` | A file path (`.md`/`.tex`/etc.). Full file Read before root construction. |
| `code` | A file or directory path. Full Read or recursive Glob+Read. |
| `design-prompt` | A string OR `.md` file. If file, full Read; treated as a structured prompt with goals / constraints / context. |

If `<root>` is empty:
- presets that allow inference (`brainstorm`'s research mode) may
  derive from the current project state (Read `CLAUDE.md` /
  `README.md` / recent `git log`);
- otherwise the engine emits `EARLY_STOP=root_unparseable` and exits.

### 1.2 Preset resolution

`--preset <name>` resolves to `presets/<name>.md` in this plugin's
install directory. `--preset <path>` resolves to a literal file path
(absolute or relative to the caller's CWD). Either way the preset is
Read in full before §2 baseline.

### 1.3 Flag table

(See `skills/tree/SKILL.md` for the full table; same semantics
applied here. The engine MUST raise errors on unknown flags rather
than silently ignoring them. A preset and its command wrapper may
document additional preset-specific flags — e.g. `attack`'s
`--focus <section|claim|equation>` — and a flag documented by the
active preset or its wrapper is not "unknown".)

---

## 2. §2 Baseline construction

The preset supplies the recipe; this section defines the engine's
universal contract.

### 2.0 Glossary grill prelude (mandatory unless `--no-grill`)

> Borrowed from `mattpocock-skills:grill-with-docs`. A root built on
> sloppy terminology produces a thousand leaves solving a problem the
> user didn't ask about.

Steps:

1. **Locate glossary source.** Read the first existing among:
   - `--glossary <path>` (if explicitly supplied);
   - the preset's `glossary_paths` list (preset frontmatter);
   - `FACTS.md` / `glossary.md` / `CLAUDE.md` in the project root;
   - if none exists, mark `[NEEDS_GLOSSARY]` and continue (§6
     convergence will add a warning).

2. **Decompose root nouns.** Extract noun-phrases from `<root>`.
   Single abstract words → skip; multi-word noun phrases with
   technical content → grill each one.

3. **Per-term decision matrix** (one question at a time per
   `grill-with-docs` convention):
   - **EXACT MATCH** in glossary → adopt glossary definition silently,
     record to `<out>/glossary-anchors.md`.
   - **ALIAS** → silently substitute the canonical name, record the
     alias in `glossary-anchors.md`.
   - **MISSING** → ask the user once, ≤ 3 options + a recommended answer.
   - **AMBIGUOUS** (≥ 2 glossary entries match) → ask once with
     specific `file:line` pointers.
   - **CONFLICT** (`<root>`'s usage contradicts the glossary) →
     **STOP** the engine; await user adjudication (modify root vs
     update glossary). Do not silently proceed.

4. **Produce `glossary-anchors.md`** with every grilled term + its
   chosen definition + `file:line` evidence. Every subsequent §3
   framing that introduces a new noun-phrase appends to this file.

`--no-grill` skips this step; root-node terms get tagged
`unverified`; §6 convergence adds a warning "no glossary grill
performed; strong-convergence claim not allowed".

### 2.1 Root construction (preset-determined)

Following the preset's baseline recipe, fill the root node with the
preset-specified set of fields (typically 5–8). Each field requires:
- a one-sentence factual statement, AND
- a `file:line` reference or URL or command-output citation.

Hedged / unverified entries in the root are not allowed — the engine
re-prompts the baseline steps until the root is fully grounded.

If after a documented effort the root still has empty fields:
- presets that allow inference (`brainstorm` research-mode) infer
  the missing fields from the closest available project state and
  flag them `[INFERRED — verify with user]`;
- presets that do not allow inference (`attack`, `code-audit`) emit
  `EARLY_STOP=root_underspecified` and exit.

Root is written to `<out>/tree.md` + `<out>/tree.json` before any
§3 pass runs.

### 2.2 Field profile (optional, `--field <name|path>`)

A **field profile** supplies domain-aware reviewer weighting so the
engine attacks/explores the way a senior practitioner in that field
would, not just the way the LLM's generic training distribution does.
It is preset-agnostic — any preset benefits.

Resolution (mirrors `--preset`):
- `--field <name>` → `field-profiles/<name>.md` in this plugin's
  install directory. Files beginning with `_` (e.g. `_template.md`)
  are scaffolding, not selectable fields — `--field _template`
  resolves to `[FIELD_PROFILE_NOT_FOUND]`;
- `--field <path>` → a literal file path;
- if neither resolves to a readable file → emit a **warning**
  (`[FIELD_PROFILE_NOT_FOUND]`) and continue. Field weighting is an
  enhancement, never a blocker (same non-blocking contract as
  `--no-grill`).

When a profile loads, `Read` it in full during §2 baseline and carry
its four lists into the framing passes that consume them:
- **Reviewer concerns** → weight §3.C (cross-disciplinary) and §3.D
  (red team) toward the named concerns first.
- **Field consensuses** → seed §3.I (contrarian) with the listed
  consensuses and their known break-regimes.
- **Common failure modes** → seed §3.J (failure-driven) candidates.
- **Evidence bar** → raise the §3.X / §4 citation standard to what
  the field treats as strong evidence.

A field profile **never** relaxes a universal rule (§0.5) — it only
re-prioritizes which branches get explored first. The
authoring format is documented in
[`field-profiles/README.md`](../field-profiles/README.md);
[`field-profiles/_template.md`](../field-profiles/_template.md) is a
domain-neutral starting point.

### 2.3 Seed-from (chaining substrate, `--seed-from <primary.md>`)

`--seed-from <path>` makes the run start from a **prior run's primary
deliverable** instead of (or in addition to) a fresh root. This is the
universal substrate for cross-preset chaining
([`chaining.md`](chaining.md)).

- `<path>` points at a previous run's `shortlist.md` / `options.md` /
  `confirmed.md` (or any list of subject lines).
- Each listed item enters the new tree as a **depth-1 seed node** with
  its `verdict_provisional` set to the preset's `advances` label, then
  is re-expanded with the full §3 pass to find children.
- Seed nodes are **not** re-validated as if novel — their content is
  taken as given; the value is the sub-tree grown beneath them (cf. the
  `--from-prior` anti-pattern: do not re-list seeds as new findings).
- `--seed-from` composes with a normal `<root>`: the root frames the
  run, the seeds prime depth-1.

`--from-prior` (used historically by the `attack` / `code-audit`
presets) is an **alias** for `--seed-from` and behaves identically.

---

## 3. §3 framing pass (12 universal framings)

> Full details + per-preset examples in
> [`framings.md`](framings.md). Below is a one-paragraph summary per
> framing. Every node runs **all 12** every round it's expanded.

### §3.A — First-principles
List the node's load-bearing assumptions. For each, ask "what's still
true after this assumption is stripped?" Output: ≥ 1 child whose
subject is the residual / minimal claim after assumption removal.

### §3.B — Inversion
The node argues / proposes X. Explore ¬X, the dual, the boundary
where X fails. Output: ≥ 1 child that flips the polarity.

### §3.C — Cross-disciplinary
List ≥ 3 external fields where the same structural problem appears
(biology / economics / CS / math / linguistics / …). Output: ≥ 1
child transplanting tooling from another field, with breakage cost
documented. If a `--field` profile is loaded (§2.2), exercise its
listed "reviewer concerns" before generic transplants.

### §3.D — Adversarial / red team
Adopt a reviewer-trying-to-disprove stance. List the 3 most
damaging counter-arguments. Output: ≥ 1 child that takes the
strongest counter and turns it into either a refutation experiment
(brainstorm/design) or a confirmed-or-refuted critique
(attack/code-audit).

### §3.E — Constraint variation
List the node's explicit and implicit constraints (data, compute,
time, API, audience). For each, ask "what changes if we relax it?"
and "what changes if we tighten it?". Output: ≥ 2 children (one
relax, one tighten).

### §3.F — Scale extrapolation
Currently the node operates at scale S. Extrapolate to 1000×, 0.001×,
and a domain boundary (Planck / cosmological / single-particle, or
the analogous boundary for the preset's domain). Output: ≥ 1 child
exposing a regime-specific failure or opportunity.

### §3.G — Substitution
Replace each major component of the node's structure (data set,
algorithm, target metric, audience, dependency) and observe the
change. Output: ≥ 1 child where one substitution produces a
non-trivial new direction.

### §3.H — Office-hours 6Q
A YC-style 6-question grilling:
1. Demand reality: who concretely will benefit, and how many?
2. Status quo: how do they cope today?
3. Sharpening: what's the narrowest "must, now, for this" slice?
4. Minimum wedge: what's the smallest experiment to validate the
   whole direction?
5. Prior art: who's already doing it?
6. Future-fit: will this matter in 5 years?

Output: ≥ 1 child that survives all 6 questions or explicitly
addresses where it fails.

### §3.I — Contrarian
Identify ≥ 3 mainstream consensuses the node implicitly depends on.
For each, ask "in what regime might this consensus be wrong?" Output:
≥ 1 child that targets one such consensus as the actual research /
critique / design question. When a `--field` profile is loaded (§2.2),
seed this pass from its "field consensuses" list and their known
break-regimes.

### §3.J — Failure-driven
List ≥ 3 concrete *present* failures (not "could be better" but
specific reproducible issues — `file:line`, Fig. N, command-output
mismatch). For each, ask "is this failure itself a question we
should pose?" Output: ≥ 1 child reframing a failure as a new node.

### §3.K — High-risk asymmetric payoff
Force ≥ 3 branch candidates whose expected value is dominated by a
small probability of paradigm-level success. Pick the most-concrete
and derive it fully. Output: ≥ 1 child. Engine MAY NOT skip this
framing (F4).

### §3.L — Meta (LLM blind-spot self-audit)
Self-audit, 7 questions:
1. Are all my branches from training-distribution-frequent framings?
2. Have I confused "what I can write" with "what's actually important"?
3. What's important to human experts but rare in LLM training data?
4. Is my prose "too smooth"? Real research / design / critique is
   rough, contradictory, partial.
5. Am I avoiding math-heavy branches? Add one.
6. Am I avoiding experiment-heavy / code-heavy branches? Add one.
7. Is the weirdest branch in the tree actually weird? Force another
   if not.

Output: ≥ 1 child sourced from the self-audit's blind-spot list.

### §3.X — External resource cross-check (per node, unless `--no-online`)

For each node, in addition to §3.A–§3.L, run one external cross-check.
**The query set is preset-determined** — see
[`framings.md` §3.X](framings.md) for the per-preset flavor. In brief:
brainstorm/design hunt for prior art + invocable tooling; attack hunts
for published critiques / errata / misrepresented citations; code-audit
hunts for CVEs / advisories / the same pattern elsewhere in the repo.

Universal steps:
1. `WebSearch` the preset-appropriate query set (baseline `<subject>
   arxiv` / `<subject> github` + the preset's specialized queries).
2. `WebFetch` each promising URL to confirm its actual contents — a
   `WebSearch` snippet is never sufficient on its own (§F1).
3. Record findings in the node's external field (`external_resources`
   for brainstorm/design; `external_check` / `related_findings` for
   attack/code-audit).

`--no-online` skips §3.X; node tagged `external_resources_unchecked=true`.

---

## 4. §4 per-node derivation (12-field schema)

Every node — root and every child — has a 12-field schema. Names
vary per preset (e.g. brainstorm's `idea_statement` vs attack's
`critique_statement`), but every preset must supply exactly 12 named
fields and the engine enforces non-empty + non-hedged + no-defer for
each.

Universal field categories:

| Slot | Universal purpose | Examples per preset |
|---|---|---|
| 1 | Subject statement (≤ 3 sentences) | `idea_statement` / `critique_statement` / `option_statement` / `finding_statement` |
| 2 | Parent framing (§3.A–§3.L) | always `parent_framing` |
| 3 | Position / target | `artifact_position` for attack; not applicable for brainstorm |
| 4 | Derivation / evidence | `derivation` / `evidence` / `mechanism` / `repro_steps` |
| 5 | Assumptions (≥ 3) | always `assumptions` |
| 6 | Predictions / consequences | `predictions` / `observable_consequences` |
| 7 | Defense / counter-defense | `falsifiability` (brainstorm/design) / `artifact_defense` (attack) / `mitigation_present` (code-audit) |
| 8 | Comparison to prior work / state | `novelty_vs_literature` / `alternative_interpretations` |
| 9 | Cost / fixability / feasibility | `feasibility` / `proposed_fix` / `cost_of_change` |
| 10 | Risks / pitfalls | always `risks` |
| 11 | Branch potential | `branch_potential` / `sub_critique_potential` |
| 12 | Provisional verdict | always `verdict_provisional` |

Strict requirements applying to every field:

1. **Non-empty.** A blank field forces `INCOMPLETE_FORBIDDEN`.
2. **Non-hedged.** §F1's forbidden phrases (outside `assumptions`)
   force `INCOMPLETE_FORBIDDEN`.
3. **No defer language.** §F8 forbidden phrases force
   `INCOMPLETE_FORBIDDEN`.
4. **Citations.** Any claim about external state must carry `file:line`
   / URL / command-output evidence in-line.
5. **Numerical self-check.** Any number, equation, or constant must be
   verified by a one-shot `python (sympy/numpy)` Bash call in the
   same turn; failed checks downgrade the verdict.

Long fields (derivation > 100 lines, evidence > 100 lines) are spilled
to `nodes/<id>.md` with the main `tree.md` carrying a `→ nodes/<id>.md`
pointer.

---

## 5. §5 scoring, verdict, recursion decision

### 5.1 Scoring

Each node receives 5 scores along the preset's `score_dims`. Each
dimension is **0–3, integer**, no half-points. The sum `score = d1
+ d2 + d3 + d4 + d5` has a maximum of 15.

Dimensions are preset-specific; common patterns:

- brainstorm: S=scientific-value, N=novelty, F=feasibility,
  K=falsifiability, B=branch-potential
- attack: S=severity, P=specificity, R=reproducibility,
  F=fixability, B=sub-critique-fan-out
- design: V=value, R=reversibility, C=cost, F=fit-with-constraints,
  E=evidence-strength
- code-audit: S=severity, P=position-specificity,
  R=reproducibility, F=fixability, X=exploit-likelihood

### 5.2 Verdict mapping

Each preset declares a 4-tuple `verdict_enum = (advances, kept,
pruned, blocked)`. The mapping rule is:

- `score ≥ 11` (and any preset-specific extra gates, e.g. attack's
  "no artifact_defense found") → `advances`
- `8 ≤ score ≤ 10` → `kept` (stays in tree but not re-expanded)
- `score ≤ 7` → `pruned` (greyed, derivation kept for reference)
- any field tagged `[NEEDS VERIFICATION]` dominating → `blocked`
  (= `INCOMPLETE_FORBIDDEN`; cannot count toward terminal width)

The 4 verdict labels are preset-supplied:

| Preset | advances | kept | pruned | blocked |
|---|---|---|---|---|
| brainstorm | PROMISING | MARGINAL | DEAD-END | NEEDS-MORE-INFO |
| attack | CONFIRMED | MARGINAL | REFUTED | INCOMPLETE_FORBIDDEN |
| design | RECOMMENDED | VIABLE | NOT-RECOMMENDED | NEEDS-MORE-INFO |
| code-audit | CONFIRMED | MARGINAL | REFUTED | INCOMPLETE_FORBIDDEN |

Note the asymmetry between brainstorm and attack: attack's `pruned`
is `REFUTED`, meaning *the engine found the artifact already
defends against the critique* — this is **valuable information**
and the node stays in the tree as a positive record.

### 5.3 Recursion decision

After §4 + §5:
- `advances` → enqueue this node as a root for another §3 pass next
  round.
- `kept` → keep in tree, don't re-expand.
- `pruned` → keep in tree (grey), don't re-expand.
- `blocked` → engine must drive it to one of the other three before
  declaring §6 convergence; until then it blocks termination.

### 5.4 Sibling merging

Within the same parent's children: if any two siblings have ≥ 0.85
cosine similarity on their `subject_statement` (field 1) plus an
overlapping or identical `position/target` (field 3, when
applicable), they merge:
- keep the higher-scored side;
- tag the other `MERGED_INTO=<id>`;
- the merged-out node remains visible in `tree.md` but with no
  further expansion.

Human judgment overrides cosine similarity — if two siblings are
*about the same underlying mechanism* despite scoring < 0.85, they
merge.

---

## 6. §6 convergence

> "Looks done" is not convergence evidence. All six conditions below
> must be **simultaneously** true for the engine to declare
> `CONVERGED`.

### 6.1 The six conditions

1. **All nodes complete.** No node currently has status
   `INCOMPLETE_FORBIDDEN`. §F8 binds here.
2. **Convergence ratio dropped.** Over the last 2 expansion rounds,
   `(new nodes with verdict=advances) / (total new nodes) <
   --min-novelty-ratio` (default 0.15).
3. **All 12 framings exercised.** §3.A through §3.L each fired ≥ 1
   time on the root.
4. **All `advances` leaves re-expanded.** Every node that ever held
   the `advances` verdict was treated as a root for ≥ 1 subsequent
   §3 pass, and that pass produced no further `advances` children.
5. **§3.K branch present.** At least one fully-derived (§4 12
   fields), §5-scored high-risk branch exists in the tree (regardless
   of its final verdict). It must not be a placeholder dropped in by
   §F4 enforcement.
6. **User-specified caps not tripped.** If `--width / --depth /
   --rounds` were set finite, none has been reached. If any was
   reached, the engine reports `WIDTH_CAP_REACHED` /
   `DEPTH_CAP_REACHED` / `ROUNDS_EXHAUSTED` instead, and all visible
   leaves must still be complete (§F7).

### 6.2 Termination decision table

Evaluated top-to-bottom each round; first matching row wins:

| Condition | Status reported | Requirements |
|---|---|---|
| All 6 conditions above hold | `CONVERGED` | — |
| `--width N` cap reached + all leaves complete | `WIDTH_CAP_REACHED` | §4 + §5 complete on every visible leaf |
| `--depth N` cap reached + all leaves complete | `DEPTH_CAP_REACHED` | same |
| `--rounds N` cap reached + all leaves complete | `ROUNDS_EXHAUSTED` | same |
| Any cap reached but `INCOMPLETE_FORBIDDEN` leaves remain | **engine must NOT stop**; complete them first |
| Root unparseable in §2 baseline | `EARLY_STOP=root_unparseable` | only valid before §3 starts |
| Sandbox / tool DENY blocking essential reads | `EARLY_STOP=tool_blocked` | report what's blocked |

When any of `CONVERGED` / `*_CAP_REACHED` / `ROUNDS_EXHAUSTED` is
reached, write the §7 final report and exit. `EARLY_STOP` exits
without a final report (no exploration was completed) but the partial
`tree.md` remains on disk.

"Exploration cost is too high" / "user might be waiting too long" /
"reasonable people would stop here" are **not** stop conditions
(§F7 + the engine's design intent). If a user wants a short run,
they pass `--width 20` or similar — the engine then truthfully
reports `WIDTH_CAP_REACHED`, not `CONVERGED`.

---

## 7. §7 output

### 7.1 Incremental write contract

The engine writes to disk **at every node completion**, not in
batches:

- `tree.md` is appended (one ≤80-char outline entry per node).
- `tree.json` is appended (one full-12-field object per node).
- `nodes/<id>.md` is created/replaced if any field exceeds 100 lines.

If the engine crashes / is interrupted / the context window fills,
the on-disk state is consistent up to the last node-write. Re-invoke
with the same `--out <dir>` to resume.

### 7.2 Output directory layout

```
<out>/
├── tree.md             # outline of every node; primary human view
├── tree.json           # full data for every node; machine source of truth
├── glossary-anchors.md # §2.0 prelude output (if --no-grill wasn't set)
├── <primary>.md        # preset's "advances" deliverable
│                       #   brainstorm: shortlist.md
│                       #   attack:     confirmed.md
│                       #   design:     options.md (recommended)
│                       #   code-audit: findings.md
├── <secondary>.md*     # preset's marginal / pending / refuted lists
├── REPORT.md           # §7.4 final-report block (also echoed to stdout)
└── nodes/
    └── <id>.md         # long-field spillovers
```

### 7.3 `tree.md` per-node format

```markdown
### <id>  <subject_statement[:80]>
- **parent**: <parent_id> | **framing**: §3.X | **score**: d1=_ d2=_ d3=_ d4=_ d5=_ → total=_
- **verdict**: <advances|kept|pruned|blocked label>
- **<field-2>**: …
- **<field-3>**: …  (or `→ nodes/<id>.md` if long)
- **<field-4>**: …
- …
- **children**: [id1, id2, ...]
```

(The exact field names come from the preset's `node_schema`. The
template above shows the universal scaffolding; the engine substitutes
the preset's labels.)

### 7.4 Final report

Emitted to stdout (and saved to `<out>/REPORT.md`) after termination:

```
## cc-tree report — <root summary> — preset=<name>

### Status
- termination: CONVERGED / WIDTH_CAP_REACHED / DEPTH_CAP_REACHED / ROUNDS_EXHAUSTED / EARLY_STOP=<reason>
- mode: <preset's mode label if applicable>
- tree: max_depth=D, leaf_count=W (= final width), total_nodes=N
- verdict distribution: advances=A, kept=K, pruned=P, blocked=0
  (if blocked > 0 → report is INVALID; engine returned to §4)
- rounds: R
- triggers: <which §6 conditions fired or which cap tripped>
- user caps: width=<N|∞>, depth=<N|∞>, rounds=<N|conv>

### Top deliverables (advances, sorted by score desc)
1. [id] <subject_statement> — score=…
   - <key field excerpts>
   - first concrete action / experiment / fix: …
2. ...

### Kept-but-not-expanded (kept verdict)
[list with score and one-line summary; useful for "consider later"]

### Pruned (pruned verdict, kept for reference)
[just IDs and one-line summary]

### §3.L meta self-audit
- Weirdest branch: <id> — <one-line>
- §3.K high-risk yield: <one-line>
- Blind spots the engine couldn't escape (honest declaration): <one-line>

### F8 completion self-audit
- All visible leaves are fully derived (no defer / future-work / TODO / NEEDS-MORE-INFO language anywhere): YES / NO
- If NO → report is INVALID; engine returned to §4

### Suggested next steps (1–3 only)
1. <action with file:line / URL evidence>
2. ...
```

---

## 8. Tool-usage projection

The engine uses Claude Code's standard tools according to this
mapping. Presets MAY extend with preset-specific tool requirements
(e.g. `code-audit` adds requirements around `Grep` + AST-style
inspection) but cannot weaken the universal mapping.

| Engine task | Required tools | Forbidden shortcuts |
|---|---|---|
| §2 baseline construction | `Read` / `Glob` / `Grep` / `Bash(git log)` | "I recall the project state" |
| §2.0 glossary lookup | `Read` (glossary file in full) | "I'll guess what the term means" |
| §3 framing pass — literature check | `WebFetch` (arXiv abs / DOI / spec page) | `WebSearch` snippets used as conclusions |
| §3 framing pass — code / data check | `Read` (full file) / `Grep` / `Bash` (run repro) | Reading only the diff or a search hit |
| §4 numerical self-check | `Bash + python (sympy / numpy)` | "Easy to verify" / "obvious by inspection" |
| §4 artifact_defense / mitigation_present check (attack/code-audit) | `Grep` across ≥ 5 major sections + `Read` each hit | Only checking adjacent paragraphs |
| Parallel framing pass for width ≥ 5 | `Agent(Explore)` or `Agent(general-purpose)` sub-agents | Sequential when wall-clock matters |
| Incremental tree write | direct `Write` / `Edit` on `tree.md` + `tree.json` | Batching to "end of run" |

### 8.1 Sub-agent dispatch (MANDATORY when a node's expected fan-out ≥ 5)

When a node will produce ≥ 5 children in a round — **always true for the
root** (12 framings) and for any hot leaf — the engine MUST parallelize
the §3 framing passes across sub-agents instead of running them
sequentially. Sequential execution at that fan-out is a defect, not a
stylistic choice (§9 anti-pattern "run §3 sequentially"). Below 5
expected children (deep, mostly-marginal leaves) sequential is allowed:
the framings themselves are cheap and the real cost is the §4
derivation that follows.

**Dispatch protocol:**

1. Spawn one `Agent(Explore)` (or `Agent(general-purpose)`) per framing
   pass — or batch 2–3 framings per agent to stay within the
   concurrency cap. Each sub-agent prompt is **self-contained**:
   - the node's full §4 fields (context the sub-agent can't otherwise
     see);
   - the framing pass's prompt (the §3.A–§3.L body from
     [`framings.md`](framings.md));
   - the preset's per-framing flavor examples;
   - the output contract: return ≥ 1 child with fields 1 (subject),
     4 (derivation/evidence), 5 (assumptions), 6 (predictions), 7
     (defense) draft-filled, **plus every `file:line` / URL it relied
     on** so the main agent can re-verify.
2. The main agent **merges** returned children: apply §F2 / §5.4
   de-duplication across sub-agents (two agents routinely surface the
   same branch), then finish the remaining §4 fields and run §5
   scoring on the survivors.
3. The main agent **re-verifies every citation** a sub-agent returned
   (the `file:line` still says what the agent claimed; the WebFetch'd
   URL still supports the point) before the child counts — cc-enslaver
   rule 04 applies transitively; a sub-agent's unverified claim is not
   evidence.

A sub-agent that returns nothing usable (all branches pseudo-divergent
or unverifiable) does **not** excuse skipping that framing — the main
agent runs it inline instead. All 12 framings must still fire (§F4).

---

## 9. Anti-patterns (full list)

In addition to the eight §0.5 forbidden patterns:

- ❌ **"I generated 10 directions, one line each."** §4 12 fields not
  filled → branch is not a node.
- ❌ **"I believe this work has been done / hasn't been done."** Must
  `WebFetch` to confirm; `WebSearch` snippet alone is insufficient.
- ❌ **"Derivation too long, see comments."** Spill to
  `nodes/<id>.md` — every byte preserved on disk.
- ❌ **"Looks like we've converged, the latest round was slow."** §6
  has six conditions; verify all six.
- ❌ **"High-risk branch is too speculative, skip §3.K."** Violates
  §F4 + §3.K; the entire pass is invalidated.
- ❌ **"To save context, I'll only show high-scored branches."** Tree
  is on-disk; context doesn't constrain output.
- ❌ **"`WebSearch` returned nothing → it's novel."** Try ≥ 3 keyword
  combinations; check adjacent fields; check non-English sources if
  the preset's domain warrants it.
- ❌ **"User didn't ask for parallelism, run §3 sequentially."** At
  width ≥ 5, sub-agent dispatch is a performance necessity, not a
  preference.
- ❌ **"Tree too big to display, I'll trim."** User asked for
  exhaustive; trim is a violation of `--width` / `--depth` semantics.
- ❌ **"Ran framings A–D, that's enough."** Floor is 12 framings
  (§F4 + `--min-frameworks 12`); below that the pass is void.
- ❌ **"Leave as `NEEDS-MORE-INFO` for the user to decide."** §F8 +
  §6.1 forbid. The engine must drive blocking nodes to one of the
  three terminal verdicts.
- ❌ **"Cost too high, early-stop."** §F7 + §F8 forbid. Caps trip
  truthfully; cost is not a cap.
- ❌ **"User wants critique-only, skip `proposed_fix`."** `attack`
  and `code-audit` presets require `proposed_fix` on `advances`-verdict
  nodes — without a fix the verdict downgrades to `kept`.
- ❌ **"Refuted critiques are noise, drop them."** `attack` /
  `code-audit` presets keep `refuted` nodes as positive records (the
  artifact handled this attack angle) — useful for response
  preparation.
- ❌ **"Re-list known issues from a prior pass."** If the preset has
  a `--from-prior <report>` flag (some do), prior items enter as
  *seed nodes*, not re-validated checklist items. The point is
  expansion, not duplication.

---

## 10. Preset extension surface (what a preset author can override)

A preset can:
- name the four verdicts (`verdict_enum`);
- name the 12 node fields (`node_schema`);
- name the 5 score dimensions (`score_dims`);
- pick which verdict counts toward the §6.2 ratio
  (`convergence_metric`);
- choose `root_kind` (topic / artifact / code / design-prompt);
- name the output deliverable files (`output_artifacts`);
- supply a custom §2 baseline recipe (in the preset body);
- supply preset-specific examples for each of §3.A–§3.L (in the
  preset body);
- add preset-specific anti-patterns (in the preset body).

A preset may NOT:
- remove any §0.5 forbidden pattern;
- reduce `--min-frameworks` below 12;
- weaken §F8 (defer / future-work / TODO ban);
- change the §6 six-condition convergence test;
- replace § 5's "score ≥ 11 → advances" mapping (it can add extra
  gates ABOVE 11, but not lower the floor).

If a preset's frontmatter declares a field count != 12, the engine
errors out at preset-load time. If a preset's `verdict_enum` has !=
4 entries, same. The validator (`tools/validate_plugin.py`) catches
these at CI time.

---

## 11. Compliance audit checklist

A maintainer auditing a preset for engine compliance:

- [ ] frontmatter has all required keys (`name`, `description`,
      `root_kind`, `subject_label`, `verdict_enum`,
      `convergence_metric`, `score_dims`, `node_schema`,
      `output_artifacts`);
- [ ] `node_schema` has exactly 12 entries;
- [ ] `verdict_enum` has exactly 4 entries with all four keys
      present;
- [ ] `score_dims` has exactly 5 entries, each with `key`, `name`,
      `desc`;
- [ ] `convergence_metric` matches one of the `verdict_enum` keys
      (typically `advances`);
- [ ] preset body's §2 baseline recipe addresses what to Read /
      Grep / WebFetch — no "TBD" placeholders;
- [ ] preset body's framing examples don't contradict §3 universal
      semantics (e.g. a preset claiming §3.B "Inversion" means
      something else than what this doc says fails compliance).

The shipped 4 presets are reference implementations of these rules.
