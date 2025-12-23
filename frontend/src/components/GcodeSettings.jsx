import React, { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Grid,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import {
  Save as SaveIcon,
  Bolt as BoltIcon,
} from "@mui/icons-material";
import { getGcodeSettings, updateGcodeSettings, runPrePrintGcode } from "../services/apiService";

/**
 * GcodeSettings allows configuring automatic G-code sent on connect and before print start.
 */
export default function GcodeSettings() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState({ on_connect: [], before_print: [] });
  const [onConnectText, setOnConnectText] = useState("");
  const [beforePrintText, setBeforePrintText] = useState("");
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [runningPrePrint, setRunningPrePrint] = useState(false);
  const [prePrintResult, setPrePrintResult] = useState(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const toMultiline = (commands = []) => commands.join("\n");

  const normalizeCommands = (text) =>
    text
      .split("\n")
      .map((cmd) => cmd.trim())
      .filter((cmd) => !!cmd);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const result = await getGcodeSettings();
      if (result.error) {
        setError(result.error);
        return;
      }
      setSettings(result);
      setOnConnectText(toMultiline(result.on_connect));
      setBeforePrintText(toMultiline(result.before_print));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setSuccess(null);
      setError(null);

      const payload = {
        on_connect: normalizeCommands(onConnectText),
        before_print: normalizeCommands(beforePrintText),
      };

      const updated = await updateGcodeSettings(payload);
      setSettings(updated);
      setSuccess("G-code settings saved");
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleRunPrePrint = async () => {
    try {
      setRunningPrePrint(true);
      setPrePrintResult(null);
      setError(null);
      const result = await runPrePrintGcode();
      setPrePrintResult(result);
      if (!result.success) {
        setError("One or more pre-print commands failed. Check the command log.");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setRunningPrePrint(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Stack spacing={3}>
        <Box>
          <Typography variant="h6" gutterBottom>
            Automatic G-code
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Define commands that run automatically. Use one command per line; empty lines are ignored.
          </Typography>
        </Box>

        {error && <Alert severity="error" onClose={() => setError(null)}>{error}</Alert>}
        {success && <Alert severity="success" onClose={() => setSuccess(null)}>{success}</Alert>}

        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <TextField
              label="On Connect"
              fullWidth
              multiline
              minRows={6}
              value={onConnectText}
              onChange={(e) => setOnConnectText(e.target.value)}
              helperText="Sent immediately after connecting to the plotter."
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              label="Before Print Start"
              fullWidth
              multiline
              minRows={6}
              value={beforePrintText}
              onChange={(e) => setBeforePrintText(e.target.value)}
              helperText="Sent right before a print job begins."
            />
          </Grid>
        </Grid>

        <Stack direction="row" spacing={2} justifyContent="flex-end">
          <Button
            variant="outlined"
            startIcon={<BoltIcon />}
            onClick={handleRunPrePrint}
            disabled={runningPrePrint}
          >
            {runningPrePrint ? "Running…" : "Run Pre-Print"}
          </Button>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? "Saving…" : "Save G-code"}
          </Button>
        </Stack>

        {prePrintResult && (
          <Alert severity={prePrintResult.success ? "success" : "warning"}>
            {prePrintResult.message || "Pre-print commands executed."}
          </Alert>
        )}

        <Box>
          <Typography variant="body2" color="text.secondary">
            Tips:
          </Typography>
          <Typography variant="body2" color="text.secondary">
            - Use absolute (`G90`) or relative (`G91`) positioning explicitly.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            - Include units (`G20` inches or `G21` millimeters) to avoid surprises.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            - Keep homing or pen-up commands here to standardize every session.
          </Typography>
        </Box>
      </Stack>
    </Paper>
  );
}

