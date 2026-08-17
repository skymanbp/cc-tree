#!/usr/bin/env python3
"""Behavioral tests for the preset schema validator.

Proves the promise in docs/ENGINE.md §10-§11 and docs/presets.md §1 is
actually enforced (not just documented): the 4 shipped presets pass full
frontmatter-schema validation, and deliberately-broken presets are rejected
*for the right reason* — every negative case pins a diagnostic substring,
so a rejection caused by an unrelated rule cannot green a dead check.

Run with no arguments; exits non-zero on any test failure.
"""

from __future__ import annotations

import functools
import sys
from pathlib import Path

# tools/ holds the modules under test and is deliberately NOT a package: CI
# runs `python tools/validate_plugin.py`, which works only because Python puts
# the script's own directory on sys.path[0]. From tools/tests/ that no longer
# happens, so add tools/ explicitly. Derived from __file__, never absolute.
TOOLS = Path(__file__).resolve().parent.parent
REPO = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import validate_plugin as vp  # noqa: E402 — requires the sys.path setup above
from _frontmatter import (  # noqa: E402 — same
    FrontmatterError,
    parse_frontmatter,
    split_frontmatter,
)

_failures: list[str] = []
# Counted at call time, never hard-coded, so the summary line cannot claim
# more cases than the file actually runs.
_n_pass = 0
_n_fail = 0
_n_parser = 0
_n_shipped = 0


def _validate_error(name: str, text: str) -> str | None:
    """Validate `text` as preset frontmatter; return the failure message,
    or None if it validates cleanly."""
    try:
        fm = parse_frontmatter(text)
    except FrontmatterError as exc:
        return f"frontmatter: {exc}"
    if fm is None:
        return "no frontmatter"
    try:
        vp.validate_preset_schema(Path(f"{name}.md"), fm)
    except vp.ValidationError as exc:
        return str(exc)
    return None


def expect_pass(label: str, text: str) -> None:
    global _n_pass
    _n_pass += 1
    err = _validate_error("test", text)
    if err is not None:
        _failures.append(f"EXPECTED PASS but was REJECTED: {label}: {err}")


def expect_fail(label: str, text: str, want: str) -> None:
    """The text must be rejected AND the diagnostic must contain `want` —
    any-rejection-counts previously let an unrelated failure green a case."""
    global _n_fail
    _n_fail += 1
    err = _validate_error("test", text)
    if err is None:
        _failures.append(f"EXPECTED FAIL but was ACCEPTED: {label}")
    elif want not in err:
        _failures.append(
            f"WRONG DIAGNOSTIC: {label}: wanted {want!r} in {err!r}")


def expect_parsed(label: str, text: str, key: str, want) -> None:
    """Parser-level regression case: frontmatter `text` must parse and
    `key` must equal `want` exactly."""
    global _n_parser
    _n_parser += 1
    try:
        fm = parse_frontmatter(text)
    except FrontmatterError as exc:
        _failures.append(f"PARSER: {label}: unexpected FrontmatterError: {exc}")
        return
    got = None if fm is None else fm.get(key)
    if got != want:
        _failures.append(f"PARSER: {label}: {key}={got!r}, want {want!r}")


def expect_parse_error(label: str, text: str, want: str) -> None:
    """The parser itself must reject `text`, mentioning `want`."""
    global _n_parser
    _n_parser += 1
    try:
        fm = parse_frontmatter(text)
    except FrontmatterError as exc:
        if want not in str(exc):
            _failures.append(
                f"PARSER: {label}: wanted {want!r} in error {exc!r}")
        return
    _failures.append(f"PARSER: {label}: expected FrontmatterError, got {fm!r}")


def _replace_once(text: str, old: str, new: str) -> str:
    """`str.replace` that fails loudly when `old` is absent or ambiguous —
    a silent no-op replacement turns a mutation test into a duplicate of
    the positive case."""
    count = text.count(old)
    if count != 1:
        raise AssertionError(
            f"mutation target occurs {count} times (need exactly 1): {old!r}")
    return text.replace(old, new, 1)


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

FLOW_DIMS = (
    'score_dims:\n'
    '  - {key: S, name: s, desc: "d"}\n'
    '  - {key: N, name: n, desc: "d"}\n'
    '  - {key: F, name: f, desc: "d"}\n'
    '  - {key: K, name: k, desc: "d"}\n'
    '  - {key: B, name: b, desc: "d"}\n'
)


def test_shipped_presets() -> None:
    """Every shipped preset must pass full frontmatter-schema validation."""
    global _n_shipped
    presets_dir = REPO / "presets"
    real = sorted(p for p in presets_dir.glob("*.md") if p.name != "README.md")
    if not real:
        _failures.append("no shipped presets found to test")
    for p in real:
        # _validate_error validates against the synthetic path "test.md",
        # which would fail the name==basename rule for every real preset —
        # so run the validation directly against the real path.
        try:
            fm = parse_frontmatter(p.read_text(encoding="utf-8"))
        except FrontmatterError as exc:
            _failures.append(f"{p.name}: frontmatter: {exc}")
            continue
        if fm is None:
            _failures.append(f"{p.name}: no frontmatter")
            continue
        try:
            vp.validate_preset_schema(p, fm)
        except vp.ValidationError as exc:  # pragma: no cover - failure path
            _failures.append(f"shipped preset REJECTED: {p.name}: {exc}")
    # Recorded in a module counter rather than returned: a `test_*` function
    # that returns non-None raises PytestReturnNotNoneWarning, which pytest
    # has been escalating toward an error across releases.
    _n_shipped = len(real)


def test_schema_rejections() -> None:
    """Broken presets are rejected with the *matching* diagnostic."""
    expect_pass("minimal valid template", VALID)

    expect_fail("node_schema has 11 fields",
                _replace_once(VALID, "  - f12\n", ""),
                "node_schema must have exactly 12")
    expect_fail("score_dims has 4 entries",
                _replace_once(VALID, '  - {key: B, name: b, desc: "d"}\n', ""),
                "score_dims must have exactly 5")
    expect_fail("score_dims entry missing desc",
                _replace_once(VALID, '  - {key: S, name: s, desc: "d"}',
                              '  - {key: S, name: s}'),
                "score_dims[0].desc")
    expect_fail("verdict_enum missing blocked role",
                _replace_once(VALID, "  blocked: B\n", ""),
                "verdict_enum roles")
    expect_fail("convergence_metric not a verdict role",
                _replace_once(VALID, "convergence_metric: advances",
                              "convergence_metric: novelty_ratio"),
                "not in verdict_enum roles")
    expect_fail("unknown root_kind",
                _replace_once(VALID, "root_kind: topic", "root_kind: bogus"),
                "root_kind=")
    expect_fail("output_artifacts missing primary",
                _replace_once(VALID, "output_artifacts:\n  primary: out.md",
                              "output_artifacts:\n  secondary:\n    x: x.md"),
                "output_artifacts.primary")
    expect_fail("name does not match file basename",
                _replace_once(VALID, "name: test", "name: wrongname"),
                "!= expected 'test'")
    expect_fail("empty node_schema entry is rejected, not a crash",
                _replace_once(VALID, "  - f12\n", "  -\n"),
                "node_schema[11]")

    # Non-string values where the schema requires scalars: the parser can
    # produce nested collections, and str()-coercion used to accept them
    # (or crash on `dict in dict` for convergence_metric).
    expect_fail("nested subject_label",
                _replace_once(VALID, "subject_label: idea",
                              "subject_label:\n  nested: idea"),
                "subject_label must be a non-empty string")
    expect_fail("flow-map node_schema entry",
                _replace_once(VALID, "  - f1\n", "  - {bad: field}\n"),
                "node_schema[0] must be a non-empty string")
    expect_fail("nested output_artifacts.primary",
                _replace_once(VALID, "  primary: out.md",
                              "  primary:\n    nested: out.md"),
                "output_artifacts.primary must be a non-empty string")
    expect_fail("nested verdict label",
                _replace_once(VALID, "  advances: A",
                              "  advances:\n    nested: A"),
                "verdict_enum.advances must be a non-empty string")
    expect_fail("mapping-valued convergence_metric is rejected, not a crash",
                _replace_once(VALID, "convergence_metric: advances",
                              "convergence_metric:\n  nested: advances"),
                "convergence_metric must be a non-empty string")

    # Identifier discipline: distinct keys/fields/labels, 1-3 letter keys,
    # out-dir-confined artifact filenames.
    expect_fail("duplicate score key",
                _replace_once(VALID, "{key: N, name: n", "{key: S, name: n"),
                "score_dims keys must be distinct")
    expect_fail("overlong score key",
                _replace_once(VALID, "{key: S,", "{key: TOOLONG,"),
                "must be 1-3 letters")
    expect_fail("duplicate node_schema fields",
                _replace_once(VALID, "  - f12\n", "  - f11\n"),
                "node_schema field names must be distinct")
    expect_fail("duplicate verdict labels",
                _replace_once(VALID, "  kept: K", "  kept: A"),
                "verdict_enum labels must be distinct")
    expect_fail("path-escaping primary artifact",
                _replace_once(VALID, "  primary: out.md",
                              "  primary: ../../escape.md"),
                "bare *.md filename")
    expect_fail("path-escaping secondary artifact",
                _replace_once(VALID, "output_artifacts:\n  primary: out.md",
                              "output_artifacts:\n  primary: out.md\n"
                              "  secondary:\n    evil: C:/absolute.md"),
                "output_artifacts.secondary.evil")
    expect_pass("well-formed secondary artifacts",
                _replace_once(VALID, "output_artifacts:\n  primary: out.md",
                              "output_artifacts:\n  primary: out.md\n"
                              "  secondary:\n    rejected: rejected.md"))


def test_frontmatter_regressions() -> None:
    """Parser-level positive cases: subset constructs must parse exactly."""
    expect_pass("quoted name scalar is unquoted before validation",
                _replace_once(VALID, "name: test", 'name: "test"'))
    expect_parsed("double-quoted scalar", '---\nname: "attack"\n---\nx\n',
                  "name", "attack")
    expect_parsed("apostrophe before # keeps comment stripped",
                  "---\nsubject_label: reviewer's take  # note\n---\nx\n",
                  "subject_label", "reviewer's take")
    expect_pass("flow-map score_dims entry tolerates trailing comment",
                _replace_once(VALID, '  - {key: S, name: s, desc: "d"}',
                              '  - {key: S, name: s, desc: "d"}  # dim S'))
    expect_parsed("hash inside quoted desc survives",
                  '---\ndims:\n  - {key: S, name: s, desc: "a # b"}\n---\nx\n',
                  "dims", [{"key": "S", "name": "s", "desc": "a # b"}])
    expect_parsed("block-map list items parse to dicts",
                  "---\ndims:\n  - key: S\n    name: s\n    desc: d\n"
                  "  - key: N\n    name: n\n    desc: d2\n---\nx\n",
                  "dims", [{"key": "S", "name": "s", "desc": "d"},
                           {"key": "N", "name": "n", "desc": "d2"}])
    BLOCK_DIMS = (
        "score_dims:\n"
        "  - key: S\n    name: s\n    desc: d\n"
        "  - key: N\n    name: n\n    desc: d\n"
        "  - key: F\n    name: f\n    desc: d\n"
        "  - key: K\n    name: k\n    desc: d\n"
        "  - key: B\n    name: b\n    desc: d\n"
    )
    expect_pass("block-map score_dims validates like flow-map",
                _replace_once(VALID, FLOW_DIMS, BLOCK_DIMS))
    expect_parsed("bare `-` list entry parses to an empty string",
                  "---\nl:\n  -\n  - real\n---\nx\n", "l", ["", "real"])
    expect_parsed("closing --- at EOF without trailing newline",
                  "---\nname: test\n---", "name", "test")

    # 2026-08 strictness sweep: constructs the parser previously mangled.
    expect_parsed("comment after a collection key keeps its children",
                  "---\nouter: # note\n  child: value\n---\nx\n",
                  "outer", {"child": "value"})
    expect_parsed("comment after a block-scalar marker keeps the block",
                  "---\nt: | # note\n  alpha\n  beta\n---\nx\n",
                  "t", "alpha\nbeta")
    expect_parsed("one-key block-map list items parse to dicts",
                  "---\nl:\n  - key: S\n  - key: N\n---\nx\n",
                  "l", [{"key": "S"}, {"key": "N"}])
    expect_parsed("inline flow map as a value parses to a dict",
                  "---\nve: {advances: A, kept: K}\n---\nx\n",
                  "ve", {"advances": "A", "kept": "K"})
    expect_pass("inline flow-map verdict_enum validates like the block form",
                _replace_once(VALID,
                              "verdict_enum:\n  advances: A\n  kept: K\n"
                              "  pruned: P\n  blocked: B",
                              "verdict_enum: {advances: A, kept: K, "
                              "pruned: P, blocked: B}"))
    expect_parsed("UTF-8 BOM before the opening --- is tolerated",
                  "\ufeff---\nname: test\n---\nx\n", "name", "test")

    global _n_parser
    _n_parser += 1
    _, body = split_frontmatter("---\nname: test\n---\n\n\n  body\n")
    if body != "\n\n  body\n":
        _failures.append(
            f"PARSER: body must keep its leading blank lines, got {body!r}")


def test_parser_rejections() -> None:
    """Out-of-subset constructs raise instead of silently recovering."""
    expect_parse_error("duplicate key",
                       "---\nname: a\nname: b\n---\nx", "duplicate key")
    expect_parse_error("junk non-mapping line",
                       "---\nname: a\nJUNK LINE\n---\nx",
                       "expected 'key: value'")
    expect_parse_error("misindented map line",
                       "---\nouter:\n    child: v\n  stray: x\n---\nx",
                       "misindented")
    expect_parse_error("sequence indicator without space",
                       "---\nl:\n  -one\n---\nx", "list item")
    expect_parse_error("text after flow map",
                       "---\nd:\n  - {key: S} GARBAGE\n---\nx",
                       "unexpected text after flow map")
    expect_parse_error("flow-map entry without a colon",
                       "---\nd:\n  - {key: S, JUNK}\n---\nx",
                       "not 'key: value'")
    expect_parse_error("unbalanced flow map",
                       "---\nd:\n  - {key: S\n---\nx", "unbalanced")


def test_heading_slugs() -> None:
    """Anchor slugs must include GitHub's -N suffixes for repeats."""
    global _n_parser
    _n_parser += 1
    got = vp._heading_slugs("## Repeat\n## Repeat\n## Other\n")
    want = {"repeat", "repeat-1", "other"}
    if got != want:
        _failures.append(f"SLUGS: got {sorted(got)}, want {sorted(want)}")


def test_section_reference_patterns() -> None:
    """Guards _check_section_refs: the check is only as good as its
    harvest. Pin the shapes that must stay harvestable and the reference
    shapes that must stay matchable."""
    valid = set()
    for src in vp._section_id_sources():
        for _level, heading in vp._headings(src.read_text(encoding="utf-8")):
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


# Ordered exactly as `main()` runs them, captured BEFORE the pytest wrapping
# below so the script runner keeps the plain, non-raising originals.
_TESTS = (
    test_shipped_presets,
    test_schema_rejections,
    test_frontmatter_regressions,
    test_parser_rejections,
    test_heading_slugs,
    test_section_reference_patterns,
)


def _pytest_visible(fn):
    """Re-raise, as an assertion, whatever `fn` recorded in `_failures`.

    Every function above reports by appending to a module-level list that only
    `main()` inspects. pytest never calls `main()`, so each collected `test_*`
    returned normally and passed unconditionally: injecting `root_kind: BOGUS`
    into a shipped preset still produced `13 passed` from `pytest` while
    `python tools/tests/test_validate.py` correctly exited 1. A green pytest
    run was therefore evidence of nothing.

    Only the failures this call added are raised, so one broken check does not
    smear its diagnostic across every later test.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        before = len(_failures)
        fn(*args, **kwargs)
        added = _failures[before:]
        if added:
            raise AssertionError("\n".join(added))
    return wrapper


for _name, _fn in list(globals().items()):
    if _name.startswith("test_") and callable(_fn):
        globals()[_name] = _pytest_visible(_fn)


def main() -> int:
    for test in _TESTS:
        test()

    if _failures:
        print("test_validate: FAILED")
        for f in _failures:
            print(f"  - {f}")
        return 1
    print("test_validate: all schema tests passed "
          f"({_n_shipped} shipped presets + {_n_pass} positive + "
          f"{_n_fail} negative + {_n_parser} parser cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
