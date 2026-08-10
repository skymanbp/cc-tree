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

from _frontmatter import FrontmatterError, parse_frontmatter, split_frontmatter
from _i18n import FLAG_RE, I18nError, is_skipped, load_manifest, validate_i18n

REPO = Path(__file__).resolve().parent.parent


class ValidationError(Exception):
    """A check failed. Check helpers raise this (via `fail`); only the
    CLI boundary in `main` turns it into stderr output + a non-zero exit,
    so the checks stay importable and testable without process games."""

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
    raise ValidationError(msg)


def _read_json_object(path: Path) -> dict:
    """Load a JSON file whose root must be an object, converting every
    I/O and decode failure into a clean check failure (a missing
    plugin.json previously escaped as a raw FileNotFoundError traceback)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        fail(f"{path} is unreadable: {e}")
    except ValueError as e:  # JSONDecodeError and UnicodeDecodeError both
        fail(f"{path} is not valid JSON: {e}")
    if not isinstance(data, dict):
        fail(f"{path} top level must be a JSON object")
    return data


def _read_frontmatter(path: Path) -> dict | None:
    """Parse a file's frontmatter, converting parser rejections into
    check failures that name the offending file."""
    try:
        return parse_frontmatter(path.read_text(encoding="utf-8"))
    except FrontmatterError as e:
        fail(f"{path}: frontmatter: {e}")


def _read_split(path: Path) -> tuple[dict | None, str]:
    try:
        return split_frontmatter(path.read_text(encoding="utf-8"))
    except FrontmatterError as e:
        fail(f"{path}: frontmatter: {e}")


def check_manifests() -> str:
    plugin = _read_json_object(REPO / ".claude-plugin" / "plugin.json")
    market = _read_json_object(REPO / ".claude-plugin" / "marketplace.json")
    for key in ("name", "version", "description"):
        value = plugin.get(key)
        if not isinstance(value, str) or not value.strip():
            fail(f"plugin.json '{key}' must be a non-empty string "
                 f"(got {value!r})")
    plugin_v = plugin["version"]
    market_v = market.get("metadata", {}).get("version")
    if market_v != plugin_v:
        fail(f"marketplace.json metadata.version ({market_v!r}) != "
             f"plugin.json version ({plugin_v!r})")
    entries = market.get("plugins", [])
    if not isinstance(entries, list) or any(
            not isinstance(p, dict) for p in entries):
        fail("marketplace.json plugins[] must be a list of objects")
    inner = next((p for p in entries if p.get("name") == plugin["name"]), None)
    if inner is None:
        fail(f"marketplace.json plugins[] has no entry named {plugin['name']!r}")
    if inner.get("version") != plugin_v:
        fail(f"marketplace.json plugins[].version ({inner.get('version')!r}) != "
             f"plugin.json version ({plugin_v!r})")
    return f"manifests OK (version {plugin_v})"


def _check_md_frontmatter(path: Path, required_keys: tuple[str, ...],
                          name_must_match: str | None) -> None:
    fm = _read_frontmatter(path)
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


# Output artifact values are bare Markdown filenames written under the
# run's `<out>/` directory (docs/ENGINE.md §7, skills/tree/SKILL.md) — a
# separator or `..` would let a preset write outside it.
_ARTIFACT_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\.md\Z")
# docs/presets.md §1 (`score_dims`): "`key` is 1–3 letters used in score
# reports".
_SCORE_KEY_RE = re.compile(r"[A-Za-z]{1,3}\Z")


def _req_str(value: object, what: str, pfail) -> str:
    """The field must actually BE a non-empty string: the parser can produce
    nested dicts/lists where the schema expects a scalar, and str()-coercion
    previously let those pass as truthy (or crash the
    `convergence_metric in verdict_enum` test with a TypeError)."""
    if not isinstance(value, str) or not value.strip():
        pfail(f"{what} must be a non-empty string (got {value!r})")
    return value


def _validate_identity(path: Path, fm: dict, pfail) -> None:
    """Rules 1-3: required keys, name==basename, scalar prose, root_kind."""
    for key in PRESET_REQUIRED_KEYS:
        if key not in fm or fm[key] in ("", None, [], {}):
            pfail(f"frontmatter missing or empty '{key}:'")
    if fm.get("name") != path.stem:
        pfail(f"frontmatter name={fm.get('name')!r} != expected {path.stem!r}")
    _req_str(fm["description"], "description", pfail)
    _req_str(fm["subject_label"], "subject_label", pfail)
    if fm["root_kind"] not in ROOT_KINDS:
        pfail(f"root_kind={fm['root_kind']!r} not in {ROOT_KINDS}")


def _validate_verdicts(fm: dict, pfail) -> None:
    """Rules 4-5: exactly the four roles, distinct non-empty labels
    (duplicates would make verdicts ambiguous in every report that prints
    them), and a convergence_metric naming one of the roles."""
    ve = fm["verdict_enum"]
    if not isinstance(ve, dict):
        pfail("verdict_enum must be a mapping of the 4 roles")
    if set(ve) != set(VERDICT_ROLES):
        pfail(f"verdict_enum roles {sorted(ve)} != required {sorted(VERDICT_ROLES)}")
    for role, label in ve.items():
        _req_str(label, f"verdict_enum.{role}", pfail)
    if len(set(ve.values())) != len(ve):
        pfail(f"verdict_enum labels must be distinct (got {sorted(ve.values())})")
    cm = _req_str(fm["convergence_metric"], "convergence_metric", pfail)
    if cm not in ve:
        pfail(f"convergence_metric={cm!r} not in verdict_enum roles {sorted(ve)}")


def _validate_score_dims(fm: dict, pfail) -> None:
    """Rule 6: exactly 5 {key, name, desc} dims; keys are 1-3 letters
    (docs/presets.md §1) and unique — the five-term score line `S=3 N=2 …`
    is unreadable with duplicate keys."""
    sd = fm["score_dims"]
    if not isinstance(sd, list) or len(sd) != SCORE_DIMS_LEN:
        n = len(sd) if isinstance(sd, list) else "not-a-list"
        pfail(f"score_dims must have exactly {SCORE_DIMS_LEN} entries (got {n})")
    for idx, dim in enumerate(sd):
        if not isinstance(dim, dict):
            pfail(f"score_dims[{idx}] is not a mapping ({{key, name, desc}})")
        for sub in ("key", "name", "desc"):
            _req_str(dim.get(sub, ""), f"score_dims[{idx}].{sub}", pfail)
        if not _SCORE_KEY_RE.fullmatch(dim["key"]):
            pfail(f"score_dims[{idx}].key={dim['key']!r} must be 1-3 letters")
    keys = [dim["key"] for dim in sd]
    if len(set(keys)) != len(keys):
        pfail(f"score_dims keys must be distinct (got {keys})")


def _validate_node_schema(fm: dict, pfail) -> None:
    """Rule 7: exactly 12 distinct non-empty strings (they become the 12
    JSON object keys of every node)."""
    ns = fm["node_schema"]
    if not isinstance(ns, list) or len(ns) != NODE_SCHEMA_LEN:
        n = len(ns) if isinstance(ns, list) else "not-a-list"
        pfail(f"node_schema must have exactly {NODE_SCHEMA_LEN} entries (got {n})")
    for idx, field in enumerate(ns):
        _req_str(field, f"node_schema[{idx}]", pfail)
    if len(set(ns)) != len(ns):
        pfail("node_schema field names must be distinct")


def _validate_artifacts(fm: dict, pfail) -> None:
    """Rule 8: 'primary' plus optional 'secondary' map, every value a bare
    .md filename confined to the run's out-dir."""
    oa = fm["output_artifacts"]
    if not isinstance(oa, dict):
        pfail("output_artifacts must be a mapping")
    primary = _req_str(oa.get("primary", ""), "output_artifacts.primary", pfail)
    if not _ARTIFACT_NAME_RE.fullmatch(primary):
        pfail(f"output_artifacts.primary={primary!r} must be a bare "
              "*.md filename (no path separators)")
    secondary = oa.get("secondary", {})
    if not isinstance(secondary, dict):
        pfail("output_artifacts.secondary must be a mapping")
    for skey, sval in secondary.items():
        _req_str(sval, f"output_artifacts.secondary.{skey}", pfail)
        if not _ARTIFACT_NAME_RE.fullmatch(sval):
            pfail(f"output_artifacts.secondary.{skey}={sval!r} must be a "
                  "bare *.md filename (no path separators)")


def validate_preset_schema(path: Path, fm: dict) -> None:
    """Enforce the preset compliance rules promised in docs/ENGINE.md §10-§11
    and docs/presets.md §1. `fm` is the parsed frontmatter mapping."""
    def pfail(msg: str) -> None:
        fail(f"{path}: {msg}")

    _validate_identity(path, fm, pfail)
    _validate_verdicts(fm, pfail)
    _validate_score_dims(fm, pfail)
    _validate_node_schema(fm, pfail)
    _validate_artifacts(fm, pfail)


def check_presets() -> str:
    presets_dir = REPO / "presets"
    if not presets_dir.is_dir():
        return "presets OK (no presets/ dir — optional)"
    files = sorted(p for p in presets_dir.glob("*.md") if p.name != "README.md")
    if not files:
        fail(f"{presets_dir} has no preset .md files (other than README.md)")
    for f in files:
        fm = _read_frontmatter(f)
        if fm is None:
            fail(f"{f} has no YAML frontmatter (--- ... ---) at top")
        validate_preset_schema(f, fm)
    return f"presets OK ({len(files)} presets, frontmatter schema)"


def check_commands() -> str:
    commands_dir = REPO / "commands"
    if not commands_dir.is_dir():
        return "commands OK (no commands/ dir — optional)"
    files = sorted(p for p in commands_dir.glob("*.md") if p.name != "README.md")
    if not files:
        return "commands OK (no command .md files — optional)"
    for f in files:
        _check_md_frontmatter(f, ("description",), None)
    # Wrapper parity: every shipped preset must keep its like-named slash
    # command (README advertises the pairing; deleting one wrapper
    # previously left a validator-approved package that contradicted it).
    # Extra commands without a preset (tree-chain) are fine.
    command_names = {f.stem for f in files}
    wrappers = 0
    for preset in sorted((REPO / "presets").glob("*.md")):
        if preset.name == "README.md":
            continue
        if preset.stem not in command_names:
            fail(f"presets/{preset.name} has no command wrapper "
                 f"commands/{preset.stem}.md")
        wrappers += 1
    return f"commands OK ({len(files)} commands, {wrappers} preset wrappers)"


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
# Most defects this repo has shipped were mechanical drift between files, not
# logic errors. Each sub-check below turns one such class — dead anchors,
# out-of-bounds example citations, undocumented command flags, malformed field
# profiles, dead §-references — into a CI failure.

_LINK_RE = re.compile(r"\]\(([^)#\s]+)#([^)\s]+)\)")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
_CITATION_RE = re.compile(r"([A-Za-z0-9_.\-/]+\.md):(\d+)(?:-(\d+))?")
# Deliberately stricter than _i18n's inline-code pattern: this one must not
# span lines, so one stray backtick cannot blank out half a document.
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
    return [p for p in sorted(REPO.rglob("*.md"))
            if not is_skipped(p.relative_to(REPO).parts)]


def _slugify(heading: str) -> str:
    """GitHub-style heading slug: drop code ticks, lowercase, strip
    punctuation (keep word chars / spaces / hyphens), spaces -> hyphens."""
    text = heading.replace("`", "").lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def _heading_slugs(text: str) -> set[str]:
    """All GitHub-resolvable heading slugs in `text`, including the `-1`,
    `-2`, … suffixes GitHub appends to repeated headings — without them a
    perfectly valid `#repeat-1` link was reported as dead."""
    counts: dict[str, int] = {}
    slugs: set[str] = set()
    for _, heading in _HEADING_RE.findall(text):
        base = _slugify(heading)
        seen = counts.get(base, 0)
        counts[base] = seen + 1
        slugs.add(base if seen == 0 else f"{base}-{seen}")
    return slugs


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
                slug_cache[target] = _heading_slugs(
                    target.read_text(encoding="utf-8"))
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


def _check_skill_flags(repo: Path, required: tuple[str, ...]) -> tuple[str, set[str]]:
    """Validate the tree skill's own hint/body flag agreement.

    Returns `(skill_body, common_flags)` — the flags the skill's
    `argument-hint` advertises form the *common* namespace that wrapper
    commands may document via the skill body.
    """
    skill_path = repo / "skills" / "tree" / "SKILL.md"
    skill_fm, skill_body = _read_split(skill_path)
    skill_hint = str((skill_fm or {}).get("argument-hint", ""))
    common = set(FLAG_RE.findall(skill_hint)) | set(required)
    for flag in set(FLAG_RE.findall(skill_hint)):
        if not _contains_flag(skill_body, flag):
            fail(f"{skill_path}: argument-hint advertises {flag} but the "
                 "skill body does not document it")
    for flag in required:
        if (not _contains_flag(skill_hint, flag)
                or not _contains_flag(skill_body, flag)):
            fail(f"{skill_path}: required common flag {flag} must appear in "
                 "both argument-hint and skill body")
    return skill_body, common


def _check_wrapper_flags(cmd: Path, repo: Path, skill_body: str,
                         common: set[str], required: tuple[str, ...]) -> int:
    """Validate one command wrapper's hint against its own documentation.

    A flag from the skill's common namespace may be documented by the
    skill body; a wrapper-SPECIFIC flag must be documented in the command
    body or its preset body. Searching the skill body for those too let
    `--focus` (an attack-preset flag mentioned in SKILL.md) "document"
    itself in any other wrapper's hint.
    """
    fm, body = _read_split(cmd)
    hint = str((fm or {}).get("argument-hint", ""))
    preset = repo / "presets" / cmd.name
    preset_body = ""
    if preset.is_file():
        _, preset_body = _read_split(preset)
    own_sources = "\n".join((body, preset_body))
    n = 0
    for flag in set(FLAG_RE.findall(hint)):
        sources = ("\n".join((own_sources, skill_body))
                   if flag in common else own_sources)
        if not _contains_flag(sources, flag):
            where = ("neither SKILL.md, the command body, nor "
                     f"{preset.name}" if flag in common
                     else f"neither the command body nor {preset.name}")
            fail(f"{cmd}: argument-hint advertises {flag} but {where} "
                 "documents it outside frontmatter")
        n += 1
    for flag in required:
        if not _contains_flag(hint, flag):
            fail(f"{cmd}: argument-hint omits required common flag {flag}")
    return n


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
    skill_body, common = _check_skill_flags(repo, required)
    return sum(_check_wrapper_flags(cmd, repo, skill_body, common, required)
               for cmd in sorted((repo / "commands").glob("*.md")))


_SECTION_REF_RE = re.compile(r"§\s?(F\d+|\d+(?:\.[0-9A-Za-z]+)?)")
_SECTION_ID_RE = re.compile(r"^§?(F\d+|\d+(?:\.[0-9A-Za-z]+)?)[.\s—-]")


def _section_id_sources() -> list[Path]:
    """Files whose headings define the engine's §-section namespace."""
    return [REPO / "docs" / "ENGINE.md", REPO / "docs" / "ENGINE.zh.md",
            REPO / "skills" / "tree" / "SKILL.md",
            *sorted((REPO / "presets").glob("*.md"))]


def _check_section_refs(md_files: list[Path]) -> int:
    """Every `§N` / `§N.M` / `§FN` prose reference must name a real heading.

    `_check_anchors` cannot cover these: they are prose tokens, not Markdown
    links, so nothing ties them to a heading. Renumbering a section therefore
    used to leave dangling pointers silently.

    The valid namespace is harvested from the headings that define it — the
    engine spec, the skill, and the presets (which add their own `§2.A` /
    `§2.B` baseline modes).

    `CHANGELOG.md` is exempt: naming a pointer it removed is that file's job.
    It is a historical record, not a runtime contract.
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
    required_sections = ("Reviewer concerns", "Field consensuses",
                         "Common failure modes", "Evidence bar")
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
        fm = _read_frontmatter(p)
        if fm is None:
            fail(f"{p} has no YAML frontmatter")
        if fm.get("field") != p.stem:
            fail(f"{p} frontmatter field={fm.get('field')!r} != {p.stem!r}")
        if not str(fm.get("description", "")).strip():
            fail(f"{p} frontmatter missing 'description:'")
        # Compare parsed (level, title) heading pairs, not substrings — the
        # string "## Evidence bar" is contained in "### Evidence bar", so a
        # substring test accepted wrong levels and even commented-out text.
        # Titles may carry an annotation after the section name (the shipped
        # profiles write "Reviewer concerns — feeds §3.C ..."), so the
        # required name matches as a whole-word prefix of the title.
        h2_titles = [title.strip() for hashes, title
                     in _HEADING_RE.findall(text) if len(hashes) == 2]
        for title in required_sections:
            if not any(t == title or t.startswith(title + " ")
                       for t in h2_titles):
                fail(f"{p} missing required level-2 section '## {title}'")
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
    except (I18nError, FrontmatterError) as exc:
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
        try:
            msg = check()
        except ValidationError as exc:
            print(f"FAIL({name}): {exc}", file=sys.stderr)
            return 1
        print(f"  [ok] {msg}")
    print("validate_plugin: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
