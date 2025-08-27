# PolarVortex Frontend

A modern React-based web interface for controlling polargraph plotters, built with Material UI and Vite.

## Features

- **Landing Page**: Beautiful introduction to the PolarVortex system
- **Control Panel**: Real-time control of plotter operations (Start, Stop, Pause)
- **Status Monitor**: Live status updates and progress tracking
- **Dashboard**: Overview of system status and recent activity
- **Settings**: Configuration panel for plotter parameters
- **Image Upload**: Interface for uploading and processing images for plotting

## Technology Stack

- **React 18.2.0** - Modern React with hooks
- **Material UI 5.14.20** - Material Design components
- **Vite 4.5.0** - Fast build tool and development server
- **Emotion** - CSS-in-JS styling solution

## Getting Started

### Prerequisites

- Node.js (version 16 or higher)
- npm or yarn package manager

### Installation

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open your browser and navigate to `http://localhost:3000`

### Building for Production

To create a production build:

```bash
npm run build
```

The built files will be in the `dist` directory.

### Preview Production Build

To preview the production build locally:

```bash
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── LandingPage.jsx      # Main landing page
│   │   ├── ControlPanel.jsx     # Plotter control interface
│   │   └── StatusPanel.jsx      # Status monitoring
│   ├── services/
│   │   └── apiService.js        # API communication
│   ├── App.jsx                  # Main application component
│   └── index.jsx                # Application entry point
├── index.html                   # HTML template
├── package.json                 # Dependencies and scripts
├── vite.config.js              # Vite configuration
└── README.md                   # This file
```

## API Integration

The frontend communicates with the backend API through the `apiService.js` module. The backend should be running on `http://localhost:8000` by default.

### Available API Endpoints

- `GET /status` - Get current plotter status
- `POST /command/{cmd}` - Send commands (START, STOP, PAUSE)

## Customization

### Theme

The application uses a custom Material UI theme defined in `src/index.jsx`. You can modify colors, typography, and component styles by editing the theme configuration.

### Navigation

The navigation system is handled in `src/App.jsx`. New views can be added by:

1. Creating a new component
2. Adding it to the `renderCurrentView` function
3. Adding a navigation item to the landing page

## Development

### Code Style

- Use functional components with hooks
- Follow Material UI design patterns
- Include JSDoc comments for complex components
- Use semantic HTML and accessibility features

### Adding New Features

1. Create new components in the `src/components/` directory
2. Add any new services to `src/services/`
3. Update the navigation in `App.jsx` if needed
4. Test thoroughly before committing

## Troubleshooting

### Common Issues

1. **Port already in use**: Change the port in `vite.config.js`
2. **API connection errors**: Ensure the backend is running on the correct port
3. **Build errors**: Check that all dependencies are installed

### Getting Help

- Check the browser console for JavaScript errors
- Verify that all dependencies are correctly installed
- Ensure the backend API is running and accessible

## License

This project is part of the PolarVortex polargraph plotter control system.
