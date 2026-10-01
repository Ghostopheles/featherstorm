from rich.align import Align
from rich.console import RenderableType

from league.timeline import HighlightEvent
from league.ui.renderers.matches import new_table


def highlight_pick_table(events: list[HighlightEvent], title: str = "") -> RenderableType:
    table = new_table(title)
    table.add_column("#", width=3)
    table.add_column("Time", width=8, highlight=True)
    table.add_column("Killed", style="eminence")

    for i, event in enumerate(events, start=1):
        killed = ", ".join(event.victim_champion_names) or "-"
        table.add_row(str(i), f"{event.timestamp // 60}:{event.timestamp % 60:02d}", killed)

    return Align.center(table)
