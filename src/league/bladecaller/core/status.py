from enum import StrEnum


class ClientStatus(StrEnum):
    """League client / match state shown by the sidebar indicator.

    Values double as the QSS `state` property used to color the dot.
    """

    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    IN_MATCH = "match"


STATUS_LABELS: dict[ClientStatus, str] = {
    ClientStatus.DISCONNECTED: "Client Offline",
    ClientStatus.CONNECTED: "Client Connected",
    ClientStatus.IN_MATCH: "In Match",
}

STATUS_TOOLTIPS: dict[ClientStatus, str] = {
    ClientStatus.DISCONNECTED: "League client is not running",
    ClientStatus.CONNECTED: "League client is running, no game in progress",
    ClientStatus.IN_MATCH: "Game in progress",
}
