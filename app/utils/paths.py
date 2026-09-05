"""
PathManager — resolves file paths correctly in both dev and PyInstaller frozen mode.
"""

import os
import sys
from pathlib import Path


class PathManager:
    """
    Provides stable paths regardless of whether the app runs from source
    or as a PyInstaller-bundled executable.
    """

    _instance: "PathManager | None" = None

    def __new__(cls) -> "PathManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self._app_root = self._resolve_app_root()

    def _resolve_app_root(self) -> Path:
        """
        Determine the application root directory.

        - Frozen (PyInstaller): directory of the .exe
        - Development: two levels up from this file (project root)
        """
        if getattr(sys, "frozen", False):
            # Running as compiled executable
            return Path(sys.executable).parent.resolve()
        else:
            # Running from source: this file is at app/utils/paths.py
            return Path(__file__).parent.parent.parent.resolve()

    # -------------------------------------------------------------------------
    # Root
    # -------------------------------------------------------------------------

    @property
    def app_root(self) -> Path:
        """Project / distribution root directory."""
        return self._app_root

    # -------------------------------------------------------------------------
    # Runtime
    # -------------------------------------------------------------------------

    @property
    def runtime_dir(self) -> Path:
        return self._app_root / "runtime"

    @property
    def scrcpy_dir(self) -> Path:
        return self.runtime_dir / "scrcpy"

    @property
    def scrcpy_exe(self) -> Path:
        return self.scrcpy_dir / "scrcpy.exe"

    @property
    def adb_dir(self) -> Path:
        return self.runtime_dir / "adb"

    @property
    def adb_exe(self) -> Path:
        return self.adb_dir / "adb.exe"

    # -------------------------------------------------------------------------
    # Config & Logs (user data — writable)
    # -------------------------------------------------------------------------

    @property
    def user_data_dir(self) -> Path:
        """
        %APPDATA%\\Xeon Scrcpy Controller — user-writable location.
        Falls back to app_root if APPDATA is unavailable.
        """
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "Xeon Scrcpy Controller"
        return self._app_root

    @property
    def config_dir(self) -> Path:
        return self.user_data_dir / "config"

    @property
    def settings_file(self) -> Path:
        return self.config_dir / "settings.json"

    @property
    def presets_file(self) -> Path:
        return self.config_dir / "presets.json"

    @property
    def logs_dir(self) -> Path:
        """
        Directory where application logs are stored.
        In dev mode: written directly to the project's 'logs' directory.
        In frozen mode: %APPDATA%/Xeon Scrcpy Controller/logs.
        """
        if not getattr(sys, "frozen", False):
            return self._app_root / "logs"
        return self.user_data_dir / "logs"

    @property
    def log_file(self) -> Path:
        return self.logs_dir / "application.log"

    @property
    def screenshots_dir(self) -> Path:
        """
        Directory where screenshots are saved.
        Default to %USERPROFILE%\\Pictures\\ScrcpyScreenshots for user convenience.
        """
        userprofile = os.environ.get("USERPROFILE")
        if userprofile:
            return Path(userprofile) / "Pictures" / "ScrcpyScreenshots"
        return self.logs_dir / "screenshots"

    # -------------------------------------------------------------------------
    # Resources
    # -------------------------------------------------------------------------

    @property
    def resources_dir(self) -> Path:
        # Check standard app/resources first
        res = self._app_root / "app" / "resources"
        if res.exists():
            return res
        # Check PyInstaller v6 _internal/app/resources
        internal_res = self._app_root / "_internal" / "app" / "resources"
        if internal_res.exists():
            return internal_res
        return res

    @property
    def icon_ico(self) -> Path:
        ico = self.resources_dir / "icon.ico"
        if ico.exists():
            return ico
        internal_ico = self._app_root / "_internal" / "app" / "resources" / "icon.ico"
        if internal_ico.exists():
            return internal_ico
        return ico

    @property
    def icon_png(self) -> Path:
        """High-resolution PNG icon path."""
        res_png = self.resources_dir / "icon.png"
        if res_png.exists():
            return res_png
        internal_res_png = self._app_root / "_internal" / "app" / "resources" / "icon.png"
        if internal_res_png.exists():
            return internal_res_png
        logo = self._app_root / "LogoAplikasi" / "icon.png"
        if logo.exists():
            return logo
        internal_logo = self._app_root / "_internal" / "LogoAplikasi" / "icon.png"
        if internal_logo.exists():
            return internal_logo
        return res_png

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def ensure_dirs(self) -> None:
        """Create writable directories if they don't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    def scrcpy_exists(self) -> bool:
        return self.scrcpy_exe.exists()

    def adb_exists(self) -> bool:
        return self.adb_exe.exists()

    def icon_path(self) -> Path:
        """Return highest quality icon path (PNG preferred for sharp rendering)."""
        if self.icon_png.exists():
            return self.icon_png
        if self.icon_ico.exists():
            return self.icon_ico
        return self.icon_png


# Singleton instance
paths = PathManager()
