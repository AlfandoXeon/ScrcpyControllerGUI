"""
Quick Tools / Device Action Bar View.

Provides direct device control without keyboard shortcuts:
- Direct PC Screenshot capture (ADB exec-out)
- Hardware button key events (Power, Volume, Mute)
- System navigation (Back, Home, Recent Apps, Menu)
- Notification drawer management (Expand, Collapse, Settings)
- Screen rotation controls (Portrait, Landscape, Auto-Rotate)
- Direct text and clipboard dispatch to device

Clean, modern dark aesthetic without emojis.
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QPushButton,
    QLineEdit,
    QLabel,
    QScrollArea,
    QSizePolicy,
)


class ToolsPanel(QWidget):
    """
    Panel providing quick hardware and system action buttons for connected devices.
    """

    # Signals
    screenshot_requested = pyqtSignal()
    open_folder_requested = pyqtSignal()
    rotation_requested = pyqtSignal(str)          # 'portrait', 'landscape', 'auto'
    keyevent_requested = pyqtSignal(int)          # Android keyevent code
    expand_notifications_requested = pyqtSignal()
    collapse_notifications_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    send_text_requested = pyqtSignal(str)
    paste_clipboard_requested = pyqtSignal()
    reboot_requested = pyqtSignal(str)            # 'system', 'recovery', 'bootloader'
    adb_shell_requested = pyqtSignal()

    # Android Keycodes
    KEYCODE_HOME = 3
    KEYCODE_BACK = 4
    KEYCODE_POWER = 26
    KEYCODE_VOLUME_UP = 24
    KEYCODE_VOLUME_DOWN = 25
    KEYCODE_VOLUME_MUTE = 164
    KEYCODE_APP_SWITCH = 187
    KEYCODE_MENU = 82

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 2-column layout for tools
        cols_layout = QHBoxLayout()
        cols_layout.setSpacing(12)

        # Left Column: Screen Capture, Navigation Controls, Display Orientation
        left_col = QVBoxLayout()
        left_col.setSpacing(10)
        left_col.addWidget(self._create_screenshot_group())
        left_col.addWidget(self._create_navigation_group())
        left_col.addWidget(self._create_orientation_group())
        left_col.addStretch(1)
        cols_layout.addLayout(left_col, 1)

        # Right Column: Device Power & ADB Tools, Hardware Buttons, Notifications
        right_col = QVBoxLayout()
        right_col.setSpacing(10)
        right_col.addWidget(self._create_power_adb_group())
        right_col.addWidget(self._create_hardware_group())
        right_col.addWidget(self._create_notification_group())
        right_col.addStretch(1)
        cols_layout.addLayout(right_col, 1)

        layout.addLayout(cols_layout)

        # Full-width Text & Clipboard Input Group
        layout.addWidget(self._create_input_group())

    # -------------------------------------------------------------------------
    # Group Builders
    # -------------------------------------------------------------------------

    def _create_screenshot_group(self) -> QGroupBox:
        grp = QGroupBox("Screen Capture")
        vbox = QVBoxLayout(grp)
        vbox.setSpacing(10)

        hbox = QHBoxLayout()
        self.btn_screenshot = QPushButton("Take Screenshot")
        self.btn_screenshot.setStyleSheet(
            "QPushButton { font-weight: bold; padding: 7px 18px; }"
        )
        self.btn_screenshot.clicked.connect(self.screenshot_requested.emit)

        self.btn_open_folder = QPushButton("Open Screenshots Folder")
        self.btn_open_folder.clicked.connect(self.open_folder_requested.emit)

        hbox.addWidget(self.btn_screenshot, 1)
        hbox.addWidget(self.btn_open_folder, 1)
        vbox.addLayout(hbox)

        self.lbl_screenshot_status = QLabel("Ready to capture screenshot.")
        self.lbl_screenshot_status.setStyleSheet("color: #8b9bb4; font-size: 11px;")
        vbox.addWidget(self.lbl_screenshot_status)

        return grp

    def _create_navigation_group(self) -> QGroupBox:
        grp = QGroupBox("Navigation Controls")
        grid = QGridLayout(grp)
        grid.setSpacing(8)

        btn_back = QPushButton("Back")
        btn_back.clicked.connect(lambda: self.keyevent_requested.emit(self.KEYCODE_BACK))

        btn_home = QPushButton("Home")
        btn_home.clicked.connect(lambda: self.keyevent_requested.emit(self.KEYCODE_HOME))

        btn_recents = QPushButton("Recent Apps")
        btn_recents.clicked.connect(lambda: self.keyevent_requested.emit(self.KEYCODE_APP_SWITCH))

        btn_menu = QPushButton("Menu")
        btn_menu.clicked.connect(lambda: self.keyevent_requested.emit(self.KEYCODE_MENU))

        grid.addWidget(btn_back, 0, 0)
        grid.addWidget(btn_home, 0, 1)
        grid.addWidget(btn_recents, 1, 0)
        grid.addWidget(btn_menu, 1, 1)

        return grp

    def _create_hardware_group(self) -> QGroupBox:
        grp = QGroupBox("Hardware Buttons")
        grid = QGridLayout(grp)
        grid.setSpacing(8)

        btn_power = QPushButton("Power / Lock")
        btn_power.clicked.connect(lambda: self.keyevent_requested.emit(self.KEYCODE_POWER))

        btn_mute = QPushButton("Mute")
        btn_mute.clicked.connect(lambda: self.keyevent_requested.emit(self.KEYCODE_VOLUME_MUTE))

        btn_vol_up = QPushButton("Volume Up")
        btn_vol_up.clicked.connect(lambda: self.keyevent_requested.emit(self.KEYCODE_VOLUME_UP))

        btn_vol_down = QPushButton("Volume Down")
        btn_vol_down.clicked.connect(lambda: self.keyevent_requested.emit(self.KEYCODE_VOLUME_DOWN))

        grid.addWidget(btn_power, 0, 0)
        grid.addWidget(btn_mute, 0, 1)
        grid.addWidget(btn_vol_up, 1, 0)
        grid.addWidget(btn_vol_down, 1, 1)

        return grp

    def _create_orientation_group(self) -> QGroupBox:
        grp = QGroupBox("Display Orientation")
        grid = QGridLayout(grp)
        grid.setSpacing(8)

        btn_portrait = QPushButton("Portrait")
        btn_portrait.clicked.connect(lambda: self.rotation_requested.emit("portrait"))

        btn_landscape = QPushButton("Landscape")
        btn_landscape.clicked.connect(lambda: self.rotation_requested.emit("landscape"))

        btn_auto = QPushButton("Toggle Auto-Rotate")
        btn_auto.clicked.connect(lambda: self.rotation_requested.emit("auto"))

        grid.addWidget(btn_portrait, 0, 0)
        grid.addWidget(btn_landscape, 0, 1)
        grid.addWidget(btn_auto, 1, 0, 1, 2)

        return grp

    def _create_notification_group(self) -> QGroupBox:
        grp = QGroupBox("Notification Drawer")
        grid = QGridLayout(grp)
        grid.setSpacing(8)

        btn_expand = QPushButton("Expand Notifications")
        btn_expand.clicked.connect(self.expand_notifications_requested.emit)

        btn_collapse = QPushButton("Collapse Notifications")
        btn_collapse.clicked.connect(self.collapse_notifications_requested.emit)

        btn_settings = QPushButton("Open Device Settings")
        btn_settings.clicked.connect(self.settings_requested.emit)

        grid.addWidget(btn_expand, 0, 0)
        grid.addWidget(btn_collapse, 0, 1)
        grid.addWidget(btn_settings, 1, 0, 1, 2)

        return grp

    def _create_input_group(self) -> QGroupBox:
        grp = QGroupBox("Text and Input Dispatch")
        vbox = QVBoxLayout(grp)
        vbox.setSpacing(8)

        hbox = QHBoxLayout()
        self.txt_input = QLineEdit()
        self.txt_input.setPlaceholderText("Type text to send to focused field on device...")
        self.txt_input.returnPressed.connect(self._on_send_text)

        btn_send = QPushButton("Send Text")
        btn_send.clicked.connect(self._on_send_text)

        btn_paste = QPushButton("Paste Clipboard")
        btn_paste.clicked.connect(self.paste_clipboard_requested.emit)

        hbox.addWidget(self.txt_input, 1)
        hbox.addWidget(btn_send)
        hbox.addWidget(btn_paste)
        vbox.addLayout(hbox)

        lbl_hint = QLabel("Sends direct ASCII text to the active text field on the device, or pastes PC clipboard.")
        lbl_hint.setStyleSheet("color: #8b9bb4; font-size: 11px;")
        vbox.addWidget(lbl_hint)

        return grp

    def _create_power_adb_group(self) -> QGroupBox:
        grp = QGroupBox("Device Power and ADB Tools")
        vbox = QVBoxLayout(grp)
        vbox.setSpacing(10)

        grid = QGridLayout()
        grid.setSpacing(8)

        btn_reboot_sys = QPushButton("Reboot System")
        btn_reboot_sys.clicked.connect(lambda: self.reboot_requested.emit("system"))

        btn_reboot_rec = QPushButton("Reboot Recovery")
        btn_reboot_rec.clicked.connect(lambda: self.reboot_requested.emit("recovery"))

        btn_reboot_boot = QPushButton("Reboot Fastboot")
        btn_reboot_boot.setToolTip("Reboot device into Bootloader / Fastboot mode")
        btn_reboot_boot.clicked.connect(lambda: self.reboot_requested.emit("bootloader"))

        grid.addWidget(btn_reboot_sys, 0, 0)
        grid.addWidget(btn_reboot_rec, 0, 1)
        grid.addWidget(btn_reboot_boot, 1, 0, 1, 2)
        vbox.addLayout(grid)

        btn_shell = QPushButton("Open Interactive ADB Shell Terminal")
        btn_shell.setStyleSheet(
            "QPushButton {"
            "  font-weight: bold;"
            "  padding: 8px 16px;"
            "  background-color: #212836;"
            "  border: 1px solid #3d5275;"
            "  border-radius: 4px;"
            "  color: #61afef;"
            "}"
            "QPushButton:hover {"
            "  background-color: #2b3548;"
            "  border-color: #61afef;"
            "}"
        )
        btn_shell.clicked.connect(self.adb_shell_requested.emit)
        vbox.addWidget(btn_shell)

        lbl_hint = QLabel(
            "Reboot actions will power cycle the target device. ADB Shell opens an interactive terminal session."
        )
        lbl_hint.setStyleSheet("color: #8b9bb4; font-size: 11px;")
        vbox.addWidget(lbl_hint)

        return grp

    # -------------------------------------------------------------------------
    # Public Update Helpers
    # -------------------------------------------------------------------------

    def set_screenshot_status(self, message: str, is_error: bool = False) -> None:
        color = "#e06c75" if is_error else "#98c379"
        self.lbl_screenshot_status.setStyleSheet(f"color: {color}; font-size: 11px;")
        self.lbl_screenshot_status.setText(message)

    def set_device_connected(self, connected: bool) -> None:
        """Enable or disable quick action controls based on connection state."""
        self.btn_screenshot.setEnabled(connected)
        self.setEnabled(connected)

    def _on_send_text(self) -> None:
        text = self.txt_input.text()
        if text.strip():
            self.send_text_requested.emit(text)
            self.txt_input.clear()
