"""
Tests for ADBService._parse_devices — uses mock strings, no device required.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.services.adb_service import ADBService
from app.models.device import DeviceState, TransportType


def parse(output: str):
    return ADBService._parse_devices(output)


def test_empty_output():
    result = parse("List of devices attached\n")
    assert result == []


def test_single_usb_device():
    output = "List of devices attached\nR58M123456\tdevice\n"
    devices = parse(output)
    assert len(devices) == 1
    assert devices[0].serial == "R58M123456"
    assert devices[0].state == DeviceState.DEVICE
    assert devices[0].transport_type == TransportType.USB


def test_single_tcp_device():
    output = "List of devices attached\n192.168.1.5:5555\tdevice\n"
    devices = parse(output)
    assert len(devices) == 1
    assert devices[0].serial == "192.168.1.5:5555"
    assert devices[0].transport_type == TransportType.TCP


def test_unauthorized_device():
    output = "List of devices attached\nR58M123456\tunauthorized\n"
    devices = parse(output)
    assert devices[0].state == DeviceState.UNAUTHORIZED


def test_offline_device():
    output = "List of devices attached\nR58M123456\toffline\n"
    devices = parse(output)
    assert devices[0].state == DeviceState.OFFLINE


def test_multiple_devices():
    output = (
        "List of devices attached\n"
        "R58M123456\tdevice\n"
        "192.168.1.5:5555\tdevice\n"
    )
    devices = parse(output)
    assert len(devices) == 2
    serials = [d.serial for d in devices]
    assert "R58M123456" in serials
    assert "192.168.1.5:5555" in serials


def test_mixed_states():
    output = (
        "List of devices attached\n"
        "R58M000001\tdevice\n"
        "R58M000002\tunauthorized\n"
        "R58M000003\toffline\n"
    )
    devices = parse(output)
    assert len(devices) == 3
    states = {d.serial: d.state for d in devices}
    assert states["R58M000001"] == DeviceState.DEVICE
    assert states["R58M000002"] == DeviceState.UNAUTHORIZED
    assert states["R58M000003"] == DeviceState.OFFLINE


def test_daemon_notice_lines_ignored():
    output = (
        "* daemon not running; starting now at tcp:5037\n"
        "* daemon started successfully\n"
        "List of devices attached\n"
        "R58M123456\tdevice\n"
    )
    devices = parse(output)
    assert len(devices) == 1
    assert devices[0].serial == "R58M123456"


def test_parse_getprop():
    sample = (
        "[ro.product.model]: [Redmi Note 30 Pro]\n"
        "[ro.product.manufacturer]: [Xiaomi]\n"
        "[ro.build.version.release]: [14]\n"
        "[ro.build.version.sdk]: [34]\n"
    )
    info = ADBService._parse_getprop(sample)
    assert info["model"] == "Redmi Note 30 Pro"
    assert info["manufacturer"] == "Xiaomi"
    assert info["android_version"] == "14"
    assert info["sdk_version"] == "34"
