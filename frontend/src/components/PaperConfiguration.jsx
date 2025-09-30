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
    createPaper,
    deletePaper,
    getPapers,
    updatePaper
} from '../services/apiService';

const PAPER_SIZES = [
  { value: 'A5', label: 'A5' },
  { value: 'A4', label: 'A4' },
  { value: 'A3', label: 'A3' },
  { value: 'A2', label: 'A2' },
  { value: 'A1', label: 'A1' },
  { value: 'A0', label: 'A0' },
  { value: 'A', label: 'US A' },
  { value: 'B', label: 'US B' },
  { value: 'C', label: 'US C' },
  { value: 'D', label: 'US D' },
  { value: 'Letter', label: 'Letter' },
  { value: 'Legal', label: 'Legal' },
  { value: 'Tabloid', label: 'Tabloid' },
  { value: 'Custom', label: 'Custom' },
];

const PAPER_COLORS = [
  'white',
  'cream',
  'ivory',
  'beige',
  'light gray',
  'gray',
  'dark gray',
  'black',
  'blue',
  'red',
  'green',
  'yellow',
  'pink',
  'purple',
  'orange',
];

export default function PaperConfiguration() {
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingPaper, setEditingPaper] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    paper_size: 'A4',
    width: 210,
    height: 297,
    color: 'white',
    is_default: false,
  });

  useEffect(() => {
    loadPapers();
  }, []);

  const loadPapers = async () => {
    try {
      setLoading(true);
      const response = await getPapers();
      if (response.error) {
        setError(response.error);
      } else {
        setPapers(response.papers || []);
      }
    } catch (err) {
      setError('Failed to load papers');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingPaper(null);
    setFormData({
      name: '',
      paper_size: 'A4',
      width: 210,
      height: 297,
      color: 'white',
      is_default: false,
    });
    setDialogOpen(true);
  };

  const handleEdit = (paper) => {
    setEditingPaper(paper);
    setFormData({
      name: paper.name,
      paper_size: paper.paper_size,
      width: paper.width,
      height: paper.height,
      color: paper.color,
      is_default: paper.is_default,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    try {
      if (editingPaper) {
        await updatePaper(editingPaper.id, formData);
        setSuccess('Paper updated successfully');
      } else {
        await createPaper(formData);
        setSuccess('Paper created successfully');
      }
      setDialogOpen(false);
      loadPapers();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async (paper) => {
    if (window.confirm(`Are you sure you want to delete "${paper.name}"?`)) {
      try {
        await deletePaper(paper.id);
        setSuccess('Paper deleted successfully');
        loadPapers();
      } catch (err) {
        setError(err.message);
      }
    }
  };

  const handleSetDefault = async (paper) => {
    try {
      await updatePaper(paper.id, { ...paper, is_default: true });
      setSuccess(`"${paper.name}" set as default`);
      loadPapers();
    } catch (err) {
      setError(err.message);
    }
  };

  const handlePaperSizeChange = (paperSize) => {
    setFormData(prev => ({
      ...prev,
      paper_size: paperSize,
    }));

    // Set standard dimensions for known paper sizes
    const standardDimensions = {
      'A5': { width: 148, height: 210 },
      'A4': { width: 210, height: 297 },
      'A3': { width: 297, height: 420 },
      'A2': { width: 420, height: 594 },
      'A1': { width: 594, height: 841 },
      'A0': { width: 841, height: 1189 },
      'A': { width: 216, height: 279 },
      'B': { width: 279, height: 432 },
      'C': { width: 432, height: 559 },
      'D': { width: 559, height: 864 },
      'Letter': { width: 216, height: 279 },
      'Legal': { width: 216, height: 356 },
      'Tabloid': { width: 279, height: 432 },
    };

    if (standardDimensions[paperSize]) {
      setFormData(prev => ({
        ...prev,
        width: standardDimensions[paperSize].width,
        height: standardDimensions[paperSize].height,
        name: `${paperSize} Paper (${standardDimensions[paperSize].width}×${standardDimensions[paperSize].height}mm)`,
      }));
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
        <Typography variant="h6">Paper Configurations</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleCreate}
        >
          Add Paper
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Size</TableCell>
              <TableCell>Dimensions (mm)</TableCell>
              <TableCell>Color</TableCell>
              <TableCell>Default</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {papers.map((paper) => (
              <TableRow key={paper.id}>
                <TableCell>{paper.name}</TableCell>
                <TableCell>{paper.paper_size}</TableCell>
                <TableCell>{paper.width} × {paper.height}</TableCell>
                <TableCell>
                  <Chip
                    label={paper.color}
                    size="small"
                    style={{ backgroundColor: paper.color === 'white' ? '#f5f5f5' : paper.color }}
                  />
                </TableCell>
                <TableCell>
                  {paper.is_default ? (
                    <Chip icon={<StarIcon />} label="Default" color="primary" size="small" />
                  ) : (
                    <IconButton
                      size="small"
                      onClick={() => handleSetDefault(paper)}
                      title="Set as default"
                    >
                      <StarBorderIcon />
                    </IconButton>
                  )}
                </TableCell>
                <TableCell>
                  <IconButton
                    size="small"
                    onClick={() => handleEdit(paper)}
                    title="Edit"
                  >
                    <EditIcon />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => handleDelete(paper)}
                    title="Delete"
                    disabled={paper.is_default}
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
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingPaper ? 'Edit Paper' : 'Add New Paper'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
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
                <InputLabel>Paper Size</InputLabel>
                <Select
                  value={formData.paper_size}
                  onChange={(e) => handlePaperSizeChange(e.target.value)}
                  label="Paper Size"
                >
                  {PAPER_SIZES.map((size) => (
                    <MenuItem key={size.value} value={size.value}>
                      {size.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth>
                <InputLabel>Color</InputLabel>
                <Select
                  value={formData.color}
                  onChange={(e) => setFormData(prev => ({ ...prev, color: e.target.value }))}
                  label="Color"
                >
                  {PAPER_COLORS.map((color) => (
                    <MenuItem key={color} value={color}>
                      {color}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
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
              <FormControl>
                <label>
                  <input
                    type="checkbox"
                    checked={formData.is_default}
                    onChange={(e) => setFormData(prev => ({ ...prev, is_default: e.target.checked }))}
                  />
                  Set as default paper
                </label>
              </FormControl>
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSave} variant="contained">
            {editingPaper ? 'Update' : 'Create'}
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
