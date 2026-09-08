# Config System

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
- `crawler.db_url` (default `http://localhost:16800`), `crawler.namespace` (`featherstorm`), `crawler.database` (`crawler`), `crawler.username` / `crawler.password` (`root`/`root`) — SurrealDB connection
- `crawler.default_window_days` (default `14`) — time window when `--days`/`--since`/`--all-time` are not passed
- `crawler.history_page_size` (default `100`, the MATCH-V5 max), `crawler.summoner_workers` (default `8`), `crawler.match_workers` (default `4`), `crawler.claim_batch` (default `8`), `crawler.frontier_low_water` (default `32`)
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
