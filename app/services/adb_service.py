"""
ADBService — all ADB interactions, running on worker threads.

All subprocess calls are non-blocking from the GUI perspective.
Use the provided QThread-based worker classes for async operations.
"""

import re
import subprocess
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot

from app.models.device import Device, DeviceState, TransportType
from app.utils.logger import get_logger
from app.utils.paths import paths

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Worker signals
# ---------------------------------------------------------------------------


class WorkerSignals(QObject):
    """Signals for ADB worker runnables."""

    finished = pyqtSignal(object)   # emits result (varies by worker)
    error = pyqtSignal(str)         # emits error message string


# ---------------------------------------------------------------------------
# Low-level ADB runner
# ---------------------------------------------------------------------------


class ADBService:
    """
    Executes ADB commands and parses their output.

    All blocking subprocess calls should be invoked from a QRunnable worker,
    not directly from the GUI thread.
    """

    def __init__(self, adb_path: Optional[Path] = None) -> None:
        self._adb = adb_path or paths.adb_exe
        logger.info("ADBService initialized. ADB path: %s", self._adb)

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True if the bundled adb.exe exists."""
        return self._adb.exists()

    # -------------------------------------------------------------------------
    # Core command runner
    # -------------------------------------------------------------------------

    def run(
        self,
        args: list[str],
        timeout: int = 10,
    ) -> tuple[int, str, str]:
        """
        Execute an ADB command.

        Args:
            args: Argument list (without the adb executable itself).
            timeout: Seconds before the subprocess is killed.

        Returns:
            (returncode, stdout, stderr)
        """
        cmd = [str(self._adb)] + args
        logger.debug("ADB command: %s", cmd)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if subprocess.CREATE_NO_WINDOW else 0,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            logger.error("ADB command timed out: %s", cmd)
            return -1, "", "ADB command timed out."
        except FileNotFoundError:
            logger.error("ADB executable not found at %s", self._adb)
            return -1, "", f"ADB executable not found: {self._adb}"
        except Exception as exc:
            logger.error("ADB command failed: %s — %s", cmd, exc)
            return -1, "", str(exc)

    # -------------------------------------------------------------------------
    # Server management
    # -------------------------------------------------------------------------

    def start_server(self) -> bool:
        """Start the ADB server. Returns True on success."""
        code, _, err = self.run(["start-server"], timeout=15)
        if code == 0:
            logger.info("ADB server started.")
            return True
        logger.error("Failed to start ADB server: %s", err)
        return False

    def kill_server(self) -> bool:
        """Stop the ADB server. Returns True on success."""
        code, _, err = self.run(["kill-server"], timeout=10)
        if code == 0:
            logger.info("ADB server stopped.")
            return True
        logger.warning("Failed to stop ADB server: %s", err)
        return False

    def restart_server(self) -> bool:
        """Restart the ADB server."""
        self.kill_server()
        return self.start_server()

    # -------------------------------------------------------------------------
    # Device discovery
    # -------------------------------------------------------------------------

    def get_devices(self) -> list[Device]:
        """
        Return list of connected devices from `adb devices`.

        Returns:
            List of Device objects (state may be unauthorized/offline).
        """
        code, stdout, _ = self.run(["devices"])
        if code != 0:
            return []
        return self._parse_devices(stdout)

    @staticmethod
    def _parse_devices(output: str) -> list[Device]:
        """
        Parse `adb devices` output into Device objects.

        Args:
            output: Raw stdout from `adb devices`.

        Returns:
            List of parsed Device objects.
        """
        devices: list[Device] = []
        lines = output.strip().splitlines()

        # Find the "List of devices attached" header — skip everything before it
        # (ADB may emit daemon startup messages before the header)
        header_idx = -1
        for i, line in enumerate(lines):
            if "List of devices attached" in line:
                header_idx = i
                break

        if header_idx == -1:
            return []

        for line in lines[header_idx + 1:]:
            line = line.strip()
            if not line or line.startswith("*"):
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            serial = parts[0]
            state_str = parts[1]

            try:
                state = DeviceState(state_str)
            except ValueError:
                state = DeviceState.UNKNOWN

            devices.append(Device(serial=serial, state=state))

        logger.debug("Parsed %d device(s).", len(devices))
        return devices

    # -------------------------------------------------------------------------
    # Device info
    # -------------------------------------------------------------------------

    def get_device_info(self, serial: str) -> dict:
        """
        Fetch device properties via `adb -s SERIAL shell getprop`.

        Args:
            serial: Device serial number.

        Returns:
            Dict with keys: model, manufacturer, android_version, sdk_version.
        """
        code, stdout, _ = self.run(["-s", serial, "shell", "getprop"], timeout=15)
        if code != 0:
            logger.warning("Could not get device info for %s", serial)
            return {}
        return self._parse_getprop(stdout)

    @staticmethod
    def _parse_getprop(output: str) -> dict:
        """Parse `adb shell getprop` output into a flat dict."""
        props: dict = {}
        for line in output.splitlines():
            match = re.match(r"\[(.+?)\]:\s*\[(.*)?\]", line)
            if match:
                props[match.group(1)] = match.group(2)

        return {
            "model": props.get("ro.product.model", ""),
            "manufacturer": props.get("ro.product.manufacturer", ""),
            "android_version": props.get("ro.build.version.release", ""),
            "sdk_version": props.get("ro.build.version.sdk", ""),
        }

    def enrich_device(self, device: Device) -> Device:
        """
        Populate a Device object with detailed info from getprop.

        Args:
            device: Device to enrich (must have state == DEVICE).

        Returns:
            The same device object with fields filled in.
        """
        if device.state != DeviceState.DEVICE:
            return device

        info = self.get_device_info(device.serial)
        device.model = info.get("model", "")
        device.manufacturer = info.get("manufacturer", "")
        device.android_version = info.get("android_version", "")
        device.sdk_version = info.get("sdk_version", "")
        return device

    # -------------------------------------------------------------------------
    # Wireless ADB
    # -------------------------------------------------------------------------

    def connect(self, ip: str, port: int = 5555) -> tuple[bool, str]:
        """
        Connect to a device over TCP/IP.

        Returns:
            (success, message)
        """
        code, stdout, stderr = self.run(["connect", f"{ip}:{port}"], timeout=15)
        output = stdout.strip() or stderr.strip()
        success = code == 0 and "connected" in output.lower() and "cannot" not in output.lower()
        return success, output

    def disconnect(self, ip: str, port: int = 5555) -> tuple[bool, str]:
        """
        Disconnect a TCP/IP device.

        Returns:
            (success, message)
        """
        code, stdout, stderr = self.run(["disconnect", f"{ip}:{port}"], timeout=10)
        output = stdout.strip() or stderr.strip()
        return code == 0, output

    # -------------------------------------------------------------------------
    # Version info
    # -------------------------------------------------------------------------

    def get_adb_version(self) -> str:
        """Return ADB version string, or empty string on failure."""
        code, stdout, _ = self.run(["version"], timeout=5)
        if code != 0:
            return ""
        for line in stdout.splitlines():
            if "Android Debug Bridge" in line:
                return line.strip()
        return stdout.strip().splitlines()[0] if stdout.strip() else ""

    # -------------------------------------------------------------------------
    # Quick Tools (Device Actions)
    # -------------------------------------------------------------------------

    def take_screenshot(self, serial: str, output_path: Path) -> tuple[bool, str]:
        """
        Capture device screen as PNG and write directly to output_path.
        Uses `adb exec-out screencap -p` for fast direct binary streaming.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [str(self._adb), "-s", serial, "exec-out", "screencap", "-p"]
        logger.debug("Taking screenshot: %s -> %s", cmd, output_path)
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW if subprocess.CREATE_NO_WINDOW else 0,
            )
            if res.returncode == 0 and res.stdout.startswith(b"\x89PNG\r\n\x1a\n"):
                output_path.write_bytes(res.stdout)
                logger.info("Screenshot saved: %s (%d bytes)", output_path, len(res.stdout))
                return True, str(output_path)
            err = res.stderr.decode("utf-8", errors="replace").strip() or "Invalid PNG stream received"
            logger.error("Screenshot failed: %s", err)
            return False, err
        except Exception as exc:
            logger.error("Screenshot error: %s", exc)
            return False, str(exc)

    def send_keyevent(self, serial: str, keycode: int) -> bool:
        """Send an Android keyevent (Power, Volume, Back, Home, Recent Apps)."""
        code, _, err = self.run(["-s", serial, "shell", "input", "keyevent", str(keycode)], timeout=5)
        if code != 0:
            logger.error("Keyevent %d failed on %s: %s", keycode, serial, err)
            return False
        return True

    def expand_notifications(self, serial: str) -> bool:
        """Expand the notification drawer."""
        code, _, err = self.run(["-s", serial, "shell", "cmd", "statusbar", "expand-notifications"], timeout=5)
        return code == 0

    def collapse_notifications(self, serial: str) -> bool:
        """Collapse the notification drawer."""
        code, _, err = self.run(["-s", serial, "shell", "cmd", "statusbar", "collapse"], timeout=5)
        return code == 0

    def open_settings(self, serial: str) -> bool:
        """Open Android Settings."""
        code, _, err = self.run(["-s", serial, "shell", "am", "start", "-a", "android.settings.SETTINGS"], timeout=5)
        return code == 0

    def send_text_input(self, serial: str, text: str) -> bool:
        """Type text into the currently active input field on the device."""
        if not text:
            return False
        safe_text = (
            text.replace(" ", "%s")
            .replace("&", "\\&")
            .replace("<", "\\<")
            .replace(">", "\\>")
            .replace("\"", "\\\"")
        )
        code, _, err = self.run(["-s", serial, "shell", "input", "text", safe_text], timeout=10)
        return code == 0

    def rotate_screen(self, serial: str, mode: str) -> bool:
        """
        Set or toggle screen orientation.
        mode: 'portrait', 'landscape', or 'auto'
        """
        if mode == "auto":
            code, out, _ = self.run(["-s", serial, "shell", "settings", "get", "system", "accelerometer_rotation"], timeout=5)
            curr = out.strip()
            new_val = "0" if curr == "1" else "1"
            c2, _, _ = self.run(["-s", serial, "shell", "settings", "put", "system", "accelerometer_rotation", new_val], timeout=5)
            return c2 == 0
        elif mode == "portrait":
            self.run(["-s", serial, "shell", "settings", "put", "system", "accelerometer_rotation", "0"], timeout=5)
            c2, _, _ = self.run(["-s", serial, "shell", "settings", "put", "system", "user_rotation", "0"], timeout=5)
            return c2 == 0
        elif mode == "landscape":
            self.run(["-s", serial, "shell", "settings", "put", "system", "accelerometer_rotation", "0"], timeout=5)
            c2, _, _ = self.run(["-s", serial, "shell", "settings", "put", "system", "user_rotation", "1"], timeout=5)
            return c2 == 0
        return False

    def reboot_device(self, serial: str, mode: str = "system") -> tuple[bool, str]:
        """
        Reboot the device.
        mode: 'system', 'recovery', 'bootloader' (or 'fastboot')
        """
        args = ["-s", serial, "reboot"]
        target = mode.lower().strip()
        if target in ("recovery", "bootloader", "fastboot"):
            args.append(target)
        elif target not in ("system", "normal", ""):
            args.append(target)

        logger.info("Executing ADB reboot (%s) on %s", target or "system", serial)
        code, out, err = self.run(args, timeout=12)
        if code == 0:
            logger.info("Reboot (%s) sent successfully to %s", target or "system", serial)
            return True, f"Reboot command ({target or 'system'}) executed."
        msg = err.strip() or out.strip() or "Failed to execute reboot command."
        logger.error("Reboot (%s) failed on %s: %s", target or "system", serial, msg)
        return False, msg


# ---------------------------------------------------------------------------
# QRunnable workers for async operations
# ---------------------------------------------------------------------------


class StartServerWorker(QRunnable):
    """Start ADB server in a background thread."""

    def __init__(self, service: ADBService) -> None:
        super().__init__()
        self.service = service
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        try:
            ok = self.service.start_server()
            self.signals.finished.emit(ok)
        except Exception as exc:
            self.signals.error.emit(str(exc))


class GetDevicesWorker(QRunnable):
    """Fetch device list in a background thread."""

    def __init__(self, service: ADBService) -> None:
        super().__init__()
        self.service = service
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        try:
            devices = self.service.get_devices()
            # Enrich each ready device
            for device in devices:
                if device.state == DeviceState.DEVICE:
                    self.service.enrich_device(device)
            self.signals.finished.emit(devices)
        except Exception as exc:
            logger.error("GetDevicesWorker error: %s", exc)
            self.signals.error.emit(str(exc))


class ConnectWorker(QRunnable):
    """Connect to a wireless device in a background thread."""

    def __init__(self, service: ADBService, ip: str, port: int) -> None:
        super().__init__()
        self.service = service
        self.ip = ip
        self.port = port
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        try:
            ok, msg = self.service.connect(self.ip, self.port)
            self.signals.finished.emit((ok, msg))
        except Exception as exc:
            self.signals.error.emit(str(exc))


class DisconnectWorker(QRunnable):
    """Disconnect a wireless device in a background thread."""

    def __init__(self, service: ADBService, ip: str, port: int) -> None:
        super().__init__()
        self.service = service
        self.ip = ip
        self.port = port
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        try:
            ok, msg = self.service.disconnect(self.ip, self.port)
            self.signals.finished.emit((ok, msg))
        except Exception as exc:
            self.signals.error.emit(str(exc))


class ScreenshotWorker(QRunnable):
    """Takes a screenshot in a background thread without freezing the UI."""

    def __init__(self, service: ADBService, serial: str, output_path: Path) -> None:
        super().__init__()
        self.service = service
        self.serial = serial
        self.output_path = output_path
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        try:
            ok, res = self.service.take_screenshot(self.serial, self.output_path)
            if ok:
                self.signals.finished.emit(res)
            else:
                self.signals.error.emit(res)
        except Exception as exc:
            self.signals.error.emit(str(exc))

