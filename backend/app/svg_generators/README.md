# SVG Generators

This directory contains the plugin system for SVG generation algorithms. Each algorithm is implemented as a separate module that extends the `BaseSvgGenerator` class.

## Adding a New SVG Generator

To add a new SVG generator:

1. **Create a new file** in this directory (e.g., `my_generator.py`)

2. **Implement the BaseSvgGenerator interface**:

```python
from typing import Dict, Any, Optional
from . import BaseSvgGenerator, SvgGenerationResult

class MySvgGenerator(BaseSvgGenerator):
    """My custom SVG generator"""
    
    @property
    def name(self) -> str:
        return "My SVG Generator"
    
    @property
    def description(self) -> str:
        return "Description of what this generator does"
    
    @property
    def generator_id(self) -> str:
        return "my_generator"  # Unique identifier
    
    def generate_svg(
        self,
        settings: Optional[Dict[str, Any]] = None,
        output_dir: Optional[str] = None,
        base_filename: Optional[str] = None,
    ) -> SvgGenerationResult:
        # Your SVG generation logic here
        # Return a SvgGenerationResult object
        pass
    
    def get_default_settings(self) -> Dict[str, Any]:
        """Return default settings for this generator"""
        return {
            "param1": 10,
            "param2": 5.0,
            # ... your default settings
        }
    
    # Optional: Implement these if your generator supports them
    def get_generation_preview(self, result: SvgGenerationResult) -> str:
        # Preview generation implementation
        pass
    
    def get_parameter_documentation(self) -> Dict[str, Dict[str, Any]]:
        # Parameter documentation implementation
        pass
```

3. **Register the generator** in `__init__.py`:

```python
# In __init__.py, add to _register_builtin_generators():
from .my_generator import MySvgGenerator
register_svg_generator(MySvgGenerator)
```

4. **The generator will automatically appear** in the UI dropdown once registered!

## SvgGenerationResult Structure

The `SvgGenerationResult` dataclass contains:
- `svg_path`: Optional[str] - Path to saved SVG file (if saved)
- `svg_content`: Optional[str] - Raw SVG content as string
- `width`: int - SVG width in pixels
- `height`: int - SVG height in pixels
- `processing_time`: float - Processing time in seconds
- `settings_used`: Any - Settings object used
- `preview`: Optional[str] - Base64 encoded preview image (if generated)

## Key Differences from Vectorizers

1. **No input image**: SVG generators don't take `image_data` parameter - they generate from scratch
2. **Project context**: Always work within a project (no standalone generation endpoint)
3. **Settings-driven**: Generation is purely algorithm + settings based
4. **SVG-first**: Focus on generating SVG content directly (not converting from images)

## Example Implementations

- **`geometric_pattern.py`**: Generates geometric pattern SVGs (grid, mandala, spiral) - demonstrates the full plugin interface
- **`spirograph.py`**: Generates spirograph patterns using hypotrochoid/epitrochoid mathematics based on Wikipedia equations - creates intricate curved patterns

## Parameter Documentation

Override `get_parameter_documentation()` to provide detailed documentation for your generator's parameters. This helps users understand what each setting does and when to adjust it.
