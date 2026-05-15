import random

from datetime import datetime

from rich.box import MINIMAL_DOUBLE_HEAD
from rich.align import Align
from rich.console import Console, Group
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.padding import Padding

from league.enums import GameTeam, GamePlayerPosition
from league.console import console, print

MAX_PLAYERS = 10

FAKE_SUMMONER_NAME = "lizard"
FAKE_DATA = {
    GameTeam.ORDER: [
        {
            "index": 1,
            "summoner_name": FAKE_SUMMONER_NAME,
            "champion_name": "Darius",
            "team": GameTeam.ORDER,
            "position": GamePlayerPosition.TOP
        },
        {
            "index": 2,
            "summoner_name": FAKE_SUMMONER_NAME,
            "champion_name": "Evelynn",
            "team": GameTeam.ORDER,
            "position": GamePlayerPosition.JUNGLE
        },
        {
            "index": 3,
            "summoner_name": FAKE_SUMMONER_NAME,
            "champion_name": "Ahri",
            "team": GameTeam.ORDER,
            "position": GamePlayerPosition.MIDDLE
        },
        {
            "index": 4,
            "summoner_name": FAKE_SUMMONER_NAME,
            "champion_name": "Xayah",
            "team": GameTeam.ORDER,
            "position": GamePlayerPosition.BOTTOM
        },
        {
            "index": 5,
            "summoner_name": FAKE_SUMMONER_NAME,
            "champion_name": "Seraphine",
            "team": GameTeam.ORDER,
            "position": GamePlayerPosition.SUPPORT
        },
    ],
    GameTeam.CHAOS: [
        {
            "index": 1,
            "summoner_name": FAKE_SUMMONER_NAME,
            "champion_name": "Illaoi",
            "team": GameTeam.CHAOS,
            "position": GamePlayerPosition.TOP
        },
        {
            "index": 2,
            "summoner_name": FAKE_SUMMONER_NAME,
            "champion_name": "Briar",
            "team": GameTeam.CHAOS,
            "position": GamePlayerPosition.JUNGLE
        },
        {
            "index": 3,
            "summoner_name": FAKE_SUMMONER_NAME,
            "champion_name": "Galio",
            "team": GameTeam.CHAOS,
            "position": GamePlayerPosition.MIDDLE
        },
        {
            "index": 4,
            "summoner_name": FAKE_SUMMONER_NAME,
            "champion_name": "Caitlyn",
            "team": GameTeam.CHAOS,
            "position": GamePlayerPosition.BOTTOM
        },
        {
            "index": 5,
            "summoner_name": FAKE_SUMMONER_NAME,
            "champion_name": "Thresh",
            "team": GameTeam.CHAOS,
            "position": GamePlayerPosition.SUPPORT
        },
    ],
}


class Header:
    def __rich__(self) -> Panel:
        grid = Table.grid(expand=True, pad_edge=False)
        grid.add_column()
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="right")
        grid.add_row(
            Panel(
                "left side"
            ),
            Panel(
                "middle",
            ),
            Panel(
                "right side"
            )
        )

        return Panel(grid)

class Footer:
    def __rich__(self) -> Panel:
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="center")
        grid.add_column(justify="right", ratio=1)

        return Panel(grid)

# will need to process the game data and split the teams out and such

class PlayerCard:
    def __init__(self, player_data: dict, assets: dict | None = None):
        self.player_data = player_data
        self.assets = assets or {}

    def __rich__(self) -> Panel:
        grid = Table.grid(expand=True, pad_edge=False)
        grid.add_column(justify="center")

        champion_name = self.player_data.get("champion_name")
        grid.add_row(
            Panel(f"[bold]{champion_name}[/]", style="featherstorm_bg", box=MINIMAL_DOUBLE_HEAD, padding=(0, 0))
        )
        grid.add_section()

        title = self.player_data.get("position")
        subtitle = f"[gold]{self.player_data.get("summoner_name")}[/]"

        border_style = None
        team = self.player_data.get("team")
        if team == GameTeam.ORDER:
            border_style = "blue"
        else:
            border_style = "red"
            title, subtitle = subtitle, title

        return Panel(grid, title=title, subtitle=subtitle, border_style=border_style)

def make_layout() -> Layout:
    """Define the layout."""
    layout = Layout(name="root")

    header_size = 5
    footer_size = header_size
    layout.split_column(
        Layout(Header(), name="header", size=header_size),
        Layout(name="your_team"),
        Layout(name="other_team"),
        Layout(Footer(), name="footer", size=footer_size),
    )

    your_team = []
    for entry in FAKE_DATA.get(GameTeam.ORDER):
        card = Layout(PlayerCard(entry), name=f"player_{entry.get('index')}")
        your_team.append(card)

    other_team = []
    for entry in FAKE_DATA.get(GameTeam.CHAOS):
        card = Layout(PlayerCard(entry), name=f"player_{entry.get('index')}")
        other_team.append(card)

    layout["your_team"].split_row(*your_team)
    layout["other_team"].split_row(*other_team)
    return layout


def main():
    layout = make_layout()
    console.print(layout)

if __name__ == "__main__":
    main()
