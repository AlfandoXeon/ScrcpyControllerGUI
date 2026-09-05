"""
WindowPanel — tab for scrcpy window options.
"""

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.config import ScrcpyConfig
from app.services.command_builder import ScrcpyCapabilities


class WindowPanel(QWidget):
    """
    Configuration controls for the scrcpy window: fullscreen, on-top, borderless, title.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._caps = ScrcpyCapabilities()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        group = QGroupBox("Window")
        form = QFormLayout(group)
        form.setSpacing(8)

        self._fullscreen_check = QCheckBox("Fullscreen")
        form.addRow(self._fullscreen_check)

        if self._caps.SUPPORTS_ALWAYS_ON_TOP:
            self._ontop_check = QCheckBox("Always on Top")
            form.addRow(self._ontop_check)
        else:
            self._ontop_check = None

        if self._caps.SUPPORTS_BORDERLESS:
            self._borderless_check = QCheckBox("Borderless")
            form.addRow(self._borderless_check)
        else:
            self._borderless_check = None

        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("(default: device name)")
        self._title_edit.setMaxLength(256)
        form.addRow("Window Title:", self._title_edit)

        layout.addWidget(group)
        layout.addStretch()

    # -------------------------------------------------------------------------
    # Config I/O
    # -------------------------------------------------------------------------

    def get_config_values(self, config: ScrcpyConfig) -> None:
        config.fullscreen = self._fullscreen_check.isChecked()
        if self._ontop_check:
            config.always_on_top = self._ontop_check.isChecked()
        if self._borderless_check:
            config.borderless = self._borderless_check.isChecked()
        config.window_title = self._title_edit.text().strip()

    def apply_config(self, config: ScrcpyConfig) -> None:
        self._fullscreen_check.setChecked(config.fullscreen)
        if self._ontop_check:
            self._ontop_check.setChecked(config.always_on_top)
        if self._borderless_check:
            self._borderless_check.setChecked(config.borderless)
        self._title_edit.setText(config.window_title)
