"""
OTG Mode / Physical Input Passthrough View.

Allows using PC keyboard and mouse to control Android device without video streaming:
- Hardware USB HID emulation (--otg)
- Streamless ADB control (--no-video --no-audio)
- Zero-latency, highly battery-efficient control

Clean, modern dark aesthetic without emojis.
"""

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QRadioButton,
    QButtonGroup,
    QCheckBox,
    QLineEdit,
    QPushButton,
    QLabel,
    QScrollArea,
    QFrame,
)

from app.services.command_builder import OTGConfig


class OTGPanel(QWidget):
    """
    Panel for configuring and launching OTG / Physical Input passthrough mode.
    """

    # Signals
    start_otg_clicked = pyqtSignal()
    stop_otg_clicked = pyqtSignal()
    config_changed = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._is_running = False
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # 1. Mode Selection Group
        layout.addWidget(self._create_mode_group())

        # 2. Input Options Group
        layout.addWidget(self._create_options_group())

        # 3. Instruction & Shortcuts Card
        layout.addWidget(self._create_info_card())

        # 4. Action Button
        self.btn_action = QPushButton("Start OTG Session")
        self.btn_action.setFixedHeight(38)
        self.btn_action.setStyleSheet(
            "QPushButton { font-weight: bold; font-size: 13px; background-color: #2e60a8; border-radius: 4px; color: #ffffff; }"
            "QPushButton:hover { background-color: #3b74c4; }"
            "QPushButton:pressed { background-color: #1f4780; }"
            "QPushButton:disabled { background-color: #2b3342; color: #5a6577; }"
        )
        self.btn_action.clicked.connect(self._on_action_clicked)
        layout.addWidget(self.btn_action)

        layout.addStretch(1)

    # -------------------------------------------------------------------------
    # Group Builders
    # -------------------------------------------------------------------------

    def _create_mode_group(self) -> QGroupBox:
        grp = QGroupBox("Passthrough Mode")
        grid = QGridLayout(grp)
        grid.setSpacing(10)

        self.radio_nodisp = QRadioButton("Streamless ADB HID Passthrough (Recommended)")
        self.radio_nodisp.setChecked(True)
        lbl_nodisp_desc = QLabel(
            "Controls device using PC physical keyboard and mouse via ADB without video or audio stream. Works over USB and Wi-Fi."
        )
        lbl_nodisp_desc.setWordWrap(True)
        lbl_nodisp_desc.setStyleSheet("color: #8b9bb4; font-size: 11px; margin-left: 20px;")

        self.radio_otg = QRadioButton("Hardware USB HID Emulation (--otg)")
        lbl_otg_desc = QLabel(
            "Direct USB hardware emulation. Bypasses ADB (requires WinUSB driver via Zadig)."
        )
        lbl_otg_desc.setWordWrap(True)
        lbl_otg_desc.setStyleSheet("color: #8b9bb4; font-size: 11px; margin-left: 20px;")

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.radio_nodisp)
        self.mode_group.addButton(self.radio_otg)
        self.mode_group.buttonClicked.connect(lambda: self.config_changed.emit())

        grid.addWidget(self.radio_nodisp, 0, 0)
        grid.addWidget(lbl_nodisp_desc, 1, 0)
        grid.addWidget(self.radio_otg, 0, 1)
        grid.addWidget(lbl_otg_desc, 1, 1)

        return grp

    def _create_options_group(self) -> QGroupBox:
        grp = QGroupBox("Input and Power Options")
        grid = QGridLayout(grp)
        grid.setSpacing(8)

        self.chk_no_keyboard = QCheckBox("Disable Keyboard Input")
        self.chk_no_keyboard.toggled.connect(lambda: self.config_changed.emit())

        self.chk_no_mouse = QCheckBox("Disable Mouse Input")
        self.chk_no_mouse.toggled.connect(lambda: self.config_changed.emit())

        self.chk_stay_awake = QCheckBox("Stay Awake While Connected")
        self.chk_stay_awake.setChecked(True)
        self.chk_stay_awake.toggled.connect(lambda: self.config_changed.emit())

        self.chk_turn_screen_off = QCheckBox("Turn Screen Off During Control")
        self.chk_turn_screen_off.toggled.connect(lambda: self.config_changed.emit())

        grid.addWidget(self.chk_no_keyboard, 0, 0)
        grid.addWidget(self.chk_no_mouse, 0, 1)
        grid.addWidget(self.chk_stay_awake, 1, 0)
        grid.addWidget(self.chk_turn_screen_off, 1, 1)

        # Custom arguments row
        lbl_custom = QLabel("Custom Arguments:")
        lbl_custom.setStyleSheet("color: #abb2bf; font-size: 11px;")
        self.txt_custom_args = QLineEdit()
        self.txt_custom_args.setPlaceholderText("e.g. --keyboard=uhid --mouse=uhid")
        self.txt_custom_args.textChanged.connect(lambda: self.config_changed.emit())

        grid.addWidget(lbl_custom, 2, 0)
        grid.addWidget(self.txt_custom_args, 2, 1)

        return grp

    def _create_info_card(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background-color: #1a1e27; border: 1px solid #282c34; border-radius: 4px; padding: 8px 12px; }"
        )
        vbox = QVBoxLayout(frame)
        vbox.setSpacing(3)

        lbl_title = QLabel("Keyboard and Mouse Capture Controls")
        lbl_title.setStyleSheet("font-weight: bold; color: #abb2bf; font-size: 11px;")

        lbl_p1 = QLabel("- Mouse Focus: Click inside scrcpy window to capture. Press Left-Alt or Right-Super to release focus to PC.")
        lbl_p1.setStyleSheet("color: #8b9bb4; font-size: 11px;")

        lbl_p2 = QLabel("- Exit Session: Close the capture window or click Stop OTG Session below.")
        lbl_p2.setStyleSheet("color: #8b9bb4; font-size: 11px;")

        vbox.addWidget(lbl_title)
        vbox.addWidget(lbl_p1)
        vbox.addWidget(lbl_p2)

        return frame

    # -------------------------------------------------------------------------
    # Public Methods
    # -------------------------------------------------------------------------

    def get_config(self) -> OTGConfig:
        mode = "no_display" if self.radio_nodisp.isChecked() else "otg"
        return OTGConfig(
            mode=mode,
            disable_keyboard=self.chk_no_keyboard.isChecked(),
            disable_mouse=self.chk_no_mouse.isChecked(),
            stay_awake=self.chk_stay_awake.isChecked(),
            turn_screen_off=self.chk_turn_screen_off.isChecked(),
            custom_args=self.txt_custom_args.text().strip(),
        )

    def set_running_state(self, running: bool) -> None:
        self._is_running = running
        if running:
            self.btn_action.setText("Stop OTG Session")
            self.btn_action.setStyleSheet(
                "QPushButton { font-weight: bold; font-size: 13px; background-color: #a82e2e; border-radius: 4px; color: #ffffff; }"
                "QPushButton:hover { background-color: #c43b3b; }"
                "QPushButton:pressed { background-color: #801f1f; }"
            )
        else:
            self.btn_action.setText("Start OTG Session")
            self.btn_action.setStyleSheet(
                "QPushButton { font-weight: bold; font-size: 13px; background-color: #2e60a8; border-radius: 4px; color: #ffffff; }"
                "QPushButton:hover { background-color: #3b74c4; }"
                "QPushButton:pressed { background-color: #1f4780; }"
            )

    def set_device_connected(self, connected: bool) -> None:
        self.btn_action.setEnabled(connected)

    def _on_action_clicked(self) -> None:
        if self._is_running:
            self.stop_otg_clicked.emit()
        else:
            self.start_otg_clicked.emit()
