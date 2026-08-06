# Changelog

All notable changes to the `cc-tree` plugin. Versions follow the
`plugin.json` / `marketplace.json` `version` field.

## Unreleased

Internal cleanup of `tools/`. No behaviour change: an old-vs-new harness
proves nine surfaces byte-identical (manifest pairs, canonical-only set,
all 154 raw tokens, both enforcement sets, `I18nStats`, the scanned
Markdown file list, flow-map parses, frontmatter parses), and six
negative cases produce identical error messages. Production logic is 26
executable lines smaller; file totals are flat because the extracted
helpers carry docstrings.

### Removed (dead code)

- `_parse_flow_map`'s `startswith("{")` guard was unreachable: with no
  `{`, `_find_flow_map_end` already returns -1 and the `close == -1` path
  returns the same `{"_raw": …}` value.
- `_split_top_level(s, sep)` was only ever called with `","`. Now
  `_split_commas(s)`.
- `test_i18n.py` imported `validate_manifest` and never used it.

### Removed (duplication)

- The skip predicate `part in SKIP_DIR_PARTS or part.endswith("-out")`
  existed in three places. Now one shared `_i18n.is_skipped`, for the
  same reason `SKIP_DIR_PARTS` is shared: three copies could drift apart.
- `_FLAG_RE` was byte-identical in `_i18n.py` and `validate_plugin.py`.
  Now one exported `FLAG_RE`.
- `build_machine_tokens` / `build_inline_tokens` each ran a full
  `_harvest_tokens` pass for the same result — re-reading SKILL.md, every
  command, every preset, and ENGINE.md a second time. Merged into
  `build_token_sets`, which returns both. Validation file reads: 128 → 117.
- `validate_manifest` walked the tree twice (`*.zh.md`, then `*.md`). One
  pass now; cyclomatic complexity 29 → 24, its worst-in-repo ranking gone.
- The fence-rescue rationale was argued at length both in `_validate_pair`
  and in `_inline_code_atoms`'s docstring. `_inline_code_atoms` owns it.

### Changed (structure)

- `_harvest_tokens` nested five deep over five extraction shapes; the
  preset-frontmatter walk is now `_preset_tokens` with one recursive
  string collector. Off the complexity top-10 entirely.
- `_validate_pair` was 94 lines covering six concerns. The structural and
  prose-coverage checks are now `_check_shape` and
  `_check_section_coverage`. Off the length top-8.
- `_content_md_files`: 9 lines → 3.
- Dropped bug-archaeology from comments that the changelog already
  records; kept every "why this shape" note.

### Added (test coverage)

- Two branches of the section-coverage check had **no** test in the
  28-case suite: a substantive section with no Chinese prose, and one
  answered with a token stub below the 20% letter floor. Only the
  byte-for-byte "English copy" case was covered. Now 30 cases, and
  neutering the check makes all three fail.

Second debug sweep, done line-by-line over every shipped file: **24
defects across 18 files**, all in classes the existing gates could not
see. Two were runtime crashes/misparses in the frontmatter parser; the
rest were contract drift — places where the runtime prompt, the engine
spec, and a preset's own declared schema disagreed about a field name, a
verdict label, or a section number. Three drift classes became CI
failures.

### Fixed (parser)

- **A bare `-` list entry crashed the validator** with
  `IndexError: string index out of range` instead of failing cleanly.
  `_strip_comment` tested `s[:1] in "\"'"`, and `"" in "\"'"` is True
  (empty-substring semantics), so an empty value fell through to `s[0]`.
  Now a malformed entry reports `node_schema[i] is empty`.
- **Frontmatter whose closing `---` was the last byte of the file** (no
  trailing newline) parsed as "no frontmatter at all". `FRONTMATTER_RE`
  now accepts `\Z` as well as a terminating newline.

### Fixed (contract drift)

- **`skills/tree/SKILL.md` documented `convergence_metric` with the exact
  alias values the validator rejects** (`novelty_ratio`,
  `confirmed_ratio`, …). v0.2.0 fixed this in `docs/presets.md` but not
  in the runtime prompt, so authoring a preset by following SKILL.md
  produced a CI failure.
- **§3.X named a field `design` does not have.** `docs/ENGINE.md` and
  `docs/framings.md` (+ zh) told the engine to record design's external
  findings in `external_resources`; design's `node_schema` declares
  `external_dependencies`. Each preset's own field name is now listed.
- **`docs/ENGINE.md` §4 slot 10 claimed "always `risks`"** — true for
  brainstorm only. `design` uses `operational_risks`; `attack` and
  `code-audit` have no risk field. The Slot column is now documented as
  a category index, not a `node_schema` position.
- **`attack` and `code-audit` mapped `score ≤ 7` to `DEAD-END`**, a label
  in neither preset's `verdict_enum` (their `pruned` role is REFUTED).
- **`design` referenced a `proposed_fix` slot** it does not declare.
- **`[NEEDS VERIFICATION]` vs `NEEDS_VERIFICATION`.** Every doc spelled
  the tag with a space while `docs/languages.json` registered the
  underscore form, so the registered machine token matched nothing and
  its i18n parity check never ran. Normalized to `[NEEDS_VERIFICATION]`.
- **Six dead `§` pointers** left by the §0.x → F1–F8 renumbering
  (`§0.4` / `§0.7` / `§0.8`) plus two invented ones (`§2.4`, `§6.6`),
  across ENGINE.md, ENGINE.zh.md, SKILL.md, EVALUATION.md, and the
  attack / design presets.
- **§2.0's glossary prompts contradicted §F6's full-auto contract**,
  whose "Stop only when" list was exhaustive and did not include them.
  F6 now carries an explicit pre-root carve-out.
- **A malformed row in the §6.2 termination table** (2 cells in a
  3-column table), and `EARLY_STOP=root_underspecified` missing from
  that table despite being specified in §2.1 and used by 3 presets.
- **`validate_plugin.py`'s own module docstring** enumerated checks 1–7
  and skipped the cross-file consistency check entirely.

### Fixed (found in the line-by-line pass)

- **`docs/framings.md` said the 12 framings "can be run in parallel"**
  at fan-out ≥ 5, while `docs/ENGINE.md` §8.1 makes dispatch
  **mandatory** there and §9 lists sequential execution as an
  anti-pattern. A MUST had been restated as a MAY.
- **Four `#anchor` fragments lived in the link *text* instead of the
  href** (`docs/ENGINE.md#22-field-profile`,
  `#81-sub-agent-dispatch`), so they rendered as navigable anchors,
  did not resolve, and were invisible to `_check_anchors` — which only
  inspects `](path#frag)`. Moved into the href with their real slugs;
  the anchor check now covers 12 links instead of 8.
- **`framings.md` used brainstorm's `DEAD-END` label generically** in a
  preset-agnostic document (two places), where the same file elsewhere
  correctly spells all three `pruned` labels. Now names the role.
- **`README.md` misquoted the skill's own description**: "Width × depth
  default to ∞" drops `× rounds`.
- **`README.md` cited "§0 forbidden patterns"** where the same file
  elsewhere cites §0.5 — the patterns are §0.5 / F1–F8.
- **`docs/presets.md`'s "validator rejects presets that…" list was
  incomplete** — it read as exhaustive but omitted empty
  `subject_label`, missing `output_artifacts.primary`, `score_dims`
  entries missing `key`/`name`/`desc`, empty `node_schema` entries, and
  blank verdict labels. Now enumerates all eight enforced rules.
- **`EVALUATION.md`'s decision log skipped v0.3.0** entirely.
- `docs/ENGINE.md` wrote `§ 5's` with a stray space.

### Added

- **`_check_section_refs`** — every `§N` / `§N.M` / `§FN` prose reference
  must resolve to a real heading. `_check_anchors` could not catch these:
  they are prose tokens, not Markdown links. 304 refs now checked.
  `CHANGELOG.md` is exempt: naming a pointer it removed is its job.
- **`_check_anchors` now blanks single-backtick spans before scanning.**
  Prose that documents link syntax quotes the pattern literally, and
  resolving the quoted placeholder as a real file was a false positive.
  Fenced blocks stay in scope — they hold real worked examples.
- `root_underspecified` and `tool_blocked` registered as fixed machine
  tokens. Newly enforced across translations: `NEEDS_VERIFICATION`,
  `operational_risks`, `threat_model_context` (289 → 298 token checks).
- Parser regression cases for the two crash/misparse bugs, plus tests
  pinning the heading shapes `_check_section_refs` harvests.

### Verification

`validate_plugin.py` + `test_validate.py` + `test_i18n.py` all pass on
py3.11 / py3.13. Eight fail-closed probes on a throwaway clone confirm
each gate rejects rather than crashes: dead `§` reference, stale i18n
digest, machine token dropped in a translation, bare `-` list entry,
`convergence_metric` alias, newly-registered token dropped, dead
`](path#frag)` anchor, and a required flag missing from a wrapper.

## v0.4.0 — 2026-07-11

English-canonical multilingual runtime and documentation version control.
Existing omitted-flag behavior remains English, while runs can now select a
stable human-readable output language without forking machine schemas.

### Added

- **`--lang <tag|auto>` common flag** across the universal skill and every
  command wrapper. Explicit BCP-47-like tags win; `auto` detects the dominant
  natural language of primary root/invocation content and falls back to `en`
  for mixed, unrecognized, path-only, or code-only input. `zh` is maintained
  Simplified Chinese; Traditional Chinese is explicit via `zh-Hant`.
- **Run-level language persistence** through `language_request`,
  `output_language`, and `language_source`. Resume reuses the recorded tag;
  conflicting explicit tags fail with `EARLY_STOP=language_mismatch`; legacy
  output is treated as English. `tree-chain` resolves once and propagates the
  concrete tag to every stage, item sub-run, and framing sub-agent.
- **Arbitrary-language content contract**: roots, artifacts, code comments,
  glossaries, field-profile bodies, custom-preset prose, citations, and quoted
  evidence may use any language. Quotations remain verbatim with localized
  explanation when needed.
- **Five new Chinese public guides** (`README.zh.md`, `docs/presets.zh.md`,
  `docs/chaining.zh.md`, `field-profiles/README.zh.md`, and
  `examples/attack/README.zh.md`) plus normalized ENGINE and framings pairs.
- **`docs/languages.json` language-version manifest** defining canonical/default
  language, maintained pairs, canonical-only exceptions, required runtime
  flags, and fixed machine tokens. Chinese files carry an LF-normalized source
  SHA-256 so stale translations fail CI.
- **`tools/test_i18n.py`** with positive and negative fixtures for manifests,
  banners, digests, ordered headings, fence handling, Chinese coverage,
  machine tokens, and body-only command-flag validation; runs on Python 3.11
  and 3.13 in CI.

### Changed

- **English machine-schema boundary is explicit and enforced**: command/flag
  names, frontmatter and JSON keys, `root_kind` values, verdict roles/labels,
  score keys/names, `node_schema` fields, framing IDs, statuses/tags, output
  filenames, paths, code, equations, and API identifiers never translate.
  Human-readable statements, derivations, evidence explanations, risks, fixes,
  warnings, headings, and summaries follow the resolved output language.
- **Hedge/defer bans are semantic across languages.** Existing English and
  Chinese phrase lists are examples, not an exhaustive bypassable whitelist.
- **I18n validation is manifest-driven and fence-aware**: reciprocal banners,
  source freshness, ordered heading levels/markers, aligned fenced examples,
  minimum Chinese body coverage, and derived load-bearing token preservation.
- **Command flag validation now excludes frontmatter**, fixing the prior
  self-documenting `argument-hint` flaw; required common flags must appear in
  the skill body and every command hint.

## v0.3.0 — 2026-07-09

Debug sweep (26 confirmed defects fixed across 20 files) + the
hardening features that turn the found drift classes into CI failures.

### Fixed

- **Frontmatter parser YAML-semantics defects** (`tools/_frontmatter.py`):
  a prose apostrophe before `#` swallowed the trailing comment; quoted
  scalars kept their quotes (`name: "x"` spuriously failed the
  name==basename check); a flow-map list item with a trailing comment
  degenerated to `{"_raw": ...}`. All three now parse per YAML
  plain/quoted-scalar rules, with regression tests.
- **`paper_defense` / `paper_position` naming drift** — the attack
  preset's schema says `artifact_defense` / `artifact_position` since
  v0.1, but ENGINE.md (×4), ENGINE.zh.md (×4), SKILL.md, framings
  (both languages), docs/presets.md, and attack.md's own anti-pattern
  list still used the old sci-paper names. Unified to `artifact_*`
  (the code-audit example in docs/presets.md now correctly says
  `mitigation_present`).
- **Chaining contract contradictions** — tree-chain.md seeded *every*
  later stage via `--seed-from` (making a design option enter attack
  as a "CONFIRMED critique" — a category error), while chaining.md's
  worked example passed the option as attack's root; and both files
  claimed all primary deliverables are "sorted by score" (attack sorts
  by severity, code-audit by severity × exploit-likelihood). Now:
  topic/design-prompt stages take seeds, artifact/code stages take the
  carried item as root; sort keys stated per preset.
- **Example line-citation drift** — `examples/attack/expected-out/*`
  carried a systematic +2 line offset against sample-claim.md
  (including a citation past EOF). Regenerated (see Added) and now
  CI-bounds-checked.
- Dead ENGINE.md anchors in SKILL.md (4), `--focus` unregistered under
  the "error on unknown flags" rule, `--field` missing from 4 command
  argument-hints, `--field` docs omitting the §3.X/§4 evidence-bar
  channel, REPORT.md missing from the §7.2 output layout (both
  languages), ENGINE.zh.md banner placed above the H1, three zh gloss
  divergences (逆共识 / 盲点自审 / 办公室时间 6 问), stale
  "9 negative cases" test-count claim (was 8; counts are now computed
  at runtime).

### Added

- **Cross-file consistency checks in CI**
  (`tools/validate_plugin.py check_crossrefs`): markdown anchor
  integrity (GitHub-slug aware), example `file:line` citation bounds,
  bilingual heading-structure parity (docs/*.zh.md vs English),
  command argument-hint flag registry (every advertised flag must be
  documented by SKILL.md, the command body, or its preset), and field
  profile schema (frontmatter + the 4 required sections).
- **`field-profiles/physics.md`** — first shipped concrete profile:
  ApJ/MNRAS/PRD reviewer weighting (unit/`h`-convention consistency,
  error budgets with dominant systematics, Hartlap-corrected
  covariances, look-elsewhere effects; weak-lensing/cosmology flavored
  consensuses and failure modes).
- **Block-map list items in the frontmatter parser** — standard YAML
  list-of-maps style (`- key: S` + indented `name:` / `desc:` lines)
  now parses identically to the inline flow-map style, closing the
  biggest custom-preset authoring footgun (continuation lines were
  silently dropped before).
- **Regenerated `examples/attack/expected-out/`** as the abridged
  output of a real capped run (`--width 3 --depth 1 --no-online
  --no-grill`) instead of a hand-authored approximation.
- **CI matrix**: Python 3.11 + 3.13.

## v0.2.0 — 2026-05-29

Closes the v0.1 documentation/implementation drift and lands the
roadmap enhancements from `EVALUATION.md` (formerly tracked as v0.2–v0.4
open questions). cc-tree is now self-contained and CLI-installable.

### Fixed (doc/impl drift)

- **The preset schema validator now actually validates the schema.**
  `docs/ENGINE.md` §10-§11 and `docs/presets.md` §1 promised CI rejects
  `node_schema≠12 / score_dims≠5 / verdict_enum missing a role /
  convergence_metric not a verdict role / unknown root_kind`, but the
  old `parse_frontmatter` dropped all nested YAML and only checked
  `name`+`description`. New zero-dependency `tools/_frontmatter.py`
  parses the frontmatter subset; `tools/validate_plugin.py` enforces all
  eight rules; `tools/test_validate.py` proves it (4 shipped presets
  pass + 8 negative cases rejected). Both run in CI.
- **§3.X external-check is now preset-aware.** It searched
  brainstorm-flavored targets (claude-code-plugin / mcp / langchain) for
  every preset; now attack hunts errata/critiques, code-audit hunts
  CVEs/advisories, brainstorm/design hunt prior art + tooling
  (`docs/framings.md` §3.X + `docs/ENGINE.md` §3.X).
- **Resolved the `convergence_metric` contradiction** in
  `docs/presets.md` (alias prose vs the "verbatim, no aliases" rule) —
  unified to "must be a verdict_enum role, verbatim".
- README install instructions corrected to the real plugin CLI;
  README verdict vocabulary for attack/code-audit fixed
  (`INCOMPLETE_FORBIDDEN`, not `DEAD-END`).

### Added (roadmap)

- **`--field <name|path>`** — domain-aware reviewer weighting via
  `field-profiles/<name>.md`; feeds §3.C / §3.D / §3.I / §3.J + the
  §3.X / §4 evidence bar.
  Non-blocking if absent. Ships `field-profiles/_template.md` +
  `field-profiles/README.md` (domain-neutral). (`docs/ENGINE.md` §2.2)
- **Cross-preset chaining** — new `/cc-tree:tree-chain` command +
  `docs/chaining.md`; universal `--seed-from <primary.md>` flag (alias
  `--from-prior`) seeds a run from a prior deliverable. (`docs/ENGINE.md`
  §2.3)
- **Mandatory sub-agent dispatch** at fan-out ≥ 5 (was optional), with a
  precise dispatch + re-verification contract. (`docs/ENGINE.md` §8.1)
- **Bilingual engine docs** — `docs/ENGINE.zh.md` + `docs/framings.zh.md`
  (English remains canonical).
- **Concept diagram** in `README.md` (ASCII radial tree + Mermaid engine
  loop) explaining the phylogenetic-tree model.
- **`examples/attack/`** — illustrative toy run showing the deliverable
  format.

## v0.1.0 — 2026-05-25

Initial release. Extracts the universal radial-tree exploration engine
from `sci-paper`'s `brainstorm` and `paper-attack-tree` skills and
generalizes it as a domain-agnostic plugin with swappable presets.

### What ships

- **One skill** `/cc-tree:tree` — the universal engine; loads a preset
  on invocation and applies the 12-framing exploration loop with hard
  bans on incomplete leaves and stable-convergence termination.
- **Full engine spec** at `docs/ENGINE.md` (~600 lines) covering the
  9 sections: data model / forbidden patterns / invocation flags /
  baseline hook / 12 framings / node 12-field schema / scoring + verdict /
  6 convergence conditions / output format / tool-usage projection /
  anti-patterns.
- **4 presets** under `presets/`:
  - `brainstorm.md` — divergent ideation / problem-solving exploration
  - `attack.md` — adversarial critique of any artifact (document /
    argument / design)
  - `design.md` — design-space exploration (option × trade-off ×
    reversibility)
  - `code-audit.md` — code-flavored adversarial review (security /
    perf / contract violations)
- **4 ergonomic slash-commands** under `commands/` that wrap the skill
  with a preset preselected: `/cc-tree:brainstorm`, `:attack`, `:design`,
  `:code-audit`.
- **Supporting docs**:
  - `docs/framings.md` — the 12 framings (§3.A–§3.L) with cross-domain
    examples for each preset
  - `docs/presets.md` — how to write your own preset
- **`tools/validate_plugin.py`** + `.github/workflows/ci.yml` — sanity
  checks on manifests / skill frontmatter / preset frontmatter /
  command frontmatter / tools syntax; runs on every push to `main` and
  every PR.
- **`README.md` / `EVALUATION.md`** — usage + design rationale.

### Provenance

The engine is a refactor of two skills shipped in
[`skymanbp/sci-paper`](https://github.com/skymanbp/sci-paper):
[`brainstorm`](https://github.com/skymanbp/sci-paper/blob/main/skills/brainstorm/SKILL.md)
and [`paper-attack-tree`](https://github.com/skymanbp/sci-paper/blob/main/skills/paper-attack-tree/SKILL.md).
sci-paper continues to ship its domain-specific versions independently;
cc-tree is the domain-agnostic generalization.
