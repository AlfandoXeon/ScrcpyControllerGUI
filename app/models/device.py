"""
Device model — represents a connected Android device.
"""

from dataclasses import dataclass, field
from enum import Enum


class DeviceState(str, Enum):
    """Possible ADB device states."""
    DEVICE = "device"
    OFFLINE = "offline"
    UNAUTHORIZED = "unauthorized"
    UNKNOWN = "unknown"


class TransportType(str, Enum):
    """Connection transport type."""
    USB = "usb"
    TCP = "tcp"
    UNKNOWN = "unknown"


@dataclass
class Device:
    """
    Represents a connected Android device as reported by ADB.

    Attributes:
        serial: ADB device serial (e.g. "R58M123456" or "192.168.1.5:5555").
        state: Current ADB state.
        model: Device model name.
        manufacturer: Device manufacturer.
        android_version: Android OS version string.
        sdk_version: Android SDK level.
        transport_type: USB or TCP/IP connection.
    """

    serial: str
    state: DeviceState = DeviceState.UNKNOWN
    model: str = ""
    manufacturer: str = ""
    android_version: str = ""
    sdk_version: str = ""
    transport_type: TransportType = TransportType.UNKNOWN

    def __post_init__(self) -> None:
        # Auto-detect transport type from serial format
        if self.transport_type == TransportType.UNKNOWN:
            if ":" in self.serial:
                self.transport_type = TransportType.TCP
            else:
                self.transport_type = TransportType.USB

    @property
    def display_name(self) -> str:
        """Human-readable name for display in UI."""
        if self.model:
            return f"{self.model} ({self.serial})"
        return self.serial

    @property
    def is_ready(self) -> bool:
        """Return True if device is connected and authorized."""
        return self.state == DeviceState.DEVICE

    @property
    def connection_type_label(self) -> str:
        """Human-readable connection type."""
        if self.transport_type == TransportType.TCP:
            return "Wi-Fi (TCP/IP)"
        elif self.transport_type == TransportType.USB:
            return "USB"
        return "Unknown"

    def to_dict(self) -> dict:
        """Serialize to dict (for logging / diagnostics)."""
        return {
            "serial": self.serial,
            "state": self.state.value,
            "model": self.model,
            "manufacturer": self.manufacturer,
            "android_version": self.android_version,
            "sdk_version": self.sdk_version,
            "transport_type": self.transport_type.value,
        }
