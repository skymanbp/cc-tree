#!/usr/bin/env python3
"""cc-tree plugin sanity checks.

Run with no arguments. Exits non-zero on any failure; prints a one-line
summary per check on success.

Checks:
  1. .claude-plugin/plugin.json is valid JSON and has name + version +
     description.
  2. .claude-plugin/marketplace.json is valid JSON; its metadata.version
     and plugins[<self>].version both match plugin.json.
  3. Every skills/<name>/SKILL.md starts with a YAML frontmatter block
     that declares `name:` (= directory name) and `description:`.
  4. Every presets/<name>.md starts with a YAML frontmatter block that
     declares `name:` (= file basename) and `description:`.
  5. Every commands/<name>.md starts with a YAML frontmatter block that
     declares `description:`.
  6. tools/*.py all parse as valid Python (ast.parse, no runtime imports).
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def check_manifests() -> str:
    plugin_path = REPO / ".claude-plugin" / "plugin.json"
    market_path = REPO / ".claude-plugin" / "marketplace.json"
    try:
        plugin = json.loads(plugin_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"{plugin_path} is not valid JSON: {e}")
    try:
        market = json.loads(market_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"{market_path} is not valid JSON: {e}")
    for key in ("name", "version", "description"):
        if key not in plugin:
            fail(f"plugin.json missing required key '{key}'")
    plugin_v = plugin["version"]
    market_v = market.get("metadata", {}).get("version")
    if market_v != plugin_v:
        fail(f"marketplace.json metadata.version ({market_v!r}) != "
             f"plugin.json version ({plugin_v!r})")
    inner = next((p for p in market.get("plugins", []) if p.get("name") == plugin["name"]), None)
    if inner is None:
        fail(f"marketplace.json plugins[] has no entry named {plugin['name']!r}")
    if inner.get("version") != plugin_v:
        fail(f"marketplace.json plugins[].version ({inner.get('version')!r}) != "
             f"plugin.json version ({plugin_v!r})")
    return f"manifests OK (version {plugin_v})"


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict | None:
    """Minimal flat YAML parse: top-level `key: value` pairs only.

    Nested keys (dicts, lists) are tolerated but their values are dropped.
    Comments and blank lines are skipped.
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        # Only consider top-level keys (no leading whitespace).
        if line[:1] in (" ", "\t", "-"):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm


def _check_md_frontmatter(path: Path, required_keys: tuple[str, ...],
                          name_must_match: str | None) -> None:
    fm = parse_frontmatter(path.read_text(encoding="utf-8"))
    if fm is None:
        fail(f"{path} has no YAML frontmatter (--- ... ---) at top")
    for key in required_keys:
        if key not in fm or not fm[key]:
            fail(f"{path} frontmatter missing '{key}:'")
    if name_must_match is not None and fm.get("name") != name_must_match:
        fail(f"{path} frontmatter name={fm.get('name')!r} != "
             f"expected {name_must_match!r}")


def check_skills() -> str:
    skills_dir = REPO / "skills"
    if not skills_dir.is_dir():
        fail(f"{skills_dir} missing")
    skill_dirs = sorted(p for p in skills_dir.iterdir() if p.is_dir())
    if not skill_dirs:
        fail("skills/ has no skill directories")
    for sd in skill_dirs:
        skill_md = sd / "SKILL.md"
        if not skill_md.is_file():
            fail(f"{skill_md} missing")
        _check_md_frontmatter(skill_md, ("name", "description"), sd.name)
    return f"skills OK ({len(skill_dirs)} skills)"


def check_presets() -> str:
    presets_dir = REPO / "presets"
    if not presets_dir.is_dir():
        return "presets OK (no presets/ dir — optional)"
    files = sorted(p for p in presets_dir.glob("*.md") if p.name != "README.md")
    if not files:
        fail(f"{presets_dir} has no preset .md files (other than README.md)")
    for f in files:
        _check_md_frontmatter(f, ("name", "description"), f.stem)
    return f"presets OK ({len(files)} presets)"


def check_commands() -> str:
    commands_dir = REPO / "commands"
    if not commands_dir.is_dir():
        return "commands OK (no commands/ dir — optional)"
    files = sorted(p for p in commands_dir.glob("*.md") if p.name != "README.md")
    if not files:
        return "commands OK (no command .md files — optional)"
    for f in files:
        _check_md_frontmatter(f, ("description",), None)
    return f"commands OK ({len(files)} commands)"


def check_tools_syntax() -> str:
    tools_dir = REPO / "tools"
    py_files = sorted(tools_dir.glob("*.py"))
    if not py_files:
        fail(f"{tools_dir} has no .py tools")
    for p in py_files:
        try:
            ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        except SyntaxError as e:
            fail(f"{p}: SyntaxError: {e}")
    return f"tools/*.py syntax OK ({len(py_files)} files)"


def main() -> int:
    for name, check in [
        ("manifests", check_manifests),
        ("skills", check_skills),
        ("presets", check_presets),
        ("commands", check_commands),
        ("tools", check_tools_syntax),
    ]:
        msg = check()
        print(f"  [ok] {msg}")
    print("validate_plugin: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
