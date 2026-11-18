"""Git subprocess helpers — the only module that runs git."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Hide the brief console flash when a windowed (no-console) build shells out to git.
_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

# Commands that mutate the working tree. Never allowed against a read-only repo (A).
_WRITE_COMMANDS = frozenset({"apply", "add", "rm", "mv", "commit", "checkout", "reset", "stash"})

_read_only_repos: set[Path] = set()


class GitError(Exception):
    """Raised when git exits with an unexpected status code."""

    def __init__(
        self,
        message: str,
        *,
        returncode: int,
        stdout: str,
        stderr: str,
        args: list[str],
    ) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.args = args


@dataclass(frozen=True)
class GitResult:
    returncode: int
    stdout: str
    stderr: str


def mark_read_only(repo: Path) -> None:
    """Register *repo* as source (A). Write commands against it will raise."""
    _read_only_repos.add(repo.resolve())


def clear_read_only() -> None:
    """Drop all read-only registrations (tests / session reset)."""
    _read_only_repos.clear()


def is_read_only(repo: Path) -> bool:
    return repo.resolve() in _read_only_repos


def _assert_writable(repo: Path, args: list[str]) -> None:
    if not args:
        return
    if args[0] not in _WRITE_COMMANDS:
        return
    resolved = repo.resolve()
    if resolved in _read_only_repos:
        raise PermissionError(
            f"Refusing to run write command {args[0]!r} in read-only repository: {resolved}"
        )


def run_git(
    repo: Path,
    args: list[str],
    *,
    ok_codes: tuple[int, ...] = (0,),
    input_data: bytes | str | None = None,
) -> GitResult:
    """Run ``git -c core.quotepath=false <args>`` with ``cwd=repo``.

    Arguments are always a list (never ``shell=True``). stdout/stderr are decoded as UTF-8.
    """
    _assert_writable(repo, args)

    cmd = ["git", "-c", "core.quotepath=false", *args]
    if isinstance(input_data, str):
        stdin_bytes: bytes | None = input_data.encode("utf-8")
    else:
        stdin_bytes = input_data

    creationflags = _CREATE_NO_WINDOW if sys.platform == "win32" else 0
    completed = subprocess.run(
        cmd,
        cwd=repo,
        input=stdin_bytes,
        capture_output=True,
        shell=False,
        check=False,
        creationflags=creationflags,
    )
    stdout = completed.stdout.decode("utf-8", errors="replace")
    stderr = completed.stderr.decode("utf-8", errors="replace")
    if completed.returncode not in ok_codes:
        cmd_name = args[0] if args else ""
        detail = stderr.strip() or stdout.strip()
        raise GitError(
            f"git {cmd_name} failed with exit {completed.returncode}: {detail}",
            returncode=completed.returncode,
            stdout=stdout,
            stderr=stderr,
            args=args,
        )
    return GitResult(returncode=completed.returncode, stdout=stdout, stderr=stderr)


def is_repo(path: Path) -> bool:
    """True when *path* is the root of a git working tree."""
    if not path.is_dir():
        return False
    try:
        result = run_git(path, ["rev-parse", "--show-toplevel"])
    except (GitError, OSError):
        return False
    toplevel = Path(result.stdout.strip())
    try:
        return toplevel.resolve() == path.resolve()
    except OSError:
        return False


def ls_files(repo: Path) -> list[str]:
    """Tracked and untracked-but-not-ignored files, relative paths with ``/``."""
    result = run_git(repo, ["ls-files", "-z", "--cached", "--others", "--exclude-standard"])
    if not result.stdout:
        return []
    paths = result.stdout.split("\0")
    return [_to_posix(p) for p in paths if p]


def status_porcelain(repo: Path) -> str:
    """Raw ``git status --porcelain`` output (empty means clean)."""
    return run_git(repo, ["status", "--porcelain"]).stdout


def diff_no_index(path_b: Path, path_a: Path, *, cwd: Path | None = None) -> str:
    """Unified diff that turns *path_b* into *path_a*.

    Exit code 1 (differences found) is success; identical files return ``\"\"``.
    """
    workdir = cwd if cwd is not None else path_b.parent
    result = run_git(
        workdir,
        [
            "diff",
            "--no-index",
            "--ignore-cr-at-eol",
            "--",
            str(path_b),
            str(path_a),
        ],
        ok_codes=(0, 1),
    )
    return result.stdout


def apply_check(repo: Path, patch: bytes | str) -> None:
    """Run ``git apply --check``. Raises :class:`GitError` if the patch does not apply."""
    run_git(repo, ["apply", "--check", "--whitespace=nowarn", "-"], input_data=patch)


def apply(repo: Path, patch: bytes | str) -> None:
    """Apply *patch* to the working tree only (no ``--index``)."""
    run_git(repo, ["apply", "--whitespace=nowarn", "-"], input_data=patch)


def _to_posix(path: str) -> str:
    return path.replace("\\", "/")
