import typer

from typing import Optional

from league import config
from league.console import print

app = typer.Typer(name="cfg", no_args_is_help=True, help="Configuration commands")


@app.command(name="view", help="View your saved config")
def view_cfg(category: Optional[str] = None):
    cfg = config.get_full_config()
    if category is not None:
        print(f"Category {category}:")
        print(cfg.get(category))
    else:
        print("Saved config:")
        print(cfg)


@app.command(name="get", help="Get a saved config value")
def get_cfg_value(category: str, key: str):
    value = config.get(key, category)
    print(f"[featherstorm]{category + '.' if category else ''}{key}[/]=[gold]{value}[/]")


@app.command(name="set", help="Set a saved config value")
def set_cfg_value(category: str, key: str, value: str):
    config.set(key, value, category)
    print(f"[featherstorm]{category + '.' if category else ''}{key}[/]=[gold]{value}[/]")


@app.command(name="clear", help="Clear a saved config value")
def clear_cfg_value(category: str, key: str):
    config.delete(key, category)
    print(f"Cleared [featherstorm]{category + '.' if category else ''}{key}[/]")


@app.command(name="reset", help="Reset saved configuration back to defaults")
def reset_cfg(force: Optional[bool] = False):
    if config.init(force):
        print("Config reset.")
    else:
        print("Config not reset, specify the --force flag to confirm your reset.")
