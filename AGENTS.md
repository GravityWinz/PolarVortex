# AGENTS.md

## Overview
This document defines the roles of different parts of the Polargraph system.

### Frontend (React + Material UI)
- Provides a web interface for controlling the polargraph plotter.
- Uploads images, sends commands, and monitors drawing status.

### Backend (FastAPI + Python)
- Provides REST API and WebSocket for real-time updates.
- Handles image processing and communication with Arduino.

### Arduino (C++/Arduino)
- Directly drives the motors and sensors of the polargraph system.
- Receives commands from backend over serial.

### Firebase Hosting
- Hosts the frontend web app for remote access.

### Deployment (Docker + Raspberry Pi)
- Dockerized services for easy deployment on Raspberry Pi.

