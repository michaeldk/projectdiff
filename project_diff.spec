# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Project Diff (Windows x64).

Set PROJECT_DIFF_PYINSTALLER_MODE=onedir (portable folder) or onefile (single .exe).
Requires frontend/dist from `npm run build` in frontend/. Uses system WebView2 Evergreen;
does not bundle a fixed WebView2 runtime.
"""

from __future__ import annotations

import os

from PyInstaller.compat import is_win
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

block_cipher = None

_spec_dir = os.path.dirname(os.path.abspath(SPEC))
_mode = os.environ.get("PROJECT_DIFF_PYINSTALLER_MODE", "onedir").strip().lower()
if _mode not in ("onedir", "onefile"):
    raise SystemExit(
        f"Invalid PROJECT_DIFF_PYINSTALLER_MODE: {_mode!r} (use onedir or onefile)"
    )

_project_name = "Project-Diff"
_frontend_dist = os.path.join(_spec_dir, "frontend", "dist")
_entry = os.path.join(_spec_dir, "backend", "src", "project_diff", "__main__.py")
_src = os.path.join(_spec_dir, "backend", "src")

if not os.path.isdir(_frontend_dist):
    raise SystemExit(
        f"Missing {_frontend_dist}. Run `npm run build` in frontend/ before packaging."
    )

datas = [
    (_frontend_dist, os.path.join("frontend", "dist")),
]

binaries: list[tuple[str, str]] = []
hiddenimports = [
    "clr_loader",
    "pythonnet",
    *collect_submodules("project_diff"),
]

if is_win:
    datas += collect_data_files("webview", subdir="lib")
    binaries += collect_dynamic_libs("webview")
    hiddenimports += collect_submodules("webview")

a = Analysis(
    [_entry],
    pathex=[_src],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

_exe_kwargs = dict(
    name=_project_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

if _mode == "onefile":
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        **_exe_kwargs,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        **_exe_kwargs,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name=_project_name,
    )
