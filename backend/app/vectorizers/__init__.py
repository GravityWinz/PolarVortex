from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class VectorizationResult:
    """Result of the vectorization process"""
    paths: List[Any]  # List of VectorPath objects
    original_size: tuple
    processed_size: tuple
    colors_detected: int
    total_paths: int
    processing_time: float
    settings_used: Any
    svg_path: Optional[str] = None
    source_image_name: Optional[str] = None

class BaseVectorizer(ABC):
    """Base class for all vectorization algorithms"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the display name of the vectorizer"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Return a description of the vectorizer"""
        pass
    
    @property
    @abstractmethod
    def algorithm_id(self) -> str:
        """Return a unique identifier for this algorithm"""
        pass
    
    @abstractmethod
    def vectorize_image(
        self,
        image_data: bytes,
        settings: Optional[Dict[str, Any]] = None,
        output_dir: Optional[str] = None,
        base_filename: Optional[str] = None,
    ) -> VectorizationResult:
        """
        Main vectorization method
        
        Args:
            image_data: Raw image bytes
            settings: Optional custom settings (dict format)
            output_dir: Optional directory to save SVG file
            base_filename: Optional base filename for output
            
        Returns:
            VectorizationResult containing all vector paths and metadata
        """
        pass
    
    def export_to_svg(self, result: VectorizationResult, output_path: str) -> bool:
        """Export vectorization result to SVG file"""
        raise NotImplementedError("SVG export not implemented for this vectorizer")
    
    def export_to_plotting_commands(
        self, 
        result: VectorizationResult, 
        machine_settings: Dict[str, Any]
    ) -> List[str]:
        """Export to polargraph plotting commands"""
        raise NotImplementedError("Plotting commands export not implemented for this vectorizer")
    
    def get_vectorization_preview(self, result: VectorizationResult) -> str:
        """Generate base64 preview of vectorization result"""
        raise NotImplementedError("Preview generation not implemented for this vectorizer")
    
    def get_default_settings(self) -> Dict[str, Any]:
        """Return default settings for this vectorizer"""
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

# Registry for vectorizers
_vectorizer_registry: Dict[str, BaseVectorizer] = {}

def register_vectorizer(vectorizer_class: type):
    """Register a vectorizer class"""
    try:
        instance = vectorizer_class()
        _vectorizer_registry[instance.algorithm_id] = instance
        logger.info(f"Registered vectorizer: {instance.name} ({instance.algorithm_id})")
    except Exception as e:
        logger.error(f"Failed to register vectorizer {vectorizer_class.__name__}: {e}")

def get_vectorizer(algorithm_id: str) -> Optional[BaseVectorizer]:
    """Get a vectorizer by its algorithm ID"""
    return _vectorizer_registry.get(algorithm_id)

def get_available_vectorizers() -> List[Dict[str, str]]:
    """Get list of all available vectorizers"""
    return [
        {
            "id": vec.algorithm_id,
            "name": vec.name,
            "description": vec.description
        }
        for vec in _vectorizer_registry.values()
    ]

def get_vectorizer_info(algorithm_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed information about a vectorizer"""
    vectorizer = get_vectorizer(algorithm_id)
    if not vectorizer:
        return None
    
    return {
        "id": vectorizer.algorithm_id,
        "name": vectorizer.name,
        "description": vectorizer.description,
        "default_settings": vectorizer.get_default_settings(),
        "parameter_documentation": vectorizer.get_parameter_documentation()
    }

# Auto-register built-in vectorizers
def _register_builtin_vectorizers():
    """Register all built-in vectorizers"""
    try:
        from .polargraph import PolargraphVectorizer
        register_vectorizer(PolargraphVectorizer)
    except Exception as e:
        logger.error(f"Failed to register polargraph vectorizer: {e}")
    
    try:
        from .simple_threshold import SimpleThresholdVectorizer
        register_vectorizer(SimpleThresholdVectorizer)
    except Exception as e:
        logger.error(f"Failed to register simple threshold vectorizer: {e}")
    
    try:
        from .img2plot import Img2PlotVectorizer
        register_vectorizer(Img2PlotVectorizer)
    except Exception as e:
        logger.error(f"Failed to register img2plot vectorizer: {e}")
    
    # Uncomment to enable the example booger vectorizer (for testing custom settings)
    # try:
    #     from .example_booger import ExampleBoogerVectorizer
    #     register_vectorizer(ExampleBoogerVectorizer)
    # except Exception as e:
    #     logger.error(f"Failed to register example booger vectorizer: {e}")

# Register on import
_register_builtin_vectorizers()
