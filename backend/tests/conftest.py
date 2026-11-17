"""Shared fixtures for real-git backend tests."""

from __future__ import annotations

import pytest

from project_diff import git


@pytest.fixture(autouse=True)
def _clear_read_only_repos() -> None:
    git.clear_read_only()
    yield
    git.clear_read_only()
