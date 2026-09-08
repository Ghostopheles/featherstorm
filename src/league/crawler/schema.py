"""Analytical schema for stored match data.

The crawler keeps two axes apart on purpose:

* `summoner` / `match` are the **frontier** — thin BFS bookkeeping rows that get scanned
  and re-scanned by every claim query, so nothing fat is ever allowed onto them.
* `game` and the `played` relation are the **dataset** — one row per match and one row
  per player-game, written once and then only read.

`played` is a real graph relation (`summoner -> played -> game`), which makes the two
queries this dataset exists for one hop each: every game a summoner played, and everyone
a summoner has shared a game with (`->played->game<-played<-summoner`). It is still a
flat table, so `SELECT * FROM played` hands a dataframe library exactly what it wants.

The `played` column list is derived from `ParticipantSummary` rather than written out by
hand — 130 duplicated `DEFINE FIELD` lines would drift from the model within one patch.
`featherstorm crawler schema --show` prints the generated DDL.
"""

import re

from typing import Union, Optional, get_args, get_origin
from datetime import datetime, timezone

from league.models import Match, ParticipantSummary

GAME = "game"
PLAYED = "played"

PENDING = "pending"
CLAIMED = "claimed"
STORED = "stored"
FAILED = "failed"

FETCH_STATES = (PENDING, CLAIMED, STORED, FAILED)

# Stored on the edge as FLEXIBLE objects instead of columns: Riot reshapes both every
# patch, and neither is worth 140 more typed fields.
NESTED_FIELDS = frozenset({"perks", "challenges"})

# `puuid` is the edge's `in`, so keeping it as a column would just duplicate it.
SKIP_FIELDS = frozenset({"puuid"})

RENAMES = {
    "championName": "champion",
    "championId": "champion_id",
    "teamPosition": "position",
    "individualPosition": "individual_position",
    "champLevel": "champ_level",
}

_CAMEL_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")


def snake(name: str) -> str:
    """`totalDamageDealtToChampions` -> `total_damage_dealt_to_champions`."""
    return RENAMES.get(name) or _CAMEL_BOUNDARY.sub("_", name).lower()


def surreal_type(annotation) -> str:
    """Map a pydantic annotation onto a SurrealDB field type."""
    origin = get_origin(annotation)
    if origin is Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        return f"option<{surreal_type(args[0])}>"

    return {bool: "bool", int: "int", float: "float", str: "string"}.get(annotation, "any")


def participant_columns() -> dict[str, tuple[str, str]]:
    """Model field name -> (column name, Surreal type), in model declaration order."""
    return {
        name: (snake(name), surreal_type(field.annotation))
        for name, field in ParticipantSummary.model_fields.items()
        if name not in SKIP_FIELDS and name not in NESTED_FIELDS
    }


# Columns the edge carries on top of the participant model's own fields.
EXTRA_PLAYED_COLUMNS = ("match_id", "queue", "patch", "keystone", "primary_style", "sub_style", "perks", "challenges")


def played_columns() -> tuple[str, ...]:
    return tuple(column for column, _ in participant_columns().values()) + EXTRA_PLAYED_COLUMNS


def played_upsert_clause() -> str:
    """Re-storing a match has to overwrite every column, so the `ON DUPLICATE KEY UPDATE`
    assignment list is generated from the same column list the rows are built from."""
    return ", ".join(f"{column} = $input.{column}" for column in played_columns())


def _played_fields() -> str:
    lines = [f"DEFINE FIELD IF NOT EXISTS {column} ON {PLAYED} TYPE {kind};" for column, kind in participant_columns().values()]
    return "\n".join(lines)


# --- fetch axis on the frontier `match` node ----------------------------------

FETCH_SCHEMA = f"""
DEFINE FIELD IF NOT EXISTS fetch_state      ON match TYPE string DEFAULT '{PENDING}'
      ASSERT $value IN {list(FETCH_STATES)};
DEFINE FIELD IF NOT EXISTS fetch_claimed_at ON match TYPE option<datetime>;
DEFINE FIELD IF NOT EXISTS fetched_at       ON match TYPE option<datetime>;
DEFINE FIELD IF NOT EXISTS fetch_attempts   ON match TYPE int DEFAULT 0;
DEFINE FIELD IF NOT EXISTS fetch_error      ON match TYPE option<string>;
DEFINE INDEX IF NOT EXISTS match_fetch ON match FIELDS fetch_state;

DEFINE FIELD IF NOT EXISTS summoner_level ON summoner TYPE option<int>;
DEFINE FIELD IF NOT EXISTS profile_icon   ON summoner TYPE option<int>;
"""

GAME_SCHEMA = f"""
DEFINE TABLE IF NOT EXISTS {GAME} SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS match_id           ON {GAME} TYPE string;
DEFINE FIELD IF NOT EXISTS platform           ON {GAME} TYPE string;
DEFINE FIELD IF NOT EXISTS game_id            ON {GAME} TYPE option<int>;
DEFINE FIELD IF NOT EXISTS queue              ON {GAME} TYPE int;
DEFINE FIELD IF NOT EXISTS map_id             ON {GAME} TYPE int;
DEFINE FIELD IF NOT EXISTS game_mode          ON {GAME} TYPE string;
DEFINE FIELD IF NOT EXISTS game_type          ON {GAME} TYPE option<string>;
DEFINE FIELD IF NOT EXISTS game_version       ON {GAME} TYPE string;
DEFINE FIELD IF NOT EXISTS patch              ON {GAME} TYPE string;
DEFINE FIELD IF NOT EXISTS end_of_game_result ON {GAME} TYPE option<string>;
DEFINE FIELD IF NOT EXISTS remake             ON {GAME} TYPE bool DEFAULT false;
DEFINE FIELD IF NOT EXISTS duration           ON {GAME} TYPE int;
DEFINE FIELD IF NOT EXISTS created_at         ON {GAME} TYPE option<datetime>;
DEFINE FIELD IF NOT EXISTS started_at         ON {GAME} TYPE option<datetime>;
DEFINE FIELD IF NOT EXISTS ended_at           ON {GAME} TYPE option<datetime>;
DEFINE FIELD IF NOT EXISTS winner             ON {GAME} TYPE option<int>;
DEFINE FIELD IF NOT EXISTS participant_count  ON {GAME} TYPE int DEFAULT 0;
DEFINE FIELD IF NOT EXISTS teams              ON {GAME} TYPE array<object> FLEXIBLE DEFAULT [];
DEFINE FIELD IF NOT EXISTS stored_at          ON {GAME} TYPE datetime DEFAULT time::now();
DEFINE INDEX IF NOT EXISTS game_queue   ON {GAME} FIELDS queue;
DEFINE INDEX IF NOT EXISTS game_patch   ON {GAME} FIELDS patch;
DEFINE INDEX IF NOT EXISTS game_started ON {GAME} FIELDS started_at;
"""


def played_schema() -> str:
    return f"""
DEFINE TABLE IF NOT EXISTS {PLAYED} TYPE RELATION IN summoner OUT {GAME} SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS match_id ON {PLAYED} TYPE string;
DEFINE FIELD IF NOT EXISTS queue    ON {PLAYED} TYPE int;
DEFINE FIELD IF NOT EXISTS patch    ON {PLAYED} TYPE string;
{_played_fields()}
DEFINE FIELD IF NOT EXISTS keystone      ON {PLAYED} TYPE option<int>;
DEFINE FIELD IF NOT EXISTS primary_style ON {PLAYED} TYPE option<int>;
DEFINE FIELD IF NOT EXISTS sub_style     ON {PLAYED} TYPE option<int>;
DEFINE FIELD IF NOT EXISTS perks      ON {PLAYED} TYPE option<object> FLEXIBLE;
DEFINE FIELD IF NOT EXISTS challenges ON {PLAYED} TYPE option<object> FLEXIBLE;
DEFINE INDEX IF NOT EXISTS played_match    ON {PLAYED} FIELDS match_id;
DEFINE INDEX IF NOT EXISTS played_champion ON {PLAYED} FIELDS champion;
DEFINE INDEX IF NOT EXISTS played_position ON {PLAYED} FIELDS position;
DEFINE INDEX IF NOT EXISTS played_queue    ON {PLAYED} FIELDS queue;
"""


# `DEFAULT` only fires when a record is created, so match rows discovered before the fetch
# axis existed carry NONE for these — which both fails the `int` coercion on write and
# hides them from `WHERE fetch_state = 'pending'`. Indexed, so it costs nothing once done.
BACKFILL = f"""
UPDATE match SET fetch_state = '{PENDING}', fetch_attempts = 0 WHERE fetch_state = NONE;
"""


def dataset_schema() -> str:
    return FETCH_SCHEMA + GAME_SCHEMA + played_schema() + BACKFILL


# --- row builders -------------------------------------------------------------


def patch_of(game_version: str) -> str:
    """`16.17.810.4348` -> `16.17`. Grouping by full version splits every patch into
    a dozen hotfix buckets, which is never what an analysis wants."""
    parts = game_version.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else game_version


def _millis(value: Optional[int]) -> Optional[datetime]:
    """Riot epoch milliseconds -> `datetime`.

    It has to be a real datetime, not an ISO string: the SDK encodes datetimes as a CBOR
    datetime, and a `TYPE datetime` field rejects the string form outright.
    """
    if not value:
        return None
    return datetime.fromtimestamp(value / 1000, timezone.utc)


def game_row(match: Match) -> dict:
    info = match.info
    winner = next((t.teamId for t in info.teams if t.win), None)
    return {
        "match_id": match.metadata.matchId,
        "platform": info.platformId,
        "game_id": info.gameId,
        "queue": int(info.queueId),
        "map_id": int(info.mapId),
        "game_mode": info.gameMode,
        "game_type": info.gameType,
        "game_version": info.gameVersion,
        "patch": patch_of(info.gameVersion),
        "end_of_game_result": info.endOfGameResult,
        "remake": info.remake,
        "duration": info.gameDuration,
        "created_at": _millis(info.gameCreation),
        "started_at": _millis(info.gameStartTimestamp),
        "ended_at": _millis(info.gameEndTimestamp),
        "winner": winner,
        "participant_count": len(info.participants),
        "teams": [t.model_dump(mode="json") for t in info.teams],
        # CONTENT replaces the whole record, and DEFAULT only fires on create, so a
        # re-store would otherwise blank this out
        "stored_at": datetime.now(timezone.utc),
    }


def played_row(match: Match, participant: ParticipantSummary) -> dict:
    """The participant's stat line, ready to become one `played` edge.

    `in` / `out` / `id` are filled in by the writer, which owns the RecordIDs.
    """
    info = match.info
    row = {column: getattr(participant, field) for field, (column, _) in participant_columns().items()}

    perks = participant.perks
    styles = {s.description: s.style for s in perks.styles} if perks else {}

    row.update(
        {
            "match_id": match.metadata.matchId,
            "queue": int(info.queueId),
            "patch": patch_of(info.gameVersion),
            "keystone": perks.keystone if perks else None,
            "primary_style": styles.get("primaryStyle"),
            "sub_style": styles.get("subStyle"),
            "perks": perks.model_dump(mode="json") if perks else None,
            "challenges": participant.challenges.model_dump(mode="json") if participant.challenges else None,
        }
    )
    return row


def summoner_row(participant: ParticipantSummary, *, depth: int) -> dict:
    """Participants double as frontier discoveries — the payload already carries the
    Riot ID and level that the `summoner` node otherwise never learns."""
    return {
        "depth": depth,
        "game_name": participant.riotIdGameName or None,
        "tag_line": participant.riotIdTagline or None,
        "summoner_level": participant.summonerLevel,
        "profile_icon": participant.profileIcon,
    }
