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
  Pagination,
  Paper,
  Select,
  Stack,
  TextField,
  Tooltip,
  Typography
} from "@mui/material";
import React, { useEffect, useRef, useState } from "react";
import logoImage from "../assets/PolarVortexLogo_small.png";
import {
  clearCommandLog,
  connectPlotter,
  disconnectPlotter,
  resolveApiBaseUrl,
  resolveWsBaseUrl,
  getAvailablePorts,
  getCommandLog,
  getConnectionStatus,
  stopPlotter,
  togglePausePlotter,
  runProjectGcode,
  sendGcodeCommand,
} from "../services/apiService";

const BASE_URL = resolveApiBaseUrl();
const WS_URL = resolveWsBaseUrl();

export default function ControlPanel({ currentProject }) {
  const [ports, setPorts] = useState([]);
  const [selectedPort, setSelectedPort] = useState("");
  const [baudRate, setBaudRate] = useState(9600);
  const [connected, setConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState(null);
  const [commandLog, setCommandLog] = useState([]);
  const [loading, setLoading] = useState(false);
  const [commandInput, setCommandInput] = useState("");
  const [motionMode, setMotionMode] = useState("relative"); // "absolute" or "relative"
  const [penState, setPenState] = useState("up"); // "up" or "down"
  const [logPage, setLogPage] = useState(1);
  const LOG_PAGE_SIZE = 25;
  const [expandedEntries, setExpandedEntries] = useState(new Set());
  const [selectedProjectGcode, setSelectedProjectGcode] = useState("");
  const [gcodeRunning, setGcodeRunning] = useState(false);
  const [gcodePaused, setGcodePaused] = useState(false);
  const logContainerRef = useRef(null);
  const wsRef = useRef(null);
  const processedMessagesRef = useRef(new Set());

  const baudRates = [9600, 19200, 38400, 57600, 115200, 250000];

  // Load available ports on mount
  useEffect(() => {
    loadPorts();
    checkConnectionStatus();
    loadCommandLog();
  }, []);

  useEffect(() => {
    if (currentProject?.gcode_files?.length) {
      setSelectedProjectGcode(currentProject.gcode_files[0]);
    } else {
      setSelectedProjectGcode("");
    }
  }, [currentProject]);

  // Keep pagination on the newest page when new log entries arrive
  useEffect(() => {
    const totalPages = Math.max(1, Math.ceil(commandLog.length / LOG_PAGE_SIZE));
    setLogPage(totalPages);
  }, [commandLog]);

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
        scrollToBottom(true);
      }
    } catch (err) {
      console.error("Error loading command log:", err);
    }
  };

  const isNearBottom = () => {
    const el = logContainerRef.current;
    if (!el) return false;
    const distance = el.scrollHeight - el.clientHeight - el.scrollTop;
    return distance < 80;
  };

  const scrollToBottom = (force = false) => {
    setTimeout(() => {
      const el = logContainerRef.current;
      if (!el) return;
      if (force || isNearBottom()) {
        el.scrollTop = el.scrollHeight;
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

        // Surface any on-connect G-code results returned by the backend
        const startupResults = result.startup_gcode?.results || [];
        if (startupResults.length) {
          const entries = startupResults.map((item) => ({
            timestamp: item.timestamp || new Date().toISOString(),
            command: item.command || "(on_connect)",
            response: item.response || (item.error ? `error: ${item.error}` : ""),
          }));

          setCommandLog((prev) => {
            const combined = [...prev];
            entries.forEach((entry) => {
              const key = `${entry.timestamp}-${entry.command}-${entry.response}`;
              const exists = combined.some(
                (e) =>
                  e.command === entry.command &&
                  e.timestamp === entry.timestamp &&
                  e.response === entry.response
              );
              if (!exists) {
                combined.push(entry);
              }
              processedMessagesRef.current.add(key);
            });

            // Trim processed keys to avoid unbounded growth
            if (processedMessagesRef.current.size > 1000) {
              const keysArray = Array.from(processedMessagesRef.current);
              processedMessagesRef.current = new Set(keysArray.slice(-1000));
            }

            return combined;
          });
        }

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
      const result = await sendGcodeCommand(gcode);

      // Immediately reflect the response locally in case WebSocket delivery lags or fails
      if (result?.timestamp) {
        const entry = {
          timestamp: result.timestamp,
          command: result.command || gcode,
          response: result.response || "",
        };
        const messageKey = `${entry.timestamp}-${entry.command}-${entry.response}`;

        setCommandLog((prev) => {
          const exists = prev.some(
            (e) =>
              e.command === entry.command &&
              e.timestamp === entry.timestamp &&
              e.response === entry.response
          );
          if (exists) return prev;
          return [...prev, entry];
        });

        processedMessagesRef.current.add(messageKey);
        if (processedMessagesRef.current.size > 1000) {
          const keysArray = Array.from(processedMessagesRef.current);
          processedMessagesRef.current = new Set(keysArray.slice(-1000));
        }
      }
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

  const handleRunProjectGcode = async () => {
    if (!currentProject?.id) {
      alert("Select a current project with G-code files first");
      return;
    }
    if (!selectedProjectGcode) {
      alert("Select a G-code file to send");
      return;
    }
    if (!connected) {
      alert("Please connect to plotter first");
      return;
    }
    try {
      setGcodeRunning(true);
      await runProjectGcode(currentProject.id, selectedProjectGcode);
    } catch (err) {
      alert(`G-code run error: ${err.message}`);
    } finally {
      setGcodeRunning(false);
    }
  };

  const handleTogglePause = async () => {
    try {
      const res = await togglePausePlotter();
      setGcodePaused(res.paused);
    } catch (err) {
      alert(`Pause error: ${err.message}`);
    }
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

  const handleTogglePen = async () => {
    const target = penState === "up" ? "down" : "up";
    // Pen up/down commands: up = S33, down = S160
    const cmd = target === "up" ? "M280 P0 S33" : "M280 P0 S160";
    const prev = penState;
    setPenState(target);
    if (!connected) return;
    try {
      await sendCommand(cmd);
    } catch {
      setPenState(prev);
    }
  };

  const handleStop = () => {
    stopPlotter().catch((err) => {
      alert(`Stop error: ${err.message}`);
    });
  };

  const handleHomeAxis = (axis) => {
    sendCommand(`G28 ${axis.toUpperCase()}`);
  };

  const stepSizes = [1, 10, 100]; // 1mm, 10mm, 100mm
  const projectGcodeFiles = currentProject?.gcode_files || [];

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

      <Grid container spacing={3} alignItems="stretch">
        {/* Left column: Connection + Movement stacked */}
        <Grid item xs={12} md={6}>
          <Stack spacing={3} sx={{ height: "100%" }}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Connection
              </Typography>
              <Stack spacing={2}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <FormControl fullWidth sx={{ flex: 1 }}>
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
                    sx={{ whiteSpace: "nowrap" }}
                  >
                    Refresh
                  </Button>
                </Box>
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

            {/* Project G-code Sender */}
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Project G-code
              </Typography>
              {!currentProject ? (
                <Typography variant="body2" color="text.secondary">
                  Select a current project on the Projects tab to send its G-code.
                </Typography>
              ) : projectGcodeFiles.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  No G-code files found in the current project.
                </Typography>
              ) : (
                <Stack spacing={2}>
                  <Typography variant="body2" color="text.secondary">
                    Current project: {currentProject.name}
                  </Typography>
                  <FormControl fullWidth>
                    <InputLabel>G-code File</InputLabel>
                    <Select
                      value={selectedProjectGcode}
                      label="G-code File"
                      onChange={(e) => setSelectedProjectGcode(e.target.value)}
                      disabled={gcodeRunning}
                    >
                      {projectGcodeFiles.map((file) => {
                        const friendly = file.split("/").pop();
                        return (
                          <MenuItem key={file} value={file}>
                            {friendly}
                          </MenuItem>
                        );
                      })}
                    </Select>
                  </FormControl>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
                    <Chip
                      icon={<Send />}
                      label={gcodeRunning ? "Sending..." : "Send to Plotter"}
                      color="primary"
                      variant="filled"
                      clickable
                      disabled={!connected || gcodeRunning || !selectedProjectGcode}
                      onClick={handleRunProjectGcode}
                      sx={{ fontWeight: "bold", textTransform: "none" }}
                    />
                    <Chip
                      icon={<Stop />}
                      label="Stop"
                      color="error"
                      variant="outlined"
                      clickable
                      disabled={!connected}
                      onClick={() => stopPlotter().catch((err) => alert(`Stop error: ${err.message}`))}
                      sx={{ fontWeight: "bold", textTransform: "none" }}
                    />
                    <Chip
                      label={gcodePaused ? "Resume" : "Pause"}
                      color={gcodePaused ? "success" : "warning"}
                      variant="filled"
                      clickable
                      disabled={!connected}
                      onClick={handleTogglePause}
                      sx={{ fontWeight: "bold", textTransform: "none" }}
                    />
                    {!connected && (
                      <Typography variant="caption" color="text.secondary">
                        Connect to the plotter to enable sending.
                      </Typography>
                    )}
                  </Box>
                </Stack>
              )}
            </Paper>

            {/* Movement Controls - Cross Layout */}
            <Paper sx={{ p: 3, display: "flex", flexDirection: "column", alignItems: "center", flex: 1 }}>
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
              <Stack spacing={2} sx={{ width: "100%" }}>
                <Divider sx={{ mt: 4, mb: 1 }} />
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  Controls
                </Typography>
                <Box
                  sx={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: 1,
                    alignItems: "center",
                  }}
                >
                  <Chip
                    label="Stop"
                    color="error"
                    variant="filled"
                    icon={<Stop />}
                    clickable={connected}
                    onClick={handleStop}
                    sx={{ minWidth: 110, textTransform: "none", fontWeight: "bold" }}
                  />
                  <Chip
                    label="Auto Home"
                    color="primary"
                    variant="filled"
                    icon={<Home />}
                    clickable={connected}
                    onClick={() => {
                      if (!connected) return;
                      handleHome();
                    }}
                    sx={{ minWidth: 110, textTransform: "none", fontWeight: "bold" }}
                  />
                  <Chip
                    label="Set Home"
                    color="primary"
                    variant="outlined"
                    clickable={connected}
                    onClick={() => {
                      if (!connected) return;
                      sendCommand("G92 X0 Y0 Z0");
                    }}
                    sx={{ minWidth: 110, textTransform: "none", fontWeight: "bold" }}
                  />

                  <Tooltip
                    title={
                      motionMode === "relative"
                        ? "Relative mode (G91): moves are relative to current position"
                        : "Absolute mode (G90): moves are to absolute coordinates"
                    }
                    arrow
                  >
                    <span>
                      <Chip
                        label={(motionMode || "relative") === "relative" ? "Relative" : "Absolute"}
                        color={motionMode === "relative" ? "primary" : "default"}
                        variant={motionMode === "relative" ? "filled" : "outlined"}
                        clickable={connected}
                        onClick={async () => {
                          if (!connected) return;
                          const current = motionMode || "relative";
                          const newMode = current === "relative" ? "absolute" : "relative";
                          const gcode = newMode === "relative" ? "G91" : "G90";
                          setMotionMode(newMode); // optimistic
                          try {
                            await sendCommand(gcode);
                          } catch {
                            setMotionMode(current);
                          }
                        }}
                        sx={{ minWidth: 110, textTransform: "none", fontWeight: "bold" }}
                      />
                    </span>
                  </Tooltip>

                  <Tooltip
                    title={
                      penState === "up"
                        ? "Pen Up: M280 P0 S33 (click to send pen down)"
                        : "Pen Down: M280 P0 S160 (click to send pen up)"
                    }
                    arrow
                  >
                    <span>
                      <Chip
                        label={penState === "up" ? "Pen Up" : "Pen Down"}
                        color={penState === "up" ? "success" : "warning"}
                        variant={penState === "up" ? "filled" : "outlined"}
                        onClick={connected ? handleTogglePen : undefined}
                        clickable={connected}
                        sx={{ minWidth: 110, textTransform: "none", fontWeight: "bold" }}
                      />
                    </span>
                  </Tooltip>
                </Box>
              </Stack>
            </Paper>
          </Stack>
        </Grid>

        {/* Command/Response Log spanning full height */}
        <Grid item xs={12} md={6} sx={{ display: "flex" }}>
          <Paper sx={{ p: 3, display: "flex", flexDirection: "column", flex: 1 }}>
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
              <Typography variant="h6">Command/Response Log</Typography>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                {commandLog.length > LOG_PAGE_SIZE && (
                  <Pagination
                    size="small"
                    color="primary"
                    count={Math.max(1, Math.ceil(commandLog.length / LOG_PAGE_SIZE))}
                    page={logPage}
                    onChange={(_, value) => setLogPage(value)}
                  />
                )}
                <Button
                  size="small"
                  startIcon={<Clear />}
                  onClick={handleClearLog}
                  disabled={commandLog.length === 0}
                >
                  Clear
                </Button>
              </Box>
            </Box>
            <Box
              sx={{
                flex: 1,
                minHeight: "70vh",
                maxHeight: "80vh",
                border: "1px solid",
                borderColor: "divider",
                borderRadius: 1,
                p: 1,
                bgcolor: "background.default",
                overflow: "auto",
                fontFamily: "monospace",
                fontSize: "0.875rem",
              }}
              ref={logContainerRef}
            >
              {commandLog.length === 0 ? (
                <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
                  No commands sent yet. Connect and send commands to see activity here.
                </Typography>
              ) : (
                (() => {
                  const totalPages = Math.max(1, Math.ceil(commandLog.length / LOG_PAGE_SIZE));
                  const safePage = Math.min(logPage, totalPages);
                  const start = (safePage - 1) * LOG_PAGE_SIZE;
                  const end = start + LOG_PAGE_SIZE;
                  const pageEntries = commandLog.slice(start, end);

                  return pageEntries.map((entry, index) => {
                    const timestamp = new Date(entry.timestamp).toLocaleTimeString();
                    const entryKey = `${entry.timestamp}-${entry.command}-${start + index}`;
                    const isExpanded = expandedEntries.has(entryKey);
                    const responseText = entry.response || "";
                    const truncated =
                      responseText.length > 200
                        ? `${responseText.slice(0, 200)}…`
                        : responseText;
                    const displayText = isExpanded ? responseText : truncated;

                    return (
                      <Box key={entryKey} sx={{ mb: 1 }}>
                        <Typography
                          variant="body2"
                          sx={{
                            fontFamily: "monospace",
                            fontSize: "0.875rem",
                            whiteSpace: "pre-wrap",
                            overflowWrap: "anywhere",
                          }}
                        >
                          <Box component="span" sx={{ color: "text.secondary", mr: 1 }}>
                            [{timestamp}]
                          </Box>
                          <Box component="span" sx={{ color: "primary.main", fontWeight: "bold" }}>
                            → {entry.command}
                          </Box>
                          <Box component="span" sx={{ color: "success.main", ml: 1 }}>
                            ← {displayText}
                          </Box>
                        </Typography>
                        {responseText.length > 200 && (
                          <Button
                            size="small"
                            variant="text"
                            onClick={() => {
                              setExpandedEntries((prev) => {
                                const next = new Set(prev);
                                if (next.has(entryKey)) {
                                  next.delete(entryKey);
                                } else {
                                  next.add(entryKey);
                                }
                                return next;
                              });
                            }}
                          >
                            {isExpanded ? "Show less" : "Show more"}
                          </Button>
                        )}
                      </Box>
                    );
                  });
                })()
              )}
            </Box>
            <Box sx={{ mt: 2 }}>
              <TextField
                fullWidth
                size="small"
                placeholder="Enter G-code command (e.g., G28, M280 P0 S33)"
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

      </Grid>
    </Box>
  );
}
