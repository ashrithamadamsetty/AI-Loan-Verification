#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate
python -m uvicorn backend.main:app --host "${BACKEND_HOST:-127.0.0.1}" --port "${BACKEND_PORT:-8000}" &
BACKEND_PID=$!
trap 'kill "$BACKEND_PID" 2>/dev/null || true' EXIT INT TERM
npm --prefix frontend run dev
