"""Tests for settings.py persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_diff.settings import (
    DEFAULT_EXCLUDES,
    Settings,
    default_settings,
    load_settings,
    save_settings,
    settings_path,
)


def test_default_settings_include_common_excludes() -> None:
    settings = default_settings()
    assert settings.theme == "system"
    assert "node_modules/" in settings.excludes
    assert ".venv/" in settings.excludes
    assert "dist/" in settings.excludes
    assert "*.pyc" in settings.excludes
    assert settings.excludes == DEFAULT_EXCLUDES


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "ProjectDiff" / "settings.json"
    original = Settings(excludes=["dist/", "build/"], theme="dark")
    save_settings(original, path=path)

    loaded = load_settings(path)
    assert loaded.theme == "dark"
    assert loaded.excludes == ["dist/", "build/"]
    assert path.is_file()
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw == {"excludes": ["dist/", "build/"], "theme": "dark"}


def test_load_missing_file_returns_defaults(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    loaded = load_settings(missing)
    assert loaded.theme == "system"
    assert loaded.excludes == DEFAULT_EXCLUDES


def test_load_invalid_json_returns_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{not-json", encoding="utf-8")
    loaded = load_settings(path)
    assert loaded.theme == default_settings().theme
    assert loaded.excludes == DEFAULT_EXCLUDES


def test_load_invalid_fields_fall_back(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text('{"excludes": "nope", "theme": "neon"}', encoding="utf-8")
    loaded = load_settings(path)
    assert loaded.excludes == DEFAULT_EXCLUDES
    assert loaded.theme == "system"


def test_settings_path_uses_appdata(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert settings_path() == tmp_path / "ProjectDiff" / "settings.json"
