import os
import typer
import asyncio

from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Annotated

from league import config
from league.markup import format_file_path
from league.highlights import HighlightManager
from league.ui import output, RichProgressReporter
from league.ui.renderers.highlights import highlight_pick_table
from league.riot_api import LOL_REGION
from league.enums import QueueChoice, resolve_queue

from league.cli._shared import try_get_cfg_or_input

app = typer.Typer(name="highlights", no_args_is_help=True, help="Highlight capture commands")

REPORTER_PREFIX = r"[highlights]\[highlights][/]: "


@app.command(name="capture", help="Capture highlights from a match (defaults to your last match).")
def capture_highlights(
    match_id: Annotated[Optional[str], typer.Argument(help="Match ID (NA1_123 or 123). Defaults to your last match.")] = None,
    game_path: Optional[Path] = None,
    export_path: Optional[Path] = None,
    name: Optional[str] = config.get("companion.default_player_name"),
    tagline: Optional[str] = config.get("companion.default_player_tagline"),
    count: Optional[int] = 2,
    queue_type: Annotated[QueueChoice, typer.Option(help="Queue Type", case_sensitive=False)] = None,
    pick: Annotated[bool, typer.Option("--pick", help="List highlights and choose one to capture (ignores --count)")] = False,
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
                output.print(f"Saved client install path ({format_file_path(game_path)}) to config")
            else:
                raise SystemError("you've given me a bungus game path")

    if export_path is None:
        path, was_input = try_get_cfg_or_input("highlights", "export_path", "Highlights export path")
        export_path = Path(path)
        if was_input:
            if export_path.exists() and export_path.is_dir():
                config.set("highlights.export_path", export_path.as_posix())
                output.print(f"Saved highlight export path ({format_file_path(export_path)}) to config")
            else:
                raise SystemError("you've given me a bungus export path")

    async def run():
        reporter = RichProgressReporter(prefix=REPORTER_PREFIX)
        highlights = await HighlightManager.create(name, tagline, game_path, export_path, api_key, reporter)
        if match_id is None:
            target_match_id = await highlights.get_last_match_id(queue_type)
        elif match_id.isdigit():
            target_match_id = f"{LOL_REGION.upper()}_{match_id}"
        else:
            target_match_id = match_id.upper()

        if not pick:
            await highlights.capture_highlights_for_match(target_match_id, numHighlights=count)
            return

        events = await highlights.get_highlight_events(target_match_id)
        events.sort(key=lambda e: e.timestamp)
        if not events:
            output.warning("No highlights found for this match")
            return

        output.print(highlight_pick_table(events))
        choice = 0
        while not 1 <= choice <= len(events):
            answer = output.prompt(f"Pick a highlight (1-{len(events)})").strip()
            choice = int(answer) if answer.isdigit() else 0

        await highlights.capture_highlights_for_match(target_match_id, events=[events[choice - 1]], index_offset=choice - 1)

    asyncio.run(run())
