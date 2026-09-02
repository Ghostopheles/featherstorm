import re

from rich.box import ROUNDED
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.console import Group, RenderableType

from league.models import DragonItem

# DDragon ships descriptions as pseudo-HTML. Map known tags -> Rich markup.
_DESC_TAGS = {
    "stats": ("[gold]", "[/gold]"),
    "attention": ("[bold white]", "[/bold white]"),
    "active": ("[bold rakan]", "[/bold rakan]"),
    "passive": ("[bold xayah]", "[/bold xayah]"),
    "keyword": ("[bold]", "[/bold]"),
    "rules": ("[dim italic]", "[/dim italic]"),
    "magicDamage": ("[blue]", "[/blue]"),
    "physicalDamage": ("[red]", "[/red]"),
    "trueDamage": ("[gold]", "[/gold]"),
    "healing": ("[green]", "[/green]"),
    "scaleAP": ("[blue]", "[/blue]"),
    "scaleAD": ("[red]", "[/red]"),
}

_STAT_ABBR = {
    "Flat": "",
    "Percent": "%",
    "Mod": "",
    "HPPool": "Health",
    "MPPool": "Mana",
    "MagicDamage": "Ability Power",
    "PhysicalDamage": "Attack Damage",
    "SpellBlock": "Magic Resist",
    "HPRegen": "Health Regen",
    "MPRegen": "Mana Regen",
    "MovementSpeed": "Move Speed",
    "CritChance": "Crit Chance",
    "AttackSpeed": "Attack Speed",
}


def _humanize_stat(key: str) -> str:
    is_percent = key.startswith("Percent")
    for raw, friendly in _STAT_ABBR.items():
        key = key.replace(raw, friendly)
    key = re.sub(r"(?<!^)(?=[A-Z])", " ", key)
    key = re.sub(r"\s+", " ", key).strip()
    return f"{key} (%)" if is_percent else key


def _clean_description(desc: str) -> Text:
    # Leading <stats> block duplicates the stat table - drop it.
    desc = re.sub(r"<stats>.*?</stats>", "", desc, flags=re.DOTALL)
    desc = re.sub(r"</?mainText>", "", desc)
    desc = re.sub(r"<br\s*/?>", "\n", desc)

    def repl(m: re.Match) -> str:
        closing, tag = m.group(1), m.group(2)
        markup = _DESC_TAGS.get(tag)
        if markup is None:
            return ""
        return markup[1] if closing else markup[0]

    desc = re.sub(r"<(/?)(\w+)>", repl, desc)
    desc = re.sub(r"\n{3,}", "\n\n", desc).strip()
    return Text.from_markup(desc)


def item_panel(item: DragonItem, item_id: int, builds_from: list[str] | None = None, builds_into: list[str] | None = None) -> RenderableType:
    """`builds_from`/`builds_into` are already-resolved item names."""
    sections = []

    if item.plaintext:
        sections.append(Text(item.plaintext, style="italic light_gray"))

    if item.stats:
        stat_table = Table.grid(padding=(0, 2))
        stat_table.add_column(style="gold", justify="right")
        stat_table.add_column(style="bold")
        for key, value in item.stats.items():
            num = value * 100 if key.startswith("Percent") else value
            num = int(num) if num == int(num) else num
            stat_table.add_row(f"+{num}", _humanize_stat(key))
        sections.append(stat_table)

    if item.description:
        sections.append(_clean_description(item.description))

    if builds_from:
        sections.append(Text.from_markup(f"[dark_rakan]Builds from:[/] {', '.join(builds_from)}"))
    if builds_into:
        sections.append(Text.from_markup(f"[dark_rakan]Builds into:[/] {', '.join(builds_into)}"))

    if item.tags:
        chips = Columns([Text(f" {t} ", style="featherstorm_bg") for t in item.tags], padding=(0, 1))
        sections.append(chips)

    gold = item.gold
    subtitle = Text.from_markup(f"[gold]{gold.total}g[/] total   [eminence_dim]{gold.base}g combine[/]   [eminence_dim]{gold.sell}g sell[/]")

    return Panel(
        Group(*sections),
        title=Text.from_markup(f"[featherstorm]{item.name}[/] [light_gray]#{item_id}[/]"),
        subtitle=subtitle,
        border_style="xayah",
        box=ROUNDED,
        padding=(1, 2),
    )
