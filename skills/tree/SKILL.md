---
name: tree
description: Universal radial-tree exploration engine. Loads a preset, builds a §2 baseline, then recursively applies 12 framing passes per node until stable convergence (no new high-verdict branches over the last 2 rounds + all 12 framings exercised + all leaves complete). Width × depth × rounds default to ∞; resource caps are opt-in. Hard ban on `defer / future-work / TODO / NEEDS-MORE-INFO` leaves — every leaf must be fully derived before counting. Use when 用户说 "brainstorm" / "attack" / "design exploration" / "code audit" / "explore options" / "find what's wrong" / "what should we build" / "tree of thoughts" / 想做穷尽的发散探索 / 想做多角度审查 / 想对一个工件 adversarial critique / 想做设计空间探索. Prefer the per-preset commands (`/cc-tree:brainstorm`, `/cc-tree:attack`, `/cc-tree:design`, `/cc-tree:code-audit`) when the use-case matches; call this skill directly with `--preset <name|path>` to override or supply a custom preset.
disable-model-invocation: false
argument-hint: "<root> --preset <name|path> [--width N|∞] [--depth N|∞] [--rounds N|conv] [--max-branches N|∞] [--out <dir>] [--glossary <path>] [--no-grill] [--no-online] [--min-frameworks N] [--min-novelty-ratio R] — `<root>` is a topic string, file path, problem statement, or design prompt; `--preset` is required (use `brainstorm` / `attack` / `design` / `code-audit` for shipped presets, or a path to your own .md)"
---

# tree — universal radial-tree exploration engine

> **What this skill is.** A single engine implementing recursive
> radial-tree exploration (root → 12-framing expansion → per-node
> 12-field derivation → score → recurse on high-verdict leaves →
> terminate on **substantive convergence**). What varies between
> use-cases (brainstorm vs critique vs design vs code-audit) is the
> baseline recipe, node schema, scoring dimensions, and verdict
> vocabulary — all parameterized via a **preset** file.

> **What this skill is NOT.** Not a one-shot LLM call that returns a
> bulleted list. Not a chat interface — once `/cc-tree:tree` is
> invoked, the engine runs to convergence without further prompts.
> Not bundled with a model — pure prompt-engineering on top of Claude
> Code's existing model setting.

The full engine specification lives in [`docs/ENGINE.md`](../../docs/ENGINE.md).
This SKILL.md is a 7-step navigation guide; **Read `docs/ENGINE.md`
before producing the first node** (the engine spec is what defines
"valid" for everything you'll write).

---

## 1. Invocation

```
/cc-tree:tree <root> --preset <name|path> [flags]
```

**`<root>`** is preset-typed:
- `brainstorm` preset → topic string, e.g. `"ways to detect dark-matter substructure"`
- `attack` preset → file path (`.md` / `.tex` / etc.) or quoted argument-text
- `design` preset → design-prompt string or `.md` file path
- `code-audit` preset → file path or directory path

**`--preset`** is required:
- Built-in: `brainstorm`, `attack`, `design`, `code-audit` (resolve to
  `presets/<name>.md` in this plugin)
- Path: `./my-custom.md` (any .md file with the right frontmatter)

### Common flags (apply across presets)

| Flag | Default | Meaning |
|---|---|---|
| `--width N` | **∞** | Cap on final leaf count (the outer arc of the tree). `∞` / `inf` / unspecified all mean unlimited. |
| `--depth N` | **∞** | Cap on tree depth from root. |
| `--rounds N` | `conv` | Cap on expansion rounds. `conv` = no cap; terminate by §6 substantive convergence. |
| `--max-branches N` | **∞** | Cap on new branches per node per round. **Floor is 12** because §3 requires all 12 framings to fire; this flag only raises the ceiling. |
| `--out <dir>` | `tree-out/<UTCdate>__<slug>/` | Output directory. Per-preset commands override (e.g. `brainstorm-out/`). |
| `--glossary <path>` | (preset-determined) | Path to a glossary / FACTS.md / glossary section in a dossier; used by §2.0 grill prelude. |
| `--no-grill` | off | Skip §2.0 glossary grill prelude. Marks root-node terms as `unverified`; §6 convergence adds a warning. |
| `--no-online` | off | Disable `WebSearch` / `WebFetch`. Local + already-Read references only. |
| `--min-frameworks N` | 12 | Minimum framing passes per node. **Floor is 12** (full §3.A–§3.L); flag exists for documentation, not relaxation. |
| `--min-novelty-ratio R` | 0.15 | §6.2 convergence requires "last 2 rounds' high-verdict / total < R". |

> Caps default to ∞ on purpose. The intended termination is §6
> substantive convergence — see [`docs/ENGINE.md#6-convergence`](../../docs/ENGINE.md#6-convergence).
> Caps are escape valves for quick exploration; when one trips, the
> engine still drives every in-flight node to a complete state before
> reporting `WIDTH_CAP_REACHED` / `DEPTH_CAP_REACHED` /
> `ROUNDS_EXHAUSTED`.

---

## 2. Execution flow

> **Required Reads at session start** (before producing the first node):
> 1. The preset file (`presets/<name>.md` or `--preset <path>`) — full file.
> 2. [`docs/ENGINE.md`](../../docs/ENGINE.md) — full file. This is the contract.
> 3. [`docs/framings.md`](../../docs/framings.md) — the 12 framings with per-preset
>    examples.
> 4. If `--glossary <path>`: Read that glossary file in full.

### Step 1 — Preset load

Open the preset file. Extract from its YAML frontmatter:
- `name`, `description`, `use-when` (informational)
- `root_kind` — `topic | artifact | code | design-prompt`
- `subject_label` — what each tree node is called (`idea`, `critique`,
  `option`, `audit-finding`, …)
- `verdict_enum` — 4-tuple: `advances / kept / pruned / blocked`
- `convergence_metric` — which verdict's ratio counts toward §6.2
  (`novelty_ratio`, `confirmed_ratio`, `recommended_ratio`, …)
- `score_dims` — list of 5 scoring dimensions (key + name + desc)
- `node_schema` — list of 12 node-field names
- `output_artifacts` — file names for the per-verdict final reports

The preset body (below frontmatter) supplies:
- §2 baseline recipe (what to Read / Grep / WebFetch to build the root)
- Optional per-framing examples (§3.A–§3.L flavored for this preset)
- Optional anti-pattern list specific to this preset

### Step 2 — §2 baseline

Follow the preset's baseline recipe. For all presets this includes:
- §2.0 (unless `--no-grill`): glossary-grill prelude. Lock root-node
  noun-phrases to the glossary if one was supplied; surface MISSING /
  AMBIGUOUS / CONFLICT one question at a time per
  [`docs/ENGINE.md#20-glossary-grill`](../../docs/ENGINE.md#20-glossary-grill).
- §2.A or §2.B (preset-determined): build the root node from real
  evidence (Read files, Grep symbols, WebFetch references). The root
  must have the 5-8 fields the preset specifies, each with `file:line`
  or URL evidence.

Save the root to `<out>/tree.md` + `<out>/tree.json` before producing
any framing branches.

### Step 3 — §3 framing pass (12 passes per node)

For each node (starting with root, then any high-verdict leaf in the
next round):

Run §3.A through §3.L in sequence, each producing **at least 1** new
child branch. See [`docs/framings.md`](../../docs/framings.md) for the
full prompt per framing, including domain-specific examples per preset.

§3.X (if `--no-online` is off): per node, do 1 round of `WebSearch` +
`WebFetch` to find prior art / tools / datasets / criticisms.

### Step 4 — §4 per-branch 12-field derivation

For each branch produced in §3, fill the preset's 12 node-field schema.
Field requirements live in
[`docs/ENGINE.md#4-per-node-derivation`](../../docs/ENGINE.md#4-per-node-derivation).
Hard rules:
- No field may contain `应该 / 大概 / probably / maybe / 也许` — the
  field is invalid and must be rewritten.
- No field may contain `defer / future work / TODO / FIXME / 略 /
  details omitted / 待定 / NEEDS-MORE-INFO`-style placeholders — the
  node is forced to `INCOMPLETE_FORBIDDEN` and **must** be driven to
  completion before counting.
- Numerical claims require a one-shot `python (sympy/numpy)` sanity
  check via `Bash` — output pasted into the field.
- External references require `WebFetch` of the actual arXiv abs / DOI
  / spec page; `WebSearch` snippets are not sufficient.

Append the filled node to `tree.md` + `tree.json` immediately
(incremental write — see §7 for crash-safety contract).

### Step 5 — §5 scoring and verdict

Score the node along the preset's 5 dimensions (each 0–3, integer).
Sum = `score` (max 15). Map score → verdict via the preset's
`verdict_enum` and the preset-specific rule (e.g. brainstorm:
`score ≥ 11 ∧ no [NEEDS_VERIFICATION] → PROMISING`; attack:
`score ≥ 11 ∧ paper_defense empty → CONFIRMED`).

Sibling merging (§5.4): any two siblings with cosine similarity ≥ 0.85
on their idea / critique / option / finding statement → merge, keep
the higher-scored one, tag the other `MERGED_INTO=<id>`.

### Step 6 — §6 convergence check

After every round, evaluate the 6 conditions in
[`docs/ENGINE.md#6-convergence`](../../docs/ENGINE.md#6-convergence).
All 6 must hold simultaneously to declare `CONVERGED`. If any
user-specified `--width / --depth / --rounds` cap trips first, report
the appropriate `*_CAP_REACHED` / `ROUNDS_EXHAUSTED` status, but **all
leaves must be complete** before stopping.

If neither convergence nor a cap-trip, pick the highest-verdict leaf
that hasn't been re-expanded yet, run §3–§5 on it, and loop.

### Step 7 — §7 final report

When termination is declared, write the preset's `output_artifacts` to
`<out>/`. For all presets this includes:
- `tree.md` — full tree, human-readable
- `tree.json` — full tree, machine-readable
- The preset-specific primary deliverable (`shortlist.md`,
  `confirmed.md`, `options.md`, `findings.md`)
- The preset-specific secondary deliverables (`pending.md`,
  `marginal.md`, `refuted.md`, …)

Then emit a terminal-report block per
[`docs/ENGINE.md#74-final-report`](../../docs/ENGINE.md#74-final-report).

---

## 3. Anti-patterns (see [`docs/ENGINE.md#9-anti-patterns`](../../docs/ENGINE.md#9-anti-patterns) for the full list)

The five that most reliably degrade output quality:

1. ❌ **Pseudo-divergence.** Two branches that differ only in word
   choice. Each branch must offer at least one of (a) a different
   testable prediction, (b) a different failure mode, (c) a different
   resource profile. Otherwise: merge.

2. ❌ **Defer-as-output.** "This direction is promising but requires
   detailed analysis beyond scope." Forbidden by §0.8. The engine must
   actually do the analysis (Read / WebFetch / Bash) or route to a
   sibling via §3.E constraint-variation.

3. ❌ **Cap-as-convergence.** Declaring `--width 20` reached → done.
   §6 convergence is the *intended* termination; caps are escape
   valves and trip ≠ converge.

4. ❌ **Skipping §3.K.** "High-risk branches feel speculative, I'll
   focus on safe ones." §0.4 + §3.K force ≥ 1 fully-explored
   high-risk branch per pass; absent it the pass is invalid.

5. ❌ **WebSearch snippet → conclusion.** Snippets are search results,
   not source-of-truth. Every external citation requires `WebFetch`
   of the actual page; otherwise the field is invalid (rule 04 +
   rule 01 from cc-enslaver, if installed).

---

## 4. Output contract

```
<out>/
├── tree.md             # human-readable outline of every node
├── tree.json           # machine-readable, full 12 fields per node
├── <primary>.md        # preset's "advances" / top-recommendation file
├── <secondary>.md*     # preset's "marginal / pending / refuted" files
└── nodes/
    └── <id>.md         # spilled when a node's evidence > 100 lines
```

Each node lands the moment its 12 fields are filled (§7.1 incremental
write contract). Restart from interruption: just re-invoke the same
`/cc-tree:tree <root> --preset <name> --out <same-dir>` — the engine
detects the existing tree and resumes from the highest-id leaf.

---

## 5. References

- [`docs/ENGINE.md`](../../docs/ENGINE.md) — full engine spec (§0–§9)
- [`docs/framings.md`](../../docs/framings.md) — the 12 framings, per-preset examples
- [`docs/presets.md`](../../docs/presets.md) — how to author your own preset
- [`presets/`](../../presets/) — shipped presets
- [`commands/`](../../commands/) — ergonomic slash-command wrappers
- [`EVALUATION.md`](../../EVALUATION.md) — design rationale
