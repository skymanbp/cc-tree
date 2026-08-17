#!/usr/bin/env python3
"""Behavioral tests for the seven top-level check groups in validate_plugin.

Why this file exists: a coverage trace of the other two suites showed that
17 of `validate_plugin.py`'s 35 functions were never entered — including
`check_manifests`, `check_crossrefs`, `check_i18n`, every cross-file
sub-check, and `main` itself. Everything those functions enforce could have
been reduced to a no-op (a bad regex, a renamed directory, an over-eager
skip rule) with the whole CI suite still printing OK. The shipped repository
passing is not evidence that a check *works*; it is evidence that the
repository is clean.

So each check is exercised against a synthetic repository in a temporary
directory: once in a state that must pass, then once per defect class in a
state that must fail *with the matching diagnostic*. Pinning the diagnostic
is what stops an unrelated rejection from greening a dead check.

Run with no arguments; exits non-zero on any test failure.
"""

from __future__ import annotations

import contextlib
import functools
import io
import json
import re
import sys
import tempfile
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
from _i18n import (  # noqa: E402 — same
    chinese_banner,
    english_banner,
    source_digest,
)

_failures: list[str] = []
_n_pass = 0
_n_fail = 0


# --- synthetic repository ---------------------------------------------------
# Small enough to read in one screen, complete enough that all seven check
# groups pass on it. Every mutation below starts from this state, so a
# rejection can only come from the mutation itself.

VERSION = "0.1.0"

PLUGIN_JSON = {
    "name": "fixture",
    "version": VERSION,
    "description": "Fixture plugin used by the validator's own tests.",
    "author": {"name": "fixture"},
    "homepage": "https://example.invalid/fixture",
    "repository": "https://example.invalid/fixture",
    "license": "MIT",
    "keywords": ["fixture", "test"],
}

PRESET = """---
name: attack
description: Fixture preset.
root_kind: artifact
subject_label: critique
verdict_enum:
  advances: CONFIRMED
  kept:     MARGINAL
  pruned:   REFUTED
  blocked:  INCOMPLETE_FORBIDDEN
convergence_metric: advances
score_dims:
  - {key: S, name: severity, desc: "d"}
  - {key: P, name: specificity, desc: "d"}
  - {key: R, name: reproducibility, desc: "d"}
  - {key: F, name: fixability, desc: "d"}
  - {key: B, name: fanout, desc: "d"}
node_schema:
  - critique_statement
  - parent_framing
  - artifact_position
  - evidence
  - assumptions
  - predictions
  - artifact_defense
  - alternative_interpretations
  - proposed_fix
  - external_check
  - sub_critique_potential
  - verdict_provisional
output_artifacts:
  primary: confirmed.md
  secondary:
    refuted: refuted.md
---

## §2.A Baseline (fixture recipe)

Read the artifact in full, then build the root node from real evidence.
"""

SKILL = """---
name: tree
description: Fixture skill.
argument-hint: "<root> --preset <name> [--lang <tag|auto>]"
---

# tree — fixture skill

## 1. Invocation

Pass `--lang <tag|auto>` to pick the output language, and `--preset <name>`
to pick the recipe. See §0.5 for the forbidden patterns and §6 for the
convergence test; the preset supplies §2.A.
"""

COMMAND = """---
description: Fixture command wrapper.
argument-hint: "<file> [--lang <tag|auto>] [--focus <section>]"
---

Run the fixture preset. Use `--lang <tag|auto>` for output language and
`--focus <section>` to narrow the review. Preset:
[`presets/attack.md`](../presets/attack.md).
"""

FIELD_PROFILE = """---
field: physics
description: Fixture field profile.
---

# `physics` field profile

## Reviewer concerns — feeds §0.5

- Unit consistency.

## Field consensuses

- Gaussian likelihoods — breaks at low signal-to-noise.

## Common failure modes

- An off-by-one in the binning.

## Evidence bar

- Strong: an independent replication.
- Weak: a single unblinded run.
"""

SAMPLE = "# Claim\n\n1. First line of the toy artifact.\n2. Second line.\n"

EXAMPLE_NOTES = """# Fixture example notes

The critique cites `sample-claim.md:3` and stays inside the file, and links
to [`sample-claim.md`](sample-claim.md). Prose that merely *shows* link
syntax, like `](nowhere.md#frag)`, is quoted code and must not be resolved
as a link.
"""

ENGINE_BODY = """
# Engine contract

## 0.5 Forbidden patterns

Every external assertion is verified in the same turn. A run that finishes
reports CONVERGED and writes tree.md next to its other deliverables. The
`root_kind` value `topic` is a machine token and is never translated, in
prose or inside the fence below. This paragraph is deliberately substantive
so that section-level translation coverage is exercised rather than passing
on headings alone.

```json
{"root_kind": "topic", "output_language": "zh"}
```

## 6. Convergence

All six conditions hold simultaneously before the engine may report
CONVERGED. The `advances` verdict role stays English even inside inline
code, and the `--lang` flag selects only the human-readable prose. This
section is likewise substantive so the coverage floor has something real to
measure against.
"""

ENGINE_ZH_BODY = """
# 引擎契约

## 0.5 禁止模式

每一条外部断言都在同一轮内被验证。一次跑完的运行会报告 CONVERGED，
并在其他交付物旁边写出 tree.md。`root_kind` 的取值 `topic` 是机器标记，
无论在散文里还是在下面这个代码块中都不会被翻译。本段刻意写得足够充实，
以便逐节翻译覆盖率能够被真正检验，而不是仅凭标题就通过。

```json
{"root_kind": "topic", "output_language": "zh"}
```

## 6. 收敛

引擎必须在六个条件同时成立时才能报告 CONVERGED。`advances` 判定角色
即使出现在行内代码中也保持英文，而 `--lang` 标志只选择人类可读的散文部分。
本节同样写得充实，好让覆盖率下限有真实的内容可以衡量。
"""

LANGUAGES = {
    "schema_version": 1,
    "canonical_language": "en",
    "default_output_language": "en",
    "documentation_languages": ["en", "zh"],
    "pairs": [{
        "canonical": "docs/ENGINE.md",
        "translations": {"zh": "docs/ENGINE.zh.md"},
    }],
    "canonical_only": [
        {"path": "CHANGELOG.md", "reason": "history, English only"},
        {"path": "skills/**/*.md", "reason": "runtime skill, English only"},
        {"path": "commands/*.md", "reason": "wrappers, English only"},
        {"path": "presets/*.md", "reason": "preset schemas, English only"},
        {"path": "field-profiles/*.md", "reason": "profiles, English only"},
        {"path": "examples/**/*.md", "reason": "fixtures, English only"},
    ],
    "required_runtime_flags": ["--lang"],
    "fixed_machine_tokens": ["CONVERGED", "tree.md"],
}


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    # newline="" keeps the bytes exactly as written; the digest is computed on
    # LF-normalized text, so a platform-translated newline would not break the
    # digest but would silently change what the fence-identity check compares.
    path.write_text(text, encoding="utf-8", newline="")


def _build(root: Path) -> Path:
    """Materialize a repository that passes all seven check groups."""
    engine_en = f"{english_banner('docs/ENGINE.md', 'docs/ENGINE.zh.md')}\n{ENGINE_BODY}"
    engine_zh = (
        f"{chinese_banner('docs/ENGINE.md', 'docs/ENGINE.zh.md')}\n"
        f"<!-- i18n-source-sha256: {source_digest(engine_en)} -->\n"
        f"{ENGINE_ZH_BODY}"
    )
    market = {
        "name": "fixture",
        "owner": {"name": "fixture"},
        "metadata": {"description": "Fixture marketplace.", "version": VERSION},
        "plugins": [dict(PLUGIN_JSON, source="./")],
    }
    _write(root, ".claude-plugin/plugin.json", json.dumps(PLUGIN_JSON, indent=2))
    _write(root, ".claude-plugin/marketplace.json", json.dumps(market, indent=2))
    _write(root, "CHANGELOG.md", f"# Changelog\n\n## v{VERSION}\n\nFirst fixture release.\n")
    _write(root, "docs/languages.json", json.dumps(LANGUAGES, indent=2))
    _write(root, "docs/ENGINE.md", engine_en)
    _write(root, "docs/ENGINE.zh.md", engine_zh)
    _write(root, "skills/tree/SKILL.md", SKILL)
    _write(root, "commands/attack.md", COMMAND)
    _write(root, "presets/attack.md", PRESET)
    _write(root, "field-profiles/physics.md", FIELD_PROFILE)
    _write(root, "examples/attack/sample-claim.md", SAMPLE)
    _write(root, "examples/attack/notes.md", EXAMPLE_NOTES)
    _write(root, "tools/helper.py", "VALUE = 1\n")
    return root


_DIGEST_RE = re.compile(r"(i18n-source-sha256:\s*)[0-9a-f]{64}")


def _refresh_digest(root: Path) -> None:
    """Recompute the translation digest after an English-side mutation, so a
    test aimed at some other check is not rejected by a stale digest instead
    of by the defect it was written for."""
    en = (root / "docs" / "ENGINE.md").read_text(encoding="utf-8")
    zh = (root / "docs" / "ENGINE.zh.md").read_text(encoding="utf-8")
    zh = _DIGEST_RE.sub(lambda m: m.group(1) + source_digest(en), zh, count=1)
    _write(root, "docs/ENGINE.zh.md", zh)


# The seven groups, in `main()`'s order. `test_main_group_list_is_complete`
# separately proves this list has not fallen behind the module.
_GROUPS = (
    "check_manifests", "check_skills", "check_presets", "check_commands",
    "check_tools_syntax", "check_crossrefs", "check_i18n",
)


def _run_checks(root: Path) -> str | None:
    """Run every check group against `root`; return the first failure message,
    or None when all pass.

    `vp.REPO` is a module global that every check reads at CALL time, so
    rebinding it redirects all seven at once. It is restored in a `finally`
    because a leaked fixture path would make every later test — and the real
    validator run in the same process — silently validate a deleted temp
    directory.
    """
    original = vp.REPO
    vp.REPO = root
    try:
        for name in _GROUPS:
            try:
                getattr(vp, name)()
            except vp.ValidationError as exc:
                return str(exc)
        return None
    finally:
        vp.REPO = original


def expect_clean(label: str, mutate=None) -> None:
    """The fixture (optionally mutated) must pass every check group."""
    global _n_pass
    _n_pass += 1
    with tempfile.TemporaryDirectory() as tmp:
        root = _build(Path(tmp))
        if mutate is not None:
            mutate(root)
        err = _run_checks(root)
        if err is not None:
            _failures.append(f"EXPECTED CLEAN but was REJECTED: {label}: {err}")


def expect_reject(label: str, mutate, want: str) -> None:
    """The mutated fixture must be rejected AND the diagnostic must contain
    `want` — any-rejection-counts would let an unrelated failure green a
    check that no longer works."""
    global _n_fail
    _n_fail += 1
    with tempfile.TemporaryDirectory() as tmp:
        root = _build(Path(tmp))
        mutate(root)
        err = _run_checks(root)
        if err is None:
            _failures.append(f"EXPECTED REJECT but was ACCEPTED: {label}")
        elif want not in err:
            _failures.append(
                f"WRONG DIAGNOSTIC: {label}: wanted {want!r} in {err!r}")


def _edit(root: Path, relative: str, old: str, new: str) -> None:
    path = root / relative
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise AssertionError(
            f"mutation target occurs {text.count(old)} times in {relative} "
            f"(need exactly 1): {old!r}")
    _write(root, relative, text.replace(old, new, 1))


def _patch_json(root: Path, relative: str, mutate) -> None:
    path = root / relative
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    _write(root, relative, json.dumps(data, indent=2))


# --- tests ------------------------------------------------------------------


def test_fixture_is_clean() -> None:
    """The unmutated fixture passes all seven groups. Without this, every
    negative case below could be passing for the wrong reason."""
    expect_clean("unmutated fixture")


def test_manifests() -> None:
    """check_manifests: version identity, metadata parity, changelog section."""
    expect_reject(
        "plugin.json is not valid JSON",
        lambda r: _write(r, ".claude-plugin/plugin.json", "{not json"),
        "is not valid JSON")
    expect_reject(
        "plugin.json top level is not an object",
        lambda r: _write(r, ".claude-plugin/plugin.json", "[]"),
        "top level must be a JSON object")
    expect_reject(
        "plugin.json missing description",
        lambda r: _patch_json(r, ".claude-plugin/plugin.json",
                              lambda d: d.pop("description")),
        "'description' must be a non-empty string")
    expect_reject(
        "marketplace metadata.version drifts",
        lambda r: _patch_json(r, ".claude-plugin/marketplace.json",
                              lambda d: d["metadata"].update(version="9.9.9")),
        "metadata.version")
    expect_reject(
        "marketplace plugins[].version drifts",
        lambda r: _patch_json(r, ".claude-plugin/marketplace.json",
                              lambda d: d["plugins"][0].update(version="9.9.9")),
        "plugins[].version")
    expect_reject(
        "marketplace has no entry for the plugin",
        lambda r: _patch_json(r, ".claude-plugin/marketplace.json",
                              lambda d: d["plugins"][0].update(name="other")),
        "has no entry named")
    expect_reject(
        "keywords drift between the two manifests",
        lambda r: _patch_json(r, ".claude-plugin/marketplace.json",
                              lambda d: d["plugins"][0]["keywords"].append("extra")),
        "plugins[].keywords != plugin.json keywords")
    expect_reject(
        "description drifts between the two manifests",
        lambda r: _patch_json(r, ".claude-plugin/marketplace.json",
                              lambda d: d["plugins"][0].update(description="other")),
        "plugins[].description != plugin.json description")
    expect_reject(
        "CHANGELOG has no section for the declared version",
        lambda r: _edit(r, "CHANGELOG.md", f"## v{VERSION}", "## v9.9.9"),
        f"no '## v{VERSION}' section")
    expect_reject(
        "CHANGELOG.md is missing entirely",
        lambda r: (r / "CHANGELOG.md").unlink(),
        "CHANGELOG.md")
    # A longer version must not satisfy the prefix: `## v0.1.0-rc1` is not
    # `## v0.1.0`, which a bare `startswith` would have accepted.
    expect_reject(
        "a longer version string does not satisfy the changelog gate",
        lambda r: _edit(r, "CHANGELOG.md", f"## v{VERSION}", f"## v{VERSION}.9"),
        f"no '## v{VERSION}' section")


def test_skills() -> None:
    """check_skills + _check_md_frontmatter + _read_frontmatter."""
    expect_reject(
        "skills/ directory missing",
        lambda r: ((r / "skills" / "tree" / "SKILL.md").unlink(),
                   (r / "skills" / "tree").rmdir(), (r / "skills").rmdir()),
        "missing")
    expect_reject(
        "SKILL.md absent from a skill directory",
        lambda r: (r / "skills" / "tree" / "SKILL.md").unlink(),
        "SKILL.md missing")
    expect_reject(
        "SKILL.md frontmatter name != directory name",
        lambda r: _edit(r, "skills/tree/SKILL.md", "name: tree", "name: other"),
        "!= expected 'tree'")
    expect_reject(
        "SKILL.md has no frontmatter at all",
        lambda r: _write(r, "skills/tree/SKILL.md", "# no frontmatter\n"),
        "no YAML frontmatter")
    expect_reject(
        "SKILL.md frontmatter is malformed",
        lambda r: _edit(r, "skills/tree/SKILL.md",
                        "name: tree", "name: tree\nname: tree"),
        "duplicate key")


def test_presets_and_commands() -> None:
    """check_presets, check_commands, and the wrapper-parity rule."""
    expect_reject(
        "preset frontmatter violates the schema",
        lambda r: _edit(r, "presets/attack.md", "  - verdict_provisional\n", ""),
        "node_schema must have exactly 12")
    expect_reject(
        "presets/ exists but holds no preset files",
        lambda r: (r / "presets" / "attack.md").unlink(),
        "no preset .md files")
    expect_reject(
        "a preset ships without its command wrapper",
        lambda r: (r / "commands" / "attack.md").unlink(),
        "has no command wrapper")
    expect_reject(
        "command frontmatter missing description",
        lambda r: _edit(r, "commands/attack.md",
                        "description: Fixture command wrapper.\n", ""),
        "missing 'description:'")
    expect_reject(
        "command advertises a flag it never documents",
        lambda r: _edit(r, "commands/attack.md",
                        "[--focus <section>]", "[--focus <section>] [--undocumented]"),
        "--undocumented")
    expect_reject(
        "command omits a required common flag",
        lambda r: _edit(r, "commands/attack.md",
                        '"<file> [--lang <tag|auto>] [--focus <section>]"',
                        '"<file> [--focus <section>]"'),
        "omits required common flag --lang")
    # An extra command with no like-named preset is legitimate (tree-chain).
    expect_clean(
        "an extra command without a preset is allowed",
        lambda r: _write(r, "commands/extra.md",
                         "---\ndescription: Extra wrapper.\n"
                         'argument-hint: "<root> [--lang <tag|auto>]"\n---\n'
                         "Uses `--lang <tag|auto>`.\n"))


def test_tools_syntax() -> None:
    """check_tools_syntax, including the recursive walk into tools/tests/."""
    expect_reject(
        "a tools/ file does not parse",
        lambda r: _write(r, "tools/helper.py", "def broken(:\n"),
        "SyntaxError")
    expect_reject(
        "a file in a tools/ SUBdirectory does not parse",
        lambda r: _write(r, "tools/tests/broken.py", "def broken(:\n"),
        "SyntaxError")
    expect_reject(
        "tools/ holds no Python at all",
        lambda r: (r / "tools" / "helper.py").unlink(),
        "no .py tools")
    # Generated directories must stay invisible: this is the defect that made
    # `pytest && validate_plugin.py` fail on .pytest_cache/README.md.
    expect_clean(
        "dot-directories under tools/ are skipped",
        lambda r: (_write(r, "tools/.pytest_cache/README.md", "# cache\n"),
                   _write(r, "tools/.pytest_cache/broken.py", "def broken(:\n")))


def test_crossrefs() -> None:
    """check_crossrefs and each of its five sub-checks."""
    expect_reject(
        "a relative link with no #anchor points at a missing file",
        lambda r: _edit(r, "commands/attack.md",
                        "(../presets/attack.md)", "(../presets/gone.md)"),
        "link target missing")
    expect_reject(
        "an anchored link points at a heading that does not exist",
        lambda r: _edit(r, "commands/attack.md",
                        "(../presets/attack.md)", "(../presets/attack.md#nope)"),
        "dead anchor")
    expect_reject(
        "an example citation runs past the end of its target",
        lambda r: _edit(r, "examples/attack/notes.md",
                        "`sample-claim.md:3`", "`sample-claim.md:999`"),
        "out of bounds")
    expect_reject(
        "a field profile's `field:` does not match its basename",
        lambda r: _edit(r, "field-profiles/physics.md",
                        "field: physics", "field: other"),
        "!= 'physics'"),
    expect_reject(
        "a field profile is missing a required section",
        lambda r: _edit(r, "field-profiles/physics.md",
                        "## Evidence bar", "## Evidence"),
        "missing required level-2 section")
    expect_reject(
        "a field profile section is at the wrong heading level",
        lambda r: _edit(r, "field-profiles/physics.md",
                        "## Common failure modes", "### Common failure modes"),
        "missing required level-2 section")
    expect_reject(
        "a §N prose reference names no real heading",
        lambda r: _edit(r, "skills/tree/SKILL.md", "§6 for the", "§6.6 for the"),
        "dead section reference")
    # A heading inside a fence is not a heading: the fence-blind regex this
    # replaced would have harvested `## 9.9` below into the §-namespace and
    # accepted the dead reference that follows.
    expect_reject(
        "a pseudo-heading inside a code fence does not define a section",
        lambda r: (_edit(r, "docs/ENGINE.md", "## 6. Convergence",
                         "## 6. Convergence\n\n```markdown\n## 9.9 Not a heading\n```"),
                   _edit(r, "skills/tree/SKILL.md", "§6 for the", "§9.9 for the"),
                   _refresh_digest(r)),
        "dead section reference")
    # `_strip_inline_code`: link syntax quoted as an example is not a link.
    expect_clean("backticked link syntax is not resolved as a link")


def test_i18n_group() -> None:
    """check_i18n: the manifest, the digest, and the coverage sweep."""
    expect_reject(
        "an unregistered English document appears",
        lambda r: _write(r, "docs/STRAY.md", "# stray\n\nnot in the manifest\n"),
        "unregistered canonical documents")
    expect_reject(
        "an unregistered Chinese document appears",
        lambda r: _write(r, "docs/STRAY.zh.md", "# 游离\n\n未登记\n"),
        "unregistered Chinese documents")
    expect_reject(
        "the translation digest is stale",
        lambda r: _edit(r, "docs/ENGINE.md", "reports CONVERGED", "reports CONVERGED now"),
        "stale i18n-source-sha256")
    expect_reject(
        "languages.json is not valid JSON",
        lambda r: _write(r, "docs/languages.json", "{not json"),
        "not valid JSON")
    expect_reject(
        "languages.json declares the wrong schema_version",
        lambda r: _patch_json(r, "docs/languages.json",
                              lambda d: d.update(schema_version=2)),
        "schema_version must be 1")
    # Run-output directories stay invisible; tracked fixtures do not. Both
    # halves matter: the unanchored `-out` rule used to hide
    # examples/attack/expected-out/*.md from every check in this file.
    expect_clean(
        "a top-level run-output directory is skipped",
        lambda r: _write(r, "attack-out/2026__x/tree.md", "# run output\n"))
    expect_reject(
        "a nested *-out fixture directory is NOT skipped",
        lambda r: _write(r, "examples/attack/expected-out/tree.md",
                         "# fixture\n\nSee §9.9 for details.\n"),
        "dead section reference")


def _main_rc(root: Path) -> int:
    """`vp.main()` against `root`, with its per-check chatter captured.

    main() prints its own `[ok]` lines and a `FAIL(<group>): …` diagnostic.
    Letting the deliberate-failure case print would put the word FAIL in the
    log of a passing run, which is exactly the sort of thing someone skims and
    misreads."""
    original = vp.REPO
    vp.REPO = root
    try:
        with io.StringIO() as out, io.StringIO() as err, \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            return vp.main()
    finally:
        vp.REPO = original


def test_main_reports_every_group() -> None:
    """`main()` runs all seven groups and returns 0/1. Nothing exercised the
    entry point itself, so a group dropped from its list would be invisible."""
    global _n_pass, _n_fail
    with tempfile.TemporaryDirectory() as tmp:
        root = _build(Path(tmp))
        _n_pass += 1
        if _main_rc(root) != 0:
            _failures.append("MAIN: clean fixture did not return 0")
        _n_fail += 1
        _edit(root, "CHANGELOG.md", f"## v{VERSION}", "## v9.9.9")
        if _main_rc(root) != 1:
            _failures.append("MAIN: broken fixture did not return 1")


def test_main_group_list_is_complete() -> None:
    """Every `check_*` function defined in the module is wired into `main`.
    Adding a check and forgetting to register it would otherwise ship a
    check that never runs."""
    global _n_pass
    _n_pass += 1
    import inspect
    defined = {name for name, obj in vars(vp).items()
               if name.startswith("check_") and inspect.isfunction(obj)}
    source = inspect.getsource(vp.main)
    missing = sorted(name for name in defined if name not in source)
    if missing:
        _failures.append(f"MAIN: check functions not wired into main(): {missing}")


# Ordered exactly as `main()` runs them, captured BEFORE the pytest wrapping
# below so the script runner keeps the plain, non-raising originals.
_TESTS = (
    test_fixture_is_clean,
    test_manifests,
    test_skills,
    test_presets_and_commands,
    test_tools_syntax,
    test_crossrefs,
    test_i18n_group,
    test_main_reports_every_group,
    test_main_group_list_is_complete,
)


def _pytest_visible(fn):
    """Re-raise, as an assertion, whatever `fn` recorded in `_failures`.

    Same contract as the sibling suites: reporting goes into a module-level
    list that only `main()` reads, so a collected `test_*` would otherwise
    pass unconditionally under pytest. Only the failures this call added are
    raised.
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
        print("test_checks: FAILED")
        for f in _failures:
            print(f"  - {f}")
        return 1
    print("test_checks: all check-group tests passed "
          f"({_n_pass} clean + {_n_fail} rejection cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
