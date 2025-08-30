from fastapi import FastAPI, UploadFile, WebSocket, WebSocketDisconnect, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import serial
import json
import os
import asyncio
import logging
from typing import List, Optional
from datetime import datetime
import cv2
import numpy as np
from PIL import Image
import io
import base64
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PolarVortex API",
    description="Backend API for Polargraph Plotter Control System",
    version="1.0.0"
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

# Image processing functions
def sanitize_filename(filename: str) -> str:
    """Sanitize filename for use as directory name"""
    # Remove file extension and replace invalid characters
    name_without_ext = os.path.splitext(filename)[0]
    # Replace invalid characters with underscore
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name_without_ext)
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    # Ensure it's not empty
    if not sanitized:
        sanitized = "unnamed_image"
    return sanitized

def create_image_directory(image_name: str) -> str:
    """Create directory structure for uploaded image"""
    # Sanitize the image name for directory creation
    sanitized_name = sanitize_filename(image_name)
    
    # Create the directory path
    image_dir = os.path.join("local_storage", "images", sanitized_name)
    os.makedirs(image_dir, exist_ok=True)
    
    return image_dir

def save_original_image(image_data: bytes, image_name: str, image_dir: str) -> str:
    """Save original image to the image directory"""
    original_path = os.path.join(image_dir, image_name)
    with open(original_path, "wb") as f:
        f.write(image_data)
    return original_path

def create_thumbnail(image_data: bytes, image_dir: str, image_name: str) -> str:
    """Create and save thumbnail of the image"""
    try:
        # Open image from bytes
        image = Image.open(io.BytesIO(image_data))
        
        # Create thumbnail (max 200x200, maintaining aspect ratio)
        image.thumbnail((200, 200), Image.Resampling.LANCZOS)
        
        # Generate thumbnail filename
        name_without_ext = os.path.splitext(image_name)[0]
        thumb_filename = f"thumb_{name_without_ext}.png"
        thumb_path = os.path.join(image_dir, thumb_filename)
        
        # Save thumbnail
        image.save(thumb_path, "PNG")
        
        return thumb_path
    except Exception as e:
        logger.error(f"Thumbnail creation error: {e}")
        return None

def process_image_for_plotting(image_data: bytes, settings: dict) -> dict:
    """Process uploaded image for polargraph plotting"""
    try:
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Resize based on settings
        resolution_map = {
            "low": (400, 300),
            "medium": (800, 600),
            "high": (1200, 900),
            "custom": (settings.get("maxWidth", 800), settings.get("maxHeight", 600))
        }
        
        target_size = resolution_map.get(settings.get("resolution", "medium"))
        image = image.resize(target_size, Image.Resampling.LANCZOS)
        
        # Convert to numpy array for OpenCV processing
        img_array = np.array(image)
        
        # Apply threshold
        threshold = settings.get("threshold", 128)
        _, binary = cv2.threshold(img_array, threshold, 255, cv2.THRESH_BINARY)
        
        # Invert if requested
        if settings.get("invert", False):
            binary = cv2.bitwise_not(binary)
        
        # Apply dithering if requested
        if settings.get("dither", True):
            binary = apply_floyd_steinberg_dithering(img_array)
        
        # Convert back to PIL Image
        processed_image = Image.fromarray(binary)
        
        # Save processed image in the image directory (this will be passed from the upload function)
        # For now, we'll save it in a temporary location and the upload function will move it
        output_path = f"temp_processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        processed_image.save(output_path)
        
        # Convert to base64 for preview
        buffer = io.BytesIO()
        processed_image.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            "success": True,
            "original_size": image.size,
            "processed_size": processed_image.size,
            "output_path": output_path,
            "preview": f"data:image/png;base64,{img_base64}",
            "plotting_data": convert_to_plotting_data(binary)
        }
        
    except Exception as e:
        logger.error(f"Image processing error: {e}")
        return {"success": False, "error": str(e)}

def apply_floyd_steinberg_dithering(image):
    """Apply Floyd-Steinberg dithering to image"""
    img = image.astype(float)
    height, width = img.shape
    
    for y in range(height):
        for x in range(width):
            old_pixel = img[y, x]
            new_pixel = 255 if old_pixel > 127 else 0
            img[y, x] = new_pixel
            
            error = old_pixel - new_pixel
            
            if x + 1 < width:
                img[y, x + 1] += error * 7 / 16
            if x - 1 >= 0 and y + 1 < height:
                img[y + 1, x - 1] += error * 3 / 16
            if y + 1 < height:
                img[y + 1, x] += error * 5 / 16
            if x + 1 < width and y + 1 < height:
                img[y + 1, x + 1] += error * 1 / 16
    
    return img.astype(np.uint8)

def convert_to_plotting_data(binary_image):
    """Convert binary image to plotting coordinates"""
    height, width = binary_image.shape
    plotting_points = []
    
    for y in range(height):
        for x in range(width):
            if binary_image[y, x] == 0:  # Black pixel
                # Convert to plotter coordinates
                plot_x = (x / width) * 100  # Scale to 0-100
                plot_y = (y / height) * 100
                plotting_points.append((plot_x, plot_y))
    
    return plotting_points

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
        sanitized_name = sanitize_filename(directory_name)
        
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
        # Validate file
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read file content
        contents = await file.read()
        if len(contents) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")
        
        # Parse settings
        try:
            processing_settings = json.loads(settings)
        except json.JSONDecodeError:
            processing_settings = {}
        
        # Create image directory
        image_name = file.filename
        # Use provided directory name if available, otherwise use filename
        dir_name = directory_name.strip() if directory_name.strip() else image_name
        image_dir = create_image_directory(dir_name)
        
        # Save original image
        original_path = save_original_image(contents, image_name, image_dir)
        
        # Create thumbnail
        thumb_path = create_thumbnail(contents, image_dir, image_name)
        
        # Process image
        result = process_image_for_plotting(contents, processing_settings)
        
        # Move processed image to the image directory if processing was successful
        processed_path = None
        if result["success"] and "output_path" in result:
            # Move the temporary processed image to the image directory
            temp_path = result["output_path"]
            if os.path.exists(temp_path):
                name_without_ext = os.path.splitext(image_name)[0]
                processed_filename = f"processed_{name_without_ext}.png"
                processed_path = os.path.join(image_dir, processed_filename)
                os.rename(temp_path, processed_path)
                result["output_path"] = processed_path
        
        if result["success"]:
            # Broadcast new image available
            await manager.broadcast(json.dumps({
                "type": "image_processed",
                "filename": file.filename,
                "processed_size": result["processed_size"],
                "plotting_points": len(result["plotting_data"]),
                "original_path": original_path,
                "thumbnail_path": thumb_path,
                "processed_path": processed_path
            }))
            
            return {
                "success": True,
                "filename": file.filename,
                "original_size": result["original_size"],
                "processed_size": result["processed_size"],
                "plotting_points": len(result["plotting_data"]),
                "preview": result["preview"],
                "original_path": original_path,
                "thumbnail_path": thumb_path,
                "processed_path": processed_path,
                "image_directory": image_dir
            }
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/images")
async def list_processed_images():
    """List all uploaded images with their directory structure"""
    try:
        images_dir = os.path.join("local_storage", "images")
        if not os.path.exists(images_dir):
            return {"images": []}
        
        images = []
        for image_dir_name in os.listdir(images_dir):
            image_dir_path = os.path.join(images_dir, image_dir_name)
            if os.path.isdir(image_dir_path):
                # Get original image file
                original_files = [f for f in os.listdir(image_dir_path) 
                                if not f.startswith('thumb_') and not f.startswith('processed_')]
                
                if original_files:
                    original_file = original_files[0]  # Take the first non-thumbnail file
                    original_path = os.path.join(image_dir_path, original_file)
                    file_stat = os.stat(original_path)
                    
                    # Check for thumbnail and processed versions
                    thumb_file = f"thumb_{os.path.splitext(original_file)[0]}.png"
                    processed_file = f"processed_{os.path.splitext(original_file)[0]}.png"
                    
                    thumb_path = os.path.join(image_dir_path, thumb_file)
                    processed_path = os.path.join(image_dir_path, processed_file)
                    
                    images.append({
                        "name": image_dir_name,
                        "original_filename": original_file,
                        "original_path": original_path,
                        "thumbnail_path": thumb_path if os.path.exists(thumb_path) else None,
                        "processed_path": processed_path if os.path.exists(processed_path) else None,
                        "size": file_stat.st_size,
                        "created": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                        "has_thumbnail": os.path.exists(thumb_path),
                        "has_processed": os.path.exists(processed_path)
                    })
        
        return {"images": images}
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

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize Arduino connection on startup"""
    logger.info("Starting PolarVortex API...")
    setup_arduino()

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    logger.info("Shutting down PolarVortex API...")
    if arduino and arduino.is_open:
        arduino.close()

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
