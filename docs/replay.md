# Replays

`src/league/replay/` — everything that touches match replays. Two halves, two transports:

| Class | Talks to | Needs |
|---|---|---|
| `ReplayManager` ([manager.py](../src/league/replay/manager.py)) | LCU `/lol-replays/...` (via `LCUClient`) | League client running |
| `ReplayAPIClient` ([api.py](../src/league/replay/api.py)) | Replay API `https://127.0.0.1:2999/replay` | A replay open in the game client |

## ReplayManager

`ReplayManager(client_install_path, lcu=None, reporter=None)` — builds its own `LCUClient` unless one is passed; `.api` is a `ReplayAPIClient`. Usable as `async with` (closes both HTTP clients).

- `resolve_match_id(match_id=None)` — `None` → last LCU match; strings go through `normalize_match_id()` (`"NA1_123"` → `123`, the LCU doesn't use platform prefixes). All methods accept prefixed or bare IDs.
- `get_metadata(id)` / `create_metadata(id)` / `get_state(id) -> LCUReplayState | None`
- `download(id) -> LCUReplayDownloadStatus` — creates metadata if missing, starts a graceful download, polls up to 10× (1s). Raises `LCUIncompatibleReplayException` on `incompatible` / `unsupported` / `missingOrExpired`.
- `open(id)` — creates metadata/downloads as needed, then `/watch`. Raises `LCUMissingReplayMetadataException` when the LCU won't create metadata.
- `open_and_wait(id)` — `open()` + `api.wait_until_ready()`.
- `close_active()` — SIGTERMs the replay process (PID from `/replay/game`).

## ReplayAPIClient

Unlike `BaseAPIClient`, requests **raise** (`raise_for_status`, `httpx.ConnectError`) — the `wait_*` pollers depend on it. No replay running → `httpx.ConnectError`.

- Playback: `get_playback()`, `update_playback(**kw)`, `pause()`, `resume()`, `toggle_playback() -> paused`, `set_speed(x)`, `seek_to(t, buffer=0)` (pauses at 1× speed), `seek_by(offset) -> target` (relative, clamped to `[0, length]`)
- Render/camera: `get_render()`, `update_render(**kw)`, `move_camera_to(x, y, fov)`, `follow_player(name, offset)`, `hide_ui()` (`HIDDEN_UI_SETTINGS`)
- Recording: `get_recording()`, `start_recording(path, start, end, ...)`, `stop_recording()`, `toggle_recording(path=None, **kw) -> (started, state)` (starts current time → end of game, resumes playback)
- `apply_sequence(seq)` — see `ReplaySequenceEasing` in `league.enums`
- `get_game()` / `get_pid()`
- Waiters: `wait_for(func, timeout=60)` (`timeout=None` waits forever), `wait_until_ready()`, `wait_for_seek()`, `wait_for_recording()`

## CLI

```bash
uv run featherstorm replay status [match_id]          # LCU replay state + metadata
uv run featherstorm replay download [match_id]
uv run featherstorm replay open [match_id] [--no-wait]
uv run featherstorm replay playback                   # current playback state
uv run featherstorm replay pause
uv run featherstorm replay resume
uv run featherstorm replay toggle                     # pause if playing, resume if paused
uv run featherstorm replay seek <time>               # keeps prior paused/playing state; +30 / -10 / -1m seek relative
uv run featherstorm replay speed <x>
uv run featherstorm replay hide-ui
uv run featherstorm replay follow <riot_id_game_name>
uv run featherstorm replay render                     # current render settings
uv run featherstorm replay record start [out] [--start T] [--end T | -d/--duration D] [--width W] [--height H] [--fps N]
                                    [--codec webm] [--lossless/--lossy] [--wait]
uv run featherstorm replay record stop
uv run featherstorm replay record toggle [out] [--width W] [--height H] [--fps N] [--codec webm] [--lossless/--lossy]
uv run featherstorm replay record status
```

`record start` writes to the game client's default replay directory when `out` is omitted, defaults to the current replay time → end of game, seeks when `--start` is given, and resumes playback (the Replay API only captures frames while playing). `--duration` records that long from the start time (clamped to game length; exclusive with `--end`). Times accept `90`, `1:30`, `1:02:03`, `30s`, `2m`, `1m30s`. `--wait` blocks until done; Ctrl+C stops the recording. `record toggle` stops an active recording, otherwise starts one like `record start` with no time options.

`match_id` defaults to your last LCU match. All commands take `--client-install-path`. Replay API commands exit with "No replay running" when nothing is open.
