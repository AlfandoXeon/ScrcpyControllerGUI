"""
MainWindow — the primary application window.

Layout:
    - QTabWidget (Device | Display | Audio | Window | Advanced | Camera | Developer)
    - Preset row (selector + Save + Manage)
    - Action buttons row (START SCRCPY | START CAMERA)
    - Status bar (ADB | Device | Scrcpy)
"""

import sys
from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QCloseEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStatusBar,
    QTabBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.version import APP_NAME, VERSION
from app.models.config import ScrcpyConfig
from app.models.device import Device
from app.services.command_builder import (
    CameraConfig,
    CameraCommandBuilder,
    OTGConfig,
    OTGCommandBuilder,
)
from app.views.device_panel import DevicePanel
from app.views.display_panel import DisplayPanel
from app.views.audio_panel import AudioPanel
from app.views.window_panel import WindowPanel
from app.views.advanced_panel import AdvancedPanel
from app.views.camera_panel import CameraPanel
from app.views.tools_panel import ToolsPanel
from app.views.otg_panel import OTGPanel
from app.views.developer_panel import DeveloperPanel
from app.views.dialogs.device_info_dialog import DeviceInfoDialog
from app.views.dialogs.wireless_dialog import WirelessDialog
from app.views.dialogs.preset_manager_dialog import PresetManagerDialog
from app.views.dialogs.command_preview_dialog import CommandPreviewDialog
from app.utils.paths import paths
from app.utils.platform import open_folder_in_explorer
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ResponsiveTabBar(QTabBar):
    """
    TabBar where tabs expand proportionally across the entire width of the tab widget,
    ensuring all tabs fill the available horizontal space without empty gaps.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setExpanding(True)

    def tabSizeHint(self, index: int) -> QSize:
        p = self.parent()
        pw = p.width() if p else 100
        count = self.count() or 1
        base = super().tabSizeHint(index)
        equal_w = pw // count
        return QSize(max(equal_w, 75), max(base.height(), 32))


class ResponsiveTabWidget(QTabWidget):
    """
    QTabWidget that keeps its QTabBar width synced with the widget width on resize,
    ensuring tabs and borders always stretch and adapt perfectly to window resizing.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setTabBar(ResponsiveTabBar(self))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.tabBar():
            self.tabBar().setFixedWidth(self.width())


class MainWindow(QMainWindow):
    """
    Main application window.

    Signals emitted to controllers:
        start_requested()
        stop_requested()
        camera_start_requested()
        camera_stop_requested()
        refresh_requested()
        device_info_requested()
        wireless_connect_requested(ip, port)
        wireless_disconnect_requested(ip, port)
        preset_selected(name)
        closing()
    """

    start_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    camera_start_requested = pyqtSignal()    # launch scrcpy in camera mode
    camera_stop_requested = pyqtSignal()     # stop camera session
    otg_start_requested = pyqtSignal()       # launch scrcpy in OTG mode
    otg_stop_requested = pyqtSignal()        # stop OTG session
    refresh_requested = pyqtSignal()
    device_info_requested = pyqtSignal()
    wireless_connect_requested = pyqtSignal(str, int)
    wireless_disconnect_requested = pyqtSignal(str, int)
    preset_selected = pyqtSignal(str)
    closing = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._last_command: str = ""
        self._wireless_dialog: Optional[WirelessDialog] = None
        self._command_preview_dialog: Optional[CommandPreviewDialog] = None

        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.setMinimumSize(700, 560)
        self.resize(860, 660)

        # Set window icon (high-res PNG preferred)
        icon_file = paths.icon_png if paths.icon_png.exists() else paths.icon_path()
        if icon_file.exists():
            self.setWindowIcon(QIcon(str(icon_file)))

        self._build_ui()
        self._connect_panel_signals()
        self._set_scrcpy_running(False)
        self.set_camera_running(False)

    # =========================================================================
    # UI Construction
    # =========================================================================

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(8)
        root.setContentsMargins(10, 10, 10, 10)

        # -- Tab widget -------------------------------------------------------
        self._tabs = ResponsiveTabWidget()
        self._tabs.tabBar().setElideMode(Qt.TextElideMode.ElideNone)

        self.device_panel = DevicePanel()
        self.display_panel = DisplayPanel()
        self.audio_panel = AudioPanel()
        self.window_panel = WindowPanel()
        self.advanced_panel = AdvancedPanel()
        self.camera_panel = CameraPanel()
        self.tools_panel = ToolsPanel()
        self.otg_panel = OTGPanel()
        self.developer_panel = DeveloperPanel()

        def _wrap_tab(widget: QWidget) -> QScrollArea:
            """Wrap tab widget in a transparent scroll area for ultra-responsiveness."""
            scroll = QScrollArea()
            scroll.setWidget(widget)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll.setStyleSheet("background: transparent;")
            return scroll

        self._tabs.addTab(_wrap_tab(self.device_panel), "Device")
        self._tabs.addTab(_wrap_tab(self.display_panel), "Display")
        self._tabs.addTab(_wrap_tab(self.audio_panel), "Audio")
        self._tabs.addTab(_wrap_tab(self.window_panel), "Window")
        self._tabs.addTab(_wrap_tab(self.advanced_panel), "Advanced")
        self._tabs.addTab(_wrap_tab(self.camera_panel), "Camera")
        self._tabs.addTab(_wrap_tab(self.tools_panel), "Tools")
        self._tabs.addTab(_wrap_tab(self.otg_panel), "OTG")
        self._tabs.addTab(_wrap_tab(self.developer_panel), "Developer")

        root.addWidget(self._tabs)

        # -- Preset row -------------------------------------------------------
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Preset:"))

        self._preset_combo = QComboBox()
        self._preset_combo.setMinimumWidth(150)
        self._preset_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._preset_combo.currentTextChanged.connect(self._on_preset_combo_changed)
        preset_row.addWidget(self._preset_combo)

        self._save_preset_btn = QPushButton("Save")
        self._save_preset_btn.setFixedWidth(64)
        self._save_preset_btn.clicked.connect(self._on_save_preset)
        preset_row.addWidget(self._save_preset_btn)

        self._manage_preset_btn = QPushButton("Manage")
        self._manage_preset_btn.setFixedWidth(74)
        self._manage_preset_btn.clicked.connect(self._on_manage_presets)
        preset_row.addWidget(self._manage_preset_btn)

        root.addLayout(preset_row)

        # -- Action buttons row -----------------------------------------------
        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self._start_btn = QPushButton("START SCRCPY")
        self._start_btn.setMinimumHeight(38)
        self._start_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._start_btn.setProperty("running", "false")
        self._start_btn.clicked.connect(self._on_start_stop)
        action_row.addWidget(self._start_btn, stretch=3)

        self._camera_btn = QPushButton("START CAMERA")
        self._camera_btn.setMinimumHeight(38)
        self._camera_btn.setMinimumWidth(135)
        self._camera_btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._camera_btn.setProperty("camera_running", "false")
        self._camera_btn.clicked.connect(self._on_camera_start_stop)
        self._camera_btn.setStyleSheet(
            "QPushButton { background-color: #0e6b6b; color: #ffffff; border: 1px solid #095555; "
            "border-radius: 3px; font-weight: bold; font-size: 9pt; } "
            "QPushButton:hover { background-color: #128282; } "
            "QPushButton:disabled { background-color: #1a2e2e; color: #446666; border-color: #162424; } "
            "QPushButton[camera_running='true'] { background-color: #8b1a1a; border-color: #6b1414; } "
            "QPushButton[camera_running='true']:hover { background-color: #a32020; border-color: #7a1818; }"
        )
        action_row.addWidget(self._camera_btn, stretch=1)

        root.addLayout(action_row)

        # -- Status bar -------------------------------------------------------
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        self._sb_adb = QLabel("ADB: —")
        self._sb_device = QLabel("Device: —")
        self._sb_scrcpy = QLabel("Scrcpy: Stopped")
        self._sb_msg = QLabel("")
        self._sb_msg.setObjectName("status_msg")

        # Scrolling message (left side)
        self._status_bar.addWidget(self._sb_msg, 1)

        # Permanent widgets (right side)
        self._status_bar.addPermanentWidget(self._sb_device)
        self._status_bar.addPermanentWidget(self._sb_adb)
        self._status_bar.addPermanentWidget(self._sb_scrcpy)

    def _connect_panel_signals(self) -> None:
        """Wire panel-internal signals to MainWindow signals."""
        self.device_panel.refresh_requested.connect(self.refresh_requested)
        self.device_panel.device_info_requested.connect(self.device_info_requested)
        self.device_panel.wireless_requested.connect(self._on_wireless_requested)
        self.advanced_panel.show_command_requested.connect(self._on_show_command)
        self.camera_panel.show_command_requested.connect(self._on_show_camera_command)
        self.otg_panel.start_otg_clicked.connect(self.otg_start_requested.emit)
        self.otg_panel.stop_otg_clicked.connect(self.otg_stop_requested.emit)

    # =========================================================================
    # Public update methods (called by MainController)
    # =========================================================================

    def update_devices(self, devices: list[Device]) -> None:
        self.device_panel.update_devices(devices)
        self._update_device_status_bar()

    def selected_device(self) -> Optional[Device]:
        return self.device_panel.selected_device()

    def select_device_by_serial(self, serial: str) -> None:
        self.device_panel.select_device_by_serial(serial)
        self._update_device_status_bar()

    def get_current_config(self) -> ScrcpyConfig:
        """Gather config from all panels (screen mirror mode)."""
        config = ScrcpyConfig()
        self.display_panel.get_config_values(config)
        self.audio_panel.get_config_values(config)
        self.window_panel.get_config_values(config)
        self.advanced_panel.get_config_values(config)
        return config

    def apply_config(self, config: ScrcpyConfig) -> None:
        """Push a config into all panels."""
        self.display_panel.apply_config(config)
        self.audio_panel.apply_config(config)
        self.window_panel.apply_config(config)
        self.advanced_panel.apply_config(config)

    def get_current_camera_config(self) -> CameraConfig:
        """Return config from camera panel."""
        return self.camera_panel.get_config()

    def apply_camera_config(self, config: CameraConfig) -> None:
        """Push a CameraConfig into the camera panel."""
        self.camera_panel.apply_config(config)

    def get_current_otg_config(self) -> OTGConfig:
        """Return config from OTG panel."""
        return self.otg_panel.get_config()

    def set_otg_running(self, running: bool) -> None:
        """Update UI state when an OTG session starts or stops."""
        self.otg_panel.set_running_state(running)
        if running:
            self._start_btn.setEnabled(False)
            self._camera_btn.setEnabled(False)
            self._sb_scrcpy.setText("OTG: Running")
        else:
            self._sb_scrcpy.setText("Scrcpy: Stopped")
            self._update_device_status_bar()

    def update_preset_list(self, names: list[str], current: str = "") -> None:
        self._preset_combo.blockSignals(True)
        self._preset_combo.clear()
        self._preset_combo.addItems(names)
        if current and current in names:
            self._preset_combo.setCurrentText(current)
        self._preset_combo.blockSignals(False)

    def set_adb_status(self, ok: bool) -> None:
        self._sb_adb.setText(f"ADB: {'Running' if ok else 'Error'}")

    def set_scrcpy_running(self, running: bool) -> None:
        self._set_scrcpy_running(running)
        if running:
            self._camera_btn.setEnabled(False)
            self.otg_panel.btn_action.setEnabled(False)
            self._sb_scrcpy.setText("Scrcpy: Running")
        else:
            self._sb_scrcpy.setText("Scrcpy: Stopped")
            self._update_device_status_bar()

    def set_camera_running(self, running: bool) -> None:
        if running:
            self._camera_btn.setText("STOP CAMERA")
            self._camera_btn.setProperty("camera_running", "true")
            self._start_btn.setEnabled(False)
            self.otg_panel.btn_action.setEnabled(False)
            self._sb_scrcpy.setText("Camera: Running")
        else:
            self._camera_btn.setText("START CAMERA")
            self._camera_btn.setProperty("camera_running", "false")
            self._sb_scrcpy.setText("Scrcpy: Stopped")
            self._update_device_status_bar()
        self._camera_btn.style().unpolish(self._camera_btn)
        self._camera_btn.style().polish(self._camera_btn)
        self._camera_btn.update()

    def show_status_message(self, message: str, timeout: int = 4000) -> None:
        self._sb_msg.setText(message)
        self._status_bar.showMessage(message, timeout)

    def show_error(self, title: str, message: str) -> None:
        logger.error("User Error [%s]: %s", title, message)
        QMessageBox.warning(self, title, message)

    def show_info(self, title: str, message: str) -> None:
        QMessageBox.information(self, title, message)

    def update_command_preview(self, command: str) -> None:
        self._last_command = command
        if self._command_preview_dialog and self._command_preview_dialog.isVisible():
            self._command_preview_dialog.update_command(command)

    def show_device_info(self, device: Device) -> None:
        dlg = DeviceInfoDialog(device, parent=self)
        dlg.exec()

    def show_wireless_result(self, success: bool, message: str) -> None:
        if self._wireless_dialog:
            self._wireless_dialog.set_status(message)
        if not success:
            self.show_error("Wireless ADB", f"Failed to connect.\n\n{message}")

    def show_logs_folder(self) -> None:
        open_folder_in_explorer(paths.logs_dir)

    # =========================================================================
    # Private helpers
    # =========================================================================

    def _set_scrcpy_running(self, running: bool) -> None:
        if running:
            self._start_btn.setText("STOP SCRCPY")
            self._start_btn.setProperty("running", "true")
        else:
            self._start_btn.setText("START SCRCPY")
            self._start_btn.setProperty("running", "false")
        self._start_btn.style().unpolish(self._start_btn)
        self._start_btn.style().polish(self._start_btn)
        self._start_btn.update()

    def _update_device_status_bar(self) -> None:
        device = self.selected_device()
        if device:
            self._sb_device.setText(f"Device: {device.model or device.serial}")
        else:
            self._sb_device.setText("Device: —")

        scrcpy_running = self._start_btn.property("running") == "true"
        camera_running = self._camera_btn.property("camera_running") == "true"
        otg_running = getattr(self.otg_panel, "_is_running", False)
        any_running = scrcpy_running or camera_running or otg_running
        ready = device is not None and device.is_ready

        if not any_running:
            self._start_btn.setEnabled(ready)
            self._camera_btn.setEnabled(ready)
            self.otg_panel.set_device_connected(ready)
        else:
            if not scrcpy_running:
                self._start_btn.setEnabled(False)
            if not camera_running:
                self._camera_btn.setEnabled(False)
            if not otg_running:
                self.otg_panel.btn_action.setEnabled(False)

        self.tools_panel.set_device_connected(ready)

    def _on_start_stop(self) -> None:
        if self._start_btn.text().startswith("STOP"):
            self.stop_requested.emit()
        else:
            if not self.advanced_panel.custom_args_valid():
                self.show_error("Invalid Arguments", "Custom arguments contain invalid syntax. Please fix before starting.")
                return
            self.start_requested.emit()

    def _on_camera_start_stop(self) -> None:
        if self._camera_btn.text().startswith("STOP"):
            self.camera_stop_requested.emit()
        else:
            if not self.camera_panel.custom_args_valid():
                self.show_error("Invalid Arguments", "Camera extra arguments contain invalid syntax. Please fix before starting.")
                return
            self.camera_start_requested.emit()

    def _on_preset_combo_changed(self, name: str) -> None:
        if name:
            self.preset_selected.emit(name)

    def _on_save_preset(self) -> None:
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Save Preset", "Preset name:")
        if ok and name.strip():
            self.preset_selected.emit(f"__save__:{name.strip()}")

    def _on_manage_presets(self) -> None:
        self.preset_selected.emit("__manage__")

    def _on_wireless_requested(self) -> None:
        if self._wireless_dialog is None:
            self._wireless_dialog = WirelessDialog(parent=self)
            self._wireless_dialog.connect_requested.connect(self.wireless_connect_requested)
            self._wireless_dialog.disconnect_requested.connect(self.wireless_disconnect_requested)
        self._wireless_dialog.show()
        self._wireless_dialog.raise_()

    def _on_show_command(self) -> None:
        if not self._last_command:
            self.start_requested.emit()
            return
        if self._command_preview_dialog is None:
            self._command_preview_dialog = CommandPreviewDialog(self._last_command, parent=self)
        else:
            self._command_preview_dialog.update_command(self._last_command)
        self._command_preview_dialog.show()
        self._command_preview_dialog.raise_()

    def _on_show_camera_command(self) -> None:
        device = self.selected_device()
        serial = device.serial if device else "<DEVICE_SERIAL>"
        builder = CameraCommandBuilder()
        cmd = builder.preview_string(self.camera_panel.get_config(), serial)
        if self._command_preview_dialog is None:
            self._command_preview_dialog = CommandPreviewDialog(cmd, parent=self)
        else:
            self._command_preview_dialog.update_command(cmd)
        self._command_preview_dialog.show()
        self._command_preview_dialog.raise_()

    # =========================================================================
    # Close event
    # =========================================================================

    def closeEvent(self, event: QCloseEvent) -> None:
        self.closing.emit()
        super().closeEvent(event)
