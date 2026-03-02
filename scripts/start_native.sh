#!/bin/bash
# Start PolarVortex backend and frontend natively with nohup so they keep
# running after the terminal exits. See docs/RUNNING_NATIVE_ON_RASPBERRY_PI.md.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
LOG_DIR="${PV_LOG_DIR:-$BACKEND_DIR/local_storage/log}"
mkdir -p "$LOG_DIR"

# Venv activate: Windows uses Scripts, Linux/macOS use bin
if [ -f "$BACKEND_DIR/.venv/Scripts/activate" ]; then
  VENV_ACTIVATE="$BACKEND_DIR/.venv/Scripts/activate"
elif [ -f "$BACKEND_DIR/.venv/bin/activate" ]; then
  VENV_ACTIVATE="$BACKEND_DIR/.venv/bin/activate"
else
  echo "Error: backend virtualenv not found. Create it with: cd backend && python -m venv .venv && pip install -r requirements.txt"
  exit 1
fi

BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
BACKEND_PID_FILE="$LOG_DIR/backend.pid"
FRONTEND_PID_FILE="$LOG_DIR/frontend.pid"

# Load backend env if present (PV_CONFIG, ARDUINO_PORTS, etc.)
if [ -f "$BACKEND_DIR/.env" ]; then
  set -a
  # shellcheck source=/dev/null
  source "$BACKEND_DIR/.env"
  set +a
fi

# Defaults if not set
export PV_CONFIG="${PV_CONFIG:-$BACKEND_DIR/local_storage/config/config.yaml}"
export ARDUINO_PORTS="${ARDUINO_PORTS:-/dev/ttyACM0,/dev/ttyUSB0}"
export BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
export BACKEND_PORT="${BACKEND_PORT:-8000}"
export VITE_API_BASE_URL="${VITE_API_BASE_URL:-http://localhost:$BACKEND_PORT}"
export VITE_WS_BASE_URL="${VITE_WS_BASE_URL:-ws://localhost:$BACKEND_PORT}"

echo "PolarVortex native startup"
echo "  Backend:  $BACKEND_HOST:$BACKEND_PORT (log: $BACKEND_LOG)"
echo "  Frontend: Vite dev server (log: $FRONTEND_LOG)"
echo ""

# Start backend (PID captured inside subshell so we get uvicorn, not the shell)
if [ -f "$BACKEND_PID_FILE" ] && kill -0 "$(cat "$BACKEND_PID_FILE")" 2>/dev/null; then
  echo "Backend already running (PID $(cat "$BACKEND_PID_FILE")). Skipping."
else
  (
    cd "$BACKEND_DIR"
    source "$VENV_ACTIVATE"
    nohup uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" >> "$BACKEND_LOG" 2>&1 &
    echo $! > "$BACKEND_PID_FILE"
  )
  echo "Backend started (PID $(cat "$BACKEND_PID_FILE"))."
fi

# Brief pause so backend is up before frontend tries to connect
sleep 2

# Start frontend (Vite dev server; PID is npm, which is enough to stop the server)
if [ -f "$FRONTEND_PID_FILE" ] && kill -0 "$(cat "$FRONTEND_PID_FILE")" 2>/dev/null; then
  echo "Frontend already running (PID $(cat "$FRONTEND_PID_FILE")). Skipping."
else
  (
    cd "$FRONTEND_DIR"
    export VITE_API_BASE_URL VITE_WS_BASE_URL
    nohup npm run dev >> "$FRONTEND_LOG" 2>&1 &
    echo $! > "$FRONTEND_PID_FILE"
  )
  echo "Frontend started (PID $(cat "$FRONTEND_PID_FILE"))."
fi

echo ""
echo "Both processes are running in the background. You can close this terminal."
echo "  Backend:  http://localhost:$BACKEND_PORT"
echo "  Frontend: http://localhost:5173 (Vite dev)"
echo "  Logs:     $BACKEND_LOG  $FRONTEND_LOG"
echo "  PIDs:     $BACKEND_PID_FILE  $FRONTEND_PID_FILE"
echo "To stop later: kill \$(cat $BACKEND_PID_FILE) \$(cat $FRONTEND_PID_FILE)"
