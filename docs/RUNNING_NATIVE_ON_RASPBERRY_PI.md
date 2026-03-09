# Running PolarVortex Outside Docker on Raspberry Pi

This guide explains how to run the PolarVortex backend and frontend **natively** on a Raspberry Pi (no Docker). Use this if you prefer a direct install, easier debugging, or a lighter footprint.

## Overview

- **Backend**: Python 3.13 + FastAPI (uvicorn), under the repo’s `backend/` directory.
- **Frontend**: Node.js + Vite (dev server or built static files), under `frontend/`.
- **Data**: All dynamic files (config, projects, logs, uploads) go under a single storage directory. The app also expects a path at `/app/local_storage`; we use a symlink so that path points at your storage directory.

## Prerequisites

- Raspberry Pi OS (or similar Debian-based Linux) on your Pi.
- Python **3.13**.
- Node.js **18+** (for the frontend).
- Your plotter’s USB serial device (e.g. `/dev/ttyACM0` or `/dev/ttyUSB0`).

## 1. System packages (backend)

Install libraries required by the backend (Pillow, OpenCV, cairosvg, vpype):

```bash
sudo apt-get update
sudo apt-get install -y \
  python3.13 python3.13-venv python3-pip \
  libglib2.0-0 libgl1 libcairo2 libpango-1.0-0 \
  libpangocairo-1.0-0 libgdk-pixbuf-2.0-0
```

## 2. Serial port access

So the backend can talk to the plotter, add your user to the `dialout` group:

```bash
sudo usermod -aG dialout $USER
```

Log out and back in (or reboot) for the group change to apply.

## 3. Clone and storage layout

```bash
cd ~
git clone <your-repo-url> PolarVortex
cd PolarVortex
```

Create the local storage directory and the path the app expects by default:

```bash
mkdir -p backend/local_storage/config
mkdir -p backend/local_storage/log
mkdir -p backend/local_storage/tmp
mkdir -p backend/local_storage/projects

# So the app finds storage at /app/local_storage (used by config and vpype)
sudo mkdir -p /app
sudo ln -sf "$(pwd)/backend/local_storage" /app/local_storage
```

If you prefer not to use `/app/local_storage`, you can use a directory under your home instead and symlink that:

```bash
mkdir -p ~/polarvortex_data/config ~/polarvortex_data/log ~/polarvortex_data/tmp ~/polarvortex_data/projects
sudo ln -sf "$HOME/polarvortex_data" /app/local_storage
```

## 4. Backend

### 4.1 Virtual environment and dependencies

```bash
cd ~/PolarVortex/backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4.2 Environment variables

Create a `.env` (or export these in your shell). At minimum:

```bash
# Config file (use absolute path)
export PV_CONFIG="$HOME/PolarVortex/backend/local_storage/config/config.yaml"

# Serial: comma-separated list; use your device(s), e.g. /dev/ttyACM0 or /dev/ttyUSB0
export ARDUINO_PORTS="/dev/ttyACM0,/dev/ttyUSB0"

# Optional
export BACKEND_HOST=0.0.0.0
export BACKEND_PORT=8000
export LOG_LEVEL=INFO
```

Copy from the repo’s example and adjust:

```bash
cp ../env.example .env
# Edit .env: set PV_CONFIG, ARDUINO_PORTS, and CORS_ORIGINS if you use another host/port for the UI
```

Note: `env.example` uses `ARDUINO_DEVICE`; the backend actually reads **`ARDUINO_PORTS`** (comma-separated). Set `ARDUINO_PORTS` as above.

### 4.3 First run and config (storage paths)

On first run the backend creates `backend/local_storage/config/config.yaml` if it’s missing. That file defaults to `/app/local_storage` for storage. Because we symlinked `/app/local_storage` to `backend/local_storage`, that’s already correct.

If you used a different path (e.g. `~/polarvortex_data`), after the first run edit `config.yaml` and set:

- `storage.local_storage` → full path to that directory (e.g. `/home/pi/polarvortex_data`)
- `storage.project_storage` → `{local_storage}/projects`

### 4.4 Start the backend

From the repo root or from `backend/`:

```bash
cd ~/PolarVortex/backend
source .venv/bin/activate
export PV_CONFIG="$HOME/PolarVortex/backend/local_storage/config/config.yaml"
export ARDUINO_PORTS="/dev/ttyACM0,/dev/ttyUSB0"

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Leave this terminal running. The API will be at `http://<pi-ip>:8000`.

**One-command startup (both backend and frontend, keeps running after terminal closes):**

```bash
cd ~/PolarVortex
# Set ARDUINO_PORTS (and optionally PV_CONFIG) in backend/.env or export them first
chmod +x scripts/start_native.sh
./scripts/start_native.sh
```

This starts backend and frontend with `nohup` and writes PIDs and logs under `backend/local_storage/log/`. To stop: `kill $(cat backend/local_storage/log/backend.pid) $(cat backend/local_storage/log/frontend.pid)`.

## 5. Frontend

### Option A: Development server (recommended for daily use)

In a **second** terminal:

```bash
cd ~/PolarVortex/frontend
npm install
```

Point the frontend at the backend on this Pi (replace with your Pi’s IP if needed):

```bash
export VITE_API_BASE_URL=http://localhost:8000
export VITE_WS_BASE_URL=ws://localhost:8000
npm run dev
```

Then open `http://<pi-ip>:5173` in a browser (on the Pi or from another machine). If you open it from another machine, set CORS and VITE URLs to use the Pi’s IP, e.g.:

```bash
export VITE_API_BASE_URL=http://192.168.1.100:8000
export VITE_WS_BASE_URL=ws://192.168.1.100:8000
npm run dev
```

And in `backend/local_storage/config/config.yaml` (or via `CORS_ORIGINS` env), add that origin (e.g. `http://192.168.1.100:5173`).

### Option B: Production build and static serve

Build the frontend with the URLs where you’ll reach the backend:

```bash
cd ~/PolarVortex/frontend
export VITE_API_BASE_URL=http://192.168.1.100:8000
export VITE_WS_BASE_URL=ws://192.168.1.100:8000
npm run build
```

Serve the built files (one of these):

- **Python one-liner**:  
  `cd dist && python3 -m http.server 5173`
- **npx serve**:  
  `npx -y serve -s dist -l 5173`
- **nginx**: point a vhost at `frontend/dist`.

Then open `http://<pi-ip>:5173` (or the port you used).

## 6. Quick checklist

| Step | What to do |
|------|------------|
| System | Install Python 3.13 and Node 18+, and the backend system packages above. |
| Serial | Add your user to `dialout` and re-login. |
| Storage | Create `backend/local_storage` (or your chosen dir) and `sudo ln -s ... /app/local_storage`. |
| Backend env | Set `PV_CONFIG` and `ARDUINO_PORTS` (and optionally CORS). |
| Backend run | `cd backend && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000`. |
| Frontend | `cd frontend && npm install`, set `VITE_*` URLs, then `npm run dev` or `npm run build` + serve. |

## 7. Running as a service (optional)

To have the backend start on boot and run in the background, use systemd.

Example unit file: `/etc/systemd/system/polarvortex-backend.service`

```ini
[Unit]
Description=PolarVortex Backend
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/PolarVortex/backend
Environment="PATH=/home/pi/PolarVortex/backend/.venv/bin"
Environment="PV_CONFIG=/home/pi/PolarVortex/backend/local_storage/config/config.yaml"
Environment="ARDUINO_PORTS=/dev/ttyACM0,/dev/ttyUSB0"
ExecStart=/home/pi/PolarVortex/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Adjust `User`, paths, and `ARDUINO_PORTS` to match your setup. Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable polarvortex-backend
sudo systemctl start polarvortex-backend
sudo systemctl status polarvortex-backend
```

You can add a similar unit for the frontend dev server or for a static file server if you use a production build.

## 8. Troubleshooting

- **Backend can’t open serial port**: Ensure user is in `dialout`, device exists (`ls -la /dev/ttyACM0` or `/dev/ttyUSB0`), and `ARDUINO_PORTS` is set.
- **Config or storage errors**: Ensure `PV_CONFIG` points to an absolute path and that the config file’s `storage.local_storage` (and `storage.project_storage`) match your layout; `/app/local_storage` must be the symlink you created.
- **Permission denied when uploading** (e.g. G-code or images to a project): If you previously ran with Docker, project directories under storage may be owned by root. When running natively, the backend runs as your user and cannot write there. Fix ownership of the whole storage tree (use the path your symlink points to, or the path in `config.yaml` under `storage.local_storage` / `storage.project_storage`), for example:
  ```bash
  # If using backend/local_storage:
  sudo chown -R $USER:$USER /home/pi/PolarVortex/backend/local_storage

  # If using ~/polarvortex_data:
  sudo chown -R $USER:$USER ~/polarvortex_data
  ```
- **CORS errors in browser**: Add the exact origin (scheme + host + port) of the frontend to `config.yaml` under `cors.origins` or set `CORS_ORIGINS` in the backend environment.
- **Frontend can’t reach backend**: Use the Pi’s IP in `VITE_API_BASE_URL` and `VITE_WS_BASE_URL` when opening the UI from another machine, and ensure the backend is bound to `0.0.0.0:8000`.

For more on the app and Docker-based run, see the main [DOCKER_README.md](../DOCKER_README.md) and [DEBUGGING_GUIDE.md](../DEBUGGING_GUIDE.md).
