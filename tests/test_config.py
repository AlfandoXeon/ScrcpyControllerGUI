"""
Tests for ConfigService — no Android device required.
"""

import sys, os, json, tempfile
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.services.config_service import ConfigService
from app.models.config import ScrcpyConfig


@pytest.fixture
def tmp_config(tmp_path):
    return tmp_path / "settings.json"


def test_defaults_when_no_file(tmp_config):
    svc = ConfigService(tmp_config)
    assert svc.get_last_device_serial() == ""
    assert svc.get_last_preset_name() == "Default"
    assert svc.is_mock_mode() is False


def test_save_and_reload(tmp_config):
    svc = ConfigService(tmp_config)
    svc.set_last_device_serial("R58M999")
    svc.set_last_preset_name("Gaming")
    svc.save()

    svc2 = ConfigService(tmp_config)
    assert svc2.get_last_device_serial() == "R58M999"
    assert svc2.get_last_preset_name() == "Gaming"


def test_corrupt_config_resets_to_defaults(tmp_config):
    tmp_config.write_text("{ this is not valid json !!!")
    svc = ConfigService(tmp_config)
    # Should not crash and should return defaults
    assert svc.get_last_preset_name() == "Default"


def test_scrcpy_config_roundtrip(tmp_config):
    svc = ConfigService(tmp_config)
    config = ScrcpyConfig(max_size=720, max_fps=30, bitrate="2M", audio_enabled=False)
    svc.set_scrcpy_config(config)
    svc.save()

    svc2 = ConfigService(tmp_config)
    restored = svc2.get_scrcpy_config()
    assert restored.max_size == 720
    assert restored.max_fps == 30
    assert restored.bitrate == "2M"
    assert restored.audio_enabled is False


def test_corrupt_scrcpy_config_returns_defaults(tmp_config):
    tmp_config.write_text(json.dumps({"scrcpy_config": "not_a_dict"}))
    svc = ConfigService(tmp_config)
    config = svc.get_scrcpy_config()
    assert isinstance(config, ScrcpyConfig)
    assert config.max_fps == 60  # default
