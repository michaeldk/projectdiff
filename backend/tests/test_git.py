"""Tests for git.py subprocess helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from project_diff import git
from tests.helpers import commit_all, init_repo, write_file


def test_is_repo_true_for_work_tree_root(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    assert git.is_repo(repo) is True


def test_is_repo_false_for_plain_folder(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    assert git.is_repo(plain) is False


def test_is_repo_false_for_subdirectory(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    nested = repo / "src"
    nested.mkdir()
    assert git.is_repo(nested) is False


def test_ls_files_honors_gitignore(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    write_file(repo, ".gitignore", "ignored.txt\n")
    write_file(repo, "tracked.txt", "ok\n")
    write_file(repo, "ignored.txt", "nope\n")
    write_file(repo, "untracked.txt", "also ok\n")
    commit_all(repo)

    files = git.ls_files(repo)
    assert "tracked.txt" in files
    assert "untracked.txt" in files
    assert "ignored.txt" not in files
    assert ".gitignore" in files


def test_is_dirty_and_status_porcelain(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    write_file(repo, "a.txt", "a\n")
    commit_all(repo)
    assert git.status_porcelain(repo) == ""
    assert git.is_dirty(repo) is False

    write_file(repo, "a.txt", "changed\n")
    assert git.status_porcelain(repo) != ""
    assert git.is_dirty(repo) is True


def test_diff_no_index_reports_differences(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("hello\n", encoding="utf-8")
    b.write_text("world\n", encoding="utf-8")

    output = git.diff_no_index(b, a, cwd=tmp_path)
    assert "hello" in output
    assert "world" in output
    assert output.startswith("diff --git")


def test_diff_no_index_identical_is_empty(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("same\n", encoding="utf-8")
    b.write_text("same\n", encoding="utf-8")
    assert git.diff_no_index(b, a, cwd=tmp_path) == ""


def test_apply_check_and_apply(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    write_file(repo, "file.txt", "line1\nline2\n")
    commit_all(repo)

    patch = (
        "diff --git a/file.txt b/file.txt\n"
        "--- a/file.txt\n"
        "+++ b/file.txt\n"
        "@@ -1,2 +1,2 @@\n"
        " line1\n"
        "-line2\n"
        "+line2-changed\n"
    )
    git.apply_check(repo, patch)
    git.apply(repo, patch)
    assert (repo / "file.txt").read_text(encoding="utf-8") == "line1\nline2-changed\n"


def test_apply_refuses_read_only_repo(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    write_file(repo_a, "file.txt", "original\n")
    commit_all(repo_a)
    before = (repo_a / "file.txt").read_bytes()

    git.mark_read_only(repo_a)
    patch = (
        "diff --git a/file.txt b/file.txt\n"
        "--- a/file.txt\n"
        "+++ b/file.txt\n"
        "@@ -1 +1 @@\n"
        "-original\n"
        "+mutated\n"
    )
    with pytest.raises(PermissionError, match="read-only"):
        git.apply(repo_a, patch)
    with pytest.raises(PermissionError, match="read-only"):
        git.apply_check(repo_a, patch)

    assert (repo_a / "file.txt").read_bytes() == before


def test_apply_check_failure_surfaces_stderr(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    write_file(repo, "file.txt", "only\n")
    commit_all(repo)

    patch = (
        "diff --git a/file.txt b/file.txt\n"
        "--- a/file.txt\n"
        "+++ b/file.txt\n"
        "@@ -1 +1 @@\n"
        "-missing context\n"
        "+new\n"
    )
    with pytest.raises(git.GitError) as exc_info:
        git.apply_check(repo, patch)
    assert exc_info.value.returncode != 0
    assert exc_info.value.stderr
