"""Tests for projects.py persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from project_diff.projects import (
    create_project,
    delete_project,
    get_project,
    list_projects,
    load_projects,
    save_projects,
    update_project,
)


def _path(tmp_path: Path) -> Path:
    return tmp_path / "ProjectDiff" / "projects.json"


def test_missing_file_yields_empty_list(tmp_path: Path) -> None:
    assert load_projects(_path(tmp_path)) == []
    assert list_projects(_path(tmp_path)) == []


def test_corrupt_file_yields_empty_list(tmp_path: Path) -> None:
    path = _path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    assert load_projects(path) == []


def test_create_list_update_delete_roundtrip(tmp_path: Path) -> None:
    path = _path(tmp_path)

    created = create_project(
        name=" Sync ",
        path_a=str(tmp_path / "a"),
        path_b=str(tmp_path / "b"),
        path=path,
    )
    assert created.name == "Sync"
    assert created.path_a.replace("\\", "/").endswith("/a")
    assert "\\" not in created.path_a
    assert created.id
    assert created.created_at == created.updated_at

    listed = list_projects(path)
    assert len(listed) == 1
    assert listed[0].id == created.id

    # Ensure paths are stored with forward slashes.
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert "\\" not in raw["projects"][0]["path_a"]
    assert "\\" not in raw["projects"][0]["path_b"]

    updated = update_project(
        created.id,
        name="Renamed",
        path_a=str(tmp_path / "a2"),
        path=path,
    )
    assert updated.name == "Renamed"
    assert updated.path_a.replace("\\", "/").endswith("/a2")
    assert updated.updated_at >= updated.created_at

    fetched = get_project(created.id, path=path)
    assert fetched is not None
    assert fetched.name == "Renamed"

    assert delete_project(created.id, path=path) is True
    assert list_projects(path) == []
    assert delete_project(created.id, path=path) is False


def test_list_projects_newest_first(tmp_path: Path) -> None:
    from project_diff.projects import Project

    path = _path(tmp_path)
    save_projects(
        [
            Project(
                id="1",
                name="Older",
                path_a="C:/a1",
                path_b="C:/b1",
                created_at="2024-01-01T00:00:00+00:00",
                updated_at="2024-01-01T00:00:00+00:00",
            ),
            Project(
                id="2",
                name="Newer",
                path_a="C:/a2",
                path_b="C:/b2",
                created_at="2024-01-02T00:00:00+00:00",
                updated_at="2024-01-02T00:00:00+00:00",
            ),
        ],
        path=path,
    )

    listed = list_projects(path)
    assert [p.name for p in listed] == ["Newer", "Older"]


def test_update_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        update_project("missing", name="x", path=_path(tmp_path))


def test_create_rejects_empty_name(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        create_project(
            name="   ",
            path_a=str(tmp_path / "a"),
            path_b=str(tmp_path / "b"),
            path=_path(tmp_path),
        )


def test_save_and_load_skips_invalid_entries(tmp_path: Path) -> None:
    path = _path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "projects": [
                    {
                        "id": "ok",
                        "name": "Good",
                        "path_a": "C:/a",
                        "path_b": "C:/b",
                        "created_at": "2024-01-01T00:00:00+00:00",
                        "updated_at": "2024-01-01T00:00:00+00:00",
                    },
                    {"id": "bad"},
                    "nope",
                ]
            }
        ),
        encoding="utf-8",
    )
    loaded = load_projects(path)
    assert len(loaded) == 1
    assert loaded[0].id == "ok"

    # Round-trip through save keeps the valid one.
    save_projects(loaded, path=path)
    assert len(load_projects(path)) == 1
