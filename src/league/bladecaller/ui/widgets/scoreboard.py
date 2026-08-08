from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from league.bladecaller.core.match import ScoreRow
from league.bladecaller.ui.widgets.champion_icon import ChampionIcon

ICON_SIZE = 24
KDA_WIDTH = 42
GOLD_WIDTH = 60


class Scoreboard(QWidget):
    """Ten-player result grid, blue team over red team.

    Only rendered when the Riot API supplied the full lobby — the LCU match
    history endpoint returns the current summoner alone.
    """

    def __init__(self, rows: list[ScoreRow], parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        blue = [r for r in rows if r.is_blue]
        red = [r for r in rows if not r.is_blue]

        for label, team, side in (("Blue Team", blue, "blue"), ("Red Team", red, "red")):
            if not team:
                continue
            layout.addWidget(_team_pill(label, side))
            layout.addWidget(_header_row())
            for row in team:
                layout.addWidget(_score_row(row))


def _team_pill(text: str, side: str) -> QLabel:
    pill = QLabel(text.upper())
    pill.setObjectName("teamPill")
    pill.setProperty("team", side)
    pill.setAlignment(Qt.AlignCenter)
    pill.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
    return pill


def _row_frame() -> tuple[QFrame, QHBoxLayout]:
    frame = QFrame()
    frame.setObjectName("scoreRow")
    frame.setAttribute(Qt.WA_StyledBackground, True)
    layout = QHBoxLayout(frame)
    layout.setContentsMargins(8, 4, 8, 4)
    layout.setSpacing(4)
    return frame, layout


def _header_row() -> QFrame:
    frame, layout = _row_frame()

    spacer = QLabel()
    spacer.setFixedWidth(ICON_SIZE)
    layout.addWidget(spacer)

    name = QLabel("PLAYER")
    name.setObjectName("scoreHeader")
    layout.addWidget(name, 1)

    for text, width in (("K", KDA_WIDTH), ("D", KDA_WIDTH), ("A", KDA_WIDTH), ("GOLD", GOLD_WIDTH)):
        cell = QLabel(text)
        cell.setObjectName("scoreHeader")
        cell.setFixedWidth(width)
        cell.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(cell)

    return frame


def _score_row(row: ScoreRow) -> QFrame:
    frame, layout = _row_frame()
    if row.is_you:
        frame.setProperty("you", "true")

    icon = ChampionIcon(ICON_SIZE)
    icon.set_champion(row.champion_id, row.champion_name)
    layout.addWidget(icon)

    name = QLabel(row.display_name)
    name.setObjectName("scoreName")
    name.setToolTip(row.champion_name or row.display_name)
    layout.addWidget(name, 1)

    cells = (
        ("scoreKills", str(row.kills), KDA_WIDTH),
        ("scoreDeaths", str(row.deaths), KDA_WIDTH),
        ("scoreAssists", str(row.assists), KDA_WIDTH),
        ("scoreGold", f"{row.gold:,}", GOLD_WIDTH),
    )
    for object_name, text, width in cells:
        cell = QLabel(text)
        cell.setObjectName(object_name)
        cell.setFixedWidth(width)
        cell.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(cell)

    return frame
