"""Verify locale files are complete and consistent.

Run before every build to catch missing translations.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from patrimony.frontend.languages import (
    AVAILABLE_LANGUAGES,
    LOCALE_DIR,
    load_translations,
)


REFERENCE_LANG = "en"


def _load_raw(lang: str) -> dict[str, str]:
    """Load a locale file directly (bypassing the fallback in load_translations)."""
    path: Path = LOCALE_DIR / f"{lang}.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def reference_keys() -> set[str]:
    return set(_load_raw(REFERENCE_LANG).keys())


def test_every_advertised_language_has_a_locale_file():
    for lang in AVAILABLE_LANGUAGES:
        path = LOCALE_DIR / f"{lang}.json"
        assert path.exists(), f"Missing locale file: {path}"


def test_locale_files_are_valid_json():
    for lang in AVAILABLE_LANGUAGES:
        # Will raise json.JSONDecodeError if invalid.
        _load_raw(lang)


@pytest.mark.parametrize(
    "lang", [lang for lang in AVAILABLE_LANGUAGES if lang != REFERENCE_LANG]
)
def test_locale_has_no_missing_keys(lang: str, reference_keys: set[str]):
    """Every key present in en.json must exist in the other locales."""
    keys = set(_load_raw(lang).keys())
    missing = reference_keys - keys
    assert (
        not missing
    ), f"Locale '{lang}' is missing {len(missing)} keys: {sorted(missing)}"


@pytest.mark.parametrize(
    "lang", [lang for lang in AVAILABLE_LANGUAGES if lang != REFERENCE_LANG]
)
def test_locale_has_no_extra_keys(lang: str, reference_keys: set[str]):
    """Other locales must not define keys that are absent from en.json."""
    keys = set(_load_raw(lang).keys())
    extra = keys - reference_keys
    assert not extra, f"Locale '{lang}' has {len(extra)} stale keys: {sorted(extra)}"


@pytest.mark.parametrize("lang", list(AVAILABLE_LANGUAGES))
def test_locale_values_are_non_empty_strings(lang: str):
    for key, value in _load_raw(lang).items():
        assert isinstance(value, str), f"{lang}: '{key}' must be a string"
        assert value.strip(), f"{lang}: '{key}' is empty"


def test_unknown_language_falls_back_to_english():
    fallback = load_translations("zz")
    english = load_translations("en")
    assert fallback == english
