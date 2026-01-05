"""
Device abstraction for serial communication.
Extracted and simplified from Printrun's device.py
"""
import logging
import platform
import serial

logger = logging.getLogger(__name__)

READ_EMPTY = b''
READ_EOF = None


class DeviceError(Exception):
    """Raised on any connection error."""
    def __init__(self, msg, cause=None):
        super().__init__(msg)
        self.cause = cause


class PlotterDevice:
    """Handler for serial connections to the plotter."""
    
    def __init__(self, port=None, baudrate=115200, force_dtr=None):
        self.port = port
        self.baudrate = baudrate
        self.force_dtr = force_dtr
        self._device = None
        self._is_connected = False
        self._timeout = 0.25
    
    @property
    def is_connected(self):
        """True if connection to device is alive."""
        return self._device is not None and self._device.is_open
    
    @property
    def has_flow_control(self):
        """Serial connections don't have flow control."""
        return False
    
    def connect(self, port=None, baudrate=None):
        """Establish connection to the device.
        
        Raises:
            DeviceError: If connection fails.
        """
        if port is not None:
            self.port = port
        if baudrate is not None:
            self.baudrate = baudrate
        
        if self.port is None:
            raise DeviceError("No port specified")
        
        self._disable_ttyhup()
        
        try:
            self._device = serial.Serial(
                baudrate=self.baudrate,
                timeout=self._timeout,
                parity=serial.PARITY_NONE
            )
            self._device.port = self.port
            
            if self.force_dtr is not None:
                self._device.dtr = self.force_dtr
            
            self._device.open()
            self._is_connected = True
        except (serial.SerialException, IOError) as e:
            msg = f"Could not connect to serial port '{self.port}'"
            raise DeviceError(msg, e) from e
    
    def disconnect(self):
        """Terminate connection to the device."""
        if self._device is not None:
            try:
                self._device.close()
            except serial.SerialException as e:
                msg = "Error on serial disconnection"
                raise DeviceError(msg, e) from e
        self._device = None
        self._is_connected = False
    
    def readline(self):
        """Read one line from the device stream.
        
        Returns:
            bytes: Array containing feedback from device.
            READ_EMPTY if no data available.
            READ_EOF if connection terminated.
        """
        if self._device is None:
            raise DeviceError("Attempted to read when disconnected")
        
        try:
            # Serial.readline() returns b'' (READ_EMPTY) on timeout
            return self._device.readline()
        except (serial.SerialException, OSError) as e:
            msg = f"Unable to read from serial port '{self.port}'"
            raise DeviceError(msg, e) from e
    
    def write(self, data: bytes):
        """Write data to the connected device.
        
        Args:
            data: The bytes data to be written.
            
        Raises:
            TypeError: If data is not bytes.
            DeviceError: If write fails.
        """
        if self._device is None:
            raise DeviceError("Attempted to write when disconnected")
        
        if not isinstance(data, bytes):
            raise TypeError("data must be bytes")
        
        try:
            self._device.write(data)
        except serial.SerialException as e:
            msg = f"Unable to write to serial port '{self.port}'"
            raise DeviceError(msg, e) from e
    
    def reset(self):
        """Attempt to reset the connection (DTR pulse)."""
        if self._device is not None and self._device.is_open:
            self._device.dtr = True
            import time
            time.sleep(0.2)
            self._device.dtr = False
    
    def _disable_ttyhup(self):
        """Disable HUPCL on Linux."""
        if platform.system() == "Linux" and self.port:
            import os
            try:
                os.system(f"stty -F {self.port} -hup")
            except Exception:
                pass  # Best effort, may fail on some systems
