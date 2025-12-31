from typing import Optional, Dict, Literal, Any

from pydantic import BaseModel


class PlotterConnectRequest(BaseModel):
    port: str
    baud_rate: int = 9600


class GcodeRequest(BaseModel):
    command: str


class ProjectGcodeRunRequest(BaseModel):
    filename: str


class SvgToGcodeRequest(BaseModel):
    filename: str
    paper_size: str = "A4"
    pen_mapping: Optional[str] = None
    origin_mode: Literal["lower_left", "center"] = "lower_left"
    rotate_90: bool = False


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
