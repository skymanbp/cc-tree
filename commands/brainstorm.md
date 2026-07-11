---
description: Divergent radial-tree ideation. Wraps `/cc-tree:tree` with the brainstorm preset preselected — exhaustive exploration of research directions or problem-solving paths, hard-banned against `future-work / TODO / NEEDS-MORE-INFO` deferred leaves. 中文触发：发散头脑风暴、穷尽探索研究方向或解题路径。
argument-hint: "[topic] [--lang <tag|auto>] [--width N|∞] [--depth N|∞] [--rounds N|conv] [--out <dir>] [--glossary <path>] [--field <name|path>] [--no-grill] [--no-online]"
---

Invoke the `tree` skill with the brainstorm preset. The default
output directory is `brainstorm-out/<UTCdate>__<topic-slug>/` (override
with `--out`).

Run:

```
/cc-tree:tree $ARGUMENTS --preset brainstorm
```

If `$ARGUMENTS` is empty, the preset's research mode (§2.A) infers
a topic from the current project state (`CLAUDE.md` / `README.md` /
recent `git log`).

Preset details: [`presets/brainstorm.md`](../presets/brainstorm.md).
Engine spec: [`docs/ENGINE.md`](../docs/ENGINE.md).
