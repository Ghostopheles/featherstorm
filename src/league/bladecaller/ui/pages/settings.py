import copy

from typing import Any
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from league.bladecaller.core.settings_schema import SCHEMA, SECTION_LABELS, SettingField
from league.bladecaller.ui.components import Page
from league.bladecaller.ui.settings.editors import make_editor


def _humanize(key: str) -> str:
    return key.replace("_", " ").capitalize()


class SettingsPage(Page):
    settings_applied = Signal(dict)

    def __init__(self, config: dict[str, dict[str, Any]], parent=None):
        super().__init__("Settings", "Configuration shared with the CLI", parent)
        self._defaults = copy.deepcopy(config)
        self._editors: dict[tuple[str, str], Any] = {}

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 8, 0)
        body_layout.setSpacing(14)

        for section, entries in config.items():
            group = QGroupBox(SECTION_LABELS.get(section, _humanize(section)).upper())
            form = QFormLayout(group)
            form.setRowWrapPolicy(QFormLayout.DontWrapRows)
            form.setHorizontalSpacing(16)
            form.setVerticalSpacing(8)
            for key, value in entries.items():
                field = SCHEMA.get(f"{section}.{key}", SettingField())
                editor = make_editor(value, field)
                if field.tooltip:
                    editor.widget.setToolTip(field.tooltip)
                form.addRow(field.label or _humanize(key), editor.widget)
                self._editors[(section, key)] = editor
            body_layout.addWidget(group)

        body_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(body)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        apply_btn = QPushButton("Apply")
        apply_btn.setProperty("accent", "true")
        reset_btn = QPushButton("Restore defaults")
        apply_btn.clicked.connect(lambda: self.settings_applied.emit(self.values()))
        reset_btn.clicked.connect(lambda: self.load(self._defaults))

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(reset_btn)
        buttons.addWidget(apply_btn)

        self.content.addWidget(scroll, 1)
        self.content.addLayout(buttons)

    def values(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        for (section, key), editor in self._editors.items():
            out.setdefault(section, {})[key] = editor.get()
        return out

    def load(self, config: dict[str, dict[str, Any]]) -> None:
        for (section, key), editor in self._editors.items():
            if key in config.get(section, {}):
                editor.set(config[section][key])
