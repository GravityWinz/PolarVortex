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
    FormControl,
    FormControlLabel,
    FormHelperText,
    Grid,
    IconButton,
    InputLabel,
    MenuItem,
    Select,
    Slider,
    Switch,
    Typography,
} from "@mui/material";
import React, { useEffect, useState } from "react";
import { 
    getProjectImageUrl, 
    getProjectVectorizationSvgUrl, 
    vectorizeProjectImage,
    getAvailableVectorizers,
    getVectorizerInfo
} from "../services/apiService";

const VectorizeDialog = ({ open, onClose, project }) => {
  const [selectedAlgorithm, setSelectedAlgorithm] = useState("polargraph");
  const [availableAlgorithms, setAvailableAlgorithms] = useState([]);
  const [loadingAlgorithms, setLoadingAlgorithms] = useState(false);
  const [algorithmInfo, setAlgorithmInfo] = useState(null);
  const [vectorizationSettings, setVectorizationSettings] = useState({});

  const [isVectorizing, setIsVectorizing] = useState(false);
  const [vectorizationResult, setVectorizationResult] = useState(null);
  const [error, setError] = useState(null);

  // Load available algorithms on mount
  useEffect(() => {
    if (open) {
      loadAvailableAlgorithms();
    }
  }, [open]);

  // Load algorithm settings when algorithm changes or dialog opens
  useEffect(() => {
    if (selectedAlgorithm && open) {
      loadAlgorithmSettings();
    }
  }, [selectedAlgorithm, open]);

  // Reset state when dialog opens/closes
  useEffect(() => {
    if (open) {
      setVectorizationResult(null);
      setError(null);
      setIsVectorizing(false);
    }
  }, [open]);

  const loadAvailableAlgorithms = async () => {
    setLoadingAlgorithms(true);
    try {
      const algorithms = await getAvailableVectorizers();
      setAvailableAlgorithms(algorithms);
      if (algorithms.length > 0 && !algorithms.find(a => a.id === selectedAlgorithm)) {
        setSelectedAlgorithm(algorithms[0].id);
      }
    } catch (err) {
      setError(`Failed to load algorithms: ${err.message}`);
    } finally {
      setLoadingAlgorithms(false);
    }
  };

  const loadAlgorithmSettings = async () => {
    try {
      const info = await getVectorizerInfo(selectedAlgorithm);
      if (info) {
        setAlgorithmInfo(info);
        if (info.default_settings) {
          setVectorizationSettings(info.default_settings);
        }
      }
    } catch (err) {
      console.warn(`Failed to load settings for ${selectedAlgorithm}:`, err);
      setAlgorithmInfo(null);
    }
  };

  const handleAlgorithmChange = (event) => {
    setSelectedAlgorithm(event.target.value);
    setVectorizationResult(null);
    setError(null);
  };

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
      const result = await vectorizeProjectImage(
        project.id, 
        vectorizationSettings,
        selectedAlgorithm
      );
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

              {/* Algorithm Selector */}
              <Box sx={{ mb: 3 }}>
                <FormControl fullWidth>
                  <InputLabel id="algorithm-select-label">Vectorization Algorithm</InputLabel>
                  <Select
                    labelId="algorithm-select-label"
                    id="algorithm-select"
                    value={selectedAlgorithm}
                    label="Vectorization Algorithm"
                    onChange={handleAlgorithmChange}
                    disabled={loadingAlgorithms || isVectorizing}
                  >
                    {availableAlgorithms.map((alg) => (
                      <MenuItem key={alg.id} value={alg.id}>
                        <Box>
                          <Typography variant="body1">{alg.name}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            {alg.description}
                          </Typography>
                        </Box>
                      </MenuItem>
                    ))}
                  </Select>
                  {loadingAlgorithms && (
                    <FormHelperText>Loading algorithms...</FormHelperText>
                  )}
                </FormControl>
              </Box>

              <Divider sx={{ my: 2 }} />

              {/* Dynamic Algorithm-Specific Settings */}
              {algorithmInfo && algorithmInfo.default_settings ? (
                <Box>
                  {Object.entries(algorithmInfo.default_settings).map(([key, defaultValue]) => {
                    const currentValue = vectorizationSettings[key] !== undefined 
                      ? vectorizationSettings[key] 
                      : defaultValue;
                    const settingType = typeof defaultValue;
                    const isBoolean = settingType === 'boolean';
                    const isNumber = settingType === 'number';
                    const isInteger = isNumber && Number.isInteger(defaultValue);
                    
                    // Format setting name for display (convert snake_case to Title Case)
                    const displayName = key
                      .split('_')
                      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                      .join(' ');
                    
                    if (isBoolean) {
                      return (
                        <Box key={key} sx={{ mb: 2 }}>
                          <FormControlLabel
                            control={
                              <Switch
                                checked={currentValue}
                                onChange={(e) => handleSettingChange(key, e.target.checked)}
                                disabled={isVectorizing}
                              />
                            }
                            label={displayName}
                          />
                        </Box>
                      );
                    } else if (isNumber) {
                      // Determine reasonable min/max/step based on value
                      let min = 0;
                      let max = 100;
                      let step = isInteger ? 1 : 0.1;
                      
                      // Smart defaults based on common setting patterns
                      if (key.includes('ratio') || key.includes('threshold') || key.includes('thresh')) {
                        min = 0;
                        max = isInteger ? 100 : 1.0;
                        step = isInteger ? 1 : 0.01;
                      } else if (key.includes('size') || key.includes('length') || key.includes('area')) {
                        min = 0;
                        max = isInteger ? 200 : 20.0;
                        step = isInteger ? 1 : 0.5;
                      } else if (key.includes('angle') || key.includes('deg')) {
                        min = 0;
                        max = 180;
                        step = 1;
                      } else if (key.includes('kernel')) {
                        min = 0;
                        max = 50;
                        step = 1;
                      } else if (key.includes('level') || key.includes('count')) {
                        min = 1;
                        max = 50;
                        step = 1;
                      } else if (key.includes('radius') || key.includes('blur')) {
                        min = 0;
                        max = 10;
                        step = isInteger ? 1 : 0.1;
                      } else if (key.includes('tolerance') || key.includes('tolerance')) {
                        min = 0;
                        max = 100;
                        step = 1;
                      }
                      
                      // Adjust max if default value suggests a different range
                      if (defaultValue > max * 0.8) {
                        max = Math.ceil(defaultValue * 1.5);
                      }
                      
                      return (
                        <Box key={key} sx={{ mb: 3 }}>
                          <Typography gutterBottom>
                            {displayName}: {currentValue}
                          </Typography>
                          <Slider
                            value={currentValue}
                            onChange={(e, value) => handleSettingChange(key, value)}
                            min={min}
                            max={max}
                            step={step}
                            valueLabelDisplay="auto"
                            disabled={isVectorizing}
                          />
                        </Box>
                      );
                    } else {
                      // String or other types - show as text field
                      return (
                        <Box key={key} sx={{ mb: 2 }}>
                          <Typography gutterBottom>{displayName}</Typography>
                          <input
                            type="text"
                            value={currentValue}
                            onChange={(e) => handleSettingChange(key, e.target.value)}
                            disabled={isVectorizing}
                            style={{
                              width: '100%',
                              padding: '8px',
                              border: '1px solid #ccc',
                              borderRadius: '4px'
                            }}
                          />
                        </Box>
                      );
                    }
                  })}
                </Box>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Loading settings...
                </Typography>
              )}
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
                  • Algorithm: {vectorizationResult.algorithm || selectedAlgorithm}
                </Typography>
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
          disabled={isVectorizing || !project.source_image || loadingAlgorithms}
          startIcon={isVectorizing ? <CircularProgress size={20} /> : null}
        >
          {isVectorizing ? 'Vectorizing...' : 'Apply Vectorization'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default VectorizeDialog;
