#!/usr/bin/env python3
"""Build Windows release artifacts via PyInstaller (onedir ZIP + onefile EXE)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = ROOT / "project_diff.spec"
DIST = ROOT / "dist"
APP_NAME = "Project-Diff"
PORTABLE_ZIP = DIST / f"{APP_NAME}-portable.zip"
ONEFILE_EXE = DIST / f"{APP_NAME}.exe"
ONEDIR_EXE = DIST / APP_NAME / f"{APP_NAME}.exe"


def run(cmd: list[str], *, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=ROOT, env=env)


def ensure_frontend_dist() -> None:
    index = ROOT / "frontend" / "dist" / "index.html"
    if not index.is_file():
        raise SystemExit(f"Missing {index}. Run `npm run build` in frontend/ first.")


def pyinstaller(mode: str) -> None:
    env = os.environ.copy()
    env["PROJECT_DIFF_PYINSTALLER_MODE"] = mode
    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            str(SPEC),
        ],
        env=env,
    )


def bundled_frontend_paths(root: Path) -> list[Path]:
    return list(root.rglob("frontend/dist/index.html"))


def assert_bundled_frontend(root: Path) -> None:
    matches = bundled_frontend_paths(root)
    if not matches:
        raise SystemExit(f"Bundled frontend/dist/index.html not found under {root}")


def make_portable_zip() -> None:
    folder = DIST / APP_NAME
    if not folder.is_dir():
        raise SystemExit(f"Expected onedir output at {folder}")

    assert_bundled_frontend(folder)

    if PORTABLE_ZIP.is_file():
        PORTABLE_ZIP.unlink()

    with zipfile.ZipFile(PORTABLE_ZIP, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in folder.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(DIST))
    print(f"Wrote {PORTABLE_ZIP}", flush=True)


def smoke_check() -> None:
    if not ONEDIR_EXE.is_file():
        raise SystemExit(f"Missing onedir executable: {ONEDIR_EXE}")
    if not ONEFILE_EXE.is_file():
        raise SystemExit(f"Missing onefile executable: {ONEFILE_EXE}")
    if not PORTABLE_ZIP.is_file():
        raise SystemExit(f"Missing portable archive: {PORTABLE_ZIP}")

    with zipfile.ZipFile(PORTABLE_ZIP) as archive:
        names = archive.namelist()
        if not any(name.endswith("frontend/dist/index.html") for name in names):
            raise SystemExit(
                f"{PORTABLE_ZIP} does not contain frontend/dist/index.html"
            )

    assert_bundled_frontend(DIST / APP_NAME)
    print("Smoke checks passed.", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)

    if sys.platform != "win32":
        print(
            "Warning: packaging targets Windows x64; PyInstaller output may not run here.",
            file=sys.stderr,
        )

    ensure_frontend_dist()
    pyinstaller("onedir")
    make_portable_zip()
    pyinstaller("onefile")
    smoke_check()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
