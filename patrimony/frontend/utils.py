"""Shared utility functions for the frontend layer."""

import os
from pathlib import Path


def get_settings_path() -> Path:
    """Get the settings file path (same directory as the database)."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    else:
        base = Path.home() / ".local" / "share"
    settings_dir = base / "patrimony" / "settings"
    settings_dir.mkdir(parents=True, exist_ok=True)
    return settings_dir / "settings.json"


# Radix color palette for pie/donut chart slices
_RADIX_COLORS = [
    "blue",
    "orange",
    "green",
    "purple",
    "red",
    "cyan",
    "yellow",
    "pink",
    "teal",
    "indigo",
    "lime",
    "amber",
    "plum",
    "mint",
    "sky",
]


def get_pie_color(index: int, shade: int = 9) -> str:
    """Return a CSS var color for pie chart slice at the given index."""
    color = _RADIX_COLORS[index % len(_RADIX_COLORS)]
    return f"var(--{color}-{shade})"
