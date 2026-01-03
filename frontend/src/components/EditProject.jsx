import {
  Code as CodeIcon,
  AutoFixHigh as ConvertIcon,
  DeleteOutline as DeleteIcon,
  InsertDriveFile as FileIcon,
  Image as ImageIcon,
  Refresh as RefreshIcon,
  Article as SvgIcon,
  AutoGraph as VectorizeIcon,
} from "@mui/icons-material";
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
  FormControlLabel,
  Grid,
  IconButton,
  InputLabel,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  ListSubheader,
  MenuItem,
  Paper,
  Select,
  Stack,
  Switch,
  Tooltip,
  Typography,
} from "@mui/material";
import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  convertSvgToGcode,
  deleteProjectFile,
  getPapers,
  getProject,
  getProjectAssets,
  getProjectFileText,
  getProjectFileUrl,
  getProjectGcodeAnalysis,
  getProjectSvgAnalysis,
  uploadGcodeToProject,
  uploadImageToProject,
} from "../services/apiService";
import VectorizeDialog from "./VectorizeDialog";

const IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "gif", "bmp", "webp"];
const SVG_EXTENSIONS = ["svg"];
const GCODE_EXTENSIONS = ["gcode", "nc", "txt"];
const DEFAULT_UPLOAD_SETTINGS = {
  threshold: 128,
  invert: false,
  dither: true,
  resolution: "medium",
};

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
  const [projectDetails, setProjectDetails] = useState(null);
  const [gcodePreview, setGcodePreview] = useState({
    loading: false,
    content: "",
    error: "",
  });
  const [gcodeAnalysis, setGcodeAnalysis] = useState({
    loading: false,
    data: null,
    error: "",
  });
  const [svgAnalysis, setSvgAnalysis] = useState({
    loading: false,
    data: null,
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
    paperSize: "",
    rotate90: false,
  });
  const [convertLoading, setConvertLoading] = useState(false);
  const [convertError, setConvertError] = useState("");
  const [paperOptions, setPaperOptions] = useState([]);
  const [paperLoadError, setPaperLoadError] = useState("");
  const [vectorizeDialogOpen, setVectorizeDialogOpen] = useState(false);
  const [vectorizeProject, setVectorizeProject] = useState(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  const defaultPaper = useMemo(() => {
    if (!paperOptions.length) return null;
    return paperOptions.find((p) => p.is_default) || paperOptions[0] || null;
  }, [paperOptions]);

  const hasAssets = useMemo(
    () =>
      assets.images.length > 0 ||
      assets.svgs.length > 0 ||
      assets.gcode.length > 0,
    [assets]
  );

  const loadAssets = async () => {
    if (!currentProject?.id) {
      setProjectDetails(null);
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
      setProjectDetails(projectResponse || null);

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
    const loadPapers = async () => {
      try {
        const resp = await getPapers();
        if (resp.error) {
          throw new Error(resp.error);
        }
        const papers = resp.papers || [];
        setPaperOptions(papers);
        if (!convertOptions.paperSize && papers.length) {
          const defaultPaper = papers.find((p) => p.is_default) || papers[0];
          setConvertOptions((prev) => ({
            ...prev,
            paperSize: defaultPaper.id || defaultPaper.paper_size,
          }));
        }
      } catch (err) {
        setPaperLoadError(err.message || "Failed to load papers");
      }
    };
    loadPapers();
  }, [convertOptions.paperSize]);

  useEffect(() => {
    if (!selectedAsset || selectedAsset.type !== "gcode" || !currentProject) {
      setGcodePreview({ loading: false, content: "", error: "" });
      setGcodeAnalysis({ loading: false, data: null, error: "" });
      setSvgAnalysis({ loading: false, data: null, error: "" });
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

  useEffect(() => {
    if (selectedAsset?.type !== "svg") {
      setSvgAnalysis({ loading: false, data: null, error: "" });
    }
  }, [selectedAsset]);

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

  const handleAnalyzeGcode = async () => {
    if (!currentProject || !selectedAsset) return;
    setGcodeAnalysis({ loading: true, data: null, error: "" });
    try {
      const result = await getProjectGcodeAnalysis(
        currentProject.id,
        selectedAsset.filename
      );
      setGcodeAnalysis({ loading: false, data: result, error: "" });
    } catch (err) {
      setGcodeAnalysis({
        loading: false,
        data: null,
        error: err.message || "Failed to analyze G-code",
      });
    }
  };

  const handleAnalyzeSvg = async () => {
    if (!currentProject || !selectedAsset) return;
    setSvgAnalysis({ loading: true, data: null, error: "" });
    try {
      const result = await getProjectSvgAnalysis(
        currentProject.id,
        selectedAsset.filename
      );
      setSvgAnalysis({ loading: false, data: result, error: "" });
    } catch (err) {
      setSvgAnalysis({
        loading: false,
        data: null,
        error: err.message || "Failed to analyze SVG",
      });
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
        pen_mapping: null,
        origin_mode: "center",
        rotate_90: Boolean(convertOptions.rotate90),
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

  const handleUploadFile = async (file) => {
    if (!file || !currentProject) return;
    const name = (file.name || "").toLowerCase();
    const ext = name.match(/\.[^.]+$/)?.[0]?.slice(1) || "";
    const isSvg = ext === "svg";
    const isGcode = GCODE_EXTENSIONS.includes(ext);
    const isImage = file.type.startsWith("image/") || isSvg;

    if (!isImage && !isGcode) {
      setAssetError(
        "Unsupported file type. Use image/SVG or G-code (.gcode/.nc/.txt)."
      );
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setAssetError("File size must be less than 10MB");
      return;
    }

    setAssetError("");
    setUploading(true);
    try {
      if (isGcode) {
        const formData = new FormData();
        formData.append("file", file);
        await uploadGcodeToProject(currentProject.id, formData);
      } else {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("settings", JSON.stringify(DEFAULT_UPLOAD_SETTINGS));
        await uploadImageToProject(currentProject.id, formData);
      }

      await loadAssets();
    } catch (err) {
      setAssetError(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleFileInputChange = async (event) => {
    const file = event.target.files?.[0];
    // Reset input so the same file can be selected again
    event.target.value = "";
    await handleUploadFile(file);
  };

  const triggerFilePicker = () => {
    fileInputRef.current?.click();
  };

  const isVectorizableAsset = (asset) => {
    if (!asset || asset.type !== "image") return false;
    const sourceImage = projectDetails?.source_image;
    return Boolean(sourceImage && asset.filename === sourceImage);
  };

  const openVectorizeDialog = (asset) => {
    if (!currentProject || !isVectorizableAsset(asset)) return;
    setVectorizeProject(projectDetails || currentProject);
    setVectorizeDialogOpen(true);
  };

  const handleCloseVectorizeDialog = () => {
    setVectorizeDialogOpen(false);
    setVectorizeProject(null);
  };

  const renderGcodePlot = () => {
    const printableSegments = (gcodeGeometry.segments || []).filter(
      (seg) => seg.penDown
    );

    const calcBounds = (segments) => {
      if (!segments.length) return null;
      return segments.reduce(
        (acc, seg) => ({
          minX: Math.min(acc.minX, seg.from.x, seg.to.x),
          maxX: Math.max(acc.maxX, seg.from.x, seg.to.x),
          minY: Math.min(acc.minY, seg.from.y, seg.to.y),
          maxY: Math.max(acc.maxY, seg.from.y, seg.to.y),
        }),
        {
          minX: Infinity,
          maxX: -Infinity,
          minY: Infinity,
          maxY: -Infinity,
        }
      );
    };

    const bounds = calcBounds(printableSegments);

    const paperWidth = defaultPaper ? Number(defaultPaper.width) || 0 : 0;
    const paperHeight = defaultPaper ? Number(defaultPaper.height) || 0 : 0;
    const paperBox =
      paperWidth > 0 && paperHeight > 0
        ? {
            minX: -paperWidth / 2,
            maxX: paperWidth / 2,
            minY: -paperHeight / 2,
            maxY: paperHeight / 2,
          }
        : null;

    // Expand bounds to include paper rectangle so both fit the viewport
    const combinedBounds = bounds
      ? {
          minX: Math.min(
            bounds.minX,
            paperBox ? paperBox.minX : bounds.minX
          ),
          maxX: Math.max(
            bounds.maxX,
            paperBox ? paperBox.maxX : bounds.maxX
          ),
          minY: Math.min(
            bounds.minY,
            paperBox ? paperBox.minY : bounds.minY
          ),
          maxY: Math.max(
            bounds.maxY,
            paperBox ? paperBox.maxY : bounds.maxY
          ),
        }
      : paperBox;

    if (!bounds || printableSegments.length === 0) {
      return (
        <Alert severity="info" sx={{ mb: 2 }}>
          No printable moves found (only travel moves present).
        </Alert>
      );
    }

    const { minX, maxX, minY, maxY } = combinedBounds || bounds;
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
          <Chip label={`${printableSegments.length} segments`} size="small" />
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
            {paperBox && (
              <rect
                x={Math.min(
                  mapPoint(paperBox.minX, paperBox.minY).x,
                  mapPoint(paperBox.maxX, paperBox.maxY).x
                )}
                y={Math.min(
                  mapPoint(paperBox.minX, paperBox.minY).y,
                  mapPoint(paperBox.maxX, paperBox.maxY).y
                )}
                width={Math.abs(
                  mapPoint(paperBox.maxX, paperBox.minY).x -
                    mapPoint(paperBox.minX, paperBox.minY).x
                )}
                height={Math.abs(
                  mapPoint(paperBox.minX, paperBox.maxY).y -
                    mapPoint(paperBox.minX, paperBox.minY).y
                )}
                fill="none"
                stroke="#8bc34a"
                strokeWidth={1.5}
                strokeDasharray="6 4"
                opacity={0.9}
              />
            )}
            {printableSegments.map((seg, idx) => {
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

  const formatMinutes = (minutes) => {
    if (minutes == null) return "—";
    const totalSeconds = Math.round(minutes * 60);
    const hrs = Math.floor(totalSeconds / 3600);
    const mins = Math.floor((totalSeconds % 3600) / 60);
    const secs = totalSeconds % 60;
    if (hrs > 0) {
      return `${hrs}h ${mins}m ${secs}s`;
    }
    if (mins > 0) {
      return `${mins}m ${secs}s`;
    }
    return `${secs}s`;
  };

  const fmt = (val, digits = 2) =>
    val === null || val === undefined ? "—" : Number(val).toFixed(digits);

  const renderGcodeAnalysis = () => {
    if (gcodeAnalysis.loading) {
      return (
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
          <CircularProgress size={18} />
          <Typography variant="body2">Analyzing G-code…</Typography>
        </Stack>
      );
    }

    if (gcodeAnalysis.error) {
      return (
        <Alert severity="error" sx={{ mb: 2 }}>
          {gcodeAnalysis.error}
        </Alert>
      );
    }

    if (!gcodeAnalysis.data) return null;

    const a = gcodeAnalysis.data;
    return (
      <Paper variant="outlined" sx={{ p: 2, mb: 2, bgcolor: "grey.50" }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
          <Typography variant="subtitle1">G-code Analysis</Typography>
          <Chip
            size="small"
            label={`${fmt(a.width_mm)}×${fmt(a.height_mm)} mm`}
          />
          <Chip
            size="small"
            label={`Segments: ${a.move_commands} (draw ${a.pen_moves} / travel ${a.travel_moves})`}
          />
        </Stack>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={4}>
            <Typography variant="body2" color="text.secondary">
              Estimated Time
            </Typography>
            <Typography variant="body1" fontWeight={600}>
              {formatMinutes(a.estimated_time_minutes)}
            </Typography>
          </Grid>
          <Grid item xs={12} sm={6} md={4}>
            <Typography variant="body2" color="text.secondary">
              Total Distance
            </Typography>
            <Typography variant="body1" fontWeight={600}>
              {a.total_distance_mm.toFixed(1)} mm
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Draw {a.pen_distance_mm.toFixed(1)} mm • Travel{" "}
              {a.travel_distance_mm.toFixed(1)} mm
            </Typography>
          </Grid>
          <Grid item xs={12} sm={6} md={4}>
            <Typography variant="body2" color="text.secondary">
              Feedrates (assumed)
            </Typography>
            <Typography variant="body1" fontWeight={600}>
              Draw {a.feedrate_assumptions_mm_per_min.draw} / Travel{" "}
              {a.feedrate_assumptions_mm_per_min.travel} mm/min
            </Typography>
            {a.average_feedrate_mm_per_min && (
              <Typography variant="caption" color="text.secondary">
                Avg {a.average_feedrate_mm_per_min} • Min{" "}
                {a.min_feedrate_mm_per_min} • Max {a.max_feedrate_mm_per_min}
              </Typography>
            )}
          </Grid>
          <Grid item xs={12} sm={6} md={4}>
            <Typography variant="body2" color="text.secondary">
              Bounds (min → max)
            </Typography>
            <Typography variant="body1" fontWeight={600}>
              X: {fmt(a.bounds?.minX)} → {fmt(a.bounds?.maxX)} mm
            </Typography>
            <Typography variant="body1" fontWeight={600}>
              Y: {fmt(a.bounds?.minY)} → {fmt(a.bounds?.maxY)} mm
            </Typography>
          </Grid>
        </Grid>
      </Paper>
    );
  };

  const renderSvgAnalysis = () => {
    if (svgAnalysis.loading) {
      return (
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
          <CircularProgress size={18} />
          <Typography variant="body2">Analyzing SVG…</Typography>
        </Stack>
      );
    }

    if (svgAnalysis.error) {
      return (
        <Alert severity="error" sx={{ mb: 2 }}>
          {svgAnalysis.error}
        </Alert>
      );
    }

    if (!svgAnalysis.data) return null;

    const a = svgAnalysis.data;
    return (
      <Paper variant="outlined" sx={{ p: 2, mb: 2, bgcolor: "grey.50" }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
          <Typography variant="subtitle1">SVG Analysis</Typography>
          <Chip
            size="small"
            label={`${fmt(a.width_mm)}×${fmt(a.height_mm)} mm`}
          />
          <Chip
            size="small"
            label={`Paths: ${a.path_count} • Segments: ${a.segment_count}`}
          />
          {a.metadata?.generator_version && (
            <Chip
              size="small"
              color="primary"
              label={`Gen: v${a.metadata.generator_version}`}
            />
          )}
        </Stack>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={4}>
            <Typography variant="body2" color="text.secondary">
              Total Path Length
            </Typography>
            <Typography variant="body1" fontWeight={600}>
              {fmt(a.total_length_mm, 1)} mm
            </Typography>
          </Grid>
          <Grid item xs={12} sm={6} md={4}>
            <Typography variant="body2" color="text.secondary">
              Bounds (min → max)
            </Typography>
            <Typography variant="body1" fontWeight={600}>
              X: {fmt(a.bounds?.minX)} → {fmt(a.bounds?.maxX)} mm
            </Typography>
            <Typography variant="body1" fontWeight={600}>
              Y: {fmt(a.bounds?.minY)} → {fmt(a.bounds?.maxY)} mm
            </Typography>
          </Grid>
          <Grid item xs={12} sm={6} md={4}>
            <Typography variant="body2" color="text.secondary">
              Scale Used
            </Typography>
            <Typography variant="body1" fontWeight={600}>
              {fmt(a.scale_used_mm_per_unit, 4)} mm/unit
            </Typography>
            {a.viewbox && (
              <Typography variant="caption" color="text.secondary">
                viewBox {fmt(a.viewbox.minX, 1)},{fmt(a.viewbox.minY, 1)} →{" "}
                {fmt(a.viewbox.width, 1)}×{fmt(a.viewbox.height, 1)}
              </Typography>
            )}
          </Grid>
          {a.metadata && (
            <Grid item xs={12}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Metadata
              </Typography>
              <Stack spacing={0.5}>
                {a.metadata.source_image && (
                  <Typography variant="body2">
                    Source: {a.metadata.source_image}
                  </Typography>
                )}
                {a.metadata.generated_at && (
                  <Typography variant="body2">
                    Generated: {a.metadata.generated_at}
                  </Typography>
                )}
                {a.metadata.parameters && (
                  <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                    Params: {JSON.stringify(a.metadata.parameters)}
                  </Typography>
                )}
              </Stack>
            </Grid>
          )}
        </Grid>
      </Paper>
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
            <Button
              size="small"
              variant="outlined"
              onClick={handleAnalyzeGcode}
              disabled={gcodeAnalysis.loading}
            >
              {gcodeAnalysis.loading ? "Analyzing…" : "Analyze G-code"}
            </Button>
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
                {renderGcodeAnalysis()}
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
    const icon = isSvg ? (
      <SvgIcon color="primary" />
    ) : (
      <ImageIcon color="primary" />
    );

    return (
      <Box>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
          {icon}
          <Typography variant="h6">
            {isSvg ? "SVG Preview" : "Image Preview"}
          </Typography>
          <Chip label={selectedAsset.displayName} size="small" />
          {!isSvg && isVectorizableAsset(selectedAsset) && (
            <Button
              size="small"
              variant="outlined"
              startIcon={<VectorizeIcon fontSize="small" />}
              onClick={() => openVectorizeDialog(selectedAsset)}
            >
              Vectorize
            </Button>
          )}
          {isSvg && (
            <Button
              size="small"
              variant="outlined"
              onClick={handleAnalyzeSvg}
              disabled={svgAnalysis.loading}
            >
              {svgAnalysis.loading ? "Analyzing…" : "Analyze SVG"}
            </Button>
          )}
        </Stack>
        {isSvg && renderSvgAnalysis()}
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
                {isVectorizableAsset(item) && (
                  <Tooltip title="Vectorize image">
                    <span>
                      <IconButton
                        edge="end"
                        aria-label={`vectorize ${item.displayName}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          openVectorizeDialog(item);
                        }}
                        size="small"
                      >
                        <VectorizeIcon fontSize="small" />
                      </IconButton>
                    </span>
                  </Tooltip>
                )}
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
        <Stack direction="row" spacing={1}>
          <input
            type="file"
            hidden
            ref={fileInputRef}
            onChange={handleFileInputChange}
          />
          <Button
            variant="contained"
            onClick={triggerFilePicker}
            disabled={!currentProject || uploading}
          >
            {uploading ? "Uploading…" : "Upload"}
          </Button>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadAssets}
            disabled={loadingAssets || !currentProject}
          >
            Refresh
          </Button>
        </Stack>
      </Stack>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, height: "100%", minHeight: 420 }}>
            <Stack
              direction="row"
              spacing={1}
              alignItems="center"
              sx={{ mb: 1 }}
            >
              <FileIcon color="primary" />
              <Typography variant="h6">Asset Viewer</Typography>
            </Stack>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Select a file to preview. Includes images, thumbnails, SVGs, and
              G-code.
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
                {renderAssetSection(
                  "Images",
                  assets.images,
                  <ImageIcon fontSize="small" />
                )}
                {renderAssetSection(
                  "SVG",
                  assets.svgs,
                  <SvgIcon fontSize="small" />
                )}
                {renderAssetSection(
                  "G-code",
                  assets.gcode,
                  <CodeIcon fontSize="small" />
                )}
              </Box>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2, minHeight: 420 }}>{renderPreview()}</Paper>
        </Grid>
      </Grid>

      <Dialog
        open={convertDialogOpen}
        onClose={() => setConvertDialogOpen(false)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>Convert SVG to G-code</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <FormControl fullWidth>
              <InputLabel>Paper Size</InputLabel>
              <Select
                label="Paper Size"
                value={convertOptions.paperSize}
                onChange={(e) =>
                  setConvertOptions((prev) => ({
                    ...prev,
                    paperSize: e.target.value,
                  }))
                }
                disabled={!paperOptions.length}
              >
                {paperOptions.map((paper) => (
                  <MenuItem key={paper.id} value={paper.id || paper.paper_size}>
                    {paper.name || paper.paper_size} ({paper.width}×
                    {paper.height}mm)
                    {paper.is_default ? " • default" : ""}
                  </MenuItem>
                ))}
              </Select>
              {!paperOptions.length && (
                <Typography variant="caption" color="text.secondary">
                  No papers configured yet. Add one in Configuration → Papers.
                </Typography>
              )}
              {paperLoadError && (
                <Typography variant="caption" color="error">
                  {paperLoadError}
                </Typography>
              )}
            </FormControl>

            <FormControlLabel
              control={
                <Switch
                  checked={convertOptions.rotate90}
                  onChange={(e) =>
                    setConvertOptions((prev) => ({
                      ...prev,
                      rotate90: e.target.checked,
                    }))
                  }
                  color="primary"
                />
              }
              label="Rotate 90° clockwise (landscape)"
            />

            {/* Fit/center and pen mapping removed; we always center without pen mapping. */}

            {convertError && <Alert severity="error">{convertError}</Alert>}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setConvertDialogOpen(false)}
            disabled={convertLoading}
          >
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

      <VectorizeDialog
        open={vectorizeDialogOpen}
        onClose={handleCloseVectorizeDialog}
        project={vectorizeProject}
      />
    </Box>
  );
}
