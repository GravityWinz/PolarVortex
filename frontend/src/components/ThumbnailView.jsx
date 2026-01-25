import {
    CloudUpload as CloudUploadIcon,
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
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    Grid,
    IconButton,
    Paper,
    Typography,
} from "@mui/material";
import React, { useEffect, useState } from "react";
import logoImage from "../assets/PolarVortexLogo_small.png";
import { deleteProject, getProjectThumbnailUrl, getProjects } from "../services/apiService";

/**
 * ThumbnailView component for displaying projects with their images
 * Shows thumbnails of all projects in a grid layout
 */
export default function ThumbnailView({ onProjectSelect }) {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [failedThumbnails, setFailedThumbnails] = useState(new Set());
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  // Fetch projects from API
  useEffect(() => {
    const fetchProjects = async () => {
      try {
        setLoading(true);
        const response = await getProjects();
        if (response.error) {
          setError(response.error);
        } else {
          // Filter projects that have thumbnails
          const projectsWithImages = (response.projects || []).filter(project => project.thumbnail_image);
          setProjects(projectsWithImages);
        }
        setLoading(false);
      } catch (err) {
        setError("Failed to load projects");
        setLoading(false);
      }
    };

    fetchProjects();
  }, []);

  const handleProjectSelect = (project) => {
    if (onProjectSelect) {
      onProjectSelect(project);
    }
  };

  const openDeleteDialog = (project) => {
    if (!project) return;
    setDeleteTarget(project);
    setDeleteDialogOpen(true);
  };

  const closeDeleteDialog = () => {
    if (deleting) return;
    setDeleteDialogOpen(false);
    setDeleteTarget(null);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      setDeleting(true);
      await deleteProject(deleteTarget.id);
      setProjects(projects.filter(project => project.id !== deleteTarget.id));
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
    } catch (err) {
      setError("Failed to delete project");
      console.error("Failed to delete project:", err);
    } finally {
      setDeleting(false);
    }
  };

  const getStatusColor = (project) => {
    // Determine status based on project data
    if (project.thumbnail_image) {
      return "success";
    }
    return "default";
  };

  const getStatusText = (project) => {
    // Determine status text based on project data
    if (project.thumbnail_image) {
      return "Ready";
    }
    return "Empty";
  };

  const handleThumbnailError = (projectId) => {
    setFailedThumbnails(prev => new Set([...prev, projectId]));
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

  if (projects.length === 0) {
    return (
      <Paper sx={{ p: 4, textAlign: "center", mt: 2 }}>
        <Typography variant="h6" color="text.secondary" gutterBottom>
          No projects with images yet
        </Typography>
        <Typography variant="body2" color="text.secondary" paragraph>
          Create a project and upload an image to get started with plotting
        </Typography>
        <Button variant="contained" color="primary">
          Create Project
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
          Projects with Images ({projects.length})
        </Typography>
      </Box>
      
      <Grid container spacing={3}>
        {projects.map((project) => (
          <Grid item xs={12} sm={6} md={4} lg={3} key={project.id}>
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
              onClick={() => handleProjectSelect(project)}
            >
              <CardMedia
                component="div"
                height="200"
                sx={{ 
                  objectFit: "cover",
                  position: "relative",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  backgroundColor: "grey.100"
                }}
              >
                {project.thumbnail_image && !failedThumbnails.has(project.id) ? (
                  // Show actual thumbnail if it exists and hasn't failed
                  <img
                    src={getProjectThumbnailUrl(project.id)}
                    alt={project.name}
                    style={{
                      width: "100%",
                      height: "100%",
                      objectFit: "cover",
                      position: "absolute",
                      top: 0,
                      left: 0,
                    }}
                    onError={() => handleThumbnailError(project.id)}
                  />
                ) : (
                  // Show watermark for projects without thumbnails or failed thumbnails
                  <>
                    {/* Watermark background */}
                    <img
                      src={logoImage}
                      alt="PolarVortex Watermark"
                      style={{
                        width: "60%",
                        height: "60%",
                        objectFit: "contain",
                        opacity: 0.3,
                        filter: "grayscale(100%)",
                      }}
                    />
                    
                    {/* Upload placeholder overlay */}
                    <Box
                      sx={{
                        position: "absolute",
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center",
                        backgroundColor: "rgba(255, 255, 255, 0.8)",
                        backdropFilter: "blur(2px)",
                      }}
                    >
                      <CloudUploadIcon sx={{ fontSize: 48, color: "text.secondary", mb: 1 }} />
                      <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center" }}>
                        Click to upload image
                      </Typography>
                    </Box>
                  </>
                )}
              </CardMedia>
              
              <CardContent sx={{ flexGrow: 1, p: 2 }}>
                <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 1 }}>
                  <Typography variant="subtitle2" component="div" noWrap sx={{ maxWidth: "70%" }}>
                    {project.name}
                  </Typography>
                  <Chip
                    label={getStatusText(project)}
                    color={getStatusColor(project)}
                    size="small"
                  />
                </Box>
                
                <Typography variant="caption" color="text.secondary" display="block">
                  Created: {new Date(project.created_at).toLocaleDateString()}
                </Typography>
                
                <Box sx={{ display: "flex", justifyContent: "space-between", mt: 2 }}>
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleProjectSelect(project);
                    }}
                    sx={{ color: "primary.main" }}
                  >
                    <EditIcon />
                  </IconButton>
                  
                  {project.thumbnail_image && (
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
                      openDeleteDialog(project);
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

      <Dialog open={deleteDialogOpen} onClose={closeDeleteDialog} maxWidth="xs" fullWidth>
        <DialogTitle>Delete project?</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            {deleteTarget
              ? `Delete "${deleteTarget.name}"? This will also delete any associated images.`
              : "Delete this project and its associated images?"}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeDeleteDialog} disabled={deleting}>
            Cancel
          </Button>
          <Button onClick={handleDelete} color="error" variant="contained" disabled={deleting}>
            {deleting ? "Deleting..." : "Delete"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
