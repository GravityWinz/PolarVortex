import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  StarBorder as StarBorderIcon,
  Star as StarIcon,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
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
  Paper,
  Snackbar,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import React, { useEffect, useState } from "react";
import {
  createPlotter,
  deletePlotter,
  getPlotters,
  updatePlotter,
} from "../services/apiService";

export default function PlotterConfiguration() {
  const [plotters, setPlotters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingPlotter, setEditingPlotter] = useState(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    width: 1000,
    height: 1000,
    pen_speed: 2000.0,
    gcode_pen_up_command: "M280 P0 S110",
    gcode_pen_down_command: "M280 P0 S130",
    gcode_on_connect: "",
    gcode_before_print: "",
    is_default: false,
  });

  const notifyPlotterConfigUpdated = () => {
    window.dispatchEvent(new Event("pv_plotter_config_updated"));
  };

  useEffect(() => {
    loadPlotters();
  }, []);

  const loadPlotters = async () => {
    try {
      setLoading(true);
      const response = await getPlotters();
      if (response.error) {
        setError(response.error);
      } else {
        setPlotters(response.plotters || []);
      }
    } catch (err) {
      setError("Failed to load plotters");
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingPlotter(null);
    setFormData({
      name: "",
      width: 1000,
      height: 1000,
      pen_speed: 2000.0,
      gcode_pen_up_command: "M280 P0 S110",
      gcode_pen_down_command: "M280 P0 S130",
      gcode_on_connect: "",
      gcode_before_print: "",
      is_default: false,
    });
    setDialogOpen(true);
  };

  const handleEdit = (plotter) => {
    setEditingPlotter(plotter);
    setFormData({
      name: plotter.name,
      width: plotter.width,
      height: plotter.height,
      pen_speed: plotter.pen_speed,
      gcode_pen_up_command:
        plotter.gcode_sequences?.pen_up_command || "M280 P0 S110",
      gcode_pen_down_command:
        plotter.gcode_sequences?.pen_down_command || "M280 P0 S130",
      gcode_on_connect: (plotter.gcode_sequences?.on_connect || []).join("\n"),
      gcode_before_print: (plotter.gcode_sequences?.before_print || []).join(
        "\n",
      ),
      is_default: plotter.is_default,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    try {
      const payload = {
        ...formData,
        gcode_sequences: {
          on_connect: (formData.gcode_on_connect || "")
            .split("\n")
            .map((s) => s.trim())
            .filter(Boolean),
          before_print: (formData.gcode_before_print || "")
            .split("\n")
            .map((s) => s.trim())
            .filter(Boolean),
          pen_up_command: formData.gcode_pen_up_command || "M280 P0 S110",
          pen_down_command: formData.gcode_pen_down_command || "M280 P0 S130",
        },
      };
      if (editingPlotter) {
        await updatePlotter(editingPlotter.id, payload);
        setSuccess("Plotter updated successfully");
      } else {
        await createPlotter(payload);
        setSuccess("Plotter created successfully");
      }
      setDialogOpen(false);
      notifyPlotterConfigUpdated();
      loadPlotters();
    } catch (err) {
      setError(err.message);
    }
  };

  const openDeleteDialog = (plotter) => {
    if (!plotter) return;
    setDeleteTarget(plotter);
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
      await deletePlotter(deleteTarget.id);
      setSuccess("Plotter deleted successfully");
      notifyPlotterConfigUpdated();
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
      loadPlotters();
    } catch (err) {
      setError(err.message);
    } finally {
      setDeleting(false);
    }
  };

  const handleSetDefault = async (plotter) => {
    try {
      await updatePlotter(plotter.id, { ...plotter, is_default: true });
      setSuccess(`"${plotter.name}" set as default`);
      notifyPlotterConfigUpdated();
      loadPlotters();
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="200px"
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        mb={3}
      >
        <Typography variant="h6">Plotter Configurations</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleCreate}
        >
          Add Plotter
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Dimensions (mm)</TableCell>
              <TableCell>Default</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {plotters.map((plotter) => (
              <TableRow key={plotter.id}>
                <TableCell>{plotter.name}</TableCell>
                <TableCell>
                  {plotter.width} × {plotter.height}
                </TableCell>
                <TableCell>
                  {plotter.is_default ? (
                    <Chip
                      icon={<StarIcon />}
                      label="Default"
                      color="primary"
                      size="small"
                    />
                  ) : (
                    <IconButton
                      size="small"
                      onClick={() => handleSetDefault(plotter)}
                      title="Set as default"
                    >
                      <StarBorderIcon />
                    </IconButton>
                  )}
                </TableCell>
                <TableCell>
                  <IconButton
                    size="small"
                    onClick={() => handleEdit(plotter)}
                    title="Edit"
                  >
                    <EditIcon />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => openDeleteDialog(plotter)}
                    title="Delete"
                    disabled={plotter.is_default}
                  >
                    <DeleteIcon />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Add/Edit Dialog */}
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {editingPlotter ? "Edit Plotter" : "Add New Plotter"}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            {/* Basic Information */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Basic Information
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Name"
                value={formData.name}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, name: e.target.value }))
                }
                required
              />
            </Grid>

            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
            </Grid>

            {/* Dimensions */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Dimensions
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Width (mm)"
                type="number"
                value={formData.width}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    width: parseFloat(e.target.value) || 0,
                  }))
                }
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Height (mm)"
                type="number"
                value={formData.height}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    height: parseFloat(e.target.value) || 0,
                  }))
                }
                required
              />
            </Grid>

            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
            </Grid>

            {/* Speed Settings */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Speed Settings
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Pen Speed (mm/min)"
                type="number"
                value={formData.pen_speed}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    pen_speed: parseFloat(e.target.value) || 0,
                  }))
                }
                required
              />
            </Grid>

            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
            </Grid>

            {/* Pen Settings */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Pen Settings
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Pen Up Command"
                value={formData.gcode_pen_up_command}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    gcode_pen_up_command: e.target.value,
                  }))
                }
                helperText="Command sent to raise the pen (e.g., servo angle)"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Pen Down Command"
                value={formData.gcode_pen_down_command}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    gcode_pen_down_command: e.target.value,
                  }))
                }
                helperText="Command sent to lower the pen"
              />
            </Grid>

            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
            </Grid>

            {/* Automatic G-code */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Automatic G-code
              </Typography>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Commands run automatically for this plotter. One command per
                line; empty lines are ignored.
              </Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                multiline
                minRows={6}
                label="On Connect"
                value={formData.gcode_on_connect}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    gcode_on_connect: e.target.value,
                  }))
                }
                placeholder="G21&#10;G90"
                helperText="Sent immediately after connecting to the plotter."
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                multiline
                minRows={6}
                label="Before Print Start"
                value={formData.gcode_before_print}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    gcode_before_print: e.target.value,
                  }))
                }
                placeholder="G92 X0 Y0 Z0"
                helperText="Sent right before a print job begins."
              />
            </Grid>

            <Grid item xs={12}>
              <FormControl>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={formData.is_default}
                      onChange={(e) =>
                        setFormData((prev) => ({
                          ...prev,
                          is_default: e.target.checked,
                        }))
                      }
                    />
                  }
                  label="Set as default plotter"
                />
                <FormHelperText>
                  Used as the default selection for new projects.
                </FormHelperText>
              </FormControl>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSave} variant="contained">
            {editingPlotter ? "Update" : "Create"}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={deleteDialogOpen}
        onClose={closeDeleteDialog}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Delete plotter?</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            {deleteTarget
              ? `Delete "${deleteTarget.name}"?`
              : "Delete this plotter?"}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeDeleteDialog} disabled={deleting}>
            Cancel
          </Button>
          <Button
            onClick={handleDelete}
            color="error"
            variant="contained"
            disabled={deleting}
          >
            {deleting ? "Deleting..." : "Delete"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={!!error}
        autoHideDuration={6000}
        onClose={() => setError(null)}
      >
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      </Snackbar>

      <Snackbar
        open={!!success}
        autoHideDuration={4000}
        onClose={() => setSuccess(null)}
      >
        <Alert severity="success" onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      </Snackbar>
    </Box>
  );
}
