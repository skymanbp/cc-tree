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
# Counted at call time so the summary line can never drift from the
# actual number of cases again (v0.2.0 shipped claiming "9 negative
# cases" while only 8 expect_fail calls existed).
_n_pass = 0
_n_fail = 0
_n_parser = 0


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
    global _n_pass
    _n_pass += 1
    if _validate_raises("test", text):
        _failures.append(f"EXPECTED PASS but was REJECTED: {label}")


def expect_fail(label: str, text: str) -> None:
    global _n_fail
    _n_fail += 1
    if not _validate_raises("test", text):
        _failures.append(f"EXPECTED FAIL but was ACCEPTED: {label}")


def expect_parsed(label: str, text: str, key: str, want) -> None:
    """Parser-level regression case: frontmatter `text` must parse and
    `key` must equal `want` exactly."""
    global _n_parser
    _n_parser += 1
    fm = parse_frontmatter(text)
    got = None if fm is None else fm.get(key)
    if got != want:
        _failures.append(f"PARSER: {label}: {key}={got!r}, want {want!r}")


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

    # --- Parser regression cases (bugs fixed after v0.2.0) ---
    # Quoted scalar values must be unquoted (was: name kept its quotes and
    # spuriously failed the name==basename check).
    expect_pass("quoted name scalar is unquoted before validation",
                VALID.replace("name: test", 'name: "test"'))
    expect_parsed("double-quoted scalar", '---\nname: "attack"\n---\nx\n',
                  "name", "attack")
    # A prose apostrophe must not swallow a trailing comment (was: the
    # apostrophe toggled quote-tracking and the comment stayed in-value).
    expect_parsed("apostrophe before # keeps comment stripped",
                  "---\nsubject_label: reviewer's take  # note\n---\nx\n",
                  "subject_label", "reviewer's take")
    # A flow-map list item with a trailing comment must still parse (was:
    # degenerated to {'_raw': ...} because the raw item no longer ended
    # with '}').
    expect_pass("flow-map score_dims entry tolerates trailing comment",
                VALID.replace('  - {key: S, name: s, desc: "d"}',
                              '  - {key: S, name: s, desc: "d"}  # dim S'))
    # '#' inside a quoted flow-map value is content, not a comment.
    expect_parsed("hash inside quoted desc survives",
                  '---\ndims:\n  - {key: S, name: s, desc: "a # b"}\n---\nx\n',
                  "dims", [{"key": "S", "name": "s", "desc": "a # b"}])
    # Standard YAML block-map list items must parse to dicts (was: the
    # continuation lines were silently dropped and each item degraded to
    # the scalar string "key: S").
    expect_parsed("block-map list items parse to dicts",
                  "---\ndims:\n  - key: S\n    name: s\n    desc: d\n"
                  "  - key: N\n    name: n\n    desc: d2\n---\nx\n",
                  "dims", [{"key": "S", "name": "s", "desc": "d"},
                           {"key": "N", "name": "n", "desc": "d2"}])
    # End-to-end: a preset whose score_dims use block-map style passes
    # full schema validation, same as the flow-map style.
    BLOCK_DIMS = (
        "score_dims:\n"
        "  - key: S\n    name: s\n    desc: d\n"
        "  - key: N\n    name: n\n    desc: d\n"
        "  - key: F\n    name: f\n    desc: d\n"
        "  - key: K\n    name: k\n    desc: d\n"
        "  - key: B\n    name: b\n    desc: d\n"
    )
    FLOW_DIMS = (
        'score_dims:\n'
        '  - {key: S, name: s, desc: "d"}\n'
        '  - {key: N, name: n, desc: "d"}\n'
        '  - {key: F, name: f, desc: "d"}\n'
        '  - {key: K, name: k, desc: "d"}\n'
        '  - {key: B, name: b, desc: "d"}\n'
    )
    expect_pass("block-map score_dims validates like flow-map",
                VALID.replace(FLOW_DIMS, BLOCK_DIMS))
    # An empty list entry must parse to "" rather than raising IndexError:
    # `_strip_comment` used `s[:1] in "\"'"`, and `"" in "\"'"` is True, so a
    # bare `-` crashed the whole validator with a traceback instead of the
    # clean "node_schema[i] is empty" failure below.
    expect_parsed("bare `-` list entry parses to an empty string",
                  "---\nl:\n  -\n  - real\n---\nx\n", "l", ["", "real"])
    expect_fail("empty node_schema entry is rejected, not a crash",
                VALID.replace("  - f12\n", "  -\n"))
    # Frontmatter whose closing `---` is the last byte of the file (no
    # trailing newline) is still frontmatter.
    expect_parsed("closing --- at EOF without trailing newline",
                  "---\nname: test\n---", "name", "test")

    # --- Section-reference namespace (guards _check_section_refs) ---
    # The check is only as good as its harvest: if the heading style of
    # ENGINE.md/presets ever changes, `valid` silently shrinks and dead
    # refs stop being caught. Pin the shapes that must stay harvestable
    # and the reference shapes that must stay matchable.
    valid = set()
    for src in vp._section_id_sources():
        for _, heading in vp._HEADING_RE.findall(src.read_text(encoding="utf-8")):
            m = vp._SECTION_ID_RE.match(heading.strip())
            if m:
                valid.add(m.group(1).upper())
    for expected in ("0.5", "1.0", "2.0", "2.A", "2.B", "3.A", "3.L", "3.X",
                     "5.2", "6.2", "7.4", "8.1", "F1", "F4", "F7", "F8",
                     "9", "10", "11"):
        if expected not in valid:
            _failures.append(
                f"SECTION-IDS: §{expected} is no longer harvestable from "
                "headings; _check_section_refs would stop catching it")
    for dead in ("0.4", "0.7", "0.8", "2.4", "6.6"):
        if dead in valid:
            _failures.append(
                f"SECTION-IDS: §{dead} unexpectedly resolves; the 2026-08 "
                "renumbering sweep assumed it does not exist")
    refs = set(vp._SECTION_REF_RE.findall("see §F8, §3.A, § 6.2 and §10 now"))
    if refs != {"F8", "3.A", "6.2", "10"}:
        _failures.append(f"SECTION-REFS: reference scan returned {sorted(refs)}")

    if _failures:
        print("test_validate: FAILED")
        for f in _failures:
            print(f"  - {f}")
        return 1
    print("test_validate: all schema tests passed "
          f"({len(real)} shipped presets + {_n_pass} positive + "
          f"{_n_fail} negative + {_n_parser} parser cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
