import time
import asyncio

from league.dragon import DataDragon
from league.discord import DiscordRichPresence, DiscordActivity, ActivityType
from league.models import AllGameData, Scores, GameTeam

UPDATE_INTERVAL = 15.0

class LeagueRichPresence:
    def __init__(self, client_id: str):
        activity = DiscordActivity(
            activity_type=ActivityType.PLAYING,
            name="League of Legends",
            details="Playing League of Legends",
            state="Loading...",
        )
        self.presence = DiscordRichPresence(client_id, activity=activity)
        self.dragon = DataDragon()

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
        await self.dragon.initialize()

        self.teams = player_teams
        self.champions = player_champions
        self.active_player_name = active_player_name

        await self.presence.connect()

        start = int(time.time() - game_data.gameData.gameTime)

        active_player = next((p for p in game_data.allPlayers if p.riotIdGameName == self.active_player_name), None)

        urlsafe_riot_name = f"{active_player.riotIdGameName.replace(" ", "%20")}-{active_player.riotIdTagLine}"
        opgg_url = f"https://op.gg/lol/summoners/na/{urlsafe_riot_name}/ingame"

        champion = player_champions.get(game_data.activePlayer.riotIdGameName)
        skin_id = active_player.skinID
        opponent = self.get_lane_opponent(game_data)
        details = f"Playing {champion}"
        if opponent is not None:
            details += f" vs. {opponent}"

        position = self.get_player_position(game_data)
        if position == "UTILITY":
            position = "SUPPORT"
        details += f" | {position.title()}"

        large_image = await self.get_image_key_for_skin(champion, skin_id)
        large_text = active_player.skinName

        name = "League of Legends"
        game_mode = self.get_game_mode_string(game_data)
        if game_mode is not None:
            name += f" ({game_mode})"

        self.presence.update_activity(
            name=name,
            details=details,
            start=start,
            large_image=large_image,
            large_text=large_text,
            #buttons=[
            #    {
            #        "label": "op.gg",
            #        "url": opgg_url
            #    }
            #]
        )

        self.start_updates(get_game_data)

    async def update(self, game_data: AllGameData):
        scores = self.get_score_for_active_player(game_data)
        if scores is None:
            return

        state = f"K/D/A: {scores.kills} / {scores.deaths} / {scores.assists} | {scores.creepScore} CS"
        self.presence.update_activity(state=state)
        await self.presence.update()

    async def end_match(self):
        self.stop_updates()
        await self.presence.clear()
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

        lane_opponent = next(
            (p for p in enemy_team if p.position == active_player_position),
            None
        )
        return lane_opponent.championName if lane_opponent else None

    async def get_image_key_for_skin(self, champion_name:str, skin_id: int) -> str:
        skins = await self.dragon.get_champion_skins(champion_name)
        for skin in skins:
            bad_id = int(skin.get("id"))
            if (bad_id % 1000) == skin_id:
                parent_skin = skin.get("parentSkin")
                if parent_skin is not None:
                    return f"{champion_name.lower()}_{parent_skin}"

        return f"{champion_name.lower()}_{skin_id}"

    def get_game_mode_string(self, game_data: AllGameData) -> str:
        game_mode = game_data.gameData.gameMode
        print(game_mode)
        match game_mode:
            case "CLASSIC":
                return "Normal"
            case "PRACTICETOOL":
                return "Practice Tool"
            case "RANKED":
                return "Ranked"
            case _:
                return None
