"""
CommandBuilder — constructs scrcpy argument lists safely.

Uses argument lists (never string concatenation) to prevent injection.
Only includes arguments supported by scrcpy v4.1.
"""

from dataclasses import dataclass
from app.models.config import ScrcpyConfig
from app.utils.logger import get_logger
from app.utils.validators import parse_custom_args, validate_custom_args
from app.utils.paths import paths

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Scrcpy v4.1 capabilities
# ---------------------------------------------------------------------------

class ScrcpyCapabilities:
    """
    Defines the arguments supported by the bundled scrcpy version (4.1).
    Only expose options that are actually supported to prevent invalid commands.
    """

    SUPPORTED_VIDEO_CODECS = ["h264", "h265", "av1"]
    SUPPORTED_AUDIO_SOURCES = ["output", "mic", "playback"]

    MAX_SIZE_OPTIONS: list[int] = [0, 480, 720, 1080, 1440, 1920]
    FPS_OPTIONS: list[int] = [15, 24, 30, 45, 60, 120]
    BITRATE_OPTIONS: list[str] = ["2M", "4M", "6M", "8M", "12M", "16M"]

    # Flags supported in v4.1
    SUPPORTS_AUDIO = True
    SUPPORTS_AUDIO_SOURCE = True
    SUPPORTS_VIDEO_CODEC = True
    SUPPORTS_BORDERLESS = True
    SUPPORTS_ALWAYS_ON_TOP = True
    SUPPORTS_STAY_AWAKE = True
    SUPPORTS_TURN_SCREEN_OFF = True
    SUPPORTS_SHOW_TOUCHES = True

    # Camera mode (--video-source=camera) — supported in v4.1+
    SUPPORTS_CAMERA = True
    CAMERA_FACING_OPTIONS = ["back", "front", "external"]
    CAMERA_SIZE_OPTIONS = [
        "auto",
        "640x480",
        "1280x720",
        "1920x1080",
        "2560x1440",
        "3840x2160",
    ]
    CAMERA_FPS_OPTIONS: list[int] = [15, 24, 30, 60, 120]


# ---------------------------------------------------------------------------
# CameraConfig dataclass
# ---------------------------------------------------------------------------

@dataclass
class CameraConfig:
    """
    Configuration for scrcpy camera mode.

    When active, uses --video-source=camera instead of screen mirroring.

    Reference:
        scrcpy --video-source=camera --camera-facing=back --camera-size=1920x1080 --no-audio
    """

    facing: str = "back"         # --camera-facing=VALUE
    size: str = "1920x1080"      # --camera-size=VALUE ("auto" = omit flag)
    fps: int = 60                # --camera-fps=VALUE
    no_audio: bool = True        # --no-audio
    video_codec: str = "h264"    # --video-codec
    bitrate: str = "8M"          # --video-bit-rate
    fullscreen: bool = False      # --fullscreen
    always_on_top: bool = False   # --always-on-top
    custom_args: str = ""         # extra raw args

    def to_dict(self) -> dict:
        return {
            "facing": self.facing,
            "size": self.size,
            "fps": self.fps,
            "no_audio": self.no_audio,
            "video_codec": self.video_codec,
            "bitrate": self.bitrate,
            "fullscreen": self.fullscreen,
            "always_on_top": self.always_on_top,
            "custom_args": self.custom_args,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CameraConfig":
        return cls(
            facing=str(data.get("facing", "back")),
            size=str(data.get("size", "1920x1080")),
            fps=int(data.get("fps", 60)),
            no_audio=bool(data.get("no_audio", True)),
            video_codec=str(data.get("video_codec", "h264")),
            bitrate=str(data.get("bitrate", "8M")),
            fullscreen=bool(data.get("fullscreen", False)),
            always_on_top=bool(data.get("always_on_top", False)),
            custom_args=str(data.get("custom_args", "")),
        )


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

def _args_to_display(args: list[str]) -> str:
    """Format an arg list as a readable command string."""
    parts = []
    for arg in args:
        if " " in arg:
            parts.append(f'"{arg}"')
        else:
            parts.append(arg)
    return " ".join(parts)


# ---------------------------------------------------------------------------
# CommandBuilder (screen mirroring)
# ---------------------------------------------------------------------------

class CommandBuilder:
    """
    Builds the scrcpy argument list from a ScrcpyConfig (screen mirror mode).
    Returns a list of strings for subprocess. Never uses shell=True.
    """

    def __init__(self, scrcpy_path=None) -> None:
        self._scrcpy_exe = scrcpy_path or paths.scrcpy_exe
        self._caps = ScrcpyCapabilities()

    def build(self, config: ScrcpyConfig, serial: str) -> list[str]:
        """
        Build the complete argument list for scrcpy screen mirroring.

        Args:
            config: User configuration.
            serial: Target device serial.

        Returns:
            Argument list starting with the scrcpy.exe path.
        """
        args: list[str] = [str(self._scrcpy_exe)]

        args += ["--serial", serial]

        # Video
        if config.max_size > 0:
            args += ["--max-size", str(config.max_size)]
        if config.max_fps > 0:
            args += ["--max-fps", str(config.max_fps)]
        if config.bitrate:
            args += ["--video-bit-rate", config.bitrate]
        if self._caps.SUPPORTS_VIDEO_CODEC and config.video_codec in self._caps.SUPPORTED_VIDEO_CODECS:
            args += ["--video-codec", config.video_codec]

        # Audio
        if self._caps.SUPPORTS_AUDIO:
            if not config.audio_enabled:
                args.append("--no-audio")
            elif self._caps.SUPPORTS_AUDIO_SOURCE and config.audio_source in self._caps.SUPPORTED_AUDIO_SOURCES:
                args += ["--audio-source", config.audio_source]

        # Window
        if config.fullscreen:
            args.append("--fullscreen")
        if self._caps.SUPPORTS_ALWAYS_ON_TOP and config.always_on_top:
            args.append("--always-on-top")
        if self._caps.SUPPORTS_BORDERLESS and config.borderless:
            args.append("--window-borderless")
        if config.window_title.strip():
            args += ["--window-title", config.window_title.strip()]

        # Behavior
        if self._caps.SUPPORTS_STAY_AWAKE and config.stay_awake:
            args.append("--stay-awake")
        if self._caps.SUPPORTS_TURN_SCREEN_OFF and config.turn_screen_off:
            args.append("--turn-screen-off")
        if self._caps.SUPPORTS_SHOW_TOUCHES and config.show_touches:
            args.append("--show-touches")

        # Custom args (last)
        if config.custom_args.strip():
            valid, err = validate_custom_args(config.custom_args)
            if valid:
                args += parse_custom_args(config.custom_args)
            else:
                logger.warning("Custom args rejected: %s", err)

        logger.debug("Built command: %s", args)
        return args

    def preview_string(self, config: ScrcpyConfig, serial: str) -> str:
        return _args_to_display(self.build(config, serial))


# ---------------------------------------------------------------------------
# CameraCommandBuilder
# ---------------------------------------------------------------------------

class CameraCommandBuilder:
    """
    Builds the scrcpy camera command.

    Reference:
        scrcpy --video-source=camera --camera-facing=back --camera-size=1920x1080 --no-audio
    """

    def __init__(self, scrcpy_path=None) -> None:
        self._scrcpy_exe = scrcpy_path or paths.scrcpy_exe
        self._caps = ScrcpyCapabilities()

    def build(self, config: CameraConfig, serial: str) -> list[str]:
        """
        Build the camera mode argument list.

        Args:
            config: Camera configuration.
            serial: Target device serial.

        Returns:
            Argument list starting with scrcpy.exe path.
        """
        args: list[str] = [str(self._scrcpy_exe)]

        args += ["--serial", serial]

        # Camera source (mandatory for camera mode)
        args.append("--video-source=camera")

        # Camera facing
        if config.facing in self._caps.CAMERA_FACING_OPTIONS:
            args.append(f"--camera-facing={config.facing}")

        # Camera size
        if config.size.strip() and config.size != "auto":
            args.append(f"--camera-size={config.size}")

        # Camera FPS
        if config.fps > 0:
            args.append(f"--camera-fps={config.fps}")

        # Video codec
        if config.video_codec in self._caps.SUPPORTED_VIDEO_CODECS:
            args += ["--video-codec", config.video_codec]

        # Bitrate
        if config.bitrate:
            args += ["--video-bit-rate", config.bitrate]

        # Audio
        if config.no_audio:
            args.append("--no-audio")

        # Window
        if config.fullscreen:
            args.append("--fullscreen")
        if config.always_on_top:
            args.append("--always-on-top")

        # Custom args
        if config.custom_args.strip():
            valid, err = validate_custom_args(config.custom_args)
            if valid:
                args += parse_custom_args(config.custom_args)
            else:
                logger.warning("Camera custom args rejected: %s", err)

        logger.debug("Camera command: %s", args)
        return args

    def preview_string(self, config: CameraConfig, serial: str) -> str:
        return _args_to_display(self.build(config, serial))


# ---------------------------------------------------------------------------
# OTGConfig dataclass
# ---------------------------------------------------------------------------

@dataclass
class OTGConfig:
    """
    Configuration for scrcpy OTG / physical input passthrough mode.

    Modes:
      - 'no_display': Streamless ADB HID control (--no-video --no-audio --keyboard=uhid --mouse=uhid).
                      Recommended: Works seamlessly with USB debugging enabled.
      - 'otg': Raw USB HID simulation (--otg). Bypasses ADB (requires WinUSB driver).
    """

    mode: str = "no_display"       # "no_display" (recommended) or "otg"
    disable_keyboard: bool = False # --no-keyboard
    disable_mouse: bool = False    # --no-mouse
    stay_awake: bool = True        # --stay-awake
    turn_screen_off: bool = False  # --turn-screen-off
    custom_args: str = ""

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "disable_keyboard": self.disable_keyboard,
            "disable_mouse": self.disable_mouse,
            "stay_awake": self.stay_awake,
            "turn_screen_off": self.turn_screen_off,
            "custom_args": self.custom_args,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OTGConfig":
        return cls(
            mode=str(data.get("mode", "no_display")),
            disable_keyboard=bool(data.get("disable_keyboard", False)),
            disable_mouse=bool(data.get("disable_mouse", False)),
            stay_awake=bool(data.get("stay_awake", True)),
            turn_screen_off=bool(data.get("turn_screen_off", False)),
            custom_args=str(data.get("custom_args", "")),
        )


# ---------------------------------------------------------------------------
# OTGCommandBuilder
# ---------------------------------------------------------------------------

class OTGCommandBuilder:
    """Builds the scrcpy OTG / input passthrough command."""

    def __init__(self, scrcpy_path=None) -> None:
        self._scrcpy_exe = scrcpy_path or paths.scrcpy_exe

    def build(self, config: OTGConfig, serial: str) -> list[str]:
        """
        Build the OTG argument list.

        Args:
            config: OTG configuration.
            serial: Target device serial.

        Returns:
            Argument list starting with scrcpy.exe path.
        """
        args: list[str] = [str(self._scrcpy_exe)]

        if serial:
            args += ["--serial", serial]

        if config.mode == "otg":
            args.append("--otg")
            if config.disable_keyboard:
                args.append("--no-keyboard")
            if config.disable_mouse:
                args.append("--no-mouse")
        else:
            # no_display mode (Streamless ADB HID Passthrough)
            args.append("--no-video")
            args.append("--no-audio")

            if config.disable_keyboard:
                args.append("--no-keyboard")
            else:
                args.append("--keyboard=uhid")

            if config.disable_mouse:
                args.append("--no-mouse")
            else:
                args.append("--mouse=uhid")

        if config.stay_awake:
            args.append("--stay-awake")
        if config.turn_screen_off:
            args.append("--turn-screen-off")

        if config.custom_args.strip():
            valid, err = validate_custom_args(config.custom_args)
            if valid:
                args += parse_custom_args(config.custom_args)
            else:
                logger.warning("OTG custom args rejected: %s", err)

        logger.debug("OTG command: %s", args)
        return args

    def preview_string(self, config: OTGConfig, serial: str) -> str:
        return _args_to_display(self.build(config, serial))

