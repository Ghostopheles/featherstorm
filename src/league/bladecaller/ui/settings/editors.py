from dataclasses import dataclass
from typing import Any, Callable

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QToolButton,
    QWidget,
)


@dataclass
class Editor:
    widget: QWidget
    get: Callable[[], Any]
    set: Callable[[Any], None]


def _path_editor(value: str, field, want_dir: bool) -> Editor:
    container = QWidget()
    row = QHBoxLayout(container)
    row.setContentsMargins(0, 0, 0, 0)
    line = QLineEdit(value)
    browse = QToolButton(text="…")
    row.addWidget(line, 1)
    row.addWidget(browse)

    def pick():
        if want_dir:
            p = QFileDialog.getExistingDirectory(container, "Select folder", line.text())
        else:
            p, _ = QFileDialog.getOpenFileName(container, "Select file", line.text())
        if p:
            line.setText(p)

    browse.clicked.connect(pick)
    return Editor(container, line.text, line.setText)


def make_editor(value: Any, field) -> Editor:
    if field.kind in ("dir", "file"):
        return _path_editor(str(value), field, field.kind == "dir")

    if field.kind == "choice":
        box = QComboBox()
        box.addItems(field.choices)
        box.setCurrentText(str(value))
        return Editor(box, box.currentText, lambda v: box.setCurrentText(str(v)))

    # bool BEFORE int — bool is a subclass of int
    if isinstance(value, bool):
        cb = QCheckBox()
        cb.setChecked(value)
        return Editor(cb, cb.isChecked, cb.setChecked)

    # numeric-looking string with bounds -> spinbox that stringifies
    if field.as_str:
        sb = QSpinBox()
        sb.setRange(int(field.minimum or 0), int(field.maximum or 10**6))
        sb.setValue(int(value))
        return Editor(sb, lambda: str(sb.value()), lambda v: sb.setValue(int(v)))

    if isinstance(value, int):
        sb = QSpinBox()
        sb.setRange(int(field.minimum if field.minimum is not None else -(10**9)), int(field.maximum if field.maximum is not None else 10**9))
        sb.setSuffix(field.suffix)
        sb.setValue(value)
        return Editor(sb, sb.value, sb.setValue)

    if isinstance(value, float):
        sb = QDoubleSpinBox()
        sb.setDecimals(field.decimals if field.decimals is not None else 3)
        sb.setSingleStep(field.step or 0.1)
        sb.setRange(field.minimum if field.minimum is not None else -1e9, field.maximum if field.maximum is not None else 1e9)
        sb.setSuffix(field.suffix)
        sb.setValue(value)
        return Editor(sb, sb.value, sb.setValue)

    line = QLineEdit(str(value))
    if field.kind == "secret":
        line.setEchoMode(QLineEdit.Password)
    return Editor(line, line.text, line.setText)
