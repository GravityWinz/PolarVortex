from typing import Optional, Dict

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
    fit_mode: str = "fit"  # fit | center
    pen_mapping: Optional[str] = None


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
