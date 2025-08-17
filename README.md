# TalentFlow

Monorepo with:
- frontend: SvelteKit + Tailwind
- backend: Kotlin Ktor

## Quick start (Docker Compose)

1. Start both services
	- Docker is required.
	- From repo root, run docker compose up.
2. Visit http://localhost:5173 for frontend. Backend runs on http://localhost:8080

## Local development (no Docker)

Run both apps with one command. The scripts start the Ktor backend on :8080 and the SvelteKit dev server on :5173 in the background, and print where to visit.

### Start both

```bash
make dev-up
```

### Stop both

```bash
make dev-down
```

### Tail logs

```bash
make dev-logs
```

### Environment variables

- BACKEND_BASE: URL the frontend server-side proxy will call (default http://localhost:8080)
- PUBLIC_API_BASE: optional public URL for client-side code; defaults to BACKEND_BASE

Example:

```bash
BACKEND_BASE=http://localhost:9090 make dev-up
```

### Backend endpoints

- GET / -> "TalentFlow backend is running"
- GET /ping -> "pong"
- GET /api/health -> {"status":"ok"}
- GET /resume -> "your resume has been curating..."
- GET /api/endpoints -> JSON list of endpoints

On the frontend, use same-origin routes under /api that proxy to the backend:

- GET /api/ping -> backend /ping
- GET /api/resume -> backend /resume
- GET /api/endpoints -> backend /api/endpoints

### Troubleshooting

- Port in use: stop prior processes (`make dev-down`) or change ports in scripts/dev-up.sh.
- Frontend fetch fails: using same-origin `/api/*` avoids CORS. Ensure BACKEND_BASE is reachable.
- Backend not ready: check `.run/backend.log` and `.run/frontend.log` via `make dev-logs`.

## Structure

```
frontend/   # SvelteKit app (Tailwind)
backend/    # Ktor server (Kotlin)
```

## License
This project is licensed under the terms of the [LICENSE](LICENSE) file in this repository.
