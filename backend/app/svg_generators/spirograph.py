from typing import Dict, Any, Optional
import logging
from datetime import datetime
from pathlib import Path
import base64
import io
import math

from . import BaseSvgGenerator, SvgGenerationResult
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

class SpirographGenerator(BaseSvgGenerator):
    """
    Generates spirograph pattern SVGs using hypotrochoid/epitrochoid mathematics.
    
    Based on Wikipedia spirograph equations:
    x(t) = R * [(1 - k) * cos(t) + l * k * cos((1 - k)/k * t)]
    y(t) = R * [(1 - k) * sin(t) - l * k * sin((1 - k)/k * t)]
    
    Where:
    - R = radius of fixed outer circle
    - r = radius of rolling inner circle  
    - k = r/R (ratio)
    - l = ρ/r (pen distance ratio)
    - ρ = distance from center of inner circle to pen point
    """
    
    def __init__(self):
        pass
    
    @property
    def name(self) -> str:
        return "Spirograph"
    
    @property
    def description(self) -> str:
        return "Generate spirograph patterns using hypotrochoid/epitrochoid mathematics"
    
    @property
    def generator_id(self) -> str:
        return "spirograph"
    
    def generate_svg(
        self,
        settings: Optional[Dict[str, Any]] = None,
        output_dir: Optional[str] = None,
        base_filename: Optional[str] = None,
    ) -> SvgGenerationResult:
        """
        Generate a spirograph pattern SVG.
        
        Parameters:
        - outer_radius: Radius of fixed outer circle (default: 200)
        - inner_radius: Radius of rolling inner circle (default: 60)
        - pen_distance: Distance from center of inner circle to pen point (default: 50)
        - num_cycles: Number of complete cycles to draw (default: 10)
        - num_points: Number of points to calculate (default: 1000)
        - width: SVG width in pixels (default: 800)
        - height: SVG height in pixels (default: 800)
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
        
        outer_radius = settings.get("outer_radius", 200)
        inner_radius = settings.get("inner_radius", 60)
        pen_distance = settings.get("pen_distance", 50)
        complete_pattern = settings.get("complete_pattern", False)
        num_cycles = settings.get("num_cycles", 10)
        num_points = settings.get("num_points", 1000)
        
        # If complete_pattern is enabled, calculate the number of cycles needed
        if complete_pattern:
            calculated_cycles = self._calculate_complete_cycles(outer_radius, inner_radius)
            num_cycles = calculated_cycles
            # Update settings to reflect the calculated value
            settings["num_cycles"] = calculated_cycles
        width = settings.get("width", 800)
        height = settings.get("height", 800)
        stroke_width = settings.get("stroke_width", 1)
        stroke_color = settings.get("stroke_color", "#000000")
        background_color = settings.get("background_color", "#ffffff")
        
        try:
            # Generate spirograph SVG
            svg_content = self._generate_spirograph(
                outer_radius, inner_radius, pen_distance, num_cycles, num_points,
                width, height, stroke_width, stroke_color, background_color,
                complete_pattern
            )
            
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
            logger.error(f"Spirograph generation error: {e}")
            raise
    
    def _calculate_complete_cycles(self, outer_radius: float, inner_radius: float) -> float:
        """
        Calculate the number of cycles needed to complete the pattern.
        
        For a hypotrochoid, the pattern closes when the inner circle completes
        enough rotations relative to the outer circle. The rotation ratio is (R-r)/r.
        
        If we write (R-r)/r as a fraction a/b in lowest terms, the pattern closes
        after b rotations of the inner circle relative to the outer, which corresponds
        to a rotations of the outer reference (parameter t).
        
        Returns the number of cycles (outer rotations) needed to complete the pattern.
        """
        if outer_radius <= 0 or inner_radius <= 0:
            return 10.0  # Fallback
        
        if inner_radius >= outer_radius:
            return 1.0  # Invalid case, return minimum
        
        from math import gcd
        
        # Convert to integers to find GCD
        # Use a large scale to maintain precision
        scale = 1000000
        R_int = int(round(outer_radius * scale))
        r_int = int(round(inner_radius * scale))
        
        # Calculate (R - r) and r
        R_minus_r = R_int - r_int
        
        if R_minus_r <= 0:
            return 1.0
        
        # Find GCD to simplify the ratio (R-r)/r
        common_divisor = gcd(R_minus_r, r_int)
        a = R_minus_r // common_divisor
        b = r_int // common_divisor
        
        # The pattern closes after 'a' rotations of the outer reference
        # This is the number of cycles we need
        cycles = float(a)
        
        return max(1.0, cycles)
    
    def _generate_spirograph(
        self,
        outer_radius: float,
        inner_radius: float,
        pen_distance: float,
        num_cycles: float,
        num_points: int,
        width: int,
        height: int,
        stroke_width: float,
        stroke_color: str,
        bg_color: str,
        complete_pattern: bool = False
    ) -> str:
        """Generate spirograph pattern using parametric equations"""
        
        # Calculate parameters
        # k = r/R (ratio of inner to outer radius)
        k = inner_radius / outer_radius if outer_radius > 0 else 0.3
        
        # l = ρ/r (pen distance ratio)
        l = pen_distance / inner_radius if inner_radius > 0 else 0.833
        
        # Center the pattern in the SVG
        center_x = width / 2
        center_y = height / 2
        
        # Calculate points using parametric equations
        points = []
        # If complete_pattern, ensure we end exactly at the closing point
        # Otherwise, use the specified number of points
        num_points_to_use = num_points + 1 if complete_pattern else num_points
        for i in range(num_points_to_use):
            # t ranges from 0 to 2π * num_cycles
            # When complete_pattern is true, the last point (i=num_points) will be at t=2π*num_cycles
            # When false, the last point (i=num_points-1) will be slightly before 2π*num_cycles
            t = i * (2 * math.pi * num_cycles) / num_points if num_points > 0 else 0
            
            # Spirograph parametric equations (hypotrochoid - inner circle rolls inside)
            x = outer_radius * ((1 - k) * math.cos(t) + l * k * math.cos((1 - k) / k * t))
            y = outer_radius * ((1 - k) * math.sin(t) - l * k * math.sin((1 - k) / k * t))
            
            # Offset to center in SVG
            points.append((center_x + x, center_y + y))
        
        # Build SVG
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
            f'  <rect width="{width}" height="{height}" fill="{bg_color}"/>',
        ]
        
        # Create path from points
        if len(points) > 0:
            path_data = f'M {points[0][0]:.2f} {points[0][1]:.2f}'
            for point in points[1:]:
                path_data += f' L {point[0]:.2f} {point[1]:.2f}'
            
            # Close the path if complete_pattern is enabled
            # This ensures the pattern connects smoothly at the start/end point
            if complete_pattern:
                path_data += ' Z'
            
            lines.append(
                f'  <path d="{path_data}" fill="none" stroke="{stroke_color}" stroke-width="{stroke_width}"/>'
            )
        
        lines.append('</svg>')
        return '\n'.join(lines)
    
    def _save_svg(self, svg_content: str, output_dir: str, base_filename: Optional[str] = None) -> Optional[str]:
        """Save SVG content to file"""
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name_root = (base_filename or "spirograph").strip() or "spirograph"
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
        """Generate base64 preview of generated SVG by rendering the actual SVG content"""
        try:
            if not result.svg_content:
                logger.warning("No SVG content available for preview")
                return ""
            
            # Use cairosvg to convert SVG to PNG
            try:
                import cairosvg
                from PIL import Image
                
                # Convert SVG string to PNG bytes
                png_bytes = cairosvg.svg2png(
                    bytestring=result.svg_content.encode('utf-8'),
                    output_width=min(result.width, 800),  # Limit preview size for performance
                    output_height=min(result.height, 800),
                )
                
                # Convert PNG bytes to base64
                img_base64 = base64.b64encode(png_bytes).decode()
                return f"data:image/png;base64,{img_base64}"
                
            except ImportError:
                # Fallback: if cairosvg is not available, use a simple placeholder
                logger.warning("cairosvg not available, using fallback preview")
                from PIL import Image, ImageDraw
                
                preview_img = Image.new('RGB', (result.width, result.height), 'white')
                draw = ImageDraw.Draw(preview_img)
                draw.rectangle([(0, 0), (result.width - 1, result.height - 1)], outline='black', width=2)
                
                # Draw text indicating SVG preview
                try:
                    from PIL import ImageFont
                    # Try to use default font
                    font = ImageFont.load_default()
                except:
                    font = None
                
                text = "SVG Preview\n(cairosvg required)"
                draw.text((10, 10), text, fill='black', font=font)
                
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
            "outer_radius": 200,
            "inner_radius": 60,
            "pen_distance": 50,
            "complete_pattern": False,
            "num_cycles": 10,
            "num_points": 1000,
            "width": 800,
            "height": 800,
            "stroke_width": 1,
            "stroke_color": "#000000",
            "background_color": "#ffffff"
        }
    
    def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize settings"""
        validated = self.get_default_settings()
        validated.update(settings)
        
        # Clamp values to valid ranges
        validated["outer_radius"] = max(10, min(500, float(validated.get("outer_radius", 200))))
        validated["inner_radius"] = max(5, min(validated["outer_radius"] * 0.9, float(validated.get("inner_radius", 60))))
        validated["pen_distance"] = max(0, min(validated["inner_radius"] * 2, float(validated.get("pen_distance", 50))))
        validated["complete_pattern"] = bool(validated.get("complete_pattern", False))
        # If complete_pattern is enabled, num_cycles will be calculated automatically
        if not validated["complete_pattern"]:
            validated["num_cycles"] = max(1, min(100, int(validated.get("num_cycles", 10))))
        validated["num_points"] = max(100, min(10000, int(validated.get("num_points", 1000))))
        validated["width"] = max(100, min(5000, int(validated.get("width", 800))))
        validated["height"] = max(100, min(5000, int(validated.get("height", 800))))
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
            "outer_radius": {
                "description": "Radius of the fixed outer circle",
                "purpose": "Sets the size of the outer fixed circle that the inner circle rolls inside",
                "range": "10-500",
                "default": 200,
                "effects": "Larger values create larger patterns. Smaller values create more compact patterns. Should be larger than inner_radius.",
                "when_to_adjust": "Adjust to control the overall size of the spirograph pattern"
            },
            "inner_radius": {
                "description": "Radius of the rolling inner circle",
                "purpose": "Sets the size of the inner circle that rolls inside the outer circle",
                "range": "5 to 90% of outer_radius",
                "default": 60,
                "effects": "Larger values relative to outer_radius create simpler patterns with fewer loops. Smaller values create more complex patterns with many loops.",
                "when_to_adjust": "Adjust to control pattern complexity - smaller ratios create more intricate patterns"
            },
            "pen_distance": {
                "description": "Distance from center of inner circle to pen point",
                "purpose": "Controls how far the pen is from the center of the rolling circle",
                "range": "0 to 2× inner_radius",
                "default": 50,
                "effects": "When pen_distance = 0, creates a circle. When pen_distance = inner_radius, creates a cardioid. Larger values create more extended patterns.",
                "when_to_adjust": "Adjust to create different curve shapes - closer to 0 for simpler curves, closer to inner_radius for more interesting shapes"
            },
            "complete_pattern": {
                "description": "Complete the pattern so pen returns to start",
                "purpose": "When enabled, automatically calculates the number of cycles needed for the pattern to close perfectly",
                "range": "true/false",
                "default": False,
                "effects": "When enabled, the pattern will close exactly at the starting point. When disabled, use num_cycles to control pattern length manually.",
                "when_to_adjust": "Enable for closed patterns, disable to manually control pattern length"
            },
            "num_cycles": {
                "description": "Number of complete cycles to draw (only used when complete_pattern is false)",
                "purpose": "Controls how many times the inner circle completes a rotation",
                "range": "1-100",
                "default": 10,
                "effects": "More cycles create more complete patterns that may close on themselves. Fewer cycles create partial patterns. Ignored when complete_pattern is enabled.",
                "when_to_adjust": "Adjust when complete_pattern is disabled. Increase to see more of the pattern, decrease for partial patterns"
            },
            "num_points": {
                "description": "Number of points to calculate for the curve",
                "purpose": "Controls the resolution/smoothness of the curve",
                "range": "100-10000",
                "default": 1000,
                "effects": "More points create smoother curves but take longer to compute. Fewer points create faster but potentially jagged curves.",
                "when_to_adjust": "Increase for smoother curves, decrease for faster generation"
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
            "stroke_width": {
                "description": "Stroke width in pixels",
                "purpose": "Sets the line thickness for the spirograph curve",
                "range": "0.1-10.0",
                "default": 1,
                "effects": "Thicker strokes (3-10) create bolder patterns. Thinner strokes (0.1-1) create finer patterns.",
                "when_to_adjust": "Adjust based on desired line weight"
            },
            "stroke_color": {
                "description": "Stroke color as hex string",
                "purpose": "Sets the color of the spirograph curve",
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
