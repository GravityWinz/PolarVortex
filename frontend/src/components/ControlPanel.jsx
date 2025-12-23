import {
  ArrowBack,
  ArrowDownward,
  ArrowForward,
  ArrowUpward,
  Clear,
  Home,
  Refresh,
  Send,
  Stop,
  VerticalAlignBottom,
  VerticalAlignTop,
} from "@mui/icons-material";
import {
  Box,
  Button,
  Chip,
  Divider,
  FormControl,
  Grid,
  IconButton,
  InputAdornment,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography
} from "@mui/material";
import React, { useEffect, useRef, useState } from "react";
import logoImage from "../assets/PolarVortexLogo_small.png";
import {
  clearCommandLog,
  connectPlotter,
  disconnectPlotter,
  getAvailablePorts,
  getCommandLog,
  getConnectionStatus,
  sendGcodeCommand,
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
  const [loading, setLoading] = useState(false);
  const [commandInput, setCommandInput] = useState("");
  const [motionMode, setMotionMode] = useState("relative"); // "absolute" or "relative"
  const logEndRef = useRef(null);
  const wsRef = useRef(null);
  const processedMessagesRef = useRef(new Set());

  const baudRates = [9600, 19200, 38400, 57600, 115200];

  // Load available ports on mount
  useEffect(() => {
    loadPorts();
    checkConnectionStatus();
    loadCommandLog();
  }, []);

  // WebSocket connection for real-time updates
  useEffect(() => {
    // Only create WebSocket if one doesn't already exist
    if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED) {
      connectWebSocket();
    }
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  const connectWebSocket = () => {
    // Prevent multiple connections
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      return;
    }
    
    try {
      const ws = new WebSocket(`${WS_URL}/ws`);
      ws.onopen = () => {
        console.log("WebSocket connected");
      };
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "gcode_response") {
            // Create a unique key for this message
            const messageKey = `${data.timestamp}-${data.command}-${data.response}`;
            
            // Check if we've already processed this message
            if (processedMessagesRef.current.has(messageKey)) {
              return; // Skip duplicate
            }
            
            // Mark as processed
            processedMessagesRef.current.add(messageKey);
            
            // Clean up old keys (keep last 1000)
            if (processedMessagesRef.current.size > 1000) {
              const keysArray = Array.from(processedMessagesRef.current);
              processedMessagesRef.current = new Set(keysArray.slice(-1000));
            }
            
            // Add to command log
            setCommandLog((prev) => {
              // Double-check in state as well
              const exists = prev.some(
                (entry) =>
                  entry.command === data.command &&
                  entry.timestamp === data.timestamp &&
                  entry.response === data.response
              );
              if (exists) {
                return prev;
              }
              return [
                ...prev,
                {
                  timestamp: data.timestamp,
                  command: data.command,
                  response: data.response,
                },
              ];
            });
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
        wsRef.current = null;
        // Attempt to reconnect after 5 seconds only if component is still mounted
        setTimeout(() => {
          if (wsRef.current === null) {
            connectWebSocket();
          }
        }, 5000);
      };
      wsRef.current = ws;
    } catch (err) {
      console.error("Failed to connect WebSocket:", err);
      wsRef.current = null;
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
        // Mark all loaded entries as processed to prevent duplicates
        result.log.forEach((entry) => {
          const messageKey = `${entry.timestamp}-${entry.command}-${entry.response}`;
          processedMessagesRef.current.add(messageKey);
        });
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

  const handleSendCommand = async () => {
    if (!commandInput.trim()) {
      return;
    }
    const command = commandInput.trim();
    setCommandInput("");
    await sendCommand(command);
  };

  const handleCommandInputKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendCommand();
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
      // Use current motion mode - don't switch modes, just move
      await sendGcodeCommand(`G0 X${x} Y${y}`);
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

  const handleStop = () => {
    sendCommand("M112"); // Emergency stop, or use M0 for program stop
  };

  const handleHomeAxis = (axis) => {
    sendCommand(`G28 ${axis.toUpperCase()}`);
  };

  const stepSizes = [1, 10, 100]; // 1mm, 10mm, 100mm

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
                commandLog.map((entry, index) => {
                  const timestamp = new Date(entry.timestamp).toLocaleTimeString();
                  return (
                    <Box key={index} sx={{ mb: 0.5 }}>
                      <Typography 
                        variant="body2" 
                        sx={{ 
                          fontFamily: "monospace",
                          fontSize: "0.875rem",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis"
                        }}
                      >
                        <Box component="span" sx={{ color: "text.secondary", mr: 1 }}>
                          [{timestamp}]
                        </Box>
                        <Box component="span" sx={{ color: "primary.main", fontWeight: "bold" }}>
                          → {entry.command}
                        </Box>
                        <Box component="span" sx={{ color: "success.main", ml: 1 }}>
                          ← {entry.response}
                        </Box>
                      </Typography>
                    </Box>
                  );
                })
              )}
              <div ref={logEndRef} />
            </Box>
            <Box sx={{ mt: 2 }}>
              <TextField
                fullWidth
                size="small"
                placeholder="Enter G-code command (e.g., G28, M280 P0 S90)"
                value={commandInput}
                onChange={(e) => setCommandInput(e.target.value)}
                onKeyPress={handleCommandInputKeyPress}
                disabled={!connected || loading}
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={handleSendCommand}
                        disabled={!connected || loading || !commandInput.trim()}
                        edge="end"
                        color="primary"
                      >
                        <Send />
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
                sx={{
                  "& .MuiOutlinedInput-root": {
                    fontFamily: "monospace",
                  },
                }}
              />
            </Box>
          </Paper>
        </Grid>

        {/* Movement Controls - Cross Layout */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, display: "flex", flexDirection: "column", alignItems: "center" }}>
            <Typography variant="h6" gutterBottom>
              Movement Controls
            </Typography>
            <Box
              sx={{
                position: "relative",
                width: "400px",
                height: "400px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                mt: 2,
              }}
            >
              {/* Central Stop Button */}
              <IconButton
                onClick={handleStop}
                disabled={!connected}
                sx={{
                  position: "absolute",
                  width: "48px",
                  height: "48px",
                  bgcolor: "error.main",
                  color: "white",
                  zIndex: 10,
                  "&:hover": {
                    bgcolor: "error.dark",
                  },
                  "&:disabled": {
                    bgcolor: "grey.400",
                  },
                }}
              >
                <Stop />
              </IconButton>

              {/* Top (+Y) - 3 buttons vertical (stacked) */}
              <Box
                sx={{
                  position: "absolute",
                  top: "10px",
                  left: "50%",
                  transform: "translateX(-50%)",
                  display: "flex",
                  flexDirection: "column",
                  gap: 2.5,
                  alignItems: "center",
                }}
              >
                <Button
                  onClick={() => handleMove(0, 100)}
                  disabled={!connected}
                  sx={{
                    minWidth: "44px",
                    height: "44px",
                    bgcolor: "primary.dark",
                    color: "white",
                    "&:hover": { bgcolor: "primary.dark", opacity: 0.9 },
                    "&:disabled": { bgcolor: "grey.300" },
                  }}
                >
                  <ArrowUpward sx={{ fontSize: "1.1rem" }} />
                  <Typography variant="caption" sx={{ ml: 0.4, fontSize: "0.6rem" }}>
                    100
                  </Typography>
                </Button>
                <Button
                  onClick={() => handleMove(0, 10)}
                  disabled={!connected}
                  sx={{
                    minWidth: "36px",
                    height: "36px",
                    bgcolor: "primary.main",
                    color: "white",
                    "&:hover": { bgcolor: "primary.dark" },
                    "&:disabled": { bgcolor: "grey.300" },
                  }}
                >
                  <ArrowUpward sx={{ fontSize: "0.95rem" }} />
                  <Typography variant="caption" sx={{ ml: 0.3, fontSize: "0.55rem" }}>
                    10
                  </Typography>
                </Button>
                <Button
                  onClick={() => handleMove(0, 1)}
                  disabled={!connected}
                  sx={{
                    minWidth: "28px",
                    height: "28px",
                    bgcolor: "primary.light",
                    color: "white",
                    "&:hover": { bgcolor: "primary.main" },
                    "&:disabled": { bgcolor: "grey.300" },
                  }}
                >
                  <ArrowUpward sx={{ fontSize: "0.8rem" }} />
                  <Typography variant="caption" sx={{ ml: 0.2, fontSize: "0.5rem" }}>
                    1
                  </Typography>
                </Button>
              </Box>

              {/* Bottom (-Y) - 3 buttons vertical (stacked) */}
              <Box
                sx={{
                  position: "absolute",
                  bottom: "10px",
                  left: "50%",
                  transform: "translateX(-50%)",
                  display: "flex",
                  flexDirection: "column-reverse",
                  gap: 2.5,
                  alignItems: "center",
                }}
              >
                <Button
                  onClick={() => handleMove(0, -100)}
                  disabled={!connected}
                  sx={{
                    minWidth: "44px",
                    height: "44px",
                    bgcolor: "primary.dark",
                    color: "white",
                    "&:hover": { bgcolor: "primary.dark", opacity: 0.9 },
                    "&:disabled": { bgcolor: "grey.300" },
                  }}
                >
                  <ArrowDownward sx={{ fontSize: "1.1rem" }} />
                  <Typography variant="caption" sx={{ ml: 0.4, fontSize: "0.6rem" }}>
                    100
                  </Typography>
                </Button>
                <Button
                  onClick={() => handleMove(0, -10)}
                  disabled={!connected}
                  sx={{
                    minWidth: "36px",
                    height: "36px",
                    bgcolor: "primary.main",
                    color: "white",
                    "&:hover": { bgcolor: "primary.dark" },
                    "&:disabled": { bgcolor: "grey.300" },
                  }}
                >
                  <ArrowDownward sx={{ fontSize: "0.95rem" }} />
                  <Typography variant="caption" sx={{ ml: 0.3, fontSize: "0.55rem" }}>
                    10
                  </Typography>
                </Button>
                <Button
                  onClick={() => handleMove(0, -1)}
                  disabled={!connected}
                  sx={{
                    minWidth: "28px",
                    height: "28px",
                    bgcolor: "primary.light",
                    color: "white",
                    "&:hover": { bgcolor: "primary.main" },
                    "&:disabled": { bgcolor: "grey.300" },
                  }}
                >
                  <ArrowDownward sx={{ fontSize: "0.8rem" }} />
                  <Typography variant="caption" sx={{ ml: 0.2, fontSize: "0.5rem" }}>
                    1
                  </Typography>
                </Button>
              </Box>

              {/* Left (-X) - 3 buttons horizontal */}
              <Box
                sx={{
                  position: "absolute",
                  left: "10px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  display: "flex",
                  gap: 2.5,
                  alignItems: "center",
                }}
              >
                <Button
                  onClick={() => handleMove(-100, 0)}
                  disabled={!connected}
                  sx={{
                    minWidth: "44px",
                    height: "44px",
                    bgcolor: "secondary.dark",
                    color: "white",
                    "&:hover": { bgcolor: "secondary.dark", opacity: 0.9 },
                    "&:disabled": { bgcolor: "grey.300" },
                  }}
                >
                  <ArrowBack sx={{ fontSize: "1.1rem" }} />
                  <Typography variant="caption" sx={{ ml: 0.4, fontSize: "0.6rem" }}>
                    100
                  </Typography>
                </Button>
                <Button
                  onClick={() => handleMove(-10, 0)}
                  disabled={!connected}
                  sx={{
                    minWidth: "36px",
                    height: "36px",
                    bgcolor: "secondary.main",
                    color: "white",
                    "&:hover": { bgcolor: "secondary.dark" },
                    "&:disabled": { bgcolor: "grey.300" },
                  }}
                >
                  <ArrowBack sx={{ fontSize: "0.95rem" }} />
                  <Typography variant="caption" sx={{ ml: 0.3, fontSize: "0.55rem" }}>
                    10
                  </Typography>
                </Button>
                <Button
                  onClick={() => handleMove(-1, 0)}
                  disabled={!connected}
                  sx={{
                    minWidth: "28px",
                    height: "28px",
                    bgcolor: "secondary.light",
                    color: "white",
                    "&:hover": { bgcolor: "secondary.main" },
                    "&:disabled": { bgcolor: "grey.300" },
                  }}
                >
                  <ArrowBack sx={{ fontSize: "0.8rem" }} />
                  <Typography variant="caption" sx={{ ml: 0.2, fontSize: "0.5rem" }}>
                    1
                  </Typography>
                </Button>
              </Box>

              {/* Right (+X) - 3 buttons horizontal */}
              <Box
                sx={{
                  position: "absolute",
                  right: "10px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  display: "flex",
                  gap: 2.5,
                  alignItems: "center",
                }}
              >
                <Button
                  onClick={() => handleMove(1, 0)}
                  disabled={!connected}
                  sx={{
                    minWidth: "28px",
                    height: "28px",
                    bgcolor: "secondary.light",
                    color: "white",
                    "&:hover": { bgcolor: "secondary.main" },
                    "&:disabled": { bgcolor: "grey.300" },
                  }}
                >
                  <ArrowForward sx={{ fontSize: "0.8rem" }} />
                  <Typography variant="caption" sx={{ ml: 0.2, fontSize: "0.5rem" }}>
                    1
                  </Typography>
                </Button>
                <Button
                  onClick={() => handleMove(10, 0)}
                  disabled={!connected}
                  sx={{
                    minWidth: "36px",
                    height: "36px",
                    bgcolor: "secondary.main",
                    color: "white",
                    "&:hover": { bgcolor: "secondary.dark" },
                    "&:disabled": { bgcolor: "grey.300" },
                  }}
                >
                  <ArrowForward sx={{ fontSize: "0.95rem" }} />
                  <Typography variant="caption" sx={{ ml: 0.3, fontSize: "0.55rem" }}>
                    10
                  </Typography>
                </Button>
                <Button
                  onClick={() => handleMove(100, 0)}
                  disabled={!connected}
                  sx={{
                    minWidth: "44px",
                    height: "44px",
                    bgcolor: "secondary.dark",
                    color: "white",
                    "&:hover": { bgcolor: "secondary.dark", opacity: 0.9 },
                    "&:disabled": { bgcolor: "grey.300" },
                  }}
                >
                  <ArrowForward sx={{ fontSize: "1.1rem" }} />
                  <Typography variant="caption" sx={{ ml: 0.4, fontSize: "0.6rem" }}>
                    100
                  </Typography>
                </Button>
              </Box>
            </Box>
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
              <Typography variant="subtitle2">Motion Mode</Typography>
              <Button
                variant={motionMode === "relative" ? "contained" : "outlined"}
                color="primary"
                onClick={async () => {
                  const current = motionMode || "relative";
                  const newMode = current === "relative" ? "absolute" : "relative";
                  const gcode = newMode === "relative" ? "G91" : "G90";
                  // Optimistic UI update
                  setMotionMode(newMode);
                  if (!connected) return;
                  try {
                    await sendCommand(gcode);
                  } catch (err) {
                    // Revert on error
                    setMotionMode(current);
                  }
                }}
                disabled={!connected}
                fullWidth
              >
                {(motionMode || "relative") === "relative" ? "Relative (G91)" : "Absolute (G90)"}
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
