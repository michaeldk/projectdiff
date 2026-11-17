"""Thin pywebview js_api facade.

Every method returns ``{ok: true, data}`` or ``{ok: false, error: {code, message}}``.
Exceptions never cross the bridge.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import webview

from project_diff import git
from project_diff.diff import DiffResult
from project_diff.diff import compute_diff as build_diff
from project_diff.files import FileEntry, pair_files
from project_diff.patch import ApplyCheckFailedError, TargetDirtyError, apply_selection
from project_diff.settings import Settings, load_settings, save_settings

FolderPicker = Callable[[], str | None]

ERROR_NOT_A_REPO = "NOT_A_REPO"
ERROR_TARGET_DIRTY = "TARGET_DIRTY"
ERROR_APPLY_CHECK_FAILED = "APPLY_CHECK_FAILED"
ERROR_STALE_DIFF = "STALE_DIFF"
ERROR_INTERNAL = "INTERNAL"


@dataclass(frozen=True)
class _CachedDiff:
    diff: DiffResult
    repo_a: Path
    repo_b: Path
    file_list: tuple[FileEntry, ...]


def ok(data: Any = None) -> dict[str, Any]:
    return {"ok": True, "data": data}


def err(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def _file_entry_to_dict(entry: FileEntry) -> dict[str, Any]:
    return {
        "path": entry.path,
        "side": entry.side.value,
        "binary": entry.binary,
    }


def _default_folder_picker() -> str | None:
    """Open the native folder dialog on the first pywebview window."""
    if not webview.windows:
        raise RuntimeError("No webview window is available for the folder dialog")
    result = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
    if not result:
        return None
    return str(result[0])


class ApiError(Exception):
    """Structured bridge error with a stable ``code``."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class Api:
    """Methods exposed to the frontend via ``window.pywebview.api``."""

    def __init__(
        self,
        *,
        settings_path: Path | None = None,
        folder_picker: FolderPicker | None = None,
    ) -> None:
        self._settings_path = settings_path
        self._folder_picker: FolderPicker = (
            folder_picker if folder_picker is not None else _default_folder_picker
        )
        self._cache: dict[str, _CachedDiff] = {}

    def ping(self) -> dict[str, Any]:
        return ok("pong")

    def pick_folder(self, side: str) -> dict[str, Any]:
        if side not in ("a", "b"):
            raise ApiError(ERROR_INTERNAL, f"Invalid side: {side!r}; expected 'a' or 'b'")

        chosen = self._folder_picker()
        if chosen is None:
            return ok(None)

        path = Path(chosen)
        if not git.is_repo(path):
            raise ApiError(
                ERROR_NOT_A_REPO,
                f"Selected folder is not a git repository: {path}",
            )

        return ok({"side": side, "path": _to_posix(path)})

    def get_settings(self) -> dict[str, Any]:
        settings = load_settings(self._settings_path)
        return ok(settings.to_dict())

    def save_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ApiError(ERROR_INTERNAL, "Settings payload must be an object")

        current = load_settings(self._settings_path)
        excludes = payload.get("excludes", current.excludes)
        theme = payload.get("theme", current.theme)

        if not isinstance(excludes, list) or not all(isinstance(x, str) for x in excludes):
            raise ApiError(ERROR_INTERNAL, "excludes must be a list of strings")
        if theme not in ("light", "dark", "system"):
            raise ApiError(ERROR_INTERNAL, f"Invalid theme: {theme!r}")

        cleaned = [x.replace("\\", "/").strip() for x in excludes if x.strip()]
        settings = Settings(excludes=cleaned, theme=theme)
        save_settings(settings, path=self._settings_path)
        return ok(settings.to_dict())

    def compute_diff(self, path_a: str, path_b: str) -> dict[str, Any]:
        repo_a = Path(path_a)
        repo_b = Path(path_b)

        if not git.is_repo(repo_a):
            raise ApiError(ERROR_NOT_A_REPO, f"Source folder is not a git repository: {repo_a}")
        if not git.is_repo(repo_b):
            raise ApiError(ERROR_NOT_A_REPO, f"Target folder is not a git repository: {repo_b}")

        git.mark_read_only(repo_a)

        settings = load_settings(self._settings_path)
        pairing = pair_files(repo_a, repo_b, settings.excludes)
        diff = build_diff(repo_a, repo_b, pairing)

        file_list = tuple(pairing.all_entries())
        self._cache.clear()
        self._cache[diff.diff_id] = _CachedDiff(
            diff=diff,
            repo_a=repo_a.resolve(),
            repo_b=repo_b.resolve(),
            file_list=file_list,
        )

        return ok(
            {
                "file_list": [_file_entry_to_dict(e) for e in file_list],
                "diff": diff.to_dict(),
            }
        )

    def apply(self, diff_id: str, line_ids: list[str]) -> dict[str, Any]:
        if not isinstance(diff_id, str) or not diff_id:
            raise ApiError(ERROR_INTERNAL, "diff_id must be a non-empty string")
        if not isinstance(line_ids, list) or not all(isinstance(x, str) for x in line_ids):
            raise ApiError(ERROR_INTERNAL, "line_ids must be a list of strings")

        cached = self._cache.get(diff_id)
        if cached is None:
            raise ApiError(
                ERROR_STALE_DIFF,
                "Diff is no longer available; compute a fresh diff and try again",
            )

        try:
            result = apply_selection(
                cached.diff,
                line_ids,
                repo_a=cached.repo_a,
                repo_b=cached.repo_b,
            )
        except TargetDirtyError as exc:
            raise ApiError(ERROR_TARGET_DIRTY, str(exc)) from exc
        except ApplyCheckFailedError as exc:
            raise ApiError(ERROR_APPLY_CHECK_FAILED, str(exc)) from exc

        return ok({"files": list(result.files)})


def wrap(fn: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
    """Wrap a js_api method so exceptions become structured errors."""

    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return fn(*args, **kwargs)
        except ApiError as exc:
            return err(exc.code, exc.message)
        except Exception as exc:  # noqa: BLE001 — bridge must never raise
            return err(ERROR_INTERNAL, str(exc))

    return wrapper


def create_api(
    *,
    settings_path: Path | None = None,
    folder_picker: FolderPicker | None = None,
) -> Api:
    api = Api(settings_path=settings_path, folder_picker=folder_picker)
    api.ping = wrap(api.ping)  # type: ignore[method-assign]
    api.pick_folder = wrap(api.pick_folder)  # type: ignore[method-assign]
    api.get_settings = wrap(api.get_settings)  # type: ignore[method-assign]
    api.save_settings = wrap(api.save_settings)  # type: ignore[method-assign]
    api.compute_diff = wrap(api.compute_diff)  # type: ignore[method-assign]
    api.apply = wrap(api.apply)  # type: ignore[method-assign]
    return api


def _to_posix(path: Path) -> str:
    return path.resolve().as_posix()
