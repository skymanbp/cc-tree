#!/usr/bin/env python3
"""Behavioral tests for cc-tree's multilingual version-control contract.

The suite uses temporary repositories for deterministic positive and negative
cases, then validates all real English/Chinese documentation pairs shipped by
this checkout. It has no dependencies outside the Python standard library.
"""

from __future__ import annotations

import copy
import json
import re
import tempfile
from pathlib import Path

import validate_plugin as vp
from _i18n import (
    I18nError,
    build_token_sets,
    chinese_banner,
    english_banner,
    load_manifest,
    normalize_newlines,
    scan_markdown,
    source_digest,
    validate_i18n,
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
        "output_artifacts:\n  primary: confirmed.md\n"
        "  secondary:\n    rejected: rejected.md\n---\nbody\n",
    )
    return root


def _expect(label: str, action, error: type[BaseException] | None = None) -> None:
    global _passed
    try:
        action()
    except BaseException as exc:
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


def _rewrite_pair(repo: Path, en_transform, zh_transform) -> None:
    """Transform BOTH sides of the fixture pair and refresh the digest, so
    a case can change the English source without tripping the staleness
    check it is not trying to exercise."""
    en_path = repo / "docs/ENGINE.md"
    old_en = en_path.read_text(encoding="utf-8")
    new_en = en_transform(old_en)
    en_path.write_text(new_en, encoding="utf-8")
    zh_path = repo / "docs/ENGINE.zh.md"
    zh = zh_transform(zh_path.read_text(encoding="utf-8"))
    zh = zh.replace(source_digest(old_en), source_digest(new_en))
    zh_path.write_text(zh, encoding="utf-8")


def _command_case(label: str, mutate, should_fail: bool) -> None:
    def run() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _repo(Path(tmp))
            mutate(repo)
            vp._check_command_flags(repo)

    _expect(label, run, vp.ValidationError if should_fail else None)


def test_text_primitives() -> None:
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
        # Fences carry (marker, info, body, owning-section index).
        if shape.fences != (("```", "md", "## Fake", 1),):
            raise AssertionError(shape.fences)

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


def test_manifest_validation() -> None:
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
        "canonical_only cannot whitelist a Chinese document",
        # Previously this combination passed: the exception list fed the
        # translation registry, so an orphan .zh.md could be laundered in.
        lambda repo: (
            _write(repo, "docs/orphan.zh.md", "# 孤立文档\n"),
            _rewrite_manifest(
                repo,
                lambda data: data["canonical_only"].append(
                    {"path": "docs/orphan.zh.md", "reason": "laundering probe"}
                ),
            ),
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
        "boolean schema_version fails",
        # json True == 1 in Python, so a bare equality check accepted it.
        lambda repo: _rewrite_manifest(
            repo, lambda data: data.update({"schema_version": True})
        ),
    )
    _fixture_case(
        "non-object manifest root fails",
        lambda repo: _write(repo, "docs/languages.json", "[]"),
    )
    _fixture_case(
        "null fixed_machine_tokens entry fails",
        lambda repo: _rewrite_manifest(
            repo, lambda data: data["fixed_machine_tokens"].append(None)
        ),
    )
    _fixture_case(
        "traversal in canonical_only path fails",
        lambda repo: _rewrite_manifest(
            repo,
            lambda data: data["canonical_only"].append(
                {"path": "../outside.md", "reason": "traversal probe"}
            ),
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

    def secondary_keys_harvested() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _repo(Path(tmp))
            manifest = load_manifest(repo)
            whole, inline = build_token_sets(
                repo, manifest, REQUIRED_KEYS, VERDICT_ROLES, ROOT_KINDS)
            # `rejected` comes only from the fixture preset's
            # output_artifacts.secondary map KEY.
            if "rejected" not in inline:
                raise AssertionError(
                    f"secondary map key not harvested: inline={sorted(inline)}")

    _expect("output_artifacts.secondary keys join the vocabulary",
            secondary_keys_harvested)


def test_pair_metadata() -> None:
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
        "missing source digest fails",
        lambda repo: _rewrite_translation(
            repo,
            lambda text: re.sub(r"<!-- i18n-source-sha256:.*?-->\n", "", text),
        ),
    )
    _fixture_case(
        "second digest comment fails",
        # First-match-wins let a correct digest shadow a stale second one.
        lambda repo: _rewrite_translation(
            repo,
            lambda text: text + "\n<!-- i18n-source-sha256: " + "a" * 64 + " -->\n",
        ),
    )
    _fixture_case(
        "digest buried mid-document fails",
        # The fixture doc is shorter than the 12-nonempty-line lead window,
        # so filler prose must push the relocated digest genuinely outside
        # it (real docs are far longer than the window).
        lambda repo: _rewrite_translation(
            repo,
            lambda text: re.sub(
                r"<!-- i18n-source-sha256: ([0-9a-f]{64}) -->\n", "", text
            ) + "".join(f"补充说明第{n}行，用于加长文档。\n" for n in range(12))
            + "<!-- i18n-source-sha256: "
            + source_digest((repo / "docs/ENGINE.md").read_text(encoding="utf-8"))
            + " -->\n",
        ),
    )


def test_heading_and_section_coverage() -> None:
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
        # becomes a byte copy of the English source.
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
        "substantive section with no Chinese prose fails",
        lambda repo: _rewrite_translation(
            repo,
            lambda text: text.replace(
                "root_kind 架构字段与 --lang 标志始终保留英文机器标记。完整运行会报告 "
                "CONVERGED 并写入 tree.md。本段提供足够的中文说明，用于验证逐节翻译覆盖，"
                "而不是仅凭标题通过检查。",
                "root_kind --lang CONVERGED tree.md are English machine tokens "
                "and this replacement paragraph is long enough to be judged.",
            ).replace(
                "`topic` 根类型在此处行内出现，并与下方逐字节一致的代码块中的取值保持一致。",
                "The `topic` root kind is named inline here as well.",
            ),
        ),
    )
    _fixture_case(
        "substantive section answered with a token stub fails",
        # Keeps Han and every machine token, but far below the letter floors —
        # the "translated the identifiers, dropped the prose" case.
        lambda repo: _rewrite_translation(
            repo,
            lambda text: text.replace(
                "root_kind 架构字段与 --lang 标志始终保留英文机器标记。完整运行会报告 "
                "CONVERGED 并写入 tree.md。本段提供足够的中文说明，用于验证逐节翻译覆盖，"
                "而不是仅凭标题通过检查。",
                "root_kind --lang CONVERGED tree.md 见英文。",
            ).replace(
                "`topic` 根类型在此处行内出现，并与下方逐字节一致的代码块中的取值保持一致。",
                "`topic` 见上。",
            ),
        ),
    )
    _fixture_case(
        "Han characters hidden in a comment do not count as prose",
        # An English copy plus a Han-rich HTML comment defeated the old
        # raw-text Han check; visible-prose stripping catches it.
        lambda repo: _rewrite_translation(
            repo,
            lambda text: text.replace(
                "root_kind 架构字段与 --lang 标志始终保留英文机器标记。完整运行会报告 "
                "CONVERGED 并写入 tree.md。本段提供足够的中文说明，用于验证逐节翻译覆盖，"
                "而不是仅凭标题通过检查。",
                "The root_kind schema and --lang flag remain English machine "
                "tokens. A completed run reports CONVERGED and writes tree.md. "
                "Longer filler prose keeps this section judged as substantive."
                "<!-- 这条注释里藏了大量汉字用来欺骗只看原始文本的检查逻辑，"
                "如果检查不剥离注释这些字符就会被当成翻译正文。 -->",
            ).replace(
                "`topic` 根类型在此处行内出现，并与下方逐字节一致的代码块中的取值保持一致。",
                "The `topic` root kind is named inline here as well.",
            ),
        ),
    )


def test_machine_token_and_fence_parity() -> None:
    _fixture_case(
        "dropped machine token fails",
        lambda repo: _rewrite_translation(
            repo, lambda text: text.replace("CONVERGED", "已收敛", 1)
        ),
    )
    _fixture_case(
        "inline machine identifier localized in code fails",
        lambda repo: _rewrite_translation(
            repo, lambda text: text.replace("`advances`", "`推进`", 1)
        ),
    )
    _fixture_case(
        "inline token localized while identical fence keeps it fails",
        lambda repo: _rewrite_translation(
            repo, lambda text: text.replace("`topic`", "`主题`", 1)
        ),
    )
    _fixture_case(
        "distinctive token localized in inline code fails",
        # `root_kind` passes the whole-document check via the fence, but its
        # inline-code use must stay verbatim too — the whole-document class
        # previously skipped the inline check entirely.
        lambda repo: _rewrite_pair(
            repo,
            lambda en: en.replace("The root_kind schema",
                                  "The `root_kind` schema", 1),
            lambda zh: zh.replace("root_kind 架构字段",
                                  "`根类型`（root_kind）架构字段", 1),
        ),
    )
    _fixture_case(
        "changed fenced code fails",
        lambda repo: _rewrite_translation(
            repo, lambda text: text.replace('"topic"', '"artifact"', 1)
        ),
    )
    _fixture_case(
        "fence delimiter swap fails",
        # Same info + body behind ~~~ instead of ``` counted as identical
        # when only (info, body) was recorded.
        lambda repo: _rewrite_translation(
            repo,
            lambda text: text.replace("```json", "~~~json", 1)
            .replace("\n```\n", "\n~~~\n", 1),
        ),
    )
    _fixture_case(
        "fence moved to a different section fails",
        lambda repo: _rewrite_translation(
            repo,
            lambda text: text.replace(
                "```json\n{\"root_kind\": \"topic\", \"output_language\": \"zh\"}\n```\n\n"
                "## 2. 证据\n\n",
                "## 2. 证据\n\n"
                "```json\n{\"root_kind\": \"topic\", \"output_language\": \"zh\"}\n```\n\n",
            ),
        ),
    )


def test_command_flags() -> None:
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
        "wrapper-specific flag documented only in the skill body fails",
        # --focus lives in the skill body here, not in the command or preset
        # body. The old single-namespace search accepted that for ANY
        # wrapper; wrapper-specific flags must be documented locally.
        lambda repo: (
            (repo / "skills/tree/SKILL.md").write_text(
                "---\nname: tree\ndescription: test\n"
                "argument-hint: '<root> [--lang <tag|auto>]'\n---\n"
                "# Tree\n\nUse `--lang <tag|auto>`. Attack mode narrows via "
                "`--focus <section>`.\n",
                encoding="utf-8",
            ),
            (repo / "commands/attack.md").write_text(
                "---\ndescription: test\n"
                "argument-hint: '<file> [--lang <tag|auto>] [--focus <section>]'\n---\n"
                "Use `--lang <tag|auto>` for output.\n",
                encoding="utf-8",
            ),
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


def test_shipped_pairs() -> None:
    _expect(
        "all shipped documentation pairs pass",
        lambda: validate_i18n(REPO, vp.PRESET_REQUIRED_KEYS,
                              vp.VERDICT_ROLES, vp.ROOT_KINDS),
    )


def main() -> int:
    test_text_primitives()
    test_manifest_validation()
    test_pair_metadata()
    test_heading_and_section_coverage()
    test_machine_token_and_fence_parity()
    test_command_flags()
    test_shipped_pairs()

    if _failures:
        print("test_i18n: FAILED")
        for failure in _failures:
            print(f"  - {failure}")
        return 1
    print(f"test_i18n: all {_passed} multilingual cases passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
