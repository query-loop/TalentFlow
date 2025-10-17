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

## Hot Module Replacement (HMR) Configuration

The Vite dev server's HMR (Hot Module Replacement) is automatically configured for different environments:

- **Local Development**: HMR uses `ws://` and connects to the same host as the browser
- **GitHub Codespaces**: Automatically detects `CODESPACE_NAME` and configures:
  - Protocol: `wss://` (secure WebSocket for HTTPS)
  - Host: `${CODESPACE_NAME}-5173.app.github.dev`
  - Port: `443` (HTTPS port)

### Manual Override

If you need to customize HMR configuration (e.g., for other cloud IDEs or custom setups), set these environment variables:

```bash
export HMR_PROTOCOL=wss       # 'ws' or 'wss'
export HMR_HOST=your-host.example.com
export HMR_CLIENT_PORT=443    # Port number
```

The auto-detection will be overridden by explicit environment variables.
