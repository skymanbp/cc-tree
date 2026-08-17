# Contributing to cc-tree

Issues and pull requests are welcome. This page is the short version of
everything CI will check before a human reads your diff.

## Run the checks locally

```bash
python tools/validate_plugin.py       # 7 check groups — run this first
python tools/tests/test_validate.py   # preset schema + frontmatter parser cases
python tools/tests/test_i18n.py       # bilingual contract cases
python tools/tests/test_checks.py     # every check group vs a synthetic repo
python tools/gen_radial_tree.py       # only if you touched the generator
```

These are the five steps
[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs, on Python 3.11
and 3.13 (CI diffs the regenerated diagram against the committed one rather
than trusting it). There are no third-party dependencies — the standard
library is enough, deliberately.

`pytest` also works (`python -m pytest tools -q`) and is a real signal: the
collected tests re-raise what they record. Before that fix they returned
normally no matter what, so `13 passed` meant nothing. The commands above
remain the authority, because they are what CI runs.

## Where things live

| Path | Contains | Moves are |
|---|---|---|
| `.claude-plugin/` | `plugin.json`, `marketplace.json` | **fixed** — Claude Code looks here |
| `commands/` | Slash-command wrappers | **fixed** — Claude Code looks here |
| `skills/<name>/SKILL.md` | The skill Claude Code loads | **fixed** — Claude Code looks here |
| `presets/<name>.md` | Preset schemas + baseline recipes | **contract** — `--preset <name>` resolves here |
| `field-profiles/<name>.md` | Domain lenses | **contract** — `--field <name>` resolves here |
| `docs/` | Engine spec, framings, authoring guides, rationale, `languages.json` | free, but every path is registered in `docs/languages.json` |
| `examples/` | Worked input + expected output fixtures | free; citations into them are bounds-checked |
| `tools/` | Validators and generators | **anchored** — each script derives the repo root as its own parent's parent |
| `tools/tests/` | Self-tests for the above | anchored one level deeper |

## The five invariants that trip people up

**1. A preset is schema-validated.** Exactly 12 `node_schema` entries,
exactly 5 `score_dims` (each with a distinct 1–3 letter `key`), exactly the
4 `verdict_enum` roles with distinct labels, a `convergence_metric` naming
one of those roles, and `output_artifacts` values that are bare `*.md`
filenames. The full rule set is `docs/ENGINE.md` §10–§11 and
[`docs/presets.md`](docs/presets.md).

**2. A preset needs its command wrapper.** Shipping `presets/foo.md`
without `commands/foo.md` fails the wrapper-parity check — the README
advertises the pairing, so the package may not contradict it.

**3. Editing an English document invalidates its translation.** Every
`X.zh.md` records a SHA-256 of the LF-normalized `X.md`. Change the English
side and CI fails until the Chinese side is reviewed and its digest
refreshed. To see the expected value:

```bash
python -c "import sys; sys.path.insert(0, 'tools'); from _i18n import source_digest; print(source_digest(open('README.md', encoding='utf-8').read()))"
```

Paste it into the `<!-- i18n-source-sha256: ... -->` comment in the lead
block of the translation. The checker also compares heading structure and
requires every fenced block to be byte-identical, so code examples carry
over verbatim rather than being localized.

**4. Any new `.md` must be registered.** `docs/languages.json` lists every
paired document and every canonical-English exception *with a reason*. An
unregistered Markdown file anywhere outside a dot-directory or a top-level
`*-out/` directory fails the coverage check. This is intentional: it makes
"ship an untranslated doc" a decision someone writes down.

**5. Renumbering a section breaks pointers.** `§N` / `§N.M` / `§FN` prose
references are resolved against real headings across the whole repository,
and every relative Markdown link must resolve on disk. Move a file or
renumber a heading and CI tells you which references died.

## Adding things

- **A preset** — copy the closest of the four shipped presets, adjust the
  frontmatter, write the §2 baseline recipe and the per-framing flavors, add
  `commands/<name>.md`, and register nothing else; the preset globs pick it
  up. Guide: [`docs/presets.md`](docs/presets.md).
- **A field profile** — copy
  [`field-profiles/_template.md`](field-profiles/_template.md), **set the
  `field:` key to your new basename**, fill the four required `##` sections,
  **and register the file in `docs/languages.json`** under `canonical_only`
  with a reason. That last step is not optional and is easy to miss:
  `presets/` and `commands/` are registered by glob, but field profiles are
  registered one path at a time, so a new profile is an *unregistered
  canonical document* and fails invariant 4 until you add it. Guide:
  [`field-profiles/README.md`](field-profiles/README.md).
- **A translation** — add a `pairs` entry to `docs/languages.json`, mirror
  the heading structure exactly, keep every fence byte-identical, and record
  the source digest.
- **A validator check** — put behavior in `tools/validate_plugin.py` and a
  case that fails without it in `tools/tests/`. Negative cases pin the
  expected diagnostic substring, so a rejection for an unrelated reason
  cannot green a dead check.

## Releasing

The version in `.claude-plugin/plugin.json` must match
`.claude-plugin/marketplace.json` in both places, the two manifests must
agree on description, keywords, author, homepage, repository, and license,
and `CHANGELOG.md` must carry a `## v<version>` section. All four are
enforced by the manifests check, so a release cannot ship without its notes.

If a change alters `tools/gen_radial_tree.py`, regenerate the diagram rather
than editing the SVG:

```bash
python tools/gen_radial_tree.py
```

## Style

Match the surrounding file. Prose documents explain *why* a rule exists,
not only what it is — most of this repository's comments exist because
something silently went wrong once, and the comment is the record of it.
Keep that habit: when you fix a defect a check should have caught, add the
check.
