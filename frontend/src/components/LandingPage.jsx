import React, { useState } from "react";
import {
  Box,
  Container,
  Typography,
  Button,
  Card,
  CardContent,
  CardMedia,
  Grid,
  Paper,
  Chip,
  Stack,
  AppBar,
  Toolbar,
  IconButton,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  useTheme,
  useMediaQuery,
} from "@mui/material";
import {
  Menu as MenuIcon,
  PlayArrow as PlayIcon,
  Stop as StopIcon,
  Pause as PauseIcon,
  Upload as UploadIcon,
  Settings as SettingsIcon,
  Info as InfoIcon,
  Home as HomeIcon,
  Dashboard as DashboardIcon,
} from "@mui/icons-material";

/**
 * Landing page component for PolarVortex - Polargraph Plotter Control System
 * Provides an introduction to the system and navigation to main features
 */
export default function LandingPage({ onNavigate }) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));

  const handleNavigation = (destination) => {
    setDrawerOpen(false);
    if (onNavigate) {
      onNavigate(destination);
    }
  };

  const features = [
    {
      title: "Real-time Control",
      description: "Control your polargraph plotter with instant command execution and status monitoring.",
      icon: <PlayIcon sx={{ fontSize: 40, color: "primary.main" }} />,
    },
    {
      title: "Image Processing",
      description: "Upload and process images for precise plotting with advanced algorithms.",
      icon: <UploadIcon sx={{ fontSize: 40, color: "primary.main" }} />,
    },
    {
      title: "Status Monitoring",
      description: "Real-time progress tracking and system status updates via WebSocket.",
      icon: <DashboardIcon sx={{ fontSize: 40, color: "primary.main" }} />,
    },
    {
      title: "System Settings",
      description: "Configure plotter parameters and system preferences for optimal performance.",
      icon: <SettingsIcon sx={{ fontSize: 40, color: "primary.main" }} />,
    },
  ];

  const navigationItems = [
    { text: "Dashboard", icon: <DashboardIcon />, destination: "dashboard" },
    { text: "Control Panel", icon: <PlayIcon />, destination: "control" },
    { text: "Status Monitor", icon: <InfoIcon />, destination: "status" },
    { text: "Settings", icon: <SettingsIcon />, destination: "settings" },
  ];

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      {/* App Bar */}
      <AppBar position="static" elevation={0} sx={{ bgcolor: "primary.main" }}>
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
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            PolarVortex
          </Typography>
          <Stack direction="row" spacing={1} sx={{ display: { xs: "none", md: "flex" } }}>
            {navigationItems.map((item) => (
              <Button
                key={item.text}
                color="inherit"
                startIcon={item.icon}
                onClick={() => handleNavigation(item.destination)}
                sx={{ textTransform: "none" }}
              >
                {item.text}
              </Button>
            ))}
          </Stack>
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
          <List>
            {navigationItems.map((item) => (
              <ListItem key={item.text} disablePadding>
                <ListItemButton onClick={() => handleNavigation(item.destination)}>
                  <ListItemIcon>{item.icon}</ListItemIcon>
                  <ListItemText primary={item.text} />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
        </Box>
      </Drawer>

      {/* Hero Section */}
      <Box
        sx={{
          background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
          color: "white",
          py: 8,
          position: "relative",
          overflow: "hidden",
        }}
      >
        <Container maxWidth="lg">
          <Grid container spacing={4} alignItems="center">
            <Grid item xs={12} md={6}>
              <Typography variant="h2" component="h1" gutterBottom sx={{ fontWeight: "bold" }}>
                PolarVortex
              </Typography>
              <Typography variant="h5" gutterBottom sx={{ mb: 3, opacity: 0.9 }}>
                Advanced Polargraph Plotter Control System
              </Typography>
              <Typography variant="body1" sx={{ mb: 4, opacity: 0.8, fontSize: "1.1rem" }}>
                Take control of your polargraph plotter with our intuitive web interface. 
                Upload images, monitor progress, and create precise drawings with real-time control.
              </Typography>
              <Stack direction="row" spacing={2} flexWrap="wrap">
                <Button
                  variant="contained"
                  size="large"
                  startIcon={<PlayIcon />}
                  onClick={() => handleNavigation("control")}
                  sx={{
                    bgcolor: "white",
                    color: "primary.main",
                    "&:hover": { bgcolor: "grey.100" },
                  }}
                >
                  Start Plotting
                </Button>
                <Button
                  variant="outlined"
                  size="large"
                  startIcon={<InfoIcon />}
                  onClick={() => handleNavigation("dashboard")}
                  sx={{ borderColor: "white", color: "white" }}
                >
                  Learn More
                </Button>
              </Stack>
            </Grid>
            <Grid item xs={12} md={6}>
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                  height: 400,
                  position: "relative",
                }}
              >
                {/* Placeholder for plotter visualization */}
                <Paper
                  elevation={8}
                  sx={{
                    width: 300,
                    height: 300,
                    borderRadius: "50%",
                    background: "rgba(255,255,255,0.1)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    position: "relative",
                    "&::before": {
                      content: '""',
                      position: "absolute",
                      width: "80%",
                      height: "80%",
                      borderRadius: "50%",
                      border: "2px dashed rgba(255,255,255,0.3)",
                    },
                  }}
                >
                  <Typography variant="h4" sx={{ color: "white", textAlign: "center" }}>
                    Polargraph<br />Plotter
                  </Typography>
                </Paper>
              </Box>
            </Grid>
          </Grid>
        </Container>
      </Box>

      {/* Features Section */}
      <Container maxWidth="lg" sx={{ py: 8 }}>
        <Typography variant="h3" component="h2" textAlign="center" gutterBottom>
          Features
        </Typography>
        <Typography variant="h6" textAlign="center" color="text.secondary" sx={{ mb: 6 }}>
          Everything you need to control your polargraph plotter
        </Typography>
        
        <Grid container spacing={4}>
          {features.map((feature, index) => (
            <Grid item xs={12} sm={6} md={3} key={index}>
              <Card
                sx={{
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                  transition: "transform 0.2s",
                  "&:hover": {
                    transform: "translateY(-4px)",
                  },
                }}
              >
                <CardContent sx={{ flexGrow: 1, textAlign: "center" }}>
                  <Box sx={{ mb: 2 }}>{feature.icon}</Box>
                  <Typography variant="h6" component="h3" gutterBottom>
                    {feature.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {feature.description}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Container>

      {/* Quick Actions Section */}
      <Box sx={{ bgcolor: "grey.50", py: 8 }}>
        <Container maxWidth="lg">
          <Typography variant="h3" component="h2" textAlign="center" gutterBottom>
            Quick Actions
          </Typography>
          <Grid container spacing={3} justifyContent="center" sx={{ mt: 4 }}>
            <Grid item>
              <Button
                variant="contained"
                size="large"
                startIcon={<PlayIcon />}
                onClick={() => handleNavigation("control")}
                sx={{ px: 4, py: 1.5 }}
              >
                Control Panel
              </Button>
            </Grid>
            <Grid item>
              <Button
                variant="outlined"
                size="large"
                startIcon={<UploadIcon />}
                onClick={() => handleNavigation("upload")}
                sx={{ px: 4, py: 1.5 }}
              >
                Upload Image
              </Button>
            </Grid>
            <Grid item>
              <Button
                variant="outlined"
                size="large"
                startIcon={<InfoIcon />}
                onClick={() => handleNavigation("status")}
                sx={{ px: 4, py: 1.5 }}
              >
                View Status
              </Button>
            </Grid>
          </Grid>
        </Container>
      </Box>

      {/* Footer */}
      <Box sx={{ bgcolor: "primary.main", color: "white", py: 4 }}>
        <Container maxWidth="lg">
          <Grid container spacing={4}>
            <Grid item xs={12} md={6}>
              <Typography variant="h6" gutterBottom>
                PolarVortex
              </Typography>
              <Typography variant="body2" sx={{ opacity: 0.8 }}>
                Advanced polargraph plotter control system built with React and Material UI.
                Real-time control, image processing, and status monitoring for precise plotting.
              </Typography>
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography variant="h6" gutterBottom>
                System Status
              </Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap">
                <Chip label="Backend Connected" color="success" size="small" />
                <Chip label="Arduino Ready" color="success" size="small" />
                <Chip label="WebSocket Active" color="success" size="small" />
              </Stack>
            </Grid>
          </Grid>
          <Divider sx={{ my: 2, borderColor: "rgba(255,255,255,0.2)" }} />
          <Typography variant="body2" textAlign="center" sx={{ opacity: 0.6 }}>
            © 2024 PolarVortex. Built with React, Material UI, and FastAPI.
          </Typography>
        </Container>
      </Box>
    </Box>
  );
}
