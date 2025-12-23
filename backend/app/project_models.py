from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid


class ProjectCreate(BaseModel):
    """Model for creating a new project"""
    name: str = Field(..., description="User-readable project name", min_length=1, max_length=100)


class VectorizationInfo(BaseModel):
    """Model for vectorization information"""
    svg_filename: Optional[str] = Field(default=None, description="Filename of the generated SVG")
    vectorized_at: Optional[datetime] = Field(default=None, description="Timestamp when vectorization was performed")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Vectorization parameters used")
    total_paths: Optional[int] = Field(default=None, description="Number of paths in the vectorized image")
    colors_detected: Optional[int] = Field(default=None, description="Number of colors detected")
    processing_time: Optional[float] = Field(default=None, description="Time taken to process in seconds")


class Project(BaseModel):
    """Model representing a project"""
    id: str = Field(..., description="System-generated project identifier")
    name: str = Field(..., description="User-readable project name")
    created_at: datetime = Field(default_factory=datetime.now, description="Project creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    thumbnail_image: Optional[str] = Field(default=None, description="Local filename of the thumbnail image")
    source_image: Optional[str] = Field(default=None, description="Original filename of the uploaded image")
    vectorization: Optional[VectorizationInfo] = Field(default=None, description="Vectorization information")
    gcode_files: list[str] = Field(default_factory=list, description="List of uploaded G-code filenames for this project")


class ProjectResponse(BaseModel):
    """Model for project API responses"""
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    thumbnail_image: Optional[str] = None
    source_image: Optional[str] = None
    vectorization: Optional[VectorizationInfo] = None
    gcode_files: list[str] = []
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ProjectListResponse(BaseModel):
    """Model for listing projects"""
    projects: list[ProjectResponse]
    total: int
