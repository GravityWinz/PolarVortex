# File uploading process
## General Architecture
    The following directory structure will be used:
local_storage/
├── projects/
│   ├── <project_id>/              # A directory for each project, using the project's GUID
│   │   ├── project.yaml           # Project metadata (id, name, created_at, updated_at)
│   │   ├── image_name.<ext>       # The original image file
│   │   ├── thumb_image_name.png   # thumbnail image
│   │   └── ...                    # other post processed versions of that image - TBD
│   └── <next_project_id>/         # Next project directory
│       ├── project.yaml           # Project metadata
│       ├── image_name.<ext>       # The original image file
│       ├── thumb_image_name.png   # thumbnail image
│       └── ...                    # other post processed versions of that image - TBD

## Flow for the file upload process
1) User creates or selects a project (via `/projects` endpoints)
2) User will be presented a file picker to choose the file
3) User will then select upload to the specific project
4) Image data, file name, and project_id will be passed to backend via `POST /projects/{project_id}/image_upload`
5) Backend verifies the project exists
6) The original image will be stored directly in the project directory `local_storage/projects/{project_id}/`
7) Image processing (thumbnail generation, etc.) will occur
8) WebSocket broadcast will notify frontend of successful upload

## Project-Based Organization
- **Projects**: Each project has a unique GUID and contains one image
- **Image Storage**: Images are stored directly in the project directory
- **Project Metadata**: Each project has a `project.yaml` file with project information
- **API Endpoints**: All operations use `/projects` resource endpoints

## Implementation Status: ✅ COMPLETED

### Endpoints Used:
- `POST /projects` - Create a new project (required before uploading images)
- `GET /projects` - List all projects with their associated images
- `GET /projects/{project_id}` - Get specific project details
- `POST /projects/{project_id}/image_upload` - Upload image to specific project
- `DELETE /projects/{project_id}` - Delete project and all associated images

### Directory Structure Benefits:
- **Simple**: Each project contains one image directly in its directory
- **Organized**: Images are grouped by project
- **Isolated**: Each project's image is separate
- **Scalable**: Easy to manage multiple projects
- **RESTful**: Clean API design with project-based resources