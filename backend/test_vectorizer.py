#!/usr/bin/env python3
"""
Test script for the PolarVortex vectorization system.
Demonstrates how to use the vectorizer similar to the legacy PolarGraph system.
"""

import os
import sys
from app.image_processor import ImageHelper
from app.vectorizer import PolargraphVectorizer, VectorizationSettings, quick_vectorize

def test_vectorization():
    """Test the vectorization system with sample images"""
    
    # Initialize image helper
    image_helper = ImageHelper()
    
    # Test with existing sample images
    sample_image_dirs = [
        "local_storage/images/dog",
        "local_storage/images/wheaton",
        "local_storage/images/Recipe"
    ]
    
    for image_dir in sample_image_dirs:
        if os.path.exists(image_dir):
            # Find original image file
            original_files = [f for f in os.listdir(image_dir) 
                            if not f.startswith('thumb_') and not f.startswith('processed_')]
            
            if original_files:
                image_path = os.path.join(image_dir, original_files[0])
                print(f"\n=== Testing vectorization with: {image_path} ===")
                
                # Read image data
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                
                # Test quick vectorization
                print("1. Quick vectorization...")
                quick_result = image_helper.quick_vectorize(image_data, blur=2, posterize=4, simplify=3.0)
                
                if quick_result["success"]:
                    vr = quick_result["vectorization_result"]
                    print(f"   ✓ Found {vr['total_paths']} paths in {vr['processing_time']:.2f}s")
                    print(f"   ✓ Detected {vr['colors_detected']} colors")
                    print(f"   ✓ Original size: {vr['original_size']}")
                    print(f"   ✓ Processed size: {vr['processed_size']}")
                else:
                    print(f"   ✗ Error: {quick_result['error']}")
                
                # Test custom settings vectorization
                print("2. Custom settings vectorization...")
                custom_settings = {
                    "blur_radius": 1,
                    "posterize_levels": 6,
                    "simplification_threshold": 1.5,
                    "enable_color_separation": True,
                    "enable_contour_simplification": True,
                    "min_contour_area": 15
                }
                
                custom_result = image_helper.vectorize_image(image_data, custom_settings)
                
                if custom_result["success"]:
                    vr = custom_result["vectorization_result"]
                    print(f"   ✓ Found {vr['total_paths']} paths in {vr['processing_time']:.2f}s")
                    print(f"   ✓ Detected {vr['colors_detected']} colors")
                else:
                    print(f"   ✗ Error: {custom_result['error']}")
                
                # Test SVG export
                print("3. SVG export...")
                svg_output = os.path.join(image_dir, f"vectorized_{original_files[0]}.svg")
                svg_result = image_helper.export_vectorization_to_svg(
                    image_data, svg_output, custom_settings
                )
                
                if svg_result["success"]:
                    print(f"   ✓ SVG exported to: {svg_result['svg_path']}")
                else:
                    print(f"   ✗ SVG export error: {svg_result['error']}")
                
                # Test plotting commands export
                print("4. Plotting commands export...")
                machine_settings = {
                    "width": 1000,
                    "height": 800,
                    "mm_per_rev": 95.0,
                    "steps_per_rev": 200.0
                }
                
                commands_result = image_helper.export_vectorization_to_commands(
                    image_data, machine_settings, custom_settings
                )
                
                if commands_result["success"]:
                    print(f"   ✓ Generated {commands_result['total_commands']} plotting commands")
                    print(f"   ✓ First few commands: {commands_result['commands'][:3]}")
                else:
                    print(f"   ✗ Commands export error: {commands_result['error']}")
                
                break  # Only test with first available image
    
    # Test presets
    print("\n=== Available Vectorization Presets ===")
    presets = image_helper.get_vectorization_settings_presets()
    for preset_name, preset_settings in presets.items():
        print(f"{preset_name.upper()}:")
        print(f"  - Blur: {preset_settings['blur_radius']}")
        print(f"  - Posterize: {preset_settings['posterize_levels']}")
        print(f"  - Simplification: {preset_settings['simplification_threshold']}")
        print(f"  - Color separation: {preset_settings['enable_color_separation']}")

def demo_vectorization_workflow():
    """Demonstrate the complete vectorization workflow"""
    print("\n=== PolarVortex Vectorization System Demo ===")
    print("This system implements similar functionality to the legacy PolarGraph vectorizer")
    print("but uses modern Python libraries (OpenCV, PIL, NumPy) for better performance.")
    print("\nKey Features:")
    print("• Blob detection and contour extraction")
    print("• Color separation for multi-color images")
    print("• Contour simplification using Douglas-Peucker algorithm")
    print("• SVG export for vector graphics")
    print("• Direct polargraph command generation")
    print("• Multiple quality presets (quick, detailed, smooth, monochrome)")
    
    test_vectorization()

if __name__ == "__main__":
    demo_vectorization_workflow()

