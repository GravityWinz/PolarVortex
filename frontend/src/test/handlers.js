import { http, HttpResponse } from "msw";

// Base URL resolved by apiService defaults to http://localhost:8000 in tests
const API_BASE = "http://localhost:8000";

export const handlers = [
  http.get(`${API_BASE}/projects`, () =>
    HttpResponse.json({ projects: [], total: 0 })
  ),
  http.post(`${API_BASE}/projects`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      id: "p1",
      name: body.name,
      gcode_files: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
  }),
  http.get(`${API_BASE}/config/papers/default`, () =>
    HttpResponse.json({
      id: "paper-default",
      paper_size: "A4",
      width: 210,
      height: 297,
    })
  ),
];

