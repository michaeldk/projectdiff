"""Start the pywebview window."""

from __future__ import annotations

import argparse
from pathlib import Path

import webview

from project_diff.api import create_api


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_url(dev: bool) -> str:
    if dev:
        return "http://localhost:5173"
    dist = _repo_root() / "frontend" / "dist" / "index.html"
    return dist.as_uri()


def main() -> None:
    parser = argparse.ArgumentParser(description="Project Diff")
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Load the UI from the Vite dev server (http://localhost:5173)",
    )
    args = parser.parse_args()

    url = _resolve_url(args.dev)
    api = create_api()
    webview.create_window("Project Diff", url, js_api=api, width=1280, height=800)
    webview.start()


if __name__ == "__main__":
    main()
