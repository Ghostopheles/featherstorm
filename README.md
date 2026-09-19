# Featherstorm

A League of Legends companion toolkit written in async Python. It links four separate Riot data sources (the in-game Live Client API, the local League client's REST + WebSocket API, the public Riot Web API and Data Dragon) and uses them to drive real-world side effects:

- **Reactive room lighting.** Razer Chroma peripherals flash on kills, objectives and turrets, colored by team. Govee smart lights switch the room to your team's color over LAN UDP.
- **Discord Rich Presence.** Shows lobby, queue and in-game status, with the champion's skin splash, lane opponent and a live KDA/CS line.
- **Automatic highlight clips.** Finds highlight-worthy moments in a match timeline, drives the League replay client to each one and records it.
- **A resumable match crawler.** Walks the summoner↔match graph breadth-first under a strict API rate limit and stores the results as an analysis-ready dataset in SurrealDB.
- **A desktop app ("Bladecaller").** A PySide6 UI with a live client-status indicator and an expandable match history that shows a 10-player scoreboard and build order.
- **A CLI** (`featherstorm`) with commands for every subsystem.

> This is a personal project built for my own machine and hardware. It's here to show the engineering work. It isn't packaged as a product.

## Tech Stack

| Area | Tools |
| --- | --- |
| Language / runtime | Python 3.14, `asyncio` (`TaskGroup`, PEP 695 generics), `uv` |
| HTTP / realtime | `httpx` (HTTP/2, async), `websockets` (WAMP over WSS) |
| Data modeling | `pydantic` v2, dataclasses, generated `StrEnum`s |
| Storage | SurrealDB 3.x (graph relations, schemafull tables) running in Docker |
| Desktop UI | PySide6 (Qt 6), `qasync`, token-driven QSS theming |
| CLI / terminal | `typer`, `rich` |
| Integrations | Razer Chroma SDK, Govee LAN protocol, Discord IPC (`pypresence`), `pynput` |
| Tooling | `ruff`, `pytest` |

The Razer Chroma and Govee drivers are my own libraries, published as separate repos ([razer-chroma](https://github.com/Ghostopheles/razer-chroma) and [govee](https://github.com/Ghostopheles/govee)).

## Architecture

```
 League Live Client API ──poll 250ms──> MatchWatcher ──┐
   (in-game, 127.0.0.1:2999)            (session        │
                                         lifecycle)     ▼
                                              ┌─────────────────────┐
 League Client (LCU) ──WAMP websocket──────>  │  LeagueEventBridge  │ ── typed LeagueEvent
   (lobby, gameflow phase)                     └─────────────────────┘        │
                                                                              ├─> ChromaLighting
                                                                              ├─> GoveeLights
                                                                              ├─> Discord presence
                                                                              └─> console kill-feed

 Riot Web API ──> RiotRateLimiter ──> MatchCrawler / MatchFetcher ──> SurrealDB (summoner ─played─> game)
              └─> MatchTimelineAnalyzer ──> HighlightManager ──> replay client ──> recorded clips
```

The `LeagueEventBridge` is the center of the app. In-game events come from polling and out-of-game events come from a push socket, and the bridge merges both into one typed event stream. Feature modules subscribe with `bridge.on(LeagueEvent.ChampionKill, handler)` and don't need to know which source produced an event.

## Engineering Challenges

### 1. Merging a polled API and a push API into one event stream

The Live Client API exists only while a game is running, and it has no push channel: you poll an ever-growing event list. The LCU sends lobby and gameflow changes over a WAMP websocket, but only while the League client itself is open. Neither source covers the full session.

- `MatchWatcher` runs the in-game side as a state machine (`DISCONNECTED → LOADING → CONNECTED → BANISHED`). It waits for a game, polls it, spots dropped connections and reconnects, all without a restart between matches. The poller tracks a high-water mark on the event index so it emits only new events, and resets that mark at every session boundary. Without the reset, a new match would stay silent until its event count passed the previous match's.
- `LeagueEventBridge` combines both sources into one `LeagueEvent` enum. The LCU websocket rejects subscriptions after it connects, so the bridge registers its own internal dispatchers up front and fans out to user callbacks. Subscribers can then register at any time.
- Async handlers run as tracked tasks, so a slow Discord or network call can't stall the 250 ms poll loop. On shutdown the bridge cancels those tasks and closes only the clients it owns. An injected client outlives the bridge.

### 2. Staying under the Riot API rate limit with concurrent workers

Personal Riot API keys allow only **100 requests per 2 minutes**, and the crawler runs a dozen workers at once. A naive limiter that reads the `X-App-Rate-Limit-Count` headers still overshoots: the count only goes up once a response arrives, so every worker passes the check at the same time.

`RiotRateLimiter` reads the limits the server advertises (it handles multiple windows) and also counts **in-flight reservations**. Every `acquire()` reserves a slot, and the matching `release()` gives it back however the request ended. As a result, concurrent callers can't jointly exceed the window.

### 3. Crash-safe, duplicate-free work queues in SurrealDB

The crawler runs a BFS over a bipartite graph: summoners → match histories → match participants → more summoners. The frontier is stored in the database, so runs can be killed and resumed, and many workers claim work from it concurrently.

- **Atomic claims.** My first version selected a batch and then marked it `claimed` in a second statement. I measured **~12% duplicate claims** across 8 workers, and each duplicate wasted a scarce API request. A multi-statement query isn't a transaction, and wrapping it in `BEGIN/COMMIT` just moved the failures elsewhere. I replaced it with a single `UPDATE (SELECT … LIMIT n) SET state='claimed' RETURN …` statement. That form is atomic and returns exactly the rows the worker won.
- **Optimistic-concurrency conflicts.** SurrealDB's RocksDB backend uses optimistic transactions, so concurrent claims regularly fail with `Transaction conflict`. Every query runs through one `_run()` wrapper that retries those conflicts with jittered exponential backoff and treats them as normal traffic, not as errors.
- **Recovery.** Each row follows a state machine (`discovered → claimed → expanded | failed`). Every run starts by sweeping stale claims back into the frontier. Failures are classified as permanent or retryable. For example, MATCH-V5 returns 403 for Brawl games and 404 for custom games, so those are never retried.
- **Idempotent dedupe.** Discovery uses `INSERT … ON DUPLICATE KEY UPDATE seen_count += 1`. Seeing a node again costs one counter bump and never triggers a re-fetch.
- **Demand-driven scheduling.** One summoner expansion yields far more IDs than one match expansion. Match workers therefore run only when the summoner frontier drops below a low-water mark, which spends API budget where it produces the most new work.

### 4. A schema generated from the data model

The dataset has a `game` table plus a `played` table with one row per player per game. `played` is a real graph edge (`summoner ─played─> game`), so "every game this player played" and "everyone they've shared a game with" are each one traversal away. It is also a flat table that loads directly into a dataframe.

The ~130 typed columns aren't written by hand. `schema.py` **generates the DDL from the pydantic model's type annotations**, so adding a field to the model adds a column. Along the way I had to handle several data-quality problems: Riot sends fractional floats in fields named like integers, it adds and retires challenge keys mid-season (so those fields use `extra="allow"` models and a `FLEXIBLE` column), and it sends puuids that start with digits (so record IDs are built as `RecordID` objects and never string-interpolated).

### 5. Reconciling inconsistent identities across APIs

The LCU match history returns only *your* participant, and it identifies players with an anonymized per-match UUID rather than the real 78-character puuid. The Bladecaller match history therefore builds its list from the LCU (which needs no API key) and loads the full 10-player lobby from MATCH-V5 when you expand a row. The two sources are joined on `participantId`, the one identifier they share. Without an API key, the view falls back to LCU-only stats.

### 6. Rule-based highlight detection and replay automation

Highlight detection uses a small composable predicate DSL: `Predicate[T]` supports `&`, `|` and `~`, and named rules are registered with a `@rule` decorator. Rules can also be loaded from JSON config, so what counts as a highlight isn't hardcoded. `ParticipantPositionTrack` interpolates the timeline's once-per-minute position frames to estimate where a player was at any moment.

`HighlightManager` then downloads the replay through the LCU, launches it, seeks to each moment, waits for the replay API to confirm each state change, and records the clip.

### 7. One event loop for Qt and asyncio

The whole backend is async, and Qt has its own event loop. Bladecaller uses `qasync` to run both on **one loop**, so UI controllers can `await` the backend directly without threads, locks or signal marshalling. Styling is token-driven: colors, fonts and radii live in one `theme.py` and are substituted into a QSS template when the app loads. I ported the design from an HTML/CSS mockup and converted its `oklch` colors to sRGB.

### 8. Hardware effects that restore themselves

Chroma flash effects are precomputed as frame sequences for **each possible base color** and uploaded before they're needed. A kill flash on the blue team fades back to blue, and on the red team it fades back to red, with no restore step and no race between overlapping effects. Every feature (Chroma, Govee, Discord) is an async context manager that becomes a no-op when disabled, so event handlers don't need `if enabled:` checks.

## Project Layout

```
src/league/
├── bridge.py, watcher.py, api.py   # event hub, session lifecycle, Live Client poller
├── companion.py                    # lighting + presence feature wiring
├── lcu/                            # League client REST + WAMP websocket
├── riot_api.py, http.py            # Riot Web API client, rate limiter
├── crawler/                        # BFS crawler, fetcher, SurrealDB store, generated schema
├── timeline.py, predicates.py      # highlight detection
├── highlights.py                   # replay-client automation + recording
├── discord/                        # Rich Presence
├── bladecaller/                    # PySide6 desktop app
├── cli/                            # typer CLI
└── ui/                             # rich terminal rendering layer
scripts/                            # enum generator, dataset analysis example
docs/                               # per-module design notes and known quirks
```

The [docs/](docs/) folder has deeper notes on each subsystem, and [docs/quirks.md](docs/quirks.md) is a running log of API and database gotchas I found along the way.

## Running It

Requires Windows, Python 3.14+, [uv](https://docs.astral.sh/uv/), and a running League client. Hardware features need Razer Chroma devices or Govee lights, and the Riot API features need a `RIOT_API_KEY` in `.env`.

```bash
uv run featherstorm companion          # lighting + Discord presence, follows you between games
uv run featherstorm riot matches       # recent match history
uv run featherstorm crawler crawl --count 5000
uv run featherstorm crawler dataset --table played --format csv
uv sync --extra ui && uv run bladecaller   # desktop app
```

---

Featherstorm isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc.
