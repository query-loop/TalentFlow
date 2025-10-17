"""
Free proxy rotation system with testing and automatic updates.
"""
from __future__ import annotations

import asyncio
import random
import time
from typing import List, Optional, Dict, Any
import httpx
import logging

logger = logging.getLogger(__name__)

class FreeProxyRotator:
    def __init__(self):
        self.proxies: List[Dict[str, str]] = []
        self.current_index = 0
        self.last_updated = 0
        self.update_interval = 3600  # 1 hour
        self.test_url = "http://httpbin.org/ip"
        self.max_proxies = 50

    async def fetch_free_proxies(self) -> List[Dict[str, str]]:
        """Fetch proxies using enhanced free sources"""
        try:
            from .free_proxy_sources import FreeProxySources
            sources = FreeProxySources()
            proxies = await sources.fetch_all_proxies()
            return proxies[:self.max_proxies]
        except Exception as e:
            logger.warning(f"Enhanced proxy sources failed, using fallback: {e}")
            return await self._fetch_fallback_proxies()

    async def _fetch_fallback_proxies(self) -> List[Dict[str, str]]:
        """Fallback proxy fetching method"""
        proxies = []
        
        # Simple GitHub source as fallback
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt")
                if resp.status_code == 200:
                    for line in resp.text.strip().split('\n'):
                        if ':' in line and len(line.split(':')) == 2:
                            ip, port = line.strip().split(':')
                            if self._is_valid_ip_port(ip, port):
                                proxies.append({
                                    'http://': f'http://{ip}:{port}',
                                    'https://': f'http://{ip}:{port}'
                                })
        except Exception as e:
            logger.warning(f"Fallback proxy fetch failed: {e}")

        random.shuffle(proxies)
        return proxies[:20]  # Limit fallback to 20 proxies

    def _is_valid_ip_port(self, ip: str, port: str) -> bool:
        """Basic validation for IP and port"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            for part in parts:
                if not (0 <= int(part) <= 255):
                    return False
            port_int = int(port)
            return 1 <= port_int <= 65535
        except (ValueError, TypeError):
            return False

    async def test_proxy(self, proxy: Dict[str, str], timeout: float = 5.0) -> bool:
        """Test if proxy is working"""
        try:
            async with httpx.AsyncClient(proxies=proxy, timeout=timeout) as client:
                resp = await client.get(self.test_url)
                return resp.status_code == 200
        except Exception:
            return False

    async def update_proxies(self):
        """Update proxy list with working proxies"""
        if time.time() - self.last_updated < self.update_interval and self.proxies:
            return

        logger.info("Updating proxy list...")
        raw_proxies = await self.fetch_free_proxies()
        
        if not raw_proxies:
            logger.warning("No proxies fetched from sources")
            return
        
        # Test proxies concurrently (limit concurrency to avoid overwhelming)
        working_proxies = []
        semaphore = asyncio.Semaphore(10)
        
        async def test_with_semaphore(proxy):
            async with semaphore:
                if await self.test_proxy(proxy):
                    return proxy
                return None
        
        logger.info(f"Testing {len(raw_proxies)} proxies...")
        tasks = [test_with_semaphore(proxy) for proxy in raw_proxies]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        working_proxies = [p for p in results if p is not None and not isinstance(p, Exception)]
        
        if working_proxies:
            self.proxies = working_proxies
            random.shuffle(self.proxies)
            logger.info(f"Updated proxy list: {len(self.proxies)} working proxies")
            self.current_index = 0
        else:
            logger.warning("No working proxies found")
        
        self.last_updated = time.time()

    async def get_next_proxy(self) -> Optional[Dict[str, str]]:
        """Get next proxy in rotation"""
        await self.update_proxies()
        
        if not self.proxies:
            return None
        
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy

    def get_proxy_count(self) -> int:
        """Get current number of available proxies"""
        return len(self.proxies)