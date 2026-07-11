#!/usr/bin/env python3
"""Deterministic multilingual-document validation helpers for cc-tree.

English Markdown is canonical. Chinese parallel files are tracked by
``docs/languages.json`` and carry a SHA-256 fingerprint of the normalized
English source. The checks here deliberately validate structure and
freshness, not translation quality; semantic review remains a human task.
"""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from _frontmatter import parse_frontmatter

_FENCE_OPEN_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")
_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$")
_MARKER_RE = re.compile(
    r"^(§\d+(?:\.[0-9A-Za-z]+)*|F\d+|\d+(?:\.\d+)*)\b",
    re.IGNORECASE,
)
_DIGEST_RE = re.compile(r"<!--\s*i18n-source-sha256:\s*([0-9a-f]{64})\s*-->")
_HAN_RE = re.compile(r"[㐀-䶿一-鿿豈-﫿]")
_INLINE_CODE_RE = re.compile(r"`[^`]*`")
_URL_RE = re.compile(r"https?://\S+")
_FLAG_RE = re.compile(r"--[a-z][a-z0-9-]*")
_FRAMING_RE = re.compile(r"§3\.[A-LX]")
# Directory names never scanned for documents (shared with validate_plugin.py
# so the two skip lists cannot drift apart).
SKIP_DIR_PARTS = {".git", ".github", "memory", "__pycache__", "node_modules"}


class I18nError(ValueError):
    """Raised when the multilingual contract is violated."""


@dataclass(frozen=True)
class MarkdownShape:
    headings: tuple[tuple[int, str], ...]
    sections: tuple[str, ...]
    fences: tuple[tuple[str, str], ...]
    heading_titles: tuple[str, ...] = ()


@dataclass(frozen=True)
class I18nStats:
    pairs: int
    canonical_only: int
    digests: int
    sections: int
    machine_tokens: int


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def source_digest(text: str) -> str:
    normalized = normalize_newlines(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _heading_marker(title: str) -> str:
    title = title.rstrip("#").strip().replace("`", "")
    match = _MARKER_RE.match(title)
    return match.group(1).upper() if match else ""


def scan_markdown(text: str) -> MarkdownShape:
    """Return ordered headings, aligned prose sections, fenced blocks, and the
    raw heading titles.

    ATX-looking lines inside backtick or tilde fences are ignored. The
    section list contains preamble text followed by one body per heading.
    ``heading_titles`` preserves each heading's text so inline code that lives
    only in a heading is still visible to the code-context checks (a heading
    body is otherwise reduced to its stable marker and dropped).
    """
    headings: list[tuple[int, str]] = []
    sections: list[str] = []
    fences: list[tuple[str, str]] = []
    titles: list[str] = []
    body: list[str] = []
    fence_char = ""
    fence_len = 0
    fence_info = ""
    fence_body: list[str] = []

    for line in normalize_newlines(text).split("\n"):
        if fence_char:
            close = re.match(
                rf"^\s{{0,3}}{re.escape(fence_char)}{{{fence_len},}}\s*$",
                line,
            )
            if close:
                fences.append((fence_info, "\n".join(fence_body)))
                fence_char = ""
                fence_len = 0
                fence_info = ""
                fence_body = []
            else:
                fence_body.append(line)
            continue

        fence = _FENCE_OPEN_RE.match(line)
        if fence:
            marker = fence.group(1)
            fence_char = marker[0]
            fence_len = len(marker)
            fence_info = fence.group(2).strip()
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            sections.append("\n".join(body))
            body = []
            title = heading.group(2).rstrip("#").strip()
            headings.append((len(heading.group(1)), _heading_marker(title)))
            titles.append(title)
        else:
            body.append(line)

    if fence_char:
        raise I18nError("unclosed Markdown code fence")
    sections.append("\n".join(body))
    return MarkdownShape(tuple(headings), tuple(sections),
                         tuple(fences), tuple(titles))


def _prose_letters(text: str) -> list[str]:
    text = _INLINE_CODE_RE.sub("", text)
    text = _URL_RE.sub("", text)
    # Keep the human-readable anchor text; drop only the URL target. Stripping
    # the whole [text](url) span would hide untranslated link labels.
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    return [char for char in text if char.isalpha()]


def _first_nonempty_lines(text: str, limit: int = 12) -> list[str]:
    return [line.strip() for line in normalize_newlines(text).split("\n")
            if line.strip()][:limit]


def _relative_link(from_path: str, to_path: str) -> str:
    parent = str(PurePosixPath(from_path).parent)
    if parent == ".":
        parent = ""
    return posixpath.relpath(to_path, parent or ".")


def english_banner(canonical: str, translation: str) -> str:
    link = _relative_link(canonical, translation)
    return f"> Language: English (canonical). Chinese: [`{translation}`]({link})."


def chinese_banner(canonical: str, translation: str) -> str:
    link = _relative_link(translation, canonical)
    return (f"> 语言：中文。英文规范版：[`{canonical}`]({link})。"
            "如有歧义，以英文版为准。")


def _expand_manifest_path(repo: Path, entry: dict) -> list[Path]:
    raw = entry.get("path")
    reason = entry.get("reason")
    if not isinstance(raw, str) or not raw:
        raise I18nError("canonical_only entry missing path")
    if not isinstance(reason, str) or not reason.strip():
        raise I18nError(f"canonical_only entry {raw!r} missing reason")
    if any(char in raw for char in "*?["):
        matches = sorted(repo.glob(raw))
        if not matches:
            raise I18nError(f"canonical_only pattern matched nothing: {raw}")
        return matches
    path = repo / raw
    if not path.is_file():
        raise I18nError(f"canonical_only path missing: {raw}")
    return [path]


def load_manifest(repo: Path) -> dict:
    path = repo / "docs" / "languages.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise I18nError("docs/languages.json missing") from exc
    except json.JSONDecodeError as exc:
        raise I18nError(f"docs/languages.json is not valid JSON: {exc}") from exc

    if manifest.get("schema_version") != 1:
        raise I18nError("languages.json schema_version must be 1")
    if manifest.get("canonical_language") != "en":
        raise I18nError("languages.json canonical_language must be 'en'")
    if manifest.get("default_output_language") != "en":
        raise I18nError("languages.json default_output_language must be 'en'")
    languages = manifest.get("documentation_languages")
    if not isinstance(languages, list) or "en" not in languages or "zh" not in languages:
        raise I18nError("languages.json documentation_languages must include en and zh")
    if not isinstance(manifest.get("pairs"), list) or not manifest["pairs"]:
        raise I18nError("languages.json pairs must be a non-empty list")
    if not isinstance(manifest.get("canonical_only"), list):
        raise I18nError("languages.json canonical_only must be a list")
    if not isinstance(manifest.get("required_runtime_flags"), list):
        raise I18nError("languages.json required_runtime_flags must be a list")
    if not isinstance(manifest.get("fixed_machine_tokens"), list):
        raise I18nError("languages.json fixed_machine_tokens must be a list")
    return manifest


def validate_manifest(repo: Path, manifest: dict) -> tuple[list[tuple[str, str]], int]:
    pairs: list[tuple[str, str]] = []
    used: set[str] = set()

    for entry in manifest["pairs"]:
        if not isinstance(entry, dict):
            raise I18nError("languages.json pair entries must be objects")
        canonical = entry.get("canonical")
        translations = entry.get("translations")
        if not isinstance(canonical, str) or not canonical.endswith(".md"):
            raise I18nError("pair canonical path must be an unsuffixed .md file")
        if canonical.endswith(".zh.md"):
            raise I18nError(f"canonical path must not have a language suffix: {canonical}")
        if not isinstance(translations, dict) or set(translations) != {"zh"}:
            raise I18nError(f"pair {canonical} must declare exactly one zh translation")
        translation = translations["zh"]
        expected = canonical[:-3] + ".zh.md"
        if translation != expected:
            raise I18nError(
                f"Chinese translation for {canonical} must be named {expected}, got {translation}"
            )
        for raw in (canonical, translation):
            if raw in used:
                raise I18nError(f"duplicate language-manifest path: {raw}")
            used.add(raw)
            if not (repo / raw).is_file():
                raise I18nError(f"language-manifest path missing: {raw}")
        pairs.append((canonical, translation))

    canonical_only_paths: set[str] = set()
    for entry in manifest["canonical_only"]:
        for path in _expand_manifest_path(repo, entry):
            rel = path.relative_to(repo).as_posix()
            if rel in used:
                raise I18nError(f"path is both paired and canonical-only: {rel}")
            canonical_only_paths.add(rel)

    registered_zh = {translation for _, translation in pairs}
    actual_zh: set[str] = set()
    for path in repo.rglob("*.zh.md"):
        parts = path.relative_to(repo).parts
        if any(part in SKIP_DIR_PARTS or part.endswith("-out") for part in parts[:-1]):
            continue
        actual_zh.add(path.relative_to(repo).as_posix())
    unregistered = sorted(actual_zh - registered_zh - canonical_only_paths)
    if unregistered:
        raise I18nError(f"unregistered Chinese documents: {', '.join(unregistered)}")

    # Reverse coverage: every canonical English document in scope must be
    # registered as a pair canonical or as canonical_only. Without this the
    # manifest fails open — a new English doc could ship untranslated and
    # unreviewed, silently escaping the freshness contract.
    registered_canonical = {canonical for canonical, _ in pairs}
    covered = registered_canonical | canonical_only_paths
    unregistered_en = []
    for path in repo.rglob("*.md"):
        parts = path.relative_to(repo).parts
        if any(part in SKIP_DIR_PARTS or part.endswith("-out") for part in parts[:-1]):
            continue
        rel = path.relative_to(repo).as_posix()
        if rel.endswith(".zh.md"):
            continue
        if rel not in covered:
            unregistered_en.append(rel)
    if unregistered_en:
        raise I18nError(
            "unregistered canonical documents (add to pairs or canonical_only): "
            + ", ".join(sorted(unregistered_en))
        )

    return pairs, len(canonical_only_paths)


def _is_enforceable_token(token: str) -> bool:
    """True when a token is a *distinctive* machine identifier whose bare
    presence anywhere in a document can be enforced without colliding with
    ordinary prose (see `build_machine_tokens`).

    The whole-document parity check must never flag a plain lowercase
    dictionary word — `derivation`, `evidence`, `value`, `topic`, `zh` — that
    doubles as narrative text: those are legitimately localized in prose. Such
    bare identifiers are instead enforced *inside code context* by
    `build_inline_tokens` / `_validate_pair`, where a prose occurrence cannot
    trigger a false positive.

    Distinctive shape (safe for whole-document matching) = any of: an uppercase
    letter or digit (status/verdict tokens like `CONVERGED`), an underscore /
    hyphen / dot / slash (compound names `finding_statement`, tags `zh-Hant`,
    filenames `tree.md`, flags `--lang`), or a non-ASCII char (framing IDs like
    `§3.A`). A single character is never distinctive enough — a lone `S` score
    key or a stray `§` occurs in almost any text by coincidence — so one-char
    tokens are not whole-document enforced (their real uses live in fenced or
    inline code, checked separately).
    """
    if len(token) < 2:
        return False
    if any(c in token for c in "_-./"):
        return True
    if any(c.isupper() or c.isdigit() for c in token):
        return True
    if any(ord(c) > 127 for c in token):
        return True
    return False


def _harvest_tokens(repo: Path, manifest: dict,
                    required_keys: tuple[str, ...],
                    verdict_roles: tuple[str, ...],
                    root_kinds: tuple[str, ...]) -> set[str]:
    """Collect every candidate machine token from the manifest, validator
    constants, command/skill flags, preset frontmatter, and ENGINE framing IDs.

    This is the raw, unfiltered vocabulary. Callers decide how each token is
    enforced: `build_machine_tokens` keeps only the distinctive ones (matched
    anywhere), and `build_inline_tokens` keeps the bare-word remainder (matched
    only inside code context).
    """
    tokens = set(required_keys) | set(verdict_roles) | set(root_kinds)
    tokens.update(str(token) for token in manifest["fixed_machine_tokens"])
    tokens.update(str(flag) for flag in manifest["required_runtime_flags"])
    tokens.update({"primary", "secondary", "language_request",
                   "output_language", "language_source"})

    for path in [repo / "skills" / "tree" / "SKILL.md",
                 *sorted((repo / "commands").glob("*.md"))]:
        if path.name == "README.md":
            continue
        tokens.update(_FLAG_RE.findall(path.read_text(encoding="utf-8")))

    for path in sorted((repo / "presets").glob("*.md")):
        if path.name == "README.md":
            continue
        fm = parse_frontmatter(path.read_text(encoding="utf-8")) or {}
        # `subject_label` is deliberately excluded: its value (idea / critique /
        # option / finding) is a human-facing node label, which docs/ENGINE.md
        # §1.0 classes as localizable prose, not part of the machine skeleton.
        for key in ("name", "root_kind", "convergence_metric"):
            value = fm.get(key)
            if isinstance(value, str) and value:
                tokens.add(value)
        verdicts = fm.get("verdict_enum", {})
        if isinstance(verdicts, dict):
            tokens.update(str(value) for value in verdicts.values())
        for field in fm.get("node_schema", []):
            if isinstance(field, str):
                tokens.add(field)
        for dim in fm.get("score_dims", []):
            if isinstance(dim, dict):
                for key in ("key", "name"):
                    value = dim.get(key)
                    if isinstance(value, str) and value:
                        tokens.add(value)
        artifacts = fm.get("output_artifacts", {})
        if isinstance(artifacts, dict):
            stack = list(artifacts.values())
            while stack:
                value = stack.pop()
                if isinstance(value, dict):
                    stack.extend(value.values())
                elif isinstance(value, str) and value:
                    tokens.add(value)

    engine = (repo / "docs" / "ENGINE.md").read_text(encoding="utf-8")
    tokens.update(_FRAMING_RE.findall(engine))
    return {token for token in tokens if token}


def build_machine_tokens(repo: Path, manifest: dict,
                         required_keys: tuple[str, ...],
                         verdict_roles: tuple[str, ...],
                         root_kinds: tuple[str, ...]) -> set[str]:
    """Tokens enforced by *whole-document* presence: only distinctive
    identifiers (see `_is_enforceable_token`) that cannot collide with prose.
    """
    return {token for token in _harvest_tokens(
                repo, manifest, required_keys, verdict_roles, root_kinds)
            if _is_enforceable_token(token)}


def build_inline_tokens(repo: Path, manifest: dict,
                        required_keys: tuple[str, ...],
                        verdict_roles: tuple[str, ...],
                        root_kinds: tuple[str, ...]) -> set[str]:
    """Tokens enforced only *inside inline code spans*: the bare lowercase
    machine identifiers that `build_machine_tokens` drops — `root_kind` values
    (`topic`), verdict roles (`advances`), preset names (`brainstorm`),
    `node_schema` fields, `score_dims` names, and the language tags `en` / `zh`.
    They double as prose words, so whole-document matching would false-positive;
    but wherever the English source uses one *as an identifier* in a backtick
    span, the translation must keep it verbatim there. Prose occurrences never
    enter an inline code span, so no false positives. (Fenced examples need no
    token check here — `_validate_pair` already forces them byte-identical, and
    counting their contents would let a fence rescue a localized inline use;
    see `_inline_code_atoms`.)

    Enforcement is exact-atom, not substring (see `_inline_code_atoms`), so a
    short tag like `zh` is required from a standalone `` `zh` `` span but is not
    spuriously demanded by the `zh` inside a `` `README.zh.md` `` filename —
    which is why `en` / `zh` can now be enforced instead of skipped. Single
    characters stay excluded: a lone score key (`S`, `E`) is too ambiguous to
    enforce even inside code.
    """
    full = _harvest_tokens(repo, manifest, required_keys, verdict_roles, root_kinds)
    distinctive = {token for token in full if _is_enforceable_token(token)}
    return {token for token in (full - distinctive) if len(token) >= 2}


def _inline_code_atoms(text: str) -> set[str]:
    """Identifier atoms drawn from a document's *inline* code spans.

    For every inline ``backtick`` span — in prose sections and in heading
    titles — the whole stripped span is one atom, plus its whitespace-separated
    words (so ``--lang zh`` yields both ``--lang`` and ``zh``). Taking the whole
    span as an atom keeps short tags safe: a filename span ``README.zh.md``
    contributes only the atom ``README.zh.md`` and never a bare ``zh``, so the
    tag ``zh`` is harvested solely from a standalone ``zh`` span.

    Fenced blocks are deliberately excluded. ``_validate_pair`` already requires
    every fence to be byte-identical between the English source and its
    translation — strictly stronger than token presence — so fences need no
    token check here. Worse, folding fence contents in would let an incidental
    English word inside a required-identical fence (e.g. ``fall back to en`` in a
    usage comment, or a ``--lang zh`` example) "rescue" a token whose inline
    ``backtick`` uses were localized away: the fence copies over verbatim and
    silently re-supplies the atom. The inline check therefore judges inline
    spans only; fence identifiers ride on the byte-identity check instead.
    """
    shape = scan_markdown(text)
    atoms: set[str] = set()
    for chunk in (*shape.sections, *shape.heading_titles):
        for span in _INLINE_CODE_RE.findall(chunk):
            content = span.strip("`").strip()
            if content:
                atoms.add(content)
                atoms.update(content.split())
    return atoms


def _token_present(text: str, token: str) -> bool:
    # Word-boundary match for *every* token shape. `re.escape` handles the `.`
    # and `/` in filenames (`tree.md`) and framing IDs (`§3.A`); the boundary
    # class then stops a token from matching inside a larger identifier — so
    # `tree.md` does not match `xtree.md`, and `finding` does not match
    # `finding_statement`. Non-ASCII and punctuation neighbours count as
    # boundaries, so `tree.md文件` and `§3.A节` still match.
    pattern = rf"(?<![A-Za-z0-9_-]){re.escape(token)}(?![A-Za-z0-9_-])"
    return re.search(pattern, text) is not None


def _validate_pair(repo: Path, canonical: str, translation: str,
                   machine_tokens: set[str],
                   inline_tokens: set[str]) -> tuple[int, int]:
    en_text = (repo / canonical).read_text(encoding="utf-8")
    zh_text = (repo / translation).read_text(encoding="utf-8")

    en_lead = _first_nonempty_lines(en_text)
    zh_lead = _first_nonempty_lines(zh_text)
    expected_en_banner = english_banner(canonical, translation)
    expected_zh_banner = chinese_banner(canonical, translation)
    if expected_en_banner not in en_lead:
        raise I18nError(f"{canonical}: missing standard English canonical banner")
    if expected_zh_banner not in zh_lead:
        raise I18nError(f"{translation}: missing standard Chinese canonical-reference banner")

    digest_match = _DIGEST_RE.search(zh_text)
    expected_digest = source_digest(en_text)
    if digest_match is None:
        raise I18nError(f"{translation}: missing i18n-source-sha256; expected {expected_digest}")
    if digest_match.group(1) != expected_digest:
        raise I18nError(
            f"{translation}: stale i18n-source-sha256 {digest_match.group(1)}; "
            f"expected {expected_digest}"
        )

    en_shape = scan_markdown(en_text)
    zh_shape = scan_markdown(zh_text)
    if en_shape.headings != zh_shape.headings:
        raise I18nError(
            f"{translation}: ordered heading structure diverges from {canonical}: "
            f"zh={zh_shape.headings} en={en_shape.headings}"
        )
    if len(en_shape.fences) != len(zh_shape.fences):
        raise I18nError(
            f"{translation}: code-fence count {len(zh_shape.fences)} != "
            f"{canonical} count {len(en_shape.fences)}"
        )
    for index, (en_fence, zh_fence) in enumerate(zip(en_shape.fences, zh_shape.fences)):
        if en_fence != zh_fence:
            raise I18nError(
                f"{translation}: fenced code block {index + 1} differs from {canonical}"
            )

    for index, (en_section, zh_section) in enumerate(
            zip(en_shape.sections, zh_shape.sections)):
        en_letters = _prose_letters(en_section)
        if len(en_letters) < 80:
            continue
        zh_letters = _prose_letters(zh_section)
        if not _HAN_RE.search(zh_section):
            raise I18nError(
                f"{translation}: substantive section {index + 1} has no Chinese prose"
            )
        minimum = max(20, int(len(en_letters) * 0.20))
        if len(zh_letters) < minimum:
            raise I18nError(
                f"{translation}: section {index + 1} is too thin "
                f"({len(zh_letters)} letters; need {minimum})"
            )
        if normalize_newlines(en_section).strip() == normalize_newlines(zh_section).strip():
            raise I18nError(
                f"{translation}: substantive section {index + 1} is an English copy"
            )

    compared = 0
    for token in machine_tokens:
        if _token_present(en_text, token):
            compared += 1
            if not _token_present(zh_text, token):
                raise I18nError(
                    f"{translation}: missing canonical machine token {token!r} "
                    f"used by {canonical}"
                )

    # Bare-word machine identifiers (root_kind values, verdict roles, preset
    # names, schema/score names, language tags) are enforced where the English
    # source uses them inside an inline `code` span: a translator may localize
    # the same word in prose, but must keep `topic`, `advances`, `zh`, ...
    # verbatim in backticks. Matching is exact-atom on inline spans only —
    # fences are already forced byte-identical above, so counting their contents
    # here would let an incidental English word in a required-identical fence
    # rescue a token whose inline uses were localized away.
    en_atoms = _inline_code_atoms(en_text)
    zh_atoms = _inline_code_atoms(zh_text)
    for token in inline_tokens:
        if token in en_atoms:
            compared += 1
            if token not in zh_atoms:
                raise I18nError(
                    f"{translation}: machine identifier {token!r} appears in "
                    f"{canonical} code context but is missing from the "
                    f"translated code context"
                )
    return len(en_shape.sections), compared


def validate_i18n(repo: Path, required_keys: tuple[str, ...],
                  verdict_roles: tuple[str, ...],
                  root_kinds: tuple[str, ...]) -> I18nStats:
    manifest = load_manifest(repo)
    pairs, canonical_only = validate_manifest(repo, manifest)
    tokens = build_machine_tokens(
        repo, manifest, required_keys, verdict_roles, root_kinds
    )
    inline_tokens = build_inline_tokens(
        repo, manifest, required_keys, verdict_roles, root_kinds
    )
    sections = 0
    compared_tokens = 0
    for canonical, translation in pairs:
        pair_sections, pair_tokens = _validate_pair(
            repo, canonical, translation, tokens, inline_tokens
        )
        sections += pair_sections
        compared_tokens += pair_tokens
    return I18nStats(
        pairs=len(pairs),
        canonical_only=canonical_only,
        digests=len(pairs),
        sections=sections,
        machine_tokens=compared_tokens,
    )
