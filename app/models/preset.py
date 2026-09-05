"""
Preset model — a named ScrcpyConfig snapshot.
"""

from dataclasses import dataclass, field
from app.models.config import ScrcpyConfig


@dataclass
class Preset:
    """
    A named configuration preset.

    Attributes:
        name: Human-readable preset name.
        config: The ScrcpyConfig this preset represents.
        is_builtin: True for factory presets (cannot be deleted).
    """

    name: str
    config: ScrcpyConfig = field(default_factory=ScrcpyConfig)
    is_builtin: bool = False

    def to_dict(self) -> dict:
        """Serialize to dict for JSON storage."""
        return {
            "name": self.name,
            "config": self.config.to_dict(),
            "is_builtin": self.is_builtin,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Preset":
        """Deserialize from dict."""
        return cls(
            name=str(data.get("name", "Unnamed")),
            config=ScrcpyConfig.from_dict(data.get("config", {})),
            is_builtin=bool(data.get("is_builtin", False)),
        )


# ---------------------------------------------------------------------------
# Built-in presets
# ---------------------------------------------------------------------------

BUILTIN_PRESETS: list[Preset] = [
    Preset(
        name="Default",
        config=ScrcpyConfig(),
        is_builtin=True,
    ),
    Preset(
        name="Gaming",
        config=ScrcpyConfig(
            max_size=1920,
            max_fps=60,
            bitrate="12M",
            audio_enabled=True,
            fullscreen=True,
            stay_awake=True,
        ),
        is_builtin=True,
    ),
    Preset(
        name="Recording",
        config=ScrcpyConfig(
            max_size=1080,
            max_fps=60,
            bitrate="12M",
            audio_enabled=True,
            stay_awake=True,
            turn_screen_off=False,
        ),
        is_builtin=True,
    ),
    Preset(
        name="High Quality",
        config=ScrcpyConfig(
            max_size=1920,
            max_fps=60,
            bitrate="16M",
            audio_enabled=True,
        ),
        is_builtin=True,
    ),
    Preset(
        name="Low Bandwidth",
        config=ScrcpyConfig(
            max_size=720,
            max_fps=30,
            bitrate="2M",
            audio_enabled=False,
        ),
        is_builtin=True,
    ),
]
