"""
Stippling Vectorizer - Point-based vectorization algorithm.
Converts images to stipple points, separates into white/black layers,
and connects points using nearest-neighbor to form continuous paths.
"""
from typing import Dict, Any, Optional, List, Tuple
import numpy as np
from PIL import Image
import io
import base64
import logging
import math
from datetime import datetime
from pathlib import Path

from . import BaseVectorizer, VectorizationResult
from ..vectorizer import VectorPath

logger = logging.getLogger(__name__)


class StipplingVectorizer(BaseVectorizer):
    """
    Stippling-based vectorization algorithm.
    Converts images to stipple points, separates them into white and black layers
    based on brightness thresholds, then connects points in each layer using
    nearest-neighbor algorithm to form continuous paths.
    """
    
    def __init__(self):
        pass
    
    @property
    def name(self) -> str:
        return "Stippling"
    
    @property
    def description(self) -> str:
        return "Stippling-based vectorization: converts images to points, separates into white/black layers with dead zone, connects using nearest-neighbor"
    
    @property
    def algorithm_id(self) -> str:
        return "stippling"
    
    def vectorize_image(
        self,
        image_data: bytes,
        settings: Optional[Dict[str, Any]] = None,
        output_dir: Optional[str] = None,
        base_filename: Optional[str] = None,
    ) -> VectorizationResult:
        """
        Vectorize using stippling algorithm.
        
        Parameters:
        - point_spacing: Distance between stipple points in pixels (default: 5)
        - white_threshold: Minimum brightness for white layer (0-255, default: 180)
        - black_threshold: Maximum brightness for black layer (0-255, default: 75)
        - min_points_per_layer: Minimum points required to create a layer path (default: 2)
        - adaptive_density: Use adaptive density based on image intensity (default: False)
        """
        start_time = datetime.now()
        
        # Get settings with defaults
        if settings is None:
            settings = self.get_default_settings()
        else:
            defaults = self.get_default_settings()
            defaults.update(settings)
            settings = defaults
        
        # Validate settings
        settings = self.validate_settings(settings)
        
        point_spacing = settings.get("point_spacing", 5)
        white_threshold = settings.get("white_threshold", 180)
        black_threshold = settings.get("black_threshold", 75)
        min_points_per_layer = settings.get("min_points_per_layer", 2)
        adaptive_density = settings.get("adaptive_density", False)
        
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            original_size = image.size
            
            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            # Convert to numpy array
            img_array = np.array(image)
            height, width = img_array.shape
            
            # Generate stipple points
            stipple_points = self._generate_stipple_points(
                img_array, point_spacing, adaptive_density
            )
            
            # Separate points into white and black layers
            white_points = []
            black_points = []
            
            for x, y, brightness in stipple_points:
                if brightness >= white_threshold:
                    white_points.append((x, y))
                elif brightness <= black_threshold:
                    black_points.append((x, y))
                # Points between thresholds are ignored (dead zone)
            
            # Connect points in each layer using nearest neighbor
            paths = []
            
            # White layer path
            if len(white_points) >= min_points_per_layer:
                white_path_points = self._connect_nearest_neighbor(white_points)
                if white_path_points:
                    white_path = self._create_path(white_path_points, (255, 255, 255), width, height)
                    paths.append(white_path)
            
            # Black layer path
            if len(black_points) >= min_points_per_layer:
                black_path_points = self._connect_nearest_neighbor(black_points)
                if black_path_points:
                    black_path = self._create_path(black_path_points, (0, 0, 0), width, height)
                    paths.append(black_path)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Create result
            result = VectorizationResult(
                paths=paths,
                original_size=original_size,
                processed_size=original_size,
                colors_detected=2 if (len(white_points) > 0 and len(black_points) > 0) else 1,
                total_paths=len(paths),
                processing_time=processing_time,
                settings_used=settings,
                source_image_name=base_filename,
            )
            
            # Create SVG if output directory provided
            if output_dir and paths:
                svg_path = self._create_svg(result, output_dir, base_filename)
                result.svg_path = svg_path
            
            return result
            
        except Exception as e:
            logger.error(f"Stippling vectorization error: {e}")
            raise
    
    def _generate_stipple_points(
        self,
        img_array: np.ndarray,
        point_spacing: int,
        adaptive_density: bool
    ) -> List[Tuple[float, float, int]]:
        """
        Generate stipple points from image.
        
        Returns:
            List of (x, y, brightness) tuples
        """
        height, width = img_array.shape
        points = []
        
        if adaptive_density:
            # Adaptive density: more points in darker areas
            # This is a simplified version - could be enhanced
            for y in range(0, height, point_spacing):
                for x in range(0, width, point_spacing):
                    brightness = int(img_array[y, x])
                    # Invert brightness for adaptive: darker = more likely to include
                    # For now, use uniform grid with adaptive as future enhancement
                    points.append((float(x), float(y), brightness))
        else:
            # Uniform grid sampling
            for y in range(0, height, point_spacing):
                for x in range(0, width, point_spacing):
                    brightness = int(img_array[y, x])
                    points.append((float(x), float(y), brightness))
        
        return points
    
    def _connect_nearest_neighbor(
        self,
        points: List[Tuple[float, float]]
    ) -> List[Tuple[float, float]]:
        """
        Connect points using greedy nearest-neighbor algorithm.
        
        Args:
            points: List of (x, y) coordinate tuples
            
        Returns:
            Ordered list of points forming a continuous path
        """
        if not points:
            return []
        
        if len(points) == 1:
            return points
        
        # Start with first point
        path = [points[0]]
        remaining = set(points[1:])
        
        current_point = points[0]
        
        while remaining:
            # Find nearest unvisited neighbor
            nearest = None
            min_distance = float('inf')
            
            for point in remaining:
                distance = self._euclidean_distance(current_point, point)
                if distance < min_distance:
                    min_distance = distance
                    nearest = point
            
            if nearest is None:
                break
            
            # Add to path and remove from remaining
            path.append(nearest)
            remaining.remove(nearest)
            current_point = nearest
        
        return path
    
    def _euclidean_distance(
        self,
        p1: Tuple[float, float],
        p2: Tuple[float, float]
    ) -> float:
        """Calculate Euclidean distance between two points"""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        return math.sqrt(dx * dx + dy * dy)
    
    def _create_path(
        self,
        points: List[Tuple[float, float]],
        color: Tuple[int, int, int],
        width: int,
        height: int
    ) -> VectorPath:
        """Create a VectorPath from ordered points"""
        if not points:
            raise ValueError("Cannot create path from empty point list")
        
        # Calculate bounding box
        x_coords = [p[0] for p in points]
        y_coords = [p[1] for p in points]
        bbox = (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
        
        # Calculate approximate area (sum of line segments)
        area = 0.0
        for i in range(len(points) - 1):
            area += self._euclidean_distance(points[i], points[i + 1])
        
        return VectorPath(
            points=points,
            color=color,
            is_closed=False,  # Stippling paths are not closed
            area=area,
            bounding_box=bbox
        )
    
    def _create_svg(
        self,
        result: VectorizationResult,
        output_dir: str,
        base_filename: Optional[str] = None
    ) -> Optional[str]:
        """Create SVG file for the result"""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name_root = (base_filename or "stippled").strip() or "stippled"
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
        
        # Drawing commands for each path
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
        """Return default settings for this vectorizer"""
        return {
            "point_spacing": 5,
            "white_threshold": 180,
            "black_threshold": 75,
            "min_points_per_layer": 2,
            "adaptive_density": False
        }
    
    def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize settings"""
        validated = self.get_default_settings()
        validated.update(settings)
        
        # Clamp values to valid ranges
        validated["point_spacing"] = max(1, int(validated.get("point_spacing", 5)))
        validated["white_threshold"] = max(0, min(255, int(validated.get("white_threshold", 180))))
        validated["black_threshold"] = max(0, min(255, int(validated.get("black_threshold", 75))))
        validated["min_points_per_layer"] = max(1, int(validated.get("min_points_per_layer", 2)))
        validated["adaptive_density"] = bool(validated.get("adaptive_density", False))
        
        # Ensure white_threshold > black_threshold for dead zone
        if validated["white_threshold"] <= validated["black_threshold"]:
            # Adjust to create a valid dead zone
            mid = (validated["white_threshold"] + validated["black_threshold"]) // 2
            validated["white_threshold"] = min(255, mid + 10)
            validated["black_threshold"] = max(0, mid - 10)
            logger.warning(
                f"Adjusted thresholds to create dead zone: "
                f"white_threshold={validated['white_threshold']}, "
                f"black_threshold={validated['black_threshold']}"
            )
        
        return validated
    
    def get_parameter_documentation(self) -> Dict[str, Dict[str, Any]]:
        """Return parameter documentation for this vectorizer"""
        return {
            "point_spacing": {
                "description": "Distance between stipple points in pixels",
                "purpose": "Controls the density of stipple points sampled from the image",
                "range": "1-50 (typically 3-10)",
                "default": 5,
                "effects": "Small values (1-3): Very dense point sampling, more detail but slower processing. Medium values (5-10): Balanced density. Large values (15+): Sparse sampling, faster but less detail.",
                "when_to_adjust": "Decrease for more detailed output, increase for faster processing or simpler results"
            },
            "white_threshold": {
                "description": "Minimum brightness for white layer",
                "purpose": "Points with brightness >= this value are assigned to the white layer",
                "range": "0-255",
                "default": 180,
                "effects": "Low values (0-100): More points in white layer. Medium values (150-200): Balanced. High values (220-255): Only very bright areas in white layer.",
                "when_to_adjust": "Decrease to include more light areas in white layer, increase to only include very bright areas"
            },
            "black_threshold": {
                "description": "Maximum brightness for black layer",
                "purpose": "Points with brightness <= this value are assigned to the black layer",
                "range": "0-255",
                "default": 75,
                "effects": "Low values (0-50): Only very dark areas in black layer. Medium values (50-100): Balanced. High values (150-255): More points in black layer.",
                "when_to_adjust": "Increase to include more dark areas in black layer, decrease to only include very dark areas"
            },
            "min_points_per_layer": {
                "description": "Minimum points required to create a layer path",
                "purpose": "Layers with fewer points than this will be skipped",
                "range": "1-100 (typically 2-10)",
                "default": 2,
                "effects": "Low values (1-2): Include even very sparse layers. Higher values (5-10): Filter out sparse layers that may be noise.",
                "when_to_adjust": "Increase to filter out sparse/noisy layers, decrease to preserve all layers"
            },
            "adaptive_density": {
                "description": "Use adaptive density based on image intensity",
                "purpose": "When enabled, adjusts point density based on local image intensity (future enhancement)",
                "range": "boolean",
                "default": False,
                "effects": "False: Uniform grid sampling. True: Adaptive sampling (currently same as uniform, enhancement planned).",
                "when_to_adjust": "Currently has no effect, reserved for future adaptive sampling implementation"
            }
        }
