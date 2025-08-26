const BASE_URL = "http://localhost:8000"; // adjust if running elsewhere

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
