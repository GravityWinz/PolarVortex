import React from "react";
import { Button, Stack, Typography } from "@mui/material";
import { sendCommand } from "../services/apiService";

export default function ControlPanel() {
  const handleCommand = async (cmd) => {
    const result = await sendCommand(cmd);
    alert(`Command response: ${JSON.stringify(result)}`);
  };

  return (
    <>
      <Typography variant="h6" gutterBottom>
        Controls
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
    </>
  );
}
