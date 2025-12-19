import {
  Box,
  Button,
  Paper,
  Stack,
  Typography,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  TextField,
  Grid,
  IconButton,
  Divider,
} from "@mui/material";
import {
  ArrowUpward,
  ArrowDownward,
  ArrowBack,
  ArrowForward,
  Home,
  VerticalAlignTop,
  VerticalAlignBottom,
  Clear,
  Refresh,
} from "@mui/icons-material";
import React, { useState, useEffect, useRef } from "react";
import logoImage from "../assets/PolarVortexLogo_small.png";
import {
  getAvailablePorts,
  connectPlotter,
  disconnectPlotter,
  getConnectionStatus,
  sendGcodeCommand,
  getCommandLog,
  clearCommandLog,
} from "../services/apiService";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
// Convert HTTP URL to WebSocket URL
const getWebSocketUrl = () => {
  const url = BASE_URL.replace("http://", "").replace("https://", "");
  if (BASE_URL.startsWith("https://")) {
    return `wss://${url}`;
  }
  return `ws://${url}`;
};
const WS_URL = getWebSocketUrl();

export default function ControlPanel() {
  const [ports, setPorts] = useState([]);
  const [selectedPort, setSelectedPort] = useState("");
  const [baudRate, setBaudRate] = useState(9600);
  const [connected, setConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState(null);
  const [commandLog, setCommandLog] = useState([]);
  const [stepSize, setStepSize] = useState(1); // 1mm, 10mm, or 100mm
  const [loading, setLoading] = useState(false);
  const logEndRef = useRef(null);
  const wsRef = useRef(null);

  const baudRates = [9600, 19200, 38400, 57600, 115200];

  // Load available ports on mount
  useEffect(() => {
    loadPorts();
    checkConnectionStatus();
    loadCommandLog();
  }, []);

  // WebSocket connection for real-time updates
  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const connectWebSocket = () => {
    try {
      const ws = new WebSocket(`${WS_URL}/ws`);
      ws.onopen = () => {
        console.log("WebSocket connected");
      };
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "gcode_response") {
            // Add to command log
            setCommandLog((prev) => [
              ...prev,
              {
                timestamp: data.timestamp,
                command: data.command,
                response: data.response,
              },
            ]);
            scrollToBottom();
          }
        } catch (err) {
          console.error("Error parsing WebSocket message:", err);
        }
      };
      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
      };
      ws.onclose = () => {
        console.log("WebSocket disconnected");
        // Attempt to reconnect after 5 seconds
        setTimeout(connectWebSocket, 5000);
      };
      wsRef.current = ws;
    } catch (err) {
      console.error("Failed to connect WebSocket:", err);
    }
  };

  const loadPorts = async () => {
    try {
      const result = await getAvailablePorts();
      if (result.ports) {
        setPorts(result.ports);
        if (result.ports.length > 0 && !selectedPort) {
          setSelectedPort(result.ports[0].device);
        }
      }
    } catch (err) {
      console.error("Error loading ports:", err);
    }
  };

  const checkConnectionStatus = async () => {
    try {
      const status = await getConnectionStatus();
      setConnected(status.connected || false);
      setConnectionStatus(status);
      if (status.connected && status.port) {
        setSelectedPort(status.port);
        setBaudRate(status.baud_rate || 9600);
      }
    } catch (err) {
      console.error("Error checking connection status:", err);
    }
  };

  const loadCommandLog = async () => {
    try {
      const result = await getCommandLog();
      if (result.log) {
        setCommandLog(result.log);
        scrollToBottom();
      }
    } catch (err) {
      console.error("Error loading command log:", err);
    }
  };

  const scrollToBottom = () => {
    setTimeout(() => {
      if (logEndRef.current) {
        logEndRef.current.scrollIntoView({ behavior: "smooth" });
      }
    }, 100);
  };

  const handleConnect = async () => {
    if (!selectedPort) {
      alert("Please select a port");
      return;
    }
    setLoading(true);
    try {
      const result = await connectPlotter(selectedPort, baudRate);
      if (result.success) {
        setConnected(true);
        setConnectionStatus({
          connected: true,
          port: selectedPort,
          baud_rate: baudRate,
        });
        await loadCommandLog();
      } else {
        alert(`Connection failed: ${result.error || "Unknown error"}`);
      }
    } catch (err) {
      alert(`Connection error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setLoading(true);
    try {
      const result = await disconnectPlotter();
      if (result.success) {
        setConnected(false);
        setConnectionStatus(null);
      } else {
        alert(`Disconnect failed: ${result.error || "Unknown error"}`);
      }
    } catch (err) {
      alert(`Disconnect error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleClearLog = async () => {
    try {
      await clearCommandLog();
      setCommandLog([]);
    } catch (err) {
      console.error("Error clearing log:", err);
    }
  };

  const sendCommand = async (gcode) => {
    if (!connected) {
      alert("Please connect to plotter first");
      return;
    }
    try {
      await sendGcodeCommand(gcode);
      // Log will be updated via WebSocket
    } catch (err) {
      alert(`Command error: ${err.message}`);
    }
  };

  const handleHome = () => {
    sendCommand("G28");
  };

  const handleMove = async (x, y) => {
    if (!connected) {
      alert("Please connect to plotter first");
      return;
    }
    try {
      // Set relative positioning
      await sendGcodeCommand("G91");
      // Move
      await sendGcodeCommand(`G0 X${x} Y${y}`);
      // Reset to absolute positioning
      await sendGcodeCommand("G90");
    } catch (err) {
      alert(`Movement error: ${err.message}`);
    }
  };

  const handlePenUp = () => {
    // M280 P0 S90 - typical servo command for pen up (adjust as needed)
    sendCommand("M280 P0 S90");
  };

  const handlePenDown = () => {
    // M280 P0 S0 - typical servo command for pen down (adjust as needed)
    sendCommand("M280 P0 S0");
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

      <Grid container spacing={3}>
        {/* Connection Section */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Connection
            </Typography>
            <Stack spacing={2}>
              <FormControl fullWidth>
                <InputLabel>Serial Port</InputLabel>
                <Select
                  value={selectedPort}
                  label="Serial Port"
                  onChange={(e) => setSelectedPort(e.target.value)}
                  disabled={connected || loading}
                >
                  {ports.map((port) => (
                    <MenuItem key={port.device} value={port.device}>
                      {port.device} - {port.description || "Unknown"}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Button
                variant="outlined"
                startIcon={<Refresh />}
                onClick={loadPorts}
                disabled={connected || loading}
              >
                Refresh Ports
              </Button>
              <FormControl fullWidth>
                <InputLabel>Baud Rate</InputLabel>
                <Select
                  value={baudRate}
                  label="Baud Rate"
                  onChange={(e) => setBaudRate(e.target.value)}
                  disabled={connected || loading}
                >
                  {baudRates.map((rate) => (
                    <MenuItem key={rate} value={rate}>
                      {rate}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Stack direction="row" spacing={2}>
                <Button
                  variant="contained"
                  color="success"
                  onClick={handleConnect}
                  disabled={connected || loading || !selectedPort}
                  fullWidth
                >
                  Connect
                </Button>
                <Button
                  variant="contained"
                  color="error"
                  onClick={handleDisconnect}
                  disabled={!connected || loading}
                  fullWidth
                >
                  Disconnect
                </Button>
              </Stack>
              {connectionStatus && (
                <Box>
                  <Chip
                    label={connected ? "Connected" : "Disconnected"}
                    color={connected ? "success" : "default"}
                    sx={{ mr: 1 }}
                  />
                  {connected && (
                    <>
                      <Chip label={`Port: ${connectionStatus.port}`} sx={{ mr: 1 }} />
                      <Chip label={`${connectionStatus.baud_rate} baud`} />
                    </>
                  )}
                </Box>
              )}
            </Stack>
          </Paper>
        </Grid>

        {/* Command/Response Log */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, display: "flex", flexDirection: "column", height: "100%" }}>
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
              <Typography variant="h6">Command/Response Log</Typography>
              <Button
                size="small"
                startIcon={<Clear />}
                onClick={handleClearLog}
                disabled={commandLog.length === 0}
              >
                Clear
              </Button>
            </Box>
            <Box
              sx={{
                flex: 1,
                border: "1px solid",
                borderColor: "divider",
                borderRadius: 1,
                p: 1,
                bgcolor: "background.default",
                overflow: "auto",
                maxHeight: "400px",
                fontFamily: "monospace",
                fontSize: "0.875rem",
              }}
            >
              {commandLog.length === 0 ? (
                <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
                  No commands sent yet. Connect and send commands to see activity here.
                </Typography>
              ) : (
                commandLog.map((entry, index) => (
                  <Box key={index} sx={{ mb: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(entry.timestamp).toLocaleTimeString()}
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{ color: "primary.main", fontWeight: "bold" }}
                    >
                      → {entry.command}
                    </Typography>
                    <Typography variant="body2" sx={{ color: "success.main", ml: 2 }}>
                      ← {entry.response}
                    </Typography>
                  </Box>
                ))
              )}
              <div ref={logEndRef} />
            </Box>
          </Paper>
        </Grid>

        {/* Movement Controls */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Movement Controls
            </Typography>
            <Stack spacing={2}>
              <FormControl fullWidth>
                <InputLabel>Step Size</InputLabel>
                <Select
                  value={stepSize}
                  label="Step Size"
                  onChange={(e) => setStepSize(e.target.value)}
                  disabled={!connected}
                >
                  <MenuItem value={1}>1 mm</MenuItem>
                  <MenuItem value={10}>10 mm</MenuItem>
                  <MenuItem value={100}>100 mm</MenuItem>
                </Select>
              </FormControl>
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  Y-Axis (Up/Down)
                </Typography>
                <Stack direction="row" spacing={1} justifyContent="center">
                  <Button
                    variant="contained"
                    startIcon={<ArrowUpward />}
                    onClick={() => handleMove(0, stepSize)}
                    disabled={!connected}
                    sx={{ minWidth: "120px" }}
                  >
                    Up
                  </Button>
                  <Button
                    variant="contained"
                    startIcon={<ArrowDownward />}
                    onClick={() => handleMove(0, -stepSize)}
                    disabled={!connected}
                    sx={{ minWidth: "120px" }}
                  >
                    Down
                  </Button>
                </Stack>
              </Box>
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  X-Axis (Left/Right)
                </Typography>
                <Stack direction="row" spacing={1} justifyContent="center">
                  <Button
                    variant="contained"
                    startIcon={<ArrowBack />}
                    onClick={() => handleMove(-stepSize, 0)}
                    disabled={!connected}
                    sx={{ minWidth: "120px" }}
                  >
                    Left
                  </Button>
                  <Button
                    variant="contained"
                    startIcon={<ArrowForward />}
                    onClick={() => handleMove(stepSize, 0)}
                    disabled={!connected}
                    sx={{ minWidth: "120px" }}
                  >
                    Right
                  </Button>
                </Stack>
              </Box>
            </Stack>
          </Paper>
        </Grid>

        {/* Home and Pen Controls */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              System Controls
            </Typography>
            <Stack spacing={2}>
              <Button
                variant="contained"
                color="primary"
                startIcon={<Home />}
                onClick={handleHome}
                disabled={!connected}
                fullWidth
                size="large"
              >
                Home (G28)
              </Button>
              <Divider />
              <Typography variant="subtitle2">Pen Control</Typography>
              <Stack direction="row" spacing={2}>
                <Button
                  variant="contained"
                  color="secondary"
                  startIcon={<VerticalAlignTop />}
                  onClick={handlePenUp}
                  disabled={!connected}
                  fullWidth
                >
                  Pen Up
                </Button>
                <Button
                  variant="contained"
                  color="secondary"
                  startIcon={<VerticalAlignBottom />}
                  onClick={handlePenDown}
                  disabled={!connected}
                  fullWidth
                >
                  Pen Down
                </Button>
              </Stack>
            </Stack>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}
