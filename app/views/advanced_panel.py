"""
AdvancedPanel — tab for behavior options and custom arguments.
"""

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.models.config import ScrcpyConfig
from app.services.command_builder import ScrcpyCapabilities
from app.utils.validators import validate_custom_args


class AdvancedPanel(QWidget):
    """
    Behavior checkboxes, custom arguments input, and command preview button.

    Signals:
        show_command_requested(): User clicked Show Command.
    """

    show_command_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._caps = ScrcpyCapabilities()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # -- Behavior group ---------------------------------------------------
        behavior_group = QGroupBox("Behavior")
        behavior_form = QFormLayout(behavior_group)
        behavior_form.setSpacing(6)

        if self._caps.SUPPORTS_STAY_AWAKE:
            self._stay_awake_check = QCheckBox("Stay Awake")
            behavior_form.addRow(self._stay_awake_check)
        else:
            self._stay_awake_check = None

        if self._caps.SUPPORTS_TURN_SCREEN_OFF:
            self._screen_off_check = QCheckBox("Turn Screen Off")
            behavior_form.addRow(self._screen_off_check)
        else:
            self._screen_off_check = None

        if self._caps.SUPPORTS_SHOW_TOUCHES:
            self._show_touches_check = QCheckBox("Show Touches")
            behavior_form.addRow(self._show_touches_check)
        else:
            self._show_touches_check = None

        layout.addWidget(behavior_group)

        # -- Custom args group ------------------------------------------------
        custom_group = QGroupBox("Custom Arguments")
        custom_layout = QVBoxLayout(custom_group)
        custom_layout.setSpacing(6)

        custom_layout.addWidget(QLabel("Extra scrcpy arguments (space-separated):"))

        self._custom_args_edit = QPlainTextEdit()
        self._custom_args_edit.setPlaceholderText("e.g. --no-control --prefer-text")
        self._custom_args_edit.setMaximumHeight(70)
        self._custom_args_edit.textChanged.connect(self._validate_custom_args)
        custom_layout.addWidget(self._custom_args_edit)

        self._args_error_label = QLabel("")
        self._args_error_label.setStyleSheet("color: #c0392b;")
        self._args_error_label.setVisible(False)
        custom_layout.addWidget(self._args_error_label)

        # Show command button
        show_cmd_btn = QPushButton("Show Command Preview")
        show_cmd_btn.clicked.connect(self.show_command_requested)
        custom_layout.addWidget(show_cmd_btn)

        layout.addWidget(custom_group)
        layout.addStretch()

    def _validate_custom_args(self) -> None:
        raw = self._custom_args_edit.toPlainText()
        valid, err = validate_custom_args(raw)
        if not valid:
            self._args_error_label.setText(err)
            self._args_error_label.setVisible(True)
        else:
            self._args_error_label.setText("")
            self._args_error_label.setVisible(False)

    def custom_args_valid(self) -> bool:
        raw = self._custom_args_edit.toPlainText()
        valid, _ = validate_custom_args(raw)
        return valid

    # -------------------------------------------------------------------------
    # Config I/O
    # -------------------------------------------------------------------------

    def get_config_values(self, config: ScrcpyConfig) -> None:
        if self._stay_awake_check:
            config.stay_awake = self._stay_awake_check.isChecked()
        if self._screen_off_check:
            config.turn_screen_off = self._screen_off_check.isChecked()
        if self._show_touches_check:
            config.show_touches = self._show_touches_check.isChecked()
        config.custom_args = self._custom_args_edit.toPlainText().strip()

    def apply_config(self, config: ScrcpyConfig) -> None:
        if self._stay_awake_check:
            self._stay_awake_check.setChecked(config.stay_awake)
        if self._screen_off_check:
            self._screen_off_check.setChecked(config.turn_screen_off)
        if self._show_touches_check:
            self._show_touches_check.setChecked(config.show_touches)
        self._custom_args_edit.setPlainText(config.custom_args)
