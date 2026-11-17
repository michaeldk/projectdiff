"""Frontend URL resolution for source and packaged runs."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from project_diff import paths
from project_diff.paths import VITE_DEV_URL, bundled_frontend_index, resolve_frontend_url


def test_dev_frontend_url_is_vite() -> None:
    assert resolve_frontend_url(dev=True) == VITE_DEV_URL


def test_source_frontend_resolves_file_uri(tmp_path: Path) -> None:
    index = tmp_path / "frontend" / "dist" / "index.html"
    index.parent.mkdir(parents=True)
    index.write_text("<html></html>", encoding="utf-8")

    with mock.patch.object(paths, "bundle_root", return_value=tmp_path):
        url = resolve_frontend_url(dev=False)
        assert url.startswith("file://")
        assert url.endswith("index.html")


def test_missing_frontend_raises(tmp_path: Path) -> None:
    with (
        mock.patch.object(paths, "bundle_root", return_value=tmp_path),
        pytest.raises(FileNotFoundError, match="Frontend build missing"),
    ):
        resolve_frontend_url(dev=False)


def test_bundled_index_path_under_repo_root_when_not_frozen() -> None:
    with mock.patch.object(paths, "is_packaged", return_value=False):
        path = bundled_frontend_index()
        assert path.name == "index.html"
        assert path.parent.name == "dist"
        assert path.parent.parent.name == "frontend"
