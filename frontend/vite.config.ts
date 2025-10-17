import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// Auto-detect GitHub Codespaces environment
const isCodespaces = process.env.CODESPACE_NAME !== undefined;

// Set defaults for Codespaces if not explicitly configured
const HMR_HOST = process.env.HMR_HOST || (isCodespaces ? process.env.CODESPACE_NAME + '-5173.app.github.dev' : undefined);
const HMR_CLIENT_PORT = process.env.HMR_CLIENT_PORT ? Number(process.env.HMR_CLIENT_PORT) : (isCodespaces ? 443 : undefined);
const HMR_PROTOCOL = process.env.HMR_PROTOCOL || (isCodespaces ? 'wss' : 'ws');

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    host: true,
    strictPort: true,
    port: 5173,
    hmr: {
      // Use ws locally; set HMR_PROTOCOL=wss in Codespaces/HTTPS proxies
      protocol: HMR_PROTOCOL as 'ws' | 'wss',
      ...(HMR_CLIENT_PORT ? { clientPort: HMR_CLIENT_PORT } : {}),
      // If HMR_HOST is set, use it; otherwise let Vite default to window.location.hostname
      ...(HMR_HOST ? { host: HMR_HOST } : {})
    },
    proxy: {
      // Proxy API calls to the backend during dev so browser uses same origin
      '/api': {
        target: process.env.BACKEND_BASE || 'http://localhost:8080',
        changeOrigin: true,
        secure: false,
        // Don't rewrite the path; keep /api prefix
      }
    }
  }
});
