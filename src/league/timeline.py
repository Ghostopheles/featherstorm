from typing import Optional
from bisect import bisect_left
from dataclasses import dataclass, field

from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.console import Group, RenderableType

from league.models import (
    TimelineEvent,
    MatchTimeline,
    PositionDto,
)
from league.predicates import rule, Predicate


@rule
def event_type_is(type_name: str, obj: TimelineEvent, **kwargs) -> bool:
    """Match events of a specific type. Args: ["CHAMPION_KILL"]"""
    return obj.type == type_name


@rule
def event_caused_by_participant(targetParticipantID: int, obj: TimelineEvent, **kwargs) -> bool:
    """Match events caused by a specific participant. Args: [1]"""
    return obj.killerId == targetParticipantID


@rule
def event_assisted_by_participant(targetParticipantID: int, obj: TimelineEvent, **kwargs) -> bool:
    """Match events assisted by a specific participant. Args: [1]"""
    return obj.assistingParticipantIds is not None and targetParticipantID in obj.assistingParticipantIds


@rule
def event_victim_is_participant(targetParticipantID: int, obj: TimelineEvent, **kwargs) -> bool:
    """Match events where the victim is a specific participant. Args: [1]"""
    return obj.victimId == targetParticipantID


@rule
def event_is_kill_type(kill_type: str, obj: TimelineEvent, **kwargs) -> bool:
    """Match events with a specific killType. Args: [killType]"""
    return obj.killType == kill_type


@rule
def event_has_multikill_length(length: int, obj: TimelineEvent, **kwargs) -> bool:
    """Match multikill events with at least the specified killstreak length. Args: [1]"""
    return obj.multiKillLength is not None and obj.multiKillLength >= length


BATCH_WINDOW_MS = 20_000


class ParticipantPositionTrack:
    """Sparse position samples for one participant, indexed by frame timestamp (ms). Linear interp between samples."""

    timestamps_ms: list[int]
    positions: list[PositionDto]

    def __init__(self, timeline: MatchTimeline, participantID: int):
        self.timestamps_ms = []
        self.positions = []
        key = str(participantID)
        for frame in timeline.info.frames:
            pframe = frame.participantFrames.get(key)
            if pframe is None or pframe.position is None:
                continue
            self.timestamps_ms.append(frame.timestamp)
            self.positions.append(pframe.position)

    def position_at(self, timestamp_ms: int) -> Optional[PositionDto]:
        if not self.timestamps_ms:
            return None
        if timestamp_ms <= self.timestamps_ms[0]:
            return self.positions[0]
        if timestamp_ms >= self.timestamps_ms[-1]:
            return self.positions[-1]
        i = bisect_left(self.timestamps_ms, timestamp_ms)
        t0, t1 = self.timestamps_ms[i - 1], self.timestamps_ms[i]
        p0, p1 = self.positions[i - 1], self.positions[i]
        frac = (timestamp_ms - t0) / (t1 - t0)
        return PositionDto(
            x=int(p0.x + (p1.x - p0.x) * frac),
            y=int(p0.y + (p1.y - p0.y) * frac),
        )


class MatchTimelineAnalyzer:
    HIGHLIGHT_RULES: set[Predicate[TimelineEvent]] = None

    targetParticipantID: int
    timeline: MatchTimeline
    target_track: ParticipantPositionTrack
    participant_champions: dict[int, str]

    def __init__(self, targetParticipantID: int, timeline: MatchTimeline, participant_champions: dict[int, str] | None = None):
        self.targetParticipantID = targetParticipantID
        self.timeline = timeline
        self.target_track = ParticipantPositionTrack(timeline, targetParticipantID)
        self.participant_champions = participant_champions or {}

        self.__init_rules()

    def __init_rules(self):
        self.HIGHLIGHT_RULES = {
            event_type_is("CHAMPION_SPECIAL_KILL")
            & (event_caused_by_participant(self.targetParticipantID) & event_is_kill_type("KILL_MULTI") & event_has_multikill_length(2))
        }

    def __is_event_relevant(self, event: TimelineEvent) -> bool:
        for rule in self.HIGHLIGHT_RULES:
            if rule(event):
                return True

        return False

    def __get_relevant_events(self) -> list[TimelineEvent]:
        relevant = []
        events = self.get_all_events()
        for event in events:
            if self.__is_event_relevant(event):
                relevant.append(event)

        return relevant

    def get_all_events(self) -> list[TimelineEvent]:
        events = []
        for frame in self.timeline.info.frames:
            events.extend(frame.events)

        return events

    def get_highlight_events(self) -> list["HighlightEvent"]:
        relevant_events = self.__get_relevant_events()
        relevant_events.sort(key=lambda e: e.timestamp)

        batches: list[list[TimelineEvent]] = []
        for event in relevant_events:
            if batches and event.timestamp - batches[-1][-1].timestamp <= BATCH_WINDOW_MS:
                batches[-1].append(event)
            else:
                batches.append([event])

        all_events = self.get_all_events()
        highlights = []
        for batch in batches:
            batch_start = batch[0].timestamp - BATCH_WINDOW_MS
            batch_end = batch[-1].timestamp + BATCH_WINDOW_MS
            victim_ids = [
                e.victimId
                for e in all_events
                if e.type == "CHAMPION_KILL" and e.killerId == self.targetParticipantID and batch_start <= e.timestamp <= batch_end and e.victimId is not None
            ]
            victim_names = [self.participant_champions[vid] for vid in victim_ids if vid in self.participant_champions]
            highlights.append(
                HighlightEvent(
                    timestamp=batch[0].timestamp,
                    events=batch,
                    position=batch[0].position,
                    victim_champion_names=victim_names,
                )
            )
        return highlights


@dataclass
class HighlightEvent:
    timestamp: int  # first event, in seconds
    events: list["TimelineEvent"]
    position: PositionDto
    victim_champion_names: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.timestamp = self.timestamp // 1000

    @property
    def type(self) -> str:
        return self.events[0].type if self.events else ""

    @property
    def event_length(self) -> int:
        """Span in seconds from first to last event in the batch. 0 for single-event highlights."""
        if len(self.events) <= 1:
            return 0
        return (self.events[-1].timestamp // 1000) - (self.events[0].timestamp // 1000)


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


def render_player_timeline(
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
