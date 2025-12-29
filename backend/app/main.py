from fastapi import FastAPI, UploadFile, WebSocket, WebSocketDisconnect, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, FileResponse
from contextlib import asynccontextmanager
import serial
import serial.tools.list_ports
import json
import os
import asyncio
import logging
from typing import List, Optional, Dict, Any
import threading
import uuid
from datetime import datetime
from pathlib import Path
import re
from pydantic import BaseModel
from .image_processor import ImageHelper
from .config import Config, Settings
from .project_models import ProjectCreate, ProjectResponse, ProjectListResponse
from .project_service import project_service
from .vectorizer import PolargraphVectorizer, VectorizationSettings
from .vpype_converter import convert_svg_to_gcode_file
from .config_models import (
    PlotterCreate, PlotterUpdate, PlotterResponse, PlotterListResponse,
    PaperCreate, PaperUpdate, PaperResponse, PaperListResponse,
    ConfigurationResponse, GcodeSettings, GcodeSettingsUpdate
)
from .config_service import config_service
from .plotter_simulator import PlotterSimulator, SIMULATOR_PORT_NAME

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
    "last_update": None,
    "port": None,
    "baud_rate": None
}
# Command/response log (session-only)
command_log: List[Dict] = []

# G-code upload validation
ALLOWED_GCODE_EXTENSIONS = {".gcode", ".nc", ".txt"}
MAX_GCODE_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
GCODE_SEND_DELAY_SECONDS = 0.1  # delay between lines when streaming files

# Background G-code job tracking
gcode_jobs: Dict[str, Dict[str, Any]] = {}
gcode_cancel_all = threading.Event()
gcode_pause_all = threading.Event()

# Helper to send a sequence of G-code commands in order
async def execute_gcode_sequence(commands: List[str], sequence_name: str = "") -> List[Dict[str, Any]]:
    """Execute a list of G-code commands sequentially and capture results."""
    results: List[Dict[str, Any]] = []

    for cmd in commands:
        gcode = (cmd or "").strip()
        if not gcode:
            continue

        response = await send_gcode_command(GcodeRequest(command=gcode))
        result_entry = {
            "command": gcode,
            "success": response.get("success", False),
            "response": response.get("response"),
            "timestamp": response.get("timestamp"),
            "error": response.get("error")
        }
        results.append(result_entry)

        # Stop if a command failed to avoid cascading issues
        if not result_entry["success"]:
            break

    return results

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


def custom_openapi():
    """Sort endpoints alphabetically in Swagger UI for easier scanning."""
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    # Order paths and tags consistently
    schema["paths"] = dict(sorted(schema.get("paths", {}).items(), key=lambda item: item[0]))
    if "tags" in schema and isinstance(schema["tags"], list):
        schema["tags"] = sorted(schema["tags"], key=lambda t: t.get("name", ""))
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi

# CORS middleware for frontend communication (allow override via CORS_ORIGINS env)
cors_origins = Settings.get_cors_origins()
allow_origin_regex = None
# If no override provided, allow any host (useful for Pi access from LAN)
if not os.getenv("CORS_ORIGINS"):
    allow_origin_regex = ".*"

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=allow_origin_regex,
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

# Plotter connection management endpoints
@app.get("/plotter/ports")
async def get_available_ports():
    """Get list of available serial ports"""
    try:
        ports = []
        
        # Add simulator port first
        ports.append({
            "device": SIMULATOR_PORT_NAME,
            "description": "PolarVortex Plotter Simulator",
            "manufacturer": "PolarVortex",
            "hwid": "SIMULATOR"
        })
        
        # Add real serial ports
        for port in serial.tools.list_ports.comports():
            ports.append({
                "device": port.device,
                "description": port.description,
                "manufacturer": port.manufacturer if port.manufacturer else "",
                "hwid": port.hwid
            })
        return {"ports": ports}
    except Exception as e:
        logger.error(f"Error listing ports: {e}")
        return {"ports": [], "error": str(e)}

class PlotterConnectRequest(BaseModel):
    port: str
    baud_rate: int = 9600

@app.post("/plotter/connect")
async def connect_plotter(request: PlotterConnectRequest):
    """Connect to plotter with specified port and baud rate"""
    global arduino
    try:
        # Disconnect if already connected
        if arduino and arduino.is_open:
            arduino.close()
        
        # Check if connecting to simulator
        if request.port == SIMULATOR_PORT_NAME:
            # Create simulator instance
            arduino = PlotterSimulator(request.port, request.baud_rate, timeout=2)
            logger.info(f"Connected to plotter simulator on {request.port} at {request.baud_rate} baud")
        else:
            # Connect to real serial port
            arduino = serial.Serial(request.port, request.baud_rate, timeout=2)
            logger.info(f"Connected to plotter on {request.port} at {request.baud_rate} baud")
        
        # Update status
        current_status["connected"] = True
        current_status["port"] = request.port
        current_status["baud_rate"] = request.baud_rate
        
        # Clear any existing input buffer
        arduino.reset_input_buffer()

        # Execute any configured on-connect G-code
        startup_results: List[Dict[str, Any]] = []
        gcode_settings = config_service.get_gcode_settings()
        if gcode_settings.on_connect:
            startup_results = await execute_gcode_sequence(gcode_settings.on_connect, "on_connect")
            logger.info(
                "Executed on-connect G-code sequence with %d commands (success=%s)",
                len(startup_results),
                all(item.get("success") for item in startup_results) if startup_results else True
            )
        
        return {
            "success": True,
            "port": request.port,
            "baud_rate": request.baud_rate,
            "message": f"Connected to {request.port}",
            "startup_gcode": {
                "commands_sent": len(startup_results),
                "results": startup_results
            }
        }
    except serial.SerialException as e:
        logger.error(f"Serial connection error: {e}")
        current_status["connected"] = False
        return {"success": False, "error": f"Failed to connect: {str(e)}"}
    except Exception as e:
        logger.error(f"Connection error: {e}")
        current_status["connected"] = False
        return {"success": False, "error": str(e)}

@app.post("/plotter/disconnect")
async def disconnect_plotter():
    """Disconnect from plotter"""
    global arduino
    try:
        if arduino and arduino.is_open:
            arduino.close()
            logger.info("Disconnected from plotter")
        
        arduino = None
        current_status["connected"] = False
        current_status["port"] = None
        current_status["baud_rate"] = None
        
        return {"success": True, "message": "Disconnected"}
    except Exception as e:
        logger.error(f"Disconnect error: {e}")
        return {"success": False, "error": str(e)}

@app.get("/plotter/connection")
async def get_connection_status():
    """Get current connection status"""
    return {
        "connected": current_status["connected"],
        "port": current_status["port"],
        "baud_rate": current_status["baud_rate"],
        "is_open": arduino.is_open if arduino else False
    }

class GcodeRequest(BaseModel):
    command: str

class ProjectGcodeRunRequest(BaseModel):
    filename: str

class SvgToGcodeRequest(BaseModel):
    filename: str
    paper_size: str = "A4"
    fit_mode: str = "fit"  # fit | center
    pen_mapping: Optional[str] = None


def _resolve_paper_dimensions(paper_size: str) -> tuple[float, float, str]:
    """Look up paper width/height from configuration by size name or ID."""
    papers = config_service.list_papers().papers
    paper = next(
        (
            p for p in papers
            if p.paper_size.lower() == paper_size.lower() or p.id == paper_size
        ),
        None,
    )
    if not paper:
        paper = config_service.get_default_paper()
    if not paper:
        raise HTTPException(status_code=400, detail="No paper configurations found")
    return float(paper.width), float(paper.height), paper.paper_size

def _response_contains_ok(responses: List[str]) -> bool:
    """Check if any response line includes an OK acknowledgement."""
    return any(line.lower().startswith("ok") for line in responses)


async def read_arduino_response(timeout_seconds: float = 3.0) -> List[str]:
    """Read response from Arduino until 'ok' or timeout"""
    responses = []
    if not arduino or not arduino.is_open:
        return responses
    
    start_time = datetime.now()
    while (datetime.now() - start_time).total_seconds() < timeout_seconds:
        if arduino.in_waiting > 0:
            try:
                line = arduino.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    responses.append(line)
                    # Marlin typically responds with "ok" or "ok N"
                    if line.lower().startswith('ok'):
                        break
            except Exception as e:
                logger.warning(f"Error reading response: {e}")
                break
        else:
            await asyncio.sleep(0.01)  # Small delay to avoid busy waiting
    
    return responses

@app.post("/plotter/gcode")
async def send_gcode_command(request: GcodeRequest):
    """Send G-code command to plotter and read response"""
    try:
        if not arduino or not arduino.is_open:
            return {"success": False, "error": "Plotter not connected"}
        
        gcode = request.command.strip()
        if not gcode:
            return {"success": False, "error": "Empty command"}
        
        # Send command with an explicit newline terminator so manual entries are processed
        command_bytes = gcode.encode('utf-8')
        arduino.write(command_bytes)
        arduino.write(b"\n")
        logger.info(f"Sent G-code: {gcode}")
        
        # Read response with busy-aware retries up to a total wait
        responses: List[str] = []
        ok_received = False
        busy_seen = False
        start_wait = datetime.now()
        max_wait_seconds = 20.0

        while (datetime.now() - start_wait).total_seconds() < max_wait_seconds:
            chunk = await read_arduino_response(timeout_seconds=1.5)
            if chunk:
                responses.extend(chunk)
                if _response_contains_ok(chunk):
                    ok_received = True
                    break
                if any("busy" in r.lower() for r in chunk):
                    busy_seen = True
            else:
                await asyncio.sleep(0.3)

        # Combine multi-line responses
        response_text = "\n".join(responses) if responses else "No response"
        success = ok_received or busy_seen
        error_text = None
        if not ok_received and not busy_seen:
            error_text = "No 'ok' received from printer; holding next commands to avoid buffer overrun"
            logger.warning("%s (command='%s', response='%s')", error_text, gcode, response_text)
        elif busy_seen and not ok_received:
            logger.warning("Printer busy without final ok; continuing (command='%s', response='%s')", gcode, response_text)
        
        # Log command/response
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "command": gcode,
            "response": response_text
        }
        command_log.append(log_entry)
        
        # Keep log size manageable (last 1000 entries)
        if len(command_log) > 1000:
            command_log.pop(0)
        
        # Broadcast via WebSocket
        await manager.broadcast(json.dumps({
            "type": "gcode_response",
            "command": gcode,
            "response": response_text,
            "ok_received": ok_received,
            "timestamp": log_entry["timestamp"]
        }))
        
        return {
            "success": success,
            "command": gcode,
            "response": response_text,
            "responses": responses,
            "ok_received": ok_received,
            "error": error_text,
            "timestamp": log_entry["timestamp"]
        }
    except Exception as e:
        logger.error(f"G-code command error: {e}")
        error_msg = str(e)
        return {"success": False, "error": error_msg, "command": request.command}


@app.post("/plotter/gcode/preprint")
async def run_preprint_gcode():
    """Run configured G-code commands before starting a print"""
    try:
        settings = config_service.get_gcode_settings()
        if not settings.before_print:
            return {
                "success": True,
                "results": [],
                "message": "No pre-print G-code configured"
            }

        results = await execute_gcode_sequence(settings.before_print, "before_print")
        success = all(item.get("success") for item in results) if results else True

        return {
            "success": success,
            "results": results,
            "message": "Pre-print G-code executed" if success else "Pre-print G-code had errors"
        }
    except Exception as e:
        logger.error(f"Pre-print G-code error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/plotter/log")
async def get_command_log():
    """Get command/response log (session-only)"""
    return {"log": command_log, "count": len(command_log)}

@app.post("/plotter/log/clear")
async def clear_command_log():
    """Clear command/response log"""
    global command_log
    command_log = []
    return {"success": True, "message": "Log cleared"}

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

@app.get("/projects/{project_id}/images/{filename:path}")
async def get_project_image(project_id: str, filename: str):
    """Get a specific image file from a project"""
    try:
        # Verify project exists
        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get the project directory and construct image path
        project_dir = project_service._get_project_directory(project_id)
        image_path = (project_dir / filename).resolve()
        
        # Prevent path traversal outside project directory
        if project_dir not in image_path.parents and project_dir != image_path:
            raise HTTPException(status_code=400, detail="Invalid file path")
        
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
            'bmp': 'image/bmp',
            'svg': 'image/svg+xml',
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


@app.post("/projects/{project_id}/svg_to_gcode")
async def convert_svg_to_gcode(project_id: str, request: SvgToGcodeRequest):
    """Convert a project SVG file into G-code and store it on the project using vpype"""
    try:
        # #region agent log
        from .vpype_converter import _dbg_log as vp_dbg  # local import to avoid circular
        vp_dbg("H2", "main.py:1009", "convert_svg_to_gcode entry", {
            "project_id": project_id,
            "filename": request.filename,
            "paper_size": request.paper_size,
            "fit_mode": request.fit_mode,
            "pen_mapping": request.pen_mapping,
        })
        # #endregion
        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        project_dir = project_service._get_project_directory(project_id).resolve()
        svg_path = (project_dir / request.filename).resolve()

        # Prevent path traversal
        if project_dir not in svg_path.parents and project_dir != svg_path:
            raise HTTPException(status_code=400, detail="Invalid file path")

        if not svg_path.exists() or not svg_path.is_file():
            raise HTTPException(status_code=404, detail="SVG file not found")

        if svg_path.suffix.lower() != ".svg":
            raise HTTPException(status_code=400, detail="File is not an SVG")

        gcode_dir = project_dir / "gcode"
        gcode_dir.mkdir(parents=True, exist_ok=True)

        base_name = svg_path.stem
        gcode_filename = f"{base_name}_converted.gcode"
        target_path = gcode_dir / gcode_filename
        # Ensure unique filename
        if target_path.exists():
            gcode_filename = f"{base_name}_converted_{uuid.uuid4().hex[:8]}.gcode"
            target_path = gcode_dir / gcode_filename

        paper_width_mm, paper_height_mm, resolved_paper_size = _resolve_paper_dimensions(request.paper_size)

        await convert_svg_to_gcode_file(
            svg_path=svg_path,
            output_path=target_path,
            paper_width_mm=paper_width_mm,
            paper_height_mm=paper_height_mm,
            fit_mode=request.fit_mode,
            pen_mapping=request.pen_mapping,
        )

        stored_name = str(Path("gcode") / gcode_filename)
        project_service.add_project_gcode_file(project_id, stored_name)

        size_bytes = target_path.stat().st_size if target_path.exists() else 0
        # #region agent log
        vp_dbg("H2", "main.py:1046", "convert_svg_to_gcode success", {
            "stored_name": stored_name,
            "size": size_bytes,
            "target_exists": target_path.exists(),
        })
        # #endregion

        return {
            "success": True,
            "project_id": project_id,
            "svg": request.filename,
            "gcode_filename": gcode_filename,
            "relative_path": stored_name,
            "size": size_bytes,
            "message": "SVG converted to G-code via vpype",
        }
    except HTTPException:
        raise
    except Exception as e:
        # #region agent log
        try:
            vp_dbg("H2", "main.py:1060", "convert_svg_to_gcode error", {"error": str(e)})
        except Exception:
            pass
        # #endregion
        logger.error(f"SVG to G-code error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/projects/{project_id}/images/{filename:path}")
async def delete_project_file(project_id: str, filename: str):
    """Delete a specific file (image/SVG/G-code) from a project"""
    try:
        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        project_dir = project_service._get_project_directory(project_id).resolve()
        file_path = (project_dir / filename).resolve()

        # Prevent path traversal outside project directory
        if project_dir not in file_path.parents and project_dir != file_path:
            raise HTTPException(status_code=400, detail="Invalid file path")

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")

        # Remove file from disk
        file_path.unlink()

        # Update project metadata if needed
        is_gcode = filename in (project.gcode_files or []) or str(Path(filename)) in (project.gcode_files or [])
        remove_thumbnail = project.thumbnail_image == filename or project.thumbnail_image == Path(filename).name
        remove_source = project.source_image == filename or project.source_image == Path(filename).name
        remove_vectorization_svg = bool(
            project.vectorization and project.vectorization.svg_filename and (
                project.vectorization.svg_filename == filename or project.vectorization.svg_filename == Path(filename).name
            )
        )

        project_service.update_project_after_file_removal(
            project_id=project_id,
            remove_thumbnail=remove_thumbnail,
            remove_source_image=remove_source,
            remove_vectorization_svg=remove_vectorization_svg,
            remove_gcode_filename=filename if is_gcode else None
        )

        return {"success": True, "message": f"Deleted {filename}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete project file error: {e}")
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

# Upload a G-code file to a project
@app.post("/projects/{project_id}/gcode_upload")
async def upload_gcode_to_project(
    project_id: str,
    file: UploadFile,
):
    """
    Upload a G-code file into a project directory and register it on the project.
    """
    try:
        # Verify project exists
        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file")

        if len(content) > MAX_GCODE_UPLOAD_SIZE:
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")

        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_GCODE_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_GCODE_EXTENSIONS))}")

        # Sanitize filename and ensure deterministic storage path
        base_name = image_helper.sanitize_filename(file.filename or "upload.gcode")
        safe_filename = f"{base_name}{ext}"

        project_dir = image_helper.get_project_directory(project_id)
        gcode_dir = project_dir / "gcode"
        gcode_dir.mkdir(parents=True, exist_ok=True)

        save_path = gcode_dir / safe_filename
        with open(save_path, "wb") as f:
            f.write(content)

        # Store relative path inside project for portability
        stored_name = str(Path("gcode") / safe_filename)
        updated_project = project_service.add_project_gcode_file(project_id, stored_name)
        if not updated_project:
            raise HTTPException(status_code=500, detail="Failed to register G-code on project")

        return {
            "success": True,
            "project_id": project_id,
            "filename": safe_filename,
            "relative_path": stored_name,
            "size": len(content),
            "gcode_files": updated_project.gcode_files,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"G-code upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/projects/{project_id}/gcode/run")
async def run_project_gcode(project_id: str, request: ProjectGcodeRunRequest):
    """
    Stream a stored project G-code file to the plotter in a background thread.
    """
    try:
        if not arduino or not arduino.is_open:
            raise HTTPException(status_code=400, detail="Plotter not connected")

        project = project_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if not project.gcode_files or request.filename not in project.gcode_files:
            raise HTTPException(status_code=404, detail="G-code file not found for this project")

        project_dir = project_service._get_project_directory(project_id).resolve()
        file_path = (project_dir / request.filename).resolve()

        # Prevent path traversal outside project directory
        if project_dir not in file_path.parents and project_dir != file_path:
            raise HTTPException(status_code=400, detail="Invalid file path")

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="G-code file missing on disk")

        commands: List[str] = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith(";"):
                    continue
                if ";" in stripped:
                    stripped = stripped.split(";", 1)[0].strip()
                if stripped:
                    commands.append(stripped)

        job_id = str(uuid.uuid4())
        # Clear any global cancel flag before starting a new job
        gcode_cancel_all.clear()
        gcode_pause_all.clear()

        gcode_jobs[job_id] = {
            "status": "queued",
            "project_id": project_id,
            "filename": request.filename,
            "commands_total": len(commands),
            "started_at": None,
            "finished_at": None,
            "error": None,
            "cancel_requested": False,
            "paused": False,
        }

        if commands:
            thread = threading.Thread(
                target=_run_gcode_commands_thread,
                args=(job_id, commands, request.filename),
                daemon=True,
            )
            thread.start()
        else:
            gcode_jobs[job_id]["status"] = "completed"
            gcode_jobs[job_id]["finished_at"] = datetime.now().isoformat()

        return {
            "success": True,
            "job_id": job_id,
            "project_id": project_id,
            "filename": request.filename,
            "queued": len(commands),
            "status": gcode_jobs[job_id]["status"],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Run project G-code error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _run_gcode_commands_thread(job_id: str, commands: List[str], filename: str):
    """Background thread runner to stream G-code commands."""
    async def runner():
        try:
            gcode_jobs[job_id]["status"] = "running"
            gcode_jobs[job_id]["started_at"] = datetime.now().isoformat()
            results: List[Dict[str, Any]] = []

            for cmd in commands:
                if gcode_cancel_all.is_set() or gcode_jobs[job_id].get("cancel_requested"):
                    gcode_jobs[job_id]["status"] = "canceled"
                    gcode_jobs[job_id]["finished_at"] = datetime.now().isoformat()
                    gcode_jobs[job_id]["results"] = results
                    return

                # Handle pause
                if gcode_pause_all.is_set():
                    gcode_jobs[job_id]["status"] = "paused"
                    gcode_jobs[job_id]["paused"] = True
                    while gcode_pause_all.is_set():
                        await asyncio.sleep(0.1)
                        if gcode_cancel_all.is_set() or gcode_jobs[job_id].get("cancel_requested"):
                            gcode_jobs[job_id]["status"] = "canceled"
                            gcode_jobs[job_id]["finished_at"] = datetime.now().isoformat()
                            gcode_jobs[job_id]["results"] = results
                            return
                    gcode_jobs[job_id]["status"] = "running"
                    gcode_jobs[job_id]["paused"] = False

                try:
                    resp = await send_gcode_command(GcodeRequest(command=cmd))
                except Exception as e:
                    resp = {"success": False, "error": str(e), "command": cmd}
                results.append(resp)
                if not resp.get("success"):
                    break
                # Yield control and add a small delay to avoid overrun
                await asyncio.sleep(GCODE_SEND_DELAY_SECONDS)

            gcode_jobs[job_id]["status"] = "completed" if all(r.get("success") for r in results) else "failed"
            gcode_jobs[job_id]["finished_at"] = datetime.now().isoformat()
            gcode_jobs[job_id]["results"] = results
        except Exception as e:
            logger.error(f"G-code job {job_id} failed: {e}")
            gcode_jobs[job_id]["status"] = "failed"
            gcode_jobs[job_id]["error"] = str(e)
            gcode_jobs[job_id]["finished_at"] = datetime.now().isoformat()

    asyncio.run(runner())


def cancel_all_gcode_jobs():
    """Request cancellation of all running/queued G-code jobs."""
    gcode_cancel_all.set()
    for job_id, job in gcode_jobs.items():
        if job.get("status") in {"queued", "running"}:
            job["cancel_requested"] = True
    gcode_pause_all.clear()


@app.post("/plotter/stop")
async def stop_plotter():
    """Stop plotter immediately and cancel any running G-code jobs."""
    try:
        cancel_all_gcode_jobs()

        stop_sent = False
        if arduino and arduino.is_open:
            try:
                arduino.write(b"M112\n")  # Emergency stop
                stop_sent = True
            except Exception as e:
                logger.warning(f"Failed to send stop command: {e}")

        current_status["drawing"] = False
        current_status["current_command"] = None

        return {
            "success": True,
            "message": "Stop requested",
            "stop_sent": stop_sent,
            "canceled_jobs": [
                job_id for job_id, job in gcode_jobs.items() if job.get("cancel_requested")
            ],
        }
    except Exception as e:
        logger.error(f"Stop error: {e}")
        return {"success": False, "error": str(e)}


@app.post("/plotter/pause")
async def pause_plotter():
    """Toggle pause/resume: on pause send M0, on resume clear pause flag."""
    try:
        was_paused = gcode_pause_all.is_set()
        if was_paused:
            gcode_pause_all.clear()
            for job in gcode_jobs.values():
                if job.get("status") == "paused":
                    job["status"] = "running"
                    job["paused"] = False
            return {"success": True, "message": "Resume requested", "paused": False}

        # Request pause
        gcode_pause_all.set()
        for job in gcode_jobs.values():
            if job.get("status") in {"queued", "running"}:
                job["paused"] = True
                job["status"] = "paused"

        # Send M0 best-effort
        pause_sent = False
        if arduino and arduino.is_open:
            try:
                arduino.write(b"M0\n")
                pause_sent = True
            except Exception as e:
                logger.warning(f"Failed to send pause command: {e}")

        return {"success": True, "message": "Pause requested", "paused": True, "pause_sent": pause_sent}
    except Exception as e:
        logger.error(f"Pause error: {e}")
        return {"success": False, "error": str(e)}

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
        
        # Update project with vectorization information
        svg_filename = Path(result.svg_path).name if result.svg_path else None
        vectorization_parameters = {
            "blur_radius": settings.blur_radius,
            "posterize_levels": settings.posterize_levels,
            "simplification_threshold": settings.simplification_threshold,
            "min_contour_area": settings.min_contour_area,
            "color_tolerance": settings.color_tolerance,
            "enable_color_separation": settings.enable_color_separation,
            "enable_contour_simplification": settings.enable_contour_simplification,
            "enable_noise_reduction": settings.enable_noise_reduction
        }
        
        project_service.update_project_vectorization(
            project_id=project_id,
            svg_filename=svg_filename,
            parameters=vectorization_parameters,
            total_paths=result.total_paths,
            colors_detected=result.colors_detected,
            processing_time=result.processing_time
        )
        
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


@app.get("/config/gcode", response_model=GcodeSettings)
async def get_gcode_settings():
    """Get automatic G-code sequences"""
    try:
        return config_service.get_gcode_settings()
    except Exception as e:
        logger.error(f"Get G-code settings error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/config/gcode", response_model=GcodeSettings)
async def update_gcode_settings(gcode_data: GcodeSettingsUpdate):
    """Update automatic G-code sequences"""
    try:
        settings = config_service.update_gcode_settings(gcode_data)

        # Broadcast update
        await manager.broadcast(json.dumps({
            "type": "gcode_settings_updated",
            "on_connect_count": len(settings.on_connect),
            "before_print_count": len(settings.before_print)
        }))

        return settings
    except Exception as e:
        logger.error(f"Update G-code settings error: {e}")
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
