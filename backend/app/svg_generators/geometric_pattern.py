from typing import Dict, Any, Optional
import logging
from datetime import datetime
from pathlib import Path
import base64
import io

from . import BaseSvgGenerator, SvgGenerationResult
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

class GeometricPatternGenerator(BaseSvgGenerator):
    """
    Generates geometric pattern SVGs (grid, mandala, spiral patterns).
    Demonstrates the SVG generator plugin interface.
    """
    
    def __init__(self):
        pass
    
    @property
    def name(self) -> str:
        return "Geometric Pattern"
    
    @property
    def description(self) -> str:
        return "Generate geometric pattern SVGs (grid, mandala, spiral)"
    
    @property
    def generator_id(self) -> str:
        return "geometric_pattern"
    
    def generate_svg(
        self,
        settings: Optional[Dict[str, Any]] = None,
        output_dir: Optional[str] = None,
        base_filename: Optional[str] = None,
    ) -> SvgGenerationResult:
        """
        Generate a geometric pattern SVG.
        
        Parameters:
        - pattern_type: Type of pattern ("grid", "mandala", "spiral") (default: "grid")
        - width: SVG width in pixels (default: 800)
        - height: SVG height in pixels (default: 800)
        - complexity: Pattern complexity level (1-10, default: 5)
        - stroke_width: Stroke width in pixels (default: 1)
        - stroke_color: Stroke color as hex string (default: "#000000")
        - background_color: Background color as hex string (default: "#ffffff")
        """
        start_time = datetime.now()
        
        # Get settings with defaults
        if not settings:
            settings = self.get_default_settings()
        else:
            settings = self.validate_settings(settings)
        
        pattern_type = settings.get("pattern_type", "grid")
        width = settings.get("width", 800)
        height = settings.get("height", 800)
        complexity = settings.get("complexity", 5)
        stroke_width = settings.get("stroke_width", 1)
        stroke_color = settings.get("stroke_color", "#000000")
        background_color = settings.get("background_color", "#ffffff")
        
        try:
            # Generate SVG content based on pattern type
            if pattern_type == "grid":
                svg_content = self._generate_grid(width, height, complexity, stroke_width, stroke_color, background_color)
            elif pattern_type == "mandala":
                svg_content = self._generate_mandala(width, height, complexity, stroke_width, stroke_color, background_color)
            elif pattern_type == "spiral":
                svg_content = self._generate_spiral(width, height, complexity, stroke_width, stroke_color, background_color)
            else:
                svg_content = self._generate_grid(width, height, complexity, stroke_width, stroke_color, background_color)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Save to file if output directory provided
            svg_path = None
            if output_dir:
                svg_path = self._save_svg(svg_content, output_dir, base_filename)
            
            # Create result
            result = SvgGenerationResult(
                svg_path=svg_path,
                svg_content=svg_content,
                width=width,
                height=height,
                processing_time=processing_time,
                settings_used=settings,
            )
            
            # Generate preview
            try:
                result.preview = self.get_generation_preview(result)
            except NotImplementedError:
                pass
            
            return result
            
        except Exception as e:
            logger.error(f"Geometric pattern generation error: {e}")
            raise
    
    def _generate_grid(self, width: int, height: int, complexity: int, stroke_width: float, stroke_color: str, bg_color: str) -> str:
        """Generate a grid pattern"""
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
            f'  <rect width="{width}" height="{height}" fill="{bg_color}"/>',
        ]
        
        # Calculate grid spacing based on complexity
        num_lines = max(5, min(50, complexity * 5))
        spacing_x = width / (num_lines + 1)
        spacing_y = height / (num_lines + 1)
        
        # Vertical lines
        for i in range(1, num_lines + 1):
            x = i * spacing_x
            lines.append(f'  <line x1="{x:.2f}" y1="0" x2="{x:.2f}" y2="{height}" stroke="{stroke_color}" stroke-width="{stroke_width}"/>')
        
        # Horizontal lines
        for i in range(1, num_lines + 1):
            y = i * spacing_y
            lines.append(f'  <line x1="0" y1="{y:.2f}" x2="{width}" y2="{y:.2f}" stroke="{stroke_color}" stroke-width="{stroke_width}"/>')
        
        lines.append('</svg>')
        return '\n'.join(lines)
    
    def _generate_mandala(self, width: int, height: int, complexity: int, stroke_width: float, stroke_color: str, bg_color: str) -> str:
        """Generate a mandala pattern"""
        center_x = width / 2
        center_y = height / 2
        max_radius = min(width, height) / 2 - 20
        
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
            f'  <rect width="{width}" height="{height}" fill="{bg_color}"/>',
        ]
        
        # Generate concentric circles and radial lines
        num_circles = max(3, min(20, complexity))
        num_rays = max(6, min(36, complexity * 4))
        
        # Concentric circles
        for i in range(1, num_circles + 1):
            radius = (max_radius / num_circles) * i
            lines.append(f'  <circle cx="{center_x:.2f}" cy="{center_y:.2f}" r="{radius:.2f}" fill="none" stroke="{stroke_color}" stroke-width="{stroke_width}"/>')
        
        # Radial lines
        import math
        for i in range(num_rays):
            angle = (2 * math.pi / num_rays) * i
            x2 = center_x + max_radius * math.cos(angle)
            y2 = center_y + max_radius * math.sin(angle)
            lines.append(f'  <line x1="{center_x:.2f}" y1="{center_y:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{stroke_color}" stroke-width="{stroke_width}"/>')
        
        lines.append('</svg>')
        return '\n'.join(lines)
    
    def _generate_spiral(self, width: int, height: int, complexity: int, stroke_width: float, stroke_color: str, bg_color: str) -> str:
        """Generate a spiral pattern"""
        center_x = width / 2
        center_y = height / 2
        max_radius = min(width, height) / 2 - 20
        
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
            f'  <rect width="{width}" height="{height}" fill="{bg_color}"/>',
        ]
        
        # Generate spiral path
        import math
        num_turns = max(2, min(10, complexity))
        num_points = num_turns * 100
        
        path_data = "M "
        for i in range(num_points):
            t = (i / num_points) * num_turns * 2 * math.pi
            radius = (max_radius / num_points) * i
            x = center_x + radius * math.cos(t)
            y = center_y + radius * math.sin(t)
            if i == 0:
                path_data += f"{x:.2f} {y:.2f}"
            else:
                path_data += f" L {x:.2f} {y:.2f}"
        
        lines.append(f'  <path d="{path_data}" fill="none" stroke="{stroke_color}" stroke-width="{stroke_width}"/>')
        lines.append('</svg>')
        return '\n'.join(lines)
    
    def _save_svg(self, svg_content: str, output_dir: str, base_filename: Optional[str] = None) -> Optional[str]:
        """Save SVG content to file"""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name_root = (base_filename or "generated").strip() or "generated"
            svg_filename = f"{name_root}_{timestamp}.svg"
            svg_path = output_path / svg_filename
            
            with open(svg_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            
            logger.info(f"SVG saved: {svg_path}")
            return str(svg_path)
            
        except Exception as e:
            logger.error(f"SVG save error: {e}")
            return None
    
    def get_generation_preview(self, result: SvgGenerationResult) -> str:
        """Generate base64 preview of generated SVG"""
        try:
            # For preview, we'll render the SVG to a PNG image
            # This is a simple approach - in production you might use cairosvg or similar
            from PIL import Image, ImageDraw
            
            # Create a white background
            preview_img = Image.new('RGB', (result.width, result.height), 'white')
            draw = ImageDraw.Draw(preview_img)
            
            # For a simple preview, we'll just draw a border and some placeholder content
            # In a real implementation, you'd parse the SVG and render it
            draw.rectangle([(0, 0), (result.width - 1, result.height - 1)], outline='black', width=2)
            
            # Draw a simple pattern indicator
            settings = result.settings_used or {}
            pattern_type = settings.get("pattern_type", "grid")
            center_x = result.width / 2
            center_y = result.height / 2
            
            if pattern_type == "grid":
                # Draw a simple grid preview
                for i in range(3):
                    x = (result.width / 4) * (i + 1)
                    y = (result.height / 4) * (i + 1)
                    draw.line([(x, 0), (x, result.height)], fill='black', width=1)
                    draw.line([(0, y), (result.width, y)], fill='black', width=1)
            elif pattern_type == "mandala":
                # Draw a simple circle preview
                radius = min(result.width, result.height) / 4
                draw.ellipse(
                    [(center_x - radius, center_y - radius), (center_x + radius, center_y + radius)],
                    outline='black', width=2
                )
            elif pattern_type == "spiral":
                # Draw a simple spiral preview
                import math
                for i in range(50):
                    t = i * 0.1
                    r = t * 5
                    x = center_x + r * math.cos(t)
                    y = center_y + r * math.sin(t)
                    if i == 0:
                        last_point = (x, y)
                    else:
                        draw.line([last_point, (x, y)], fill='black', width=1)
                        last_point = (x, y)
            
            # Convert to base64
            buffer = io.BytesIO()
            preview_img.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_base64}"
            
        except Exception as e:
            logger.error(f"Preview generation error: {e}")
            return ""
    
    def get_default_settings(self) -> Dict[str, Any]:
        """Return default settings for this generator"""
        return {
            "pattern_type": "grid",
            "width": 800,
            "height": 800,
            "complexity": 5,
            "stroke_width": 1,
            "stroke_color": "#000000",
            "background_color": "#ffffff"
        }
    
    def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize settings"""
        validated = self.get_default_settings()
        validated.update(settings)
        
        # Validate pattern_type
        valid_patterns = ["grid", "mandala", "spiral"]
        if validated.get("pattern_type") not in valid_patterns:
            validated["pattern_type"] = "grid"
        
        # Clamp values to valid ranges
        validated["width"] = max(100, min(5000, int(validated.get("width", 800))))
        validated["height"] = max(100, min(5000, int(validated.get("height", 800))))
        validated["complexity"] = max(1, min(10, int(validated.get("complexity", 5))))
        validated["stroke_width"] = max(0.1, min(10.0, float(validated.get("stroke_width", 1))))
        
        # Validate colors (simple hex check)
        stroke_color = validated.get("stroke_color", "#000000")
        if not stroke_color.startswith("#") or len(stroke_color) != 7:
            validated["stroke_color"] = "#000000"
        
        bg_color = validated.get("background_color", "#ffffff")
        if not bg_color.startswith("#") or len(bg_color) != 7:
            validated["background_color"] = "#ffffff"
        
        return validated
    
    def get_parameter_documentation(self) -> Dict[str, Dict[str, Any]]:
        """Return parameter documentation for this generator"""
        return {
            "pattern_type": {
                "description": "Type of geometric pattern to generate",
                "purpose": "Selects the pattern algorithm (grid, mandala, or spiral)",
                "range": "grid, mandala, spiral",
                "default": "grid",
                "effects": "grid: Creates a regular grid pattern. mandala: Creates concentric circles with radial lines. spiral: Creates a spiral pattern.",
                "when_to_adjust": "Change to generate different pattern styles"
            },
            "width": {
                "description": "SVG width in pixels",
                "purpose": "Sets the width of the generated SVG",
                "range": "100-5000",
                "default": 800,
                "effects": "Larger values create wider patterns. Smaller values create narrower patterns.",
                "when_to_adjust": "Adjust based on desired output size"
            },
            "height": {
                "description": "SVG height in pixels",
                "purpose": "Sets the height of the generated SVG",
                "range": "100-5000",
                "default": 800,
                "effects": "Larger values create taller patterns. Smaller values create shorter patterns.",
                "when_to_adjust": "Adjust based on desired output size"
            },
            "complexity": {
                "description": "Pattern complexity level",
                "purpose": "Controls the detail level of the pattern",
                "range": "1-10",
                "default": 5,
                "effects": "Lower values (1-3) create simpler patterns with fewer elements. Higher values (7-10) create more complex patterns with more elements.",
                "when_to_adjust": "Increase for more detailed patterns, decrease for simpler patterns"
            },
            "stroke_width": {
                "description": "Stroke width in pixels",
                "purpose": "Sets the line thickness for pattern elements",
                "range": "0.1-10.0",
                "default": 1,
                "effects": "Thicker strokes (3-10) create bolder patterns. Thinner strokes (0.1-1) create finer patterns.",
                "when_to_adjust": "Adjust based on desired line weight"
            },
            "stroke_color": {
                "description": "Stroke color as hex string",
                "purpose": "Sets the color of pattern lines",
                "range": "Hex color string (e.g., #000000)",
                "default": "#000000",
                "effects": "Different colors create different visual styles. Black (#000000) is standard, but any hex color works.",
                "when_to_adjust": "Change to match desired color scheme"
            },
            "background_color": {
                "description": "Background color as hex string",
                "purpose": "Sets the background color of the SVG",
                "range": "Hex color string (e.g., #ffffff)",
                "default": "#ffffff",
                "effects": "White (#ffffff) is standard, but any hex color works. Transparent backgrounds can be achieved by setting this to match your display background.",
                "when_to_adjust": "Change to match desired background"
            }
        }
