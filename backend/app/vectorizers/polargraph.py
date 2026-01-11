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
    
    def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize settings"""
        validated = self.get_default_settings()
        validated.update(settings)
        
        # Clamp values to valid ranges
        validated["blur_radius"] = max(0, min(10, int(validated.get("blur_radius", 1))))
        validated["posterize_levels"] = max(2, min(256, int(validated.get("posterize_levels", 5))))
        validated["simplification_threshold"] = max(0.1, min(10.0, float(validated.get("simplification_threshold", 2.0))))
        validated["simplification_iterations"] = max(1, min(10, int(validated.get("simplification_iterations", 3))))
        validated["min_contour_points"] = max(3, min(100, int(validated.get("min_contour_points", 3))))
        validated["min_contour_area"] = max(1, int(validated.get("min_contour_area", 10)))
        validated["color_tolerance"] = max(0, min(255, int(validated.get("color_tolerance", 10))))
        validated["enable_color_separation"] = bool(validated.get("enable_color_separation", True))
        validated["enable_contour_simplification"] = bool(validated.get("enable_contour_simplification", True))
        validated["enable_noise_reduction"] = bool(validated.get("enable_noise_reduction", True))
        
        return validated
    
    def get_parameter_documentation(self) -> Dict[str, Dict[str, Any]]:
        """Return parameter documentation for this vectorizer"""
        return {
            "blur_radius": {
                "description": "Gaussian blur radius for noise reduction",
                "purpose": "Controls the amount of smoothing applied to the image before vectorization",
                "range": "0-10 (typically)",
                "default": 1,
                "effects": "Low values (0-1) preserve fine details but may include noise. Medium values (2-3) balance smoothing and detail. High values (4+) remove fine details but reduce noise.",
                "when_to_adjust": "Increase for noisy images, decrease for images with fine details you want to preserve"
            },
            "posterize_levels": {
                "description": "Number of color levels for quantization",
                "purpose": "Reduces the number of colors in the image by quantizing to a specific number of color levels",
                "range": "2-256 (typically 2-20 for vectorization)",
                "default": 5,
                "effects": "Low values (2-4) create high-contrast, posterized effect with few colors. Medium values (5-8) maintain some color detail. High values (9+) preserve more color information but may create more complex paths.",
                "when_to_adjust": "Lower for simpler vectorization with fewer colors, higher for preserving color gradients"
            },
            "enable_noise_reduction": {
                "description": "Enable/disable noise reduction preprocessing",
                "purpose": "Master switch to enable/disable noise reduction preprocessing",
                "range": "boolean",
                "default": True,
                "effects": "When enabled, applies blur based on blur_radius. When disabled, skips blur entirely.",
                "when_to_adjust": "Disable if you want to preserve all fine details, even if they might be noise"
            },
            "enable_color_separation": {
                "description": "Separate image into individual color layers",
                "purpose": "Controls whether the algorithm separates the image into individual color layers",
                "range": "boolean",
                "default": True,
                "effects": "Enabled: Each unique color is processed separately, creating separate vector paths for each color. Disabled: Image is processed as a single grayscale layer.",
                "when_to_adjust": "Disable for grayscale images or when you want a single-color output"
            },
            "color_tolerance": {
                "description": "RGB tolerance for grouping similar colors",
                "purpose": "Determines how similar colors must be to be grouped together during color separation",
                "range": "0-255 (typically 5-30)",
                "default": 10,
                "effects": "Low values (0-5) use very strict color matching. Medium values (10-15) balance grouping. High values (20+) treat different shades as the same color.",
                "when_to_adjust": "Increase if you have many similar color shades you want to merge. Decrease if you want to preserve subtle color differences."
            },
            "min_contour_area": {
                "description": "Minimum area in pixels² for valid contours",
                "purpose": "Minimum area required for a contour to be included in the vectorization",
                "range": "1-10000+ (typically 5-100)",
                "default": 10,
                "effects": "Low values (1-5) include very small details and noise. Medium values (10-50) filter out small noise while preserving important details. High values (100+) only include large features.",
                "when_to_adjust": "Increase to remove small artifacts and noise, decrease to preserve fine details"
            },
            "min_contour_points": {
                "description": "Minimum points required for valid contours",
                "purpose": "Minimum number of points required for a contour to be valid",
                "range": "3-10 (typically)",
                "default": 3,
                "effects": "Low values (3) accept very simple shapes (triangles). Higher values (5+) require more complex shapes, filtering out degenerate contours.",
                "when_to_adjust": "Rarely needs adjustment - 3 is usually appropriate for minimum valid polygon"
            },
            "enable_contour_simplification": {
                "description": "Enable/disable contour simplification",
                "purpose": "Master switch to enable/disable contour simplification",
                "range": "boolean",
                "default": True,
                "effects": "When enabled, applies Douglas-Peucker algorithm to reduce the number of points in contours. When disabled, preserves all original contour points.",
                "when_to_adjust": "Disable if you want to preserve all original contour points"
            },
            "simplification_threshold": {
                "description": "Max deviation in pixels for simplification",
                "purpose": "Maximum distance that a simplified contour point can deviate from the original",
                "range": "0.1-10.0 (typically 1.0-5.0)",
                "default": 2.0,
                "effects": "Low values (0.5-1.0) preserve fine curves and details. Medium values (2.0-3.0) reduce points while maintaining shape. High values (5.0+) create smoother but less detailed paths.",
                "when_to_adjust": "Increase for smoother, simpler paths (fewer points, faster plotting). Decrease to preserve fine curves and details."
            },
            "simplification_iterations": {
                "description": "Number of simplification passes",
                "purpose": "Number of times to apply the Douglas-Peucker simplification algorithm",
                "range": "1-10 (typically 1-5)",
                "default": 3,
                "effects": "Low values (1-2) use single or double pass simplification. Medium values (3-4) use multiple passes for progressive simplification. High values (5+) may over-simplify and lose important details.",
                "when_to_adjust": "Increase for more aggressive simplification (fewer points). Decrease if simplification is removing important features."
            }
        }