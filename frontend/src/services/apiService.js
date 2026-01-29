const isLoopbackOrDockerHost = (url = "") => {
  const lower = url.toLowerCase();
  return (
    lower.includes("localhost") ||
    lower.includes("127.0.0.1") ||
    lower.includes("backend")
  );
};

export const resolveApiBaseUrl = () => {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl && !isLoopbackOrDockerHost(envUrl)) {
    return envUrl;
  }
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "https:" : "http:";
    const host = window.location.hostname;
    return `${protocol}//${host}:8000`;
  }
  return envUrl || "http://localhost:8000";
};

export const resolveWsBaseUrl = () => {
  const envUrl = import.meta.env.VITE_WS_BASE_URL;
  if (envUrl && !isLoopbackOrDockerHost(envUrl)) {
    return envUrl;
  }
  const apiBase = resolveApiBaseUrl();
  const isSecure = apiBase.startsWith("https://");
  const host = apiBase.replace(/^https?:\/\//, "");
  return `${isSecure ? "wss" : "ws"}://${host}`;
};

export const BASE_URL = resolveApiBaseUrl();

export async function getStatus() {
  try {
    const response = await fetch(`${BASE_URL}/status`);
    return await response.json();
  } catch (err) {
    console.error("Error fetching status:", err);
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

export async function updateProject(projectId, projectData) {
  try {
    const response = await fetch(`${BASE_URL}/projects/${projectId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(projectData),
    });

    if (!response.ok) {
      throw new Error(`Failed to update project: ${response.statusText}`);
    }

    return await response.json();
  } catch (err) {
    console.error("Error updating project:", err);
    throw err;
  }
}

// Project assets API
export async function getProjectAssets(projectId) {
  try {
    const response = await fetch(`${BASE_URL}/projects/${projectId}/images`);
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || error.error || `Failed to fetch project assets: ${response.statusText}`);
    }
    return await response.json();
  } catch (err) {
    console.error("Error fetching project assets:", err);
    return { images: [], error: err.message };
  }
}

export function getProjectFileUrl(projectId, filename) {
  const safePath = (filename || "").split("/").map(encodeURIComponent).join("/");
  return `${BASE_URL}/projects/${projectId}/images/${safePath}`;
}

export async function getProjectFileText(projectId, filename) {
  const safePath = (filename || "").split("/").map(encodeURIComponent).join("/");
  const url = `${BASE_URL}/projects/${projectId}/images/${safePath}`;
  const response = await fetch(url);
  const text = await response.text();
  if (!response.ok) {
    throw new Error(`Failed to load file: ${response.statusText}`);
  }
  return text;
}

export async function deleteProjectFile(projectId, filename) {
  const safePath = (filename || "").split("/").map(encodeURIComponent).join("/");
  const url = `${BASE_URL}/projects/${projectId}/images/${safePath}`;
  const response = await fetch(url, { method: "DELETE" });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || data.error || `Failed to delete file: ${response.statusText}`);
  }
  return data;
}

export async function renameProjectFile(projectId, filename, newFilename) {
  const safePath = (filename || "").split("/").map(encodeURIComponent).join("/");
  const url = `${BASE_URL}/projects/${projectId}/images/${safePath}/rename`;
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ new_filename: newFilename }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.success === false) {
    throw new Error(
      data.detail ||
        data.error ||
        data.message ||
        `Failed to rename file: ${response.statusText}`
    );
  }
  return data;
}

export async function createProjectThumbnail(projectId, filename) {
  const safePath = (filename || "").split("/").map(encodeURIComponent).join("/");
  const url = `${BASE_URL}/projects/${projectId}/images/${safePath}/thumbnail`;
  const response = await fetch(url, { method: "POST" });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.success === false) {
    throw new Error(
      data.detail ||
        data.error ||
        data.message ||
        `Failed to create thumbnail: ${response.statusText}`
    );
  }
  return data;
}

export async function getProjectSvgAnalysis(projectId, filename) {
  const safePath = (filename || "").split("/").map(encodeURIComponent).join("/");
  const url = `${BASE_URL}/projects/${projectId}/svg/${safePath}/analysis`;
  const response = await fetch(url);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(
      data.detail ||
        data.error ||
        data.message ||
        `Failed to analyze SVG: ${response.statusText}`
    );
  }
  return data;
}

export async function getProjectGcodeAnalysis(projectId, filename) {
  const safePath = (filename || "").split("/").map(encodeURIComponent).join("/");
  const url = `${BASE_URL}/projects/${projectId}/gcode/${safePath}/analysis`;
  const response = await fetch(url);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(
      data.detail ||
        data.error ||
        data.message ||
        `Failed to analyze G-code: ${response.statusText}`
    );
  }
  return data;
}

export async function convertSvgToGcode(projectId, payload) {
  const response = await fetch(`${BASE_URL}/projects/${projectId}/svg_to_gcode`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.success === false) {
    throw new Error(data.detail || data.error || data.message || "Failed to convert SVG to G-code");
  }
  return data;
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

export async function uploadGcodeToProject(projectId, formData) {
  try {
    const response = await fetch(`${BASE_URL}/projects/${projectId}/gcode_upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || error.error || `Upload failed: ${response.statusText}`);
    }

    return await response.json();
  } catch (err) {
    console.error("Error uploading G-code:", err);
    throw err;
  }
}

export async function runProjectGcode(projectId, filename) {
  try {
    const response = await fetch(`${BASE_URL}/projects/${projectId}/gcode/run`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ filename }),
    });

    const data = await response.json();
    if (!response.ok || data.success === false) {
      throw new Error(data.detail || data.error || "Failed to run G-code file");
    }

    return data;
  } catch (err) {
    console.error("Error running project G-code:", err);
    throw err;
  }
}

export async function getJobProgress(jobId) {
  try {
    const response = await fetch(`${BASE_URL}/plotter/jobs/${jobId}/progress`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    const data = await response.json();
    if (!response.ok || data.success === false) {
      throw new Error(data.detail || data.error || "Failed to get job progress");
    }

    return data;
  } catch (err) {
    console.error("Error getting job progress:", err);
    throw err;
  }
}

export async function togglePausePlotter() {
  try {
    const response = await fetch(`${BASE_URL}/plotter/pause`, {
      method: "POST",
    });
    const data = await response.json();
    if (!response.ok || data.success === false) {
      throw new Error(data.error || data.detail || "Failed to toggle pause");
    }
    return data;
  } catch (err) {
    console.error("Error toggling pause:", err);
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
export async function getAvailableVectorizers() {
  try {
    const response = await fetch(`${BASE_URL}/vectorizers`);
    if (!response.ok) {
      throw new Error(`Failed to get vectorizers: ${response.statusText}`);
    }
    const data = await response.json();
    return data.vectorizers || [];
  } catch (err) {
    console.error("Error getting vectorizers:", err);
    throw err;
  }
}

export async function getVectorizerInfo(algorithmId) {
  try {
    const response = await fetch(`${BASE_URL}/vectorizers/${algorithmId}`);
    if (!response.ok) {
      throw new Error(`Failed to get vectorizer info: ${response.statusText}`);
    }
    return await response.json();
  } catch (err) {
    console.error("Error getting vectorizer info:", err);
    throw err;
  }
}

export async function vectorizeProjectImage(projectId, vectorizationSettings, algorithm = "polargraph") {
  try {
    // Use query params for algorithm (for URL visibility) and JSON body for settings
    // This allows any algorithm-specific settings (like "booger") to be passed
    const params = new URLSearchParams();
    params.append("algorithm", algorithm);
    
    const response = await fetch(`${BASE_URL}/projects/${projectId}/vectorize?${params}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        settings: vectorizationSettings
      }),
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Vectorization failed: ${response.statusText}`);
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

// SVG Generation API
export async function getAvailableSvgGenerators() {
  try {
    const response = await fetch(`${BASE_URL}/svg-generators`);
    if (!response.ok) {
      throw new Error(`Failed to get SVG generators: ${response.statusText}`);
    }
    const data = await response.json();
    return data.generators || [];
  } catch (err) {
    console.error("Error getting SVG generators:", err);
    throw err;
  }
}

export async function getSvgGeneratorInfo(generatorId) {
  try {
    const response = await fetch(`${BASE_URL}/svg-generators/${generatorId}`);
    if (!response.ok) {
      throw new Error(`Failed to get SVG generator info: ${response.statusText}`);
    }
    return await response.json();
  } catch (err) {
    console.error("Error getting SVG generator info:", err);
    throw err;
  }
}

export async function generateProjectSvg(projectId, settings, algorithm = "geometric_pattern") {
  try {
    const params = new URLSearchParams();
    params.append("algorithm", algorithm);
    
    const response = await fetch(`${BASE_URL}/projects/${projectId}/generate-svg?${params}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        settings: settings
      }),
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `SVG generation failed: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (err) {
    console.error("Error generating SVG:", err);
    throw err;
  }
}

export async function saveProjectSvg(projectId, svgContent, filename) {
  try {
    const response = await fetch(`${BASE_URL}/projects/${projectId}/save-svg`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        svg_content: svgContent,
        filename: filename
      }),
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Failed to save SVG: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (err) {
    console.error("Error saving SVG:", err);
    throw err;
  }
}

// Terrain SVG API
export async function generateTerrainRidgeline(payload) {
  try {
    const response = await fetch(`${BASE_URL}/terrain/ridgeline`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.success === false) {
      throw new Error(data.detail || data.error || "Terrain SVG generation failed");
    }
    return data;
  } catch (err) {
    console.error("Error generating terrain SVG:", err);
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

export async function getGcodeSettings() {
  try {
    const response = await fetch(`${BASE_URL}/config/gcode`);
    return await response.json();
  } catch (err) {
    console.error("Error fetching G-code settings:", err);
    return { error: err.message };
  }
}

export async function updateGcodeSettings(gcodeSettings) {
  try {
    const response = await fetch(`${BASE_URL}/config/gcode`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(gcodeSettings),
    });

    if (!response.ok) {
      throw new Error(`Failed to update G-code settings: ${response.statusText}`);
    }

    return await response.json();
  } catch (err) {
    console.error("Error updating G-code settings:", err);
    throw err;
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

export async function getDefaultPlotter() {
  try {
    const response = await fetch(`${BASE_URL}/config/plotters/default`, {
      cache: "no-store",
      headers: {
        "Cache-Control": "no-cache",
      },
    });
    return await response.json();
  } catch (err) {
    console.error("Error fetching default plotter:", err);
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

// Plotter Control API
export async function getAvailablePorts() {
  try {
    const response = await fetch(`${BASE_URL}/plotter/ports`);
    return await response.json();
  } catch (err) {
    console.error("Error fetching ports:", err);
    return { error: err.message, ports: [] };
  }
}

export async function connectPlotter(port, baudRate) {
  try {
    const response = await fetch(`${BASE_URL}/plotter/connect`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ port, baud_rate: baudRate }),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || `Failed to connect: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (err) {
    console.error("Error connecting plotter:", err);
    throw err;
  }
}

export async function disconnectPlotter() {
  try {
    const response = await fetch(`${BASE_URL}/plotter/disconnect`, {
      method: "POST",
    });
    
    if (!response.ok) {
      throw new Error(`Failed to disconnect: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (err) {
    console.error("Error disconnecting plotter:", err);
    throw err;
  }
}

export async function getConnectionStatus() {
  try {
    const response = await fetch(`${BASE_URL}/plotter/connection`);
    return await response.json();
  } catch (err) {
    console.error("Error fetching connection status:", err);
    return { error: err.message, connected: false };
  }
}

export async function stopPlotter() {
  try {
    const response = await fetch(`${BASE_URL}/plotter/stop`, {
      method: "POST",
    });
    const data = await response.json();
    if (!response.ok || data.success === false) {
      throw new Error(data.error || data.detail || "Failed to stop plotter");
    }
    return data;
  } catch (err) {
    console.error("Error stopping plotter:", err);
    throw err;
  }
}

export async function sendGcodeCommand(gcode) {
  try {
    const response = await fetch(`${BASE_URL}/plotter/gcode`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ command: gcode }),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || `Failed to send command: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (err) {
    console.error("Error sending G-code command:", err);
    throw err;
  }
}

export async function getCommandLog() {
  try {
    const response = await fetch(`${BASE_URL}/plotter/log`);
    return await response.json();
  } catch (err) {
    console.error("Error fetching command log:", err);
    return { error: err.message, log: [] };
  }
}

export async function clearCommandLog() {
  try {
    const response = await fetch(`${BASE_URL}/plotter/log/clear`, {
      method: "POST",
    });
    
    if (!response.ok) {
      throw new Error(`Failed to clear log: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (err) {
    console.error("Error clearing command log:", err);
    throw err;
  }
}

export async function runPrePrintGcode() {
  try {
    const response = await fetch(`${BASE_URL}/plotter/gcode/preprint`, {
      method: "POST",
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `Failed to run pre-print G-code: ${response.statusText}`);
    }

    return await response.json();
  } catch (err) {
    console.error("Error running pre-print G-code:", err);
    throw err;
  }
}

