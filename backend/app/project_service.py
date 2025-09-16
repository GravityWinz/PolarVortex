import os
import yaml
import uuid
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import logging

from .project_models import Project, ProjectCreate, ProjectResponse
from .config import config

logger = logging.getLogger(__name__)


class ProjectService:
    """Service class for managing projects"""
    
    def __init__(self):
        """Initialize the project service"""
        self.project_storage_path = Path(config.project_storage)
        self._ensure_project_storage_exists()
    
    def _ensure_project_storage_exists(self):
        """Ensure the project storage directory exists"""
        try:
            self.project_storage_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Project storage directory ensured: {self.project_storage_path}")
        except Exception as e:
            logger.error(f"Failed to create project storage directory: {e}")
            raise RuntimeError(f"Failed to create project storage directory: {e}")
    
    def _generate_project_id(self) -> str:
        """Generate a unique project ID"""
        return str(uuid.uuid4())
    
    def _get_project_directory(self, project_id: str) -> Path:
        """Get the project directory path for a given project ID"""
        return self.project_storage_path / project_id
    
    def _get_project_yaml_path(self, project_id: str) -> Path:
        """Get the project.yaml file path for a given project ID"""
        return self._get_project_directory(project_id) / "project.yaml"
    
    def _sanitize_project_name(self, name: str) -> str:
        """Sanitize project name for use in directory names"""
        # Remove or replace invalid characters for directory names
        import re
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
        sanitized = sanitized.strip()
        return sanitized if sanitized else "unnamed_project"
    
    def create_project(self, project_data: ProjectCreate) -> ProjectResponse:
        """Create a new project"""
        try:
            # Generate unique project ID
            project_id = self._generate_project_id()
            
            # Create project directory
            project_dir = self._get_project_directory(project_id)
            project_dir.mkdir(parents=True, exist_ok=True)
            
            # Create project object
            now = datetime.now()
            project = Project(
                id=project_id,
                name=project_data.name,
                created_at=now,
                updated_at=now
            )
            
            # Save project.yaml file
            self._save_project_yaml(project)
            
            logger.info(f"Created project: {project_id} - {project_data.name}")
            return ProjectResponse(**project.dict())
            
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            raise RuntimeError(f"Failed to create project: {e}")
    
    def get_project(self, project_id: str) -> Optional[ProjectResponse]:
        """Get a project by ID"""
        try:
            project_yaml_path = self._get_project_yaml_path(project_id)
            
            if not project_yaml_path.exists():
                logger.warning(f"Project not found: {project_id}")
                return None
            
            # Load project from YAML file
            with open(project_yaml_path, 'r', encoding='utf-8') as file:
                project_data = yaml.safe_load(file)
            
            if not project_data:
                logger.error(f"Invalid project.yaml file: {project_yaml_path}")
                return None
            
            # Convert datetime strings back to datetime objects
            if 'created_at' in project_data and isinstance(project_data['created_at'], str):
                project_data['created_at'] = datetime.fromisoformat(project_data['created_at'])
            if 'updated_at' in project_data and isinstance(project_data['updated_at'], str):
                project_data['updated_at'] = datetime.fromisoformat(project_data['updated_at'])
            
            project = Project(**project_data)
            return ProjectResponse(**project.dict())
            
        except Exception as e:
            logger.error(f"Failed to get project {project_id}: {e}")
            return None
    
    def list_projects(self) -> List[ProjectResponse]:
        """List all projects"""
        try:
            projects = []
            
            if not self.project_storage_path.exists():
                return projects
            
            # Iterate through all project directories
            for project_dir in self.project_storage_path.iterdir():
                if project_dir.is_dir():
                    project_id = project_dir.name
                    project = self.get_project(project_id)
                    if project:
                        projects.append(project)
            
            # Sort by creation date (newest first)
            projects.sort(key=lambda p: p.created_at, reverse=True)
            
            logger.info(f"Listed {len(projects)} projects")
            return projects
            
        except Exception as e:
            logger.error(f"Failed to list projects: {e}")
            return []
    
    def _save_project_yaml(self, project: Project):
        """Save project data to project.yaml file"""
        try:
            project_yaml_path = self._get_project_yaml_path(project.id)
            
            # Convert project to dictionary
            project_data = project.dict()
            
            # Convert datetime objects to ISO format strings for YAML
            project_data['created_at'] = project.created_at.isoformat()
            project_data['updated_at'] = project.updated_at.isoformat()
            
            # Write to YAML file
            with open(project_yaml_path, 'w', encoding='utf-8') as file:
                yaml.dump(project_data, file, default_flow_style=False, indent=2, sort_keys=False)
            
            logger.debug(f"Saved project.yaml: {project_yaml_path}")
            
        except Exception as e:
            logger.error(f"Failed to save project.yaml for {project.id}: {e}")
            raise RuntimeError(f"Failed to save project.yaml: {e}")
    
    def update_project(self, project_id: str, project_data: ProjectCreate) -> Optional[ProjectResponse]:
        """Update an existing project"""
        try:
            # Get existing project
            existing_project = self.get_project(project_id)
            if not existing_project:
                return None
            
            # Create updated project
            updated_project = Project(
                id=project_id,
                name=project_data.name,
                created_at=existing_project.created_at,
                updated_at=datetime.now()
            )
            
            # Save updated project
            self._save_project_yaml(updated_project)
            
            logger.info(f"Updated project: {project_id}")
            return ProjectResponse(**updated_project.dict())
            
        except Exception as e:
            logger.error(f"Failed to update project {project_id}: {e}")
            return None
    
    def update_project_thumbnail(self, project_id: str, thumbnail_filename: str) -> Optional[ProjectResponse]:
        """Update project with thumbnail image filename"""
        try:
            # Get existing project
            existing_project = self.get_project(project_id)
            if not existing_project:
                return None
            
            # Create updated project with thumbnail info
            updated_project = Project(
                id=project_id,
                name=existing_project.name,
                created_at=existing_project.created_at,
                updated_at=datetime.now(),
                thumbnail_image=thumbnail_filename,
                source_image=existing_project.source_image
            )
            
            # Save updated project
            self._save_project_yaml(updated_project)
            
            logger.info(f"Updated project thumbnail: {project_id} - {thumbnail_filename}")
            return ProjectResponse(**updated_project.dict())
            
        except Exception as e:
            logger.error(f"Failed to update project thumbnail {project_id}: {e}")
            return None
    
    def update_project_source_image(self, project_id: str, source_filename: str) -> Optional[ProjectResponse]:
        """Update a project's source image filename"""
        try:
            # Get existing project
            existing_project = self.get_project(project_id)
            if not existing_project:
                return None
            
            # Create updated project with source image info
            updated_project = Project(
                id=project_id,
                name=existing_project.name,
                created_at=existing_project.created_at,
                updated_at=datetime.now(),
                thumbnail_image=existing_project.thumbnail_image,
                source_image=source_filename
            )
            
            # Save updated project
            self._save_project_yaml(updated_project)
            
            logger.info(f"Updated project source image: {project_id} - {source_filename}")
            return ProjectResponse(**updated_project.dict())
            
        except Exception as e:
            logger.error(f"Failed to update project source image {project_id}: {e}")
            return None
    
    def delete_project(self, project_id: str) -> bool:
        """Delete a project and its directory"""
        try:
            project_dir = self._get_project_directory(project_id)
            
            if not project_dir.exists():
                logger.warning(f"Project directory not found: {project_dir}")
                return False
            
            # Remove the entire project directory
            import shutil
            shutil.rmtree(project_dir)
            
            logger.info(f"Deleted project: {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete project {project_id}: {e}")
            return False


# Create global instance
project_service = ProjectService()
