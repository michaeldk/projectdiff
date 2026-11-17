# AGENTS.md — Project Diff

Desktop app that compares two local git repositories, shows the differences in a GitHub pull-request style view, and lets the user pick individual lines to bring from project A (source) into project B (target).

The repo is greenfield. This file is the specification for the scaffold: if a path or command below does not exist yet, create it as described rather than inventing a different layout.

## Stack

- **Frontend:** Vue 3, Composition API with `<script setup>`, TypeScript (strict), Vite. **Styling:** Tailwind CSS v4 via `@tailwindcss/vite`; design tokens in `src/styles/theme.css`, semantic classes in `src/styles/components.css`, and small primitives in `src/components/ui/` — templates avoid long utility strings. No UI component library and no state library unless a task asks for one.
- **Backend:** Python with pywebview. Dependencies and virtualenv managed with `uv`; lint and format with `ruff`; tests with `pytest`.
- **Bridge:** pywebview `js_api` only. No HTTP server, no websockets.
- **Git:** the `git` CLI through `subprocess`. No GitPython, no pygit2.
- **Platform:** Windows native (WebView2). Do not add Linux or macOS code paths.

## Layout

```
backend/
  pyproject.toml
  src/project_diff/
    __main__.py      # starts the pywebview window
    api.py           # js_api class: thin, no git logic
    git.py           # the only module that runs subprocess
    files.py         # file listing, ignore rules, pairing A/B
    diff.py          # unified diff parsing into a typed model
    patch.py         # builds a patch from selected lines, applies it
    paths.py         # frontend URL for source vs PyInstaller bundle
  tests/
frontend/
  src/
    api/             # typed wrapper around window.pywebview.api
    components/      # diff view: file list, file, hunk, line
    composables/     # selection state and other shared logic
    types/           # mirrors the backend's diff model
build_windows.py     # PyInstaller onedir ZIP + onefile EXE
project_diff.spec
.github/workflows/release.yml  # tag v* → GitHub Release
```

## Commands

Backend, run from `backend/`:

- `uv sync` — install
- `uv run python -m project_diff --dev` — run against the Vite dev server
- `uv run python -m project_diff` — run against `frontend/dist`
- `uv run pytest`
- `uv run ruff check .` and `uv run ruff format .`
- `uv sync --all-groups` then `uv run python ../build_windows.py` — Windows release artifacts (needs `frontend/dist`)

Frontend, run from `frontend/`:

- `npm install`
- `npm run dev` — Vite dev server with hot reload
- `npm run build`
- `npm run test` — Vitest
- `npm run type-check` — `vue-tsc --noEmit`

Release: push a `v*` tag (e.g. `v0.1.0`); `.github/workflows/release.yml` builds on `windows-latest` and publishes `Project-Diff-portable.zip` and `Project-Diff.exe`.

Before finishing any task, run ruff, pytest, type-check and Vitest, and fix what fails.

## How the app works

1. **Pick folders.** The user chooses A and B with the native folder dialog opened from Python. Both must be git repositories; reject anything else with a clear message.
2. **List files.** In each repo, list tracked and untracked-but-not-ignored files with `git ls-files --cached --others --exclude-standard`, so each side's `.gitignore` is honored. Then remove anything matching the app-level exclude list, which the user can edit in the UI.
3. **Pair files** by relative path: in both, only in A, only in B.
4. **Diff** each differing pair with `git diff --no-index --ignore-cr-at-eol`, oriented so that applying the result turns B's file into A's. Exit code 1 means "differences found", not failure.
5. **Display.** The backend parses the diff into a model (files, hunks, lines, each line with a stable ID) and sends that to the frontend. The frontend never parses raw diff text.
6. **Select.** The user ticks lines, hunks or whole files. Selection state lives in the frontend as a set of line IDs.
7. **Apply.** The frontend sends the selected line IDs. The backend builds the patch, runs `git apply --check`, then `git apply` in B. Changes land in B's working tree only.

## Rules that must hold

- **A is read-only.** Never run a command that can write to A.
- **B must be clean.** If `git status --porcelain` in B is not empty, refuse to apply and tell the user to commit or stash. Re-check immediately before applying, not only when the folder was picked.
- **Check before apply.** Always run `git apply --check` first. If it fails, apply nothing and surface git's error message.
- **Working tree only.** Never stage, commit, create branches, stash, or reset in B.
- **Patch building lives in `patch.py`.** For a partial selection: an unselected added line is dropped, an unselected removed line becomes context, and hunk headers are recomputed. A hunk with nothing selected is omitted.
- **Line endings.** CR-at-EOL differences are hidden in the view. Lines written into B take the line endings B's file already uses; a file new to B keeps A's.
- **Files only in A** are shown as all-added; selecting lines creates the file in B. **Files only in B** are shown as all-removed; selecting every line deletes the file.
- **Subprocess hygiene.** Arguments as a list, never `shell=True`, explicit `cwd`, UTF-8 decoding, `-c core.quotepath=false`. All calls go through `git.py`.
- **Paths.** Use `pathlib`. Relative paths cross the bridge with forward slashes.
- **Bridge contract.** Every `js_api` method returns JSON-serializable data and reports failure as a structured error, never a raised exception. Any change to the diff model is made in the Python types and `frontend/src/types` in the same commit.

## Out of scope for v1

Do not build these unless asked: binary file handling (list them as "binary, not supported"), rename detection, a non-git folder as target, committing or staging on the user's behalf, i18n.

## Testing

- **pytest:** build temporary git repos with `tmp_path` and exercise the real `git` binary; do not mock git. Required coverage: file listing with ignore rules, diff parsing, partial-line patch building, CRLF/LF mixes, files only in A, files only in B, dirty-target refusal, failed `--check`.
- **Vitest:** selection logic (line, hunk, file toggles and their interaction) and the API wrapper. Component snapshot tests are not required.

## Conventions

- Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`, `refactor:`, `docs:`).
- English for code, comments, commit messages and UI text.
- Python: type hints everywhere, dataclasses for the diff model.
- TypeScript: no `any`; `window.pywebview.api` is touched only inside `frontend/src/api`.
