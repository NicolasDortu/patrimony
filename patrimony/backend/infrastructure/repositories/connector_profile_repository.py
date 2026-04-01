"""Repository for loading and persisting web connector profiles from YAML files."""

import logging
from pathlib import Path

import yaml

from ...domain.entities import ConnectorProfile, ConnectorStep
from ...domain.repositories import ConnectorProfileRepository

logger = logging.getLogger(__name__)

# Built-in profiles shipped with the app
_BUILTIN_DIR = (
    Path(__file__).resolve().parent.parent / "database" / "data" / "connector_profiles"
)


class ConnectorProfileRepositoryImpl(ConnectorProfileRepository):
    """Loads connector profiles from JSON files on disk."""

    def __init__(self, user_profiles_dir: Path | None = None):
        self._builtin_dir = _BUILTIN_DIR
        self._user_dir = user_profiles_dir

    def list_profiles(self) -> list[ConnectorProfile]:
        """Return all built-in and user profiles."""
        profiles: list[ConnectorProfile] = []
        # Built-in profiles
        profiles.extend(self._load_dir(self._builtin_dir))
        # User profiles (if configured)
        if self._user_dir and self._user_dir.exists():
            profiles.extend(self._load_dir(self._user_dir))
        return profiles

    def get_profile(self, profile_id: str) -> ConnectorProfile | None:
        """Load a specific profile by ID."""
        for profile in self.list_profiles():
            if profile.id == profile_id:
                return profile
        return None

    def save_profile(self, profile: ConnectorProfile) -> None:
        """Save a profile to the user profiles directory."""
        if not self._user_dir:
            raise RuntimeError("User profiles directory not configured.")
        self._user_dir.mkdir(parents=True, exist_ok=True)
        path = self._user_dir / f"{profile.id}.yaml"
        data = _profile_to_dict(profile)
        path.write_text(
            yaml.dump(data, default_flow_style=False, sort_keys=False), encoding="utf-8"
        )

    # --- internal ---

    def _load_dir(self, directory: Path) -> list[ConnectorProfile]:
        """Load all .yaml profiles from a directory."""
        profiles: list[ConnectorProfile] = []
        if not directory.exists():
            return profiles
        for path in sorted(directory.glob("*.yaml")):
            try:
                profiles.append(_load_profile(path))
            except Exception:
                logger.warning("Failed to load profile: %s", path, exc_info=True)
        return profiles


def _load_profile(path: Path) -> ConnectorProfile:
    """Parse a single YAML profile file into a ConnectorProfile."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    steps = [
        ConnectorStep(
            action=s["action"],
            selector=s.get("selector", ""),
            value=s.get("value", ""),
            timeout=s.get("timeout", 30),
        )
        for s in data.get("steps", [])
    ]
    return ConnectorProfile(
        id=data["id"],
        name=data["name"],
        url=data["url"],
        steps=steps,
        column_mapping=data.get("column_mapping", {}),
        import_mode=data.get("import_mode", "positions"),
        delimiter=data.get("delimiter", ","),
        description=data.get("description", ""),
        new_accounts=data.get("new_accounts"),
    )


def _profile_to_dict(profile: ConnectorProfile) -> dict:
    """Serialize a ConnectorProfile to a JSON-serializable dict."""
    return {
        "id": profile.id,
        "name": profile.name,
        "description": profile.description,
        "url": profile.url,
        "import_mode": profile.import_mode,
        "delimiter": profile.delimiter,
        "steps": [
            {
                "action": s.action,
                "selector": s.selector,
                "value": s.value,
                "timeout": s.timeout,
            }
            for s in profile.steps
        ],
        "column_mapping": profile.column_mapping,
        "new_accounts": profile.new_accounts,
    }
