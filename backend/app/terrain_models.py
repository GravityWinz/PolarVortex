from pydantic import BaseModel, Field, model_validator
from typing import Optional


class TerrainBbox(BaseModel):
    minLat: float = Field(..., description="Minimum latitude")
    minLon: float = Field(..., description="Minimum longitude")
    maxLat: float = Field(..., description="Maximum latitude")
    maxLon: float = Field(..., description="Maximum longitude")

    @model_validator(mode="after")
    def validate_bounds(self):
        min_lat = self.minLat
        max_lat = self.maxLat
        min_lon = self.minLon
        max_lon = self.maxLon

        if min_lat >= max_lat:
            raise ValueError("minLat must be less than maxLat")
        if min_lon >= max_lon:
            raise ValueError("minLon must be less than maxLon")

        if not (-90 <= min_lat <= 90) or not (-90 <= max_lat <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        if not (-180 <= min_lon <= 180) or not (-180 <= max_lon <= 180):
            raise ValueError("Longitude must be between -180 and 180")

        return self


class TerrainRidgelineRequest(BaseModel):
    bbox: TerrainBbox
    paper_id: Optional[str] = Field(None, description="Paper configuration ID")
    paper_size: Optional[str] = Field(None, description="Fallback paper size label")
    rows: int = Field(default=80, ge=10, le=300, description="Number of ridgeline rows")
    cols: int = Field(default=240, ge=20, le=800, description="Samples per row")
    row_spacing: float = Field(default=2.0, gt=0, description="Row spacing in mm")
    height_scale: float = Field(default=0.03, gt=0, description="Height scale (mm per meter)")
    stroke_width: float = Field(default=0.35, gt=0, description="Stroke width in mm")
    stroke_color: str = Field(default="#000000", description="Stroke color")


class TerrainRidgelineResponse(BaseModel):
    success: bool
    svg: str
    width_mm: float
    height_mm: float
    paper_name: Optional[str] = None
