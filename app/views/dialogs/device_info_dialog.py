"""
DeviceInfoDialog — displays detailed information about a selected device.
"""

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QClipboard
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.models.device import Device


class DeviceInfoDialog(QDialog):
    """
    Shows device model, manufacturer, Android version, SDK, serial, and connection type.
    Provides a Copy button to copy all info to clipboard.
    """

    def __init__(self, device: Device, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._device = device
        self.setWindowTitle("Device Information")
        self.setMinimumWidth(360)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(6)

        d = self._device

        fields = [
            ("Model",        d.model or "—"),
            ("Manufacturer", d.manufacturer or "—"),
            ("Android",      d.android_version or "—"),
            ("SDK",          d.sdk_version or "—"),
            ("Serial",       d.serial),
            ("State",        d.state.value.capitalize()),
            ("Connection",   d.connection_type_label),
        ]

        for label, value in fields:
            value_label = QLabel(value)
            value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            value_label.setWordWrap(True)
            form.addRow(f"{label}:", value_label)

        layout.addLayout(form)
        layout.addSpacing(8)

        # Buttons
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self._copy_to_clipboard)

        close_btn = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_btn.rejected.connect(self.accept)

        layout.addWidget(copy_btn)
        layout.addWidget(close_btn)

    def _copy_to_clipboard(self) -> None:
        """Copy all device info as plain text to clipboard."""
        d = self._device
        text = (
            f"Model:        {d.model or '—'}\n"
            f"Manufacturer: {d.manufacturer or '—'}\n"
            f"Android:      {d.android_version or '—'}\n"
            f"SDK:          {d.sdk_version or '—'}\n"
            f"Serial:       {d.serial}\n"
            f"State:        {d.state.value}\n"
            f"Connection:   {d.connection_type_label}\n"
        )
        QApplication.clipboard().setText(text)
