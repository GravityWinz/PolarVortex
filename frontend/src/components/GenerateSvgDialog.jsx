import { Close as CloseIcon, ExpandMore as ExpandMoreIcon, Help as HelpIcon, Save as SaveIcon } from "@mui/icons-material";
import {
    Accordion,
    AccordionDetails,
    AccordionSummary,
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
    TextField,
    Tooltip,
    Typography,
} from "@mui/material";
import React, { useEffect, useState } from "react";
import {
    generateProjectSvg,
    getAvailableSvgGenerators,
    getSvgGeneratorInfo,
    saveProjectSvg
} from "../services/apiService";

const GenerateSvgDialog = ({ open, onClose, project }) => {
  const [selectedAlgorithm, setSelectedAlgorithm] = useState("geometric_pattern");
  const [availableAlgorithms, setAvailableAlgorithms] = useState([]);
  const [loadingAlgorithms, setLoadingAlgorithms] = useState(false);
  const [algorithmInfo, setAlgorithmInfo] = useState(null);
  const [generationSettings, setGenerationSettings] = useState({});

  const [isGenerating, setIsGenerating] = useState(false);
  const [generationResult, setGenerationResult] = useState(null);
  const [error, setError] = useState(null);
  const [filename, setFilename] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const normalizeFilename = (value) => value.trim().replace(/\.svg$/i, "");
  const getFilenameError = (value) => {
    const trimmed = value.trim();
    if (!trimmed) {
      return "Filename is required";
    }
    if (/[\\/]/.test(trimmed)) {
      return "Filename cannot include slashes";
    }
    if (trimmed.includes("..")) {
      return "Filename cannot include ..";
    }
    return "";
  };
  const normalizedFilename = normalizeFilename(filename);
  const rawFilenameError = getFilenameError(filename);
  const filenameError =
    generationResult || filename.trim() ? rawFilenameError : "";

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
      setGenerationResult(null);
      setError(null);
      setIsGenerating(false);
      setFilename("");
      setIsSaving(false);
    }
  }, [open]);

  // Set default filename when generation completes
  useEffect(() => {
    if (generationResult && !filename) {
      const defaultName = `${selectedAlgorithm}_${new Date().toISOString().slice(0, 10)}`;
      setFilename(defaultName);
    }
  }, [generationResult, selectedAlgorithm, filename]);

  const loadAvailableAlgorithms = async () => {
    setLoadingAlgorithms(true);
    try {
      const algorithms = await getAvailableSvgGenerators();
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
      const info = await getSvgGeneratorInfo(selectedAlgorithm);
      if (info) {
        setAlgorithmInfo(info);
        if (info.default_settings) {
          setGenerationSettings(info.default_settings);
        }
      }
    } catch (err) {
      console.warn(`Failed to load settings for ${selectedAlgorithm}:`, err);
      setAlgorithmInfo(null);
    }
  };

  const handleAlgorithmChange = (event) => {
    setSelectedAlgorithm(event.target.value);
    setGenerationResult(null);
    setError(null);
  };

  const handleSettingChange = (setting, value) => {
    setGenerationSettings(prev => ({
      ...prev,
      [setting]: value
    }));
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);
    setGenerationResult(null);

    try {
      const result = await generateProjectSvg(
        project.id, 
        generationSettings,
        selectedAlgorithm
      );
      setGenerationResult(result);
    } catch (err) {
      setError(err.message || "SVG generation failed");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSave = async () => {
    if (!generationResult?.svg_content) {
      setError("Please generate an SVG first");
      return;
    }

    if (filenameError) {
      return;
    }

    const saveFilename = `${normalizedFilename}.svg`;

    setIsSaving(true);
    setError(null);

    try {
      await saveProjectSvg(project.id, generationResult.svg_content, saveFilename);
      // Close dialog after successful save
      handleClose();
    } catch (err) {
      setError(err.message || "Failed to save SVG");
    } finally {
      setIsSaving(false);
    }
  };

  const handleClose = () => {
    setGenerationResult(null);
    setError(null);
    setFilename("");
    setIsSaving(false);
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
              Generate SVG: {project.name}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Generate SVG content algorithmically
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
          {/* Left Column - Preview */}
          <Grid item xs={12} md={6}>
            <Card sx={{ height: '100%' }}>
              {generationResult?.preview ? (
                <CardMedia
                  component="img"
                  height="400"
                  image={generationResult.preview}
                  alt="Generated SVG preview"
                  sx={{ objectFit: 'contain', backgroundColor: 'grey.100' }}
                />
              ) : (
                <Box
                  sx={{
                    height: 400,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: 'grey.100',
                    color: 'text.secondary'
                  }}
                >
                  <Typography variant="body1">
                    Preview will appear here after generation
                  </Typography>
                </Box>
              )}
              <Box sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  {generationResult ? "Generated SVG Preview" : "Preview"}
                </Typography>
                {generationResult && (
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      Size: {generationResult.width} × {generationResult.height}px
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Processing time: {generationResult.processing_time?.toFixed(2)}s
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1, fontStyle: 'italic' }}>
                      Click "Save SVG" to save to project
                    </Typography>
                  </Box>
                )}
              </Box>
            </Card>
          </Grid>

          {/* Right Column - Generation Controls */}
          <Grid item xs={12} md={6}>
            <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <Typography variant="h6" gutterBottom>
                Generation Settings
              </Typography>

              {/* Algorithm Selector */}
              <Box sx={{ mb: 3 }}>
                <FormControl fullWidth>
                  <InputLabel id="algorithm-select-label">SVG Generator</InputLabel>
                  <Select
                    labelId="algorithm-select-label"
                    id="algorithm-select"
                    value={selectedAlgorithm}
                    label="SVG Generator"
                    onChange={handleAlgorithmChange}
                    disabled={loadingAlgorithms || isGenerating}
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
                    <FormHelperText>Loading generators...</FormHelperText>
                  )}
                </FormControl>
              </Box>

              <Divider sx={{ my: 2 }} />

              {/* Parameter Documentation Accordion */}
              {algorithmInfo && algorithmInfo.parameter_documentation && 
               Object.keys(algorithmInfo.parameter_documentation).length > 0 && (
                <Accordion sx={{ mb: 2 }}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <HelpIcon color="primary" />
                      <Typography variant="subtitle2">
                        Parameter Documentation
                      </Typography>
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Box>
                      {Object.entries(algorithmInfo.parameter_documentation).map(([paramKey, doc]) => (
                        <Box key={paramKey} sx={{ mb: 3, pb: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
                          <Typography variant="subtitle1" sx={{ fontWeight: 'bold', mb: 1 }}>
                            {paramKey.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
                          </Typography>
                          <Typography variant="body2" sx={{ mb: 1 }}>
                            <strong>Purpose:</strong> {doc.purpose}
                          </Typography>
                          <Typography variant="body2" sx={{ mb: 1 }}>
                            <strong>Range:</strong> {doc.range} | <strong>Default:</strong> {doc.default}
                          </Typography>
                          <Typography variant="body2" sx={{ mb: 1 }}>
                            <strong>Effects:</strong> {doc.effects}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            <strong>When to adjust:</strong> {doc.when_to_adjust}
                          </Typography>
                        </Box>
                      ))}
                    </Box>
                  </AccordionDetails>
                </Accordion>
              )}

              <Divider sx={{ my: 2 }} />

              {/* Dynamic Algorithm-Specific Settings */}
              {algorithmInfo && algorithmInfo.default_settings ? (
                <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
                  {Object.entries(algorithmInfo.default_settings).map(([key, defaultValue]) => {
                    const currentValue = generationSettings[key] !== undefined 
                      ? generationSettings[key] 
                      : defaultValue;
                    const settingType = typeof defaultValue;
                    const isBoolean = settingType === 'boolean';
                    const isNumber = settingType === 'number';
                    const isInteger = isNumber && Number.isInteger(defaultValue);
                    const isString = settingType === 'string';
                    
                    // Format setting name for display (convert snake_case to Title Case)
                    const displayName = key
                      .split('_')
                      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                      .join(' ');
                    
                    // Get parameter documentation if available
                    const paramDoc = algorithmInfo.parameter_documentation?.[key];
                    
                    if (isBoolean) {
                      return (
                        <Box key={key} sx={{ mb: 2 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            <FormControlLabel
                              control={
                                <Switch
                                  checked={currentValue}
                                  onChange={(e) => handleSettingChange(key, e.target.checked)}
                                  disabled={isGenerating}
                                />
                              }
                              label={displayName}
                            />
                            {paramDoc && (
                              <Tooltip 
                                title={
                                  <Box>
                                    <Typography variant="caption" display="block" sx={{ fontWeight: 'bold', mb: 0.5 }}>
                                      {paramDoc.description}
                                    </Typography>
                                    <Typography variant="caption" display="block">
                                      {paramDoc.purpose}
                                    </Typography>
                                  </Box>
                                }
                                arrow
                                placement="right"
                              >
                                <IconButton size="small" sx={{ p: 0.5 }}>
                                  <HelpIcon fontSize="small" color="action" />
                                </IconButton>
                              </Tooltip>
                            )}
                          </Box>
                        </Box>
                      );
                    } else if (isNumber) {
                      // Determine reasonable min/max/step based on value and key name
                      let min = 0;
                      let max = 100;
                      let step = isInteger ? 1 : 0.1;
                      
                      // Smart defaults based on common setting patterns
                      if (key.includes('width') || key.includes('height')) {
                        min = 100;
                        max = 5000;
                        step = 10;
                      } else if (key.includes('complexity')) {
                        min = 1;
                        max = 10;
                        step = 1;
                      } else if (key.includes('stroke_width')) {
                        min = 0.1;
                        max = 10;
                        step = 0.1;
                      } else if (defaultValue > max * 0.8) {
                        max = Math.ceil(defaultValue * 1.5);
                      }
                      
                      return (
                        <Box key={key} sx={{ mb: 3 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            <Typography gutterBottom sx={{ mb: 0 }}>
                              {displayName}: {currentValue}
                            </Typography>
                            {paramDoc && (
                              <Tooltip 
                                title={
                                  <Box>
                                    <Typography variant="caption" display="block" sx={{ fontWeight: 'bold', mb: 0.5 }}>
                                      {paramDoc.description}
                                    </Typography>
                                    <Typography variant="caption" display="block">
                                      {paramDoc.purpose}
                                    </Typography>
                                    <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
                                      Range: {paramDoc.range} | Default: {paramDoc.default}
                                    </Typography>
                                  </Box>
                                }
                                arrow
                                placement="right"
                              >
                                <IconButton size="small" sx={{ p: 0.5 }}>
                                  <HelpIcon fontSize="small" color="action" />
                                </IconButton>
                              </Tooltip>
                            )}
                          </Box>
                          <Slider
                            value={currentValue}
                            onChange={(e, value) => handleSettingChange(key, value)}
                            min={min}
                            max={max}
                            step={step}
                            valueLabelDisplay="auto"
                            disabled={isGenerating}
                          />
                        </Box>
                      );
                    } else if (isString) {
                      // String input - check if it's a select (like pattern_type)
                      const paramDoc = algorithmInfo.parameter_documentation?.[key];
                      const rangeStr = paramDoc?.range || "";
                      const isSelect = rangeStr.includes(',') || rangeStr.includes(' or ');
                      
                      if (isSelect) {
                        // Extract options from range string
                        const options = rangeStr.split(',').map(s => s.trim()).filter(s => s);
                        return (
                          <Box key={key} sx={{ mb: 2 }}>
                            <FormControl fullWidth>
                              <InputLabel>{displayName}</InputLabel>
                              <Select
                                value={currentValue}
                                label={displayName}
                                onChange={(e) => handleSettingChange(key, e.target.value)}
                                disabled={isGenerating}
                              >
                                {options.map(opt => (
                                  <MenuItem key={opt} value={opt}>{opt}</MenuItem>
                                ))}
                              </Select>
                            </FormControl>
                          </Box>
                        );
                      } else {
                        // Regular text field
                        return (
                          <Box key={key} sx={{ mb: 2 }}>
                            <TextField
                              fullWidth
                              label={displayName}
                              value={currentValue}
                              onChange={(e) => handleSettingChange(key, e.target.value)}
                              disabled={isGenerating}
                              helperText={paramDoc?.description}
                            />
                          </Box>
                        );
                      }
                    } else {
                      return null;
                    }
                  })}
                </Box>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No settings available for this generator
                </Typography>
              )}

              <Divider sx={{ my: 2 }} />

              <TextField
                fullWidth
                label="Filename"
                value={filename}
                onChange={(e) => setFilename(e.target.value)}
                disabled={isSaving}
                error={Boolean(filenameError)}
                helperText={
                  filenameError ||
                  (normalizedFilename
                    ? `Saved as ${normalizedFilename}.svg`
                    : "Add a filename; .svg is added automatically.")
                }
              />

              {error && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {error}
                </Alert>
              )}
            </Box>
          </Grid>
        </Grid>
      </DialogContent>

      <DialogActions>
        <Button 
          onClick={handleClose} 
          disabled={isGenerating || isSaving}
        >
          Close
        </Button>
        <Button
          onClick={handleSave}
          variant="contained"
          color="primary"
          disabled={!generationResult || isSaving || Boolean(filenameError)}
          startIcon={isSaving ? <CircularProgress size={20} /> : <SaveIcon />}
        >
          {isSaving ? "Saving..." : "Save"}
        </Button>
        <Button
          onClick={handleGenerate}
          variant="contained"
          disabled={isGenerating || !selectedAlgorithm}
          startIcon={isGenerating ? <CircularProgress size={20} /> : null}
        >
          {isGenerating ? "Generating..." : "Generate"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default GenerateSvgDialog;
