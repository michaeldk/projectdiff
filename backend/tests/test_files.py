"""Tests for files.py listing, excludes, pairing, and binary detection."""

from __future__ import annotations

from pathlib import Path

from project_diff.files import (
    FileSide,
    is_binary_file,
    is_excluded,
    list_repo_files,
    pair_files,
)
from tests.helpers import commit_all, init_repo, write_file


def test_is_excluded_directory_prefix() -> None:
    assert is_excluded("node_modules/pkg/index.js", ["node_modules/"])
    assert is_excluded("src/node_modules/pkg/a.js", ["node_modules/"])
    assert not is_excluded("src/app.js", ["node_modules/"])


def test_is_excluded_glob_basename() -> None:
    assert is_excluded("src/foo.pyc", ["*.pyc"])
    assert is_excluded("foo.pyc", ["*.pyc"])
    assert not is_excluded("src/foo.py", ["*.pyc"])


def test_list_repo_files_applies_excludes_after_gitignore(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    write_file(repo, ".gitignore", "secret.log\n")
    write_file(repo, "app.py", "print(1)\n")
    write_file(repo, "secret.log", "nope\n")
    write_file(repo, "dist/bundle.js", "built\n")
    write_file(repo, "src/util.pyc", "bytecode")
    commit_all(repo)

    files = list_repo_files(repo, excludes=["dist/", "*.pyc"])
    assert "app.py" in files
    assert ".gitignore" in files
    assert "secret.log" not in files
    assert "dist/bundle.js" not in files
    assert "src/util.pyc" not in files


def test_pair_files_both_only_a_only_b(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")

    write_file(repo_a, "shared.txt", "a\n")
    write_file(repo_a, "only_a.txt", "a only\n")
    write_file(repo_b, "shared.txt", "b\n")
    write_file(repo_b, "only_b.txt", "b only\n")
    commit_all(repo_a)
    commit_all(repo_b)

    pairing = pair_files(repo_a, repo_b)

    assert [e.path for e in pairing.both] == ["shared.txt"]
    assert pairing.both[0].side is FileSide.BOTH
    assert pairing.both[0].binary is False

    assert [e.path for e in pairing.only_a] == ["only_a.txt"]
    assert pairing.only_a[0].side is FileSide.ONLY_A

    assert [e.path for e in pairing.only_b] == ["only_b.txt"]
    assert pairing.only_b[0].side is FileSide.ONLY_B


def test_pair_files_marks_binary(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    write_file(repo_a, "pic.bin", b"hello\0world")
    write_file(repo_b, "pic.bin", b"hello\0there")
    write_file(repo_a, "readme.txt", "text\n")
    write_file(repo_b, "readme.txt", "text\n")
    commit_all(repo_a)
    commit_all(repo_b)

    pairing = pair_files(repo_a, repo_b)
    by_path = {e.path: e for e in pairing.all_entries()}
    assert by_path["pic.bin"].binary is True
    assert by_path["readme.txt"].binary is False


def test_is_binary_file_detects_nul(tmp_path: Path) -> None:
    text = tmp_path / "a.txt"
    text.write_bytes(b"plain text")
    binary = tmp_path / "b.bin"
    binary.write_bytes(b"x\0y")
    assert is_binary_file(text) is False
    assert is_binary_file(binary) is True
