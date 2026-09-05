"""
CameraPanel — tab for scrcpy camera mode configuration.

Uses --video-source=camera and related camera flags.
Reference: scrcpy --video-source=camera --camera-facing=back --camera-size=1920x1080 --no-audio
"""

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.services.command_builder import CameraConfig, ScrcpyCapabilities
from app.utils.validators import validate_custom_args


class CameraPanel(QWidget):
    """
    Configuration controls for scrcpy camera mode.

    Signals:
        show_command_requested(): User clicked Show Command Preview.
    """

    show_command_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._caps = ScrcpyCapabilities()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        # ── Info label ─────────────────────────────────────────────────────────
        info_label = QLabel(
            "Camera mode streams your device camera directly.\n"
            "Requires Android 12+ with camera support."
        )
        info_label.setStyleSheet(
            "color: #aaaaaa; font-size: 8pt; padding: 6px 8px; "
            "background: #252525; border: 1px solid #333; border-radius: 3px;"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # ── Camera settings group ──────────────────────────────────────────────
        cam_group = QGroupBox("Camera")
        cam_form = QFormLayout(cam_group)
        cam_form.setSpacing(8)
        cam_form.setContentsMargins(10, 14, 10, 10)
        cam_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Facing
        self._facing_combo = QComboBox()
        facing_labels = {"back": "Back (Rear)", "front": "Front (Selfie)", "external": "External"}
        for key in self._caps.CAMERA_FACING_OPTIONS:
            self._facing_combo.addItem(facing_labels.get(key, key), userData=key)
        cam_form.addRow("Facing:", self._facing_combo)

        # Resolution / size
        self._size_combo = QComboBox()
        size_labels = {
            "auto": "Auto (device decides)",
            "640x480": "480p  (640×480)",
            "1280x720": "720p  (1280×720)",
            "1920x1080": "1080p (1920×1080)",
            "2560x1440": "1440p (2560×1440)",
            "3840x2160": "4K    (3840×2160)",
        }
        for key in self._caps.CAMERA_SIZE_OPTIONS:
            self._size_combo.addItem(size_labels.get(key, key), userData=key)
        # Default: 1920x1080
        self._size_combo.setCurrentIndex(
            self._caps.CAMERA_SIZE_OPTIONS.index("1920x1080")
            if "1920x1080" in self._caps.CAMERA_SIZE_OPTIONS else 0
        )
        cam_form.addRow("Resolution:", self._size_combo)

        # FPS
        self._fps_combo = QComboBox()
        for fps in self._caps.CAMERA_FPS_OPTIONS:
            self._fps_combo.addItem(f"{fps} FPS", userData=fps)
        # Default 60
        if 60 in self._caps.CAMERA_FPS_OPTIONS:
            self._fps_combo.setCurrentIndex(self._caps.CAMERA_FPS_OPTIONS.index(60))
        cam_form.addRow("FPS:", self._fps_combo)

        layout.addWidget(cam_group)

        # ── Video encoding group ───────────────────────────────────────────────
        enc_group = QGroupBox("Video Encoding")
        enc_form = QFormLayout(enc_group)
        enc_form.setSpacing(8)
        enc_form.setContentsMargins(10, 14, 10, 10)
        enc_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._codec_combo = QComboBox()
        for codec in self._caps.SUPPORTED_VIDEO_CODECS:
            self._codec_combo.addItem(codec.upper(), userData=codec)
        enc_form.addRow("Codec:", self._codec_combo)

        self._bitrate_combo = QComboBox()
        for br in self._caps.BITRATE_OPTIONS:
            self._bitrate_combo.addItem(br, userData=br)
        default_br_idx = self._caps.BITRATE_OPTIONS.index("8M") if "8M" in self._caps.BITRATE_OPTIONS else 0
        self._bitrate_combo.setCurrentIndex(default_br_idx)
        enc_form.addRow("Bitrate:", self._bitrate_combo)

        layout.addWidget(enc_group)

        # ── Options group ──────────────────────────────────────────────────────
        opt_group = QGroupBox("Options")
        opt_form = QFormLayout(opt_group)
        opt_form.setSpacing(6)
        opt_form.setContentsMargins(10, 14, 10, 10)

        self._no_audio_check = QCheckBox("No Audio (recommended for camera)")
        self._no_audio_check.setChecked(True)
        opt_form.addRow(self._no_audio_check)

        self._fullscreen_check = QCheckBox("Fullscreen")
        opt_form.addRow(self._fullscreen_check)

        self._ontop_check = QCheckBox("Always on Top")
        opt_form.addRow(self._ontop_check)

        layout.addWidget(opt_group)

        # ── Custom args ────────────────────────────────────────────────────────
        extra_group = QGroupBox("Extra Arguments")
        extra_layout = QVBoxLayout(extra_group)
        extra_layout.setSpacing(6)
        extra_layout.setContentsMargins(10, 14, 10, 10)

        self._custom_args_edit = QPlainTextEdit()
        self._custom_args_edit.setPlaceholderText("e.g. --window-title MyCam")
        self._custom_args_edit.setMaximumHeight(60)
        self._custom_args_edit.textChanged.connect(self._validate_custom_args)
        extra_layout.addWidget(self._custom_args_edit)

        self._args_error_label = QLabel("")
        self._args_error_label.setStyleSheet("color: #e05050;")
        self._args_error_label.setVisible(False)
        extra_layout.addWidget(self._args_error_label)

        preview_btn = QPushButton("Show Command Preview")
        preview_btn.clicked.connect(self.show_command_requested)
        extra_layout.addWidget(preview_btn)

        layout.addWidget(extra_group)
        layout.addStretch()

    # ── Validation ──────────────────────────────────────────────────────────────

    def _validate_custom_args(self) -> None:
        raw = self._custom_args_edit.toPlainText()
        if not raw.strip():
            self._args_error_label.setVisible(False)
            return
        valid, err = validate_custom_args(raw)
        self._args_error_label.setText("" if valid else err)
        self._args_error_label.setVisible(not valid)

    def custom_args_valid(self) -> bool:
        raw = self._custom_args_edit.toPlainText()
        if not raw.strip():
            return True
        valid, _ = validate_custom_args(raw)
        return valid

    # ── Config I/O ──────────────────────────────────────────────────────────────

    def get_config(self) -> CameraConfig:
        """Read all controls and return a CameraConfig."""
        return CameraConfig(
            facing=self._facing_combo.currentData() or "back",
            size=self._size_combo.currentData() or "1920x1080",
            fps=self._fps_combo.currentData() or 60,
            no_audio=self._no_audio_check.isChecked(),
            video_codec=self._codec_combo.currentData() or "h264",
            bitrate=self._bitrate_combo.currentData() or "8M",
            fullscreen=self._fullscreen_check.isChecked(),
            always_on_top=self._ontop_check.isChecked(),
            custom_args=self._custom_args_edit.toPlainText().strip(),
        )

    def apply_config(self, config: CameraConfig) -> None:
        """Load a CameraConfig into all controls."""
        _set_combo_by_data(self._facing_combo, config.facing)
        _set_combo_by_data(self._size_combo, config.size)
        _set_combo_by_data(self._fps_combo, config.fps)
        self._no_audio_check.setChecked(config.no_audio)
        _set_combo_by_data(self._codec_combo, config.video_codec)
        _set_combo_by_data(self._bitrate_combo, config.bitrate)
        self._fullscreen_check.setChecked(config.fullscreen)
        self._ontop_check.setChecked(config.always_on_top)
        self._custom_args_edit.setPlainText(config.custom_args)


def _set_combo_by_data(combo: QComboBox, value) -> None:
    for i in range(combo.count()):
        if combo.itemData(i) == value:
            combo.setCurrentIndex(i)
            return
