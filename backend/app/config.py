import os
import yaml
from typing import List, Dict, Any
from pathlib import Path

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


class Config:
    """Configuration class that loads settings from YAML file specified by PV_CONFIG environment variable"""
    
    def __init__(self):
        """Initialize configuration by loading from YAML file"""
        self._config_data = {}
        self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file specified by PV_CONFIG environment variable"""
        config_file_path = os.getenv("PV_CONFIG")
        
        if not config_file_path:
            # If no config file specified, use default location
            config_file_path = "/app/local_storage/config/config.yaml"
        
        config_path = Path(config_file_path)
        
        if not config_path.exists():
                self._create_default_config_file(config_path)

        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                self._config_data = yaml.safe_load(file) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration file: {e}")
        except Exception as e:
            raise RuntimeError(f"Error loading configuration file: {e}")
    
    def _create_default_config_file(self, config_path: Path):
        """Create default configuration file with default values"""
        try:
            # Ensure the directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Get default configuration
            default_config = self._get_default_config()
            
            # Write the default configuration to file
            with open(config_path, 'w', encoding='utf-8') as file:
                yaml.dump(default_config, file, default_flow_style=False, indent=2, sort_keys=False)
            
            # Set the config data to the defaults
            self._config_data = default_config
            
        except Exception as e:
            raise RuntimeError(f"Error creating default configuration file: {e}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values"""
        return {
            "api": {
                "title": "PolarVortex API",
                "version": "1.0.0",
                "host": "0.0.0.0",
                "port": 8000
            },
            "cors": {
                "origins": [
                    "http://localhost:3000",
                    "http://127.0.0.1:3000",
                    "http://localhost:5173",
                    "http://127.0.0.1:5173"
                ]
            },
            "arduino": {
                "baudrate": 9600,
                "timeout": 1,
                "ports": [
                    '/dev/ttyUSB0',
                    '/dev/ttyACM0',
                    'COM3',
                    'COM4',
                    'COM5',
                    'COM6',
                    'COM7',
                    'COM8'
                ]
            },
            "image_processing": {
                "max_file_size": 10485760,  # 10MB
                "allowed_types": [
                    'image/jpeg',
                    'image/jpg',
                    'image/png',
                    'image/gif',
                    'image/bmp'
                ],
                "resolution_presets": {
                    "low": [400, 300],
                    "medium": [800, 600],
                    "high": [1200, 900],
                    "ultra": [1600, 1200]
                }
            },
            "storage": {
                "processed_images_dir": "processed_images",
                "uploads_dir": "uploads"
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "websocket": {
                "ping_interval": 30,
                "ping_timeout": 10
            },
            "plotting": {
                "default_threshold": 128,
                "default_dither": True,
                "default_invert": False
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'api.port')"""
        keys = key.split('.')
        value = self._config_data
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_api_title(self) -> str:
        """Get API title"""
        return self.get('api.title', 'PolarVortex API')
    
    def get_api_version(self) -> str:
        """Get API version"""
        return self.get('api.version', '1.0.0')
    
    def get_api_host(self) -> str:
        """Get API host"""
        return self.get('api.host', '0.0.0.0')
    
    def get_api_port(self) -> int:
        """Get API port"""
        return self.get('api.port', 8000)
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins"""
        return self.get('cors.origins', [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173"
        ])
    
    def get_arduino_baudrate(self) -> int:
        """Get Arduino baudrate"""
        return self.get('arduino.baudrate', 9600)
    
    def get_arduino_timeout(self) -> int:
        """Get Arduino timeout"""
        return self.get('arduino.timeout', 1)
    
    def get_arduino_ports(self) -> List[str]:
        """Get Arduino ports"""
        return self.get('arduino.ports', [
            '/dev/ttyUSB0',
            '/dev/ttyACM0',
            'COM3',
            'COM4',
            'COM5',
            'COM6',
            'COM7',
            'COM8'
        ])
    
    def get_max_file_size(self) -> int:
        """Get maximum file size"""
        return self.get('image_processing.max_file_size', 10485760)
    
    def get_allowed_image_types(self) -> List[str]:
        """Get allowed image types"""
        return self.get('image_processing.allowed_types', [
            'image/jpeg',
            'image/jpg',
            'image/png',
            'image/gif',
            'image/bmp'
        ])
    
    def get_resolution_presets(self) -> Dict[str, List[int]]:
        """Get resolution presets"""
        return self.get('image_processing.resolution_presets', {
            "low": [400, 300],
            "medium": [800, 600],
            "high": [1200, 900],
            "ultra": [1600, 1200]
        })
    
    def get_processed_images_dir(self) -> str:
        """Get processed images directory"""
        return self.get('storage.processed_images_dir', 'processed_images')
    
    def get_uploads_dir(self) -> str:
        """Get uploads directory"""
        return self.get('storage.uploads_dir', 'uploads')
    
    def get_log_level(self) -> str:
        """Get log level"""
        return self.get('logging.level', 'INFO')
    
    def get_log_format(self) -> str:
        """Get log format"""
        return self.get('logging.format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    def get_ws_ping_interval(self) -> int:
        """Get WebSocket ping interval"""
        return self.get('websocket.ping_interval', 30)
    
    def get_ws_ping_timeout(self) -> int:
        """Get WebSocket ping timeout"""
        return self.get('websocket.ping_timeout', 10)
    
    def get_default_threshold(self) -> int:
        """Get default threshold"""
        return self.get('plotting.default_threshold', 128)
    
    def get_default_dither(self) -> bool:
        """Get default dither setting"""
        return self.get('plotting.default_dither', True)
    
    def get_default_invert(self) -> bool:
        """Get default invert setting"""
        return self.get('plotting.default_invert', False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Return the entire configuration as a dictionary"""
        return self._config_data.copy()


# Create config instance
config = Config()

