# Docker Serial Port Access Guide

This guide explains how to expose serial ports (COM ports) from your host machine to the Docker container for Arduino/plotter communication.

## Linux Systems

### Finding Your Serial Port

1. **List available serial ports:**
   ```bash
   ls -l /dev/ttyUSB* /dev/ttyACM*
   ```

2. **Check with dmesg after plugging in Arduino:**
   ```bash
   dmesg | tail
   ```

3. **Common Arduino port names:**
   - `/dev/ttyUSB0` - USB-to-Serial adapters
   - `/dev/ttyACM0` - Arduino Uno/Nano (CDC ACM)
   - `/dev/ttyACM1` - Second Arduino device

### Docker Compose Configuration

The `docker-compose.yml` file includes device mappings. Update the `devices` section in the backend service:

```yaml
devices:
  - /dev/ttyUSB0:/dev/ttyUSB0  # Your actual port
  - /dev/ttyACM0:/dev/ttyACM0  # If you have multiple devices
```

### Permission Issues

If you encounter permission errors (`Permission denied: /dev/ttyUSB0`):

**Option 1: Add user to dialout group (Recommended)**
```bash
sudo usermod -a -G dialout $USER
# Log out and back in for changes to take effect
```

**Option 2: Use privileged mode (Less secure)**
Add to docker-compose.yml:
```yaml
privileged: true
```

**Option 3: Modify Dockerfile to add user to dialout group**
Add to backend Dockerfile before USER command:
```dockerfile
RUN usermod -a -G dialout appuser
```

### Testing

1. **Start the container:**
   ```bash
   docker-compose up backend
   ```

2. **Check if device is accessible inside container:**
   ```bash
   docker-compose exec backend ls -l /dev/ttyUSB0
   ```

3. **Test serial port access:**
   ```bash
   docker-compose exec backend python -c "import serial; s = serial.Serial('/dev/ttyUSB0', 9600); print('Connected!'); s.close()"
   ```

## Windows Systems

### Docker Desktop on Windows

Docker Desktop on Windows uses WSL2, which complicates COM port access. Here are your options:

#### Option 1: Use WSL2 USB Passthrough (Recommended for WSL2)

1. **Install usbipd-win** (Windows USB/IP tool):
   ```powershell
   winget install usbipd
   ```

2. **List USB devices:**
   ```powershell
   usbipd list
   ```

3. **Bind Arduino device to WSL2:**
   ```powershell
   usbipd bind --busid <BUSID>
   # Then in WSL2:
   usbipd attach --remote=localhost --busid <BUSID>
   ```

4. **Find device in WSL2:**
   ```bash
   ls -l /dev/ttyUSB* /dev/ttyACM*
   ```

5. **Update docker-compose.yml** with the WSL2 device path

#### Option 2: Use COM Port Mapping (Docker Desktop)

Docker Desktop can map Windows COM ports, but this requires additional setup:

1. **Enable COM port support in Docker Desktop:**
   - Open Docker Desktop Settings
   - Go to Resources → WSL Integration
   - Enable integration with your WSL2 distribution

2. **Access COM ports via WSL2:**
   COM ports appear as `/dev/ttyS#` in WSL2, but this is unreliable.

#### Option 3: Run Backend Outside Docker (Development)

For development on Windows, you may want to run the backend directly:

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The frontend can still run in Docker and connect to `http://host.docker.internal:8000`.

### Finding Your COM Port on Windows

1. **Device Manager:**
   - Open Device Manager
   - Look under "Ports (COM & LPT)"
   - Note the COM port number (e.g., COM3, COM4)

2. **PowerShell:**
   ```powershell
   Get-WmiObject Win32_SerialPort | Select-Object Name, DeviceID
   ```

## Raspberry Pi / Linux Host

If running Docker on a Raspberry Pi:

1. **Find your serial port:**
   ```bash
   ls -l /dev/ttyUSB* /dev/ttyACM* /dev/ttyAMA0
   ```

2. **Update docker-compose.yml:**
   ```yaml
   devices:
     - /dev/ttyUSB0:/dev/ttyUSB0  # Or your actual port
   ```

3. **Ensure user permissions:**
   ```bash
   sudo usermod -a -G dialout $USER
   ```

## Troubleshooting

### Device Not Found

1. **Check if device exists on host:**
   ```bash
   ls -l /dev/ttyUSB0
   ```

2. **Verify device is accessible:**
   ```bash
   sudo chmod 666 /dev/ttyUSB0  # Temporary fix
   ```

3. **Check Docker container can see device:**
   ```bash
   docker-compose exec backend ls -l /dev/
   ```

### Permission Denied

1. **Add user to dialout group:**
   ```bash
   sudo usermod -a -G dialout $USER
   ```

2. **Or use privileged mode** (less secure):
   ```yaml
   privileged: true
   ```

### Device Busy

1. **Check if another process is using the port:**
   ```bash
   lsof /dev/ttyUSB0
   ```

2. **Kill the process if needed:**
   ```bash
   sudo kill <PID>
   ```

### Windows-Specific Issues

- **COM ports don't appear in WSL2:** Use usbipd-win or run backend outside Docker
- **Permission errors:** Run Docker Desktop as Administrator (not recommended)
- **Device disconnects:** Check USB cable and power supply

## Dynamic Port Detection

The application now supports dynamic port selection through the web UI. You can:

1. Connect to the plotter control page
2. Click "Refresh Ports" to scan for available ports
3. Select your port from the dropdown
4. Connect with the specified baud rate

This eliminates the need to hardcode device paths in docker-compose.yml for most use cases.

## Production Considerations

For production deployments:

1. **Use specific device paths** in docker-compose.prod.yml
2. **Set proper permissions** via Dockerfile or privileged mode
3. **Monitor device availability** - implement reconnection logic
4. **Consider device persistence** - USB devices may change paths on reboot

## Example: Complete docker-compose.yml for Linux

```yaml
backend:
  # ... other config ...
  devices:
    - /dev/ttyUSB0:/dev/ttyUSB0
  # Or use privileged mode:
  # privileged: true
```

## Example: Windows Development Setup

```yaml
backend:
  # ... other config ...
  # For Windows, consider running backend outside Docker
  # Or use WSL2 with usbipd-win
  extra_hosts:
    - "host.docker.internal:host-gateway"
```

## Additional Resources

- [Docker Device Access Documentation](https://docs.docker.com/engine/reference/run/#runtime-privilege-and-linux-capabilities)
- [PySerial Documentation](https://pyserial.readthedocs.io/)
- [usbipd-win GitHub](https://github.com/dorssel/usbipd-win)

