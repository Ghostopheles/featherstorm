from typing import Optional
from dataclasses import dataclass

from league.lcu.models import LCUTimeline, LCUTimelineEvent, LCUTimelineFrame, MapPosition


class LCUTimelineAnalyzer:
    HIGHLIGHT_EVENTS = {"CHAMPION_KILL"}

    def __init__(self, targetParticipantID: int, timeline: LCUTimeline):
        self.targetParticipantID = targetParticipantID
        self.timeline = timeline

    def get_relevant_events(self) -> list[LCUTimelineEvent]:
        events = []
        for frame in self.timeline.frames:
            for event in frame.events:
                if event.type not in self.HIGHLIGHT_EVENTS:
                    continue

                if (event.participantId == self.targetParticipantID) or (self.targetParticipantID in event.assistingParticipantIds):
                    events.append(event)

        return events

    def get_highlight_info(self) -> list["LCUHighlightEvent"]:
        relevant_events = self.get_relevant_events()

        events = []
        for event in relevant_events:
            events.append(LCUHighlightEvent(type=event.type, timestamp=event.timestamp, position=event.position))

        return events


@dataclass
class LCUHighlightEvent:
    type: str
    timestamp: int
    position: Optional[MapPosition] = None
