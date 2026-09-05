"""
ScrcpyConfig — holds all user-configurable scrcpy parameters.
"""

from dataclasses import dataclass, field


@dataclass
class ScrcpyConfig:
    """
    All configurable scrcpy options.

    Each field maps directly to one or more scrcpy CLI arguments.
    See CommandBuilder for how these are translated to an arglist.
    """

    # -- Video -----------------------------------------------------------------
    max_size: int = 0             # 0 = original; else --max-size VALUE
    max_fps: int = 60             # --max-fps VALUE
    bitrate: str = "8M"          # --video-bit-rate VALUE
    video_codec: str = "h264"    # --video-codec VALUE

    # -- Audio -----------------------------------------------------------------
    audio_enabled: bool = True   # False → --no-audio
    audio_source: str = "output" # --audio-source VALUE (if supported)

    # -- Window ----------------------------------------------------------------
    fullscreen: bool = False      # --fullscreen
    always_on_top: bool = False   # --always-on-top
    borderless: bool = False      # --window-borderless
    window_title: str = ""        # --window-title VALUE (empty = use default)

    # -- Behavior --------------------------------------------------------------
    stay_awake: bool = False      # --stay-awake
    turn_screen_off: bool = False # --turn-screen-off
    show_touches: bool = False    # --show-touches

    # -- Advanced --------------------------------------------------------------
    custom_args: str = ""         # raw extra args, parsed by CommandBuilder

    def to_dict(self) -> dict:
        """Serialize config to a plain dict (for JSON storage)."""
        return {
            "max_size": self.max_size,
            "max_fps": self.max_fps,
            "bitrate": self.bitrate,
            "video_codec": self.video_codec,
            "audio_enabled": self.audio_enabled,
            "audio_source": self.audio_source,
            "fullscreen": self.fullscreen,
            "always_on_top": self.always_on_top,
            "borderless": self.borderless,
            "window_title": self.window_title,
            "stay_awake": self.stay_awake,
            "turn_screen_off": self.turn_screen_off,
            "show_touches": self.show_touches,
            "custom_args": self.custom_args,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScrcpyConfig":
        """Deserialize from a plain dict (from JSON storage)."""
        return cls(
            max_size=int(data.get("max_size", 0)),
            max_fps=int(data.get("max_fps", 60)),
            bitrate=str(data.get("bitrate", "8M")),
            video_codec=str(data.get("video_codec", "h264")),
            audio_enabled=bool(data.get("audio_enabled", True)),
            audio_source=str(data.get("audio_source", "output")),
            fullscreen=bool(data.get("fullscreen", False)),
            always_on_top=bool(data.get("always_on_top", False)),
            borderless=bool(data.get("borderless", False)),
            window_title=str(data.get("window_title", "")),
            stay_awake=bool(data.get("stay_awake", False)),
            turn_screen_off=bool(data.get("turn_screen_off", False)),
            show_touches=bool(data.get("show_touches", False)),
            custom_args=str(data.get("custom_args", "")),
        )
