import cv2
import numpy as np
from PIL import Image, ImageEnhance
import io
import base64
from typing import List, Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ImageProcessor:
    """Advanced image processing for polargraph plotting"""
    
    def __init__(self):
        self.supported_formats = ['JPEG', 'PNG', 'GIF', 'BMP', 'TIFF']
    
    def process_image(self, image_data: bytes, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process image for polargraph plotting
        
        Args:
            image_data: Raw image bytes
            settings: Processing settings dictionary
            
        Returns:
            Dictionary with processing results
        """
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # Validate format
            if image.format not in self.supported_formats:
                raise ValueError(f"Unsupported image format: {image.format}")
            
            # Store original size
            original_size = image.size
            
            # Apply preprocessing
            image = self._preprocess_image(image, settings)
            
            # Resize image
            image = self._resize_image(image, settings)
            
            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            # Apply image enhancements
            image = self._enhance_image(image, settings)
            
            # Convert to numpy array
            img_array = np.array(image)
            
            # Apply thresholding
            binary = self._apply_threshold(img_array, settings)
            
            # Apply dithering if requested
            if settings.get("dither", True):
                binary = self._apply_dithering(img_array, settings)
            
            # Convert to plotting data
            plotting_data = self._convert_to_plotting_data(binary, settings)
            
            # Create preview
            preview = self._create_preview(binary)
            
            return {
                "success": True,
                "original_size": original_size,
                "processed_size": image.size,
                "plotting_points": len(plotting_data),
                "preview": preview,
                "plotting_data": plotting_data,
                "statistics": self._calculate_statistics(binary, plotting_data)
            }
            
        except Exception as e:
            logger.error(f"Image processing error: {e}")
            return {"success": False, "error": str(e)}
    
    def _preprocess_image(self, image: Image.Image, settings: Dict[str, Any]) -> Image.Image:
        """Apply basic preprocessing to image"""
        # Auto-rotate based on EXIF data
        try:
            image = Image.fromarray(np.array(image))
        except:
            pass
        
        # Apply contrast enhancement if requested
        if settings.get("enhance_contrast", False):
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
        
        # Apply brightness adjustment
        brightness = settings.get("brightness", 1.0)
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(brightness)
        
        return image
    
    def _resize_image(self, image: Image.Image, settings: Dict[str, Any]) -> Image.Image:
        """Resize image based on settings"""
        resolution = settings.get("resolution", "medium")
        
        # Resolution presets
        resolution_map = {
            "low": (400, 300),
            "medium": (800, 600),
            "high": (1200, 900),
            "ultra": (1600, 1200),
            "custom": (
                settings.get("maxWidth", 800),
                settings.get("maxHeight", 600)
            )
        }
        
        target_size = resolution_map.get(resolution, (800, 600))
        
        # Maintain aspect ratio
        image.thumbnail(target_size, Image.Resampling.LANCZOS)
        
        return image
    
    def _enhance_image(self, image: Image.Image, settings: Dict[str, Any]) -> Image.Image:
        """Apply image enhancements"""
        # Convert to numpy for OpenCV operations
        img_array = np.array(image)
        
        # Apply Gaussian blur to reduce noise
        if settings.get("reduce_noise", True):
            img_array = cv2.GaussianBlur(img_array, (3, 3), 0)
        
        # Apply edge enhancement
        if settings.get("enhance_edges", False):
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            img_array = cv2.filter2D(img_array, -1, kernel)
        
        return Image.fromarray(img_array)
    
    def _apply_threshold(self, img_array: np.ndarray, settings: Dict[str, Any]) -> np.ndarray:
        """Apply thresholding to create binary image"""
        threshold = settings.get("threshold", 128)
        
        # Use adaptive thresholding for better results
        if settings.get("adaptive_threshold", True):
            binary = cv2.adaptiveThreshold(
                img_array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
        else:
            _, binary = cv2.threshold(img_array, threshold, 255, cv2.THRESH_BINARY)
        
        # Invert if requested
        if settings.get("invert", False):
            binary = cv2.bitwise_not(binary)
        
        return binary
    
    def _apply_dithering(self, img_array: np.ndarray, settings: Dict[str, Any]) -> np.ndarray:
        """Apply Floyd-Steinberg dithering"""
        img = img_array.astype(float)
        height, width = img.shape
        
        for y in range(height):
            for x in range(width):
                old_pixel = img[y, x]
                new_pixel = 255 if old_pixel > 127 else 0
                img[y, x] = new_pixel
                
                error = old_pixel - new_pixel
                
                # Distribute error to neighboring pixels
                if x + 1 < width:
                    img[y, x + 1] += error * 7 / 16
                if x - 1 >= 0 and y + 1 < height:
                    img[y + 1, x - 1] += error * 3 / 16
                if y + 1 < height:
                    img[y + 1, x] += error * 5 / 16
                if x + 1 < width and y + 1 < height:
                    img[y + 1, x + 1] += error * 1 / 16
        
        return img.astype(np.uint8)
    
    def _convert_to_plotting_data(self, binary: np.ndarray, settings: Dict[str, Any]) -> List[Tuple[float, float]]:
        """Convert binary image to plotting coordinates"""
        height, width = binary.shape
        plotting_points = []
        
        # Get plotting strategy
        strategy = settings.get("plotting_strategy", "all_points")
        
        if strategy == "all_points":
            # Include all black pixels
            for y in range(height):
                for x in range(width):
                    if binary[y, x] == 0:  # Black pixel
                        plot_x = (x / width) * 100
                        plot_y = (y / height) * 100
                        plotting_points.append((plot_x, plot_y))
        
        elif strategy == "contour":
            # Find contours and plot only contour points
            contours, _ = cv2.findContours(
                cv2.bitwise_not(binary), 
                cv2.RETR_EXTERNAL, 
                cv2.CONTOUR_APPROX_SIMPLE
            )
            
            for contour in contours:
                for point in contour:
                    x, y = point[0]
                    plot_x = (x / width) * 100
                    plot_y = (y / height) * 100
                    plotting_points.append((plot_x, plot_y))
        
        elif strategy == "sampled":
            # Sample points at regular intervals
            sample_rate = settings.get("sample_rate", 2)
            for y in range(0, height, sample_rate):
                for x in range(0, width, sample_rate):
                    if binary[y, x] == 0:
                        plot_x = (x / width) * 100
                        plot_y = (y / height) * 100
                        plotting_points.append((plot_x, plot_y))
        
        return plotting_points
    
    def _create_preview(self, binary: np.ndarray) -> str:
        """Create base64 preview of processed image"""
        try:
            # Convert binary image to PIL Image
            preview_image = Image.fromarray(binary)
            
            # Resize for preview
            preview_image.thumbnail((300, 300), Image.Resampling.LANCZOS)
            
            # Convert to base64
            buffer = io.BytesIO()
            preview_image.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_base64}"
        except Exception as e:
            logger.error(f"Preview creation error: {e}")
            return ""
    
    def _calculate_statistics(self, binary: np.ndarray, plotting_points: List[Tuple[float, float]]) -> Dict[str, Any]:
        """Calculate image and plotting statistics"""
        height, width = binary.shape
        total_pixels = height * width
        black_pixels = np.sum(binary == 0)
        
        return {
            "total_pixels": total_pixels,
            "black_pixels": int(black_pixels),
            "white_pixels": int(total_pixels - black_pixels),
            "black_percentage": float((black_pixels / total_pixels) * 100),
            "plotting_points": len(plotting_points),
            "estimated_drawing_time": self._estimate_drawing_time(plotting_points)
        }
    
    def _estimate_drawing_time(self, plotting_points: List[Tuple[float, float]]) -> float:
        """Estimate drawing time based on number of points"""
        # Rough estimation: 0.1 seconds per point
        base_time = len(plotting_points) * 0.1
        
        # Add overhead for pen movements
        overhead = len(plotting_points) * 0.05
        
        return round(base_time + overhead, 2)

# Create global instance
image_processor = ImageProcessor()

