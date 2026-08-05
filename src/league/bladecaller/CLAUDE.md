# Bladecaller UI

PySide6 desktop app for Featherstorm. Entry point is the `bladecaller` gui-script, which calls `launch_ui()` in [`__init__.py`](__init__.py). Needs the optional `ui` extra:

```bash
uv sync --extra ui
uv run bladecaller
```

Visual language derives from the design mockup at `ref/Featherstorm.html` (repo root) — dark violet/near-black surfaces, magenta accent, Barlow Semi Condensed for display text, Inter for body text.

## Layout

```
bladecaller/
├── __init__.py      # launch_ui() — imports ui.app lazily, errors if `ui` extra missing
├── core/
│   └── settings_schema.py  # SettingField/SCHEMA/SECTION_LABELS — widget hints per config key
├── controllers/     # (empty — reserved for page ↔ backend wiring)
├── qt/              # (empty)
├── resources/
│   ├── __init__.py  # load_stylesheet(), load_fonts(), load_icon(), icon_path(), app_version()
│   ├── theme.py     # design tokens (colors, fonts, radii) — single source of truth
│   ├── app.qss      # stylesheet template, $TOKEN placeholders substituted from theme.py
│   ├── fonts/       # bundled Inter + Barlow Semi Condensed TTFs
│   └── icons/       # feather (logo), gear, chevrons, check, nav icons (SVG)
└── ui/
    ├── app.py       # run() — QApplication setup, font/stylesheet install
    ├── main_window.py  # MainWindow + SidebarHeader (logo/title/version)
    ├── components.py   # Page, PageHeader, Card, CardTitle, Separator, StatValue, StatLabel
    ├── pages/       # DashboardPage, SettingsPage
    └── settings/    # editors.py — make_editor() maps config values to widgets
```

## Style system

- **[`resources/theme.py`](resources/theme.py)** — single source of truth for design tokens. Every uppercase module-level name is collected into `TOKENS`. The mockup's `oklch()` values are pre-converted to sRGB hex because Qt stylesheets don't understand `oklch()`; alpha colors use `rgba(r, g, b, N%)` because Qt truncates float alpha to 0.
- **[`resources/app.qss`](resources/app.qss)** — stylesheet template. `$TOKEN` / `${TOKEN}` placeholders substituted from `TOKENS` by `load_stylesheet()` via `string.Template`. **Never write a literal `$` in the QSS** — `Template.substitute()` raises on unknown names.
- **`resources/fonts/`** — bundled Inter (300–600) and Barlow Semi Condensed (400–700) TTFs, registered by `load_fonts()` *before* the stylesheet is applied. Extracted from the mockup's woff2 bundle; name records were normalized (nameID 16/17 = typographic family/subfamily) so Qt matches faces by `font-weight` rather than treating "Inter SemiBold" as a separate family.
- **`resources/icons/`** — Feather-style 24×24 SVGs, stroke color baked into the file. `load_icon(name)` → `QIcon`; `icon_path(name)` → forward-slashed str for QSS `url()`.

Startup order in [`ui/app.py`](ui/app.py) matters: `load_fonts()` → `setFont()` → `setStyleSheet()`.

## Applying the style

Styling hangs off object names and Qt properties, not per-widget stylesheets:

| Selector | Use |
|----------|-----|
| `#sidebar`, `#sidebarHeader`, `#logoMark`, `#appTitle`, `#appVersion` | Sidebar chrome |
| `#nav`, `#navSettings` | Nav list + gear button |
| `#pageTitle`, `#pageSubtitle` | Page header text |
| `#card`, `#cardTitle`, `#sectionTitle` | Card surfaces |
| `#statValue`, `#statLabel` | Stat readouts |
| `QPushButton[accent="true"]` | Primary action button |
| `QLabel[muted="true"]` | De-emphasized text |

[`ui/components.py`](ui/components.py) wraps these:

- **`Page(title, subtitle)`** — standard page shell; subclass and add to `self.content`.
- **`Card(title=None, fill=False)`** — bordered surface; add to `card.body`. `fill=True` claims leftover vertical space, otherwise the card hugs its contents.
- **`PageHeader`**, **`CardTitle`**, **`Separator`**, **`StatValue`**, **`StatLabel`**.

## Adding a page

```python
class MyPage(Page):
    def __init__(self, parent=None):
        super().__init__("My Page", "Subtitle", parent)
        card = Card("Section")
        card.body.addWidget(...)
        self.content.addWidget(card)
```

Register in `MainWindow._build_pages()`:

```python
self.add_page("My Page", MyPage(), load_icon("my-icon.svg"))
```

## Settings page

[`ui/pages/settings.py`](ui/pages/settings.py) renders the whole TOML config (`league.config.get_full_config()`) generically — one `QGroupBox` per section, one row per key. Widget choice comes from the value's Python type, overridden per key by `SCHEMA` in [`core/settings_schema.py`](core/settings_schema.py) (`kind`, bounds, suffix, `as_str` for numeric-looking strings). Adding a config key needs no UI change; add a `SettingField` only when the inferred widget is wrong.

`settings_applied` signal emits the edited dict — not yet wired to a writer.

## Quirks

- Qt stylesheets have no variables — that's why `app.qss` is templated. Adding a color means adding it to `theme.py`, nothing else.
- The settings gear lives at the *bottom* of the sidebar (`#navSettings`), separate from the nav list; selecting a nav row unchecks it and vice versa.
- Sidebar version string comes from `importlib.metadata.version("featherstorm")`, falling back to `"dev"` when the package isn't installed.
- `Card` defaults to `QSizePolicy.Maximum` vertically. Without that a `Preferred` card swallows the space a trailing `addStretch()` was meant to take.
- Offscreen render for visual checks: `QT_QPA_PLATFORM=offscreen`, then `window.grab().save(path)`.
- This file is excluded from built wheels/sdists via `wheel-exclude`/`source-exclude` in the root `pyproject.toml`.
