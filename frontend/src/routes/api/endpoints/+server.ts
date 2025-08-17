import { json } from '@sveltejs/kit';
import { proxyGet } from '$lib/server/backend';

export async function GET() {
  const res = await proxyGet('/api/endpoints');
  if (!res.ok) return json({ error: 'upstream', status: res.status }, { status: 502 });
  return json(await res.json());
}
