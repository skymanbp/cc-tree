---
description: Design-space exploration tree. Wraps `/cc-tree:tree` with the design preset preselected — enumerates options × trade-offs × reversibility × cost × fit-with-constraints for an engineering / product / process decision. Produces a comparison table and a RECOMMENDED short-list.
argument-hint: "<design-prompt-string|file.md> [--width N|∞] [--depth N|∞] [--rounds N|conv] [--out <dir>] [--glossary <path>] [--field <name|path>] [--no-online]"
---

Invoke the `tree` skill with the design preset. The default output
directory is `design-out/<UTCdate>__<prompt-slug>/` (override with
`--out`).

Run:

```
/cc-tree:tree $ARGUMENTS --preset design
```

If `$ARGUMENTS` is a quoted prompt string, the engine uses it
directly. If it's a `.md` file path, the engine reads structured
goals / constraints / context from the file.

Preset details: [`presets/design.md`](../presets/design.md).
Engine spec: [`docs/ENGINE.md`](../docs/ENGINE.md).
