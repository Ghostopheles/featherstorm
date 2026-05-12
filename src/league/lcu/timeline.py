from typing import Optional
from dataclasses import dataclass

from league.lcu.models import LCUTimeline, LCUTimelineEvent, MapPosition
from league.predicates import rule, Predicate

@rule
def event_type_is(type_name: str, obj: LCUTimelineEvent, **kwargs) -> bool:
    """Match events of a specific type. Args: ["CHAMPION_KILL"]"""
    return obj.type == type_name

@rule
def event_caused_by_participant(targetParticipantID: int, obj: LCUTimelineEvent, **kwargs) -> bool:
    """Match events caused by a specific participant. Args: [1]"""
    return obj.killerId == targetParticipantID

@rule
def event_assisted_by_participant(targetParticipantID: int, obj: LCUTimelineEvent, **kwargs) -> bool:
    """Match events assisted by a specific participant. Args: [1]"""
    return obj.assistingParticipantIds is not None and targetParticipantID in obj.assistingParticipantIds

@rule
def event_victim_is_participant(targetParticipantID: int, obj: LCUTimelineEvent, **kwargs) -> bool:
    """Match events where the victim is a specific participant. Args: [1]"""
    return obj.victimId == targetParticipantID

class LCUTimelineAnalyzer:
    HIGHLIGHT_RULES: set[Predicate[LCUTimelineEvent]] = None

    def __init__(self, targetParticipantID: int, timeline: LCUTimeline):
        self.targetParticipantID = targetParticipantID
        self.timeline = timeline

        self.__init_rules()

    def __init_rules(self):
        self.HIGHLIGHT_RULES = { # using OR logic
            event_type_is("CHAMPION_KILL") & event_victim_is_participant(self.targetParticipantID),
            event_type_is("ELITE_MONSTER_KILL") & event_assisted_by_participant(self.targetParticipantID),
        }

    def __is_event_relevant(self, event: LCUTimelineEvent) -> bool:
        for rule in self.HIGHLIGHT_RULES:
            if rule(event):
                return True

        return False

    def __get_relevant_events(self) -> list[LCUTimelineEvent]:
        events = []
        for frame in self.timeline.frames:
            for event in frame.events:
                if self.__is_event_relevant(event):
                    events.append(event)

        return events

    def get_highlight_events(self) -> list["LCUHighlightEvent"]:
        relevant_events = self.__get_relevant_events()

        events = [
            LCUHighlightEvent(type=event.type, timestamp=event.timestamp, position=event.position)
                for event in relevant_events
            ]
        return events

    def get_all_events(self) -> list[LCUTimelineEvent]:
        events = []
        for frame in self.timeline.frames:
            events.extend(frame.events)

        return events


@dataclass
class LCUHighlightEvent:
    type: str
    timestamp: int # in seconds
    position: Optional[MapPosition] = None

    def __post_init__(self):
        self.timestamp = self.timestamp // 1000
