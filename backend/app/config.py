import os
from typing import List

class Settings:
    """Application settings for PolarVortex backend"""
    
    # API Configuration
    API_TITLE: str = "PolarVortex API"
    API_VERSION: str = "1.0.0"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173"
    ]
    
    # Arduino Configuration
    ARDUINO_BAUDRATE: int = 9600
    ARDUINO_TIMEOUT: int = 1
    ARDUINO_PORTS: List[str] = [
        '/dev/ttyUSB0',
        '/dev/ttyACM0',
        'COM3',
        'COM4',
        'COM5',
        'COM6',
        'COM7',
        'COM8'
    ]
    
    # Image Processing Configuration
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_TYPES: List[str] = [
        'image/jpeg',
        'image/jpg',
        'image/png',
        'image/gif',
        'image/bmp'
    ]
    
    # Resolution presets
    RESOLUTION_PRESETS = {
        "low": (400, 300),
        "medium": (800, 600),
        "high": (1200, 900),
        "ultra": (1600, 1200)
    }
    
    # File Storage
    PROCESSED_IMAGES_DIR: str = "processed_images"
    UPLOADS_DIR: str = "uploads"
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # WebSocket Configuration
    WS_PING_INTERVAL: int = 30  # seconds
    WS_PING_TIMEOUT: int = 10   # seconds
    
    # Plotting Configuration
    DEFAULT_THRESHOLD: int = 128
    DEFAULT_DITHER: bool = True
    DEFAULT_INVERT: bool = False
    
    @classmethod
    def get_arduino_ports(cls) -> List[str]:
        """Get Arduino ports with environment variable override"""
        env_ports = os.getenv("ARDUINO_PORTS")
        if env_ports:
            return env_ports.split(",")
        return cls.ARDUINO_PORTS
    
    @classmethod
    def get_cors_origins(cls) -> List[str]:
        """Get CORS origins with environment variable override"""
        env_origins = os.getenv("CORS_ORIGINS")
        if env_origins:
            return env_origins.split(",")
        return cls.CORS_ORIGINS

# Create settings instance
settings = Settings()

