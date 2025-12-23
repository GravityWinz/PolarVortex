import {
  Article as SvgIcon,
  Code as CodeIcon,
  DeleteOutline as DeleteIcon,
  AutoFixHigh as ConvertIcon,
  Image as ImageIcon,
  InsertDriveFile as FileIcon,
  Refresh as RefreshIcon,
} from "@mui/icons-material";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  ListSubheader,
  Paper,
  Stack,
  Typography,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
} from "@mui/material";
import React, { useEffect, useMemo, useState } from "react";
import {
  getProject,
  getProjectAssets,
  getProjectFileText,
  getProjectFileUrl,
  deleteProjectFile,
  convertSvgToGcode,
} from "../services/apiService";

const IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "gif", "bmp", "webp"];
const SVG_EXTENSIONS = ["svg"];
const GCODE_EXTENSIONS = ["gcode", "nc", "txt"];

function normalizeAsset(filename, meta = {}, typeOverride) {
  const ext = (filename || "").split(".").pop()?.toLowerCase() || "";
  const type =
    typeOverride ||
    (IMAGE_EXTENSIONS.includes(ext)
      ? "image"
      : SVG_EXTENSIONS.includes(ext)
      ? "svg"
      : GCODE_EXTENSIONS.includes(ext)
      ? "gcode"
      : "other");

  return {
    filename,
    type,
    label: meta.is_thumbnail
      ? `Thumbnail (${filename})`
      : meta.is_processed
      ? `Processed (${filename})`
      : filename,
    meta,
    displayName: filename?.split("/").pop() || filename,
  };
}

function groupAssets(imageEntries = [], gcodeEntries = []) {
  const images = [];
  const svgs = [];

  imageEntries.forEach((entry) => {
    const normalized = normalizeAsset(entry.filename, {
      is_thumbnail: entry.is_thumbnail,
      is_processed: entry.is_processed,
      is_original: entry.is_original,
    });
    if (normalized.type === "svg") {
      svgs.push(normalized);
    } else if (normalized.type === "image") {
      images.push(normalized);
    }
  });

  const gcode = (gcodeEntries || []).map((file) =>
    normalizeAsset(file, {}, "gcode")
  );

  return { images, svgs, gcode };
}

function parseGcodeForPreview(content) {
  let x = 0;
  let y = 0;
  const segments = [];
  let bounds = null;

  const lines = content.split(/\r?\n/);
  for (const rawLine of lines) {
    const noComment = rawLine.split(";")[0].trim();
    if (!noComment) continue;

    const cmdMatch = noComment.match(/\bG0?0\b|\bG0?1\b/i);
    if (!cmdMatch) continue;
    const cmd = cmdMatch[0].toUpperCase();
    const penDown = cmd !== "G0" && cmd !== "G00";

    const xMatch = noComment.match(/X(-?\d+(\.\d+)?)/i);
    const yMatch = noComment.match(/Y(-?\d+(\.\d+)?)/i);
    const nextX = xMatch ? parseFloat(xMatch[1]) : x;
    const nextY = yMatch ? parseFloat(yMatch[1]) : y;

    if (Number.isNaN(nextX) || Number.isNaN(nextY)) {
      continue;
    }

    if (nextX === x && nextY === y) {
      continue;
    }

    segments.push({
      from: { x, y },
      to: { x: nextX, y: nextY },
      penDown,
    });

    x = nextX;
    y = nextY;

    bounds = bounds
      ? {
          minX: Math.min(bounds.minX, x),
          maxX: Math.max(bounds.maxX, x),
          minY: Math.min(bounds.minY, y),
          maxY: Math.max(bounds.maxY, y),
        }
      : { minX: x, maxX: x, minY: y, maxY: y };
  }

  return { segments, bounds };
}

export default function EditProject({ currentProject }) {
  const [assets, setAssets] = useState({ images: [], svgs: [], gcode: [] });
  const [loadingAssets, setLoadingAssets] = useState(false);
  const [assetError, setAssetError] = useState("");
  const [selectedAsset, setSelectedAsset] = useState(null);
  const [gcodePreview, setGcodePreview] = useState({
    loading: false,
    content: "",
    error: "",
  });
  const [deletingFile, setDeletingFile] = useState(null);
  const [gcodeGeometry, setGcodeGeometry] = useState({
    segments: [],
    bounds: null,
  });
  const [convertDialogOpen, setConvertDialogOpen] = useState(false);
  const [convertTarget, setConvertTarget] = useState(null);
  const [convertOptions, setConvertOptions] = useState({
    paperSize: "A4",
    fitMode: "fit",
    penMapping: "default",
  });
  const [convertLoading, setConvertLoading] = useState(false);
  const [convertError, setConvertError] = useState("");

  const hasAssets = useMemo(
    () =>
      assets.images.length > 0 ||
      assets.svgs.length > 0 ||
      assets.gcode.length > 0,
    [assets]
  );

  const loadAssets = async () => {
    if (!currentProject?.id) {
      setAssets({ images: [], svgs: [], gcode: [] });
      setSelectedAsset(null);
      return;
    }

    setLoadingAssets(true);
    setAssetError("");
    try {
      const [imageResponse, projectResponse] = await Promise.all([
        getProjectAssets(currentProject.id),
        getProject(currentProject.id),
      ]);

      if (imageResponse.error) {
        throw new Error(imageResponse.error);
      }

      const grouped = groupAssets(
        imageResponse.images || [],
        projectResponse?.gcode_files || []
      );
      setAssets(grouped);

      const first =
        grouped.images[0] || grouped.svgs[0] || grouped.gcode[0] || null;
      setSelectedAsset(first);
    } catch (err) {
      setAssetError(err.message || "Failed to load project assets");
    } finally {
      setLoadingAssets(false);
    }
  };

  useEffect(() => {
    loadAssets();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentProject?.id]);

  useEffect(() => {
    if (!selectedAsset || selectedAsset.type !== "gcode" || !currentProject) {
      setGcodePreview({ loading: false, content: "", error: "" });
      return;
    }

    let cancelled = false;
    const loadText = async () => {
      setGcodePreview({ loading: true, content: "", error: "" });
      try {
        const content = await getProjectFileText(
          currentProject.id,
          selectedAsset.filename
        );
        if (!cancelled) {
          setGcodePreview({ loading: false, content, error: "" });
        }
      } catch (err) {
        if (!cancelled) {
          setGcodePreview({
            loading: false,
            content: "",
            error: err.message || "Failed to load file",
          });
        }
      }
    };

    loadText();
    return () => {
      cancelled = true;
    };
  }, [currentProject, selectedAsset]);

  useEffect(() => {
    if (selectedAsset?.type !== "gcode" || !gcodePreview.content) {
      setGcodeGeometry({ segments: [], bounds: null });
      return;
    }

    const parsed = parseGcodeForPreview(gcodePreview.content);
    setGcodeGeometry(parsed);
  }, [selectedAsset, gcodePreview.content]);

  const handleDeleteAsset = async (asset) => {
    if (!currentProject || !asset) return;
    const confirmed = window.confirm(
      `Delete ${asset.displayName}? This cannot be undone.`
    );
    if (!confirmed) return;
    try {
      setDeletingFile(asset.filename);
      await deleteProjectFile(currentProject.id, asset.filename);
      if (selectedAsset?.filename === asset.filename) {
        setSelectedAsset(null);
      }
      await loadAssets();
    } catch (err) {
      setAssetError(err.message || "Failed to delete file");
    } finally {
      setDeletingFile(null);
    }
  };

  const openConvertDialog = (asset) => {
    setConvertTarget(asset);
    setConvertError("");
    setConvertDialogOpen(true);
  };

  const handleConvert = async () => {
    if (!currentProject || !convertTarget) return;
    setConvertLoading(true);
    setConvertError("");
    try {
      await convertSvgToGcode(currentProject.id, {
        filename: convertTarget.filename,
        paper_size: convertOptions.paperSize,
        fit_mode: convertOptions.fitMode,
        pen_mapping: convertOptions.penMapping,
      });
      await loadAssets();
      setConvertDialogOpen(false);
      setConvertTarget(null);
    } catch (err) {
      setConvertError(err.message || "Failed to convert SVG");
    } finally {
      setConvertLoading(false);
    }
  };

  const renderGcodePlot = () => {
    if (!gcodeGeometry.bounds || gcodeGeometry.segments.length === 0) {
      return (
        <Alert severity="info" sx={{ mb: 2 }}>
          No drawable moves found in this G-code (need G0/G1 with X/Y).
        </Alert>
      );
    }

    const { minX, maxX, minY, maxY } = gcodeGeometry.bounds;
    const width = 640;
    const height = 420;
    const padding = 16;
    const spanX = Math.max(maxX - minX, 1);
    const spanY = Math.max(maxY - minY, 1);
    const scaleX = (width - padding * 2) / spanX;
    const scaleY = (height - padding * 2) / spanY;
    const scale = Math.min(scaleX, scaleY);

    const mapPoint = (x, y) => ({
      x: padding + (x - minX) * scale,
      // Flip Y so higher Y is up visually
      y: height - padding - (y - minY) * scale,
    });

    return (
      <Box sx={{ mb: 2 }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
          <CodeIcon color="primary" />
          <Typography variant="subtitle1">G-code Plot Preview</Typography>
          <Chip
            label={`${gcodeGeometry.segments.length} segments`}
            size="small"
          />
        </Stack>
        <Paper
          variant="outlined"
          sx={{
            p: 1,
            bgcolor: "grey.50",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <Box
            component="svg"
            width="100%"
            height="100%"
            viewBox={`0 0 ${width} ${height}`}
            sx={{ maxHeight: 460 }}
          >
            <rect
              x={0}
              y={0}
              width={width}
              height={height}
              fill="white"
              stroke="#e0e0e0"
            />
            {gcodeGeometry.segments.map((seg, idx) => {
              const from = mapPoint(seg.from.x, seg.from.y);
              const to = mapPoint(seg.to.x, seg.to.y);
              return (
                <line
                  key={`seg-${idx}`}
                  x1={from.x}
                  y1={from.y}
                  x2={to.x}
                  y2={to.y}
                  stroke={seg.penDown ? "#1976d2" : "#9e9e9e"}
                  strokeWidth={seg.penDown ? 1.5 : 1}
                  strokeDasharray={seg.penDown ? "none" : "4 4"}
                  opacity={seg.penDown ? 0.9 : 0.5}
                />
              );
            })}
          </Box>
        </Paper>
      </Box>
    );
  };

  const renderPreview = () => {
    if (!currentProject) {
      return (
        <Alert severity="info">
          Select a project to view its assets and previews.
        </Alert>
      );
    }

    if (!selectedAsset) {
      return hasAssets ? (
        <Alert severity="info">Choose a file from the Asset Viewer.</Alert>
      ) : (
        <Alert severity="info">
          No assets found. Upload images or G-code to this project.
        </Alert>
      );
    }

    if (selectedAsset.type === "gcode") {
      return (
        <Box>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
            <CodeIcon color="primary" />
            <Typography variant="h6">G-code Preview</Typography>
            <Chip label={selectedAsset.displayName} size="small" />
          </Stack>
          <Paper
            variant="outlined"
            sx={{
              p: 2,
              bgcolor: "grey.50",
              maxHeight: 500,
              overflow: "auto",
              fontFamily: "monospace",
              whiteSpace: "pre",
            }}
          >
            {gcodePreview.loading && (
              <Stack direction="row" spacing={1} alignItems="center">
                <CircularProgress size={18} />
                <Typography variant="body2">Loading G-code…</Typography>
              </Stack>
            )}
            {!gcodePreview.loading && gcodePreview.error && (
              <Alert severity="error">{gcodePreview.error}</Alert>
            )}
            {!gcodePreview.loading && !gcodePreview.error && (
              <Stack spacing={2}>
                {renderGcodePlot()}
                <Typography
                  component="pre"
                  variant="body2"
                  sx={{ m: 0, whiteSpace: "pre-wrap" }}
                >
                  {gcodePreview.content || "File is empty."}
                </Typography>
              </Stack>
            )}
          </Paper>
        </Box>
      );
    }

    const isSvg = selectedAsset.type === "svg";
    const icon = isSvg ? <SvgIcon color="primary" /> : <ImageIcon color="primary" />;

    return (
      <Box>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
          {icon}
          <Typography variant="h6">
            {isSvg ? "SVG Preview" : "Image Preview"}
          </Typography>
          <Chip label={selectedAsset.displayName} size="small" />
        </Stack>
        <Paper
          variant="outlined"
          sx={{
            p: 2,
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            bgcolor: "grey.50",
            minHeight: 320,
          }}
        >
          <Box
            component="img"
            src={getProjectFileUrl(currentProject.id, selectedAsset.filename)}
            alt={selectedAsset.displayName}
            sx={{
              maxWidth: "100%",
              maxHeight: 600,
              borderRadius: 1,
              boxShadow: 1,
              objectFit: "contain",
            }}
          />
        </Paper>
      </Box>
    );
  };

  const renderAssetSection = (title, items, icon) => {
    if (!items.length) return null;

    return (
      <List
        subheader={
          <ListSubheader component="div" disableSticky>
            <Stack direction="row" spacing={1} alignItems="center">
              {icon}
              <Typography variant="subtitle2">{title}</Typography>
              <Chip label={items.length} size="small" />
            </Stack>
          </ListSubheader>
        }
        dense
      >
        {items.map((item) => (
          <ListItem
            key={`${title}-${item.filename}`}
            disablePadding
            secondaryAction={
              <Stack direction="row" spacing={0.5}>
                {item.type === "svg" && (
                  <IconButton
                    edge="end"
                    aria-label={`convert ${item.displayName}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      openConvertDialog(item);
                    }}
                    size="small"
                    color="primary"
                    disabled={convertLoading}
                  >
                    <ConvertIcon fontSize="small" />
                  </IconButton>
                )}
                <IconButton
                  edge="end"
                  aria-label={`delete ${item.displayName}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteAsset(item);
                  }}
                  disabled={deletingFile === item.filename}
                  size="small"
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Stack>
            }
          >
            <ListItemButton
              selected={selectedAsset?.filename === item.filename}
              onClick={() => setSelectedAsset(item)}
            >
              <ListItemText primary={item.displayName} secondary={item.label} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    );
  };

  return (
    <Box sx={{ p: 2 }}>
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 2 }}
      >
        <Box>
          <Typography variant="h4" sx={{ mb: 0.5 }}>
            Edit Project
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Browse project assets and preview images, SVGs, or G-code.
          </Typography>
          {currentProject?.name && (
            <Typography variant="subtitle2" color="text.secondary">
              Active project: {currentProject.name}
            </Typography>
          )}
        </Box>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={loadAssets}
          disabled={loadingAssets || !currentProject}
        >
          Refresh
        </Button>
      </Stack>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, height: "100%", minHeight: 420 }}>
            <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
              <FileIcon color="primary" />
              <Typography variant="h6">Asset Viewer</Typography>
            </Stack>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Select a file to preview. Includes images, thumbnails, SVGs, and G-code.
            </Typography>
            <Divider sx={{ mb: 1 }} />

            {!currentProject && (
              <Alert severity="info">Choose a project to see its assets.</Alert>
            )}

            {currentProject && loadingAssets && (
              <Stack
                direction="row"
                spacing={1}
                alignItems="center"
                sx={{ py: 2 }}
              >
                <CircularProgress size={18} />
                <Typography variant="body2">Loading assets…</Typography>
              </Stack>
            )}

            {currentProject && !loadingAssets && assetError && (
              <Alert severity="error">{assetError}</Alert>
            )}

            {currentProject && !loadingAssets && !assetError && !hasAssets && (
              <Alert severity="info">
                No assets yet. Upload an image or G-code to this project.
              </Alert>
            )}

            {currentProject && !loadingAssets && !assetError && hasAssets && (
              <Box sx={{ maxHeight: 600, overflow: "auto" }}>
                {renderAssetSection("Images", assets.images, <ImageIcon fontSize="small" />)}
                {renderAssetSection("SVG", assets.svgs, <SvgIcon fontSize="small" />)}
                {renderAssetSection("G-code", assets.gcode, <CodeIcon fontSize="small" />)}
              </Box>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2, minHeight: 420 }}>
            {renderPreview()}
          </Paper>
        </Grid>
      </Grid>

      <Dialog open={convertDialogOpen} onClose={() => setConvertDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Convert SVG to G-code</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <FormControl fullWidth>
              <InputLabel>Paper Size</InputLabel>
              <Select
                label="Paper Size"
                value={convertOptions.paperSize}
                onChange={(e) =>
                  setConvertOptions((prev) => ({ ...prev, paperSize: e.target.value }))
                }
              >
                <MenuItem value="A4">A4</MenuItem>
                <MenuItem value="Letter">Letter</MenuItem>
                <MenuItem value="A3">A3</MenuItem>
              </Select>
            </FormControl>

            <FormControl fullWidth>
              <InputLabel>Fit / Center</InputLabel>
              <Select
                label="Fit / Center"
                value={convertOptions.fitMode}
                onChange={(e) =>
                  setConvertOptions((prev) => ({ ...prev, fitMode: e.target.value }))
                }
              >
                <MenuItem value="fit">Fit to page</MenuItem>
                <MenuItem value="center">Center on page</MenuItem>
              </Select>
            </FormControl>

            <TextField
              label="Pen Mapping (placeholder)"
              value={convertOptions.penMapping}
              onChange={(e) =>
                setConvertOptions((prev) => ({ ...prev, penMapping: e.target.value }))
              }
              helperText="E.g., pen color or channel to use"
              fullWidth
            />

            {convertError && <Alert severity="error">{convertError}</Alert>}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConvertDialogOpen(false)} disabled={convertLoading}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleConvert}
            disabled={convertLoading || !currentProject || !convertTarget}
          >
            {convertLoading ? "Converting..." : "Convert"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

