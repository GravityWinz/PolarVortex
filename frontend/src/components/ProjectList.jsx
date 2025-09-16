import {
    Add as AddIcon,
    CloudUpload as CloudUploadIcon,
    Delete as DeleteIcon,
    Edit as EditIcon,
    Folder as FolderIcon,
    AutoGraph as VectorizeIcon
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
import { createProject, deleteProject, getProjectThumbnailUrl, getProjects, uploadImageToProject } from "../services/apiService";
import VectorizeDialog from "./VectorizeDialog";

/**
 * ProjectList component for displaying and managing projects
 * Shows all projects in a grid layout with project management actions
 */
export default function ProjectList({ onProjectSelect }) {
    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [createDialogOpen, setCreateDialogOpen] = useState(false);
    const [newProjectName, setNewProjectName] = useState("");
    const [creating, setCreating] = useState(false);
    const [uploadingProjects, setUploadingProjects] = useState(new Set());
    const [uploadProgress, setUploadProgress] = useState({});
    const [failedThumbnails, setFailedThumbnails] = useState(new Set());
    const [vectorizeDialogOpen, setVectorizeDialogOpen] = useState(false);
    const [selectedProjectForVectorize, setSelectedProjectForVectorize] = useState(null);

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
            setProjects(prev => [newProject, ...prev]);
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
        if (!window.confirm("Are you sure you want to delete this project? This will also delete any associated images.")) {
            return;
        }

        try {
            await deleteProject(projectId);
            setProjects(prev => prev.filter(p => p.id !== projectId));
        } catch (err) {
            setError("Failed to delete project");
            console.error("Error deleting project:", err);
        }
    };

    const handleProjectSelect = (project) => {
        if (onProjectSelect) {
            onProjectSelect(project);
        }
    };


    const handleFileUpload = async (project, file) => {
        if (!file) return;

        // Validate file
        if (!file.type.startsWith("image/")) {
            setError("Please select a valid image file");
            return;
        }

        if (file.size > 10 * 1024 * 1024) {
            setError("File size must be less than 10MB");
            return;
        }

        try {
            // Add project to uploading set
            setUploadingProjects(prev => new Set([...prev, project.id]));
            setUploadProgress(prev => ({ ...prev, [project.id]: 0 }));

            // Create form data
            const formData = new FormData();
            formData.append("file", file);
            formData.append("settings", JSON.stringify({
                threshold: 128,
                invert: false,
                dither: true,
                resolution: "medium"
            }));

            // Upload file
            const response = await uploadImageToProject(project.id, formData);

            // Update progress
            setUploadProgress(prev => ({ ...prev, [project.id]: 100 }));

            // Refresh projects list
            await fetchProjects();

            // Clear uploading state
            setUploadingProjects(prev => {
                const newSet = new Set(prev);
                newSet.delete(project.id);
                return newSet;
            });
            setUploadProgress(prev => {
                const newProgress = { ...prev };
                delete newProgress[project.id];
                return newProgress;
            });

        } catch (err) {
            setError("Failed to upload image");
            console.error("Error uploading image:", err);
            
            // Clear uploading state
            setUploadingProjects(prev => {
                const newSet = new Set(prev);
                newSet.delete(project.id);
                return newSet;
            });
            setUploadProgress(prev => {
                const newProgress = { ...prev };
                delete newProgress[project.id];
                return newProgress;
            });
        }
    };

    const formatDate = (dateString) => {
        return new Date(dateString).toLocaleDateString();
    };

    const handleThumbnailError = (projectId) => {
        setFailedThumbnails(prev => new Set([...prev, projectId]));
    };

    const handleVectorizeProject = (project) => {
        setSelectedProjectForVectorize(project);
        setVectorizeDialogOpen(true);
    };

    const handleCloseVectorizeDialog = () => {
        setVectorizeDialogOpen(false);
        setSelectedProjectForVectorize(null);
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

    return (
        <Box sx={{ p: 2 }}>
            {/* Header with Logo */}
            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 3 }}>
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
                    startIcon={<AddIcon />}
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
                        startIcon={<AddIcon />}
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
                                    transition: "transform 0.2s, box-shadow 0.2s",
                                    "&:hover": {
                                        transform: "translateY(-4px)",
                                        boxShadow: 4,
                                    },
                                }}
                                onClick={(e) => {
                                    // Only handle project selection if not clicking on the upload area
                                    if (e.target.closest('[data-upload-area]')) {
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
                                        if (!uploadingProjects.has(project.id)) {
                                            document.getElementById(`file-input-${project.id}`).click();
                                        }
                                    }}
                                >
                                    <input
                                        id={`file-input-${project.id}`}
                                        type="file"
                                        accept="image/*"
                                        onChange={(e) => {
                                            const file = e.target.files[0];
                                            if (file) {
                                                handleFileUpload(project, file);
                                            }
                                        }}
                                        style={{ display: "none" }}
                                        disabled={uploadingProjects.has(project.id)}
                                    />
                                    
                                    {uploadingProjects.has(project.id) ? (
                                        <Box sx={{ textAlign: "center", width: "100%", position: "absolute", zIndex: 2 }}>
                                            <CircularProgress size={40} sx={{ mb: 1 }} />
                                            <Typography variant="body2" color="text.secondary">
                                                Uploading...
                                            </Typography>
                                            <LinearProgress 
                                                variant="determinate" 
                                                value={uploadProgress[project.id] || 0}
                                                sx={{ mt: 1, width: "80%" }}
                                            />
                                        </Box>
                                    ) : (
                                        <Box sx={{ position: "relative", width: "100%", height: "100%" }}>
                                            {project.thumbnail_image && !failedThumbnails.has(project.id) ? (
                                                // Show actual thumbnail if it exists and hasn't failed
                                                <>
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
                                                        onError={() => handleThumbnailError(project.id)}
                                                    />
                                                    <Box
                                                        sx={{
                                                            position: "absolute",
                                                            top: 0,
                                                            left: 0,
                                                            right: 0,
                                                            bottom: 0,
                                                            backgroundColor: "rgba(0, 0, 0, 0.3)",
                                                            display: "flex",
                                                            alignItems: "center",
                                                            justifyContent: "center",
                                                            opacity: 0,
                                                            transition: "opacity 0.2s",
                                                            "&:hover": {
                                                                opacity: 1,
                                                            },
                                                        }}
                                                    >
                                                        <CloudUploadIcon sx={{ fontSize: 32, color: "white" }} />
                                                    </Box>
                                                </>
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
                                                </Box>
                                            )}
                                        </Box>
                                    )}
                                </CardMedia>
                                
                                <CardContent sx={{ flexGrow: 1, p: 2 }}>
                                    <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 1 }}>
                                        <Typography variant="subtitle2" component="div" noWrap sx={{ maxWidth: "70%" }}>
                                            {project.name}
                                        </Typography>
                                        <Chip
                                            label={project.thumbnail_image ? "Has Image" : "Empty"}
                                            color={project.thumbnail_image ? "success" : "default"}
                                            size="small"
                                        />
                                    </Box>
                                    
                                    <Typography variant="caption" color="text.secondary" display="block">
                                        Created: {formatDate(project.created_at)}
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
                                        
                                        {project.source_image && (
                                        <IconButton
                                            size="small"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                    handleVectorizeProject(project);
                                            }}
                                                sx={{ color: "secondary.main" }}
                                                title="Vectorize Image"
                                        >
                                                <VectorizeIcon />
                                        </IconButton>
                                        )}
                                        
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
                            if (e.key === 'Enter') {
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

            {/* Vectorization Dialog */}
            <VectorizeDialog
                open={vectorizeDialogOpen}
                onClose={handleCloseVectorizeDialog}
                project={selectedProjectForVectorize}
            />
        </Box>
    );
}
