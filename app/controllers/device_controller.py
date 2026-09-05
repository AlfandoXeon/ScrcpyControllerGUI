"""
DeviceController — coordinates ADB operations and updates the view.
"""

from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import QObject, QThreadPool, pyqtSignal

from app.models.device import Device, DeviceState
from app.services.adb_service import (
    ADBService,
    GetDevicesWorker,
    StartServerWorker,
    ConnectWorker,
    DisconnectWorker,
)
from app.utils.logger import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class DeviceController(QObject):
    """
    Manages device discovery and ADB server lifecycle.

    Signals:
        devices_updated(list[Device]): New device list is available.
        adb_server_ready(bool): ADB server start result.
        connect_result(bool, str): Wireless connect result.
        disconnect_result(bool, str): Wireless disconnect result.
        status_message(str): Short status message for the status bar.
    """

    devices_updated = pyqtSignal(list)
    adb_server_ready = pyqtSignal(bool)
    connect_result = pyqtSignal(bool, str)
    disconnect_result = pyqtSignal(bool, str)
    status_message = pyqtSignal(str)

    def __init__(self, adb_service: ADBService, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._adb = adb_service
        self._pool = QThreadPool.globalInstance()
        self._devices: list[Device] = []

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def start_adb_server(self) -> None:
        """Start ADB server in background thread."""
        if not self._adb.is_available():
            logger.error("ADB not available at %s", self._adb._adb)
            self.adb_server_ready.emit(False)
            self.status_message.emit("ADB runtime not found.")
            return

        self.status_message.emit("Starting ADB server...")
        worker = StartServerWorker(self._adb)
        worker.signals.finished.connect(self._on_server_started)
        worker.signals.error.connect(self._on_adb_error)
        self._pool.start(worker)

    def refresh_devices(self) -> None:
        """Refresh the device list in a background thread."""
        self.status_message.emit("Scanning devices...")
        worker = GetDevicesWorker(self._adb)
        worker.signals.finished.connect(self._on_devices_fetched)
        worker.signals.error.connect(self._on_adb_error)
        self._pool.start(worker)

    def connect_wireless(self, ip: str, port: int) -> None:
        """Connect to a wireless device."""
        self.status_message.emit(f"Connecting to {ip}:{port}...")
        worker = ConnectWorker(self._adb, ip, port)
        worker.signals.finished.connect(self._on_connect_done)
        worker.signals.error.connect(self._on_adb_error)
        self._pool.start(worker)

    def disconnect_wireless(self, ip: str, port: int) -> None:
        """Disconnect a wireless device."""
        self.status_message.emit(f"Disconnecting {ip}:{port}...")
        worker = DisconnectWorker(self._adb, ip, port)
        worker.signals.finished.connect(self._on_disconnect_done)
        worker.signals.error.connect(self._on_adb_error)
        self._pool.start(worker)

    @property
    def devices(self) -> list[Device]:
        return list(self._devices)

    @property
    def adb_service(self) -> ADBService:
        return self._adb

    def get_device(self, serial: str) -> Optional[Device]:
        """Find device by serial."""
        for d in self._devices:
            if d.serial == serial:
                return d
        return None

    # -------------------------------------------------------------------------
    # Slots
    # -------------------------------------------------------------------------

    def _on_server_started(self, ok: bool) -> None:
        self.adb_server_ready.emit(ok)
        if ok:
            self.status_message.emit("ADB: Running")
            self.refresh_devices()
        else:
            self.status_message.emit("ADB: Failed to start")

    def _on_devices_fetched(self, devices: object) -> None:
        self._devices = devices  # type: ignore[assignment]
        self.devices_updated.emit(self._devices)
        count = len(self._devices)
        if count == 0:
            self.status_message.emit("No Android device detected.")
        elif count == 1:
            self.status_message.emit("1 device connected.")
        else:
            self.status_message.emit(f"{count} devices connected.")

    def _on_connect_done(self, result: object) -> None:
        ok, msg = result  # type: ignore[misc]
        self.connect_result.emit(ok, msg)
        if ok:
            self.refresh_devices()

    def _on_disconnect_done(self, result: object) -> None:
        ok, msg = result  # type: ignore[misc]
        self.disconnect_result.emit(ok, msg)
        if ok:
            self.refresh_devices()

    def _on_adb_error(self, message: str) -> None:
        logger.error("ADB error: %s", message)
        self.status_message.emit(f"ADB error: {message}")
