"""
WirelessDialog — UI for connecting/disconnecting wireless ADB devices.
"""

from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.utils.validators import is_valid_ip, is_valid_port


class WirelessDialog(QDialog):
    """
    Dialog for wireless ADB connect/disconnect.

    Signals:
        connect_requested(ip, port): User clicked Connect.
        disconnect_requested(ip, port): User clicked Disconnect.
    """

    connect_requested = pyqtSignal(str, int)
    disconnect_requested = pyqtSignal(str, int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Wireless ADB")
        self.setMinimumWidth(320)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        form = QFormLayout()
        form.setSpacing(6)

        self._ip_edit = QLineEdit()
        self._ip_edit.setPlaceholderText("e.g. 192.168.1.10")
        self._ip_edit.setMaxLength(45)

        self._port_spin = QSpinBox()
        self._port_spin.setMinimum(1)
        self._port_spin.setMaximum(65535)
        self._port_spin.setValue(5555)

        form.addRow("IP Address:", self._ip_edit)
        form.addRow("Port:", self._port_spin)
        layout.addLayout(form)
        layout.addSpacing(4)

        # Buttons
        btn_layout = QHBoxLayout()
        self._connect_btn = QPushButton("Connect")
        self._disconnect_btn = QPushButton("Disconnect")
        close_btn = QPushButton("Close")

        self._connect_btn.clicked.connect(self._on_connect)
        self._disconnect_btn.clicked.connect(self._on_disconnect)
        close_btn.clicked.connect(self.accept)

        btn_layout.addWidget(self._connect_btn)
        btn_layout.addWidget(self._disconnect_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        # Status label
        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

    def _validate(self) -> bool:
        ip = self._ip_edit.text().strip()
        port = self._port_spin.value()
        if not is_valid_ip(ip):
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid IP address.")
            self._ip_edit.setFocus()
            return False
        if not is_valid_port(port):
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid port (1–65535).")
            return False
        return True

    def _on_connect(self) -> None:
        if not self._validate():
            return
        self.set_status("Connecting...")
        self.connect_requested.emit(
            self._ip_edit.text().strip(),
            self._port_spin.value(),
        )

    def _on_disconnect(self) -> None:
        if not self._validate():
            return
        self.set_status("Disconnecting...")
        self.disconnect_requested.emit(
            self._ip_edit.text().strip(),
            self._port_spin.value(),
        )

    def set_status(self, message: str) -> None:
        """Update the in-dialog status label."""
        self._status_label.setText(message)
