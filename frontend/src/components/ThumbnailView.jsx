import {
    Delete as DeleteIcon,
    Download as DownloadIcon,
    Edit as EditIcon,
    PlayArrow as PlayIcon,
} from "@mui/icons-material";
import {
    Alert,
    Box,
    Button,
    Card,
    CardContent,
    CardMedia,
    Chip,
    CircularProgress,
    Grid,
    IconButton,
    Paper,
    Typography,
} from "@mui/material";
import React, { useEffect, useState } from "react";
import logoImage from "../assets/PolarVortexLogo_small.png";

/**
 * ThumbnailView component for displaying uploaded images
 * Shows thumbnails of all uploaded images in a grid layout
 */
export default function ThumbnailView({ onImageSelect }) {
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Mock data for demonstration - replace with actual API call
  useEffect(() => {
    const fetchImages = async () => {
      try {
        setLoading(true);
        // TODO: Replace with actual API call to backend
        // const response = await fetch('/api/projects');
        // const data = await response.json();
        
        // Note: When backend is configured to serve static files, use:
        // thumbnail: "http://localhost:8000/projects/dog/thumb_dog.png"
        // original: "http://localhost:8000/projects/dog/dog.jpg"
        
        // Mock data for now
        const mockImages = [
          {
            id: 1,
            name: "dog.jpg",
            thumbnail: "https://via.placeholder.com/200x200/f0f0f0/666666?text=Dog+Image",
            original: "https://via.placeholder.com/400x300/f0f0f0/666666?text=Dog+Original",
            processed: "https://via.placeholder.com/400x300/e8f5e8/2e7d32?text=Dog+Processed",
            status: "processed",
            uploadDate: "2024-01-15",
          },
          {
            id: 2,
            name: "wheaton.jfif",
            thumbnail: "https://via.placeholder.com/200x200/f0f0f0/666666?text=Wheaton+Image",
            original: "https://via.placeholder.com/400x300/f0f0f0/666666?text=Wheaton+Original",
            processed: "https://via.placeholder.com/400x300/e8f5e8/2e7d32?text=Wheaton+Processed",
            status: "processed",
            uploadDate: "2024-01-14",
          },
          {
            id: 3,
            name: "Recipe.PNG",
            thumbnail: "https://via.placeholder.com/200x200/f0f0f0/666666?text=Recipe+Image",
            original: "https://via.placeholder.com/400x300/f0f0f0/666666?text=Recipe+Original",
            processed: null,
            status: "uploaded",
            uploadDate: "2024-01-13",
          },
        ];
        
        setImages(mockImages);
        setLoading(false);
      } catch (err) {
        setError("Failed to load images");
        setLoading(false);
      }
    };

    fetchImages();
  }, []);

  const handleImageSelect = (image) => {
    if (onImageSelect) {
      onImageSelect(image);
    }
  };

  const handleDelete = async (imageId) => {
    try {
      // TODO: Implement actual delete API call
      // await fetch(`/api/projects/${imageId}`, { method: 'DELETE' });
      setImages(images.filter(img => img.id !== imageId));
    } catch (err) {
      console.error("Failed to delete image:", err);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "processed":
        return "success";
      case "processing":
        return "warning";
      case "uploaded":
        return "info";
      default:
        return "default";
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case "processed":
        return "Ready";
      case "processing":
        return "Processing";
      case "uploaded":
        return "Uploaded";
      default:
        return "Unknown";
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        {error}
      </Alert>
    );
  }

  if (images.length === 0) {
    return (
      <Paper sx={{ p: 4, textAlign: "center", mt: 2 }}>
        <Typography variant="h6" color="text.secondary" gutterBottom>
          No images uploaded yet
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          Upload your first image to get started with plotting
        </Typography>
        <Button variant="contained" color="primary">
          Upload Image
        </Button>
      </Paper>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      {/* Header with Logo */}
      <Box sx={{ display: "flex", alignItems: "center", mb: 3 }}>
        <img 
          src={logoImage} 
          alt="PolarVortex Logo" 
          style={{ height: "32px", width: "auto", marginRight: "12px" }} 
        />
        <Typography variant="h5" gutterBottom sx={{ mb: 0 }}>
          Uploaded Images ({images.length})
        </Typography>
      </Box>
      
      <Grid container spacing={3}>
        {images.map((image) => (
          <Grid item xs={12} sm={6} md={4} lg={3} key={image.id}>
            <Card
              sx={{
                height: "100%",
                display: "flex",
                flexDirection: "column",
                cursor: "pointer",
                transition: "transform 0.2s, box-shadow 0.2s",
                "&:hover": {
                  transform: "translateY(-4px)",
                  boxShadow: 4,
                },
              }}
              onClick={() => handleImageSelect(image)}
            >
              <CardMedia
                component="img"
                height="200"
                image={image.thumbnail}
                alt={image.name}
                sx={{ objectFit: "cover" }}
              />
              
              <CardContent sx={{ flexGrow: 1, p: 2 }}>
                <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 1 }}>
                  <Typography variant="subtitle2" component="div" noWrap sx={{ maxWidth: "70%" }}>
                    {image.name}
                  </Typography>
                  <Chip
                    label={getStatusText(image.status)}
                    color={getStatusColor(image.status)}
                    size="small"
                  />
                </Box>
                
                <Typography variant="caption" color="text.secondary" display="block">
                  Uploaded: {new Date(image.uploadDate).toLocaleDateString()}
                </Typography>
                
                <Box sx={{ display: "flex", justifyContent: "space-between", mt: 2 }}>
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleImageSelect(image);
                    }}
                    sx={{ color: "primary.main" }}
                  >
                    <EditIcon />
                  </IconButton>
                  
                  {image.processed && (
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        // TODO: Implement plot action
                      }}
                      sx={{ color: "success.main" }}
                    >
                      <PlayIcon />
                    </IconButton>
                  )}
                  
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      // TODO: Implement download action
                    }}
                    sx={{ color: "info.main" }}
                  >
                    <DownloadIcon />
                  </IconButton>
                  
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(image.id);
                    }}
                    sx={{ color: "error.main" }}
                  >
                    <DeleteIcon />
                  </IconButton>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
