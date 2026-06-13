import typer
import asyncio

from league.dragon import DataDragon
from league.console import print

app = typer.Typer(name="dragon", no_args_is_help=True, help="DataDragon API commands")


@app.command(name="item", help="Get item info by ID")
def dragon_item(item_id: int):
    async def run():
        dragon = DataDragon()
        await dragon.initialize()
        item = await dragon.get_item(item_id)
        if item is None:
            print(f"[bold red]Item {item_id} not found[/bold red]")
            return
        print(item)

    asyncio.run(run())


@app.command(name="champion", help="Get champion info by ID")
def dragon_champion(champion_id: int):
    async def run():
        dragon = DataDragon()
        await dragon.initialize()
        champion = await dragon.get_champion(champion_id)
        if champion is None:
            print(f"[bold red]Champion {champion_id} not found[/bold red]")
            return
        print(champion)

    asyncio.run(run())
