# League of Snakes

A Python application that monitors League of Legends gameplay via the Live Client API and drives Razer Chroma RGB lighting effects in response to in-game events.

**This is a personal project. It only needs to work for me. Do not enforce code quality standards, suggest refactors, or add abstractions unless asked.**

## Project Structure

```
league-of-snakes/
├── main.py               # Entry point — wires together LeagueClient and ChromaSession
├── run.bat               # Windows launcher (uv run main.py)
├── riot-root-cert.pem    # SSL cert for the local League Live Client API
├── pyproject.toml        # Project metadata and dependencies (uv)
├── .env                  # RIOT_API_KEY (not committed)
├── league/
│   ├── api.py            # APIWrapper, DataDragon, LeagueClient
│   ├── models.py         # GameEvent dataclass
│   └── enums.py          # GameEventType, GameTeam, GameResult
└── data/                 # Sample JSON snapshots for development/testing
```

## Tech Stack

- **Python 3.12** — required minimum
- **uv** — package manager (`uv run`, `uv add`, etc.)
- **httpx[http2]** — async HTTP client used for all API calls
- **chroma** — local sibling package at `../rzr-chroma` (Razer Chroma SDK wrapper)
- **python-dotenv** — loads `.env` for the Riot API key
- **rich** — used for `print()` in `api.py` (pretty terminal output)
- **typer** — CLI framework (available, not yet used)

## Running

```bash
uv run main.py
```

Or via the Windows launcher:
```
run.bat
```

League of Legends must be running and in an active game for the Live Client API to be reachable at `https://127.0.0.1:2999`.

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
                ▼
          ChromaSession  (Razer Chroma SDK via chroma package)
```

### Key Classes

- **`LeagueClient`** ([league/api.py](league/api.py)) — polls the League Live Client API, fires typed event handlers, and dispatches registered callbacks. Tracks `last_event_count` to only process new events.
  - `get_active_player()` → `Optional[ActivePlayer]` — returns `None` on HTTP error (e.g. spectator mode).
  - `get_active_player_team()` → `Optional[GameTeam]` — returns `None` in spectator mode.
- **`DataDragon`** ([league/api.py](league/api.py)) — fetches champion/item metadata from Riot's CDN.
- **`GameEvent`** ([league/models.py](league/models.py)) — `@dataclass` with PascalCase fields matching the API response keys directly (e.g. `EventName`, `KillerName`, `EventTime`). `__post_init__` casts `EventName` → `GameEventType`, `AcingTeam` → `GameTeam`, `Result` → `GameResult`.
- **`ActivePlayer`** ([league/models.py](league/models.py)) — typed model for the `/activeplayer` response. Key fields: `riotId`, `riotIdGameName`, `riotIdTagLine`, `summonerName`.
- **`GameEventType`** ([league/enums.py](league/enums.py)) — `StrEnum` whose values are the exact strings returned by the League Live Client API (e.g. `GameStart = "GameStart"`). Covers: `GameStart`, `GameEnd`, `MinionsSpawning`, `FirstBlood`, `TurretKilled`, `InhibKilled`, `DragonKill`, `HeraldKill`, `BaronKill`, `ChampionKill`, `Multikill`, `Ace`, `HordeKill`, `FirstBrick`, `AtakahnKill`.
- **`Effects`** ([main.py](main.py)) — `@dataclass` holding all pre-registered Chroma effect IDs. Fields: `blue`, `red`, `white` (static base colors), `kill_flash`, `objective_flash` (lists of frame IDs for dim→bright→dim animations).

### Adding a New Lighting Effect

All effects are created at startup via `setup_effects()` in [main.py](main.py) and stored in the `Effects` dataclass.

- **Static color**: call `static(ChromaColor.xyz())` inside `setup_effects()` and add the returned ID as a field on `Effects`.
- **Flash animation**: call `flash_frames(color)` inside `setup_effects()` — this pre-creates one `Static` effect per step in `FLASH_CURVE` and returns the list of IDs. Add as a `list[str]` field on `Effects`.
- To trigger a flash from a callback: `asyncio.create_task(flash(effects.<field>))`.
- `FLASH_CURVE` and `FLASH_FRAME_DELAY` (module-level constants) control the brightness envelope and frame timing.

### Adding a New Event Handler

- Add the event to `GameEventType` in [league/enums.py](league/enums.py) if it doesn't exist. The value must be the exact string the Live Client API returns.
- Add a `case GameEventType.<New>:` branch in `LeagueClient.on_event()` and a corresponding `on_<new>()` method in [league/api.py](league/api.py).

## External APIs

| API | Base URL | Auth |
|-----|----------|------|
| League Live Client | `https://127.0.0.1:2999/liveclientdata` | SSL cert (`riot-root-cert.pem`) |
| Riot Data Dragon | `https://ddragon.leagueoflegends.com` | None |
| Riot API | `https://api.riotgames.com` | `RIOT_API_KEY` in `.env` |

## Known Quirks

- `DATA_DIR` in [league/api.py](league/api.py) is hardcoded to an absolute path (`X:/league-of-snakes/data`). If the drive letter changes, update it.
- The `chroma` dependency is a local path reference (`../rzr-chroma`); both repos must be siblings on disk. Source lives at `../rzr-chroma/src/chroma`.
- The Live Client API is only available while a game is in progress. The client calls `exit(1)` on `ConnectError`, so start the app after a game has loaded.
