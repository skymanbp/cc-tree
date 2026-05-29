#!/usr/bin/env python3
"""Behavioral tests for the preset schema validator.

Proves the promise in docs/ENGINE.md §10-§11 and docs/presets.md §1 is
actually enforced (not just documented): the 4 shipped presets pass full
schema validation, and deliberately-broken presets are rejected.

Run with no arguments; exits non-zero on any test failure.
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path

import validate_plugin as vp
from _frontmatter import parse_frontmatter

REPO = Path(__file__).resolve().parent.parent

_failures: list[str] = []


def _validate_raises(name: str, text: str) -> bool:
    """Return True if validating the frontmatter `text` triggers vp.fail()."""
    fm = parse_frontmatter(text)
    if fm is None:
        return True  # no frontmatter is itself a rejection
    path = Path(f"{name}.md")
    with contextlib.redirect_stderr(io.StringIO()):
        try:
            vp.validate_preset_schema(path, fm)
        except SystemExit:
            return True
    return False


def expect_pass(label: str, text: str) -> None:
    if _validate_raises("test", text):
        _failures.append(f"EXPECTED PASS but was REJECTED: {label}")


def expect_fail(label: str, text: str) -> None:
    if not _validate_raises("test", text):
        _failures.append(f"EXPECTED FAIL but was ACCEPTED: {label}")


# A minimal, fully-valid preset frontmatter (name must be "test").
VALID = """---
name: test
description: A minimal valid preset.
root_kind: topic
subject_label: idea
verdict_enum:
  advances: A
  kept: K
  pruned: P
  blocked: B
convergence_metric: advances
score_dims:
  - {key: S, name: s, desc: "d"}
  - {key: N, name: n, desc: "d"}
  - {key: F, name: f, desc: "d"}
  - {key: K, name: k, desc: "d"}
  - {key: B, name: b, desc: "d"}
node_schema:
  - f1
  - f2
  - f3
  - f4
  - f5
  - f6
  - f7
  - f8
  - f9
  - f10
  - f11
  - f12
output_artifacts:
  primary: out.md
---
body
"""


def main() -> int:
    # --- Real shipped presets must pass full schema validation ---
    presets_dir = REPO / "presets"
    real = sorted(p for p in presets_dir.glob("*.md") if p.name != "README.md")
    if not real:
        _failures.append("no shipped presets found to test")
    for p in real:
        fm = parse_frontmatter(p.read_text(encoding="utf-8"))
        if fm is None:
            _failures.append(f"{p.name}: no frontmatter")
            continue
        with contextlib.redirect_stderr(io.StringIO()):
            try:
                vp.validate_preset_schema(p, fm)
            except SystemExit:  # pragma: no cover - failure path
                _failures.append(f"shipped preset REJECTED: {p.name}")

    # --- Sanity: the minimal template passes ---
    expect_pass("minimal valid template", VALID)

    # --- Broken presets must be rejected ---
    # 11 node_schema fields (drop f12).
    expect_fail("node_schema has 11 fields",
                VALID.replace("  - f12\n", "", 1))
    # 4 score_dims (drop the B dimension line).
    expect_fail("score_dims has 4 entries",
                VALID.replace('  - {key: B, name: b, desc: "d"}\n', "", 1))
    # score_dims entry missing desc.
    expect_fail("score_dims entry missing desc",
                VALID.replace('  - {key: S, name: s, desc: "d"}',
                              '  - {key: S, name: s}'))
    # verdict_enum missing the 'blocked' role.
    expect_fail("verdict_enum missing blocked role",
                VALID.replace("  blocked: B\n", "", 1))
    # convergence_metric not one of the verdict roles.
    expect_fail("convergence_metric not a verdict role",
                VALID.replace("convergence_metric: advances",
                              "convergence_metric: novelty_ratio"))
    # unknown root_kind.
    expect_fail("unknown root_kind",
                VALID.replace("root_kind: topic", "root_kind: bogus"))
    # output_artifacts without primary.
    expect_fail("output_artifacts missing primary",
                VALID.replace("output_artifacts:\n  primary: out.md",
                              "output_artifacts:\n  secondary: x.md"))
    # name mismatch (frontmatter name != file stem "test").
    expect_fail("name does not match file basename",
                VALID.replace("name: test", "name: wrongname"))

    if _failures:
        print("test_validate: FAILED")
        for f in _failures:
            print(f"  - {f}")
        return 1
    print("test_validate: all schema tests passed "
          f"({len(real)} shipped presets + 9 negative cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
