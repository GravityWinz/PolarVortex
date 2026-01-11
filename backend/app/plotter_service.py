import asyncio
import json
import logging
import threading
import time
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional

import serial
import serial.tools.list_ports
from fastapi import HTTPException

from .config_service import config_service
from .plotter_models import GcodeRequest, PlotterConnectRequest
from .plotter_simulator import PlotterSimulator, SIMULATOR_PORT_NAME
from .plotter_core import PlotterCore

GCODE_SEND_DELAY_SECONDS = 0.1  # delay between lines when streaming files

logger = logging.getLogger(__name__)


class PlotterService:
    def __init__(self) -> None:
        self.arduino = None  # For simulator only
        self.plotter_core: Optional[PlotterCore] = None  # For real plotter connections
        self.current_status: Dict[str, Any] = {
            "connected": False,
            "drawing": False,
            "progress": 0,
            "current_command": None,
            "last_update": None,
            "port": None,
            "baud_rate": None,
        }
        self.command_log: List[Dict[str, Any]] = []
        self._command_log_lock = threading.Lock()  # Lock for thread-safe command_log access
        self.gcode_jobs: Dict[str, Dict[str, Any]] = {}
        self._gcode_jobs_lock = threading.Lock()  # Lock for thread-safe gcode_jobs access
        self.gcode_cancel_all = threading.Event()
        self.gcode_pause_all = threading.Event()
        self._broadcast: Optional[Callable[[str], Awaitable[None]]] = None

    def set_broadcaster(self, broadcaster: Optional[Callable[[str], Awaitable[None]]]) -> None:
        """Set async broadcast function (e.g., ConnectionManager.broadcast)."""
        self._broadcast = broadcaster

    async def _broadcast_json(self, payload: Dict[str, Any]) -> None:
        if not self._broadcast:
            return
        try:
            await self._broadcast(json.dumps(payload))
        except Exception as exc:  # Best-effort; avoid crashing callers
            logger.warning("Plotter broadcast failed: %s", exc)

    def get_available_ports(self) -> Dict[str, Any]:
        """List available serial ports including simulator."""
        try:
            ports: List[Dict[str, Any]] = [
                {
                    "device": SIMULATOR_PORT_NAME,
                    "description": "PolarVortex Plotter Simulator",
                    "manufacturer": "PolarVortex",
                    "hwid": "SIMULATOR",
                }
            ]

            for port in serial.tools.list_ports.comports():
                ports.append(
                    {
                        "device": port.device,
                        "description": port.description,
                        "manufacturer": port.manufacturer if port.manufacturer else "",
                        "hwid": port.hwid,
                    }
                )
            return {"ports": ports}
        except Exception as exc:
            logger.error("Error listing ports: %s", exc)
            return {"ports": [], "error": str(exc)}

    async def connect_plotter(self, request: PlotterConnectRequest) -> Dict[str, Any]:
        """Connect to a real or simulated plotter."""
        try:
            # Disconnect existing connections
            if self.plotter_core:
                self.plotter_core.disconnect()
                self.plotter_core = None
            if self.arduino and getattr(self.arduino, "is_open", False):
                self.arduino.close()
                self.arduino = None

            if request.port == SIMULATOR_PORT_NAME:
                # Use simulator
                self.arduino = PlotterSimulator(request.port, request.baud_rate, timeout=2)
                logger.info(
                    "Connected to plotter simulator on %s at %s baud", request.port, request.baud_rate
                )
                self.current_status["connected"] = True
                self.current_status["port"] = request.port
                self.current_status["baud_rate"] = request.baud_rate
                self.arduino.reset_input_buffer()
            else:
                # Use PlotterCore for real connections
                self.plotter_core = PlotterCore(port=request.port, baud=request.baud_rate)
                
                # Set up callback to capture command/response pairs for command log
                # on_send creates a new log entry with the command
                # on_recv updates the most recent entry without a response
                # Both use locks for thread-safe access
                def on_send(command: str, original: str):
                    log_entry = {
                        "timestamp": datetime.now().isoformat(),
                        "command": original,
                        "response": "",  # Will be filled by recv callback
                    }
                    with self._command_log_lock:
                        self.command_log.append(log_entry)
                        if len(self.command_log) > 1000:
                            self.command_log.pop(0)
                
                def on_recv(line: str):
                    # Find the oldest entry without a response and update it
                    # This pairs the response with the oldest unpaired command (FIFO order)
                    with self._command_log_lock:
                        for entry in self.command_log:
                            if not entry.get("response"):
                                entry["response"] = line.strip()
                                break
                        # If no unpaired command found, create a new entry (shouldn't happen normally)
                        else:
                            log_entry = {
                                "timestamp": datetime.now().isoformat(),
                                "command": "",  # Orphaned response
                                "response": line.strip(),
                            }
                            self.command_log.append(log_entry)
                            if len(self.command_log) > 1000:
                                self.command_log.pop(0)
                
                self.plotter_core.add_callback('send', on_send)
                self.plotter_core.add_callback('recv', on_recv)
                
                # Wait for plotter to come online
                timeout = 10.0
                start = time.time()
                while not self.plotter_core.online and (time.time() - start) < timeout:
                    await asyncio.sleep(0.1)
                
                if not self.plotter_core.online:
                    self.plotter_core = None
                    return {"success": False, "error": "Plotter did not come online within timeout"}
                
                logger.info("Connected to plotter on %s at %s baud", request.port, request.baud_rate)
                self.current_status["connected"] = True
                self.current_status["port"] = request.port
                self.current_status["baud_rate"] = request.baud_rate

            startup_results: List[Dict[str, Any]] = []
            gcode_settings = config_service.get_gcode_settings()
            if gcode_settings.on_connect:
                startup_results = await self.execute_gcode_sequence(gcode_settings.on_connect, "on_connect")
                logger.info(
                    "Executed on-connect G-code sequence with %d commands (success=%s)",
                    len(startup_results),
                    all(item.get("success") for item in startup_results) if startup_results else True,
                )

            return {
                "success": True,
                "port": request.port,
                "baud_rate": request.baud_rate,
                "message": f"Connected to {request.port}",
                "startup_gcode": {
                    "commands_sent": len(startup_results),
                    "results": startup_results,
                },
            }
        except serial.SerialException as exc:
            logger.error("Serial connection error: %s", exc)
            self.current_status["connected"] = False
            return {"success": False, "error": f"Failed to connect: {str(exc)}"}
        except Exception as exc:
            logger.error("Connection error: %s", exc)
            self.current_status["connected"] = False
            return {"success": False, "error": str(exc)}

    async def disconnect_plotter(self) -> Dict[str, Any]:
        """Disconnect from plotter."""
        try:
            if self.plotter_core:
                self.plotter_core.disconnect()
                self.plotter_core = None
                logger.info("Disconnected from plotter")
            
            if self.arduino and getattr(self.arduino, "is_open", False):
                self.arduino.close()
                logger.info("Disconnected from plotter simulator")

            self.arduino = None
            self.current_status["connected"] = False
            self.current_status["port"] = None
            self.current_status["baud_rate"] = None

            return {"success": True, "message": "Disconnected"}
        except Exception as exc:
            logger.error("Disconnect error: %s", exc)
            return {"success": False, "error": str(exc)}

    def get_connection_status(self) -> Dict[str, Any]:
        """Return connection status snapshot."""
        is_open = False
        if self.plotter_core:
            is_open = self.plotter_core.online and self.plotter_core.device and self.plotter_core.device.is_connected
        elif self.arduino:
            is_open = getattr(self.arduino, "is_open", False)
        
        return {
            "connected": self.current_status["connected"],
            "port": self.current_status["port"],
            "baud_rate": self.current_status["baud_rate"],
            "is_open": is_open,
        }

    @staticmethod
    def _response_contains_ok(responses: List[str]) -> bool:
        return any(line.lower().startswith("ok") for line in responses)

    async def read_arduino_response(self, timeout_seconds: float = 3.0) -> List[str]:
        """Read response from Arduino until 'ok' or timeout."""
        responses: List[str] = []
        if not self.arduino or not getattr(self.arduino, "is_open", False):
            return responses

        start_time = datetime.now()
        while (datetime.now() - start_time).total_seconds() < timeout_seconds:
            if self.arduino.in_waiting > 0:
                try:
                    line = self.arduino.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        responses.append(line)
                        if line.lower().startswith("ok"):
                            break
                except Exception as exc:
                    logger.warning("Error reading response: %s", exc)
                    break
            else:
                await asyncio.sleep(0.01)

        return responses

    async def send_gcode_command(self, request: GcodeRequest) -> Dict[str, Any]:
        """Send G-code command to plotter and read response."""
        try:
            gcode = request.command.strip()
            if not gcode:
                return {"success": False, "error": "Empty command"}

            # Use PlotterCore for real connections
            if self.plotter_core and self.plotter_core.online:
                # Send via priority queue (immediate command)
                self.plotter_core.send_now(gcode)
                logger.info("Sent G-code via PlotterCore: %s", gcode)
                
                # Wait a bit for response to be captured by callback
                await asyncio.sleep(0.2)
                
                # Get recent responses from log
                recent_logs = list(self.plotter_core.log)[-10:] if self.plotter_core.log else []
                responses = [line.strip() for line in recent_logs if line.strip()]
                response_text = "\n".join(responses) if responses else "Command sent"
                ok_received = any("ok" in r.lower() for r in responses)
                
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "command": gcode,
                    "response": response_text,
                }
                
                await self._broadcast_json(
                    {
                        "type": "gcode_response",
                        "command": gcode,
                        "response": response_text,
                        "ok_received": ok_received,
                        "timestamp": log_entry["timestamp"],
                    }
                )
                
                return {
                    "success": True,
                    "command": gcode,
                    "response": response_text,
                    "responses": responses,
                    "ok_received": ok_received,
                    "timestamp": log_entry["timestamp"],
                }
            
            # Fallback to simulator or old method
            if not self.arduino or not getattr(self.arduino, "is_open", False):
                return {"success": False, "error": "Plotter not connected"}

            command_bytes = gcode.encode("utf-8")
            self.arduino.write(command_bytes)
            self.arduino.write(b"\n")
            logger.info("Sent G-code: %s", gcode)

            responses: List[str] = []
            ok_received = False
            busy_seen = False
            start_wait = datetime.now()
            last_progress = datetime.now()
            max_total_seconds = 300.0  # hard cap
            idle_timeout_seconds = 30.0
            busy_idle_timeout_seconds = 120.0

            while True:
                total_elapsed = (datetime.now() - start_wait).total_seconds()
                idle_elapsed = (datetime.now() - last_progress).total_seconds()

                # Stop if we exceeded overall or idle thresholds
                if total_elapsed >= max_total_seconds:
                    break
                if busy_seen and idle_elapsed >= busy_idle_timeout_seconds:
                    break
                if not busy_seen and idle_elapsed >= idle_timeout_seconds:
                    break

                chunk = await self.read_arduino_response(timeout_seconds=1.5)
                if chunk:
                    last_progress = datetime.now()
                    responses.extend(chunk)
                    if self._response_contains_ok(chunk):
                        ok_received = True
                        break
                    if any("busy" in r.lower() for r in chunk):
                        busy_seen = True
                else:
                    await asyncio.sleep(0.3)

            response_text = "\n".join(responses) if responses else "No response"
            success = ok_received
            error_text = None
            if not ok_received:
                if busy_seen:
                    error_text = "Printer reported busy and no 'ok' arrived before timeout; pausing further commands"
                else:
                    error_text = "No 'ok' received from printer; holding next commands to avoid buffer overrun"
                logger.warning("%s (command='%s', response='%s')", error_text, gcode, response_text)

            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "command": gcode,
                "response": response_text,
            }
            with self._command_log_lock:
                self.command_log.append(log_entry)
                if len(self.command_log) > 1000:
                    self.command_log.pop(0)

            await self._broadcast_json(
                {
                    "type": "gcode_response",
                    "command": gcode,
                    "response": response_text,
                    "ok_received": ok_received,
                    "timestamp": log_entry["timestamp"],
                }
            )

            return {
                "success": success,
                "command": gcode,
                "response": response_text,
                "responses": responses,
                "ok_received": ok_received,
                "error": error_text,
                "timestamp": log_entry["timestamp"],
            }
        except Exception as exc:
            logger.error("G-code command error: %s", exc)
            return {"success": False, "error": str(exc), "command": request.command}

    async def execute_gcode_sequence(self, commands: List[str], sequence_name: str = "") -> List[Dict[str, Any]]:
        """Execute a list of G-code commands sequentially and capture results."""
        results: List[Dict[str, Any]] = []
        for cmd in commands:
            gcode = (cmd or "").strip()
            if not gcode:
                continue

            response = await self.send_gcode_command(GcodeRequest(command=gcode))
            result_entry = {
                "command": gcode,
                "success": response.get("success", False),
                "response": response.get("response"),
                "timestamp": response.get("timestamp"),
                "error": response.get("error"),
            }
            results.append(result_entry)
            if not result_entry["success"]:
                break
        return results

    async def run_preprint_gcode(self) -> Dict[str, Any]:
        """Run configured G-code commands before starting a print."""
        try:
            settings = config_service.get_gcode_settings()
            if not settings.before_print:
                return {
                    "success": True,
                    "results": [],
                    "message": "No pre-print G-code configured",
                }

            results = await self.execute_gcode_sequence(settings.before_print, "before_print")
            success = all(item.get("success") for item in results) if results else True

            return {
                "success": success,
                "results": results,
                "message": "Pre-print G-code executed" if success else "Pre-print G-code had errors",
            }
        except Exception as exc:
            logger.error("Pre-print G-code error: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))

    def get_command_log(self) -> Dict[str, Any]:
        """Return command/response log."""
        with self._command_log_lock:
            # Create a copy to avoid holding the lock while returning
            log_copy = self.command_log.copy()
            return {"log": log_copy, "count": len(log_copy)}

    def clear_command_log(self) -> Dict[str, Any]:
        """Clear command/response log."""
        with self._command_log_lock:
            self.command_log = []
        return {"success": True, "message": "Log cleared"}

    def cancel_all_gcode_jobs(self) -> None:
        """Request cancellation of all running/queued G-code jobs."""
        self.gcode_cancel_all.set()
        
        # Cancel PlotterCore print if running
        if self.plotter_core and self.plotter_core.printing:
            self.plotter_core.cancelprint()
        
        with self._gcode_jobs_lock:
            for job_id, job in self.gcode_jobs.items():
                if job.get("status") in {"queued", "running", "paused"}:
                    job["cancel_requested"] = True
                    job["status"] = "canceled"
                    if not job.get("finished_at"):
                        job["finished_at"] = datetime.now().isoformat()
        self.gcode_pause_all.clear()

    async def stop_plotter(self) -> Dict[str, Any]:
        """Stop plotter immediately and cancel any running G-code jobs."""
        try:
            self.cancel_all_gcode_jobs()

            stop_sent = False
            
            # Use PlotterCore if available
            if self.plotter_core and self.plotter_core.online:
                try:
                    # Cancel any running print
                    if self.plotter_core.printing:
                        self.plotter_core.cancelprint()
                    # Send emergency stop via priority queue
                    self.plotter_core.send_now("M112")
                    stop_sent = True
                except Exception as exc:
                    logger.warning("Failed to send stop command via PlotterCore: %s", exc)
            elif self.arduino and getattr(self.arduino, "is_open", False):
                try:
                    self.arduino.write(b"M112\n")
                    stop_sent = True
                except Exception as exc:
                    logger.warning("Failed to send stop command: %s", exc)

            self.current_status["drawing"] = False
            self.current_status["current_command"] = None

            with self._gcode_jobs_lock:
                canceled_jobs = [job_id for job_id, job in self.gcode_jobs.items() if job.get("cancel_requested")]
            
            return {
                "success": True,
                "message": "Stop requested",
                "stop_sent": stop_sent,
                "canceled_jobs": canceled_jobs,
            }
        except Exception as exc:
            logger.error("Stop error: %s", exc)
            return {"success": False, "error": str(exc)}

    async def pause_plotter(self) -> Dict[str, Any]:
        """Toggle pause/resume: on pause send M0, on resume clear pause flag."""
        try:
            was_paused = self.gcode_pause_all.is_set()
            
            # Use PlotterCore if available
            if self.plotter_core and self.plotter_core.online:
                if was_paused:
                    # Resume
                    if self.plotter_core.paused:
                        self.plotter_core.resume()
                    self.gcode_pause_all.clear()
                    with self._gcode_jobs_lock:
                        for job in self.gcode_jobs.values():
                            if job.get("status") == "paused":
                                job["status"] = "running"
                                job["paused"] = False
                    return {"success": True, "message": "Resume requested", "paused": False}
                else:
                    # Pause
                    if self.plotter_core.printing:
                        self.plotter_core.pause()
                    self.gcode_pause_all.set()
                    with self._gcode_jobs_lock:
                        for job in self.gcode_jobs.values():
                            if job.get("status") in {"queued", "running"}:
                                job["paused"] = True
                                job["status"] = "paused"
                    
                    # Send pause command via priority queue
                    pause_sent = False
                    try:
                        self.plotter_core.send_now("M0")
                        pause_sent = True
                    except Exception as exc:
                        logger.warning("Failed to send pause command via PlotterCore: %s", exc)
                    
                    return {"success": True, "message": "Pause requested", "paused": True, "pause_sent": pause_sent}
            
            # Fallback to old method
            if was_paused:
                self.gcode_pause_all.clear()
                with self._gcode_jobs_lock:
                    for job in self.gcode_jobs.values():
                        if job.get("status") == "paused":
                            job["status"] = "running"
                            job["paused"] = False
                return {"success": True, "message": "Resume requested", "paused": False}

            self.gcode_pause_all.set()
            with self._gcode_jobs_lock:
                for job in self.gcode_jobs.values():
                    if job.get("status") in {"queued", "running"}:
                        job["paused"] = True
                        job["status"] = "paused"

            pause_sent = False
            if self.arduino and getattr(self.arduino, "is_open", False):
                try:
                    self.arduino.write(b"M0\n")
                    pause_sent = True
                except Exception as exc:
                    logger.warning("Failed to send pause command: %s", exc)

            return {"success": True, "message": "Pause requested", "paused": True, "pause_sent": pause_sent}
        except Exception as exc:
            logger.error("Pause error: %s", exc)
            return {"success": False, "error": str(exc)}
    
    def start_gcode_print(self, commands: List[str], job_id: str) -> bool:
        """Start printing G-code commands using PlotterCore.
        
        Args:
            commands: List of G-code commands to print
            job_id: Job ID for tracking
            
        Returns:
            True if print started successfully, False otherwise
        """
        if self.plotter_core and self.plotter_core.online:
            success = self.plotter_core.startprint(commands)
            if success:
                with self._gcode_jobs_lock:
                    if job_id in self.gcode_jobs:
                        self.gcode_jobs[job_id]["status"] = "running"
                self.current_status["drawing"] = True
            return success
        return False


plotter_service = PlotterService()




