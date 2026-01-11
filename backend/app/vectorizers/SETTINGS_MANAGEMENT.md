# Settings Management in Plugin Vectorizers

This document explains how settings are managed throughout the vectorization plugin system.

## Overview

Settings flow through the system in this order:
1. **UI** → User selects algorithm and adjusts settings
2. **API** → Settings sent as query parameters or form data
3. **ImageHelper** → Settings merged with defaults and validated
4. **Vectorizer** → Settings used for vectorization

## Settings Flow Diagram

```
┌─────────────┐
│   Frontend  │
│  (UI State) │
└──────┬──────┘
       │ User selects algorithm & settings
       ▼
┌─────────────┐
│  API Service │
│  (apiService)│
└──────┬──────┘
       │ HTTP POST with settings
       ▼
┌─────────────┐
│  FastAPI     │
│  Endpoint    │
└──────┬──────┘
       │ Create settings dict
       ▼
┌─────────────┐
│ ImageHelper  │
│ vectorize() │
└──────┬──────┘
       │ Get vectorizer + merge defaults + validate
       ▼
┌─────────────┐
│  Vectorizer │
│ vectorize() │
└─────────────┘
```

## 1. Base Interface Methods

Every vectorizer must implement two methods for settings management:

### `get_default_settings() -> Dict[str, Any]`

Returns a dictionary of default settings for the algorithm.

**Example from `simple_threshold.py`:**
```python
def get_default_settings(self) -> Dict[str, Any]:
    return {
        "threshold_value": 127,
        "invert": False,
        "min_area": 10,
        "blur_size": 3
    }
```

### `validate_settings(settings: Dict[str, Any]) -> Dict[str, Any]`

Validates and normalizes settings. Should:
- Merge provided settings with defaults
- Clamp values to valid ranges
- Convert types if needed
- Return a complete, validated settings dict

**Example from `simple_threshold.py`:**
```python
def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
    validated = self.get_default_settings()
    validated.update(settings)
    
    # Clamp values to valid ranges
    validated["threshold_value"] = max(0, min(255, int(validated.get("threshold_value", 127))))
    validated["min_area"] = max(1, int(validated.get("min_area", 10)))
    validated["blur_size"] = max(0, min(15, int(validated.get("blur_size", 3))))
    validated["invert"] = bool(validated.get("invert", False))
    
    return validated
```

**Note:** The base class provides a default implementation that just returns the settings as-is, but it's recommended to override it for validation.

## 2. Settings Flow Through the System

### Frontend (VectorizeDialog.jsx)

**Initial State:**
```javascript
const [vectorizationSettings, setVectorizationSettings] = useState({
  blur_radius: 1,
  posterize_levels: 5,
  // ... polargraph defaults
});
```

**When Algorithm Changes:**
```javascript
const loadAlgorithmSettings = async () => {
  const info = await getVectorizerInfo(selectedAlgorithm);
  if (info && info.default_settings) {
    setVectorizationSettings(info.default_settings); // Load algorithm-specific defaults
  }
};
```

**On Vectorize:**
```javascript
const result = await vectorizeProjectImage(
  project.id, 
  vectorizationSettings,  // Current UI state
  selectedAlgorithm
);
```

### API Endpoint (main.py)

**For `/projects/{project_id}/vectorize`:**
```python
@app.post("/projects/{project_id}/vectorize")
async def vectorize_project_image(
    project_id: str,
    algorithm: str = "polargraph",
    blur_radius: int = 1,  # Query parameters
    posterize_levels: int = 5,
    # ... more parameters
):
    # Get vectorizer
    vectorizer = get_vectorizer(algorithm)
    
    # Create settings dict from query parameters
    settings = {
        "blur_radius": blur_radius,
        "posterize_levels": posterize_levels,
        # ...
    }
    
    # Validate settings (merges with defaults, clamps values)
    settings = vectorizer.validate_settings(settings)
    
    # Pass to vectorizer
    result = vectorizer.vectorize_image(image_data, settings, ...)
```

**For `/vectorize` (file upload):**
```python
@app.post("/vectorize")
async def vectorize_image(
    file: UploadFile,
    settings: str = Form(default="{}"),  # JSON string
    algorithm: str = Form(default="polargraph")
):
    # Parse JSON settings
    vectorization_settings = json.loads(settings) if settings else {}
    
    # Pass to ImageHelper (which handles defaults/validation)
    result = temp_helper.vectorize_image(contents, vectorization_settings, algorithm)
```

### ImageHelper (image_processor.py)

**Settings Processing:**
```python
def vectorize_image(
    self, 
    image_data: bytes, 
    vectorization_settings: Optional[Dict[str, Any]] = None,
    algorithm: str = "polargraph"
) -> Dict[str, Any]:
    vectorizer = get_vectorizer(algorithm)
    
    # Step 1: Use defaults if none provided
    if not vectorization_settings:
        vectorization_settings = vectorizer.get_default_settings()
    else:
        # Step 2: Merge with defaults (user settings override defaults)
        defaults = vectorizer.get_default_settings()
        defaults.update(vectorization_settings)  # User settings win
        vectorization_settings = defaults
    
    # Step 3: Validate settings (clamp, normalize, etc.)
    vectorization_settings = vectorizer.validate_settings(vectorization_settings)
    
    # Step 4: Pass to vectorizer
    result = vectorizer.vectorize_image(image_data, vectorization_settings)
```

### Vectorizer Implementation

**Settings Usage:**
```python
def vectorize_image(
    self,
    image_data: bytes,
    settings: Optional[Dict[str, Any]] = None,  # Already validated!
    output_dir: Optional[str] = None,
    base_filename: Optional[str] = None,
) -> VectorizationResult:
    # Settings are already validated, just use them
    threshold_value = settings.get("threshold_value", 127)
    invert = settings.get("invert", False)
    # ...
```

## 3. Key Design Decisions

### Why Merge with Defaults?

- **User convenience**: Users don't need to provide all settings
- **Backward compatibility**: Missing settings get sensible defaults
- **Algorithm flexibility**: Each algorithm can have different settings

### Why Validate Settings?

- **Type safety**: Ensure correct types (int, float, bool)
- **Range checking**: Clamp values to valid ranges
- **Security**: Prevent invalid inputs that could cause errors

### Why Algorithm-Specific Defaults?

- **Different algorithms need different settings**: 
  - Polargraph: `blur_radius`, `posterize_levels`, `color_tolerance`
  - Simple Threshold: `threshold_value`, `invert`, `min_area`
- **Better UX**: UI loads appropriate defaults when algorithm changes

## 4. Example: Adding Settings to a New Vectorizer

```python
class MyVectorizer(BaseVectorizer):
    def get_default_settings(self) -> Dict[str, Any]:
        return {
            "sensitivity": 0.5,
            "edge_threshold": 100,
            "smooth_edges": True,
            "max_paths": 1000
        }
    
    def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        validated = self.get_default_settings()
        validated.update(settings)
        
        # Validate each setting
        validated["sensitivity"] = max(0.0, min(1.0, float(validated.get("sensitivity", 0.5))))
        validated["edge_threshold"] = max(0, min(255, int(validated.get("edge_threshold", 100))))
        validated["smooth_edges"] = bool(validated.get("smooth_edges", True))
        validated["max_paths"] = max(1, int(validated.get("max_paths", 1000)))
        
        return validated
    
    def vectorize_image(self, image_data: bytes, settings: Optional[Dict[str, Any]] = None, ...):
        # Settings are already validated when they reach here
        sensitivity = settings.get("sensitivity", 0.5)
        edge_threshold = settings.get("edge_threshold", 100)
        # ... use settings
```

## 5. Current Limitations & Future Improvements

### Current State:
- ✅ Algorithm-specific defaults
- ✅ Settings validation
- ✅ Automatic merging with defaults
- ⚠️ UI shows all settings (not algorithm-specific)
- ⚠️ API endpoint has hardcoded parameters for polargraph

### Potential Improvements:

1. **Dynamic UI Controls**: Show only relevant settings for selected algorithm
   - Could use a settings schema from `get_vectorizer_info()`
   - Generate UI controls dynamically based on settings types

2. **Settings Schema**: Add metadata about settings
   ```python
   def get_settings_schema(self) -> Dict[str, Any]:
       return {
           "threshold_value": {
               "type": "int",
               "min": 0,
               "max": 255,
               "default": 127,
               "description": "Threshold value for binarization"
           },
           # ...
       }
   ```

3. **Settings Presets**: Allow saving/loading setting presets
   - Common configurations for different image types
   - User-defined presets

## 6. Best Practices

1. **Always provide defaults**: Every setting should have a sensible default
2. **Validate everything**: Don't trust user input, always validate
3. **Clamp to ranges**: Prevent invalid values that could cause errors
4. **Document settings**: Add comments explaining what each setting does
5. **Type conversion**: Convert strings to appropriate types in validation
6. **Backward compatibility**: New settings should have defaults so old code still works
