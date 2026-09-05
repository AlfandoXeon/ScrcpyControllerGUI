"""
CommandPreviewDialog — shows the full scrcpy command string for debugging.
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class CommandPreviewDialog(QDialog):
    """
    Displays the full scrcpy command that would be run.
    Provides a Copy button for easy debugging.
    """

    def __init__(self, command: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._command = command
        self.setWindowTitle("Command Preview")
        self.setMinimumWidth(560)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        layout.addWidget(QLabel("Generated scrcpy command:"))

        self._text = QPlainTextEdit(self._command)
        self._text.setReadOnly(True)
        self._text.setMinimumHeight(80)
        layout.addWidget(self._text)

        copy_btn = QPushButton("Copy Command")
        copy_btn.clicked.connect(self._copy)

        close_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_box.rejected.connect(self.accept)

        layout.addWidget(copy_btn)
        layout.addWidget(close_box)

    def update_command(self, command: str) -> None:
        """Update the displayed command (e.g. when config changes while dialog is open)."""
        self._command = command
        self._text.setPlainText(command)

    def _copy(self) -> None:
        QApplication.clipboard().setText(self._command)
