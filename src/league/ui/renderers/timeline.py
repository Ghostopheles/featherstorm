from dataclasses import dataclass

from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.console import Group, RenderableType

from league.models import MatchTimeline


_EVENT_PRIORITY: dict[str, int] = {"multi": 4, "kill": 3, "death": 2, "assist": 1}
_EVENT_STYLES: dict[str, tuple[str, str]] = {
    "kill": ("bold green", "K"),
    "death": ("bold red", "D"),
    "assist": ("bold yellow", "A"),
    "multi": ("bold magenta", "M"),
}


@dataclass
class _PlayerTimelineEvent:
    timestamp_ms: int
    kind: str
    detail: str


def player_timeline_panel(
    timeline: MatchTimeline,
    participant_id: int,
    participant_champions: dict[int, str] | None = None,
    game_duration_seconds: int | None = None,
    bar_width: int = 82,
) -> RenderableType:
    participant_champions = participant_champions or {}
    pid = participant_id
    inner = bar_width - 2

    last_frame_ms = timeline.info.frames[-1].timestamp if timeline.info.frames else 60_000
    game_duration_ms = (game_duration_seconds * 1000) if game_duration_seconds else last_frame_ms
    game_duration_s = max(game_duration_ms // 1000, 1)

    evs: list[_PlayerTimelineEvent] = []
    for frame in timeline.info.frames:
        for e in frame.events:
            if e.type == "CHAMPION_SPECIAL_KILL" and e.killerId == pid and e.killType == "KILL_MULTI":
                length = e.multiKillLength or 2
                name = {2: "Double", 3: "Triple", 4: "Quadra", 5: "Penta"}.get(length, f"{length}x")
                evs.append(_PlayerTimelineEvent(e.timestamp, "multi", f"{name} Kill"))
            elif e.type == "CHAMPION_KILL":
                if e.killerId == pid:
                    victim = participant_champions.get(e.victimId, f"#{e.victimId}") if e.victimId else "?"
                    evs.append(_PlayerTimelineEvent(e.timestamp, "kill", f"Killed {victim}"))
                elif e.victimId == pid:
                    killer = participant_champions.get(e.killerId, f"#{e.killerId}") if e.killerId else "?"
                    evs.append(_PlayerTimelineEvent(e.timestamp, "death", f"Killed by {killer}"))
                elif e.assistingParticipantIds and pid in e.assistingParticipantIds:
                    victim = participant_champions.get(e.victimId, f"#{e.victimId}") if e.victimId else "?"
                    evs.append(_PlayerTimelineEvent(e.timestamp, "assist", f"Assisted on {victim}"))

    evs.sort(key=lambda e: e.timestamp_ms)

    # build bar
    cells: list[tuple[str, str] | None] = [None] * inner
    for ev in evs:
        pos = int(ev.timestamp_ms / game_duration_ms * inner)
        pos = max(0, min(inner - 1, pos))
        existing = cells[pos]
        if existing is None or _EVENT_PRIORITY[ev.kind] > _EVENT_PRIORITY[existing[0]]:
            cells[pos] = (ev.kind, _EVENT_STYLES[ev.kind][1])

    bar = Text()
    bar.append("├", style="dim")
    for cell in cells:
        if cell is None:
            bar.append("─", style="dim")
        else:
            bar.append(cell[1], style=_EVENT_STYLES[cell[0]][0])
    bar.append("┤", style="dim")

    # timestamp label row aligned to bar positions
    label_chars = [" "] * bar_width
    t = 0
    while t <= game_duration_s:
        pos = 1 + int(t / game_duration_s * inner)
        lbl = f"{t // 60}:{t % 60:02}"
        for i, ch in enumerate(lbl):
            if pos + i < bar_width:
                label_chars[pos + i] = ch
        t += 300
    label_row = Text("".join(label_chars), style="dim")

    # legend
    legend = Text()
    for kind in ("kill", "death", "assist", "multi"):
        style, label = _EVENT_STYLES[kind]
        legend.append(f" {label}", style=style)
        legend.append(f" {kind}  ", style="dim")

    # detail table
    table = Table(show_header=False, box=None, show_edge=False, padding=(0, 1, 0, 0))
    table.add_column("time", width=5, style="dim")
    table.add_column("ev", width=1, no_wrap=True)
    table.add_column("detail")
    for ev in evs:
        ts_s = ev.timestamp_ms // 1000
        mins, secs = divmod(ts_s, 60)
        style, label = _EVENT_STYLES[ev.kind]
        table.add_row(f"{mins:02}:{secs:02}", Text(label, style=style), ev.detail)

    content = Group(label_row, bar, Text(""), legend, Text(""), table)
    return Panel(content, title="[featherstorm]Player Timeline[/]", border_style="dark_xayah")
