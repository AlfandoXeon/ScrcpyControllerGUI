"""
Tests for ADB Tools (Reboot, ADB Shell), QtLogHandler, and live Application Log.
"""

import logging
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication

# Ensure single QApplication exists for GUI tests
app = QApplication.instance() or QApplication([])

from app.services.adb_service import ADBService
from app.utils.logger import QtLogHandler
from app.views.tools_panel import ToolsPanel
from app.views.device_panel import DevicePanel


def test_adb_service_reboot_system():
    service = ADBService()
    with patch.object(service, "run", return_value=(0, "rebooting", "")) as mock_run:
        ok, msg = service.reboot_device("device_abc", "system")
        assert ok is True
        mock_run.assert_called_once_with(["-s", "device_abc", "reboot"], timeout=12)


def test_adb_service_reboot_recovery():
    service = ADBService()
    with patch.object(service, "run", return_value=(0, "", "")) as mock_run:
        ok, msg = service.reboot_device("device_abc", "recovery")
        assert ok is True
        mock_run.assert_called_once_with(["-s", "device_abc", "reboot", "recovery"], timeout=12)


def test_adb_service_reboot_bootloader():
    service = ADBService()
    with patch.object(service, "run", return_value=(0, "", "")) as mock_run:
        ok, msg = service.reboot_device("device_abc", "bootloader")
        assert ok is True
        mock_run.assert_called_once_with(["-s", "device_abc", "reboot", "bootloader"], timeout=12)


def test_qt_log_handler_emission():
    handler = QtLogHandler()
    received = []

    def _on_log(msg: str, levelno: int):
        received.append((msg, levelno))

    handler.log_emitted.connect(_on_log)

    record = logging.LogRecord(
        name="test_logger",
        level=logging.WARNING,
        pathname="test.py",
        lineno=10,
        msg="Test warning message",
        args=(),
        exc_info=None,
    )
    handler.emit(record)

    assert len(received) == 1
    msg, lvl = received[0]
    assert lvl == logging.WARNING
    assert "Test warning message" in msg


def test_device_panel_log_widget():
    panel = DevicePanel()
    assert hasattr(panel, "_log_edit")
    assert hasattr(panel, "_clear_log_btn")
    assert hasattr(panel, "_copy_log_btn")
    assert hasattr(panel, "_open_log_folder_btn")

    # Append test log
    panel.append_log("Diagnostic test message", level=logging.INFO)
    content = panel._log_edit.toPlainText()
    assert "Diagnostic test message" in content

    # Clear log
    panel._on_clear_log()
    assert panel._log_edit.toPlainText() == ""


def test_tools_panel_signals():
    panel = ToolsPanel()
    assert hasattr(panel, "reboot_requested")
    assert hasattr(panel, "adb_shell_requested")

    reboot_signals = []
    panel.reboot_requested.connect(lambda mode: reboot_signals.append(mode))
    panel.reboot_requested.emit("recovery")
    assert reboot_signals == ["recovery"]
