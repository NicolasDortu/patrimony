"""Internationalization support using JSON translation files.

Translation catalogs are stored as JSON files under:
    languages/locale/{lang}.json

Each file is a flat ``{"key": "translated string"}`` dictionary.

Supported languages: en, fr, es
"""

import json
from pathlib import Path

LOCALE_DIR = Path(__file__).parent / "locale"

AVAILABLE_LANGUAGES: dict[str, str] = {
    "en": "English",
    "fr": "Français",
    "es": "Español",
}


def load_translations(lang: str) -> dict[str, str]:
    """Load translations for *lang* from a JSON file.

    Falls back to English when the requested language is unavailable.
    """
    if lang not in AVAILABLE_LANGUAGES:
        lang = "en"

    path = LOCALE_DIR / f"{lang}.json"
    if not path.exists():
        path = LOCALE_DIR / "en.json"

    if not path.exists():
        return {}

    return json.loads(path.read_text(encoding="utf-8"))
