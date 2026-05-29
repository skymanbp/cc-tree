#!/usr/bin/env python3
"""Generate the cc-tree "phylogenetic tree of thoughts" radial diagram (SVG).

The picture is a circular cladogram, the same shape as a radial tree-of-life:
one ROOT at the centre, depth growing outward as concentric rings, four
coloured "clades" = the four shipped presets, and terminal leaves (tips)
scattered at *different* depths — because that is the whole point of the
engine: only leaves that score "advances" re-expand into the next ring, so
some branches die after one round (an idea that didn't pan out) while others
keep advancing and run to full depth (a direction worth chasing). The branch
lengths are therefore uneven, exactly like the limbs of a real phylogenetic
tree. Annotated to define the engine's modules: root / node / depth / width /
n / the 12 framings / leaf verdicts.

Run:  python3 tools/gen_radial_tree.py
Out:  docs/assets/cc-tree-radial-tree.svg
"""
import math
import os

# ---- canvas + geometry ----------------------------------------------------
W, H = 1440, 1360
CX, CY = 720.0, 660.0          # centre of the radial tree
ROOT_R = 50.0                  # root circle radius
RING0 = 92.0                   # radius of the root's "shoulder" connector arc
RING = {1: 172.0, 2: 254.0, 3: 336.0, 4: 418.0}   # radius per depth
RMAX = RING[4]

# Angle convention: 0 deg = up (12 o'clock), increasing CLOCKWISE.
def pt(theta_deg, r):
    a = math.radians(theta_deg)
    return (CX + r * math.sin(a), CY - r * math.cos(a))

def fmt(p):
    return f"{p[0]:.2f},{p[1]:.2f}"

def arc(a1, a2, r):
    """SVG path for an arc at radius r from angle a1 to a2 (clockwise convention)."""
    if abs(a2 - a1) < 1e-6:
        return ""  # degenerate single-child arc -> nothing to draw
    sweep = 1 if a2 >= a1 else 0
    large = 1 if abs(a2 - a1) > 180 else 0
    return f"M {fmt(pt(a1, r))} A {r:.2f} {r:.2f} 0 {large} {sweep} {fmt(pt(a2, r))}"

def annulus_sector(a1, a2, r_in, r_out):
    """Filled annulus-sector path (a coloured 'clade' wedge)."""
    return (f"M {fmt(pt(a1, r_out))} "
            f"A {r_out:.2f} {r_out:.2f} 0 0 1 {fmt(pt(a2, r_out))} "
            f"L {fmt(pt(a2, r_in))} "
            f"A {r_in:.2f} {r_in:.2f} 0 0 0 {fmt(pt(a1, r_in))} Z")

# ---- tree spec ------------------------------------------------------------
# Verdict codes: A=advances, K=kept, P=pruned, B=blocked.
# An *internal* node is one that scored "advances" and therefore re-expanded;
# we render it with the small open node-dot. A *leaf* (no children) carries a
# verdict glyph: A-leaves are the live frontier (would re-expand, but the tree
# hit substantive convergence); K/P/B leaves are terminal by decision.
def lf(v):            # leaf
    return {"v": v, "children": []}
def br(*kids):        # internal node that advanced and re-expanded
    return {"v": "A", "children": list(kids)}

# Each preset's depth-1 children. There is NO single winner: a branch can end
# in "advances" (a direction that paid off — several of these, at different
# depths), dead-end in "pruned"/"blocked", or keep branching and be judged
# again. The shapes deliberately differ in how deep they grow:
#   design     -> shallow: wins early, max depth 2
#   brainstorm -> a deep spine that runs to full depth 4
#   attack / code-audit -> mixed, max depth 3
PRESETS = [
    dict(name="brainstorm", advances="PROMISING", color="#6aa84f", fill="#b6d7a8",
         wedge=(200, 271),
         tree=[lf("P"),                                   # tried, dead end at depth 1
               br(lf("A"), lf("P")),                      # one direction wins, one dies
               br(lf("P"),                                # branch on...
                  br(lf("A"),                             # ...a win at depth 3...
                     br(lf("A"), lf("P"))))]),            # ...and again to full depth 4
    dict(name="attack", advances="CONFIRMED", color="#cc4125", fill="#ea9999",
         wedge=(283, 354),
         tree=[br(lf("A"), lf("B")),
               lf("P"),
               br(br(lf("A"), lf("P")), lf("K"))]),
    dict(name="design", advances="RECOMMENDED", color="#8e7cc3", fill="#d5c6ec",
         wedge=(6, 77),
         tree=[lf("A"),
               br(lf("A"), lf("P")),
               lf("P")]),
    dict(name="code-audit", advances="CONFIRMED", color="#a6794c", fill="#e0cba8",
         wedge=(89, 160),
         tree=[br(lf("A"), lf("P")),
               br(br(lf("B"), lf("A")), lf("K")),
               lf("P")]),
]

VERDICT = {
    "A": dict(color="#2e7d32", label="advances — re-expands (grows deeper)"),
    "K": dict(color="#e69138", label="kept — stays, no re-expand"),
    "P": dict(color="#9e9e9e", label="pruned — kept for reference"),
    "B": dict(color="#cc0000", label="blocked — must be completed"),
}

def verdict_marker(x, y, code, R=8.0):
    """Font-independent drawn marker so it renders identically everywhere."""
    c = VERDICT[code]["color"]
    s = []
    if code == "P":  # pruned: hollow circle with an x
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{R:.1f}" fill="#fff" '
                 f'stroke="{c}" stroke-width="1.8"/>')
        d = R * 0.45
        s.append(f'<path d="M{x-d:.1f},{y-d:.1f} L{x+d:.1f},{y+d:.1f} '
                 f'M{x-d:.1f},{y+d:.1f} L{x+d:.1f},{y-d:.1f}" '
                 f'stroke="{c}" stroke-width="1.8" stroke-linecap="round"/>')
        return "".join(s)
    s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{R:.1f}" fill="{c}"/>')
    if code == "A":   # advances: white check
        s.append(f'<path d="M{x-R*0.45:.1f},{y:.1f} L{x-R*0.1:.1f},{y+R*0.4:.1f} '
                 f'L{x+R*0.5:.1f},{y-R*0.4:.1f}" fill="none" stroke="#fff" '
                 f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>')
    elif code == "K":  # kept: white equals sign
        for dy in (-R*0.28, R*0.28):
            s.append(f'<line x1="{x-R*0.45:.1f}" y1="{y+dy:.1f}" '
                     f'x2="{x+R*0.45:.1f}" y2="{y+dy:.1f}" stroke="#fff" '
                     f'stroke-width="1.8" stroke-linecap="round"/>')
    elif code == "B":  # blocked: white slash (no-entry)
        d = R * 0.5
        s.append(f'<line x1="{x-d:.1f}" y1="{y+d:.1f}" x2="{x+d:.1f}" '
                 f'y2="{y-d:.1f}" stroke="#fff" stroke-width="2" '
                 f'stroke-linecap="round"/>')
    return "".join(s)

# ---- layout helpers -------------------------------------------------------
def collect_leaves(node, out):
    if node["children"]:
        for c in node["children"]:
            collect_leaves(c, out)
    else:
        out.append(node)

def set_angles(node):
    """Post-order: leaf angles are pre-assigned; internal = mean of children."""
    if not node["children"]:
        return node["angle"]
    node["angle"] = sum(set_angles(c) for c in node["children"]) / len(node["children"])
    return node["angle"]

def count_internal(node):
    if not node["children"]:
        return 0
    return 1 + sum(count_internal(c) for c in node["children"])

def max_depth(node, d=1):
    if not node["children"]:
        return d
    return max(max_depth(c, d + 1) for c in node["children"])

svg = []
def add(s):
    svg.append(s)

add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif">')

# defs
add('<defs>')
for p in PRESETS:
    add(f'<radialGradient id="g_{p["name"]}" gradientUnits="userSpaceOnUse" '
        f'fx="{CX}" fy="{CY}" cx="{CX}" cy="{CY}" r="{RMAX}">'
        f'<stop offset="0%" stop-color="{p["fill"]}" stop-opacity="0.12"/>'
        f'<stop offset="100%" stop-color="{p["fill"]}" stop-opacity="0.72"/>'
        f'</radialGradient>')
add('<marker id="arrow" markerWidth="9" markerHeight="9" refX="7" refY="3" '
    'orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="#888"/></marker>')
add('</defs>')

add(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')

# ---- title ----------------------------------------------------------------
add(f'<text x="{CX}" y="48" text-anchor="middle" font-size="30" '
    f'font-weight="700" fill="#222">cc-tree &#8212; a phylogenetic tree of thoughts</text>')
add(f'<text x="{CX}" y="76" text-anchor="middle" font-size="16" fill="#666">'
    f'one universal radial-tree engine &#183; four swappable presets &#183; '
    f'many directions win, some dead-end, the rest keep branching &#8212; '
    f'no single winner</text>')

# ---- depth ring guides (dashed) -------------------------------------------
for d, r in RING.items():
    add(f'<circle cx="{CX}" cy="{CY}" r="{r}" fill="none" stroke="#dadada" '
        f'stroke-width="1" stroke-dasharray="2 6"/>')

# ---- coloured clade wedges ------------------------------------------------
for p in PRESETS:
    a1, a2 = p["wedge"]
    add(f'<path d="{annulus_sector(a1, a2, ROOT_R + 8, RMAX + 16)}" '
        f'fill="url(#g_{p["name"]})" stroke="none"/>')

# ---- draw each preset subtree ---------------------------------------------
def draw_subtree(node, depth, color):
    r = RING[depth]
    if not node["children"]:               # leaf: tip dot + verdict glyph
        x, y = pt(node["angle"], r)
        add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="{color}"/>')
        gx, gy = pt(node["angle"], r + 16)
        add(verdict_marker(gx, gy, node["v"], R=8))
        return
    cr = RING[depth + 1]
    cangles = [c["angle"] for c in node["children"]]
    add(f'<path d="{arc(min(cangles), max(cangles), r)}" fill="none" '
        f'stroke="{color}" stroke-width="2.0"/>')
    for c in node["children"]:
        x1, y1 = pt(c["angle"], r)
        x2, y2 = pt(c["angle"], cr)
        add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{color}" stroke-width="1.9"/>')
        draw_subtree(c, depth + 1, color)
    nx, ny = pt(node["angle"], r)          # internal node-dot (it re-expanded)
    add(f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="4.2" fill="#fff" '
        f'stroke="{color}" stroke-width="2.0"/>')

total_leaves = 0
total_internal = 0
deepest = 1
for p in PRESETS:
    a1, a2 = p["wedge"]
    leaves = []
    for child in p["tree"]:
        collect_leaves(child, leaves)
    n_leaf = len(leaves)
    span = a2 - a1
    margin = span * 0.12
    lo, hi = a1 + margin, a2 - margin
    for i, leaf in enumerate(leaves):
        leaf["angle"] = lo + (hi - lo) * (i + 0.5) / n_leaf
    for child in p["tree"]:
        set_angles(child)
    total_internal += sum(count_internal(c) for c in p["tree"])
    total_leaves += n_leaf
    deepest = max([deepest] + [max_depth(c) for c in p["tree"]])

    # root "shoulder" arc spanning the depth-1 children + stub from root
    d1_angles = [c["angle"] for c in p["tree"]]
    add(f'<path d="{arc(min(d1_angles), max(d1_angles), RING0)}" fill="none" '
        f'stroke="{p["color"]}" stroke-width="2.4"/>')
    mid = (min(d1_angles) + max(d1_angles)) / 2
    rx, ry = pt(mid, ROOT_R + 8)
    sx, sy = pt(mid, RING0)
    add(f'<line x1="{rx:.1f}" y1="{ry:.1f}" x2="{sx:.1f}" y2="{sy:.1f}" '
        f'stroke="{p["color"]}" stroke-width="2.6"/>')
    for child in p["tree"]:
        x1, y1 = pt(child["angle"], RING0)
        x2, y2 = pt(child["angle"], RING[1])
        add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{p["color"]}" stroke-width="1.9"/>')
        draw_subtree(child, 1, p["color"])

    # preset label: a clade name on the OUTER RIM at the wedge mid-angle,
    # beyond every leaf (RMAX is the deepest any branch can reach), so it can
    # never sit on a branch or a verdict glyph however the clade grew.
    lang = (a1 + a2) / 2
    label_r = RMAX + 40
    lx, ly = pt(lang, label_r)
    sub = f'advances = {p["advances"]}'
    halo_w = max(11.5 * len(p["name"]), 7.0 * len(sub)) + 24
    add(f'<rect x="{lx-halo_w/2:.1f}" y="{ly-23:.1f}" width="{halo_w:.1f}" '
        f'height="46" rx="9" fill="#ffffff" fill-opacity="0.82"/>')
    add(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" font-size="22" '
        f'font-weight="700" fill="{p["color"]}">{p["name"]}</text>')
    add(f'<text x="{lx:.1f}" y="{ly + 16:.1f}" text-anchor="middle" '
        f'font-size="11.5" fill="{p["color"]}">{sub}</text>')

# ---- ROOT at the centre ---------------------------------------------------
add(f'<circle cx="{CX}" cy="{CY}" r="{ROOT_R}" fill="#37474f"/>')
add(f'<circle cx="{CX}" cy="{CY}" r="{ROOT_R}" fill="none" stroke="#fff" '
    f'stroke-width="2" stroke-dasharray="3 3"/>')
add(f'<text x="{CX}" y="{CY-8}" text-anchor="middle" font-size="20" '
    f'font-weight="700" fill="#fff">ROOT</text>')
add(f'<text x="{CX}" y="{CY+11}" text-anchor="middle" font-size="10.5" '
    f'fill="#cfd8dc">topic &#183; artifact</text>')
add(f'<text x="{CX}" y="{CY+25}" text-anchor="middle" font-size="10.5" '
    f'fill="#cfd8dc">code &#183; design</text>')

# ---- radial depth ruler (bottom gap, ~185 deg) ----------------------------
# (depth 0 is the ROOT itself at the centre, so the ruler starts at depth 1)
ruler = 185
for r, lbl in [(RING[1], "depth 1"), (RING[2], "depth 2"),
               (RING[3], "depth 3"), (RING[4], "depth 4")]:
    px, py = pt(ruler, r)
    add(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2.4" fill="#aaa"/>')
    add(f'<text x="{px-12:.1f}" y="{py+4:.1f}" text-anchor="end" font-size="11.5" '
        f'fill="#888">{lbl}</text>')

# ======================  ANNOTATION CALL-OUTS  ============================
def callout(x, y, w, h, title, lines, anchor_xy=None, title_color="#222"):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" '
        f'fill="#ffffff" stroke="#bbb" stroke-width="1.2"/>')
    add(f'<text x="{x+14}" y="{y+24}" font-size="15.5" font-weight="700" '
        f'fill="{title_color}">{title}</text>')
    for i, ln in enumerate(lines):
        add(f'<text x="{x+14}" y="{y+46+i*18}" font-size="12.5" fill="#444">{ln}</text>')
    if anchor_xy:
        ex, ey = anchor_xy
        if y < ey < y + h:                  # anchor roughly level -> exit a side
            bx = x + w if ex > x + w else x
            by = y + h / 2
        else:                               # exit top or bottom edge
            by = y + h if ey > y + h / 2 else y
            bx = min(max(ex, x + 18), x + w - 18)
        add(f'<line x1="{bx:.1f}" y1="{by:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" '
            f'stroke="#999" stroke-width="1.3" marker-end="url(#arrow)"/>')

# root callout (top-left). No leader line: the centre is already labelled
# "ROOT", and a corner arrow would have to cut across the attack clade.
callout(34, 150, 264, 110, "root — the input",
        ["What you hand the engine:",
         "a topic, an artifact (file / doc),",
         "a code path, or a design prompt.",
         "The whole tree grows from it."])

def preset(name):
    return next(p for p in PRESETS if p["name"] == name)

# 12-framings callout (left, at root level) -> a depth-1 node in the attack
# clade; the leader runs horizontally through the empty left gap, so it
# crosses no branches.
fram_anchor = pt(preset("attack")["tree"][0]["angle"], RING[1])
callout(34, 516, 264, 110, "12 framings (§3.A–§3.L)",
        ["Each node is expanded by the",
         "same 12 framing passes —",
         "first-principles, inversion,",
         "red-team, contrarian, high-risk…"],
        fram_anchor)

# node callout (right, at root level) -> a depth-1 node in the design clade;
# the leader runs horizontally through the empty right gap.
node_anchor = pt(preset("design")["tree"][1]["angle"], RING[1])
callout(W - 298, 476, 264, 130, "node — one thought",
        ["One idea / critique / option /",
         "finding. Every node gets the",
         "same 12-field derivation, is",
         "scored on 5 dims, and earns a",
         "verdict. No hedging, no defer."],
        node_anchor)

# depth callout (bottom-left). No leader line — the depth ruler and the
# concentric rings right beside it already carry the meaning (an arrow here
# would only collide with the "depth N" labels).
callout(34, 1000, 312, 130, "depth — concentric rings",
        ["How far a node sits from the root.",
         "A branch grows while it keeps",
         "advancing; it stops when it wins,",
         "dead-ends, or is pruned — so the",
         "branches reach uneven depth."])

# width callout (top centre, small) -> outer rings (top gap, angle 0)
wc_w = 300
callout(int(CX - wc_w / 2), 94, wc_w, 92, "width — how many tips",
        ["Total terminal leaves delivered,",
         "wherever they land. Set by",
         "convergence — not a fixed cap."])
wx, wy = pt(0, RMAX + 6)
add(f'<line x1="{CX}" y1="186" x2="{wx:.1f}" y2="{wy:.1f}" '
    f'stroke="#999" stroke-width="1.3" marker-end="url(#arrow)"/>')

# n callout (bottom-right)
n_total = total_leaves + total_internal + 1
callout(W - 298, 1000, 264, 110, "n — total nodes",
        ["Every node in the tree: root +",
         f"internal + leaves. Here n = {n_total}",
         f"(width = {total_leaves}, max depth = {deepest}).",
         "Streamed incrementally to tree.json."])

# ---- verdict legend (bottom strip) ----------------------------------------
ly0 = 1188
add(f'<text x="{CX}" y="{ly0}" text-anchor="middle" font-size="13.5" '
    f'font-weight="700" fill="#333">every leaf is a verdict — a branch can '
    f'win, dead-end, or keep branching (open node = re-expanded):</text>')
items = ["A", "K", "P", "B"]
labels = {  # short legend labels to avoid overflow
    "A": "advances — a win (or re-expands)",
    "K": "kept — held for reference",
    "P": "pruned — a dead end",
    "B": "blocked — must be resolved",
}
cols = [CX - 520, CX - 250, CX + 30, CX + 320]
for code, cxp in zip(items, cols):
    add(verdict_marker(cxp, ly0 + 26, code, R=8.5))
    add(f'<text x="{cxp + 16:.1f}" y="{ly0 + 31}" font-size="12.5" '
        f'fill="#444">{labels[code]}</text>')

add('</svg>')

out_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "assets")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.normpath(os.path.join(out_dir, "cc-tree-radial-tree.svg"))
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(svg))
print("wrote", out_path)
print("leaves(width) =", total_leaves, "internal =", total_internal,
      "n =", n_total, "max depth =", deepest)
