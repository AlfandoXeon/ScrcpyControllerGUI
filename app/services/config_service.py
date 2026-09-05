"""
ConfigService — loads and saves application settings from/to JSON.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

from app.models.config import ScrcpyConfig
from app.services.command_builder import CameraConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ConfigService:
    """
    Manages persistent application settings.

    Stores settings in <user_data>/config/settings.json.
    If the file is corrupt, it is backed up and reset to defaults.
    """

    _DEFAULTS: dict = {
        "last_device_serial": "",
        "last_preset_name": "Default",
        "mock_mode": False,
        "scrcpy_config": {},
        "camera_config": {},
    }

    def __init__(self, settings_file: Path) -> None:
        self._path = settings_file
        self._data: dict = {}
        self.load()

    # -------------------------------------------------------------------------
    # Load / Save
    # -------------------------------------------------------------------------

    def load(self) -> None:
        """Load settings from disk. Resets to defaults on error."""
        if not self._path.exists():
            logger.info("Settings file not found — using defaults.")
            self._data = dict(self._DEFAULTS)
            return

        try:
            raw = self._path.read_text(encoding="utf-8")
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError("Settings file root is not a JSON object.")
            self._data = {**self._DEFAULTS, **parsed}
            logger.info("Settings loaded from %s", self._path)
        except Exception as exc:
            logger.error("Failed to load settings: %s — resetting to defaults.", exc)
            self._backup_corrupt()
            self._data = dict(self._DEFAULTS)

    def save(self) -> None:
        """Persist current settings to disk."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug("Settings saved to %s", self._path)
        except Exception as exc:
            logger.error("Failed to save settings: %s", exc)

    def _backup_corrupt(self) -> None:
        """Rename corrupt settings file with a timestamp suffix."""
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = self._path.with_suffix(f".corrupt_{ts}.json")
            shutil.move(str(self._path), str(backup))
            logger.warning("Corrupt settings backed up to %s", backup)
        except Exception as exc:
            logger.error("Could not back up corrupt settings: %s", exc)

    # -------------------------------------------------------------------------
    # Accessors
    # -------------------------------------------------------------------------

    def get_last_device_serial(self) -> str:
        return str(self._data.get("last_device_serial", ""))

    def set_last_device_serial(self, serial: str) -> None:
        self._data["last_device_serial"] = serial

    def get_last_preset_name(self) -> str:
        return str(self._data.get("last_preset_name", "Default"))

    def set_last_preset_name(self, name: str) -> None:
        self._data["last_preset_name"] = name

    def is_mock_mode(self) -> bool:
        return bool(self._data.get("mock_mode", False))

    def get_scrcpy_config(self) -> ScrcpyConfig:
        """Return the last-used ScrcpyConfig."""
        raw = self._data.get("scrcpy_config", {})
        try:
            return ScrcpyConfig.from_dict(raw)
        except Exception as exc:
            logger.warning("Could not parse saved scrcpy config: %s — using defaults.", exc)
            return ScrcpyConfig()

    def set_scrcpy_config(self, config: ScrcpyConfig) -> None:
        self._data["scrcpy_config"] = config.to_dict()

    def get_camera_config(self) -> CameraConfig:
        """Return the last-used CameraConfig."""
        raw = self._data.get("camera_config", {})
        try:
            return CameraConfig.from_dict(raw)
        except Exception as exc:
            logger.warning("Could not parse saved camera config: %s — using defaults.", exc)
            return CameraConfig()

    def set_camera_config(self, config: CameraConfig) -> None:
        self._data["camera_config"] = config.to_dict()
