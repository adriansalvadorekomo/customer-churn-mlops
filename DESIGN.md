<!-- impeccable:design-schema 1 -->

# Design

## World

**The bank back-office decision desk.** The product is a prediction console,
but it presents as a physical desk where single customer case files are
handled: a manila intake sheet with ruled fields, carbon-copy figures, and an
inked rubber-stamp verdict filed into a ledger. The world is chosen against
the category default (dark glassy dashboard, gradient KPI cards) — it comes
from what the *subject* does (a bank scoring one customer at a time), not from
what dashboards look like.

Direction roll: seed `2203f498`, assigned candidate index 3 of seven grounded
directions. Raised by the disciplines of four declined challengers: split-flap
arrival cascade (the verdict resolves in staged ticks), vertical-feed hard
states (binary verdicts, no in-between), labanotation density channel (shade
encodes quantity, never hue alone), lexicon measure discipline (fixed reading
measure; width goes to structure). Competitive alternates seen and set aside:
the design-annual plate section, the jet-age ticket wallet.

## Platform & Stack

web · Astro static build + Tailwind 4 · tokens live in
`frontend/src/styles/global.css` (`@theme`). Fonts self-hosted via Fontsource
(no CDN — the stack runs offline).

## Color tokens

| Token | Value | Role |
|-------|-------|------|
| `desk` / `desk-deep` | `#2e342e` / `#242924` | Steel-green desk ground |
| `steel` / `steel-dark` | `#a6ada3` / `#46504a` | Secondary text on desk, hardware rules |
| `manila` / `manila-deep` | `#e7dfc6` / `#d9cfae` | Paper surfaces (case files, tabs) |
| `ink` / `ink-soft` | `#1e251f` / `#4d5649` | Text on paper |
| `carbon` | `#3f4568` | Carbon-copy figures, refs, links on paper |
| `stamp-red` / `stamp-green` | `#b3311f` / `#1f5c3a` | Verdict stamps, errors / verified |

Rules: gray never lands on color — desk secondary text tints toward steel,
paper secondary text toward ink/green; vermilion and pine are reserved for
stamps and state, never decoration.

## Type

- **Archivo Variable** (wght 100–900, wdth 62–125): all words — headings,
  labels, controls, tabular figures in tables. Wordmark at wdth 116%.
- **Courier Prime**: all measurement — figures, case refs, timestamps,
  receipts, mono labels. Numbers always `tabular-nums`.
- Display max 2.75rem (intake h1), inline result figure 2.7rem, body measure
  62–68ch.

## Materials & geometry

Flat manila panels (3px radius, one soft offset shadow, no border); steel desk
panels (1px `steel-dark` border, no shadow); punched filing holes on case
files; hairlines drawn from ink/steel mixes; index tabs that sit on the
section rule; dashed empty slot for the un-stamped verdict. No textures, no
gradients, no noise. Ink irregularity comes from rotation, double frames, and
`mix-blend-mode: multiply` — the stamp sits *into* the paper. Scrollbars are
slim 6px muted-green pills on a transparent track (arrow buttons hidden;
Firefox gets the `scrollbar-width`/`scrollbar-color` fallback).

## Named rules

1. **Stamp anatomy** — verdict stamps rotate off-axis (leaves −2°, stays
   +1.6°), double-framed, text-first (color is redundant encoding).
2. **Density as data** — the confusion matrix shades cells by count; text
   inverts on dark cells. Quantities are never carried by hue.
3. **Arrival cascade** — the verdict arrives in staged mono lines, then the
   stamp lands exactly once and rests.
4. **Hard states** — a case resolves to `stays` or `leaves`; no ambiguous
   middle is shown, and failures say so plainly ("the desk got no verdict").
5. **Measure discipline** — prose holds a fixed measure; tables and figures
   absorb the width.
6. **One-screen frame** — at ≥lg each case file fills the rest of the first
   viewport (`sheet-fit`), so the whole sheet reads without page scrolling;
   inner lists scroll only when the window itself is short, and short-window
   tiers tighten the dossier before dropping optional copy.

## Motion

One authored moment: `stamp-land` (320ms, expo-out) riding the staged status
lines (230ms apart, min 720ms total). Everything else ≤160ms or static.
`prefers-reduced-motion` removes staging and landing entirely.

## States

Verdict pan: empty (dashed slot) · loading (staged lines + CSS caret) ·
result (stamp, case ref `CD-yymm-nnnn`, request receipt in JSON) · error (red
no-answer slip with backend-start hints, reachable because `/predict` carries
a 15 s timeout). When the sheet was long and the pan landed off-screen, the
pan scrolls into view as the verdict arrives (smooth; instant under reduced
motion, and a no-op when the pan is already visible). Unknown URLs get an
in-world "not on file" slip (`404.astro`). Intake: per-field inline errors in
red ink, `data-invalid` turns the rule red, `aria-invalid` + described-by
wire the errors for assistive tech. Ledger: empty state + two-step
"void all" (arm → confirm, auto-disarms). API lamp: checking / online /
offline pinned in the masthead, refreshed every 20s and after every
prediction.

## Accessibility

`currentColor` focus rings (2px, offset), full keyboard path, labels bound to
controls, errors announced as text, verdict pan is `aria-live="polite"`, skip
link, reduced-motion honored. Contrast: ink on manila ≈12:1, carbon on manila
≈6.8:1, steel on desk-deep ≈5.6:1, stamp red on manila ≈4.6:1 (large text).

## Provenance

Every displayed number comes from the repo's verified run: accuracy 85.55%,
classification report (0: .87/.97/.91, 1: .78/.42/.55), confusion matrix
[[1535, 50], [239, 176]]. No invented users, customers, or benchmarks. The
sample case is dataset row 5 (Mitchell) with its recorded outcome stated.
