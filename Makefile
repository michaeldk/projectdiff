.PHONY: build

# Build frontend/dist, then produce dist/Project-Diff.exe (and portable ZIP).
build:
	cd frontend && npm install && npm run build
	cd backend && uv sync --all-groups && uv run python ../build_windows.py
