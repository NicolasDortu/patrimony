"""Configuration store for file connector source paths."""

import json

from ..utils import get_settings_path


class FileConnectorPathStore:
    """Persists source file paths for file connector history entries as JSON."""

    _CONFIG_NAME = "file_connector_paths.json"

    def __init__(self) -> None:
        self._path = get_settings_path().parent / self._CONFIG_NAME

    def get(self, entry_id: int) -> str:
        """Get the stored source path for a connector history entry."""
        return self._load().get(str(entry_id), "")

    def set(self, entry_id: int, path: str) -> None:
        """Set/update the stored source path for a connector history entry."""
        data = self._load()
        data[str(entry_id)] = path
        self._save(data)

    def remove(self, entry_id: int) -> None:
        """Remove the stored source path for a connector history entry."""
        data = self._load()
        data.pop(str(entry_id), None)
        self._save(data)

    def _load(self) -> dict:
        if self._path.is_file():
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save(self, data: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2), encoding="utf-8")


file_connector_paths = FileConnectorPathStore()
