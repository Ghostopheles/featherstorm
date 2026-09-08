# Architecture

### Data Flow

```
League Live Client API (127.0.0.1:2999)
        │
        ▼
  MatchWatcher.run()           ← session lifecycle loop (watcher.py), owned by the bridge
        │
        ├── _wait_for_session()   ← polls LeagueClientStatus until CONNECTED or timeout
        │
        └── _poll_session()       ← calls LeagueClient.poll_events() every 250ms
                │
                ▼
        LeagueClient.on_event()  ← builds GameEvent, appends history, fires callbacks (api.py)
                │
                ▼
LeagueEventBridge (bridge.py)   ← single event hub, in-game + out-of-game
        │
        ├── companion callbacks registered via bridge.on(LeagueEvent.X, ...) (companion.py)
        │      ├── lighting (on_game_start / on_champion_kill / ...)
        │      ├── console kill-feed (register_event_feed)
        │      └── Discord presence (init_match on GameStart, end_match on GameEnd,
        │                            lobby states via register_presence_lobby_events)
        │
        ├── ChromaSession  (Razer Chroma SDK via chroma package)
        │
        └── GoveeConnectionListener  (Govee LAN UDP, if govee_enabled)

LCU websocket (wss://localhost:<port>, lockfile auth) — started by LeagueEventBridge.run()
        │
        ├── /lol-lobby/v2/lobby          → LeagueEvent.LobbyCreated/Updated/Deleted
        └── /lol-gameflow/v1/gameflow-phase → LeagueEvent.PhaseChanged

LeagueRichPresence (discord/league_presence.py, if enable_rich_presence)
        ├── borrows the bridge's LCUClient for lobby/phase reads (no second client)
        ├── lobby/queue/in-game activity states
        └── 15s update loop: KDA/CS state line while in game
```

### Crawler Data Flow

Separate from the companion pipeline — offline, Riot Web API only, no League client needed.

```
seed Riot ID ──> get_puuid ──> summoner frontier (SurrealDB)
                                      │
        ┌─────────────────────────────┴──────────────────────────────┐
        ▼                                                            ▼
 summoner workers (x8)                                    match workers (x4, gated)
 claim_summoners()                                        claim_matches()
   └─ MATCH-V5 by-puuid/ids (windowed)                      └─ MATCH-V5 matches/{id}
        ~20 ids per call at 14 days                              metadata.participants → 10 puuids
   └─ complete_summoner() ──> match frontier              └─ store_match() ──> summoner frontier
                                                                              + game / played rows

stop when total matches >= target, or both frontiers empty (CrawlerExhausted)
```

The crawl only downloads the fraction of matches it needs to keep the summoner frontier fed, so most
discovered IDs never get a payload. `crawler fetch` walks a **second, independent frontier** over the
same `match` rows to close that gap:

```
match rows (fetch_state: pending ──> claimed ──> stored | failed)
        │
        ▼  fetch workers (x8)
 claim_unfetched()
   └─ MATCH-V5 matches/{id}
        └─ store_match() ──┬─> game:<match_id>            (one row per match)
                           ├─> played edges               (summoner -> played -> game, one per participant)
                           └─> summoner rows              (Riot ID + level, and BFS discovery for free)
```

`store_match()` settles both axes at once, so a match expanded by the crawl is already stored — the two
passes never pay for the same payload twice.

### Dataset Tables

`summoner` / `match` stay thin because every claim query rescans them; the analytical rows live apart.

| Table | Record id | Holds |
| --- | --- | --- |
| `game` | match id | match-level facts — queue, `patch` (`16.17`, not the four-part `gameVersion`), duration, timestamps, winner, per-team bans/objectives |
| `played` | `<match id>_<participantId>` | one player-game: ~131 typed columns generated from `ParticipantSummary`, plus `perks` / `challenges` as `FLEXIBLE` objects |

`played` is a real graph relation (`DEFINE TABLE played TYPE RELATION IN summoner OUT game`), which puts
both queries this dataset exists for one hop away — every game a summoner played, and everyone they have
shared a game with:

```surql
SELECT VALUE ->played->game FROM summoner:<puuid>;
SELECT VALUE ->played->game<-played<-summoner FROM summoner:<puuid>;
```

It is still a flat table, so `SELECT * FROM played` (or `crawler dataset`) hands a dataframe library one
row per player-game. Column names are snake_case — `totalDamageDealtToChampions` becomes
`total_damage_dealt_to_champions`, with `championName`/`teamPosition` shortened to `champion`/`position`.
The column list is **generated from the pydantic model**, not written by hand, so adding a field to
`ParticipantSummary` adds the column; `featherstorm crawler schema --show` prints the resulting DDL.

Match workers only run when the summoner frontier is below `frontier_low_water`: a summoner expansion
yields many more IDs per request than a match expansion, so match fetches exist purely to refill the
summoner side. Widening the window makes each summoner fetch cheaper per ID; narrowing it makes the crawl
more request-hungry (a 14-day window returns ~20 IDs per summoner, not the full 100-ID page).

### Key Classes

- **`LeagueClient`** ([league/api.py](../src/league/api.py)) — polls League Live Client API; `on_event()` builds a `GameEvent`, appends to `_history`, and dispatches to callbacks registered via `on(event_type, cb)`. No built-in per-event handlers (lighting + console feed live in companion). Tracks `last_event_count` for new events only — **`reset()` (clears `last_event_count` and `_history`) must be called at the start of every session**, or the next match dispatches nothing until its event count passes the previous one's.
  - `get_active_player()` → `Optional[ActivePlayer]` — returns `None` on HTTP error or spectator mode (API returns `{"error": "..."}` with 200 status in spectator).
  - `get_active_player_team()` → `Optional[GameTeam]` — returns `None` in spectator mode.
  - `get_all_game_data()` → `AllGameData` — full snapshot; `allPlayers` always populated, `activePlayer` is `None` in spectator mode.
- **`DataDragon`** ([league/api.py](../src/league/api.py)) — fetches champion/item metadata from Riot CDN.
- **`DragonItem`** ([league/models.py](../src/league/models.py)) — constructed via `**data` unpacking from CDN JSON; every field in API response needs matching dataclass field or `get_item()` raises `TypeError`. Two keys remapped: `"from"` → `builds_from`, `"into"` → `builds_into` (popped before unpacking in `dragon.py`).
- **`GameEvent`** ([league/models.py](../src/league/models.py)) — `@dataclass` with PascalCase fields matching API response keys directly (e.g. `EventName`, `KillerName`, `EventTime: float`). `__post_init__` casts `EventName` → `GameEventType`, `AcingTeam` → `GameTeam`, `Result` → `GameResult` via `try_cast_to_enum` — an unrecognised value stays a raw string instead of raising. **Build with `GameEvent.from_dict(raw)`, not `GameEvent(**raw)`** — it filters unmodelled keys (keeping them as plain attributes) so a new API field can't `TypeError` the poll loop.
- **`ActivePlayer`** ([league/models.py](../src/league/models.py)) — typed model for `/activeplayer` response. Key fields: `riotId`, `riotIdGameName`, `riotIdTagLine`, `summonerName`. `fullRunes` is `Optional[FullRunes]` — empty in some game modes.
- **`Player`** ([league/models.py](../src/league/models.py)) — model for each entry in `allPlayers`. Key fields: `riotIdGameName`, `team: GameTeam`. `runes` is `Optional[PlayerRunes]` — empty list in some game modes. `screenPositionBottom`/`screenPositionCenter` are `Optional[str]` comma-separated coordinates, spectator mode only (`FLT_MAX` sentinel when player not visible).
- **`GameEventType`** ([league/enums/base.py](../src/league/enums/base.py)) — `StrEnum` with exact strings from League Live Client API (e.g. `GameStart = "GameStart"`). Covers: `GameStart`, `GameEnd`, `MinionsSpawning`, `FirstBlood`, `TurretKilled`, `InhibKilled`, `InhibRespawned`, `DragonKill`, `HeraldKill`, `BaronKill`, `ChampionKill`, `Multikill`, `Ace`, `HordeKill`, `FirstBrick`, `AtakahnKill`.
- **`LeagueClientStatus`** ([league/enums/base.py](../src/league/enums/base.py)) — `Enum`: `DISCONNECTED` (no API), `LOADING` (API up but no active game), `CONNECTED` (in game), `BANISHED` (connection dropped mid-session). Used by `MatchWatcher` to decide reconnect behavior.
- **`GamePlayerPosition`** ([league/enums/base.py](../src/league/enums/base.py)) — `StrEnum`: `TOP`, `JUNGLE`, `MIDDLE`, `BOTTOM`, `SUPPORT`.
- **`ReplaySequenceEasing`** ([league/enums/base.py](../src/league/enums/base.py)) — `StrEnum` with all easing types for the League replay API (linear, snap, smoothStep, quadratic/cubic/quartic/quintic/sine/circular/exponential/elastic/back/bounce ease in/out/in-out).
- **`Queue`** ([league/enums/queues.py](../src/league/enums/queues.py)) — `LookupEnum` of every League queue ID (blind, draft, ranked, ARAM, RGMs, bots…). Duplicate historic names suffixed `_2`/`_3` — live queue IDs are usually the highest suffix (e.g. `Q_5V5_ARAM_GAMES_3 = 450`, `Q_5V5_RANKED_SOLO_GAMES_2 = 420`). `QUEUE_DESCRIPTION` and `QUEUE_MAP` dicts map queue → display name / map name.
- **`LCUWebsocketClient`** ([league/lcu/socket.py](../src/league/lcu/socket.py)) — LCU WAMP websocket (`wss://localhost:<port>`, lockfile Basic auth, `verify` off). `on(endpoint, callback, event_type)` registers callbacks; endpoint paths converted to event names (`/lol-lobby/v2/lobby` → `OnJsonApiEvent_lol-lobby_v2_lobby`). Subscribes per registered event on connect (or firehose `OnJsonApiEvent` if none). Auto-reconnects via `websockets.connect` iterator. Callbacks must be registered **before** `connect()` — raises after.
- **`LCUGameFlow`** ([league/lcu/gameflow.py](../src/league/lcu/gameflow.py)) — high-level gameflow wrapper over `LCUClient` + its websocket. `add_callback(LCUGameFlowEvent.LobbyCreated|LobbyUpdated|LobbyDeleted, cb)`, `get_phase()` → `LCUGameflowPhase`, `start()` connects websocket.
- **`DiscordRichPresence`** ([league/discord/presence.py](../src/league/discord/presence.py)) — generic pypresence `AioPresence` wrapper. `DiscordActivity` dataclass holds full activity payload; `set_activity()` / `update_activity(**kwargs)` mutate local state, `update()` pushes to Discord.
- **`LeagueRichPresence`** ([league/discord/league_presence.py](../src/league/discord/league_presence.py)) — League-aware presence. Ctor `LeagueRichPresence(client_id, lcu_client=None)` — pass the bridge's `LCUClient` so presence shares it instead of opening a second one; with no client (and none constructible) `self.gameflow` is `None` and `init()` degrades to `init_empty()` instead of raising. Tracks `SessionStatus` (Empty/InLobby/InQueue/InGame). `init_lobby()` from LCU lobby data (queue description, party size), `init_match()` from `AllGameData` (champion + lane opponent, skin splash as large image, role icon as small image), 15s update loop pushes KDA/CS state. `try_update_queue_type()` resolves queue via Riot SPECTATOR-V5 live match.
- **`CurrentGameInfo`** ([league/models.py](../src/league/models.py)) — SPECTATOR-V5 active-game model (`gameQueueConfigId`, participants, bans).
- **`Effects`** ([league/companion.py](../src/league/companion.py)) — `@dataclass` holding Chroma effect state. Fields: `blue`, `red`, `white` (static base effect IDs), plus flash animation fields (`kill_flash`, `teammate_kill_flash`, `objective_flash`, `turret_flash`, `teammate_turret_flash`, `first_brick_flash`) — each `dict[Optional[GameTeam], ChromaAnimation]` keyed by team so animation fades back to correct base color. `base_for(team)` / `flash_for(name, team)` do the team lookup.
- **`ChromaLighting`** ([league/companion.py](../src/league/companion.py)) — async context manager owning the `ChromaSession`, device and `Effects`. `await set_team(team)` sets the base colour, `flash(name, team)` fires an animation. Constructed with `enabled=False` it enters cleanly and every method no-ops.
- **`GoveeLights`** ([league/companion.py](../src/league/companion.py)) — same shape for Govee: `__aenter__` discovers devices and applies config defaults, `set_team(team)` pushes a colour, `__aexit__` calls `listener.cleanup()`. No-ops when disabled.
- **`MatchWatcher`** ([league/watcher.py](../src/league/watcher.py)) — wraps `LeagueClient`, manages session lifecycle (connect → poll → disconnect → reconnect). Key methods: `watcher.on(event_type, callback)`, `@watcher.on_session_start`, `@watcher.on_session_end`, `await watcher.run()`. Config keys: `companion.max_reconnect_attempts`, `companion.wait_interval`, `companion.poll_interval`, `companion.session_timeout`. Uses `LeagueClientStatus` to decide reconnect vs clean exit. Ctor param `exit_on_timeout` (default `True`): when `False`, `run()` keeps waiting forever instead of exiting after `session_timeout` with no game (used by `LeagueEventBridge`). Ctor param `reporter` (default `NullReporter()`): drives the "waiting for client/match" spinner — `run_companion()` passes a `RichProgressReporter`.
- **`LeagueEventBridge`** ([league/bridge.py](../src/league/bridge.py)) — top-level unified event hub bridging in-game (Live Client API via `MatchWatcher`) and out-of-game (LCU websocket) events. **`run_companion()` is built on it.**
  - Register: `bridge.on(LeagueEvent.X, cb)` — decorator-or-direct, sync or async. `event` may also be an *iterable* of `LeagueEvent` to wire one callback to several. `bridge.on_game_events(iterable_of_GameEventType, cb)` is the same thing for callers holding `GameEventType` values (e.g. `FEED_EVENTS`). `LeagueEvent.for_game_event(t)` does the single conversion, returning `None` for an unmodelled type.
  - `LeagueEvent` StrEnum = all `GameEventType` members (payload `GameEvent`) + `LobbyCreated/Updated/Deleted` (payload `LCUWebsocketEvent`) + `PhaseChanged` (payload `LCUGameflowPhase`, via ws endpoint `/lol-gameflow/v1/gameflow-phase`) + `SessionStart`/`SessionEnd` (no args).
  - Ctor: `LeagueEventBridge(game_client=None, lcu_client=None, *, exit_on_timeout=False, reporter=None)`. `exit_on_timeout` and `reporter` pass straight to the internal `MatchWatcher` — `run_companion()` passes `exit_on_timeout=True` (exit after `companion.session_timeout` with no game) and a `RichProgressReporter` (the "waiting for client/match" spinner).
  - Registers internal fan-out dispatchers in `__init__` so user callbacks can be added after ws connect. `SessionStart` calls `game.reset()` before firing, so callers don't have to.
  - Exposes `bridge.game` (`LeagueClient`) and `bridge.lcu` (`LCUClient`, `None` when League client not running — out-of-game events disabled with warning).
  - Helpers: `get_phase()`, `get_lobby()`, `get_game_data()`, `get_active_player()`, `get_active_player_team()`, `is_in_game()`, `emit_current_phase()` (fires `PhaseChanged` for the phase the client is *already* in — the websocket only pushes transitions), `close()`.
  - Async callbacks are dispatched as tasks (tracked in `_tasks`, cancelled by `close()`) so a slow handler can't stall the poll loop — they run concurrently, not serialized; sync callbacks still run inline.
  - `close()` is idempotent, disconnects the websocket (the bridge always starts it in `run()`) and `aclose()`s the httpx clients — but only closes `bridge.lcu` when the bridge created it, so an *injected* client outlives the bridge. `run()` calls `close()` in a `finally`.
- **`CrawlerDatabase`** ([league/crawler/database.py](../src/league/crawler/database.py)) — SurrealDB store for the match crawler. Two tables driven by one state machine (`discovered → claimed → expanded | failed`): `summoner` (record id = puuid) and `match` (record id = match id). Async context manager; `connect()` signs in, selects ns/db and applies the schema idempotently (`DEFINE ... IF NOT EXISTS`).
  - Dedupe primitive: `add_summoners()` / `add_matches()` run `INSERT ... ON DUPLICATE KEY UPDATE seen_count += 1` and return **how many were new**. An already-`expanded` record keeps its state and depth — re-seeing a node costs one bumped counter, never a re-fetch.
  - Frontier: `claim_summoners()` / `claim_matches()` / `claim_unfetched()` select-and-mark a batch in **one statement** (`UPDATE (subquery) ... RETURN`), so a killed run is recoverable and concurrent workers can't claim the same row; `release_stale_claims()` / `release_stale_fetch_claims()` return abandoned `claimed` rows to the frontier at the start of every run.
  - Completion: `complete_summoner()` marks the node expanded and inserts everything it discovered in a single round trip, returning the new-node count. `fail_*(permanent=)` parks a node in `failed` or returns it for retry.
  - `store_match()` is the write path for a full payload: it upserts `game`, inserts the ten `played` edges, enriches the `summoner` rows with the Riot ID and level the payload carries, and settles both the BFS state and the fetch state — one query, idempotent, so re-storing a match is a no-op rather than a duplicate.
  - `match.participants` is an `array<record<summoner>>` with an array index — the cheap link the BFS needs. The richer `summoner->played->game` relation is written by `store_match()`, where there are per-participant stats to hang on it.
  - `iter_dataset()` pages `played` / `game` for export, flattening RecordIDs to bare keys and datetimes to ISO strings.
  - Every query goes through `_run()`, which retries `TransactionConflict` with jittered backoff — see [quirks.md](quirks.md).
- **`MatchCrawler`** ([league/crawler/match_crawler.py](../src/league/crawler/match_crawler.py)) — BFS over the summoner↔match graph until `CrawlConfig.target_matches` distinct match IDs are held. Two worker pools in one `asyncio.TaskGroup`: summoner workers expand match histories, match workers extract the 10 puuids from `metadata.participants`. Match expansion is **demand-driven** — gated on the summoner frontier dropping below `frontier_low_water` — because one summoner expansion yields far more IDs than one match expansion. Raises `CrawlerExhausted` (caught, reported as `status="exhausted"`) when both frontiers empty before the target.
- **`CrawlConfig`** ([league/crawler/match_crawler.py](../src/league/crawler/match_crawler.py)) — frozen config. `resolved()` freezes the time window to an absolute `start_time` **once**, so a long or resumed run can't slide its own window.
- **`MatchFetcher`** ([league/crawler/match_fetcher.py](../src/league/crawler/match_fetcher.py)) — the second pass. `cfg.workers` workers claim from the `fetch_state` frontier, request MATCH-V5, and hand the payload to `store_match()`. `FetchConfig.target=None` drains the whole backlog. Resumable: anything left `claimed` by a stop returns to `pending`, either immediately or via the stale-claim sweep. 403/404 and pydantic `ValidationError` are permanent failures (a payload that won't parse now won't parse on a retry); everything else retries up to `max_attempts`.
- **`crawler/schema.py`** ([league/crawler/schema.py](../src/league/crawler/schema.py)) — the dataset DDL and row builders. `participant_columns()` derives column names and Surreal types from `ParticipantSummary`'s annotations; `game_row()` / `played_row()` / `summoner_row()` turn a `Match` into rows. `patch_of()` trims `gameVersion` to `major.minor`.
- **`MatchTimelineAnalyzer`** ([league/timeline.py](../src/league/timeline.py)) — analyzes Riot API `MatchTimeline` for highlight events using composable `Predicate` rules. `get_highlight_events()` → `list[HighlightEvent]`. `ParticipantPositionTrack` provides linear-interpolated position at any timestamp.
- **`Predicate[T]`** ([league/predicates.py](../src/league/predicates.py)) — composable boolean predicate wrapping a `T → bool` function. Supports `&`, `|`, `~` operators. `@rule` decorator registers named factories. `load_rule_from_config(path)` / `load_rule_from_dict(config)` build predicates from JSON config.
- **`Output`** ([league/ui/output.py](../src/league/ui/output.py)) — the console facade; module-level instance `output`. `print()` (routes through `render()`), `json()`, `rule()`, `info/success/warning/error()`, `prompt()`, `status(msg)` (project spinner baked in), `progress(*columns)`. Every CLI command writes through this.
- **`ProgressReporter`** ([league/reporting.py](../src/league/reporting.py)) — `Protocol` with `message()`, `step()`, `advance()`, `task(description, total=None)`. `NullReporter` is the no-op default; `RichProgressReporter` ([league/ui/progress.py](../src/league/ui/progress.py)) is the terminal implementation (indeterminate `task` → spinner + elapsed, `total=` → bar + M-of-N). Lets backend code report progress without importing rich.
- **`MatchRow`** ([league/ui/viewmodels.py](../src/league/ui/viewmodels.py)) — presentation-only match view shared by the Riot and LCU match-history commands; `match_table()` shows the Position column only when rows carry one, Game Mode likewise.
- **`GoveeConnectionListener`** ([govee package](../../govee/src/govee/govee.py)) — discovers + manages Govee smart lights over LAN UDP. `listener.devices: dict[str, GoveeDevice]` holds discovered devices by IP. Wrapped by `GoveeLights`, which awaits `govee.request_timeout` (0.5s) after `start()` for discovery.

### Team → Effect Mapping

Team → colour lookups live next to the thing that owns them, avoiding if/elif chains. Chroma: `Effects.base_for(team)` ([league/companion.py](../src/league/companion.py)) maps `ORDER → blue`, `CHAOS → red`, everything else (spectator, unknown) → `white`. Govee: module-level `TEAM_TO_GOVEE_COLOR`, same shape, read by `GoveeLights.set_team()`:

```python
TEAM_TO_GOVEE_COLOR = {
    GameTeam.ORDER: GoveeColor.blue(),
    GameTeam.CHAOS: GoveeColor.red(),
    GameTeam.SPECTATOR: GoveeColor.white(),
}
```

### Adding a New Lighting Effect

All Chroma effects created at startup via `setup_chroma_effects()` in [league/companion.py](../src/league/companion.py), stored in `Effects` dataclass.

- **Static color** (base): call `static(ChromaColor.xyz())` inside `setup_effects()`, add returned ID as `str` field on `Effects`.
- **Flash animation**: call `make_flash(ChromaColor.xyz())` — uses `ChromaAnimation.flash_fade()` to build `dict[Optional[GameTeam], ChromaAnimation]` with one animation variant per base color (ORDER/CHAOS/spectator). Add as `dict` field on `Effects`.
  - Optionally pass `steps`, `flash_duration`, `total_fade_duration` to tune (e.g. `first_brick_flash` uses `steps=5, total_fade_duration=0.5`).
  - Dim teammate effects: pass `scale_color(ChromaColor.xyz(), TEAMMATE_DIM_FACTOR)` as color.
- Trigger flash from callback: `chroma.flash("<field>", active_player_team)` — `ChromaLighting.flash()` picks the team variant (falling back to the `None` one) and fires `play_animation()` as a task. No-ops when Chroma is disabled.
- `play_animation()` pre-uploads all frames to Chroma SDK, steps through with baked-in timing. Fades back to team base color automatically — no manual restore needed.
- Govee in callback: `govee.set_team(team)`, or reach into `govee.listener.devices.values()` for other `set_*` methods. Govee has no animation support — only instant color/brightness/power changes.

### Adding a New Event Handler

- Add event to `GameEventType` in [league/enums/base.py](../src/league/enums/base.py) if missing. Value must be exact string Live Client API returns.
- Add a matching member to `LeagueEvent` ([league/bridge.py](../src/league/bridge.py)) with the **same value** — the bridge logs a warning at construction for any `GameEventType` without one, and never dispatches it.
- Register a callback via `bridge.on(LeagueEvent.<New>, cb)` in `run_companion` ([league/companion.py](../src/league/companion.py)) for lighting. For console kill-feed output, add a `case` to `describe_event()` and the event to `FEED_EVENTS` ([league/ui/renderers/events.py](../src/league/ui/renderers/events.py)) — `register_event_feed` in companion wires every member of `FEED_EVENTS` to one callback via `bridge.on_game_events()`.
