import { Close as CloseIcon, Save as SaveIcon } from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Slider,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import React, { useEffect, useRef, useState } from "react";
import { generateTerrainRidgeline, getPapers, saveProjectSvg } from "../services/apiService";

const DEFAULT_CENTER = { lat: 47.0, lon: -122.0 };
const DEFAULT_SETTINGS = {
  rows: 80,
  cols: 240,
  rowSpacing: 2.0,
  heightScale: 0.03,
  strokeWidth: 0.35,
};

const bboxToGeoJson = (bbox) => {
  if (!bbox) return null;
  const { minLon, minLat, maxLon, maxLat } = bbox;
  return {
    type: "Feature",
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [minLon, minLat],
          [maxLon, minLat],
          [maxLon, maxLat],
          [minLon, maxLat],
          [minLon, minLat],
        ],
      ],
    },
  };
};

const normalizeFilename = (value) => value.trim().replace(/\.svg$/i, "");
const getFilenameError = (value) => {
  const trimmed = value.trim();
  if (!trimmed) return "Filename is required";
  if (/[\\/]/.test(trimmed)) return "Filename cannot include slashes";
  if (trimmed.includes("..")) return "Filename cannot include ..";
  return "";
};

const TerrainSvgDialog = ({ open, onClose, project }) => {
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const draggingRef = useRef(false);
  const dragStartRef = useRef(null);
  const selectingRef = useRef(false);

  const [paperOptions, setPaperOptions] = useState([]);
  const [paperError, setPaperError] = useState("");
  const [selectedPaper, setSelectedPaper] = useState("");
  const [bbox, setBbox] = useState(null);
  const [selecting, setSelecting] = useState(false);

  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [generationResult, setGenerationResult] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [filename, setFilename] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const filenameError =
    generationResult || filename.trim() ? getFilenameError(filename) : "";
  const normalizedFilename = normalizeFilename(filename);

  useEffect(() => {
    if (!open) return;
    setGenerationResult(null);
    setError(null);
    setFilename("");
    setIsSaving(false);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const loadPapers = async () => {
      try {
        const resp = await getPapers();
        if (resp.error) {
          throw new Error(resp.error);
        }
        const papers = resp.papers || [];
        setPaperOptions(papers);
        if (!selectedPaper && papers.length) {
          const defaultPaper = papers.find((p) => p.is_default) || papers[0];
          setSelectedPaper(defaultPaper.id || defaultPaper.paper_size);
        }
      } catch (err) {
        setPaperError(err.message || "Failed to load papers");
      }
    };
    loadPapers();
  }, [open, selectedPaper]);

  useEffect(() => {
    selectingRef.current = selecting;
  }, [selecting]);

  useEffect(() => {
    if (!open || !mapContainerRef.current) return;
    const token = import.meta.env.VITE_MAPBOX_TOKEN;
    if (!token) {
      setError("VITE_MAPBOX_TOKEN is not configured.");
      return;
    }
    mapboxgl.accessToken = token;
    const map = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: "mapbox://styles/mapbox/light-v11",
      center: [DEFAULT_CENTER.lon, DEFAULT_CENTER.lat],
      zoom: 9,
    });
    mapRef.current = map;

    const ensureLayer = () => {
      if (!map.getSource("bbox")) {
        map.addSource("bbox", {
          type: "geojson",
          data: bboxToGeoJson(bbox) || { type: "FeatureCollection", features: [] },
        });
        map.addLayer({
          id: "bbox-fill",
          type: "fill",
          source: "bbox",
          paint: {
            "fill-color": "#1976d2",
            "fill-opacity": 0.15,
          },
        });
        map.addLayer({
          id: "bbox-outline",
          type: "line",
          source: "bbox",
          paint: {
            "line-color": "#1976d2",
            "line-width": 2,
          },
        });
      }
    };

    map.on("load", ensureLayer);

    const handleMouseDown = (e) => {
      if (!selectingRef.current) return;
      draggingRef.current = true;
      dragStartRef.current = e.lngLat;
      map.dragPan.disable();
    };

    const handleMouseMove = (e) => {
      if (!draggingRef.current || !dragStartRef.current) return;
      const start = dragStartRef.current;
      const current = e.lngLat;
      const nextBbox = {
        minLat: Math.min(start.lat, current.lat),
        minLon: Math.min(start.lng, current.lng),
        maxLat: Math.max(start.lat, current.lat),
        maxLon: Math.max(start.lng, current.lng),
      };
      setBbox(nextBbox);
      const source = map.getSource("bbox");
      if (source) {
        source.setData(bboxToGeoJson(nextBbox));
      }
    };

    const handleMouseUp = () => {
      if (!draggingRef.current) return;
      draggingRef.current = false;
      dragStartRef.current = null;
      map.dragPan.enable();
      setSelecting(false);
    };

    map.on("mousedown", handleMouseDown);
    map.on("mousemove", handleMouseMove);
    map.on("mouseup", handleMouseUp);

    return () => {
      map.off("mousedown", handleMouseDown);
      map.off("mousemove", handleMouseMove);
      map.off("mouseup", handleMouseUp);
      map.remove();
      mapRef.current = null;
    };
  }, [open]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getSource("bbox")) return;
    map.getSource("bbox").setData(bboxToGeoJson(bbox) || { type: "FeatureCollection", features: [] });
  }, [bbox]);

  const handleGenerate = async () => {
    if (!project) return;
    if (!bbox) {
      setError("Please draw a bounding box on the map.");
      return;
    }
    setIsGenerating(true);
    setError(null);
    try {
      const result = await generateTerrainRidgeline({
        bbox,
        paper_id: selectedPaper,
        rows: settings.rows,
        cols: settings.cols,
        row_spacing: settings.rowSpacing,
        height_scale: settings.heightScale,
        stroke_width: settings.strokeWidth,
      });
      setGenerationResult(result);
      if (!filename) {
        setFilename(`terrain_${new Date().toISOString().slice(0, 10)}`);
      }
    } catch (err) {
      setError(err.message || "Failed to generate terrain SVG");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSave = async () => {
    if (!generationResult?.svg) {
      setError("Generate an SVG first.");
      return;
    }
    if (filenameError) return;
    const saveFilename = `${normalizedFilename}.svg`;
    setIsSaving(true);
    setError(null);
    try {
      await saveProjectSvg(project.id, generationResult.svg, saveFilename);
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
    setSelecting(false);
    onClose();
  };

  if (!project) return null;

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="lg">
      <DialogTitle>
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Box>
            <Typography variant="h5">Terrain SVG: {project.name}</Typography>
            <Typography variant="body2" color="text.secondary">
              Generate ridgeline SVG from Mapbox terrain data
            </Typography>
          </Box>
          <Button onClick={handleClose} startIcon={<CloseIcon />}>
            Close
          </Button>
        </Stack>
      </DialogTitle>
      <DialogContent>
        <Stack spacing={2}>
          <Box sx={{ height: 360, borderRadius: 1, overflow: "hidden" }}>
            <Box
              ref={mapContainerRef}
              sx={{ height: "100%", width: "100%" }}
            />
          </Box>
          <Stack direction="row" spacing={2} alignItems="center">
            <Button
              variant={selecting ? "contained" : "outlined"}
              onClick={() => setSelecting((prev) => !prev)}
            >
              {selecting ? "Drawing bbox..." : "Draw bounding box"}
            </Button>
            {bbox && (
              <Typography variant="body2" color="text.secondary">
                BBox: {bbox.minLat.toFixed(4)}, {bbox.minLon.toFixed(4)} →{" "}
                {bbox.maxLat.toFixed(4)}, {bbox.maxLon.toFixed(4)}
              </Typography>
            )}
          </Stack>

          <Divider />

          <FormControl fullWidth>
            <InputLabel>Paper Size</InputLabel>
            <Select
              label="Paper Size"
              value={selectedPaper}
              onChange={(e) => setSelectedPaper(e.target.value)}
              disabled={!paperOptions.length}
            >
              {paperOptions.map((paper) => (
                <MenuItem key={paper.id} value={paper.id || paper.paper_size}>
                  {paper.name || paper.paper_size} ({paper.width}×{paper.height}mm)
                  {paper.is_default ? " • default" : ""}
                </MenuItem>
              ))}
            </Select>
            {paperError && (
              <Typography variant="caption" color="error">
                {paperError}
              </Typography>
            )}
          </FormControl>

          <Stack spacing={2}>
            <Box>
              <Typography variant="body2" color="text.secondary">
                Rows: {settings.rows}
              </Typography>
              <Slider
                value={settings.rows}
                min={20}
                max={200}
                step={1}
                onChange={(e, value) =>
                  setSettings((prev) => ({ ...prev, rows: value }))
                }
              />
            </Box>
            <Box>
              <Typography variant="body2" color="text.secondary">
                Columns: {settings.cols}
              </Typography>
              <Slider
                value={settings.cols}
                min={50}
                max={500}
                step={1}
                onChange={(e, value) =>
                  setSettings((prev) => ({ ...prev, cols: value }))
                }
              />
            </Box>
            <Box>
              <Typography variant="body2" color="text.secondary">
                Row Spacing (mm): {settings.rowSpacing.toFixed(2)}
              </Typography>
              <Slider
                value={settings.rowSpacing}
                min={0.5}
                max={6}
                step={0.1}
                onChange={(e, value) =>
                  setSettings((prev) => ({ ...prev, rowSpacing: value }))
                }
              />
            </Box>
            <Box>
              <Typography variant="body2" color="text.secondary">
                Height Scale (mm/m): {settings.heightScale.toFixed(3)}
              </Typography>
              <Slider
                value={settings.heightScale}
                min={0.005}
                max={0.1}
                step={0.001}
                onChange={(e, value) =>
                  setSettings((prev) => ({ ...prev, heightScale: value }))
                }
              />
            </Box>
            <Box>
              <Typography variant="body2" color="text.secondary">
                Stroke Width (mm): {settings.strokeWidth.toFixed(2)}
              </Typography>
              <Slider
                value={settings.strokeWidth}
                min={0.1}
                max={2}
                step={0.05}
                onChange={(e, value) =>
                  setSettings((prev) => ({ ...prev, strokeWidth: value }))
                }
              />
            </Box>
          </Stack>

          <Divider />

          <TextField
            fullWidth
            label="Filename"
            value={filename}
            onChange={(e) => setFilename(e.target.value)}
            error={Boolean(filenameError)}
            helperText={
              filenameError ||
              (normalizedFilename
                ? `Saved as ${normalizedFilename}.svg`
                : "Add a filename; .svg is added automatically.")
            }
          />

          {error && <Alert severity="error">{error}</Alert>}

          {generationResult?.svg && (
            <Box sx={{ border: "1px solid", borderColor: "divider", p: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Preview
              </Typography>
              <Box
                sx={{
                  maxHeight: 400,
                  overflow: "auto",
                  "& svg": { width: "100%", height: "auto" },
                }}
                dangerouslySetInnerHTML={{ __html: generationResult.svg }}
              />
            </Box>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleGenerate} disabled={isGenerating}>
          {isGenerating ? "Generating..." : "Generate"}
        </Button>
        <Button
          variant="contained"
          onClick={handleSave}
          disabled={!generationResult?.svg || isSaving || Boolean(filenameError)}
          startIcon={isSaving ? <CircularProgress size={18} /> : <SaveIcon />}
        >
          {isSaving ? "Saving..." : "Save SVG"}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TerrainSvgDialog;
