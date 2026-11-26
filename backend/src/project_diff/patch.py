"""Build patches from selected lines and apply them to target (B)."""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from pathlib import Path

from project_diff import git
from project_diff.diff import DiffResult, FileDiff, Hunk, Line, LineKind
from project_diff.files import FileSide


class ApplyCheckFailedError(Exception):
    """Raised when ``git apply --check`` rejects the patch."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.code = "APPLY_CHECK_FAILED"


@dataclass(frozen=True)
class ApplyResult:
    """Paths (forward slashes) successfully written into B's working tree."""

    files: tuple[str, ...]


@dataclass(frozen=True)
class _RawFile:
    bodies: tuple[bytes, ...]
    eol: bytes
    ends_with_newline: bool


@dataclass(frozen=True)
class _OutLine:
    kind: LineKind  # ADD / DEL / CTX after selection filtering
    body: bytes
    old_no: int | None = None


def build_patch(
    diff: DiffResult,
    selected_ids: Collection[str],
    *,
    repo_a: Path,
    repo_b: Path,
) -> bytes:
    """Build a unified diff patch for the selected line IDs.

    Unselected adds are dropped, unselected deletes become context, and hunk
    headers are recomputed. Hunks (and files) with no selected changes are omitted.
    """
    selected = set(selected_ids)
    chunks: list[bytes] = []

    for file_diff in diff.files:
        if file_diff.binary:
            continue
        file_patch = _build_file_patch(file_diff, selected, repo_a=repo_a, repo_b=repo_b)
        if file_patch:
            chunks.append(file_patch)

    if not chunks:
        return b""
    return b"".join(chunks)


def apply_selection(
    diff: DiffResult,
    selected_ids: Collection[str],
    *,
    repo_a: Path,
    repo_b: Path,
) -> ApplyResult:
    """``git apply --check``, then ``git apply`` the selection into B's working tree."""
    patch = build_patch(diff, selected_ids, repo_a=repo_a, repo_b=repo_b)
    if not patch:
        return ApplyResult(files=())

    try:
        git.apply_check(repo_b, patch)
    except git.GitError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        raise ApplyCheckFailedError(detail) from exc

    git.apply(repo_b, patch)
    return ApplyResult(files=_applied_paths(diff, selected_ids))


def detect_eol(data: bytes) -> bytes:
    """Dominant end-of-line sequence in *data* (defaults to ``\\n``)."""
    if b"\r\n" in data:
        return b"\r\n"
    if b"\n" in data:
        return b"\n"
    if b"\r" in data:
        return b"\r"
    return b"\n"


def read_raw_file(path: Path) -> _RawFile:
    """Read *path* as bytes, split into EOL-stripped bodies, and detect EOL style."""
    if not path.is_file():
        return _RawFile(bodies=(), eol=b"\n", ends_with_newline=True)

    data = path.read_bytes()
    if not data:
        return _RawFile(bodies=(), eol=b"\n", ends_with_newline=True)

    eol = detect_eol(data)
    if eol not in data:
        return _RawFile(bodies=(data,), eol=eol, ends_with_newline=False)

    ends_with_newline = data.endswith(eol)
    if ends_with_newline:
        trimmed = data[: -len(eol)]
        bodies = [b""] if trimmed == b"" else trimmed.split(eol)
    else:
        bodies = data.split(eol)

    return _RawFile(bodies=tuple(bodies), eol=eol, ends_with_newline=ends_with_newline)


def _applied_paths(diff: DiffResult, selected_ids: Collection[str]) -> tuple[str, ...]:
    selected = set(selected_ids)
    return tuple(
        file_diff.path
        for file_diff in diff.files
        if not file_diff.binary and _file_has_selected_change(file_diff, selected)
    )


def _file_has_selected_change(file_diff: FileDiff, selected: set[str]) -> bool:
    return any(
        line.kind in (LineKind.ADD, LineKind.DEL) and line.id in selected
        for hunk in file_diff.hunks
        for line in hunk.lines
    )


def _build_file_patch(
    file_diff: FileDiff,
    selected: set[str],
    *,
    repo_a: Path,
    repo_b: Path,
) -> bytes:
    if file_diff.side is FileSide.ONLY_A:
        return _build_only_a_patch(file_diff, selected, repo_a=repo_a)

    if file_diff.side is FileSide.ONLY_B:
        return _build_only_b_patch(file_diff, selected, repo_b=repo_b)

    return _build_both_patch(file_diff, selected, repo_b=repo_b)


def _build_only_a_patch(
    file_diff: FileDiff,
    selected: set[str],
    *,
    repo_a: Path,
) -> bytes:
    """New-file patch: only selected add lines, using A's EOL."""
    selected_lines = [
        line
        for hunk in file_diff.hunks
        for line in hunk.lines
        if line.kind is LineKind.ADD and line.id in selected
    ]
    if not selected_lines:
        return b""

    raw_a = read_raw_file(repo_a / file_diff.path)
    eol = raw_a.eol
    path = file_diff.path
    out_lines = [_OutLine(LineKind.ADD, line.text.encode("utf-8")) for line in selected_lines]
    # Preserve "no newline at EOF" only when every line of A was selected.
    all_adds = [
        line for hunk in file_diff.hunks for line in hunk.lines if line.kind is LineKind.ADD
    ]
    ends_with_newline = raw_a.ends_with_newline or len(selected_lines) < len(all_adds)

    hunk_body = _format_hunk(
        old_start=0,
        old_count=0,
        new_start=1,
        out_lines=out_lines,
        eol=eol,
        ends_with_newline=ends_with_newline,
        old_line_total=0,
    )
    header = (
        f"diff --git a/{path} b/{path}\nnew file mode 100644\n--- /dev/null\n+++ b/{path}\n"
    ).encode()
    return header + hunk_body


def _build_only_b_patch(
    file_diff: FileDiff,
    selected: set[str],
    *,
    repo_b: Path,
) -> bytes:
    """Delete or partial-removal patch for a file that exists only in B."""
    selectable = _selectable_lines(file_diff)
    if not selectable:
        return b""

    selected_dels = [line for line in selectable if line.id in selected]
    if not selected_dels:
        return b""

    raw_b = read_raw_file(repo_b / file_diff.path)
    path = file_diff.path

    if len(selected_dels) == len(selectable):
        out_lines = [_OutLine(LineKind.DEL, _line_body(line), line.old_no) for line in selectable]
        hunk_body = _format_hunk(
            old_start=1 if out_lines else 0,
            old_count=len(out_lines),
            new_start=0,
            out_lines=out_lines,
            eol=raw_b.eol,
            ends_with_newline=raw_b.ends_with_newline,
            old_line_total=len(raw_b.bodies),
        )
        header = (
            f"diff --git a/{path} b/{path}\ndeleted file mode 100644\n--- a/{path}\n+++ /dev/null\n"
        ).encode()
        return header + hunk_body

    # Partial removal: selected dels removed, unselected dels become context.
    out_lines = [
        _OutLine(
            LineKind.DEL if line.id in selected else LineKind.CTX,
            _line_body(line),
            line.old_no,
        )
        for line in selectable
    ]

    old_count = len(out_lines)
    new_count = sum(1 for ol in out_lines if ol.kind in (LineKind.CTX, LineKind.ADD))
    hunk_body = _format_hunk(
        old_start=1,
        old_count=old_count,
        new_start=1 if new_count else 0,
        out_lines=out_lines,
        eol=raw_b.eol,
        ends_with_newline=raw_b.ends_with_newline,
        old_line_total=len(raw_b.bodies),
    )
    header = (f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n").encode()
    return header + hunk_body


def _build_both_patch(
    file_diff: FileDiff,
    selected: set[str],
    *,
    repo_b: Path,
) -> bytes:
    if not _file_has_selected_change(file_diff, selected):
        return b""

    raw_b = read_raw_file(repo_b / file_diff.path)
    eol = raw_b.eol
    path = file_diff.path

    hunk_blobs: list[bytes] = []
    cumulative_delta = 0

    for hunk in file_diff.hunks:
        out_lines = _filter_hunk_lines(hunk, selected)
        if not any(ol.kind in (LineKind.ADD, LineKind.DEL) for ol in out_lines):
            continue

        old_count = sum(1 for ol in out_lines if ol.kind in (LineKind.CTX, LineKind.DEL))
        new_count = sum(1 for ol in out_lines if ol.kind in (LineKind.CTX, LineKind.ADD))

        if old_count == 0:
            old_start = 0
        else:
            old_start = hunk.old_start

        if new_count == 0:
            new_start = 0
        elif old_count == 0:
            new_start = 1 + cumulative_delta
        else:
            new_start = old_start + cumulative_delta

        hunk_blobs.append(
            _format_hunk(
                old_start=old_start,
                old_count=old_count,
                new_start=new_start,
                out_lines=out_lines,
                eol=eol,
                ends_with_newline=raw_b.ends_with_newline,
                old_line_total=len(raw_b.bodies),
            )
        )
        cumulative_delta += new_count - old_count

    if not hunk_blobs:
        return b""

    header = (f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n").encode()
    return header + b"".join(hunk_blobs)


def _filter_hunk_lines(hunk: Hunk, selected: set[str]) -> list[_OutLine]:
    out: list[_OutLine] = []
    for line in hunk.lines:
        if line.kind is LineKind.CTX:
            out.append(_OutLine(LineKind.CTX, _line_body(line), line.old_no))
        elif line.kind is LineKind.ADD:
            if line.id in selected:
                out.append(_OutLine(LineKind.ADD, _line_body(line)))
        elif line.kind is LineKind.DEL:
            body = _line_body(line)
            if line.id in selected:
                out.append(_OutLine(LineKind.DEL, body, line.old_no))
            else:
                out.append(_OutLine(LineKind.CTX, body, line.old_no))
    return out


def _selectable_lines(file_diff: FileDiff) -> list[Line]:
    return [
        line
        for hunk in file_diff.hunks
        for line in hunk.lines
        if line.kind in (LineKind.ADD, LineKind.DEL)
    ]


def _line_body(line: Line) -> bytes:
    """UTF-8 body from the cached diff (CR-at-EOL already stripped)."""
    return line.text.encode("utf-8")


def _format_hunk(
    *,
    old_start: int,
    old_count: int,
    new_start: int,
    out_lines: Sequence[_OutLine],
    eol: bytes,
    ends_with_newline: bool,
    old_line_total: int,
) -> bytes:
    new_count = sum(1 for ol in out_lines if ol.kind in (LineKind.CTX, LineKind.ADD))
    header = (
        f"@@ -{_count_spec(old_start, old_count)} +{_count_spec(new_start, new_count)} @@\n"
    ).encode()

    parts: list[bytes] = [header]
    for i, ol in enumerate(out_lines):
        prefix = {LineKind.ADD: b"+", LineKind.DEL: b"-", LineKind.CTX: b" "}[ol.kind]
        is_last = i == len(out_lines) - 1
        needs_no_newline = False
        if not ends_with_newline and is_last:
            if ol.kind in (LineKind.DEL, LineKind.CTX):
                needs_no_newline = ol.old_no == old_line_total
            elif ol.kind is LineKind.ADD and old_count == 0:
                needs_no_newline = True

        if needs_no_newline:
            parts.append(prefix + ol.body)
            parts.append(b"\n\\ No newline at end of file\n")
        else:
            parts.append(prefix + ol.body + eol)

    return b"".join(parts)


def _count_spec(start: int, count: int) -> str:
    if count == 1:
        return str(start)
    return f"{start},{count}"
