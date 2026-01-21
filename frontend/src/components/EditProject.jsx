import {
  Code as CodeIcon,
  AutoFixHigh as ConvertIcon,
  DeleteOutline as DeleteIcon,
  DriveFileRenameOutline as RenameIcon,
  InsertDriveFile as FileIcon,
  Create as GenerateSvgIcon,
  Image as ImageIcon,
  Refresh as RefreshIcon,
  RestartAlt as ResetZoomIcon,
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
  ListItemIcon,
  ListItemText,
  ListSubheader,
  Menu,
  MenuItem,
  Paper,
  Select,
  Slider,
  Stack,
  Switch,
  TextField,
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
  createProjectThumbnail,
  renameProjectFile,
  uploadGcodeToProject,
  uploadImageToProject,
} from "../services/apiService";
import GenerateSvgDialog from "./GenerateSvgDialog";
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
const PAN_STEP = 10;
const SVG_PX_PER_INCH = 96;
const SVG_MM_PER_INCH = 25.4;

function parseSvgLength(value) {
  if (!value) return null;
  const match = String(value).trim().match(/^([+-]?\d*\.?\d+)([a-z%]*)$/i);
  if (!match) return null;
  const number = Number.parseFloat(match[1]);
  if (Number.isNaN(number)) return null;
  const unit = (match[2] || "").toLowerCase();

  switch (unit) {
    case "":
    case "px":
      return number;
    case "mm":
      return (number * SVG_PX_PER_INCH) / SVG_MM_PER_INCH;
    case "cm":
      return (number * SVG_PX_PER_INCH) / (SVG_MM_PER_INCH / 10);
    case "in":
      return number * SVG_PX_PER_INCH;
    case "pt":
      return (number * SVG_PX_PER_INCH) / 72;
    case "pc":
      return (number * SVG_PX_PER_INCH) / 6;
    default:
      return null;
  }
}

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

  const label = meta.is_thumbnail
    ? "Thumbnail"
    : meta.is_processed
    ? "Processed"
    : meta.is_original
    ? "Original"
    : "";

  return {
    filename,
    type,
    label,
    meta: {
      ...meta,
      size: meta.size ?? null,
      created: meta.created ?? null,
      modified: meta.modified ?? null,
    },
    displayName: filename?.split("/").pop() || filename,
  };
}

function groupAssets(imageEntries = [], gcodeEntries = []) {
  const metaByFilename = new Map(
    (imageEntries || [])
      .filter((entry) => entry?.filename)
      .map((entry) => [entry.filename, entry])
  );
  const images = [];
  const svgs = [];

  imageEntries.forEach((entry) => {
    // Skip thumbnail files - they shouldn't appear in the asset viewer
    if (entry.is_thumbnail) {
      return;
    }

    const normalized = normalizeAsset(entry.filename, {
      is_thumbnail: entry.is_thumbnail,
      is_processed: entry.is_processed,
      is_original: entry.is_original,
      size: entry.size,
      created: entry.created,
      modified: entry.modified,
    });
    if (normalized.type === "svg") {
      svgs.push(normalized);
    } else if (normalized.type === "image") {
      images.push(normalized);
    }
  });

  const gcode = (gcodeEntries || []).map((file) => {
    const filename = file || "";
    const meta =
      metaByFilename.get(filename) ||
      metaByFilename.get(filename.split("/").pop()) ||
      {};
    return normalizeAsset(filename, {
      size: meta.size,
      created: meta.created,
      modified: meta.modified,
    }, "gcode");
  });

  return { images, svgs, gcode };
}

function formatFileSize(bytes) {
  if (bytes === null || bytes === undefined || Number.isNaN(Number(bytes))) {
    return "";
  }
  const size = Number(bytes);
  if (size < 1024) return `${size} B`;
  const kb = size / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  const mb = kb / 1024;
  if (mb < 1024) return `${mb.toFixed(1)} MB`;
  const gb = mb / 1024;
  return `${gb.toFixed(1)} GB`;
}

function formatFileDate(isoString) {
  if (!isoString) return "";
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
}

function buildAssetSecondaryText(asset) {
  if (!asset) return undefined;
  const parts = [];
  if (asset.label) parts.push(asset.label);
  const sizeText = formatFileSize(asset.meta?.size);
  if (sizeText) parts.push(sizeText);
  const dateText = formatFileDate(asset.meta?.modified || asset.meta?.created);
  if (dateText) parts.push(dateText);
  return parts.length ? parts.join(" • ") : undefined;
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
  const [contextMenu, setContextMenu] = useState(null);
  const [contextAsset, setContextAsset] = useState(null);
  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [renameValue, setRenameValue] = useState("");
  const [renameError, setRenameError] = useState("");
  const [renaming, setRenaming] = useState(false);
  const [thumbnailLoading, setThumbnailLoading] = useState(false);
  const [isDragActive, setIsDragActive] = useState(false);
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
    suppressM0: false,
    enableOccult: false,
    occultIgnoreLayers: false,
    occultAcrossLayersOnly: false,
    occultKeepOcculted: false,
    enableOptimization: false,
    linemergeTolerance: 0.5,
    linesimplifyTolerance: 0.1,
    reloopTolerance: 0.1,
    linesortEnabled: true,
    linesortTwoOpt: true,
    linesortPasses: 250,
    servoDelayMs: 100.0,
    penDebounceSteps: 7,
  });
  const [convertLoading, setConvertLoading] = useState(false);
  const [convertError, setConvertError] = useState("");
  const [paperOptions, setPaperOptions] = useState([]);
  const [paperLoadError, setPaperLoadError] = useState("");
  const [vectorizeDialogOpen, setVectorizeDialogOpen] = useState(false);
  const [vectorizeProject, setVectorizeProject] = useState(null);
  const [generateSvgDialogOpen, setGenerateSvgDialogOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);
  const [gcodeZoom, setGcodeZoom] = useState(1);
  const [gcodePan, setGcodePan] = useState({ x: 0, y: 0 });
  const [svgContent, setSvgContent] = useState("");
  const [svgContentLoading, setSvgContentLoading] = useState(false);
  const [svgZoom, setSvgZoom] = useState(1);
  const [svgPan, setSvgPan] = useState({ x: 0, y: 0 });
  const [svgDragging, setSvgDragging] = useState(false);
  const [svgDragStart, setSvgDragStart] = useState({ x: 0, y: 0 });
  const svgContainerRef = useRef(null);
  const gcodeCanvasRef = useRef(null);
  const gcodeContainerRef = useRef(null);
  const [gcodeDragging, setGcodeDragging] = useState(false);
  const [gcodeDragStart, setGcodeDragStart] = useState({ x: 0, y: 0 });
  const [imageZoom, setImageZoom] = useState(1);
  const [imagePan, setImagePan] = useState({ x: 0, y: 0 });
  const [imageDragging, setImageDragging] = useState(false);
  const [imageDragStart, setImageDragStart] = useState({ x: 0, y: 0 });
  const imageContainerRef = useRef(null);

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

  const loadAssets = async (preferFilename = "") => {
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
      const allAssets = [...grouped.images, ...grouped.svgs, ...grouped.gcode];
      const preferred = preferFilename
        ? allAssets.find(
            (asset) =>
              asset.filename === preferFilename ||
              asset.displayName === preferFilename
          )
        : null;
      const first = allAssets[0] || null;
      setSelectedAsset(preferred || first);
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
    if (!selectedAsset || selectedAsset.type !== "svg" || !currentProject) {
      setSvgContent("");
      setSvgContentLoading(false);
      return;
    }

    let cancelled = false;
    const loadSvg = async () => {
      setSvgContentLoading(true);
      try {
        const content = await getProjectFileText(
          currentProject.id,
          selectedAsset.filename
        );
        if (!cancelled) {
          setSvgContent(content);
          setSvgContentLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setSvgContent("");
          setSvgContentLoading(false);
        }
      }
    };
    loadSvg();
    return () => {
      cancelled = true;
    };
  }, [selectedAsset, currentProject]);

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

  // Handle global mouse events for SVG dragging
  useEffect(() => {
    if (!svgDragging || !svgContainerRef.current) return;

    const container = svgContainerRef.current;

    const handleMouseMove = (e) => {
      const rect = container.getBoundingClientRect();
      const containerCenterX = rect.width / 2;
      const containerCenterY = rect.height / 2;
      const mouseX = e.clientX - rect.left - containerCenterX;
      const mouseY = e.clientY - rect.top - containerCenterY;

      setSvgPan({
        x: mouseX - svgDragStart.x,
        y: mouseY - svgDragStart.y,
      });
    };

    const handleMouseUp = () => {
      setSvgDragging(false);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [svgDragging, svgDragStart]);

  // Handle global mouse events for G-code dragging
  useEffect(() => {
    if (!gcodeDragging || !gcodeContainerRef.current) return;

    const container = gcodeContainerRef.current;

    const handleMouseMove = (e) => {
      const rect = container.getBoundingClientRect();
      const cx = rect.width / 2;
      const cy = rect.height / 2;
      const mouseX = e.clientX - rect.left - cx;
      const mouseY = e.clientY - rect.top - cy;

      setGcodePan({
        x: mouseX - gcodeDragStart.x,
        y: mouseY - gcodeDragStart.y,
      });
    };

    const handleMouseUp = () => {
      setGcodeDragging(false);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [gcodeDragging, gcodeDragStart]);

  // Handle global mouse events for image dragging
  useEffect(() => {
    if (!imageDragging || !imageContainerRef.current) return;

    const container = imageContainerRef.current;

    const handleMouseMove = (e) => {
      const rect = container.getBoundingClientRect();
      const containerCenterX = rect.width / 2;
      const containerCenterY = rect.height / 2;
      const mouseX = e.clientX - rect.left - containerCenterX;
      const mouseY = e.clientY - rect.top - containerCenterY;

      setImagePan({
        x: mouseX - imageDragStart.x,
        y: mouseY - imageDragStart.y,
      });
    };

    const handleMouseUp = () => {
      setImageDragging(false);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [imageDragging, imageDragStart]);

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

  const handleOpenContextMenu = (event, asset) => {
    event.preventDefault();
    setSelectedAsset(asset);
    setContextAsset(asset);
    setContextMenu({
      mouseX: event.clientX + 2,
      mouseY: event.clientY - 6,
    });
  };

  const handleCloseContextMenu = () => {
    setContextMenu(null);
  };

  const openRenameDialog = (asset) => {
    if (!asset) return;
    setRenameValue(asset.displayName || "");
    setRenameError("");
    setRenameDialogOpen(true);
    handleCloseContextMenu();
  };

  const closeRenameDialog = () => {
    if (renaming) return;
    setRenameDialogOpen(false);
    setRenameError("");
  };

  const handleRename = async () => {
    if (!currentProject || !contextAsset) return;
    const trimmed = renameValue.trim();
    if (!trimmed) {
      setRenameError("File name is required.");
      return;
    }
    if (/[\\/]/.test(trimmed)) {
      setRenameError("File name cannot include path separators.");
      return;
    }
    if (trimmed === contextAsset.displayName) {
      setRenameDialogOpen(false);
      return;
    }

    setRenaming(true);
    setRenameError("");
    try {
      const result = await renameProjectFile(
        currentProject.id,
        contextAsset.filename,
        trimmed
      );
      const newFilename = result.new_filename || trimmed;
      await loadAssets(newFilename);
      setContextAsset((prev) =>
        prev ? { ...prev, filename: newFilename, displayName: trimmed } : prev
      );
      setRenameDialogOpen(false);
    } catch (err) {
      setRenameError(err.message || "Failed to rename file");
    } finally {
      setRenaming(false);
    }
  };

  const handleCreateThumbnail = async (asset) => {
    if (!currentProject || !asset) return;
    setThumbnailLoading(true);
    setAssetError("");
    try {
      await createProjectThumbnail(currentProject.id, asset.filename);
      await loadAssets(asset.filename);
    } catch (err) {
      setAssetError(err.message || "Failed to create thumbnail");
    } finally {
      setThumbnailLoading(false);
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
        suppress_m0: Boolean(convertOptions.suppressM0),
        enable_occult: Boolean(convertOptions.enableOccult),
        occult_ignore_layers: Boolean(convertOptions.occultIgnoreLayers),
        occult_across_layers_only: Boolean(convertOptions.occultAcrossLayersOnly),
        occult_keep_occulted: Boolean(convertOptions.occultKeepOcculted),
        enable_optimization: Boolean(convertOptions.enableOptimization),
        linemerge_tolerance: convertOptions.linemergeTolerance,
        linesimplify_tolerance: convertOptions.linesimplifyTolerance,
        reloop_tolerance: convertOptions.reloopTolerance,
        linesort_enabled: Boolean(convertOptions.linesortEnabled),
        linesort_two_opt: Boolean(convertOptions.linesortTwoOpt),
        linesort_passes: convertOptions.linesortPasses,
        servo_delay_ms: convertOptions.servoDelayMs,
        pen_debounce_steps: convertOptions.penDebounceSteps,
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

  const validateUploadFile = (file) => {
    if (!file) {
      throw new Error("No file selected.");
    }
    const name = (file.name || "").toLowerCase();
    const ext = name.match(/\.[^.]+$/)?.[0]?.slice(1) || "";
    const isSvg = ext === "svg";
    const isGcode = GCODE_EXTENSIONS.includes(ext);
    const isImage = file.type.startsWith("image/") || isSvg;

    if (!isImage && !isGcode) {
      throw new Error(
        "Unsupported file type. Use image/SVG or G-code (.gcode/.nc/.txt)."
      );
    }

    if (file.size > 10 * 1024 * 1024) {
      throw new Error("File size must be less than 10MB");
    }

    return { isGcode };
  };

  const uploadSingleFile = async (file) => {
    if (!currentProject) return;
    const { isGcode } = validateUploadFile(file);
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
  };

  const handleUploadFiles = async (files = []) => {
    if (!currentProject || !files.length) return;
    setAssetError("");
    setUploading(true);
    try {
      for (const file of files) {
        await uploadSingleFile(file);
      }
      await loadAssets();
    } catch (err) {
      setAssetError(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleUploadFile = async (file) => {
    await handleUploadFiles(file ? [file] : []);
  };

  const handleDragOver = (event) => {
    if (!currentProject) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
    setIsDragActive(true);
  };

  const handleDragEnter = (event) => {
    if (!currentProject) return;
    event.preventDefault();
    setIsDragActive(true);
  };

  const handleDragLeave = (event) => {
    if (!event.currentTarget.contains(event.relatedTarget)) {
      setIsDragActive(false);
    }
  };

  const handleDrop = async (event) => {
    if (!currentProject) return;
    event.preventDefault();
    setIsDragActive(false);
    const files = Array.from(event.dataTransfer.files || []);
    await handleUploadFiles(files);
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

  const clampZoom = (value) => Math.min(4, Math.max(0.25, value));
  const handleZoomIn = () => setGcodeZoom((z) => clampZoom(z + 0.25));
  const handleZoomOut = () => setGcodeZoom((z) => clampZoom(z - 0.25));
  const handleZoomReset = () => setGcodeZoom(1);
  const handlePan = (dx, dy) =>
    setGcodePan((p) => ({ x: p.x + dx, y: p.y + dy }));
  const handlePanReset = () => setGcodePan({ x: 0, y: 0 });

  // G-code pan/zoom handlers (mouse)
  const handleGcodeMouseDown = (e) => {
    if (e.button !== 0) return; // Only left mouse button
    if (!gcodeContainerRef.current) return;

    const rect = gcodeContainerRef.current.getBoundingClientRect();
    const cx = rect.width / 2;
    const cy = rect.height / 2;
    const mouseX = e.clientX - rect.left - cx;
    const mouseY = e.clientY - rect.top - cy;

    setGcodeDragging(true);
    setGcodeDragStart({ x: mouseX - gcodePan.x, y: mouseY - gcodePan.y });
    e.preventDefault();
  };

  const handleGcodeMouseMove = (e) => {
    if (gcodeDragging) {
      e.preventDefault();
    }
  };

  const handleGcodeMouseUp = () => {
    setGcodeDragging(false);
  };

  const handleGcodeWheel = (e) => {
    e.preventDefault();
    if (!gcodeContainerRef.current) return;

    const rect = gcodeContainerRef.current.getBoundingClientRect();
    const cx = rect.width / 2;
    const cy = rect.height / 2;
    const mouseX = e.clientX - rect.left - cx;
    const mouseY = e.clientY - rect.top - cy;

    const zoomFactor = e.deltaY > 0 ? 0.95 : 1.05;
    const newZoom = clampZoom(gcodeZoom * zoomFactor);

    const pointX = (mouseX - gcodePan.x) / gcodeZoom;
    const pointY = (mouseY - gcodePan.y) / gcodeZoom;

    const newPanX = mouseX - pointX * newZoom;
    const newPanY = mouseY - pointY * newZoom;

    setGcodeZoom(newZoom);
    setGcodePan({ x: newPanX, y: newPanY });
  };

  const handleGcodeViewReset = () => {
    setGcodeZoom(1);
    setGcodePan({ x: 0, y: 0 });
  };

  // Draw G-code preview on canvas for performance
  useEffect(() => {
    const canvas = gcodeCanvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    const printableSegments = (gcodeGeometry.segments || []).filter(
      (seg) => seg.penDown
    );

    const width = 640;
    const height = 420;
    canvas.width = width;
    canvas.height = height;

    const fillBackground = () => {
      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = "#999999";
      ctx.fillRect(0, 0, width, height);
    };

    if (!printableSegments.length) {
      fillBackground();
      return;
    }

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

    const combinedBounds = bounds
      ? {
          minX: Math.min(bounds.minX, paperBox ? paperBox.minX : bounds.minX),
          maxX: Math.max(bounds.maxX, paperBox ? paperBox.maxX : bounds.maxX),
          minY: Math.min(bounds.minY, paperBox ? paperBox.minY : bounds.minY),
          maxY: Math.max(bounds.maxY, paperBox ? paperBox.maxY : bounds.maxY),
        }
      : paperBox;

    const { minX, maxX, minY, maxY } = combinedBounds || bounds;
    const padding = 16;
    const spanX = Math.max(maxX - minX, 1);
    const spanY = Math.max(maxY - minY, 1);
    const scaleX = (width - padding * 2) / spanX;
    const scaleY = (height - padding * 2) / spanY;
    const baseScale = Math.min(scaleX, scaleY);
    const scale = baseScale * gcodeZoom;
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;

    const mapPoint = (x, y) => ({
      // Positive pan moves the drawing in the same direction as the mouse drag
      x: width / 2 + (x - centerX + gcodePan.x) * scale,
      y: height / 2 - (y - centerY - gcodePan.y) * scale,
    });

    fillBackground();

    // Draw paper outline
    if (paperBox) {
      const tl = mapPoint(paperBox.minX, paperBox.minY);
      const br = mapPoint(paperBox.maxX, paperBox.maxY);
      ctx.save();
      ctx.strokeStyle = "#8bc34a";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([6, 4]);
      ctx.strokeRect(tl.x, tl.y, br.x - tl.x, br.y - tl.y);
      ctx.restore();
    }

    // Draw segments in a single path for speed
    ctx.save();
    ctx.strokeStyle = "#1976d2";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (const seg of printableSegments) {
      const from = mapPoint(seg.from.x, seg.from.y);
      const to = mapPoint(seg.to.x, seg.to.y);
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
    }
    ctx.stroke();
    ctx.restore();
  }, [gcodeGeometry, gcodeZoom, gcodePan, defaultPaper]);

  // SVG pan/zoom handlers
  const handleSvgMouseDown = (e) => {
    if (e.button !== 0) return; // Only left mouse button
    if (!svgContainerRef.current) return;

    const container = svgContainerRef.current;
    const rect = container.getBoundingClientRect();
    const containerCenterX = rect.width / 2;
    const containerCenterY = rect.height / 2;
    const mouseX = e.clientX - rect.left - containerCenterX;
    const mouseY = e.clientY - rect.top - containerCenterY;

    setSvgDragging(true);
    setSvgDragStart({ x: mouseX - svgPan.x, y: mouseY - svgPan.y });
    e.preventDefault();
  };

  const handleSvgMouseMove = (e) => {
    // This is handled by the global event listener in useEffect
    if (svgDragging) {
      e.preventDefault();
    }
  };

  const handleSvgMouseUp = () => {
    setSvgDragging(false);
  };

  const handleSvgWheel = (e) => {
    e.preventDefault();
    if (!svgContainerRef.current) return;

    const container = svgContainerRef.current;
    const rect = container.getBoundingClientRect();

    // Mouse position relative to container center
    const containerCenterX = rect.width / 2;
    const containerCenterY = rect.height / 2;
    const mouseX = e.clientX - rect.left - containerCenterX;
    const mouseY = e.clientY - rect.top - containerCenterY;

    // Calculate zoom factor (smaller steps for smoother zooming)
    const zoomFactor = e.deltaY > 0 ? 0.95 : 1.05;
    const newZoom = clampZoom(svgZoom * zoomFactor);

    // Calculate the point in SVG space before zoom
    // The SVG is centered, so we need to account for pan and current zoom
    const pointX = (mouseX - svgPan.x) / svgZoom;
    const pointY = (mouseY - svgPan.y) / svgZoom;

    // Calculate new pan to keep the mouse position fixed
    const newPanX = mouseX - pointX * newZoom;
    const newPanY = mouseY - pointY * newZoom;

    setSvgZoom(newZoom);
    setSvgPan({ x: newPanX, y: newPanY });
  };

  const handleSvgZoomReset = () => {
    setSvgZoom(1);
    setSvgPan({ x: 0, y: 0 });
  };

  // Image pan/zoom handlers
  const handleImageMouseDown = (e) => {
    if (e.button !== 0) return; // Only left mouse button
    if (!imageContainerRef.current) return;

    const container = imageContainerRef.current;
    const rect = container.getBoundingClientRect();
    const containerCenterX = rect.width / 2;
    const containerCenterY = rect.height / 2;
    const mouseX = e.clientX - rect.left - containerCenterX;
    const mouseY = e.clientY - rect.top - containerCenterY;

    setImageDragging(true);
    setImageDragStart({ x: mouseX - imagePan.x, y: mouseY - imagePan.y });
    e.preventDefault();
  };

  const handleImageMouseMove = (e) => {
    // This is handled by the global event listener in useEffect
    if (imageDragging) {
      e.preventDefault();
    }
  };

  const handleImageMouseUp = () => {
    setImageDragging(false);
  };

  const handleImageWheel = (e) => {
    e.preventDefault();
    if (!imageContainerRef.current) return;

    const container = imageContainerRef.current;
    const rect = container.getBoundingClientRect();

    // Mouse position relative to container center
    const containerCenterX = rect.width / 2;
    const containerCenterY = rect.height / 2;
    const mouseX = e.clientX - rect.left - containerCenterX;
    const mouseY = e.clientY - rect.top - containerCenterY;

    // Calculate zoom factor (smaller steps for smoother zooming)
    const zoomFactor = e.deltaY > 0 ? 0.95 : 1.05;
    const newZoom = clampZoom(imageZoom * zoomFactor);

    // Calculate the point in image space before zoom
    const pointX = (mouseX - imagePan.x) / imageZoom;
    const pointY = (mouseY - imagePan.y) / imageZoom;

    // Calculate new pan to keep the mouse position fixed
    const newPanX = mouseX - pointX * newZoom;
    const newPanY = mouseY - pointY * newZoom;

    setImageZoom(newZoom);
    setImagePan({ x: newPanX, y: newPanY });
  };

  const handleImageZoomReset = () => {
    setImageZoom(1);
    setImagePan({ x: 0, y: 0 });
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
    // Refresh assets after vectorization
    if (currentProject) {
      loadAssets();
    }
  };

  const openGenerateSvgDialog = () => {
    if (!currentProject) return;
    setGenerateSvgDialogOpen(true);
  };

  const handleCloseGenerateSvgDialog = () => {
    setGenerateSvgDialogOpen(false);
    // Refresh assets after generation
    if (currentProject) {
      loadAssets();
    }
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
          minX: Math.min(bounds.minX, paperBox ? paperBox.minX : bounds.minX),
          maxX: Math.max(bounds.maxX, paperBox ? paperBox.maxX : bounds.maxX),
          minY: Math.min(bounds.minY, paperBox ? paperBox.minY : bounds.minY),
          maxY: Math.max(bounds.maxY, paperBox ? paperBox.maxY : bounds.maxY),
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
    const baseScale = Math.min(scaleX, scaleY);
    const scale = baseScale * gcodeZoom;
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;

    const mapPoint = (x, y) => ({
      x: width / 2 + (x - centerX - gcodePan.x) * scale,
      // Flip Y so higher Y is up visually
      y: height / 2 - (y - centerY - gcodePan.y) * scale,
    });

    return (
      <Box sx={{ mb: 2 }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
          <CodeIcon color="primary" />
          <Typography variant="subtitle1">G-code Plot Preview</Typography>
          <Chip label={`${printableSegments.length} segments`} size="small" />
          <Box sx={{ flexGrow: 1 }} />
          <Button
            size="small"
            variant="outlined"
            startIcon={<ResetZoomIcon fontSize="small" />}
            onClick={handleGcodeViewReset}
            disabled={gcodeZoom === 1 && gcodePan.x === 0 && gcodePan.y === 0}
          >
            Reset View
          </Button>
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
            ref={gcodeContainerRef}
            onMouseDown={handleGcodeMouseDown}
            onMouseMove={handleGcodeMouseMove}
            onMouseUp={handleGcodeMouseUp}
            onMouseLeave={handleGcodeMouseUp}
            onWheel={handleGcodeWheel}
            sx={{
              width: "100%",
              maxHeight: 460,
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              cursor: gcodeDragging ? "grabbing" : "grab",
              userSelect: "none",
              overflow: "hidden",
            }}
          >
            <canvas
              ref={gcodeCanvasRef}
              style={{
                width: "100%",
                height: "100%",
              }}
            />
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
          {!isSvg && (
            <Button
              size="small"
              variant="outlined"
              startIcon={<ResetZoomIcon fontSize="small" />}
              onClick={handleImageZoomReset}
              disabled={imageZoom === 1 && imagePan.x === 0 && imagePan.y === 0}
            >
              Reset View
            </Button>
          )}
          {isSvg && (
            <>
              <Button
                size="small"
                variant="outlined"
                onClick={handleAnalyzeSvg}
                disabled={svgAnalysis.loading}
              >
                {svgAnalysis.loading ? "Analyzing…" : "Analyze SVG"}
              </Button>
              <Button
                size="small"
                variant="outlined"
                startIcon={<ResetZoomIcon fontSize="small" />}
                onClick={handleSvgZoomReset}
                disabled={svgZoom === 1 && svgPan.x === 0 && svgPan.y === 0}
              >
                Reset View
              </Button>
            </>
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
            bgcolor: "grey.200",
            minHeight: 320,
          }}
        >
          <Box
            sx={{
              bgcolor: "#bdbdbd",
              p: 2,
              borderRadius: 1,
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              width: "100%",
              maxWidth: "100%",
            }}
          >
            {isSvg ? (
              svgContentLoading ? (
                <CircularProgress />
              ) : svgContent ? (
                <Box
                  ref={svgContainerRef}
                  component="div"
                  onMouseDown={handleSvgMouseDown}
                  onMouseMove={handleSvgMouseMove}
                  onMouseUp={handleSvgMouseUp}
                  onMouseLeave={handleSvgMouseUp}
                  onWheel={handleSvgWheel}
                  sx={{
                    maxWidth: "100%",
                    maxHeight: 600,
                    borderRadius: 1,
                    boxShadow: 1,
                    overflow: "hidden",
                    bgcolor: "#bdbdbd",
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                    cursor: svgDragging ? "grabbing" : "grab",
                    userSelect: "none",
                    position: "relative",
                    "& svg": {
                      display: "block",
                      maxWidth: "100%",
                      maxHeight: "600px",
                      width: "100%",
                      height: "auto",
                      backgroundColor: "#bdbdbd",
                      objectFit: "contain",
                      transform: `translate(${svgPan.x}px, ${svgPan.y}px) scale(${svgZoom})`,
                      transformOrigin: "center center",
                      transition: svgDragging
                        ? "none"
                        : "transform 0.1s ease-out",
                    },
                  }}
                  dangerouslySetInnerHTML={{
                    __html: svgContent.replace(
                      /<svg([^>]*)>/i,
                      (match, attrs) => {
                        // Extract width and height from attributes if present
                        const widthMatch = attrs.match(
                          /width=["']([^"']+)["']/
                        );
                        const heightMatch = attrs.match(
                          /height=["']([^"']+)["']/
                        );
                        const viewBoxMatch = attrs.match(
                          /viewBox=["']([^"']+)["']/
                        );

                        let rectWidth = "100%";
                        let rectHeight = "100%";
                        let computedViewBox = null;

                        // Use viewBox if available, otherwise use width/height
                        if (viewBoxMatch) {
                          const viewBox = viewBoxMatch[1].trim().split(/[\s,]+/);
                          if (viewBox.length >= 4) {
                            rectWidth = viewBox[2];
                            rectHeight = viewBox[3];
                          }
                        } else if (widthMatch && heightMatch) {
                          const widthRaw = widthMatch[1];
                          const heightRaw = heightMatch[1];
                          const widthPx = parseSvgLength(widthRaw);
                          const heightPx = parseSvgLength(heightRaw);

                          if (widthPx !== null && heightPx !== null) {
                            rectWidth = String(widthPx);
                            rectHeight = String(heightPx);
                            computedViewBox = `0 0 ${rectWidth} ${rectHeight}`;
                          } else {
                            rectWidth = widthRaw;
                            rectHeight = heightRaw;
                          }
                        }

                        // Add viewBox if it doesn't exist but width/height do
                        let newAttrs = attrs;
                        if (!viewBoxMatch && computedViewBox) {
                          newAttrs = `${attrs} viewBox="${computedViewBox}"`;
                        }

                        // Preserve original SVG attributes but add background
                        return `<svg${newAttrs} style="background-color: #bdbdbd; max-width: 100%; max-height: 600px; width: 100%; height: auto;"><rect x="0" y="0" width="${rectWidth}" height="${rectHeight}" fill="#bdbdbd"/>`;
                      }
                    ),
                  }}
                />
              ) : (
                <Box
                  component="object"
                  data={getProjectFileUrl(
                    currentProject.id,
                    selectedAsset.filename
                  )}
                  type="image/svg+xml"
                  sx={{
                    maxWidth: "100%",
                    maxHeight: 600,
                    borderRadius: 1,
                    boxShadow: 1,
                    bgcolor: "#bdbdbd",
                  }}
                  aria-label={selectedAsset.displayName}
                />
              )
            ) : (
              <Box
                ref={imageContainerRef}
                onMouseDown={handleImageMouseDown}
                onMouseMove={handleImageMouseMove}
                onMouseUp={handleImageMouseUp}
                onMouseLeave={handleImageMouseUp}
                onWheel={handleImageWheel}
                sx={{
                  maxWidth: "100%",
                  maxHeight: 600,
                  borderRadius: 1,
                  boxShadow: 1,
                  overflow: "hidden",
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                  cursor: imageDragging ? "grabbing" : "grab",
                  userSelect: "none",
                  position: "relative",
                }}
              >
                <Box
                  component="img"
                  src={getProjectFileUrl(
                    currentProject.id,
                    selectedAsset.filename
                  )}
                  alt={selectedAsset.displayName}
                  sx={{
                    maxWidth: "100%",
                    maxHeight: 600,
                    borderRadius: 1,
                    boxShadow: 1,
                    objectFit: "contain",
                    transform: `translate(${imagePan.x}px, ${imagePan.y}px) scale(${imageZoom})`,
                    transformOrigin: "center center",
                    transition: imageDragging
                      ? "none"
                      : "transform 0.1s ease-out",
                  }}
                />
              </Box>
            )}
          </Box>
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
            secondaryAction={null}
          >
            <ListItemButton
              selected={selectedAsset?.filename === item.filename}
              onClick={() => setSelectedAsset(item)}
              onContextMenu={(event) => handleOpenContextMenu(event, item)}
            >
            <ListItemText
              primary={item.displayName}
              secondary={buildAssetSecondaryText(item)}
            />
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
          <Button
            variant="outlined"
            startIcon={<GenerateSvgIcon />}
            onClick={openGenerateSvgDialog}
            disabled={!currentProject}
          >
            Generate SVG
          </Button>
        </Stack>
      </Stack>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Paper
            sx={{
              p: 2,
              height: "100%",
              minHeight: 420,
              border: isDragActive ? "2px dashed" : undefined,
              borderColor: isDragActive ? "primary.main" : undefined,
              bgcolor: isDragActive ? "action.hover" : undefined,
              position: "relative",
            }}
            onDragOver={handleDragOver}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            {isDragActive && (
              <Box
                sx={{
                  position: "absolute",
                  inset: 0,
                  zIndex: 1,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  pointerEvents: "none",
                }}
              >
                <Paper
                  elevation={2}
                  sx={{ px: 2, py: 1, bgcolor: "background.paper" }}
                >
                  <Typography variant="body2" color="text.secondary">
                    Drop files to upload
                  </Typography>
                </Paper>
              </Box>
            )}
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
              Select a file to preview. Includes images, SVGs, and G-code.
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

            <FormControlLabel
              control={
                <Switch
                  checked={convertOptions.suppressM0}
                  onChange={(e) =>
                    setConvertOptions((prev) => ({
                      ...prev,
                      suppressM0: e.target.checked,
                    }))
                  }
                  color="primary"
                />
              }
              label="Suppress M0 pen changes (print in one color)"
            />

            <Divider sx={{ my: 2 }} />

            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
              Hidden Line Removal (Occult)
            </Typography>

            <FormControlLabel
              control={
                <Switch
                  checked={convertOptions.enableOccult}
                  onChange={(e) =>
                    setConvertOptions((prev) => ({
                      ...prev,
                      enableOccult: e.target.checked,
                    }))
                  }
                  color="primary"
                />
              }
              label="Enable hidden line removal (occult)"
            />

            {convertOptions.enableOccult && (
              <Box sx={{ pl: 3, mt: 1 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={convertOptions.occultIgnoreLayers}
                      onChange={(e) =>
                        setConvertOptions((prev) => ({
                          ...prev,
                          occultIgnoreLayers: e.target.checked,
                          occultAcrossLayersOnly: e.target.checked
                            ? false
                            : prev.occultAcrossLayersOnly,
                        }))
                      }
                      disabled={convertOptions.occultAcrossLayersOnly}
                      color="primary"
                    />
                  }
                  label="Ignore layers (-i) - Perform occlusion across all layers"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={convertOptions.occultAcrossLayersOnly}
                      onChange={(e) =>
                        setConvertOptions((prev) => ({
                          ...prev,
                          occultAcrossLayersOnly: e.target.checked,
                          occultIgnoreLayers: e.target.checked
                            ? false
                            : prev.occultIgnoreLayers,
                        }))
                      }
                      color="primary"
                    />
                  }
                  label="Across layers only (-a) - Only occlude across layers, not within"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={convertOptions.occultKeepOcculted}
                      onChange={(e) =>
                        setConvertOptions((prev) => ({
                          ...prev,
                          occultKeepOcculted: e.target.checked,
                        }))
                      }
                      color="primary"
                    />
                  }
                  label="Keep occulted lines (-k) - Keep removed lines in separate layer"
                />
              </Box>
            )}

            <Divider sx={{ my: 2 }} />

            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
              G-code Optimization
            </Typography>

            <FormControlLabel
              control={
                <Switch
                  checked={convertOptions.enableOptimization}
                  onChange={(e) =>
                    setConvertOptions((prev) => ({
                      ...prev,
                      enableOptimization: e.target.checked,
                    }))
                  }
                  color="primary"
                />
              }
              label="Enable G-code optimization"
            />

            {convertOptions.enableOptimization && (
              <Box sx={{ pl: 3, mt: 1 }}>
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    Linemerge tolerance: {convertOptions.linemergeTolerance.toFixed(2)}mm
                  </Typography>
                  <Slider
                    value={convertOptions.linemergeTolerance}
                    onChange={(e, value) =>
                      setConvertOptions((prev) => ({
                        ...prev,
                        linemergeTolerance: value,
                      }))
                    }
                    min={0.01}
                    max={2.0}
                    step={0.01}
                    valueLabelDisplay="auto"
                    disabled={convertLoading}
                  />
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    Linesimplify tolerance: {convertOptions.linesimplifyTolerance.toFixed(2)}mm
                  </Typography>
                  <Slider
                    value={convertOptions.linesimplifyTolerance}
                    onChange={(e, value) =>
                      setConvertOptions((prev) => ({
                        ...prev,
                        linesimplifyTolerance: value,
                      }))
                    }
                    min={0.01}
                    max={1.0}
                    step={0.01}
                    valueLabelDisplay="auto"
                    disabled={convertLoading}
                  />
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    Reloop tolerance: {convertOptions.reloopTolerance.toFixed(2)}mm
                  </Typography>
                  <Slider
                    value={convertOptions.reloopTolerance}
                    onChange={(e, value) =>
                      setConvertOptions((prev) => ({
                        ...prev,
                        reloopTolerance: value,
                      }))
                    }
                    min={0.01}
                    max={1.0}
                    step={0.01}
                    valueLabelDisplay="auto"
                    disabled={convertLoading}
                  />
                </Box>

                <FormControlLabel
                  control={
                    <Switch
                      checked={convertOptions.linesortEnabled}
                      onChange={(e) =>
                        setConvertOptions((prev) => ({
                          ...prev,
                          linesortEnabled: e.target.checked,
                        }))
                      }
                      color="primary"
                    />
                  }
                  label="Enable linesort"
                />

                <Box sx={{ pl: 3, mt: 1 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={convertOptions.linesortTwoOpt}
                        onChange={(e) =>
                          setConvertOptions((prev) => ({
                            ...prev,
                            linesortTwoOpt: e.target.checked,
                          }))
                        }
                        disabled={!convertOptions.linesortEnabled}
                        color="primary"
                      />
                    }
                    label="Use two-opt algorithm"
                  />

                  <Box sx={{ mb: 2, mt: 2 }}>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      Linesort passes: {convertOptions.linesortPasses}
                    </Typography>
                    <Slider
                      value={convertOptions.linesortPasses}
                      onChange={(e, value) =>
                        setConvertOptions((prev) => ({
                          ...prev,
                          linesortPasses: value,
                        }))
                      }
                      min={1}
                      max={1000}
                      step={1}
                      valueLabelDisplay="auto"
                      disabled={convertLoading || !convertOptions.linesortEnabled}
                    />
                  </Box>
                </Box>
              </Box>
            )}

            <Divider sx={{ my: 2 }} />

            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
              Pen Control (Servo Debounce)
            </Typography>

            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Servo delay after pen down: {convertOptions.servoDelayMs.toFixed(0)}ms
              </Typography>
              <Slider
                value={convertOptions.servoDelayMs}
                onChange={(e, value) =>
                  setConvertOptions((prev) => ({
                    ...prev,
                    servoDelayMs: value,
                  }))
                }
                min={0}
                max={500}
                step={10}
                valueLabelDisplay="auto"
                disabled={convertLoading}
              />
              <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                Delay after pen down to allow servo to settle (reduces bouncing)
              </Typography>
            </Box>

            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Pen debounce steps: {convertOptions.penDebounceSteps}
              </Typography>
              <Slider
                value={convertOptions.penDebounceSteps}
                onChange={(e, value) =>
                  setConvertOptions((prev) => ({
                    ...prev,
                    penDebounceSteps: value,
                  }))
                }
                min={1}
                max={15}
                step={1}
                valueLabelDisplay="auto"
                disabled={convertLoading}
              />
              <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                Number of M280 commands for exponential pen down approach (more steps = smoother but slower)
              </Typography>
            </Box>

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
        {contextAsset &&
          (contextAsset.type === "image" || contextAsset.type === "svg") &&
          !contextAsset.meta?.is_thumbnail && (
            <MenuItem
              onClick={() => {
                handleCloseContextMenu();
                handleCreateThumbnail(contextAsset);
              }}
              disabled={thumbnailLoading}
            >
              <ListItemIcon>
                <ImageIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>Set as Project Thumbnail</ListItemText>
            </MenuItem>
          )}
        <MenuItem onClick={() => openRenameDialog(contextAsset)} disabled={!contextAsset}>
          <ListItemIcon>
            <RenameIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Rename</ListItemText>
        </MenuItem>
        {contextAsset && isVectorizableAsset(contextAsset) && (
          <MenuItem
            onClick={() => {
              handleCloseContextMenu();
              openVectorizeDialog(contextAsset);
            }}
          >
            <ListItemIcon>
              <VectorizeIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>Vectorize</ListItemText>
          </MenuItem>
        )}
        {contextAsset?.type === "svg" && (
          <MenuItem
            onClick={() => {
              handleCloseContextMenu();
              openConvertDialog(contextAsset);
            }}
          >
            <ListItemIcon>
              <ConvertIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>Convert to G-code</ListItemText>
          </MenuItem>
        )}
        <MenuItem
          onClick={() => {
            handleCloseContextMenu();
            handleDeleteAsset(contextAsset);
          }}
          disabled={!contextAsset}
        >
          <ListItemIcon>
            <DeleteIcon fontSize="small" color="error" />
          </ListItemIcon>
          <ListItemText>Delete</ListItemText>
        </MenuItem>
      </Menu>

      <Dialog open={renameDialogOpen} onClose={closeRenameDialog} maxWidth="xs" fullWidth>
        <DialogTitle>Rename File</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            margin="dense"
            label="File name"
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            error={Boolean(renameError)}
            helperText={renameError || " "}
            disabled={renaming}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleRename();
              }
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={closeRenameDialog} disabled={renaming}>
            Cancel
          </Button>
          <Button variant="contained" onClick={handleRename} disabled={renaming}>
            {renaming ? "Renaming..." : "Rename"}
          </Button>
        </DialogActions>
      </Dialog>

      <VectorizeDialog
        open={vectorizeDialogOpen}
        onClose={handleCloseVectorizeDialog}
        project={vectorizeProject}
      />

      <GenerateSvgDialog
        open={generateSvgDialogOpen}
        onClose={handleCloseGenerateSvgDialog}
        project={currentProject}
      />
    </Box>
  );
}
