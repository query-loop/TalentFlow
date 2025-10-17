# TalentFlow Frontend

SvelteKit + Tailwind starter.

## Scripts

Environment:
The app supports both relative API calls and absolute base URLs.

- Dev (Vite): API calls use relative paths (e.g., `/api/...`). Vite proxies them to the backend using `BACKEND_BASE`.
	- Set `BACKEND_BASE` to your backend URL (defaults to `http://localhost:8080`).
	- Works seamlessly on localhost and Codespaces (same-origin from the browser).
- Prod (Built app): Set `PUBLIC_API_BASE` to your backend URL if frontend and backend are on different origins.
	- If you serve frontend and backend from the same origin and path, you can leave `PUBLIC_API_BASE` unset and use reverse proxying.

Examples:

- Local dev: `BACKEND_BASE=http://localhost:8080` (default). Start with `npm run dev`.
- Codespaces: expose ports 5173 and 8080; `BACKEND_BASE` defaults to the internal backend URL; browser uses `/api/...` via proxy.
- Production (separate domains): `PUBLIC_API_BASE=https://api.example.com` then `npm run build && npm run preview` or deploy the static/SSR as needed.
