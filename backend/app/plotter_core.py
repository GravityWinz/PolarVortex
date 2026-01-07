"""
Core plotter communication library.
Extracted and adapted from Printrun's printcore.py

Provides proper flow control, command queuing, checksums, and resend handling
to prevent missed commands and ensure reliable communication.
"""
import logging
import threading
import time
from functools import wraps, reduce
from queue import Queue, Empty as QueueEmpty
from collections import deque
from typing import Optional, Callable, List, Dict, Any

from .plotter_device import PlotterDevice, DeviceError, READ_EOF, READ_EMPTY

logger = logging.getLogger(__name__)

PR_EOF = None
PR_AGAIN = b''


def locked(f):
    """Decorator to make a method thread-safe."""
    @wraps(f)
    def inner(*args, **kw):
        with inner.lock:
            return f(*args, **kw)
    inner.lock = threading.Lock()
    return inner


class PlotterCore:
    """
    Core plotter communication with proper flow control, command queuing,
    and resend handling.
    
    Features:
    - Dual queue system: priority queue for immediate commands (stop, pause),
      main queue for G-code file streaming
    - Flow control: waits for 'ok' before sending next command
    - Command numbering and checksums for serial connections
    - Resend handling when printer requests resend
    - Separate read and send threads for reliable communication
    """
    
    def __init__(self, port=None, baud=None, dtr=None):
        self.port = port
        self.baud = baud
        self.dtr = dtr
        
        # Device connection
        self.device: Optional[PlotterDevice] = None
        
        # Flow control: clear to send (enabled after 'ok' responses)
        self.clear = True
        
        # Connection state
        self.online = False
        
        # Printing state
        self.printing = False
        self.paused = False
        
        # Command queues
        self.priqueue = Queue(0)  # Priority queue for immediate commands
        self.mainqueue: Optional[List[str]] = None  # Main queue for print jobs
        self.queueindex = 0
        self._queue_lock = threading.Lock()  # Lock for thread-safe queue access
        
        # Command numbering and resend
        self.lineno = 0
        self.resendfrom = -1
        self.sentlines: Dict[int, str] = {}
        
        # Logging
        self.log = deque(maxlen=10000)
        self.sent: List[str] = []
        self.writefailures = 0
        
        # Threads
        self.read_thread: Optional[threading.Thread] = None
        self.stop_read_thread = False
        self.send_thread: Optional[threading.Thread] = None
        self.stop_send_thread = False
        self.print_thread: Optional[threading.Thread] = None
        
        # Greetings that indicate printer is online
        self.greetings = ['start', 'Grbl ']
        
        # Callbacks
        self.callbacks: Dict[str, List[Callable]] = {
            'send': [],
            'recv': [],
            'online': [],
            'error': [],
        }
        
        # Auto-connect if port/baud provided
        if port is not None and baud is not None:
            self.connect(port, baud, dtr)
    
    def add_callback(self, event: str, callback: Callable):
        """Add a callback for an event.
        
        Args:
            event: Event name ('send', 'recv', 'online', 'error')
            callback: Callback function to call
        """
        if event not in self.callbacks:
            self.callbacks[event] = []
        self.callbacks[event].append(callback)
    
    def _trigger_callback(self, event: str, *args):
        """Trigger all callbacks for an event."""
        for callback in self.callbacks.get(event, []):
            try:
                callback(*args)
            except Exception as e:
                logger.error(f"Callback {event} failed: {e}", exc_info=True)
    
    @locked
    def connect(self, port=None, baud=None, dtr=None):
        """Connect to plotter.
        
        Args:
            port: Serial port name
            baud: Baud rate
            dtr: DTR setting (optional)
        """
        if self.device:
            self.disconnect()
        
        if port is not None:
            self.port = port
        if baud is not None:
            self.baud = baud
        if dtr is not None:
            self.dtr = dtr
        
        if self.port is None or self.baud is None:
            return
        
        self.writefailures = 0
        self.device = PlotterDevice(port=self.port, baudrate=self.baud, force_dtr=self.dtr)
        
        try:
            self.device.connect()
        except DeviceError as e:
            logger.error(f"Connection error: {e}")
            self.device = None
            return
        
        self.stop_read_thread = False
        self.read_thread = threading.Thread(target=self._listen, name='read thread', daemon=True)
        self.read_thread.start()
        self._start_sender()
    
    @locked
    def disconnect(self):
        """Disconnect from plotter."""
        if self.device:
            if self.read_thread:
                self.stop_read_thread = True
                if threading.current_thread() != self.read_thread:
                    self.read_thread.join(timeout=1.0)
                self.read_thread = None
            
            if self.print_thread:
                self.printing = False
                if threading.current_thread() != self.print_thread:
                    self.print_thread.join(timeout=1.0)
                self.print_thread = None
            
            self._stop_sender()
            
            try:
                self.device.disconnect()
            except DeviceError:
                pass
        
        self.device = None
        self.online = False
        self.printing = False
    
    def reset(self):
        """Reset connection (DTR pulse)."""
        if self.device:
            self.device.reset()
    
    def _checksum(self, command: str) -> int:
        """Calculate checksum for command."""
        return reduce(lambda x, y: x ^ y, map(ord, command))
    
    def _readline(self):
        """Read a line from the device."""
        try:
            line_bytes = self.device.readline()
            if line_bytes is READ_EOF or line_bytes is None:
                logger.error("Can't read from plotter (disconnected?)")
                self.stop_read_thread = True
                return PR_EOF
            
            line = line_bytes.decode('utf-8', errors='ignore')
            
            if len(line) > 1:
                self.log.append(line)
                self._trigger_callback('recv', line)
                logger.debug(f"RECV: {line.rstrip()}")
            
            return line
        except UnicodeDecodeError:
            msg = f"Got invalid reply from {self.port} at baudrate {self.baud}: Maybe bad baudrate?"
            logger.error(msg)
            self._trigger_callback('error', msg)
            return None
        except DeviceError as e:
            msg = f"Can't read from plotter (disconnected?) {e}"
            logger.error(msg)
            self._trigger_callback('error', msg)
            return None
    
    def _listen_can_continue(self):
        """Check if listen thread should continue."""
        return (not self.stop_read_thread
                and self.device
                and self.device.is_connected)
    
    def _listen_until_online(self):
        """Listen until plotter comes online."""
        while not self.online and self._listen_can_continue():
            self._send("M105", wait_for_ok=False)
            if self.writefailures >= 4:
                logger.error("Aborting connection attempt after 4 failed writes.")
                return
            
            empty_lines = 0
            while self._listen_can_continue():
                line = self._readline()
                if line is None:
                    break
                
                # Count empty lines (timeouts)
                if not line.strip():
                    empty_lines += 1
                    if empty_lines == 15:
                        break
                else:
                    empty_lines = 0
                
                if (line.startswith(tuple(self.greetings)) or
                    line.startswith('ok') or
                    "T:" in line):
                    self.online = True
                    self._trigger_callback('online')
                    return
    
    def _listen(self):
        """Listen thread - processes responses from plotter."""
        self.clear = True
        if not self.printing:
            self._listen_until_online()
        
        while self._listen_can_continue():
            line = self._readline()
            if line is None:
                break
            
            if line.startswith('DEBUG_'):
                continue
            
            # Handle 'ok' responses
            if line.startswith(tuple(self.greetings)) or line.startswith('ok'):
                self.clear = True
            
            # Handle temperature responses
            if line.startswith('ok') and "T:" in line:
                self._trigger_callback('recv', line)
            
            # Handle errors
            if line.startswith('Error'):
                self._trigger_callback('error', line)
            
            # Handle resend requests
            if line.lower().startswith("resend") or line.startswith("rs"):
                # Parse resend line number
                for haystack in ["N:", "N", ":"]:
                    line = line.replace(haystack, " ")
                linewords = line.split()
                while len(linewords) != 0:
                    try:
                        toresend = int(linewords.pop(0))
                        self.resendfrom = toresend
                        break
                    except (ValueError, IndexError):
                        pass
                self.clear = True
        
        self.clear = True
        logger.debug('Exiting read thread')
    
    def _start_sender(self):
        """Start the sender thread."""
        self.stop_send_thread = False
        self.send_thread = threading.Thread(target=self._sender, name='send thread', daemon=True)
        self.send_thread.start()
    
    def _stop_sender(self):
        """Stop the sender thread."""
        if self.send_thread:
            self.stop_send_thread = True
            self.send_thread.join(timeout=1.0)
            self.send_thread = None
    
    def _sender(self):
        """Sender thread - sends commands from priority queue when not printing."""
        while not self.stop_send_thread:
            try:
                command = self.priqueue.get(True, 0.1)
            except QueueEmpty:
                continue
            
            # Wait for clear if printing
            while self.device and self.printing and not self.clear:
                time.sleep(0.001)
            
            self._send(command, wait_for_ok=True)
            
            # Wait for clear after sending
            while self.device and self.printing and not self.clear:
                time.sleep(0.001)
    
    def _send(self, command: str, lineno: int = 0, calcchecksum: bool = False, wait_for_ok: bool = True):
        """Send a command to the plotter.
        
        Args:
            command: G-code command to send
            lineno: Line number for checksum (if calcchecksum is True)
            calcchecksum: Whether to add line number and checksum
            wait_for_ok: Whether to wait for 'ok' response (sets clear=False)
        """
        if not self.device:
            return
        
        original_command = command
        
        # Add checksum and line number for serial connections
        if calcchecksum and not self.device.has_flow_control:
            prefix = f"N{lineno} {command}"
            checksum = self._checksum(prefix)
            command = f"{prefix}*{checksum}"
            if "M110" not in command:
                self.sentlines[lineno] = command
        
        # Store command
        self.sent.append(command)
        self._trigger_callback('send', command, original_command)
        logger.debug(f"SENT: {command}")
        
        # Send to device
        try:
            self.device.write((command + "\n").encode('ascii'))
            self.writefailures = 0
            
            # Wait for 'ok' if requested
            if wait_for_ok:
                self.clear = False
                timeout = 5.0  # 5 second timeout
                start = time.time()
                while not self.clear and (time.time() - start) < timeout:
                    time.sleep(0.001)
                if not self.clear:
                    logger.warning(f"Timeout waiting for 'ok' after command: {command}")
        except DeviceError as e:
            msg = f"Can't write to plotter (disconnected?) {e}"
            logger.error(msg)
            self._trigger_callback('error', msg)
            self.writefailures += 1
    
    def send_now(self, command: str):
        """Send command immediately via priority queue.
        
        Use this for urgent commands like emergency stop (M112), pause (M0),
        or status queries (M105). These commands will interrupt the main
        print queue and be sent immediately.
        
        Args:
            command: G-code command to send
        """
        if self.online:
            self.priqueue.put_nowait(command)
        else:
            logger.warning("Not connected to plotter.")
    
    def send(self, command: str):
        """Send command (adds to main queue if printing, else priority queue).
        
        Args:
            command: G-code command to send
        """
        if self.online:
            if self.printing:
                if self.mainqueue is not None:
                    self.mainqueue.append(command)
            else:
                self.priqueue.put_nowait(command)
        else:
            logger.warning("Not connected to plotter.")
    
    def startprint(self, commands: List[str], startindex: int = 0) -> bool:
        """Start printing a list of G-code commands.
        
        Args:
            commands: List of G-code commands to print
            startindex: Index to start from (for resuming)
            
        Returns:
            True if print started successfully, False otherwise
        """
        if self.printing or not self.online or not self.device:
            return False
        
        with self._queue_lock:
            self.queueindex = startindex
            self.mainqueue = commands.copy() if commands else []
        self.printing = True
        self.lineno = 0
        self.resendfrom = -1
        
        if not self.mainqueue:
            return True
        
        self.clear = False
        self._send("M110 N-1", -1, True, wait_for_ok=False)
        
        resuming = (startindex != 0)
        self.print_thread = threading.Thread(
            target=self._print,
            name='print thread',
            daemon=True,
            kwargs={"resuming": resuming}
        )
        self.print_thread.start()
        return True
    
    def _print(self, resuming: bool = False):
        """Print thread - sends commands from main queue."""
        self._stop_sender()
        try:
            while self.printing and self.device and self.online:
                self._sendnext()
            
            self.sentlines = {}
            self.log.clear()
            self.sent = []
        except Exception as e:
            logger.error(f"Print thread error: {e}", exc_info=True)
        finally:
            self.print_thread = None
            self._start_sender()
    
    def _sendnext(self):
        """Send next command from queues. Priority queue takes precedence."""
        if not self.device:
            return
        
        # Wait for clear signal (waiting for 'ok' from previous command)
        while self.device and self.printing and not self.clear:
            time.sleep(0.001)
        
        # Only wait for oks when using serial (no flow control)
        if not self.device.has_flow_control:
            self.clear = False
        
        if not (self.printing and self.device and self.online):
            self.clear = True
            return
        
        # Handle resend requests first
        if self.resendfrom < self.lineno and self.resendfrom > -1:
            if self.resendfrom in self.sentlines:
                self._send(self.sentlines[self.resendfrom], self.resendfrom, False, wait_for_ok=True)
                self.resendfrom += 1
            return
        
        self.resendfrom = -1
        
        # PRIORITY 1: Check priority queue FIRST (emergency stop, pause, status, etc.)
        if not self.priqueue.empty():
            try:
                command = self.priqueue.get_nowait()
                self._send(command, wait_for_ok=True)
                self.priqueue.task_done()
            except QueueEmpty:
                pass
            return  # Priority command sent, exit (main queue waits)
        
        # PRIORITY 2: Send from main queue (G-code file streaming)
        if self.printing and self.mainqueue and self.queueindex < len(self.mainqueue):
            command = self.mainqueue[self.queueindex]
            
            # Strip comments
            if ";" in command:
                command = command.split(";", 1)[0].strip()
            
            if command:
                self._send(command, self.lineno, True, wait_for_ok=True)
                self.lineno += 1
            
            self.queueindex += 1
        else:
            # Print finished
            self.printing = False
            self.clear = True
            if not self.paused:
                self.queueindex = 0
                self.lineno = 0
                self._send("M110 N-1", -1, True, wait_for_ok=False)
    
    def pause(self):
        """Pause the current print.
        
        Returns:
            True if paused, False if not printing
        """
        if not self.printing:
            return False
        self.paused = True
        self.printing = False
        
        if not threading.current_thread() is self.print_thread:
            if self.print_thread:
                self.print_thread.join(timeout=1.0)
        self.print_thread = None
        return True
    
    def resume(self):
        """Resume a paused print.
        
        Returns:
            True if resumed, False if not paused
        """
        if not self.paused:
            return False
        self.paused = False
        self.printing = True
        self.print_thread = threading.Thread(
            target=self._print,
            name='print thread',
            daemon=True,
            kwargs={"resuming": True}
        )
        self.print_thread.start()
        return True
    
    def cancelprint(self):
        """Cancel the current print."""
        self.pause()
        self.paused = False
        with self._queue_lock:
            self.mainqueue = None
            self.queueindex = 0
        self.clear = True
