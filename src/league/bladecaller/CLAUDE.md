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
│   ├── status.py           # ClientStatus + STATUS_LABELS/STATUS_TOOLTIPS for the sidebar indicator
│   └── match.py            # MatchSummary / MatchDetail / ScoreRow view models (no Qt)
├── controllers/     # page ↔ backend wiring
│   ├── client_status.py    # ClientStatusController — polls LCU gameflow phase, emits ClientStatus
│   └── match_history.py    # MatchHistoryController — LCU match list + Riot per-match expansion
├── qt/              # (empty)
├── resources/
│   ├── __init__.py  # load_stylesheet(), load_fonts(), load_icon(), icon_path(), app_version()
│   ├── theme.py     # design tokens (colors, fonts, radii) — single source of truth
│   ├── app.qss      # stylesheet template, $TOKEN placeholders substituted from theme.py
│   ├── fonts/       # bundled Inter + Barlow Semi Condensed TTFs
│   └── icons/       # feather (logo), gear, chevrons, check, nav icons (SVG)
└── ui/
    ├── app.py       # run() — QApplication setup, font/stylesheet install, controller wiring
    ├── main_window.py  # MainWindow + SidebarHeader (logo/title) + SidebarStatus (client state)
    ├── components.py   # Page, PageHeader, Card, CardTitle, Separator, StatValue, StatLabel,
    │                   #   Badge, StatTile, ScrollColumn, repolish()
    ├── icons.py     # IconProvider — async disk-cached champion/item/spell pixmaps; run_async()
    ├── widgets/     # ChampionIcon, MatchRow, MatchDetailPanel, MatchEntry, Scoreboard
    ├── pages/       # DashboardPage, MatchHistoryPage, SettingsPage
    └── settings/    # editors.py — make_editor() maps config values to widgets
```

## Style system

- **[`resources/theme.py`](resources/theme.py)** — single source of truth for design tokens. Every uppercase module-level name is collected into `TOKENS`. The mockup's `oklch()` values are pre-converted to sRGB hex because Qt stylesheets don't understand `oklch()`; alpha colors use `rgba(r, g, b, N%)` because Qt truncates float alpha to 0.
- **[`resources/app.qss`](resources/app.qss)** — stylesheet template. `$TOKEN` / `${TOKEN}` placeholders substituted from `TOKENS` by `load_stylesheet()` via `string.Template`. **Never write a literal `$` in the QSS** — `Template.substitute()` raises on unknown names.
- **`resources/fonts/`** — bundled Inter (300–600) and Barlow Semi Condensed (400–700) TTFs, registered by `load_fonts()` *before* the stylesheet is applied. Extracted from the mockup's woff2 bundle; name records were normalized (nameID 16/17 = typographic family/subfamily) so Qt matches faces by `font-weight` rather than treating "Inter SemiBold" as a separate family.
- **`resources/icons/`** — Feather-style 24×24 SVGs, stroke color baked into the file. `load_icon(name)` → `QIcon`; `icon_path(name)` → forward-slashed str for QSS `url()`.

Startup order in [`ui/app.py`](ui/app.py) matters: `config.init()` → `setStyle("Fusion")` → `load_fonts()` → `setFont()` → `setStyleSheet()`. The Fusion style is not cosmetic — the native Windows style ignores large parts of the QSS (sub-control rules like `QSpinBox::up-button`, `QComboBox::down-arrow`, `QCheckBox::indicator`). Any offscreen/test harness must set it too or the render won't match.

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
| `#statValue`, `#statLabel`, `#statTile` | Stat readouts |
| `QPushButton[accent="true"]` | Primary action button |
| `QLabel[muted="true"]` | De-emphasized text |
| `#badge[variant="win\|loss\|gold\|purple"]` | Result / status pill |
| `#matchRow` (+ `[expanded="true"]`), `#matchAccent[result="win\|loss"]` | Match list row |
| `#matchChamp`, `#matchKda`, `#matchMeta`, `#matchDetail` | Match row text + expanded body |
| `#championIcon`, `#itemSquare[empty="true"]` | Art placeholders |
| `#scoreRow[you="true"]`, `#scoreHeader`, `#scoreName`, `#scoreKills`, `#scoreDeaths`, `#scoreAssists`, `#scoreGold` | Scoreboard grid |
| `#teamPill[team="blue\|red"]` | Scoreboard team headers |
| `#filterChip[active="true"]` | Match history filter chips |
| `#splitBar`, `#splitFill` | Win/loss split bar |

[`ui/components.py`](ui/components.py) wraps these:

- **`Page(title, subtitle)`** — standard page shell; subclass and add to `self.content`.
- **`Card(title=None, fill=False)`** — bordered surface; add to `card.body`. `fill=True` claims leftover vertical space, otherwise the card hugs its contents.
- **`ScrollColumn()`** — the design's `.grow-scroll`; `add(widget)` inserts above a trailing stretch, `clear()` empties it. Scrollbar styling is already in `app.qss`.
- **`Badge(text, variant)`**, **`StatTile(value, label)`**, **`PageHeader`**, **`CardTitle`**, **`Separator`**, **`StatValue`**, **`StatLabel`**.
- **`repolish(widget)`** — re-applies the stylesheet after a dynamic property used as a selector changes. Use it any time a `[prop="…"]` selector is set after construction.

## Event loop

The UI runs Qt and asyncio on **one** loop via [`qasync`](https://pypi.org/project/qasync/) (part of the `ui` extra), so `run()` ends in `loop.run_forever()` instead of `app.exec()`:

```python
loop = qasync.QEventLoop(app)
asyncio.set_event_loop(loop)
app.aboutToQuit.connect(loop.stop)
...
with loop:
    controller.start()
    loop.run_forever()
    loop.run_until_complete(controller.close())
```

The backend is async top to bottom (`httpx.AsyncClient` everywhere), and this is what lets a controller `await` it directly. Because there is only one loop, controller callbacks and signal emissions already run on the GUI thread — no `QThread`, no cross-thread marshalling.

Consequences:

- `run()` returns `0` explicitly; `loop.run_forever()` has no exit code.
- **`app.quit()` does not stop `run_forever()`** — without `aboutToQuit → loop.stop`, closing the window leaves the process alive. qasync emits `aboutToQuit` more than once during teardown; `loop.stop()` is idempotent, so that's fine.
- Async cleanup runs *after* `run_forever()` returns, via `run_until_complete` while still inside `with loop:` (the `with` closes the loop on exit). Scheduling it from the `aboutToQuit` handler instead would never complete — the loop is stopping.
- **Never call `app.processEvents()` from inside a coroutine** — it re-enters the loop qasync is driving. Use `await asyncio.sleep(0)`. This only bites test harnesses; the offscreen render below runs outside the loop.
- Quitting from a non-GUI thread doesn't work under this setup (a test harness that calls `app.quit()` from a `threading.Thread` will hang). Use `QTimer.singleShot`.

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

Current nav order is `0` Dashboard, `1` Match History. `DashboardPage.show_match_history` is connected to `nav.setCurrentRow(1)` — adding a page above Match History means updating that row number too. Pages that `ui/app.py` needs to wire are kept as attributes (`self.dashboard`, `self.match_history`).

`_build_pages()` imports pages and `league.config` inside the function body, not at module scope — keeps `main_window` importable without dragging in the page tree. Follow that when registering new pages.

## Status indicator

`SidebarStatus` ([`ui/main_window.py`](ui/main_window.py)) sits between the nav list and the footer, reachable as `window.status`. It can still be driven manually:

```python
window.status.set_status(ClientStatus.IN_MATCH)
```

`ClientStatus` ([`core/status.py`](core/status.py)) has `DISCONNECTED` / `CONNECTED` / `IN_MATCH`; its values double as the QSS `state` property on `#statusDot` (grey / `GREEN` / `ACCENT`). Labels and tooltips come from `STATUS_LABELS` / `STATUS_TOOLTIPS`. `set_status()` repolishes the dot, since a dynamic property set after show doesn't restyle on its own.

It is wired to [`controllers/client_status.py`](controllers/client_status.py) in [`ui/app.py`](ui/app.py) — `status_changed` → `window.status.set_status`. `main_window` stays free of `league.lcu`; the controller owns that import.

## Controllers

**[`ClientStatusController`](controllers/client_status.py)** — `QObject` with a `status_changed = Signal(ClientStatus)`. `start()` spawns an asyncio task polling every `bladecaller.status_poll_interval` seconds (default 3.0); `poll_once()` is the single-shot version. Emits **only on transitions**, so connecting it directly to `set_status` won't thrash the repolish.

Status comes from the **LCU gameflow phase**, not the Live Client API:

| Phase | Status |
|-------|--------|
| LCU unreachable | `DISCONNECTED` |
| `InProgress` | `IN_MATCH` |
| anything else | `CONNECTED` |

Probing the Live Client API (`127.0.0.1:2999`) costs **~2s per poll** when no game is running — Windows doesn't promptly refuse the closed loopback port, so the connect attempt stalls. The gameflow phase answers in ~3ms and additionally reports `InProgress` during the load screen, before the Live Client API is serving. Don't reintroduce a `LeagueClient` probe here.

`LCUClient` is cached across polls, not rebuilt — its `__init__` also constructs a `DataDragon` with a second `httpx.AsyncClient`, so per-poll construction leaks two clients a tick. `_drop_lcu()` closes both. The cache is dropped whenever a phase request raises (client exited, stale lockfile) and rebuilt on the next poll; that's what makes the app tolerate League starting *after* it.

Note `LCUClient.__init__` raises if the lockfile is missing, so a controller can never hold one from startup — `_get_phase()` builds it lazily on first success.

**[`MatchHistoryController`](controllers/match_history.py)** — feeds both the Match History page and the dashboard's Recent Matches card. Signals: `matches_loaded(list)` (a page of `MatchSummary`, append semantics), `load_failed(str)`, `detail_loaded(game_id, MatchDetail)`, `detail_failed(game_id, str)`. `load_page()` pulls the next `bladecaller.match_history_page_size` entries; `load_detail(game_id)` expands one, memoised in a dict.

Two data sources, on purpose:

| Source | Gives | Cost |
|--------|-------|------|
| `LCUClient.get_match_history()` | the **current summoner only** — one participant per game | none; no API key, no rate limit |
| `RiotAPIClient.get_match()` | all ten participants + `challenges.killParticipation` | needs `RIOT_API_KEY`, rate-limited |

The LCU list endpoint genuinely returns a single participant per game (see `ref/lcu_match_history.json`), which is why the full scoreboard has to come from MATCH-V5. The match id is `f"{platformId}_{gameId}"`.

**The two sources do not share puuids.** The LCU reports an anonymized per-match UUID (`03c57e4e-11c8-550e-…`, 36 chars) where Riot reports the account's real 78-character puuid, so they never compare equal — which is why `RiotAPIClient.get_player_match()` is *not* used here. `MatchDetail.from_match(summary, match)` lines the two up on `participantId` instead (`participantIdentities[0].participantId`, carried on `MatchSummary.participant_id`), then narrows the match with the real puuid it found. `MatchSummary.puuid` is kept for reference but must not be passed to the Riot API.

The failure paths all fall back to `MatchDetail.from_summary(...)` — the four stat tiles and build order still render from the LCU stats, Kill Participation shows `—`, and a muted note replaces the scoreboard. The panel never blanks. Three notes, deliberately distinct:

| Case | Note | Client dropped? |
|------|------|-----------------|
| no `RIOT_API_KEY` | `NO_KEY_MESSAGE` | — |
| HTTP 403 / 404 | `UNAVAILABLE_MESSAGE` | no — not retryable, not a fault |
| anything else | `RIOT_FAILED_MESSAGE` | yes, rebuilt next expansion |

**MATCH-V5 does not serve every queue.** Brawl (queue `2400`, game mode `KIWI`) answers **403**, and custom / Practice Tool games (`3140`) answer **404**. Those are permanent, so they must not be reported as a failure or drop the cached client — the `UNAVAILABLE_STATUSES` branch exists for exactly that.

It builds its own `RiotAPIClient` from `load_dotenv()` + `os.getenv`. **Don't reach for `league.cli._shared._riot_client()`** — it raises `typer.Exit` and pulls typer into the UI.

`LCUClient` and `RiotAPIClient` are both constructed via `asyncio.to_thread` — see the httpx quirk below.

Adding another controller: same shape (`QObject` + signal, asyncio task, no Qt widgets), constructed and connected in `ui/app.py`.

## Match history

[`core/match.py`](core/match.py) holds the view models, and no widget touches `LCUMatch` / `PlayerMatch` directly:

- **`MatchSummary.from_lcu(LCUMatch)`** — one collapsed row. Derived text lives on properties (`kda_text`, `kda_ratio_text`, `cs_per_min`, `duration_text`, `relative_time`, `queue_name`, `meta_text`), so formatting is testable without Qt.
- **`MatchDetail`** — `from_match(summary, match)` (full scoreboard, resolves the player by `participantId`), `from_player_match()` (when a `PlayerMatch` is already in hand) or `from_summary()` (degraded).
- **`ScoreRow`** — one scoreboard line; holds `champion_id` *or* `champion_name`, since the LCU reports ids and Riot reports names.

[`ui/widgets/match_row.py`](ui/widgets/match_row.py) has `MatchEntry` = `MatchRow` + `MatchDetailPanel` stacked. `MatchRow(compact=…)` drops the trailing stat columns for the dashboard; `expandable=False` makes a click emit `activated` instead of toggling, which is how the dashboard jumps to the page.

[`ui/pages/match_history.py`](ui/pages/match_history.py) filters client-side over the loaded summaries (All/Wins/Losses chips + a queue combo) and recomputes the summary card from the *filtered* set. Only one row is expanded at a time.

Art comes from [`ui/icons.py`](ui/icons.py). `IconProvider` holds two `asyncio.Lock`s and they are both load-bearing — see the quirk below. The loading, disk cache and scaling are real, but the three URL builders at the bottom (`_champion_square_url`, `_item_icon_url`, `_spell_icon_url`) are **stubs returning `None`** — `DataDragon` has no item/spell icon fetchers yet. Every caller falls back to its placeholder (champion tiles show the first two letters, item squares stay empty), so filling those in later is a one-liner each and needs no widget change.

`LeagueEventBridge` ([`league/bridge.py`](../bridge.py)) is the eventual home for live match events, but it builds its `LCUClient` once in `__init__` and permanently disables out-of-game events if the client wasn't running then — unusable for a desktop app that starts before League. Fix that before wiring the bridge into the UI.

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
- **League `gameId`s exceed 32 bits.** A `Signal(int)` is a C++ `int` and raises `OverflowError` on emit. Pass game ids as `Signal(object)` — every match-history signal does.
- **`httpx.AsyncClient()`'s constructor blocks ~0.4s on Windows** building an SSL context from the system cert store, and under qasync that is 0.4s of frozen GUI. Anything that builds one from a coroutine (`LCUClient`, `RiotAPIClient`, `DataDragon`) goes through `asyncio.to_thread` — the ctors touch no event loop, so a worker thread is safe.
- **A lazy `if self._x is None: … await …` cache is not a cache under fan-out.** Every caller passes the `is None` check before the first one finishes awaiting, so all of them do the work. A page of 20 rows built 42 `DataDragon`s this way, each paying the SSL cost above — ~18s of stalls. `IconProvider._get_dragon()` and `champion_name()` each hold an `asyncio.Lock` (cheap check first, re-check inside) precisely to stop that. Any new shared async resource needs the same treatment.
- **`QScrollArea` sizes its widget to `minimumSizeHint()`, not `sizeHint()`**, and nested layouts report a smaller minimum than they need — rows get squeezed or overlap. Fix is `layout.setSizeConstraint(QLayout.SetMinimumSize)` on the scrolled column *and* on each row/panel inside it; `ScrollColumn`, `MatchRow`, `MatchDetailPanel` and `MatchEntry` all set it. Their vertical policy is `Minimum` (never shrink below the hint), not `Maximum`.
- **`deleteLater()` alone doesn't remove a widget from view.** Taking it out of a layout leaves it parented and painting at its last geometry until the event loop destroys it, so a rebuilt panel renders its old contents underneath. Call `widget.setParent(None)` first — `ScrollColumn.clear()` and `_clear_layout()` both do.
- Widgets are often constructed before `loop.run_forever()` starts, so `run_async()` ([`ui/icons.py`](ui/icons.py)) falls back to the loop `ui/app.py` *set* when none is *running*. A task created on a not-yet-running loop simply waits for it; `asyncio.get_running_loop()` alone would silently drop every fetch.
- Python 3.14 (PEP 758) allows unparenthesized `except A, B:`, and `ruff format` strips the parens. That is valid, not a syntax error — don't "fix" it back.
- Offscreen render for visual checks: `QT_QPA_PLATFORM=offscreen`, then `window.grab().save(path)` — see [Verifying a change](#verifying-a-change) for the full command.
- PySide6 is an *optional* dep (`ui` extra). Nothing under `bladecaller/` may be imported from `league.cli`, `league.companion`, or any other non-UI module — `launch_ui()` in [`__init__.py`](__init__.py) is the only entry point and it catches the `ImportError`. Import in the other direction (UI → `league.config` etc.) is fine.
