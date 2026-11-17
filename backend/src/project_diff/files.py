"""File listing, ignore rules, and A/B pairing."""

from __future__ import annotations

import fnmatch
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from project_diff import git

_BINARY_SAMPLE_SIZE = 8192


class FileSide(StrEnum):
    BOTH = "both"
    ONLY_A = "only_a"
    ONLY_B = "only_b"


@dataclass(frozen=True)
class FileEntry:
    """One relative path after pairing A and B."""

    path: str
    side: FileSide
    binary: bool


@dataclass(frozen=True)
class FilePairing:
    both: list[FileEntry]
    only_a: list[FileEntry]
    only_b: list[FileEntry]

    def all_entries(self) -> list[FileEntry]:
        return [*self.both, *self.only_a, *self.only_b]


def is_excluded(rel_path: str, patterns: Sequence[str]) -> bool:
    """Return True when *rel_path* matches any app-level exclude pattern.

    Patterns use forward slashes. A trailing ``/`` means a directory (matched at
    any depth). Patterns without a slash also match the basename (e.g. ``*.pyc``).
    """
    path = rel_path.replace("\\", "/").lstrip("./")
    if not path:
        return False
    name = path.rsplit("/", 1)[-1]
    parts = path.split("/")

    for raw in patterns:
        pattern = raw.replace("\\", "/").strip()
        if not pattern:
            continue

        if pattern.endswith("/"):
            directory = pattern.rstrip("/")
            if not directory:
                continue
            if path == directory or path.startswith(directory + "/"):
                return True
            if f"/{directory}/" in f"/{path}/":
                return True
            continue

        if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(name, pattern):
            return True
        if "/" not in pattern and any(fnmatch.fnmatch(part, pattern) for part in parts):
            return True

    return False


def list_repo_files(repo: Path, excludes: Sequence[str] = ()) -> list[str]:
    """List repo files via git, then drop paths matching *excludes*."""
    return [p for p in git.ls_files(repo) if not is_excluded(p, excludes)]


def is_binary_file(path: Path) -> bool:
    """Detect binary files with the NUL-in-sample heuristic used by git."""
    if not path.is_file():
        return False
    try:
        with path.open("rb") as handle:
            sample = handle.read(_BINARY_SAMPLE_SIZE)
    except OSError:
        return False
    return b"\0" in sample


def pair_files(repo_a: Path, repo_b: Path, excludes: Sequence[str] = ()) -> FilePairing:
    """Pair relative paths from A and B into both / only_a / only_b."""
    files_a = set(list_repo_files(repo_a, excludes))
    files_b = set(list_repo_files(repo_b, excludes))

    both: list[FileEntry] = []
    only_a: list[FileEntry] = []
    only_b: list[FileEntry] = []

    for path in sorted(files_a & files_b):
        binary = is_binary_file(repo_a / path) or is_binary_file(repo_b / path)
        both.append(FileEntry(path=path, side=FileSide.BOTH, binary=binary))

    for path in sorted(files_a - files_b):
        only_a.append(
            FileEntry(
                path=path,
                side=FileSide.ONLY_A,
                binary=is_binary_file(repo_a / path),
            )
        )

    for path in sorted(files_b - files_a):
        only_b.append(
            FileEntry(
                path=path,
                side=FileSide.ONLY_B,
                binary=is_binary_file(repo_b / path),
            )
        )

    return FilePairing(both=both, only_a=only_a, only_b=only_b)
