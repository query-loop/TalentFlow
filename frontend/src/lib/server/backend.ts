import { env as privateEnv } from '$env/dynamic/private';

export function getBackendBase(): string {
  // Prefer explicit BACKEND_BASE; fallback to PUBLIC_API_BASE (if set in env) or localhost
  return (
    privateEnv.BACKEND_BASE || privateEnv.PUBLIC_API_BASE || 'http://localhost:8080'
  );
}

export async function proxyGet(path: string, init?: RequestInit) {
  const base = getBackendBase();
  const url = `${base}${path}`;
  const res = await fetch(url, { method: 'GET', ...init });
  return res;
}
