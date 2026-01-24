import { Box, Button, Chip, LinearProgress, Paper, Typography } from "@mui/material";
import React, { useEffect, useState } from "react";
import logoImage from "../assets/PolarVortexLogo_small.png";
import { getStatus } from "../services/apiService";

export default function StatusPanel() {
  const [status, setStatus] = useState({
    progress: 0,
    drawing: false,
    raw: "",
    error: "",
  });

  const fetchStatus = async () => {
    const data = await getStatus();
    const progressValue = Number.isFinite(Number(data.progress)) ? Number(data.progress) : 0;
    const isError = Boolean(data.error);
    setStatus((prev) => ({
      ...prev,
      progress: isError ? 0 : progressValue,
      drawing: isError ? false : Boolean(data.drawing),
      raw: data.status || data.error || JSON.stringify(data),
      error: isError ? data.error : "",
    }));
  };

  useEffect(() => {
    const interval = setInterval(fetchStatus, 1000);
    return () => clearInterval(interval);
  }, []);

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
            Status Monitor
          </Typography>
          <Typography variant="body1" color="text.secondary" paragraph sx={{ mb: 0 }}>
            Monitor the real-time status of your polargraph plotter.
          </Typography>
        </Box>
      </Box>

      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
          <Typography variant="h6" gutterBottom sx={{ mb: 0, mr: 2 }}>
            Drawing Status
          </Typography>
          <Chip 
            label={status.error ? "Error" : status.drawing ? "Active" : "Idle"} 
            color={status.error ? "error" : status.drawing ? "success" : "default"}
            size="small"
          />
        </Box>
        
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {status.raw}
        </Typography>
        
        <LinearProgress variant="determinate" value={status.progress} sx={{ mb: 2 }} />
        
        <Button variant="outlined" onClick={fetchStatus}>
          Refresh Status
        </Button>
      </Paper>
    </Box>
  );
}
