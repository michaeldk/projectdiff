"""Resolve frontend URLs for source runs and PyInstaller bundles."""

from __future__ import annotations

import sys
from pathlib import Path

FRONTEND_DIST_REL = Path("frontend") / "dist" / "index.html"
VITE_DEV_URL = "http://localhost:5173"


def is_packaged() -> bool:
    return bool(getattr(sys, "frozen", False))


def repo_root() -> Path:
    """Repository root when running from source (``backend/src/project_diff`` → root)."""
    return Path(__file__).resolve().parents[3]


def bundle_root() -> Path:
    if is_packaged():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
    return repo_root()


def bundled_frontend_index() -> Path:
    return bundle_root() / FRONTEND_DIST_REL


def resolve_frontend_url(*, dev: bool) -> str:
    if dev:
        return VITE_DEV_URL
    index = bundled_frontend_index()
    if not index.is_file():
        raise FileNotFoundError(
            f"Frontend build missing: {index}. Run `npm run build` in frontend/ first."
        )
    return index.resolve().as_uri()
