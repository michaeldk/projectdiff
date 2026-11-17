"""Tests for the js_api bridge."""

from project_diff.api import create_api


def test_ping_returns_pong() -> None:
    api = create_api()
    result = api.ping()
    assert result == {"ok": True, "data": "pong"}
