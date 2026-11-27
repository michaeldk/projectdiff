"""Unified diff parsing into a typed model."""

from __future__ import annotations

import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from project_diff import git
from project_diff.files import FileEntry, FilePairing, FileSide

_HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")


class LineKind(StrEnum):
    ADD = "add"
    DEL = "del"
    CTX = "ctx"


@dataclass(frozen=True)
class Line:
    id: str
    kind: LineKind
    old_no: int | None
    new_no: int | None
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "old_no": self.old_no,
            "new_no": self.new_no,
            "text": self.text,
        }


@dataclass(frozen=True)
class Hunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    section: str
    lines: tuple[Line, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "old_start": self.old_start,
            "old_count": self.old_count,
            "new_start": self.new_start,
            "new_count": self.new_count,
            "section": self.section,
            "lines": [line.to_dict() for line in self.lines],
        }


@dataclass(frozen=True)
class FileDiff:
    path: str
    side: FileSide
    binary: bool
    hunks: tuple[Hunk, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "side": self.side.value,
            "binary": self.binary,
            "hunks": [hunk.to_dict() for hunk in self.hunks],
        }


@dataclass(frozen=True)
class DiffResult:
    diff_id: str
    files: tuple[FileDiff, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "diff_id": self.diff_id,
            "files": [file.to_dict() for file in self.files],
        }


def make_line_id(file_idx: int, hunk_idx: int, line_idx: int) -> str:
    """Deterministic line id scoped to a DiffResult (and its diff_id)."""
    return f"{file_idx}:{hunk_idx}:{line_idx}"


def compute_diff(
    repo_a: Path,
    repo_b: Path,
    pairing: FilePairing,
    *,
    diff_id: str | None = None,
) -> DiffResult:
    """Build a typed DiffResult for all differing / only-A / only-B / binary files."""
    token = diff_id if diff_id is not None else uuid.uuid4().hex
    files: list[FileDiff] = []

    for entry in pairing.all_entries():
        file_diff = _diff_entry(repo_a, repo_b, entry, file_idx=len(files))
        if file_diff is not None:
            files.append(file_diff)

    return DiffResult(diff_id=token, files=tuple(files))


def parse_unified_diff(
    text: str,
    *,
    path: str,
    side: FileSide = FileSide.BOTH,
    file_idx: int = 0,
    binary: bool = False,
) -> FileDiff | None:
    """Parse a unified diff into a FileDiff.

    Headers in *text* are ignored for the path; *path* is used instead (relative,
    forward slashes). Returns ``None`` when there are no hunks.
    """
    if binary:
        return FileDiff(path=path, side=side, binary=True, hunks=())

    hunks = _parse_hunks(text, file_idx=file_idx)
    if not hunks:
        return None
    return FileDiff(path=path, side=side, binary=False, hunks=tuple(hunks))


def synthesize_added(
    path: str,
    lines: Sequence[str],
    *,
    file_idx: int = 0,
    binary: bool = False,
) -> FileDiff:
    """Synthesize an all-added FileDiff for a file that exists only in A."""
    if binary:
        return FileDiff(path=path, side=FileSide.ONLY_A, binary=True, hunks=())
    return FileDiff(
        path=path,
        side=FileSide.ONLY_A,
        binary=False,
        hunks=_single_hunk(
            file_idx=file_idx,
            old_start=0,
            old_count=0,
            new_start=1 if lines else 0,
            kinds=[LineKind.ADD] * len(lines),
            texts=list(lines),
            old_nos=[None] * len(lines),
            new_nos=list(range(1, len(lines) + 1)),
        ),
    )


def synthesize_removed(
    path: str,
    lines: Sequence[str],
    *,
    file_idx: int = 0,
    binary: bool = False,
) -> FileDiff:
    """Synthesize an all-removed FileDiff for a file that exists only in B."""
    if binary:
        return FileDiff(path=path, side=FileSide.ONLY_B, binary=True, hunks=())
    return FileDiff(
        path=path,
        side=FileSide.ONLY_B,
        binary=False,
        hunks=_single_hunk(
            file_idx=file_idx,
            old_start=1 if lines else 0,
            old_count=len(lines),
            new_start=0,
            kinds=[LineKind.DEL] * len(lines),
            texts=list(lines),
            old_nos=list(range(1, len(lines) + 1)),
            new_nos=[None] * len(lines),
        ),
    )


def read_text_lines(path: Path) -> list[str]:
    """Read *path* as UTF-8 text lines with CR/LF stripped (view-oriented)."""
    raw = path.read_bytes()
    if not raw:
        return []
    text = raw.decode("utf-8", errors="replace")
    return text.splitlines()


def _diff_entry(
    repo_a: Path,
    repo_b: Path,
    entry: FileEntry,
    *,
    file_idx: int,
) -> FileDiff | None:
    if entry.side is FileSide.ONLY_A:
        if entry.binary:
            return synthesize_added(entry.path, (), file_idx=file_idx, binary=True)
        lines = read_text_lines(repo_a / entry.path)
        return synthesize_added(entry.path, lines, file_idx=file_idx)

    if entry.side is FileSide.ONLY_B:
        if entry.binary:
            return synthesize_removed(entry.path, (), file_idx=file_idx, binary=True)
        lines = read_text_lines(repo_b / entry.path)
        return synthesize_removed(entry.path, lines, file_idx=file_idx)

    # both
    if entry.binary:
        if (repo_a / entry.path).read_bytes() == (repo_b / entry.path).read_bytes():
            return None
        return FileDiff(path=entry.path, side=FileSide.BOTH, binary=True, hunks=())

    raw = git.diff_no_index(repo_b / entry.path, repo_a / entry.path, cwd=repo_b)
    if not raw.strip():
        return None
    return parse_unified_diff(
        raw,
        path=entry.path,
        side=FileSide.BOTH,
        file_idx=file_idx,
    )


def _single_hunk(
    *,
    file_idx: int,
    old_start: int,
    old_count: int,
    new_start: int,
    kinds: list[LineKind],
    texts: list[str],
    old_nos: list[int | None],
    new_nos: list[int | None],
) -> tuple[Hunk, ...]:
    if not kinds and old_count == 0 and len(texts) == 0:
        # Empty file: one empty hunk so the file still appears as a change.
        return (
            Hunk(
                old_start=old_start,
                old_count=old_count,
                new_start=new_start,
                new_count=0,
                section="",
                lines=(),
            ),
        )

    lines = tuple(
        Line(
            id=make_line_id(file_idx, 0, i),
            kind=kind,
            old_no=old_no,
            new_no=new_no,
            text=text,
        )
        for i, (kind, text, old_no, new_no) in enumerate(
            zip(kinds, texts, old_nos, new_nos, strict=True)
        )
    )
    new_count = sum(1 for k in kinds if k in (LineKind.ADD, LineKind.CTX))
    return (
        Hunk(
            old_start=old_start,
            old_count=old_count,
            new_start=new_start,
            new_count=new_count,
            section="",
            lines=lines,
        ),
    )


def _parse_hunks(text: str, *, file_idx: int) -> list[Hunk]:
    hunks: list[Hunk] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        match = _HUNK_HEADER_RE.match(lines[i])
        if match is None:
            i += 1
            continue

        old_start = int(match.group(1))
        old_count = int(match.group(2)) if match.group(2) is not None else 1
        new_start = int(match.group(3))
        new_count = int(match.group(4)) if match.group(4) is not None else 1
        section = match.group(5).strip()
        i += 1

        hunk_lines: list[Line] = []
        old_no = old_start
        new_no = new_start
        line_idx = 0

        while i < len(lines):
            raw = lines[i]
            if raw.startswith("@@"):
                break
            if raw.startswith("diff --git"):
                break
            if raw.startswith("\\"):
                # "\ No newline at end of file" — skip for the view model.
                i += 1
                continue
            if not raw:
                # Empty line without prefix can appear; treat as unexpected and stop.
                break

            prefix = raw[0]
            body = raw[1:]
            if prefix == "+":
                kind = LineKind.ADD
                line_old: int | None = None
                line_new: int | None = new_no
                new_no += 1
            elif prefix == "-":
                kind = LineKind.DEL
                line_old = old_no
                line_new = None
                old_no += 1
            elif prefix == " ":
                kind = LineKind.CTX
                line_old = old_no
                line_new = new_no
                old_no += 1
                new_no += 1
            else:
                # File headers (---, +++, index, …) after a hunk shouldn't happen;
                # stop this hunk cleanly.
                break

            hunk_lines.append(
                Line(
                    id=make_line_id(file_idx, len(hunks), line_idx),
                    kind=kind,
                    old_no=line_old,
                    new_no=line_new,
                    text=body,
                )
            )
            line_idx += 1
            i += 1

        hunks.append(
            Hunk(
                old_start=old_start,
                old_count=old_count,
                new_start=new_start,
                new_count=new_count,
                section=section,
                lines=tuple(hunk_lines),
            )
        )

    return hunks
