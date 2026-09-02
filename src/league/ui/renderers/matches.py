from rich import box
from rich.align import Align
from rich.table import Table
from rich.console import RenderableType

from league.ui.viewmodels import MatchRow
from league.markup import format_kda, format_result, format_duration


UNKNOWN_POSITIONS = {"N/A", "Unknown"}


def new_table(title: str = "", **kwargs) -> Table:
    return Table(
        title=title,
        show_header=True,
        border_style="rakan",
        header_style="featherstorm",
        box=box.ROUNDED,
        show_lines=True,
        **kwargs,
    )


def match_table(rows: list[MatchRow], title: str = "") -> RenderableType:
    show_position = any(row.position for row in rows)
    show_game_mode = any(row.game_mode for row in rows)

    table = new_table(title)
    table.add_column("#", width=3)
    if show_position:
        table.add_column("Position", width=15, style="highlights")
    table.add_column("Champion", width=15, style="eminence")
    table.add_column("Result", width=8)
    table.add_column("KDA Ratio : K/D/A", width=20)
    table.add_column("Duration", width=8, highlight=True)
    if show_game_mode:
        table.add_column("Game Mode", width=10)
    table.add_column("Queue Type", width=14)
    table.add_column("Match ID", width=15)

    for row in rows:
        kda, row_style = format_kda(row.kills, row.deaths, row.assists)

        cells = [f"{row.index}"]
        if show_position:
            position = row.position or ""
            cells.append(f"[dim]{position}[/]" if position in UNKNOWN_POSITIONS else position)
        cells.append(row.champion)
        cells.append(format_result(row.win))
        cells.append(kda)
        cells.append(format_duration(row.duration_s))
        if show_game_mode:
            cells.append(row.game_mode or "")
        cells.append(row.queue_name)
        cells.append(row.match_id)

        table.add_row(*cells, style=row_style)

    return Align.center(table)
