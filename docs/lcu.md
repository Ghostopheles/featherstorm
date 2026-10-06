# LCU Client

`src/league/lcu/lcu.py` — `LCUClient` talks to League client UI API via local lockfile.
- League client must be running (not just in-game)
- Reads `<client_install_path>/lockfile` for port + password (Basic auth, username `riot`)
- `LCUClient(client_install_path: Path)` — path defaults to `config.get("client_install_path", "lcu")`; falls back to hardcoded `F:/Games/League of Legends/lockfile` if lockfile missing
- Key methods: `get_locked_champion()`, `get_hovered_champion()`, `create_game_lobby()`, `create_custom_game_lobby()`, `create_normal_game_lobby()` (non-functional), `get_current_summoner()`, `get_lobby()`, `get_match_history()`, `get_match()`, `get_match_timeline()`, inventory methods, gameflow methods (`get_gameflow_phase()`, `get_gameflow_availability()`, `get_gameflow_session()`)
- Replay endpoints (`/lol-replays/...`) live in `ReplayManager` — see [replay.md](replay.md)
- Websocket: `client.ws` is an `LCUWebsocketClient`; `start_websocket()` / `close_websocket()` (also via `async with`). See `LCUGameFlow` (in [architecture.md](architecture.md)) for the high-level event wrapper.

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

See [quirks.md](quirks.md) for LCU websocket event-naming and gotchas.
