from typing import Optional, Dict, Literal, Any

from pydantic import BaseModel


class PlotterConnectRequest(BaseModel):
    port: str
    baud_rate: int = 115200


class GcodeRequest(BaseModel):
    command: str


class ProjectGcodeRunRequest(BaseModel):
    filename: str


class SvgToGcodeRequest(BaseModel):
    filename: str
    paper_size: str = "A4"
    pen_mapping: Optional[Dict[str, Any]] = None
    origin_mode: Literal["lower_left", "center"] = "lower_left"
    rotate_90: bool = False
    suppress_m0: bool = False  # If True, skip M0 pen change commands (print in one color)
    enable_occult: bool = False  # If True, remove hidden/occluded lines using vpype-occult
    occult_ignore_layers: bool = False  # If True, perform occlusion across all layers (-i flag)
    occult_across_layers_only: bool = False  # If True, only occlude across layers, not within (-a flag, overrides -i)
    occult_keep_occulted: bool = False  # If True, keep removed lines in separate layer (-k flag)
    enable_optimization: bool = False  # If True, apply G-code optimization commands
    linemerge_tolerance: float = 0.5  # Tolerance in mm for linemerge command
    linesimplify_tolerance: float = 0.1  # Tolerance in mm for linesimplify command
    reloop_tolerance: float = 0.1  # Tolerance in mm for reloop command
    linesort_enabled: bool = True  # Enable linesort when optimization is enabled
    linesort_two_opt: bool = True  # Use two-opt algorithm for linesort
    linesort_passes: int = 250  # Number of passes for linesort
    servo_delay_ms: float = 100.0  # Delay in milliseconds after pen down to allow servo settling
    pen_debounce_steps: int = 7  # Number of M280 commands for exponential pen down approach (reduces bouncing)


class GcodeAnalysisResult(BaseModel):
    filename: Optional[str] = None
    lines_processed: int
    move_commands: int
    pen_moves: int
    travel_moves: int
    total_distance_mm: float
    pen_distance_mm: float
    travel_distance_mm: float
    bounds: Optional[Dict[str, float]] = None
    width_mm: Optional[float] = None
    height_mm: Optional[float] = None
    estimated_time_seconds: float
    estimated_time_minutes: float
    feedrate_assumptions_mm_per_min: Dict[str, float]
    average_feedrate_mm_per_min: Optional[float] = None
    max_feedrate_mm_per_min: Optional[float] = None
    min_feedrate_mm_per_min: Optional[float] = None
    absolute_mode: bool = True


class SvgAnalysisResult(BaseModel):
    filename: Optional[str] = None
    path_count: int
    segment_count: int
    total_length_mm: float
    bounds: Optional[Dict[str, float]] = None
    width_mm: Optional[float] = None
    height_mm: Optional[float] = None
    viewbox: Optional[Dict[str, float]] = None
    scale_used_mm_per_unit: float
    metadata: Optional[Dict[str, Any]] = None
