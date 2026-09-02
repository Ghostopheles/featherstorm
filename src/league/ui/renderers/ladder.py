from typing import Optional
from collections.abc import Iterable

from rich.console import RenderableType

from league.models import LeagueEntry
from league.ui.renderers.matches import new_table


def ranked_ladder_table(entries: Iterable[LeagueEntry], names: dict[str, str], title: str = "") -> RenderableType:
    """`names` maps puuid -> already-resolved display name."""
    table = new_table(title)
    table.add_column("#", width=3)
    table.add_column("Name", width=30)
    table.add_column("Record", width=11, justify="center")
    table.add_column("Winrate", width=7, justify="center")
    table.add_column("LP", width=5)

    for i, entry in enumerate(entries, 1):
        total_games = entry.wins + entry.losses
        winrate = int((entry.wins / total_games) * 100) if total_games else 0
        winrate_str = f"[red]{winrate}[/]%" if winrate < 50 else f"[green]{winrate}[/]%"

        table.add_row(
            f"{i}",
            names.get(entry.puuid) or "N/A",
            f"{entry.wins}[green]W[/] : {entry.losses}[red]L[/]",
            winrate_str,
            f"{entry.leaguePoints} LP",
        )

    return table


def format_ladder_name(game_name: Optional[str], tag_line: Optional[str]) -> Optional[str]:
    if not game_name:
        return None
    return f"{game_name}[dim]#{tag_line}[/]"
