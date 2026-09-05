"""
ScrcpyService — launches, monitors, and terminates scrcpy processes.

Only manages processes that were started by this application.
Does NOT kill all scrcpy.exe processes system-wide.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from app.utils.logger import get_logger
from app.utils.paths import paths

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Process monitor thread
# ---------------------------------------------------------------------------

class ScrcpyMonitorThread(QThread):
    """
    Asynchronously reads scrcpy process output, logs each line,
    and emits a signal when the process exits.
    """

    process_exited = pyqtSignal(int, str)  # exit code, last error output

    def __init__(self, process: subprocess.Popen, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._process = process

    def run(self) -> None:
        """Read stdout/stderr until process exits, then emit exit code and last output."""
        output_lines: list[str] = []
        try:
            if self._process.stdout:
                for line in self._process.stdout:
                    cleaned = line.rstrip()
                    if cleaned:
                        logger.info("[scrcpy] %s", cleaned)
                        output_lines.append(cleaned)
                        if len(output_lines) > 30:
                            output_lines.pop(0)

            exit_code = self._process.wait()
            # Only extract genuine error/failure lines from process output
            error_lines = [
                line for line in output_lines
                if line.startswith("ERROR:") or "error:" in line.lower() or "exception" in line.lower() or "failed" in line.lower()
            ]
            last_err = "\n".join(error_lines[-6:]) if error_lines else ""
            logger.info("Scrcpy process exited with code %d.", exit_code)
            self.process_exited.emit(exit_code, last_err)
        except Exception as exc:
            logger.error("Monitor thread error: %s", exc)
            self.process_exited.emit(-1, str(exc))


# ---------------------------------------------------------------------------
# ScrcpyService
# ---------------------------------------------------------------------------

class ScrcpyService(QObject):
    """
    Manages the scrcpy subprocess lifecycle.

    Signals:
        started: Emitted when scrcpy process starts successfully.
        stopped(exit_code, last_error): Emitted when scrcpy process exits.
        error(message): Emitted when launch fails.
    """

    started = pyqtSignal()
    stopped = pyqtSignal(int, str)  # exit_code, last_error
    error = pyqtSignal(str)         # error message

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._process: Optional[subprocess.Popen] = None
        self._monitor: Optional[ScrcpyMonitorThread] = None
        self._intentional_stop: bool = False

    # -------------------------------------------------------------------------
    # State
    # -------------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        """Return True if scrcpy is currently running."""
        if self._process is None:
            return False
        return self._process.poll() is None

    # -------------------------------------------------------------------------
    # Launch
    # -------------------------------------------------------------------------

    def launch(self, args: list[str]) -> bool:
        """
        Start scrcpy with the given argument list.

        Args:
            args: Full command list including scrcpy.exe path.

        Returns:
            True if process started successfully.
        """
        if self.is_running:
            logger.warning("Scrcpy is already running.")
            return False

        self._intentional_stop = False

        if not paths.scrcpy_exists():
            msg = f"scrcpy.exe not found at {paths.scrcpy_exe}"
            logger.error(msg)
            self.error.emit("Scrcpy runtime was not found.")
            return False

        try:
            logger.info("Launching scrcpy: %s", args)

            # Ensure environment has ADB set and ADB dir in PATH
            # This is critical: scrcpy requires ADB in env or PATH to connect to adb server!
            env = os.environ.copy()
            env["ADB"] = str(paths.adb_exe)
            env["SCRCPY_ICON_DIR"] = str(paths.scrcpy_dir)
            env["SCRCPY_SERVER_PATH"] = str(paths.scrcpy_dir / "scrcpy-server")
            adb_dir_str = str(paths.adb_dir)
            scrcpy_dir_str = str(paths.scrcpy_dir)
            env["PATH"] = f"{adb_dir_str};{scrcpy_dir_str};{env.get('PATH', '')}"

            # Hide the black console window on Windows while keeping SDL3 mirror window active
            creationflags = 0
            startupinfo = None
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0  # SW_HIDE

            self._process = subprocess.Popen(
                args,
                cwd=str(paths.scrcpy_dir),
                env=env,
                creationflags=creationflags,
                startupinfo=startupinfo,
                # Capture stdout and stderr to monitor logs without buffer deadlocks.
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )

            # Start monitor thread
            self._monitor = ScrcpyMonitorThread(self._process, parent=self)
            self._monitor.process_exited.connect(self._on_process_exited)
            self._monitor.start()

            self.started.emit()
            logger.info("Scrcpy started (PID %d).", self._process.pid)
            return True

        except FileNotFoundError:
            msg = f"scrcpy.exe not found: {args[0]}"
            logger.error(msg)
            self.error.emit("Unable to start scrcpy. Executable not found.")
            return False
        except Exception as exc:
            logger.error("Failed to launch scrcpy: %s", exc)
            self.error.emit(f"Unable to start scrcpy: {exc}")
            return False

    # -------------------------------------------------------------------------
    # Stop
    # -------------------------------------------------------------------------

    def stop(self) -> None:
        """
        Terminate the scrcpy process started by this service.
        Does NOT affect any other scrcpy processes running on the system.
        """
        if not self.is_running:
            logger.debug("stop() called but scrcpy is not running.")
            return

        self._intentional_stop = True
        logger.info("Stopping scrcpy (PID %d).", self._process.pid)
        try:
            self._process.terminate()
        except Exception as exc:
            logger.warning("Could not terminate scrcpy gracefully: %s — forcing.", exc)
            try:
                self._process.kill()
            except Exception as kill_exc:
                logger.error("Could not kill scrcpy: %s", kill_exc)

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    def cleanup(self) -> None:
        """Stop process and wait for monitor thread to finish."""
        self.stop()
        if self._monitor and self._monitor.isRunning():
            self._monitor.wait(2000)

    # -------------------------------------------------------------------------
    # Internal slots
    # -------------------------------------------------------------------------

    def _on_process_exited(self, exit_code: int, last_error: str) -> None:
        """Called by the monitor thread when scrcpy exits."""
        self._process = None
        self._monitor = None
        if self._intentional_stop:
            logger.info("Process exit was requested by user — treating as clean exit.")
            exit_code = 0
            last_error = ""
        self._intentional_stop = False
        self.stopped.emit(exit_code, last_error)
        logger.info("ScrcpyService: process_exited signal handled (code %d).", exit_code)
