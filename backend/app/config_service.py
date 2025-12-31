import os
import yaml
import json
import uuid
import copy
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from .config_models import (
    PlotterSettings, PaperSettings, PlotterCreate, PlotterUpdate,
    PaperCreate, PaperUpdate, PlotterResponse, PaperResponse,
    PlotterListResponse, PaperListResponse, ConfigurationResponse,
    GcodeSettings, GcodeSettingsUpdate
)
from .config import Config


class ConfigurationService:
    """Service for managing plotter and paper configurations"""
    
    def __init__(self):
        """Initialize the configuration service"""
        self.config = Config()
        self.config_file_path = self._get_config_file_path()
        self._ensure_config_directory()
        self._load_configurations()
    
    def _get_config_file_path(self) -> Path:
        """Get the path to the configuration file"""
        config_file_path = os.getenv("PV_CONFIG")
        if not config_file_path:
            config_file_path = "/app/local_storage/config/config.yaml"
        return Path(config_file_path)
    
    def _ensure_config_directory(self):
        """Ensure the configuration directory exists"""
        self.config_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_configurations(self):
        """Load configurations from the YAML file"""
        if not self.config_file_path.exists():
            self._create_default_config_file()
        
        try:
            with open(self.config_file_path, 'r', encoding='utf-8') as file:
                self.config_data = yaml.safe_load(file) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration file: {e}")
        except Exception as e:
            raise RuntimeError(f"Error loading configuration file: {e}")
        
        # Check if essential sections exist, if not create them
        needs_update = False
        
        # Initialize plotters if they don't exist or are empty
        if 'plotters' not in self.config_data or not self.config_data['plotters']:
            self.config_data['plotters'] = self._get_default_plotters()
            needs_update = True
        
        # Initialize papers if they don't exist or are empty
        if 'papers' not in self.config_data or not self.config_data['papers']:
            self.config_data['papers'] = self._get_default_papers()
            needs_update = True
        
        # Ensure other essential sections exist
        essential_sections = ['api', 'cors', 'arduino', 'image_processing', 'storage', 'logging', 'websocket', 'plotting']
        for section in essential_sections:
            if section not in self.config_data:
                default_config = self._get_default_config()
                self.config_data[section] = default_config[section]
                needs_update = True

        # Remove legacy top-level gcode_sequences (now per-plotter)
        if 'gcode_sequences' in self.config_data:
            self.config_data.pop('gcode_sequences', None)
            needs_update = True

        # Save updated configuration if needed
        if needs_update:
            self._save_configurations()
        
        # Validate and repair configuration if needed
        self._validate_and_repair_config()
    
    def _create_default_config_file(self):
        """Create default configuration file with default plotters and papers"""
        default_config = self._get_default_config()
        
        try:
            with open(self.config_file_path, 'w', encoding='utf-8') as file:
                yaml.dump(default_config, file, default_flow_style=False, indent=2, sort_keys=False)
            
            self.config_data = default_config
        except Exception as e:
            raise RuntimeError(f"Error creating default configuration file: {e}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration with plotters and papers.

        If a config is already loaded, reuse it as the template so regenerated
        files keep current settings.
        """
        if hasattr(self, "config_data") and self.config_data:
            return copy.deepcopy(self.config_data)

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
                "max_file_size": 10485760,
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
                "local_storage": "/app/local_storage",
                "project_storage": "/app/local_storage/projects",
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
            },
            "plotters": self._get_default_plotters(),
            "papers": self._get_default_papers()
        }
    
    def _get_default_plotters(self) -> List[Dict[str, Any]]:
        """Get default plotter configurations"""
        return [
            {
                "id": str(uuid.uuid4()),
                "name": "Default Polargraph",
                "plotter_type": "polargraph",
                "width": 1000.0,
                "height": 1000.0,
                "mm_per_rev": 95.0,
                "steps_per_rev": 200.0,
                "max_speed": 100.0,
            "acceleration": 50.0,
            "pen_up_position": 10.0,
            "pen_down_position": 0.0,
            "pen_speed": 20.0,
            "gcode_sequences": self._get_default_gcode_sequences(),
                "home_position_x": 0.0,
                "home_position_y": 0.0,
                "is_default": True,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        ]
    
    def _get_default_papers(self) -> List[Dict[str, Any]]:
        """Get default paper configurations"""
        return [
            # European A series
            {
                "id": str(uuid.uuid4()),
                "name": "A5 Paper (148×210mm)",
                "paper_size": "A5",
                "width": 148.0,
                "height": 210.0,
                "color": "white",
                "is_default": False,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "A4 Paper (210×297mm)",
                "paper_size": "A4",
                "width": 210.0,
                "height": 297.0,
                "color": "white",
                "is_default": True,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "A3 Paper (297×420mm)",
                "paper_size": "A3",
                "width": 297.0,
                "height": 420.0,
                "color": "white",
                "is_default": False,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "A2 Paper (420×594mm)",
                "paper_size": "A2",
                "width": 420.0,
                "height": 594.0,
                "color": "white",
                "is_default": False,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "A1 Paper (594×841mm)",
                "paper_size": "A1",
                "width": 594.0,
                "height": 841.0,
                "color": "white",
                "is_default": False,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "A0 Paper (841×1189mm)",
                "paper_size": "A0",
                "width": 841.0,
                "height": 1189.0,
                "color": "white",
                "is_default": False,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            # US paper sizes
            {
                "id": str(uuid.uuid4()),
                "name": "US A (8.50x11.00 in)",
                "paper_size": "A",
                "width": 216.0,
                "height": 279.0,
                "color": "white",
                "is_default": False,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "US B Size (11.0x17.0 in)",
                "paper_size": "B",
                "width": 279.0,
                "height": 432.0,
                "color": "white",
                "is_default": False,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "US C Size (17.0x22.0 in)",
                "paper_size": "C",
                "width": 432.0,
                "height": 559.0,
                "color": "white",
                "is_default": False,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "US D Size (22.0x34.0 in)",
                "paper_size": "D",
                "width": 559.0,
                "height": 864.0,
                "color": "white",
                "is_default": False,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Letter Size (8.50x11.00 in)",
                "paper_size": "Letter",
                "width": 216.0,
                "height": 279.0,
                "color": "white",
                "is_default": False,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Legal Size (8.50x14.0 in)",
                "paper_size": "Legal",
                "width": 216.0,
                "height": 356.0,
                "color": "white",
                "is_default": False,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Tabloid Size (11.0x17.0 in)",
                "paper_size": "Tabloid",
                "width": 279.0,
                "height": 432.0,
                "color": "white",
                "is_default": False,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        ]

    def _get_default_gcode_sequences(self) -> Dict[str, List[str]]:
        """Get default G-code sequences for automation"""
        return {
            "on_connect": [
                "M115; get machine status",
                "G91; set relative motion mode",
                "G21; set units to mm"
            ],
            "before_print": [
                "G92 X0 Y0 Z0; set home position"
            ],
            "pen_up_command": "M280 P0 S110",
            "pen_down_command": "M280 P0 S130",
        }
    
    def _validate_and_repair_config(self):
        """Validate and repair configuration to ensure all required fields exist"""
        needs_repair = False
        
        # Check if we have at least one default plotter
        default_plotters = [p for p in self.config_data.get('plotters', []) if p.get('is_default', False)]
        if not default_plotters:
            # Set the first plotter as default if none exists
            if self.config_data.get('plotters'):
                self.config_data['plotters'][0]['is_default'] = True
                needs_repair = True
            else:
                # Add default plotter if none exists
                self.config_data['plotters'] = self._get_default_plotters()
                needs_repair = True
        
        # Check if we have at least one default paper
        default_papers = [p for p in self.config_data.get('papers', []) if p.get('is_default', False)]
        if not default_papers:
            # Set the first paper as default if none exists
            if self.config_data.get('papers'):
                self.config_data['papers'][0]['is_default'] = True
                needs_repair = True
            else:
                # Add default papers if none exist
                self.config_data['papers'] = self._get_default_papers()
                needs_repair = True
        
        # Ensure all plotters have required fields
        for plotter in self.config_data.get('plotters', []):
            required_fields = [
                'id', 'name', 'plotter_type', 'width', 'height',
                'mm_per_rev', 'steps_per_rev', 'gcode_sequences'
            ]
            for field in required_fields:
                if field not in plotter:
                    if field == 'id':
                        plotter[field] = str(uuid.uuid4())
                    elif field in ['width', 'height', 'mm_per_rev', 'steps_per_rev']:
                        plotter[field] = 0.0
                    elif field == 'gcode_sequences':
                        plotter[field] = self._get_default_gcode_sequences()
                    elif field == 'plotter_type':
                        plotter[field] = 'polargraph'
                    else:
                        plotter[field] = 'Unknown'
                    needs_repair = True
        
        # Ensure all papers have required fields
        for paper in self.config_data.get('papers', []):
            required_fields = ['id', 'name', 'paper_size', 'width', 'height', 'color']
            for field in required_fields:
                if field not in paper:
                    if field == 'id':
                        paper[field] = str(uuid.uuid4())
                    elif field in ['width', 'height']:
                        paper[field] = 0.0
                    elif field == 'paper_size':
                        paper[field] = 'A4'
                    elif field == 'color':
                        paper[field] = 'white'
                    else:
                        paper[field] = 'Unknown'
                    needs_repair = True
        
        # Save repaired configuration if needed
        if needs_repair:
            self._save_configurations()
    
    def _save_configurations(self):
        """Save configurations to the YAML file"""
        try:
            with open(self.config_file_path, 'w', encoding='utf-8') as file:
                yaml.dump(self.config_data, file, default_flow_style=False, indent=2, sort_keys=False)
        except Exception as e:
            raise RuntimeError(f"Error saving configuration file: {e}")
    
    # Plotter management methods
    def create_plotter(self, plotter_data: PlotterCreate) -> PlotterResponse:
        """Create a new plotter configuration"""
        plotter_id = str(uuid.uuid4())
        now = datetime.now()
        
        # If this is set as default, unset other defaults
        if plotter_data.is_default:
            for plotter in self.config_data['plotters']:
                plotter['is_default'] = False
        
        plotter_dict = {
            "id": plotter_id,
            "name": plotter_data.name,
            "plotter_type": plotter_data.plotter_type.value,
            "width": plotter_data.width,
            "height": plotter_data.height,
            "mm_per_rev": plotter_data.mm_per_rev,
            "steps_per_rev": plotter_data.steps_per_rev,
            "max_speed": plotter_data.max_speed,
            "acceleration": plotter_data.acceleration,
            "pen_up_position": plotter_data.pen_up_position,
            "pen_down_position": plotter_data.pen_down_position,
            "pen_speed": plotter_data.pen_speed,
            "gcode_sequences": (
                plotter_data.gcode_sequences.dict()
                if plotter_data.gcode_sequences is not None
                else GcodeSettings().dict()
            ),
            "home_position_x": plotter_data.home_position_x,
            "home_position_y": plotter_data.home_position_y,
            "is_default": plotter_data.is_default,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        self.config_data['plotters'].append(plotter_dict)
        self._save_configurations()
        
        return self._dict_to_plotter_response(plotter_dict)
    
    def get_plotter(self, plotter_id: str) -> Optional[PlotterResponse]:
        """Get a plotter configuration by ID"""
        for plotter in self.config_data['plotters']:
            if plotter['id'] == plotter_id:
                return self._dict_to_plotter_response(plotter)
        return None
    
    def list_plotters(self) -> PlotterListResponse:
        """List all plotter configurations"""
        plotters = [self._dict_to_plotter_response(plotter) for plotter in self.config_data['plotters']]
        return PlotterListResponse(plotters=plotters, total=len(plotters))
    
    def update_plotter(self, plotter_id: str, plotter_data: PlotterUpdate) -> Optional[PlotterResponse]:
        """Update a plotter configuration"""
        for i, plotter in enumerate(self.config_data['plotters']):
            if plotter['id'] == plotter_id:
                # If this is set as default, unset other defaults
                if plotter_data.is_default is True:
                    for other_plotter in self.config_data['plotters']:
                        if other_plotter['id'] != plotter_id:
                            other_plotter['is_default'] = False
                
                # Update fields that are provided
                update_data = plotter_data.dict(exclude_unset=True)
                for key, value in update_data.items():
                    if key == 'plotter_type':
                        plotter[key] = value.value
                    elif key == 'gcode_sequences' and value is not None:
                        if isinstance(value, dict):
                            plotter[key] = value
                        else:
                            plotter[key] = value.dict()
                    else:
                        plotter[key] = value
                
                plotter['updated_at'] = datetime.now().isoformat()
                self._save_configurations()
                return self._dict_to_plotter_response(plotter)
        return None
    
    def delete_plotter(self, plotter_id: str) -> bool:
        """Delete a plotter configuration"""
        for i, plotter in enumerate(self.config_data['plotters']):
            if plotter['id'] == plotter_id:
                del self.config_data['plotters'][i]
                self._save_configurations()
                return True
        return False
    
    def get_default_plotter(self) -> Optional[PlotterResponse]:
        """Get the default plotter configuration"""
        for plotter in self.config_data['plotters']:
            if plotter.get('is_default', False):
                return self._dict_to_plotter_response(plotter)
        return None
    
    # Paper management methods
    def create_paper(self, paper_data: PaperCreate) -> PaperResponse:
        """Create a new paper configuration"""
        paper_id = str(uuid.uuid4())
        now = datetime.now()
        
        # If this is set as default, unset other defaults
        if paper_data.is_default:
            for paper in self.config_data['papers']:
                paper['is_default'] = False
        
        paper_dict = {
            "id": paper_id,
            "name": paper_data.name,
            "paper_size": paper_data.paper_size.value,
            "width": paper_data.width,
            "height": paper_data.height,
            "color": paper_data.color,
            "is_default": paper_data.is_default,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        self.config_data['papers'].append(paper_dict)
        self._save_configurations()
        
        return self._dict_to_paper_response(paper_dict)
    
    def get_paper(self, paper_id: str) -> Optional[PaperResponse]:
        """Get a paper configuration by ID"""
        for paper in self.config_data['papers']:
            if paper['id'] == paper_id:
                return self._dict_to_paper_response(paper)
        return None
    
    def list_papers(self) -> PaperListResponse:
        """List all paper configurations"""
        papers = [self._dict_to_paper_response(paper) for paper in self.config_data['papers']]
        return PaperListResponse(papers=papers, total=len(papers))
    
    def update_paper(self, paper_id: str, paper_data: PaperUpdate) -> Optional[PaperResponse]:
        """Update a paper configuration"""
        for i, paper in enumerate(self.config_data['papers']):
            if paper['id'] == paper_id:
                # If this is set as default, unset other defaults
                if paper_data.is_default is True:
                    for other_paper in self.config_data['papers']:
                        if other_paper['id'] != paper_id:
                            other_paper['is_default'] = False
                
                # Update fields that are provided
                update_data = paper_data.dict(exclude_unset=True)
                for key, value in update_data.items():
                    if key == 'paper_size':
                        paper[key] = value.value
                    else:
                        paper[key] = value
                
                paper['updated_at'] = datetime.now().isoformat()
                self._save_configurations()
                return self._dict_to_paper_response(paper)
        return None
    
    def delete_paper(self, paper_id: str) -> bool:
        """Delete a paper configuration"""
        for i, paper in enumerate(self.config_data['papers']):
            if paper['id'] == paper_id:
                del self.config_data['papers'][i]
                self._save_configurations()
                return True
        return False
    
    def get_default_paper(self) -> Optional[PaperResponse]:
        """Get the default paper configuration"""
        for paper in self.config_data['papers']:
            if paper.get('is_default', False):
                return self._dict_to_paper_response(paper)
        return None
    
    def get_default_plotter_id(self) -> Optional[str]:
        default = self.get_default_plotter()
        return default.id if default else None

    def get_gcode_settings(self) -> GcodeSettings:
        """Return automatic G-code sequences for the default plotter."""
        default_plotter = self.get_default_plotter()
        if default_plotter:
            return default_plotter.gcode_sequences
        # Fallback: ensure we always return a model
        defaults = self._get_default_gcode_sequences()
        return GcodeSettings(
            on_connect=defaults.get("on_connect", []),
            before_print=defaults.get("before_print", []),
            pen_up_command=defaults.get("pen_up_command", "M280 P0 S110"),
            pen_down_command=defaults.get("pen_down_command", "M280 P0 S130"),
        )

    def update_gcode_settings(self, gcode_data: GcodeSettingsUpdate) -> GcodeSettings:
        """Update automatic G-code sequences on the default plotter."""
        # Try default plotter, else first plotter, else create defaults
        target_id = self.get_default_plotter_id()
        if not target_id and self.config_data.get("plotters"):
            target_id = self.config_data["plotters"][0]["id"]
        if not target_id:
            # No plotters present; seed defaults
            self.config_data["plotters"] = self._get_default_plotters()
            target_id = self.config_data["plotters"][0]["id"]

        updated = self.update_plotter_gcode_settings(target_id, gcode_data)
        return updated or self.get_gcode_settings()

    def get_all_configurations(self) -> ConfigurationResponse:
        """Get all configurations (plotters and papers)"""
        plotters = [self._dict_to_plotter_response(plotter) for plotter in self.config_data['plotters']]
        papers = [self._dict_to_paper_response(paper) for paper in self.config_data['papers']]
        default_plotter = self.get_default_plotter()
        default_paper = self.get_default_paper()
        
        return ConfigurationResponse(
            plotters=plotters,
            papers=papers,
            default_plotter=default_plotter,
            default_paper=default_paper,
            gcode=self.get_gcode_settings()
        )
    
    def _dict_to_plotter_response(self, plotter_dict: Dict[str, Any]) -> PlotterResponse:
        """Convert dictionary to PlotterResponse"""
        gcode_data = plotter_dict.get('gcode_sequences', self._get_default_gcode_sequences())
        return PlotterResponse(
            id=plotter_dict['id'],
            name=plotter_dict['name'],
            plotter_type=plotter_dict['plotter_type'],
            width=plotter_dict['width'],
            height=plotter_dict['height'],
            mm_per_rev=plotter_dict['mm_per_rev'],
            steps_per_rev=plotter_dict['steps_per_rev'],
            max_speed=plotter_dict['max_speed'],
            acceleration=plotter_dict['acceleration'],
            pen_up_position=plotter_dict['pen_up_position'],
            pen_down_position=plotter_dict['pen_down_position'],
            pen_speed=plotter_dict['pen_speed'],
            gcode_sequences=GcodeSettings(
                on_connect=gcode_data.get('on_connect', []),
                before_print=gcode_data.get('before_print', []),
                pen_up_command=gcode_data.get('pen_up_command', "M280 P0 S110"),
                pen_down_command=gcode_data.get('pen_down_command', "M280 P0 S130"),
            ),
            home_position_x=plotter_dict['home_position_x'],
            home_position_y=plotter_dict['home_position_y'],
            is_default=plotter_dict['is_default'],
            created_at=datetime.fromisoformat(plotter_dict['created_at']),
            updated_at=datetime.fromisoformat(plotter_dict['updated_at'])
        )
    
    def _dict_to_paper_response(self, paper_dict: Dict[str, Any]) -> PaperResponse:
        """Convert dictionary to PaperResponse"""
        return PaperResponse(
            id=paper_dict['id'],
            name=paper_dict['name'],
            paper_size=paper_dict['paper_size'],
            width=paper_dict['width'],
            height=paper_dict['height'],
            color=paper_dict['color'],
            is_default=paper_dict['is_default'],
            created_at=datetime.fromisoformat(paper_dict['created_at']),
            updated_at=datetime.fromisoformat(paper_dict['updated_at'])
        )


    def get_plotter_gcode_settings(self, plotter_id: str) -> Optional[GcodeSettings]:
        """Return automatic G-code sequences for a specific plotter"""
        for plotter in self.config_data.get('plotters', []):
            if plotter['id'] == plotter_id:
                gcode_data = plotter.get('gcode_sequences', self._get_default_gcode_sequences())
                pen_up = gcode_data.get('pen_up_command')
                if pen_up is None:
                    pen_up = "M280 P0 S110"
                pen_down = gcode_data.get('pen_down_command')
                if pen_down is None:
                    pen_down = "M280 P0 S130"
                return GcodeSettings(
                    on_connect=gcode_data.get('on_connect', []),
                    before_print=gcode_data.get('before_print', []),
                    pen_up_command=pen_up,
                    pen_down_command=pen_down,
                )
        return None

    def update_plotter_gcode_settings(self, plotter_id: str, gcode_data: GcodeSettingsUpdate) -> Optional[GcodeSettings]:
        """Update automatic G-code sequences for a specific plotter"""
        for plotter in self.config_data.get('plotters', []):
            if plotter['id'] == plotter_id:
                existing = plotter.get('gcode_sequences', self._get_default_gcode_sequences())
                update_payload = gcode_data.dict(exclude_unset=True)

                if 'on_connect' in update_payload:
                    if update_payload['on_connect'] is not None:
                        existing['on_connect'] = update_payload['on_connect']
                if 'before_print' in update_payload:
                    if update_payload['before_print'] is not None:
                        existing['before_print'] = update_payload['before_print']
                if 'pen_up_command' in update_payload:
                    if update_payload['pen_up_command'] is not None:
                        existing['pen_up_command'] = update_payload['pen_up_command']
                if 'pen_down_command' in update_payload:
                    if update_payload['pen_down_command'] is not None:
                        existing['pen_down_command'] = update_payload['pen_down_command']

                plotter['gcode_sequences'] = existing
                self._save_configurations()
                return self.get_plotter_gcode_settings(plotter_id)
        return None

    def rebuild_default_config(self):
        """Force rebuild the configuration with all default values"""
        try:
            # Create backup of existing config if it exists
            if self.config_file_path.exists():
                backup_path = self.config_file_path.with_suffix('.yaml.backup')
                import shutil
                shutil.copy2(self.config_file_path, backup_path)
            
            # Rebuild with defaults
            self.config_data = self._get_default_config()
            self._save_configurations()
            
            return True
        except Exception as e:
            raise RuntimeError(f"Error rebuilding configuration: {e}")


# Create global instance
config_service = ConfigurationService()
