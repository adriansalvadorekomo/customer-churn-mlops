"""C4 drawing kit shared by the project READMEs, in the identity of the portfolio (DESIGN.md).

Canvas primitives: header, cards (containers, stores, externals), people, boundaries,
arrows, relationship labels, legend. SVGs embed Schibsted Grotesk / IBM Plex Mono (OFL) as base64
woff2 and technology logos as inline Simple Icons paths (CC0, assets/icons.json), so
they render offline; PNGs are taken at 2x with headless Chromium.

Each repository's build_c4.py imports this module and only describes its own model.
Stdlib only.
"""

from __future__ import annotations

import base64
import itertools
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


# ── themes: the "instrument" identity (portfolio DESIGN.md) ─────────────────
# Two grounds, one signal. Graphite (dark) and aluminium (light) plates, silkscreen
# mono labels, and exactly one colour: orange, reserved for the gate, the step where
# bad data, code or a model is stopped. Every other category key resolves to the
# same neutral ink; a card says what it is in its silkscreen line, not with a hue.
_DARK = {
    "bench": "#121212",
    "plate": "#191919",
    "card": "#1e1e1d",
    "card2": "#232322",
    "line": "#2e2e2d",
    "strong": "#4a4945",
    "text": "#ebe9e4",
    "muted": "#c4c0b7",
    "faint": "#9d998f",
    "arrow": "#a8a49b",
    "signal": "#ff4f00",
    "signal_text": "#ff6a26",
    "display": "#0d0d0d",
    "display_off": "#232323",
    "display_dim": "#8a867e",
    "highlight": "rgba(255,255,255,0.06)",
    "led_off": "#3a3a3a",
    "external": "#7d796f",
    "logo": "#c4c0b7",
}
_LIGHT = {
    "bench": "#d9d6cf",
    "plate": "#e8e6e1",
    "card": "#f1efeb",
    "card2": "#e9e7e2",
    "line": "#c9c5bc",
    "strong": "#a9a59c",
    "text": "#121212",
    "muted": "#3b3833",
    "faint": "#57534c",
    "arrow": "#57534c",
    "signal": "#ff4f00",
    "signal_text": "#a33300",
    "display": "#0d0d0d",
    "display_off": "#232323",
    "display_dim": "#8a867e",
    "highlight": "rgba(255,255,255,0.6)",
    "led_off": "#c9c5bc",
    "external": "#8a8478",
    "logo": "#3b3833",
}


def _theme(p: dict) -> dict:
    t = dict(p)
    # compatibility keys used by the build scripts: neutral categories, one signal
    for k in ("ops", "ana", "dlv", "gold", "person", "bronze", "silver"):
        t[k] = p["faint"]
    t["ext"] = p["external"]
    t["ok"] = p["signal_text"]  # gates: orange outline, lit LED
    t["bg"] = p["bench"]
    t["border"] = p["line"]
    t["tile"] = p["card2"]
    t["halo"] = p["plate"]
    t["dark_logo"] = p["logo"]
    return t


THEMES = {"dark": _theme(_DARK), "light": _theme(_LIGHT)}

SANS = "'Schibsted Grotesk', ui-sans-serif, system-ui, sans-serif"
MONO = "'IBM Plex Mono', ui-monospace, Menlo, Consolas, monospace"


def font_css() -> str:
    faces = [
        ("Schibsted Grotesk", 400, "schibsted-grotesk-latin-400-normal"),
        ("Schibsted Grotesk", 500, "schibsted-grotesk-latin-500-normal"),
        ("IBM Plex Mono", 400, "ibm-plex-mono-latin-400-normal"),
        ("IBM Plex Mono", 500, "ibm-plex-mono-latin-500-normal"),
    ]
    out = []
    for fam, w, f in faces:
        b64 = base64.b64encode((ASSETS / "fonts" / f"{f}.woff2").read_bytes()).decode()
        out.append(
            f"@font-face{{font-family:'{fam}';font-weight:{w};font-style:normal;"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}"
        )
    return "".join(out)


def text_width(s: str, size: float, mono: bool = False) -> float:
    """Rendered width estimate: JetBrains Mono is 0.6 em per glyph; Inter about 0.56 em on average."""
    if mono:
        return len(s) * size * 0.6
    narrow = sum(ch in "iljtfr.,:;'|!() " for ch in s)
    wide = sum(ch in "mwMW@%" for ch in s) + sum(ch.isupper() for ch in s) * 0.35
    return size * (0.555 * len(s) - 0.24 * narrow + 0.25 * wide)


# ── drawing primitives ──────────────────────────────────────────────────────
class Canvas:
    def __init__(self, w: int, h: int, theme: str):
        self.w, self.h, self.t = w, h, THEMES[theme]
        _LAST.append(self)
        self.theme = theme
        self.defs: list[str] = []
        self.back: list[str] = []  # boundaries
        self.mid: list[str] = []  # arrows
        self.front: list[str] = []  # cards, labels
        self._id = 0
        self._markers: dict[str, str] = {}
        # Geometry for lint(): every box (kind, name, x, y, w, h), every arrow, text overflow.
        self.boxes: list[tuple[str, str, float, float, float, float]] = []
        self.arrows: list[list[tuple[float, float]]] = []
        self.issues: list[str] = []
        self._quiet = 0  # >0 while a primitive draws its own text

    def _box(self, kind, name, x, y, w, h):
        self.boxes.append((kind, name, x, y, w, h))

    def _fits(self, what, text, size, avail, mono=False):
        width = text_width(text, size, mono)
        if width > avail + 0.5:
            self.issues.append(
                f"overflow: {what} {text!r} needs {width:.0f}px, has {avail:.0f}px"
            )

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
        if not self._quiet and layer is None:
            w = text_width(s, size, family == MONO)
            x0 = x - w if anchor == "end" else (x - w / 2 if anchor == "middle" else x)
            self._box("note", s[:40], x0, y - size * 0.8, w, size * 1.05)
        ls = f' letter-spacing="{spacing}"' if spacing else ""
        op = f' opacity="{opacity}"' if opacity != 1 else ""
        (layer if layer is not None else self.front).append(
            f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}"{ls}{op}>{escape(s)}</text>'
        )

    # icons -----------------------------------------------------------------
    def logo(self, slug, x, y, size, color=None, layer=None):
        """Technology marks are printed like silkscreen: one ink, never brand colours."""
        ic = ICONS[slug]
        col = color or self.t["logo"]
        s = size / 24
        (layer if layer is not None else self.front).append(
            f'<path transform="translate({x:.1f},{y:.1f}) scale({s:.4f})" fill="{col}" d="{ic["path"]}">'
            f"<title>{escape(ic['title'])}</title></path>"
        )

    def tile(self, slug, x, y, size=34, layer=None, color=None):
        layer = layer if layer is not None else self.front
        t = self.t
        layer.append(
            f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="4" '
            f'fill="{t["card2"]}" stroke="{t["line"]}" stroke-width="1"/>'
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
            pad = size * 0.22
            self.logo(slug, x + pad, y + pad, size - 2 * pad, color=color, layer=layer)

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
        """A plate on the faceplate. accent t["ok"] = a gate (orange outline, lit LED);
        accent t["ext"] = an external system (dashed edge). Everything else is neutral."""
        t = self.t
        self._quiet += 1
        self._box("card", title, x, y, w, h)
        gate = accent == t["ok"]
        external = accent == t["ext"]
        edge = (
            t["signal"] if gate else t["strong"] if shape == "cylinder" else t["line"]
        )
        sw = 1.6 if gate else 1.1
        dash = ' stroke-dasharray="6 4"' if external else ""
        if shape == "cylinder":
            e = 11
            body = (
                f"M{x},{y + e} A{w / 2},{e} 0 0 1 {x + w},{y + e} V{y + h - e} "
                f"A{w / 2},{e} 0 0 1 {x},{y + h - e} Z"
            )
            self.front.append(
                f'<path d="{body}" fill="{t["card"]}" stroke="{edge}" stroke-width="{sw}"{dash}/>'
            )
            self.front.append(
                f'<ellipse cx="{x + w / 2}" cy="{y + e}" rx="{w / 2}" ry="{e}" fill="{t["card2"]}" '
                f'stroke="{edge}" stroke-width="{sw}"/>'
            )
            top = y + 2 * e - 4
        else:
            self.front.append(
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{t["card"]}" '
                f'stroke="{edge}" stroke-width="{sw}"{dash}/>'
            )
            self.front.append(
                f'<path d="M{x + 6},{y + 1.5} H{x + w - 6}" stroke="{t["highlight"]}" stroke-width="1"/>'
            )
            top = y
        px = x + 20
        big = title_size > 24
        y_title = top + (72 if big else 61)
        y_tech = y_title + (27 if big else 23)
        lh = 20 if line_size <= 15 else round(line_size * 1.5)
        y_lines = y_tech + (34 if big else 27)
        # status LED + silkscreen line
        led = t["signal"] if gate else t["led_off"]
        self.front.append(
            f'<rect x="{px}" y="{top + 22}" width="9" height="9" rx="2" fill="{led}"/>'
        )
        self.text(
            px + 17,
            top + 31,
            eyebrow,
            11.5,
            500,
            t["signal_text"] if gate else t["faint"],
            MONO,
            spacing=0.9,
        )
        n = len(icons)
        for i, slug in enumerate(icons):
            self.tile(slug, x + w - 16 - 32 * (n - i) - 6 * (n - 1 - i), top + 14, 32)
        self.text(px, y_title, title, title_size, 500, spacing=-0.02 * title_size)
        if tech:
            self.text(px, y_tech, tech, 13.5 if big else 12.5, 400, t["faint"], MONO)
        for i, ln in enumerate(lines):
            self.text(px, y_lines + i * lh, ln, line_size, 400, t["muted"])
        icons_w = n * 38
        self._fits(
            f"card {title!r} eyebrow",
            eyebrow,
            11.5,
            w - 57 - icons_w - 0.9 * len(eyebrow),
            mono=True,
        )
        self._fits(
            f"card {title!r} title",
            title,
            title_size,
            w - 40 - (icons_w if title_size > 22 else 0),
        )
        if tech:
            self._fits(
                f"card {title!r} tech", tech, 13.5 if big else 12.5, w - 40, mono=True
            )
        for ln in lines:
            self._fits(f"card {title!r} line", ln, line_size, w - 40)
        if lines and y_lines + (len(lines) - 1) * lh + 8 > y + h - 6:
            self.issues.append(
                f"overflow: card {title!r} has {len(lines)} lines, too many for height {h}"
            )
        self._quiet -= 1

    def person(self, x, y, w, h, title, lines, color=None):
        t = self.t
        self._quiet += 1
        self._box("person", title, x, y - 23, w, h + 23)
        cx = x + w / 2
        self.front.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{t["card"]}" '
            f'stroke="{t["strong"]}" stroke-width="1.2"/>'
            f'<path d="M{x + 10},{y + 1.5} H{x + w - 10}" stroke="{t["highlight"]}" stroke-width="1"/>'
        )
        self.front.append(
            f'<circle cx="{cx}" cy="{y - 2}" r="21" fill="{t["card"]}" stroke="{t["strong"]}" '
            f'stroke-width="1.2"/>'
            f'<circle cx="{cx}" cy="{y - 7}" r="6" fill="{t["faint"]}"/>'
            f'<path d="M{cx - 11},{y + 11} a11,9 0 0 1 22,0" fill="{t["faint"]}"/>'
        )
        self.text(cx, y + 42, "PERSON", 11, 500, t["faint"], MONO, "middle", 1.0)
        self.text(cx, y + 68, title, 19, 500, anchor="middle", spacing=-0.3)
        for i, ln in enumerate(lines):
            self.text(cx, y + 93 + i * 19, ln, 14, 400, t["muted"], anchor="middle")
        self._fits(f"person {title!r} title", title, 19, w - 30)
        for ln in lines:
            self._fits(f"person {title!r} line", ln, 14, w - 30)
        self._quiet -= 1

    def boundary(
        self, x, y, w, h, color, eyebrow, title, icons=(), tab="left", dash=True
    ):
        t = self.t
        d = ' stroke-dasharray="7 6"' if dash else ""
        self.back.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{t["text"]}" '
            f'fill-opacity="0.018" stroke="{t["strong"]}" stroke-width="1.2"{d}/>'
        )
        ew = text_width(eyebrow, 11.5, True) + 0.9 * len(eyebrow)
        tw = 22 + len(icons) * 28 + ew + 14 + text_width(title, 14.5) + 18
        tx = x + 28 if tab == "left" else x + w - 28 - tw
        self._box("tab", title, tx, y - 15, tw, 30)
        self._quiet += 1
        self.back.append(
            f'<rect x="{tx:.1f}" y="{y - 15}" width="{tw:.0f}" height="30" rx="3" '
            f'fill="{t["plate"]}" stroke="{t["strong"]}" stroke-width="1.1"/>'
        )
        cx = tx + 13
        for slug in icons:
            if slug in ICONS:
                self.logo(slug, cx, y - 8, 16, layer=self.back)
            cx += 28
        self.text(
            cx,
            y + 4.5,
            eyebrow,
            11.5,
            500,
            t["faint"],
            MONO,
            spacing=0.9,
            layer=self.back,
        )
        cx += ew + 14
        self.text(cx, y + 5, title, 14.5, 500, t["text"], layer=self.back)
        self._quiet -= 1

    # arrows ----------------------------------------------------------------
    def arrow(self, pts, color=None, width=1.6, dashed=False, halo=False, head=True):
        t = self.t
        self.arrows.append([(float(a), float(b)) for a, b in pts])
        c = color or t["arrow"]
        mk = self.marker(c) if head else None
        d = "M" + " L".join(f"{px},{py}" for px, py in pts)
        if halo:
            self.mid.append(
                f'<path d="{d}" fill="none" stroke="{t["plate"]}" stroke-width="8" stroke-linecap="round"/>'
            )
        dash = ' stroke-dasharray="6 5"' if dashed else ""
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
        """Relationship label: a small printed plate, verb in grotesk, technology in mono."""
        t = self.t
        rows = [
            (s, 13.5, 500, t["text"] if color is None else color, SANS) for s in lines
        ]
        if tech:
            rows.append((tech, 12, 400, t["faint"], MONO))
        wmax = max(text_width(r[0], r[1], r[4] == MONO) for r in rows)
        h = 12 + 18 * len(rows)
        w = wmax + 22
        bx = x - w / 2 if anchor == "middle" else (x - w if anchor == "end" else x)
        self._box("label", " / ".join(lines), bx, y - h / 2, w, h)
        self._quiet += 1
        self.front.append(
            f'<rect x="{bx:.1f}" y="{y - h / 2:.1f}" width="{w:.1f}" height="{h}" rx="3" '
            f'fill="{t["plate"]}" stroke="{t["line"]}" stroke-width="1"/>'
        )
        cx = bx + w / 2
        for i, (s, sz, wt, col, fam) in enumerate(rows):
            self.text(cx, y - h / 2 + 22 + i * 18, s, sz, wt, col, fam, "middle")
        self._quiet -= 1

    # page ------------------------------------------------------------------
    LEVELS = (
        ("L1", "CONTEXT"),
        ("L2", "CONTAINER"),
        ("L3", "COMPONENT"),
        ("D", "DEPLOY"),
    )

    def header(self, eyebrow, title, subtitle, stack):
        """Silkscreen eyebrow and a lowercase grotesk title (as on the banner); on the right
        the always-dark display: a four-step sequencer of the C4 views with the playhead on
        this one, and the stack printed under it."""
        t = self.t
        title = title.lower()
        self._box(
            "header",
            title,
            60,
            40,
            max(text_width(title, 40) + 10, text_width(subtitle, 17.5)),
            115,
        )
        self._quiet += 1
        self.text(60, 66, eyebrow, 13, 500, t["faint"], MONO, spacing=1.3)
        self.text(60, 112, title, 40, 500, spacing=-1.4)
        self.text(60, 146, subtitle, 17.5, 400, t["muted"])
        e = eyebrow.upper()
        cur = (
            0 if "LEVEL 1" in e else 1 if "LEVEL 2" in e else 2 if "LEVEL 3" in e else 3
        )
        dw = max(520, len(stack) * 34 + 40)
        dx, dy, dh = self.w - 60 - dw, 38, 104
        self._box("stack", "display", dx, dy, dw, dh)
        self.front.append(
            f'<rect x="{dx}" y="{dy}" width="{dw}" height="{dh}" rx="12" fill="{t["display"]}" '
            f'stroke="{t["strong"]}" stroke-width="1"/>'
            f'<rect x="{dx + 3}" y="{dy + 3}" width="{dw - 6}" height="{dh - 6}" rx="10" fill="none" '
            f'stroke="#000" stroke-opacity="0.6" stroke-width="2"/>'
        )
        pw = (dw - 40 - 3 * 8) / 4
        for i, (code, name) in enumerate(self.LEVELS):
            px = dx + 20 + i * (pw + 8)
            on = i == cur
            self.text(
                px,
                dy + 24,
                f"{code} · {name}",
                10.5,
                500,
                "#ebe9e4" if on else t["display_dim"],
                MONO,
                spacing=0.6,
            )
            self.front.append(
                f'<rect x="{px:.1f}" y="{dy + 32}" width="{pw:.1f}" height="16" rx="3" '
                f'fill="{"#ebe9e4" if on else t["display_off"]}"/>'
            )
        x = dx + 20
        for slug in stack:
            if slug in ICONS:
                self.logo(slug, x, dy + 64, 22, color=t["display_dim"])
            x += 34
        self._quiet -= 1

    def legend(
        self,
        y,
        items_note,
        kinds=("person", "container", "store", "external", "boundary", "rel"),
        items=None,
    ):
        """Key at the bottom, listing exactly what the diagram uses. Kinds: person, card, store,
        boundary, rel, rel_dashed; a card with colour key "ext" is external, "ok" is a gate."""
        t = self.t
        self._quiet += 1
        if items is None:
            generic = {
                "person": ("person", "person", "Person"),
                "container": ("card", "ops", "Container"),
                "component": ("card", "ops", "Component"),
                "store": ("store", "gold", "Data store"),
                "external": ("card", "ext", "External system"),
                "boundary": ("boundary", "ana", "Boundary"),
                "rel": ("rel", "line", "Uses"),
            }
            items = [generic[k] for k in kinds]
        x = 60
        for kind, col, label in items:
            if kind == "person":
                self.front.append(
                    f'<rect x="{x}" y="{y - 13}" width="26" height="18" rx="7" fill="{t["card"]}" '
                    f'stroke="{t["strong"]}" stroke-width="1.2"/>'
                )
            elif kind == "card":
                gate, ext = col == "ok", col == "ext"
                edge = t["signal"] if gate else t["line"]
                dash = ' stroke-dasharray="4 3"' if ext else ""
                self.front.append(
                    f'<rect x="{x}" y="{y - 13}" width="26" height="18" rx="3" fill="{t["card"]}" '
                    f'stroke="{edge}" stroke-width="{1.6 if gate else 1.1}"{dash}/>'
                    f'<rect x="{x + 5}" y="{y - 8}" width="6" height="6" rx="1.5" '
                    f'fill="{t["signal"] if gate else t["led_off"]}"/>'
                )
            elif kind == "store":
                self.front.append(
                    f'<path d="M{x},{y - 10} a13,4 0 0 1 26,0 v12 a13,4 0 0 1 -26,0 Z" '
                    f'fill="{t["card"]}" stroke="{t["strong"]}" stroke-width="1.2"/>'
                )
            elif kind == "boundary":
                self.front.append(
                    f'<rect x="{x}" y="{y - 13}" width="26" height="18" rx="4" fill="none" '
                    f'stroke="{t["strong"]}" stroke-dasharray="4 3" stroke-width="1.2"/>'
                )
            elif kind in ("rel", "rel_dashed"):
                dash = ' stroke-dasharray="5 4"' if kind == "rel_dashed" else ""
                self.front.append(
                    f'<path d="M{x},{y - 4} H{x + 22}" stroke="{t["arrow"]}" stroke-width="1.6"{dash} '
                    f'marker-end="url(#{self.marker(t["arrow"])})"/>'
                )
            self.text(x + 36, y + 1, label, 13.5, 400, t["muted"])
            x += 36 + text_width(label, 13.5) + 30
        self.text(60, y - 34, "LEGEND", 11.5, 500, t["faint"], MONO, spacing=1.2)
        self.text(self.w - 60, y + 1, items_note, 12.5, 400, t["faint"], MONO, "end")
        self._box("legend", "legend", 60, y - 48, x - 60, 56)
        nw = text_width(items_note, 12.5, True)
        self._box("legend-note", items_note, self.w - 60 - nw, y - 12, nw, 16)
        self._quiet -= 1

    # quality gate ------------------------------------------------------------
    def lint(self) -> list[str]:
        """Collisions a reader would notice: overlapping boxes and labels, arrows through cards,
        text overflowing its card, anything off the canvas."""
        out = list(self.issues)
        solid = (
            "card",
            "person",
            "label",
            "tab",
            "note",
            "header",
            "stack",
            "legend",
            "legend-note",
        )

        def overlap(a, b, pad=1.0):
            return (
                a[2] < b[2] + b[4] - pad
                and b[2] < a[2] + a[4] - pad
                and a[3] < b[3] + b[5] - pad
                and b[3] < a[3] + a[5] - pad
            )

        bx = [b for b in self.boxes if b[0] in solid]
        for i, a in enumerate(bx):
            if a[2] < 0 or a[3] < 0 or a[2] + a[4] > self.w or a[3] + a[5] > self.h:
                out.append(f"off-canvas: {a[0]} {a[1]!r}")
            for b in bx[i + 1 :]:
                if overlap(a, b):
                    out.append(f"overlap: {a[0]} {a[1]!r} and {b[0]} {b[1]!r}")

        def seg_hits(p, q, r):
            (x1, y1), (x2, y2) = p, q
            rx, ry, rw, rh = r
            if x1 == x2:
                return rx < x1 < rx + rw and max(min(y1, y2), ry) < min(
                    max(y1, y2), ry + rh
                )
            if y1 == y2:
                return ry < y1 < ry + rh and max(min(x1, x2), rx) < min(
                    max(x1, x2), rx + rw
                )
            n = 40  # diagonal: sample
            return any(
                rx < x1 + (x2 - x1) * k / n < rx + rw
                and ry < y1 + (y2 - y1) * k / n < ry + rh
                for k in range(n + 1)
            )

        blockers = [
            b
            for b in self.boxes
            if b[0] in ("card", "person", "tab", "header", "stack", "legend")
        ]
        for pts in self.arrows:
            for p, q in itertools.pairwise(pts):
                for b in blockers:
                    r = (b[2] + 4, b[3] + 4, b[4] - 8, b[5] - 8)
                    if r[2] > 0 and r[3] > 0 and seg_hits(p, q, r):
                        out.append(f"arrow {pts[0]}→{pts[-1]} crosses {b[0]} {b[1]!r}")
        return sorted(set(out))

    def svg(self, title, desc) -> str:
        """The faceplate: a plate on the bench with four corner screws (the banner's hardware)."""
        t = self.t
        w, h = self.w, self.h
        screws = []
        for sx, sy in ((26, 26), (w - 26, 26), (26, h - 26), (w - 26, h - 26)):
            screws.append(
                f'<circle cx="{sx}" cy="{sy}" r="7" fill="{t["card2"]}" stroke="{t["strong"]}" '
                f'stroke-width="1"/><path d="M{sx - 4.2},{sy + 4.2} L{sx + 4.2},{sy - 4.2}" '
                f'stroke="{t["strong"]}" stroke-width="1.4" stroke-linecap="round"/>'
            )
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-labelledby="t d">'
            f'<title id="t">{escape(title)}</title><desc id="d">{escape(desc)}</desc>'
            f"<defs><style>{font_css()}</style>{''.join(self.defs)}</defs>"
            f'<rect width="100%" height="100%" fill="{t["bench"]}"/>'
            f'<rect x="8" y="8" width="{w - 16}" height="{h - 16}" rx="16" fill="{t["plate"]}" '
            f'stroke="{t["strong"]}" stroke-width="1"/>'
            f'<path d="M24,9.5 H{w - 24}" stroke="{t["highlight"]}" stroke-width="1"/>'
            + "".join(screws)
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


_LAST: list[Canvas] = []


def lint_diagram(fn) -> list[str]:
    """Draw once (light theme) and lint the canvas the function used."""
    _LAST.clear()
    fn("light")
    return _LAST[-1].lint() if _LAST else []


def build(here: Path, diagrams) -> None:
    """diagrams: iterable of (name, fn(theme) -> svg, (w, h)). Writes c4-<name>-<theme>.svg/.png."""
    svg_only = "--svg-only" in sys.argv
    browser = None if svg_only else chromium()
    if not svg_only and not browser:
        sys.exit("Chromium not found: install it or pass --svg-only")
    problems = []
    for name, fn, size in diagrams:
        canvas_issues = lint_diagram(fn)
        if canvas_issues:
            problems += [f"{name}: {i}" for i in canvas_issues]
    if problems:
        print("\n".join(problems), file=sys.stderr)
        if "--force" not in sys.argv:
            sys.exit(f"{len(problems)} layout problem(s); fix them or pass --force")
    for name, fn, size in diagrams:
        for theme in THEMES:
            out = here / f"c4-{name}-{theme}.svg"
            out.write_text(fn(theme))
            if browser:
                to_png(out, *size, browser)
            print(f"wrote {out.name}" + ("" if svg_only else " + .png"))
