"""Persist named source/target project pairs under %APPDATA%\\ProjectDiff."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class Project:
    id: str
    name: str
    path_a: str
    path_b: str
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "path_a": self.path_a,
            "path_b": self.path_b,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def projects_path() -> Path:
    """``%APPDATA%\\ProjectDiff\\projects.json`` on Windows."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is not set; cannot locate projects file")
    return Path(appdata) / "ProjectDiff" / "projects.json"


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _to_posix(path: str) -> str:
    return Path(path).resolve().as_posix()


def load_projects(path: Path | None = None) -> list[Project]:
    """Load projects from disk. Missing or invalid files yield an empty list."""
    target = path if path is not None else projects_path()
    if not target.is_file():
        return []

    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(raw, dict):
        return []

    items = raw.get("projects")
    if not isinstance(items, list):
        return []

    projects: list[Project] = []
    for item in items:
        project = _parse_project(item)
        if project is not None:
            projects.append(project)
    return projects


def save_projects(projects: list[Project], path: Path | None = None) -> None:
    """Write the full project list as JSON, creating the parent directory if needed."""
    target = path if path is not None else projects_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "projects": [p.to_dict() for p in projects],
    }
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    target.write_text(text, encoding="utf-8")


def list_projects(path: Path | None = None) -> list[Project]:
    """Return projects sorted newest-first by ``updated_at``."""
    projects = load_projects(path)
    return sorted(projects, key=lambda p: p.updated_at, reverse=True)


def get_project(project_id: str, path: Path | None = None) -> Project | None:
    for project in load_projects(path):
        if project.id == project_id:
            return project
    return None


def create_project(
    *,
    name: str,
    path_a: str,
    path_b: str,
    path: Path | None = None,
) -> Project:
    """Append a new project and persist. Does not validate git repos."""
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError("Project name must not be empty")

    now = _now_iso()
    project = Project(
        id=str(uuid.uuid4()),
        name=cleaned_name,
        path_a=_to_posix(path_a),
        path_b=_to_posix(path_b),
        created_at=now,
        updated_at=now,
    )
    projects = load_projects(path)
    projects.append(project)
    save_projects(projects, path=path)
    return project


def update_project(
    project_id: str,
    *,
    name: str | None = None,
    path_a: str | None = None,
    path_b: str | None = None,
    path: Path | None = None,
) -> Project:
    """Update fields on an existing project. Raises ``KeyError`` if missing."""
    projects = load_projects(path)
    index = next((i for i, p in enumerate(projects) if p.id == project_id), None)
    if index is None:
        raise KeyError(project_id)

    current = projects[index]
    new_name = current.name if name is None else name.strip()
    if not new_name:
        raise ValueError("Project name must not be empty")

    updated = Project(
        id=current.id,
        name=new_name,
        path_a=current.path_a if path_a is None else _to_posix(path_a),
        path_b=current.path_b if path_b is None else _to_posix(path_b),
        created_at=current.created_at,
        updated_at=_now_iso(),
    )
    projects[index] = updated
    save_projects(projects, path=path)
    return updated


def delete_project(project_id: str, path: Path | None = None) -> bool:
    """Remove a project by id. Returns True if something was deleted."""
    projects = load_projects(path)
    remaining = [p for p in projects if p.id != project_id]
    if len(remaining) == len(projects):
        return False
    save_projects(remaining, path=path)
    return True


def _parse_project(value: Any) -> Project | None:
    if not isinstance(value, dict):
        return None
    project_id = value.get("id")
    name = value.get("name")
    path_a = value.get("path_a")
    path_b = value.get("path_b")
    created_at = value.get("created_at")
    updated_at = value.get("updated_at")
    if not all(
        isinstance(x, str) and x.strip()
        for x in (project_id, name, path_a, path_b, created_at, updated_at)
    ):
        return None
    return Project(
        id=project_id.strip(),
        name=name.strip(),
        path_a=path_a.replace("\\", "/").strip(),
        path_b=path_b.replace("\\", "/").strip(),
        created_at=created_at.strip(),
        updated_at=updated_at.strip(),
    )
