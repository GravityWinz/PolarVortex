import {
  Delete as DeleteIcon,
  Folder as FolderIcon
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
  LinearProgress,
  Paper,
  TextField,
  Typography,
} from "@mui/material";
import React, { useEffect, useState } from "react";
import logoImage from "../assets/PolarVortexLogo_small.png";
import {
  createProject,
  deleteProject,
  getProjectThumbnailUrl,
  getProjects
} from "../services/apiService";

/**
 * ProjectList component for displaying and managing projects
 * Shows all projects in a grid layout with project management actions
 */
export default function ProjectList({
  onProjectSelect,
  currentProject,
  onSetCurrentProject,
  onNavigate,
}) {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [creating, setCreating] = useState(false);

  // Fetch projects from API
  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const response = await getProjects();
      if (response.error) {
        setError(response.error);
      } else {
        setProjects(response.projects || []);
      }
    } catch (err) {
      setError("Failed to load projects");
      console.error("Error fetching projects:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) return;

    try {
      setCreating(true);
      const newProject = await createProject({ name: newProjectName.trim() });
      setProjects((prev) => [newProject, ...prev]);
      setNewProjectName("");
      setCreateDialogOpen(false);
    } catch (err) {
      setError("Failed to create project");
      console.error("Error creating project:", err);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteProject = async (projectId) => {
    if (
      !window.confirm(
        "Are you sure you want to delete this project? This will also delete any associated images."
      )
    ) {
      return;
    }

    try {
      await deleteProject(projectId);
      setProjects((prev) => prev.filter((p) => p.id !== projectId));
    } catch (err) {
      setError("Failed to delete project");
      console.error("Error deleting project:", err);
    }
  };

  const handleProjectSelect = (project) => {
    if (onSetCurrentProject) {
      onSetCurrentProject(project);
    }
    if (onProjectSelect) {
      onProjectSelect(project);
    }
    if (onNavigate) {
      onNavigate("edit");
    }
  };

  if (loading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="400px"
      >
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

  return (
    <Box sx={{ p: 2 }}>
      {/* Header with Logo */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          mb: 3,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center" }}>
          <img
            src={logoImage}
            alt="PolarVortex Logo"
            style={{ height: "32px", width: "auto", marginRight: "12px" }}
          />
          <Typography variant="h5" gutterBottom sx={{ mb: 0 }}>
            Projects ({projects.length})
          </Typography>
        </Box>
        <Button
          variant="contained"
          onClick={() => setCreateDialogOpen(true)}
        >
          New Project
        </Button>
      </Box>

      {projects.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: "center", mt: 2 }}>
          <FolderIcon sx={{ fontSize: 64, color: "text.secondary", mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No projects yet
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            Create your first project to start uploading and processing images
          </Typography>
          <Button
            variant="contained"
            onClick={() => setCreateDialogOpen(true)}
          >
            Create Project
          </Button>
        </Paper>
      ) : (
        <Grid container spacing={3}>
          {projects.map((project) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={project.id}>
              <Card
                sx={{
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                  cursor: "pointer",
                  transition:
                    "transform 0.2s, box-shadow 0.2s, border-color 0.2s",
                  border:
                    currentProject?.id === project.id
                      ? "2px solid"
                      : "1px solid",
                  borderColor:
                    currentProject?.id === project.id
                      ? "primary.main"
                      : "divider",
                  boxShadow: currentProject?.id === project.id ? 6 : 1,
                  "&:hover": {
                    transform: "translateY(-4px)",
                    boxShadow: 4,
                  },
                }}
                onClick={(e) => {
                  // Only handle project selection if not clicking on the upload area
                  if (e.target.closest("[data-upload-area]")) {
                    return;
                  }
                  handleProjectSelect(project);
                }}
              >
                <CardMedia
                  component="div"
                  data-upload-area
                  sx={{
                    height: 200,
                    backgroundColor: "grey.100",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexDirection: "column",
                    position: "relative",
                    cursor: "pointer",
                    overflow: "hidden",
                    "&:hover": {
                      backgroundColor: "grey.200",
                    },
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    // If project has a thumbnail, navigate to project instead of uploading
                    if (project.thumbnail_image && !failedThumbnails.has(project.id)) {
                      handleProjectSelect(project);
                    }
                  }}
                >
                  {project.thumbnail_image &&
                  !failedThumbnails.has(project.id) ? (
                    // Show actual thumbnail if it exists and hasn't failed
                    <img
                      src={getProjectThumbnailUrl(project.id)}
                      alt={`${project.name} thumbnail`}
                      style={{
                        width: "100%",
                        height: "100%",
                        objectFit: "cover",
                        position: "absolute",
                        top: 0,
                        left: 0,
                        cursor: "pointer",
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleProjectSelect(project);
                      }}
                    />
                  ) : (
                    // Show watermark for projects without thumbnails or failed thumbnails
                    <Box
                      sx={{
                        width: "100%",
                        height: "100%",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        backgroundColor: "grey.100",
                        position: "relative",
                      }}
                    >
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
                    </Box>
                  )}
                </CardMedia>

                <CardContent sx={{ flexGrow: 1, p: 2 }}>
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      mb: 1,
                    }}
                  >
                    <Typography
                      variant="subtitle2"
                      component="div"
                      noWrap
                      sx={{ maxWidth: "70%" }}
                    >
                      {project.name}
                    </Typography>
                    <Box sx={{ display: "flex", gap: 0.5 }}>
                      <Chip
                        label={project.thumbnail_image ? "Has Image" : "Empty"}
                        color={project.thumbnail_image ? "success" : "default"}
                        size="small"
                      />
                      <Chip
                        label={`G-code ${project.gcode_files?.length || 0}`}
                        color={
                          (project.gcode_files?.length || 0) > 0
                            ? "primary"
                            : "default"
                        }
                        size="small"
                      />
                    </Box>
                  </Box>

                  <Typography
                    variant="caption"
                    color="text.secondary"
                    display="block"
                  >
                    Created: {formatDate(project.created_at)}
                  </Typography>

                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      mt: 2,
                      gap: 1,
                      flexWrap: "wrap",
                    }}
                  >
                    <Button
                      variant={
                        currentProject?.id === project.id
                          ? "contained"
                          : "outlined"
                      }
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleProjectSelect(project);
                      }}
                      sx={{ textTransform: "none" }}
                    >
                      {currentProject?.id === project.id
                        ? "Current"
                        : "Set Current"}
                    </Button>

                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteProject(project.id);
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
      )}

      {/* Create Project Dialog */}
      <Dialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create New Project</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Project Name"
            fullWidth
            variant="outlined"
            value={newProjectName}
            onChange={(e) => setNewProjectName(e.target.value)}
            disabled={creating}
            onKeyPress={(e) => {
              if (e.key === "Enter") {
                handleCreateProject();
              }
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setCreateDialogOpen(false)}
            disabled={creating}
          >
            Cancel
          </Button>
          <Button
            onClick={handleCreateProject}
            variant="contained"
            disabled={!newProjectName.trim() || creating}
          >
            {creating ? "Creating..." : "Create"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
