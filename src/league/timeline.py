from typing import Optional
from bisect import bisect_left
from dataclasses import dataclass, field

from league.enums import ReplaySequenceEasing
from league.models import TimelineFrame, TimelineEvent, TimelineInfo, TimelineParticipant, MatchTimeline, PositionDto
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


BATCH_WINDOW_MS = 15_000
DEFAULT_CLIP_WINDOW_MS = 15_000
MAX_KEYFRAME_JUMP = 5000  # units; drops clip endpoints where participant-frame interpolation is unreliable


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

    def __init__(self, targetParticipantID: int, timeline: MatchTimeline):
        self.targetParticipantID = targetParticipantID
        self.timeline = timeline
        self.target_track = ParticipantPositionTrack(timeline, targetParticipantID)

        self.__init_rules()

    def __init_rules(self):
        self.HIGHLIGHT_RULES = {  # using OR logic
            event_type_is("CHAMPION_KILL") & event_caused_by_participant(self.targetParticipantID),
            event_type_is("ELITE_MONSTER_KILL")
            & (event_caused_by_participant(self.targetParticipantID) | event_assisted_by_participant(self.targetParticipantID)),
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

    def get_highlight_events(self, clip_window_ms: int = DEFAULT_CLIP_WINDOW_MS) -> list["HighlightEvent"]:
        relevant_events = self.__get_relevant_events()
        relevant_events.sort(key=lambda e: e.timestamp)

        batches: list[list[TimelineEvent]] = []
        for event in relevant_events:
            if batches and event.timestamp - batches[-1][-1].timestamp <= BATCH_WINDOW_MS:
                batches[-1].append(event)
            else:
                batches.append([event])

        half_clip_ms = clip_window_ms // 2
        return [
            HighlightEvent(
                timestamp=batch[0].timestamp,
                events=batch,
                positions=self.__build_keyframes(batch, half_clip_ms),
            )
            for batch in batches
        ]

    def __build_keyframes(self, batch: list[TimelineEvent], half_clip_ms: int) -> list["PositionKeyframe"]:
        """Build camera keyframes spanning [first_event - half_clip, last_event + half_clip].

        Sources:
          - Clip endpoints: interpolated target-participant position from participantFrames.
          - Each event in batch: event.position when present, else interpolated target position.
        Deduplicates adjacent identical positions.
        """
        first_ms = batch[0].timestamp
        last_ms = batch[-1].timestamp
        clip_start_ms = max(0, first_ms - half_clip_ms)
        clip_end_ms = last_ms + half_clip_ms

        raw: list[tuple[int, Optional[PositionDto]]] = []
        raw.append((clip_start_ms, self.target_track.position_at(clip_start_ms)))
        for event in batch:
            pos = event.position if event.position is not None else self.target_track.position_at(event.timestamp)
            raw.append((event.timestamp, pos))
        raw.append((clip_end_ms, self.target_track.position_at(clip_end_ms)))

        keyframes: list[PositionKeyframe] = []
        for ts_ms, pos in raw:
            if pos is None:
                continue
            if keyframes and keyframes[-1].position.x == pos.x and keyframes[-1].position.y == pos.y:
                continue
            if keyframes:
                prev = keyframes[-1].position
                dist = ((pos.x - prev.x) ** 2 + (pos.y - prev.y) ** 2) ** 0.5
                if dist > MAX_KEYFRAME_JUMP:
                    continue
            keyframes.append(PositionKeyframe(timestamp=ts_ms, position=pos))
        return keyframes


@dataclass
class PositionKeyframe:
    timestamp: int  # absolute game seconds
    position: PositionDto

    def __post_init__(self):
        self.timestamp = self.timestamp // 1000


@dataclass
class HighlightEvent:
    timestamp: int  # first event, in seconds
    events: list["TimelineEvent"]
    positions: list[PositionKeyframe] = field(default_factory=list)

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
        return self.events[-1].timestamp - self.events[0].timestamp
