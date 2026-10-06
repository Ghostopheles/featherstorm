# Featherstorm

Async Python League of Legends companion toolkit. Bridges Live Client API, LCU (REST + websocket), Riot Web API and Data Dragon into: Razer Chroma + Govee lighting driven by in-game events, Discord Rich Presence, highlight clip capture, a SurrealDB-backed match crawler, and the Bladecaller PySide6 desktop app.

**Personal project. Works for me only. No code quality enforcement, refactors, or abstractions unless asked.**

Detailed docs live in [docs/](docs/) — split by module to keep this file short. Load the relevant one for the area you're touching:

- [docs/architecture.md](docs/architecture.md) — data flow diagrams, crawler BFS flow, every key class (`LeagueClient`, `LeagueEventBridge`, `MatchWatcher`, `CrawlerDatabase`, etc.), team→effect color mapping, how to add a lighting effect or event handler
- [docs/config.md](docs/config.md) — full TOML config key reference + `featherstorm cfg` CLI
- [docs/rendering.md](docs/rendering.md) — terminal UI layer rules (`league/ui/`), renderer/progress-reporter conventions
- [docs/lcu.md](docs/lcu.md) — `LCUClient` (League client UI API via lockfile), CLI commands
- [docs/replay.md](docs/replay.md) — `ReplayManager` / `ReplayAPIClient` (replay download/launch via LCU, in-replay control via Replay API), CLI commands
- [docs/govee.md](docs/govee.md) — Govee LAN UDP smart-light integration
- [docs/riot-api.md](docs/riot-api.md) — `RiotAPIClient` (MATCH-V5, rate limiting), external API table
- [docs/quirks.md](docs/quirks.md) — known gotchas/workarounds across the whole app (read before debugging anything weird)
- [src/league/bladecaller/CLAUDE.md](src/league/bladecaller/CLAUDE.md) — PySide6 desktop UI (style system, components, adding a page)

## Project Structure

```
featherstorm/
├── pyproject.toml        # Project metadata and dependencies (uv)
├── docker-compose.yml    # SurrealDB server for the crawler (port 16800, data in ./data/surreal)
├── .env                  # RIOT_API_KEY (not committed)
├── logs/                 # Log output directory (created at runtime)
├── docs/                 # Domain-specific docs (see links above)
├── scripts/
│   ├── generate_enums.py    # Generates enum modules from Riot static JSON
│   └── champion_winrates.py # Example crawler-dataset consumer (champion winrate/playrate)
├── src/league/
│   ├── api.py            # LeagueClient (Live Client API poller)
│   ├── bridge.py         # LeagueEventBridge + LeagueEvent — unified in-game/out-of-game event hub
│   ├── cache.py          # DataCache (simple JSON/text file cache under a directory)
│   ├── companion.py      # run_companion() — companion mode runner, built on LeagueEventBridge; ChromaLighting/GoveeLights/open_presence feature context managers
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
│   ├── highlights.py     # HighlightManager (picks highlight events, records clip ranges through ReplayManager, ffmpeg compression)
│   ├── replay/           # Replay handling (see docs/replay.md)
│   │   ├── __init__.py   # re-exports ReplayManager, ReplayAPIClient, normalize_match_id
│   │   ├── api.py        # ReplayAPIClient — in-game Replay API (127.0.0.1:2999/replay): playback, render/camera, recording, sequences, waiters
│   │   └── manager.py    # ReplayManager — LCU replay metadata/download/open + close running replay; owns a ReplayAPIClient
│   ├── watcher.py        # MatchWatcher (session lifecycle, reconnect logic, event routing)
│   ├── crawler/          # Match crawler (SurrealDB-backed BFS over the summoner↔match graph + match dataset)
│   │   ├── __init__.py   # re-exports CrawlerDatabase, MatchCrawler, MatchFetcher, configs, CrawlStats
│   │   ├── schema.py     # `game` / `played` dataset DDL (generated from ParticipantSummary) + row builders
│   │   ├── database.py   # CrawlerDatabase (schema, dedupe, frontier claim/complete, store_match, exports)
│   │   ├── match_crawler.py # MatchCrawler + CrawlConfig — the BFS crawl loop
│   │   └── match_fetcher.py # MatchFetcher + FetchConfig — downloads and stores full match payloads
│   ├── cli/              # Typer CLI package — primary entry point (featherstorm)
│   │   ├── __init__.py   # runs config.init(), re-exports `app` (keeps league.cli:app entry point)
│   │   ├── main.py       # root app: callback + `companion` command; registers only the subcommand group in argv[1] (all groups for --help) to keep startup fast
│   │   ├── _shared.py    # try_get_cfg_or_input(), default_client_path, _riot_client()
│   │   ├── lcu.py        # lcu_app (+ nested champ-select, lobby, inventory, gameflow apps)
│   │   ├── cfg.py        # cfg_app
│   │   ├── riot.py       # riot_app (matches, match, timeline, puuid, ranked, live-game)
│   │   ├── highlights.py # highlights_app
│   │   ├── replay.py     # replay_app (status, download, open, playback, pause, resume, toggle, seek, speed, hide-ui, follow, render, record start/stop/toggle/status)
│   │   ├── crawler.py    # crawler_app (crawl, fetch, dataset, stats, export, schema, reset)
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
│   │       ├── crawler.py  # crawl_stats_table()
│   │       └── events.py   # EventFeedContext, describe_event(), format_event_line(), FEED_EVENTS
│   ├── bladecaller/      # PySide6 desktop UI (Dashboard, Match History, Settings) — see src/league/bladecaller/CLAUDE.md
│   ├── discord/
│   │   ├── presence.py         # DiscordRichPresence, DiscordActivity — generic pypresence wrapper
│   │   └── league_presence.py  # LeagueRichPresence — League-aware presence (lobby/in-game status, KDA, skin art, role icon)
│   └── lcu/
│       ├── lcu.py        # LCUClient (lockfile auth, champ-select, lobby, match history, inventory, gameflow endpoints)
│       ├── models.py     # MyChampSelection, Summoner, LobbyGameMode, LobbyType, LCUGameflowPhase, LCUTimeline*, LCUMatch*
│       ├── socket.py     # LCUWebsocketClient (LCU WAMP websocket, OnJsonApiEvent subscriptions)
│       ├── gameflow.py   # LCUGameFlow + LCUGameFlowEvent (lobby created/updated/deleted via websocket, gameflow phase)
│       └── exceptions.py # LCU replay exceptions
├── data/                 # Local only (gitignored): sample JSON snapshots, cache, SurrealDB volume
└── ref/                  # Local only (gitignored): reference JSON snapshots + Featherstorm.html (UI design mockup)
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
- **surrealdb** — crawler store (SurrealDB 2.x SDK, HTTP connection; server runs via `docker-compose.yml`)
- **pyside6** — desktop UI (optional `ui` extra; `bladecaller` gui-script)
- **qasync** — unifies the Qt and asyncio event loops in the UI (optional `ui` extra)

## Running

Primary (CLI, recommended):
```bash
uv run featherstorm companion [--no-govee] [--no-discord] [--no-chroma]
                                       # Govee via companion.govee_enabled, Chroma via companion.chroma_enabled, Discord presence via discord.enable_rich_presence
                                       # --no-* flags force a feature off for that run (they can't force one on)
                                       # runs on LeagueEventBridge — needs the League client for lobby/phase events
uv run featherstorm riot matches ["Name"] ["TAG"] [--count N] [--match-type ranked|normal|tourney|tutorial]
uv run featherstorm riot match <match_id>
uv run featherstorm riot timeline <match_id>
uv run featherstorm riot puuid ["Name"] ["TAG"]
uv run featherstorm riot ranked <solo|tft|flex> <tier> <division>
uv run featherstorm riot live-game ["Name"] ["TAG"]   # currently ongoing match (SPECTATOR-V5)
uv run featherstorm highlights capture [--game-path P] [--export-path P] [--name N] [--tagline T] [--count N] [--pick]
                                  # --pick lists highlights (time + killed champs), captures the one you choose
uv run featherstorm replay status|download|open [match_id]   # match_id optional (defaults to last LCU match); open has --wait/--no-wait
uv run featherstorm replay playback|pause|resume|toggle|render|hide-ui
uv run featherstorm replay seek <time>                 # 90, 1:30, 1m30s, or relative +30 / -10 / -1m
uv run featherstorm replay speed <x>
uv run featherstorm replay follow <riot_id_game_name>
uv run featherstorm replay record start [out] [--start T] [--end T | -d/--duration D] [--wait] | record stop | record toggle [out] | record status
uv run featherstorm crawler crawl [--count N] [--days N | --since YYYY-MM-DD --until YYYY-MM-DD | --all-time]
                                  [--queue ...] [--match-type ...] [--max-depth N] [--reset]
uv run featherstorm crawler fetch [--count N] [--max-depth N] [--workers N]
                                  # downloads + stores the full payload for crawled match IDs
uv run featherstorm crawler dataset [--table played|game] [--format jsonl|csv] [--out PATH]
                                    [--queue 420] [--patch 16.17] [--limit N]
uv run featherstorm crawler stats
uv run featherstorm crawler export [--out PATH] [--limit N] [--state expanded]
uv run featherstorm crawler schema [--show]
uv run featherstorm crawler reset [--force]
uv run featherstorm dragon item <item_id>
uv run featherstorm dragon champion <champion_id>
uv run featherstorm dragon art <champion_name> [--skin N] [--asset-type splash|...] [--output-path P]
```

Desktop UI:
```bash
uv sync --extra ui
uv run bladecaller
```

Crawler database:
```bash
docker compose up -d
```

League must run for Live Client API (`https://127.0.0.1:2999`) to be reachable. App waits + reconnects automatically — no manual restart between games.

## Config System

TOML config at OS app dir, auto-created on first run. Full key reference + CLI: [docs/config.md](docs/config.md).

## Architecture

Data flow diagrams, key classes, team→effect mapping, and how-to guides for adding lighting effects or event handlers: [docs/architecture.md](docs/architecture.md).

## Rendering Layer

Terminal UI rules for `src/league/ui/`: [docs/rendering.md](docs/rendering.md).

## Bladecaller UI

PySide6 desktop app (`bladecaller` gui-script, optional `ui` extra). Style is token-driven: colors/fonts/radii live in `src/league/bladecaller/resources/theme.py`, substituted into the `app.qss` template at load.

Qt and asyncio share one loop via `qasync`, so controllers `await` the async backend directly with no threading. `ClientStatusController` (`bladecaller/controllers/client_status.py`) polls the LCU gameflow phase and drives the sidebar status dot.

Pages: **Dashboard** (Recent Matches card) and **Match History** (paged, filterable list; rows expand to stat tiles, a 10-player scoreboard and build order), plus Settings. `MatchHistoryController` (`bladecaller/controllers/match_history.py`) feeds both — the list comes from the LCU (no API key), and expanding a row fetches the full lobby from Riot MATCH-V5, degrading to LCU-only stats when `RIOT_API_KEY` is unset.

**Working on the UI? Read [src/league/bladecaller/CLAUDE.md](src/league/bladecaller/CLAUDE.md)** — style system, selector table, `components.py` API, adding-a-page recipe, quirks.

## LCU Client

`LCUClient` talks to League client UI API via local lockfile. Full method list + CLI: [docs/lcu.md](docs/lcu.md).

## Replays

`ReplayManager` (`league.replay`) owns all replay interaction: LCU `/lol-replays` metadata/download/launch plus the in-game Replay API via `ReplayAPIClient`. `HighlightManager` builds on it. Details + CLI: [docs/replay.md](docs/replay.md).

## Govee Integration

`govee` package (`../govee`, sibling on disk) controls Govee smart lights over LAN UDP — no cloud, no API key. Details: [docs/govee.md](docs/govee.md).

## Riot API (riot_api.py)

`RiotAPIClient` — reads `RIOT_API_KEY` from `.env`. MATCH-V5, ranked, spectator methods + external API table: [docs/riot-api.md](docs/riot-api.md).

## Known Quirks

Gotchas and workarounds accumulated across the app — hardcoded paths, sibling-package deps, API oddities, SurrealDB behavior. **Read [docs/quirks.md](docs/quirks.md) before debugging anything that looks weird.**
