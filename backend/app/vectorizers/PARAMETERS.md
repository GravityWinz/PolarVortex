# Vectorization Parameters Documentation

This document provides comprehensive documentation for all parameters used by the vectorization algorithms in PolarVortex. Each algorithm has its own set of parameters that control how images are converted to vector paths.

---

## Polargraph Algorithm Parameters

The Polargraph algorithm uses contour detection with color separation and noise reduction. It's designed for converting raster images to vector paths suitable for polargraph plotting.

### Image Preprocessing Parameters

#### `blur_radius` (int, default: 1)
- **Purpose**: Controls the amount of Gaussian blur applied to the image before vectorization
- **Range**: 0-10 (typically)
- **Effect**: 
  - **Low values (0-1)**: Minimal smoothing, preserves fine details but may include noise
  - **Medium values (2-3)**: Balanced smoothing, reduces noise while maintaining important features
  - **High values (4+)**: Heavy smoothing, removes fine details and noise but may blur important edges
- **When to adjust**: Increase for noisy images, decrease for images with fine details you want to preserve
- **Implementation**: Applied via `ImageFilter.GaussianBlur(radius=blur_radius)` in the preprocessing stage

#### `posterize_levels` (int, default: 5)
- **Purpose**: Reduces the number of colors in the image by quantizing to a specific number of color levels
- **Range**: 2-256 (typically 2-20 for vectorization)
- **Effect**:
  - **Low values (2-4)**: Creates high-contrast, posterized effect with few colors - good for simple graphics
  - **Medium values (5-8)**: Balanced color reduction, maintains some color detail
  - **High values (9+)**: Preserves more color information, may result in more complex vector paths
- **When to adjust**: Lower for simpler vectorization with fewer colors, higher for preserving color gradients
- **Implementation**: Uses PIL's `quantize()` method to reduce color palette

#### `enable_noise_reduction` (bool, default: True)
- **Purpose**: Master switch to enable/disable noise reduction preprocessing
- **Effect**: When enabled, applies blur based on `blur_radius`. When disabled, skips blur entirely
- **When to adjust**: Disable if you want to preserve all fine details, even if they might be noise

### Color Separation Parameters

#### `enable_color_separation` (bool, default: True)
- **Purpose**: Controls whether the algorithm separates the image into individual color layers
- **Effect**:
  - **Enabled**: Each unique color is processed separately, creating separate vector paths for each color
  - **Disabled**: Image is processed as a single grayscale layer
- **When to adjust**: Disable for grayscale images or when you want a single-color output

#### `color_tolerance` (int, default: 10)
- **Purpose**: Determines how similar colors must be to be grouped together during color separation
- **Range**: 0-255 (typically 5-30)
- **Effect**:
  - **Low values (0-5)**: Very strict color matching - only nearly identical colors are grouped
  - **Medium values (10-15)**: Balanced grouping - similar colors are treated as the same
  - **High values (20+)**: Loose grouping - different shades are treated as the same color
- **When to adjust**: 
  - Increase if you have many similar color shades you want to merge
  - Decrease if you want to preserve subtle color differences
- **Implementation**: Used in `_is_color_similar()` to check if colors are within tolerance: `abs(c - e) <= color_tolerance` for each RGB channel

### Contour Detection Parameters

#### `min_contour_area` (int, default: 10)
- **Purpose**: Minimum area (in pixels²) required for a contour to be included in the vectorization
- **Range**: 1-10000+ (typically 5-100)
- **Effect**:
  - **Low values (1-5)**: Includes very small details and noise
  - **Medium values (10-50)**: Filters out small noise while preserving important details
  - **High values (100+)**: Only includes large features, removes small details
- **When to adjust**: Increase to remove small artifacts and noise, decrease to preserve fine details
- **Implementation**: Contours with `cv2.contourArea(contour) < min_contour_area` are discarded

#### `min_contour_points` (int, default: 3)
- **Purpose**: Minimum number of points required for a contour to be valid
- **Range**: 3-10 (typically)
- **Effect**:
  - **Low values (3)**: Accepts very simple shapes (triangles)
  - **Higher values (5+)**: Requires more complex shapes, filters out degenerate contours
- **When to adjust**: Rarely needs adjustment - 3 is usually appropriate for minimum valid polygon

### Contour Simplification Parameters

#### `enable_contour_simplification` (bool, default: True)
- **Purpose**: Master switch to enable/disable contour simplification
- **Effect**: When enabled, applies Douglas-Peucker algorithm to reduce the number of points in contours
- **When to adjust**: Disable if you want to preserve all original contour points

#### `simplification_threshold` (float, default: 2.0)
- **Purpose**: Maximum distance (in pixels) that a simplified contour point can deviate from the original
- **Range**: 0.1-10.0 (typically 1.0-5.0)
- **Effect**:
  - **Low values (0.5-1.0)**: Minimal simplification, preserves fine curves and details
  - **Medium values (2.0-3.0)**: Balanced simplification, reduces points while maintaining shape
  - **High values (5.0+)**: Aggressive simplification, creates smoother but less detailed paths
- **When to adjust**: 
  - Increase for smoother, simpler paths (fewer points, faster plotting)
  - Decrease to preserve fine curves and details
- **Implementation**: Used as epsilon parameter in `cv2.approxPolyDP()` - the maximum distance from the original curve

#### `simplification_iterations` (int, default: 3)
- **Purpose**: Number of times to apply the Douglas-Peucker simplification algorithm
- **Range**: 1-10 (typically 1-5)
- **Effect**:
  - **Low values (1-2)**: Single or double pass simplification
  - **Medium values (3-4)**: Multiple passes for progressive simplification
  - **High values (5+)**: Many passes, may over-simplify and lose important details
- **When to adjust**: 
  - Increase for more aggressive simplification (fewer points)
  - Decrease if simplification is removing important features
- **Implementation**: The simplification algorithm is applied iteratively, with each pass further reducing points

---

## Img2Plot Algorithm Parameters

The Img2Plot algorithm uses edge detection with Sobel operators to follow edges and create continuous lines. It's optimized for creating line-art style vectorizations.

### Edge Detection Parameters

#### `termination_ratio` (float, default: 1.0/3.5 ≈ 0.286)
- **Purpose**: Determines when to stop processing edges - stops when the maximum edge strength falls below this ratio of the initial maximum
- **Range**: 0.01-1.0 (typically 0.1-0.5)
- **Effect**:
  - **Low values (0.1-0.2)**: Processes more edges, including weaker ones - more complete but slower
  - **Medium values (0.25-0.35)**: Balanced processing of strong and medium edges
  - **High values (0.5+)**: Only processes the strongest edges - faster but may miss details
- **When to adjust**: 
  - Decrease to capture more subtle edges and details
  - Increase to focus only on strong edges and speed up processing
- **Implementation**: Algorithm stops when `current_max_edge < initial_max_edge * termination_ratio`

#### `line_continue_thresh` (float, default: 0.01)
- **Purpose**: Minimum edge strength (as fraction of peak intensity) required to continue following a line
- **Range**: 0.0-1.0 (typically 0.005-0.05)
- **Effect**:
  - **Low values (0.005-0.01)**: Lines continue even through weak edges - longer, more continuous lines
  - **Medium values (0.01-0.02)**: Balanced line following
  - **High values (0.05+)**: Lines stop at weaker edges - shorter, more fragmented lines
- **When to adjust**: 
  - Decrease for longer, more continuous lines
  - Increase if lines are extending into noise or unwanted areas
- **Implementation**: Used in `_get_line_from_gradient()` to determine if line should continue: `edge_strength > line_continue_thresh * peak_intensity`

#### `min_line_length` (int, default: 21)
- **Purpose**: Minimum length (in pixels) for a detected line to be included in the output
- **Range**: 1-100+ (typically 10-50)
- **Effect**:
  - **Low values (5-15)**: Includes very short lines and fragments
  - **Medium values (20-30)**: Filters out short noise while preserving important lines
  - **High values (50+)**: Only includes long lines, removes short segments
- **When to adjust**: Increase to remove short artifacts and noise, decrease to preserve fine details
- **Implementation**: Lines shorter than this are discarded and their edge strength is replaced with neighbor average

#### `max_curve_angle_deg` (float, default: 20.0)
- **Purpose**: Maximum angle change (in degrees) allowed when following a curved line before the line is terminated
- **Range**: 0.0-180.0 (typically 10.0-45.0)
- **Effect**:
  - **Low values (5-15°)**: Lines stop at sharp turns - good for straight lines, may break on curves
  - **Medium values (20-30°)**: Allows moderate curves to be followed continuously
  - **High values (45°+)**: Allows sharp turns and curves - may follow unwanted paths
- **When to adjust**: 
  - Increase for images with curved lines
  - Decrease for images with mostly straight lines or to prevent following unwanted paths
- **Implementation**: Used in `_get_line_from_gradient()` - if angle change exceeds this, line growth stops

#### `lpf_atk` (float, default: 0.05)
- **Purpose**: Low-pass filter attack coefficient for smoothing angle changes when following lines
- **Range**: 0.0-1.0 (typically 0.01-0.2)
- **Effect**:
  - **Low values (0.01-0.05)**: Strong smoothing, gradual angle changes - smoother lines
  - **Medium values (0.05-0.1)**: Balanced smoothing
  - **High values (0.2+)**: Weak smoothing, rapid angle changes - more responsive but potentially jittery
- **When to adjust**: 
  - Decrease for smoother, more stable line following
  - Increase for more responsive angle tracking on sharp curves
- **Implementation**: Used in angle update: `new_angle = old_angle * (1 - lpf_atk) + current_angle * lpf_atk`

### Image Enhancement Parameters

#### `use_clahe` (bool, default: True)
- **Purpose**: Enable/disable Contrast Limited Adaptive Histogram Equalization (CLAHE)
- **Effect**:
  - **Enabled**: Enhances local contrast, brings out details in both dark and bright areas
  - **Disabled**: Uses original grayscale image without enhancement
- **When to adjust**: Disable if CLAHE is creating unwanted artifacts or over-enhancing the image

#### `clahe_kernel_size` (int, default: 32)
- **Purpose**: Size of the local neighborhood used for CLAHE contrast enhancement
- **Range**: 1-128+ (typically 8-64)
- **Effect**:
  - **Small values (8-16)**: Very local enhancement, may create artifacts
  - **Medium values (32-64)**: Balanced local enhancement
  - **Large values (128+)**: More global enhancement, less local detail
- **When to adjust**: 
  - Decrease for more localized contrast enhancement
  - Increase for smoother, more global enhancement
- **Implementation**: Used as `kernel_size` parameter in `skimage.exposure.equalize_adapthist()`

#### `use_gaussian_blur` (bool, default: True)
- **Purpose**: Enable/disable Gaussian blur preprocessing
- **Effect**:
  - **Enabled**: Smooths the image before edge detection, reduces noise
  - **Disabled**: Uses original image without smoothing
- **When to adjust**: Disable if you want to preserve all fine details and edges

#### `gaussian_kernel_size` (float, default: 1.0)
- **Purpose**: Standard deviation of the Gaussian blur kernel
- **Range**: 0.0-10.0 (typically 0.5-3.0)
- **Effect**:
  - **Low values (0.5-1.0)**: Light smoothing, preserves most details
  - **Medium values (1.0-2.0)**: Balanced smoothing
  - **High values (3.0+)**: Heavy smoothing, removes fine details
- **When to adjust**: 
  - Increase for noisy images
  - Decrease to preserve fine details
- **Implementation**: Used as `sigma` parameter in `ndimage.gaussian_filter()`

---

## Simple Threshold Algorithm Parameters

The Simple Threshold algorithm is a basic vectorization method that converts images to grayscale, applies a threshold, and extracts contours. It's useful for simple black-and-white conversions.

### Threshold Parameters

#### `threshold_value` (int, default: 127)
- **Purpose**: Grayscale threshold value for binary conversion (0-255 scale)
- **Range**: 0-255
- **Effect**:
  - **Low values (0-100)**: More pixels become white (foreground), fewer become black
  - **Medium values (100-150)**: Balanced threshold
  - **High values (150-255)**: More pixels become black (background), fewer become white
- **When to adjust**: 
  - Increase if too much is being detected as foreground
  - Decrease if not enough is being detected
- **Implementation**: Used in `cv2.threshold()` - pixels above threshold become white (or black if inverted)

#### `invert` (bool, default: False)
- **Purpose**: Invert the threshold result (swap black and white)
- **Effect**:
  - **False**: Pixels above threshold → white, below → black
  - **True**: Pixels above threshold → black, below → white
- **When to adjust**: Enable for dark images on light backgrounds, or when you want inverted output

### Filtering Parameters

#### `min_area` (int, default: 10)
- **Purpose**: Minimum area (in pixels²) required for a contour to be included
- **Range**: 1-10000+ (typically 5-100)
- **Effect**:
  - **Low values (1-5)**: Includes very small details and noise
  - **Medium values (10-50)**: Filters out small noise while preserving details
  - **High values (100+)**: Only includes large features
- **When to adjust**: Increase to remove small artifacts, decrease to preserve fine details
- **Implementation**: Contours with `cv2.contourArea(contour) < min_area` are discarded

#### `blur_size` (int, default: 3)
- **Purpose**: Size of the Gaussian blur kernel applied before thresholding
- **Range**: 0-15 (must be odd: 1, 3, 5, 7, 9, 11, 13, 15)
- **Effect**:
  - **0**: No blur, preserves all details and noise
  - **Small (1-3)**: Light smoothing, reduces minor noise
  - **Medium (5-7)**: Moderate smoothing
  - **Large (9-15)**: Heavy smoothing, removes fine details
- **When to adjust**: 
  - Increase for noisy images
  - Decrease or set to 0 to preserve fine details
- **Implementation**: Used as kernel size in `cv2.GaussianBlur()` - must be odd number

---

## Parameter Interaction and Best Practices

### General Guidelines

1. **Start with defaults**: Most algorithms have sensible defaults that work well for many images
2. **Adjust incrementally**: Make small changes (10-20%) and test results
3. **Understand the trade-offs**: 
   - More detail preservation = more complex paths = slower plotting
   - More simplification = simpler paths = faster plotting but less detail
4. **Image-specific tuning**: Different image types (photos, line art, logos) may need different settings

### Algorithm Selection Guide

- **Polargraph**: Best for color images, logos, illustrations with distinct color regions
- **Img2Plot**: Best for photos, images with gradients, edge-based artwork
- **Simple Threshold**: Best for simple black-and-white images, scanned documents

### Common Parameter Combinations

**For detailed, high-quality output:**
- Low simplification, low noise reduction, high color tolerance
- More paths, more detail, slower processing

**For fast, simple output:**
- High simplification, high noise reduction, low min_area
- Fewer paths, less detail, faster processing

**For noisy images:**
- Increase blur/noise reduction parameters
- Increase min_area/min_line_length to filter noise
- May need to adjust thresholds

**For images with fine details:**
- Decrease blur/noise reduction
- Decrease min_area/min_line_length
- Lower simplification thresholds

---

## Technical Implementation Notes

### Parameter Validation

All parameters are validated by each algorithm's `validate_settings()` method, which:
- Merges user settings with defaults
- Clamps values to valid ranges
- Converts types as needed
- Returns a validated settings dictionary

### Default Values

Default values are defined in each algorithm's `get_default_settings()` method. These defaults represent tested values that work well for typical images, but may need adjustment for specific use cases.

### Settings Flow

1. User provides settings via API (JSON body or query parameters)
2. Settings are merged with algorithm defaults
3. Settings are validated and clamped to ranges
4. Validated settings are used during vectorization
5. Settings are stored in the result for reference

---

## References

- OpenCV documentation: https://docs.opencv.org/
- PIL/Pillow documentation: https://pillow.readthedocs.io/
- Scikit-image documentation: https://scikit-image.org/
- Douglas-Peucker algorithm: Used for contour simplification
- Sobel operators: Used for edge detection in Img2Plot
