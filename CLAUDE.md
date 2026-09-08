# League of Snakes

Python app monitors League of Legends via Live Client API, drives RGB on Razer Chroma + Govee smart lights from in-game events.

**Personal project. Works for me only. No code quality enforcement, refactors, or abstractions unless asked.**

## Project Structure

```
league-of-snakes/
├── main.py               # Legacy entry point (direct run, always enables Govee)
├── lcu_main.py           # Scratch script: LCU lobby creation test
├── riot_main.py          # Scratch script: Riot API test
├── justfile              # Recipes: `just run` / `just lcu` / `just riot` (PowerShell on Windows)
├── riotgames.pem         # SSL cert (no longer used — LeagueClient uses verify=False)
├── pyproject.toml        # Project metadata and dependencies (uv)
├── .env                  # RIOT_API_KEY (not committed)
├── logs/                 # Log output directory (created at runtime)
├── src/league/
│   ├── api.py            # LeagueClient (Live Client API poller)
│   ├── bridge.py         # LeagueEventBridge + LeagueEvent — unified in-game/out-of-game event hub
│   ├── cache.py          # DataCache (simple JSON/text file cache under a directory)
│   ├── companion.py      # run_companion() — async companion mode runner; ChromaLighting/GoveeLights/open_presence/open_gameflow feature context managers
│   ├── markup.py         # Pure markup-string helpers (format_file_path/url/kda/result/duration/player) — no rich, safe for backend messages
│   ├── reporting.py      # ProgressReporter protocol + NullReporter — backend-facing progress channel
│   ├── models.py         # GameEvent, ActivePlayer, Player, AllGameData, Match, PlayerMatch, DragonItem, CurrentGameInfo (SPECTATOR-V5)
│   ├── enums/            # Enum package
│   │   ├── __init__.py   # re-exports everything below
│   │   ├── enum_base.py  # LookupEnum base
│   │   ├── base.py       # GameEventType, GameTeam, GameResult, LeagueClientStatus, GamePlayerPosition, ReplaySequenceEasing, Ranked* enums
│   │   ├── queues.py     # Queue (all queue IDs) + QUEUE_DESCRIPTION / QUEUE_MAP lookup dicts
│   │   ├── maps.py       # Map
│   │   ├── match_type.py # MatchType
│   │   └── aliases.py    # QueueChoice/MatchTypeChoice CLI aliases + resolve_* helpers
│   ├── http.py           # BaseAPIClient (shared base for all API clients); RiotRateLimiter (X-App-Rate-Limit header tracking)
│   ├── config.py         # TOML config (stored at OS app dir via typer.get_app_dir); ConfigSection helper
│   ├── constants.py      # Shared constants
│   ├── dragon.py         # CommunityDataDragon (champion/item metadata)
│   ├── predicates.py     # Predicate[T] composable predicate system (@rule decorator, &/|/~ operators)
│   ├── riot_api.py       # RiotAPIClient (PUUID, matches, summoner, ranked data, live match via SPECTATOR-V5)
│   ├── timeline.py       # MatchTimelineAnalyzer, HighlightEvent, ParticipantPositionTrack (Riot API match timeline → highlights) — analysis only, no rendering
│   ├── highlights.py     # HighlightManager (replay download, open replay client, OBS-style recording of clip ranges)
│   ├── watcher.py        # MatchWatcher (session lifecycle, reconnect logic, event routing)
│   ├── cli/              # Typer CLI package — primary entry point (featherstorm)
│   │   ├── __init__.py   # runs config.init(), re-exports `app` (keeps league.cli:app entry point)
│   │   ├── main.py       # root app: callback + `companion` command, add_typer each group
│   │   ├── _shared.py    # try_get_cfg_or_input(), default_client_path, _riot_client()
│   │   ├── lcu.py        # lcu_app (+ nested champ-select, lobby, inventory, gameflow apps)
│   │   ├── cfg.py        # cfg_app
│   │   ├── riot.py       # riot_app (matches, match, timeline, puuid, ranked, live-game)
│   │   ├── highlights.py # highlights_app
│   │   └── dragon.py     # dragon_app (item, champion, art)
│   ├── ui/               # Terminal rendering layer — the only place that writes to the console
│   │   ├── __init__.py   # public surface (output, console, setup_logging, render, RichProgressReporter, MatchRow)
│   │   ├── theme.py      # THEME + colour constants (Xayah/Rakan/Gold)
│   │   ├── console.py    # Rich Console singleton + get_console()
│   │   ├── output.py     # Output facade (print/json/rule/info/success/warning/error/prompt/status/progress) + `output` default
│   │   ├── registry.py   # @singledispatch render(obj) -> RenderableType, Pretty fallback
│   │   ├── logging.py    # setup_logging() — installs RichHandler on the shared Console
│   │   ├── progress.py   # RichProgressReporter (terminal impl of league.reporting.ProgressReporter)
│   │   ├── viewmodels.py # MatchRow (presentation-only dataclasses)
│   │   └── renderers/    # Pure sync model → renderable functions
│   │       ├── matches.py  # match_table(rows), new_table()
│   │       ├── ladder.py   # ranked_ladder_table(), format_ladder_name()
│   │       ├── items.py    # item_panel() (DDragon pseudo-HTML → markup)
│   │       ├── timeline.py # player_timeline_panel()
│   │       └── events.py   # EventFeedContext, describe_event(), format_event_line(), FEED_EVENTS
│   ├── bladecaller/      # PySide6 desktop UI (Dashboard, Match History, Settings) — see src/league/bladecaller/CLAUDE.md
│   ├── discord/
│   │   ├── presence.py         # DiscordRichPresence, DiscordActivity — generic pypresence wrapper
│   │   └── league_presence.py  # LeagueRichPresence — League-aware presence (lobby/in-game status, KDA, skin art, role icon)
│   └── lcu/
│       ├── lcu.py        # LCUClient (lockfile auth, champ-select, lobby, match history, replays, inventory, gameflow endpoints)
│       ├── models.py     # MyChampSelection, Summoner, LobbyGameMode, LobbyType, LCUGameflowPhase, LCUTimeline*, LCUMatch*
│       ├── socket.py     # LCUWebsocketClient (LCU WAMP websocket, OnJsonApiEvent subscriptions)
│       ├── gameflow.py   # LCUGameFlow + LCUGameFlowEvent (lobby created/updated/deleted via websocket, gameflow phase)
│       └── exceptions.py # LCU replay exceptions
├── data/                 # Sample JSON snapshots for development/testing
└── ref/                  # Reference JSON snapshots + Featherstorm.html (UI design mockup)
```

## Tech Stack

- **Python 3.14** — required minimum (per `pyproject.toml`)
- **uv** — package manager (`uv run`, `uv add`, etc.)
- **httpx[http2]** — async HTTP client for all API calls
- **chroma** — local sibling package at `../rzr-chroma` (Razer Chroma SDK wrapper)
- **govee** — local sibling package at `../govee` (Govee LAN UDP controller)
- **python-dotenv** — loads `.env` for Riot API key
- **pydantic** — used for `Match`, `PlayerMatch` models in `models.py`
- **toml** — reads/writes `config.py` TOML file
- **rich** — used for `print()` in `api.py` (pretty terminal output)
- **typer** — CLI framework (`featherstorm` CLI entry point)
- **pypresence** — Discord Rich Presence (AioPresence IPC)
- **websockets** — LCU websocket client (`lcu/socket.py`)
- **pillow** — image handling (skin tiles/art)
- **pynput** — input simulation (highlights recording)
- **pyside6** — desktop UI (optional `ui` extra; `bladecaller` gui-script)
- **qasync** — unifies the Qt and asyncio event loops in the UI (optional `ui` extra)

## Running

Primary (CLI, recommended):
```bash
uv run featherstorm companion [--no-govee] [--no-discord] [--no-chroma]
                                       # Govee via companion.govee_enabled, Chroma via companion.chroma_enabled, Discord presence via discord.enable_rich_presence
                                       # --no-* flags force a feature off for that run (they can't force one on)
uv run featherstorm riot matches ["Name"] ["TAG"] [--count N] [--match-type ranked|normal|tourney|tutorial]
uv run featherstorm riot match <match_id>
uv run featherstorm riot timeline <match_id>
uv run featherstorm riot puuid ["Name"] ["TAG"]
uv run featherstorm riot ranked <solo|tft|flex> <tier> <division>
uv run featherstorm riot live-game ["Name"] ["TAG"]   # currently ongoing match (SPECTATOR-V5)
uv run featherstorm highlights capture [--game-path P] [--export-path P] [--name N] [--tagline T] [--count N]
uv run featherstorm dragon item <item_id>
uv run featherstorm dragon champion <champion_id>
uv run featherstorm dragon art <champion_name> [--skin N] [--asset-type splash|...] [--output-path P]
```

Desktop UI:
```bash
uv sync --extra ui
uv run bladecaller
```

Legacy (direct, always enables Govee):
```bash
uv run main.py
```

League must run for Live Client API (`https://127.0.0.1:2999`) to be reachable. App waits + reconnects automatically — no manual restart between games.

## Config System

`src/league/config.py` stores TOML config at `typer.get_app_dir("featherstorm")` (OS app dir). Auto-created on first run with defaults.

Categories and keys:
- `lcu.client_install_path` — path to League install dir (for LCU lockfile)
- `govee.default_power_state`, `govee.default_brightness`, `govee.request_timeout`
- `chroma.teammate_dim_factor` (default `0.4`)
- `companion.default_player_name` — fallback name when not in active game
- `companion.default_player_tagline` — fallback tagline (used by riot commands as default arg)
- `companion.govee_enabled` (default `False`) — toggle Govee integration (replaces old `--no-govee` CLI flag)
- `companion.chroma_enabled` (default `False`) — toggle Razer Chroma integration
- `companion.max_reconnect_attempts` (default `5`), `companion.wait_interval` (default `2.0`s), `companion.poll_interval` (default `0.25`s), `companion.session_timeout` (default `30.0`s)
- `discord.enable_rich_presence` (default `True`) — toggle Discord Rich Presence in companion mode
- `discord.app_id` — Discord application ID for Rich Presence
- `highlights.export_path` — directory for saved highlight clips (prompted on first use if unset)
- `highlights.export_constant_quality` (default `'20'`) — FFmpeg CRF quality
- `highlights.export_preset` (default `'6'`) — FFmpeg preset (0–9, lower = slower/smaller)
- `highlights.export_fps` (default `'60'`) — output framerate
- `highlights.export_multipass` (default `'fullres'`) — multipass encoding mode
- `highlights.export_audio_quality` (default `'192k'`) — audio bitrate
- `meta.cache_dir` — cache directory for Data Dragon and other metadata
- `bladecaller.status_poll_interval` (default `3.0`s) — how often the UI sidebar indicator polls the LCU gameflow phase
- `bladecaller.match_history_page_size` (default `20`) — matches fetched per "Load more" on the Match History page
- `bladecaller.dashboard_recent_matches` (default `5`) — rows shown in the dashboard's Recent Matches card

Manage via CLI:
```bash
uv run featherstorm cfg view [category]
uv run featherstorm cfg get <category> <key>
uv run featherstorm cfg set <category> <key> <value>
uv run featherstorm cfg clear <category> <key>
uv run featherstorm cfg reset [--force]
```

## Architecture

### Data Flow

```
League Live Client API (127.0.0.1:2999)
        │
        ▼
  MatchWatcher.run()           ← session lifecycle loop (watcher.py)
        │
        ├── _wait_for_session()   ← polls LeagueClientStatus until CONNECTED or timeout
        │
        └── _poll_session()       ← calls LeagueClient.poll_events() every 250ms
                │
                ▼
        LeagueClient.on_event()  ← builds GameEvent, appends history, fires callbacks (api.py)
                │
                ├── companion callbacks registered via watcher.on(...) (companion.py)
                │      ├── lighting (on_game_start / on_champion_kill / ...)
                │      ├── console kill-feed (register_event_feed)
                │      └── Discord presence (init_match on GameStart, end_match on GameEnd)
                │
                ├── ChromaSession  (Razer Chroma SDK via chroma package)
                │
                └── GoveeConnectionListener  (Govee LAN UDP, if govee_enabled)

LCU websocket (wss://localhost:<port>, lockfile auth)
        │
        ▼
  LCUGameFlow (gameflow.py) — LobbyCreated/Updated/Deleted events
        │
        └── LeagueRichPresence (discord/league_presence.py, if enable_rich_presence)
               ├── lobby/queue/in-game activity states
               └── 15s update loop: KDA/CS state line while in game
```

### Key Classes

- **`LeagueClient`** ([league/api.py](league/api.py)) — polls League Live Client API; `on_event()` builds a `GameEvent`, appends to `_history`, and dispatches to callbacks registered via `on(event_type, cb)`. No built-in per-event handlers (lighting + console feed live in companion). Tracks `last_event_count` for new events only — **`reset()` (clears `last_event_count` and `_history`) must be called at the start of every session**, or the next match dispatches nothing until its event count passes the previous one's.
  - `get_active_player()` → `Optional[ActivePlayer]` — returns `None` on HTTP error or spectator mode (API returns `{"error": "..."}` with 200 status in spectator).
  - `get_active_player_team()` → `Optional[GameTeam]` — returns `None` in spectator mode.
  - `get_all_game_data()` → `AllGameData` — full snapshot; `allPlayers` always populated, `activePlayer` is `None` in spectator mode.
- **`DataDragon`** ([league/api.py](league/api.py)) — fetches champion/item metadata from Riot CDN.
- **`DragonItem`** ([league/models.py](league/models.py)) — constructed via `**data` unpacking from CDN JSON; every field in API response needs matching dataclass field or `get_item()` raises `TypeError`. Two keys remapped: `"from"` → `builds_from`, `"into"` → `builds_into` (popped before unpacking in `dragon.py`).
- **`GameEvent`** ([league/models.py](league/models.py)) — `@dataclass` with PascalCase fields matching API response keys directly (e.g. `EventName`, `KillerName`, `EventTime: float`). `__post_init__` casts `EventName` → `GameEventType`, `AcingTeam` → `GameTeam`, `Result` → `GameResult` via `try_cast_to_enum` — an unrecognised value stays a raw string instead of raising. **Build with `GameEvent.from_dict(raw)`, not `GameEvent(**raw)`** — it filters unmodelled keys (keeping them as plain attributes) so a new API field can't `TypeError` the poll loop.
- **`ActivePlayer`** ([league/models.py](league/models.py)) — typed model for `/activeplayer` response. Key fields: `riotId`, `riotIdGameName`, `riotIdTagLine`, `summonerName`. `fullRunes` is `Optional[FullRunes]` — empty in some game modes.
- **`Player`** ([league/models.py](league/models.py)) — model for each entry in `allPlayers`. Key fields: `riotIdGameName`, `team: GameTeam`. `runes` is `Optional[PlayerRunes]` — empty list in some game modes. `screenPositionBottom`/`screenPositionCenter` are `Optional[str]` comma-separated coordinates, spectator mode only (`FLT_MAX` sentinel when player not visible).
- **`GameEventType`** ([league/enums/base.py](src/league/enums/base.py)) — `StrEnum` with exact strings from League Live Client API (e.g. `GameStart = "GameStart"`). Covers: `GameStart`, `GameEnd`, `MinionsSpawning`, `FirstBlood`, `TurretKilled`, `InhibKilled`, `InhibRespawned`, `DragonKill`, `HeraldKill`, `BaronKill`, `ChampionKill`, `Multikill`, `Ace`, `HordeKill`, `FirstBrick`, `AtakahnKill`.
- **`LeagueClientStatus`** ([league/enums/base.py](src/league/enums/base.py)) — `Enum`: `DISCONNECTED` (no API), `LOADING` (API up but no active game), `CONNECTED` (in game), `BANISHED` (connection dropped mid-session). Used by `MatchWatcher` to decide reconnect behavior.
- **`GamePlayerPosition`** ([league/enums/base.py](src/league/enums/base.py)) — `StrEnum`: `TOP`, `JUNGLE`, `MIDDLE`, `BOTTOM`, `SUPPORT`.
- **`ReplaySequenceEasing`** ([league/enums/base.py](src/league/enums/base.py)) — `StrEnum` with all easing types for the League replay API (linear, snap, smoothStep, quadratic/cubic/quartic/quintic/sine/circular/exponential/elastic/back/bounce ease in/out/in-out).
- **`Queue`** ([league/enums/queues.py](src/league/enums/queues.py)) — `LookupEnum` of every League queue ID (blind, draft, ranked, ARAM, RGMs, bots…). Duplicate historic names suffixed `_2`/`_3` — live queue IDs are usually the highest suffix (e.g. `Q_5V5_ARAM_GAMES_3 = 450`, `Q_5V5_RANKED_SOLO_GAMES_2 = 420`). `QUEUE_DESCRIPTION` and `QUEUE_MAP` dicts map queue → display name / map name.
- **`LCUWebsocketClient`** ([league/lcu/socket.py](src/league/lcu/socket.py)) — LCU WAMP websocket (`wss://localhost:<port>`, lockfile Basic auth, `verify` off). `on(endpoint, callback, event_type)` registers callbacks; endpoint paths converted to event names (`/lol-lobby/v2/lobby` → `OnJsonApiEvent_lol-lobby_v2_lobby`). Subscribes per registered event on connect (or firehose `OnJsonApiEvent` if none). Auto-reconnects via `websockets.connect` iterator. Callbacks must be registered **before** `connect()` — raises after.
- **`LCUGameFlow`** ([league/lcu/gameflow.py](src/league/lcu/gameflow.py)) — high-level gameflow wrapper over `LCUClient` + its websocket. `add_callback(LCUGameFlowEvent.LobbyCreated|LobbyUpdated|LobbyDeleted, cb)`, `get_phase()` → `LCUGameflowPhase`, `start()` connects websocket.
- **`DiscordRichPresence`** ([league/discord/presence.py](src/league/discord/presence.py)) — generic pypresence `AioPresence` wrapper. `DiscordActivity` dataclass holds full activity payload; `set_activity()` / `update_activity(**kwargs)` mutate local state, `update()` pushes to Discord.
- **`LeagueRichPresence`** ([league/discord/league_presence.py](src/league/discord/league_presence.py)) — League-aware presence. Tracks `SessionStatus` (Empty/InLobby/InQueue/InGame). `init_lobby()` from LCU lobby data (queue description, party size), `init_match()` from `AllGameData` (champion + lane opponent, skin splash as large image, role icon as small image), 15s update loop pushes KDA/CS state. `try_update_queue_type()` resolves queue via Riot SPECTATOR-V5 live match.
- **`CurrentGameInfo`** ([league/models.py](src/league/models.py)) — SPECTATOR-V5 active-game model (`gameQueueConfigId`, participants, bans).
- **`Effects`** ([league/companion.py](src/league/companion.py)) — `@dataclass` holding Chroma effect state. Fields: `blue`, `red`, `white` (static base effect IDs), plus flash animation fields (`kill_flash`, `teammate_kill_flash`, `objective_flash`, `turret_flash`, `teammate_turret_flash`, `first_brick_flash`) — each `dict[Optional[GameTeam], ChromaAnimation]` keyed by team so animation fades back to correct base color. `base_for(team)` / `flash_for(name, team)` do the team lookup.
- **`ChromaLighting`** ([league/companion.py](src/league/companion.py)) — async context manager owning the `ChromaSession`, device and `Effects`. `await set_team(team)` sets the base colour, `flash(name, team)` fires an animation. Constructed with `enabled=False` it enters cleanly and every method no-ops.
- **`GoveeLights`** ([league/companion.py](src/league/companion.py)) — same shape for Govee: `__aenter__` discovers devices and applies config defaults, `set_team(team)` pushes a colour, `__aexit__` calls `listener.cleanup()`. No-ops when disabled.
- **`MatchWatcher`** ([league/watcher.py](src/league/watcher.py)) — wraps `LeagueClient`, manages session lifecycle (connect → poll → disconnect → reconnect). Key methods: `watcher.on(event_type, callback)`, `@watcher.on_session_start`, `@watcher.on_session_end`, `await watcher.run()`. Config keys: `companion.max_reconnect_attempts`, `companion.wait_interval`, `companion.poll_interval`, `companion.session_timeout`. Uses `LeagueClientStatus` to decide reconnect vs clean exit. Ctor param `exit_on_timeout` (default `True`): when `False`, `run()` keeps waiting forever instead of exiting after `session_timeout` with no game (used by `LeagueEventBridge`). Ctor param `reporter` (default `NullReporter()`): drives the "waiting for client/match" spinner — `run_companion()` passes a `RichProgressReporter`.
- **`LeagueEventBridge`** ([league/bridge.py](src/league/bridge.py)) — top-level unified event hub bridging in-game (Live Client API via `MatchWatcher`) and out-of-game (LCU websocket) events. `bridge.on(LeagueEvent.X, cb)` (decorator-or-direct, sync or async), `await bridge.run()`. `LeagueEvent` StrEnum = all `GameEventType` members (payload `GameEvent`) + `LobbyCreated/Updated/Deleted` (payload `LCUWebsocketEvent`) + `PhaseChanged` (payload `LCUGameflowPhase`, via ws endpoint `/lol-gameflow/v1/gameflow-phase`) + `SessionStart`/`SessionEnd` (no args). Registers internal fan-out dispatchers in `__init__` so user callbacks can be added after ws connect. Exposes `bridge.game` (`LeagueClient`) and `bridge.lcu` (`LCUClient`, `None` when League client not running — out-of-game events disabled with warning). Helpers: `get_phase()`, `get_game_data()`, `is_in_game()`, `close()`. Async callbacks are dispatched as tasks (tracked in `_tasks`, cancelled by `close()`) so a slow handler can't stall the poll loop — they run concurrently, not serialized; sync callbacks still run inline. `close()` also disconnects the websocket and `aclose()`s both httpx clients, and `run()` calls it in a `finally`. Additive — `run_companion()` does not use it.
- **`MatchTimelineAnalyzer`** ([league/timeline.py](src/league/timeline.py)) — analyzes Riot API `MatchTimeline` for highlight events using composable `Predicate` rules. `get_highlight_events()` → `list[HighlightEvent]`. `ParticipantPositionTrack` provides linear-interpolated position at any timestamp.
- **`Predicate[T]`** ([league/predicates.py](src/league/predicates.py)) — composable boolean predicate wrapping a `T → bool` function. Supports `&`, `|`, `~` operators. `@rule` decorator registers named factories. `load_rule_from_config(path)` / `load_rule_from_dict(config)` build predicates from JSON config.
- **`Output`** ([league/ui/output.py](src/league/ui/output.py)) — the console facade; module-level instance `output`. `print()` (routes through `render()`), `json()`, `rule()`, `info/success/warning/error()`, `prompt()`, `status(msg)` (project spinner baked in), `progress(*columns)`. Every CLI command writes through this.
- **`ProgressReporter`** ([league/reporting.py](src/league/reporting.py)) — `Protocol` with `message()`, `step()`, `advance()`, `task(description, total=None)`. `NullReporter` is the no-op default; `RichProgressReporter` ([league/ui/progress.py](src/league/ui/progress.py)) is the terminal implementation (indeterminate `task` → spinner + elapsed, `total=` → bar + M-of-N). Lets backend code report progress without importing rich.
- **`MatchRow`** ([league/ui/viewmodels.py](src/league/ui/viewmodels.py)) — presentation-only match view shared by the Riot and LCU match-history commands; `match_table()` shows the Position column only when rows carry one, Game Mode likewise.
- **`GoveeConnectionListener`** ([govee package](../govee/src/govee/govee.py)) — discovers + manages Govee smart lights over LAN UDP. `listener.devices: dict[str, GoveeDevice]` holds discovered devices by IP. Wrapped by `GoveeLights`, which awaits `govee.request_timeout` (0.5s) after `start()` for discovery.

### Team → Effect Mapping

Team → colour lookups live next to the thing that owns them, avoiding if/elif chains. Chroma: `Effects.base_for(team)` ([league/companion.py](src/league/companion.py)) maps `ORDER → blue`, `CHAOS → red`, everything else (spectator, unknown) → `white`. Govee: module-level `TEAM_TO_GOVEE_COLOR`, same shape, read by `GoveeLights.set_team()`:

```python
TEAM_TO_GOVEE_COLOR = {
    GameTeam.ORDER: GoveeColor.blue(),
    GameTeam.CHAOS: GoveeColor.red(),
    GameTeam.SPECTATOR: GoveeColor.white(),
}
```

### Adding a New Lighting Effect

All Chroma effects created at startup via `setup_chroma_effects()` in [league/companion.py](src/league/companion.py), stored in `Effects` dataclass.

- **Static color** (base): call `static(ChromaColor.xyz())` inside `setup_effects()`, add returned ID as `str` field on `Effects`.
- **Flash animation**: call `make_flash(ChromaColor.xyz())` — uses `ChromaAnimation.flash_fade()` to build `dict[Optional[GameTeam], ChromaAnimation]` with one animation variant per base color (ORDER/CHAOS/spectator). Add as `dict` field on `Effects`.
  - Optionally pass `steps`, `flash_duration`, `total_fade_duration` to tune (e.g. `first_brick_flash` uses `steps=5, total_fade_duration=0.5`).
  - Dim teammate effects: pass `scale_color(ChromaColor.xyz(), TEAMMATE_DIM_FACTOR)` as color.
- Trigger flash from callback: `chroma.flash("<field>", active_player_team)` — `ChromaLighting.flash()` picks the team variant (falling back to the `None` one) and fires `play_animation()` as a task. No-ops when Chroma is disabled.
- `play_animation()` pre-uploads all frames to Chroma SDK, steps through with baked-in timing. Fades back to team base color automatically — no manual restore needed.
- Govee in callback: `govee.set_team(team)`, or reach into `govee.listener.devices.values()` for other `set_*` methods. Govee has no animation support — only instant color/brightness/power changes.

### Adding a New Event Handler

- Add event to `GameEventType` in [league/enums.py](league/enums.py) if missing. Value must be exact string Live Client API returns.
- Register a callback via `watcher.on(GameEventType.<New>, cb)` in `run_companion` ([league/companion.py](src/league/companion.py)) for lighting. For console kill-feed output, add a `case` to `describe_event()` and the event to `FEED_EVENTS` ([league/ui/renderers/events.py](src/league/ui/renderers/events.py)) — `register_event_feed` in companion wires every member of `FEED_EVENTS` to one callback.

## Rendering Layer

`src/league/ui/` owns every byte written to the terminal. Four rules:

1. **Renderers are pure and sync** — domain/view model in, `RenderableType` out. No `await`, no console, no I/O. Anything a renderer needs (champion names, resolved item names) is fetched by the caller first.
2. **Only `ui/output.py` and `ui/console.py` touch the `Console`.** Commands call `output.print(...)`, never `console.print(...)`.
3. **Backend modules never import rich** and never import `league.ui`. They emit data (return values), diagnostics (`logging.getLogger(__name__)`), and progress (an injected `league.reporting.ProgressReporter`). The only ui-adjacent import they may take is `league.markup` — pure markup strings, zero rich.
4. **Markup is produced in the ui layer**, with one sanctioned exception: log and reporter messages may carry markup, since `RichHandler` is installed with `markup=True`.

Diagnostics: `setup_logging()` ([league/ui/logging.py](src/league/ui/logging.py)) is called from the CLI callback and installs a `RichHandler` on the shared Console (httpx/websockets/asyncio pinned to WARNING). Bladecaller configures its own handlers — it imports nothing from `league.ui`.

Per-model rendering: `render()` ([league/ui/registry.py](src/league/ui/registry.py)) is a `functools.singledispatch` — register a concrete model type in a renderer module to give it a default view; unregistered objects fall back to `rich.Pretty` (the old `print(model)` behaviour). Models themselves stay rich-free — no `__rich__` on anything in `models.py`.

Adding a renderer: write a pure function in `ui/renderers/`, export it from `ui/renderers/__init__.py`, and call it from the command as `output.print(my_renderer(data))`. Reuse `new_table()` ([league/ui/renderers/matches.py](src/league/ui/renderers/matches.py)) for the project's table style and the `format_*` helpers in [league/markup.py](src/league/markup.py) for KDA/result/duration/player cells.

Progress from backend code: take a `ProgressReporter` in the constructor, default to `NullReporter()`, and call `reporter.message()` / `reporter.step()` / `reporter.advance()` / `with reporter.task(desc, total=...)`. The CLI/composition root injects `RichProgressReporter()`. `HighlightManager` and `MatchWatcher` both work this way.

## Bladecaller UI

PySide6 desktop app (`bladecaller` gui-script, optional `ui` extra). Style is token-driven: colors/fonts/radii live in `src/league/bladecaller/resources/theme.py`, substituted into the `app.qss` template at load.

Qt and asyncio share one loop via `qasync`, so controllers `await` the async backend directly with no threading. `ClientStatusController` (`bladecaller/controllers/client_status.py`) polls the LCU gameflow phase and drives the sidebar status dot.

Pages: **Dashboard** (Recent Matches card) and **Match History** (paged, filterable list; rows expand to stat tiles, a 10-player scoreboard and build order), plus Settings. `MatchHistoryController` (`bladecaller/controllers/match_history.py`) feeds both — the list comes from the LCU (no API key), and expanding a row fetches the full lobby from Riot MATCH-V5, degrading to LCU-only stats when `RIOT_API_KEY` is unset.

**Working on the UI? Read [src/league/bladecaller/CLAUDE.md](src/league/bladecaller/CLAUDE.md)** — style system, selector table, `components.py` API, adding-a-page recipe, quirks.

## LCU Client

`src/league/lcu/lcu.py` — `LCUClient` talks to League client UI API via local lockfile.
- League client must be running (not just in-game)
- Reads `<client_install_path>/lockfile` for port + password (Basic auth, username `riot`)
- `LCUClient(client_install_path: Path)` — path defaults to `config.get("client_install_path", "lcu")`; falls back to hardcoded `F:/Games/League of Legends/lockfile` if lockfile missing
- Key methods: `get_locked_champion()`, `get_hovered_champion()`, `create_game_lobby()`, `create_custom_game_lobby()`, `create_normal_game_lobby()` (non-functional), `get_current_summoner()`, `get_lobby()`, `get_match_history()`, `get_match()`, `get_match_timeline()`, replay methods (`download_replay()`, `launch_replay()`), inventory methods, gameflow methods (`get_gameflow_phase()`, `get_gameflow_availability()`, `get_gameflow_session()`)
- Websocket: `client.ws` is an `LCUWebsocketClient`; `start_websocket()` / `close_websocket()` (also via `async with`). See `LCUGameFlow` for the high-level event wrapper.

CLI:
```bash
uv run featherstorm lcu summoner
uv run featherstorm lcu matches [--count N]
uv run featherstorm lcu last
uv run featherstorm lcu champ-select locked
uv run featherstorm lcu champ-select hovered
uv run featherstorm lcu lobby get
uv run featherstorm lcu inventory item [--content-id ID]
uv run featherstorm lcu inventory asset <endpoint>
uv run featherstorm lcu inventory tiles <champion_name> [--output-dir P]
uv run featherstorm lcu gameflow session
```

## Govee Integration

`govee` package (`../govee`, sibling on disk) controls Govee smart lights over LAN UDP — no cloud, no API key.

- **`GoveeConnectionListener`** — discovers devices via multicast broadcast (`239.255.255.250:4001`), listens on `4002`. Call `listener.start()` then `await asyncio.sleep(GOVEE_REQUEST_TIMEOUT)` before accessing `listener.devices`.
- **`GoveeDevice`** — per-device control. Key methods: `set_power_state(bool)`, `set_brightness(0–100)`, `set_color_and_temperature(GoveeColor, temp_kelvin=5000)`. All sends fire-and-forget (retries 5× with 50ms gaps, no confirmation).
- **`GoveeColor`** — simple RGB dataclass with same factory methods as `ChromaColor` (`.blue()`, `.red()`, `.white()`, `.gold()`, `.purple()`).
- Govee only updated on `GameStart` (sets team color). Flash events drive Chroma only.

## Riot API (riot_api.py)

`RiotAPIClient` — reads `RIOT_API_KEY` from `.env` (via `python-dotenv`). Route logic in `get_region_for_url()`: `/riot/*` and `match/v5` → `americas`, `/lol/*` → `na1`.

MATCH-V5 methods:
- `get_match_ids(puuid, *, count, start, match_type, queue, start_time, end_time)` → `list[str]`
- `get_match(match_id)` → `Match`
- `get_match_timeline(match_id)` → `MatchTimeline`
- `get_recent_matches(puuid, count, match_type)` → `list[PlayerMatch]` (convenience wrapper)

Other methods:
- `get_puuid(game_name, tag_line)` → `str | None`; `get_account()` / `get_many_accounts()` cached via `DataCache`
- `get_ranked_data(queue: RankedQueueType, tier: RankedTier, division: RankedDivision, page)` → `set[LeagueEntry]` — LEAGUE-V4 ladder entries
- `get_live_match_for_puuid(puuid)` → `CurrentGameInfo | None` — SPECTATOR-V5 active game (404 when not in game → `None`)

`RiotRateLimiter` ([league/http.py](src/league/http.py)) tracks `X-App-Rate-Limit`/`-Count` headers per window; `acquire()` sleeps until capacity available.

> `developer.riotgames.com/apis` is correct API reference but JS-heavy SPA — **WebFetch cannot render it**. Use **WebSearch** as fallback (e.g. `"riot match-v5 API endpoints query parameters"`), or headless browser tool (e.g. Playwright MCP) if available.

> `https://developer.riotgames.com/docs/lol#data-dragon` is correct place for Data Dragon API docs.

## External APIs

| API | Base URL | Auth |
|-----|----------|------|
| League Live Client | `https://127.0.0.1:2999/liveclientdata` | None (`verify=False`) |
| Riot Data Dragon | `https://ddragon.leagueoflegends.com` | None |
| Riot API | `https://api.riotgames.com` | `RIOT_API_KEY` in `.env` |
| Govee LAN | UDP `device_ip:4003` / broadcast `239.255.255.250:4001` | None |

## Known Quirks

- `DATA_DIR` in [league/api.py](league/api.py) hardcoded to absolute path (`X:/league-of-snakes/data`). Drive letter changes → update it.
- `chroma` dep is local path ref (`../rzr-chroma`); both repos must be disk siblings. Source at `../rzr-chroma/src/chroma`.
- `govee` dep is local path ref (`../govee`); must also be disk sibling. Source at `../govee/src/govee`.
- Live Client API only available during active game. `MatchWatcher` polls every `companion.wait_interval` (2s default) until connected, then every `companion.poll_interval` (0.25s default). No manual restart between games.
- All three companion features resolve through `feature_enabled(flag, key, default=...)` ([league/companion.py](src/league/companion.py)): `--no-govee` / `--no-discord` / `--no-chroma` on `featherstorm companion` only *disable* — the config key (`companion.govee_enabled`, `companion.chroma_enabled`, `discord.enable_rich_presence`) is what turns a feature on.
- Disabled features are still entered as objects, not `None` — `ChromaLighting` / `GoveeLights` no-op on every method when off, so callbacks have no `if chroma:` guards. Discord is the exception: `open_presence()` yields `None` when off (it wraps a third-party class), and `open_gameflow(presence)` no-ops in turn, so the LCU websocket is only started when presence exists.
- `riot-root-cert.pem` renamed to `riotgames.pem` but no longer used — `LeagueClient` uses `verify=False`.
- pypresence `AioPresence.close()` is sync and calls `loop.close()` on the running event loop — never call it. `DiscordRichPresence.close()` ([league/discord/presence.py](src/league/discord/presence.py)) closes the IPC pipe transport directly instead. `run_companion()` closes presence in a `finally` so Ctrl+C doesn't leave an unclosed proactor pipe transport (`ValueError: I/O operation on closed pipe` warning at exit).
- Spectator mode: `/activeplayer` returns `{"error": "..."}` with HTTP 200 (not 4xx). Both `get_active_player()` and `AllGameData.__post_init__` guard against this, returning `None` for `activePlayer`.
- `Player.runes` and `ActivePlayer.fullRunes` can be empty list `[]` in some game modes — both typed `Optional`, guarded with falsy check before construction.
- `FirstBrick` events can have `TurretKilled = None` in some game modes — `on_first_brick` guards before calling `Turret.from_str()`.
- Govee local IP auto-detection in `govee/shared.py` uses socket to `8.8.8.8:80`. May fail on isolated networks — hardcode `LISTEN_ADDR` in `../govee/src/govee/shared.py` if needed.
- Govee discovery is periodic (every 180s); allow 0.5–2s after `listener.start()` before accessing `listener.devices`. New network devices may take up to 3 minutes.
- Govee sends fire-and-forget — no confirmation device received command.
- LCU match history (`/lol-match-history/v1/products/lol/current-summoner/matches`) returns **only the current summoner's participant** per game, not the full lobby — see the fixtures in `ref/`. The ten-player scoreboard has to come from Riot MATCH-V5; the match id is `f"{platformId}_{gameId}"`.
- **LCU puuids are not Riot puuids.** LCU match history reports an anonymized per-match UUID (`03c57e4e-11c8-550e-…`, 36 chars) where the Riot API reports the account's real 78-character puuid, so they never compare equal and `PlayerMatch.from_match(match, lcu_puuid)` raises `StopIteration`. Cross-reference the two sources on `participantId` instead — it is identical in both.
- **MATCH-V5 doesn't serve every queue.** Brawl (queue `2400`, Live Client game mode `KIWI`) returns **403 Forbidden**, custom / Practice Tool games (`3140`) return **404**. Both are permanent, not transient faults or a bad key — don't retry, and don't report them as a request failure.
- `RiotAPIClient.get_match()` re-raises the underlying `httpx.HTTPStatusError` rather than handing `None` to pydantic, so callers can read the status code. Everything else on `BaseAPIClient` still returns `None` on HTTP error.
- `DataDragon._make_champion_lookup()` stores `by-id` keys as **strings**. `get_champion_name()` / `get_champion()` index with `str(championID)`, and the JSON cache round-trip stringifies them anyway — int keys silently broke every lookup on the run that first built the cache.
- Upgrading Data Dragon version in `dragon.py`: test `get_item()` against a few items (e.g. `1001` Boots, `1054` Doran's Blade) — new CDN response fields cause `TypeError` on construction since `DragonItem` uses `**data` unpacking.
- LCU websocket callbacks must be registered **before** `connect()` — `LCUWebsocketClient.on()` raises once the listen task exists. `run_companion()` therefore calls `register_gameflow_events()` before starting the watcher.
- The LCU sends a **list** payload for some `/lol-lobby/v2/lobby` transitions — guard `isinstance(event.data, list)` before treating it as a lobby dict (`LeagueEventBridge` filters these out of its lobby dispatch; `run_companion`'s `on_lobby_create` guards directly).
- `data/help.json` is a dump of the LCU `/help` endpoint — 976 entries under `events`, the authoritative list of every `OnJsonApiEvent` the client emits. Use it instead of guessing endpoint names.
- LCU websocket event names derive from endpoint paths: slashes → underscores, prefixed `OnJsonApiEvent` (e.g. `/lol-lobby/v2/lobby` → `OnJsonApiEvent_lol-lobby_v2_lobby`).
- `LCUWebsocketClient.on()` with `type=None` never fires: `_on_message` matches `handler.event_type == event.eventType` exactly. Always pass an explicit `LCUWebsocketEventType`.
- `LCUGameflowPhase.Home` maps to the literal string `"None"` (LCU returns `"None"` when idle in client).
- Live Client `gameMode` string `"KIWI"` = ARAM (see `get_game_mode_string()` in `league_presence.py`); `"CLASSIC"` intentionally maps to `None` (no suffix on presence name).
- Queue type for presence can't come from Live Client API — `try_update_queue_type()` fetches it from Riot SPECTATOR-V5 (`gameQueueConfigId`), needs `RIOT_API_KEY`, only sets once per match.
- `Queue` enum has duplicate historic names suffixed `_2`/`_3`; live IDs usually highest suffix (ARAM = `Q_5V5_ARAM_GAMES_3` = 450).
- op.gg button on Discord presence disabled (commented out in `init_match()`).