from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class GcodeSettings(BaseModel):
    """Settings for automatic G-code sequences and pen control commands"""
    on_connect: List[str] = Field(default_factory=list, description="Commands to run right after connecting to the plotter")
    before_print: List[str] = Field(default_factory=list, description="Commands to run just before starting a print job")
    pen_up_command: str = Field(default="M280 P0 S110", description="Command to raise pen")
    pen_down_command: str = Field(default="M280 P0 S130", description="Command to lower pen")


class GcodeSettingsUpdate(BaseModel):
    """Model for updating automatic G-code sequences"""
    on_connect: Optional[List[str]] = Field(None, description="Commands to run after connect")
    before_print: Optional[List[str]] = Field(None, description="Commands to run before print start")
    pen_up_command: Optional[str] = Field(None, description="Command to raise pen")
    pen_down_command: Optional[str] = Field(None, description="Command to lower pen")


class PlotterType(str, Enum):
    """Enum for different plotter types"""
    POLARGRAPH = "polargraph"
    XY_PLOTTER = "xy_plotter"
    PEN_PLOTTER = "pen_plotter"


class PaperSize(str, Enum):
    """Enum for standard paper sizes"""
    # European A series
    A5 = "A5"
    A4 = "A4"
    A3 = "A3"
    A2 = "A2"
    A1 = "A1"
    A0 = "A0"
    # US paper sizes
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    LETTER = "Letter"
    LEGAL = "Legal"
    TABLOID = "Tabloid"
    CUSTOM = "Custom"


class PlotterSettings(BaseModel):
    """Settings for a specific plotter configuration"""
    name: str = Field(..., description="Name of the plotter configuration")
    plotter_type: PlotterType = Field(..., description="Type of plotter")
    width: float = Field(..., description="Plotting area width in mm")
    height: float = Field(..., description="Plotting area height in mm")
    mm_per_rev: float = Field(..., description="Millimeters per motor revolution")
    steps_per_rev: float = Field(..., description="Steps per motor revolution")
    max_speed: float = Field(default=100.0, description="Maximum speed in mm/s")
    acceleration: float = Field(default=50.0, description="Acceleration in mm/s²")
    pen_up_position: float = Field(default=10.0, description="Pen up position in mm")
    pen_down_position: float = Field(default=0.0, description="Pen down position in mm")
    pen_speed: float = Field(default=20.0, description="Pen movement speed in mm/s")
    gcode_sequences: GcodeSettings = Field(default_factory=GcodeSettings, description="Automatic G-code for this plotter")
    home_position_x: float = Field(default=0.0, description="Home position X coordinate")
    home_position_y: float = Field(default=0.0, description="Home position Y coordinate")
    is_default: bool = Field(default=False, description="Whether this is the default plotter")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class PaperSettings(BaseModel):
    """Settings for a specific paper configuration"""
    name: str = Field(..., description="Name of the paper configuration")
    paper_size: PaperSize = Field(..., description="Standard paper size")
    width: float = Field(..., description="Paper width in mm")
    height: float = Field(..., description="Paper height in mm")
    color: str = Field(default="white", description="Paper color")
    is_default: bool = Field(default=False, description="Whether this is the default paper")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class PlotterCreate(BaseModel):
    """Model for creating a new plotter configuration"""
    name: str = Field(..., description="Name of the plotter configuration")
    plotter_type: PlotterType = Field(default=PlotterType.POLARGRAPH, description="Type of plotter")
    width: float = Field(default=1000.0, description="Plotting area width in mm")
    height: float = Field(default=1000.0, description="Plotting area height in mm")
    mm_per_rev: float = Field(default=95.0, description="Millimeters per motor revolution")
    steps_per_rev: float = Field(default=200.0, description="Steps per motor revolution")
    max_speed: float = Field(default=100.0, description="Maximum speed in mm/s")
    acceleration: float = Field(default=50.0, description="Acceleration in mm/s²")
    pen_up_position: float = Field(default=10.0, description="Pen up position in mm")
    pen_down_position: float = Field(default=0.0, description="Pen down position in mm")
    pen_speed: float = Field(default=20.0, description="Pen movement speed in mm/s")
    gcode_sequences: GcodeSettings = Field(default_factory=GcodeSettings, description="Automatic G-code for this plotter")
    home_position_x: float = Field(default=0.0, description="Home position X coordinate")
    home_position_y: float = Field(default=0.0, description="Home position Y coordinate")
    is_default: bool = Field(default=False, description="Whether this is the default plotter")


class PlotterUpdate(BaseModel):
    """Model for updating a plotter configuration"""
    name: Optional[str] = Field(None, description="Name of the plotter configuration")
    plotter_type: Optional[PlotterType] = Field(None, description="Type of plotter")
    width: Optional[float] = Field(None, description="Plotting area width in mm")
    height: Optional[float] = Field(None, description="Plotting area height in mm")
    mm_per_rev: Optional[float] = Field(None, description="Millimeters per motor revolution")
    steps_per_rev: Optional[float] = Field(None, description="Steps per motor revolution")
    max_speed: Optional[float] = Field(None, description="Maximum speed in mm/s")
    acceleration: Optional[float] = Field(None, description="Acceleration in mm/s²")
    pen_up_position: Optional[float] = Field(None, description="Pen up position in mm")
    pen_down_position: Optional[float] = Field(None, description="Pen down position in mm")
    pen_speed: Optional[float] = Field(None, description="Pen movement speed in mm/s")
    gcode_sequences: Optional[GcodeSettings] = Field(None, description="Automatic G-code for this plotter")
    home_position_x: Optional[float] = Field(None, description="Home position X coordinate")
    home_position_y: Optional[float] = Field(None, description="Home position Y coordinate")
    is_default: Optional[bool] = Field(None, description="Whether this is the default plotter")


class PaperCreate(BaseModel):
    """Model for creating a new paper configuration"""
    name: str = Field(..., description="Name of the paper configuration")
    paper_size: PaperSize = Field(..., description="Standard paper size")
    width: float = Field(..., description="Paper width in mm")
    height: float = Field(..., description="Paper height in mm")
    color: str = Field(default="white", description="Paper color")
    is_default: bool = Field(default=False, description="Whether this is the default paper")


class PaperUpdate(BaseModel):
    """Model for updating a paper configuration"""
    name: Optional[str] = Field(None, description="Name of the paper configuration")
    paper_size: Optional[PaperSize] = Field(None, description="Standard paper size")
    width: Optional[float] = Field(None, description="Paper width in mm")
    height: Optional[float] = Field(None, description="Paper height in mm")
    color: Optional[str] = Field(None, description="Paper color")
    is_default: Optional[bool] = Field(None, description="Whether this is the default paper")


class PlotterResponse(BaseModel):
    """Response model for plotter configuration"""
    id: str = Field(..., description="Unique identifier for the plotter")
    name: str = Field(..., description="Name of the plotter configuration")
    plotter_type: PlotterType = Field(..., description="Type of plotter")
    width: float = Field(..., description="Plotting area width in mm")
    height: float = Field(..., description="Plotting area height in mm")
    mm_per_rev: float = Field(..., description="Millimeters per motor revolution")
    steps_per_rev: float = Field(..., description="Steps per motor revolution")
    max_speed: float = Field(..., description="Maximum speed in mm/s")
    acceleration: float = Field(..., description="Acceleration in mm/s²")
    pen_up_position: float = Field(..., description="Pen up position in mm")
    pen_down_position: float = Field(..., description="Pen down position in mm")
    pen_speed: float = Field(..., description="Pen movement speed in mm/s")
    gcode_sequences: GcodeSettings = Field(..., description="Automatic G-code for this plotter")
    home_position_x: float = Field(..., description="Home position X coordinate")
    home_position_y: float = Field(..., description="Home position Y coordinate")
    is_default: bool = Field(..., description="Whether this is the default plotter")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class PaperResponse(BaseModel):
    """Response model for paper configuration"""
    id: str = Field(..., description="Unique identifier for the paper")
    name: str = Field(..., description="Name of the paper configuration")
    paper_size: PaperSize = Field(..., description="Standard paper size")
    width: float = Field(..., description="Paper width in mm")
    height: float = Field(..., description="Paper height in mm")
    color: str = Field(..., description="Paper color")
    is_default: bool = Field(..., description="Whether this is the default paper")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class PlotterListResponse(BaseModel):
    """Response model for listing plotters"""
    plotters: List[PlotterResponse] = Field(..., description="List of plotter configurations")
    total: int = Field(..., description="Total number of plotters")


class PaperListResponse(BaseModel):
    """Response model for listing papers"""
    papers: List[PaperResponse] = Field(..., description="List of paper configurations")
    total: int = Field(..., description="Total number of papers")


class ConfigurationResponse(BaseModel):
    """Response model for general configuration"""
    plotters: List[PlotterResponse] = Field(..., description="List of plotter configurations")
    papers: List[PaperResponse] = Field(..., description="List of paper configurations")
    default_plotter: Optional[PlotterResponse] = Field(None, description="Default plotter configuration")
    default_paper: Optional[PaperResponse] = Field(None, description="Default paper configuration")
    gcode: GcodeSettings = Field(default_factory=GcodeSettings, description="Automatic G-code sequences")
