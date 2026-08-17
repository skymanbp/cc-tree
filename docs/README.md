# cc-tree documentation

> Language: English (canonical). Chinese: [`docs/README.zh.md`](README.zh.md).

Everything that specifies, teaches, or justifies the engine. The project
overview lives one level up in [`../README.md`](../README.md); this page is
the annotated index of the rest.

## Start here

| Document | Read it when |
|---|---|
| [`../README.md`](../README.md) | You want the overview, the install command, and the feature list |
| [`ENGINE.md`](ENGINE.md) | You want the binding contract: §0 data model through §11 compliance checklist |
| [`framings.md`](framings.md) | You want the 12 framing prompts in full, with a worked example per preset |
| [`../examples/attack/README.md`](../examples/attack/README.md) | You want to see a real input, a real deliverable, and how to reproduce them |

`ENGINE.md` is the one to read if you only read one. The skill file
([`../skills/tree/SKILL.md`](../skills/tree/SKILL.md)) is a seven-step
navigation guide that defers to it; every preset extends it and none may
weaken it.

## Authoring

| Document | Read it when |
|---|---|
| [`presets.md`](presets.md) | You are writing a preset — the frontmatter schema, the body sections, the compliance rules |
| [`../field-profiles/README.md`](../field-profiles/README.md) | You are writing a domain lens for `--field` |
| [`chaining.md`](chaining.md) | You are wiring several presets into a pipeline, by hand or via `tree-chain` |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | You are opening a pull request against this repository |

## Background

| Document | Read it when |
|---|---|
| [`EVALUATION.md`](EVALUATION.md) | You want the design rationale: why one engine and four presets, why 12 framings, why the bans, and which alternatives were rejected |
| [`../CHANGELOG.md`](../CHANGELOG.md) | You want the per-version history, including what each debug sweep found |

## Machine-readable sources

| File | Owns |
|---|---|
| [`languages.json`](languages.json) | The bilingual document manifest: every English/Chinese pair, every canonical-English exception with its reason, the required runtime flags, and the fixed machine tokens a translation may never localize |
| [`assets/`](assets/) | Generated diagrams. `cc-tree-radial-tree.svg` is produced by [`../tools/gen_radial_tree.py`](../tools/gen_radial_tree.py) and is regenerated, never hand-edited |

## Documentation conventions

Unsuffixed `X.md` files are canonical English. `X.zh.md` files are
maintained Chinese parallels, and each records a SHA-256 digest of the
LF-normalized English source in its lead block. Editing an English
document therefore invalidates its translation's digest, and CI fails
until the Chinese side is reviewed and the digest refreshed — the
mechanism that keeps a translation from quietly describing last month's
behavior. Documents with no translation are declared in `languages.json`
with a reason, not left implicit.

Section pointers of the form `§N`, `§N.M`, and `§FN` are prose references
into `ENGINE.md`, the skill, or a preset. They are validated: every one
must resolve to a real heading, so renumbering a section fails CI rather
than leaving dangling pointers.

## Verifying a change

```bash
python tools/validate_plugin.py     # 7 check groups; what CI runs first
python tools/tests/test_validate.py # preset schema + frontmatter parser cases
python tools/tests/test_i18n.py     # bilingual contract cases
```

Details, including how to refresh a translation digest, are in
[`../CONTRIBUTING.md`](../CONTRIBUTING.md).
