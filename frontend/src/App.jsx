import { Box, Container, CssBaseline, Paper, Tab, Tabs, ThemeProvider, Typography, createTheme } from "@mui/material";
import React, { useEffect, useState } from "react";
import logoImage from "./assets/PolarVortexLogo_small.png";
import ControlPanel from "./components/ControlPanel";
import EditProject from "./components/EditProject";
import MenuBar from "./components/MenuBar";
import PaperConfiguration from "./components/PaperConfiguration";
import PlotterConfiguration from "./components/PlotterConfiguration";
import GcodeSettings from "./components/GcodeSettings";
import ProjectList from "./components/ProjectList";
import StatusPanel from "./components/StatusPanel";

// Create a custom theme for PolarVortex
const theme = createTheme({
  palette: {
    primary: {
      main: "#1976d2",
      light: "#42a5f5",
      dark: "#1565c0",
    },
    secondary: {
      main: "#dc004e",
      light: "#ff5983",
      dark: "#9a0036",
    },
    background: {
      default: "#f5f5f5",
      paper: "#ffffff",
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontWeight: 600,
    },
    h5: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 600,
    },
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
          borderRadius: 8,
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 8,
        },
      },
    },
  },
});

/**
 * Main App component for PolarVortex
 * Clean design with menu bar and thumbnail view
 */
export default function App() {
  const [currentView, setCurrentView] = useState("projects");
  const [currentProject, setCurrentProject] = useState(() => {
    try {
      const stored = localStorage.getItem("pv_current_project");
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    try {
      if (currentProject) {
        localStorage.setItem("pv_current_project", JSON.stringify(currentProject));
      } else {
        localStorage.removeItem("pv_current_project");
      }
    } catch (err) {
      console.warn("Failed to persist current project", err);
    }
  }, [currentProject]);

  const handleNavigation = (destination) => {
    setCurrentView(destination);
  };

  const handleProjectSelect = (project) => {
    setCurrentProject(project);
    setCurrentView("edit");
  };

  const renderCurrentView = () => {
    switch (currentView) {
      case "edit":
        return <EditProject currentProject={currentProject} />;
      case "control":
        return <ControlPanel currentProject={currentProject} />;
      case "status":
        return <StatusPanel />;
      case "settings":
        return <SettingsView />;
      case "projects":
      default:
        return (
          <ProjectList 
            onProjectSelect={handleProjectSelect}
            currentProject={currentProject}
            onSetCurrentProject={setCurrentProject}
            onNavigate={handleNavigation}
          />
        );
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
        {/* Menu Bar */}
        <MenuBar 
          currentView={currentView} 
          onNavigate={handleNavigation} 
          currentProject={currentProject}
        />
        
        {/* Main Content */}
        <Container maxWidth="xl" sx={{ py: 3 }}>
          {renderCurrentView()}
        </Container>
      </Box>
    </ThemeProvider>
  );
}

/**
 * Settings view component
 */
function SettingsView() {
  const [activeTab, setActiveTab] = useState(0);

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
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
            Settings
          </Typography>
          <Typography variant="body1" color="text.secondary" paragraph sx={{ mb: 0 }}>
            Configure your polargraph plotter settings and system preferences.
          </Typography>
        </Box>
      </Box>

      {/* Configuration Tabs */}
      <Paper sx={{ p: 3 }}>
        <Tabs value={activeTab} onChange={handleTabChange} sx={{ mb: 3 }}>
          <Tab label="Paper Configuration" />
          <Tab label="Plotter Configuration" />
          <Tab label="G-code" />
        </Tabs>

        {activeTab === 0 && <PaperConfiguration />}
        {activeTab === 1 && <PlotterConfiguration />}
        {activeTab === 2 && <GcodeSettings />}
      </Paper>
    </Box>
  );
}


