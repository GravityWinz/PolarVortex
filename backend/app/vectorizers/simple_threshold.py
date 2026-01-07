from typing import Dict, Any, Optional, List
import cv2
import numpy as np
from PIL import Image
import io
import base64
import logging
from datetime import datetime
from pathlib import Path

from . import BaseVectorizer, VectorizationResult
from ..vectorizer import VectorPath

logger = logging.getLogger(__name__)

class SimpleThresholdVectorizer(BaseVectorizer):
    """
    Simple threshold-based vectorization algorithm.
    Converts image to grayscale, applies threshold, and extracts contours.
    This is a simplified example demonstrating how to create a new vectorizer.
    """
    
    def __init__(self):
        pass
    
    @property
    def name(self) -> str:
        return "Simple Threshold"
    
    @property
    def description(self) -> str:
        return "Simple threshold-based vectorization using grayscale conversion and contour detection"
    
    @property
    def algorithm_id(self) -> str:
        return "simple_threshold"
    
    def vectorize_image(
        self,
        image_data: bytes,
        settings: Optional[Dict[str, Any]] = None,
        output_dir: Optional[str] = None,
        base_filename: Optional[str] = None,
    ) -> VectorizationResult:
        """
        Vectorize using simple threshold algorithm.
        
        See backend/app/vectorizers/PARAMETERS.md for detailed parameter documentation.
        
        Parameters:
        - threshold_value: Grayscale threshold for binary conversion (0-255, default: 127)
        - invert: Invert threshold result (default: False)
        - min_area: Minimum contour area in pixels² to include (default: 10)
        - blur_size: Gaussian blur kernel size before thresholding (must be odd, default: 3)
        """
        start_time = datetime.now()
        
        # Get settings with defaults
        threshold_value = settings.get("threshold_value", 127) if settings else 127
        invert = settings.get("invert", False) if settings else False
        min_area = settings.get("min_area", 10) if settings else 10
        blur_size = settings.get("blur_size", 3) if settings else 3
        
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            original_size = image.size
            
            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            # Convert to numpy array
            img_array = np.array(image)
            
            # Apply blur if specified: blur_size must be odd (1, 3, 5, 7, etc.)
            # Higher values = more smoothing, reduces noise but may blur details
            if blur_size > 0:
                img_array = cv2.GaussianBlur(img_array, (blur_size, blur_size), 0)
            
            # Apply threshold: threshold_value determines cutoff point (0-255)
            # invert=True swaps black/white result
            if invert:
                _, thresh = cv2.threshold(img_array, threshold_value, 255, cv2.THRESH_BINARY_INV)
            else:
                _, thresh = cv2.threshold(img_array, threshold_value, 255, cv2.THRESH_BINARY)
            
            # Find contours
            contours, _ = cv2.findContours(
                thresh,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            # Convert contours to paths
            # min_area: Filter out small contours/artifacts
            paths = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < min_area:
                    continue
                
                # Extract points
                points = []
                for point in contour:
                    x, y = point[0]
                    points.append((float(x), float(y)))
                
                if len(points) < 3:
                    continue
                
                # Close the path
                if points[0] != points[-1]:
                    points.append(points[0])
                
                # Calculate bounding box
                x_coords = [p[0] for p in points]
                y_coords = [p[1] for p in points]
                bbox = (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
                
                # Create path (black color for threshold)
                path = VectorPath(
                    points=points,
                    color=(0, 0, 0),
                    is_closed=True,
                    area=area,
                    bounding_box=bbox
                )
                paths.append(path)
            
            # Sort by area (largest first)
            paths.sort(key=lambda p: p.area, reverse=True)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Create result
            result = VectorizationResult(
                paths=paths,
                original_size=original_size,
                processed_size=original_size,  # Same size for this algorithm
                colors_detected=1,  # Grayscale = 1 color
                total_paths=len(paths),
                processing_time=processing_time,
                settings_used=settings or {},
                source_image_name=base_filename,
            )
            
            # Create SVG if output directory provided
            if output_dir and paths:
                svg_path = self._create_svg(result, output_dir, base_filename)
                result.svg_path = svg_path
            
            return result
            
        except Exception as e:
            logger.error(f"Simple threshold vectorization error: {e}")
            raise
    
    def _create_svg(self, result: VectorizationResult, output_dir: str, base_filename: Optional[str] = None) -> Optional[str]:
        """Create SVG file for the result"""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name_root = (base_filename or "vectorized").strip() or "vectorized"
            svg_filename = f"{name_root}_{timestamp}.svg"
            svg_path = output_path / svg_filename
            
            width, height = result.processed_size
            
            svg_lines = [
                '<?xml version="1.0" encoding="UTF-8"?>',
                f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
                '  <defs>',
                '    <style>',
                '      .path { fill: none; stroke-width: 1; }',
                '    </style>',
                '  </defs>'
            ]
            
            # Add paths
            for i, path in enumerate(result.paths):
                if len(path.points) < 2:
                    continue
                
                path_data = "M "
                for j, (x, y) in enumerate(path.points):
                    if j == 0:
                        path_data += f"{x:.2f} {y:.2f}"
                    else:
                        path_data += f" L {x:.2f} {y:.2f}"
                
                if path.is_closed:
                    path_data += " Z"
                
                color_hex = "#{:02x}{:02x}{:02x}".format(*path.color)
                svg_lines.append(
                    f'  <path d="{path_data}" class="path" stroke="{color_hex}" id="path_{i}"/>'
                )
            
            svg_lines.append('</svg>')
            
            with open(svg_path, 'w') as f:
                f.write('\n'.join(svg_lines))
            
            logger.info(f"SVG created: {svg_path}")
            return str(svg_path)
            
        except Exception as e:
            logger.error(f"SVG creation error: {e}")
            return None
    
    def export_to_svg(self, result: VectorizationResult, output_path: str) -> bool:
        """Export to SVG file"""
        try:
            output_dir = str(Path(output_path).parent)
            base_filename = Path(output_path).stem
            svg_path = self._create_svg(result, output_dir, base_filename)
            return svg_path is not None
        except Exception as e:
            logger.error(f"SVG export error: {e}")
            return False
    
    def export_to_plotting_commands(
        self, 
        result: VectorizationResult, 
        machine_settings: Dict[str, Any]
    ) -> List[str]:
        """Export to polargraph plotting commands"""
        commands = []
        
        # Machine setup commands
        commands.append("C24,{},{}".format(
            machine_settings.get("width", 1000),
            machine_settings.get("height", 1000)
        ))
        commands.append("C29,{}".format(machine_settings.get("mm_per_rev", 95.0)))
        commands.append("C30,{}".format(machine_settings.get("steps_per_rev", 200.0)))
        
        # Drawing commands
        for path in result.paths:
            if len(path.points) < 2:
                continue
            
            # Move to first point
            x, y = path.points[0]
            commands.append("C09,{:.2f},{:.2f}".format(x, y))
            commands.append("C13")  # Pen down
            
            # Draw to subsequent points
            for x, y in path.points[1:]:
                commands.append("C01,{:.2f},{:.2f}".format(x, y))
            
            commands.append("C14")  # Pen up
        
        return commands
    
    def get_vectorization_preview(self, result: VectorizationResult) -> str:
        """Generate base64 preview of vectorization result"""
        try:
            from PIL import ImageDraw
            
            width, height = result.processed_size
            preview_img = Image.new('RGB', (width, height), 'white')
            draw = ImageDraw.Draw(preview_img)
            
            for path in result.paths:
                if len(path.points) >= 2:
                    color = tuple(path.color)
                    draw.line(path.points, fill=color, width=1)
            
            # Convert to base64
            buffer = io.BytesIO()
            preview_img.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_base64}"
            
        except Exception as e:
            logger.error(f"Preview generation error: {e}")
            return ""
    
    def get_default_settings(self) -> Dict[str, Any]:
        """
        Return default settings for this vectorizer.
        
        See backend/app/vectorizers/PARAMETERS.md for detailed parameter documentation.
        """
        return {
            "threshold_value": 127,
            "invert": False,
            "min_area": 10,
            "blur_size": 3
        }
    
    def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize settings"""
        validated = self.get_default_settings()
        validated.update(settings)
        
        # Clamp values to valid ranges
        validated["threshold_value"] = max(0, min(255, int(validated.get("threshold_value", 127))))
        validated["min_area"] = max(1, int(validated.get("min_area", 10)))
        validated["blur_size"] = max(0, min(15, int(validated.get("blur_size", 3))))
        validated["invert"] = bool(validated.get("invert", False))
        
        return validated
    
    def get_parameter_documentation(self) -> Dict[str, Dict[str, Any]]:
        """Return parameter documentation for this vectorizer"""
        return {
            "threshold_value": {
                "description": "Grayscale threshold for binary conversion",
                "purpose": "Grayscale threshold value for binary conversion (0-255 scale)",
                "range": "0-255",
                "default": 127,
                "effects": "Low values (0-100) make more pixels become white (foreground), fewer become black. Medium values (100-150) provide balanced threshold. High values (150-255) make more pixels become black (background), fewer become white.",
                "when_to_adjust": "Increase if too much is being detected as foreground. Decrease if not enough is being detected."
            },
            "invert": {
                "description": "Invert the threshold result",
                "purpose": "Invert the threshold result (swap black and white)",
                "range": "boolean",
                "default": False,
                "effects": "False: Pixels above threshold → white, below → black. True: Pixels above threshold → black, below → white.",
                "when_to_adjust": "Enable for dark images on light backgrounds, or when you want inverted output"
            },
            "min_area": {
                "description": "Minimum contour area in pixels² to include",
                "purpose": "Minimum area required for a contour to be included",
                "range": "1-10000+ (typically 5-100)",
                "default": 10,
                "effects": "Low values (1-5) include very small details and noise. Medium values (10-50) filter out small noise while preserving details. High values (100+) only include large features.",
                "when_to_adjust": "Increase to remove small artifacts, decrease to preserve fine details"
            },
            "blur_size": {
                "description": "Gaussian blur kernel size before thresholding",
                "purpose": "Size of the Gaussian blur kernel applied before thresholding",
                "range": "0-15 (must be odd: 1, 3, 5, 7, 9, 11, 13, 15)",
                "default": 3,
                "effects": "0: No blur, preserves all details and noise. Small (1-3): Light smoothing, reduces minor noise. Medium (5-7): Moderate smoothing. Large (9-15): Heavy smoothing, removes fine details.",
                "when_to_adjust": "Increase for noisy images. Decrease or set to 0 to preserve fine details."
            }
        }