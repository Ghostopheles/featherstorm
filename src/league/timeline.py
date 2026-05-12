from typing import Optional
from dataclasses import dataclass

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

class MatchTimelineAnalyzer:
    HIGHLIGHT_RULES: set[Predicate[TimelineEvent]] = None

    targetParticipantID: int
    timeline: MatchTimeline

    def __init__(self, targetParticipantID: int, timeline: MatchTimeline):
        self.targetParticipantID = targetParticipantID
        self.timeline = timeline

        self.__init_rules()

    def __init_rules(self):
        self.HIGHLIGHT_RULES = { # using OR logic
            event_type_is("CHAMPION_KILL") & event_caused_by_participant(self.targetParticipantID),
            event_type_is("ELITE_MONSTER_KILL") & event_assisted_by_participant(self.targetParticipantID),
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

        events = [
            HighlightEvent(type=event.type, timestamp=event.timestamp, position=event.position)
                for event in relevant_events
            ]
        return events

@dataclass
class HighlightEvent:
    type: str
    timestamp: int # in seconds
    position: Optional[PositionDto] = None

    def __post_init__(self):
        self.timestamp = self.timestamp // 1000
