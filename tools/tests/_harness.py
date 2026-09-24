#!/usr/bin/env python3
"""Scaffolding the three script-style suites in this directory share.

Each suite is a plain script — CI runs `python tools/tests/test_x.py` — that
records diagnostics into a module-level list only its own `main()` reads.
Two things every suite needs identically live here, once, instead of as
three copies that could drift:

- **`sys.path` bootstrap.** `tools/` holds the modules under test and is
  deliberately NOT a package: `python tools/validate_plugin.py` works only
  because Python puts the script's own directory on `sys.path[0]`, and from
  `tools/tests/` that no longer happens. Importing this module first puts
  `tools/` on the path. Derived from `__file__`, never absolute.

- **`expose_to_pytest`.** pytest never calls `main()`, so a collected
  `test_*` used to return normally and pass unconditionally: injecting
  `root_kind: BOGUS` into a shipped preset still produced `13 passed` while
  the script runner correctly exited 1 — a green pytest run was evidence of
  nothing. Wrapping every `test_*` so it re-raises the failures *it* added
  (only those, so one broken check does not smear its diagnostic across
  later tests) makes the collected run mean what it says. A suite calls it
  after capturing its ordered `_TESTS` tuple, so the script runner keeps
  the plain, non-raising originals.
"""

from __future__ import annotations

import functools
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
REPO = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))


def expose_to_pytest(namespace: dict, failures: list[str]) -> None:
    """Rebind every `test_*` callable in `namespace` to a wrapper that raises
    `AssertionError` with whatever the call appended to `failures`."""
    def visible(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            before = len(failures)
            fn(*args, **kwargs)
            added = failures[before:]
            if added:
                raise AssertionError("\n".join(added))
        return wrapper

    for name, fn in list(namespace.items()):
        if name.startswith("test_") and callable(fn):
            namespace[name] = visible(fn)
