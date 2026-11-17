"""Persist exclude list and theme mode under %APPDATA%\\ProjectDiff."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

ThemeMode = Literal["light", "dark", "system"]

DEFAULT_EXCLUDES: list[str] = [
    "node_modules/",
    ".venv/",
    "venv/",
    "dist/",
    "build/",
    "__pycache__/",
    "*.pyc",
    ".pytest_cache/",
    ".ruff_cache/",
    ".mypy_cache/",
    "*.egg-info/",
    ".tox/",
    ".git/",
]

_VALID_THEMES: frozenset[str] = frozenset({"light", "dark", "system"})


@dataclass
class Settings:
    excludes: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDES))
    theme: ThemeMode = "system"

    def to_dict(self) -> dict[str, Any]:
        return {"excludes": list(self.excludes), "theme": self.theme}


def default_settings() -> Settings:
    return Settings()


def settings_path() -> Path:
    """``%APPDATA%\\ProjectDiff\\settings.json`` on Windows."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is not set; cannot locate settings file")
    return Path(appdata) / "ProjectDiff" / "settings.json"


def load_settings(path: Path | None = None) -> Settings:
    """Load settings from disk, falling back to defaults when missing or invalid."""
    target = path if path is not None else settings_path()
    if not target.is_file():
        return default_settings()

    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_settings()

    if not isinstance(raw, dict):
        return default_settings()

    excludes = _parse_excludes(raw.get("excludes"))
    theme = _parse_theme(raw.get("theme"))
    return Settings(excludes=excludes, theme=theme)


def save_settings(settings: Settings, path: Path | None = None) -> None:
    """Write settings as JSON, creating the parent directory if needed."""
    target = path if path is not None else settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(settings.to_dict(), indent=2, ensure_ascii=False) + "\n"
    target.write_text(payload, encoding="utf-8")


def _parse_excludes(value: Any) -> list[str]:
    if not isinstance(value, list):
        return list(DEFAULT_EXCLUDES)
    cleaned: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            cleaned.append(item.replace("\\", "/").strip())
    return cleaned if cleaned else list(DEFAULT_EXCLUDES)


def _parse_theme(value: Any) -> ThemeMode:
    if isinstance(value, str) and value in _VALID_THEMES:
        return value  # type: ignore[return-value]
    return "system"
