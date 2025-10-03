#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# Ensure we are in project root containing backend/
if [ ! -d backend ]; then
  echo "Error: run from project root (directory containing backend/)" >&2
  exit 1
fi

# Recreate .env if missing or invalid
if [ ! -f .env ]; then
  printf 'SECRET_KEY=change-me\nOPENAI_API_KEY=sk-placeholder-key\nFLASK_ENV=development\nDATABASE_URL=sqlite:///smartretail.db\n' > .env
fi

# Choose virtual environment directory
VENV_DIR="venv_linux"
if [ ! -d "$VENV_DIR" ]; then
  # fallback to common names if user has a different venv
  for alt in geof venv env; do
    if [ -d "$alt" ]; then VENV_DIR="$alt"; break; fi
  done
fi

# Activate venv
if [ -f "$VENV_DIR/bin/activate" ]; then
  # shellcheck disable=SC1090
  . "$VENV_DIR/bin/activate"
else
  echo "Virtual environment not found at $VENV_DIR. Create it with: python3 -m venv venv_linux" >&2
  exit 1
fi

# Environment variables
export FLASK_APP=backend.app
export PYTHONPATH="$(pwd)"

# Start app with logs
mkdir -p logs
: > logs/app.log
nohup python backend/app.py >> logs/app.log 2>&1 &
PID=$!

echo "Started SmartRetail AI (PID: $PID). Logs: logs/app.log"

echo "Last 50 log lines (follow with Ctrl+C to stop tailing):"
tail -n 50 -f logs/app.log
