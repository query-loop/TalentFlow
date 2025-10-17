import { PUBLIC_API_BASE } from '$env/static/public';

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const base = (typeof window !== 'undefined')
    ? ((PUBLIC_API_BASE && PUBLIC_API_BASE.length) ? PUBLIC_API_BASE : '')
    : (PUBLIC_API_BASE || '');
  const res = await fetch(`${base}${path}`, init);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}
