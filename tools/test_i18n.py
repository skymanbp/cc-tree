#!/usr/bin/env python3
"""Behavioral tests for cc-tree's multilingual version-control contract.

The suite uses temporary repositories for deterministic positive and negative
cases, then validates all real English/Chinese documentation pairs shipped by
this checkout. It has no dependencies outside the Python standard library.
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import re
import tempfile
from pathlib import Path

import validate_plugin as vp
from _i18n import (
    I18nError,
    chinese_banner,
    english_banner,
    normalize_newlines,
    scan_markdown,
    source_digest,
    validate_i18n,
    validate_manifest,
)

REPO = Path(__file__).resolve().parent.parent
REQUIRED_KEYS = ("name", "root_kind")
VERDICT_ROLES = ("advances", "kept", "pruned", "blocked")
ROOT_KINDS = ("topic", "artifact", "code", "design-prompt")

_failures: list[str] = []
_passed = 0


def _write(repo: Path, relative: str, text: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")


def _manifest() -> dict:
    return {
        "schema_version": 1,
        "canonical_language": "en",
        "default_output_language": "en",
        "documentation_languages": ["en", "zh"],
        "pairs": [{
            "canonical": "docs/ENGINE.md",
            "translations": {"zh": "docs/ENGINE.zh.md"},
        }],
        "canonical_only": [
            {"path": "skills/**/*.md", "reason": "runtime skill, English-only"},
            {"path": "commands/*.md", "reason": "command wrappers, English-only"},
            {"path": "presets/*.md", "reason": "preset schemas, English-only"},
        ],
        "required_runtime_flags": ["--lang"],
        "fixed_machine_tokens": ["CONVERGED", "tree.md"],
    }


def _english() -> str:
    return (
        f"{english_banner('docs/ENGINE.md', 'docs/ENGINE.zh.md')}\n\n"
        "# Engine contract\n\n"
        "## 1. Language contract\n\n"
        "The root_kind schema and --lang flag remain English machine tokens. "
        "A completed run reports CONVERGED and writes tree.md. This paragraph "
        "is deliberately substantive so section-level translation coverage is "
        "checked rather than passing on headings alone.\n\n"
        "The `topic` root kind is named inline here and also appears verbatim "
        "inside the byte-identical fence below.\n\n"
        "```json\n{\"root_kind\": \"topic\", \"output_language\": \"zh\"}\n```\n\n"
        "## 2. Evidence\n\n"
        "Quoted evidence remains verbatim while the surrounding explanation "
        "uses the resolved output language for the entire run. The `advances` "
        "verdict role stays English even inside inline code.\n"
    )


def _chinese(en_text: str) -> str:
    return (
        f"{chinese_banner('docs/ENGINE.md', 'docs/ENGINE.zh.md')}\n"
        f"<!-- i18n-source-sha256: {source_digest(en_text)} -->\n\n"
        "# 引擎契约\n\n"
        "## 1. 语言契约\n\n"
        "root_kind 架构字段与 --lang 标志始终保留英文机器标记。完整运行会报告 "
        "CONVERGED 并写入 tree.md。本段提供足够的中文说明，用于验证逐节翻译覆盖，"
        "而不是仅凭标题通过检查。\n\n"
        "`topic` 根类型在此处行内出现，并与下方逐字节一致的代码块中的取值保持一致。\n\n"
        "```json\n{\"root_kind\": \"topic\", \"output_language\": \"zh\"}\n```\n\n"
        "## 2. 证据\n\n"
        "引用证据保持原文，周围解释则统一使用本次运行解析出的输出语言。"
        "`advances` 判定角色即使在行内代码中也保持英文。\n"
    )


def _repo(root: Path) -> Path:
    manifest = _manifest()
    _write(root, "docs/languages.json", json.dumps(manifest, indent=2))
    en_text = _english()
    _write(root, "docs/ENGINE.md", en_text)
    _write(root, "docs/ENGINE.zh.md", _chinese(en_text))
    _write(
        root,
        "skills/tree/SKILL.md",
        "---\nname: tree\ndescription: test\n"
        "argument-hint: '<root> [--lang <tag|auto>]'\n---\n"
        "# Tree\n\nUse `--lang <tag|auto>` to select output language.\n",
    )
    _write(
        root,
        "commands/attack.md",
        "---\ndescription: test\n"
        "argument-hint: '<file> [--lang <tag|auto>] [--focus <section>]'\n---\n"
        "Use `--lang <tag|auto>` for output and `--focus <section>` to narrow review.\n",
    )
    _write(
        root,
        "presets/attack.md",
        "---\nname: attack\nroot_kind: artifact\nsubject_label: critique\n"
        "verdict_enum:\n  advances: CONFIRMED\n  kept: MARGINAL\n"
        "  pruned: REFUTED\n  blocked: INCOMPLETE_FORBIDDEN\n"
        "convergence_metric: advances\nnode_schema:\n  - statement\n"
        "score_dims:\n  - {key: S, name: severity, desc: d}\n"
        "output_artifacts:\n  primary: confirmed.md\n---\nbody\n",
    )
    return root


def _expect(label: str, action, error: type[BaseException] | None = None) -> None:
    global _passed
    try:
        action()
    except BaseException as exc:  # tests deliberately exercise SystemExit too
        if error is not None and isinstance(exc, error):
            _passed += 1
            return
        _failures.append(f"{label}: unexpected {type(exc).__name__}: {exc}")
        return
    if error is None:
        _passed += 1
    else:
        _failures.append(f"{label}: expected {error.__name__}, but call passed")


def _fixture_case(label: str, mutate, error: type[BaseException] = I18nError) -> None:
    def run() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _repo(Path(tmp))
            mutate(repo)
            validate_i18n(repo, REQUIRED_KEYS, VERDICT_ROLES, ROOT_KINDS)

    _expect(label, run, error)


def _rewrite_translation(repo: Path, transform) -> None:
    path = repo / "docs/ENGINE.zh.md"
    path.write_text(transform(path.read_text(encoding="utf-8")), encoding="utf-8")


def _rewrite_manifest(repo: Path, transform) -> None:
    path = repo / "docs/languages.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    transform(data)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _command_case(label: str, mutate, should_fail: bool) -> None:
    def run() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _repo(Path(tmp))
            mutate(repo)
            with contextlib.redirect_stderr(io.StringIO()):
                vp._check_command_flags(repo)

    _expect(label, run, SystemExit if should_fail else None)


def main() -> int:
    _expect(
        "LF and CRLF sources hash identically",
        lambda: (_ for _ in ()).throw(AssertionError("digest mismatch"))
        if source_digest("a\nb\n") != source_digest("a\r\nb\r\n") else None,
    )
    _expect(
        "newline normalization handles bare CR",
        lambda: (_ for _ in ()).throw(AssertionError("normalization mismatch"))
        if normalize_newlines("a\rb") != "a\nb" else None,
    )

    def fence_scan() -> None:
        shape = scan_markdown("# Real\n```md\n## Fake\n```\n## 1. Real child\n")
        if shape.headings != ((1, ""), (2, "1")):
            raise AssertionError(shape.headings)

    _expect("fenced fake headings are ignored", fence_scan)

    def banner_shapes() -> None:
        # Root-level canonical: reciprocal links are bare basenames.
        if english_banner("README.md", "README.zh.md") != (
            "> Language: English (canonical). Chinese: [`README.zh.md`](README.zh.md)."
        ):
            raise AssertionError("root english banner")
        # Nested canonical: link is relative to the doc's own directory.
        if english_banner("field-profiles/README.md", "field-profiles/README.zh.md") != (
            "> Language: English (canonical). "
            "Chinese: [`field-profiles/README.zh.md`](README.zh.md)."
        ):
            raise AssertionError("nested english banner")
        if chinese_banner("docs/ENGINE.md", "docs/ENGINE.zh.md") != (
            "> 语言：中文。英文规范版：[`docs/ENGINE.md`](ENGINE.md)。"
            "如有歧义，以英文版为准。"
        ):
            raise AssertionError("chinese banner")

    _expect("banner helpers emit repo-correct reciprocal links", banner_shapes)
    _fixture_case("valid translated fixture passes", lambda repo: None, error=None)

    _fixture_case(
        "missing manifest translation path fails",
        lambda repo: (repo / "docs/ENGINE.zh.md").unlink(),
    )
    _fixture_case(
        "invalid Chinese filename fails",
        lambda repo: _rewrite_manifest(
            repo,
            lambda data: data["pairs"][0]["translations"].update(
                {"zh": "docs/ENGINE.cn.md"}
            ),
        ),
    )
    _fixture_case(
        "duplicate manifest path fails",
        lambda repo: _rewrite_manifest(
            repo, lambda data: data["pairs"].append(copy.deepcopy(data["pairs"][0]))
        ),
    )
    _fixture_case(
        "pair and canonical-only overlap fails",
        lambda repo: _rewrite_manifest(
            repo,
            lambda data: data["canonical_only"].append(
                {"path": "docs/ENGINE.md", "reason": "overlap probe"}
            ),
        ),
    )
    _fixture_case(
        "unregistered Chinese document fails",
        lambda repo: _write(repo, "docs/orphan.zh.md", "# 孤立文档\n"),
    )
    _fixture_case(
        "missing Chinese banner fails",
        lambda repo: _rewrite_translation(
            repo, lambda text: text.replace("> 语言：中文。", "> 中文。", 1)
        ),
    )
    _fixture_case(
        "stale digest after English edit fails",
        lambda repo: (repo / "docs/ENGINE.md").write_text(
            _english() + "\nCanonical change.\n", encoding="utf-8"
        ),
    )
    _fixture_case(
        "equal-count reordered headings fail",
        lambda repo: _rewrite_translation(
            repo,
            lambda text: text.replace("## 1. 语言契约", "## 2. 语言契约", 1)
            .replace("## 2. 证据", "## 1. 证据", 1),
        ),
    )
    _fixture_case(
        "section marker mismatch fails",
        lambda repo: _rewrite_translation(
            repo, lambda text: text.replace("## 2. 证据", "## 3. 证据", 1)
        ),
    )
    _fixture_case(
        "English-copy substantive section fails",
        # Convert BOTH paragraphs of section 1 to English so the whole section
        # becomes a byte copy of the English source (the second `topic`
        # paragraph was added to exercise the inline/fence interaction, so it
        # must be Anglicized here too or the section stays partly Chinese).
        lambda repo: _rewrite_translation(
            repo,
            lambda text: text.replace(
                "root_kind 架构字段与 --lang 标志始终保留英文机器标记。完整运行会报告 "
                "CONVERGED 并写入 tree.md。本段提供足够的中文说明，用于验证逐节翻译覆盖，"
                "而不是仅凭标题通过检查。",
                "The root_kind schema and --lang flag remain English machine tokens. "
                "A completed run reports CONVERGED and writes tree.md. This paragraph "
                "is deliberately substantive so section-level translation coverage is "
                "checked rather than passing on headings alone.",
            ).replace(
                "`topic` 根类型在此处行内出现，并与下方逐字节一致的代码块中的取值保持一致。",
                "The `topic` root kind is named inline here and also appears verbatim "
                "inside the byte-identical fence below.",
            ),
        ),
    )
    _fixture_case(
        "dropped machine token fails",
        lambda repo: _rewrite_translation(
            repo, lambda text: text.replace("CONVERGED", "已收敛", 1)
        ),
    )
    _fixture_case(
        "inline machine identifier localized in code fails",
        # `advances` is a bare verdict-role word (legitimate as prose), but the
        # English source uses it as an identifier inside inline code, so the
        # translation must keep it verbatim there. Localizing it must fail.
        lambda repo: _rewrite_translation(
            repo, lambda text: text.replace("`advances`", "`推进`", 1)
        ),
    )
    _fixture_case(
        "inline token localized while identical fence keeps it fails",
        # Mirrors the real README shape: `topic` is used inline in prose AND
        # appears as a bare word inside the byte-identical JSON fence. Localizing
        # the inline `` `topic` `` while leaving the fence untouched must still
        # fail — the fence must not "rescue" a localized inline identifier. The
        # quoted `"topic"` in the fence is a different string than the backtick
        # span, so this replace targets only the inline use.
        lambda repo: _rewrite_translation(
            repo, lambda text: text.replace("`topic`", "`主题`", 1)
        ),
    )
    _fixture_case(
        "changed fenced code fails",
        lambda repo: _rewrite_translation(
            repo, lambda text: text.replace('"topic"', '"artifact"', 1)
        ),
    )
    _fixture_case(
        "missing source digest fails",
        lambda repo: _rewrite_translation(
            repo,
            lambda text: re.sub(r"<!-- i18n-source-sha256:.*?-->\n", "", text),
        ),
    )
    _fixture_case(
        "unregistered canonical English document fails",
        lambda repo: _write(repo, "docs/rogue.md", "# Rogue\n\nUntracked English.\n"),
    )
    _fixture_case(
        "malformed manifest schema_version fails",
        lambda repo: _rewrite_manifest(
            repo, lambda data: data.update({"schema_version": 2})
        ),
    )
    _fixture_case(
        "canonical_only pattern matching nothing fails",
        lambda repo: _rewrite_manifest(
            repo,
            lambda data: data["canonical_only"].append(
                {"path": "nonexistent/*.md", "reason": "empty glob probe"}
            ),
        ),
    )

    _command_case("documented wrapper-specific flag passes", lambda repo: None, False)
    _command_case(
        "skill body dropping --lang fails",
        lambda repo: (repo / "skills/tree/SKILL.md").write_text(
            "---\nname: tree\ndescription: test\n"
            "argument-hint: '<root> [--lang <tag|auto>]'\n---\n"
            "# Tree\n\nNo language flag documented here.\n",
            encoding="utf-8",
        ),
        True,
    )
    _command_case(
        "flag found only in command frontmatter fails",
        lambda repo: (repo / "commands/attack.md").write_text(
            "---\ndescription: test\n"
            "argument-hint: '<file> [--lang <tag|auto>] [--ghost]'\n---\n"
            "Use `--lang <tag|auto>` for output.\n",
            encoding="utf-8",
        ),
        True,
    )
    _command_case(
        "wrapper omitting required --lang fails",
        lambda repo: (repo / "commands/attack.md").write_text(
            "---\ndescription: test\nargument-hint: '<file> [--focus <section>]'\n---\n"
            "Use `--focus <section>` to narrow review.\n",
            encoding="utf-8",
        ),
        True,
    )

    _expect(
        "all shipped documentation pairs pass",
        lambda: validate_i18n(REPO, vp.PRESET_REQUIRED_KEYS,
                              vp.VERDICT_ROLES, vp.ROOT_KINDS),
    )

    if _failures:
        print("test_i18n: FAILED")
        for failure in _failures:
            print(f"  - {failure}")
        return 1
    print(f"test_i18n: all {_passed} multilingual cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
