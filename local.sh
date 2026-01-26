#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_PORT=""

copy_env() {
  if [[ ! -f "$ROOT_DIR/.env" && -f "$ROOT_DIR/env.example" ]]; then
    cp "$ROOT_DIR/env.example" "$ROOT_DIR/.env"
  fi
}

backend_running() {
  if ! command -v curl >/dev/null 2>&1; then
    return 1
  fi

  local code
  code="$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || true)"
  [[ "$code" == "200" ]]
}

frontend_running() {
  if ! command -v curl >/dev/null 2>&1; then
    return 1
  fi

  local port
  for port in {5173..5185}; do
    local code
    code="$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${port}/" || true)"
    if [[ "$code" == "200" ]]; then
      FRONTEND_PORT="$port"
      return 0
    fi
  done

  return 1
}

stop_port() {
  local port="$1"
  local stopped=false

  if command -v lsof >/dev/null 2>&1; then
    local pids=""
    pids="$(lsof -ti "tcp:${port}" 2>/dev/null || true)"
    if [[ -n "$pids" ]]; then
      kill $pids >/dev/null 2>&1 || true
      stopped=true
    fi
  else
    case "$(uname -s 2>/dev/null || echo "")" in
      MINGW*|MSYS*|CYGWIN*)
        local pids=""
        pids="$(netstat -ano 2>/dev/null | findstr ":${port}" | awk '{print $NF}' | sort -u || true)"
        if [[ -n "$pids" ]]; then
          local pid
          for pid in $pids; do
            taskkill /PID "$pid" /F >/dev/null 2>&1 || true
          done
          stopped=true
        fi
        ;;
    esac
  fi

  if [[ "$stopped" == "true" ]]; then
    echo "Stopped service on port ${port}"
  else
    echo "No service found on port ${port}"
  fi
}

stop_services() {
  stop_port 8000

  local port
  for port in {5173..5185}; do
    stop_port "$port"
  done
}

detect_python_cmd() {
  local py_cmd="python"

  case "$(uname -s 2>/dev/null || echo "")" in
    MINGW*|MSYS*|CYGWIN*)
      if command -v py >/dev/null 2>&1; then
        if py -3.12 -V >/dev/null 2>&1; then
          py_cmd="py -3.12"
        fi
      fi
      ;;
  esac

  echo "$py_cmd"
}

ensure_supported_python() {
  local py_cmd="$1"
  local version
  version="$($py_cmd -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')")"

  case "$version" in
    3.13|3.14|3.15)
      cat <<'EOF'
Python 3.13+ detected. Some dependencies (e.g., Pillow) do not ship
prebuilt wheels yet, so backend installs can fail.

Fix options:
- Install Python 3.12 and re-run this script, or
- Use Docker: ./local.sh docker
EOF
      exit 1
      ;;
  esac
}

ensure_venv() {
  local py_cmd="$1"
  local venv_dir="$2"
  local expected_version="$3"

  if [[ -f "$venv_dir/pyvenv.cfg" ]]; then
    local current_version=""
    while IFS= read -r line; do
      case "$line" in
        "version = "*) current_version="${line#version = }" ;;
      esac
    done < "$venv_dir/pyvenv.cfg"

    if [[ -n "$current_version" ]]; then
      current_version="${current_version%.*}"
      if [[ "$current_version" != "$expected_version" ]]; then
        rm -rf "$venv_dir"
      fi
    fi
  fi
}

run_docker() {
  copy_env
  if command -v make >/dev/null 2>&1; then
    (cd "$ROOT_DIR" && make dev)
  else
    (cd "$ROOT_DIR" && docker-compose up --build -d)
  fi
}

run_backend() {
  copy_env

  if backend_running; then
    echo "Backend already running on http://localhost:8000"
    return 0
  fi

  local py_cmd
  py_cmd="$(detect_python_cmd)"
  ensure_supported_python "$py_cmd"
  local py_version
  py_version="$($py_cmd -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')")"
  local venv_dir="$ROOT_DIR/backend/venv-$py_version"
  ensure_venv "$py_cmd" "$venv_dir" "$py_version"

  local req_file="requirements.txt"
  case "$(uname -s 2>/dev/null || echo "")" in
    MINGW*|MSYS*|CYGWIN*)
      if [[ -f "$ROOT_DIR/backend/requirements-windows.txt" ]]; then
        req_file="requirements-windows.txt"
      fi
      ;;
  esac

  (cd "$ROOT_DIR/backend" && \
    $py_cmd -m venv "$venv_dir" && \
    source "$venv_dir/Scripts/activate" && \
    pip install -r "$req_file" && \
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000)
}

run_frontend() {
  if frontend_running; then
    echo "Frontend already running on http://localhost:${FRONTEND_PORT}"
    return 0
  fi

  (cd "$ROOT_DIR/frontend" && \
    npm install && \
    npm run dev)
}

run_local_full() {
  copy_env

  local backend_is_up=false
  local frontend_is_up=false
  if backend_running; then
    backend_is_up=true
  fi
  if frontend_running; then
    frontend_is_up=true
  fi

  if [[ "$backend_is_up" == "true" && "$frontend_is_up" == "true" ]]; then
    echo "Backend and frontend already running."
    echo "Backend: http://localhost:8000"
    echo "Frontend: http://localhost:${FRONTEND_PORT}"
    return 0
  fi

  if [[ "$backend_is_up" == "true" && "$frontend_is_up" == "false" ]]; then
    echo "Backend already running. Starting frontend..."
    run_frontend
    return 0
  fi

  if [[ "$backend_is_up" == "false" && "$frontend_is_up" == "true" ]]; then
    echo "Frontend already running. Starting backend..."
    run_backend
    return 0
  fi

  local py_cmd
  py_cmd="$(detect_python_cmd)"
  ensure_supported_python "$py_cmd"
  local py_version
  py_version="$($py_cmd -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')")"
  local venv_dir="$ROOT_DIR/backend/venv-$py_version"
  ensure_venv "$py_cmd" "$venv_dir" "$py_version"

  local req_file="requirements.txt"
  case "$(uname -s 2>/dev/null || echo "")" in
    MINGW*|MSYS*|CYGWIN*)
      if [[ -f "$ROOT_DIR/backend/requirements-windows.txt" ]]; then
        req_file="requirements-windows.txt"
      fi
      ;;
  esac

  (cd "$ROOT_DIR/backend" && \
    $py_cmd -m venv "$venv_dir" && \
    source "$venv_dir/Scripts/activate" && \
    pip install -r "$req_file" && \
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000) &
  BACKEND_PID=$!

  cleanup() {
    if [[ -n "${BACKEND_PID:-}" ]]; then
      kill "$BACKEND_PID" >/dev/null 2>&1 || true
    fi
  }
  trap cleanup EXIT INT TERM

  run_frontend
}

print_help() {
  cat <<'EOF'
Usage: ./local.sh [local|docker|backend|frontend|stop]

local     Run backend + frontend locally (default)
docker    Run full stack with Docker
backend   Run backend locally (venv + uvicorn)
frontend  Run frontend locally (vite)
stop      Stop backend and frontend services

Notes:
- Backend listens on http://localhost:8000
- Frontend dev server listens on http://localhost:5173
EOF
}

case "${1:-local}" in
  local)
    run_local_full
    ;;
  docker)
    run_docker
    ;;
  backend)
    run_backend
    ;;
  frontend)
    run_frontend
    ;;
  stop)
    stop_services
    ;;
  *)
    print_help
    exit 1
    ;;
esac
