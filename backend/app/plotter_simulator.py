"""
Plotter Simulator Module

Provides a simulated plotter that mimics the serial.Serial interface.
All commands and responses are logged to Docker container logs.
"""
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Simulator port identifier
SIMULATOR_PORT_NAME = "SIMULATOR"


class PlotterSimulator:
    """
    Simulates a plotter connection by mimicking the serial.Serial interface.
    All commands are logged to Docker container logs instead of being sent to hardware.
    """
    
    def __init__(self, port: str, baudrate: int = 115200, timeout: Optional[float] = None):
        """
        Initialize the plotter simulator.
        
        Args:
            port: Port name (should be SIMULATOR_PORT_NAME)
            baudrate: Baud rate (for compatibility, not used)
            timeout: Read timeout (for compatibility, not used)
        """
        self._port = port
        self._baudrate = baudrate
        self._timeout = timeout
        self._is_open = True
        self._input_buffer = []  # Stores tuples of (response, command, timestamp)
        self._last_command = None
        
        logger.info(f"[SIMULATOR] Plotter simulator initialized on port '{port}' at {baudrate} baud")
    
    @property
    def is_open(self) -> bool:
        """Check if simulator connection is open."""
        return self._is_open
    
    @property
    def port(self) -> str:
        """Get the port name."""
        return self._port
    
    @property
    def baudrate(self) -> int:
        """Get the baud rate."""
        return self._baudrate
    
    @property
    def in_waiting(self) -> int:
        """
        Return number of bytes waiting in input buffer.
        Simulates having responses ready after commands.
        """
        if self._input_buffer:
            return sum(len(response.encode('utf-8')) for response, _, _ in self._input_buffer)
        return 0
    
    def write(self, data: bytes) -> int:
        """
        Write data to simulator (logs to Docker logs).
        
        Args:
            data: Bytes to write (typically G-code commands)
            
        Returns:
            Number of bytes written
        """
        if not self._is_open:
            raise RuntimeError("Simulator connection is closed")
        
        try:
            # Decode the command
            command = data.decode('utf-8', errors='ignore').strip()
            self._last_command = command
            
            # Store timestamp for logging
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # Format: HH:MM:SS.mmm
            
            # Simulate response based on command type
            response = self._generate_response(command)
            if response:
                # Store response with command and timestamp for combined logging
                self._input_buffer.append((response, command, timestamp))
            
            return len(data)
        except Exception as e:
            logger.error(f"[SIMULATOR] Error processing command: {e}")
            return 0
    
    def readline(self) -> bytes:
        """
        Read a line from the simulator's response buffer.
        
        Returns:
            Bytes containing the response line (with newline)
        """
        if not self._is_open:
            return b''
        
        if self._input_buffer:
            response, command, timestamp = self._input_buffer.pop(0)
            
            # Log in compressed format: [time] -> command <- response
            logger.info(f"[{timestamp}] -> {command} <- {response.strip()}")
            
            # Ensure response ends with newline
            if not response.endswith('\n'):
                response += '\n'
            return response.encode('utf-8')
        
        return b''
    
    def reset_input_buffer(self) -> None:
        """Clear the input buffer."""
        self._input_buffer.clear()
        logger.debug("[SIMULATOR] Input buffer reset")
    
    def close(self) -> None:
        """Close the simulator connection."""
        if self._is_open:
            self._is_open = False
            self._input_buffer.clear()
            logger.info(f"[SIMULATOR] Simulator connection closed on port '{self._port}'")
    
    def _generate_response(self, command: str) -> Optional[str]:
        """
        Generate a simulated response based on the command.
        
        Args:
            command: The command string
            
        Returns:
            Response string or None
        """
        cmd_upper = command.upper().strip()
        
        # G-code commands typically respond with "ok"
        if cmd_upper.startswith('G') or cmd_upper.startswith('M'):
            return "ok"
        
        # Status queries
        if cmd_upper == "STATUS":
            return "Status: Ready"
        
        if cmd_upper == "PING":
            return "PONG"
        
        # Default response for most commands
        if command:
            return "ok"
        
        return None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False

