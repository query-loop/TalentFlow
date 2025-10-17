"""
Free proxy sources that don't require API keys.
"""
from __future__ import annotations

import asyncio
import random
import logging
from typing import List, Dict, Optional
import httpx

logger = logging.getLogger(__name__)

class FreeProxySources:
    """Aggregates free proxy sources without requiring API keys"""
    
    def __init__(self):
        self.sources = [
            self._fetch_from_github_1,
            self._fetch_from_github_2, 
            self._fetch_from_github_3,
            self._fetch_from_pubproxy,
            self._fetch_from_freeproxyworld,
        ]

    async def fetch_all_proxies(self) -> List[Dict[str, str]]:
        """Fetch proxies from all available sources"""
        all_proxies = []
        
        for source in self.sources:
            try:
                proxies = await source()
                all_proxies.extend(proxies)
                logger.info(f"Fetched {len(proxies)} proxies from {source.__name__}")
            except Exception as e:
                logger.warning(f"Failed to fetch from {source.__name__}: {e}")
                continue
        
        # Remove duplicates
        seen = set()
        unique_proxies = []
        for proxy in all_proxies:
            proxy_url = list(proxy.values())[0]  # Get the proxy URL
            if proxy_url not in seen:
                seen.add(proxy_url)
                unique_proxies.append(proxy)
        
        logger.info(f"Total unique proxies found: {len(unique_proxies)}")
        random.shuffle(unique_proxies)
        return unique_proxies[:100]  # Limit to 100 best proxies

    async def _fetch_from_github_1(self) -> List[Dict[str, str]]:
        """Fetch from TheSpeedX/PROXY-List repository"""
        proxies = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt")
                if resp.status_code == 200:
                    for line in resp.text.strip().split('\n'):
                        if self._is_valid_proxy_line(line):
                            proxies.append(self._format_proxy(line))
        except Exception as e:
            logger.warning(f"GitHub source 1 failed: {e}")
        return proxies

    async def _fetch_from_github_2(self) -> List[Dict[str, str]]:
        """Fetch from clarketm/proxy-list repository"""
        proxies = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get("https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt")
                if resp.status_code == 200:
                    for line in resp.text.strip().split('\n'):
                        if self._is_valid_proxy_line(line):
                            proxies.append(self._format_proxy(line))
        except Exception as e:
            logger.warning(f"GitHub source 2 failed: {e}")
        return proxies

    async def _fetch_from_github_3(self) -> List[Dict[str, str]]:
        """Fetch from proxy4parsing/proxy-list repository"""
        proxies = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get("https://raw.githubusercontent.com/proxy4parsing/proxy-list/main/http.txt")
                if resp.status_code == 200:
                    for line in resp.text.strip().split('\n'):
                        if self._is_valid_proxy_line(line):
                            proxies.append(self._format_proxy(line))
        except Exception as e:
            logger.warning(f"GitHub source 3 failed: {e}")
        return proxies

    async def _fetch_from_pubproxy(self) -> List[Dict[str, str]]:
        """Fetch from pubproxy.com free API"""
        proxies = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # PubProxy free API - no key required, limited to 50 requests/day
                resp = await client.get("http://pubproxy.com/api/proxy?limit=20&format=txt&type=http")
                if resp.status_code == 200:
                    for line in resp.text.strip().split('\n'):
                        if self._is_valid_proxy_line(line):
                            proxies.append(self._format_proxy(line))
        except Exception as e:
            logger.warning(f"PubProxy source failed: {e}")
        return proxies

    async def _fetch_from_freeproxyworld(self) -> List[Dict[str, str]]:
        """Scrape proxies from free proxy world (fallback)"""
        proxies = []
        try:
            # This would require scraping, so for now return empty
            # In a real implementation, you could scrape proxy sites
            pass
        except Exception as e:
            logger.warning(f"FreeProxyWorld source failed: {e}")
        return proxies

    def _is_valid_proxy_line(self, line: str) -> bool:
        """Validate proxy line format"""
        if not line or not line.strip():
            return False
        
        line = line.strip()
        if ':' not in line:
            return False
        
        try:
            ip, port = line.split(':', 1)
            # Basic IP validation
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            for part in parts:
                if not (0 <= int(part) <= 255):
                    return False
            # Port validation
            port_int = int(port)
            if not (1 <= port_int <= 65535):
                return False
            return True
        except (ValueError, AttributeError):
            return False

    def _format_proxy(self, proxy_line: str) -> Dict[str, str]:
        """Format proxy line into httpx proxy dict"""
        return {
            'http://': f'http://{proxy_line.strip()}',
            'https://': f'http://{proxy_line.strip()}'
        }

# Enhanced proxy rotator that uses free sources
class EnhancedFreeProxyRotator:
    def __init__(self):
        self.proxy_sources = FreeProxySources()
        self.proxies: List[Dict[str, str]] = []
        self.current_index = 0
        self.last_updated = 0
        self.update_interval = 1800  # 30 minutes
        self.test_timeout = 3.0  # Faster testing

    async def update_proxies(self):
        """Update proxy list from free sources"""
        import time
        
        if time.time() - self.last_updated < self.update_interval and self.proxies:
            return

        logger.info("Updating proxy list from free sources...")
        raw_proxies = await self.proxy_sources.fetch_all_proxies()
        
        if not raw_proxies:
            logger.warning("No proxies fetched from any source")
            return
        
        # Test proxies concurrently with higher concurrency for speed
        working_proxies = []
        semaphore = asyncio.Semaphore(20)  # Higher concurrency
        
        async def test_with_semaphore(proxy):
            async with semaphore:
                if await self._test_proxy_fast(proxy):
                    return proxy
                return None
        
        logger.info(f"Testing {len(raw_proxies)} proxies...")
        tasks = [test_with_semaphore(proxy) for proxy in raw_proxies]
        
        # Use asyncio.wait with timeout for faster processing
        done, pending = await asyncio.wait(tasks, timeout=30.0)
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
        
        # Collect results
        working_proxies = []
        for task in done:
            try:
                result = await task
                if result:
                    working_proxies.append(result)
            except Exception:
                continue
        
        if working_proxies:
            self.proxies = working_proxies
            random.shuffle(self.proxies)
            logger.info(f"Updated proxy list: {len(self.proxies)} working proxies")
            self.current_index = 0
        else:
            logger.warning("No working proxies found from free sources")
        
        self.last_updated = time.time()

    async def _test_proxy_fast(self, proxy: Dict[str, str], timeout: float = 3.0) -> bool:
        """Fast proxy testing with shorter timeout"""
        try:
            async with httpx.AsyncClient(proxies=proxy, timeout=timeout) as client:
                resp = await client.get("http://httpbin.org/ip")
                return resp.status_code == 200 and len(resp.text) > 0
        except Exception:
            return False

    async def get_next_proxy(self) -> Optional[Dict[str, str]]:
        """Get next working proxy"""
        await self.update_proxies()
        
        if not self.proxies:
            return None
        
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy

    def get_proxy_count(self) -> int:
        """Get current number of available proxies"""
        return len(self.proxies)