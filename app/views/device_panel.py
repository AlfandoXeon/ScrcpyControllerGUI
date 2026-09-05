"""
DevicePanel — tab for device selection, status, and management.
"""

import html
import logging
from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.models.device import Device, DeviceState
from app.utils.paths import paths
from app.utils.platform import open_folder_in_explorer


class DevicePanel(QWidget):
    """
    Displays the device selector, connection status, and action buttons.

    Signals:
        refresh_requested(): User clicked Refresh.
        device_info_requested(): User clicked Device Info.
        wireless_requested(): User clicked Wireless ADB.
        device_changed(serial): Selected device serial changed.
    """

    refresh_requested = pyqtSignal()
    device_info_requested = pyqtSignal()
    wireless_requested = pyqtSignal()
    device_changed = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._devices: list[Device] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # Device selector
        device_group = QGroupBox("Device")
        device_layout = QVBoxLayout(device_group)
        device_layout.setSpacing(10)
        device_layout.setContentsMargins(10, 14, 10, 10)

        self._device_combo = QComboBox()
        self._device_combo.setSizePolicy(
            self._device_combo.sizePolicy().horizontalPolicy(),
            self._device_combo.sizePolicy().verticalPolicy(),
        )
        self._device_combo.currentIndexChanged.connect(self._on_device_changed)
        device_layout.addWidget(self._device_combo)

        # Status row
        status_row = QHBoxLayout()
        status_row.setSpacing(6)
        status_label_title = QLabel("Status:")
        status_label_title.setStyleSheet("color: #888888;")
        self._status_indicator = QLabel("●")
        self._status_indicator.setFixedWidth(18)
        self._status_indicator.setStyleSheet("font-size: 11pt; color: #555555;")
        self._status_text = QLabel("Not connected")
        self._status_text.setStyleSheet("font-weight: bold;")
        status_row.addWidget(status_label_title)
        status_row.addWidget(self._status_indicator)
        status_row.addWidget(self._status_text)
        status_row.addStretch()
        device_layout.addLayout(status_row)

        # Message label (for unauthorized / offline hints)
        self._message_label = QLabel("")
        self._message_label.setWordWrap(True)
        self._message_label.setStyleSheet(
            "color: #f0a040; background: #2a2015; border: 1px solid #5a4010; "
            "border-radius: 3px; padding: 6px 8px; font-size: 8pt;"
        )
        self._message_label.setVisible(False)
        device_layout.addWidget(self._message_label)

        layout.addWidget(device_group)

        # Action buttons
        btn_layout = QHBoxLayout()
        self._refresh_btn = QPushButton("Refresh")
        self._info_btn = QPushButton("Device Info")
        self._wireless_btn = QPushButton("Wireless ADB")

        self._refresh_btn.clicked.connect(self.refresh_requested)
        self._info_btn.clicked.connect(self.device_info_requested)
        self._wireless_btn.clicked.connect(self.wireless_requested)

        self._info_btn.setEnabled(False)

        btn_layout.addWidget(self._refresh_btn)
        btn_layout.addWidget(self._info_btn)
        btn_layout.addWidget(self._wireless_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Application Log Section
        layout.addWidget(self._create_log_group(), 1)

    def _create_log_group(self) -> QGroupBox:
        """Construct the live Application Log viewer section."""
        log_group = QGroupBox("Application Log")
        log_layout = QVBoxLayout(log_group)
        log_layout.setSpacing(8)
        log_layout.setContentsMargins(10, 12, 10, 10)

        # Controls bar
        ctrl_bar = QHBoxLayout()
        ctrl_bar.setSpacing(8)

        lbl_desc = QLabel("Real-time system and runtime diagnostics")
        lbl_desc.setStyleSheet("color: #7b889b; font-size: 11px;")
        ctrl_bar.addWidget(lbl_desc)
        ctrl_bar.addStretch()

        self._auto_scroll_cb = QCheckBox("Auto-scroll")
        self._auto_scroll_cb.setChecked(True)
        self._auto_scroll_cb.setStyleSheet("font-size: 11px; color: #8b9bb4;")
        ctrl_bar.addWidget(self._auto_scroll_cb)

        self._clear_log_btn = QPushButton("Clear")
        self._clear_log_btn.setToolTip("Clear current log display")
        self._clear_log_btn.clicked.connect(self._on_clear_log)
        ctrl_bar.addWidget(self._clear_log_btn)

        self._copy_log_btn = QPushButton("Copy")
        self._copy_log_btn.setToolTip("Copy all displayed logs to clipboard")
        self._copy_log_btn.clicked.connect(self._on_copy_log)
        ctrl_bar.addWidget(self._copy_log_btn)

        self._open_log_folder_btn = QPushButton("Open Folder")
        self._open_log_folder_btn.setToolTip("Open the logs directory in Explorer")
        self._open_log_folder_btn.clicked.connect(self._on_open_log_folder)
        ctrl_bar.addWidget(self._open_log_folder_btn)

        log_layout.addLayout(ctrl_bar)

        # Console Text Area
        self._log_edit = QPlainTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setMaximumBlockCount(2000)
        self._log_edit.setMinimumHeight(200)
        self._log_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._log_edit.setStyleSheet(
            "QPlainTextEdit {"
            "  background-color: #12151a;"
            "  color: #abb2bf;"
            "  border: 1px solid #232833;"
            "  border-radius: 4px;"
            "  padding: 6px 8px;"
            "  font-family: Consolas, 'Courier New', monospace;"
            "  font-size: 11px;"
            "  line-height: 1.4;"
            "}"
        )
        log_layout.addWidget(self._log_edit)

        # Preload recent log lines if file exists
        self._preload_recent_logs()

        return log_group

    def _preload_recent_logs(self) -> None:
        """Preload the last 40 lines of the existing application.log file."""
        log_file = paths.log_file
        if not log_file.exists():
            return
        try:
            lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
            recent_lines = lines[-40:] if len(lines) > 40 else lines
            for line in recent_lines:
                lvl = logging.INFO
                if " [ERROR   ]" in line or " [CRITICAL]" in line:
                    lvl = logging.ERROR
                elif " [WARNING ]" in line:
                    lvl = logging.WARNING
                elif " [DEBUG   ]" in line:
                    lvl = logging.DEBUG
                self.append_log(line, level=lvl, scroll=False)
            self._scroll_log_to_bottom()
        except Exception:
            pass

    def append_log(self, text: str, level: int = logging.INFO, scroll: bool = True) -> None:
        """Append a log message to the log viewer with color formatting."""
        if not text:
            return

        # Syntax color based on log level
        if level >= logging.ERROR:
            color = "#e06c75"  # Red
        elif level >= logging.WARNING:
            color = "#e5c07b"  # Amber
        elif level <= logging.DEBUG:
            color = "#6c778a"  # Muted Gray
        else:
            color = "#98c379"  # Green

        escaped = html.escape(text)
        formatted_html = f"<span style='color: {color}; white-space: pre-wrap;'>{escaped}</span>"
        self._log_edit.appendHtml(formatted_html)

        if scroll and self._auto_scroll_cb.isChecked():
            self._scroll_log_to_bottom()

    def _scroll_log_to_bottom(self) -> None:
        sb = self._log_edit.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _on_clear_log(self) -> None:
        self._log_edit.clear()

    def _on_copy_log(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self._log_edit.toPlainText())

    def _on_open_log_folder(self) -> None:
        open_folder_in_explorer(paths.log_file.parent)

    # -------------------------------------------------------------------------
    # Public update methods
    # -------------------------------------------------------------------------

    def update_devices(self, devices: list[Device]) -> None:
        """Populate the device combo box with the given list."""
        self._devices = devices
        self._device_combo.blockSignals(True)
        self._device_combo.clear()

        if not devices:
            self._device_combo.addItem("No device detected")
            self._update_status_display(None)
        else:
            for device in devices:
                self._device_combo.addItem(device.display_name, userData=device.serial)
            self._update_status_display(devices[0] if devices else None)

        self._device_combo.blockSignals(False)

        # Trigger info for currently selected device
        current = self.selected_device()
        self._info_btn.setEnabled(current is not None and current.is_ready)

    def selected_device(self) -> Optional[Device]:
        """Return the currently selected Device, or None."""
        idx = self._device_combo.currentIndex()
        if idx < 0 or idx >= len(self._devices):
            return None
        return self._devices[idx]

    def select_device_by_serial(self, serial: str) -> None:
        """Select device by serial (restores previous selection)."""
        for i, d in enumerate(self._devices):
            if d.serial == serial:
                self._device_combo.setCurrentIndex(i)
                return

    # -------------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------------

    def _on_device_changed(self, index: int) -> None:
        device = self.selected_device()
        if device:
            self._update_status_display(device)
            self._info_btn.setEnabled(device.is_ready)
            self.device_changed.emit(device.serial)
        else:
            self._update_status_display(None)
            self._info_btn.setEnabled(False)

    def _update_status_display(self, device: Optional[Device]) -> None:
        """Update the colored status indicator and message."""
        BASE_STYLE = "font-size: 11pt; font-weight: bold;"
        if device is None:
            self._status_indicator.setStyleSheet(f"{BASE_STYLE} color: #555555;")
            self._status_text.setText("No device detected")
            self._status_text.setStyleSheet("color: #888888; font-weight: bold;")
            self._set_message("")
            return

        state = device.state
        if state == DeviceState.DEVICE:
            self._status_indicator.setStyleSheet(f"{BASE_STYLE} color: #3ddc5a;")
            self._status_text.setText("Connected")
            self._status_text.setStyleSheet("color: #3ddc5a; font-weight: bold;")
            self._set_message("")
        elif state == DeviceState.UNAUTHORIZED:
            self._status_indicator.setStyleSheet(f"{BASE_STYLE} color: #f0a040;")
            self._status_text.setText("Unauthorized")
            self._status_text.setStyleSheet("color: #f0a040; font-weight: bold;")
            self._set_message("USB debugging authorization is required. Please unlock your device and allow USB debugging.")
        elif state == DeviceState.OFFLINE:
            self._status_indicator.setStyleSheet(f"{BASE_STYLE} color: #e05050;")
            self._status_text.setText("Offline")
            self._status_text.setStyleSheet("color: #e05050; font-weight: bold;")
            self._set_message("Device is offline. Try reconnecting the USB cable.")
        else:
            self._status_indicator.setStyleSheet(f"{BASE_STYLE} color: #666666;")
            self._status_text.setText("Unknown")
            self._status_text.setStyleSheet("color: #888888; font-weight: bold;")
            self._set_message("")

    def _set_message(self, message: str) -> None:
        if message:
            self._message_label.setText(message)
            self._message_label.setVisible(True)
        else:
            self._message_label.setText("")
            self._message_label.setVisible(False)
