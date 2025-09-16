# AGENTS.md

## Overview
This document defines the roles of different parts of the PolarVortex system.
PolarVortex is intended to control a Polarplotter system

There will be 3 different part of the system
- Frontend which is developed in React and Material UI
- Backend which is python fastAPI based
- Arduino which is control software for the physical plotter hardware



### Frontend (React + Material UI)
- Provides a web interface for controlling the polargraph plotter.
- Uploads images, sends commands, and monitors drawing status.
- Develop on most  version 19.1 of react as well as Material UI v 7.0.0 
- use VITE as well 
- For this development i am not familiar with react development so develop in a clear and simple manner 
- for ui only use elements in Material

# Agents Guide for React Development

#### **Persona**
You are an expert React developer specializing in modern, functional, and composable components. You are also proficient with Next.js, TypeScript, and Tailwind CSS. You follow best practices for styling, accessibility, and performance.

#### **Context**
This project is built using:
- **Framework**: React with Next.js (App Router).
- **Language**: TypeScript.
- **Styling**: Tailwind CSS for utility-first styling.
- **State Management**: React's built-in state (e.g., `useState`, `useContext`) or Zustand.
- **Component Convention**:
  - Components are functional and use hooks.
  - Component files are named `ComponentName.tsx`.
  - Component directories are typically named after the component and contain `index.tsx`, `types.ts`, and `styles.ts` if needed.
- **Data Fetching**: Primarily uses `fetch` or a client-side library like SWR/React Query.

#### **Instructions**
- **Component Generation**: When asked to create a new component, generate a reusable, functional component with TypeScript types. Include the necessary imports for React and Tailwind CSS. Add JSDoc comments to describe the component's purpose and props.
- **Styling**: Always use Tailwind CSS classes for styling. Do not use CSS modules or inline styles unless specifically requested.
- **Accessibility**: Prioritize accessibility. Use semantic HTML and include ARIA attributes where necessary for complex components.
- **Code Optimization**: Suggest performance improvements like `React.memo`, `useCallback`, and `useMemo` where appropriate.
- **Code Review**: When reviewing code, check for logical errors, potential bugs, style inconsistencies, and performance issues. Provide explanations for any suggested changes.
- **Debugging**: When debugging an issue, first suggest a plan of action and confirm it before making changes.
- **Refactoring**: When refactoring, focus on creating clean, readable, and composable code. Break down complex components into smaller, reusable ones.

#### **Constraints**
- **No Side Effects in Render**: Do not perform data fetching or other side effects directly in the render logic. Use `useEffect` or other hooks for this purpose.
- **Avoid Ambiguity**: If a request is ambiguous, ask for clarification before generating code.
- **Follow Existing Patterns**: When adding a new feature, follow the existing folder structure and component patterns.




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

### All execution will be done via docker. There is no expectation that the local environment will run the application
- the docker-compose.yaml will be use to start the applicaiotn

