#!/usr/bin/env python3
"""Generate the cc-tree "phylogenetic tree of thoughts" radial diagram (SVG).

The picture is a circular cladogram, the same shape as a radial tree-of-life:
one ROOT at the centre, depth growing outward as concentric rings, four
coloured "clades" = the four shipped presets, and the terminal leaves aligned
on the outer arc (their count = width). Annotated to define the engine's
modules: root / node / depth / width / n / the 12 framings / leaf verdicts.

Run:  python3 tools/gen_radial_tree.py
Out:  docs/assets/cc-tree-radial-tree.svg
"""
import math
import os

CX, CY = 620.0, 600.0          # centre of the radial tree
R_D1, R_D2 = 150.0, 250.0      # ring radius for depth-1 / depth-2 internal nodes
R_LEAF = 360.0                 # all tips align on this outer arc (= width arc)
W, H = 1240, 1180

# Angle convention: 0 deg = up (12 o'clock), increasing CLOCKWISE.
def pt(theta_deg, r):
    a = math.radians(theta_deg)
    return (CX + r * math.sin(a), CY - r * math.cos(a))

def fmt(p):
    return f"{p[0]:.2f},{p[1]:.2f}"

def arc(a1, a2, r):
    """SVG path for an arc at radius r from angle a1 to a2 (clockwise convention)."""
    sweep = 1 if a2 >= a1 else 0
    large = 1 if abs(a2 - a1) > 180 else 0
    return f"M {fmt(pt(a1, r))} A {r:.2f} {r:.2f} 0 {large} {sweep} {fmt(pt(a2, r))}"

def annulus_sector(a1, a2, r_in, r_out):
    """Filled annulus-sector path (a coloured 'clade' wedge)."""
    return (f"M {fmt(pt(a1, r_out))} "
            f"A {r_out:.2f} {r_out:.2f} 0 0 1 {fmt(pt(a2, r_out))} "
            f"L {fmt(pt(a2, r_in))} "
            f"A {r_in:.2f} {r_in:.2f} 0 0 0 {fmt(pt(a1, r_in))} Z")

# ---- the four preset "clades" --------------------------------------------
# Each preset: colour, label, angular wedge [start,end] (clockwise), and a
# little tree spec: list of depth-1 internal nodes, each carrying tip verdicts.
# Verdict codes: A=advances (re-expands), K=kept, P=pruned, B=blocked.
PRESETS = [
    dict(name="brainstorm", advances="PROMISING", color="#6aa84f", fill="#b6d7a8",
         wedge=(200, 271),
         d1=[["A", "K", "P"], ["A", "A", "P"]]),
    dict(name="attack", advances="CONFIRMED", color="#cc4125", fill="#ea9999",
         wedge=(283, 354),
         d1=[["A", "P"], ["A", "K", "B"]]),
    dict(name="design", advances="RECOMMENDED", color="#8e7cc3", fill="#d5c6ec",
         wedge=(6, 77),
         d1=[["A", "K"], ["A", "P", "K"]]),
    dict(name="code-audit", advances="CONFIRMED", color="#a6794c", fill="#e0cba8",
         wedge=(89, 160),
         d1=[["A", "P", "P"], ["A", "K", "P"]]),
]

VERDICT = {
    "A": dict(color="#2e7d32", label="advances — re-expands"),
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

svg = []
def add(s):
    svg.append(s)

add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif">')

# defs: radial gradients per preset wedge
add('<defs>')
for p in PRESETS:
    add(f'<radialGradient id="g_{p["name"]}" '
        f'gradientUnits="userSpaceOnUse" '
        f'fx="{CX}" fy="{CY}" cx="{CX}" cy="{CY}" r="{R_LEAF}">'
        f'<stop offset="0%" stop-color="{p["fill"]}" stop-opacity="0.15"/>'
        f'<stop offset="100%" stop-color="{p["fill"]}" stop-opacity="0.78"/>'
        f'</radialGradient>')
add('<marker id="arrow" markerWidth="9" markerHeight="9" refX="7" refY="3" '
    'orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="#444"/></marker>')
add('</defs>')

add(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')

# ---- title ----------------------------------------------------------------
add(f'<text x="{CX}" y="46" text-anchor="middle" font-size="30" '
    f'font-weight="700" fill="#222">cc-tree &#8212; a phylogenetic tree of thoughts</text>')
add(f'<text x="{CX}" y="74" text-anchor="middle" font-size="16" fill="#666">'
    f'one universal radial-tree engine &#183; four swappable presets &#183; '
    f'grows outward from one root until substantive convergence</text>')

# ---- coloured clade wedges + preset labels --------------------------------
for p in PRESETS:
    a1, a2 = p["wedge"]
    add(f'<path d="{annulus_sector(a1, a2, 95, R_LEAF + 14)}" '
        f'fill="url(#g_{p["name"]})" stroke="none"/>')

# ---- build + draw each preset subtree -------------------------------------
total_tips = 0
total_internal = 0
for p in PRESETS:
    a1, a2 = p["wedge"]
    tips = [v for grp in p["d1"] for v in grp]
    n_tips = len(tips)
    total_tips += n_tips
    total_internal += len(p["d1"])
    # spread tips evenly across the wedge (with margin)
    span = a2 - a1
    margin = span * 0.10
    lo, hi = a1 + margin, a2 - margin
    tip_angles = [lo + (hi - lo) * (i + 0.5) / n_tips for i in range(n_tips)]

    # group tips under each depth-1 node; d1 angle = mean of its tips
    idx = 0
    d1_nodes = []
    for grp in p["d1"]:
        these = tip_angles[idx:idx + len(grp)]
        idx += len(grp)
        d1_nodes.append((sum(these) / len(these), these, grp))

    # root -> arc spanning the d1 nodes -> radial spokes to each d1 node
    d1_angles = [d for (d, _, _) in d1_nodes]
    add(f'<path d="{arc(min(d1_angles), max(d1_angles), R_D1)}" '
        f'fill="none" stroke="{p["color"]}" stroke-width="2.4"/>')
    # root spoke into the middle of that arc
    mid = (min(d1_angles) + max(d1_angles)) / 2
    rx, ry = pt(mid, 70)
    ax, ay = pt(mid, R_D1)
    add(f'<line x1="{rx:.1f}" y1="{ry:.1f}" x2="{ax:.1f}" y2="{ay:.1f}" '
        f'stroke="{p["color"]}" stroke-width="2.6"/>')

    for (d_ang, these, grp) in d1_nodes:
        # spoke root-arc radius -> this d1 node
        x1, y1 = pt(d_ang, R_D1)
        # arc at R_D2 spanning this node's tips, plus spoke d1->that arc
        x2, y2 = pt(d_ang, R_D2)
        add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{p["color"]}" stroke-width="2.2"/>')
        add(f'<path d="{arc(min(these), max(these), R_D2)}" fill="none" '
            f'stroke="{p["color"]}" stroke-width="2.0"/>')
        # depth-1 node dot
        add(f'<circle cx="{x1:.1f}" cy="{y1:.1f}" r="4.5" fill="#fff" '
            f'stroke="{p["color"]}" stroke-width="2.2"/>')
        # tips: radial spoke R_D2 -> R_LEAF, then verdict glyph
        for ang, code in zip(these, grp):
            sx, sy = pt(ang, R_D2)
            tx, ty = pt(ang, R_LEAF)
            add(f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{tx:.1f}" y2="{ty:.1f}" '
                f'stroke="{p["color"]}" stroke-width="1.6"/>')
            add(f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="2.6" '
                f'fill="{p["color"]}"/>')
            gx, gy = pt(ang, R_LEAF + 17)
            add(verdict_marker(gx, gy, code, R=8))

    # preset label, INSIDE the wedge at its mid-angle (cf. clade names in a
    # tree-of-life), with a soft white halo so it reads over the branches.
    cmid = (a1 + a2) / 2
    lx, ly = pt(cmid, 235)
    halo_w = 11 * len(p["name"]) + 24
    add(f'<rect x="{lx-halo_w/2:.1f}" y="{ly-22:.1f}" width="{halo_w:.1f}" '
        f'height="44" rx="9" fill="#ffffff" fill-opacity="0.72"/>')
    add(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" font-size="22" '
        f'font-weight="700" fill="{p["color"]}">{p["name"]}</text>')
    add(f'<text x="{lx:.1f}" y="{ly + 16:.1f}" text-anchor="middle" '
        f'font-size="11.5" fill="{p["color"]}">advances = {p["advances"]}</text>')

# ---- ROOT at the centre ---------------------------------------------------
add(f'<circle cx="{CX}" cy="{CY}" r="52" fill="#37474f"/>')
add(f'<circle cx="{CX}" cy="{CY}" r="52" fill="none" stroke="#fff" '
    f'stroke-width="2" stroke-dasharray="3 3"/>')
add(f'<text x="{CX}" y="{CY-8}" text-anchor="middle" font-size="20" '
    f'font-weight="700" fill="#fff">ROOT</text>')
add(f'<text x="{CX}" y="{CY+12}" text-anchor="middle" font-size="10.5" '
    f'fill="#cfd8dc">topic &#183; artifact</text>')
add(f'<text x="{CX}" y="{CY+26}" text-anchor="middle" font-size="10.5" '
    f'fill="#cfd8dc">code &#183; design</text>')

# ---- depth ring guides (dashed) + labels ----------------------------------
for r, lbl in [(R_D1, "depth 1"), (R_D2, "depth 2"), (R_LEAF, "leaves")]:
    add(f'<circle cx="{CX}" cy="{CY}" r="{r}" fill="none" stroke="#cfcfcf" '
        f'stroke-width="1" stroke-dasharray="2 5"/>')

# radial depth ruler pointing down-left into the bottom gap (~185 deg)
ruler = 183
for r, lbl in [(0, "depth 0"), (R_D1, "depth 1"), (R_D2, "depth 2"), (R_LEAF, "leaves")]:
    px, py = pt(ruler, r)
    add(f'<text x="{px-12:.1f}" y="{py+4:.1f}" text-anchor="end" font-size="11.5" '
        f'fill="#777">{lbl}</text>')
    add(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2.4" fill="#999"/>')

# ======================  ANNOTATION CALL-OUTS  ============================
def callout(x, y, w, h, title, lines, anchor_xy, title_color="#222"):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" '
        f'fill="#ffffff" stroke="#bbb" stroke-width="1.2"/>')
    add(f'<text x="{x+14}" y="{y+24}" font-size="15.5" font-weight="700" '
        f'fill="{title_color}">{title}</text>')
    for i, ln in enumerate(lines):
        add(f'<text x="{x+14}" y="{y+46+i*18}" font-size="12.5" fill="#444">{ln}</text>')
    if anchor_xy:
        # leader line from the box edge to the anchored feature
        ex, ey = anchor_xy
        add(f'<line x1="{x+w/2}" y1="{y+h if ey>y else y}" x2="{ex}" y2="{ey}" '
            f'stroke="#888" stroke-width="1.3" marker-end="url(#arrow)"/>')

# ROOT callout (top-left) -> centre
callout(40, 110, 250, 92, "root — the input",
        ["What you hand the engine:",
         "a topic, an artifact (file/doc),",
         "a code path, or a design prompt.",
         "The whole tree grows from it."],
        (CX-55, CY-20))

# NODE callout (top-right) -> a nearby design depth-1 node
node_anchor = pt((6+77)/2, R_D1)
callout(950, 110, 250, 110, "node — one thought",
        ["One idea / critique / option /",
         "finding. Every node gets the",
         "same 12-field derivation, is",
         "scored on 5 dims, and earns a",
         "verdict. No hedging, no defer."],
        node_anchor)

# 12-framings callout (left) -> root
callout(40, 250, 250, 92, "12 framings (§3.A–§3.L)",
        ["Each node is expanded by the",
         "same 12 framing passes —",
         "first-principles, inversion,",
         "red-team, contrarian, high-risk…"],
        (CX-52, CY))

# DEPTH callout (bottom-left) -> ruler
callout(40, 940, 270, 90, "depth — concentric rings",
        ["How many framing-recursion",
         "rounds a node sits from the root.",
         "Default ∞: only 'advances' leaves",
         "re-expand into the next ring."],
        pt(ruler, R_D2))

# WIDTH callout (top centre) -> outer arc at top gap (~330 deg, attack/design boundary -> use top 0deg area)
width_anchor = pt(0, R_LEAF)
callout(int(CX-135), 96, 270, 70, "width — the outer arc",
        ["The number of terminal leaves",
         "delivered. Decided by convergence,",
         "not a hand-picked cap."],
        None)
add(f'<line x1="{CX}" y1="166" x2="{width_anchor[0]:.1f}" y2="{width_anchor[1]:.1f}" '
    f'stroke="#888" stroke-width="1.3" marker-end="url(#arrow)"/>')

# n callout (bottom-right) -> whole tree
callout(940, 940, 260, 70, "n — total nodes",
        [f"Every node in the tree: root +",
         f"internal + leaves. Here n = "
         f"{total_tips + total_internal + 1} "
         f"(width = {total_tips}).",
         "Written incrementally to tree.json."],
        None)

# ---- verdict legend (bottom centre) ---------------------------------------
ly0 = 1086
add(f'<text x="{CX}" y="{ly0}" text-anchor="middle" font-size="13.5" '
    f'font-weight="700" fill="#333">leaf verdict → recurse decision:</text>')
items = ["A", "K", "P", "B"]
gap = 290
startx = CX - (gap * (len(items) - 1)) / 2
for i, code in enumerate(items):
    x = startx + i * gap
    add(verdict_marker(x - 96, ly0 + 19, code, R=8.5))
    add(f'<text x="{x-80:.1f}" y="{ly0+24}" font-size="12.5" '
        f'fill="#444">{VERDICT[code]["label"]}</text>')

add('</svg>')

out_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "assets")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.normpath(os.path.join(out_dir, "cc-tree-radial-tree.svg"))
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(svg))
print("wrote", out_path)
print("tips(width) =", total_tips, "internal =", total_internal,
      "n =", total_tips + total_internal + 1)
