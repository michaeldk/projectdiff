"""Helpers for building temporary git repositories in tests."""

from __future__ import annotations

import subprocess
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> None:
    completed = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"{cmd!r} failed ({completed.returncode}): {completed.stderr or completed.stdout}"
        )


def init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    run(["git", "init"], cwd=path)
    run(["git", "config", "user.email", "test@example.com"], cwd=path)
    run(["git", "config", "user.name", "Test"], cwd=path)
    # Avoid CRLF surprises in assertions on Windows.
    run(["git", "config", "core.autocrlf", "false"], cwd=path)
    return path


def write_file(repo: Path, rel: str, content: str | bytes) -> Path:
    target = repo / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        target.write_bytes(content)
    else:
        target.write_text(content, encoding="utf-8", newline="\n")
    return target


def commit_all(repo: Path, message: str = "commit") -> None:
    run(["git", "add", "-A"], cwd=repo)
    run(["git", "commit", "-m", message], cwd=repo)
