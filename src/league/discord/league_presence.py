import time
import asyncio

from league.discord import DiscordRichPresence, DiscordActivity, ActivityType
from league.models import AllGameData, Scores, GameTeam

UPDATE_INTERVAL = 15.0

class LeagueRichPresence:
    def __init__(self, client_id: str):
        activity = DiscordActivity(
            activity_type=ActivityType.PLAYING,
            name="League of Legends",
            details="Playing League of Legends",
            state="Loading..."
        )
        self.presence = DiscordRichPresence(client_id, activity=activity)

    async def _update_loop(self, get_game_data):
        while True:
            try:
                data = await get_game_data()
                await self.update(data)
            except Exception:
                pass
            await asyncio.sleep(UPDATE_INTERVAL)

    def start_updates(self, get_game_data):
        self._update_task = asyncio.create_task(self._update_loop(get_game_data))

    def stop_updates(self):
        if self._update_task:
            self._update_task.cancel()
            self._update_task = None

    async def init_match(
        self,
        game_data: AllGameData,
        player_teams: dict[str, GameTeam],
        player_champions: dict[str, str],
        active_player_name: str,
        get_game_data
    ):
        self.teams = player_teams
        self.champions = player_champions
        self.active_player_name = active_player_name

        await self.presence.connect()

        start = int(time.time())

        active_player = next((p for p in game_data.allPlayers if p.riotIdGameName == self.active_player_name), None)

        champion = player_champions.get(game_data.activePlayer.riotIdGameName)
        skin_id = active_player.skinID
        opponent = self.get_lane_opponent(game_data)
        details = f"Playing {champion} vs. {opponent}"
        large_image = f"{champion.lower()}_{skin_id}"
        large_text = active_player.skinName

        self.presence.update_activity(
            details=details,
            start=start,
            large_image=large_image,
            large_text=large_text
        )

        self.start_updates(get_game_data)

    async def update(self, game_data: AllGameData):
        scores = self.get_score_for_active_player(game_data)
        if scores is None:
            return

        state = f"K/D/A: {scores.kills} / {scores.deaths} / {scores.assists}"
        self.presence.update_activity(state=state)
        await self.presence.update()

    async def end_match(self):
        self.stop_updates()
        await self.presence.clear()
        await self.presence.close()

    def get_score_for_active_player(self, game_data: AllGameData) -> Scores | None:
        active_player = next((p for p in game_data.allPlayers if p.riotIdGameName == self.active_player_name), None)
        return active_player.scores if active_player else None

    def get_lane_opponent(self, game_data: AllGameData) -> str | None:
        active_player = next((p for p in game_data.allPlayers if p.riotIdGameName == self.active_player_name), None)
        if not active_player:
            return None

        active_team = self.teams.get(self.active_player_name)
        if not active_team:
            return None

        active_player_position = active_player.position
        if active_player_position == "NONE":
            active_player_position = "MIDDLE"

        enemy_team = [p for p in game_data.allPlayers if self.teams.get(p.riotIdGameName) != active_team]

        lane_opponent = next(
            (p for p in enemy_team if p.position == active_player_position),
            None
        )
        return lane_opponent.championName if lane_opponent else None
