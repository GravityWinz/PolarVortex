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
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
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
  getProjects,
  updateProject
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
  const [contextMenu, setContextMenu] = useState(null);
  const [contextProject, setContextProject] = useState(null);
  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [renameValue, setRenameValue] = useState("");
  const [renameError, setRenameError] = useState("");
  const [renaming, setRenaming] = useState(false);

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

  const handleOpenContextMenu = (event, project) => {
    event.preventDefault();
    setContextProject(project);
    setContextMenu({
      mouseX: event.clientX + 2,
      mouseY: event.clientY - 6,
    });
  };

  const handleCloseContextMenu = () => {
    setContextMenu(null);
  };

  const openRenameDialog = (project) => {
    if (!project) return;
    setRenameValue(project.name || "");
    setRenameError("");
    setRenameDialogOpen(true);
    handleCloseContextMenu();
  };

  const closeRenameDialog = () => {
    if (renaming) return;
    setRenameDialogOpen(false);
    setRenameError("");
  };

  const handleRenameProject = async () => {
    if (!contextProject) return;
    const trimmed = renameValue.trim();
    if (!trimmed) {
      setRenameError("Project name is required.");
      return;
    }
    if (trimmed === contextProject.name) {
      setRenameDialogOpen(false);
      return;
    }
    try {
      setRenaming(true);
      const updated = await updateProject(contextProject.id, { name: trimmed });
      setProjects((prev) =>
        prev.map((project) =>
          project.id === updated.id ? updated : project
        )
      );
      if (currentProject?.id === updated.id && onSetCurrentProject) {
        onSetCurrentProject(updated);
      }
      setRenameDialogOpen(false);
    } catch (err) {
      setRenameError("Failed to rename project");
      console.error("Error renaming project:", err);
    } finally {
      setRenaming(false);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString();
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
                onClick={() => {
                  handleProjectSelect(project);
                }}
                onContextMenu={(event) => handleOpenContextMenu(event, project)}
              >
                <Box
                  sx={{
                    px: 2,
                    pt: 2,
                    pb: 1,
                    textAlign: "center",
                  }}
                >
                  <Typography variant="subtitle1" component="div" noWrap>
                    {project.name}
                  </Typography>
                </Box>
                <CardMedia
                  component="div"
                  sx={{
                    height: 170,
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
                >
                  {project.thumbnail_image ? (
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
                      justifyContent: "flex-end",
                      alignItems: "center",
                      mt: 2,
                    }}
                  >
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

      <Menu
        open={contextMenu !== null}
        onClose={handleCloseContextMenu}
        anchorReference="anchorPosition"
        anchorPosition={
          contextMenu !== null
            ? { top: contextMenu.mouseY, left: contextMenu.mouseX }
            : undefined
        }
      >
        <MenuItem onClick={() => openRenameDialog(contextProject)} disabled={!contextProject}>
          <ListItemIcon>
            <FolderIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Rename</ListItemText>
        </MenuItem>
        <MenuItem
          onClick={() => {
            handleCloseContextMenu();
            if (contextProject) {
              handleDeleteProject(contextProject.id);
            }
          }}
          disabled={!contextProject}
        >
          <ListItemIcon>
            <DeleteIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Delete</ListItemText>
        </MenuItem>
      </Menu>

      <Dialog open={renameDialogOpen} onClose={closeRenameDialog} maxWidth="xs" fullWidth>
        <DialogTitle>Rename Project</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Project Name"
            fullWidth
            variant="outlined"
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            error={Boolean(renameError)}
            helperText={renameError || " "}
            disabled={renaming}
            onKeyPress={(e) => {
              if (e.key === "Enter") {
                handleRenameProject();
              }
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={closeRenameDialog} disabled={renaming}>
            Cancel
          </Button>
          <Button onClick={handleRenameProject} variant="contained" disabled={renaming}>
            {renaming ? "Renaming..." : "Rename"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
