#!/usr/bin/env python3
"""Generate the cc-tree radial diagram (SVG): one converged run, drawn as a tree.

The picture is a circular cladogram — the shape of a radial tree of life —
of ONE run of ONE preset, in the engine's own terms (docs/ENGINE.md):

- the ROOT sits at the centre; depth grows outward as concentric rings;
- every expansion runs all 12 framings (§3.A–§3.L), so every node that grew
  has 12 children, one per framing (§0.1 allows more; the picture keeps 12);
- a node grows children only when at least one of them scores `advances`
  (§0.1), and only `advances` nodes are re-expanded (§5.3) — so branches stop
  at different rings;
- the run is CONVERGED (§6.1): every `advances` node was re-expanded, the ones
  whose re-expansion found no `advances` child are tips, no tip is `blocked`,
  and a §3.K high-risk branch exists.

`validate_model()` enforces exactly those rules on the hard-coded tree, so an
edit that draws a state the engine cannot reach fails before anything is
written. The four presets are not clades of one tree — a run uses one preset —
so they appear as the vocabulary table under the tree (§5.2).

Run:  python3 tools/gen_radial_tree.py
Out:  docs/assets/cc-tree-radial-tree.svg
"""
import html
import math
import os
import xml.etree.ElementTree as ET

# ---- canvas + geometry ----------------------------------------------------
W, H = 1440, 1215
CX, CY = 720.0, 610.0          # centre of the radial tree
ROOT_R = 46.0                  # root circle radius
RING = {1: 150.0, 2: 285.0, 3: 410.0}    # radius per depth
SPAN = (287.0, 613.0)          # tips spread clockwise over this; the gap left of the
                               # root (253-287 deg) carries the root arrow and the ruler
RULER = 279.0                  # angle of the depth ruler, inside the gap
D1_WEIGHT = 1.5                # a depth-1 tip gets this much more room: ring 1 is short
TIP_OFF = 16.0                 # verdict marker sits this far outside its tip
FRAMINGS = "ABCDEFGHIJKL"      # §3.A–§3.L


def esc(s: str) -> str:
    """XML-escape text/attribute content."""
    return html.escape(str(s), quote=True)


# ---- theme ----------------------------------------------------------------
# Neutral ink, cards, rings and leader lines are CSS classes so the SVG follows
# the viewer's colour scheme (GitHub shows a README image in an <img>, where the
# SVG's own prefers-color-scheme query still applies). Branch and verdict
# colours are literal: they read on both.
THEME_CSS = """
.bg{fill:#ffffff}.ink{fill:#222}.sub{fill:#666}.body{fill:#444}.muted{fill:#888}
.card{fill:#ffffff;stroke:#bbb}.ring{stroke:#d4d4d4}.lead{stroke:#888}
.leadfill{fill:#888}.tick{fill:#999}.hole{fill:#ffffff}.rule{stroke:#ddd}
@media (prefers-color-scheme: dark){
.bg{fill:#0d1117}.ink{fill:#e6edf3}.sub{fill:#9da7b3}.body{fill:#c9d1d9}
.muted{fill:#8b949e}.card{fill:#161b22;stroke:#3d444d}.ring{stroke:#30363d}
.lead{stroke:#8b949e}.leadfill{fill:#8b949e}.tick{fill:#6e7681}.hole{fill:#0d1117}
.rule{stroke:#30363d}}
"""
BRANCH = "#3d85c6"


# Angle convention: 0 deg = up (12 o'clock), increasing CLOCKWISE. Angles stay
# unwrapped (an arc from 300 to 400 is fine): pt() goes through sin/cos.
def pt(theta_deg, r):
    a = math.radians(theta_deg)
    return (CX + r * math.sin(a), CY - r * math.cos(a))


def fmt(p):
    return f"{p[0]:.2f},{p[1]:.2f}"


def arc(a1, a2, r):
    """SVG path for an arc at radius r from angle a1 to a2 (a1 <= a2, clockwise)."""
    if a2 - a1 < 1e-6:
        return ""
    large = 1 if a2 - a1 > 180 else 0
    return f"M {fmt(pt(a1, r))} A {r:.2f} {r:.2f} 0 {large} 1 {fmt(pt(a2, r))}"


# ---- the run --------------------------------------------------------------
# Verdict codes: A=advances, K=kept, P=pruned, B=blocked (§5.2 roles).
# grow(...) is an `advances` node that was re-expanded and kept its 12
# children; a leaf is a tip. The tree below: the root's 12 framings give three
# `advances` children — A and D grow, K's re-expansion finds nothing new and it
# stays a tip (the §3.K high-risk branch §6.1 condition 5 asks for); A's
# children give two more, one of which (A·C) grows once more.
def leaf(v):
    return {"v": v, "children": []}


def grow(verdicts):
    """An `advances` node with one child per framing; a verdict code per child,
    or a nested grow(...) for a child that grew in turn."""
    kids = [k if isinstance(k, dict) else leaf(k) for k in verdicts]
    return {"v": "A", "children": kids}


ROOT = {"v": None, "children": grow([
    grow(["P", "K", grow(["K", "P", "A", "P", "K", "A", "P", "K", "P", "P", "K", "P"]),
          "K", "P", "A", "P", "K", "P", "A", "K", "P"]),     # A: first-principles
    "P",                                                       # B: inversion
    "K",                                                       # C: cross-disciplinary
    grow(["K", "A", "P", "P", "K", "P", "K", "P", "P", "K", "P", "P"]),  # D: red team
    "P", "K", "P", "K", "P", "K",                               # E–J
    "A",                                                       # K: high-risk, exhausted
    "P",                                                       # L: meta
])["children"]}

# Preset vocabulary for the four roles (ENGINE.md §5.2, verbatim).
PRESETS = [
    ("brainstorm", "#6aa84f", ("PROMISING", "MARGINAL", "DEAD-END", "NEEDS-MORE-INFO")),
    ("attack", "#cc4125", ("CONFIRMED", "MARGINAL", "REFUTED", "INCOMPLETE_FORBIDDEN")),
    ("design", "#8e7cc3", ("RECOMMENDED", "VIABLE", "NOT-RECOMMENDED", "NEEDS-MORE-INFO")),
    ("code-audit", "#a6794c", ("CONFIRMED", "MARGINAL", "REFUTED", "INCOMPLETE_FORBIDDEN")),
]

VERDICT = {
    "A": dict(color="#2e7d32", role="advances",
              text="advances — score ≥ 11; re-expanded. A tip only once its own re-expansion found nothing new"),
    "K": dict(color="#e69138", role="kept",
              text="kept — score 8–10; stays in the tree, not re-expanded"),
    "P": dict(color="#9e9e9e", role="pruned",
              text="pruned — score ≤ 7; derivation kept for reference, not re-expanded"),
    "B": dict(color="#cc0000", role="blocked",
              text="blocked — incomplete; must be finished, never counts as a tip (none left once converged)"),
}


def verdict_marker(x, y, code, R=7.0):
    """Font-independent drawn marker so it renders identically everywhere."""
    c = VERDICT[code]["color"]
    if code == "P":  # pruned: hollow circle with an x
        d = R * 0.45
        return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{R:.1f}" class="hole" '
                f'stroke="{c}" stroke-width="1.7"/>'
                f'<path d="M{x-d:.1f},{y-d:.1f} L{x+d:.1f},{y+d:.1f} '
                f'M{x-d:.1f},{y+d:.1f} L{x+d:.1f},{y-d:.1f}" '
                f'stroke="{c}" stroke-width="1.7" stroke-linecap="round"/>')
    s = [f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{R:.1f}" fill="{c}"/>']
    if code == "A":   # advances: white check
        s.append(f'<path d="M{x-R*0.45:.1f},{y:.1f} L{x-R*0.1:.1f},{y+R*0.4:.1f} '
                 f'L{x+R*0.5:.1f},{y-R*0.4:.1f}" fill="none" stroke="#fff" '
                 f'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>')
    elif code == "K":  # kept: white equals sign
        for dy in (-R * 0.28, R * 0.28):
            s.append(f'<line x1="{x-R*0.45:.1f}" y1="{y+dy:.1f}" x2="{x+R*0.45:.1f}" '
                     f'y2="{y+dy:.1f}" stroke="#fff" stroke-width="1.7" stroke-linecap="round"/>')
    elif code == "B":  # blocked: white slash
        d = R * 0.5
        s.append(f'<line x1="{x-d:.1f}" y1="{y+d:.1f}" x2="{x+d:.1f}" y2="{y-d:.1f}" '
                 f'stroke="#fff" stroke-width="1.9" stroke-linecap="round"/>')
    return "".join(s)


# ---- model checks -----------------------------------------------------------
def walk(node, depth=0):
    yield node, depth
    for c in node["children"]:
        yield from walk(c, depth + 1)


def validate_model():
    """Refuse a tree the engine could not have produced at convergence."""
    if not ROOT["children"]:
        raise ValueError("the root must have grown")
    for node, depth in walk(ROOT):
        kids = node["children"]
        if depth > max(RING):
            raise ValueError(f"depth {depth} exceeds the ring table (max {max(RING)})")
        if node["v"] is not None and node["v"] not in VERDICT:
            raise ValueError(f"unknown verdict {node['v']!r}")
        if node["v"] == "B":
            raise ValueError("a converged tree has no blocked node (§6.1 condition 1)")
        if kids:
            if node["v"] not in (None, "A"):
                raise ValueError("only an advances node is re-expanded (§5.3)")
            if len(kids) != len(FRAMINGS):
                raise ValueError("an expansion yields one child per framing (§0.1)")
            if not any(k["v"] == "A" for k in kids):
                raise ValueError("a node grows children only if one of them advances (§0.1)")
    # §6.1 condition 5 asks for a scored §3.K (high-risk) branch: the root's K child.
    if ROOT["children"][FRAMINGS.index("K")]["v"] not in VERDICT:
        raise ValueError("no scored §3.K branch")


# ---- layout -------------------------------------------------------------
def layout():
    """Tips spread evenly over SPAN in tree order; a parent sits at the middle
    of its children's angles."""
    tips = [(n, d) for n, d in walk(ROOT) if not n["children"]]
    weights = [D1_WEIGHT if d == 1 else 1.0 for _, d in tips]
    lo, hi = SPAN
    step = (hi - lo) / sum(weights)
    at = lo
    for (t, _), w in zip(tips, weights):
        t["angle"] = at + step * w / 2
        at += step * w

    def settle(node):
        if node["children"]:
            angles = [settle(c) for c in node["children"]]
            node["angle"] = (min(angles) + max(angles)) / 2
        return node["angle"]
    settle(ROOT)
    return [t for t, _ in tips]


def build() -> tuple[str, dict]:
    """Render the SVG; returns (svg_text, stats)."""
    validate_model()
    tips = layout()
    nodes = list(walk(ROOT))
    n_total = len(nodes)
    width = sum(1 for t in tips if t["v"] != "B")
    depth = max(d for _, d in nodes)
    svg = []
    add = svg.append

    add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif">')
    add(f'<defs><style>{THEME_CSS}</style>'
        '<marker id="arrow" markerWidth="9" markerHeight="9" refX="7" refY="3" '
        'orient="auto"><path d="M0,0 L7,3 L0,6 Z" class="leadfill"/></marker></defs>')
    add(f'<rect width="{W}" height="{H}" class="bg"/>')

    # ---- title ----------------------------------------------------------
    add(f'<text x="{CX}" y="44" text-anchor="middle" font-size="28" font-weight="700" '
        f'class="ink">cc-tree &#8212; one run, grown as a radial tree</text>')
    add(f'<text x="{CX}" y="72" text-anchor="middle" font-size="15" class="sub">'
        f'every expansion tries all 12 framings &#183; only advances children grow further '
        f'&#183; it stops on §6 convergence, not a node budget</text>')
    add(f'<text x="{CX}" y="96" text-anchor="middle" font-size="14" font-weight="700" '
        f'class="body">this run: CONVERGED &#183; n = {n_total} nodes &#183; width = {width} tips '
        f'&#183; depth {depth}</text>')

    # ---- depth rings + ruler ----------------------------------------------
    for d, r in RING.items():
        add(f'<circle cx="{CX}" cy="{CY}" r="{r}" fill="none" class="ring" '
            f'stroke-width="1" stroke-dasharray="2 6"/>')
        px, py = pt(RULER, r)
        add(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2.4" class="tick"/>')
        add(f'<text x="{px-8:.1f}" y="{py-6:.1f}" text-anchor="end" font-size="12" '
            f'class="muted">depth {d}</text>')

    # ---- branches ----------------------------------------------------------
    def draw(node, d):
        r = RING[d] if d else ROOT_R
        if node["children"]:
            cang = [c["angle"] for c in node["children"]]
            if d:  # the parent's own arc, spanning its children
                add(f'<path d="{arc(min(cang), max(cang), r)}" fill="none" '
                    f'stroke="{BRANCH}" stroke-width="2"/>')
            for c in node["children"]:
                x1, y1 = pt(c["angle"], r)
                x2, y2 = pt(c["angle"], RING[d + 1])
                add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                    f'stroke="{BRANCH}" stroke-width="1.8"/>')
                draw(c, d + 1)
            if d:  # open dot: an advances node that grew children
                x, y = pt(node["angle"], r)
                add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" class="hole" '
                    f'stroke="{BRANCH}" stroke-width="2.2"/>')
        else:
            x, y = pt(node["angle"], r)
            add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5" fill="{BRANCH}"/>')
            gx, gy = pt(node["angle"], r + TIP_OFF)
            add(verdict_marker(gx, gy, node["v"]))
    draw(ROOT, 0)

    # framing letters on the root's twelve children: beyond the verdict marker
    # on a tip, beside the open dot on a node that grew (off its branch line)
    for letter, c in zip(FRAMINGS, ROOT["children"]):
        if c["children"]:
            lx, ly = pt(c["angle"] + 5, RING[1] - 16)
        else:
            lx, ly = pt(c["angle"], RING[1] + TIP_OFF + 17)
        add(f'<text x="{lx:.1f}" y="{ly+4:.1f}" text-anchor="middle" font-size="12" '
            f'font-weight="700" class="body">{letter}</text>')

    # ---- ROOT -------------------------------------------------------------
    add(f'<circle cx="{CX}" cy="{CY}" r="{ROOT_R}" fill="#37474f"/>')
    add(f'<text x="{CX}" y="{CY-4}" text-anchor="middle" font-size="18" font-weight="700" '
        f'fill="#fff">ROOT</text>')
    add(f'<text x="{CX}" y="{CY+14}" text-anchor="middle" font-size="10" '
        f'fill="#cfd8dc">your input</text>')

    # ---- call-outs: every arrow ends on the thing it names ------------------
    def callout(x, y, w, title, lines, target=None, side=None):
        h = 34 + 18 * len(lines)
        add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" class="card" '
            f'stroke-width="1.2"/>')
        add(f'<text x="{x+14}" y="{y+24}" font-size="15" font-weight="700" '
            f'class="ink">{esc(title)}</text>')
        for i, ln in enumerate(lines):
            add(f'<text x="{x+14}" y="{y+44+i*18}" font-size="12.5" class="body">{esc(ln)}</text>')
        if target:
            tx, ty = target
            bx = {"right": x + w, "left": x}.get(side, min(max(tx, x + 18), x + w - 18))
            by = {"bottom": y + h, "top": y}.get(side, y + h / 2)
            add(f'<line x1="{bx:.1f}" y1="{by:.1f}" x2="{tx:.1f}" y2="{ty:.1f}" class="lead" '
                f'stroke-width="1.3" marker-end="url(#arrow)"/>')

    # Arrow targets sit on the tree's outer edge, so no leader crosses a branch:
    # the node callout points at the last advances tip among A's children (upper
    # right), the width callout at a tip of D (lower right), the framings
    # callout at the letter of a depth-1 tip in the lower left.
    a_node = ROOT["children"][0]
    node_tip = [c for c in a_node["children"] if c["v"] == "A" and not c["children"]][-1]
    d_node = ROOT["children"][FRAMINGS.index("D")]
    width_tip = d_node["children"][len(d_node["children"]) * 2 // 3]
    h_child = ROOT["children"][FRAMINGS.index("H")]

    callout(30, int(CY) - 52, 300, "root — your input",
            ["A topic, a document, a code path or a",
             "design prompt. Depth 0; the tree grows",
             "outward from it."],
            target=pt(270, ROOT_R + 4), side="right")
    callout(30, 840, 300, "12 framings (§3.A–§3.L)",
            ["Every expansion runs all twelve, so a",
             "node that grows gets one child per",
             "framing — here the root's are lettered",
             "A–L: first-principles, inversion, … ,",
             "K high-risk, L meta."],
            target=pt(h_child["angle"], RING[1] + TIP_OFF + 26), side="top")
    callout(W - 330, 150, 300, "node — one thought",
            ["An idea, critique, option or finding with",
             "the same 12-field derivation (§4), five",
             "0–3 scores (§5.1) and a verdict (§5.2).",
             "An open dot is an advances node that",
             "grew its own twelve children."],
            target=pt(node_tip["angle"], RING[2] + TIP_OFF + 9), side="bottom")
    callout(30, 300, 300, "depth — the rings",
            ["How far a node is from the root. Only",
             "advances nodes grow outward, so",
             "branches stop on different rings; this",
             f"run reaches depth {depth}."],
            target=pt(RULER, RING[3] + 4), side="bottom")
    callout(W - 330, 900, 300, "width — the tips",
            [f"Every terminal tip, wherever it lands: {width}",
             "here. kept and pruned tips count where",
             "they stop; an advances tip counts once",
             "its re-expansion found nothing new;",
             "a blocked node never counts."],
            target=pt(width_tip["angle"], RING[2] + TIP_OFF + 9), side="left")

    # ---- legend: the four roles, then the preset vocabulary ----------------
    y0 = 1078
    add(f'<line x1="60" y1="{y0-22}" x2="{W-60}" y2="{y0-22}" class="rule" stroke-width="1"/>')
    for i, code in enumerate(("A", "K", "P", "B")):
        yy = y0 + i * 24
        add(verdict_marker(80, yy - 4, code))
        add(f'<text x="96" y="{yy}" font-size="13" class="body">{esc(VERDICT[code]["text"])}</text>')
    add(f'<circle cx="80" cy="{y0 + 4*24 - 4}" r="5" class="hole" stroke="{BRANCH}" stroke-width="2.2"/>')
    add(f'<text x="96" y="{y0 + 4*24}" font-size="13" class="body">open dot — an advances '
        f'node that grew children (only advances nodes grow)</text>')

    tx = 820
    add(f'<text x="{tx}" y="{y0-2}" font-size="13" font-weight="700" class="ink">'
        f'One engine, four presets — a run uses one; the roles are the same, the words differ (§5.2)</text>')
    heads = ("preset", "advances", "kept", "pruned")
    cols = (tx, tx + 110, tx + 225, tx + 320)
    for cx_, h_ in zip(cols, heads):
        add(f'<text x="{cx_}" y="{y0+22}" font-size="12" font-weight="700" class="muted">{h_}</text>')
    for i, (name, color, words) in enumerate(PRESETS):
        yy = y0 + 44 + i * 20
        add(f'<text x="{cols[0]}" y="{yy}" font-size="12.5" font-weight="700" fill="{color}">{name}</text>')
        for cx_, wd in zip(cols[1:], words[:3]):
            add(f'<text x="{cx_}" y="{yy}" font-size="12" class="body">{wd}</text>')
    add('</svg>')
    stats = dict(tips=len(tips), width=width, n=n_total, max_depth=depth)
    return "\n".join(svg), stats


def main() -> int:
    svg_text, stats = build()
    ET.fromstring(svg_text)  # well-formedness gate before anything is written
    out_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "assets")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.normpath(os.path.join(out_dir, "cc-tree-radial-tree.svg"))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg_text)
    print("wrote", out_path)
    print("tips =", stats["tips"], "width =", stats["width"], "n =", stats["n"],
          "max depth =", stats["max_depth"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
