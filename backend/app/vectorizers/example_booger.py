"""
Example vectorizer demonstrating algorithm-specific settings.
This shows how a vectorizer can have completely different settings
that don't exist in other vectorizers (like "booger").
"""
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

class ExampleBoogerVectorizer(BaseVectorizer):
    """
    Example vectorizer with completely custom settings including "booger".
    This demonstrates that each vectorizer can have its own unique settings.
    """
    
    @property
    def name(self) -> str:
        return "Example Booger Vectorizer"
    
    @property
    def description(self) -> str:
        return "Example vectorizer with custom settings like 'booger' to demonstrate algorithm-specific settings"
    
    @property
    def algorithm_id(self) -> str:
        return "example_booger"
    
    def vectorize_image(
        self,
        image_data: bytes,
        settings: Optional[Dict[str, Any]] = None,
        output_dir: Optional[str] = None,
        base_filename: Optional[str] = None,
    ) -> VectorizationResult:
        """Vectorize using booger algorithm"""
        start_time = datetime.now()
        
        # Get settings - notice "booger" is a valid setting here!
        booger = settings.get("booger", 42) if settings else 42
        wibble = settings.get("wibble", 3.14) if settings else 3.14
        enable_frobnication = settings.get("enable_frobnication", True) if settings else True
        
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            original_size = image.size
            
            # Convert to numpy array
            img_array = np.array(image.convert('RGB'))
            
            # Apply "booger" effect (simple threshold based on booger value)
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            threshold = int(booger) % 256
            _, thresh = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
            
            # Apply "wibble" smoothing if enabled
            if enable_frobnication:
                kernel_size = max(1, int(wibble * 2))
                if kernel_size % 2 == 0:
                    kernel_size += 1
                thresh = cv2.GaussianBlur(thresh, (kernel_size, kernel_size), 0)
            
            # Find contours
            contours, _ = cv2.findContours(
                thresh,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            # Convert to paths
            paths = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 10:
                    continue
                
                points = [(float(p[0][0]), float(p[0][1])) for p in contour]
                if len(points) < 3:
                    continue
                
                if points[0] != points[-1]:
                    points.append(points[0])
                
                x_coords = [p[0] for p in points]
                y_coords = [p[1] for p in points]
                bbox = (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
                
                path = VectorPath(
                    points=points,
                    color=(0, 0, 0),
                    is_closed=True,
                    area=area,
                    bounding_box=bbox
                )
                paths.append(path)
            
            paths.sort(key=lambda p: p.area, reverse=True)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = VectorizationResult(
                paths=paths,
                original_size=original_size,
                processed_size=original_size,
                colors_detected=1,
                total_paths=len(paths),
                processing_time=processing_time,
                settings_used=settings or {},
                source_image_name=base_filename,
            )
            
            if output_dir and paths:
                svg_path = self._create_svg(result, output_dir, base_filename)
                result.svg_path = svg_path
            
            return result
            
        except Exception as e:
            logger.error(f"Booger vectorization error: {e}")
            raise
    
    def _create_svg(self, result: VectorizationResult, output_dir: str, base_filename: Optional[str] = None) -> Optional[str]:
        """Create SVG file"""
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
                '  <defs><style>.path { fill: none; stroke-width: 1; }</style></defs>'
            ]
            
            for i, path in enumerate(result.paths):
                if len(path.points) < 2:
                    continue
                
                path_data = "M " + " L ".join([f"{x:.2f} {y:.2f}" for x, y in path.points])
                if path.is_closed:
                    path_data += " Z"
                
                color_hex = "#{:02x}{:02x}{:02x}".format(*path.color)
                svg_lines.append(f'  <path d="{path_data}" class="path" stroke="{color_hex}" id="path_{i}"/>')
            
            svg_lines.append('</svg>')
            
            with open(svg_path, 'w') as f:
                f.write('\n'.join(svg_lines))
            
            return str(svg_path)
        except Exception as e:
            logger.error(f"SVG creation error: {e}")
            return None
    
    def export_to_svg(self, result: VectorizationResult, output_path: str) -> bool:
        output_dir = str(Path(output_path).parent)
        base_filename = Path(output_path).stem
        svg_path = self._create_svg(result, output_dir, base_filename)
        return svg_path is not None
    
    def export_to_plotting_commands(
        self, 
        result: VectorizationResult, 
        machine_settings: Dict[str, Any]
    ) -> List[str]:
        """Export to plotting commands"""
        commands = []
        commands.append("C24,{},{}".format(
            machine_settings.get("width", 1000),
            machine_settings.get("height", 1000)
        ))
        commands.append("C29,{}".format(machine_settings.get("mm_per_rev", 95.0)))
        commands.append("C30,{}".format(machine_settings.get("steps_per_rev", 200.0)))
        
        for path in result.paths:
            if len(path.points) < 2:
                continue
            x, y = path.points[0]
            commands.append("C09,{:.2f},{:.2f}".format(x, y))
            commands.append("C13")
            for x, y in path.points[1:]:
                commands.append("C01,{:.2f},{:.2f}".format(x, y))
            commands.append("C14")
        
        return commands
    
    def get_vectorization_preview(self, result: VectorizationResult) -> str:
        """Generate preview"""
        try:
            from PIL import ImageDraw
            width, height = result.processed_size
            preview_img = Image.new('RGB', (width, height), 'white')
            draw = ImageDraw.Draw(preview_img)
            
            for path in result.paths:
                if len(path.points) >= 2:
                    draw.line(path.points, fill=tuple(path.color), width=1)
            
            buffer = io.BytesIO()
            preview_img.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            return f"data:image/png;base64,{img_base64}"
        except Exception as e:
            logger.error(f"Preview error: {e}")
            return ""
    
    def get_default_settings(self) -> Dict[str, Any]:
        """Return default settings - notice 'booger' is a valid setting!"""
        return {
            "booger": 42,  # This setting doesn't exist in other vectorizers!
            "wibble": 3.14,  # Another custom setting
            "enable_frobnication": True  # Yet another custom setting
        }
    
    def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Validate settings including 'booger'"""
        validated = self.get_default_settings()
        validated.update(settings)
        
        # Validate booger (0-255 range)
        validated["booger"] = max(0, min(255, int(validated.get("booger", 42))))
        
        # Validate wibble (0.1 to 10.0)
        validated["wibble"] = max(0.1, min(10.0, float(validated.get("wibble", 3.14))))
        
        # Validate boolean
        validated["enable_frobnication"] = bool(validated.get("enable_frobnication", True))
        
        return validated
