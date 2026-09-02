import os
import typer

from pathlib import Path
from dotenv import load_dotenv

from league import config
from league.ui import output
from league.riot_api import RiotAPIClient

default_client_path = Path(config.get("lcu.client_install_path"))


def try_get_cfg_or_input(category: str, key: str, prompt: str, *args, **kwargs):
    value = config.get(key, category)
    if value is not None:
        return value, False

    value = output.prompt(prompt, *args, **kwargs)
    return value, True


def _riot_client() -> RiotAPIClient:
    load_dotenv()
    api_key = os.getenv("RIOT_API_KEY")
    if not api_key:
        output.error("RIOT_API_KEY not set")
        raise typer.Exit(1)
    return RiotAPIClient(api_key)
