# League of Snakes

A Python application that monitors League of Legends gameplay via the Live Client API and drives RGB lighting effects on both Razer Chroma peripherals and Govee smart lights in response to in-game events.

**This is a personal project. It only needs to work for me. Do not enforce code quality standards, suggest refactors, or add abstractions unless asked.**

## Project Structure

```
league-of-snakes/
├── main.py               # Legacy entry point (direct run, always enables Govee)
├── lcu_main.py           # Scratch script: LCU lobby creation test
├── riot_main.py          # Scratch script: Riot API test
├── log_config.yaml       # Python logging configuration (queue handler, file + console)
├── run.bat               # Windows launcher (uv run main.py)
├── riotgames.pem         # SSL cert (no longer used — LeagueClient uses verify=False)
├── pyproject.toml        # Project metadata and dependencies (uv)
├── .env                  # RIOT_API_KEY (not committed)
├── logs/                 # Log output directory (created at runtime)
├── src/league/
│   ├── api.py            # LeagueClient (Live Client API poller)
│   ├── models.py         # GameEvent, ActivePlayer, Player, AllGameData, Match, PlayerMatch
│   ├── enums.py          # GameEventType, GameTeam, GameResult, QueueType
│   ├── http.py           # BaseAPIClient (shared base for all API clients)
│   ├── config.py         # TOML config (stored at OS app dir via typer.get_app_dir)
│   ├── constants.py      # Shared constants
│   ├── dragon.py         # CommunityDataDragon (champion/item metadata)
│   ├── riot_api.py       # RiotAPIClient (PUUID, matches, summoner, champion mastery)
│   ├── cli.py            # Typer CLI app — primary entry point (featherstorm)
│   └── lcu/
│       ├── lcu.py        # LCUClient (reads lockfile, champ-select, lobby creation)
│       └── models.py     # MyChampSelection, Summoner, LobbyGameMode, LobbyType
├── data/                 # Sample JSON snapshots for development/testing
└── ref/                  # Reference JSON snapshots
```

## Tech Stack

- **Python 3.12** — required minimum
- **uv** — package manager (`uv run`, `uv add`, etc.)
- **httpx[http2]** — async HTTP client used for all API calls
- **chroma** — local sibling package at `../rzr-chroma` (Razer Chroma SDK wrapper)
- **govee** — local sibling package at `../govee` (Govee LAN UDP controller)
- **pyyaml** — loads `log_config.yaml` for logging configuration
- **python-dotenv** — loads `.env` for the Riot API key
- **pydantic** — used for `Match`, `PlayerMatch` models in `models.py`
- **toml** — reads/writes `config.py` TOML file
- **rich** — used for `print()` in `api.py` (pretty terminal output)
- **typer** — CLI framework (`featherstorm` CLI entry point)

## Running

Primary (CLI, recommended):
```bash
uv run featherstorm companion          # with Govee (default)
uv run featherstorm companion --no-govee
uv run featherstorm riot matches "Name" "TAG" [--count N] [--match-type ranked|normal|tourney|tutorial]
uv run featherstorm riot match <match_id>
uv run featherstorm riot timeline <match_id>
```

Legacy (direct, always enables Govee):
```bash
uv run main.py
```

League must be running for the Live Client API (`https://127.0.0.1:2999`) to be reachable. The app waits and reconnects automatically — no manual restart needed between games.

## Config System

`src/league/config.py` stores a TOML config at `typer.get_app_dir("featherstorm")` (OS app dir). Created automatically on first run with defaults.

Categories and keys:
- `lcu.client_install_path` — path to League install dir (for LCU lockfile)
- `govee.default_power_state`, `govee.default_brightness`, `govee.request_timeout`
- `chroma.teammate_dim_factor` (default `0.4`)
- `companion.default_player_name` — fallback name when not in active game

Manage via CLI:
```bash
uv run featherstorm lcu cfg view
uv run featherstorm lcu cfg set <key> <value> [--category <cat>]
uv run featherstorm lcu cfg reset [--force]
```

## Architecture

### Data Flow

```
League Live Client API (127.0.0.1:2999)
        │
        ▼
  LeagueClient.poll_events()   ← called every 250ms
        │
        ▼
  LeagueClient.on_event()      ← dispatches to typed handlers + registered callbacks
        │
        ├── on_game_start / on_champion_kill / on_dragon_killed / ...
        │
        └── try_fire_callbacks_for_event()  ← user-registered async/sync callbacks
                │
                ├── ChromaSession  (Razer Chroma SDK via chroma package)
                │
                └── GoveeConnectionListener  (Govee LAN UDP via govee package)
```

### Key Classes

- **`LeagueClient`** ([league/api.py](league/api.py)) — polls the League Live Client API, fires typed event handlers, and dispatches registered callbacks. Tracks `last_event_count` to only process new events.
  - `get_active_player()` → `Optional[ActivePlayer]` — returns `None` on HTTP error or spectator mode (API returns `{"error": "..."}` with 200 status in spectator).
  - `get_active_player_team()` → `Optional[GameTeam]` — returns `None` in spectator mode.
  - `get_all_game_data()` → `AllGameData` — full snapshot; `allPlayers` always populated, `activePlayer` is `None` in spectator mode.
- **`DataDragon`** ([league/api.py](league/api.py)) — fetches champion/item metadata from Riot's CDN.
- **`GameEvent`** ([league/models.py](league/models.py)) — `@dataclass` with PascalCase fields matching the API response keys directly (e.g. `EventName`, `KillerName`, `EventTime: float`). `__post_init__` casts `EventName` → `GameEventType`, `AcingTeam` → `GameTeam`, `Result` → `GameResult`.
- **`ActivePlayer`** ([league/models.py](league/models.py)) — typed model for the `/activeplayer` response. Key fields: `riotId`, `riotIdGameName`, `riotIdTagLine`, `summonerName`. `fullRunes` is `Optional[FullRunes]` — empty in some game modes.
- **`Player`** ([league/models.py](league/models.py)) — model for each entry in `allPlayers`. Key fields: `riotIdGameName`, `team: GameTeam`. `runes` is `Optional[PlayerRunes]` — empty list in some game modes. `screenPositionBottom`/`screenPositionCenter` are `Optional[str]` comma-separated coordinates, only present in spectator mode (`FLT_MAX` sentinel when player not visible).
- **`GameEventType`** ([league/enums.py](league/enums.py)) — `StrEnum` whose values are the exact strings returned by the League Live Client API (e.g. `GameStart = "GameStart"`). Covers: `GameStart`, `GameEnd`, `MinionsSpawning`, `FirstBlood`, `TurretKilled`, `InhibKilled`, `DragonKill`, `HeraldKill`, `BaronKill`, `ChampionKill`, `Multikill`, `Ace`, `HordeKill`, `FirstBrick`, `AtakahnKill`.
- **`Effects`** ([main.py](main.py)) — `@dataclass` holding Chroma effect state. Fields: `blue`, `red`, `white` (static base effect IDs), plus flash animation fields (`kill_flash`, `teammate_kill_flash`, `objective_flash`, `turret_flash`, `teammate_turret_flash`, `first_brick_flash`) — each a `dict[Optional[GameTeam], ChromaAnimation]` keyed by team so the animation fades back to the correct base color.
- **`GoveeConnectionListener`** ([govee package](../govee/src/govee/govee.py)) — discovers and manages Govee smart lights over LAN UDP. `listener.devices: dict[str, GoveeDevice]` holds discovered devices by IP. Started before the Chroma session; `GOVEE_REQUEST_TIMEOUT` (0.5s) is awaited after start to let discovery run.

### Team → Effect Mapping

Two lookup dicts in `amain()` map `GameTeam` → effect, avoiding if/elif chains:

```python
team_to_chroma_effect = {
    GameTeam.ORDER:    effects.blue,
    GameTeam.CHAOS:    effects.red,
    GameTeam.SPECTATOR: effects.white,
}
team_to_govee_color = {
    GameTeam.ORDER:    GoveeColor.blue(),
    GameTeam.CHAOS:    GoveeColor.red(),
    GameTeam.SPECTATOR: GoveeColor.white(),
}
```

### Adding a New Lighting Effect

All Chroma effects are created at startup via `setup_effects()` in [main.py](main.py) and stored in the `Effects` dataclass.

- **Static color** (base): call `static(ChromaColor.xyz())` inside `setup_effects()` and add the returned ID as a `str` field on `Effects`.
- **Flash animation**: call `make_flash(ChromaColor.xyz())` — this uses `ChromaAnimation.flash_fade()` to build a `dict[Optional[GameTeam], ChromaAnimation]` with one animation variant per base color (ORDER/CHAOS/spectator). Add as a `dict` field on `Effects`.
  - Optionally pass `steps`, `flash_duration`, `total_fade_duration` to tune the animation (e.g. `first_brick_flash` uses `steps=5, total_fade_duration=0.5` for a short flash).
  - Dim teammate effects by passing `scale_color(ChromaColor.xyz(), TEAMMATE_DIM_FACTOR)` as the color.
- To trigger a flash from a callback: `asyncio.create_task(chroma.play_animation(effects.<field>[active_player_team], device))`.
- `play_animation()` pre-uploads all frames to the Chroma SDK, then steps through them with the baked-in timing. The animation fades back to the team base color automatically — no manual restore needed.
- To also update Govee lights in a callback, iterate `govee_listener.devices.values()` and call the appropriate `set_*` methods. Govee has no animation support — only instant color/brightness/power changes.

### Adding a New Event Handler

- Add the event to `GameEventType` in [league/enums.py](league/enums.py) if it doesn't exist. The value must be the exact string the Live Client API returns.
- Add a `case GameEventType.<New>:` branch in `LeagueClient.on_event()` and a corresponding `on_<new>()` method in [league/api.py](league/api.py).

## LCU Client

`src/league/lcu/lcu.py` — `LCUClient` talks to the League client UI API via the local lockfile.
- Requires League client to be running (not just in-game)
- Reads `<client_install_path>/lockfile` for port + password (Basic auth, username `riot`)
- `LCUClient(client_install_path: Path)` — path defaults to `config.get("client_install_path", "lcu")`
- Key methods: `get_locked_champion()`, `get_hovered_champion()`, `create_game_lobby()`, `create_custom_game_lobby()`, `create_normal_game_lobby()` (non-functional), `get_current_summoner()`

CLI:
```bash
uv run featherstorm lcu champ-select locked
uv run featherstorm lcu champ-select hovered
uv run featherstorm lcu lobby get
```

## Govee Integration

The `govee` package (`../govee`, sibling on disk) controls Govee smart lights over LAN UDP — no cloud, no API key.

- **`GoveeConnectionListener`** — discovers devices via multicast broadcast (`239.255.255.250:4001`), listens on `4002`. Call `listener.start()` then `await asyncio.sleep(GOVEE_REQUEST_TIMEOUT)` before accessing `listener.devices`.
- **`GoveeDevice`** — per-device control. Key methods: `set_power_state(bool)`, `set_brightness(0–100)`, `set_color_and_temperature(GoveeColor, temp_kelvin=5000)`. All sends are fire-and-forget (retries 5× with 50ms gaps, no confirmation).
- **`GoveeColor`** — simple RGB dataclass with the same factory methods as `ChromaColor` (`.blue()`, `.red()`, `.white()`, `.gold()`, `.purple()`).
- Currently Govee is only updated on `GameStart` (sets team color). Flash events only drive Chroma.

## Riot API (riot_api.py)

`RiotAPIClient` — reads `RIOT_API_KEY` from `.env` (loaded via `python-dotenv`). Route logic in `get_region_for_url()`: `/riot/*` and `match/v5` → `americas`, `/lol/*` → `na1`.

MATCH-V5 methods:
- `get_match_ids(puuid, *, count, start, match_type, queue, start_time, end_time)` → `list[str]`
- `get_match(match_id)` → `Match`
- `get_match_timeline(match_id)` → `MatchTimeline`
- `get_recent_matches(puuid, count, match_type)` → `list[PlayerMatch]` (convenience wrapper)

> `developer.riotgames.com/apis` is the correct API reference but is a JS-heavy SPA — **WebFetch cannot render it**. Use **WebSearch** as a fallback (e.g. `"riot match-v5 API endpoints query parameters"`), or a headless browser tool (e.g. Playwright MCP) if available.

## External APIs

| API | Base URL | Auth |
|-----|----------|------|
| League Live Client | `https://127.0.0.1:2999/liveclientdata` | SSL cert (`riot-root-cert.pem`) |
| Riot Data Dragon | `https://ddragon.leagueoflegends.com` | None |
| Riot API | `https://api.riotgames.com` | `RIOT_API_KEY` in `.env` |
| Govee LAN | UDP `device_ip:4003` / broadcast `239.255.255.250:4001` | None |

## Known Quirks

- `DATA_DIR` in [league/api.py](league/api.py) is hardcoded to an absolute path (`X:/league-of-snakes/data`). If the drive letter changes, update it.
- The `chroma` dependency is a local path reference (`../rzr-chroma`); both repos must be siblings on disk. Source lives at `../rzr-chroma/src/chroma`.
- The `govee` dependency is a local path reference (`../govee`); it must also be a sibling on disk. Source lives at `../govee/src/govee`.
- The Live Client API is only available while a game is in progress. Both `main.py` and `cli.py` poll every 2s waiting for the API to become available, then switch to 250ms polling — no manual restart needed between games.
- `riot-root-cert.pem` was renamed to `riotgames.pem` but is no longer used — `LeagueClient` now uses `verify=False`.
- In spectator mode, `/activeplayer` returns `{"error": "..."}` with HTTP 200 (not a 4xx). Both `get_active_player()` and `AllGameData.__post_init__` guard against this, returning `None` for `activePlayer`.
- `Player.runes` and `ActivePlayer.fullRunes` can be an empty list `[]` in some game modes — both are typed `Optional` and guarded with a falsy check before construction.
- `FirstBrick` events can have `TurretKilled = None` in some game modes — `on_first_brick` guards before calling `Turret.from_str()`.
- Govee local IP auto-detection in `govee/shared.py` uses a socket to `8.8.8.8:80`. May fail on isolated networks — hardcode `LISTEN_ADDR` in `../govee/src/govee/shared.py` if needed.
- Govee discovery is periodic (every 180s); allow 0.5–2s after `listener.start()` before accessing `listener.devices`. New devices on the network may take up to 3 minutes to appear.
- Govee sends are fire-and-forget — no confirmation that the device received the command.
