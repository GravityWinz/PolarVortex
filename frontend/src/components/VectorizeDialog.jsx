import { Close as CloseIcon } from "@mui/icons-material";
import {
    Alert,
    Box,
    Button,
    Card,
    CardMedia,
    CircularProgress,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    Divider,
    FormControlLabel,
    Grid,
    IconButton,
    Slider,
    Switch,
    Typography,
} from "@mui/material";
import React, { useEffect, useState } from "react";
import { getProjectImageUrl, getProjectVectorizationSvgUrl, vectorizeProjectImage } from "../services/apiService";

const VectorizeDialog = ({ open, onClose, project }) => {
  const [vectorizationSettings, setVectorizationSettings] = useState({
    blur_radius: 1,
    posterize_levels: 5,
    simplification_threshold: 2.0,
    min_contour_area: 10,
    color_tolerance: 10,
    enable_color_separation: true,
    enable_contour_simplification: true,
    enable_noise_reduction: true,
  });

  const [isVectorizing, setIsVectorizing] = useState(false);
  const [vectorizationResult, setVectorizationResult] = useState(null);
  const [error, setError] = useState(null);

  // Reset state when dialog opens/closes
  useEffect(() => {
    if (open) {
      setVectorizationResult(null);
      setError(null);
      setIsVectorizing(false);
    }
  }, [open]);

  const handleSettingChange = (setting, value) => {
    setVectorizationSettings(prev => ({
      ...prev,
      [setting]: value
    }));
  };

  const handleVectorize = async () => {
    if (!project?.source_image) {
      setError("No source image available for vectorization");
      return;
    }

    setIsVectorizing(true);
    setError(null);
    setVectorizationResult(null);

    try {
      const result = await vectorizeProjectImage(project.id, vectorizationSettings);
      setVectorizationResult(result);
    } catch (err) {
      setError(err.message || "Vectorization failed");
    } finally {
      setIsVectorizing(false);
    }
  };

  const handleClose = () => {
    setVectorizationResult(null);
    setError(null);
    onClose();
  };

  if (!project) return null;

  return (
    <Dialog 
      open={open} 
      onClose={handleClose} 
      maxWidth="lg" 
      fullWidth
      PaperProps={{
        sx: { minHeight: '80vh' }
      }}
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box>
            <Typography variant="h5" component="div">
              Vectorize Image: {project.name}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Convert your image to vector paths for plotting
            </Typography>
          </Box>
          <IconButton
            onClick={handleClose}
            sx={{ ml: 2 }}
            size="small"
          >
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Grid container spacing={3}>
          {/* Left Column - Image Preview */}
          <Grid item xs={12} md={6}>
            <Card sx={{ height: '100%' }}>
              <CardMedia
                component="img"
                height="400"
                image={getProjectImageUrl(project.id, project.source_image)}
                alt={`${project.name} source image`}
                sx={{ objectFit: 'contain', backgroundColor: 'grey.100' }}
              />
              <Box sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Source Image
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {project.source_image}
                </Typography>
              </Box>
            </Card>
          </Grid>

          {/* Right Column - Vectorization Controls */}
          <Grid item xs={12} md={6}>
            <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <Typography variant="h6" gutterBottom>
                Vectorization Settings
              </Typography>

              {/* Blur Radius */}
              <Box sx={{ mb: 3 }}>
                <Typography gutterBottom>
                  Blur Radius: {vectorizationSettings.blur_radius}
                </Typography>
                <Slider
                  value={vectorizationSettings.blur_radius}
                  onChange={(e, value) => handleSettingChange('blur_radius', value)}
                  min={0}
                  max={5}
                  step={1}
                  marks
                  valueLabelDisplay="auto"
                />
                <Typography variant="caption" color="text.secondary">
                  Noise reduction (0 = no blur)
                </Typography>
              </Box>

              {/* Posterize Levels */}
              <Box sx={{ mb: 3 }}>
                <Typography gutterBottom>
                  Color Levels: {vectorizationSettings.posterize_levels}
                </Typography>
                <Slider
                  value={vectorizationSettings.posterize_levels}
                  onChange={(e, value) => handleSettingChange('posterize_levels', value)}
                  min={2}
                  max={16}
                  step={1}
                  marks
                  valueLabelDisplay="auto"
                />
                <Typography variant="caption" color="text.secondary">
                  Number of color levels (fewer = simpler)
                </Typography>
              </Box>

              {/* Simplification Threshold */}
              <Box sx={{ mb: 3 }}>
                <Typography gutterBottom>
                  Simplification: {vectorizationSettings.simplification_threshold}
                </Typography>
                <Slider
                  value={vectorizationSettings.simplification_threshold}
                  onChange={(e, value) => handleSettingChange('simplification_threshold', value)}
                  min={0.5}
                  max={10}
                  step={0.5}
                  valueLabelDisplay="auto"
                />
                <Typography variant="caption" color="text.secondary">
                  Path simplification (lower = more detailed)
                </Typography>
              </Box>

              {/* Min Contour Area */}
              <Box sx={{ mb: 3 }}>
                <Typography gutterBottom>
                  Min Area: {vectorizationSettings.min_contour_area}
                </Typography>
                <Slider
                  value={vectorizationSettings.min_contour_area}
                  onChange={(e, value) => handleSettingChange('min_contour_area', value)}
                  min={1}
                  max={100}
                  step={1}
                  valueLabelDisplay="auto"
                />
                <Typography variant="caption" color="text.secondary">
                  Minimum area for shapes (filters small details)
                </Typography>
              </Box>

              {/* Color Tolerance */}
              <Box sx={{ mb: 3 }}>
                <Typography gutterBottom>
                  Color Tolerance: {vectorizationSettings.color_tolerance}
                </Typography>
                <Slider
                  value={vectorizationSettings.color_tolerance}
                  onChange={(e, value) => handleSettingChange('color_tolerance', value)}
                  min={1}
                  max={50}
                  step={1}
                  valueLabelDisplay="auto"
                />
                <Typography variant="caption" color="text.secondary">
                  Color grouping sensitivity
                </Typography>
              </Box>

              <Divider sx={{ my: 2 }} />

              {/* Toggle Options */}
              <Box sx={{ mb: 2 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={vectorizationSettings.enable_color_separation}
                      onChange={(e) => handleSettingChange('enable_color_separation', e.target.checked)}
                    />
                  }
                  label="Color Separation"
                />
                <Typography variant="caption" color="text.secondary" display="block">
                  Separate different colors into different paths
                </Typography>
              </Box>

              <Box sx={{ mb: 2 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={vectorizationSettings.enable_contour_simplification}
                      onChange={(e) => handleSettingChange('enable_contour_simplification', e.target.checked)}
                    />
                  }
                  label="Contour Simplification"
                />
                <Typography variant="caption" color="text.secondary" display="block">
                  Simplify contours using Douglas-Peucker algorithm
                </Typography>
              </Box>

              <Box sx={{ mb: 2 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={vectorizationSettings.enable_noise_reduction}
                      onChange={(e) => handleSettingChange('enable_noise_reduction', e.target.checked)}
                    />
                  }
                  label="Noise Reduction"
                />
                <Typography variant="caption" color="text.secondary" display="block">
                  Apply blur for noise reduction
                </Typography>
              </Box>
            </Box>
          </Grid>
        </Grid>

        {/* Error Display */}
        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}

        {/* Vectorization Result */}
        {vectorizationResult && (
          <Box sx={{ mt: 3 }}>
            <Alert severity="success" sx={{ mb: 2 }}>
              Vectorization completed successfully!
            </Alert>
            
            <Grid container spacing={3}>
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" gutterBottom>Results:</Typography>
                <Typography variant="body2">
                  • Total Paths: {vectorizationResult.vectorization_result.total_paths}
                </Typography>
                <Typography variant="body2">
                  • Colors Detected: {vectorizationResult.vectorization_result.colors_detected}
                </Typography>
                <Typography variant="body2">
                  • Processing Time: {vectorizationResult.vectorization_result.processing_time.toFixed(2)}s
                </Typography>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Typography variant="subtitle2" gutterBottom>Files Created:</Typography>
                <Typography variant="body2">
                  • SVG: {vectorizationResult.svg_path ? 'Created' : 'Not created'}
                </Typography>
                <Typography variant="body2">
                  • Plotting Commands: {vectorizationResult.plotting_commands?.length || 0} commands
                </Typography>
              </Grid>
            </Grid>

            {/* SVG Result Display */}
            {vectorizationResult.svg_path && (
              <Box sx={{ mt: 3 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Generated SVG:
                </Typography>
                <Card sx={{ p: 2, backgroundColor: 'grey.50' }}>
                  <Box sx={{ 
                    maxHeight: '400px', 
                    overflow: 'auto',
                    border: '1px solid #ccc',
                    borderRadius: '4px',
                    backgroundColor: 'white'
                  }}>
                    <iframe
                      src={getProjectVectorizationSvgUrl(project.id)}
                      style={{
                        width: '100%',
                        height: '400px',
                        border: 'none'
                      }}
                      title="Generated SVG"
                    />
                  </Box>
                </Card>
              </Box>
            )}

            {/* Preview Image */}
            {vectorizationResult.preview && (
              <Box sx={{ mt: 3 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Vectorization Preview:
                </Typography>
                <img
                  src={vectorizationResult.preview}
                  alt="Vectorization preview"
                  style={{
                    maxWidth: '100%',
                    height: 'auto',
                    border: '1px solid #ccc',
                    borderRadius: '4px'
                  }}
                />
              </Box>
            )}
          </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ p: 3 }}>
        <Button onClick={handleClose} disabled={isVectorizing}>
          Close
        </Button>
        {vectorizationResult && (
          <Button
            onClick={() => {
              setVectorizationResult(null);
              setError(null);
            }}
            variant="outlined"
            disabled={isVectorizing}
          >
            Vectorize Again
          </Button>
        )}
        <Button
          onClick={handleVectorize}
          variant="contained"
          disabled={isVectorizing || !project.source_image}
          startIcon={isVectorizing ? <CircularProgress size={20} /> : null}
        >
          {isVectorizing ? 'Vectorizing...' : 'Apply Vectorization'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default VectorizeDialog;
