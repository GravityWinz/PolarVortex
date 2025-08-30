# PolarVortex Debugging Guide

This guide explains how to debug both the frontend and backend components of the PolarVortex application using VS Code and Docker.

## 🐛 Backend Python Debugging

### Prerequisites
- VS Code with Python extension installed
- Docker containers running
- Python debugpy package installed (already included in requirements.txt)

### Configuration Status ✅

#### 1. Docker Configuration
- **Debug Port**: 5678 (exposed and mapped)
- **Debugpy**: Running with `--wait-for-client` flag
- **Frozen Modules**: Disabled with `-Xfrozen_modules=off`
- **Environment**: `PYDEVD_DISABLE_FILE_VALIDATION=1` set

#### 2. VS Code Configuration
- **Launch Configuration**: `Attach to Backend (Python in Docker)`
- **Path Mappings**: Local `backend/` → Container `/app`
- **Debug Port**: localhost:5678

### How to Debug Backend

#### Method 1: VS Code Debugger (Recommended)

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
   - Select `Attach to Backend (Python in Docker)`
   - Click the play button

5. **Trigger the code** by making an API request:
   ```bash
   curl http://localhost:8000/health
   ```

#### Method 2: Manual Debugging

1. **Attach to the running container:**
   ```bash
   docker-compose exec backend bash
   ```

2. **Check if debugpy is listening:**
   ```bash
   netstat -tlnp | grep 5678
   ```

3. **Use Python debugger directly:**
   ```python
   import pdb; pdb.set_trace()
   ```

### Debugging Features Available

- ✅ **Breakpoints**: Set and hit breakpoints in VS Code
- ✅ **Variable Inspection**: View local and global variables
- ✅ **Call Stack**: Navigate through function calls
- ✅ **Step Through**: Step into, over, and out of functions
- ✅ **Hot Reload**: Code changes trigger automatic reload
- ✅ **Console Output**: View print statements and logs

## 🎨 Frontend React Debugging

### Configuration Status ✅

#### 1. Docker Configuration
- **Debug Port**: 9229 (exposed and mapped)
- **Node Inspector**: Running with `--inspect=0.0.0.0:9229`
- **Hot Reload**: Vite development server with hot reload

#### 2. VS Code Configuration
- **Launch Configuration**: `Attach to Frontend (Node.js in Docker)`
- **Path Mappings**: Local `frontend/` → Container `/app`
- **Debug Port**: localhost:9229

### How to Debug Frontend

1. **Start the containers:**
   ```bash
   docker-compose up -d
   ```

2. **Open VS Code and set breakpoints** in your React components

3. **Start debugging:**
   - Press `F5` or go to Run and Debug panel
   - Select `Attach to Frontend (Node.js in Docker)`
   - Click the play button

4. **Open the application** in your browser:
   - Navigate to http://localhost:5173
   - Trigger the code with breakpoints

## 🔧 Full Stack Debugging

### Compound Debugging
VS Code supports debugging both frontend and backend simultaneously:

1. **Select compound configuration:**
   - Choose `Debug Full Stack (Docker)` from the debug dropdown

2. **Start debugging:**
   - This will attach to both containers simultaneously
   - Set breakpoints in both Python and JavaScript/React code

## 🛠️ Troubleshooting

### Common Issues

#### 1. Debugger Won't Connect
```bash
# Check if debug ports are accessible
curl -v telnet://localhost:5678  # Backend
curl -v telnet://localhost:9229  # Frontend
```

#### 2. Breakpoints Not Hitting
- Ensure path mappings are correct
- Check that files are being watched for changes
- Verify the debugger is attached before making requests

#### 3. Container Not Starting
```bash
# Check container logs
docker-compose logs backend
docker-compose logs frontend

# Rebuild containers
docker-compose down
docker-compose up --build -d
```

#### 4. Frozen Modules Warning
- This is now fixed with `-Xfrozen_modules=off` flag
- Environment variable `PYDEVD_DISABLE_FILE_VALIDATION=1` is set

### Debug Commands

#### Container Management
```bash
# Start debugging environment
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Restart specific service
docker-compose restart backend
docker-compose restart frontend

# Rebuild and restart
docker-compose up --build -d
```

#### Health Checks
```bash
# Test backend health
curl http://localhost:8000/health

# Test frontend
curl http://localhost:5173

# Test debug ports
netstat -an | grep 5678  # Backend debug
netstat -an | grep 9229  # Frontend debug
```

## 📊 Debugging Tips

### Backend Debugging
1. **Set breakpoints** in API endpoints before making requests
2. **Use logging** for debugging without stopping execution
3. **Inspect variables** in the debug console
4. **Step through async code** carefully

### Frontend Debugging
1. **Set breakpoints** in React components and event handlers
2. **Use React DevTools** browser extension for component inspection
3. **Check network requests** in browser DevTools
4. **Debug state changes** with Redux DevTools (if using Redux)

### Performance Debugging
1. **Monitor container resources:**
   ```bash
   docker stats
   ```

2. **Check memory usage:**
   ```bash
   docker-compose exec backend python -c "import psutil; print(psutil.virtual_memory())"
   ```

3. **Profile API endpoints:**
   ```python
   import time
   start_time = time.time()
   # Your code here
   print(f"Execution time: {time.time() - start_time}")
   ```

## 🔍 Advanced Debugging

### Remote Debugging
If you need to debug from a different machine:

1. **Update launch.json** with the correct host IP
2. **Ensure firewall allows** debug ports (5678, 9229)
3. **Use SSH tunneling** if needed

### Production Debugging
For debugging production issues:

1. **Enable debug mode** in production environment
2. **Add logging** to track issues
3. **Use health checks** to monitor service status
4. **Set up monitoring** with tools like Prometheus/Grafana

## 📝 Debugging Checklist

Before starting debugging:

- [ ] Containers are running (`docker-compose ps`)
- [ ] Debug ports are accessible (5678, 9229)
- [ ] VS Code extensions are installed
- [ ] Launch configurations are set up
- [ ] Path mappings are correct
- [ ] Breakpoints are set
- [ ] Application is accessible (http://localhost:8000, http://localhost:5173)

## 🎯 Quick Start Commands

```bash
# Start debugging environment
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:5173

# Attach debugger in VS Code
# 1. Open Run and Debug panel
# 2. Select "Attach to Backend (Python in Docker)"
# 3. Press F5
```

Your debugging setup is now fully configured and ready to use! 🚀

