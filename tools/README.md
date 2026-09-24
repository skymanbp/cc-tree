# `tools/` — how the verification toolchain fits together

Nothing in this directory ships to the runtime. The plugin is Markdown;
these scripts exist to keep that Markdown honest, and they use the Python
standard library only (CI installs nothing).

## Modules

| File | Role | Used by |
|---|---|---|
| [`_frontmatter.py`](_frontmatter.py) | YAML-subset parser for the `--- … ---` blocks in presets, skills, commands, and field profiles. Anything outside the subset raises `FrontmatterError` rather than being guessed at. | `validate_plugin.py`, `_i18n.py`, tests |
| [`_i18n.py`](_i18n.py) | Fence-aware Markdown scanner, `docs/languages.json` loader, the bilingual contract (`validate_i18n`), and the two path rules every scan shares: `is_skipped` (what is never a document) and `is_clean_relative_path` (what may not leave its root). | `validate_plugin.py`, tests |
| [`validate_plugin.py`](validate_plugin.py) | The seven check groups CI runs — the one entry point contributors call by hand. | tests |
| [`gen_radial_tree.py`](gen_radial_tree.py) | Renders `docs/assets/cc-tree-radial-tree.svg`. CI regenerates and diffs it, so the committed diagram cannot drift from the generator. | — |
| [`tests/_harness.py`](tests/_harness.py) | The `sys.path` bootstrap and the pytest-visibility wrapper the three suites share. | the suites |

## One `validate_plugin.py` run

Groups run in this order and the first failure stops the run:

```
.claude-plugin/*.json ─► check_manifests ──── versions agree, duplicated metadata identical,
                                              CHANGELOG has the declared version's section
skills/*/SKILL.md ────► check_skills ──────── frontmatter name == directory name
presets/*.md ─────────► check_presets ─────── _frontmatter → validate_preset_schema
                                              (ENGINE §10–§11: 12 fields, 5 dims, 4 verdict
                                              roles, confined artifact and glossary paths)
commands/*.md ────────► check_commands ────── description present; every preset has a wrapper
tools/**/*.py ────────► check_tools_syntax ── ast.parse only, never imported
every *.md ───────────► check_crossrefs ───── links stay in the repo, exist, and anchor to a
                                              real heading; examples/ citations in bounds;
                                              command flags documented; field-profile schema;
                                              §-references resolve to a heading
docs/languages.json ──► check_i18n ────────── _i18n.validate_i18n: every document registered,
                                              digests fresh, headings and fences aligned,
                                              machine tokens preserved
```

A check raises `ValidationError`; only `main()` turns one into stderr plus a
non-zero exit, so every check is importable and testable without process
games. "Every `*.md`" is decided by `_i18n.is_skipped` for both the
cross-ref and the i18n scans: dot-directories, `SKIP_DIR_PARTS`, and a
top-level `*-out/` run directory are never documents.

## Tests

| Suite | Proves |
|---|---|
| [`tests/test_validate.py`](tests/test_validate.py) | `validate_preset_schema` and the parser: the shipped presets pass; each rule rejects a broken preset *with the pinned diagnostic*; parser edge cases parse exactly. |
| [`tests/test_i18n.py`](tests/test_i18n.py) | `validate_i18n` against a temporary bilingual fixture, one mutation per contract clause, then the shipped pairs. |
| [`tests/test_checks.py`](tests/test_checks.py) | All seven check groups against a synthetic repository: clean once, then one mutation per rule. This is the suite that can tell a check has silently become a no-op. |

Each suite is a plain script — what CI runs — and also collects under
pytest; `_harness.expose_to_pytest` is what makes a collected test fail
whenever the script would. The commands, in CI order, are in
[`../CONTRIBUTING.md`](../CONTRIBUTING.md).
