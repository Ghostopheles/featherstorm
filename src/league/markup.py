from pathlib import Path
from typing import Union, Optional

from league.enums import GameTeam

# Pure markup-string helpers - no rich import, safe for backend log/report messages.

KDA_POOR = 1.0
KDA_GREAT = 4.0


def format_file_path(path: Union[Path, str]) -> str:
    if isinstance(path, Path):
        path = path.as_posix()

    return f"[file][link=file://{path}]{path}[/link][/]"


def format_url(url: str, display_text: Optional[str] = None) -> str:
    return f"[url][link={url}]{display_text or url}[/link][/]"


def format_result(win: bool) -> str:
    return "[bold green]WIN[/bold green]" if win else "[bold red]LOSS[/bold red]"


def format_duration(seconds: int) -> str:
    return f"[green]{seconds // 60}[/]m"


def kda_ratio(kills: int, deaths: int, assists: int) -> float:
    return (kills + assists) / max(1, deaths)


def format_kda(kills: int, deaths: int, assists: int) -> tuple[str, str]:
    """Returns the rendered KDA cell and the row style it implies."""
    ratio = kda_ratio(kills, deaths, assists)
    left = f"{ratio:.2f}".rjust(5)

    row_style = ""
    if ratio < KDA_POOR:
        left = f"[bold red]{left}[/]"
        row_style = "less_dim"
    elif ratio > KDA_GREAT:
        left = f"[bold green]{left}[/]"

    return f"KDA {left} : {kills}/{deaths}/{assists}", row_style


def format_player(name: str, champion: Optional[str] = None, team: Optional[GameTeam] = None) -> str:
    display = f"{name} [bold white]({champion})[/bold white]" if champion else name
    if team == GameTeam.ORDER:
        return f"[bold blue]{display}[/bold blue]"
    if team == GameTeam.CHAOS:
        return f"[bold red]{display}[/bold red]"
    return display
