import { Box, Button, Paper, Stack, Typography } from "@mui/material";
import React from "react";
import logoImage from "../assets/PolarVortexLogo_small.png";
import { sendCommand } from "../services/apiService";

export default function ControlPanel() {
  const handleCommand = async (cmd) => {
    const result = await sendCommand(cmd);
    alert(`Command response: ${JSON.stringify(result)}`);
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header with Logo */}
      <Box sx={{ display: "flex", alignItems: "center", mb: 3 }}>
        <img 
          src={logoImage} 
          alt="PolarVortex Logo" 
          style={{ height: "40px", width: "auto", marginRight: "16px" }} 
        />
        <Box>
          <Typography variant="h4" gutterBottom sx={{ mb: 0 }}>
            Plotter Control
          </Typography>
          <Typography variant="body1" color="text.secondary" paragraph sx={{ mb: 0 }}>
            Control your polargraph plotter with real-time commands.
          </Typography>
        </Box>
      </Box>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Basic Controls
        </Typography>
        <Stack direction="row" spacing={2}>
          <Button variant="contained" color="success" onClick={() => handleCommand("START")}>
            Start
          </Button>
          <Button variant="contained" color="error" onClick={() => handleCommand("STOP")}>
            Stop
          </Button>
          <Button variant="contained" color="warning" onClick={() => handleCommand("PAUSE")}>
            Pause
          </Button>
        </Stack>
      </Paper>
    </Box>
  );
}
