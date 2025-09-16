import cv2
import numpy as np
from PIL import Image, ImageFilter
import io
import base64
import json
import logging
from typing import List, Tuple, Dict, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import math

logger = logging.getLogger(__name__)

@dataclass
class VectorizationSettings:
    """Settings for the vectorization process"""
    blur_radius: int = 1
    posterize_levels: int = 5
    simplification_threshold: float = 2.0
    simplification_iterations: int = 3
    min_contour_points: int = 3
    min_contour_area: int = 10
    color_tolerance: int = 10
    enable_color_separation: bool = True
    enable_contour_simplification: bool = True
    enable_noise_reduction: bool = True

@dataclass
class VectorPath:
    """Represents a single vector path"""
    points: List[Tuple[float, float]]
    color: Tuple[int, int, int]
    is_closed: bool = True
    area: float = 0.0
    bounding_box: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)

@dataclass
class VectorizationResult:
    """Result of the vectorization process"""
    paths: List[VectorPath]
    original_size: Tuple[int, int]
    processed_size: Tuple[int, int]
    colors_detected: int
    total_paths: int
    processing_time: float
    settings_used: VectorizationSettings
    svg_path: Optional[str] = None

class PolargraphVectorizer:
    """
    Vectorizer for converting raster images to vector paths suitable for polargraph plotting.
    Implements similar functionality to the legacy PolarGraph system.
    """
    
    def __init__(self):
        self.settings = VectorizationSettings()
    
    def set_settings(self, settings: VectorizationSettings) -> None:
        """Update vectorization settings"""
        self.settings = settings
    
    def vectorize_image(self, image_data: bytes, settings: Optional[VectorizationSettings] = None, 
                       output_dir: Optional[str] = None) -> VectorizationResult:
        """
        Main vectorization method - converts raster image to vector paths
        
        Args:
            image_data: Raw image bytes
            settings: Optional custom settings
            output_dir: Optional directory to save SVG file (if None, no SVG is saved)
            
        Returns:
            VectorizationResult containing all vector paths and metadata
        """
        start_time = datetime.now()
        
        if settings:
            self.settings = settings
        
        try:
            # Load and preprocess image
            image = Image.open(io.BytesIO(image_data))
            original_size = image.size
            
            # Preprocess image
            processed_image = self._preprocess_image(image)
            processed_size = processed_image.size
            
            # Create color separations
            if self.settings.enable_color_separation:
                color_separations = self._create_color_separations(processed_image)
            else:
                # Single color separation
                color_separations = {0: np.array(processed_image)}
            
            # Vectorize each color separation
            all_paths = []
            for color, separation in color_separations.items():
                paths = self._vectorize_separation(separation, color)
                all_paths.extend(paths)
            
            # Sort paths by area (largest first for efficient plotting)
            all_paths.sort(key=lambda p: p.area, reverse=True)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Create result object
            result = VectorizationResult(
                paths=all_paths,
                original_size=original_size,
                processed_size=processed_size,
                colors_detected=len(color_separations),
                total_paths=len(all_paths),
                processing_time=processing_time,
                settings_used=self.settings
            )
            
            # Automatically create SVG file if output directory is provided
            svg_path = None
            if output_dir and all_paths:
                import os
                from pathlib import Path
                
                # Ensure output directory exists
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
                
                # Generate unique SVG filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                svg_filename = f"vectorized_{timestamp}.svg"
                svg_path = str(output_path / svg_filename)
                
                # Export SVG
                if self.export_to_svg(result, svg_path):
                    result.svg_path = svg_path
                    logger.info(f"SVG file created: {svg_path}")
                else:
                    logger.warning(f"Failed to create SVG file: {svg_path}")
            
            return result
            
        except Exception as e:
            logger.error(f"Vectorization error: {e}")
            raise
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better vectorization"""
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Apply blur for noise reduction
        if self.settings.enable_noise_reduction and self.settings.blur_radius > 0:
            image = image.filter(ImageFilter.GaussianBlur(radius=self.settings.blur_radius))
        
        # Apply posterization to reduce color complexity
        if self.settings.posterize_levels > 1:
            image = image.quantize(colors=self.settings.posterize_levels).convert('RGB')
        
        return image
    
    def _create_color_separations(self, image: Image.Image) -> Dict[int, np.ndarray]:
        """Create separate images for each unique color"""
        # Convert to numpy array
        img_array = np.array(image)
        
        # Get unique colors
        unique_colors = self._extract_unique_colors(img_array)
        
        separations = {}
        for color in unique_colors:
            # Create binary mask for this color
            mask = self._create_color_mask(img_array, color)
            separations[color] = mask
        
        return separations
    
    def _extract_unique_colors(self, img_array: np.ndarray) -> List[int]:
        """Extract unique colors from image with tolerance"""
        # Reshape to 2D array of pixels
        pixels = img_array.reshape(-1, 3)
        
        # Group similar colors
        unique_colors = []
        for pixel in pixels:
            color_key = tuple(pixel)
            if not self._is_color_similar(color_key, unique_colors):
                unique_colors.append(color_key)
        
        return unique_colors
    
    def _is_color_similar(self, color: Tuple[int, int, int], existing_colors: List[Tuple[int, int, int]]) -> bool:
        """Check if color is similar to any existing color"""
        for existing in existing_colors:
            if all(abs(c - e) <= self.settings.color_tolerance for c, e in zip(color, existing)):
                return True
        return False
    
    def _create_color_mask(self, img_array: np.ndarray, target_color: Tuple[int, int, int]) -> np.ndarray:
        """Create binary mask for a specific color"""
        # Create tolerance range
        lower = np.array([max(0, c - self.settings.color_tolerance) for c in target_color])
        upper = np.array([min(255, c + self.settings.color_tolerance) for c in target_color])
        
        # Create mask
        mask = cv2.inRange(img_array, lower, upper)
        return mask
    
    def _vectorize_separation(self, separation: np.ndarray, color: Tuple[int, int, int]) -> List[VectorPath]:
        """Vectorize a single color separation"""
        paths = []
        
        # Find contours using OpenCV
        contours, _ = cv2.findContours(
            separation, 
            cv2.RETR_EXTERNAL, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        for contour in contours:
            # Filter by area
            area = cv2.contourArea(contour)
            if area < self.settings.min_contour_area:
                continue
            
            # Simplify contour if enabled
            if self.settings.enable_contour_simplification:
                simplified_contour = self._simplify_contour(contour)
            else:
                simplified_contour = contour
            
            # Convert to path
            if len(simplified_contour) >= self.settings.min_contour_points:
                path = self._contour_to_path(simplified_contour, color, area)
                if path:
                    paths.append(path)
        
        return paths
    
    def _simplify_contour(self, contour: np.ndarray) -> np.ndarray:
        """Simplify contour using Douglas-Peucker algorithm"""
        simplified = contour.copy()
        
        for _ in range(self.settings.simplification_iterations):
            epsilon = self.settings.simplification_threshold
            simplified = cv2.approxPolyDP(simplified, epsilon, True)
            
            # Stop if simplification doesn't reduce points significantly
            if len(simplified) <= 3:
                break
        
        return simplified
    
    def _contour_to_path(self, contour: np.ndarray, color: Tuple[int, int, int], area: float) -> Optional[VectorPath]:
        """Convert OpenCV contour to VectorPath"""
        try:
            # Extract points from contour
            points = []
            for point in contour:
                x, y = point[0]
                points.append((float(x), float(y)))
            
            if len(points) < self.settings.min_contour_points:
                return None
            
            # Calculate bounding box
            x_coords = [p[0] for p in points]
            y_coords = [p[1] for p in points]
            bbox = (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
            
            # Ensure path is closed
            if points[0] != points[-1]:
                points.append(points[0])
            
            return VectorPath(
                points=points,
                color=color,
                is_closed=True,
                area=area,
                bounding_box=bbox
            )
            
        except Exception as e:
            logger.warning(f"Failed to convert contour to path: {e}")
            return None
    
    def export_to_svg(self, result: VectorizationResult, output_path: str) -> bool:
        """Export vectorization result to SVG file"""
        try:
            svg_content = self._generate_svg_content(result)
            
            with open(output_path, 'w') as f:
                f.write(svg_content)
            
            logger.info(f"SVG exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"SVG export error: {e}")
            return False
    
    def create_svg_for_project(self, result: VectorizationResult, project_id: str, 
                              base_filename: str = None) -> Optional[str]:
        """
        Create SVG file for a specific project with organized naming
        
        Args:
            result: VectorizationResult to export
            project_id: Project identifier for directory structure
            base_filename: Base filename (without extension) - if None, uses timestamp
            
        Returns:
            Path to created SVG file, or None if failed
        """
        try:
            from pathlib import Path
            
            # Create project-specific directory structure
            project_dir = Path("local_storage/projects") / project_id
            project_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            if base_filename:
                # Use provided base filename
                svg_filename = f"{base_filename}.svg"
            else:
                # Use timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                svg_filename = f"vectorized_{timestamp}.svg"
            
            svg_path = project_dir / svg_filename
            
            # Export SVG
            if self.export_to_svg(result, str(svg_path)):
                logger.info(f"Project SVG created: {svg_path}")
                return str(svg_path)
            else:
                logger.error(f"Failed to create project SVG: {svg_path}")
                return None
                
        except Exception as e:
            logger.error(f"Project SVG creation error: {e}")
            return None
    
    def _generate_svg_content(self, result: VectorizationResult) -> str:
        """Generate SVG content from vectorization result"""
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
                
            # Convert points to SVG path format
            path_data = "M "
            for j, (x, y) in enumerate(path.points):
                if j == 0:
                    path_data += f"{x:.2f} {y:.2f}"
                else:
                    path_data += f" L {x:.2f} {y:.2f}"
            
            if path.is_closed:
                path_data += " Z"
            
            # Color as hex
            color_hex = "#{:02x}{:02x}{:02x}".format(*path.color)
            
            svg_lines.append(
                f'  <path d="{path_data}" class="path" stroke="{color_hex}" id="path_{i}"/>'
            )
        
        svg_lines.append('</svg>')
        
        return '\n'.join(svg_lines)
    
    def export_to_plotting_commands(self, result: VectorizationResult, 
                                  machine_settings: Dict[str, Any]) -> List[str]:
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
            # Create a simple preview image
            width, height = result.processed_size
            preview_img = Image.new('RGB', (width, height), 'white')
            
            # Draw paths (simplified for preview)
            from PIL import ImageDraw
            draw = ImageDraw.Draw(preview_img)
            
            for path in result.paths:
                if len(path.points) >= 2:
                    # Convert color tuple to RGB
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

# Convenience function for quick vectorization
def quick_vectorize(image_data: bytes, 
                   blur: int = 1, 
                   posterize: int = 5, 
                   simplify: float = 2.0,
                   output_dir: Optional[str] = None) -> VectorizationResult:
    """
    Quick vectorization with minimal settings
    
    Args:
        image_data: Raw image bytes
        blur: Blur radius for noise reduction
        posterize: Number of color levels
        simplify: Contour simplification threshold
        output_dir: Optional directory to save SVG file
    
    Returns:
        VectorizationResult
    """
    vectorizer = PolargraphVectorizer()
    settings = VectorizationSettings(
        blur_radius=blur,
        posterize_levels=posterize,
        simplification_threshold=simplify
    )
    
    return vectorizer.vectorize_image(image_data, settings, output_dir)

