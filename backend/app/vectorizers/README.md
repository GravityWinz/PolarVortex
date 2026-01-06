# Vectorization Algorithms

This directory contains the plugin system for vectorization algorithms. Each algorithm is implemented as a separate module that extends the `BaseVectorizer` class.

## Adding a New Vectorization Algorithm

To add a new vectorization algorithm:

1. **Create a new file** in this directory (e.g., `my_algorithm.py`)

2. **Implement the BaseVectorizer interface**:

```python
from typing import Dict, Any, Optional, List
from . import BaseVectorizer, VectorizationResult

class MyVectorizer(BaseVectorizer):
    """My custom vectorization algorithm"""
    
    @property
    def name(self) -> str:
        return "My Vectorizer"
    
    @property
    def description(self) -> str:
        return "Description of what this algorithm does"
    
    @property
    def algorithm_id(self) -> str:
        return "my_algorithm"  # Unique identifier
    
    def vectorize_image(
        self,
        image_data: bytes,
        settings: Optional[Dict[str, Any]] = None,
        output_dir: Optional[str] = None,
        base_filename: Optional[str] = None,
    ) -> VectorizationResult:
        # Your vectorization logic here
        # Return a VectorizationResult object
        pass
    
    def get_default_settings(self) -> Dict[str, Any]:
        """Return default settings for this algorithm"""
        return {
            "param1": 10,
            "param2": 5.0,
            # ... your default settings
        }
    
    # Optional: Implement these if your algorithm supports them
    def export_to_svg(self, result: VectorizationResult, output_path: str) -> bool:
        # SVG export implementation
        pass
    
    def export_to_plotting_commands(
        self, 
        result: VectorizationResult, 
        machine_settings: Dict[str, Any]
    ) -> List[str]:
        # Plotting commands export implementation
        pass
    
    def get_vectorization_preview(self, result: VectorizationResult) -> str:
        # Preview generation implementation
        pass
```

3. **Register the vectorizer** in `__init__.py`:

```python
# In __init__.py, add to _register_builtin_vectorizers():
from .my_algorithm import MyVectorizer
register_vectorizer(MyVectorizer)
```

4. **The algorithm will automatically appear** in the UI dropdown once registered!

## VectorizationResult Structure

The `VectorizationResult` dataclass contains:
- `paths`: List of VectorPath objects (from `vectorizer.py`)
- `original_size`: Tuple[int, int] - Original image dimensions
- `processed_size`: Tuple[int, int] - Processed image dimensions
- `colors_detected`: int - Number of colors detected
- `total_paths`: int - Total number of paths
- `processing_time`: float - Processing time in seconds
- `settings_used`: Any - Settings object used
- `svg_path`: Optional[str] - Path to SVG file if created
- `source_image_name`: Optional[str] - Source image filename

## VectorPath Structure

Each path in `result.paths` should be a `VectorPath` object (from `vectorizer.py`):
- `points`: List[Tuple[float, float]] - Path coordinates
- `color`: Tuple[int, int, int] - RGB color
- `is_closed`: bool - Whether path is closed
- `area`: float - Path area
- `bounding_box`: Tuple[float, float, float, float] - Bounding box

## Example Implementations

- **`polargraph.py`**: Full-featured vectorizer with color separation, contour simplification, and noise reduction
- **`simple_threshold.py`**: Simple threshold-based vectorizer demonstrating the basic pattern - good starting point for new algorithms
