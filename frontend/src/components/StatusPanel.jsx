import React, { useEffect, useState } from "react";
import { Typography, LinearProgress, Button } from "@mui/material";
import { getStatus } from "../services/apiService";

export default function StatusPanel() {
  const [status, setStatus] = useState({ progress: 0, drawing: false, raw: "" });

  const fetchStatus = async () => {
    const data = await getStatus();
    setStatus({
      ...status,
      raw: data.status || JSON.stringify(data),
    });
  };

  useEffect(() => {
    const interval = setInterval(fetchStatus, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      <Typography variant="h6" gutterBottom>
        Drawing Status
      </Typography>
      <Typography>{status.raw}</Typography>
      <LinearProgress variant="determinate" value={status.progress} sx={{ mt: 2 }} />
      <Button sx={{ mt: 1 }} variant="outlined" onClick={fetchStatus}>
        Refresh Status
      </Button>
    </>
  );
}
