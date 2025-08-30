# Debugging Guide for PolarVortex

This guide covers how to set up and use debugging for the PolarVortex backend.

## 🐛 Debugging Setup

### Prerequisites

1. **VS Code Extensions**:
   - Python extension (ms-python.python)
   - Python Debugger extension (ms-python.debugpy)

2. **Docker Compose Running**:
   ```bash
   docker-compose up -d
   ```

### Method 1: Docker Debugging (Recommended)

This method allows you to debug the FastAPI application running inside the Docker container.

#### Step 1: Start the Backend Container
```bash
docker-compose up -d backend
```

#### Step 2: Verify Debug Port is Exposed
Check that port 5678 is exposed in `docker-compose.yml`:
```yaml
ports:
  - "8000:8000"
  - "5678:5678"  # Debug port
```

#### Step 3: Set Breakpoints
1. Open `backend/app/main.py` in VS Code
2. Click in the left margin next to line numbers to set breakpoints
3. Breakpoints will appear as red dots

#### Step 4: Start Debugging
1. Press `F5` or go to Run → Start Debugging
2. Select "Debug FastAPI Backend (Docker)" from the dropdown
3. VS Code will connect to the debugger running in the container

#### Step 5: Trigger Breakpoints
1. Make an API request to trigger your breakpoint:
   ```bash
   curl http://localhost:8000/status
   ```
2. The debugger will pause execution at your breakpoint
3. Use the debug toolbar to step through code

### Method 2: Local Debugging

This method runs the FastAPI application locally for debugging.

#### Step 1: Set Up Local Environment
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# or source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

#### Step 2: Start Local Debugging
1. Set breakpoints in your code
2. Press `F5` and select "Debug FastAPI Backend (Local)"
3. The application will start locally and break at your breakpoints

## 🔧 Debug Configuration Details

### VS Code Launch Configuration

The `.vscode/launch.json` file contains two debug configurations:

#### Docker Configuration
```json
{
    "name": "Debug FastAPI Backend (Docker)",
    "type": "python",
    "request": "attach",
    "connect": {
        "host": "localhost",
        "port": 5678
    },
    "pathMappings": [
        {
            "localRoot": "${workspaceFolder}/backend",
            "remoteRoot": "/app"
        }
    ]
}
```

**Key Points**:
- `"request": "attach"` - Connects to existing debugger
- `"port": 5678` - Matches the debug port in Docker
- `"pathMappings"` - Maps local files to container paths

#### Local Configuration
```json
{
    "name": "Debug FastAPI Backend (Local)",
    "type": "python",
    "request": "launch",
    "program": "${workspaceFolder}/backend/app/main.py"
}
```

### Docker Debug Configuration

The `backend/Dockerfile.dev` runs debugpy:
```dockerfile
CMD ["python", "-Xfrozen_modules=off", "-m", "debugpy", "--listen", "0.0.0.0:5678", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

**Key Components**:
- `-Xfrozen_modules=off` - Disables frozen modules for debugging
- `debugpy` - Python debugger
- `--listen 0.0.0.0:5678` - Listens on all interfaces, port 5678
- `--reload` - Enables auto-reload for development

## 🎯 Debugging Tips

### Setting Effective Breakpoints

1. **API Endpoints**: Set breakpoints at the start of endpoint functions
   ```python
   @app.get("/status")
   async def get_status():
       # Set breakpoint here
       try:
           # Your code here
   ```

2. **Error Handling**: Set breakpoints in exception handlers
   ```python
   except Exception as e:
       # Set breakpoint here to catch errors
       logger.error(f"Error: {e}")
   ```

3. **Data Processing**: Set breakpoints before/after data transformations
   ```python
   def process_image_for_plotting(image_data: bytes, settings: dict) -> dict:
       # Set breakpoint here to inspect input
       try:
           image = Image.open(io.BytesIO(image_data))
           # Set breakpoint here to inspect processed image
   ```

### Debug Console Commands

When paused at a breakpoint, use the Debug Console:

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

### Common Debugging Scenarios

#### 1. File Upload Issues
```python
# Set breakpoint in upload endpoint
@app.post("/upload")
async def upload_image(file: UploadFile, settings: str = Form(default="{}")):
    # Breakpoint here
    contents = await file.read()
    # Check file contents
    print(f"File size: {len(contents)}")
    print(f"File type: {file.content_type}")
```

#### 2. Directory Creation Issues
```python
def create_image_directory(image_name: str) -> str:
    # Breakpoint here
    sanitized_name = sanitize_filename(image_name)
    # Check sanitized name
    print(f"Original: {image_name}")
    print(f"Sanitized: {sanitized_name}")
```

#### 3. Image Processing Issues
```python
def process_image_for_plotting(image_data: bytes, settings: dict) -> dict:
    # Breakpoint here
    image = Image.open(io.BytesIO(image_data))
    # Check image properties
    print(f"Image size: {image.size}")
    print(f"Image mode: {image.mode}")
```

## 🚨 Troubleshooting

### Debugger Won't Connect

1. **Check Container Status**:
   ```bash
   docker-compose ps
   ```

2. **Check Debug Port**:
   ```bash
   docker-compose logs backend | grep debugpy
   ```

3. **Restart Container**:
   ```bash
   docker-compose restart backend
   ```

### Breakpoints Not Hit

1. **Check Path Mappings**: Ensure `localRoot` and `remoteRoot` are correct
2. **Verify File Changes**: Make sure you're editing the correct file
3. **Check Container Restart**: Changes require container restart

### Performance Issues

1. **Disable Just My Code**: Set `"justMyCode": false` in launch.json
2. **Limit Breakpoints**: Too many breakpoints can slow down execution
3. **Use Conditional Breakpoints**: Right-click breakpoint → Edit Breakpoint

## 📋 Debug Checklist

Before starting debugging:

- [ ] VS Code Python extension installed
- [ ] Docker container running with debug port exposed
- [ ] Breakpoints set in correct locations
- [ ] Path mappings configured correctly
- [ ] Debug configuration selected

## 🔗 Useful Resources

- [VS Code Python Debugging](https://code.visualstudio.com/docs/python/debugging)
- [debugpy Documentation](https://github.com/microsoft/debugpy)
- [FastAPI Debugging](https://fastapi.tiangolo.com/tutorial/debugging/)
