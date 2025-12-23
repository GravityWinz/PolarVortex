import {
    ControlCamera as ControlIcon,
    Folder as FolderIcon,
    Menu as MenuIcon,
    Monitor as MonitorIcon,
    Settings as SettingsIcon,
    Timeline as TimelineIcon,
} from "@mui/icons-material";
import {
    AppBar,
    Box,
    Button,
    Drawer,
    IconButton,
    List,
    ListItem,
    ListItemButton,
    ListItemIcon,
    ListItemText,
    Toolbar,
    Typography,
    useMediaQuery,
    useTheme,
} from "@mui/material";
import React from "react";
import logoImage from "../assets/PolarVortexLogo_small.png";

/**
 * MenuBar component for PolarVortex
 * Provides navigation between different sections of the application
 */
export default function MenuBar({ currentView, onNavigate, currentProject }) {
  const [drawerOpen, setDrawerOpen] = React.useState(false);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));

  const menuItems = [
    {
      text: "Projects",
      icon: <FolderIcon />,
      destination: "projects",
    },
    {
      text: "Graph Preparation",
      icon: <TimelineIcon />,
      destination: "preparation",
    },
    {
      text: "Plotter Control",
      icon: <ControlIcon />,
      destination: "control",
    },
    {
      text: "Status Monitor",
      icon: <MonitorIcon />,
      destination: "status",
    },
    {
      text: "Settings",
      icon: <SettingsIcon />,
      destination: "settings",
    },
  ];

  const handleNavigation = (destination) => {
    setDrawerOpen(false);
    if (onNavigate) {
      onNavigate(destination);
    }
  };

  return (
    <>
      <AppBar position="static" elevation={1} sx={{ bgcolor: "primary.main" }}>
        <Toolbar>
          <IconButton
            edge="start"
            color="inherit"
            aria-label="menu"
            onClick={() => setDrawerOpen(true)}
            sx={{ mr: 2, display: { md: "none" } }}
          >
            <MenuIcon />
          </IconButton>
          
          {/* Logo and Title */}
          <Box sx={{ display: "flex", alignItems: "center", flexGrow: 1, minWidth: 0 }}>
            <img 
              src={logoImage} 
              alt="PolarVortex Logo" 
              style={{ 
                height: "40px", 
                width: "auto", 
                marginRight: "12px",
                filter: "brightness(0) invert(1)" // Make logo white for dark background
              }} 
            />
            <Typography variant="h6" component="div">
              PolarVortex
            </Typography>
            {currentProject?.name && (
              <Typography 
                variant="subtitle2" 
                sx={{ ml: 2, color: "rgba(255,255,255,0.85)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: { xs: 140, sm: 240, md: 320 } }}
                title={currentProject.name}
              >
                Current: {currentProject.name}
              </Typography>
            )}
          </Box>
          
          {/* Desktop Menu */}
          <Box sx={{ display: { xs: "none", md: "flex" } }}>
            {menuItems.map((item) => (
              <Button
                key={item.text}
                color="inherit"
                startIcon={item.icon}
                onClick={() => handleNavigation(item.destination)}
                sx={{
                  textTransform: "none",
                  mx: 1,
                  bgcolor: currentView === item.destination ? "rgba(255,255,255,0.1)" : "transparent",
                  "&:hover": {
                    bgcolor: "rgba(255,255,255,0.1)",
                  },
                }}
              >
                {item.text}
              </Button>
            ))}
          </Box>
        </Toolbar>
      </AppBar>

      {/* Mobile Navigation Drawer */}
      <Drawer
        anchor="left"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        sx={{ display: { md: "none" } }}
      >
        <Box sx={{ width: 250 }} role="presentation">
          {/* Logo in Drawer Header */}
          <Box sx={{ p: 2, textAlign: "center", borderBottom: 1, borderColor: "divider" }}>
            <img 
              src={logoImage} 
              alt="PolarVortex Logo" 
              style={{ height: "50px", width: "auto" }} 
            />
            <Typography variant="h6" sx={{ mt: 1, color: "primary.main" }}>
              PolarVortex
            </Typography>
          </Box>
          
          <List>
            {menuItems.map((item) => (
              <ListItem key={item.text} disablePadding>
                <ListItemButton 
                  onClick={() => handleNavigation(item.destination)}
                  selected={currentView === item.destination}
                >
                  <ListItemIcon>{item.icon}</ListItemIcon>
                  <ListItemText primary={item.text} />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        </Box>
      </Drawer>
    </>
  );
}
