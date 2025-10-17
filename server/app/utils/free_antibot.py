"""
Free alternatives to paid scraping services using open-source tools.
"""
from __future__ import annotations

import asyncio
import os
import random
import tempfile
from typing import Tuple, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class FreeScrapingAlternatives:
    def __init__(self):
        self.selenium_available = self._check_selenium()
        self.undetected_chrome_available = self._check_undetected_chrome()

    def _check_selenium(self) -> bool:
        """Check if Selenium is available"""
        try:
            from selenium import webdriver
            return True
        except ImportError:
            logger.warning("Selenium not available. Install with: pip install selenium")
            return False

    def _check_undetected_chrome(self) -> bool:
        """Check if undetected-chromedriver is available"""
        try:
            import undetected_chromedriver as uc
            return True
        except ImportError:
            logger.warning("undetected-chromedriver not available. Install with: pip install undetected-chromedriver")
            return False

    async def fetch_with_selenium(self, url: str, timeout: float = 30.0) -> Tuple[str, int]:
        """Fetch using Selenium with Chrome in headless mode and auto ChromeDriver management"""
        if not self.selenium_available:
            return "", 0

        try:
            import chromedriver_autoinstaller
            chromedriver_autoinstaller.install()
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException

            # Configure Chrome options for stealth
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            # Randomize window size
            width = random.randint(1200, 1920)
            height = random.randint(800, 1080)
            chrome_options.add_argument(f"--window-size={width},{height}")

            # Random user agent
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            ]
            chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")

            # Create driver
            driver = webdriver.Chrome(options=chrome_options)

            try:
                # Execute stealth script
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

                # Navigate to URL
                driver.get(url)

                # Wait for page to load
                WebDriverWait(driver, timeout).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )

                # Additional wait for dynamic content
                await asyncio.sleep(2)

                # Get page source
                html = driver.page_source
                return html, 200

            finally:
                driver.quit()

        except Exception as e:
            logger.error(f"Selenium fetch failed for {url}: {e}")
            return "", 0

    async def fetch_with_undetected_chrome(self, url: str, timeout: float = 30.0) -> Tuple[str, int]:
        """Fetch using undetected-chromedriver for maximum stealth"""
        if not self.undetected_chrome_available:
            return await self.fetch_with_selenium(url, timeout)

        try:
            import undetected_chromedriver as uc
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            # Configure undetected Chrome
            options = uc.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            
            # Randomize window size
            width = random.randint(1200, 1920)
            height = random.randint(800, 1080)
            options.add_argument(f"--window-size={width},{height}")

            # Create undetected Chrome driver
            driver = uc.Chrome(options=options, version_main=None)
            
            try:
                # Navigate to URL
                driver.get(url)
                
                # Wait for page to load
                WebDriverWait(driver, timeout).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                
                # Additional wait for dynamic content
                await asyncio.sleep(3)
                
                # Get page source
                html = driver.page_source
                return html, 200
                
            finally:
                driver.quit()
                
        except Exception as e:
            logger.error(f"Undetected Chrome fetch failed for {url}: {e}")
            return await self.fetch_with_selenium(url, timeout)

    async def fetch_with_requests_session(self, url: str, proxy: Optional[str] = None) -> Tuple[str, int]:
        """Enhanced requests session with session persistence and cookies"""
        import httpx
        
        # Create session-like headers that persist across requests
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "User-Agent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            ])
        }

        proxies = {"all://": proxy} if proxy else None

        try:
            async with httpx.AsyncClient(
                headers=headers,
                proxies=proxies,
                timeout=25.0,
                follow_redirects=True,
                http2=True,
                cookies={}  # Session cookies will be handled automatically
            ) as client:
                # First, visit the main domain to establish session
                from urllib.parse import urlparse
                parsed = urlparse(url)
                base_url = f"{parsed.scheme}://{parsed.netloc}"
                
                try:
                    await client.get(base_url)
                    await asyncio.sleep(1)  # Brief pause
                except:
                    pass  # Ignore errors on base URL
                
                # Now fetch the actual URL
                resp = await client.get(url)
                return resp.text, resp.status_code
                
        except Exception as e:
            logger.error(f"Enhanced requests session failed for {url}: {e}")
            return "", 0

    async def fetch_with_curl_subprocess(self, url: str, proxy: Optional[str] = None) -> Tuple[str, int]:
        """Use curl subprocess as fallback method"""
        try:
            import subprocess
            
            cmd = [
                "curl", "-s", "-L", "--compressed",
                "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "-H", "Accept-Language: en-US,en;q=0.9",
                "-H", "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "--max-time", "30",
                "--retry", "2",
            ]
            
            if proxy:
                cmd.extend(["--proxy", proxy])
            
            cmd.append(url)
            
            # Run curl
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
            
            if result.returncode == 0:
                return result.stdout, 200
            else:
                logger.warning(f"Curl failed for {url}: {result.stderr}")
                return "", result.returncode
                
        except Exception as e:
            logger.error(f"Curl subprocess failed for {url}: {e}")
            return "", 0

class FreeAntiBot:
    """Free anti-bot service using multiple open-source techniques"""
    
    def __init__(self):
        self.scraping_alternatives = FreeScrapingAlternatives()
        
    async def fetch_antibot_free(self, url: str) -> Tuple[str, int]:
        """
        Try multiple free anti-bot techniques in order of effectiveness:
        1. Undetected Chrome (best for bypassing detection)
        2. Regular Selenium (good for JS-heavy sites)  
        3. Enhanced requests session (fastest)
        4. Curl subprocess (most basic fallback)
        """
        
        methods = [
            ("undetected_chrome", self.scraping_alternatives.fetch_with_undetected_chrome),
            ("selenium", self.scraping_alternatives.fetch_with_selenium),
            ("requests_session", self.scraping_alternatives.fetch_with_requests_session),
            ("curl", self.scraping_alternatives.fetch_with_curl_subprocess),
        ]
        
        for method_name, method in methods:
            try:
                logger.info(f"Trying {method_name} for {url}")
                html, status = await method(url)
                
                if html and status == 200:
                    # Quick check for block indicators
                    html_lower = html.lower()
                    block_indicators = [
                        "captcha", "are you a robot", "access denied", "blocked",
                        "cloudflare", "checking your browser"
                    ]
                    
                    if not any(indicator in html_lower for indicator in block_indicators):
                        logger.info(f"Successfully fetched {url} using {method_name}")
                        return html, status
                
                logger.warning(f"{method_name} for {url} returned status {status} or blocked content")
                
            except Exception as e:
                logger.warning(f"{method_name} failed for {url}: {e}")
                continue
        
        return "", 0

# Global instance
_free_antibot = FreeAntiBot()

async def fetch_html_antibot_free(url: str) -> Tuple[str, int]:
    """Free alternative to paid anti-bot services"""
    return await _free_antibot.fetch_antibot_free(url)