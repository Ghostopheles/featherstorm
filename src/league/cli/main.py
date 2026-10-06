import sys
import typer
import asyncio
import importlib

from league.constants import APP_NAME
from league.ui import output, setup_logging

# Subcommand groups are imported on demand so a single command doesn't pay for every group's dependencies
# (surrealdb/aiohttp, chroma, pydantic models, ...). Keys must match each module's Typer `name`.
SUBCOMMAND_MODULES = {
    "lcu": "league.cli.lcu",
    "cfg": "league.cli.cfg",
    "riot": "league.cli.riot",
    "highlights": "league.cli.highlights",
    "replay": "league.cli.replay",
    "dragon": "league.cli.dragon",
    "crawler": "league.cli.crawler",
}

app = typer.Typer(name=APP_NAME, no_args_is_help=True, add_completion=False)


@app.callback()
def app_main():
    setup_logging()
    output.rule(f"[featherstorm]{APP_NAME.title()}[/]")


@app.command(name="companion", help="Runs Featherstorm in 'companion' mode alongside your current match.")
def companion(
    govee: bool = typer.Option(True, "--govee/--no-govee", help="Enable Govee smart light control."),
    discord: bool = typer.Option(True, "--discord/--no-discord", help="Enable Discord Rich Presence."),
    chroma: bool = typer.Option(True, "--chroma/--no-chroma", help="Enable Razer Chroma lighting."),
):
    from league.companion import run_companion

    asyncio.run(run_companion(enable_govee=govee, enable_discord=discord, enable_chroma=chroma))


def _register_subcommands():
    requested = sys.argv[1] if len(sys.argv) > 1 else None
    if requested == "companion":
        return

    # unknown/missing subcommand (e.g. --help) registers everything so help output stays complete
    names = [requested] if requested in SUBCOMMAND_MODULES else list(SUBCOMMAND_MODULES)
    for name in names:
        app.add_typer(importlib.import_module(SUBCOMMAND_MODULES[name]).app)


_register_subcommands()
