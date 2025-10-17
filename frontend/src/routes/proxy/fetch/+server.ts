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
          'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
          'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
          'accept-language': 'en-US,en;q=0.9',
          'cache-control': 'no-cache',
          'pragma': 'no-cache',
          'upgrade-insecure-requests': '1',
          'sec-ch-ua': '"Chromium";v="123", "Not:A-Brand";v="8"',
          'sec-ch-ua-mobile': '?0',
          'sec-ch-ua-platform': '"Linux"',
          'sec-fetch-site': 'cross-site',
          'sec-fetch-mode': 'navigate',
          'sec-fetch-dest': 'document',
          'referer': parsed.origin + '/',
          // Optional cookie hint: comment out if problematic
          // 'cookie': 'locale=en_US;'
        },
        redirect: 'follow',
        signal: controller.signal,
      });
      const text = await res.text();
      if (!res.ok) {
        const body = text.length > 10_000 ? text.slice(0, 10_000) : text;
        return new Response(JSON.stringify({ error: `Upstream ${res.status}`, body }), { status: 502, headers: { 'content-type': 'application/json' } });
      }
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
