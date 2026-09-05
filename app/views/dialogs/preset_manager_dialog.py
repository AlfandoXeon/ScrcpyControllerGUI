"""
PresetManagerDialog — view and manage user presets.
"""

from typing import Optional

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.services.preset_service import PresetService
from app.models.preset import Preset
from app.models.config import ScrcpyConfig


class PresetManagerDialog(QDialog):
    """
    Allows the user to save, overwrite, and delete presets.

    Signals:
        preset_selected(name): User double-clicked or applied a preset.
    """

    preset_selected = pyqtSignal(str)

    def __init__(
        self,
        preset_service: PresetService,
        current_config: ScrcpyConfig,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._service = preset_service
        self._current_config = current_config
        self.setWindowTitle("Preset Manager")
        self.setMinimumWidth(380)
        self.setMinimumHeight(300)
        self.setModal(True)
        self._build_ui()
        self._refresh_list()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        layout.addWidget(QLabel("Presets:"))

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._on_apply)
        layout.addWidget(self._list)

        # Buttons
        btn_layout = QHBoxLayout()

        self._save_btn = QPushButton("Save Current as New")
        self._overwrite_btn = QPushButton("Overwrite Selected")
        self._delete_btn = QPushButton("Delete Selected")
        self._apply_btn = QPushButton("Apply")
        close_btn = QPushButton("Close")

        self._save_btn.clicked.connect(self._on_save_new)
        self._overwrite_btn.clicked.connect(self._on_overwrite)
        self._delete_btn.clicked.connect(self._on_delete)
        self._apply_btn.clicked.connect(self._on_apply)
        close_btn.clicked.connect(self.accept)

        for btn in [self._save_btn, self._overwrite_btn, self._delete_btn, self._apply_btn, close_btn]:
            btn_layout.addWidget(btn)

        layout.addLayout(btn_layout)

    def _refresh_list(self) -> None:
        self._list.clear()
        for preset in self._service.all_presets:
            item = QListWidgetItem(preset.name)
            if preset.is_builtin:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setToolTip("Built-in preset (cannot be deleted)")
            self._list.addItem(item)

    def _selected_name(self) -> Optional[str]:
        item = self._list.currentItem()
        return item.text() if item else None

    def _on_save_new(self) -> None:
        name, ok = QInputDialog.getText(self, "Save Preset", "Preset name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        preset = Preset(name=name, config=self._current_config)
        self._service.save_preset(preset)
        self._refresh_list()

    def _on_overwrite(self) -> None:
        name = self._selected_name()
        if not name:
            return
        existing = self._service.get_preset(name)
        if existing and existing.is_builtin:
            QMessageBox.warning(self, "Cannot Overwrite", "Built-in presets cannot be overwritten.")
            return
        reply = QMessageBox.question(
            self,
            "Overwrite Preset",
            f"Overwrite preset '{name}' with current settings?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            preset = Preset(name=name, config=self._current_config)
            self._service.save_preset(preset)
            self._refresh_list()

    def _on_delete(self) -> None:
        name = self._selected_name()
        if not name:
            return
        existing = self._service.get_preset(name)
        if existing and existing.is_builtin:
            QMessageBox.warning(self, "Cannot Delete", "Built-in presets cannot be deleted.")
            return
        reply = QMessageBox.question(
            self,
            "Delete Preset",
            f"Delete preset '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._service.delete_preset(name)
            self._refresh_list()

    def _on_apply(self) -> None:
        name = self._selected_name()
        if name:
            self.preset_selected.emit(name)
            self.accept()
