from fastapi import FastAPI, UploadFile, WebSocket, WebSocketDisconnect, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import serial
import json
import os
import asyncio
import logging
from typing import List, Optional
from datetime import datetime
import re
from .image_processor import ImageHelper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
arduino = None
websocket_connections: List[WebSocket] = []
current_status = {
    "connected": False,
    "drawing": False,
    "progress": 0,
    "current_command": None,
    "last_update": None
}

# Initialize ImageHelper
image_helper = ImageHelper()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting PolarVortex API...")
    setup_arduino()
    yield
    # Shutdown
    logger.info("Shutting down PolarVortex API...")
    if arduino and arduino.is_open:
        arduino.close()

app = FastAPI(
    title="PolarVortex API",
    description="Backend API for Polargraph Plotter Control System",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Arduino connection setup
def setup_arduino():
    """Initialize Arduino connection"""
    global arduino
    try:
        # Try common Arduino ports
        ports = ['/dev/ttyUSB0', '/dev/ttyACM0', 'COM3', 'COM4', 'COM5', 'COM6']
        for port in ports:
            try:
                arduino = serial.Serial(port, 9600, timeout=1)
                logger.info(f"Arduino connected on {port}")
                current_status["connected"] = True
                return True
            except:
                continue
        logger.warning("No Arduino found on common ports")
        return False
    except Exception as e:
        logger.error(f"Arduino connection error: {e}")
        return False

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Image processing is now handled by ImageHelper class

# API Endpoints
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "PolarVortex API",
        "version": "1.0.0",
        "status": "running",
        "arduino_connected": current_status["connected"]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker"""
    try:
        # Basic health check
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "arduino_connected": current_status["connected"]
        }
        
        # Check if Arduino is responding (if connected)
        if arduino and arduino.is_open:
            try:
                arduino.write(b'PING\n')
                response = arduino.readline().decode().strip()
                health_status["arduino_response"] = response
            except Exception as e:
                health_status["arduino_response"] = f"error: {str(e)}"
        
        return health_status
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

@app.get("/status")
async def get_status():
    """Get current system status"""
    try:
        if arduino and arduino.is_open:
            arduino.write(b'STATUS\n')
            response = arduino.readline().decode().strip()
            current_status["last_update"] = datetime.now().isoformat()
            return {
                "status": response,
                "connected": True,
                "drawing": current_status["drawing"],
                "progress": current_status["progress"],
                "current_command": current_status["current_command"],
                "last_update": current_status["last_update"]
            }
        else:
            return {
                "status": "Arduino not connected",
                "connected": False,
                "drawing": False,
                "progress": 0,
                "current_command": None,
                "last_update": current_status["last_update"]
            }
    except Exception as e:
        logger.error(f"Status error: {e}")
        return {"error": str(e)}

@app.post("/command/{cmd}")
async def send_command(cmd: str):
    """Send command to Arduino"""
    try:
        if arduino and arduino.is_open:
            command = f"{cmd}\n".encode()
            arduino.write(command)
            
            # Update status
            current_status["current_command"] = cmd
            if cmd.upper() in ["START", "DRAW"]:
                current_status["drawing"] = True
                current_status["progress"] = 0
            elif cmd.upper() in ["STOP", "PAUSE"]:
                current_status["drawing"] = False
            
            # Broadcast status update
            await manager.broadcast(json.dumps({
                "type": "status_update",
                "command": cmd,
                "drawing": current_status["drawing"],
                "progress": current_status["progress"]
            }))
            
            return {"success": True, "command": cmd, "sent": True}
        else:
            return {"success": False, "error": "Arduino not connected"}
    except Exception as e:
        logger.error(f"Command error: {e}")
        return {"success": False, "error": str(e)}

@app.get("/check-directory/{directory_name}")
async def check_directory_exists(directory_name: str):
    """Check if a directory with the given name already exists"""
    try:
        # Sanitize the directory name
        sanitized_name = image_helper.sanitize_filename(directory_name)
        
        # Check if directory exists
        image_dir = os.path.join("local_storage", "images", sanitized_name)
        exists = os.path.exists(image_dir)
        
        return {
            "exists": exists,
            "directory_name": sanitized_name,
            "path": image_dir
        }
    except Exception as e:
        logger.error(f"Check directory error: {e}")
        return {"error": str(e)}

@app.post("/upload")
async def upload_image(
    file: UploadFile,
    settings: str = Form(default="{}"),
    directory_name: str = Form(default="")
):
    """Upload and process image for plotting"""
    try:
        # Read file content
        contents = await file.read()
        
        # Process upload using ImageHelper
        result = image_helper.process_upload(
            file_content=contents,
            file_content_type=file.content_type,
            file_size=len(contents),
            file_name=file.filename,
            settings_json=settings,
            directory_name=directory_name
        )
        
        # Broadcast new image available
        await manager.broadcast(json.dumps({
            "type": "image_processed",
            "filename": file.filename,
            "processed_size": result["processed_size"],
            "plotting_points": result["plotting_points"],
            "original_path": result["original_path"],
            "thumbnail_path": result["thumbnail_path"],
            "processed_path": result["processed_path"]
        }))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/images")
async def list_processed_images():
    """List all uploaded images with their directory structure"""
    try:
        return image_helper.list_processed_images()
    except Exception as e:
        logger.error(f"List images error: {e}")
        return {"error": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        # Send initial status
        await manager.send_personal_message(json.dumps({
            "type": "connection_established",
            "message": "Connected to PolarVortex"
        }), websocket)
        
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await manager.send_personal_message(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    }), websocket)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {data}")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)



# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
