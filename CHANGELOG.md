# Changelog

All notable changes to the `cc-tree` plugin. Versions follow the
`plugin.json` / `marketplace.json` `version` field.

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
  pass + 9 negative cases rejected). Both run in CI.
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
  `field-profiles/<name>.md`; feeds §3.C / §3.D / §3.I / §3.J.
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
