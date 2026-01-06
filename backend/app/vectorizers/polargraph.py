from typing import Dict, Any, Optional, List
from . import BaseVectorizer, VectorizationResult
from ..vectorizer import (
    PolargraphVectorizer as OriginalPolargraphVectorizer,
    VectorizationSettings,
    VectorPath
)

class PolargraphVectorizer(BaseVectorizer):
    """Polargraph vectorization algorithm - original implementation"""
    
    def __init__(self):
        self._vectorizer = OriginalPolargraphVectorizer()
    
    @property
    def name(self) -> str:
        return "Polargraph Vectorizer"
    
    @property
    def description(self) -> str:
        return "Original polargraph vectorization algorithm using contour detection and color separation"
    
    @property
    def algorithm_id(self) -> str:
        return "polargraph"
    
    def vectorize_image(
        self,
        image_data: bytes,
        settings: Optional[Dict[str, Any]] = None,
        output_dir: Optional[str] = None,
        base_filename: Optional[str] = None,
    ) -> VectorizationResult:
        """Vectorize using the polargraph algorithm"""
        # Convert dict settings to VectorizationSettings object
        if settings:
            vec_settings = VectorizationSettings(
                blur_radius=settings.get("blur_radius", 1),
                posterize_levels=settings.get("posterize_levels", 5),
                simplification_threshold=settings.get("simplification_threshold", 2.0),
                simplification_iterations=settings.get("simplification_iterations", 3),
                min_contour_points=settings.get("min_contour_points", 3),
                min_contour_area=settings.get("min_contour_area", 10),
                color_tolerance=settings.get("color_tolerance", 10),
                enable_color_separation=settings.get("enable_color_separation", True),
                enable_contour_simplification=settings.get("enable_contour_simplification", True),
                enable_noise_reduction=settings.get("enable_noise_reduction", True)
            )
        else:
            vec_settings = None
        
        # Use the original vectorizer
        result = self._vectorizer.vectorize_image(
            image_data, 
            vec_settings, 
            output_dir, 
            base_filename
        )
        
        # Convert to our base VectorizationResult format
        return VectorizationResult(
            paths=result.paths,
            original_size=result.original_size,
            processed_size=result.processed_size,
            colors_detected=result.colors_detected,
            total_paths=result.total_paths,
            processing_time=result.processing_time,
            settings_used=result.settings_used,
            svg_path=result.svg_path,
            source_image_name=result.source_image_name
        )
    
    def export_to_svg(self, result: VectorizationResult, output_path: str) -> bool:
        """Export to SVG using original vectorizer"""
        # Convert back to original format temporarily
        from ..vectorizer import VectorizationResult as OriginalResult
        original_result = OriginalResult(
            paths=result.paths,
            original_size=result.original_size,
            processed_size=result.processed_size,
            colors_detected=result.colors_detected,
            total_paths=result.total_paths,
            processing_time=result.processing_time,
            settings_used=result.settings_used,
            svg_path=result.svg_path,
            source_image_name=result.source_image_name
        )
        return self._vectorizer.export_to_svg(original_result, output_path)
    
    def export_to_plotting_commands(
        self, 
        result: VectorizationResult, 
        machine_settings: Dict[str, Any]
    ) -> List[str]:
        """Export to plotting commands"""
        from ..vectorizer import VectorizationResult as OriginalResult
        original_result = OriginalResult(
            paths=result.paths,
            original_size=result.original_size,
            processed_size=result.processed_size,
            colors_detected=result.colors_detected,
            total_paths=result.total_paths,
            processing_time=result.processing_time,
            settings_used=result.settings_used,
            svg_path=result.svg_path,
            source_image_name=result.source_image_name
        )
        return self._vectorizer.export_to_plotting_commands(original_result, machine_settings)
    
    def get_vectorization_preview(self, result: VectorizationResult) -> str:
        """Generate preview"""
        from ..vectorizer import VectorizationResult as OriginalResult
        original_result = OriginalResult(
            paths=result.paths,
            original_size=result.original_size,
            processed_size=result.processed_size,
            colors_detected=result.colors_detected,
            total_paths=result.total_paths,
            processing_time=result.processing_time,
            settings_used=result.settings_used,
            svg_path=result.svg_path,
            source_image_name=result.source_image_name
        )
        return self._vectorizer.get_vectorization_preview(original_result)
    
    def get_default_settings(self) -> Dict[str, Any]:
        """Return default settings"""
        default = VectorizationSettings()
        return {
            "blur_radius": default.blur_radius,
            "posterize_levels": default.posterize_levels,
            "simplification_threshold": default.simplification_threshold,
            "simplification_iterations": default.simplification_iterations,
            "min_contour_points": default.min_contour_points,
            "min_contour_area": default.min_contour_area,
            "color_tolerance": default.color_tolerance,
            "enable_color_separation": default.enable_color_separation,
            "enable_contour_simplification": default.enable_contour_simplification,
            "enable_noise_reduction": default.enable_noise_reduction
        }
