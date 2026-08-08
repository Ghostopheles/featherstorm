import os
import asyncio

from pathlib import Path
from dotenv import load_dotenv

from PySide6.QtCore import QObject, Signal

from league import config
from league.lcu import LCUClient
from league.riot_api import RiotAPIClient
from league.bladecaller.core.match import MatchSummary, MatchDetail

DEFAULT_PAGE_SIZE = 20

NO_LCU_MESSAGE = "League client not running"
NO_KEY_MESSAGE = "Full scoreboard needs RIOT_API_KEY in .env"
RIOT_FAILED_MESSAGE = "Riot API request failed — showing your stats only"


class MatchHistoryController(QObject):
    """Loads the match list from the LCU and expands rows via the Riot API.

    Shape mirrors `ClientStatusController`: a `QObject` with signals, driven by
    asyncio tasks on the qasync loop, holding no Qt widgets. Signals are already
    delivered on the GUI thread.

    The two data sources are deliberate. The LCU match-history endpoint only
    returns the current summoner's participant, which is everything a collapsed
    row needs and costs no API key; the full ten-player lobby only exists on
    MATCH-V5, so it is fetched lazily when a row is expanded.
    """

    matches_loaded = Signal(list)
    load_failed = Signal(str)
    # game ids exceed 32 bits, which Qt's `int` signal type truncates
    detail_loaded = Signal(object, object)
    detail_failed = Signal(object, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lcu: LCUClient | None = None
        self._riot: RiotAPIClient | None = None
        self._riot_checked = False

        self._page_size = config.get_int("bladecaller.match_history_page_size", default=DEFAULT_PAGE_SIZE)
        self._next_index = 0
        self._summaries: dict[int, MatchSummary] = {}
        self._details: dict[int, MatchDetail] = {}

        self._tasks: set[asyncio.Task] = set()
        self._loading = False

    def start(self):
        self.load_page()

    def stop(self):
        for task in list(self._tasks):
            task.cancel()
        self._tasks.clear()

    async def close(self):
        self.stop()
        await self._drop_lcu()
        await self._drop_riot()

    def load_page(self):
        if self._loading:
            return
        self._loading = True
        self._spawn(self._load_page())

    def reload(self):
        self._next_index = 0
        self._summaries.clear()
        self._details.clear()
        self._loading = False
        self.load_page()

    def load_detail(self, game_id: int):
        cached = self._details.get(game_id)
        if cached is not None:
            self.detail_loaded.emit(game_id, cached)
            return
        self._spawn(self._load_detail(game_id))

    def _spawn(self, coro):
        task = asyncio.ensure_future(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _load_page(self):
        try:
            lcu = await self._get_lcu()
            if lcu is None:
                self.load_failed.emit(NO_LCU_MESSAGE)
                return

            start = self._next_index
            history = await lcu.get_match_history(start_index=start, count=self._page_size)
            games = history.games.games
            summaries = [MatchSummary.from_lcu(game) for game in games]
            for summary in summaries:
                self._summaries[summary.game_id] = summary

            self._next_index = start + len(summaries)
            self.matches_loaded.emit(summaries)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await self._drop_lcu()
            self.load_failed.emit(str(exc) or NO_LCU_MESSAGE)
        finally:
            self._loading = False

    async def _load_detail(self, game_id: int):
        summary = self._summaries.get(game_id)
        if summary is None:
            self.detail_failed.emit(game_id, "Match not loaded")
            return

        detail = MatchDetail.from_summary(summary, note=NO_KEY_MESSAGE)
        try:
            riot = self._get_riot()
            if riot is not None:
                player_match = await riot.get_player_match(summary.match_id, summary.puuid)
                detail = MatchDetail.from_player_match(game_id, player_match)
        except asyncio.CancelledError:
            raise
        except Exception:
            await self._drop_riot()
            detail = MatchDetail.from_summary(summary, note=RIOT_FAILED_MESSAGE)

        self._details[game_id] = detail
        self.detail_loaded.emit(game_id, detail)

    async def _get_lcu(self) -> LCUClient | None:
        if self._lcu is None:
            try:
                self._lcu = LCUClient(client_install_path=Path(config.get("lcu.client_install_path")))
            except Exception:
                # lockfile missing — League isn't running yet, retry on the next call
                return None
        return self._lcu

    def _get_riot(self) -> RiotAPIClient | None:
        if self._riot is None and not self._riot_checked:
            self._riot_checked = True
            load_dotenv()
            api_key = os.getenv("RIOT_API_KEY")
            if api_key:
                self._riot = RiotAPIClient(api_key)
        return self._riot

    async def _drop_lcu(self):
        if self._lcu is None:
            return
        lcu, self._lcu = self._lcu, None
        await lcu.client.aclose()
        await lcu.dragon.client.aclose()

    async def _drop_riot(self):
        if self._riot is None:
            return
        riot, self._riot = self._riot, None
        self._riot_checked = False
        await riot.client.aclose()
