# Featherstorm

A personal playground for experimenting with the League of Legends APIs. This project has no specific end-goal — it's a sandbox for poking at the Live Client API, the LCU (League Client Update) API, the Riot Games API, and Data Dragon, and wiring them up to whatever seems fun (currently: RGB lighting and automatic highlight capture).

**This is a personal project built to work on my machine.** Expect hardcoded paths, missing error handling, and half-finished features.

## What It Does

- **Companion mode** — monitors a live game via the Live Client API and drives RGB lighting from in-game events. Razer Chroma devices flash on kills, turret takedowns, and objectives (colored by team); Govee smart lights set the room to your team color over LAN.
- **Highlight capture** — pulls recent match timelines from the Riot API, finds highlight-worthy moments using composable predicate rules, downloads the replay through the League client, and records clips of those moments.
- **Riot API CLI** — look up recent matches, match details, match timelines, and ranked stats from the terminal.
- **LCU tools** — talk to the running League client: read champ select state (locked/hovered champion), create lobbies.
- **Data Dragon lookups** — fetch champion and item metadata from Riot's CDN.

## Requirements

- Windows (Chroma SDK, League client paths)
- Python 3.14+ and [uv](https://docs.astral.sh/uv/)
- Two sibling repos on disk (local path dependencies):
  - `../rzr-chroma` — Razer Chroma SDK wrapper
  - `../govee` — Govee LAN UDP controller
- A `RIOT_API_KEY` in `.env` (only needed for the `riot` and `highlights` commands)
- Razer Chroma-capable hardware and/or Govee smart lights for the lighting features

## Usage

The CLI is the primary entry point:

```bash
# Lighting companion — waits for a game, reconnects between games automatically
uv run featherstorm companion

# Riot API
uv run featherstorm riot matches ["Name"] ["TAG"] [--count N] [--match-type ranked|normal|tourney|tutorial]
uv run featherstorm riot match <match_id>
uv run featherstorm riot timeline <match_id>

# Highlight capture
uv run featherstorm highlights capture [--game-path P] [--export-path P] [--name N] [--tagline T] [--count N]

# LCU (League client must be running)
uv run featherstorm lcu champ-select locked
uv run featherstorm lcu champ-select hovered
uv run featherstorm lcu lobby get

# Data Dragon
uv run featherstorm dragon item <item_id>
```

League itself must be running for the Live Client API (`https://127.0.0.1:2999`) to be reachable — companion mode waits and reconnects on its own.

## Configuration

Config lives in a TOML file in the OS app directory (`featherstorm`), auto-created with defaults on first run. Manage it via the CLI:

```bash
uv run featherstorm cfg view [category]
uv run featherstorm cfg get <category> <key>
uv run featherstorm cfg set <category> <key> <value>
uv run featherstorm cfg clear <category> <key>
uv run featherstorm cfg reset [--force]
```

Notable keys:

- `companion.govee_enabled` — toggle Govee lights (default `false`)
- `companion.default_player_name` / `companion.default_player_tagline` — fallback identity for Riot API commands
- `lcu.client_install_path` — League install dir (for the LCU lockfile)
- `highlights.export_path` — where highlight clips are saved
- `highlights.export_*` — FFmpeg encoding settings (quality, preset, fps, audio)

## How It Works

Companion mode polls the Live Client API event stream every 250ms. A `MatchWatcher` handles the session lifecycle (waiting for a game, polling, reconnecting after disconnects), builds typed `GameEvent`s, and dispatches them to registered callbacks — lighting effects for Chroma/Govee and a kill-feed printed to the console.

Highlight detection analyzes Riot API match timelines with a composable `Predicate` rule system (`&`/`|`/`~` operators), then drives the League replay client to record the matching time ranges.

See [CLAUDE.md](CLAUDE.md) for the full architecture breakdown and module map.

## External APIs

| API | Base URL | Auth |
|-----|----------|------|
| League Live Client | `https://127.0.0.1:2999/liveclientdata` | None |
| LCU | lockfile port on `127.0.0.1` | Basic auth from lockfile |
| Riot API | `https://api.riotgames.com` | `RIOT_API_KEY` in `.env` |
| Riot Data Dragon | `https://ddragon.leagueoflegends.com` | None |
| Govee LAN | UDP `device_ip:4003` | None |
