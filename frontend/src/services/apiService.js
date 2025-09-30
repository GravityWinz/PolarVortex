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

// Vectorization API
export async function vectorizeProjectImage(projectId, vectorizationSettings) {
  try {
    const params = new URLSearchParams();
    
    // Add all vectorization parameters
    Object.entries(vectorizationSettings).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, value.toString());
      }
    });
    
    const response = await fetch(`${BASE_URL}/projects/${projectId}/vectorize?${params}`, {
      method: "POST",
    });
    
    if (!response.ok) {
      throw new Error(`Vectorization failed: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (err) {
    console.error("Error vectorizing image:", err);
    throw err;
  }
}

export async function getProjectVectorizationCommands(projectId, machineSettings = {}) {
  try {
    const params = new URLSearchParams();
    
    // Add machine settings parameters
    Object.entries(machineSettings).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, value.toString());
      }
    });
    
    const response = await fetch(`${BASE_URL}/projects/${projectId}/vectorize/commands?${params}`);
    
    if (!response.ok) {
      throw new Error(`Failed to get vectorization commands: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (err) {
    console.error("Error getting vectorization commands:", err);
    throw err;
  }
}

export function getProjectVectorizationSvgUrl(projectId) {
  return `${BASE_URL}/projects/${projectId}/vectorize/export-svg`;
}

// Configuration API
export async function getAllConfigurations() {
  try {
    const response = await fetch(`${BASE_URL}/config`);
    return await response.json();
  } catch (err) {
    console.error("Error fetching configurations:", err);
    return { error: err.message };
  }
}

// Paper Configuration API
export async function getPapers() {
  try {
    const response = await fetch(`${BASE_URL}/config/papers`);
    return await response.json();
  } catch (err) {
    console.error("Error fetching papers:", err);
    return { error: err.message };
  }
}

export async function getPaper(paperId) {
  try {
    const response = await fetch(`${BASE_URL}/config/papers/${paperId}`);
    return await response.json();
  } catch (err) {
    console.error("Error fetching paper:", err);
    return { error: err.message };
  }
}

export async function createPaper(paperData) {
  try {
    const response = await fetch(`${BASE_URL}/config/papers`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(paperData),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to create paper: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (err) {
    console.error("Error creating paper:", err);
    throw err;
  }
}

export async function updatePaper(paperId, paperData) {
  try {
    const response = await fetch(`${BASE_URL}/config/papers/${paperId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(paperData),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to update paper: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (err) {
    console.error("Error updating paper:", err);
    throw err;
  }
}

export async function deletePaper(paperId) {
  try {
    const response = await fetch(`${BASE_URL}/config/papers/${paperId}`, {
      method: "DELETE",
    });
    
    if (!response.ok) {
      throw new Error(`Failed to delete paper: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (err) {
    console.error("Error deleting paper:", err);
    throw err;
  }
}

export async function getDefaultPaper() {
  try {
    const response = await fetch(`${BASE_URL}/config/papers/default`);
    return await response.json();
  } catch (err) {
    console.error("Error fetching default paper:", err);
    return { error: err.message };
  }
}

// Plotter Configuration API
export async function getPlotters() {
  try {
    const response = await fetch(`${BASE_URL}/config/plotters`);
    return await response.json();
  } catch (err) {
    console.error("Error fetching plotters:", err);
    return { error: err.message };
  }
}

export async function getPlotter(plotterId) {
  try {
    const response = await fetch(`${BASE_URL}/config/plotters/${plotterId}`);
    return await response.json();
  } catch (err) {
    console.error("Error fetching plotter:", err);
    return { error: err.message };
  }
}

export async function createPlotter(plotterData) {
  try {
    const response = await fetch(`${BASE_URL}/config/plotters`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(plotterData),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to create plotter: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (err) {
    console.error("Error creating plotter:", err);
    throw err;
  }
}

export async function updatePlotter(plotterId, plotterData) {
  try {
    const response = await fetch(`${BASE_URL}/config/plotters/${plotterId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(plotterData),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to update plotter: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (err) {
    console.error("Error updating plotter:", err);
    throw err;
  }
}

export async function deletePlotter(plotterId) {
  try {
    const response = await fetch(`${BASE_URL}/config/plotters/${plotterId}`, {
      method: "DELETE",
    });
    
    if (!response.ok) {
      throw new Error(`Failed to delete plotter: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (err) {
    console.error("Error deleting plotter:", err);
    throw err;
  }
}

export async function getDefaultPlotter() {
  try {
    const response = await fetch(`${BASE_URL}/config/plotters/default`);
    return await response.json();
  } catch (err) {
    console.error("Error fetching default plotter:", err);
    return { error: err.message };
  }
}

// Configuration Management
export async function rebuildConfiguration() {
  try {
    const response = await fetch(`${BASE_URL}/config/rebuild`, {
      method: "POST",
    });
    
    if (!response.ok) {
      throw new Error(`Failed to rebuild configuration: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (err) {
    console.error("Error rebuilding configuration:", err);
    throw err;
  }
}

