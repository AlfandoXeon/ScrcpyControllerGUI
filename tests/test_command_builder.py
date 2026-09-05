"""
Tests for CommandBuilder — no Android device required.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.models.config import ScrcpyConfig
from app.services.command_builder import CommandBuilder, ScrcpyCapabilities
from app.utils.paths import paths


@pytest.fixture
def builder():
    return CommandBuilder(scrcpy_path=paths.scrcpy_exe)


def test_basic_command_has_serial(builder):
    config = ScrcpyConfig()
    args = builder.build(config, serial="R58M123456")
    assert "--serial" in args
    assert "R58M123456" in args


def test_max_size_added_when_nonzero(builder):
    config = ScrcpyConfig(max_size=1080)
    args = builder.build(config, serial="test")
    assert "--max-size" in args
    assert "1080" in args


def test_max_size_omitted_when_zero(builder):
    config = ScrcpyConfig(max_size=0)
    args = builder.build(config, serial="test")
    assert "--max-size" not in args


def test_fps_included(builder):
    config = ScrcpyConfig(max_fps=30)
    args = builder.build(config, serial="test")
    assert "--max-fps" in args
    assert "30" in args


def test_bitrate_included(builder):
    config = ScrcpyConfig(bitrate="4M")
    args = builder.build(config, serial="test")
    assert "--video-bit-rate" in args
    assert "4M" in args


def test_no_audio_flag(builder):
    config = ScrcpyConfig(audio_enabled=False)
    args = builder.build(config, serial="test")
    assert "--no-audio" in args


def test_audio_enabled_no_flag(builder):
    config = ScrcpyConfig(audio_enabled=True)
    args = builder.build(config, serial="test")
    assert "--no-audio" not in args


def test_fullscreen_flag(builder):
    config = ScrcpyConfig(fullscreen=True)
    args = builder.build(config, serial="test")
    assert "--fullscreen" in args


def test_stay_awake_flag(builder):
    config = ScrcpyConfig(stay_awake=True)
    args = builder.build(config, serial="test")
    assert "--stay-awake" in args


def test_show_touches_flag(builder):
    config = ScrcpyConfig(show_touches=True)
    args = builder.build(config, serial="test")
    assert "--show-touches" in args


def test_window_title_included(builder):
    config = ScrcpyConfig(window_title="My Mirror")
    args = builder.build(config, serial="test")
    assert "--window-title" in args
    assert "My Mirror" in args


def test_window_title_empty_omitted(builder):
    config = ScrcpyConfig(window_title="")
    args = builder.build(config, serial="test")
    assert "--window-title" not in args


def test_valid_custom_args_appended(builder):
    config = ScrcpyConfig(custom_args="--no-control")
    args = builder.build(config, serial="test")
    assert "--no-control" in args


def test_invalid_custom_args_rejected(builder):
    # Shell injection attempt — should be silently dropped
    config = ScrcpyConfig(custom_args="--no-control; rm -rf /")
    args = builder.build(config, serial="test")
    assert "rm" not in args
    assert ";" not in args


def test_command_is_list_not_string(builder):
    config = ScrcpyConfig()
    args = builder.build(config, serial="test")
    assert isinstance(args, list)
    for arg in args:
        assert isinstance(arg, str)


def test_preview_string_returns_string(builder):
    config = ScrcpyConfig(max_fps=60)
    preview = builder.preview_string(config, serial="test")
    assert isinstance(preview, str)
    assert "test" in preview


# ---------------------------------------------------------------------------
# Camera mode tests
# ---------------------------------------------------------------------------

from app.services.command_builder import CameraConfig, CameraCommandBuilder


@pytest.fixture
def camera_builder():
    return CameraCommandBuilder(scrcpy_path=paths.scrcpy_exe)


def test_camera_command_basic(camera_builder):
    config = CameraConfig(facing="back", size="1920x1080", fps=60, no_audio=True)
    args = camera_builder.build(config, serial="CAM_DEVICE")
    assert "--serial" in args
    assert "CAM_DEVICE" in args
    assert "--video-source=camera" in args
    assert "--camera-facing=back" in args
    assert "--camera-size=1920x1080" in args
    assert "--camera-fps=60" in args
    assert "--no-audio" in args


def test_camera_auto_size_omitted(camera_builder):
    config = CameraConfig(size="auto")
    args = camera_builder.build(config, serial="CAM_DEVICE")
    assert not any(arg.startswith("--camera-size") for arg in args)


def test_camera_custom_args(camera_builder):
    config = CameraConfig(custom_args="--window-title MyCam")
    args = camera_builder.build(config, serial="CAM_DEVICE")
    assert "--window-title" in args
    assert "MyCam" in args


def test_camera_preview_string(camera_builder):
    config = CameraConfig()
    preview = camera_builder.preview_string(config, serial="CAM_DEVICE")
    assert isinstance(preview, str)
    assert "--video-source=camera" in preview


# ---------------------------------------------------------------------------
# OTG mode tests
# ---------------------------------------------------------------------------

from app.services.command_builder import OTGConfig, OTGCommandBuilder


@pytest.fixture
def otg_builder():
    return OTGCommandBuilder(scrcpy_path=paths.scrcpy_exe)


def test_otg_command_basic(otg_builder):
    config = OTGConfig(mode="otg")
    args = otg_builder.build(config, serial="OTG_DEVICE")
    assert "--serial" in args
    assert "OTG_DEVICE" in args
    assert "--otg" in args
    assert "--no-video" not in args


def test_otg_command_no_display(otg_builder):
    config = OTGConfig(mode="no_display")
    args = otg_builder.build(config, serial="OTG_DEVICE")
    assert "--no-video" in args
    assert "--no-audio" in args
    assert "--keyboard=uhid" in args
    assert "--mouse=uhid" in args
    assert "--otg" not in args


def test_otg_disable_keyboard_and_mouse(otg_builder):
    config = OTGConfig(mode="no_display", disable_keyboard=True, disable_mouse=True)
    args = otg_builder.build(config, serial="OTG_DEVICE")
    assert "--no-keyboard" in args
    assert "--no-mouse" in args
    assert "--keyboard=uhid" not in args
    assert "--mouse=uhid" not in args


def test_otg_stay_awake_and_screen_off(otg_builder):
    config = OTGConfig(mode="otg", stay_awake=True, turn_screen_off=True)
    args = otg_builder.build(config, serial="OTG_DEVICE")
    assert "--stay-awake" in args
    assert "--turn-screen-off" in args


def test_otg_custom_args(otg_builder):
    config = OTGConfig(custom_args="--window-title MyOTG")
    args = otg_builder.build(config, serial="OTG_DEVICE")
    assert "--window-title" in args
    assert "MyOTG" in args


def test_otg_config_dict_roundtrip():
    original = OTGConfig(
        mode="no_display",
        disable_keyboard=True,
        disable_mouse=False,
        stay_awake=False,
        turn_screen_off=True,
        custom_args="--hid-keyboard",
    )
    d = original.to_dict()
    restored = OTGConfig.from_dict(d)
    assert original == restored


