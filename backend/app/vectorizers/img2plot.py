"""
Img2Plot Vectorizer - Edge detection based vectorization algorithm.
Converts images to vector paths by following edges using Sobel operators.
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

from scipy import ndimage
import skimage.exposure
import skimage.draw

from . import BaseVectorizer, VectorizationResult
from ..vectorizer import VectorPath

logger = logging.getLogger(__name__)


def rgb2gray(rgb):
    """Convert RGB image to grayscale"""
    return np.dot(rgb[..., :3], [0.299, 0.587, 0.114])


def bilinear_interpolate(img: np.ndarray, x: float, y: float) -> float:
    """Bilinear interpolation for sub-pixel sampling"""
    xfloat = x - math.floor(x)
    yfloat = y - math.floor(y)

    xfloor = int(math.floor(x))
    yfloor = int(math.floor(y))
    xceil = int(math.ceil(x))
    yceil = int(math.ceil(y))

    if xfloor < 0:
        xfloor = 0
    if xceil >= img.shape[1]:
        xceil = img.shape[1] - 1

    if yfloor < 0:
        yfloor = 0
    if yceil >= img.shape[0]:
        yceil = img.shape[0] - 1

    topLeft = img[yfloor, xfloor]
    topRight = img[yfloor, xceil]
    bottomLeft = img[yceil, xfloor]
    bottomRight = img[yceil, xceil]

    topMid = xfloat * topRight + (1 - xfloat) * topLeft
    botMid = xfloat * bottomRight + (1 - xfloat) * bottomLeft

    mid = yfloat * botMid + (1 - yfloat) * topMid

    return mid


class Img2PlotVectorizer(BaseVectorizer):
    """
    Edge detection based vectorization using Sobel operators.
    Follows edges to create continuous lines, suitable for pen plotting.
    """
    
    @property
    def name(self) -> str:
        return "Img2Plot Edge Detection"
    
    @property
    def description(self) -> str:
        return "Edge detection vectorization using Sobel operators to follow edges and create continuous lines"
    
    @property
    def algorithm_id(self) -> str:
        return "img2plot"
    
    def vectorize_image(
        self,
        image_data: bytes,
        settings: Optional[Dict[str, Any]] = None,
        output_dir: Optional[str] = None,
        base_filename: Optional[str] = None,
    ) -> VectorizationResult:
        """Vectorize using img2plot edge detection algorithm"""
        start_time = datetime.now()
        
        # Get settings with defaults
        termination_ratio = settings.get("termination_ratio", 1.0/3.5) if settings else 1.0/3.5
        line_continue_thresh = settings.get("line_continue_thresh", 0.01) if settings else 0.01
        min_line_length = settings.get("min_line_length", 21) if settings else 21
        max_curve_angle_deg = settings.get("max_curve_angle_deg", 20.0) if settings else 20.0
        lpf_atk = settings.get("lpf_atk", 0.05) if settings else 0.05
        use_clahe = settings.get("use_clahe", True) if settings else True
        clahe_kernel_size = settings.get("clahe_kernel_size", 32) if settings else 32
        use_gaussian_blur = settings.get("use_gaussian_blur", True) if settings else True
        gaussian_kernel_size = settings.get("gaussian_kernel_size", 1) if settings else 1
        
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            original_size = image.size
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert to numpy array
            base_image = np.array(image)
            base_image_gray = rgb2gray(base_image)
            
            # Normalize 0..1
            norm_img_gray = base_image_gray - base_image_gray.min()
            if norm_img_gray.max() > 0:
                norm_img_gray = norm_img_gray / norm_img_gray.max()
            
            # CLAHE (brings out details)
            if use_clahe:
                norm_img_gray = skimage.exposure.equalize_adapthist(
                    norm_img_gray, 
                    kernel_size=clahe_kernel_size
                )
            
            # Gaussian blur (gets rid of details)
            if use_gaussian_blur:
                norm_img_gray = ndimage.gaussian_filter(norm_img_gray, gaussian_kernel_size)
            
            # Calculate Sobel gradients
            sobel_dx = ndimage.sobel(norm_img_gray, 0)  # horizontal
            sobel_dy = ndimage.sobel(norm_img_gray, 1)  # vertical
            mag = np.hypot(sobel_dx, sobel_dy)
            
            # Where the image is locally darker in low frequencies, increase probability of drawing a line
            img_blur = ndimage.gaussian_filter(norm_img_gray, 2)
            mag = np.multiply(mag, img_blur.max() - img_blur)
            
            # Turn mag into a proper probability distribution function
            mag_sum = np.sum(mag)
            if mag_sum > 0:
                mag = mag / mag_sum
            
            # Calculate gradients for line following
            mag_grad_y, mag_grad_x = np.gradient(norm_img_gray)
            
            # Initialize line tracking
            line_img = np.zeros(mag.shape)
            line_img = line_img - 1
            
            # Process edges
            paths = []
            init_max_p = mag.max()
            cmax = init_max_p
            i = 0
            
            while cmax > init_max_p * termination_ratio:
                i = i + 1
                if i % 250 == 0:
                    logger.debug(f"Max P: {mag.max()}, term at: {init_max_p * termination_ratio}")
                
                pix_idx = mag.argmax()
                p_idx_row = int(pix_idx / mag.shape[1])
                p_idx_col = pix_idx % mag.shape[1]
                
                cmax = mag[p_idx_row, p_idx_col]
                
                # Get line from gradient
                line_result = self._get_line_from_gradient(
                    mag, 
                    (p_idx_col, p_idx_row), 
                    (mag_grad_x, mag_grad_y),
                    line_continue_thresh,
                    max_curve_angle_deg,
                    lpf_atk
                )
                
                if line_result is None:
                    # Line too short, replace peak with mean of neighbors
                    acc = 0.0
                    cnt = 0
                    if p_idx_row + 1 < mag.shape[0]:
                        acc = acc + mag[p_idx_row + 1, p_idx_col]
                        cnt = cnt + 1
                    if p_idx_col + 1 < mag.shape[1]:
                        acc = acc + mag[p_idx_row, p_idx_col + 1]
                        cnt = cnt + 1
                    if p_idx_row - 1 >= 0:
                        acc = acc + mag[p_idx_row - 1, p_idx_col]
                        cnt = cnt + 1
                    if p_idx_col - 1 >= 0:
                        acc = acc + mag[p_idx_row, p_idx_col - 1]
                        cnt = cnt + 1
                    
                    if cnt > 0:
                        mag[p_idx_row, p_idx_col] = acc / cnt
                    continue
                
                lstartx, lstarty, lendx, lendy, total_length = line_result
                
                if total_length < min_line_length:
                    # Line too short, replace peak
                    acc = 0.0
                    cnt = 0
                    if p_idx_row + 1 < mag.shape[0]:
                        acc = acc + mag[p_idx_row + 1, p_idx_col]
                        cnt = cnt + 1
                    if p_idx_col + 1 < mag.shape[1]:
                        acc = acc + mag[p_idx_row, p_idx_col + 1]
                        cnt = cnt + 1
                    if p_idx_row - 1 >= 0:
                        acc = acc + mag[p_idx_row - 1, p_idx_col]
                        cnt = cnt + 1
                    if p_idx_col - 1 >= 0:
                        acc = acc + mag[p_idx_row, p_idx_col - 1]
                        cnt = cnt + 1
                    
                    if cnt > 0:
                        mag[p_idx_row, p_idx_col] = acc / cnt
                    continue
                
                # Create path from line
                points = [
                    (float(lstartx), float(lstarty)),
                    (float(lendx), float(lendy))
                ]
                
                # Calculate bounding box
                x_coords = [p[0] for p in points]
                y_coords = [p[1] for p in points]
                bbox = (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
                
                # Calculate area (approximate as line length * 1 pixel width)
                area = total_length
                
                path = VectorPath(
                    points=points,
                    color=(0, 0, 0),  # Black lines
                    is_closed=False,  # Lines are not closed
                    area=area,
                    bounding_box=bbox
                )
                paths.append(path)
                
                # Remove line from magnitude image
                rr, cc, val = skimage.draw.line_aa(lstarty, lstartx, lendy, lendx)
                rrd, ccd = skimage.draw.line(lstarty, lstartx, lendy, lendx)
                
                # Clamp coordinates
                rr = np.clip(rr, 0, mag.shape[0] - 1)
                cc = np.clip(cc, 0, mag.shape[1] - 1)
                rrd = np.clip(rrd, 0, mag.shape[0] - 1)
                ccd = np.clip(ccd, 0, mag.shape[1] - 1)
                
                # Remove drawn line from magnitude
                mag[rr, cc] = 0
                mag[p_idx_row, p_idx_col] = 0
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Create result
            result = VectorizationResult(
                paths=paths,
                original_size=original_size,
                processed_size=original_size,
                colors_detected=1,  # Grayscale processing
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
            logger.error(f"Img2Plot vectorization error: {e}")
            raise
    
    def _get_line_from_gradient(
        self,
        img: np.ndarray,
        px_py: Tuple[int, int],
        grad: Tuple[np.ndarray, np.ndarray],
        line_continue_thresh: float,
        max_curve_angle_deg: float,
        lpf_atk: float
    ) -> Optional[Tuple[int, int, int, int, int]]:
        """Get line from gradient direction"""
        px, py = px_py
        gradx, grady = grad
        
        angle = math.atan2(grady[py, px], gradx[py, px])
        
        # Attempt to grow the line as much as possible
        len_left = 0
        len_right = 0
        
        startx = float(px)
        starty = float(py)
        endx = float(px)
        endy = float(py)
        
        mangle = angle
        peak_intensity = img[py, px]
        
        # Grow the "start" side
        while (0 < starty < img.shape[0] - 1 and 0 < startx < img.shape[1] - 1 and
               bilinear_interpolate(img, startx, starty) > line_continue_thresh * peak_intensity):
            
            len_left += 1
            
            # Recalculate angle
            cangle = math.atan2(
                grady[int(round(starty)), int(round(startx))],
                gradx[int(round(starty)), int(round(startx))]
            )
            
            # Low pass filtered angle update
            mangle = mangle * (1 - lpf_atk) + cangle * lpf_atk
            
            if abs(angle - mangle) > max_curve_angle_deg * (2 * math.pi / 360):
                break
            
            startx = px + len_left * math.sin(mangle)
            starty = py - len_left * math.cos(mangle)
        
        mangle = angle
        
        # Grow the "end" side
        while (0 < endy < img.shape[0] - 1 and 0 < endx < img.shape[1] - 1 and
               bilinear_interpolate(img, endx, endy) > line_continue_thresh * peak_intensity):
            
            len_right += 1
            
            # Recalculate angle
            cangle = math.atan2(
                grady[int(round(endy)), int(round(endx))],
                gradx[int(round(endy)), int(round(endx))]
            )
            
            # Low pass filtered angle update
            mangle = mangle * (1 - lpf_atk) + cangle * lpf_atk
            
            if abs(angle - mangle) > max_curve_angle_deg * (2 * math.pi / 360):
                break
            
            endx = px - len_right * math.sin(mangle)
            endy = py + len_right * math.cos(mangle)
        
        total_length = len_left + len_right + 1
        
        return (int(round(startx)), int(round(starty)), int(round(endx)), int(round(endy)), total_length)
    
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
            
            # Add paths as lines
            for i, path in enumerate(result.paths):
                if len(path.points) < 2:
                    continue
                
                # For img2plot, paths are typically 2-point lines
                x1, y1 = path.points[0]
                x2, y2 = path.points[1] if len(path.points) > 1 else path.points[0]
                
                color_hex = "#{:02x}{:02x}{:02x}".format(*path.color)
                svg_lines.append(
                    f'  <line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                    f'class="path" stroke="{color_hex}" id="line_{i}"/>'
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
        
        # Drawing commands - img2plot creates lines (2 points each)
        for path in result.paths:
            if len(path.points) < 2:
                continue
            
            # Move to first point
            x, y = path.points[0]
            commands.append("C09,{:.2f},{:.2f}".format(x, y))
            commands.append("C13")  # Pen down
            
            # Draw to second point (img2plot lines are typically 2 points)
            if len(path.points) > 1:
                x, y = path.points[1]
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
                    # Draw line from first to second point
                    draw.line([path.points[0], path.points[1]], fill=color, width=1)
            
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
            "termination_ratio": 1.0 / 3.5,
            "line_continue_thresh": 0.01,
            "min_line_length": 21,
            "max_curve_angle_deg": 20.0,
            "lpf_atk": 0.05,
            "use_clahe": True,
            "clahe_kernel_size": 32,
            "use_gaussian_blur": True,
            "gaussian_kernel_size": 1
        }
    
    def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize settings"""
        validated = self.get_default_settings()
        validated.update(settings)
        
        # Validate ranges
        validated["termination_ratio"] = max(0.01, min(1.0, float(validated.get("termination_ratio", 1.0/3.5))))
        validated["line_continue_thresh"] = max(0.0, min(1.0, float(validated.get("line_continue_thresh", 0.01))))
        validated["min_line_length"] = max(1, int(validated.get("min_line_length", 21)))
        validated["max_curve_angle_deg"] = max(0.0, min(180.0, float(validated.get("max_curve_angle_deg", 20.0))))
        validated["lpf_atk"] = max(0.0, min(1.0, float(validated.get("lpf_atk", 0.05))))
        validated["use_clahe"] = bool(validated.get("use_clahe", True))
        validated["clahe_kernel_size"] = max(1, int(validated.get("clahe_kernel_size", 32)))
        validated["use_gaussian_blur"] = bool(validated.get("use_gaussian_blur", True))
        validated["gaussian_kernel_size"] = max(0.0, min(10.0, float(validated.get("gaussian_kernel_size", 1))))
        
        return validated
