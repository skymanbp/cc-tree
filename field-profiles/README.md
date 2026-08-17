# Field profiles

> Language: English (canonical). Chinese: [`field-profiles/README.zh.md`](README.zh.md).

A **field profile** is an optional markdown file that gives the cc-tree
engine domain-aware reviewer weighting. It makes the 12 framings attack
and explore the way a senior practitioner in a specific field would —
prioritizing that field's habitual concerns, consensuses, and failure
modes — instead of relying only on the model's generic training
distribution.

Profiles are **preset-agnostic**: one profile (say, a `physics.md`
you author) helps `attack` audit a physics paper, `brainstorm` explore
physics research directions, and `code-audit` review a physics
simulation.

One concrete profile ships with the plugin:
[`physics.md`](physics.md) (ApJ/MNRAS/PRD-reviewer weighting, weak-
lensing/cosmology flavored). For any other field, author your own from
[`_template.md`](_template.md) (see "Authoring one" below); an
unresolvable `--field <name>` warns `[FIELD_PROFILE_NOT_FOUND]` and
continues without weighting.

## Using a profile

```bash
# By name — resolves to field-profiles/<name>.md in this plugin
# (physics ships built-in; other names need authoring first)
/cc-tree:attack ./paper.tex --field physics

# By path — any file you control
/cc-tree:brainstorm "research directions" --field ./my-lab-profile.md
```

If the profile can't be found, the engine warns
(`[FIELD_PROFILE_NOT_FOUND]`) and continues without weighting — a
profile is an enhancement, never a requirement.

## What a profile contains

Four short, concrete lists (see [`_template.md`](_template.md)). The required
section headings remain the canonical English identifiers shown below so the
engine and validator can find them deterministically; the list bodies,
descriptions, citations, and quoted evidence may use any language. They do not
change the run's `output_language` selected by `--lang`.

| Section | Feeds | Purpose |
|---|---|---|
| Reviewer concerns | §3.C cross-disciplinary, §3.D red team | What this field's reviewers attack first |
| Field consensuses | §3.I contrarian | What the field assumes + where it breaks |
| Common failure modes | §3.J failure-driven | How work here goes wrong in practice |
| Evidence bar | §3.X external check, §4 citations | What counts as strong vs weak evidence |

## Authoring one

1. Copy [`_template.md`](_template.md) to `field-profiles/<your-field>.md`
   (or anywhere, and pass the path).
2. **Set the `field:` key to the new basename** and rewrite
   `description:`. The validator requires `field` == filename, so a
   copy that keeps `field: _template` is rejected — and the underscore
   that exempts the template itself will not exempt yours.
3. Fill each list with **concrete, checkable** entries. "Be rigorous"
   carries no weighting signal; "report effect size with a 95% CI"
   does.
4. Keep it short — 3–6 items for the three enumerative lists. The
   profile re-prioritizes; it does not replace the framings.
5. If the profile lives **in this repository**, register it in
   [`docs/languages.json`](../docs/languages.json) under `canonical_only`,
   with a reason. Profiles are registered one path at a time rather than by
   glob, so an unregistered one fails the documentation-coverage check. A
   profile you keep outside the repo and pass by path needs no registration.

A field profile **cannot** weaken any universal engine rule
(`docs/ENGINE.md` §0.5). It only changes the *order* in which branches
are explored and raises the evidence bar — it never permits a hedge, a
deferred leaf, or an unverified citation.

> Files beginning with `_` (like `_template.md`) are scaffolding, not
> selectable fields.
