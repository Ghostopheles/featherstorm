# Bladecaller UI

PySide6 desktop app for Featherstorm. Entry point is the `bladecaller` gui-script, which calls `launch_ui()` in [`__init__.py`](__init__.py). Needs the optional `ui` extra:

```bash
uv sync --extra ui
uv run bladecaller
```

Visual language derives from the design mockup at `ref/Featherstorm.html` (repo root) — dark violet/near-black surfaces, magenta accent, Barlow Semi Condensed for display text, Inter for body text.

> **Design reference is [`DESIGN.md`](DESIGN.md)** — the mockup transcribed: every token (with `oklch` → sRGB conversions), the type scale, layout utilities, per-component specs, page compositions, and a Qt-porting table. Read that, not the mockup.
>
> **Never `Read` `ref/Featherstorm.html` whole — it is ~1.8 MB**, a self-extracting bundle (base64 asset manifest + JSON-escaped React template), so grepping it is also unhelpful. If something genuinely isn't in `DESIGN.md`, extract the real markup first: the template is the single JSON string line starting `"<!DOCTYPE html>` — `json.loads()` it to get ~88 KB of readable CSS/JSX. Everything already ported lives in [`resources/theme.py`](resources/theme.py); check there first.

## Layout

```
bladecaller/
├── DESIGN.md        # design reference — mockup transcribed (tokens, type, components, pages)
├── __init__.py      # launch_ui() — imports ui.app lazily, errors if `ui` extra missing
├── core/
│   ├── settings_schema.py  # SettingField/SCHEMA/SECTION_LABELS — widget hints per config key
│   └── status.py           # ClientStatus + STATUS_LABELS/STATUS_TOOLTIPS for the sidebar indicator
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
    ├── main_window.py  # MainWindow + SidebarHeader (logo/title) + SidebarStatus (client state)
    ├── components.py   # Page, PageHeader, Card, CardTitle, Separator, StatValue, StatLabel
    ├── pages/       # DashboardPage, SettingsPage
    └── settings/    # editors.py — make_editor() maps config values to widgets
```

## Style system

- **[`resources/theme.py`](resources/theme.py)** — single source of truth for design tokens. Every uppercase module-level name is collected into `TOKENS`. The mockup's `oklch()` values are pre-converted to sRGB hex because Qt stylesheets don't understand `oklch()`; alpha colors use `rgba(r, g, b, N%)` because Qt truncates float alpha to 0.
- **[`resources/app.qss`](resources/app.qss)** — stylesheet template. `$TOKEN` / `${TOKEN}` placeholders substituted from `TOKENS` by `load_stylesheet()` via `string.Template`. **Never write a literal `$` in the QSS** — `Template.substitute()` raises on unknown names.
- **`resources/fonts/`** — bundled Inter (300–600) and Barlow Semi Condensed (400–700) TTFs, registered by `load_fonts()` *before* the stylesheet is applied. Extracted from the mockup's woff2 bundle; name records were normalized (nameID 16/17 = typographic family/subfamily) so Qt matches faces by `font-weight` rather than treating "Inter SemiBold" as a separate family.
- **`resources/icons/`** — Feather-style 24×24 SVGs, stroke color baked into the file. `load_icon(name)` → `QIcon`; `icon_path(name)` → forward-slashed str for QSS `url()`.

Startup order in [`ui/app.py`](ui/app.py) matters: `setStyle("Fusion")` → `load_fonts()` → `setFont()` → `setStyleSheet()`. The Fusion style is not cosmetic — the native Windows style ignores large parts of the QSS (sub-control rules like `QSpinBox::up-button`, `QComboBox::down-arrow`, `QCheckBox::indicator`). Any offscreen/test harness must set it too or the render won't match.

Adding an icon that QSS references by `url()` takes two steps: drop the SVG in `resources/icons/`, then register it in the `tokens.update({...})` block of `load_stylesheet()` ([`resources/__init__.py`](resources/__init__.py)). Icons used only from Python (`load_icon(...)`) need no registration.

## Applying the style

Styling hangs off object names and Qt properties, not per-widget stylesheets:

| Selector | Use |
|----------|-----|
| `#sidebar`, `#sidebarHeader`, `#logoMark`, `#appTitle` | Sidebar chrome |
| `#sidebarStatus`, `#statusDot`, `#statusText` | Client/match status strip |
| `#sidebarFooter`, `#appVersion` | Sidebar footer (gear + version) |
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

## Verifying a change

There are no UI tests (`pytest-qt` is a dev dep but `tests/` doesn't exist). The verification loop is a headless render — run it and `Read` the PNG:

```bash
QT_QPA_PLATFORM=offscreen uv run python -c "
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from league.bladecaller.resources import load_fonts, load_stylesheet
from league.bladecaller.resources.theme import FONT_BODY, FONT_SIZE
from league.bladecaller.ui.main_window import MainWindow
app = QApplication([])
app.setStyle('Fusion'); load_fonts(); app.setFont(QFont(FONT_BODY, FONT_SIZE)); app.setStyleSheet(load_stylesheet())
w = MainWindow(); w.show(); app.processEvents()
w.grab().save('shot.png')
"
```

Notes:
- `app.processEvents()` before `grab()` — without it the layout hasn't settled and the image is blank/unstyled.
- To shoot a specific page, `w.stack.setCurrentWidget(w.settings_page)` (or `setCurrentIndex`) before the grab.
- `load_stylesheet()` alone catches the most common breakage, no Qt needed — a token missing from `theme.py` raises `KeyError`, a stray literal `$` raises `ValueError`. A malformed *rule*, by contrast, fails silently: Qt drops the declaration and prints nothing.
- Lint is `uv run ruff check` / `uv run ruff format`; the rule set is deliberately tiny (`E9,F63,F7,F82`), line length 160, and `__init__.py` is excluded.

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

**Nav row index and stack index are the same number** — `_on_nav_row_changed()` does `stack.setCurrentIndex(row)`. So every `add_page()` call must come *before* any other `stack.addWidget()`; `set_settings_page()` deliberately runs last in `_build_pages()` so the settings widget lands past the nav rows and is only reachable via `stack.setCurrentWidget()`. Insert a non-nav widget earlier and every nav row points at the wrong page.

`_build_pages()` imports pages and `league.config` inside the function body, not at module scope — keeps `main_window` importable without dragging in the page tree. Follow that when registering new pages.

## Status indicator

`SidebarStatus` ([`ui/main_window.py`](ui/main_window.py)) sits between the nav list and the footer, reachable as `window.status`. It is **not wired to a backend** — nothing polls the LCU or Live Client API yet. Drive it manually:

```python
window.status.set_status(ClientStatus.IN_MATCH)
```

`ClientStatus` ([`core/status.py`](core/status.py)) has `DISCONNECTED` / `CONNECTED` / `IN_MATCH`; its values double as the QSS `state` property on `#statusDot` (grey / `GREEN` / `ACCENT`). Labels and tooltips come from `STATUS_LABELS` / `STATUS_TOOLTIPS`. `set_status()` repolishes the dot, since a dynamic property set after show doesn't restyle on its own.

Wiring it up means a controller in `controllers/` on a `QTimer` — `LCUClient` for client presence/gameflow phase, `LeagueClient` for in-game. Keep the import inside the controller; `main_window` must stay free of `league.lcu`.

## Settings page

[`ui/pages/settings.py`](ui/pages/settings.py) renders the whole TOML config (`league.config.get_full_config()`) generically — one `QGroupBox` per section, one row per key. Widget choice comes from the value's Python type, overridden per key by `SCHEMA` in [`core/settings_schema.py`](core/settings_schema.py) (`kind`, bounds, suffix, `as_str` for numeric-looking strings). Adding a config key needs no UI change; add a `SettingField` only when the inferred widget is wrong.

`settings_applied` signal emits the edited dict — **not yet wired to a writer**. Nothing connects it, so Apply is a no-op today. The writer would be `league.config.set(key, value, category)` inside a `with league.config.batch():` block (batch defers the TOML write until the outermost context exits — see [`league/config.py`](../config.py)).

`get_full_config()` returns the module's live `_cache` dict, not a copy — `SettingsPage` deepcopies it into `self._defaults`. "Restore defaults" therefore restores *the values as of page construction*, not the schema defaults from `config.init()`.

Widget dispatch order in [`ui/settings/editors.py`](ui/settings/editors.py) is load-bearing: `kind` overrides first, then `bool` **before** `int` (`bool` subclasses `int`), then `as_str`, then `int`/`float`, `QLineEdit` last. A new widget type means adding to the `Kind` `Literal` in `core/settings_schema.py` plus a branch near the top of `make_editor()`. Every branch returns an `Editor(widget, get, set)` — `get`/`set` must round-trip the config's original Python type (that's what `as_str` exists for).

## Quirks

- Qt stylesheets have no variables — that's why `app.qss` is templated. Adding a color means adding it to `theme.py`, nothing else. `TOKENS` is built by scanning `globals()` for uppercase names, so a new token needs no registration — but it also means non-color constants (`SIDEBAR_WIDTH`, `FONT_SIZE`) are tokens too, and are imported directly as Python where Qt needs a number.
- QSS is not CSS. No `box-shadow`, no `transition`/animation, no `transform`, no `gap`, no `calc()`, no `oklch()`, no `:has()`/`>`/sibling combinators, no `::before`/`::after`. Porting anything from the mockup means picking a Qt-expressible stand-in (usually `qlineargradient`, a border color, or a layout margin). Qt's shorthand parsing is also stricter — prefer explicit `border-color` / `padding` longhands when a rule silently does nothing.
- Dynamic Qt properties used as selectors (`accent`, `muted`) only restyle at polish time. Setting one *after* the widget is shown needs `w.style().unpolish(w); w.style().polish(w)`. Existing code sets them at construction, so it hasn't bitten yet.
- The settings gear lives at the *bottom* of the sidebar (`#navSettings`), separate from the nav list; selecting a nav row unchecks it and vice versa. The version label shares that footer row, right-aligned.
- Sidebar version string comes from `importlib.metadata.version("featherstorm")`, falling back to `"dev"` when the package isn't installed.
- **A `QWidget` *subclass* does not paint its QSS `background`/`border` unless it sets `Qt.WA_StyledBackground`.** Plain `QWidget()` instances get the attribute automatically when a rule matches, which is why `#sidebar`/`#sidebarFooter` work untouched while `SidebarHeader`/`SidebarStatus` set it explicitly. A border that silently doesn't render is almost always this.
- Sidebar divider lines use the `DIVIDER` token, not `BORDER` — `BORDER` (18% alpha) is invisible against the sidebar gradient.
- `Card` defaults to `QSizePolicy.Maximum` vertically. Without that a `Preferred` card swallows the space a trailing `addStretch()` was meant to take.
- Offscreen render for visual checks: `QT_QPA_PLATFORM=offscreen`, then `window.grab().save(path)` — see [Verifying a change](#verifying-a-change) for the full command.
- PySide6 is an *optional* dep (`ui` extra). Nothing under `bladecaller/` may be imported from `league.cli`, `league.companion`, or any other non-UI module — `launch_ui()` in [`__init__.py`](__init__.py) is the only entry point and it catches the `ImportError`. Import in the other direction (UI → `league.config` etc.) is fine.
