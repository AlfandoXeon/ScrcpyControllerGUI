"""
AudioPanel — tab for audio configuration.
"""

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.models.config import ScrcpyConfig
from app.services.command_builder import ScrcpyCapabilities


class AudioPanel(QWidget):
    """
    Configuration controls for audio: enable/disable, audio source.
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

        group = QGroupBox("Audio")
        form = QFormLayout(group)
        form.setSpacing(8)

        # Enable/disable audio
        self._audio_check = QCheckBox("Enable audio")
        self._audio_check.setChecked(True)
        self._audio_check.toggled.connect(self._on_audio_toggled)
        form.addRow(self._audio_check)

        # Audio source
        if self._caps.SUPPORTS_AUDIO_SOURCE:
            self._source_combo = QComboBox()
            source_labels = {
                "output": "Device Output (speakers)",
                "mic": "Microphone",
                "playback": "App Playback",
            }
            for key in self._caps.SUPPORTED_AUDIO_SOURCES:
                self._source_combo.addItem(source_labels.get(key, key), userData=key)

            self._source_label = QLabel("Audio Source:")
            form.addRow(self._source_label, self._source_combo)
        else:
            self._source_combo = None
            self._source_label = None

        layout.addWidget(group)
        layout.addStretch()

    def _on_audio_toggled(self, enabled: bool) -> None:
        if self._source_combo:
            self._source_combo.setEnabled(enabled)
        if self._source_label:
            self._source_label.setEnabled(enabled)

    # -------------------------------------------------------------------------
    # Config I/O
    # -------------------------------------------------------------------------

    def get_config_values(self, config: ScrcpyConfig) -> None:
        config.audio_enabled = self._audio_check.isChecked()
        if self._source_combo is not None and config.audio_enabled:
            config.audio_source = self._source_combo.currentData()

    def apply_config(self, config: ScrcpyConfig) -> None:
        self._audio_check.setChecked(config.audio_enabled)
        if self._source_combo is not None:
            for i in range(self._source_combo.count()):
                if self._source_combo.itemData(i) == config.audio_source:
                    self._source_combo.setCurrentIndex(i)
                    break
        self._on_audio_toggled(config.audio_enabled)
