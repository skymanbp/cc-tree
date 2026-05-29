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
    * a scalar string (e.g. `node_schema`, `glossary_paths`), or
    * an inline flow-map `- {key: S, name: ..., desc: "..."}`
      (e.g. `score_dims`).

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
    """Drop a trailing `# comment`, respecting single/double quotes.

    A `#` only starts a comment when it is at the start of the string or
    preceded by whitespace and not inside a quoted span.
    """
    in_single = in_double = False
    for i, c in enumerate(s):
        if c == "'" and not in_double:
            in_single = not in_single
        elif c == '"' and not in_single:
            in_double = not in_double
        elif c == "#" and not in_single and not in_double and (i == 0 or s[i - 1] in " \t"):
            return s[:i].rstrip()
    return s.rstrip()


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


def _parse_flow_map(s: str) -> dict[str, str]:
    """Parse `{key: S, name: severity, desc: "..."}` into a dict."""
    s = s.strip()
    if not (s.startswith("{") and s.endswith("}")):
        # Not a flow map after all; return as a degenerate single value.
        return {"_raw": _unquote(s)}
    inner = s[1:-1]
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
        else:
            items.append(_strip_comment(item))
        i += 1
    return items, i


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
            d[key] = _strip_comment(rest)
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


def parse_frontmatter(text: str) -> dict | None:
    """Parse the leading `--- ... ---` frontmatter block of `text`.

    Returns the parsed mapping, or None if there is no frontmatter block.
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    lines = m.group(1).split("\n")
    result, _ = _parse_map(lines, 0, 0)
    return result
