from __future__ import annotations

import os
import random
import re
from typing import Dict, Optional, Tuple
import time

import httpx


UA_POOL = [
    # Realistic, varied desktop UA strings for better bot evasion
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
]


def _parse_proxy_pool(env_var: str = "PROXY_URLS") -> list[str]:
    raw = os.getenv(env_var, "").strip()
    if not raw:
        return []
    parts = re.split(r"[\s,]+", raw)
    return [p for p in parts if p]


def choose_proxy() -> Optional[str]:
    pool = _parse_proxy_pool()
    if not pool:
        return None
    return random.choice(pool)


def random_headers() -> Dict[str, str]:
    ua = random.choice(UA_POOL)
    # Vary accept headers slightly to look more natural
    accept_variations = [
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    ]
    lang_variations = [
        "en-US,en;q=0.9",
        "en-US,en;q=0.8,fr;q=0.6",
        "en-US,en;q=0.9,es;q=0.8",
    ]
    return {
        "User-Agent": ua,
        "Accept": random.choice(accept_variations),
        "Accept-Language": random.choice(lang_variations),
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }


def _has_usable_html(text: str) -> bool:
    t = text.strip().lower()
    if len(t) < 200:
        return False
    return ("<html" in t) or ("<body" in t)


async def fetch_html(url: str, *, timeout: float = 25.0, tries: int = 3, follow_redirects: bool = True) -> Tuple[str, int]:
    """
    Fetch HTML with smart retry logic and anti-detection headers.
    Returns (html, http_status). Raises on failure to obtain usable HTML after retries.
    """
    last_status = 0
    last_error: Optional[Exception] = None

    # Simple in-process per-host rate limiting and short TTL cache
    # Note: this is per-process best-effort; for multi-worker, consider Redis keys
    from urllib.parse import urlparse
    parsed = urlparse(url)
    host = parsed.netloc
    now = time.time()
    # Basic rate limiting state (module-level singletons)
    global _RATE_LIMIT, _HTML_CACHE
    try:
        _RATE_LIMIT
    except NameError:
        _RATE_LIMIT = {}
    try:
        _HTML_CACHE
    except NameError:
        _HTML_CACHE = {}
    # Cache lookup (10s TTL)
    cache_entry = _HTML_CACHE.get(url)
    if cache_entry and (now - cache_entry[0] < 10):
        return cache_entry[1], cache_entry[2]
    # Per-host min interval 1.5s between requests
    last_hit = _RATE_LIMIT.get(host, 0)
    delay = 1.5 - max(0.0, now - last_hit)
    if delay > 0:
        import asyncio
        await asyncio.sleep(delay)
    
    for attempt in range(max(1, tries)):
        headers = random_headers()
        # Add slight delay between attempts to avoid rate limiting
        if attempt > 0:
            import asyncio
            await asyncio.sleep(random.uniform(1.0, 3.0))
        
        try:
            proxy = choose_proxy()
            async with httpx.AsyncClient(
                timeout=timeout, 
                follow_redirects=follow_redirects,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            ) as client:
                req_kwargs = {"headers": headers}
                if proxy:
                    req_kwargs["proxies"] = proxy
                resp = await client.get(url, **req_kwargs)

            last_status = resp.status_code
            html = resp.text

            # Accept any response with usable HTML, even if status isn't perfect
            if resp.is_success or _has_usable_html(html):
                # update caches
                _HTML_CACHE[url] = (time.time(), html, last_status)
                _RATE_LIMIT[host] = time.time()
                return html, last_status

        except Exception as e:
            last_error = e
            continue
    
    # If we exhausted retries
    if last_error:
        raise last_error
    raise RuntimeError(f"Failed to fetch usable HTML (last status {last_status})")


async def fetch_html_via_scraperapi(url: str, *, render: bool = False, timeout: float = 30.0) -> Tuple[str, int]:
    """Fetch HTML using ScraperAPI if SCRAPERAPI_KEY is configured.
    Returns (html, status). Raises if key missing or request fails.
    """
    key = os.getenv("SCRAPERAPI_KEY")
    if not key:
        raise RuntimeError("SCRAPERAPI_KEY not set")
    params = {
        "api_key": key,
        "url": url,
        "render": "true" if render else "false",
        "keep_headers": "true",
    }
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.get("https://api.scraperapi.com/", params=params)
        return resp.text, resp.status_code




async def fetch_html_antibot(url: str) -> Tuple[str, int]:
    """Fetch HTML using only free anti-bot methods (browser automation, Tor, free proxies). No paid APIs."""
    from app.utils.free_antibot import fetch_html_antibot_free
    return await fetch_html_antibot_free(url)
