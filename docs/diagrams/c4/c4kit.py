"""C4 diagram kit in the author's design system (same engine as the Episteme diagrams).

Design: the GitHub profile and portfolio (adriansalvadorekomodev.vercel.app): a labelled
panel framed by the dot-matrix mark, hairlines, no shadows, one orange signal for the focal
element, IBM Plex Mono for labels and Schibsted Grotesk for names. Technology logos sit on
small black "display" chips, like the mark.

Text is converted to vector paths, so the SVGs look the same in every browser, on GitHub
(an SVG shown through <img> cannot load web fonts) and once exported to PNG.

Each repository's build_c4.py imports this module and only describes its views:

    uv run --no-project --with fonttools --with brotli python docs/diagrams/c4/build_c4.py [--png]

Assets: assets/fonts (Schibsted Grotesk, IBM Plex Mono; SIL OFL 1.1), assets/icons.json
(Simple Icons subset, CC0; each trademark belongs to its owner), assets/mark.svg.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

KIT = Path(__file__).resolve().parent
ASSETS = KIT / "assets"
ICONS = json.loads((ASSETS / "icons.json").read_text())["icons"]

ORANGE = "#ff4f00"
DISPLAY = "#121212"  # logo chips: the mark's black display, in both themes
THEMES = {
    # "aluminium edition", the same tokens as the profile images
    "light": {
        "panel": "#ebe9e4",
        "ink": "#121212",
        "ink2": "#5c5952",
        "hair": "#cdc9c0",
        "node": "#f4f2ee",
        "ext": "#e3e0d9",
        "chip_line": "#121212",
    },
    # "black edition"
    "dark": {
        "panel": "#121212",
        "ink": "#ebe9e4",
        "ink2": "#9b978f",
        "hair": "#2e2e2e",
        "node": "#1b1b1b",
        "ext": "#161616",
        "chip_line": "#3a3a3a",
    },
}

# Tabler Icons (MIT): stroked glyphs for things that have no logo.
GLYPHS = {
    "user": [
        "M8 7a4 4 0 1 0 8 0a4 4 0 0 0 -8 0",
        "M6 21v-2a4 4 0 0 1 4 -4h4a4 4 0 0 1 4 4v2",
    ],
    "terminal": ["M5 7l5 5l-5 5", "M12 19l7 0"],
    "file": [
        "M14 3v4a1 1 0 0 0 1 1h4",
        "M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2z",
        "M9 13h6",
        "M9 17h6",
    ],
    "folder": [
        "M5 4h4l3 3h7a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2v-11a2 2 0 0 1 2 -2"
    ],
    "key": [
        (
            "M16.555 3.843l3.602 3.602a2.877 2.877 0 0 1 0 4.069l-2.643 2.643a2.877 2.877 0 0 1 -4.069 0l-.301 -.301"
            "l-6.558 6.558a2 2 0 0 1 -1.239 .578l-.175 .008h-1.172a1 1 0 0 1 -.993 -.883l-.007 -.117v-1.172a2 2 0 0 1 "
            ".467 -1.284l.119 -.13l.414 -.414h2v-2h2v-2l2.144 -2.144l-.301 -.301a2.877 2.877 0 0 1 0 -4.069l2.643 "
            "-2.643a2.877 2.877 0 0 1 4.069 0z"
        ),
        "M15 9h.01",
    ],
    "bell": [
        "M10 5a2 2 0 1 1 4 0a7 7 0 0 1 4 6v3a4 4 0 0 0 2 3h-16a4 4 0 0 0 2 -3v-3a7 7 0 0 1 4 -6",
        "M9 17v1a3 3 0 0 0 6 0v-1",
    ],
}


def num(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


# ── text as vector paths ───────────────────────────────────────────────────
class Face:
    def __init__(
        self, path: Path, tag: str, defs: dict[str, str], wght: float | None = None
    ):
        f = TTFont(str(path))
        if wght is not None and "fvar" in f:
            f = instancer.instantiateVariableFont(f, {"wght": wght})
        self.f, self.tag, self.defs = f, tag, defs
        self.gs = f.getGlyphSet()
        self.cmap = f.getBestCmap()
        self.upm = f["head"].unitsPerEm
        self.hmtx = f["hmtx"]

    def _g(self, ch: str) -> str:
        g = self.cmap.get(ord(ch))
        if g is None:
            raise KeyError(f"{self.tag}: no glyph for {ch!r}")
        return g

    def width(self, text: str, size: float, track: float = 0) -> float:
        adv = sum(self.hmtx[self._g(c)][0] for c in text) * size / self.upm
        return adv + track * size * max(0, len(text) - 1)

    def text(
        self,
        s: str,
        x: float,
        y: float,
        size: float,
        fill: str,
        anchor: str = "start",
        track: float = 0,
    ) -> str:
        w = self.width(s, size, track)
        if anchor == "middle":
            x -= w / 2
        elif anchor == "end":
            x -= w
        k = size / self.upm
        uses = []
        for ch in s:
            g = self._g(ch)
            gid = f"{self.tag}{self.f.getGlyphID(g)}"
            if gid not in self.defs:
                pen = SVGPathPen(self.gs)
                self.gs[g].draw(pen)
                self.defs[gid] = pen.getCommands()
            if self.defs[gid]:
                uses.append(f'<use href="#{gid}" x="{num(x / k)}" y="{num(-y / k)}"/>')
            x += self.hmtx[g][0] * k + track * size
        return (
            f'<g fill="{fill}" transform="scale({k:.7g} {-k:.7g})">{"".join(uses)}</g>'
        )


def load_fonts(defs: dict[str, str]) -> dict[str, Face]:
    fd = ASSETS / "fonts"
    grot = fd / "SchibstedGrotesk-wght.ttf"
    return {
        "mono": Face(fd / "IBMPlexMono-Regular.ttf", "m", defs),
        "mono_md": Face(fd / "IBMPlexMono-Medium.ttf", "n", defs),
        "grot": Face(grot, "g", defs, 400),
        "grot_md": Face(grot, "h", defs, 560),
        "grot_sb": Face(grot, "s", defs, 640),
    }


# ── logos ──────────────────────────────────────────────────────────────────
def _luminance(hex6: str) -> float:
    def ch(c: float) -> float:
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (int(hex6[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def _contrast(a: str, b: str) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def logo(name: str, x: float, y: float, s: float) -> str:
    """Logo of side `s` at (x, y), drawn for a dark chip. Brand colour unless it vanishes on black."""
    if name in GLYPHS:
        k = s / 24
        d = "".join(f'<path d="{p}"/>' for p in GLYPHS[name])
        return (
            f'<g transform="translate({num(x)} {num(y)}) scale({k:.6g})" fill="none" stroke="#ebe9e4" '
            f'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{d}</g>'
        )
    ic = ICONS[name]
    color = "#" + ic["hex"]
    if _contrast(ic["hex"], DISPLAY[1:]) < 2.6:
        color = "#ebe9e4"
    return f'<path transform="translate({num(x)} {num(y)}) scale({s / 24:.6g})" fill="{color}" d="{ic["path"]}"/>'


# ── drawing context ────────────────────────────────────────────────────────
@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    @property
    def r(self) -> float:
        return self.x + self.w

    @property
    def b(self) -> float:
        return self.y + self.h


@dataclass
class Canvas:
    theme: str
    fonts: dict
    W: int
    H: int
    t: dict = field(init=False)
    zones: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    nodes: list[str] = field(default_factory=list)
    top: list[str] = field(default_factory=list)
    # geometry for lint()
    g_nodes: list[tuple[str, Box]] = field(default_factory=list)
    g_labels: list[tuple[str, Box]] = field(default_factory=list)
    g_arrows: list[list[tuple[float, float]]] = field(default_factory=list)
    g_fixed: list[tuple[str, Box]] = field(default_factory=list)

    def __post_init__(self):
        self.t = THEMES[self.theme]

    # text helpers ---------------------------------------------------------
    def mono(self, s, x, y, size=12, fill=None, anchor="start", track=0.0):
        return self.fonts["mono"].text(
            s, x, y, size, fill or self.t["ink2"], anchor, track
        )

    def monom(self, s, x, y, size=12, fill=None, anchor="start", track=0.0):
        return self.fonts["mono_md"].text(
            s, x, y, size, fill or self.t["ink"], anchor, track
        )

    def name(self, s, x, y, size=16, fill=None, anchor="start"):
        return self.fonts["grot_sb"].text(
            s, x, y, size, fill or self.t["ink"], anchor, -0.005
        )

    def body(self, s, x, y, size=13, fill=None, anchor="start"):
        return self.fonts["grot"].text(s, x, y, size, fill or self.t["ink2"], anchor)

    def fits(self, face: str, s: str, size: float, width: float, track: float = 0):
        w = self.fonts[face].width(s, size, track)
        assert w <= width, f"text too wide ({w:.0f} > {width:.0f}px): {s!r}"

    # elements -------------------------------------------------------------
    def chips(self, names: list[str], right: float, y: float, size: int = 28) -> str:
        out, x = [], right - size
        for n in reversed(names):
            out.append(
                f'<rect x="{num(x)}" y="{num(y)}" width="{size}" height="{size}" rx="7" '
                f'fill="{DISPLAY}" stroke="{self.t["chip_line"]}" stroke-width="1"/>'
            )
            pad = 6
            out.append(logo(n, x + pad, y + pad, size - 2 * pad))
            x -= size + 6
        return "".join(out)

    def node(
        self,
        b: Box,
        kind: str,
        eyebrow: str,
        title: str,
        tech: str | None,
        desc: list[str],
        logos: list[str] = (),
        focal: bool = False,
        dashed: bool = False,
    ):
        """kind: person | container | store | external. focal = the orange signal (one per view)."""
        t = self.t
        self.g_nodes.append((title, b))
        fill = t["ext"] if kind == "external" else t["node"]
        stroke, sw = (ORANGE, 2) if focal else (t["ink2"], 1.2)
        if kind == "external":
            stroke, sw = t["ink2"], 1
        dash = ' stroke-dasharray="5 4"' if dashed else ""
        g = [
            (
                f'<rect x="{num(b.x)}" y="{num(b.y)}" width="{num(b.w)}" height="{num(b.h)}" rx="10" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{dash}/>'
            )
        ]
        if (
            kind == "store"
        ):  # a data store: a second hairline under the top edge (C4 "cylinder" cue)
            g.append(
                f'<path d="M{num(b.x + 1)} {num(b.y + 8)} H{num(b.r - 1)}" stroke="{t["hair"]}" '
                f'stroke-width="1"/>'
            )
        px = b.x + 16
        ex = px
        if focal:
            g.append(
                f'<circle cx="{num(px + 4)}" cy="{num(b.y + 24)}" r="4" fill="{ORANGE}"/>'
            )
            ex = px + 14
        chips_w = len(logos) * 34
        self.fits("mono", eyebrow.upper(), 11, b.w - 32 - chips_w - (ex - px), 0.1)
        g.append(self.mono(eyebrow.upper(), ex, b.y + 28, 11, t["ink2"], track=0.1))
        if logos:
            g.append(self.chips(list(logos), b.r - 12, b.y + 12))
        avail = b.w - 32
        y = b.y + 56
        self.fits("grot_sb", title, 16, avail)
        g.append(self.name(title, px, y))
        if tech:
            y += 18
            self.fits("mono", tech, 12, avail)
            g.append(self.mono(tech, px, y, 12, t["ink2"]))
        last = y
        y += 6
        for line in desc:
            y += 18
            self.fits("grot", line, 13, avail)
            g.append(self.body(line, px, y, 13, t["ink"]))
            last = y
        assert last + 12 <= b.b, (
            f"{title}: content overflows the box ({last + 12} > {b.b})"
        )
        self.nodes.append("".join(g))

    def zone(
        self,
        b: Box,
        label: str,
        sub: str | None = None,
        at: str = "top",
        lx: float | None = None,
    ):
        """Dashed boundary; its label sits on the top or bottom edge, at x = lx (default: left)."""
        t = self.t
        g = [
            (
                f'<rect x="{num(b.x)}" y="{num(b.y)}" width="{num(b.w)}" height="{num(b.h)}" rx="14" '
                f'fill="none" stroke="{t["ink2"]}" stroke-width="1" stroke-dasharray="6 5" stroke-opacity="0.7"/>'
            )
        ]
        lw = self.fonts["mono_md"].width(label, 12, 0.1) + (
            self.fonts["mono"].width("  " + sub, 12) if sub else 0
        )
        ly = b.y if at == "top" else b.b
        x0 = b.x + 16 if lx is None else lx
        self.g_fixed.append((label, Box(x0, ly - 10, lw + 16, 20)))
        g.append(
            f'<rect x="{num(x0)}" y="{num(ly - 10)}" width="{num(lw + 16)}" height="20" fill="{t["panel"]}"/>'
        )
        g.append(self.monom(label, x0 + 8, ly + 4, 12, t["ink"], track=0.1))
        if sub:
            g.append(
                self.mono(
                    "  " + sub,
                    x0 + 8 + self.fonts["mono_md"].width(label, 12, 0.1),
                    ly + 4,
                    12,
                )
            )
        self.zones.append("".join(g))

    def _path(self, pts):
        d = [f"M{num(pts[0][0])} {num(pts[0][1])}"]
        for i in range(1, len(pts) - 1):
            (x0, y0), (x1, y1), (x2, y2) = pts[i - 1], pts[i], pts[i + 1]
            r = min(8, abs(x1 - x0 + y1 - y0) / 2, abs(x2 - x1 + y2 - y1) / 2)
            sx = (x1 > x0) - (x1 < x0)
            sy = (y1 > y0) - (y1 < y0)
            tx = (x2 > x1) - (x2 < x1)
            ty = (y2 > y1) - (y2 < y1)
            d.append(
                f"L{num(x1 - sx * r)} {num(y1 - sy * r)} Q{num(x1)} {num(y1)} {num(x1 + tx * r)} {num(y1 + ty * r)}"
            )
        return d

    def arrow(
        self,
        pts: list[tuple[float, float]],
        dashed: bool = False,
        color: str | None = None,
        head: bool = True,
    ):
        """Orthogonal connector through `pts` with r=8 rounded corners and a drawn arrowhead."""
        self.g_arrows.append([(float(a), float(b)) for a, b in pts])
        color = color or self.t["ink2"]
        d = self._path(pts)
        (xa, ya), (xb, yb) = pts[-2], pts[-1]
        ux = (xb > xa) - (xb < xa)
        uy = (yb > ya) - (yb < ya)
        d.append(
            f"L{num(xb - ux * 7)} {num(yb - uy * 7)}"
            if head
            else f"L{num(xb)} {num(yb)}"
        )
        dash = ' stroke-dasharray="5 4"' if dashed else ""
        self.lines.append(
            f'<path d="{" ".join(d)}" fill="none" stroke="{color}" stroke-width="1.5"{dash}/>'
        )
        if head:  # 9 long, 7 wide, tip on the box edge
            bx, by = xb - ux * 9, yb - uy * 9
            px, py = -uy * 3.5, ux * 3.5
            self.lines.append(
                f'<path d="M{num(xb)} {num(yb)} L{num(bx + px)} {num(by + py)} '
                f'L{num(bx - px)} {num(by - py)} Z" fill="{color}"/>'
            )

    def label(
        self, lines: list[tuple[str, bool]], x: float, y: float, anchor: str = "middle"
    ):
        """Masked connector label; lines = [(text, is_tech)]. (x, y) = baseline of the first line."""
        t = self.t
        ws = [
            self.fonts["mono_md" if not tech else "mono"].width(s, 12)
            for s, tech in lines
        ]
        w = max(ws) + 12
        h = 16 * len(lines) + 4
        x0 = x - w / 2 if anchor == "middle" else (x - w if anchor == "end" else x)
        self.g_labels.append((lines[0][0], Box(x0, y - 14, w, h)))
        g = [
            f'<rect x="{num(x0)}" y="{num(y - 14)}" width="{num(w)}" height="{num(h)}" rx="3" fill="{t["panel"]}"/>'
        ]
        tx = x0 + w / 2
        for i, (s, tech) in enumerate(lines):
            face = self.mono if tech else self.monom
            g.append(
                face(s, tx, y + 16 * i, 12, t["ink2"] if tech else t["ink"], "middle")
            )
        self.labels.append("".join(g))

    def note(self, s: str, x: float, y: float, size: float = 12):
        """A short mono annotation on the panel (operational facts, not prose)."""
        w = self.fonts["mono"].width(s, size)
        self.g_fixed.append((s[:30], Box(x, y - size, w, size * 1.3)))
        self.top.append(self.mono(s, x, y, size, self.t["ink2"]))

    # page -----------------------------------------------------------------
    def frame(self, mark: str, left: str, right: str, title: str, subtitle: str):
        t = self.t
        self.g_fixed.append(
            ("title", Box(32, 84, self.fonts["grot_md"].width(title, 32) + 4, 64))
        )
        self.zones.insert(
            0,
            "".join(
                [
                    (
                        f'<rect x="1" y="1" width="{self.W - 2}" height="{self.H - 2}" rx="20" fill="{t["panel"]}" '
                        f'stroke="{t["hair"]}" stroke-width="2"/>'
                    ),
                    f'<svg x="32" y="20" width="32" height="32" viewBox="0 0 64 64">{mark}</svg>',
                    self.mono(left, 76, 42, 14, t["ink2"], track=0.03),
                    self.mono(right, self.W - 32, 42, 14, t["ink2"], "end", 0.03),
                    f'<rect x="32" y="64" width="{self.W - 64}" height="1" fill="{t["hair"]}"/>',
                    self.fonts["grot_md"].text(
                        title, 32, 112, 32, t["ink"], track=-0.01
                    ),
                    self.mono(subtitle, 32, 140, 13, t["ink2"]),
                ]
            ),
        )
        self.fits("mono", subtitle, 13, self.W - 64)

    def readout(
        self, cols: list[tuple[str, str]], right: float, y: float, gap: float = 40
    ):
        """Stat columns, right-aligned: small mono label above a value."""
        t = self.t
        x = right
        out = []
        for label, value in reversed(cols):
            w = max(
                self.fonts["mono"].width(label, 11, 0.1),
                self.fonts["mono_md"].width(value, 16),
            )
            x0 = x - w
            self.g_fixed.append((label, Box(x0, y - 6, w, 46)))
            out.append(
                f'<rect x="{num(x0)}" y="{num(y - 6)}" width="{num(w)}" height="1" fill="{t["hair"]}"/>'
            )
            out.append(self.mono(label, x0, y + 12, 11, t["ink2"], track=0.1))
            out.append(self.monom(value, x0, y + 36, 16, t["ink"]))
            x = x0 - gap
        self.top.append("".join(out))

    def legend(self, y: float, items: list[tuple[str, str]], note: str | None = None):
        """kinds: person, container, focal, store, external, call, occasional."""
        t = self.t
        g = [
            f'<rect x="32" y="{num(y)}" width="{self.W - 64}" height="1" fill="{t["hair"]}"/>',
            self.mono("LEGEND", 32, y + 32, 11, t["ink2"], track=0.14),
        ]
        x = 120
        for kind, text in items:
            cy = y + 28
            if kind in ("person", "container"):
                g.append(
                    f'<rect x="{x}" y="{cy - 8}" width="24" height="16" rx="4" fill="{t["node"]}" '
                    f'stroke="{t["ink2"]}" stroke-width="1.2"/>'
                )
            elif kind == "focal":
                g.append(
                    f'<rect x="{x}" y="{cy - 8}" width="24" height="16" rx="4" fill="{t["node"]}" '
                    f'stroke="{ORANGE}" stroke-width="2"/>'
                )
            elif kind == "store":
                g.append(
                    f'<rect x="{x}" y="{cy - 8}" width="24" height="16" rx="4" fill="{t["node"]}" '
                    f'stroke="{t["ink2"]}" stroke-width="1.2"/><path d="M{x + 1} {cy - 4} H{x + 23}" '
                    f'stroke="{t["hair"]}"/>'
                )
            elif kind == "external":
                g.append(
                    f'<rect x="{x}" y="{cy - 8}" width="24" height="16" rx="4" fill="{t["ext"]}" '
                    f'stroke="{t["ink2"]}" stroke-width="1"/>'
                )
            elif kind == "zone":
                g.append(
                    f'<rect x="{x}" y="{cy - 8}" width="24" height="16" rx="4" fill="none" '
                    f'stroke="{t["ink2"]}" stroke-width="1" stroke-dasharray="4 3"/>'
                )
            elif kind in ("call", "occasional"):
                dash = ' stroke-dasharray="5 4"' if kind == "occasional" else ""
                g.append(
                    f'<path d="M{x} {cy} H{x + 17}" stroke="{t["ink2"]}" stroke-width="1.5"{dash}/>'
                    f'<path d="M{x + 24} {cy} L{x + 15} {cy - 3.5} L{x + 15} {cy + 3.5} Z" fill="{t["ink2"]}"/>'
                )
            g.append(self.mono(text, x + 32, cy + 4, 12, t["ink"]))
            x += 32 + self.fonts["mono"].width(text, 12) + 28
        if note:
            g.append(self.mono(note, self.W - 32, y + 32, 11, t["ink2"], "end"))
            assert x < self.W - 32 - self.fonts["mono"].width(note, 11) - 16, (
                "legend runs into its note"
            )
        assert x <= self.W - 32, "legend too wide"
        self.top.append("".join(g))

    # quality gate -----------------------------------------------------------
    def lint(self) -> list[str]:
        """What a reader would notice: boxes or labels that overlap, arrows through boxes."""
        out = []

        def overlap(a: Box, b: Box) -> bool:
            return a.x < b.r - 1 and b.x < a.r - 1 and a.y < b.b - 1 and b.y < a.b - 1

        solid = (
            [("node", n, b) for n, b in self.g_nodes]
            + [("label", n, b) for n, b in self.g_labels]
            + [("fixed", n, b) for n, b in self.g_fixed]
        )
        for (ka, na, a), (kb, nb, b) in itertools.combinations(solid, 2):
            nested = ka == kb == "node" and (
                (a.x >= b.x and a.r <= b.r and a.y >= b.y and a.b <= b.b)
                or (b.x >= a.x and b.r <= a.r and b.y >= a.y and b.b <= a.b)
            )
            if overlap(a, b) and not nested:
                out.append(f"overlap: {ka} {na!r} / {kb} {nb!r}")
        for n, b in [(n, b) for _, n, b in solid]:
            if b.x < 0 or b.y < 0 or b.r > self.W or b.b > self.H:
                out.append(f"off-canvas: {n!r}")

        def hits(p, q, r: Box) -> bool:
            (x1, y1), (x2, y2) = p, q
            if x1 == x2:
                return r.x < x1 < r.r and max(min(y1, y2), r.y) < min(max(y1, y2), r.b)
            if y1 == y2:
                return r.y < y1 < r.b and max(min(x1, x2), r.x) < min(max(x1, x2), r.r)
            return False

        for pts in self.g_arrows:
            for p, q in itertools.pairwise(pts):
                for n, b in self.g_nodes:
                    inner = Box(b.x + 3, b.y + 3, b.w - 6, b.h - 6)
                    if hits(p, q, inner):
                        out.append(f"arrow {pts[0]}→{pts[-1]} crosses {n!r}")
                for n, b in self.g_fixed:  # zone labels, notes, title, readouts
                    if hits(p, q, b):
                        out.append(f"arrow {pts[0]}→{pts[-1]} crosses the text {n!r}")
        return sorted(set(out))

    def svg(self, slug: str, title: str, desc: str, defs: dict[str, str]) -> str:
        glyphs = "".join(f'<path id="{k}" d="{v}"/>' for k, v in defs.items() if v)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.W} {self.H}" width="{self.W}" '
            f'height="{self.H}" role="img" aria-labelledby="{slug}-title {slug}-desc">'
            f'<title id="{slug}-title">{_esc(title)}</title><desc id="{slug}-desc">{_esc(desc)}</desc>'
            f"<defs>{glyphs}</defs>"
            + "".join(self.zones + self.lines + self.labels + self.nodes + self.top)
            + "</svg>"
        )


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ── build ──────────────────────────────────────────────────────────────────
@dataclass
class View:
    name: str
    fn: Callable[[Canvas], None]
    W: int
    H: int
    right: str
    title: str
    subtitle: str
    alt_title: str
    desc: str


def _png(svg: Path, w: int, h: int) -> None:
    browser = next(
        (
            shutil.which(b)
            for b in ("chromium", "chromium-browser", "google-chrome")
            if shutil.which(b)
        ),
        None,
    )
    if browser is None:
        sys.exit("--png needs Chromium")
    with tempfile.TemporaryDirectory() as d:
        page = Path(d) / "p.html"
        page.write_text(
            f'<!doctype html><body style="margin:0"><img src="{svg.as_uri()}" width="{w}" height="{h}">'
        )
        out = svg.with_name(svg.stem + "@2x.png")
        subprocess.run(
            [
                browser,
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--force-device-scale-factor=2",
                f"--window-size={w},{h}",
                "--allow-file-access-from-files",
                f"--user-data-dir={d}/u",
                f"--screenshot={out}",
                page.as_uri(),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )


def build(out_dir: Path, repo: str, views: list[View]) -> None:
    ap = argparse.ArgumentParser(
        description="Draw the C4 diagrams (SVG, light and dark)."
    )
    ap.add_argument(
        "--png", action="store_true", help="also write @2x PNGs (needs Chromium)"
    )
    ap.add_argument("--only", choices=[v.name for v in views])
    a = ap.parse_args()
    mark = re.search(
        r"<svg[^>]*>(.*)</svg>", (ASSETS / "mark.svg").read_text(), re.DOTALL
    ).group(1)
    mark = re.sub(r"<!--.*?-->", "", mark, flags=re.DOTALL)
    problems = []
    for v in views:
        if a.only and v.name != a.only:
            continue
        for theme in THEMES:
            defs: dict[str, str] = {}
            cv = Canvas(theme, load_fonts(defs), v.W, v.H)
            cv.frame(
                mark, f"adriansalvadorekomo / {repo}", v.right, v.title, v.subtitle
            )
            v.fn(cv)
            if theme == "light":
                problems += [f"{v.name}: {p}" for p in cv.lint()]
            slug = f"c4-{v.name}-{theme}"
            out = out_dir / f"{slug}.svg"
            out.write_text(cv.svg(slug, v.alt_title, v.desc, defs), encoding="utf-8")
            if a.png:
                _png(out, v.W, v.H)
            print(f"wrote {out.name}  ({out.stat().st_size // 1024} KB)")
    if problems:
        sys.exit("layout problems:\n  " + "\n  ".join(problems))
