"""Tests for patch.py: partial selection, EOL, dirty destination apply, apply --check."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from project_diff.diff import LineKind, compute_diff
from project_diff.files import pair_files
from project_diff.patch import (
    ApplyCheckFailedError,
    apply_selection,
    build_patch,
    detect_eol,
    read_raw_file,
)
from tests.helpers import commit_all, init_repo, write_file


def _tree_hash(repo: Path) -> str:
    """Hash of all tracked+untracked file bytes (for asserting A is untouched)."""
    h = hashlib.sha256()
    for path in sorted(repo.rglob("*")):
        if not path.is_file():
            continue
        if ".git" in path.parts:
            continue
        rel = path.relative_to(repo).as_posix().encode()
        h.update(rel)
        h.update(b"\0")
        h.update(path.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def _ids_of_kind(diff, path: str, kind: LineKind) -> list[str]:
    file_diff = next(f for f in diff.files if f.path == path)
    return [line.id for hunk in file_diff.hunks for line in hunk.lines if line.kind is kind]


def _all_change_ids(diff, path: str) -> list[str]:
    file_diff = next(f for f in diff.files if f.path == path)
    return [
        line.id
        for hunk in file_diff.hunks
        for line in hunk.lines
        if line.kind in (LineKind.ADD, LineKind.DEL)
    ]


def test_detect_eol_and_read_raw_file(tmp_path: Path) -> None:
    lf = tmp_path / "lf.txt"
    crlf = tmp_path / "crlf.txt"
    none = tmp_path / "none.txt"
    lf.write_bytes(b"a\nb\n")
    crlf.write_bytes(b"a\r\nb\r\n")
    none.write_bytes(b"solo")

    assert detect_eol(lf.read_bytes()) == b"\n"
    assert detect_eol(crlf.read_bytes()) == b"\r\n"
    assert detect_eol(b"") == b"\n"

    raw_lf = read_raw_file(lf)
    assert raw_lf.bodies == (b"a", b"b")
    assert raw_lf.eol == b"\n"
    assert raw_lf.ends_with_newline is True

    raw_crlf = read_raw_file(crlf)
    assert raw_crlf.bodies == (b"a", b"b")
    assert raw_crlf.eol == b"\r\n"

    raw_none = read_raw_file(none)
    assert raw_none.bodies == (b"solo",)
    assert raw_none.ends_with_newline is False


def test_partial_selection_drops_add_and_keeps_unselected_del_as_context(
    tmp_path: Path,
) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    write_file(repo_a, "f.txt", "keep\nfrom-a\n")
    write_file(repo_b, "f.txt", "keep\nfrom-b\n")
    commit_all(repo_a)
    commit_all(repo_b)

    diff = compute_diff(repo_a, repo_b, pair_files(repo_a, repo_b))
    adds = _ids_of_kind(diff, "f.txt", LineKind.ADD)
    dels = _ids_of_kind(diff, "f.txt", LineKind.DEL)
    assert len(adds) == 1
    assert len(dels) == 1

    # Select only the add; leave the delete unselected → becomes context.
    patch = build_patch(diff, adds, repo_a=repo_a, repo_b=repo_b)
    assert b"-from-b" not in patch
    assert b" from-b" in patch or b" from-b\n" in patch
    assert b"+from-a" in patch

    result = apply_selection(diff, adds, repo_a=repo_a, repo_b=repo_b)
    assert result.files == ("f.txt",)
    assert (repo_b / "f.txt").read_text(encoding="utf-8") == "keep\nfrom-b\nfrom-a\n"


def test_partial_selection_omits_hunk_with_nothing_selected(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    # Two well-separated changes so git emits two hunks.
    write_file(
        repo_a,
        "f.txt",
        "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12\nA-change\n14\n15\n",
    )
    write_file(
        repo_b,
        "f.txt",
        "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12\nB-change\n14\n15\n",
    )
    # Also change line 2 for a first hunk.
    write_file(
        repo_a,
        "f.txt",
        "1\nA2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12\nA-change\n14\n15\n",
    )
    write_file(
        repo_b,
        "f.txt",
        "1\nB2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12\nB-change\n14\n15\n",
    )
    commit_all(repo_a)
    commit_all(repo_b)

    diff = compute_diff(repo_a, repo_b, pair_files(repo_a, repo_b))
    file_diff = diff.files[0]
    assert len(file_diff.hunks) >= 2

    # Select changes only in the last hunk.
    last_hunk = file_diff.hunks[-1]
    selected = [line.id for line in last_hunk.lines if line.kind in (LineKind.ADD, LineKind.DEL)]
    patch = build_patch(diff, selected, repo_a=repo_a, repo_b=repo_b)
    # First hunk's B2/A2 must not appear as a change (one hunk header only).
    assert patch.count(b"\n@@ ") == 1
    assert b"A-change" in patch
    assert b"-B2" not in patch
    assert b"+A2" not in patch


def test_hunk_headers_are_recomputed(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    write_file(repo_a, "f.txt", "a\nb\nc\n")
    write_file(repo_b, "f.txt", "a\nX\nc\n")
    commit_all(repo_a)
    commit_all(repo_b)

    diff = compute_diff(repo_a, repo_b, pair_files(repo_a, repo_b))
    adds = _ids_of_kind(diff, "f.txt", LineKind.ADD)
    patch = build_patch(diff, adds, repo_a=repo_a, repo_b=repo_b)
    # Unselected del → context, so old and new counts both include that line.
    assert b"@@ " in patch
    text = patch.decode("utf-8")
    # Expect something like @@ -1,3 +1,4 @@ (3 old lines, 4 new with the add)
    assert "@@ -1,3 +1,4 @@" in text or "@@ -1,3 +1,4@@" in text.replace(" ", "")


def test_only_a_creates_file_with_selected_lines(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    write_file(repo_a, "new.txt", "one\ntwo\nthree\n")
    write_file(repo_a, "pad.txt", "x\n")
    write_file(repo_b, "pad.txt", "x\n")
    commit_all(repo_a)
    commit_all(repo_b)

    diff = compute_diff(repo_a, repo_b, pair_files(repo_a, repo_b))
    adds = _ids_of_kind(diff, "new.txt", LineKind.ADD)
    assert len(adds) == 3

    # Select first and third lines only.
    selected = [adds[0], adds[2]]
    before_a = _tree_hash(repo_a)
    result = apply_selection(diff, selected, repo_a=repo_a, repo_b=repo_b)
    assert result.files == ("new.txt",)
    assert (repo_b / "new.txt").read_text(encoding="utf-8") == "one\nthree\n"
    assert _tree_hash(repo_a) == before_a


def test_only_b_full_selection_deletes_file(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    write_file(repo_a, "pad.txt", "x\n")
    write_file(repo_b, "pad.txt", "x\n")
    write_file(repo_b, "gone.txt", "bye\nnow\n")
    commit_all(repo_a)
    commit_all(repo_b)

    diff = compute_diff(repo_a, repo_b, pair_files(repo_a, repo_b))
    selected = _all_change_ids(diff, "gone.txt")
    result = apply_selection(diff, selected, repo_a=repo_a, repo_b=repo_b)
    assert result.files == ("gone.txt",)
    assert not (repo_b / "gone.txt").exists()


def test_only_b_partial_selection_removes_some_lines(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    write_file(repo_a, "pad.txt", "x\n")
    write_file(repo_b, "pad.txt", "x\n")
    write_file(repo_b, "trim.txt", "keep\ndrop\nkeep2\n")
    commit_all(repo_a)
    commit_all(repo_b)

    diff = compute_diff(repo_a, repo_b, pair_files(repo_a, repo_b))
    dels = _ids_of_kind(diff, "trim.txt", LineKind.DEL)
    assert len(dels) == 3
    # Drop the middle line only.
    result = apply_selection(diff, [dels[1]], repo_a=repo_a, repo_b=repo_b)
    assert result.files == ("trim.txt",)
    assert (repo_b / "trim.txt").read_text(encoding="utf-8") == "keep\nkeep2\n"


def test_crlf_destination_preserves_crlf_when_applying(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    (repo_a / "f.txt").write_bytes(b"same\r\nfrom-a\r\n")
    (repo_b / "f.txt").write_bytes(b"same\r\nfrom-b\r\n")
    commit_all(repo_a)
    commit_all(repo_b)

    diff = compute_diff(repo_a, repo_b, pair_files(repo_a, repo_b))
    selected = _all_change_ids(diff, "f.txt")
    apply_selection(diff, selected, repo_a=repo_a, repo_b=repo_b)
    data = (repo_b / "f.txt").read_bytes()
    assert b"\r\n" in data
    assert data == b"same\r\nfrom-a\r\n"


def test_lf_destination_preserves_lf_when_applying(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    (repo_a / "f.txt").write_bytes(b"same\nfrom-a\n")
    (repo_b / "f.txt").write_bytes(b"same\nfrom-b\n")
    commit_all(repo_a)
    commit_all(repo_b)

    diff = compute_diff(repo_a, repo_b, pair_files(repo_a, repo_b))
    selected = _all_change_ids(diff, "f.txt")
    apply_selection(diff, selected, repo_a=repo_a, repo_b=repo_b)
    assert (repo_b / "f.txt").read_bytes() == b"same\nfrom-a\n"


def test_mixed_eol_a_lf_b_crlf_preserves_b_eol(tmp_path: Path) -> None:
    """B's existing CRLF wins even when A's content is LF-only."""
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    (repo_a / "f.txt").write_bytes(b"same\nfrom-a\n")
    (repo_b / "f.txt").write_bytes(b"same\r\nfrom-b\r\n")
    commit_all(repo_a)
    commit_all(repo_b)

    diff = compute_diff(repo_a, repo_b, pair_files(repo_a, repo_b))
    selected = _all_change_ids(diff, "f.txt")
    apply_selection(diff, selected, repo_a=repo_a, repo_b=repo_b)
    assert (repo_b / "f.txt").read_bytes() == b"same\r\nfrom-a\r\n"


def test_mixed_eol_a_crlf_b_lf_preserves_b_eol(tmp_path: Path) -> None:
    """B's existing LF wins even when A's content is CRLF."""
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    (repo_a / "f.txt").write_bytes(b"same\r\nfrom-a\r\n")
    (repo_b / "f.txt").write_bytes(b"same\nfrom-b\n")
    commit_all(repo_a)
    commit_all(repo_b)

    diff = compute_diff(repo_a, repo_b, pair_files(repo_a, repo_b))
    selected = _all_change_ids(diff, "f.txt")
    apply_selection(diff, selected, repo_a=repo_a, repo_b=repo_b)
    assert (repo_b / "f.txt").read_bytes() == b"same\nfrom-a\n"


def test_new_file_keeps_a_eol(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    (repo_a / "new.txt").write_bytes(b"line\r\n")
    write_file(repo_a, "pad.txt", "x\n")
    write_file(repo_b, "pad.txt", "x\n")
    commit_all(repo_a)
    commit_all(repo_b)

    diff = compute_diff(repo_a, repo_b, pair_files(repo_a, repo_b))
    selected = _all_change_ids(diff, "new.txt")
    apply_selection(diff, selected, repo_a=repo_a, repo_b=repo_b)
    assert (repo_b / "new.txt").read_bytes() == b"line\r\n"


def test_dirty_destination_allows_apply_when_check_passes(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    write_file(repo_a, "f.txt", "a\n")
    write_file(repo_b, "f.txt", "b\n")
    commit_all(repo_a)
    commit_all(repo_b)

    # Dirty B after commit; diff reflects the working tree.
    write_file(repo_b, "f.txt", "dirty\n")

    diff = compute_diff(repo_a, repo_b, pair_files(repo_a, repo_b))
    selected = _all_change_ids(diff, "f.txt")
    result = apply_selection(diff, selected, repo_a=repo_a, repo_b=repo_b)
    assert result.files == ("f.txt",)
    assert (repo_b / "f.txt").read_text(encoding="utf-8") == "a\n"


def test_apply_check_failure_surfaces_message(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    write_file(repo_a, "f.txt", "alpha\n")
    write_file(repo_b, "f.txt", "beta\n")
    commit_all(repo_a)
    commit_all(repo_b)

    diff = compute_diff(repo_a, repo_b, pair_files(repo_a, repo_b))
    selected = _all_change_ids(diff, "f.txt")
    patch = build_patch(diff, selected, repo_a=repo_a, repo_b=repo_b)
    assert patch

    # Change B after the diff so --check fails (tree may be dirty).
    write_file(repo_b, "f.txt", "gamma\n")

    with pytest.raises(ApplyCheckFailedError) as exc_info:
        apply_selection(diff, selected, repo_a=repo_a, repo_b=repo_b)
    assert exc_info.value.code == "APPLY_CHECK_FAILED"
    assert str(exc_info.value)
    assert (repo_b / "f.txt").read_text(encoding="utf-8") == "gamma\n"


def test_apply_never_modifies_a(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    write_file(repo_a, "f.txt", "from-a\n")
    write_file(repo_a, "only_a.txt", "secret\n")
    write_file(repo_b, "f.txt", "from-b\n")
    write_file(repo_b, "only_b.txt", "temp\n")
    commit_all(repo_a)
    commit_all(repo_b)

    before = _tree_hash(repo_a)
    diff = compute_diff(repo_a, repo_b, pair_files(repo_a, repo_b))
    selected: list[str] = []
    for f in diff.files:
        selected.extend(_all_change_ids(diff, f.path))

    apply_selection(diff, selected, repo_a=repo_a, repo_b=repo_b)
    assert _tree_hash(repo_a) == before


def test_empty_selection_is_noop(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    write_file(repo_a, "f.txt", "a\n")
    write_file(repo_b, "f.txt", "b\n")
    commit_all(repo_a)
    commit_all(repo_b)

    diff = compute_diff(repo_a, repo_b, pair_files(repo_a, repo_b))
    result = apply_selection(diff, [], repo_a=repo_a, repo_b=repo_b)
    assert result.files == ()
    assert (repo_b / "f.txt").read_text(encoding="utf-8") == "b\n"


def test_full_both_selection_makes_b_match_a(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    write_file(repo_a, "f.txt", "line1\nline2\nline3\n")
    write_file(repo_b, "f.txt", "line1\nOLD\nline3\n")
    commit_all(repo_a)
    commit_all(repo_b)

    diff = compute_diff(repo_a, repo_b, pair_files(repo_a, repo_b))
    selected = _all_change_ids(diff, "f.txt")
    apply_selection(diff, selected, repo_a=repo_a, repo_b=repo_b)
    assert (repo_b / "f.txt").read_bytes() == (repo_a / "f.txt").read_bytes()


def test_build_patch_skips_binary(tmp_path: Path) -> None:
    repo_a = init_repo(tmp_path / "a")
    repo_b = init_repo(tmp_path / "b")
    write_file(repo_a, "pic.bin", b"a\0b")
    write_file(repo_b, "pic.bin", b"a\0c")
    write_file(repo_a, "t.txt", "a\n")
    write_file(repo_b, "t.txt", "b\n")
    commit_all(repo_a)
    commit_all(repo_b)

    diff = compute_diff(repo_a, repo_b, pair_files(repo_a, repo_b))
    selected = _all_change_ids(diff, "t.txt")
    patch = build_patch(diff, selected, repo_a=repo_a, repo_b=repo_b)
    assert b"pic.bin" not in patch
    assert b"t.txt" in patch
