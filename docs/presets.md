# Authoring a cc-tree preset

> Language: English (canonical). Chinese: [`docs/presets.zh.md`](presets.zh.md).

A preset is a single `.md` file that customizes the universal
engine ([`ENGINE.md`](ENGINE.md)) for one use-case. It supplies six
overridable slots (vocabulary + recipe) without weakening any of
the engine's universal rules.

This doc covers: (1) the required frontmatter schema, (2) what to
put in the preset body, (3) compliance rules the engine enforces.

The shipped 4 presets (`brainstorm`, `attack`, `design`,
`code-audit`) in [`../presets/`](../presets/) are reference
implementations — copy one as a starting point.

---

## 1. Frontmatter schema

The preset's YAML frontmatter declares the six override slots:

```yaml
---
name: my-preset                    # must match file basename
description: One-paragraph description with "Use when …" triggers.
use-when: |
  - User says "X"
  - User wants to explore Y
  - Domain Z task that needs divergent exploration with adversarial bite

# === Slot 1: root type ===
# topic | artifact | code | design-prompt
root_kind: topic

# === Slot 2: what the engine calls each node ===
# A single word; appears in tree.md and the final report.
subject_label: idea

# === Slot 3: verdict vocabulary (4-tuple, all four roles required) ===
verdict_enum:
  advances: PROMISING       # nodes with this verdict trigger another §3 round
  kept:     MARGINAL        # nodes kept in tree but not re-expanded
  pruned:   DEAD-END        # nodes pruned (kept for reference)
  blocked:  NEEDS-MORE-INFO # incomplete; must be driven to one of the above

# === Slot 4: which verdict counts toward §6.2 convergence ratio ===
# Typically "advances" — engine checks: (last 2 rounds' advances / total) < --min-novelty-ratio
convergence_metric: advances   # must be one of the 4 verdict_enum roles above (verbatim)

# === Slot 5: scoring dimensions (exactly 5; each 0–3) ===
# Inline flow-map entries (shown) and standard block-map list items
# (`- key: S` + indented `name:` / `desc:` lines) both parse.
score_dims:
  - {key: S, name: scientific-value,  desc: "Magnitude of contribution if successful"}
  - {key: N, name: novelty,           desc: "Difference from existing work"}
  - {key: F, name: feasibility,       desc: "Probability of completion within user resources"}
  - {key: K, name: falsifiability,    desc: "Clarity of experimental / computational test"}
  - {key: B, name: branch-potential,  desc: "Number of sub-directions opened on success"}

# === Slot 6: node 12-field schema (exactly 12 entries) ===
node_schema:
  - idea_statement          # field 1: subject (≤ 3 sentences)
  - parent_framing          # field 2: §3.A / §3.B / ... / §3.L
  - derivation              # field 3: full math / mechanism / evidence chain
  - assumptions             # field 4: ≥ 3 explicit assumptions
  - predictions             # field 5: ≥ 1 quantitative falsifiable prediction
  - falsifiability          # field 6: what would refute this
  - novelty_vs_literature   # field 7: comparison to ≥ 3 real refs with DOI/arXiv
  - feasibility             # field 8: data / compute / time / skill
  - risks                   # field 9: ≥ 3 risks, tagged technical/scientific/resource
  - branch_potential        # field 10: ≥ 2 sub-directions if this succeeds
  - external_resources      # field 11: repos / plugins / datasets found via §3.X
  - verdict_provisional     # field 12: verdict label from verdict_enum

# === Output artifact file names ===
output_artifacts:
  primary: shortlist.md     # main deliverable; sorted by score; advances-verdict nodes
  secondary:
    pending: pending.md     # blocked nodes (should be empty at converged time)
    marginal: marginal.md   # kept-verdict nodes

# === Optional: per-framing examples and custom baseline glossary paths ===
glossary_paths:
  - FACTS.md
  - glossary.md
  - CLAUDE.md
---
```

### Required vs optional keys

**Required** (engine errors at preset-load if missing):

- `name`, `description`
- `root_kind`, `subject_label`
- `verdict_enum` (with all 4 roles: `advances` / `kept` / `pruned` / `blocked`)
- `convergence_metric`
- `score_dims` (exactly 5)
- `node_schema` (exactly 12)
- `output_artifacts.primary`

**Optional**:

- `use-when` (recommended for slash-command discoverability)
- `output_artifacts.secondary.*`
- `glossary_paths` (defaults to `FACTS.md` / `glossary.md` /
  `CLAUDE.md` if unset)
- Any preset-specific extension fields (engine ignores unknown
  top-level keys)

### Engine-enforced compliance

`tools/validate_plugin.py` rejects presets that:

- Have `node_schema.length != 12`
- Have `score_dims.length != 5`
- Have `verdict_enum` missing any of the 4 required roles
- Reference a `convergence_metric` that isn't one of the
  `verdict_enum` keys
- Have an unknown `root_kind`
- Have empty `name` or `description`
- File basename doesn't match `name:`

CI runs the validator on every push; broken presets block the
merge.

### 1.1 Language boundary

A custom preset may describe its baseline recipe, framing flavors,
anti-patterns, citations, and examples in any language. Its schema remains the
English machine skeleton consumed by the engine and validator. Keep these in
English and do not translate them:

- frontmatter keys and the `root_kind` values;
- `verdict_enum` role keys **and their labels**;
- `convergence_metric`, `score_dims[].key`, and `score_dims[].name`;
- every `node_schema` field name;
- `output_artifacts` keys and filenames;
- framing IDs, status/tag tokens, paths, code, equations, and API identifiers.

Free-form values such as `description`, `use-when`, `score_dims[].desc`, the
preset body, and cited or quoted source material may use any language. They do
not override the run's `output_language`: generated node prose and report
narrative still follow `--lang`, while quotations remain verbatim and receive a
localized explanation when their language differs from the output language.
The engine rejects a preset that translates or aliases a load-bearing schema
identifier instead of using the canonical English token.

---

## 2. What goes in the preset body

The frontmatter declares vocabulary; the body declares the
*recipe* — particularly the §2 baseline. The body is parsed by
the engine in the order below.

### §2 baseline recipe (required)

Tell the engine what to Read / Grep / WebFetch to build the root
node. Be specific about file types, command-line invocations, and
where to find domain conventions.

Example for `code-audit`:

```markdown
## §2 Baseline (code-audit recipe)

For each `<root>` (file or directory path):

1. **Full Read.** If a file: `Read` the whole file. If a directory:
   `Glob <dir>/**/*.py` (or relevant extension), then `Read` every
   file ≤ 500 lines; spill larger ones via `Read --offset/--limit`.
2. **Test suite / fixtures.** `Glob tests/**/*.py` near the target;
   `Read` the most relevant ≤ 5 test files.
3. **Recent change context.** `Bash git log --oneline --follow
   <target>` for the last 20 commits.
4. **Project conventions.** `Read CLAUDE.md` (if present) and
   `Read .github/CODEOWNERS` (if present) to learn who-owns-what.
5. **Dependency surface.** `Grep "import " <target>` to enumerate
   external-dependency call sites that may need verification.

**Root node fields (5):**

- `target_summary`: 1 sentence describing what the target does.
- `entry_points`: list of public functions/methods/HTTP routes /
  CLI commands.
- `inputs_from_caller`: parameter types, validation present/absent.
- `external_dependencies`: libraries, services, files, env vars.
- `threat_surface`: list (auth bypass / injection / data leak /
  DoS / etc.) with rationale.
```

### §3.A–§3.L flavor (optional but recommended)

Each framing in [`framings.md`](framings.md) has a "Per-preset
flavor" section. If your preset is novel enough that the shipped
flavors aren't directly applicable, supply your own — the engine
will use them as the framing prompt for nodes under this preset.

Example:

```markdown
## §3.D — Adversarial / red team (security-audit flavor)

Adopt a real adversary's perspective at each of:
- unauthenticated outsider (network attacker)
- authenticated low-privilege user (insider)
- authenticated high-privilege user gone rogue
- supply-chain attacker (malicious dependency)
- compromised CI / build pipeline

For each, ask: "what's the highest-impact thing I could do with
the access this category has, leveraging anything in the audited
code?"
```

### Preset-specific anti-patterns (optional)

Add anti-patterns specific to your preset:

```markdown
## Preset anti-patterns (code-audit-specific, in addition to ENGINE.md §9)

- ❌ "Defense in depth" used as `mitigation_present` — must be a *specific*
  mitigation at a *specific* file:line.
- ❌ "Insufficient input validation" as a critique — must specify
  *which* input, *what* validation is missing, and *which* attack the
  missing validation enables.
- ❌ Reporting a finding without `proposed_fix` and without a runnable
  PoC (or a clear path to one) — downgrade to MARGINAL.
```

---

## 3. Slot semantics in detail

### `root_kind`

| Value | Behavior |
|---|---|
| `topic` | `<root>` is a string; used verbatim as root's subject. May be empty (preset can attempt inference). |
| `artifact` | `<root>` is a file path; engine `Read`s the full file before §2.1. Errors if file missing / unreadable. |
| `code` | Same as `artifact` but with the added convention that file extensions hint at language for §3.G substitution and §3.E constraint variation. Directory input → recursive Glob+Read. |
| `design-prompt` | `<root>` may be a string OR a file path. If file, Read it as structured design-prompt (goals / constraints / context sections expected). |

### `subject_label`

Single noun, appears throughout `tree.md`, REPORT.md, and the
final-report verdict counts. Pick something that reads naturally in
"the 14 [subject_label]s produced by this run". Examples: `idea` /
`critique` / `option` / `finding` / `direction` / `risk`.

### `verdict_enum` roles

| Role | Semantic | Common labels |
|---|---|---|
| `advances` | Recurse into another §3 pass on this node. Counts toward §6.2 convergence ratio (unless `convergence_metric` overrides). | PROMISING / CONFIRMED / RECOMMENDED |
| `kept` | Stay in tree, don't re-expand. Often "interesting but not actionable now". | MARGINAL / VIABLE / SECONDARY |
| `pruned` | Don't re-expand; derivation kept for reference and to prevent regeneration. For `attack`-style presets this is REFUTED (valuable positive record). | DEAD-END / REFUTED / NOT-RECOMMENDED |
| `blocked` | Forbidden state; must be driven to one of the other three before §6 convergence. | NEEDS-MORE-INFO / INCOMPLETE_FORBIDDEN |

### `convergence_metric`

Which verdict's "ratio drops below `--min-novelty-ratio`" triggers
§6.2. **It must be one of the four `verdict_enum` role keys**
(`advances` / `kept` / `pruned` / `blocked`), written *verbatim* —
the validator (`tools/validate_plugin.py`) rejects anything else
(no aliases like `novelty_ratio` / `confirmed_ratio`). For almost
every preset this is `advances`: "I'm still finding new
expand-worthy nodes". The domain reading (novelty for brainstorm,
confirmed for attack, recommended for design) comes from the
*label* you mapped onto the `advances` role in `verdict_enum`, not
from renaming the metric. Only pick a non-`advances` role if your
preset genuinely converges on a different signal (rare).

### `score_dims`

Each dim is `{key, name, desc}`. `key` is 1–3 letters used in
score reports (e.g. `S=3 N=2 F=3 K=2 B=1 → total=11`). `name` is
human-readable. `desc` is the rubric — what does a 0 mean, what
does a 3 mean. Keep dims orthogonal; if two dims correlate at
> 0.7 in practice, they're not pulling independent weight.

### `node_schema`

Exactly 12 entries. Match each entry roughly to one of the
universal slot categories in [`ENGINE.md`](ENGINE.md) §4 — slot 1
is subject statement, slot 2 is parent framing, etc. You can
deviate in names but the engine expects 12 fields covering the
universal categories. For radically different schemas (e.g. you
need 14 fields), file an issue.

### `output_artifacts`

Filenames written to `<out>/`. `primary` is the main deliverable.
`secondary` is a map (typically with keys named after verdicts
the user might want to navigate separately, e.g. `pending`,
`marginal`, `refuted`).

---

## 4. Distributing your preset

Two options:

1. **Local file.** Save anywhere; invoke with
   `--preset /path/to/my-preset.md`. No plugin changes needed.
2. **Ship in this plugin.** Add `presets/my-preset.md`, optionally
   add `commands/my-preset.md` (15-line slash-command wrapper),
   open a PR. CI will validate frontmatter / schema compliance.

For commands wrappers, see the shipped `commands/*.md` for the
4-line pattern.

---

## 5. Compliance audit checklist

Before submitting a preset:

- [ ] Frontmatter has all required keys (see §1).
- [ ] `node_schema` length = 12.
- [ ] `score_dims` length = 5; each has `key`, `name`, `desc`.
- [ ] `verdict_enum` has all 4 roles (`advances` / `kept` /
      `pruned` / `blocked`).
- [ ] `convergence_metric` matches one of the `verdict_enum` keys
      (verbatim, no aliases).
- [ ] Machine identifiers listed in §1.1 remain canonical English tokens;
      free-form prose may use any language.
- [ ] Preset body's §2 baseline has no "TBD" / "TODO" placeholders.
- [ ] Preset body's framing flavors (if supplied) don't contradict
      [`framings.md`](framings.md) universal semantics.
- [ ] `python tools/validate_plugin.py` passes locally.
- [ ] (Optional but encouraged) An example run exists under
      `examples/` with `tree.md` / `tree.json` / primary output —
      demonstrates the preset on a toy root.
