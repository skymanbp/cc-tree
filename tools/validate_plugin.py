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
  7. Cross-file consistency: `](path#anchor)` links resolve to a real
     heading, `examples/` line citations stay in bounds, command
     `argument-hint` flags are documented outside frontmatter, field
     profiles match the schema, and every `§N` / `§FN` prose reference
     names a real section.
  8. docs/languages.json controls English-canonical / Chinese-parallel
     documentation, source digests, structure, and machine-token parity.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

from _frontmatter import parse_frontmatter, split_frontmatter
from _i18n import I18nError, SKIP_DIR_PARTS, load_manifest, validate_i18n

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


# --- Cross-file consistency checks -----------------------------------------
# Added after the 2026-07 audit: ~2/3 of the defects found were mechanical
# drift between files (dead anchors, stale example line citations, bilingual
# heading divergence, command hints advertising unregistered flags). Each
# sub-check below turns one of those defect classes into a CI failure.

_LINK_RE = re.compile(r"\]\(([^)#\s]+)#([^)\s]+)\)")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
_CITATION_RE = re.compile(r"([A-Za-z0-9_.\-/]+\.md):(\d+)(?:-(\d+))?")
_FLAG_RE = re.compile(r"--[a-z][a-z0-9-]*")
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def _strip_inline_code(text: str) -> str:
    """Blank out single-backtick spans before link/citation scanning.

    Prose that *documents* link syntax writes the pattern literally — e.g.
    the changelog entry explaining that a fragment belongs in ``](path#frag)``
    rather than in the label. Those are quoted examples, not links, and
    resolving `path` as a file is a false positive. Fenced blocks are left
    intact: they carry real worked examples whose links should still resolve.
    """
    return _INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), text)


def _content_md_files() -> list[Path]:
    out = []
    for p in sorted(REPO.rglob("*.md")):
        rel_parts = p.relative_to(REPO).parts
        if any(part in SKIP_DIR_PARTS or part.endswith("-out")
               for part in rel_parts[:-1]):
            continue
        out.append(p)
    return out


def _slugify(heading: str) -> str:
    """GitHub-style heading slug: drop code ticks, lowercase, strip
    punctuation (keep word chars / spaces / hyphens), spaces -> hyphens."""
    text = heading.replace("`", "").lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def _check_anchors(md_files: list[Path]) -> int:
    """Every `](path#fragment)` link must point at a file that exists and
    a heading whose slug equals the fragment. Pure-fragment links
    (`](#L42)`) are skipped — the docs use those as illustrative
    pseudo-references in framing examples."""
    n = 0
    slug_cache: dict[Path, set[str]] = {}
    for src in md_files:
        text = _strip_inline_code(src.read_text(encoding="utf-8"))
        for target_rel, frag in _LINK_RE.findall(text):
            if target_rel.startswith(("http://", "https://")):
                continue
            target = (src.parent / target_rel).resolve()
            if not target.is_file():
                fail(f"{src}: link target missing: {target_rel}")
            if target.suffix != ".md":
                continue
            if target not in slug_cache:
                text = target.read_text(encoding="utf-8")
                slug_cache[target] = {
                    _slugify(h) for _, h in _HEADING_RE.findall(text)}
            if frag.lower() not in slug_cache[target]:
                fail(f"{src}: dead anchor #{frag} -> {target_rel} "
                     f"(no heading slugs match)")
            n += 1
    return n


def _check_example_citations() -> int:
    """Every `<file>.md:N[-M]` citation inside examples/ whose target file
    exists must stay within the target's real line count (the +2 drift
    class: expected-out written against an older sample-claim.md)."""
    n = 0
    for src in sorted((REPO / "examples").rglob("*.md")):
        for target_rel, a, b in _CITATION_RE.findall(
                src.read_text(encoding="utf-8")):
            target = (src.parent / target_rel).resolve()
            if not target.is_file():
                continue  # prose mention, not a checkable citation
            total = len(target.read_text(encoding="utf-8").splitlines())
            lo, hi = int(a), int(b) if b else int(a)
            if not (1 <= lo <= hi <= total):
                fail(f"{src}: citation {target_rel}:{a}"
                     f"{'-' + b if b else ''} out of bounds "
                     f"(file has {total} lines)")
            n += 1
    return n


def _contains_flag(text: str, flag: str) -> bool:
    pattern = rf"(?<![A-Za-z0-9-]){re.escape(flag)}(?![A-Za-z0-9-])"
    return re.search(pattern, text) is not None


def _check_command_flags(repo: Path = REPO) -> int:
    """Validate command hints against authoritative Markdown bodies.

    Frontmatter is excluded from the documentation sources so a flag cannot
    validate itself merely by appearing in the same `argument-hint`. The
    language manifest may also require a common flag in every wrapper.
    """
    # This runs during the cross-refs check, before check_i18n's guard, so a
    # malformed manifest must be reported here rather than escaping as a
    # traceback.
    try:
        manifest = load_manifest(repo)
    except I18nError as exc:
        fail(f"command-flags: {exc}")
    required = tuple(str(flag) for flag in manifest["required_runtime_flags"])

    skill_path = repo / "skills" / "tree" / "SKILL.md"
    skill_fm, skill_body = split_frontmatter(
        skill_path.read_text(encoding="utf-8")
    )
    skill_hint = str((skill_fm or {}).get("argument-hint", ""))
    for flag in set(_FLAG_RE.findall(skill_hint)):
        if not _contains_flag(skill_body, flag):
            fail(f"{skill_path}: argument-hint advertises {flag} but the "
                 "skill body does not document it")
    for flag in required:
        if (not _contains_flag(skill_hint, flag)
                or not _contains_flag(skill_body, flag)):
            fail(f"{skill_path}: required common flag {flag} must appear in "
                 "both argument-hint and skill body")

    n = 0
    for cmd in sorted((repo / "commands").glob("*.md")):
        fm, body = split_frontmatter(cmd.read_text(encoding="utf-8"))
        hint = str((fm or {}).get("argument-hint", ""))
        preset = repo / "presets" / cmd.name
        preset_body = ""
        if preset.is_file():
            _, preset_body = split_frontmatter(
                preset.read_text(encoding="utf-8")
            )
        sources = "\n".join((skill_body, body, preset_body))
        for flag in set(_FLAG_RE.findall(hint)):
            if not _contains_flag(sources, flag):
                fail(f"{cmd}: argument-hint advertises {flag} but neither "
                     f"SKILL.md, the command body, nor {preset.name} "
                     "documents it outside frontmatter")
            n += 1
        for flag in required:
            if not _contains_flag(hint, flag):
                fail(f"{cmd}: argument-hint omits required common flag {flag}")
    return n


_SECTION_REF_RE = re.compile(r"§\s?(F\d+|\d+(?:\.[0-9A-Za-z]+)?)")
_SECTION_ID_RE = re.compile(r"^§?(F\d+|\d+(?:\.[0-9A-Za-z]+)?)[.\s—-]")


def _section_id_sources() -> list[Path]:
    """Files whose headings define the engine's §-section namespace."""
    return [REPO / "docs" / "ENGINE.md", REPO / "docs" / "ENGINE.zh.md",
            REPO / "skills" / "tree" / "SKILL.md",
            *sorted((REPO / "presets").glob("*.md"))]


def _check_section_refs(md_files: list[Path]) -> int:
    """Every `§N` / `§N.M` / `§FN` prose reference must name a real heading.

    The 2026-08 sweep found six dead pointers (`§0.4` / `§0.7` / `§0.8` left
    behind when §0.x was renumbered to F1–F8, plus invented `§2.4` / `§6.6`)
    spread over five files. `_check_anchors` cannot catch them: they are prose
    tokens, not Markdown links, so nothing tied them to a heading.

    The valid namespace is harvested from the headings that define it — the
    engine spec, the skill, and the presets (which add their own `§2.A` /
    `§2.B` baseline modes).

    `CHANGELOG.md` is exempt: recording *which* dead pointer was removed is
    the file's job, so it must be able to name identifiers that no longer
    resolve. It is a historical record, not a runtime contract — nothing
    dereferences a changelog.
    """
    valid: set[str] = set()
    for src in _section_id_sources():
        if not src.is_file():
            continue
        for _, heading in _HEADING_RE.findall(src.read_text(encoding="utf-8")):
            m = _SECTION_ID_RE.match(heading.strip())
            if m:
                valid.add(m.group(1).upper())
    if not valid:  # pragma: no cover - the spec always has headings
        fail("section-refs: no section IDs harvested; heading format changed?")

    n = 0
    for src in md_files:
        if src.name == "CHANGELOG.md":
            continue
        for ref in set(_SECTION_REF_RE.findall(src.read_text(encoding="utf-8"))):
            if ref.upper() not in valid:
                fail(f"{src}: dead section reference §{ref} "
                     "(no heading defines it)")
            n += 1
    return n


def _check_field_profiles() -> int:
    """Every selectable field profile (non-underscore, non-README) must
    declare `field:` == basename + a description, and carry the four
    template sections the engine consumes (ENGINE.md §2.2)."""
    required_sections = ("## Reviewer concerns", "## Field consensuses",
                         "## Common failure modes", "## Evidence bar")
    n = 0
    profiles_dir = REPO / "field-profiles"
    for p in sorted(profiles_dir.glob("*.md")):
        # README (canonical + `.zh.md` translations) and `_scaffold` files are
        # documentation/templates, not selectable `--field` profiles. Translations
        # follow the `X.zh.md` convention and are governed by docs/languages.json,
        # not the field-profile schema, so they must be skipped here.
        if p.name == "README.md" or p.name.startswith("_") or p.name.endswith(".zh.md"):
            continue
        text = p.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if fm is None:
            fail(f"{p} has no YAML frontmatter")
        if fm.get("field") != p.stem:
            fail(f"{p} frontmatter field={fm.get('field')!r} != {p.stem!r}")
        if not str(fm.get("description", "")).strip():
            fail(f"{p} frontmatter missing 'description:'")
        for section in required_sections:
            if section not in text:
                fail(f"{p} missing required section '{section}'")
        n += 1
    return n


def check_crossrefs() -> str:
    md_files = _content_md_files()
    anchors = _check_anchors(md_files)
    citations = _check_example_citations()
    flags = _check_command_flags()
    profiles = _check_field_profiles()
    sections = _check_section_refs(md_files)
    return (f"cross-refs OK ({anchors} anchors, {citations} example "
            f"citations, {flags} command flags, {profiles} field profiles, "
            f"{sections} section refs)")


def check_i18n() -> str:
    try:
        stats = validate_i18n(
            REPO, PRESET_REQUIRED_KEYS, VERDICT_ROLES, ROOT_KINDS
        )
    except I18nError as exc:
        fail(f"i18n: {exc}")
    return (f"i18n OK ({stats.pairs} pairs, {stats.canonical_only} "
            f"canonical-only docs, {stats.digests} digests, "
            f"{stats.sections} aligned sections, "
            f"{stats.machine_tokens} machine-token checks)")


def main() -> int:
    for name, check in [
        ("manifests", check_manifests),
        ("skills", check_skills),
        ("presets", check_presets),
        ("commands", check_commands),
        ("tools", check_tools_syntax),
        ("cross-refs", check_crossrefs),
        ("i18n", check_i18n),
    ]:
        msg = check()
        print(f"  [ok] {msg}")
    print("validate_plugin: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
