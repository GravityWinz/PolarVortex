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
from pathlib import Path

from .config import config

logger = logging.getLogger(__name__)

class ImageHelper:
    """Helper class for image processing and file management"""
    
    def __init__(self):
        """Initialize ImageHelper with configuration from config system"""
        self.project_storage_path = Path(config.project_storage)
        self.max_file_size = config.max_file_size
        self.allowed_image_types = config.allowed_image_types
        self.resolution_presets = config.resolution_presets
        self.default_threshold = config.default_threshold
        self.default_dither = config.default_dither
        self.default_invert = config.default_invert
        
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
    
    def get_project_directory(self, project_id: str) -> Path:
        """Get the project directory path for a given project ID"""
        return self.project_storage_path / project_id
    
    def save_original_image(self, image_data: bytes, image_name: str, project_id: str) -> str:
        """Save original image to the project directory"""
        project_dir = self.get_project_directory(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        
        original_path = project_dir / image_name
        with open(original_path, "wb") as f:
            f.write(image_data)
        return str(original_path)
    
    def create_thumbnail(self, image_data: bytes, image_name: str, project_id: str) -> Optional[str]:
        """Create and save thumbnail of the image"""
        try:
            # Open image from bytes
            image = Image.open(io.BytesIO(image_data))
            
            # Create thumbnail (max 200x200, maintaining aspect ratio)
            image.thumbnail((200, 200), Image.Resampling.LANCZOS)
            
            # Generate thumbnail filename
            name_without_ext = os.path.splitext(image_name)[0]
            thumb_filename = f"thumb_{name_without_ext}.png"
            
            project_dir = self.get_project_directory(project_id)
            thumb_path = project_dir / thumb_filename
            
            # Save thumbnail
            image.save(thumb_path, "PNG")
            
            return str(thumb_path)
        except Exception as e:
            logger.error(f"Thumbnail creation error: {e}")
            return None
    
    def validate_upload(self, file_content_type: str, file_size: int) -> None:
        """Validate uploaded file using configuration settings"""
        if file_content_type not in self.allowed_image_types:
            raise HTTPException(status_code=400, detail=f"File type not allowed. Allowed types: {self.allowed_image_types}")
        
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
                                 project_id: Optional[str] = None, 
                                 image_name: Optional[str] = None) -> Dict[str, Any]:
        """Process uploaded image for polargraph plotting"""
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            # Resize based on settings using config resolution presets
            resolution = settings.get("resolution", "medium")
            if resolution in self.resolution_presets:
                target_size = tuple(self.resolution_presets[resolution])
            elif resolution == "custom":
                target_size = (settings.get("maxWidth", 800), settings.get("maxHeight", 600))
            else:
                target_size = tuple(self.resolution_presets["medium"])
            
            image = image.resize(target_size, Image.Resampling.LANCZOS)
            
            # Convert to numpy array for OpenCV processing
            img_array = np.array(image)
            
            # Apply threshold using config defaults
            threshold = settings.get("threshold", self.default_threshold)
            _, binary = cv2.threshold(img_array, threshold, 255, cv2.THRESH_BINARY)
            
            # Invert if requested using config defaults
            if settings.get("invert", self.default_invert):
                binary = cv2.bitwise_not(binary)
            
            # Apply dithering if requested using config defaults
            if settings.get("dither", self.default_dither):
                binary = self._apply_floyd_steinberg_dithering(img_array)
            
            # Convert back to PIL Image
            processed_image = Image.fromarray(binary)
            
            # Save processed image to project directory if provided
            output_path = None
            if project_id and image_name:
                name_without_ext = os.path.splitext(image_name)[0]
                processed_filename = f"processed_{name_without_ext}.png"
                
                project_dir = self.get_project_directory(project_id)
                project_dir.mkdir(parents=True, exist_ok=True)
                output_path = project_dir / processed_filename
                
                try:
                    processed_image.save(output_path)
                    logger.info(f"Successfully saved processed image to {output_path}")
                    output_path = str(output_path)
                except Exception as e:
                    logger.error(f"Failed to save processed image to {output_path}: {e}")
                    # Fallback to temporary location
                    output_path = f"temp_processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    processed_image.save(output_path)
            else:
                # Fallback to temporary location if no project provided
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
    
    
    def process_upload(self, file_content: bytes, file_content_type: str, file_size: int, 
                      file_name: str, settings_json: str, project_id: str) -> Dict[str, Any]:
        """Complete upload processing workflow for a specific project"""
        try:
            # Validate file
            self.validate_upload(file_content_type, file_size)
            
            # Parse settings
            processing_settings = self.parse_processing_settings(settings_json)
            
            # Ensure project directory exists
            project_dir = self.get_project_directory(project_id)
            project_dir.mkdir(parents=True, exist_ok=True)
            
            # Save original image
            original_path = self.save_original_image(file_content, file_name, project_id)
            
            # Create thumbnail
            thumb_path = self.create_thumbnail(file_content, file_name, project_id)
            
            # Process image
            result = self.process_image_for_plotting(file_content, processing_settings, project_id, file_name)
            
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
                    "project_id": project_id
                }
            else:
                raise HTTPException(status_code=500, detail=result["error"])
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Upload processing error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def vectorize_image(self, image_data: bytes, vectorization_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Vectorize an image using the polargraph vectorizer"""
        try:
            from .vectorizer import PolargraphVectorizer, VectorizationSettings
            vectorizer = PolargraphVectorizer()
            
            if vectorization_settings:
                settings = VectorizationSettings(
                    blur_radius=vectorization_settings.get("blur_radius", 1),
                    posterize_levels=vectorization_settings.get("posterize_levels", 5),
                    simplification_threshold=vectorization_settings.get("simplification_threshold", 2.0),
                    simplification_iterations=vectorization_settings.get("simplification_iterations", 3),
                    min_contour_points=vectorization_settings.get("min_contour_points", 3),
                    min_contour_area=vectorization_settings.get("min_contour_area", 10),
                    color_tolerance=vectorization_settings.get("color_tolerance", 10),
                    enable_color_separation=vectorization_settings.get("enable_color_separation", True),
                    enable_contour_simplification=vectorization_settings.get("enable_contour_simplification", True),
                    enable_noise_reduction=vectorization_settings.get("enable_noise_reduction", True)
                )
            else:
                settings = VectorizationSettings()
            
            result = vectorizer.vectorize_image(image_data, settings)
            preview = vectorizer.get_vectorization_preview(result)
            
            return {
                "success": True,
                "vectorization_result": {
                    "total_paths": result.total_paths,
                    "colors_detected": result.colors_detected,
                    "original_size": result.original_size,
                    "processed_size": result.processed_size,
                    "processing_time": result.processing_time,
                    "preview": preview
                },
                "settings_used": {
                    "blur_radius": settings.blur_radius,
                    "posterize_levels": settings.posterize_levels,
                    "simplification_threshold": settings.simplification_threshold,
                    "simplification_iterations": settings.simplification_iterations,
                    "min_contour_points": settings.min_contour_points,
                    "min_contour_area": settings.min_contour_area,
                    "color_tolerance": settings.color_tolerance,
                    "enable_color_separation": settings.enable_color_separation,
                    "enable_contour_simplification": settings.enable_contour_simplification,
                    "enable_noise_reduction": settings.enable_noise_reduction
                }
            }
            
        except Exception as e:
            logger.error(f"Vectorization error: {e}")
            return {"success": False, "error": str(e)}

    def quick_vectorize(self, image_data: bytes, blur: int = 1, posterize: int = 5, simplify: float = 2.0) -> Dict[str, Any]:
        """Quick vectorization with minimal settings"""
        try:
            from .vectorizer import quick_vectorize as qv, PolargraphVectorizer
            
            result = qv(image_data, blur, posterize, simplify)
            vectorizer = PolargraphVectorizer()
            preview = vectorizer.get_vectorization_preview(result)
            
            return {
                "success": True,
                "vectorization_result": {
                    "total_paths": result.total_paths,
                    "colors_detected": result.colors_detected,
                    "original_size": result.original_size,
                    "processed_size": result.processed_size,
                    "processing_time": result.processing_time,
                    "preview": preview
                },
                "settings_used": {
                    "blur_radius": blur,
                    "posterize_levels": posterize,
                    "simplification_threshold": simplify
                }
            }
            
        except Exception as e:
            logger.error(f"Quick vectorization error: {e}")
            return {"success": False, "error": str(e)}

    def export_vectorization_to_svg(self, image_data: bytes, output_path: str, 
                                  vectorization_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Vectorize image and export to SVG file"""
        try:
            from .vectorizer import PolargraphVectorizer, VectorizationSettings
            vectorizer = PolargraphVectorizer()
            
            # Vectorize image
            vectorization_result = self.vectorize_image(image_data, vectorization_settings)
            
            if not vectorization_result["success"]:
                return vectorization_result
            
            # Get the vectorization result
            result = vectorizer.vectorize_image(image_data)
            
            # Export to SVG
            svg_success = vectorizer.export_to_svg(result, output_path)
            
            if svg_success:
                return {
                    "success": True,
                    "svg_path": output_path,
                    "vectorization_info": vectorization_result["vectorization_result"]
                }
            else:
                return {"success": False, "error": "Failed to export SVG"}
                
        except Exception as e:
            logger.error(f"SVG export error: {e}")
            return {"success": False, "error": str(e)}

    def export_vectorization_to_commands(self, image_data: bytes, 
                                       machine_settings: Dict[str, Any],
                                       vectorization_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Vectorize image and export to polargraph plotting commands"""
        try:
            from .vectorizer import PolargraphVectorizer
            vectorizer = PolargraphVectorizer()
            
            # Vectorize image
            result = vectorizer.vectorize_image(image_data)
            
            # Export to plotting commands
            commands = vectorizer.export_to_plotting_commands(result, machine_settings)
            
            return {
                "success": True,
                "commands": commands,
                "total_commands": len(commands),
                "vectorization_info": {
                    "total_paths": result.total_paths,
                    "colors_detected": result.colors_detected,
                    "processing_time": result.processing_time
                }
            }
            
        except Exception as e:
            logger.error(f"Command export error: {e}")
            return {"success": False, "error": str(e)}

    def get_project_images(self, project_id: str) -> Dict[str, Any]:
        """Get all images associated with a specific project"""
        try:
            project_dir = self.get_project_directory(project_id)
            
            if not project_dir.exists():
                logger.warning(f"Project directory not found: {project_dir}")
                return {"images": [], "error": "Project not found"}
            
            images = []
            
            # Get all files in the project directory
            for file_path in project_dir.iterdir():
                if file_path.is_file():
                    file_stat = file_path.stat()
                    
                    # Skip project.yaml file
                    if file_path.name == "project.yaml":
                        continue
                    
                    # Determine file type
                    is_original = not file_path.name.startswith('thumb_') and not file_path.name.startswith('processed_')
                    is_thumbnail = file_path.name.startswith('thumb_')
                    is_processed = file_path.name.startswith('processed_')
                    
                    images.append({
                        "filename": file_path.name,
                        "path": str(file_path),
                        "size": file_stat.st_size,
                        "created": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                        "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                        "is_original": is_original,
                        "is_thumbnail": is_thumbnail,
                        "is_processed": is_processed
                    })
            
            # Sort by creation time (newest first)
            images.sort(key=lambda x: x["created"], reverse=True)
            
            logger.info(f"Found {len(images)} files in project {project_id}")
            return {"images": images, "project_id": project_id}
            
        except Exception as e:
            logger.error(f"Error getting project images for {project_id}: {e}")
            return {"images": [], "error": str(e)}
    
    def get_vectorization_settings_presets(self) -> Dict[str, Dict[str, Any]]:
        """Get predefined vectorization settings presets"""
        return {
            "quick": {
                "blur_radius": 1,
                "posterize_levels": 5,
                "simplification_threshold": 2.0,
                "simplification_iterations": 2,
                "min_contour_points": 3,
                "min_contour_area": 5,
                "color_tolerance": 15,
                "enable_color_separation": True,
                "enable_contour_simplification": True,
                "enable_noise_reduction": True
            },
            "detailed": {
                "blur_radius": 0,
                "posterize_levels": 8,
                "simplification_threshold": 1.0,
                "simplification_iterations": 1,
                "min_contour_points": 2,
                "min_contour_area": 2,
                "color_tolerance": 5,
                "enable_color_separation": True,
                "enable_contour_simplification": False,
                "enable_noise_reduction": False
            },
            "smooth": {
                "blur_radius": 3,
                "posterize_levels": 3,
                "simplification_threshold": 5.0,
                "simplification_iterations": 5,
                "min_contour_points": 5,
                "min_contour_area": 20,
                "color_tolerance": 25,
                "enable_color_separation": True,
                "enable_contour_simplification": True,
                "enable_noise_reduction": True
            },
            "monochrome": {
                "blur_radius": 1,
                "posterize_levels": 2,
                "simplification_threshold": 3.0,
                "simplification_iterations": 3,
                "min_contour_points": 3,
                "min_contour_area": 10,
                "color_tolerance": 50,
                "enable_color_separation": False,
                "enable_contour_simplification": True,
                "enable_noise_reduction": True
            }
        }


# Create global instance
image_helper = ImageHelper()

