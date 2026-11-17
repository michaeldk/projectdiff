"""Tests for the js_api bridge."""

from __future__ import annotations

from pathlib import Path

import pytest

from project_diff.api import create_api
from project_diff.diff import LineKind
from project_diff.git import is_read_only
from tests.helpers import commit_all, init_repo, write_file


def _settings(tmp_path: Path) -> Path:
    return tmp_path / "ProjectDiff" / "settings.json"


def _api(tmp_path: Path, *, folder: Path | None = None):
    picker = (lambda: str(folder)) if folder is not None else (lambda: None)
    return create_api(settings_path=_settings(tmp_path), folder_picker=picker)


def _change_ids(diff_payload: dict, path: str) -> list[str]:
    for file in diff_payload["files"]:
        if file["path"] != path:
            continue
        ids: list[str] = []
        for hunk in file["hunks"]:
            for line in hunk["lines"]:
                if line["kind"] in (LineKind.ADD.value, LineKind.DEL.value):
                    ids.append(line["id"])
        return ids
    raise AssertionError(f"no file {path}")


def test_ping_returns_pong(tmp_path: Path) -> None:
    api = _api(tmp_path)
    assert api.ping() == {"ok": True, "data": "pong"}


def test_pick_folder_cancelled(tmp_path: Path) -> None:
    api = _api(tmp_path)
    assert api.pick_folder("a") == {"ok": True, "data": None}


def test_pick_folder_rejects_non_repo(tmp_path: Path) -> None:
    not_repo = tmp_path / "plain"
    not_repo.mkdir()
    api = _api(tmp_path, folder=not_repo)
    result = api.pick_folder("a")
    assert result["ok"] is False
    assert result["error"]["code"] == "NOT_A_REPO"


def test_pick_folder_accepts_repo(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    write_file(repo, "f.txt", "x\n")
    commit_all(repo)

    api = _api(tmp_path, folder=repo)
    result = api.pick_folder("b")
    assert result["ok"] is True
    assert result["data"]["side"] == "b"
    assert Path(result["data"]["path"]).resolve() == repo.resolve()


def test_pick_folder_invalid_side(tmp_path: Path) -> None:
    api = _api(tmp_path)
    result = api.pick_folder("c")
    assert result["ok"] is False
    assert result["error"]["code"] == "INTERNAL"


def test_get_and_save_settings(tmp_path: Path) -> None:
    api = _api(tmp_path)

    defaults = api.get_settings()
    assert defaults["ok"] is True
    assert defaults["data"]["theme"] == "system"
    assert "node_modules/" in defaults["data"]["excludes"]

    saved = api.save_settings({"excludes": ["dist/", "build/"], "theme": "dark"})
    assert saved["ok"] is True
    assert saved["data"] == {"excludes": ["dist/", "build/"], "theme": "dark"}

    loaded = api.get_settings()
    assert loaded["data"] == saved["data"]


def test_save_settings_rejects_bad_theme(tmp_path: Path) -> None:
    api = _api(tmp_path)
    result = api.save_settings({"theme": "neon"})
    assert result["ok"] is False
    assert result["error"]["code"] == "INTERNAL"


def test_compute_diff_returns_file_list_and_diff(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    write_file(repo_a, "shared.txt", "from-a\n")
    write_file(repo_b, "shared.txt", "from-b\n")
    write_file(repo_a, "only_a.txt", "a\n")
    write_file(repo_b, "only_b.txt", "b\n")
    commit_all(repo_a)
    commit_all(repo_b)

    api = _api(tmp_path)
    result = api.compute_diff(str(repo_a), str(repo_b))
    assert result["ok"] is True
    data = result["data"]
    assert "diff" in data and "file_list" in data
    assert data["diff"]["diff_id"]
    paths = {e["path"] for e in data["file_list"]}
    assert paths == {"shared.txt", "only_a.txt", "only_b.txt"}
    assert is_read_only(repo_a)


def test_compute_diff_not_a_repo(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "a")
    write_file(repo, "f.txt", "x\n")
    commit_all(repo)
    plain = tmp_path / "plain"
    plain.mkdir()

    api = _api(tmp_path)
    bad_a = api.compute_diff(str(plain), str(repo))
    assert bad_a["ok"] is False
    assert bad_a["error"]["code"] == "NOT_A_REPO"

    bad_b = api.compute_diff(str(repo), str(plain))
    assert bad_b["ok"] is False
    assert bad_b["error"]["code"] == "NOT_A_REPO"


def test_compute_diff_honors_excludes(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    write_file(repo_a, "keep.txt", "a\n")
    write_file(repo_b, "keep.txt", "b\n")
    write_file(repo_a, "dist/out.js", "a\n")
    write_file(repo_b, "dist/out.js", "b\n")
    commit_all(repo_a)
    commit_all(repo_b)

    api = _api(tmp_path)
    api.save_settings({"excludes": ["dist/"], "theme": "system"})
    result = api.compute_diff(str(repo_a), str(repo_b))
    paths = {e["path"] for e in result["data"]["file_list"]}
    assert "keep.txt" in paths
    assert "dist/out.js" not in paths


def test_apply_selection_through_api(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    write_file(repo_a, "f.txt", "hello\n")
    write_file(repo_b, "f.txt", "world\n")
    commit_all(repo_a)
    commit_all(repo_b)

    api = _api(tmp_path)
    computed = api.compute_diff(str(repo_a), str(repo_b))
    assert computed["ok"] is True
    diff_id = computed["data"]["diff"]["diff_id"]
    line_ids = _change_ids(computed["data"]["diff"], "f.txt")

    applied = api.apply(diff_id, line_ids)
    assert applied["ok"] is True
    assert applied["data"]["files"] == ["f.txt"]
    assert (repo_b / "f.txt").read_text(encoding="utf-8") == "hello\n"


def test_apply_stale_diff(tmp_path: Path) -> None:
    api = _api(tmp_path)
    result = api.apply("missing-id", ["0:0:0"])
    assert result["ok"] is False
    assert result["error"]["code"] == "STALE_DIFF"


def test_apply_stale_after_recompute(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    write_file(repo_a, "f.txt", "a\n")
    write_file(repo_b, "f.txt", "b\n")
    commit_all(repo_a)
    commit_all(repo_b)

    api = _api(tmp_path)
    first = api.compute_diff(str(repo_a), str(repo_b))
    old_id = first["data"]["diff"]["diff_id"]
    second = api.compute_diff(str(repo_a), str(repo_b))
    assert second["data"]["diff"]["diff_id"] != old_id

    stale = api.apply(old_id, _change_ids(first["data"]["diff"], "f.txt"))
    assert stale["ok"] is False
    assert stale["error"]["code"] == "STALE_DIFF"


def test_apply_refuses_dirty_target(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    write_file(repo_a, "f.txt", "a\n")
    write_file(repo_b, "f.txt", "b\n")
    commit_all(repo_a)
    commit_all(repo_b)

    api = _api(tmp_path)
    computed = api.compute_diff(str(repo_a), str(repo_b))
    diff_id = computed["data"]["diff"]["diff_id"]
    line_ids = _change_ids(computed["data"]["diff"], "f.txt")

    write_file(repo_b, "f.txt", "dirty\n")
    result = api.apply(diff_id, line_ids)
    assert result["ok"] is False
    assert result["error"]["code"] == "TARGET_DIRTY"


def test_apply_check_failed(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    write_file(repo_a, "f.txt", "line1\nline2\n")
    write_file(repo_b, "f.txt", "line1\nold\n")
    commit_all(repo_a)
    commit_all(repo_b)

    api = _api(tmp_path)
    computed = api.compute_diff(str(repo_a), str(repo_b))
    diff_id = computed["data"]["diff"]["diff_id"]
    line_ids = _change_ids(computed["data"]["diff"], "f.txt")

    # Change B after the diff so --check fails, but keep status clean via amend-like rewrite:
    # status is dirty if we just edit. Commit the conflicting content instead.
    write_file(repo_b, "f.txt", "changed\ncontext\n")
    commit_all(repo_b, "change after diff")

    result = api.apply(diff_id, line_ids)
    assert result["ok"] is False
    assert result["error"]["code"] == "APPLY_CHECK_FAILED"
    assert result["error"]["message"]


def test_wrap_never_raises(tmp_path: Path) -> None:
    def boom() -> Path:
        raise RuntimeError("kaboom")

    api = create_api(settings_path=_settings(tmp_path), folder_picker=boom)  # type: ignore[arg-type]
    result = api.pick_folder("a")
    assert result["ok"] is False
    assert result["error"]["code"] == "INTERNAL"
    assert "kaboom" in result["error"]["message"]


@pytest.mark.parametrize("side", ["a", "b"])
def test_pick_folder_sides(tmp_path: Path, side: str) -> None:
    repo = init_repo(tmp_path / "repo")
    write_file(repo, "f.txt", "x\n")
    commit_all(repo)
    api = _api(tmp_path, folder=repo)
    result = api.pick_folder(side)
    assert result["ok"] is True
    assert result["data"]["side"] == side
