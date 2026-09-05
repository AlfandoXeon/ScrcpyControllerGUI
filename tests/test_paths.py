"""
Tests for PathManager — dev mode (no PyInstaller required).
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from pathlib import Path
from app.utils.paths import PathManager


@pytest.fixture
def pm():
    # Fresh PathManager instance for testing
    pm = PathManager.__new__(PathManager)
    pm._initialized = False
    PathManager.__init__(pm)
    return pm


def test_app_root_is_directory(pm):
    assert pm.app_root.is_dir()


def test_adb_exe_path_is_under_runtime(pm):
    assert "runtime" in str(pm.adb_exe)
    assert pm.adb_exe.name == "adb.exe"


def test_scrcpy_exe_path_is_under_runtime(pm):
    assert "runtime" in str(pm.scrcpy_exe)
    assert pm.scrcpy_exe.name == "scrcpy.exe"


def test_config_dir_contains_config(pm):
    assert "config" in str(pm.config_dir).lower() or "appdata" in str(pm.config_dir).lower()


def test_ensure_dirs_creates_directories(pm, tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    # Recreate with new env
    pm2 = PathManager.__new__(PathManager)
    pm2._initialized = False
    PathManager.__init__(pm2)
    pm2.ensure_dirs()
    assert pm2.config_dir.exists()
    assert pm2.logs_dir.exists()


def test_icon_path_returns_path(pm):
    p = pm.icon_path()
    assert isinstance(p, Path)


def test_runtime_files_exist_in_dev():
    """Check actual dev files are present after setup."""
    pm = PathManager()
    assert pm.adb_exists(), f"adb.exe not found at {pm.adb_exe}"
    assert pm.scrcpy_exists(), f"scrcpy.exe not found at {pm.scrcpy_exe}"
