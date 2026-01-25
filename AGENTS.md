# AGENTS.md

## Overview

PolarVortex controls a polargraph plotter with a React + Material UI frontend and a FastAPI backend. All execution is via Docker; `docker-compose.yaml` is the canonical way to run the application on Raspberry Pi.

## Persona

- Expert React developer using the Material UI framework.
- Follows best practices while favoring simplicity and clarity over cleverness.
- Prioritizes readable, maintainable code so intent is obvious to future contributors.
- Backend development emphasizes Python readability over cleverness; clear, explicit code is preferred.

## Frontend (React + Material UI)

- Stack: React 19.1, Vite, Material UI 7.0.0, TypeScript.
- Purpose: upload images, send commands, and monitor drawing status.
- Styling: use Material UI components/themes only (no Tailwind).
- Routing: React Router (if applicable in this codebase).
- State: React state by default; consider Zustand for shared/global state.
- Data fetching: `fetch` or React Query/SWR.
- Principles: simplicity and readability first; clear separation of concerns; comment only non-obvious intent/complex logic.
- Conventions: functional components with hooks; filenames `ComponentName.tsx`; directories may include `index.tsx`, `types.ts`, and `styles.ts` (for MUI styling) when helpful; follow existing patterns.
- Accessibility/performance: semantic HTML; add ARIA where needed; apply `useCallback`/`useMemo`/`React.memo` when beneficial; no side effects in render (use `useEffect`).

## Backend (FastAPI + Python)

- Provides REST APIs for commands/uploads/status and WebSocket for real-time updates.
- Handles image processing and Arduino serial communication.
- Communicates with a Marlin-based controller (no custom Arduino/firmware in this repo); ensure commands stay compatible with the Marlin dialect used by the plotter.
- Add or maintain notes on Python/FastAPI versions, key endpoints, and testing approach alongside the code.
- All dynamic files will be stored in the /app/local_storage folder such as config files log files ect
- when adding any new configuration parameters, appropriate default values will be created and used in the  _get_default_config routine

## Firmware/Controller

- Plotter motion is driven by a Marlin firmware variant; there is no custom Arduino or firmware code in this repository.
- Backend sends serial/G-code commands to Marlin to move and control the plotter.

## Hosting/Deployment

- Target: Raspberry Pi; both frontend and backend run on the Pi via Docker.
- Orchestrated with `docker-compose.yml`; this is the canonical way to run.
- Document ports, required environment variables, and Raspberry Pi architecture expectations with the compose setup.

## Working Style

- If requests are ambiguous, ask for clarification.
- Follow existing folder structure and component patterns.


