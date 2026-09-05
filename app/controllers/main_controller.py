"""
MainController — top-level coordinator for the entire application.

Wires together: MainWindow, DeviceController, ScrcpyController,
ConfigService, and PresetService.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, QThreadPool
from PyQt6.QtWidgets import QApplication, QMessageBox

from app.views.main_window import MainWindow
from app.controllers.device_controller import DeviceController
from app.controllers.scrcpy_controller import ScrcpyController
from app.services.config_service import ConfigService
from app.services.preset_service import PresetService
from app.services.adb_service import ScreenshotWorker
from app.models.preset import Preset
from app.utils.logger import get_logger, get_qt_log_handler
from app.utils.paths import paths
from app.utils.platform import open_folder_in_explorer

logger = get_logger(__name__)

# Auto-refresh interval in milliseconds (30 seconds)
AUTO_REFRESH_INTERVAL_MS = 30_000


class MainController(QObject):
    """
    Top-level application coordinator.

    Responsibilities:
        - Initialize all subsystems on startup
        - Wire all signals (including screen mirror, camera, OTG, and tools)
        - Coordinate device refresh, scrcpy/camera/otg launch/stop
        - Save/restore configuration and presets
        - Handle application shutdown cleanly
    """

    def __init__(
        self,
        window: MainWindow,
        device_ctrl: DeviceController,
        scrcpy_ctrl: ScrcpyController,
        config_service: ConfigService,
        preset_service: PresetService,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._window = window
        self._device_ctrl = device_ctrl
        self._scrcpy_ctrl = scrcpy_ctrl
        self._config_svc = config_service
        self._preset_svc = preset_service
        self._shell_dialog: Optional[QObject] = None

        self._auto_refresh_timer = QTimer(self)
        self._auto_refresh_timer.timeout.connect(self._on_auto_refresh)

        self._wire_signals()
        self._restore_state()

    # =========================================================================
    # Wiring
    # =========================================================================

    def _wire_signals(self) -> None:
        w = self._window
        dc = self._device_ctrl
        sc = self._scrcpy_ctrl

        # Window → controllers
        w.start_requested.connect(self._on_start_requested)
        w.stop_requested.connect(self._on_stop_requested)
        w.camera_start_requested.connect(self._on_camera_start_requested)
        w.camera_stop_requested.connect(self._on_camera_stop_requested)
        w.otg_start_requested.connect(self._on_otg_start_requested)
        w.otg_stop_requested.connect(self._on_otg_stop_requested)
        w.refresh_requested.connect(dc.refresh_devices)
        w.device_info_requested.connect(self._on_device_info_requested)
        w.wireless_connect_requested.connect(dc.connect_wireless)
        w.wireless_disconnect_requested.connect(dc.disconnect_wireless)
        w.preset_selected.connect(self._on_preset_action)
        w.closing.connect(self._on_closing)

        # Quick Tools
        w.tools_panel.screenshot_requested.connect(self._on_screenshot_requested)
        w.tools_panel.open_folder_requested.connect(self._on_open_screenshots_folder)
        w.tools_panel.rotation_requested.connect(self._on_rotation_requested)
        w.tools_panel.keyevent_requested.connect(self._on_keyevent_requested)
        w.tools_panel.expand_notifications_requested.connect(self._on_expand_notifications)
        w.tools_panel.collapse_notifications_requested.connect(self._on_collapse_notifications)
        w.tools_panel.settings_requested.connect(self._on_settings_requested)
        w.tools_panel.send_text_requested.connect(self._on_send_text_requested)
        w.tools_panel.paste_clipboard_requested.connect(self._on_paste_clipboard_requested)
        w.tools_panel.reboot_requested.connect(self._on_reboot_requested)
        w.tools_panel.adb_shell_requested.connect(self._on_adb_shell_requested)

        # DeviceController → Window
        dc.devices_updated.connect(self._on_devices_updated)
        dc.adb_server_ready.connect(w.set_adb_status)
        dc.status_message.connect(w.show_status_message)
        dc.connect_result.connect(self._on_connect_result)
        dc.disconnect_result.connect(lambda ok, msg: w.show_wireless_result(ok, msg))

        # ScrcpyController → Window
        sc.scrcpy_started.connect(self._on_scrcpy_started)
        sc.scrcpy_stopped.connect(self._on_scrcpy_stopped)
        sc.scrcpy_error.connect(lambda msg: w.show_error("Scrcpy Error", msg))
        sc.status_message.connect(w.show_status_message)
        sc.command_built.connect(w.update_command_preview)

        # Live Application Log stream
        qt_handler = get_qt_log_handler()
        if qt_handler:
            qt_handler.log_emitted.connect(w.device_panel.append_log)

    # =========================================================================
    # Startup
    # =========================================================================

    def start(self) -> None:
        """
        Called after the window is shown.
        Initializes ADB and starts device discovery.
        """
        logger.info("MainController starting up.")
        self._device_ctrl.start_adb_server()

        # Start periodic auto-refresh
        self._auto_refresh_timer.start(AUTO_REFRESH_INTERVAL_MS)

    def _restore_state(self) -> None:
        """Load last config and preset from ConfigService."""
        # Populate preset list
        names = self._preset_svc.get_preset_names()
        last_preset = self._config_svc.get_last_preset_name()
        self._window.update_preset_list(names, current=last_preset)

        # Apply last screen config
        config = self._config_svc.get_scrcpy_config()
        self._window.apply_config(config)

        # Apply last camera config
        cam_config = self._config_svc.get_camera_config()
        self._window.apply_camera_config(cam_config)

    # =========================================================================
    # Slots
    # =========================================================================

    def _on_devices_updated(self, devices: list) -> None:
        self._window.update_devices(devices)

        # Restore last selected device serial
        last_serial = self._config_svc.get_last_device_serial()
        if last_serial:
            self._window.select_device_by_serial(last_serial)

        # Enable START and CAMERA only if there's a ready device
        device = self._window.selected_device()
        start_enabled = device is not None and device.is_ready
        if not self._scrcpy_ctrl.is_running:
            self._window._start_btn.setEnabled(start_enabled)
            self._window._camera_btn.setEnabled(start_enabled)

    def _on_start_requested(self) -> None:
        device = self._window.selected_device()
        if device is None:
            self._window.show_error("No Device", "No Android device selected.")
            return

        config = self._window.get_current_config()

        # Save current config
        self._config_svc.set_scrcpy_config(config)
        self._config_svc.set_last_device_serial(device.serial)
        self._config_svc.save()

        self._scrcpy_ctrl.start(device, config)

    def _on_stop_requested(self) -> None:
        self._scrcpy_ctrl.stop()

    def _on_camera_start_requested(self) -> None:
        device = self._window.selected_device()
        if device is None:
            self._window.show_error("No Device", "No Android device selected.")
            return

        cam_config = self._window.get_current_camera_config()

        # Save current camera config
        self._config_svc.set_camera_config(cam_config)
        self._config_svc.set_last_device_serial(device.serial)
        self._config_svc.save()

        self._scrcpy_ctrl.start_camera(device, cam_config)

    def _on_camera_stop_requested(self) -> None:
        self._scrcpy_ctrl.stop()

    def _on_otg_start_requested(self) -> None:
        device = self._window.selected_device()
        if device is None:
            self._window.show_error("No Device", "No Android device selected.")
            return

        otg_config = self._window.get_current_otg_config()
        self._scrcpy_ctrl.start_otg(device, otg_config)

    def _on_otg_stop_requested(self) -> None:
        self._scrcpy_ctrl.stop()

    def _on_screenshot_requested(self) -> None:
        device = self._window.selected_device()
        if not device:
            self._window.tools_panel.set_screenshot_status("No device selected.", is_error=True)
            return

        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        sanitized_serial = "".join(c for c in device.serial if c.isalnum() or c in ("-", "_"))
        filename = f"screenshot_{sanitized_serial}_{now_str}.png"
        output_path = paths.screenshots_dir / filename

        self._window.tools_panel.set_screenshot_status("Capturing screenshot...")
        worker = ScreenshotWorker(self._device_ctrl.adb_service, device.serial, output_path)
        worker.signals.finished.connect(
            lambda path: self._window.tools_panel.set_screenshot_status(f"Saved: {Path(path).name}")
        )
        worker.signals.error.connect(
            lambda err: self._window.tools_panel.set_screenshot_status(f"Error: {err}", is_error=True)
        )
        QThreadPool.globalInstance().start(worker)

    def _on_open_screenshots_folder(self) -> None:
        paths.screenshots_dir.mkdir(parents=True, exist_ok=True)
        open_folder_in_explorer(paths.screenshots_dir)

    def _on_rotation_requested(self, mode: str) -> None:
        device = self._window.selected_device()
        if not device:
            return
        self._device_ctrl.adb_service.rotate_screen(device.serial, mode)
        self._window.show_status_message(f"Orientation set: {mode}")

    def _on_keyevent_requested(self, keycode: int) -> None:
        device = self._window.selected_device()
        if not device:
            return
        self._device_ctrl.adb_service.send_keyevent(device.serial, keycode)

    def _on_expand_notifications(self) -> None:
        device = self._window.selected_device()
        if not device:
            return
        self._device_ctrl.adb_service.expand_notifications(device.serial)

    def _on_collapse_notifications(self) -> None:
        device = self._window.selected_device()
        if not device:
            return
        self._device_ctrl.adb_service.collapse_notifications(device.serial)

    def _on_settings_requested(self) -> None:
        device = self._window.selected_device()
        if not device:
            return
        self._device_ctrl.adb_service.open_settings(device.serial)

    def _on_send_text_requested(self, text: str) -> None:
        device = self._window.selected_device()
        if not device:
            return
        ok = self._device_ctrl.adb_service.send_text_input(device.serial, text)
        if ok:
            self._window.show_status_message("Text dispatched to device.")
        else:
            self._window.show_status_message("Failed to dispatch text.")

    def _on_paste_clipboard_requested(self) -> None:
        device = self._window.selected_device()
        if not device:
            return
        clipboard = QApplication.clipboard()
        text = clipboard.text() if clipboard else ""
        if not text:
            self._window.show_status_message("PC clipboard is empty.")
            return
        ok = self._device_ctrl.adb_service.send_text_input(device.serial, text)
        if ok:
            self._window.show_status_message("Clipboard text sent to device.")
        else:
            self._window.show_status_message("Failed to send clipboard text.")

    def _on_reboot_requested(self, mode: str) -> None:
        device = self._window.selected_device()
        if not device:
            self._window.show_warning("No Device", "Please select a connected device first.")
            return

        mode_title = mode.upper()
        reply = QMessageBox.question(
            self._window,
            "Confirm Device Reboot",
            f"Are you sure you want to reboot device '{device.display_name}' into {mode_title} mode?\n\n"
            "This will close any active mirroring sessions and restart the device.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Stop active scrcpy sessions cleanly before rebooting
        if self._scrcpy_ctrl.is_running:
            self._scrcpy_ctrl.stop()

        ok, msg = self._device_ctrl.adb_service.reboot_device(device.serial, mode)
        if ok:
            self._window.show_status_message(f"Device rebooting to {mode_title}...")
        else:
            self._window.show_error("Reboot Failed", msg)

    def _on_adb_shell_requested(self) -> None:
        device = self._window.selected_device()
        if not device:
            self._window.show_warning("No Device", "Please select a connected device first.")
            return

        reply = QMessageBox.warning(
            self._window,
            "Direct ADB Shell Security Warning",
            f"Warning: ADB Shell grants direct low-level command access to the Android operating system on '{device.display_name}'.\n\n"
            "Running unverified or incorrect commands can alter system configurations, terminate critical services, or modify protected storage.\n\n"
            "Do you want to proceed to the interactive shell terminal?",
            QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Open:
            return

        from app.views.dialogs.adb_shell_dialog import ADBShellDialog
        self._shell_dialog = ADBShellDialog(
            serial=device.serial,
            device_name=device.display_name,
            adb_path=self._device_ctrl.adb_service._adb,
            parent=self._window,
        )
        self._shell_dialog.show()

    def _on_scrcpy_started(self, mode: str) -> None:
        if mode == "camera":
            self._window.set_camera_running(True)
        elif mode == "otg":
            self._window.set_otg_running(True)
        else:
            self._window.set_scrcpy_running(True)

    def _on_scrcpy_stopped(self, exit_code: int, last_error: str, mode: str) -> None:
        self._window.set_scrcpy_running(False)
        self._window.set_camera_running(False)
        self._window.set_otg_running(False)
        if exit_code != 0:
            # Only alert user if there were actual error/failure messages captured.
            # Normal user window closure or termination on Windows often exits with code 1 without error.
            has_real_error = bool(last_error and last_error.strip())
            if has_real_error:
                target = (
                    "OTG session"
                    if mode == "otg"
                    else ("Camera mode" if mode == "camera" else "Scrcpy")
                )
                err_msg = f"{target} exited unexpectedly (code {exit_code}).\n\nDetails:\n{last_error.strip()}"
                self._window.show_error(f"{target} Error", err_msg)
            else:
                logger.info("Scrcpy process exited with code %d (no errors logged).", exit_code)

    def _on_device_info_requested(self) -> None:
        device = self._window.selected_device()
        if device is None:
            return
        self._window.show_device_info(device)

    def _on_connect_result(self, ok: bool, message: str) -> None:
        self._window.show_wireless_result(ok, message)

    def _on_preset_action(self, action: str) -> None:
        """
        Handle preset combo changes and special __save__/__manage__ signals.
        """
        if action.startswith("__save__:"):
            name = action[len("__save__:"):]
            config = self._window.get_current_config()
            preset = Preset(name=name, config=config)
            self._preset_svc.save_preset(preset)
            names = self._preset_svc.get_preset_names()
            self._window.update_preset_list(names, current=name)
            self._window.show_status_message(f"Preset '{name}' saved.")

        elif action == "__manage__":
            config = self._window.get_current_config()
            from app.views.dialogs.preset_manager_dialog import PresetManagerDialog
            dlg = PresetManagerDialog(self._preset_svc, config, parent=self._window)
            dlg.preset_selected.connect(self._on_preset_applied)
            dlg.exec()
            names = self._preset_svc.get_preset_names()
            current = self._window._preset_combo.currentText()
            self._window.update_preset_list(names, current=current)

        else:
            self._on_preset_applied(action)

    def _on_preset_applied(self, name: str) -> None:
        preset = self._preset_svc.get_preset(name)
        if preset is None:
            return
        self._window.apply_config(preset.config)
        self._config_svc.set_last_preset_name(name)
        self._config_svc.save()
        self._window.show_status_message(f"Preset '{name}' applied.")

    def _on_auto_refresh(self) -> None:
        """Periodic device refresh — only if scrcpy is not running."""
        if not self._scrcpy_ctrl.is_running:
            self._device_ctrl.refresh_devices()

    def _on_closing(self) -> None:
        """Clean shutdown when the window is closed."""
        logger.info("Application closing — cleaning up.")
        self._auto_refresh_timer.stop()

        # Save configs
        config = self._window.get_current_config()
        self._config_svc.set_scrcpy_config(config)
        cam_config = self._window.get_current_camera_config()
        self._config_svc.set_camera_config(cam_config)
        device = self._window.selected_device()
        if device:
            self._config_svc.set_last_device_serial(device.serial)
        self._config_svc.save()

        self._scrcpy_ctrl.cleanup()
        logger.info("Cleanup done. Goodbye.")
