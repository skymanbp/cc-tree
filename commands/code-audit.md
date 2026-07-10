---
description: Adversarial code review tree. Wraps `/cc-tree:tree` with the code-audit preset preselected — finds security / performance / correctness / contract findings a static linter would miss. Every finding carries `file:line` evidence + threat-model context + proposed_fix; hard-banned against NEEDS-MORE-INFO deferrals.
argument-hint: "<file_or_directory_path> [--width N|∞] [--depth N|∞] [--rounds N|conv] [--out <dir>] [--glossary <path>] [--field <name|path>] [--no-online]"
---

Invoke the `tree` skill with the code-audit preset. The default
output directory is `code-audit-out/<UTCdate>__<target-slug>/`
(override with `--out`).

Run:

```
/cc-tree:tree $ARGUMENTS --preset code-audit
```

If `$ARGUMENTS` doesn't include a path, the engine will report
`EARLY_STOP=root_unparseable` — point it at a file or directory.

Preset details: [`presets/code-audit.md`](../presets/code-audit.md).
Engine spec: [`docs/ENGINE.md`](../docs/ENGINE.md).
