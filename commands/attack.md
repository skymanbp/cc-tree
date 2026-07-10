---
description: Adversarial radial-tree critique. Wraps `/cc-tree:tree` with the attack preset preselected — finds the strongest reviewer-style attacks against a finished artifact (document / argument / proposal). Every leaf resolves to CONFIRMED / MARGINAL / REFUTED with `file:line` evidence; hard-banned against NEEDS-MORE-INFO deferrals.
argument-hint: "<file_path> [--focus <section|claim|equation>] [--from-prior <report.md>] [--width N|∞] [--depth N|∞] [--rounds N|conv] [--out <dir>] [--field <name|path>] [--no-online]"
---

Invoke the `tree` skill with the attack preset. The default output
directory is `attack-out/<UTCdate>__<artifact-slug>/` (override with
`--out`).

Run:

```
/cc-tree:tree $ARGUMENTS --preset attack
```

If `$ARGUMENTS` is empty or doesn't specify a file path, the engine
will report `EARLY_STOP=root_unparseable` — you must point it at
an artifact.

Preset details: [`presets/attack.md`](../presets/attack.md).
Engine spec: [`docs/ENGINE.md`](../docs/ENGINE.md).
