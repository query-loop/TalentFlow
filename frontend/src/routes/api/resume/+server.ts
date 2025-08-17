import { json, text } from '@sveltejs/kit';
import { proxyGet } from '$lib/server/backend';

export async function GET() {
  const res = await proxyGet('/resume');
  if (!res.ok) return json({ error: 'upstream', status: res.status }, { status: 502 });
  return text(await res.text());
}
