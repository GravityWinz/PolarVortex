import React, { useState } from "react";
import { Box, Container, Paper, Typography, Button, Stack } from "@mui/material";
import { ArrowBack as ArrowBackIcon } from "@mui/icons-material";
import LandingPage from "./components/LandingPage";
import ControlPanel from "./components/ControlPanel";
import StatusPanel from "./components/StatusPanel";

/**
 * Main App component for PolarVortex
 * Handles navigation between different sections of the application
 */
export default function App() {
  const [currentView, setCurrentView] = useState("landing");

  const handleNavigation = (destination) => {
    setCurrentView(destination);
  };

  const handleBackToLanding = () => {
    setCurrentView("landing");
  };

  // Render the landing page
  if (currentView === "landing") {
    return <LandingPage onNavigate={handleNavigation} />;
  }

  // Render other views with navigation header
  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      {/* Navigation Header */}
      <Paper 
        elevation={1} 
        sx={{ 
          p: 2, 
          mb: 3, 
          bgcolor: "primary.main", 
          color: "white",
          borderRadius: 0
        }}
      >
        <Container maxWidth="lg">
          <Stack direction="row" alignItems="center" spacing={2}>
            <Button
              variant="text"
              startIcon={<ArrowBackIcon />}
              onClick={handleBackToLanding}
              sx={{ color: "white", textTransform: "none" }}
            >
              Back to Home
            </Button>
            <Typography variant="h6" sx={{ flexGrow: 1 }}>
              PolarVortex - {getViewTitle(currentView)}
            </Typography>
          </Stack>
        </Container>
      </Paper>

      {/* Main Content */}
      <Container maxWidth="lg" sx={{ pb: 4 }}>
        {renderCurrentView(currentView)}
      </Container>
    </Box>
  );
}

/**
 * Get the title for the current view
 */
function getViewTitle(view) {
  const titles = {
    control: "Control Panel",
    status: "Status Monitor",
    dashboard: "Dashboard",
    settings: "Settings",
    upload: "Image Upload",
  };
  return titles[view] || "Unknown View";
}

/**
 * Render the appropriate component based on current view
 */
function renderCurrentView(view) {
  switch (view) {
    case "control":
      return <ControlPanel />;
    case "status":
      return <StatusPanel />;
    case "dashboard":
      return <DashboardView />;
    case "settings":
      return <SettingsView />;
    case "upload":
      return <UploadView />;
    default:
      return <Typography>View not found</Typography>;
  }
}

/**
 * Dashboard view component
 */
function DashboardView() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Welcome to the PolarVortex dashboard. Here you can monitor your polargraph plotter's status and access all controls.
      </Typography>
      
      <Stack spacing={3}>
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Quick Overview
          </Typography>
          <Typography variant="body2" color="text.secondary">
            System is ready for plotting operations. All components are connected and functioning properly.
          </Typography>
        </Paper>
        
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Recent Activity
          </Typography>
          <Typography variant="body2" color="text.secondary">
            No recent plotting activity. Start a new project to begin plotting.
          </Typography>
        </Paper>
      </Stack>
    </Box>
  );
}

/**
 * Settings view component
 */
function SettingsView() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Settings
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Configure your polargraph plotter settings and system preferences.
      </Typography>
      
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Plotter Configuration
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Settings configuration will be implemented here. This will include plotter dimensions, motor settings, and other parameters.
        </Typography>
      </Paper>
    </Box>
  );
}

/**
 * Upload view component
 */
function UploadView() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Image Upload
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Upload and process images for plotting with your polargraph plotter.
      </Typography>
      
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Upload Area
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Image upload functionality will be implemented here. This will allow you to upload images and convert them for plotting.
        </Typography>
      </Paper>
    </Box>
  );
}
