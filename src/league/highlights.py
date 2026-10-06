import asyncio

from pathlib import Path
from typing import Optional

import league.config as cfg

from league.lcu.lcu import LCUClient, LCUMatch
from league.lcu.exceptions import LCUMissingReplayMetadataException, LCUIncompatibleReplayException
from league.models import PlayerMatch, TimelineEvent, MatchTimeline
from league.enums import MatchType, Queue
from league.timeline import MatchTimelineAnalyzer, HighlightEvent
from league.riot_api import RiotAPIClient
from league.markup import format_file_path
from league.replay import ReplayManager
from league.reporting import ProgressReporter, NullReporter

CLIP_DURATION = 15  # seconds
GAME_CLIENT_NAME = "League of Legends.exe"

REALITY_CHECK_BUFFER = 5

LEAD_BUFFER = 7  # seconds
TRAIL_BUFFER = 7  # seconds


class HighlightManager:
    game_path: Path
    cache_path: Path

    lcu: LCUClient | None = None
    replay: ReplayManager | None = None

    riot: RiotAPIClient | None = None
    puuid: str | None = None

    cfg: dict | None = None

    __matches: list[PlayerMatch] | None = None
    __match_cache: dict[str, PlayerMatch] | None = None
    __timeline_cache: dict[str, MatchTimeline] | None = None

    __current_match: PlayerMatch | None = None

    def __init__(self, game_path: Path, cache_path: Path, reporter: Optional[ProgressReporter] = None):
        self.reporter = reporter or NullReporter()

        if not game_path.exists():
            raise FileNotFoundError("Invalid League of Legends game path")

        if GAME_CLIENT_NAME not in str(game_path):
            if str(game_path.parent) != "Game":
                game_path = game_path / "Game"

            game_path = game_path / GAME_CLIENT_NAME

        if not game_path.exists():
            raise FileNotFoundError("Unable to find League of Legends executable")

        self.game_path = game_path

        self.cache_path = cache_path
        self.cache_path.mkdir(parents=True, exist_ok=True)

    async def __init_api(self, name: str, tag: str, api_key: str):
        if self.riot is not None:
            return

        self.riot = RiotAPIClient(api_key)
        self.puuid = await self.riot.get_puuid(name, tag)

    def __init_lcu(self):
        if self.lcu is not None:
            return

        self.lcu = LCUClient(self.game_path.parent.parent)
        self.replay = ReplayManager(self.game_path.parent.parent, lcu=self.lcu, reporter=self.reporter)

    def __init_cfg(self):
        if self.cfg is not None:
            return

        self.cfg = cfg.get_category("highlights")

    async def __init(self, *args, **kwargs):
        await self.__init_api(*args, **kwargs)
        self.__init_lcu()
        self.__init_cfg()

    @classmethod
    async def create(cls, name: str, tag: str, game_path: Path, cache_path: Path, api_key: str, reporter: Optional[ProgressReporter] = None):
        obj = cls(game_path, cache_path, reporter)
        await obj.__init(name, tag, api_key)
        return obj

    @staticmethod
    def get_player_participant_id(match: PlayerMatch) -> int:
        return match.player.participantId

    async def get_match(self, matchID: str) -> PlayerMatch:
        if self.__match_cache is None:
            self.__match_cache = {}
            match = await self.riot.get_player_match(matchID, self.puuid)
            self.__match_cache.setdefault(matchID, match)

        return self.__match_cache.get(matchID)

    async def get_recent_matches(
        self,
        count: int = 10,
        match_type: Optional[MatchType] = None,
        queue_type: Optional[Queue] = None,
    ) -> list[PlayerMatch]:
        if self.__matches is None:
            self.__matches = await self.riot.get_recent_matches(self.puuid, count=count, match_type=match_type, queue_type=queue_type)
            self.__match_cache = {match.matchId: match for match in self.__matches}

        return self.__matches

    async def get_recent_lcu_matches(
        self,
        count: int = 10,
        queue_type: Optional[Queue] = None,
    ) -> list[LCUMatch]:
        if self.__matches is None or len(self.__matches) != count:
            self.__matches = await self.lcu.get_match_history(count=count, queue_type=queue_type)
            self.__match_cache = {match.matchId: match for match in self.__matches}

        return self.__matches

    async def get_last_match(self, queue_type: Optional[Queue] = None) -> PlayerMatch:
        matches = await self.get_recent_matches(count=1, queue_type=queue_type)
        return matches[0]

    async def get_last_match_id(self, queue_type: Optional[Queue] = None) -> str:
        match = await self.get_last_match(queue_type=queue_type)
        return match.matchId

    async def get_timeline_for_match(self, matchID: str) -> MatchTimeline:
        if self.__timeline_cache is None:
            self.__timeline_cache = {}
            timeline = await self.riot.get_match_timeline(matchID)
            self.__timeline_cache.setdefault(matchID, timeline)

        return self.__timeline_cache.get(matchID)

    async def get_highlight_events(self, matchID: str) -> list[HighlightEvent]:
        timeline = await self.get_timeline_for_match(matchID)

        match = await self.get_match(matchID)
        playerParticipantID = self.get_player_participant_id(match)

        all_participants = [match.player, *match.teammates, *match.enemies]
        participant_champions = {p.participantId: p.championName for p in all_participants}

        analyzer = MatchTimelineAnalyzer(playerParticipantID, timeline, participant_champions)
        return analyzer.get_highlight_events()

    async def get_all_events_for_match(self, matchID: str) -> list[TimelineEvent]:
        timeline = await self.get_timeline_for_match(matchID)

        match = await self.get_match(matchID)
        playerParticipantID = self.get_player_participant_id(match)

        analyzer = MatchTimelineAnalyzer(playerParticipantID, timeline)
        return analyzer.get_all_events()

    async def capture_highlights_for_match(
        self,
        matchID: str,
        numHighlights: int = 5,
        events: Optional[list[HighlightEvent]] = None,
        index_offset: int = 0,
    ):
        count = len(events) if events is not None else numHighlights
        self.reporter.message(f"Capturing {count} highlight(s) for match [highlights_match_id]{matchID}[/]")

        with self.reporter.task():
            if events is None:
                self.reporter.step("Fetching highlight events...")
                events = await self.get_highlight_events(matchID)
                events.sort(key=lambda x: x.timestamp)  # sort by the start time

            self.reporter.step("Fetching match data...")
            match = await self.get_match(matchID)
            self.__current_match = match

            self.reporter.step("Opening replay file...")
            if not await self.open_replay(matchID):
                return
            await self.replay.api.wait_until_ready()
        try:
            await self.record(events, numHighlights, index_offset)
        except KeyboardInterrupt, asyncio.CancelledError:
            self.reporter.message("[warning]Cancelled[/] - pausing replay and ending recording...")
            try:
                await self.replay.api.pause()
                await self.replay.api.stop_recording()
            except Exception:
                pass
            raise

    async def open_replay(self, matchID: str) -> bool:
        try:
            await self.replay.open(matchID)
        except LCUMissingReplayMetadataException, LCUIncompatibleReplayException:
            self.reporter.message(f"[error]Unable to open replay for match {matchID}[/]")
            return False

        return True

    async def record(self, events: list[HighlightEvent], numHighlights: int = None, index_offset: int = 0):
        api = self.replay.api

        await api.pause()
        await asyncio.sleep(REALITY_CHECK_BUFFER)

        await api.hide_ui()

        raw_highlight_paths = []
        for i, batch in enumerate(events):
            if numHighlights is not None and i >= numHighlights:
                break

            idx = i + 1 + index_offset
            self.reporter.message(f"Capturing highlight [highlights_match_id]{idx}[/]...")

            timestamp = batch.timestamp

            with self.reporter.task("Recording..."):
                start_time = max(0, timestamp - LEAD_BUFFER)
                length = batch.event_length
                end_time = timestamp + length + TRAIL_BUFFER
                self.reporter.step("Seeking...")
                await api.seek_to(timestamp)

                self.reporter.step("Buffering...")
                await api.wait_for_seek()

                self.reporter.step("Tracking player...")
                await api.follow_player(self.__current_match.player.riotIdGameName)

                self.reporter.step("Resuming playback...")
                await api.resume()

                matchID = self.__current_match.matchId
                file_name = f"highlight_{idx}.webm"

                file_dir = self.cache_path / matchID
                file_dir.mkdir(parents=True, exist_ok=True)

                self.reporter.step("Configuring recording...")
                file_path = (file_dir / file_name).resolve()
                await api.start_recording(file_path.as_posix(), start_time, end_time, lossless=True)  # re-encoded by ffmpeg afterwards

                self.reporter.step("Recording...")
                await api.wait_for_recording()

            self.reporter.message(f"Captured highlight [highlights_match_id]{idx}[/]!")
            raw_highlight_paths.append(file_path)

        self.reporter.message(f"Done capturing highlights - exiting in {REALITY_CHECK_BUFFER} seconds...")
        await asyncio.sleep(REALITY_CHECK_BUFFER)
        await self.replay.close_active()

        self.reporter.message(f"Converting & compressing {len(raw_highlight_paths)} highlights...")
        await self.compress_many_highlights(raw_highlight_paths)

        return True

    async def compress_many_highlights(self, paths: list[Path]):
        with self.reporter.task("Compressing highlights...", total=len(paths)):

            async def _track(path: Path):
                result = await self.compress_highlight(path)
                self.reporter.advance()
                self.reporter.message(f"Highlight saved to {format_file_path(result)}")
                return result

            await asyncio.gather(*[_track(p) for p in paths])

        self.reporter.message(":cherry_blossom: Done compressing highlights")

    async def compress_highlight(self, file_path: Path) -> Path:
        dest = file_path.with_suffix(".mp4")

        if dest.exists():
            dest.unlink()

        cmd = [
            "ffmpeg",
            "-i",
            file_path.as_posix(),
            "-c:v",
            "av1_nvenc",
            "-cq",
            self.cfg.get("export_constant_quality"),
            "-preset",
            f"p{self.cfg.get('export_preset')}",
            "-r",
            self.cfg.get("export_fps"),
            "-multipass",
            self.cfg.get("export_multipass"),
            "-spatial-aq",
            "1",
            "-temporal-aq",
            "1",
            "-b:a",
            self.cfg.get("export_audio_quality"),
            "-rc-lookahead",
            "32",
            dest.as_posix(),
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {stderr.decode()}")

        file_path.unlink()

        return dest
