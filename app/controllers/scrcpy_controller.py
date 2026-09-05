"""
ScrcpyController — coordinates ScrcpyService with the view for screen mirror and camera modes.
"""

from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal

from app.models.config import ScrcpyConfig
from app.models.device import Device, DeviceState
from app.services.scrcpy_service import ScrcpyService
from app.services.command_builder import (
    CameraConfig,
    CommandBuilder,
    CameraCommandBuilder,
    OTGConfig,
    OTGCommandBuilder,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ScrcpyController(QObject):
    """
    Manages the scrcpy launch/stop lifecycle for Screen Mirroring, Camera, and OTG modes.

    Signals:
        scrcpy_started(mode): Scrcpy process launched ('mirror', 'camera', or 'otg').
        scrcpy_stopped(exit_code, last_error, mode): Scrcpy process exited.
        scrcpy_error(message): Error during launch or execution.
        status_message(str): Short status message for the status bar.
        command_built(str): Full command string (for preview).
    """

    scrcpy_started = pyqtSignal(str)              # mode ('mirror', 'camera', or 'otg')
    scrcpy_stopped = pyqtSignal(int, str, str)    # exit_code, last_error, mode
    scrcpy_error = pyqtSignal(str)
    status_message = pyqtSignal(str)
    command_built = pyqtSignal(str)

    def __init__(
        self,
        scrcpy_service: ScrcpyService,
        command_builder: Optional[CommandBuilder] = None,
        camera_builder: Optional[CameraCommandBuilder] = None,
        otg_builder: Optional[OTGCommandBuilder] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._service = scrcpy_service
        self._builder = command_builder or CommandBuilder()
        self._camera_builder = camera_builder or CameraCommandBuilder()
        self._otg_builder = otg_builder or OTGCommandBuilder()
        self._current_mode: str = "mirror"

        # Wire service signals
        self._service.started.connect(self._on_started)
        self._service.stopped.connect(self._on_stopped)
        self._service.error.connect(self._on_error)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._service.is_running

    @property
    def current_mode(self) -> str:
        return self._current_mode

    def start(self, device: Device, config: ScrcpyConfig) -> bool:
        """
        Validate, build command, and launch scrcpy screen mirroring.

        Args:
            device: Selected device (must be in DEVICE state).
            config: Current scrcpy configuration.

        Returns:
            True if launch was attempted (result via signals).
        """
        if self.is_running:
            logger.warning("Cannot start screen mirror: another session is already running (%s).", self._current_mode)
            self.scrcpy_error.emit("Another session is already running. Please stop it first.")
            return False

        if device.state != DeviceState.DEVICE:
            msg = self._device_state_message(device)
            logger.warning("Cannot start scrcpy: device state is %s.", device.state)
            self.scrcpy_error.emit(msg)
            return False

        args = self._builder.build(config, device.serial)
        preview = self._builder.preview_string(config, device.serial)
        self.command_built.emit(preview)
        logger.info("Screen mirror command: %s", preview)

        self.status_message.emit("Starting scrcpy mirror...")
        ok = self._service.launch(args)
        if ok:
            self._current_mode = "mirror"
        return ok

    def start_camera(self, device: Device, config: CameraConfig) -> bool:
        """
        Validate, build command, and launch scrcpy in camera mode.

        Args:
            device: Selected device (must be in DEVICE state).
            config: Camera mode configuration.

        Returns:
            True if launch was attempted (result via signals).
        """
        if self.is_running:
            logger.warning("Cannot start camera: another session is already running (%s).", self._current_mode)
            self.scrcpy_error.emit("Another session is already running. Please stop it first.")
            return False

        if device.state != DeviceState.DEVICE:
            msg = self._device_state_message(device)
            logger.warning("Cannot start camera: device state is %s.", device.state)
            self.scrcpy_error.emit(msg)
            return False

        args = self._camera_builder.build(config, device.serial)
        preview = self._camera_builder.preview_string(config, device.serial)
        self.command_built.emit(preview)
        logger.info("Camera mode command: %s", preview)

        self.status_message.emit("Starting camera mode...")
        ok = self._service.launch(args)
        if ok:
            self._current_mode = "camera"
        return ok

    def start_otg(self, device: Device, config: OTGConfig) -> bool:
        """
        Validate, build command, and launch scrcpy in OTG / input passthrough mode.

        Args:
            device: Selected device (must be in DEVICE state).
            config: OTG mode configuration.

        Returns:
            True if launch was attempted (result via signals).
        """
        if self.is_running:
            logger.warning("Cannot start OTG: another session is already running (%s).", self._current_mode)
            self.scrcpy_error.emit("Another session is already running. Please stop it first.")
            return False

        if device.state != DeviceState.DEVICE:
            msg = self._device_state_message(device)
            logger.warning("Cannot start OTG: device state is %s.", device.state)
            self.scrcpy_error.emit(msg)
            return False

        args = self._otg_builder.build(config, device.serial)
        preview = self._otg_builder.preview_string(config, device.serial)
        self.command_built.emit(preview)
        logger.info("OTG mode command: %s", preview)

        self.status_message.emit("Starting OTG mode...")
        ok = self._service.launch(args)
        if ok:
            self._current_mode = "otg"
        return ok

    def stop(self) -> None:
        """Stop the running scrcpy process."""
        if not self._service.is_running:
            return
        mode_text = (
            "OTG session"
            if self._current_mode == "otg"
            else ("camera" if self._current_mode == "camera" else "scrcpy")
        )
        self.status_message.emit(f"Stopping {mode_text}...")
        self._service.stop()

    def cleanup(self) -> None:
        """Called on application exit."""
        self._service.cleanup()

    # -------------------------------------------------------------------------
    # Internal slots
    # -------------------------------------------------------------------------

    def _on_started(self) -> None:
        self.scrcpy_started.emit(self._current_mode)
        if self._current_mode == "camera":
            self.status_message.emit("Camera: Running")
        elif self._current_mode == "otg":
            self.status_message.emit("OTG: Running")
        else:
            self.status_message.emit("Scrcpy: Running")

    def _on_stopped(self, exit_code: int, last_error: str) -> None:
        mode = self._current_mode
        self.scrcpy_stopped.emit(exit_code, last_error, mode)
        if exit_code == 0:
            self.status_message.emit("Scrcpy stopped.")
        else:
            self.status_message.emit(f"Scrcpy exited with code {exit_code}.")
            logger.warning("Scrcpy (%s) exited with non-zero code: %d", mode, exit_code)

    def _on_error(self, message: str) -> None:
        self.scrcpy_error.emit(message)
        self.status_message.emit("Scrcpy: Error")

    @staticmethod
    def _device_state_message(device: Device) -> str:
        if device.state == DeviceState.UNAUTHORIZED:
            return "Please unlock your device and allow USB debugging."
        elif device.state == DeviceState.OFFLINE:
            return "Device is offline. Try reconnecting."
        return "No valid device selected."
