from rich.table import Table
from rich.console import RenderableType

from league.crawler.database import STATES, CrawlStats
from league.ui.renderers.matches import new_table

STATE_STYLES = {
    "discovered": "rakan",
    "claimed": "eminence",
    "expanded": "success",
    "failed": "error",
}


def crawl_stats_table(stats: CrawlStats, title: str = "") -> RenderableType:
    table: Table = new_table(title)
    table.add_column("State", width=12, style="highlights")
    table.add_column("Summoners", width=12, justify="right")
    table.add_column("Matches", width=12, justify="right")

    for state in STATES:
        style = STATE_STYLES.get(state, "")
        table.add_row(
            f"[{style}]{state}[/]" if style else state,
            f"{stats.summoners.get(state, 0):,}",
            f"{stats.matches.get(state, 0):,}",
        )

    table.add_row(
        "[bold]total[/]",
        f"[bold]{stats.total_summoners:,}[/]",
        f"[bold]{stats.total_matches:,}[/]",
    )
    if stats.requests:
        table.add_row(
            "[dim]per request[/]",
            "",
            f"[dim]{stats.matches_per_request:.1f}[/]",
        )

    return table
