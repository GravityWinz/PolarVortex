# PolarVortex Debugging Guide

This guide explains how to debug both the frontend and backend components of the PolarVortex application using VS Code and Docker.

## 🐛 Backend Python Debugging

### Prerequisites

- **VS Code extensions**: Python (ms-python.python), Python Debugger (ms-python.debugpy)
- Docker containers running
- Python debugpy package (already in requirements.txt)

### Configuration Status ✅

#### 1. Docker Configuration
- **Debug Port**: 5678 (exposed and mapped)
- **Debugpy**: Running with `--wait-for-client` flag
- **Frozen Modules**: Disabled with `-Xfrozen_modules=off`
- **Environment**: `PYDEVD_DISABLE_FILE_VALIDATION=1` set

#### 2. VS Code Configuration
- **Launch configurations**: e.g. `Attach to Backend (Python in Docker)` or `Debug FastAPI Backend (Docker)` for Docker; `Debug FastAPI Backend (Local)` for local runs
- **Path Mappings**: Local `backend/` → Container `/app`
- **Debug Port**: localhost:5678

### How to Debug Backend

#### Method 1: VS Code + Docker (Recommended)

1. **Start the containers:**
   ```bash
   docker-compose up -d
   ```

2. **Open VS Code in the project root:**
   ```bash
   code .
   ```

3. **Set breakpoints** in your Python files (e.g., `backend/app/main.py`)

4. **Start debugging:**
   - Press `F5` or go to Run and Debug panel
   - Select `Attach to Backend (Python in Docker)` (or `Debug FastAPI Backend (Docker)`)
   - Click the play button

5. **Trigger the code** by making an API request:
   ```bash
   curl http://localhost:8000/health
   ```

#### Method 2: Local Debugging (no Docker)

1. **Set up a local environment:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate   # macOS/Linux
   # or: venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

2. **Set breakpoints**, then press `F5` and select **Debug FastAPI Backend (Local)**. The app runs locally and will stop at breakpoints.

#### Method 3: Manual (attach + pdb)

1. **Attach to the running container:**
   ```bash
   docker-compose exec backend bash
   ```

2. **Check if debugpy is listening:**
   ```bash
   netstat -tlnp | grep 5678
   ```

3. **Use Python debugger in code:**
   ```python
   import pdb; pdb.set_trace()
   ```

### Debug Configuration Details

**.vscode/launch.json** typically includes:

**Docker attach:**
```json
{
    "name": "Debug FastAPI Backend (Docker)",
    "type": "python",
    "request": "attach",
    "connect": { "host": "localhost", "port": 5678 },
    "pathMappings": [
        { "localRoot": "${workspaceFolder}/backend", "remoteRoot": "/app" }
    ]
}
```

**Local run:**
```json
{
    "name": "Debug FastAPI Backend (Local)",
    "type": "python",
    "request": "launch",
    "program": "${workspaceFolder}/backend/app/main.py"
}
```

**Docker (backend):** `backend/Dockerfile.dev` runs debugpy, e.g.:
- `-Xfrozen_modules=off` for debugging
- `--listen 0.0.0.0:5678`, `--reload` for uvicorn

### Setting Effective Breakpoints

1. **API endpoints** – at the start of route handlers:
   ```python
   @app.get("/status")
   async def get_status():
       # Set breakpoint here
       try:
           # ...
   ```

2. **Error handling** – in exception handlers:
   ```python
   except Exception as e:
       # Set breakpoint here to catch errors
       logger.error(f"Error: {e}")
   ```

3. **Data processing** – before/after transformations:
   ```python
   def process_image_for_plotting(image_data: bytes, settings: dict) -> dict:
       # Set breakpoint here to inspect input
       image = Image.open(io.BytesIO(image_data))
       # Set breakpoint here to inspect processed image
   ```

### Debug Console (when paused)

In the Debug Console you can run:

```python
# Inspect variables
print(image_data)
print(settings)

# Check file paths
import os
print(os.path.exists("local_storage"))

# Test functions
result = process_image_for_plotting(image_data, settings)
print(result)
```

### Common Backend Debugging Scenarios

**File upload:** break in the upload endpoint and inspect `file`, `contents`, `file.content_type`.

**Directory creation:** break in `create_image_directory` and compare `image_name` vs `sanitize_filename(image_name)`.

**Image processing:** break in `process_image_for_plotting` and inspect `image.size`, `image.mode`, and intermediate results.

### Debugging Features Available

- ✅ Breakpoints, variable inspection, call stack
- ✅ Step into / over / out
- ✅ Hot reload on code changes
- ✅ Console output and logs

---

## 🎨 Frontend React Debugging

### Configuration Status ✅

- **Debug Port**: 9229 (exposed and mapped)
- **Node Inspector**: `--inspect=0.0.0.0:9229`
- **Launch**: e.g. `Attach to Frontend (Node.js in Docker)`, path mapping `frontend/` → `/app`

### How to Debug Frontend

1. **Start containers:** `docker-compose up -d`
2. **Set breakpoints** in React components
3. **Start debugging:** F5 → select `Attach to Frontend (Node.js in Docker)`
4. **Open** http://localhost:5173 and trigger the code with breakpoints

---

## 🔧 Full Stack Debugging

**Compound configuration:** Choose **Debug Full Stack (Docker)** to attach to both backend and frontend at once. Set breakpoints in Python and React and trigger flows from the UI or API.

---

## 🛠️ Troubleshooting

### Debugger won’t connect

- **Ports:** `curl -v telnet://localhost:5678` (backend), `telnet://localhost:9229` (frontend)
- **Container:** `docker-compose ps` and `docker-compose logs backend | grep debugpy`
- **Restart:** `docker-compose restart backend` (or `frontend`)

### Breakpoints not hitting

- Check **path mappings** (`localRoot` / `remoteRoot`)
- Attach **before** sending requests
- For Docker: ensure you’re editing the same files that are mounted in the container
- Optionally set `"justMyCode": false` in launch.json; use **conditional breakpoints** (right‑click breakpoint → Edit Breakpoint) to reduce noise

### Performance

- Use fewer breakpoints or conditional breakpoints
- Consider `"justMyCode": false` only when you need to step into libraries

### Container not starting

```bash
docker-compose logs backend
docker-compose logs frontend
docker-compose down && docker-compose up --build -d
```

### Frozen modules warning

- Handled by `-Xfrozen_modules=off` and `PYDEVD_DISABLE_FILE_VALIDATION=1` in the dev setup.

### Cursor Remote (SSH) install timeout

If Cursor reports “Failed to install server within the timeout”:

1. **Increase timeout** in settings, e.g. `"remote.SSH.serverInstallTimeout": 120` (or 300 on slow ARM boards).
2. **Check remote log:** `ls /run/user/<uid>/cursor-remote-code.log.*`
3. **Disk and permissions:** ensure `~/.cursor-server` is writable and there’s enough free space.
4. **Retry install:** `rm -rf ~/.cursor-server/bin` then reconnect.

---

## 📊 Debugging Tips

- **Backend:** Break in API handlers and async boundaries; use logging when you don’t want to stop.
- **Frontend:** Use React DevTools and Network tab; break in event handlers and state updates.
- **Resources:** `docker stats`; optionally profile with `time.time()` or a profiler.

---

## 📝 Debugging Checklist

- [ ] Containers running (`docker-compose ps`)
- [ ] Debug ports reachable (5678, 9229)
- [ ] VS Code extensions and launch configs set up
- [ ] Path mappings correct for Docker attach
- [ ] Breakpoints set; app reachable (http://localhost:8000, http://localhost:5173)

---

## 🎯 Quick Start

```bash
docker-compose up -d
docker-compose ps
curl http://localhost:8000/health
curl http://localhost:5173
# In VS Code: Run and Debug → Attach to Backend (Python in Docker) → F5
```

---

## 🔗 Useful Resources

- [VS Code Python Debugging](https://code.visualstudio.com/docs/python/debugging)
- [debugpy](https://github.com/microsoft/debugpy)
- [FastAPI Debugging](https://fastapi.tiangolo.com/tutorial/debugging/)
