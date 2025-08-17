import type { RequestEvent } from '@sveltejs/kit';
import { json } from '@sveltejs/kit';

function tally(text: string) {
  const tokens = (text.toLowerCase().match(/[a-z][a-z+\-]{2,}/g) || []).filter((w) => !['and','the','for','with','from','this','that','you','are','was','were'].includes(w));
  const map = new Map<string, number>();
  for (const t of tokens) map.set(t, (map.get(t) || 0) + 1);
  return Array.from(map.entries()).map(([term, count]) => ({ term, count })).sort((a, b) => b.count - a.count);
}

export async function POST({ request }: RequestEvent) {
  const { text = '', jd = '' } = await request.json().catch(() => ({} as { text?: string; jd?: string }));
  const top = tally(text + ' ' + jd).slice(0, 20);
  return json(top);
}
