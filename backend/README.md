# PolarVortex Backend

A FastAPI-based backend for the PolarVortex polargraph plotter control system. Provides image processing, Arduino communication, and real-time WebSocket updates.

## Features

- **Image Processing**: Advanced image processing with multiple algorithms
- **Arduino Communication**: Serial communication with polargraph hardware
- **Real-time Updates**: WebSocket support for live status updates
- **REST API**: Comprehensive REST endpoints for all operations
- **CORS Support**: Cross-origin resource sharing for frontend integration
- **Error Handling**: Robust error handling and logging

## Technology Stack

- **FastAPI**: Modern, fast web framework for building APIs
- **OpenCV**: Computer vision library for image processing
- **Pillow**: Python Imaging Library for image manipulation
- **NumPy**: Numerical computing library
- **PySerial**: Serial communication library
- **WebSockets**: Real-time bidirectional communication

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Arduino IDE (for uploading sketch to Arduino)

### Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   ```bash
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Create necessary directories:
   ```bash
   mkdir processed_images
   mkdir uploads
   ```

## Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Arduino Configuration
ARDUINO_PORTS=COM3,COM4,/dev/ttyUSB0,/dev/ttyACM0

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Logging
LOG_LEVEL=INFO
```

### Arduino Setup

1. Upload the `polargraph.ino` sketch to your Arduino
2. Connect Arduino via USB
3. Note the COM port (Windows) or device path (Linux/macOS)
4. Update the `ARDUINO_PORTS` environment variable if needed

## Running the Backend

### Development Mode

```bash
# Run with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
# Run with production server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker

```bash
# Build image
docker build -t polarvortex-backend .

# Run container
docker run -p 8000:8000 --device=/dev/ttyUSB0 polarvortex-backend
```

## API Documentation

Once the server is running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc

### Core Endpoints

#### Status
- `GET /status` - Get current system status
- `GET /` - API information and health check

#### Commands
- `POST /command/{cmd}` - Send command to Arduino
  - Commands: `START`, `STOP`, `PAUSE`, `RESUME`, `STATUS`

#### Image Processing
- `POST /upload` - Upload and process image
- `GET /projects` - List processed images

#### WebSocket
- `WS /ws` - Real-time status updates

## Image Processing

### Supported Formats
- JPEG/JPG
- PNG
- GIF
- BMP
- TIFF

### Processing Options

#### Resolution Presets
- `low`: 400x300
- `medium`: 800x600
- `high`: 1200x900
- `ultra`: 1600x1200
- `custom`: User-defined dimensions

#### Processing Settings
- `threshold`: Black/white conversion threshold (0-255)
- `invert`: Invert image colors
- `dither`: Enable Floyd-Steinberg dithering
- `enhance_contrast`: Enhance image contrast
- `reduce_noise`: Apply Gaussian blur for noise reduction
- `plotting_strategy`: Point selection strategy
  - `all_points`: Include all black pixels
  - `contour`: Plot only contour points
  - `sampled`: Sample points at regular intervals

### Example Upload Request

```python
import requests

url = "http://localhost:8000/upload"
files = {"file": open("image.jpg", "rb")}
data = {
    "settings": json.dumps({
        "resolution": "medium",
        "threshold": 128,
        "dither": True,
        "invert": False
    })
}

response = requests.post(url, files=files, data=data)
print(response.json())
```

## WebSocket Communication

### Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = function() {
    console.log('Connected to PolarVortex');
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};
```

### Message Types

#### Status Updates
```json
{
    "type": "status_update",
    "command": "START",
    "drawing": true,
    "progress": 25
}
```

#### Image Processed
```json
{
    "type": "image_processed",
    "filename": "image.jpg",
    "processed_size": [800, 600],
    "plotting_points": 15000
}
```

#### Connection Established
```json
{
    "type": "connection_established",
    "message": "Connected to PolarVortex"
}
```

## Arduino Communication

### Serial Protocol

The backend communicates with Arduino using simple text commands:

- `START` - Start drawing
- `STOP` - Stop drawing
- `PAUSE` - Pause drawing
- `RESUME` - Resume drawing
- `STATUS` - Request status update

### Expected Arduino Responses

- `READY` - System ready
- `DRAWING` - Currently drawing
- `PAUSED` - Drawing paused
- `COMPLETE` - Drawing complete
- `ERROR: <message>` - Error occurred

## Error Handling

### Common Errors

1. **Arduino Not Connected**
   - Check USB connection
   - Verify correct COM port
   - Ensure Arduino sketch is uploaded

2. **Image Processing Errors**
   - Check file format support
   - Verify file size limits
   - Ensure sufficient memory

3. **WebSocket Connection Issues**
   - Check CORS configuration
   - Verify WebSocket endpoint
   - Check network connectivity

### Logging

Logs are written to console with different levels:
- `INFO`: General information
- `WARNING`: Non-critical issues
- `ERROR`: Error conditions
- `DEBUG`: Detailed debugging information

## Development

### Project Structure
```
backend/
├── app/
│   ├── main.py              # Main FastAPI application
│   ├── config.py            # Configuration settings
│   ├── image_processor.py   # Image processing module
│   └── __init__.py
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker configuration
├── .env                    # Environment variables
└── README.md              # This file
```

### Adding New Features

1. **New API Endpoints**: Add to `main.py`
2. **Image Processing**: Extend `image_processor.py`
3. **Configuration**: Update `config.py`
4. **Dependencies**: Add to `requirements.txt`

### Testing

```bash
# Run tests (when implemented)
pytest

# Test API endpoints
curl http://localhost:8000/status
curl http://localhost:8000/
```

## Deployment

### Production Considerations

1. **Security**
   - Use HTTPS in production
   - Implement authentication
   - Validate all inputs

2. **Performance**
   - Use production ASGI server (Gunicorn + Uvicorn)
   - Implement caching
   - Optimize image processing

3. **Monitoring**
   - Add health checks
   - Implement logging
   - Monitor system resources

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Find process using port 8000
   lsof -i :8000
   # Kill process
   kill -9 <PID>
   ```

2. **Arduino Permission Issues (Linux)**
   ```bash
   # Add user to dialout group
   sudo usermod -a -G dialout $USER
   # Reboot or logout/login
   ```

3. **Missing Dependencies**
   ```bash
   # Reinstall requirements
   pip install -r requirements.txt --force-reinstall
   ```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is part of the PolarVortex polargraph plotter control system.

