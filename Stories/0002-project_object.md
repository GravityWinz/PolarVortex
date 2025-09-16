create a new "project" rest resource with endpoint /projects.
It will have 
A project will have attributes:
name - this will be user readable
id - this will be some system generated identifier
created_at - timestamp when the project was created
updated_at - timestamp when the project was last updated

verbs:

get - returns the project object 

post - create a project

delete - delete a project
Creating a new project will involve the steps
first generate a GUID for the project ID
create a new directory under the directory specified by config.project_storage with the ID as the name
in the project directory create a file called project.yaml which will contain the attributes of the project object

## Implementation Status: ✅ COMPLETED

### Endpoints Implemented:
- `POST /projects` - Create a new project (requires only `name` in request body)
- `GET /projects` - List all projects
- `GET /projects/{project_id}` - Get a specific project by ID
- `DELETE /projects/{project_id}` - Delete a project by ID
- `POST /projects/{project_id}/image_upload` - Upload and process image for a specific project

### Project Model:
- `id`: System-generated GUID
- `name`: User-readable project name (required for creation)
- `created_at`: Project creation timestamp
- `updated_at`: Last update timestamp

### File Structure:
- Projects are stored in `config.project_storage/{project_id}/`
- Each project has a `project.yaml` file containing project metadata
- Project directories are created automatically upon project creation
