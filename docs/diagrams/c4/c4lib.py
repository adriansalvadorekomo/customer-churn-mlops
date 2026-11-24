"""C4 drawing kit shared by the project READMEs (same look as the DataOps Lakehouse diagrams).

Canvas primitives: header, cards (containers, stores, externals), people, boundaries,
arrows, relationship labels, legend. SVGs embed Inter / JetBrains Mono (OFL) as base64
woff2 and technology logos as inline Simple Icons paths (CC0, assets/icons.json), so
they render offline; PNGs are taken at 2x with headless Chromium.

Each repository's build_c4.py imports this module and only describes its own model.
Stdlib only.
"""

from __future__ import annotations

import base64
import json
import shutil
import subprocess
import sys
import tempfile
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
ICONS = json.loads((ASSETS / "icons.json").read_text())["icons"]


# ── themes ──────────────────────────────────────────────────────────────────
THEMES = {
    "dark": {
        "bg": "#0A0E17",
        "grid": "#141A26",
        "text": "#E8ECF3",
        "muted": "#9AA4B5",
        "faint": "#5E6879",
        "card": "#111726",
        "card2": "#0D1320",
        "border": "#232C3D",
        "tile": "#0B101B",
        "line": "#7D889B",
        "halo": "#0A0E17",
        "ops": "#5B9BFF",
        "ana": "#FF6A4D",
        "dlv": "#A98BFF",
        "ext": "#8C97A8",
        "person": "#3CC6E8",
        "bronze": "#D08A52",
        "silver": "#C3CCD7",
        "gold": "#EFC04F",
        "ok": "#3DDC97",
        "dark_logo": "#E8ECF3",
    },
    "light": {
        "bg": "#F6F7F9",
        "grid": "#E6E9EE",
        "text": "#0E1726",
        "muted": "#4A5568",
        "faint": "#8A94A6",
        "card": "#FFFFFF",
        "card2": "#FBFCFD",
        "border": "#D9DFE7",
        "tile": "#F1F4F8",
        "line": "#7A8699",
        "halo": "#F6F7F9",
        "ops": "#1F63E0",
        "ana": "#E2401F",
        "dlv": "#6D3FE0",
        "ext": "#64748B",
        "person": "#0A86B3",
        "bronze": "#A5602A",
        "silver": "#6E7C8C",
        "gold": "#B07D0A",
        "ok": "#0E9F6E",
        "dark_logo": "#0E1726",
    },
}

SANS = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', ui-monospace, Menlo, Consolas, monospace"


def font_css() -> str:
    faces = [
        ("Inter", 400, "inter-latin-400-normal"),
        ("Inter", 500, "inter-latin-500-normal"),
        ("Inter", 600, "inter-latin-600-normal"),
        ("Inter", 700, "inter-latin-700-normal"),
        ("Inter", 800, "inter-latin-800-normal"),
        ("Inter", 400, "inter-latin-ext-400-normal"),
        ("Inter", 600, "inter-latin-ext-600-normal"),
        ("Inter", 700, "inter-latin-ext-700-normal"),
        ("JetBrains Mono", 400, "jetbrains-mono-latin-400-normal"),
        ("JetBrains Mono", 500, "jetbrains-mono-latin-500-normal"),
    ]
    out = []
    for fam, w, f in faces:
        b64 = base64.b64encode((ASSETS / "fonts" / f"{f}.woff2").read_bytes()).decode()
        rng = ";unicode-range:U+0100-02BA,U+20A0-20C0,U+2113" if "ext" in f else ""
        out.append(
            f"@font-face{{font-family:'{fam}';font-weight:{w};font-style:normal;"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2'){rng}}}"
        )
    return "".join(out)


# ── drawing primitives ──────────────────────────────────────────────────────
class Canvas:
    def __init__(self, w: int, h: int, theme: str):
        self.w, self.h, self.t = w, h, THEMES[theme]
        self.theme = theme
        self.defs: list[str] = []
        self.back: list[str] = []  # boundaries
        self.mid: list[str] = []  # arrows
        self.front: list[str] = []  # cards, labels
        self._id = 0
        self._markers: dict[str, str] = {}

    def uid(self, p="c") -> str:
        self._id += 1
        return f"{p}{self._id}"

    # text ------------------------------------------------------------------
    def text(
        self,
        x,
        y,
        s,
        size=15,
        weight=400,
        color=None,
        family=SANS,
        anchor="start",
        spacing=0.0,
        layer=None,
        opacity=1.0,
    ):
        color = color or self.t["text"]
        ls = f' letter-spacing="{spacing}"' if spacing else ""
        op = f' opacity="{opacity}"' if opacity != 1 else ""
        (layer if layer is not None else self.front).append(
            f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}"{ls}{op}>{escape(s)}</text>'
        )

    # icons -----------------------------------------------------------------
    def logo(self, slug, x, y, size, color=None, layer=None):
        ic = ICONS[slug]
        col = color or f"#{ic['hex']}"
        if self._too_close(col):
            col = self.t["dark_logo"]
        s = size / 24
        (layer if layer is not None else self.front).append(
            f'<path transform="translate({x:.1f},{y:.1f}) scale({s:.4f})" fill="{col}" d="{ic["path"]}">'
            f"<title>{escape(ic['title'])}</title></path>"
        )

    def _too_close(self, hex_col: str) -> bool:
        """Swap logos that vanish on the background (e.g. GitHub's near-black)."""
        h = hex_col.lstrip("#")
        r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        return lum < 0.12 if self.theme == "dark" else lum > 0.80

    def tile(self, slug, x, y, size=34, layer=None):
        layer = layer if layer is not None else self.front
        t = self.t
        layer.append(
            f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="{size * 0.26:.1f}" '
            f'fill="{t["tile"]}" stroke="{t["border"]}" stroke-width="1"/>'
        )
        if slug == "delta":
            self.delta_glyph(x + size / 2, y + size / 2, size * 0.58, layer)
        elif slug == "csv":
            self.file_glyph(x + size / 2, y + size / 2, size * 0.62, layer)
        elif slug == "contract":
            self.contract_glyph(x + size / 2, y + size / 2, size * 0.62, layer)
        elif slug not in ICONS:
            self.box_glyph(x + size / 2, y + size / 2, size * 0.56, layer)
        else:
            pad = size * 0.2
            self.logo(slug, x + pad, y + pad, size - 2 * pad, layer=layer)

    def delta_glyph(self, cx, cy, s, layer):
        """Generic delta mark for Delta Lake (Simple Icons has no Delta Lake logo)."""
        c = "#00ADD4"
        h = s * 0.9
        layer.append(
            f'<path d="M{cx:.1f},{cy - h / 2:.1f} L{cx + s / 2:.1f},{cy + h / 2:.1f} '
            f'L{cx - s / 2:.1f},{cy + h / 2:.1f} Z" fill="none" stroke="{c}" '
            f'stroke-width="{s * 0.16:.1f}" stroke-linejoin="round"/>'
        )

    def contract_glyph(self, cx, cy, s, layer):
        """Generic data-contract mark (shield + check) for Great Expectations."""
        c = self.t["ok"]
        w, h = s * 0.82, s
        x, y = cx - w / 2, cy - h / 2
        layer.append(
            f'<path d="M{cx:.1f},{y:.1f} L{x + w:.1f},{y + h * 0.2:.1f} V{y + h * 0.52:.1f} '
            f"Q{x + w:.1f},{y + h * 0.86:.1f} {cx:.1f},{y + h:.1f} Q{x:.1f},{y + h * 0.86:.1f} "
            f'{x:.1f},{y + h * 0.52:.1f} V{y + h * 0.2:.1f} Z" fill="none" stroke="{c}" '
            f'stroke-width="1.8" stroke-linejoin="round"/>'
            f'<path d="M{cx - w * 0.22:.1f},{cy + h * 0.02:.1f} L{cx - w * 0.04:.1f},{cy + h * 0.2:.1f} '
            f'L{cx + w * 0.26:.1f},{cy - h * 0.14:.1f}" fill="none" stroke="{c}" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
        )

    def box_glyph(self, cx, cy, s, layer):
        """Neutral mark for a technology without a Simple Icons logo (never a look-alike)."""
        c = self.t["ext"]
        layer.append(
            f'<rect x="{cx - s / 2:.1f}" y="{cy - s / 2:.1f}" width="{s:.1f}" height="{s:.1f}" rx="{s * 0.2:.1f}" '
            f'fill="none" stroke="{c}" stroke-width="1.8"/>'
            f'<path d="M{cx - s * 0.22:.1f},{cy:.1f} H{cx + s * 0.22:.1f}" stroke="{c}" stroke-width="1.8"/>'
        )

    def file_glyph(self, cx, cy, s, layer):
        c = self.t["ext"]
        w, h = s * 0.78, s
        x, y = cx - w / 2, cy - h / 2
        f = w * 0.32
        layer.append(
            f'<path d="M{x:.1f},{y:.1f} H{x + w - f:.1f} L{x + w:.1f},{y + f:.1f} V{y + h:.1f} '
            f'H{x:.1f} Z" fill="none" stroke="{c}" stroke-width="1.8" stroke-linejoin="round"/>'
            f'<path d="M{x + w * 0.22:.1f},{y + h * 0.55:.1f} H{x + w * 0.78:.1f} M{x + w * 0.22:.1f},'
            f'{y + h * 0.75:.1f} H{x + w * 0.78:.1f}" stroke="{c}" stroke-width="1.6"/>'
        )

    # cards -----------------------------------------------------------------
    def card(
        self,
        x,
        y,
        w,
        h,
        accent,
        eyebrow,
        title,
        tech,
        lines,
        icons=(),
        shape="box",
        title_size=21,
        line_size=14.5,
    ):
        t = self.t
        cid = self.uid()
        if shape == "cylinder":
            e = 11
            body = (
                f"M{x},{y + e} A{w / 2},{e} 0 0 1 {x + w},{y + e} V{y + h - e} "
                f"A{w / 2},{e} 0 0 1 {x},{y + h - e} Z"
            )
            self.front.append(
                f'<path d="{body}" fill="{t["card"]}" stroke="{t["border"]}" stroke-width="1.25"/>'
            )
            self.front.append(
                f'<ellipse cx="{x + w / 2}" cy="{y + e}" rx="{w / 2}" ry="{e}" fill="{t["card2"]}" '
                f'stroke="{accent}" stroke-width="2"/>'
            )
            top = y + 2 * e - 4
        else:
            self.defs.append(
                f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14"/></clipPath>'
            )
            self.front.append(
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{t["card"]}" '
                f'stroke="{t["border"]}" stroke-width="1.25" filter="url(#shadow)"/>'
            )
            self.front.append(
                f'<rect x="{x}" y="{y}" width="{w}" height="4" fill="{accent}" clip-path="url(#{cid})"/>'
            )
            top = y
        px = x + 20
        self.text(px, top + 31, eyebrow, 11.5, 500, accent, MONO, spacing=1.1)
        n = len(icons)
        for i, slug in enumerate(icons):
            self.tile(slug, x + w - 16 - 32 * (n - i) - 6 * (n - 1 - i), top + 14, 32)
        self.text(px, top + 61, title, title_size, 700)
        if tech:
            self.text(px, top + 84, tech, 12.5, 400, t["muted"], MONO)
        for i, ln in enumerate(lines):
            self.text(px, top + 111 + i * 20, ln, line_size, 400, t["muted"])

    def person(self, x, y, w, h, title, lines, color=None):
        t = self.t
        c = color or t["person"]
        cx = x + w / 2
        self.front.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="28" fill="{t["card"]}" '
            f'stroke="{c}" stroke-width="1.6" filter="url(#shadow)"/>'
        )
        self.front.append(
            f'<circle cx="{cx}" cy="{y - 2}" r="21" fill="{t["card"]}" stroke="{c}" stroke-width="1.6"/>'
        )
        self.front.append(
            f'<circle cx="{cx}" cy="{y - 7}" r="6.5" fill="{c}"/>'
            f'<path d="M{cx - 11},{y + 11} a11,9 0 0 1 22,0" fill="{c}"/>'
        )
        self.text(cx, y + 42, "PERSON", 11, 500, c, MONO, "middle", 1.2)
        self.text(cx, y + 68, title, 19, 700, anchor="middle")
        for i, ln in enumerate(lines):
            self.text(cx, y + 93 + i * 19, ln, 14, 400, t["muted"], anchor="middle")

    def boundary(
        self, x, y, w, h, color, eyebrow, title, icons=(), tab="left", dash=True
    ):
        t = self.t
        d = ' stroke-dasharray="8 7"' if dash else ""
        self.back.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="22" fill="{color}" fill-opacity="0.045" '
            f'stroke="{color}" stroke-opacity="0.75" stroke-width="1.6"{d}/>'
        )
        tw = 26 + len(icons) * 30 + len(eyebrow) * 8.4 + len(title) * 8.9 + 26
        tx = x + 28 if tab == "left" else x + w - 28 - tw
        self.back.append(
            f'<rect x="{tx}" y="{y - 17}" width="{tw:.0f}" height="34" rx="17" fill="{t["bg"]}" '
            f'stroke="{color}" stroke-opacity="0.75" stroke-width="1.4"/>'
        )
        cx = tx + 14
        for slug in icons:
            if slug in ICONS:
                self.logo(slug, cx, y - 9, 18, layer=self.back)
            cx += 30
        self.text(
            cx, y + 5, eyebrow, 12, 500, color, MONO, spacing=1.1, layer=self.back
        )
        cx += len(eyebrow) * 8.4 + 12
        self.text(cx, y + 5.5, title, 15, 600, t["text"], layer=self.back)

    # arrows ----------------------------------------------------------------
    def arrow(self, pts, color=None, width=1.8, dashed=False, halo=False, head=True):
        t = self.t
        c = color or t["line"]
        mk = self.marker(c) if head else None
        d = "M" + " L".join(f"{px},{py}" for px, py in pts)
        if halo:
            self.mid.append(
                f'<path d="{d}" fill="none" stroke="{t["halo"]}" stroke-width="9" stroke-linecap="round"/>'
            )
        dash = ' stroke-dasharray="6 6"' if dashed else ""
        m = f' marker-end="url(#{mk})"' if mk else ""
        self.mid.append(
            f'<path d="{d}" fill="none" stroke="{c}" stroke-width="{width}" '
            f'stroke-linejoin="round"{dash}{m}/>'
        )

    def marker(self, color):
        if color not in self._markers:
            mid = self.uid("m")
            self._markers[color] = mid
            self.defs.append(
                f'<marker id="{mid}" viewBox="0 0 12 12" refX="10.5" refY="6" markerWidth="10" '
                f'markerHeight="10" orient="auto-start-reverse" markerUnits="userSpaceOnUse">'
                f'<path d="M1,1.5 L11,6 L1,10.5 Z" fill="{color}"/></marker>'
            )
        return self._markers[color]

    def label(self, x, y, lines, anchor="middle", tech=None, color=None):
        """Relationship label: pill with 1–2 lines + optional [technology] line."""
        t = self.t
        rows = [
            (s, 13.5, 500, t["text"] if color is None else color, SANS) for s in lines
        ]
        if tech:
            rows.append((tech, 12, 400, t["muted"], MONO))
        wmax = max(len(r[0]) * (r[1] * (0.6 if r[4] == MONO else 0.53)) for r in rows)
        h = 12 + 18 * len(rows)
        w = wmax + 24
        bx = x - w / 2 if anchor == "middle" else (x - w if anchor == "end" else x)
        self.front.append(
            f'<rect x="{bx:.1f}" y="{y - h / 2:.1f}" width="{w:.1f}" height="{h}" rx="9" '
            f'fill="{t["bg"]}" fill-opacity="0.94" stroke="{t["border"]}" stroke-width="1"/>'
        )
        cx = bx + w / 2
        for i, (s, sz, wt, col, fam) in enumerate(rows):
            self.text(cx, y - h / 2 + 22 + i * 18, s, sz, wt, col, fam, "middle")

    # page ------------------------------------------------------------------
    def header(self, eyebrow, title, subtitle, stack):
        t = self.t
        self.text(60, 66, eyebrow, 14, 500, t["ana"], MONO, spacing=1.6)
        self.text(60, 112, title, 40, 800, spacing=-0.6)
        self.text(60, 146, subtitle, 17.5, 400, t["muted"])
        x = self.w - 60 - len(stack) * 52 + 8
        for slug in stack:
            self.tile(slug, x, 70, 44)
            x += 52
        self.text(self.w - 60, 52, "STACK", 11.5, 500, t["faint"], MONO, "end", 1.4)

    def legend(
        self,
        y,
        items_note,
        kinds=("person", "container", "store", "external", "boundary", "rel"),
    ):
        t = self.t
        x = 60

        def sw(kind, label):
            nonlocal x
            if kind == "person":
                self.front.append(
                    f'<rect x="{x}" y="{y - 13}" width="26" height="18" rx="9" fill="none" stroke="{t["person"]}" stroke-width="1.6"/>'
                )
            elif kind == "container":
                self.front.append(
                    f'<rect x="{x}" y="{y - 13}" width="26" height="18" rx="4" fill="{t["card"]}" stroke="{t["border"]}"/>'
                    f'<rect x="{x}" y="{y - 13}" width="26" height="3" fill="{t["ops"]}"/>'
                )
            elif kind == "store":
                self.front.append(
                    f'<path d="M{x},{y - 10} a13,4 0 0 1 26,0 v12 a13,4 0 0 1 -26,0 Z" fill="{t["card"]}" stroke="{t["gold"]}" stroke-width="1.4"/>'
                )
            elif kind == "external":
                self.front.append(
                    f'<rect x="{x}" y="{y - 13}" width="26" height="18" rx="4" fill="{t["card"]}" stroke="{t["border"]}"/>'
                    f'<rect x="{x}" y="{y - 13}" width="26" height="3" fill="{t["ext"]}"/>'
                )
            elif kind == "boundary":
                self.front.append(
                    f'<rect x="{x}" y="{y - 13}" width="26" height="18" rx="5" fill="none" stroke="{t["ana"]}" stroke-dasharray="4 3" stroke-width="1.4"/>'
                )
            elif kind == "rel":
                self.front.append(
                    f'<path d="M{x},{y - 4} H{x + 22}" stroke="{t["line"]}" stroke-width="1.8" marker-end="url(#{self.marker(t["line"])})"/>'
                )
            self.text(x + 36, y + 1, label, 13.5, 500, t["muted"])
            x += 36 + len(label) * 7.4 + 34

        self.text(60, y - 34, "LEGEND", 11.5, 500, t["faint"], MONO, spacing=1.4)
        labels = {
            "person": "Person",
            "container": "Container",
            "component": "Component",
            "store": "Data store",
            "external": "External system",
            "boundary": "Boundary",
            "rel": "Uses / data flow",
        }
        for k in kinds:
            sw("container" if k == "component" else k, labels[k])
        self.text(self.w - 60, y + 1, items_note, 13, 400, t["faint"], MONO, "end")

    def svg(self, title, desc) -> str:
        t = self.t
        grid = (
            f'<pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse">'
            f'<circle cx="1" cy="1" r="1" fill="{t["grid"]}"/></pattern>'
        )
        sh_op = 0.35 if self.theme == "dark" else 0.07
        shadow = (
            f'<filter id="shadow" x="-10%" y="-10%" width="120%" height="130%">'
            f'<feDropShadow dx="0" dy="6" stdDeviation="9" flood-color="#000" flood-opacity="{sh_op}"/></filter>'
        )
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" role="img" aria-labelledby="t d">'
            f'<title id="t">{escape(title)}</title><desc id="d">{escape(desc)}</desc>'
            f"<defs><style>{font_css()}</style>{grid}{shadow}{''.join(self.defs)}</defs>"
            f'<rect width="100%" height="100%" fill="{t["bg"]}"/>'
            f'<rect width="100%" height="100%" fill="url(#grid)"/>'
            + "".join(self.back)
            + "".join(self.mid)
            + "".join(self.front)
            + "</svg>"
        )


# ── render ──────────────────────────────────────────────────────────────────
def chromium() -> str | None:
    for name in (
        "chromium",
        "chromium-browser",
        "google-chrome",
        "google-chrome-stable",
    ):
        if p := shutil.which(name):
            return p
    return None


def to_png(svg_path: Path, w: int, h: int, browser: str) -> None:
    with tempfile.TemporaryDirectory() as d:
        page = Path(d) / "p.html"
        page.write_text(
            f'<!doctype html><html><body style="margin:0">'
            f'<img src="{svg_path.as_uri()}" width="{w}" height="{h}" style="display:block"></body></html>'
        )
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
                f"--screenshot={svg_path.with_suffix('.png')}",
                page.as_uri(),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )


def build(here: Path, diagrams) -> None:
    """diagrams: iterable of (name, fn(theme) -> svg, (w, h)). Writes c4-<name>-<theme>.svg/.png."""
    svg_only = "--svg-only" in sys.argv
    browser = None if svg_only else chromium()
    if not svg_only and not browser:
        sys.exit("Chromium not found: install it or pass --svg-only")
    for name, fn, size in diagrams:
        for theme in THEMES:
            out = here / f"c4-{name}-{theme}.svg"
            out.write_text(fn(theme))
            if browser:
                to_png(out, *size, browser)
            print(f"wrote {out.name}" + ("" if svg_only else " + .png"))
