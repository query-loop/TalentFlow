"""
Tor network integration for anonymous web scraping.
"""
from __future__ import annotations

import asyncio
import time
import os
from typing import Optional, Tuple
import httpx
import logging

logger = logging.getLogger(__name__)

class TorRotator:
    def __init__(self, tor_port: int = None, control_port: int = None, password: str = "", host: str = None):
        # Support dockerized Tor via env
        self.tor_host = host or os.getenv("TOR_HOST", "127.0.0.1")
        self.tor_port = tor_port or int(os.getenv("TOR_SOCKS_PORT", "9050"))
        self.control_port = control_port or int(os.getenv("TOR_CONTROL_PORT", "9051"))
        self.password = password or os.getenv("TOR_PASSWORD", "")
        self.last_rotation = 0
        self.min_rotation_interval = 10  # seconds
        self.available = self._check_tor_availability()

    def _check_tor_availability(self) -> bool:
        """Check if Tor and stem are available"""
        try:
            import stem
            from stem.control import Controller
            # Try to connect to control port
            with Controller.from_port(address=self.tor_host, port=self.control_port) as controller:
                if self.password:
                    controller.authenticate(password=self.password)
                else:
                    controller.authenticate()
                return True
        except ImportError:
            logger.warning("Tor not available: stem library not installed. Install with: pip install stem")
            return False
        except Exception as e:
            logger.warning(f"Tor not available: {e}")
            return False

    def is_available(self) -> bool:
        """Check if Tor is available for use"""
        return self.available

    async def rotate_ip(self) -> bool:
        """Request new Tor circuit (new IP)"""
        if not self.available:
            return False
            
        current_time = time.time()
        if current_time - self.last_rotation < self.min_rotation_interval:
            return True  # Too soon to rotate
        
        try:
            from stem import Signal
            from stem.control import Controller
            
            with Controller.from_port(address=self.tor_host, port=self.control_port) as controller:
                if self.password:
                    controller.authenticate(password=self.password)
                else:
                    controller.authenticate()
                
                controller.signal(Signal.NEWNYM)
                self.last_rotation = current_time
                
                # Wait for new circuit
                await asyncio.sleep(3)
                logger.info("Tor IP rotated successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to rotate Tor IP: {e}")
            return False

    async def fetch_with_tor(self, url: str, rotate_first: bool = False, timeout: float = 30.0) -> Tuple[str, int]:
        """Fetch URL through Tor"""
        if not self.available:
            raise RuntimeError("Tor is not available")
            
        if rotate_first:
            await self.rotate_ip()
        
        proxies = {
            'http://': f'socks5://{self.tor_host}:{self.tor_port}',
            'https://': f'socks5://{self.tor_host}:{self.tor_port}'
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                headers=headers,
                follow_redirects=True
            ) as client:
                resp = await client.get(url, proxies=proxies)
                return resp.text, resp.status_code
        except Exception as e:
            logger.error(f"Tor fetch failed for {url}: {e}")
            return "", 0

    async def get_current_ip(self) -> Optional[str]:
        """Get current Tor exit IP"""
        if not self.available:
            return None
            
        html, status = await self.fetch_with_tor("http://httpbin.org/ip")
        if status == 200:
            import json
            try:
                data = json.loads(html)
                return data.get("origin")
            except Exception:
                pass
        return None

    async def test_tor_connection(self) -> bool:
        """Test if Tor connection is working"""
        if not self.available:
            return False
            
        try:
            ip = await self.get_current_ip()
            return ip is not None
        except Exception:
            return False