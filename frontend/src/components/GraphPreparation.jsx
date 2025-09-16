import {
    Image as ImageIcon,
    PlayArrow as PlayIcon,
    Save as SaveIcon,
    Settings as SettingsIcon,
} from "@mui/icons-material";
import {
    Alert,
    Box,
    Button,
    Divider,
    FormControl,
    FormControlLabel,
    Grid,
    InputLabel,
    MenuItem,
    Paper,
    Select,
    Slider,
    Switch,
    Typography
} from "@mui/material";
import React, { useEffect, useState } from "react";
import logoImage from "../assets/PolarVortexLogo_small.png";

/**
 * GraphPreparation component for preparing images for plotting
 * Allows users to configure plotting parameters and preview settings
 */
export default function GraphPreparation({ selectedImage: propSelectedImage }) {
  const [selectedImage, setSelectedImage] = useState(propSelectedImage);
  
  useEffect(() => {
    setSelectedImage(propSelectedImage);
  }, [propSelectedImage]);
  
  const [settings, setSettings] = useState({
    lineThickness: 1,
    contrast: 50,
    brightness: 50,
    threshold: 128,
    smoothing: true,
    resolution: "medium",
  });

  const handleSettingChange = (setting, value) => {
    setSettings(prev => ({
      ...prev,
      [setting]: value
    }));
  };

  const handleProcess = () => {
    // TODO: Implement image processing with current settings
    console.log("Processing image with settings:", settings);
  };

  const handleSave = () => {
    // TODO: Implement save settings
    console.log("Saving settings:", settings);
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header with Logo */}
      <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
        <img 
          src={logoImage} 
          alt="PolarVortex Logo" 
          style={{ height: "40px", width: "auto", marginRight: "16px" }} 
        />
        <Box>
          <Typography variant="h4" gutterBottom sx={{ mb: 0 }}>
            Graph Preparation
          </Typography>
          <Typography variant="body1" color="text.secondary" paragraph sx={{ mb: 0 }}>
            Configure plotting parameters and prepare your images for optimal drawing results.
          </Typography>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* Image Selection */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: "fit-content" }}>
            <Typography variant="h6" gutterBottom>
              <ImageIcon sx={{ mr: 1, verticalAlign: "middle" }} />
              Image Selection
            </Typography>
            
            {selectedImage ? (
              <Box>
                <img 
                  src={selectedImage.thumbnail} 
                  alt={selectedImage.name}
                  style={{ width: "100%", height: "auto", borderRadius: "8px" }}
                />
                <Typography variant="subtitle2" sx={{ mt: 1 }}>
                  {selectedImage.name}
                </Typography>
                <Button 
                  variant="outlined" 
                  size="small" 
                  sx={{ mt: 1 }}
                  onClick={() => setSelectedImage(null)}
                >
                  Change Image
                </Button>
              </Box>
            ) : (
              <Box sx={{ textAlign: "center", py: 4 }}>
                <ImageIcon sx={{ fontSize: 48, color: "text.secondary", mb: 2 }} />
                <Typography variant="body2" color="text.secondary">
                  Select an image from the thumbnail view to begin preparation
                </Typography>
              </Box>
            )}
          </Paper>
        </Grid>

        {/* Settings Panel */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              <SettingsIcon sx={{ mr: 1, verticalAlign: "middle" }} />
              Plotting Settings
            </Typography>

            <Grid container spacing={3}>
              {/* Line Thickness */}
              <Grid item xs={12} sm={6}>
                <Typography gutterBottom>Line Thickness</Typography>
                <Slider
                  value={settings.lineThickness}
                  onChange={(e, value) => handleSettingChange('lineThickness', value)}
                  min={0.5}
                  max={3}
                  step={0.1}
                  marks
                  valueLabelDisplay="auto"
                />
              </Grid>

              {/* Contrast */}
              <Grid item xs={12} sm={6}>
                <Typography gutterBottom>Contrast</Typography>
                <Slider
                  value={settings.contrast}
                  onChange={(e, value) => handleSettingChange('contrast', value)}
                  min={0}
                  max={100}
                  valueLabelDisplay="auto"
                />
              </Grid>

              {/* Brightness */}
              <Grid item xs={12} sm={6}>
                <Typography gutterBottom>Brightness</Typography>
                <Slider
                  value={settings.brightness}
                  onChange={(e, value) => handleSettingChange('brightness', value)}
                  min={0}
                  max={100}
                  valueLabelDisplay="auto"
                />
              </Grid>

              {/* Threshold */}
              <Grid item xs={12} sm={6}>
                <Typography gutterBottom>Threshold</Typography>
                <Slider
                  value={settings.threshold}
                  onChange={(e, value) => handleSettingChange('threshold', value)}
                  min={0}
                  max={255}
                  valueLabelDisplay="auto"
                />
              </Grid>

              {/* Resolution */}
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Resolution</InputLabel>
                  <Select
                    value={settings.resolution}
                    label="Resolution"
                    onChange={(e) => handleSettingChange('resolution', e.target.value)}
                  >
                    <MenuItem value="low">Low (Fast)</MenuItem>
                    <MenuItem value="medium">Medium (Balanced)</MenuItem>
                    <MenuItem value="high">High (Precise)</MenuItem>
                  </Select>
                </FormControl>
              </Grid>

              {/* Smoothing */}
              <Grid item xs={12} sm={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.smoothing}
                      onChange={(e) => handleSettingChange('smoothing', e.target.checked)}
                    />
                  }
                  label="Enable Smoothing"
                />
              </Grid>
            </Grid>

            <Divider sx={{ my: 3 }} />

            {/* Action Buttons */}
            <Box sx={{ display: "flex", gap: 2, justifyContent: "flex-end" }}>
              <Button
                variant="outlined"
                startIcon={<SaveIcon />}
                onClick={handleSave}
                disabled={!selectedImage}
              >
                Save Settings
              </Button>
              <Button
                variant="contained"
                startIcon={<PlayIcon />}
                onClick={handleProcess}
                disabled={!selectedImage}
              >
                Process Image
              </Button>
            </Box>
          </Paper>
        </Grid>

        {/* Preview Panel */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Preview
            </Typography>
            
            {selectedImage ? (
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" gutterBottom>Original</Typography>
                  <img 
                    src={selectedImage.original} 
                    alt="Original"
                    style={{ width: "100%", height: "auto", borderRadius: "4px" }}
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" gutterBottom>Processed Preview</Typography>
                  <Box 
                    sx={{ 
                      width: "100%", 
                      height: "200px", 
                      bgcolor: "grey.100", 
                      borderRadius: "4px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center"
                    }}
                  >
                    <Typography color="text.secondary">
                      Preview will appear here after processing
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            ) : (
              <Alert severity="info">
                Select an image to see the preview and processing options.
              </Alert>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
