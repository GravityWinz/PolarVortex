const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function getStatus() {
  try {
    const response = await fetch(`${BASE_URL}/status`);
    return await response.json();
  } catch (err) {
    console.error("Error fetching status:", err);
    return { error: err.message };
  }
}

export async function sendCommand(cmd) {
  try {
    const response = await fetch(`${BASE_URL}/command/${cmd}`, {
      method: "POST",
    });
    return await response.json();
  } catch (err) {
    console.error("Error sending command:", err);
    return { error: err.message };
  }
}

// Project Management API
export async function createProject(projectData) {
  try {
    const response = await fetch(`${BASE_URL}/projects`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(projectData),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to create project: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (err) {
    console.error("Error creating project:", err);
    throw err;
  }
}

export async function getProjects() {
  try {
    const response = await fetch(`${BASE_URL}/projects`);
    return await response.json();
  } catch (err) {
    console.error("Error fetching projects:", err);
    return { error: err.message };
  }
}

export async function getProject(projectId) {
  try {
    const response = await fetch(`${BASE_URL}/projects/${projectId}`);
    return await response.json();
  } catch (err) {
    console.error("Error fetching project:", err);
    return { error: err.message };
  }
}

export async function deleteProject(projectId) {
  try {
    const response = await fetch(`${BASE_URL}/projects/${projectId}`, {
      method: "DELETE",
    });
    
    if (!response.ok) {
      throw new Error(`Failed to delete project: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (err) {
    console.error("Error deleting project:", err);
    throw err;
  }
}

// Image Upload API (now project-specific)
export async function uploadImageToProject(projectId, formData, onProgress) {
  try {
    const response = await fetch(`${BASE_URL}/projects/${projectId}/image_upload`, {
      method: "POST",
      body: formData,
    });
    
    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (err) {
    console.error("Error uploading image:", err);
    throw err;
  }
}

// Utility functions for image URLs
export function getProjectThumbnailUrl(projectId) {
  return `${BASE_URL}/projects/${projectId}/thumbnail`;
}

export function getProjectImageUrl(projectId, filename) {
  return `${BASE_URL}/projects/${projectId}/images/${filename}`;
}
