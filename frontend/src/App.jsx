import { Box, Container, CssBaseline, Paper, ThemeProvider, Typography, createTheme } from "@mui/material";
import React, { useState } from "react";
import logoImage from "./assets/PolarVortexLogo_small.png";
import ControlPanel from "./components/ControlPanel";
import GraphPreparation from "./components/GraphPreparation";
import ImageUpload from "./components/ImageUpload";
import MenuBar from "./components/MenuBar";
import StatusPanel from "./components/StatusPanel";
import ThumbnailView from "./components/ThumbnailView";

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
  const [currentView, setCurrentView] = useState("thumbnails");
  const [selectedImage, setSelectedImage] = useState(null);

  const handleNavigation = (destination) => {
    setCurrentView(destination);
  };

  const handleImageSelect = (image) => {
    setSelectedImage(image);
    // You can navigate to preparation view when an image is selected
    // setCurrentView("preparation");
  };

  const renderCurrentView = () => {
    switch (currentView) {
      case "upload":
        return <ImageUpload />;
      case "preparation":
        return <GraphPreparation selectedImage={selectedImage} />;
      case "control":
        return <ControlPanel />;
      case "status":
        return <StatusPanel />;
      case "settings":
        return <SettingsView />;
      case "thumbnails":
      default:
        return <ThumbnailView onImageSelect={handleImageSelect} />;
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
        {/* Menu Bar */}
        <MenuBar currentView={currentView} onNavigate={handleNavigation} />
        
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


