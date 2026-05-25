# Changelog

All notable changes to the `cc-tree` plugin. Versions follow the
`plugin.json` / `marketplace.json` `version` field.

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
