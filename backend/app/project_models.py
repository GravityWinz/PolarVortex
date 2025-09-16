from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class ProjectCreate(BaseModel):
    """Model for creating a new project"""
    name: str = Field(..., description="User-readable project name", min_length=1, max_length=100)


class Project(BaseModel):
    """Model representing a project"""
    id: str = Field(..., description="System-generated project identifier")
    name: str = Field(..., description="User-readable project name")
    created_at: datetime = Field(default_factory=datetime.now, description="Project creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")


class ProjectResponse(BaseModel):
    """Model for project API responses"""
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ProjectListResponse(BaseModel):
    """Model for listing projects"""
    projects: list[ProjectResponse]
    total: int
