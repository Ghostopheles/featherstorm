import os
import time
import asyncio
import logging

from enum import Enum
from typing import Callable

from league.enums import Queue
from league.lcu import LCUClient
from league.dragon import DataDragon
from league.riot_api import RiotAPIClient
from league.enums.queues import QUEUE_DESCRIPTION
from league.lcu.gameflow import LCUGameFlow, LCUGameflowPhase
from league.models import AllGameData, Scores, GameTeam, CurrentGameInfo
from league.discord import DiscordRichPresence, DiscordActivity, ActivityType

log = logging.getLogger(__name__)

MAX_PARTY_SIZE = 5
UPDATE_INTERVAL = 15.0

ASSETS_BASE_URL = "https://ghst.tools/media/featherstorm/assets"


class SessionStatus(Enum):
    Empty = 1
    InLobby = 2
    InQueue = 3
    InGame = 4


class LeagueRichPresence:
    presence: DiscordRichPresence
    dragon: DataDragon
    riot: RiotAPIClient | None = None
    teams: dict[str, GameTeam] | None = None
    champions: dict[str, str] | None = None
    active_player_name: str | None = None
    active_player_puuid: str | None = None
    gameflow: LCUGameFlow | None = None
    session_status: SessionStatus = SessionStatus.Empty

    _queue_type_set: bool | None = False
    _update_task: asyncio.Task | None = None
    _get_game_data: Callable | None = None

    def __init__(self, client_id: str, lcu_client: LCUClient | None = None):
        self.presence = DiscordRichPresence(client_id)
        self.dragon = DataDragon()
        self._update_task = None

        riot_api_key = os.getenv("RIOT_API_KEY")
        if riot_api_key is not None:
            self.riot = RiotAPIClient(riot_api_key)

        # presence only needs the LCU for lobby/phase reads - a caller that already owns a client
        # (the event bridge) passes it in so we don't open a second one
        self.lcu = lcu_client
        try:
            self.gameflow = LCUGameFlow(lcu_client)
            self.lcu = self.gameflow.lcu
        except Exception:
            log.warning("League client not running - presence will start in its empty state")
            self.gameflow = None

    async def _update_loop(self):
        while True:
            try:
                await self.update()
            except Exception:
                pass
            await asyncio.sleep(UPDATE_INTERVAL)

    async def start_updates(self):
        await self.presence.connect()
        self._update_task = asyncio.create_task(self._update_loop())

    def stop_updates(self):
        if self._update_task:
            self._update_task.cancel()
            self._update_task = None

    async def init(self):
        if self.gameflow is None:
            await self.init_empty()
            return

        phase = await self.gameflow.get_phase()
        match phase:
            case LCUGameflowPhase.Home:
                await self.init_empty()
            case LCUGameflowPhase.Lobby:
                lobby_data = await self.lcu.get_lobby()
                await self.init_lobby(lobby_data)
            case _:
                await self.init_empty()

    async def init_empty(self):
        activity = DiscordActivity(
            activity_type=ActivityType.PLAYING, name="League of Legends", state="Hanging out", details="In Client", start=int(time.time())
        )
        self.presence.set_activity(activity)
        self.session_status = SessionStatus.Empty

    async def init_lobby(self, event_data: dict | list):
        name = "League of Legends (Lobby)"

        game_config = event_data.get("gameConfig")

        num_players = len(event_data.get("members"))
        max_players = game_config.get("maxLobbySize")
        party_size = [num_players, max_players]

        queue_id = game_config.get("queueId")
        state = QUEUE_DESCRIPTION.get(queue_id)

        activity = DiscordActivity(
            activity_type=ActivityType.PLAYING,
            name=name,
            state=state,
            start=int(time.time()),
            party_size=party_size,
        )
        self.presence.set_activity(activity)
        self.session_status = SessionStatus.InLobby

    async def init_match(
        self, game_data: AllGameData, player_teams: dict[str, GameTeam], player_champions: dict[str, str], active_player_name: str, get_game_data
    ):
        self._get_game_data = get_game_data
        await self.dragon.initialize()

        self.teams = player_teams
        self.champions = player_champions
        self.active_player_name = active_player_name

        start = int(time.time() - game_data.gameData.gameTime)

        active_player = next((p for p in game_data.allPlayers if p.riotIdGameName == self.active_player_name), None)
        if self.riot:
            self.active_player_puuid = await self.riot.get_puuid(active_player.riotIdGameName, active_player.riotIdTagLine)

        # urlsafe_riot_name = f"{active_player.riotIdGameName.replace(" ", "%20")}-{active_player.riotIdTagLine}"
        # opgg_url = f"https://op.gg/lol/summoners/na/{urlsafe_riot_name}/ingame"

        champion = player_champions.get(game_data.activePlayer.riotIdGameName)
        skin_id = active_player.skinID
        opponent = self.get_lane_opponent(game_data)
        details = f"Playing {champion}"
        if opponent is not None:
            details += f" vs. {opponent}"

        large_image = await self.get_image_url_for_skin(champion, skin_id)
        large_text = active_player.skinName

        position = self.get_player_position(game_data)
        if position == "UTILITY":
            position = "SUPPORT"

        small_image = self.get_image_url_for_position(position)
        small_text = position.title()

        name = "League of Legends"
        game_mode = self.get_game_mode_string(game_data)
        if game_mode is not None:
            name += f" ({game_mode})"

        activity = DiscordActivity(
            name=name,
            details=details,
            start=start,
            large_image=large_image,
            large_text=large_text,
            small_image=small_image,
            small_text=small_text,
            # buttons=[
            #    {
            #        "label": "op.gg",
            #        "url": opgg_url
            #    }
            # ]
        )
        self.presence.set_activity(activity)
        self.session_status = SessionStatus.InGame

    async def update_lobby(self, lobby_data): ...

    async def update_active_match(self):
        if self._get_game_data is None:
            return

        game_data = await self._get_game_data()
        scores = self.get_score_for_active_player(game_data)
        if scores is None:
            return

        state = f"K/D/A: {scores.kills} / {scores.deaths} / {scores.assists} | {scores.creepScore} CS"
        self.presence.update_activity(state=state)

    async def update(self):
        match self.session_status:
            case SessionStatus.InGame:
                await self.update_active_match()

        await self.presence.update()

    async def end_match(self):
        self.stop_updates()
        await self.presence.clear()
        await self.presence.close()

    async def try_update_queue_type(self):
        if not self.riot or self._queue_type_set:
            return

        live_match = await self.get_current_match_from_riot()
        if live_match is None:
            return None

        queue_type = live_match.gameQueueConfigId
        if queue_type is None:
            return

        queue_type_str = self.get_queue_type_string(queue_type)
        name = f"League of Legends ({queue_type_str})"
        self.presence.update_activity(name=name)
        self._queue_type_set = True

    async def close(self):
        self.stop_updates()
        if self.presence.connected:
            await self.presence.close()

    def get_score_for_active_player(self, game_data: AllGameData) -> Scores | None:
        active_player = next((p for p in game_data.allPlayers if p.riotIdGameName == self.active_player_name), None)
        return active_player.scores if active_player else None

    def get_player_position(self, game_data: AllGameData) -> str | None:
        active_player = next((p for p in game_data.allPlayers if p.riotIdGameName == self.active_player_name), None)
        if not active_player:
            return None

        active_team = self.teams.get(self.active_player_name)
        if not active_team:
            return None

        active_player_position = active_player.position
        if active_player_position == "NONE":
            active_player_position = "MIDDLE"

        return active_player_position

    def get_lane_opponent(self, game_data: AllGameData) -> str | None:
        active_player = next((p for p in game_data.allPlayers if p.riotIdGameName == self.active_player_name), None)
        if not active_player:
            return None

        active_team = self.teams.get(self.active_player_name)
        if not active_team:
            return None

        active_player_position = self.get_player_position(game_data)

        enemy_team = [p for p in game_data.allPlayers if self.teams.get(p.riotIdGameName) != active_team]

        lane_opponent = next((p for p in enemy_team if p.position == active_player_position), None)
        return lane_opponent.championName if lane_opponent else None

    async def get_image_key_for_skin(self, champion_name: str, skin_id: int) -> str:
        skins = await self.dragon.get_champion_skins(champion_name)
        for skin in skins:
            bad_id = int(skin.get("id"))
            if (bad_id % 1000) == skin_id:
                parent_skin = skin.get("parentSkin")
                if parent_skin is not None:
                    return f"{champion_name.lower()}_{parent_skin}"

        return f"{champion_name.lower()}_{skin_id}"

    def get_image_key_for_position(self, position: str) -> str:
        return f"role_{position.lower()}"

    def format_tile_url(self, champion_name: str, skin_id: int):
        return f"{ASSETS_BASE_URL}/tiles/{champion_name.lower()}/{skin_id}.jpg"

    async def get_image_url_for_skin(self, champion_name: str, skin_id: int) -> str:
        skins = await self.dragon.get_champion_skins(champion_name)
        for skin in skins:
            bad_id = int(skin.get("id"))
            if (bad_id % 1000) == skin_id:
                parent_skin = skin.get("parentSkin")
                if parent_skin is not None:
                    return self.format_tile_url(champion_name.lower(), parent_skin)

        return self.format_tile_url(champion_name.lower(), skin_id)

    def get_image_url_for_position(self, position: str) -> str:
        return f"{ASSETS_BASE_URL}/roles/{position.lower()}.png"

    def get_game_mode_string(self, game_data: AllGameData) -> str:
        game_mode = game_data.gameData.gameMode
        match game_mode:
            case "CLASSIC":
                return None
            case "PRACTICETOOL":
                return "Practice Tool"
            case "RANKED":
                return "Ranked"
            case "KIWI":
                return "ARAM"
            case _:
                return None

    def get_queue_type_string(self, queue_type: Queue) -> str:
        match queue_type:
            case Queue.SWIFTPLAY_GAMES:
                return "Swiftplay"
            case Queue.Q_5V5_DRAFT_PICK_GAMES_2:
                return "Normal Draft"
            case Queue.Q_5V5_RANKED_SOLO_GAMES_2:
                return "Ranked"
            case Queue.Q_5V5_ARAM_GAMES_3:
                return "ARAM"
            case Queue.ARAM_MAYHEM:
                return "ARAM: Mayhem"
            case Queue.PRACTICE:
                return "Practice"

    async def get_current_match_from_riot(self, puuid: str | None = None) -> CurrentGameInfo | None:
        if self.riot is None:
            return None

        if puuid is None:
            puuid = self.active_player_puuid

        if puuid is None:
            return None

        game = await self.riot.get_live_match_for_puuid(puuid)
        return game
