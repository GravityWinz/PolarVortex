# Docker Hot Reload Guide

## When You DON'T Need to Restart

Your setup is configured for **hot reload** - code changes should automatically refresh:

### ✅ Auto-Reloads (No Restart Needed)

1. **Frontend Code Changes** (`.jsx`, `.js`, `.css`, etc.)
   - Vite HMR automatically updates the browser
   - Changes appear instantly

2. **Backend Code Changes** (`.py` files)
   - Uvicorn `--reload` flag watches for changes
   - Server restarts automatically when Python files change

### ⚠️ Requires Restart

1. **docker-compose.yml changes**
   - Device mappings (`devices:` section)
   - Port mappings
   - Environment variables
   - Volume mounts
   - Network changes

2. **Dockerfile changes**
   - Requires rebuild: `docker-compose build`
   - Then restart: `docker-compose up`

3. **Dependency Changes**
   - `package.json` changes → rebuild frontend
   - `requirements.txt` changes → rebuild backend

4. **Environment Variable Changes**
   - Changes in `env.example` or `environment:` section
   - Requires restart to pick up new values

## Troubleshooting Hot Reload

If code changes aren't auto-reloading:

### For Frontend:

1. **Check browser console** - Look for HMR connection errors
2. **Hard refresh** - Press `Ctrl+Shift+R` (or `Cmd+Shift+R` on Mac)
3. **Check Vite logs** - Look in Docker logs: `docker-compose logs frontend`
4. **Verify file watching** - The config uses polling mode for better Docker compatibility

### For Backend:

1. **Check uvicorn logs** - Look for reload messages: `docker-compose logs backend`
2. **Verify file changes detected** - You should see: `Detected file change in 'app/main.py'. Reloading...`
3. **Check file permissions** - Ensure files are readable

### Common Issues:

**Windows/WSL2 File Watching:**
- The config uses polling mode (`CHOKIDAR_USEPOLLING=true`) which is slower but more reliable
- If still not working, try: `docker-compose restart frontend backend`

**File System Events Not Working:**
- Some file systems (especially network mounts) don't support inotify
- Polling mode is enabled as fallback

**Port Already in Use:**
- If you see port conflicts, stop other services using those ports
- Or change ports in docker-compose.yml

## Quick Commands

```bash
# Start with hot-reload (code changes auto-reload)
docker-compose up

# Restart services (for config changes)
docker-compose restart

# Rebuild and restart (for Dockerfile/dependency changes)
docker-compose build
docker-compose up

# View logs to verify hot-reload is working
docker-compose logs -f backend
docker-compose logs -f frontend

# Restart just one service
docker-compose restart backend
docker-compose restart frontend
```

## Verification

To verify hot-reload is working:

1. **Frontend Test:**
   - Make a small change to `frontend/src/components/ControlPanel.jsx`
   - Save the file
   - Browser should update automatically (check browser console for HMR message)

2. **Backend Test:**
   - Make a small change to `backend/app/main.py`
   - Save the file
   - Check logs: `docker-compose logs backend | tail`
   - Should see: `Detected file change... Reloading...`

## Performance Note

Polling mode (used for better Docker compatibility) uses slightly more CPU than native file watching, but ensures reliable hot-reload across all platforms.



