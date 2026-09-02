import typer
import asyncio

from league.constants import APP_NAME
from league.ui import output, setup_logging
from league.companion import run_companion

from league.cli import lcu, cfg, riot, dragon, highlights

app = typer.Typer(name=APP_NAME, no_args_is_help=True, add_completion=False)


@app.callback()
def app_main():
    setup_logging()
    output.rule(f"[featherstorm]{APP_NAME.title()}[/]")


@app.command(name="companion", help="Runs Featherstorm in 'companion' mode alongside your current match.")
def companion():
    asyncio.run(run_companion())


app.add_typer(lcu.app)
app.add_typer(cfg.app)
app.add_typer(riot.app)
app.add_typer(highlights.app)
app.add_typer(dragon.app)
