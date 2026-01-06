# Algorithm-Specific Settings

## The Problem

Different vectorization algorithms need different settings. For example:
- **Polargraph**: `blur_radius`, `posterize_levels`, `color_tolerance`
- **Simple Threshold**: `threshold_value`, `invert`, `min_area`
- **Your Custom Algorithm**: `booger`, `wibble`, `enable_frobnication` (completely different!)

## The Solution

The system now supports **algorithm-specific settings** through JSON body requests.

### How It Works

1. **Frontend sends settings as JSON body**:
   ```javascript
   {
     settings: {
       booger: 42,
       wibble: 3.14,
       enable_frobnication: true
     }
   }
   ```

2. **Backend accepts flexible settings**:
   ```python
   @app.post("/projects/{project_id}/vectorize")
   async def vectorize_project_image(
       project_id: str,
       algorithm: str = "polargraph",
       settings: Dict[str, Any] = Body(default={}),  # Any settings!
       # Legacy query params still work for backward compatibility
   ):
   ```

3. **Vectorizer validates its own settings**:
   ```python
   def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
       # Only validate settings that this algorithm uses
       validated = self.get_default_settings()
       validated.update(settings)
       validated["booger"] = max(0, min(255, int(validated.get("booger", 42))))
       return validated
   ```

## Example: Vectorizer with "booger" Setting

See `example_booger.py` for a complete example that uses:
- `booger` (int, 0-255)
- `wibble` (float, 0.1-10.0)
- `enable_frobnication` (bool)

These settings are **completely different** from other vectorizers and work perfectly!

## Backward Compatibility

The API still accepts query parameters for backward compatibility:
- Old code using query params: ✅ Still works
- New code using JSON body: ✅ Works with any settings
- Mix of both: ✅ Query params override JSON body

## Adding Your Own Settings

1. **Define defaults in your vectorizer**:
   ```python
   def get_default_settings(self) -> Dict[str, Any]:
       return {
           "my_custom_setting": 100,
           "another_setting": "value"
       }
   ```

2. **Validate in `validate_settings()`**:
   ```python
   def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
       validated = self.get_default_settings()
       validated.update(settings)
       # Validate and clamp your custom settings
       validated["my_custom_setting"] = max(0, min(255, int(validated.get("my_custom_setting", 100))))
       return validated
   ```

3. **Use in `vectorize_image()`**:
   ```python
   def vectorize_image(self, image_data: bytes, settings: Optional[Dict[str, Any]] = None, ...):
       my_setting = settings.get("my_custom_setting", 100)
       # Use my_setting in your algorithm
   ```

4. **Frontend automatically sends all settings**:
   - The UI state contains all settings
   - They're sent as JSON body
   - Your vectorizer receives them and validates

## Current Limitations

- **UI shows all settings**: The UI currently shows controls for polargraph settings even when other algorithms are selected
- **Future improvement**: Dynamic UI that only shows relevant settings for the selected algorithm

## Testing

To test with the example booger vectorizer:

1. Uncomment the registration in `__init__.py`
2. Restart the backend
3. Select "Example Booger Vectorizer" in the UI
4. The settings will load with `booger: 42`, `wibble: 3.14`, etc.
5. Adjust and vectorize - it works!
