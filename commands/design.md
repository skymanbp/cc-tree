---
description: Design-space exploration tree. Wraps `/cc-tree:tree` with the design preset preselected — enumerates options × trade-offs × reversibility × cost × fit-with-constraints for an engineering / product / process decision. Produces a comparison table and a RECOMMENDED short-list. 中文触发：设计空间探索、方案对比与取舍、给出推荐短名单。
argument-hint: "<design-prompt-string|file.md> [--lang <tag|auto>] [--seed-from <primary.md>] [--width N|∞] [--depth N|∞] [--rounds N|conv] [--out <dir>] [--glossary <path>] [--field <name|path>] [--no-grill] [--no-online]"
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
goals / constraints / context from the file. With
`--seed-from <primary.md>` (how `tree-chain` wires stage 2) a fresh
root may be omitted: the prior run's items enter as depth-1 seeds and
the preset derives its root fields from them
([`presets/design.md`](../presets/design.md) §2).

Preset details: [`presets/design.md`](../presets/design.md).
Engine spec: [`docs/ENGINE.md`](../docs/ENGINE.md).
