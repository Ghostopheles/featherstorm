# Riot API (riot_api.py)

`RiotAPIClient` — reads `RIOT_API_KEY` from `.env` (via `python-dotenv`). Route logic in `get_region_for_url()`: `/riot/*` and `match/v5` → `americas`, `/lol/*` → `na1`.

`RiotAPIClient(api_key, limiter=None)` — pass a `RiotRateLimiter` and every `get()` waits for capacity, feeds response headers back into the limiter, and retries 429s honouring `Retry-After`. With `limiter=None` (the default, used by companion/bladecaller/all other CLI commands) behaviour is exactly as before. The crawler is the only caller that installs one.

MATCH-V5 methods:
- `get_match_ids(puuid, *, count, start, match_type, queue, start_time, end_time)` → `list[str]`
- `get_match(match_id)` → `Match`
- `get_match_timeline(match_id)` → `MatchTimeline`
- `get_recent_matches(puuid, count, match_type)` → `list[PlayerMatch]` (convenience wrapper)

Other methods:
- `get_puuid(game_name, tag_line)` → `str | None`; `get_account()` / `get_many_accounts()` cached via `DataCache`
- `get_ranked_data(queue: RankedQueueType, tier: RankedTier, division: RankedDivision, page)` → `set[LeagueEntry]` — LEAGUE-V4 ladder entries
- `get_live_match_for_puuid(puuid)` → `CurrentGameInfo | None` — SPECTATOR-V5 active game (404 when not in game → `None`)

`RiotRateLimiter` ([league/http.py](../src/league/http.py)) tracks `X-App-Rate-Limit`/`-Count` headers per window; `acquire()` sleeps until capacity available.

> `developer.riotgames.com/apis` is correct API reference but JS-heavy SPA — **WebFetch cannot render it**. Use **WebSearch** as fallback (e.g. `"riot match-v5 API endpoints query parameters"`), or headless browser tool (e.g. Playwright MCP) if available.

> `https://developer.riotgames.com/docs/lol#data-dragon` is correct place for Data Dragon API docs.

## External APIs

| API | Base URL | Auth |
|-----|----------|------|
| League Live Client | `https://127.0.0.1:2999/liveclientdata` | None (`verify=False`) |
| Riot Data Dragon | `https://ddragon.leagueoflegends.com` | None |
| Riot API | `https://api.riotgames.com` | `RIOT_API_KEY` in `.env` |
| Govee LAN | UDP `device_ip:4003` / broadcast `239.255.255.250:4001` | None |

See [quirks.md](quirks.md) for MATCH-V5 queue coverage gaps, Data Dragon lookup gotchas, and error-handling quirks.
