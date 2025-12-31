import {
  CheckCircle as CheckCircleIcon,
  CloudUpload as CloudUploadIcon,
  Delete as DeleteIcon,
  FileUpload as FileUploadIcon,
  Image as ImageIcon,
  PlayArrow as PlayIcon,
  Settings as SettingsIcon,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CardMedia,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  Grid,
  IconButton,
  InputLabel,
  LinearProgress,
  MenuItem,
  Paper,
  Select,
  Slider,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import React, { useCallback, useState } from "react";
import logoImage from "../assets/PolarVortexLogo_small.png";
import { uploadImageToProject } from "../services/apiService";

/**
 * Image Upload component for PolarVortex
 * Handles file selection, image processing, and upload to backend for a specific project
 */
export default function ImageUpload({ project, onUploadComplete }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStatus, setUploadStatus] = useState("idle"); // idle, uploading, success, error
  const [errorMessage, setErrorMessage] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [processingSettings, setProcessingSettings] = useState({
    threshold: 128,
    invert: false,
    dither: true,
    resolution: "medium",
    maxWidth: 800,
    maxHeight: 600,
  });

  // Handle file selection
  const handleFileSelect = useCallback((event) => {
    const file = event.target.files[0];
    if (file) {
      validateAndSetFile(file);
    }
  }, []);

  // Handle drag and drop
  const handleDrop = useCallback((event) => {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    if (file) {
      validateAndSetFile(file);
    }
  }, []);

  const handleDragOver = useCallback((event) => {
    event.preventDefault();
  }, []);

  // Validate file and create preview
  const validateAndSetFile = (file) => {
    // Check file type
    if (!file.type.startsWith("image/")) {
      setErrorMessage(
        "Please select a valid image file (JPEG, PNG, GIF, etc.)"
      );
      return;
    }

    // Check file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      setErrorMessage("File size must be less than 10MB");
      return;
    }

    setSelectedFile(file);
    setErrorMessage("");
    setUploadStatus("idle");

    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setPreviewUrl(e.target.result);
    };
    reader.readAsDataURL(file);
  };

  // Remove selected file
  const handleRemoveFile = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setUploadProgress(0);
    setUploadStatus("idle");
    setErrorMessage("");
  };

  // Upload file to backend
  const handleUpload = async () => {
    if (!selectedFile || !project) return;

    setUploadStatus("uploading");
    setUploadProgress(0);

    try {
      const formData = new FormData();
      // Backend expects field name 'file' and 'settings'
      formData.append("file", selectedFile);
      formData.append("settings", JSON.stringify(processingSettings));

      const response = await uploadImageToProject(project.id, formData);

      setUploadProgress(100);
      setUploadStatus("success");

      // If backend returns preview, update preview to processed image
      if (response?.preview) {
        setPreviewUrl(response.preview);
      }

      // Notify parent component of successful upload
      if (onUploadComplete) {
        onUploadComplete(project, response);
      }
    } catch (error) {
      setUploadStatus("error");
      setErrorMessage(error?.message || "Upload failed. Please try again.");
      setUploadProgress(0);
    }
  };

  // Get file size in readable format
  const getFileSize = (bytes) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  // Get status color
  const getStatusColor = () => {
    switch (uploadStatus) {
      case "success":
        return "success";
      case "error":
        return "error";
      case "uploading":
        return "primary";
      default:
        return "default";
    }
  };

  return (
    <Box>
      {/* Header with Logo */}
      <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
        <img
          src={logoImage}
          alt="PolarVortex Logo"
          style={{ height: "40px", width: "auto", marginRight: "16px" }}
        />
        <Box>
          <Typography variant="h4" gutterBottom sx={{ mb: 0 }}>
            {project ? `Upload to ${project.name}` : "Image Upload"}
          </Typography>
          <Typography
            variant="body1"
            color="text.secondary"
            paragraph
            sx={{ mb: 0 }}
          >
            {project
              ? `Upload and process an image for the "${project.name}" project.`
              : "Please select a project to upload images."}
          </Typography>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* File Upload Area */}
        <Grid item xs={12} md={6}>
          <Paper
            sx={{
              p: 3,
              border: "2px dashed",
              borderColor: selectedFile ? "primary.main" : "grey.300",
              backgroundColor: selectedFile ? "primary.50" : "background.paper",
              transition: "all 0.3s ease",
              cursor: "pointer",
              "&:hover": {
                borderColor: "primary.main",
                backgroundColor: "primary.50",
              },
            }}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onClick={() => document.getElementById("file-input").click()}
          >
            <input
              id="file-input"
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              style={{ display: "none" }}
            />

            <Box sx={{ textAlign: "center" }}>
              {selectedFile ? (
                <CheckCircleIcon
                  sx={{ fontSize: 48, color: "success.main", mb: 2 }}
                />
              ) : (
                <CloudUploadIcon
                  sx={{ fontSize: 48, color: "primary.main", mb: 2 }}
                />
              )}

              <Typography variant="h6" gutterBottom>
                {selectedFile
                  ? "File Selected"
                  : "Drop image here or click to browse"}
              </Typography>

              <Typography variant="body2" color="text.secondary">
                {selectedFile
                  ? `${selectedFile.name} (${getFileSize(selectedFile.size)})`
                  : "Supports JPEG, PNG, GIF up to 10MB"}
              </Typography>
            </Box>
          </Paper>

          {/* File Actions */}
          {selectedFile && (
            <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
              <Button
                variant="contained"
                startIcon={<PlayIcon />}
                onClick={handleUpload}
                disabled={
                  uploadStatus === "uploading" ||
                  !project
                }
                fullWidth
              >
                Process & Upload
              </Button>
              <Button
                variant="outlined"
                startIcon={<SettingsIcon />}
                onClick={() => setSettingsOpen(true)}
              >
                Settings
              </Button>
              <IconButton
                color="error"
                onClick={handleRemoveFile}
                disabled={uploadStatus === "uploading"}
              >
                <DeleteIcon />
              </IconButton>
            </Stack>
          )}

          {/* Upload Progress */}
          {uploadStatus === "uploading" && (
            <Box sx={{ mt: 2 }}>
              <LinearProgress variant="determinate" value={uploadProgress} />
              <Typography variant="body2" sx={{ mt: 1 }}>
                Uploading... {uploadProgress}%
              </Typography>
            </Box>
          )}

          {/* Status Messages */}
          {uploadStatus === "success" && (
            <Alert severity="success" sx={{ mt: 2 }}>
              Image uploaded successfully! Ready for processing.
            </Alert>
          )}

          {uploadStatus === "error" && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {errorMessage}
            </Alert>
          )}

          {errorMessage && uploadStatus === "idle" && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {errorMessage}
            </Alert>
          )}
        </Grid>

        {/* Image Preview */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Preview
              </Typography>

              {previewUrl ? (
                <Box sx={{ position: "relative" }}>
                  <CardMedia
                    component="img"
                    image={previewUrl}
                    alt="Preview"
                    sx={{
                      height: 300,
                      objectFit: "contain",
                      border: "1px solid",
                      borderColor: "grey.300",
                      borderRadius: 1,
                    }}
                  />

                  {/* File Info */}
                  <Box sx={{ mt: 2 }}>
                    <Stack direction="row" spacing={1} flexWrap="wrap">
                      <Chip
                        icon={<ImageIcon />}
                        label={selectedFile?.type || "Image"}
                        size="small"
                      />
                      <Chip
                        icon={<FileUploadIcon />}
                        label={getFileSize(selectedFile?.size || 0)}
                        size="small"
                      />
                      <Chip
                        label={uploadStatus}
                        color={getStatusColor()}
                        size="small"
                      />
                    </Stack>
                  </Box>
                </Box>
              ) : (
                <Box
                  sx={{
                    height: 300,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    border: "2px dashed",
                    borderColor: "grey.300",
                    borderRadius: 1,
                    backgroundColor: "grey.50",
                  }}
                >
                  <Typography variant="body2" color="text.secondary">
                    No image selected
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Processing Settings Dialog */}
      <Dialog
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Image Processing Settings</DialogTitle>
        <DialogContent>
          <Grid container spacing={3} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <Typography variant="subtitle2" gutterBottom>
                Threshold (Black & White Conversion)
              </Typography>
              <Slider
                value={processingSettings.threshold}
                onChange={(_, value) =>
                  setProcessingSettings((prev) => ({
                    ...prev,
                    threshold: value,
                  }))
                }
                min={0}
                max={255}
                valueLabelDisplay="auto"
                marks={[
                  { value: 0, label: "0" },
                  { value: 128, label: "128" },
                  { value: 255, label: "255" },
                ]}
              />
            </Grid>

            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Resolution</InputLabel>
                <Select
                  value={processingSettings.resolution}
                  onChange={(e) =>
                    setProcessingSettings((prev) => ({
                      ...prev,
                      resolution: e.target.value,
                    }))
                  }
                  label="Resolution"
                >
                  <MenuItem value="low">Low (400x300)</MenuItem>
                  <MenuItem value="medium">Medium (800x600)</MenuItem>
                  <MenuItem value="high">High (1200x900)</MenuItem>
                  <MenuItem value="custom">Custom</MenuItem>
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} sm={6}>
              <FormControlLabel
                control={
                  <Switch
                    checked={processingSettings.invert}
                    onChange={(e) =>
                      setProcessingSettings((prev) => ({
                        ...prev,
                        invert: e.target.checked,
                      }))
                    }
                  />
                }
                label="Invert Colors"
              />
            </Grid>

            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={processingSettings.dither}
                    onChange={(e) =>
                      setProcessingSettings((prev) => ({
                        ...prev,
                        dither: e.target.checked,
                      }))
                    }
                  />
                }
                label="Enable Dithering"
              />
            </Grid>

            {processingSettings.resolution === "custom" && (
              <>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Max Width"
                    type="number"
                    value={processingSettings.maxWidth}
                    onChange={(e) =>
                      setProcessingSettings((prev) => ({
                        ...prev,
                        maxWidth: parseInt(e.target.value),
                      }))
                    }
                    inputProps={{ min: 100, max: 2000 }}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Max Height"
                    type="number"
                    value={processingSettings.maxHeight}
                    onChange={(e) =>
                      setProcessingSettings((prev) => ({
                        ...prev,
                        maxHeight: parseInt(e.target.value),
                      }))
                    }
                    inputProps={{ min: 100, max: 2000 }}
                  />
                </Grid>
              </>
            )}
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSettingsOpen(false)}>Cancel</Button>
          <Button onClick={() => setSettingsOpen(false)} variant="contained">
            Apply Settings
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
