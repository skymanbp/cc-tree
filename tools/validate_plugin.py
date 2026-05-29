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
  4. Every presets/<name>.md passes full schema validation (docs/ENGINE.md
     §10-§11, docs/presets.md §1): name (= file basename) + description +
     root_kind (known kind) + subject_label + verdict_enum (exactly the 4
     roles) + convergence_metric (a verdict role) + score_dims (exactly 5,
     each key/name/desc) + node_schema (exactly 12) + output_artifacts.primary.
  5. Every commands/<name>.md starts with a YAML frontmatter block that
     declares `description:`.
  6. tools/*.py all parse as valid Python (ast.parse, no runtime imports).
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

from _frontmatter import parse_frontmatter

REPO = Path(__file__).resolve().parent.parent

# Schema vocabulary the engine contract fixes (docs/ENGINE.md §5.2, §10-§11;
# docs/presets.md §1). Presets may name the *labels* freely but must supply
# exactly these four verdict *roles* and one of these root kinds.
VERDICT_ROLES = ("advances", "kept", "pruned", "blocked")
ROOT_KINDS = ("topic", "artifact", "code", "design-prompt")
PRESET_REQUIRED_KEYS = (
    "name", "description", "root_kind", "subject_label",
    "verdict_enum", "convergence_metric", "score_dims",
    "node_schema", "output_artifacts",
)
NODE_SCHEMA_LEN = 12
SCORE_DIMS_LEN = 5


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


def validate_preset_schema(path: Path, fm: dict) -> None:
    """Enforce the preset compliance rules promised in docs/ENGINE.md §10-§11
    and docs/presets.md §1. `fm` is the parsed frontmatter mapping."""
    def pfail(msg: str) -> None:
        fail(f"{path}: {msg}")

    # 1. Required keys present and non-empty.
    for key in PRESET_REQUIRED_KEYS:
        if key not in fm or fm[key] in ("", None, [], {}):
            pfail(f"frontmatter missing or empty '{key}:'")

    # 2. name == file basename.
    if fm.get("name") != path.stem:
        pfail(f"frontmatter name={fm.get('name')!r} != expected {path.stem!r}")

    # 3. root_kind is one of the known kinds.
    if fm["root_kind"] not in ROOT_KINDS:
        pfail(f"root_kind={fm['root_kind']!r} not in {ROOT_KINDS}")

    # 4. verdict_enum has exactly the four required roles.
    ve = fm["verdict_enum"]
    if not isinstance(ve, dict):
        pfail("verdict_enum must be a mapping of the 4 roles")
    if set(ve) != set(VERDICT_ROLES):
        pfail(f"verdict_enum roles {sorted(ve)} != required {sorted(VERDICT_ROLES)}")
    if any(not str(v).strip() for v in ve.values()):
        pfail("verdict_enum has an empty label for some role")

    # 5. convergence_metric must name one of the verdict_enum roles (verbatim).
    cm = fm["convergence_metric"]
    if cm not in ve:
        pfail(f"convergence_metric={cm!r} not in verdict_enum roles {sorted(ve)}")

    # 6. score_dims is a list of exactly 5, each with key/name/desc.
    sd = fm["score_dims"]
    if not isinstance(sd, list) or len(sd) != SCORE_DIMS_LEN:
        n = len(sd) if isinstance(sd, list) else "not-a-list"
        pfail(f"score_dims must have exactly {SCORE_DIMS_LEN} entries (got {n})")
    for idx, dim in enumerate(sd):
        if not isinstance(dim, dict):
            pfail(f"score_dims[{idx}] is not a mapping ({{key, name, desc}})")
        for sub in ("key", "name", "desc"):
            if not str(dim.get(sub, "")).strip():
                pfail(f"score_dims[{idx}] missing '{sub}'")

    # 7. node_schema is a list of exactly 12 non-empty entries.
    ns = fm["node_schema"]
    if not isinstance(ns, list) or len(ns) != NODE_SCHEMA_LEN:
        n = len(ns) if isinstance(ns, list) else "not-a-list"
        pfail(f"node_schema must have exactly {NODE_SCHEMA_LEN} entries (got {n})")
    for idx, field in enumerate(ns):
        if not str(field).strip():
            pfail(f"node_schema[{idx}] is empty")

    # 8. output_artifacts has a non-empty 'primary'.
    oa = fm["output_artifacts"]
    if not isinstance(oa, dict) or not str(oa.get("primary", "")).strip():
        pfail("output_artifacts.primary missing or empty")


def check_presets() -> str:
    presets_dir = REPO / "presets"
    if not presets_dir.is_dir():
        return "presets OK (no presets/ dir — optional)"
    files = sorted(p for p in presets_dir.glob("*.md") if p.name != "README.md")
    if not files:
        fail(f"{presets_dir} has no preset .md files (other than README.md)")
    for f in files:
        fm = parse_frontmatter(f.read_text(encoding="utf-8"))
        if fm is None:
            fail(f"{f} has no YAML frontmatter (--- ... ---) at top")
        validate_preset_schema(f, fm)
    return f"presets OK ({len(files)} presets, full schema)"


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
