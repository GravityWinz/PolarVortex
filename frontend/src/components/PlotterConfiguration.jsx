import {
    Add as AddIcon,
    Delete as DeleteIcon,
    Edit as EditIcon,
    StarBorder as StarBorderIcon,
    Star as StarIcon,
} from '@mui/icons-material';
import {
    Alert,
    Box,
    Button,
    Chip,
    CircularProgress,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    Divider,
    FormControl,
    Grid,
    IconButton,
    InputLabel,
    MenuItem,
    Paper,
    Select,
    Snackbar,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    TextField,
    Typography
} from '@mui/material';
import React, { useEffect, useState } from 'react';
import {
    createPlotter,
    deletePlotter,
    getPlotters,
    updatePlotter
} from '../services/apiService';

const PLOTTER_TYPES = [
  { value: 'polargraph', label: 'Polargraph' },
  { value: 'xy_plotter', label: 'XY Plotter' },
  { value: 'pen_plotter', label: 'Pen Plotter' },
];

export default function PlotterConfiguration() {
  const [plotters, setPlotters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingPlotter, setEditingPlotter] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    plotter_type: 'polargraph',
    width: 1000,
    height: 1000,
    mm_per_rev: 95.0,
    steps_per_rev: 200.0,
    max_speed: 100.0,
    acceleration: 50.0,
    pen_up_position: 10.0,
    pen_down_position: 0.0,
    pen_speed: 20.0,
    home_position_x: 0.0,
    home_position_y: 0.0,
    is_default: false,
  });

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
      setError('Failed to load plotters');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingPlotter(null);
    setFormData({
      name: '',
      plotter_type: 'polargraph',
      width: 1000,
      height: 1000,
      mm_per_rev: 95.0,
      steps_per_rev: 200.0,
      max_speed: 100.0,
      acceleration: 50.0,
      pen_up_position: 10.0,
      pen_down_position: 0.0,
      pen_speed: 20.0,
      home_position_x: 0.0,
      home_position_y: 0.0,
      is_default: false,
    });
    setDialogOpen(true);
  };

  const handleEdit = (plotter) => {
    setEditingPlotter(plotter);
    setFormData({
      name: plotter.name,
      plotter_type: plotter.plotter_type,
      width: plotter.width,
      height: plotter.height,
      mm_per_rev: plotter.mm_per_rev,
      steps_per_rev: plotter.steps_per_rev,
      max_speed: plotter.max_speed,
      acceleration: plotter.acceleration,
      pen_up_position: plotter.pen_up_position,
      pen_down_position: plotter.pen_down_position,
      pen_speed: plotter.pen_speed,
      home_position_x: plotter.home_position_x,
      home_position_y: plotter.home_position_y,
      is_default: plotter.is_default,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    try {
      if (editingPlotter) {
        await updatePlotter(editingPlotter.id, formData);
        setSuccess('Plotter updated successfully');
      } else {
        await createPlotter(formData);
        setSuccess('Plotter created successfully');
      }
      setDialogOpen(false);
      loadPlotters();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (plotter) => {
    if (window.confirm(`Are you sure you want to delete "${plotter.name}"?`)) {
      try {
        await deletePlotter(plotter.id);
        setSuccess('Plotter deleted successfully');
        loadPlotters();
      } catch (err) {
        setError(err.message);
      }
    }
  };

  const handleSetDefault = async (plotter) => {
    try {
      await updatePlotter(plotter.id, { ...plotter, is_default: true });
      setSuccess(`"${plotter.name}" set as default`);
      loadPlotters();
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
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
              <TableCell>Type</TableCell>
              <TableCell>Dimensions (mm)</TableCell>
              <TableCell>Motor Settings</TableCell>
              <TableCell>Default</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {plotters.map((plotter) => (
              <TableRow key={plotter.id}>
                <TableCell>{plotter.name}</TableCell>
                <TableCell>
                  <Chip label={plotter.plotter_type} size="small" />
                </TableCell>
                <TableCell>{plotter.width} × {plotter.height}</TableCell>
                <TableCell>
                  {plotter.mm_per_rev}mm/rev, {plotter.steps_per_rev} steps/rev
                </TableCell>
                <TableCell>
                  {plotter.is_default ? (
                    <Chip icon={<StarIcon />} label="Default" color="primary" size="small" />
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
                    onClick={() => handleDelete(plotter)}
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
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingPlotter ? 'Edit Plotter' : 'Add New Plotter'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            {/* Basic Information */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>Basic Information</Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Name"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Plotter Type</InputLabel>
                <Select
                  value={formData.plotter_type}
                  onChange={(e) => setFormData(prev => ({ ...prev, plotter_type: e.target.value }))}
                  label="Plotter Type"
                >
                  {PLOTTER_TYPES.map((type) => (
                    <MenuItem key={type.value} value={type.value}>
                      {type.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
            </Grid>

            {/* Dimensions */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>Dimensions</Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Width (mm)"
                type="number"
                value={formData.width}
                onChange={(e) => setFormData(prev => ({ ...prev, width: parseFloat(e.target.value) || 0 }))}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Height (mm)"
                type="number"
                value={formData.height}
                onChange={(e) => setFormData(prev => ({ ...prev, height: parseFloat(e.target.value) || 0 }))}
                required
              />
            </Grid>

            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
            </Grid>

            {/* Motor Settings */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>Motor Settings</Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="mm per revolution"
                type="number"
                value={formData.mm_per_rev}
                onChange={(e) => setFormData(prev => ({ ...prev, mm_per_rev: parseFloat(e.target.value) || 0 }))}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Steps per revolution"
                type="number"
                value={formData.steps_per_rev}
                onChange={(e) => setFormData(prev => ({ ...prev, steps_per_rev: parseFloat(e.target.value) || 0 }))}
                required
              />
            </Grid>

            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
            </Grid>

            {/* Speed Settings */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>Speed Settings</Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Max Speed (mm/s)"
                type="number"
                value={formData.max_speed}
                onChange={(e) => setFormData(prev => ({ ...prev, max_speed: parseFloat(e.target.value) || 0 }))}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Acceleration (mm/s²)"
                type="number"
                value={formData.acceleration}
                onChange={(e) => setFormData(prev => ({ ...prev, acceleration: parseFloat(e.target.value) || 0 }))}
                required
              />
            </Grid>

            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
            </Grid>

            {/* Pen Settings */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>Pen Settings</Typography>
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Pen Up Position (mm)"
                type="number"
                value={formData.pen_up_position}
                onChange={(e) => setFormData(prev => ({ ...prev, pen_up_position: parseFloat(e.target.value) || 0 }))}
                required
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Pen Down Position (mm)"
                type="number"
                value={formData.pen_down_position}
                onChange={(e) => setFormData(prev => ({ ...prev, pen_down_position: parseFloat(e.target.value) || 0 }))}
                required
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Pen Speed (mm/s)"
                type="number"
                value={formData.pen_speed}
                onChange={(e) => setFormData(prev => ({ ...prev, pen_speed: parseFloat(e.target.value) || 0 }))}
                required
              />
            </Grid>

            <Grid item xs={12}>
              <Divider sx={{ my: 2 }} />
            </Grid>

            {/* Home Position */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>Home Position</Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Home X (mm)"
                type="number"
                value={formData.home_position_x}
                onChange={(e) => setFormData(prev => ({ ...prev, home_position_x: parseFloat(e.target.value) || 0 }))}
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Home Y (mm)"
                type="number"
                value={formData.home_position_y}
                onChange={(e) => setFormData(prev => ({ ...prev, home_position_y: parseFloat(e.target.value) || 0 }))}
                required
              />
            </Grid>

            <Grid item xs={12}>
              <FormControl>
                <label>
                  <input
                    type="checkbox"
                    checked={formData.is_default}
                    onChange={(e) => setFormData(prev => ({ ...prev, is_default: e.target.checked }))}
                  />
                  Set as default plotter
                </label>
              </FormControl>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSave} variant="contained">
            {editingPlotter ? 'Update' : 'Create'}
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
