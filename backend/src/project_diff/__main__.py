"""Start the pywebview window."""

from __future__ import annotations

import argparse
import sys

import webview

from project_diff.api import create_api
from project_diff.paths import is_packaged, resolve_frontend_url


def main() -> None:
    parser = argparse.ArgumentParser(description="Project Diff")
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Load the UI from the Vite dev server (http://localhost:5173)",
    )
    args = parser.parse_args()

    packaged = is_packaged()
    if packaged and args.dev:
        print("Ignoring --dev in a packaged build.", file=sys.stderr)
        args.dev = False

    try:
        url = resolve_frontend_url(dev=args.dev)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

    api = create_api()
    webview.create_window("Project Diff", url, js_api=api, width=1280, height=800)
    webview.start(debug=not packaged)


if __name__ == "__main__":
    main()
