import os
import typer
import asyncio

from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Annotated

from league import config
from league.highlights import HighlightManager
from league.console import print, format_file_path
from league.enums import QueueChoice, resolve_queue

from league.cli._shared import try_get_cfg_or_input

app = typer.Typer(name="highlights", no_args_is_help=True, help="Highlight capture commands")


@app.command(name="capture", help="Capture highlights from your last match.")
def capture_highlights(
    game_path: Optional[Path] = None,
    export_path: Optional[Path] = None,
    name: Optional[str] = config.get("companion.default_player_name"),
    tagline: Optional[str] = config.get("companion.default_player_tagline"),
    count: Optional[int] = 2,
    queue_type: Annotated[QueueChoice, typer.Option(help="Queue Type", case_sensitive=False)] = None,
):
    load_dotenv()
    api_key = os.getenv("RIOT_API_KEY")

    if queue_type is not None:
        queue_type = resolve_queue(queue_type)

    if game_path is None:
        path, was_input = try_get_cfg_or_input("lcu", "client_install_path", "League of Legends install path")
        game_path = Path(path)
        if was_input:
            if game_path.exists() and game_path.is_dir():
                config.set("lcu.client_install_path", game_path.as_posix())
                print(f"Saved client install path ({format_file_path(game_path)}) to config")
            else:
                raise SystemError("you've given me a bungus game path")

    if export_path is None:
        path, was_input = try_get_cfg_or_input("highlights", "export_path", "Highlights export path")
        export_path = Path(path)
        if was_input:
            if export_path.exists() and export_path.is_dir():
                config.set("highlights.export_path", export_path.as_posix())
                print(f"Saved highlight export path ({format_file_path(export_path)}) to config")
            else:
                raise SystemError("you've given me a bungus export path")

    async def run():
        highlights = await HighlightManager.create(name, tagline, game_path, export_path, api_key)
        last_match_id = await highlights.get_last_match_id(queue_type)
        await highlights.capture_highlights_for_match(last_match_id, numHighlights=count)

    asyncio.run(run())
