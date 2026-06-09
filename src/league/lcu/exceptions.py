class LCUInvalidMatchException(Exception):
    matchID: int

class LCUInvalidReplayException(Exception):
    matchID: int

class LCUMissingReplayMetadataException(Exception):
    matchID: int

class LCUIncompatibleReplayException(Exception):
    matchID: int
