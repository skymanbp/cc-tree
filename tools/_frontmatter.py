#!/usr/bin/env python3
"""Zero-dependency YAML-subset parser for cc-tree preset/skill frontmatter.

This is **not** a general YAML parser. It handles exactly the subset the
cc-tree frontmatter blocks use, so that `validate_plugin.py` can enforce
the schema rules promised in `docs/ENGINE.md` §10-§11 and
`docs/presets.md` §1 without taking a PyYAML runtime dependency (the
plugin's selling point is being pure-prompt + stdlib-only; CI installs
nothing — see `.github/workflows/ci.yml`).

Supported constructs (everything the 4 shipped presets use):

- Top-level `key: value` scalars (value may carry a trailing `# comment`).
- Block scalars `key: |` / `key: >` — following deeper-indented lines are
  collected as one string (used by `use-when:`).
- Block maps — `key:` with no value, followed by deeper-indented
  `subkey: value` lines. Nesting is supported (e.g. `output_artifacts`
  has a nested `secondary:` map).
- Block lists — `key:` with no value, followed by deeper-indented
  `- item` lines. Each item is either:
    * a scalar string (e.g. `node_schema`, `glossary_paths`),
    * an inline flow-map `- {key: S, name: ..., desc: "..."}`
      (e.g. `score_dims`), or
    * a block-map item — `- key: v` whose following lines are
      indented deeper (standard YAML list-of-maps style); parsed
      into the same dict shape as the flow-map form.

Return shape:
- scalar  -> str
- block scalar -> str (lines joined with "\n")
- block list of scalars -> list[str]
- block list of flow-maps -> list[dict[str, str]]
- block map -> dict (possibly nested)

Comment/quote handling is quote-aware so commas and `#` inside a quoted
`desc:` value are not mistaken for separators or comments.

Anything *outside* the subset raises `FrontmatterError` instead of being
silently skipped or coerced: this parser feeds a validator, so guessing
at malformed input would convert authoring mistakes into false passes
(junk lines, duplicate keys, `-item` without a space, and text after a
flow map were all previously absorbed without a sound).

Known, deliberate divergences from full YAML (the shipped presets use
none of these): quote escapes (`\"`, doubled `''`) are not decoded, and
block scalars are joined line-by-line — per-line indentation inside a
`|` block and `>`-folding/chomping semantics are not preserved.
"""

from __future__ import annotations

import re


class FrontmatterError(ValueError):
    """Raised when a frontmatter block falls outside the supported subset."""


# `(?:\n|\Z)`: the closing `---` may be the file's last byte, with no
# trailing newline after it. `\ufeff?`: tolerate a UTF-8 BOM. `[ \t]*`
# (not `\s*`): horizontal whitespace only, so the match cannot swallow
# blank lines that belong to the Markdown body.
FRONTMATTER_RE = re.compile(r"^\ufeff?---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)",
                            re.DOTALL)

_BLOCK_SCALAR_MARKERS = {"|", ">", "|-", ">-", "|+", ">+"}


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _strip_comment(s: str) -> str:
    """Drop a trailing `# comment` per YAML scalar rules.

    In a *plain* (unquoted) scalar, quote characters are literal — an
    apostrophe in prose (`reviewer's take`) does NOT open a quoted span, so
    the first whitespace-preceded `#` starts the comment. Only when the value
    *starts* with a quote is the span up to the matching closing quote
    protected; the comment scan resumes after it.
    """
    s = s.rstrip()
    if not s:
        return s
    start = 0
    # `s[0]` after the empty guard, never `s[:1]`: `"" in "\"'"` is True
    # (substring semantics), so the slice form lets "" reach `s[0]`.
    if s[0] in "\"'":
        close = s.find(s[0], 1)
        if close == -1:
            return s  # unterminated quote; keep verbatim
        start = close + 1
    for i in range(start, len(s)):
        if s[i] == "#" and (i == 0 or s[i - 1] in " \t"):
            return s[:i].rstrip()
    return s


def _unquote(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def _split_commas(s: str) -> list[str]:
    """Split a flow-map body on commas at brace/bracket depth 0, ignoring
    commas inside quotes or nested `{}` / `[]`."""
    parts: list[str] = []
    buf: list[str] = []
    in_single = in_double = False
    depth = 0
    for c in s:
        if c == "'" and not in_double:
            in_single = not in_single
        elif c == '"' and not in_single:
            in_double = not in_double
        elif not in_single and not in_double:
            if c in "{[":
                depth += 1
            elif c in "}]":
                depth -= 1
            elif c == "," and depth == 0:
                parts.append("".join(buf))
                buf = []
                continue
        buf.append(c)
    if buf:
        parts.append("".join(buf))
    return parts


def _find_flow_map_end(s: str) -> int:
    """Index of the `}` matching the opening `{` at s[0], quote-aware.

    Returns -1 if the braces never balance (malformed flow map).
    """
    in_single = in_double = False
    depth = 0
    for i, c in enumerate(s):
        if c == "'" and not in_double:
            in_single = not in_single
        elif c == '"' and not in_single:
            in_double = not in_double
        elif not in_single and not in_double:
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return i
    return -1


def _parse_flow_map(s: str) -> dict[str, str]:
    """Parse `{key: S, name: severity, desc: "..."}` into a dict.

    A trailing `# comment` after the matching closing `}` is allowed
    (cutting at the matched brace keeps a commented flow-map item alive);
    any *other* trailing text, an unbalanced brace, or an entry without a
    `key: value` colon raises — silently dropping those turned malformed
    presets into validated ones.
    """
    s = s.strip()
    close = _find_flow_map_end(s)
    if close == -1:
        raise FrontmatterError(f"unbalanced braces in flow map: {s!r}")
    tail = _strip_comment(s[close + 1:].strip())
    if tail:
        raise FrontmatterError(
            f"unexpected text after flow map: {tail!r} in {s!r}")
    inner = s[1:close]
    out: dict[str, str] = {}
    for part in _split_commas(inner):
        if ":" not in part:
            raise FrontmatterError(
                f"flow-map entry is not 'key: value': {part.strip()!r} in {s!r}")
        k, _, v = part.partition(":")
        out[k.strip()] = _unquote(v.strip())
    return out


def _is_comment_or_blank(line: str) -> bool:
    return (not line.strip()) or line.lstrip().startswith("#")


def _next_content_line(lines: list[str], i: int) -> int:
    n = len(lines)
    while i < n and _is_comment_or_blank(lines[i]):
        i += 1
    return i


def _parse_list(lines: list[str], i: int, base: int) -> tuple[list, int]:
    items: list = []
    n = len(lines)
    while i < n:
        raw = lines[i]
        if _is_comment_or_blank(raw):
            i += 1
            continue
        ind = _indent(raw)
        if ind < base:
            break
        if ind > base:
            # A deeper line here belongs to no entry: block-map items
            # consume their own continuations, so this is a stray.
            raise FrontmatterError(
                f"misindented line under list (indent {ind} > {base}): "
                f"{raw.strip()!r}")
        s = raw.strip()
        if not s.startswith("-"):
            break
        if s != "-" and not s.startswith("- "):
            # YAML requires the sequence indicator to stand alone: `-one`
            # is a plain scalar, which cannot start a list entry.
            raise FrontmatterError(f"list item must be '-' or '- ...': {s!r}")
        item = s[1:].strip()
        if item.startswith("{"):
            items.append(_parse_flow_map(item))
            i += 1
        elif _looks_like_map_entry(item):
            # Block-map list item (standard YAML list-of-maps):
            #   - key: S
            #     name: severity
            # Re-parse "- key: S" as the first line of a map whose base
            # indent is the position after "- ", then absorb any deeper
            # continuation lines. A single `- key: S` with no continuation
            # is still a (one-entry) mapping — treating it as the scalar
            # string "key: S" mis-shaped the value.
            item_indent = ind + 2
            sub = [" " * item_indent + item]
            i += 1
            while i < n:
                cont = lines[i]
                if cont.strip() and _indent(cont) <= base:
                    break
                sub.append(cont)
                i += 1
            mapping, _ = _parse_map(sub, 0, item_indent)
            items.append(mapping)
        else:
            # Unquote after comment-stripping so quoted list items parse to
            # their content, matching how flow-map values are unquoted.
            items.append(_unquote(_strip_comment(item)))
            i += 1
    return items, i


def _looks_like_map_entry(item: str) -> bool:
    """True if a list item body reads as `key: value` / `key:` (a block-map
    start) rather than a plain scalar. Quoted scalars and URLs (`https://…`,
    no space after the colon) are not map entries."""
    if item.startswith(("'", '"')):
        return False
    key, sep, rest = item.partition(":")
    return bool(sep) and " " not in key.strip() and (rest == "" or rest.startswith(" "))


def _parse_map(lines: list[str], i: int, base: int) -> tuple[dict, int]:
    d: dict = {}
    n = len(lines)
    while i < n:
        raw = lines[i]
        if _is_comment_or_blank(raw):
            i += 1
            continue
        ind = _indent(raw)
        if ind < base:
            break
        if ind > base:
            # Nested blocks are consumed by their `key:` line below, so a
            # deeper line arriving at this loop is orphaned — usually a
            # misindented sibling that would otherwise vanish silently.
            raise FrontmatterError(
                f"misindented line (indent {ind} > {base}): {raw.strip()!r}")
        content = raw.strip()
        if ":" not in content:
            raise FrontmatterError(
                f"expected 'key: value', got {content!r}")
        key, _, rest = content.partition(":")
        key = key.strip()
        if key in d:
            # Last-wins would let a duplicate silently shadow the value the
            # validator then approves.
            raise FrontmatterError(f"duplicate key {key!r}")
        rest = rest.strip()
        if rest.startswith("{"):
            # Inline flow map as a value: `verdict_enum: {advances: A, …}`.
            # Comment handling rides on _parse_flow_map's cut-at-brace (a
            # bare _strip_comment here would sever a quoted `#` inside).
            d[key] = _parse_flow_map(rest)
            i += 1
            continue
        # Strip a trailing comment BEFORE the branch decisions: `key: # c`
        # is an empty value (nested block or "") and `key: | # c` is a
        # block scalar — with the comment left in place, the first parsed
        # as the scalar "" and dropped its children, the second as the
        # literal string "|".
        rest = _strip_comment(rest)
        if rest in _BLOCK_SCALAR_MARKERS:
            i += 1
            block: list[str] = []
            while i < n:
                bl = lines[i]
                if bl.strip() and _indent(bl) <= base:
                    break
                block.append(bl.strip())
                i += 1
            d[key] = "\n".join(block).strip()
        elif rest:
            # Unquote after comment-stripping: `name: "attack"` must parse
            # to `attack`, matching flow-map value handling — otherwise the
            # validator's name==basename check rejects valid quoted YAML.
            d[key] = _unquote(rest)
            i += 1
        else:
            j = _next_content_line(lines, i + 1)
            if j < n and _indent(lines[j]) > base:
                child_indent = _indent(lines[j])
                if lines[j].lstrip().startswith("-"):
                    value, i = _parse_list(lines, i + 1, child_indent)
                else:
                    value, i = _parse_map(lines, i + 1, child_indent)
                d[key] = value
            else:
                d[key] = ""
                i += 1
    return d, i


def split_frontmatter(text: str) -> tuple[dict | None, str]:
    """Return parsed frontmatter and the remaining Markdown body.

    Keeping the body separate is important for validators: an
    `argument-hint` must not count as documentation for the flags it
    advertises. Files without frontmatter return ``(None, text)``.
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, text
    lines = m.group(1).split("\n")
    result, _ = _parse_map(lines, 0, 0)
    return result, text[m.end():]


def parse_frontmatter(text: str) -> dict | None:
    """Parse the leading `--- ... ---` frontmatter block of `text`.

    Returns the parsed mapping, or None if there is no frontmatter block.
    """
    result, _ = split_frontmatter(text)
    return result
