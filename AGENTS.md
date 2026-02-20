# AGENTS.md

## Overview

PolarVortex controls a polargraph plotter with a React + Material UI frontend and a FastAPI backend. All execution is via Docker; `docker-compose.yml` is the canonical way to run the application on Raspberry Pi.

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
- All dynamic files will be stored in the /app/local_storage folder (e.g. config files, log files, etc.).
- When adding any new configuration parameters, create appropriate default values in the `_get_default_config` routine.

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

## Working Agreements

- Use `gh` for issues, PRs, and repo operations.
- Follow the project management standards in `PROJECT_PLANNING.md` when creating/refining issues.
- Create a feature branch per issue off `dev`.
- Add tests for changes and ensure they pass before PRs.
- Do not commit secrets or backend config files.
- Prefer small, focused commits with clear messages.

## Agent Dev Workflow (Issue → Branch → PR)

This section is the default execution loop for agents. If the user gives different instructions, follow the user.

1) Open (or refine) an Issue

- Use the issue forms in `.github/ISSUE_TEMPLATE/` and the standards in `PROJECT_PLANNING.md`.
- Recommended (uses the GitHub UI so required fields are enforced): `gh issue create --web`

1) Create a feature branch off `dev` (one branch per issue)

- Recommended (links the branch to the issue): `gh issue develop <issue_number> --base dev --checkout --name issue-<issue_number>-short-slug`
- Alternative (git only): `git fetch origin && git checkout -b issue-<issue_number>-short-slug origin/dev`

1) Do the dev work

- Keep changes focused to the Issue’s Outcome/Requirements.
- Follow any more-specific `AGENTS.md` files under the target area (`backend/`, `frontend/`).
- Do **not** commit secrets or local backend config (e.g., `.env.*`, `infra/**/backend.tf`).

1) Add tests + run checks

- Add or update tests that cover the change.
- Run the narrowest relevant checks first, then broader smoke checks as appropriate (see `./scripts/smoke_local.sh`).

1) Human feedback checkpoint (default)

- Unless explicitly told not to, pause after implementation + tests and ask for a quick human check on scope/behavior before finalizing a PR for review/merge.

1) Create and push a PR that closes the Issue

- Push branch: `git push -u origin HEAD`
- Create PR (draft recommended until human confirms): `gh pr create --base dev --draft --fill --body "Closes #<issue_number>"`
- Ensure the PR links the Issue (e.g., `Closes #123`) and includes a concrete demo/test plan.
- By default, a human merges PRs (see `PROJECT_PLANNING.md` “Definition of Done”).
