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
"""

from __future__ import annotations

import re

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

_BLOCK_SCALAR_MARKERS = {"|", ">", "|-", ">-", "|+", ">+"}


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _strip_comment(s: str) -> str:
    """Drop a trailing `# comment` per YAML scalar rules.

    YAML semantics: in a *plain* (unquoted) scalar, quote characters are
    literal — an apostrophe in prose (`reviewer's take`) does NOT open a
    quoted span, so the first whitespace-preceded `#` starts the comment.
    Only when the value *starts* with a quote is the span up to the
    matching closing quote protected; the comment scan resumes after it.
    (The old toggle-on-any-quote logic swallowed comments after prose
    apostrophes and mis-split quoted values.)
    """
    s = s.rstrip()
    start = 0
    if s[:1] in "\"'":
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


def _split_top_level(s: str, sep: str) -> list[str]:
    """Split on `sep` at brace/bracket depth 0, ignoring separators inside
    quotes or nested `{}` / `[]`."""
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
            elif c == sep and depth == 0:
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

    Anything after the matching closing `}` (e.g. a trailing `# comment`)
    is ignored — cutting at the matched brace, not requiring endswith("}"),
    keeps a commented flow-map item from degenerating to `{"_raw": ...}`.
    """
    s = s.strip()
    if not s.startswith("{"):
        # Not a flow map after all; return as a degenerate single value.
        return {"_raw": _unquote(s)}
    close = _find_flow_map_end(s)
    if close == -1:
        return {"_raw": _unquote(s)}
    inner = s[1:close]
    out: dict[str, str] = {}
    for part in _split_top_level(inner, ","):
        if ":" not in part:
            continue
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
            # Deeper than the list level and not a list entry we model; skip.
            i += 1
            continue
        s = raw.strip()
        if not s.startswith("-"):
            break
        item = s[1:].strip()
        if item.startswith("{"):
            items.append(_parse_flow_map(item))
            i += 1
        elif _looks_like_map_entry(item) and _has_deeper_continuation(lines, i + 1, base):
            # Block-map list item (standard YAML list-of-maps):
            #   - key: S
            #     name: severity
            # Re-parse "- key: S" as the first line of a map whose base
            # indent is the position after "- ", then absorb the deeper
            # continuation lines. Without this, continuation lines were
            # silently dropped and the item degraded to a scalar string.
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


def _has_deeper_continuation(lines: list[str], i: int, base: int) -> bool:
    """True if the next content line is indented deeper than `base`
    (i.e. the current list item continues as a block map)."""
    j = _next_content_line(lines, i)
    return j < len(lines) and _indent(lines[j]) > base


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
            i += 1
            continue
        content = raw.strip()
        if ":" not in content:
            i += 1
            continue
        key, _, rest = content.partition(":")
        key = key.strip()
        rest = rest.strip()
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
            d[key] = _unquote(_strip_comment(rest))
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
