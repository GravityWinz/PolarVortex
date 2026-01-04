# Testing Guide

This project uses FastAPI (backend) and Vite/React (frontend). Tests are split into backend pytest suites and frontend Vitest suites.

## Backend (pytest)

- Location: `backend/tests/`
- Fixtures: `conftest.py` provides isolated `PV_CONFIG` and `local_storage` per test and a FastAPI `TestClient`.
- Sample commands:
  - Run all: `pytest backend/app --cov=backend.app`
  - Quiet: `pytest backend/app -q`
  - Filter: `pytest backend/app -k upload`
- Run inside Docker:
  - Build (if needed): `docker compose build backend`
  - One-off test run: `docker compose run --rm backend pytest -q`
  - Against running container: `docker  compose up -d backend && docker compose exec backend pytest -q`
- Areas covered:
  - Project lifecycle (create/get/delete)
  - Upload validation (image/gcode) and path traversal guards
  - Config defaults via temp storage
- Requirements: install `backend/requirements-dev.txt` (or `requirements.txt` + `pytest`, `pytest-asyncio`, `httpx`).

## Frontend (Vitest + Testing Library + MSW)

- Location: `frontend/src/__tests__/` with MSW setup in `frontend/src/test/`.
- Config: `vite.config.js` sets `happy-dom` environment and `setupFiles`.
- Sample commands (from `frontend`):
  - Install deps: `npm install`
  - Run once: `npm run test:unit`
  - Watch: `npm run test`
  - Lint: `npm run lint`
- MSW mocks `http://localhost:8000` APIs for deterministic component tests.

## Quick start

Backend:

1) `cd backend`
2) `pip install -r requirements-dev.txt`
3) `pytest backend/app --cov=backend.app`

Frontend:

1) `cd frontend`
2) `npm install`
3) `npm run test:unit`

## Notes

- Tests avoid real hardware: serial access is mocked via the simulator in app code.
- Frontend tests stub network with MSW; ensure no live backend is required.
- Use `-k` or `--runInBand` (Vitest: `--runInBand`) if debugging single tests.
