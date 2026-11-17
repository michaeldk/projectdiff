"""Thin pywebview js_api facade."""

from __future__ import annotations

from typing import Any


class Api:
    """Methods exposed to the frontend via window.pywebview.api."""

    def ping(self) -> dict[str, Any]:
        return {"ok": True, "data": "pong"}


def wrap(fn: Any) -> Any:
    """Wrap a js_api method to return structured errors on exception."""

    def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 — bridge must never raise
            return {
                "ok": False,
                "error": {"code": "INTERNAL", "message": str(exc)},
            }

    return wrapper


def create_api() -> Api:
    api = Api()
    api.ping = wrap(api.ping)  # type: ignore[method-assign]
    return api
