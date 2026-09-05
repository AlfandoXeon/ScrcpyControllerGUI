"""
DisplayPanel — tab for video/display configuration.
"""

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QVBoxLayout,
    QWidget,
)

from app.models.config import ScrcpyConfig
from app.services.command_builder import ScrcpyCapabilities


class DisplayPanel(QWidget):
    """
    Configuration controls for video: resolution, FPS, bitrate, codec.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._caps = ScrcpyCapabilities()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        group = QGroupBox("Video")
        form = QFormLayout(group)
        form.setSpacing(8)

        # Resolution
        self._resolution_combo = QComboBox()
        res_options = [
            ("Original (no limit)", 0),
            ("480p", 480),
            ("720p", 720),
            ("1080p", 1080),
            ("1440p", 1440),
            ("1920 (Full HD)", 1920),
        ]
        for label, value in res_options:
            self._resolution_combo.addItem(label, userData=value)
        self._resolution_combo.setCurrentIndex(3)  # default 1080p
        form.addRow("Resolution:", self._resolution_combo)

        # Framerate
        self._fps_combo = QComboBox()
        for fps in self._caps.FPS_OPTIONS:
            self._fps_combo.addItem(f"{fps} FPS", userData=fps)
        self._fps_combo.setCurrentIndex(self._caps.FPS_OPTIONS.index(60))
        form.addRow("Framerate:", self._fps_combo)

        # Bitrate
        self._bitrate_combo = QComboBox()
        for br in self._caps.BITRATE_OPTIONS:
            self._bitrate_combo.addItem(br, userData=br)
        default_br_idx = self._caps.BITRATE_OPTIONS.index("8M") if "8M" in self._caps.BITRATE_OPTIONS else 0
        self._bitrate_combo.setCurrentIndex(default_br_idx)
        form.addRow("Bitrate:", self._bitrate_combo)

        # Video codec
        if self._caps.SUPPORTS_VIDEO_CODEC:
            self._codec_combo = QComboBox()
            for codec in self._caps.SUPPORTED_VIDEO_CODECS:
                self._codec_combo.addItem(codec, userData=codec)
            form.addRow("Video Codec:", self._codec_combo)
        else:
            self._codec_combo = None

        layout.addWidget(group)
        layout.addStretch()

    # -------------------------------------------------------------------------
    # Config I/O
    # -------------------------------------------------------------------------

    def get_config_values(self, config: ScrcpyConfig) -> None:
        """Write panel values into a ScrcpyConfig (in-place)."""
        config.max_size = self._resolution_combo.currentData()
        config.max_fps = self._fps_combo.currentData()
        config.bitrate = self._bitrate_combo.currentData()
        if self._codec_combo is not None:
            config.video_codec = self._codec_combo.currentData()

    def apply_config(self, config: ScrcpyConfig) -> None:
        """Load a ScrcpyConfig into the panel controls."""
        self._set_combo_by_data(self._resolution_combo, config.max_size)
        self._set_combo_by_data(self._fps_combo, config.max_fps)
        self._set_combo_by_data(self._bitrate_combo, config.bitrate)
        if self._codec_combo is not None:
            self._set_combo_by_data(self._codec_combo, config.video_codec)

    @staticmethod
    def _set_combo_by_data(combo: QComboBox, value) -> None:
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return
