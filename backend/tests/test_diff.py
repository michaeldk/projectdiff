"""Tests for diff.py parsing, synthesis, and compute_diff."""

from __future__ import annotations

from pathlib import Path

from project_diff.diff import (
    DiffResult,
    LineKind,
    compute_diff,
    make_line_id,
    parse_unified_diff,
    read_text_lines,
    synthesize_added,
    synthesize_removed,
)
from project_diff.files import FileSide, pair_files
from tests.helpers import commit_all, init_repo, write_file


def test_make_line_id_format() -> None:
    assert make_line_id(0, 1, 2) == "0:1:2"


def test_parse_unified_diff_hunks_and_line_numbers() -> None:
    text = (
        "diff --git a/file.txt b/file.txt\n"
        "index 111..222 100644\n"
        "--- a/file.txt\n"
        "+++ b/file.txt\n"
        "@@ -1,3 +1,4 @@\n"
        " line1\n"
        "-line2\n"
        "+line2-changed\n"
        " line3\n"
        "+line4\n"
    )
    file_diff = parse_unified_diff(text, path="src/file.txt", file_idx=3)
    assert file_diff is not None
    assert file_diff.path == "src/file.txt"
    assert file_diff.side is FileSide.BOTH
    assert file_diff.binary is False
    assert len(file_diff.hunks) == 1

    hunk = file_diff.hunks[0]
    assert hunk.old_start == 1
    assert hunk.old_count == 3
    assert hunk.new_start == 1
    assert hunk.new_count == 4
    assert [line.kind for line in hunk.lines] == [
        LineKind.CTX,
        LineKind.DEL,
        LineKind.ADD,
        LineKind.CTX,
        LineKind.ADD,
    ]
    assert [line.old_no for line in hunk.lines] == [1, 2, None, 3, None]
    assert [line.new_no for line in hunk.lines] == [1, None, 2, 3, 4]
    assert [line.text for line in hunk.lines] == [
        "line1",
        "line2",
        "line2-changed",
        "line3",
        "line4",
    ]
    assert hunk.lines[0].id == "3:0:0"
    assert hunk.lines[-1].id == "3:0:4"


def test_parse_unified_diff_empty_returns_none() -> None:
    assert parse_unified_diff("", path="x.txt") is None
    assert parse_unified_diff("diff --git a/x b/x\n", path="x.txt") is None


def test_parse_skips_no_newline_marker() -> None:
    text = "@@ -1 +1 @@\n-old\n+new\n\\ No newline at end of file\n"
    file_diff = parse_unified_diff(text, path="a.txt")
    assert file_diff is not None
    assert len(file_diff.hunks[0].lines) == 2
    assert file_diff.hunks[0].lines[1].text == "new"


def test_synthesize_added_and_removed() -> None:
    added = synthesize_added("only_a.txt", ["a", "b"], file_idx=1)
    assert added.side is FileSide.ONLY_A
    assert added.binary is False
    assert len(added.hunks) == 1
    assert [line.kind for line in added.hunks[0].lines] == [LineKind.ADD, LineKind.ADD]
    assert [line.new_no for line in added.hunks[0].lines] == [1, 2]
    assert added.hunks[0].lines[0].id == "1:0:0"
    assert added.hunks[0].old_start == 0
    assert added.hunks[0].old_count == 0
    assert added.hunks[0].new_count == 2

    removed = synthesize_removed("only_b.txt", ["x"], file_idx=2)
    assert removed.side is FileSide.ONLY_B
    assert [line.kind for line in removed.hunks[0].lines] == [LineKind.DEL]
    assert removed.hunks[0].lines[0].old_no == 1
    assert removed.hunks[0].lines[0].new_no is None
    assert removed.hunks[0].new_start == 0
    assert removed.hunks[0].old_count == 1


def test_synthesize_empty_file_still_has_hunk() -> None:
    added = synthesize_added("empty.txt", [])
    assert added.hunks[0].lines == ()
    assert added.hunks[0].old_count == 0
    assert added.hunks[0].new_count == 0


def test_synthesize_binary() -> None:
    added = synthesize_added("pic.bin", (), binary=True)
    assert added.binary is True
    assert added.hunks == ()
    removed = synthesize_removed("pic.bin", (), binary=True)
    assert removed.binary is True
    assert removed.hunks == ()


def test_read_text_lines_strips_crlf(tmp_path: Path) -> None:
    path = tmp_path / "f.txt"
    path.write_bytes(b"a\r\nb\nc\r\n")
    assert read_text_lines(path) == ["a", "b", "c"]


def test_compute_diff_pairs_only_a_only_b_and_modified(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")

    write_file(repo_a, "shared.txt", "hello\nworld\n")
    write_file(repo_a, "same.txt", "identical\n")
    write_file(repo_a, "only_a.txt", "from a\n")
    write_file(repo_b, "shared.txt", "hello\nthere\n")
    write_file(repo_b, "same.txt", "identical\n")
    write_file(repo_b, "only_b.txt", "from b\n")
    commit_all(repo_a)
    commit_all(repo_b)

    pairing = pair_files(repo_a, repo_b)
    result = compute_diff(repo_a, repo_b, pairing, diff_id="fixed-id")

    assert isinstance(result, DiffResult)
    assert result.diff_id == "fixed-id"
    paths = [f.path for f in result.files]
    assert "shared.txt" in paths
    assert "only_a.txt" in paths
    assert "only_b.txt" in paths
    assert "same.txt" not in paths

    by_path = {f.path: f for f in result.files}
    shared = by_path["shared.txt"]
    assert shared.side is FileSide.BOTH
    assert shared.binary is False
    assert any(line.kind is LineKind.DEL and line.text == "there" for line in shared.hunks[0].lines)
    assert any(line.kind is LineKind.ADD and line.text == "world" for line in shared.hunks[0].lines)

    only_a = by_path["only_a.txt"]
    assert only_a.side is FileSide.ONLY_A
    assert all(line.kind is LineKind.ADD for line in only_a.hunks[0].lines)
    assert only_a.hunks[0].lines[0].text == "from a"

    only_b = by_path["only_b.txt"]
    assert only_b.side is FileSide.ONLY_B
    assert all(line.kind is LineKind.DEL for line in only_b.hunks[0].lines)
    assert only_b.hunks[0].lines[0].text == "from b"


def test_compute_diff_line_ids_are_stable_and_scoped(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    write_file(repo_a, "f.txt", "one\ntwo\n")
    write_file(repo_b, "f.txt", "one\nTOO\n")
    commit_all(repo_a)
    commit_all(repo_b)

    pairing = pair_files(repo_a, repo_b)
    first = compute_diff(repo_a, repo_b, pairing, diff_id="abc")
    second = compute_diff(repo_a, repo_b, pairing, diff_id="abc")

    assert first.to_dict() == second.to_dict()
    assert first.files[0].hunks[0].lines[0].id == "0:0:0"


def test_compute_diff_marks_binary(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    write_file(repo_a, "pic.bin", b"hello\0a")
    write_file(repo_b, "pic.bin", b"hello\0b")
    write_file(repo_a, "only.bin", b"x\0")
    commit_all(repo_a)
    commit_all(repo_b)

    pairing = pair_files(repo_a, repo_b)
    result = compute_diff(repo_a, repo_b, pairing)
    by_path = {f.path: f for f in result.files}

    assert by_path["pic.bin"].binary is True
    assert by_path["pic.bin"].hunks == ()
    assert by_path["only.bin"].binary is True
    assert by_path["only.bin"].side is FileSide.ONLY_A


def test_compute_diff_ignores_cr_at_eol(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    (repo_a / "eol.txt").write_bytes(b"same\n")
    (repo_b / "eol.txt").write_bytes(b"same\r\n")
    commit_all(repo_a)
    commit_all(repo_b)

    pairing = pair_files(repo_a, repo_b)
    result = compute_diff(repo_a, repo_b, pairing)
    assert all(f.path != "eol.txt" for f in result.files)


def test_diff_result_to_dict_is_json_friendly(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    write_file(repo_a, "a.txt", "x\n")
    write_file(repo_b, "a.txt", "y\n")
    commit_all(repo_a)
    commit_all(repo_b)

    result = compute_diff(repo_a, repo_b, pair_files(repo_a, repo_b), diff_id="id")
    payload = result.to_dict()
    assert payload["diff_id"] == "id"
    assert isinstance(payload["files"], list)
    file0 = payload["files"][0]
    assert file0["side"] == "both"
    assert file0["hunks"][0]["lines"][0]["kind"] in {"add", "del", "ctx"}
