"""
PresetService — manages user presets stored in JSON.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.models.preset import Preset, BUILTIN_PRESETS
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PresetService:
    """
    Manages the collection of presets (built-in + user-defined).

    Presets are persisted at <user_data>/config/presets.json.
    Built-in presets are always present and cannot be deleted.
    """

    def __init__(self, presets_file: Path) -> None:
        self._path = presets_file
        self._user_presets: list[Preset] = []
        self.load()

    # -------------------------------------------------------------------------
    # Load / Save
    # -------------------------------------------------------------------------

    def load(self) -> None:
        """Load user presets from disk."""
        if not self._path.exists():
            logger.info("Presets file not found — starting with empty user presets.")
            self._user_presets = []
            return

        try:
            raw = self._path.read_text(encoding="utf-8")
            parsed = json.loads(raw)
            if not isinstance(parsed, list):
                raise ValueError("Presets file root is not a JSON array.")
            self._user_presets = [Preset.from_dict(p) for p in parsed]
            logger.info("Loaded %d user preset(s) from %s", len(self._user_presets), self._path)
        except Exception as exc:
            logger.error("Failed to load presets: %s — resetting.", exc)
            self._backup_corrupt()
            self._user_presets = []

    def save(self) -> None:
        """Persist user presets to disk (built-ins are NOT saved)."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            data = [p.to_dict() for p in self._user_presets]
            self._path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug("Presets saved to %s", self._path)
        except Exception as exc:
            logger.error("Failed to save presets: %s", exc)

    def _backup_corrupt(self) -> None:
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup = self._path.with_suffix(f".corrupt_{ts}.json")
            shutil.move(str(self._path), str(backup))
            logger.warning("Corrupt presets backed up to %s", backup)
        except Exception as exc:
            logger.error("Could not back up corrupt presets: %s", exc)

    # -------------------------------------------------------------------------
    # Access
    # -------------------------------------------------------------------------

    @property
    def all_presets(self) -> list[Preset]:
        """All presets: built-ins first, then user presets."""
        return list(BUILTIN_PRESETS) + list(self._user_presets)

    def get_preset_names(self) -> list[str]:
        """Return list of all preset names."""
        return [p.name for p in self.all_presets]

    def get_preset(self, name: str) -> Optional[Preset]:
        """Find a preset by name (case-sensitive)."""
        for p in self.all_presets:
            if p.name == name:
                return p
        return None

    # -------------------------------------------------------------------------
    # Mutations (user presets only)
    # -------------------------------------------------------------------------

    def save_preset(self, preset: Preset) -> None:
        """
        Save or overwrite a user preset by name.
        Cannot overwrite built-in presets.
        """
        if any(p.name == preset.name for p in BUILTIN_PRESETS):
            logger.warning("Cannot overwrite built-in preset '%s'.", preset.name)
            return

        # Overwrite existing user preset with same name
        for i, p in enumerate(self._user_presets):
            if p.name == preset.name:
                self._user_presets[i] = preset
                self.save()
                return

        self._user_presets.append(preset)
        self.save()
        logger.info("Saved preset '%s'.", preset.name)

    def delete_preset(self, name: str) -> bool:
        """
        Delete a user preset by name.

        Returns:
            True if deleted, False if not found or is a built-in.
        """
        if any(p.name == name for p in BUILTIN_PRESETS):
            logger.warning("Cannot delete built-in preset '%s'.", name)
            return False

        for i, p in enumerate(self._user_presets):
            if p.name == name:
                del self._user_presets[i]
                self.save()
                logger.info("Deleted preset '%s'.", name)
                return True
        return False
