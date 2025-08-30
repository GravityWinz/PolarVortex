import cv2
import numpy as np
from PIL import Image, ImageEnhance
import io
import base64
import os
import re
import json
import logging
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class ImageHelper:
    """Helper class for image processing and file management"""
    
    def __init__(self, base_storage_path: str = "local_storage"):
        self.base_storage_path = base_storage_path
        self.images_dir = os.path.join(base_storage_path, "images")
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for use as directory name"""
        # Remove file extension and replace invalid characters
        name_without_ext = os.path.splitext(filename)[0]
        # Replace invalid characters with underscore
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', name_without_ext)
        # Remove leading/trailing spaces and dots
        sanitized = sanitized.strip(' .')
        # Ensure it's not empty
        if not sanitized:
            sanitized = "unnamed_image"
        return sanitized
    
    def create_image_directory(self, image_name: str) -> str:
        """Create directory structure for uploaded image"""
        # Sanitize the image name for directory creation
        sanitized_name = self.sanitize_filename(image_name)
        
        # Create the directory path
        image_dir = os.path.join(self.images_dir, sanitized_name)
        os.makedirs(image_dir, exist_ok=True)
        
        return image_dir
    
    def save_original_image(self, image_data: bytes, image_name: str, image_dir: str) -> str:
        """Save original image to the image directory"""
        original_path = os.path.join(image_dir, image_name)
        with open(original_path, "wb") as f:
            f.write(image_data)
        return original_path
    
    def create_thumbnail(self, image_data: bytes, image_dir: str, image_name: str) -> Optional[str]:
        """Create and save thumbnail of the image"""
        try:
            # Open image from bytes
            image = Image.open(io.BytesIO(image_data))
            
            # Create thumbnail (max 200x200, maintaining aspect ratio)
            image.thumbnail((200, 200), Image.Resampling.LANCZOS)
            
            # Generate thumbnail filename
            name_without_ext = os.path.splitext(image_name)[0]
            thumb_filename = f"thumb_{name_without_ext}.png"
            thumb_path = os.path.join(image_dir, thumb_filename)
            
            # Save thumbnail
            image.save(thumb_path, "PNG")
            
            return thumb_path
        except Exception as e:
            logger.error(f"Thumbnail creation error: {e}")
            return None
    
    def validate_upload(self, file_content_type: str, file_size: int) -> None:
        """Validate uploaded file"""
        if not file_content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        if file_size > self.max_file_size:
            raise HTTPException(status_code=400, detail=f"File too large (max {self.max_file_size // (1024*1024)}MB)")
    
    def parse_processing_settings(self, settings_json: str) -> Dict[str, Any]:
        """Parse processing settings from JSON string"""
        try:
            return json.loads(settings_json) if settings_json else {}
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in processing settings, using defaults")
            return {}
    
    def process_image_for_plotting(self, image_data: bytes, settings: Dict[str, Any], 
                                 image_dir: Optional[str] = None, 
                                 image_name: Optional[str] = None) -> Dict[str, Any]:
        """Process uploaded image for polargraph plotting"""
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            # Resize based on settings
            resolution_map = {
                "low": (400, 300),
                "medium": (800, 600),
                "high": (1200, 900),
                "custom": (settings.get("maxWidth", 800), settings.get("maxHeight", 600))
            }
            
            target_size = resolution_map.get(settings.get("resolution", "medium"))
            image = image.resize(target_size, Image.Resampling.LANCZOS)
            
            # Convert to numpy array for OpenCV processing
            img_array = np.array(image)
            
            # Apply threshold
            threshold = settings.get("threshold", 128)
            _, binary = cv2.threshold(img_array, threshold, 255, cv2.THRESH_BINARY)
            
            # Invert if requested
            if settings.get("invert", False):
                binary = cv2.bitwise_not(binary)
            
            # Apply dithering if requested
            if settings.get("dither", True):
                binary = self._apply_floyd_steinberg_dithering(img_array)
            
            # Convert back to PIL Image
            processed_image = Image.fromarray(binary)
            
            # Save processed image directly to the image directory if provided
            output_path = None
            if image_dir and image_name:
                name_without_ext = os.path.splitext(image_name)[0]
                processed_filename = f"processed_{name_without_ext}.png"
                output_path = os.path.join(image_dir, processed_filename)
                
                try:
                    processed_image.save(output_path)
                    logger.info(f"Successfully saved processed image to {output_path}")
                except Exception as e:
                    logger.error(f"Failed to save processed image to {output_path}: {e}")
                    # Fallback to temporary location
                    output_path = f"temp_processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    processed_image.save(output_path)
            else:
                # Fallback to temporary location if no directory provided
                output_path = f"temp_processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                processed_image.save(output_path)
            
            # Convert to base64 for preview
            buffer = io.BytesIO()
            processed_image.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return {
                "success": True,
                "original_size": image.size,
                "processed_size": processed_image.size,
                "output_path": output_path,
                "preview": f"data:image/png;base64,{img_base64}",
                "plotting_data": self._convert_to_plotting_data(binary)
            }
            
        except Exception as e:
            logger.error(f"Image processing error: {e}")
            return {"success": False, "error": str(e)}
    
    def _apply_floyd_steinberg_dithering(self, image: np.ndarray) -> np.ndarray:
        """Apply Floyd-Steinberg dithering to image"""
        img = image.astype(float)
        height, width = img.shape
        
        for y in range(height):
            for x in range(width):
                old_pixel = img[y, x]
                new_pixel = 255 if old_pixel > 127 else 0
                img[y, x] = new_pixel
                
                error = old_pixel - new_pixel
                
                if x + 1 < width:
                    img[y, x + 1] += error * 7 / 16
                if x - 1 >= 0 and y + 1 < height:
                    img[y + 1, x - 1] += error * 3 / 16
                if y + 1 < height:
                    img[y + 1, x] += error * 5 / 16
                if x + 1 < width and y + 1 < height:
                    img[y + 1, x + 1] += error * 1 / 16
        
        return img.astype(np.uint8)
    
    def _convert_to_plotting_data(self, binary_image: np.ndarray) -> List[Tuple[float, float]]:
        """Convert binary image to plotting coordinates"""
        height, width = binary_image.shape
        plotting_points = []
        
        for y in range(height):
            for x in range(width):
                if binary_image[y, x] == 0:  # Black pixel
                    # Convert to plotter coordinates
                    plot_x = (x / width) * 100  # Scale to 0-100
                    plot_y = (y / height) * 100
                    plotting_points.append((plot_x, plot_y))
        
        return plotting_points
    
    def list_processed_images(self) -> Dict[str, Any]:
        """List all uploaded images with their directory structure"""
        try:
            if not os.path.exists(self.images_dir):
                return {"images": []}
            
            images = []
            for image_dir_name in os.listdir(self.images_dir):
                image_dir_path = os.path.join(self.images_dir, image_dir_name)
                if os.path.isdir(image_dir_path):
                    # Get original image file
                    original_files = [f for f in os.listdir(image_dir_path) 
                                    if not f.startswith('thumb_') and not f.startswith('processed_')]
                    
                    if original_files:
                        original_file = original_files[0]  # Take the first non-thumbnail file
                        original_path = os.path.join(image_dir_path, original_file)
                        file_stat = os.stat(original_path)
                        
                        # Check for thumbnail and processed versions
                        thumb_file = f"thumb_{os.path.splitext(original_file)[0]}.png"
                        processed_file = f"processed_{os.path.splitext(original_file)[0]}.png"
                        
                        thumb_path = os.path.join(image_dir_path, thumb_file)
                        processed_path = os.path.join(image_dir_path, processed_file)
                        
                        images.append({
                            "name": image_dir_name,
                            "original_filename": original_file,
                            "original_path": original_path,
                            "thumbnail_path": thumb_path if os.path.exists(thumb_path) else None,
                            "processed_path": processed_path if os.path.exists(processed_path) else None,
                            "size": file_stat.st_size,
                            "created": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                            "has_thumbnail": os.path.exists(thumb_path),
                            "has_processed": os.path.exists(processed_path)
                        })
            
            return {"images": images}
        except Exception as e:
            logger.error(f"List images error: {e}")
            return {"error": str(e)}
    
    def process_upload(self, file_content: bytes, file_content_type: str, file_size: int, 
                      file_name: str, settings_json: str, directory_name: str = "") -> Dict[str, Any]:
        """Complete upload processing workflow"""
        try:
            # Validate file
            self.validate_upload(file_content_type, file_size)
            
            # Parse settings
            processing_settings = self.parse_processing_settings(settings_json)
            
            # Create image directory
            dir_name = directory_name.strip() if directory_name.strip() else file_name
            image_dir = self.create_image_directory(dir_name)
            
            # Save original image
            original_path = self.save_original_image(file_content, file_name, image_dir)
            
            # Create thumbnail
            thumb_path = self.create_thumbnail(file_content, image_dir, file_name)
            
            # Process image
            result = self.process_image_for_plotting(file_content, processing_settings, image_dir, file_name)
            
            # Get the processed image path from the result
            processed_path = result.get("output_path") if result["success"] else None
            
            if result["success"]:
                return {
                    "success": True,
                    "filename": file_name,
                    "original_size": result["original_size"],
                    "processed_size": result["processed_size"],
                    "plotting_points": len(result["plotting_data"]),
                    "preview": result["preview"],
                    "original_path": original_path,
                    "thumbnail_path": thumb_path,
                    "processed_path": processed_path,
                    "image_directory": image_dir
                }
            else:
                raise HTTPException(status_code=500, detail=result["error"])
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Upload processing error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

