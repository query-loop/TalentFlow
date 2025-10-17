"""
Advanced job extraction with IP rotation and anti-blocking techniques.
Enhanced with comprehensive anti-bot detection and mitigation.
"""
from __future__ import annotations

import asyncio
import os
import time
import random
from typing import Optional, Tuple, Dict, Any, List
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
import logging

from .proxy_rotator import FreeProxyRotator
from .tor_rotator import TorRotator
from .antibot import antibot
from .stealth_browser import stealth_browser

logger = logging.getLogger(__name__)

# Global cache and rate limiting
_CACHE: Dict[str, Tuple[float, str, int]] = {}
_LAST_HIT: Dict[str, float] = {}

BLOCK_MARKERS = [
    "captcha", "are you a robot", "robot check", "access denied",
    "forbidden", "error 403", "blocked", "verify you are human",
    "attention required | cloudflare", "request was denied",
    "temporarily unavailable", "checking your browser", "ddos protection",
    "security check", "please wait", "ray id", "cloudflare"
]

DEFAULT_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "upgrade-insecure-requests": "1",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "dnt": "1",
    "connection": "keep-alive",
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

class IPRotationManager:
    def __init__(self):
        self.free_proxy_rotator = FreeProxyRotator()
        self.tor_rotator = TorRotator()
        
        # Configuration from environment
        self.rotation_strategy = os.getenv("IP_ROTATION_STRATEGY", "free_proxy")  # free_proxy, tor, mixed, aggressive
        self.rotation_interval = int(os.getenv("IP_ROTATION_INTERVAL", "5"))
        self.request_count = 0
        self.cache_ttl = 10.0  # seconds
        self.rate_limit_delay = 1.5  # seconds between requests to same host
        
        # Free anti-bot alternatives available
        self.free_antibot_available = True  # Always available as it's open source

    def _blocked(self, html: str, status: int, url: str = "") -> Optional[Dict[str, Any]]:
        """Enhanced blocking detection using antibot system"""
        return antibot.detect_blocking(html, status, url)

    async def _respect_rate_limit(self, host: str) -> None:
        """Enforce per-host rate limiting"""
        now = time.time()
        last = _LAST_HIT.get(host, 0.0)
        gap = now - last
        if gap < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - gap)
        _LAST_HIT[host] = time.time()

    def _cache_get(self, url: str) -> Optional[Tuple[str, int]]:
        """Get cached response if available and fresh"""
        entry = _CACHE.get(url)
        if not entry:
            return None
        timestamp, html, status = entry
        if time.time() - timestamp <= self.cache_ttl:
            return html, status
        _CACHE.pop(url, None)
        return None

    def _cache_put(self, url: str, html: str, status: int) -> None:
        """Cache response"""
        _CACHE[url] = (time.time(), html, status)

    def _get_random_headers(self, url: str, previous_url: str = None) -> Dict[str, str]:
        """Get realistic headers using antibot system"""
        return antibot.generate_realistic_headers(url, previous_url)

    async def _fetch_direct(self, url: str, timeout: float = 25.0) -> Tuple[str, int]:
        """Direct fetch without proxy with enhanced anti-bot measures"""
        # Track request for pattern analysis
        antibot.track_request(url)
        
        # Get realistic headers
        headers = self._get_random_headers(url)
        
        # Simulate human behavior delays
        behavior = antibot.simulate_human_behavior()
        await asyncio.sleep(behavior["delay_before_request"])
        
        try:
            async with httpx.AsyncClient(
                headers=headers,
                timeout=timeout,
                follow_redirects=True,
                http2=True,
            ) as client:
                resp = await client.get(url)
                
                # Post-request delay
                await asyncio.sleep(behavior["delay_after_request"])
                
                return resp.text, resp.status_code
        except Exception as e:
            logger.warning(f"Direct fetch failed for {url}: {e}")
            return "", 0

    async def _fetch_with_proxy(self, url: str, timeout: float = 25.0) -> Tuple[str, int]:
        """Fetch using free proxy rotation with anti-bot measures"""
        proxy = await self.free_proxy_rotator.get_next_proxy()
        if not proxy:
            return await self._fetch_direct(url, timeout)
        
        # Track request and apply human behavior
        antibot.track_request(url)
        headers = self._get_random_headers(url)
        behavior = antibot.simulate_human_behavior()
        await asyncio.sleep(behavior["delay_before_request"])
        
        try:
            async with httpx.AsyncClient(
                proxies=proxy,
                headers=headers,
                timeout=timeout,
                follow_redirects=True,
            ) as client:
                resp = await client.get(url)
                await asyncio.sleep(behavior["delay_after_request"])
                return resp.text, resp.status_code
        except Exception as e:
            logger.warning(f"Proxy fetch failed for {url}: {e}")
            return await self._fetch_direct(url, timeout)

    async def _fetch_with_tor(self, url: str, rotate_first: bool = False) -> Tuple[str, int]:
        """Fetch using Tor"""
        if not self.tor_rotator.is_available():
            return await self._fetch_with_proxy(url)
        
        try:
            return await self.tor_rotator.fetch_with_tor(url, rotate_first=rotate_first)
        except Exception as e:
            logger.warning(f"Tor fetch failed for {url}: {e}")
            return await self._fetch_with_proxy(url)

    async def _fetch_with_free_antibot(self, url: str) -> Tuple[str, int]:
        """Fetch using free anti-bot alternatives"""
        try:
            from .free_antibot import fetch_html_antibot_free
            return await fetch_html_antibot_free(url)
        except Exception as e:
            logger.warning(f"Free anti-bot fetch failed for {url}: {e}")
            return "", 0

    async def _fetch_with_browser_automation(self, url: str) -> Tuple[str, int]:
        """Fetch using browser automation (Selenium/undetected-chrome)"""
        try:
            from .free_antibot import FreeScrapingAlternatives
            alternatives = FreeScrapingAlternatives()
            
            # Try undetected chrome first, then regular selenium
            if alternatives.undetected_chrome_available:
                return await alternatives.fetch_with_undetected_chrome(url)
            elif alternatives.selenium_available:
                return await alternatives.fetch_with_selenium(url)
            else:
                return "", 0
        except Exception as e:
            logger.warning(f"Browser automation fetch failed for {url}: {e}")
            return "", 0

    async def _fetch_with_stealth_browser(self, url: str) -> Tuple[str, int]:
        """Fetch using stealth browser automation"""
        try:
            logger.info(f"Using stealth browser for {url}")
            
            # Check if we need to solve challenges
            domain = urlparse(url).netloc
            if "cloudflare" in url.lower() or antibot.is_domain_blocked(domain):
                return await stealth_browser.solve_cloudflare_challenge(url)
            else:
                return await stealth_browser.fetch_with_browser(url)
                
        except Exception as e:
            logger.warning(f"Stealth browser fetch failed for {url}: {e}")
            return "", 0

    async def _try_solve_challenge(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """Attempt to solve simple challenges"""
        return await antibot.solve_simple_challenge(html, url)

    async def fetch_with_rotation(self, url: str, max_retries: int = 3) -> Tuple[str, int, Optional[str]]:
        """
        Fetch URL with IP rotation and anti-blocking techniques.
        Returns (html, status, blocked_reason)
        """
        # Check cache first
        cached = self._cache_get(url)
        if cached:
            html, status = cached
            blocked_reason = self._blocked(html, status)
            return html, status, blocked_reason

        # Rate limiting
        parsed = urlparse(url)
        await self._respect_rate_limit(parsed.netloc)

        self.request_count += 1
        
        # Determine strategy based on configuration, request count, and anti-bot analysis
        strategies = self._get_fetch_strategies(url)
        
        last_error = None
        
        for attempt in range(max_retries):
            strategy = strategies[attempt % len(strategies)]
            
            try:
                logger.info(f"Attempt {attempt + 1} for {url} using strategy: {strategy}")
                
                # Apply rotation if needed
                if self.request_count % self.rotation_interval == 0 and strategy == "tor":
                    await self.tor_rotator.rotate_ip()
                
                # Fetch based on strategy
                if strategy == "direct":
                    html, status = await self._fetch_direct(url)
                elif strategy == "proxy":
                    html, status = await self._fetch_with_proxy(url)
                elif strategy == "tor":
                    html, status = await self._fetch_with_tor(url, rotate_first=(attempt > 0))
                elif strategy == "free_antibot":
                    html, status = await self._fetch_with_free_antibot(url)
                elif strategy == "browser":
                    html, status = await self._fetch_with_browser_automation(url)
                elif strategy == "stealth_browser":
                    html, status = await self._fetch_with_stealth_browser(url)
                else:
                    html, status = await self._fetch_direct(url)
                
                # Enhanced blocking detection
                block_info = self._blocked(html, status, url)
                
                if not block_info and html:
                    # Success - cache and return
                    self._cache_put(url, html, status)
                    logger.info(f"Successfully fetched {url} with {strategy}")
                    return html, status, None
                
                if block_info:
                    domain = urlparse(url).netloc
                    antibot.mark_domain_blocked(domain)
                    
                    logger.warning(f"Blocked response from {url} with {strategy}: {block_info}")
                    
                    # Try to solve simple challenges
                    if block_info.get("suggested_action") == "use_browser_automation":
                        if strategy != "stealth_browser":
                            logger.info("Switching to stealth browser for challenge solving")
                            try:
                                html, status = await self._fetch_with_stealth_browser(url)
                                if html and len(html) > 1000:
                                    self._cache_put(url, html, status)
                                    return html, status, None
                            except Exception as e:
                                logger.warning(f"Stealth browser fallback failed: {e}")
                    
                    last_error = block_info.get("type", "blocked")
                
                # Add delay between attempts
                if attempt < max_retries - 1:
                    delay = (attempt + 1) * 2.0
                    await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"Error fetching {url} with {strategy}: {e}")
                last_error = str(e)
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0 + attempt * 0.5)

        # All attempts failed
        return "", 0, last_error

    def _get_fetch_strategies(self, url: str = "") -> List[str]:
        """Get intelligent fetch strategies based on configuration and anti-bot analysis"""
        # Analyze request patterns
        pattern_analysis = antibot.get_request_pattern_analysis()
        domain = urlparse(url).netloc if url else ""
        
        # Base strategies from configuration
        base_strategies = []
        
        if self.rotation_strategy == "direct":
            base_strategies = ["direct"]
        elif self.rotation_strategy == "free_proxy":
            base_strategies = ["proxy", "direct"]
        elif self.rotation_strategy == "tor":
            if self.tor_rotator.is_available():
                base_strategies = ["tor", "proxy", "direct"]
            else:
                base_strategies = ["proxy", "direct"]
        elif self.rotation_strategy == "mixed":
            base_strategies = ["proxy", "direct"]
            if self.tor_rotator.is_available():
                base_strategies.insert(0, "tor")
        elif self.rotation_strategy == "aggressive":
            base_strategies = ["stealth_browser", "free_antibot"]
            if self.tor_rotator.is_available():
                base_strategies.append("tor")
            base_strategies.extend(["proxy", "direct"])
        else:
            base_strategies = ["proxy", "direct"]
        
        # Adjust strategies based on analysis
        if pattern_analysis["risk_score"] > 0.7:
            # High risk - use more sophisticated methods
            if "stealth_browser" not in base_strategies:
                base_strategies.insert(0, "stealth_browser")
            if "tor" not in base_strategies and self.tor_rotator.is_available():
                base_strategies.insert(1, "tor")
        
        # If domain is blocked, prioritize browser automation
        if antibot.is_domain_blocked(domain):
            if "stealth_browser" not in base_strategies:
                base_strategies.insert(0, "stealth_browser")
        
        # If we should rotate identity, ensure we have rotation methods
        if antibot.should_rotate_identity():
            if "tor" not in base_strategies and self.tor_rotator.is_available():
                base_strategies.insert(0, "tor")
        
        return base_strategies

    async def get_current_ip(self) -> Optional[str]:
        """Get current public IP"""
        try:
            if self.rotation_strategy == "tor" and self.tor_rotator.is_available():
                return await self.tor_rotator.get_current_ip()
            else:
                html, status = await self._fetch_direct("http://httpbin.org/ip")
                if status == 200:
                    import json
                    data = json.loads(html)
                    return data.get("origin")
        except Exception:
            pass
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get rotation statistics"""
        return {
            "request_count": self.request_count,
            "rotation_strategy": self.rotation_strategy,
            "rotation_interval": self.rotation_interval,
            "cache_size": len(_CACHE),
            "free_proxies_available": self.free_proxy_rotator.get_proxy_count(),
            "tor_available": self.tor_rotator.is_available(),
            "free_antibot_available": self.free_antibot_available,
            "browser_automation_available": True,
        }