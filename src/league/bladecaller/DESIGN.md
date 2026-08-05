# Featherstorm Design Reference

Transcription of the UI design mockup at `ref/Featherstorm.html` (repo root). That file is a
~1.8 MB self-extracting bundle — a base64 manifest plus a JSON-escaped React/Babel template —
so **read this document instead of the mockup**. Everything below is the mockup's own CSS and
component structure, transcribed; nothing here is invented.

The mockup is a React SPA driven by a websocket. Bladecaller is PySide6 and does not follow its
component tree — treat this as the *visual* spec (color, type, spacing, composition), not an
architecture to copy. Qt-porting caveats are collected at the bottom.

> Values already ported live in [`resources/theme.py`](resources/theme.py) — check there first;
> this document is the source they were derived from, plus everything not yet ported.

---

## Design tokens

The mockup declares these on `:root`. `oklch()` values are given with their sRGB equivalent
(Qt stylesheets can't parse `oklch()`); the conversions below match `theme.py` exactly.

### Surfaces

| CSS var | Value | `theme.py` | Use |
|---------|-------|-----------|-----|
| `--bg0` | `#070510` | `BG0` | App/page background, root |
| `--bg1` | `#0d0a1a` | `BG1` | Card gradient end, demo bar |
| `--bg2` | `#141028` | `BG2` | Card gradient start, inputs, timer cards, phase badge |
| `--bg3` | `#1c1636` | `BG3` | Raised chips, champ-icon fallback, select fields |
| `--bg4` | `#241e44` | `BG4` | Toggle track, scrollbar thumb, progress-bar trough |
| — | `#0e0b1e` → `#0a0816` | `SIDEBAR_TOP` / `SIDEBAR_BOTTOM` | Sidebar `linear-gradient(180deg, …)` |
| `--border` | `rgba(120, 90, 180, 0.18)` | `BORDER` | Default 1px border everywhere |
| `--border-bright` | `rgba(180, 100, 200, 0.35)` | `BORDER_BRIGHT` | Hover borders, champ/item icon borders |
| — | `rgba(120, 90, 180, 0.08)` | `BORDER_SOFT` | Settings-row divider |
| — | `rgba(255, 255, 255, 0.03)` | `HOVER_WASH` | Row hover wash (nav, event, scoreboard) |

### Brand + status

| CSS var | oklch | sRGB | `theme.py` |
|---------|-------|------|-----------|
| `--accent` | `oklch(0.62 0.22 345)` | `#da3aa4` | `ACCENT` |
| `--accent-dim` | `oklch(0.45 0.18 345)` | `#93126b` | `ACCENT_DIM` |
| `--accent-glow` | `oklch(0.62 0.22 345 / 0.25)` | `rgba(218, 58, 164, 25%)` | `ACCENT_GLOW` |
| `--accent2` | `oklch(0.60 0.18 290)` | `#8267e2` | `ACCENT2` |
| `--accent2-dim` | `oklch(0.42 0.16 290)` | `#50349c` | `ACCENT2_DIM` |
| `--gold` | `oklch(0.80 0.14 68)` | `#f8ab4f` | `GOLD` |
| `--gold-glow` | `oklch(0.80 0.14 68 / 0.3)` | `rgba(248, 171, 79, 30%)` | `GOLD_GLOW` |
| `--red` | `oklch(0.62 0.22 25)` | `#ee343b` | `RED` |
| `--green` | `oklch(0.65 0.18 145)` | `#31aa40` | `GREEN` |
| `--blue` | `oklch(0.65 0.18 240)` | `#0099f0` | `BLUE` |

Recurring alpha washes of those hues (`theme.py` names them because Qt truncates float alpha to 0):

| Mockup | `theme.py` | Where |
|--------|-----------|-------|
| `oklch(0.62 0.22 345 / 0.12)` | `ACCENT_WASH` | Active nav gradient, selected rune, active demo button |
| `oklch(0.62 0.22 345 / 0.06)` | `ACCENT_FAINT` | `.scoreboard-row.you`, expanded match row (`0.05`) |
| `oklch(0.60 0.18 290 / 0.12)` | `ACCENT2_WASH` | `.badge-purple`, selected secondary tree chip |
| `oklch(0.80 0.14 68 / 0.15)` | `GOLD_WASH` | `.badge-gold`, `.event-icon.objective` |
| `oklch(0.65 0.18 145 / 0.15)` | — | `.badge-win` |
| `oklch(0.62 0.22 25 / 0.15)` | — | `.badge-loss`, `.event-icon.kill` |
| `oklch(0.65 0.18 240 / 0.15)` | — | `.event-icon.turret` |

### Text

| CSS var | Value | `theme.py` | Use |
|---------|-------|-----------|-----|
| `--text` | `#f0eaf8` | `TEXT` | Primary |
| `--text2` | `#a899c0` | `TEXT2` | Secondary — nav idle, event text, settings values |
| `--text3` | `#5c5270` | `TEXT3` | Tertiary — labels, captions, placeholders, disabled |

### Geometry

| CSS var | Value | `theme.py` |
|---------|-------|-----------|
| `--radius` | `8px` | `RADIUS` |
| `--radius-sm` | `4px` | `RADIUS_SM` |
| `--sidebar-w` | `200px` | `SIDEBAR_WIDTH` |

Radii used outside the tokens: `6px` (logo mark, badges' container chips, buttons, stat tiles,
champ icons ≥34px), `3px` (badges, small bars), `50%` (dots, rune slots, swatches, toggle thumb).

### Colors not in `theme.py`

Present in the mockup, no Qt equivalent ported yet:

| Purpose | oklch | sRGB |
|---------|-------|------|
| Logo-mark gradient end / thumbnail SVG | `oklch(0.58 0.18 290)` | `#7c60db` |
| App background radial 1 (`30% 50%`, α 0.15) | `oklch(0.35 0.12 300)` | `#45266e` |
| App background radial 2 (`80% 20%`, α 0.08) | `oklch(0.35 0.15 340)` | `#680252` |
| Gold-graph blue area fill | `oklch(0.62 0.22 240)` | `#008efa` |
| Baron timer value | `oklch(0.72 0.16 310)` | `#c385ef` |
| Elder timer value | `oklch(0.72 0.18 55)` | `#f77f00` |
| Rune tree — Precision | — | `#c8a84b` |
| Rune tree — Domination | — | `#be2633` |
| Rune tree — Sorcery | — | `#9ba3d6` |

### Alternate accent themes

The mockup ships a runtime theme switcher (Settings → Appearance, and the tweaks panel) that
rewrites four custom properties. Rose is the default and the one Bladecaller implements.

| Theme | `--accent` | `--accent-dim` | `--accent2` |
|-------|-----------|----------------|-------------|
| Crimson Rose (default) | `#da3aa4` | `#93126b` | `#8267e2` |
| Cosmic Dawn | `#009de0` | `#006699` | `#00a084` |
| Ember Gold | `#f87300` | `#b93600` | `#dd503f` |

---

## Typography

Two families, both bundled as woff2 in the mockup and re-extracted to TTF in
[`resources/fonts/`](resources/fonts):

- **Inter** — weights 300/400/500/600. Body font. `body { font-family: 'Inter'; font-size: 13px; }`.
- **Barlow Semi Condensed** — weights 400/500/600/700. Display font: every heading, stat value,
  numeric readout, and uppercase label.

Barlow is used *only* where the mockup names it explicitly; everything else is Inter.

| Role | Family | Size | Weight | Tracking | Case |
|------|--------|------|--------|----------|------|
| `.sidebar-logo-text` | Barlow | 15px | 700 | `0.04em` | uppercase |
| `.sidebar-logo-sub` | Inter | 9px | — | `0.1em` | uppercase, `--text3` |
| `.nav-section` | Inter | 9px | 500 | `0.12em` | uppercase, `--text3` |
| `.nav-item` | Inter | 13px | 500 | — | — |
| `.page-title` | Barlow | 22px | 700 | `0.02em` | — |
| `.page-sub` | Inter | 12px | — | — | `--text3` |
| `.card-title` | Barlow | 11px | 600 | `0.1em` | uppercase, `--text3` |
| `.stat-val` | Barlow | 28px | 700 | — | `line-height: 1` |
| `.stat-label` | Inter | 11px | — | — | `--text3` |
| `.badge` | Inter | 10px | 600 | `0.05em` | uppercase |
| `.tree-name` | Barlow | 14px | 700 | `0.04em` | — |
| `.timer-name` / `.timer-time` | Barlow | 14px / 18px | 600 / 700 | — | time is `tabular-nums` |
| `.match-champ` | Barlow | 15px | 700 | — | — |
| `.match-kda` | Barlow | 16px | 600 | — | centered |
| `.settings-title` | Barlow | 14px | 700 | `0.06em` | uppercase, `--text2` |
| `.settings-label` | Inter | 13px | 500 | — | — |
| `.settings-desc` | Inter | 11px | — | — | `--text3` |
| `.event-time` | Inter | 10px | — | — | `--text3`, `tabular-nums`, `min-width: 32px` |
| `.event-text` | Inter | 12px | — | — | `--text2`; `<b>` → `--text`, 600 |
| Scoreboard header row | Inter | 10px | — | `0.06em` | uppercase, `--text3` |

Numeric columns (event time, timer time, scoreboard cells) all set
`font-variant-numeric: tabular-nums`.

---

## Layout

```
.app  (display:flex; height:100vh)
├── .sidebar          200px fixed, vertical gradient, 1px right border, z-index 10
│   ├── .sidebar-logo     28px gradient mark + wordmark + version, bottom border
│   ├── .sidebar-nav      flex:1 — "NAVIGATION" section label + nav items
│   └── (bottom stack)    .phase-badge + connection-status pill
└── .main  (flex:1)
    └── .page             padding 24px, overflow-y auto, fadeIn 0.2s
        ├── .page-header  title/subtitle left, contextual widget right, margin-bottom 20px
        └── .page-body    flex column, gap 12px, min-height 0
```

The page body uses a small set of flex utilities so cards fill height without scrolling the page:

| Class | Rule |
|-------|------|
| `.page-body` | `flex:1; display:flex; flex-direction:column; min-height:0; gap:12px` |
| `.fill-row` | `flex:1; min-height:0; display:flex; gap:12px` |
| `.fill-col` | `flex:1; display:flex; flex-direction:column; min-height:0; gap:12px` |
| `.grow` | `flex:1; min-height:0` |
| `.grow-scroll` | `flex:1; min-height:0; overflow-y:auto` |
| `.grid2` / `.grid3` | `display:grid; grid-template-columns: 1fr 1fr [1fr]; gap:12px` |

Standard gap is **12px** between cards, **24px** page padding, **16px** card padding.

The app background layers two radial gradients over `--bg0`:

```css
background-image:
  radial-gradient(ellipse 60% 50% at 30% 50%, oklch(0.35 0.12 300 / 0.15) 0%, transparent 70%),
  radial-gradient(ellipse 40% 60% at 80% 20%, oklch(0.35 0.15 340 / 0.08) 0%, transparent 60%);
```

Scrollbars are 4px wide, transparent track, `--bg4` thumb at 2px radius.

---

## Components

### Sidebar

- **Logo mark** — 28×28, `linear-gradient(135deg, var(--accent), var(--accent2))`, radius 6px,
  `box-shadow: 0 0 12px var(--accent-glow)`, centered 14px white feather icon.
- **Nav item** — `padding: 9px 16px`, `gap: 10px`, 16px icon, `border-left: 2px solid transparent`,
  color `--text2`, `transition: all 0.15s`.
  - Hover: color `--text`, background `rgba(255,255,255,0.03)`.
  - Active: color `--text`, `border-left-color: var(--accent)`, background
    `linear-gradient(90deg, oklch(0.62 0.22 345 / 0.12) 0%, transparent 100%)`; the icon turns
    `--accent` and gains `drop-shadow(0 0 4px var(--accent-glow))`.
- **Phase badge** — `margin: 0 10px 10px`, `padding: 8px 10px`, `--bg2` on `--border`, radius 8px,
  11px text. Leading 7px dot: `idle` → `--text3` flat; `champselect` → `--gold` + 6px glow +
  `pulse-gold 2s infinite`; `ingame` → `--green` + 6px glow + `pulse-green 2s infinite`.
- **Connection pill** — same surface treatment, 6px dot, green + `pulse-green 3s` when connected,
  `--text3` when not; label "Connected" / "Connecting…".

### Card

```css
.card {
  background: linear-gradient(135deg, var(--bg2) 0%, var(--bg1) 100%);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  position: relative;
  overflow: hidden;
}
.card::before {  /* subtle top-left sheen */
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(135deg, rgba(255,255,255,0.02) 0%, transparent 50%);
}
```

`.card-title` is the uppercase Barlow micro-label with `margin-bottom: 12px`.

### Badge

`display: inline-flex; padding: 2px 7px; border-radius: 3px; font-size: 10px; font-weight: 600;
letter-spacing: 0.05em; text-transform: uppercase`. Variants tint background at 15% (12% for
purple) and set the matching text color: `win` green, `loss` red, `gold` gold, `purple` accent2.

### Stat

`.stat-val` (Barlow 28/700, `line-height: 1`) over `.stat-label` (11px `--text3`, `margin-top: 4px`).
Per-instance overrides drop the value to 22px in dense contexts and recolor it green/red/gold.

### Event feed

`.event-feed` is a 2px-gap column. Each `.event-item` is `padding: 7px 10px`, radius 4px,
`border-left: 2px solid transparent`, animates in with `slideIn 0.3s`, hover wash
`rgba(255,255,255,0.03)`. Type sets the left border and the 22px round icon's tint:

| Type | Left border | Icon background |
|------|-------------|-----------------|
| `kill` | `--red` | `oklch(0.62 0.22 25 / 0.15)` |
| `objective` | `--gold` | `oklch(0.80 0.14 68 / 0.15)` |
| `turret` | `--blue` | `oklch(0.65 0.18 240 / 0.15)` |

Row layout: icon · `.event-time` (10px, min-width 32px) · `.event-text` (flex:1, `--text2`, with
bolded subject names in `--text`).

Event copy in the mockup, mapped from the backend event type:

| Event | Icon | Text |
|-------|------|------|
| `PLAYER_KILLED` | 💀 | **{killer}** killed **{victim}** *(multikill)* |
| `DRAGON_KILLED` | 🐉 | **{Blue/Red} team** slew the {type} Drake |
| `BARON_KILLED` | 👁 | **{Blue/Red} team** slew Baron Nashor |
| `TURRET_DESTROYED` | 🗼 | **{Blue/Red} team** destroyed {lane} {type} turret |

`ORDER` renders as "Blue", anything else as "Red".

### Scoreboard

Row grid: `24px 1fr 52px 52px 52px 60px` (icon, name, K, D, A, gold), `gap: 4px`,
`padding: 6px 8px`, radius 4px. Header row is the 10px uppercase `--text3` variant. `.you` rows
get `oklch(0.62 0.22 345 / 0.06)`. Numeric columns are right-aligned `tabular-nums`; K is green,
D is red, A is default, gold is `--gold` at 11px.

Team headers are 10px 600 pills — `padding: 4px 8px`, radius 4px, hue at 6% background:
BLUE TEAM `oklch(0.65 0.18 240)`, RED TEAM `oklch(0.62 0.22 25)`.

### Champion icon

Square, radius 4–8px scaling with size, `--bg3` background on a 1px border, `object-fit: cover`
image. Falls back to the first two letters of the name at `max(9, size * 0.38)`px, weight 700,
`--text3`. Sizes in use: 24 (scoreboard), 26 (team comp), 34 (top champs), 38–40 (match rows).

### Objective timer

`.timer-card` — `display:flex; justify-content:space-between; padding: 10px 14px`, `--bg2` on
`--border`, radius 8px, `margin-bottom: 6px`. Left: 18px emoji + `.timer-name` over a 10px
`--text3` status line (`Not spawned yet` / `Alive now` / `Respawning in`). Right: `.timer-time`
Barlow 18/700 tabular. `< 30s` → `--red` + `pulse-red 1s infinite`; `<= 0` → `--green` and the
literal `UP`; `null` → `--text3` and an em dash.

### Match row

Grid `4px 56px 1fr 80px 80px 80px`, `gap: 12px`, `padding: 12px 14px`, `--bg2` on `--border`,
radius 8px, `margin-bottom: 6px`, `cursor: pointer`,
`transition: border-color 0.15s`; hover → `--border-bright`. The 4px leading `.match-accent` bar
is green on win, red on loss. Clicking expands a detail panel underneath (top corners squared,
`border-top: none`): a `repeat(4, 1fr)` grid of Damage Dealt / Damage Taken / Kill Participation /
Gold Earned tiles on `--bg2` at radius 6, then a "BUILD ORDER" strip of 44px item squares.

### Rune slot

36×36 circle, `1.5px solid var(--border)` on `--bg2`, `transition: all 0.15s`; hover
`border-color: var(--accent); transform: scale(1.08)`. Selected: accent border +
`box-shadow: 0 0 8px var(--accent-glow)` + accent-wash gradient. Keystones are 52×52 with a gold
border, and when selected take a doubled gold glow
(`0 0 16px var(--gold-glow), 0 0 32px var(--gold-glow)`). Rune name labels sit under each slot at
9px, `--text3` unselected / tree color when selected.

`.tree-header` is an 8px dot in the tree color (with a `0 0 6px` glow) plus `.tree-name`, over an
8px-padded bottom border.

### Form controls

- **`.input-field`** — `--bg2` on `--border`, `padding: 7px 10px`, radius 4px, 12px text,
  `width: 280px`, no outline, `transition: border-color 0.15s`; focus → `--accent`; placeholder
  `--text3`.
- **`.toggle`** — 36×20 track, radius 10px, `--bg4` on `--border`; 14px thumb at `top/left: 2px`,
  `--text3`. On: track `--accent-dim` with `--accent` border, thumb slides to `left: 18px` and
  turns white. `transition: 0.2s`.
- **`.select-field`** — `--bg3` on `--border`, `padding: 5px 8px`, radius 4px, 12px.
- **Primary button** — `padding: 9px 20px`, radius 6px, no border, white 13/600 Inter,
  `linear-gradient(135deg, var(--accent-dim), var(--accent2-dim))`,
  `box-shadow: 0 0 12px var(--accent-glow)`.
- **Secondary button** — `--bg2` on `--border`, `--text2`, otherwise identical box.
- **`.swatch`** — 28–32px circle, `linear-gradient(135deg, a, b)` of the theme pair, 2px
  transparent border; active → white border + `scale(1.15)` + `0 0 10px` tinted glow.

### Settings rows

`.settings-section` stacks with `margin-bottom: 28px` under a `.settings-title` that has a 8px
bottom padding and a `--border` underline. Each `.settings-row` is
`display:flex; justify-content:space-between; padding: 10px 0` divided by
`1px solid rgba(120,90,180,0.08)`, with label + description on the left and the control on the right.

---

## Pages

Five, in nav order. Each is `.page` > `.page-header` + `.page-body`.

| Page | Header subtitle | Composition |
|------|-----------------|-------------|
| **Dashboard** | "Waiting for a game to start…"; right side shows a clock icon + "Last updated just now" | Full-width rank card, then a `.fill-row`: fixed 280px left column (Last 10 Games + Top Champions) and a growing right card (Recent Matches, `.grow-scroll`) |
| **Champ Select** | "Configure runes and review matchups"; right side shows a gold "playing as {champ}" chip | Three equal columns: Primary Path, Secondary Path (+ Stat Shards), and a right `.fill-col` of Enemy Matchup / Counter Tips / Team Composition |
| **Live Game** | Green dot + "In game · {mm:ss}" | `.fill-row` of Scoreboard card and a `.fill-col` (Gold Differential + Objective Timers), then a full-width Game Events card |
| **Match History** | "Ranked Solo/Duo · Season 2025"; right side shows All / Wins / Losses filter chips | Summary card (total games, W/L split bar, avg KDA/CS/Vision) then a `.grow-scroll` list of `.match-row` |
| **Settings** | "Configure Featherstorm"; page capped at `max-width: 680px` | Account / Appearance / Behavior sections, then Save Changes + Reset Defaults |

**Rank card** (Dashboard) overrides the card gradient to
`linear-gradient(135deg, #1a1236 0%, #0e0b1a 60%)` with `border-color: rgba(180,100,200,0.25)`.
Inside: a 64px rounded-12px shield tile on an accent gradient with `0 0 20px` glow, the queue
label (11px uppercase `--text3`), tier in Barlow 26/700, an LP line, and a 32px-gapped row of
stat pairs.

**Last 10 Games** renders ten flex-1 32px tiles, W tinted green (20% fill / 30% border), L red.

**Gold Differential** is an SVG area chart: blue and red line at 2px, each over a vertical
gradient fading its own hue from 0.3/0.2 alpha to transparent, with a 4px endpoint dot. Legend is
a 20×2 color rule plus label; a 0:00–20:00 tick row sits underneath at 9px.

The mockup also carries a floating **tweaks panel** (`position: fixed; bottom: 60px; right: 16px`,
220px wide, `--bg2` on `--border-bright`, `box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 20px
oklch(0.62 0.22 345 / 0.1)`) and a bottom **demo bar** of phase-switch buttons. Both are mockup
scaffolding for the live preview, not product surface.

---

## Motion

| Name | Definition | Applied to |
|------|-----------|-----------|
| `fadeIn` | `opacity 0→1`, `translateY(4px)→0`, 0.2s ease | Page enter, expanded match detail (0.15s), tweaks panel |
| `slideIn` | `opacity 0→1`, `translateX(-8px)→0`, 0.3s ease | Event feed items |
| `pulse-gold` | `opacity 1→0.4→1`, 2s infinite | Champ-select phase dot |
| `pulse-green` | `opacity 1→0.5→1`, 2s infinite | In-game phase dot; 3s on the connection dot |
| `pulse-red` | `opacity 1→0.5→1`, 1s infinite | Objective timer under 30s |

Transitions: `0.15s` for interactive color/border changes (nav, buttons, rune slots, inputs,
match rows), `0.2s` for the toggle, `0.1s` for the event-item hover, `0.4s` on the win-rate bar's
width.

---

## Iconography

24×24 stroke icons, `stroke-width: 1.6`, `fill: none`, round caps and joins, `currentColor`,
rendered at 13–28px. The mockup's set: `home`, `sword`, `zap`, `bar`, `settings`, `shield`,
`feather`, `skull`, `dragon`, `tower`, `clock`, `check`, `eye`, `key`, `trend` — Feather-style
geometry throughout. Nav uses `home` / `sword` / `zap` / `bar` / `settings` in that order;
`feather` is the logo mark.

Objectives and event types use emoji rather than icons: 💀 kill, 🐉 dragon, 👁 baron, 🗼 turret,
🔥 elder, ⚡ fallback.

---

## Porting to Qt

Things in this document that QSS cannot express directly, and what the mockup's intent maps to.
See the Quirks section of [`CLAUDE.md`](CLAUDE.md) for the full list of QSS limitations.

| Mockup device | Qt approach |
|---------------|-------------|
| `oklch()` | Pre-convert to hex — the conversions in this doc are exact |
| Float alpha (`rgba(…, 0.18)`) | Percent form — `rgba(120, 90, 180, 18%)`; Qt truncates float alpha to 0 |
| `box-shadow` glows | No equivalent. Substitute a brighter `border-color`, or `QGraphicsDropShadowEffect` on the widget |
| `transition` / `@keyframes` | No equivalent in QSS. Use `QPropertyAnimation` if the motion matters, otherwise drop it |
| `transform: scale()` | No equivalent. Reserve the space and swap geometry, or skip |
| `gap` | Layout `setSpacing()` |
| `::before` sheen overlay | Fold into the widget's own `qlineargradient` background |
| `radial-gradient` | `qradialgradient` — but the app-background pair is subtle enough to omit |
| `flex: 1` / `min-height: 0` | `QSizePolicy` stretch factors; `Card` defaults to `Maximum` vertically (see `CLAUDE.md`) |
| `letter-spacing` | Not in QSS — set on the `QFont` (`QFont.setLetterSpacing`) |
| `font-variant-numeric: tabular-nums` | `QFont.setStyleStrategy` won't do it; use a `QFontDatabase` feature tag or accept proportional digits |
