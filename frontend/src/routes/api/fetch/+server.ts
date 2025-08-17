import type { RequestHandler } from '@sveltejs/kit';

const PRIVATE_HOSTS = [
  'localhost',
  '127.0.0.1',
  '::1'
];

function isPrivateHost(hostname: string) {
  const hn = hostname.toLowerCase();
  if (PRIVATE_HOSTS.includes(hn)) return true;
  if (/^127\./.test(hn)) return true;
  if (/^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[0-1])\.)/.test(hn)) return true;
  return false;
}

export const POST: RequestHandler = async ({ request, fetch }) => {
  try {
    const { url } = await request.json();
    if (!url || typeof url !== 'string') {
      return new Response(JSON.stringify({ error: 'Missing url' }), { status: 400 });
    }
    let parsed: URL;
    try { parsed = new URL(url); } catch {
      return new Response(JSON.stringify({ error: 'Invalid URL' }), { status: 400 });
    }
    if (!/^https?:$/.test(parsed.protocol)) {
      return new Response(JSON.stringify({ error: 'Only http/https allowed' }), { status: 400 });
    }
    if (isPrivateHost(parsed.hostname)) {
      return new Response(JSON.stringify({ error: 'Host not allowed' }), { status: 400 });
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    try {
      const res = await fetch(parsed.toString(), {
        headers: {
          'user-agent': 'TalentFlowBot/1.0 (+https://example.invalid)'
        },
        signal: controller.signal
      });
      if (!res.ok) {
        return new Response(JSON.stringify({ error: `Upstream ${res.status}` }), { status: 502 });
      }
      const text = await res.text();
      // Cap response size to ~1MB
      const capped = text.length > 1_000_000 ? text.slice(0, 1_000_000) : text;
      return new Response(JSON.stringify({ html: capped }), {
        headers: { 'content-type': 'application/json' }
      });
    } finally {
      clearTimeout(timeout);
    }
  } catch (e) {
    return new Response(JSON.stringify({ error: 'Failed to fetch URL' }), { status: 500 });
  }
};
