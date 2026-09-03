# Changelog

All notable changes to the `cc-tree` plugin. Versions follow the
`plugin.json` / `marketplace.json` `version` field.

## v0.7.2 — unreleased

Documentation only. No preset, command, skill, runtime prompt, or
validator behaviour changed.

### Changed

- **Both READMEs were restructured into a nine-section standard layout**,
  and the repository map now names all three test suites.
- **The engine's companion project is named `cc-enforcer`** in
  `docs/ENGINE.md`, its Chinese parallel, `skills/tree/SKILL.md`, and
  `.gitignore`; `docs/ENGINE.zh.md`'s source digest was re-stamped for the
  English edit.
- **`.gitignore` covers `.ce/` and `.ccm/`** — a cc-enforcer index and
  cc-memory state; machine-local, never content.
- **README §4.3 is scoped to sweeps rather than releases** — four
  whole-corpus adversarial sweeps since v0.3.0 plus v0.7.1's documentation
  audit — and the v0.5.0 row names all three drift classes that sweep
  turned into CI failures. The validator transcript was refreshed to the
  run the corpus produces today.

### Fixed

- **`docs/EVALUATION.md` undercounted v0.5.0's drift gates as two.** Three
  became CI failures: dead `§N` prose references, anchors outside the link
  href, and a machine token registered in a form that matched nothing.
- **`docs/EVALUATION.md` counted seven maintained English↔Chinese
  documentation pairs, and its header date trailed its last content
  change.** `docs/languages.json` declares eight pairs — `docs/README.md`
  joined as the eighth in v0.7.0's restructure.
- **The validator transcript in both READMEs was labelled a v0.7.1
  snapshot.** No such block existed at that tag, and its counts were
  revised after it. The label now names what the block is: a snapshot at
  `HEAD`, dated.
- **README §9.1 pointed all four roadmap items at `docs/EVALUATION.md`**,
  where only the scoring-rubric question is open — the other three are
  recorded there as resolved. Each item now links the issue that tracks
  it, and the three open help-wanted issues the section did not name — a
  `tree.json` diagram export, a showcase gallery, and long-run ergonomics
  — are listed.

## v0.7.1 — 2026-08-16

Closes the coverage gap v0.7.0 documented but did not fix, and applies a
full-corpus documentation audit. 14 findings confirmed, 26 rejected by an
independent refuting pass — including one the maintainer had called
confirmed (`presets/design.md`'s `(F = 0)` parenthetical glosses "violated
hard constraint", so the gate was never inverted).

### Added (test coverage)

- **`tools/tests/test_checks.py`** — 7 clean cases + 40 rejection cases,
  running all seven check groups against a synthetic repository and
  mutating it once per rule. A trace had shown 17 of
  `validate_plugin.py`'s 35 functions were never entered by any test,
  including `main()`, `check_manifests`, `check_crossrefs`, `check_i18n`
  and every cross-file sub-check: all of them could have been reduced to
  no-ops with CI still green. Coverage is now 35/35. Wired into CI as a
  fifth step.

### Fixed (found by the new tests)

- **Deleting *every* command wrapper passed the wrapper-parity check.**
  `check_commands` returned early on `not files`, so N=0 — the most
  complete way to violate the rule — was the one case that passed.
- **`_check_command_flags` ignored its argument.** Written as
  `def f(repo: Path = REPO)`, the module global was captured at def time,
  so the check always scanned the real repository. It was consequently the
  one cross-ref sub-check that could not be pointed at a fixture, and
  therefore the one that could not be tested.
- **v0.7.0's own zero-count tripwire was too strict.** It required at
  least one *anchored* link, but zero anchored links is a legitimate
  state, and it rejected the validator's own fixture repository. Narrowed
  to the one count that cannot legitimately be zero (`md_files`); proving
  each sub-check still fires is a test's job, and now is one.

### Fixed (documentation)

- **Following CONTRIBUTING's field-profile recipe broke CI.** Profiles are
  registered in `docs/languages.json` one path at a time while `presets/`
  and `commands/` use globs, so a new profile was an unregistered
  canonical document. Both the contributor guide and
  `field-profiles/README.md` now carry the registration step.
- **The chaining handoff contract said deliverables are "line-per-item"**
  and told `tree-chain` to take "the first K lines". Deliverables are
  ranked `## <id>` sections carrying several lines of fields each, so a
  head-N over lines would slice an item's body in half. Now defined as
  entries, split on level-2 headings.
- **ENGINE §4's slot table named fields no preset declares.**
  `falsifiability` was attributed to `design` (which has no such field)
  and `cost_of_change` to nothing at all. Every example is now a field a
  shipped preset really declares, slots 8 and 11 are marked
  preset-optional, and the §3.X external-check category — required by the
  spec but occupying whichever of the 12 slots a preset can spare — has a
  row.
- **§F7 listed `--max-branches` as a cap with a cap-trip status**, but
  §6.1, §6.2 and §7.4 define none. It raises a per-node ceiling whose
  floor §3 fixes at 12 and never terminates a run; §F7 now says so.
- **README's output-layout paragraph double-nested the run directory**,
  contradicting its own fence six lines below and the worked example: an
  explicit `--out` *is* the run directory, and the dated segment belongs
  to the default value only.
- README described `CONTRIBUTING.md` as "one command and two rules" (it is
  five and five) — counts removed rather than corrected, so the two files
  cannot drift again; "on every push" narrowed to "every pull request and
  every push to `main`", matching `ci.yml`'s `branches: [main]`.
- Two physically wrong worked examples in `framings.md`: relaxing a 5σ cut
  to 3σ cannot make detections *drop out* (it triples the sample), and
  10¹¹ M_sun is a Milky-Way-scale halo, not the galaxy-cluster regime.
- `docs/EVALUATION.md` gained the v0.7.0 and v0.7.1 decision paragraphs its
  header date already claimed; the v0.7.0 changelog's "4 per preset"
  phantom-heading count corrected to "3–4".

## v0.7.0 — 2026-08-16

Repository restructure, README rewrite, and a fourth adversarial sweep —
this one a 5-dimension multi-agent audit (32 findings confirmed by an
independent refuting pass, 6 rejected, including one the verifier and a
first-party `wc -l` both refuted). Nothing in the runtime prompt changed
semantics except three contract-drift fixes listed below.

### Fixed (the checks themselves)

- **Running the test suite broke the validator.** `is_skipped`'s skip
  list was maintained by hand against `.gitignore` and had drifted:
  `.pytest_cache/README.md` is a real file pytest writes, so
  `pytest && python tools/validate_plugin.py` reported it as an
  *unregistered canonical document*. Dot-prefixed directories are now
  skipped by rule, which cannot drift from `.gitignore` the way a list
  can. `.venv/`, `.ce/`, `.claude/`, `.mypy_cache/`, `.tox/` are covered
  by the same rule.
- **`examples/attack/expected-out/*.md` was invisible to every
  cross-file check.** The run-output heuristic skipped any path
  component ending in `-out`, which swallowed the repository's own
  showcase fixtures. The suffix test is now anchored to the top-level
  component, where run output actually lands.
- **`pytest` passed unconditionally.** Both suites record diagnostics in
  a module list that only `main()` inspects, so every collected `test_*`
  returned normally: injecting `root_kind: BOGUS` into a shipped preset
  still printed `13 passed` while the script runner correctly exited 1.
  Collected tests now re-raise what they recorded, and the same mutation
  produces `1 failed`.
- **Heading extraction was fence-blind.** `validate_plugin` had its own
  `^#{1,6}` regex applied to raw text, so a `#`-prefixed line inside a
  fenced example counted as a heading (9 phantom headings in ENGINE.md,
  3–4 per preset) and fed the §-namespace, the anchor slug table, and the
  field-profile section check. It now reuses `_i18n.scan_markdown`,
  leaving one heading scanner in the repository.
- **Relative links without an anchor were never checked.** The link
  pattern required a `#fragment`, so `](../docs/ENGINE.md)` — the form
  nearly every command, preset, and doc uses — was unverified. All 208
  relative links now resolve or CI fails; the check caught its own
  authors' stale paths during this restructure.
- **Zero-count tripwires.** Each cross-ref sub-check returned a count
  nothing asserted on, so any of them could silently become a no-op. A
  zero now fails.
- **Nothing tied the version to its release notes.** `CHANGELOG.md` had
  no `## v0.5.0` section although v0.5.0 shipped as a tag and a GitHub
  release — its notes sat unheaded inside `## v0.5.1`. The manifests
  check now requires a section for the declared version, and requires
  `plugin.json` and `marketplace.json` to agree on description,
  keywords, author, homepage, repository, and license.
- **Skill discovery was hard-coded** to `skills/tree/SKILL.md` in the
  flag and §-namespace checks while every neighbouring check globbed
  `skills/*/SKILL.md`. Both now enumerate.
- **`tools/**/*.py`** is syntax-checked recursively, so the relocated
  tests stay covered.
- **The diagram generator has a CI gate.** It was only `ast.parse`-d,
  never run; CI now regenerates and diffs against the committed SVG.

### Fixed (contract drift)

- **`/cc-tree:brainstorm --no-online` could never converge.** The preset
  declared field 11 `--no-online → empty`, and ENGINE §4 forces
  `INCOMPLETE_FORBIDDEN` on any empty field, which §6.1 condition 1 then
  blocks on forever. The field now records
  `external_resources_unchecked=true`, matching ENGINE §3.X.
- **The default `tree-chain` pipeline stopped at stage 2.** `design`'s
  baseline stops unconditionally with `EARLY_STOP=root_underspecified`
  when `goal_statement` / `hard_constraints` are empty, and a seeded
  stage-2 run has no `<root>` to fill them from. Seeded runs now derive
  both fields from the seeds and the prior run's root.
- **`option_<id>.md` was undeclared.** The design→attack handoff file is
  named by `chaining.md` and `tree-chain.md` but appeared in no output
  contract. ENGINE §7.2 and SKILL.md §4 now list per-item files, and
  explain why they cannot live in `output_artifacts` frontmatter.
- `glossary-anchors.md` added to SKILL.md's output contract (ENGINE §7.2
  had it); `§6.2` corrected to `§6.1 condition 2` at the seven sites that
  meant the ratio rather than the decision table; `§0–§9` corrected to
  `§0–§11`; ENGINE §2.1's non-inference preset list now includes
  `design`; `docs/presets.md`'s "eight rules" replaced by the ten
  conditions the validator actually enforces, and its contradictory
  "15-line"/"4-line" wrapper sizes dropped.
- **Copying `_template.md` produced a rejected profile.** Neither the
  template nor the authoring steps said to change `field:`, which the
  validator requires to equal the basename. Both now do.
- **The showcase example blamed the cap for its own abridgement.** All
  four files claimed `tree.json`, `REPORT.md`, and the 12-field
  derivation appear only in an "uncapped run"; §F7 requires them under a
  cap too. The regeneration target also moved to the already-ignored
  `attack-out/`, so there is one list of ignored output names instead of
  two.

### Changed (structure)

- `EVALUATION.md` → `docs/EVALUATION.md`; `tools/test_*.py` →
  `tools/tests/`. Test scripts put `tools/` on `sys.path` themselves, so
  both the script form CI uses and `pytest` work from any directory.
- New `docs/README.md` (+ `.zh.md`) documentation index and
  `CONTRIBUTING.md`.
- `.gitignore` grouped by purpose and completed: `chain-out/` (the
  shipped `tree-chain` default) and `.claude/` were missing.

### Changed (docs)

- README rewritten and restructured: what it is, how it works in five
  steps, why it differs, a categorized feature reference, a full flag
  table, the output layout, a repository map, and a documentation index.
  Chinese parallel rewritten alongside it.
- Manifest keywords expanded from 9 to 35 across both manifests.

## v0.6.0 — 2026-08-10

Adversarial multi-model review sweep. Three parallel read-only
`gpt-5.6-sol` (xhigh reasoning) reviews — parser+validator, i18n
subsystem, whole-repo architecture — returned 55 numbered findings; 26
selected claims were reproduced by execution before any fix (26/26
confirmed), the rest verified or rejected by reading. The theme of what
they found: the *gates themselves* had false-pass channels. Nothing that
ships in the runtime prompt changed except one ENGINE contract
clarification; this release is the validator, the parser, the i18n
checker, and their tests.

### Fixed (validator false-passes)

- **Nested collections passed where the schema requires scalars.**
  `str()`-coercion made a parsed dict truthy, so
  `subject_label:\n  nested: idea`, a flow-map `node_schema` entry, a
  nested `output_artifacts.primary`, and a nested verdict label all
  validated; a mapping-valued `convergence_metric` crashed with
  `TypeError: unhashable type` instead of failing. Every scalar field
  now must BE a non-empty string.
- **Identifier discipline was unenforced.** 12 identical `node_schema`
  fields, duplicate `score_dims` keys, duplicate verdict labels, and a
  `TOOLONG` score key all passed. Now: node fields / score keys /
  verdict labels must be distinct, and score keys must match the 1–3
  letters `docs/presets.md` §1 has always promised.
- **`output_artifacts` paths were not confined.** `../../escape.md` and
  `C:/absolute.md` validated although every artifact is written under
  the run's `<out>/`; `secondary` values were not validated at all. Both
  now require a bare `*.md` filename.
- **Field-profile sections were substring-matched**, so `###
  Reviewer concerns` (wrong level) — and even a commented-out heading —
  satisfied `"## Reviewer concerns" in text`. Now parsed as headings and
  matched as level-2 titles (annotation suffixes still allowed).
- **A wrapper-specific flag could be "documented" by an unrelated
  preset's mention in the skill body** (e.g. `--focus` added to the
  design command validated via SKILL.md's attack-flag docs). Common
  flags (the skill's own `argument-hint` namespace) may ride on skill
  docs; wrapper-specific flags now need the command body or its own
  preset body.
- **Duplicate headings broke anchor checking**: GitHub serves
  `#repeat-1` for the second `## Repeat`, but the slug cache only held
  `repeat`, so a valid link was reported dead.
- **`check_manifests` accepted empty strings** for name/version/
  description, non-object `plugins[]` entries — and a *missing*
  plugin.json escaped as a raw `FileNotFoundError` traceback.
- **Preset↔command wrapper parity is now enforced**: deleting a shipped
  wrapper command previously left a validator-approved package that
  contradicted README's advertised pairing.

### Fixed (parser — strict subset, no silent recovery)

The frontmatter parser feeds the validator, so silently guessing at
malformed input converted authoring mistakes into validated presets.
Out-of-subset constructs now raise `FrontmatterError` (which the
validator reports as a clean per-file failure):

- junk non-mapping lines and **duplicate keys** (last-wins let
  `name: wrong` be shadowed) — now errors;
- misindented orphan lines (silently skipped before) — now errors;
- `-one` without the YAML-required space after `-` — was accepted as a
  list item, now an error;
- text after a flow map (`- {key: S} GARBAGE`) and flow-map entries
  without `key: value` — were discarded, now errors.

Constructs that are *valid* YAML the parser previously mangled now parse
correctly:

- `key: # comment` kept its children (was: parsed as the scalar `""`
  and silently dropped the nested block); `key: | # comment` starts a
  block scalar (was: the literal string `"|"`);
- a one-key block-map list item (`- key: S` with no continuation) is a
  mapping (was: the scalar string `"key: S"`);
- an inline flow map as a value (`verdict_enum: {advances: A, …}`)
  parses to a dict and validates like the block form (was: one string,
  falsely rejected);
- a UTF-8 BOM before `---` no longer hides the frontmatter, and the
  returned Markdown body keeps its leading blank lines (`\s*` in the
  delimiter regex ate them).

Deliberately NOT implemented (documented subset limits in the module
docstring): double-quoted `\"` escapes and doubled `''` decoding, and
literal/folded block-scalar indentation + chomping semantics — the
shipped presets use none of these, and a false *rejection* is loud
while the above false *acceptances* were silent.

### Fixed (i18n gates)

- **`canonical_only` could whitelist an orphan Chinese file**: its paths
  fed the translation registry, so declaring `docs/orphan.zh.md` an
  "English-only exception" laundered it past coverage. `.zh.md` entries
  are now rejected and the registry is built from pair translations
  only.
- **Han characters hidden in comments counted as Chinese prose.** The
  has-Chinese check ran on raw text, so an English copy plus
  `<!-- 中 -->` passed. Prose checks now strip comments/code/URLs
  first, and a Han floor (≥ 10 % of the English letter count; shipped
  pairs' measured minimum is 21 %) replaces mere Han presence.
- **Distinctive tokens escaped the inline-code check.** `root_kind`
  (whole-document class) could be localized in its inline `` `code` ``
  uses as long as a byte-identical fence still contained the word.
  Inline-code parity now applies to every harvested token.
- **Harvesting missed map keys and non-tree skills.** A preset's
  `output_artifacts.secondary.rejected: rejected.md` never contributed
  `rejected`; a second `skills/*/SKILL.md` would contribute nothing.
  Both harvested now (298 → 439 machine-token checks across the 7
  shipped pairs, all already faithful).
- **Fence parity ignored the delimiter and the owning section**: a
  tilde fence swapped in for a backtick fence with the same body, or an
  identical fence moved to a different section, passed
  "byte-identical". Fences now carry (marker, info, body, section
  index).
- **`load_manifest` robustness**: a JSON array root crashed with
  `AttributeError`; `"schema_version": true` passed because
  `True == 1`; null token/flag entries were coerced to `"None"`. All
  clean `I18nError`s now. Manifest paths (pairs and `canonical_only`)
  must be clean repo-relative POSIX paths — backslashes, absolute
  paths, drive letters, and `.`/`..` segments are rejected.
- **Digest declarations**: first-match-wins allowed a correct digest to
  shadow a stale second one, anywhere in the file. Now exactly one
  `i18n-source-sha256` comment, inside the lead block (same 12-line
  window as the banner).

### Fixed (contract)

- **ENGINE.md §0.1 contradicted §5.3 / §7.4 on what counts toward
  `width`.** §0.1 required every terminal leaf to have had §3 run on it
  and score ≥ the pruning threshold — under which `kept`/`pruned` tips
  (never re-expanded, per §5.3) could never be terminal leaves, while
  §7.4's report template counts `leaf_count` across the full verdict
  distribution. §0.1 now defines terminality by verdict role:
  `kept`/`pruned` are tips the moment they are scored (and count);
  `advances` is terminal only after its re-expansion produced no
  surviving children; `blocked` never counts. (+ zh mirror)
- **The README diagram is labeled an illustrative mid-run snapshot** —
  it shows live `advances` frontier tips and `blocked` leaves, both of
  which §0.1/§6 forbid in a *converged* tree, so claiming it as a final
  state contradicted the contract it illustrates.
- The validator's summary line now says `frontmatter schema` instead of
  `full schema` — body-level compliance (§11's checklist) is explicitly
  a maintainer audit, not a CI claim.

### Changed (structure)

- **`ValidationError` replaces `sys.exit` in every check helper**;
  only `main()` prints and exits (`FAIL(<check>): …`), so the checks
  are importable and the tests stopped redirecting stderr to catch
  `SystemExit`. `FrontmatterError` is converted to the same clean
  failure at each parse site.
- **`validate_manifest` split** into `_validate_pairs` /
  `_collect_canonical_only` / `_check_coverage` — the one function the
  complexity scan flagged as genuinely decomposable (three independent
  failure domains). `validate_preset_schema` likewise became five
  rule-cluster helpers; `_check_command_flags` split into skill-side
  and wrapper-side halves. radon: two D-grade functions (CC 25 / 24)
  → zero at D, worst now C(19); MI all A.
- **`gen_radial_tree.py` no longer renders at import time**: the
  imperative body moved into `build()` + `main()`, all text is
  XML-escaped, the hard-coded model is validated before rendering
  (depth vs ring table, non-empty trees, known verdict codes, wedge
  bounds — previously a deep tree raised `KeyError: 5` mid-render),
  and the emitted SVG must pass `ElementTree.fromstring` before being
  written. The angle helpers' single-revolution / ≤ 180° wedge
  assumptions are now stated and enforced rather than latent.
- **Both test runners grouped into named test functions**; negative
  schema cases pin a diagnostic substring (`expect_fail(label, text,
  want)`) so an unrelated rejection cannot green a dead check, and
  mutations go through a replace-exactly-once helper so a drifted
  `VALID` template cannot silently turn a mutation case into a no-op.
  test_validate: 23 → 50 cases; test_i18n: 30 → 43 cases.

### Not adopted (reviewed and rejected, with reasons)

- Per-section machine-token *counts* (vs presence): a faithful zh
  translation legitimately merges repeated English mentions; equal
  counts would false-fail correct translations.
- `tree.md.bak`-style boundary porosity in `_token_present`: excluding
  a trailing `.` would false-fail `writes tree.md.` at sentence end;
  trade-off documented in the function comment.
- Double-backtick inline spans and Setext headings in `scan_markdown`:
  zero uses in the repo; the structure check only needs to be sound for
  the constructs the docs actually use.
- Splitting `_parse_map`/`_parse_list` further or merging the two
  quote-tracking scanners: recursive-descent traversal is essential
  complexity; both reviews' architecture lens agreed the parser should
  stay intact.
- Inverting the `validate_plugin` ↔ `_i18n` constant-passing
  relationship: real coupling, but the inversion churns every consumer
  for a boundary that is documented and tested as-is.

### Added (CI)

- `workflow_dispatch` trigger. The 2026-08-06 Actions outage wedged run
  31120377768 into a state no API call could clear — the run reported
  `queued` while its re-run was never dispatched, so `rerun` answered
  "already running", `cancel` answered "already completed", and
  `force-cancel` answered "re-run that has not yet queued". With only
  `push` and `pull_request` triggers, no verdict was reachable for that
  commit without pushing another one. `gh workflow run ci.yml` now is.

### Verification

`validate_plugin.py` (7 checks, now 439 machine-token checks + wrapper
parity) + `test_validate.py` (50 cases) + `test_i18n.py` (43 cases) all
pass; every fixed false-pass has a regression case that pins its
diagnostic; the regenerated SVG diffs only in the snapshot-wording
subtitle (n = 35 stats unchanged).

## v0.5.1 — 2026-08-06

Maintenance release. Nothing that ships with the plugin changed — no
skill, preset, command, or doc differs from v0.5.0. This is the CI
toolchain and the validator's own internals.

### Changed (CI)

- `actions/checkout` v4 → v7 and `actions/setup-python` v5 → v7. Both
  older majors target Node 20, which GitHub deprecated and now
  force-migrates to Node 24 with a warning on every run; v7 targets
  Node 24 natively, so the pinned version is the version that runs.

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

## v0.5.0 — 2026-08-06

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
