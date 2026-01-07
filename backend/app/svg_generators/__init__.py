from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class SvgGenerationResult:
    """Result of the SVG generation process"""
    svg_path: Optional[str] = None
    svg_content: Optional[str] = None
    width: int = 0
    height: int = 0
    processing_time: float = 0.0
    settings_used: Any = None
    preview: Optional[str] = None  # Base64 encoded preview image

class BaseSvgGenerator(ABC):
    """Base class for all SVG generation algorithms"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the display name of the generator"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Return a description of the generator"""
        pass
    
    @property
    @abstractmethod
    def generator_id(self) -> str:
        """Return a unique identifier for this generator"""
        pass
    
    @abstractmethod
    def generate_svg(
        self,
        settings: Optional[Dict[str, Any]] = None,
        output_dir: Optional[str] = None,
        base_filename: Optional[str] = None,
    ) -> SvgGenerationResult:
        """
        Main SVG generation method
        
        Args:
            settings: Optional custom settings (dict format)
            output_dir: Optional directory to save SVG file
            base_filename: Optional base filename for output
            
        Returns:
            SvgGenerationResult containing SVG content and metadata
        """
        pass
    
    def get_generation_preview(self, result: SvgGenerationResult) -> str:
        """Generate base64 preview of generated SVG"""
        raise NotImplementedError("Preview generation not implemented for this generator")
    
    def get_default_settings(self) -> Dict[str, Any]:
        """Return default settings for this generator"""
        return {}
    
    def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize settings"""
        return settings
    
    def get_parameter_documentation(self) -> Dict[str, Dict[str, Any]]:
        """
        Return documentation for each parameter.
        
        Returns a dictionary mapping parameter names to documentation dicts with:
        - description: Brief description of the parameter
        - purpose: What the parameter controls
        - range: Valid range (tuple of min, max) or description
        - default: Default value
        - effects: Description of how different values affect the output
        - when_to_adjust: Guidance on when to change this parameter
        
        Override this method in subclasses to provide parameter documentation.
        """
        return {}

# Registry for SVG generators
_svg_generator_registry: Dict[str, BaseSvgGenerator] = {}

def register_svg_generator(generator_class: type):
    """Register a SVG generator class"""
    try:
        instance = generator_class()
        _svg_generator_registry[instance.generator_id] = instance
        logger.info(f"Registered SVG generator: {instance.name} ({instance.generator_id})")
    except Exception as e:
        logger.error(f"Failed to register SVG generator {generator_class.__name__}: {e}")

def get_svg_generator(generator_id: str) -> Optional[BaseSvgGenerator]:
    """Get a SVG generator by its generator ID"""
    return _svg_generator_registry.get(generator_id)

def get_available_svg_generators() -> List[Dict[str, str]]:
    """Get list of all available SVG generators"""
    return [
        {
            "id": gen.generator_id,
            "name": gen.name,
            "description": gen.description
        }
        for gen in _svg_generator_registry.values()
    ]

def get_svg_generator_info(generator_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed information about a SVG generator"""
    generator = get_svg_generator(generator_id)
    if not generator:
        return None
    
    return {
        "id": generator.generator_id,
        "name": generator.name,
        "description": generator.description,
        "default_settings": generator.get_default_settings(),
        "parameter_documentation": generator.get_parameter_documentation()
    }

# Auto-register built-in generators
def _register_builtin_generators():
    """Register all built-in SVG generators"""
    try:
        from .geometric_pattern import GeometricPatternGenerator
        register_svg_generator(GeometricPatternGenerator)
    except Exception as e:
        logger.error(f"Failed to register geometric pattern generator: {e}")
    
    try:
        from .spirograph import SpirographGenerator
        register_svg_generator(SpirographGenerator)
    except Exception as e:
        logger.error(f"Failed to register spirograph generator: {e}")

# Register on import
_register_builtin_generators()
