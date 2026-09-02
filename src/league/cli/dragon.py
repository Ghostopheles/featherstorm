import typer
import asyncio

from pathlib import Path

from league.ui import output
from league.markup import format_file_path
from league.ui.renderers import item_panel
from league.dragon import DataDragon, ArtAssetType

app = typer.Typer(name="dragon", no_args_is_help=True, help="DataDragon API commands")


async def _resolve_item_names(dragon: DataDragon, ids: list[str] | None) -> list[str]:
    if not ids:
        return []

    names = []
    for id_str in ids:
        item = await dragon.get_item(int(id_str))
        names.append(item.name if item else id_str)
    return names


@app.command(name="item", help="Get item info by ID")
def dragon_item(item_id: int):
    async def run():
        dragon = DataDragon()
        await dragon.initialize()
        item = await dragon.get_item(item_id)
        if item is None:
            output.error(f"Item {item_id} not found")
            return

        builds_from = await _resolve_item_names(dragon, item.builds_from)
        builds_into = await _resolve_item_names(dragon, item.builds_into)
        output.print(item_panel(item, item_id, builds_from, builds_into))

    asyncio.run(run())


@app.command(name="champion", help="Get champion info by ID")
def dragon_champion(champion_id: int):
    async def run():
        dragon = DataDragon()
        await dragon.initialize()
        champion = await dragon.get_champion(champion_id)
        if champion is None:
            output.error(f"Champion {champion_id} not found")
            return
        output.print(champion)

    asyncio.run(run())


@app.command(name="art", help="Get champion splash art by name")
def dragon_splash(champion_name: str, skin: int = 0, asset_type: ArtAssetType = ArtAssetType.splash, output_path: Path | None = None):
    filename = f"{asset_type.title()}_{champion_name}"

    if asset_type == ArtAssetType.square:
        filename += ".png"
    else:
        filename += f"_{skin}.jpg"

    if output_path is None:
        output_path = Path.cwd() / filename
    else:
        output_path = output_path.expanduser().resolve()
        if output_path.is_dir():
            output_path = output_path / filename

    async def run():
        dragon = DataDragon()
        await dragon.initialize()

        asset = await dragon.get_art_by_champion_name(champion_name, skin, asset_type)
        if asset is None:
            output.error(f"Champion {champion_name} not found")
            return

        output_path.write_bytes(asset)
        output.success(f"Saved splash art to {format_file_path(output_path)}")

    asyncio.run(run())
