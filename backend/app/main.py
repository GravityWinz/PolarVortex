from fastapi import FastAPI, UploadFile, WebSocket, WebSocketDisconnect, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
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
from .config import Config
from .project_models import ProjectCreate, ProjectResponse, ProjectListResponse
from .project_service import project_service
from .vectorizer import PolargraphVectorizer, VectorizationSettings
from .config_models import (
    PlotterCreate, PlotterUpdate, PlotterResponse, PlotterListResponse,
    PaperCreate, PaperUpdate, PaperResponse, PaperListResponse,
    ConfigurationResponse
)
from .config_service import config_service

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

@app.get("/projects/{project_id}/images")
async def get_project_images(project_id: str):
    """Get all images associated with a specific project"""
    try:
        # Verify project exists
        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get images from image helper
        result = image_helper.get_project_images(project_id)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get project images error: {e}")
        return {"error": str(e)}

@app.get("/projects/{project_id}/thumbnail")
async def get_project_thumbnail(project_id: str):
    """Get the thumbnail image for a specific project"""
    try:
        # Verify project exists
        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if project has a thumbnail
        if not project.thumbnail_image:
            raise HTTPException(status_code=404, detail="No thumbnail available for this project")
        
        # Get the project directory and construct thumbnail path
        project_dir = project_service._get_project_directory(project_id)
        thumbnail_path = project_dir / project.thumbnail_image
        
        # Check if thumbnail file exists
        if not thumbnail_path.exists():
            logger.warning(f"Thumbnail file not found: {thumbnail_path}")
            raise HTTPException(status_code=404, detail="Thumbnail file not found")
        
        # Return the image file
        return FileResponse(
            path=str(thumbnail_path),
            media_type="image/png",
            filename=project.thumbnail_image
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get project thumbnail error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/projects/{project_id}/images/{filename}")
async def get_project_image(project_id: str, filename: str):
    """Get a specific image file from a project"""
    try:
        # Verify project exists
        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get the project directory and construct image path
        project_dir = project_service._get_project_directory(project_id)
        image_path = project_dir / filename
        
        # Check if image file exists
        if not image_path.exists():
            logger.warning(f"Image file not found: {image_path}")
            raise HTTPException(status_code=404, detail="Image file not found")
        
        # Determine media type based on file extension
        file_extension = filename.lower().split('.')[-1]
        media_type_map = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'bmp': 'image/bmp'
        }
        media_type = media_type_map.get(file_extension, 'application/octet-stream')
        
        # Return the image file
        return FileResponse(
            path=str(image_path),
            media_type=media_type,
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get project image error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/projects/{project_id}/image_upload")
async def upload_image_to_project(
    project_id: str,
    file: UploadFile,
    settings: str = Form(default="{}")
):
    """Upload and process image for a specific project"""
    try:
        # Verify project exists
        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Read file content
        contents = await file.read()
        
        # Process upload using ImageHelper with project_id
        result = image_helper.process_upload(
            file_content=contents,
            file_content_type=file.content_type,
            file_size=len(contents),
            file_name=file.filename,
            settings_json=settings,
            project_id=project_id
        )
        
        # Update project with thumbnail and source image information if upload was successful
        if result.get("success"):
            # Extract just the filename from the thumbnail path
            if result.get("thumbnail_path"):
                thumbnail_filename = os.path.basename(result["thumbnail_path"])
                project_service.update_project_thumbnail(project_id, thumbnail_filename)
            
            # Update source image filename
            if result.get("filename"):
                project_service.update_project_source_image(project_id, result["filename"])
        
        # Broadcast new image available for this project
        await manager.broadcast(json.dumps({
            "type": "image_uploaded",
            "project_id": project_id,
            "project_name": project.name,
            "filename": file.filename,
            "original_size": result["original_size"],
            "original_path": result["original_path"],
            "thumbnail_path": result["thumbnail_path"]
        }))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Project Management Endpoints
@app.post("/projects", response_model=ProjectResponse)
async def create_project(project_data: ProjectCreate):
    """Create a new project"""
    try:
        project = project_service.create_project(project_data)
        
        # Broadcast project creation
        await manager.broadcast(json.dumps({
            "type": "project_created",
            "project_id": project.id,
            "project_name": project.name
        }))
        
        return project
        
    except Exception as e:
        logger.error(f"Create project error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects", response_model=ProjectListResponse)
async def list_projects():
    """List all projects"""
    try:
        projects = project_service.list_projects()
        return ProjectListResponse(projects=projects, total=len(projects))
        
    except Exception as e:
        logger.error(f"List projects error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get a project by ID"""
    try:
        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get project error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project by ID"""
    try:
        success = project_service.delete_project(project_id)
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Broadcast project deletion
        await manager.broadcast(json.dumps({
            "type": "project_deleted",
            "project_id": project_id
        }))
        
        return {"success": True, "message": f"Project {project_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete project error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/projects/{project_id}/vectorize")
async def vectorize_project_image(project_id: str, 
                                 blur_radius: int = 1,
                                 posterize_levels: int = 5,
                                 simplification_threshold: float = 2.0,
                                 min_contour_area: int = 10,
                                 color_tolerance: int = 10,
                                 enable_color_separation: bool = True,
                                 enable_contour_simplification: bool = True,
                                 enable_noise_reduction: bool = True):
    """Vectorize the source image of a project"""
    try:
        # Verify project exists
        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if project has a source image
        if not project.source_image:
            raise HTTPException(status_code=400, detail="Project has no source image to vectorize")
        
        # Get project directory
        project_dir = image_helper.get_project_directory(project_id)
        source_image_path = project_dir / project.source_image
        
        # Check if source image file exists
        if not source_image_path.exists():
            raise HTTPException(status_code=404, detail="Source image file not found")
        
        # Read the source image
        with open(source_image_path, 'rb') as f:
            image_data = f.read()
        
        # Create vectorization settings
        settings = VectorizationSettings(
            blur_radius=blur_radius,
            posterize_levels=posterize_levels,
            simplification_threshold=simplification_threshold,
            min_contour_area=min_contour_area,
            color_tolerance=color_tolerance,
            enable_color_separation=enable_color_separation,
            enable_contour_simplification=enable_contour_simplification,
            enable_noise_reduction=enable_noise_reduction
        )
        
        # Initialize vectorizer
        vectorizer = PolargraphVectorizer()
        
        # Vectorize the image with SVG creation in project directory
        result = vectorizer.vectorize_image(image_data, settings, str(project_dir))
        
        # Generate plotting commands
        machine_settings = {
            "width": 1000,
            "height": 1000,
            "mm_per_rev": 95.0,
            "steps_per_rev": 200.0
        }
        plotting_commands = vectorizer.export_to_plotting_commands(result, machine_settings)
        
        # Generate preview
        preview = vectorizer.get_vectorization_preview(result)
        
        # Broadcast vectorization completion
        await manager.broadcast(json.dumps({
            "type": "image_vectorized",
            "project_id": project_id,
            "project_name": project.name,
            "total_paths": result.total_paths,
            "colors_detected": result.colors_detected,
            "processing_time": result.processing_time,
            "svg_path": result.svg_path
        }))
        
        return {
            "success": True,
            "project_id": project_id,
            "source_image": project.source_image,
            "vectorization_result": {
                "total_paths": result.total_paths,
                "colors_detected": result.colors_detected,
                "processing_time": result.processing_time,
                "original_size": result.original_size,
                "processed_size": result.processed_size
            },
            "svg_path": result.svg_path,
            "plotting_commands": plotting_commands,
            "preview": preview,
            "settings_used": {
                "blur_radius": settings.blur_radius,
                "posterize_levels": settings.posterize_levels,
                "simplification_threshold": settings.simplification_threshold,
                "min_contour_area": settings.min_contour_area,
                "color_tolerance": settings.color_tolerance,
                "enable_color_separation": settings.enable_color_separation,
                "enable_contour_simplification": settings.enable_contour_simplification,
                "enable_noise_reduction": settings.enable_noise_reduction
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vectorization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects/{project_id}/vectorize/export-svg")
async def export_project_vectorization_svg(project_id: str):
    """Export the vectorization SVG for a specific project"""
    try:
        # Verify project exists
        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get project directory
        project_dir = image_helper.get_project_directory(project_id)
        
        # Look for SVG files in the project directory
        svg_files = list(project_dir.glob("*.svg"))
        
        if not svg_files:
            raise HTTPException(status_code=404, detail="No vectorization SVG found for this project")
        
        # Get the most recent SVG file
        latest_svg = max(svg_files, key=lambda f: f.stat().st_mtime)
        
        # Return the SVG file
        return FileResponse(
            path=str(latest_svg),
            media_type="image/svg+xml",
            filename=latest_svg.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export SVG error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects/{project_id}/vectorize/commands")
async def get_project_vectorization_commands(project_id: str, 
                                           width: int = 1000,
                                           height: int = 1000,
                                           mm_per_rev: float = 95.0,
                                           steps_per_rev: float = 200.0):
    """Get plotting commands for the vectorization of a specific project"""
    try:
        # Verify project exists
        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if project has a source image
        if not project.source_image:
            raise HTTPException(status_code=400, detail="Project has no source image to vectorize")
        
        # Get project directory
        project_dir = image_helper.get_project_directory(project_id)
        source_image_path = project_dir / project.source_image
        
        # Check if source image file exists
        if not source_image_path.exists():
            raise HTTPException(status_code=404, detail="Source image file not found")
        
        # Read the source image
        with open(source_image_path, 'rb') as f:
            image_data = f.read()
        
        # Use default vectorization settings
        settings = VectorizationSettings()
        
        # Initialize vectorizer
        vectorizer = PolargraphVectorizer()
        
        # Vectorize the image
        result = vectorizer.vectorize_image(image_data, settings)
        
        # Generate plotting commands
        machine_settings = {
            "width": width,
            "height": height,
            "mm_per_rev": mm_per_rev,
            "steps_per_rev": steps_per_rev
        }
        plotting_commands = vectorizer.export_to_plotting_commands(result, machine_settings)
        
        return {
            "success": True,
            "project_id": project_id,
            "commands": plotting_commands,
            "total_commands": len(plotting_commands),
            "machine_settings": machine_settings,
            "vectorization_info": {
                "total_paths": result.total_paths,
                "colors_detected": result.colors_detected,
                "processing_time": result.processing_time
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get vectorization commands error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects/{project_id}/svg")
async def get_project_svg(project_id: str):
    """Get the SVG file for a specific project"""
    try:
        # Verify project exists
        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get project directory
        project_dir = image_helper.get_project_directory(project_id)
        
        # Look for SVG files in the project directory
        svg_files = list(project_dir.glob("*.svg"))
        
        if not svg_files:
            raise HTTPException(status_code=404, detail="No SVG files found for this project")
        
        # Get the most recent SVG file
        latest_svg = max(svg_files, key=lambda f: f.stat().st_mtime)
        
        # Return the SVG file
        return FileResponse(
            path=str(latest_svg),
            media_type="image/svg+xml",
            filename=latest_svg.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get SVG error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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


# Vectorization endpoints
@app.post("/vectorize")
async def vectorize_image(
    file: UploadFile,
    settings: str = Form(default="{}")
):
    """Vectorize an uploaded image"""
    try:
        # Read file content
        contents = await file.read()
        
        # Parse vectorization settings
        vectorization_settings = json.loads(settings) if settings else {}
        
        # Create a temporary ImageHelper instance with vectorizer
        temp_helper = ImageHelper()
        
        # Perform vectorization
        result = temp_helper.vectorize_image(contents, vectorization_settings)
        
        # Broadcast vectorization complete
        await manager.broadcast(json.dumps({
            "type": "vectorization_complete",
            "filename": file.filename,
            "total_paths": result.get("vectorization_result", {}).get("total_paths", 0),
            "colors_detected": result.get("vectorization_result", {}).get("colors_detected", 0),
            "processing_time": result.get("vectorization_result", {}).get("processing_time", 0)
        }))
        
        return result
        
    except Exception as e:
        logger.error(f"Vectorization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/quick-vectorize")
async def quick_vectorize_image(
    file: UploadFile,
    blur: int = Form(default=1),
    posterize: int = Form(default=5),
    simplify: float = Form(default=2.0)
):
    """Quick vectorization with minimal settings"""
    try:
        # Read file content
        contents = await file.read()
        
        # Create a temporary ImageHelper instance with vectorizer
        temp_helper = ImageHelper()
        
        # Perform quick vectorization
        result = temp_helper.quick_vectorize(contents, blur, posterize, simplify)
        
        return result
        
    except Exception as e:
        logger.error(f"Quick vectorization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vectorize/presets")
async def get_vectorization_presets():
    """Get predefined vectorization settings presets"""
    try:
        # Create a temporary ImageHelper instance with vectorizer
        temp_helper = ImageHelper()
        
        return temp_helper.get_vectorization_settings_presets()
        
    except Exception as e:
        logger.error(f"Presets error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Configuration Endpoints
@app.get("/config", response_model=ConfigurationResponse)
async def get_all_configurations():
    """Get all configuration settings (plotters and papers)"""
    try:
        return config_service.get_all_configurations()
    except Exception as e:
        logger.error(f"Get configurations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Plotter Configuration Endpoints
@app.post("/config/plotters", response_model=PlotterResponse)
async def create_plotter(plotter_data: PlotterCreate):
    """Create a new plotter configuration"""
    try:
        plotter = config_service.create_plotter(plotter_data)
        
        # Broadcast plotter creation
        await manager.broadcast(json.dumps({
            "type": "plotter_created",
            "plotter_id": plotter.id,
            "plotter_name": plotter.name
        }))
        
        return plotter
    except Exception as e:
        logger.error(f"Create plotter error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config/plotters", response_model=PlotterListResponse)
async def list_plotters():
    """List all plotter configurations"""
    try:
        return config_service.list_plotters()
    except Exception as e:
        logger.error(f"List plotters error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config/plotters/{plotter_id}", response_model=PlotterResponse)
async def get_plotter(plotter_id: str):
    """Get a plotter configuration by ID"""
    try:
        plotter = config_service.get_plotter(plotter_id)
        if not plotter:
            raise HTTPException(status_code=404, detail="Plotter not found")
        return plotter
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get plotter error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/config/plotters/{plotter_id}", response_model=PlotterResponse)
async def update_plotter(plotter_id: str, plotter_data: PlotterUpdate):
    """Update a plotter configuration"""
    try:
        plotter = config_service.update_plotter(plotter_id, plotter_data)
        if not plotter:
            raise HTTPException(status_code=404, detail="Plotter not found")
        
        # Broadcast plotter update
        await manager.broadcast(json.dumps({
            "type": "plotter_updated",
            "plotter_id": plotter.id,
            "plotter_name": plotter.name
        }))
        
        return plotter
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update plotter error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/config/plotters/{plotter_id}")
async def delete_plotter(plotter_id: str):
    """Delete a plotter configuration"""
    try:
        success = config_service.delete_plotter(plotter_id)
        if not success:
            raise HTTPException(status_code=404, detail="Plotter not found")
        
        # Broadcast plotter deletion
        await manager.broadcast(json.dumps({
            "type": "plotter_deleted",
            "plotter_id": plotter_id
        }))
        
        return {"success": True, "message": f"Plotter {plotter_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete plotter error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config/plotters/default", response_model=PlotterResponse)
async def get_default_plotter():
    """Get the default plotter configuration"""
    try:
        plotter = config_service.get_default_plotter()
        if not plotter:
            raise HTTPException(status_code=404, detail="No default plotter found")
        return plotter
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get default plotter error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Paper Configuration Endpoints
@app.post("/config/papers", response_model=PaperResponse)
async def create_paper(paper_data: PaperCreate):
    """Create a new paper configuration"""
    try:
        paper = config_service.create_paper(paper_data)
        
        # Broadcast paper creation
        await manager.broadcast(json.dumps({
            "type": "paper_created",
            "paper_id": paper.id,
            "paper_name": paper.name
        }))
        
        return paper
    except Exception as e:
        logger.error(f"Create paper error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config/papers", response_model=PaperListResponse)
async def list_papers():
    """List all paper configurations"""
    try:
        return config_service.list_papers()
    except Exception as e:
        logger.error(f"List papers error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config/papers/{paper_id}", response_model=PaperResponse)
async def get_paper(paper_id: str):
    """Get a paper configuration by ID"""
    try:
        paper = config_service.get_paper(paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        return paper
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get paper error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/config/papers/{paper_id}", response_model=PaperResponse)
async def update_paper(paper_id: str, paper_data: PaperUpdate):
    """Update a paper configuration"""
    try:
        paper = config_service.update_paper(paper_id, paper_data)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        # Broadcast paper update
        await manager.broadcast(json.dumps({
            "type": "paper_updated",
            "paper_id": paper.id,
            "paper_name": paper.name
        }))
        
        return paper
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update paper error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/config/papers/{paper_id}")
async def delete_paper(paper_id: str):
    """Delete a paper configuration"""
    try:
        success = config_service.delete_paper(paper_id)
        if not success:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        # Broadcast paper deletion
        await manager.broadcast(json.dumps({
            "type": "paper_deleted",
            "paper_id": paper_id
        }))
        
        return {"success": True, "message": f"Paper {paper_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete paper error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config/papers/default", response_model=PaperResponse)
async def get_default_paper():
    """Get the default paper configuration"""
    try:
        paper = config_service.get_default_paper()
        if not paper:
            raise HTTPException(status_code=404, detail="No default paper found")
        return paper
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get default paper error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/config/rebuild")
async def rebuild_configuration():
    """Rebuild configuration with all default values"""
    try:
        success = config_service.rebuild_default_config()
        
        # Broadcast configuration rebuild
        await manager.broadcast(json.dumps({
            "type": "configuration_rebuilt",
            "message": "Configuration has been rebuilt with default values"
        }))
        
        return {"success": success, "message": "Configuration rebuilt successfully"}
    except Exception as e:
        logger.error(f"Rebuild configuration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
