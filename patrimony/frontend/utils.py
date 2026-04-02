"""Shared utility functions for the frontend layer."""

import os
from pathlib import Path

import reflex as rx


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


def tauri_open_url(url: str) -> rx.event.EventSpec:
    """Open a URL in the system browser, using Tauri opener if available."""
    return rx.call_script(
        f"""
        if (window.__TAURI__) {{
            window.__TAURI__.opener.openUrl("{url}");
        }} else {{
            window.open("{url}", "_blank");
        }}
        """
    )


def tauri_save_file(data: str, filename: str) -> rx.event.EventSpec:
    """Save data to a file using Tauri native dialog, with browser fallback."""
    return rx.call_script(
        f"""
        (function() {{
            if (window.__TAURI__) {{
                window.__TAURI__.core.invoke("save_file", {{
                    contents: `{data}`,
                    filename: "{filename}"
                }});
            }} else {{
                const blob = new Blob([`{data}`], {{type: "text/csv"}});
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = "{filename}";
                a.click();
                URL.revokeObjectURL(url);
            }}
        }})()
        """
    )


def export_csv(
    rows: list[dict],
    columns: list[str],
    filename: str,
) -> rx.event.EventSpec:
    """Build a CSV string from rows/columns and trigger a file save.

    Args:
        rows: List of dicts (or dataclass-like objects with __dataclass_fields__).
        columns: Ordered list of column names.
        filename: Suggested filename for the download.
    """
    header = ",".join(columns)
    body = "\n".join(
        ",".join(
            str(row.get(col, "") if isinstance(row, dict) else getattr(row, col, ""))
            for col in columns
        )
        for row in rows
    )
    return tauri_save_file(f"{header}\n{body}", filename)
