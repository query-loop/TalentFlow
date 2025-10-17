"""
Enhanced browser automation with advanced anti-detection techniques.
Uses undetected-chrome and stealth techniques to bypass bot detection.
"""
from __future__ import annotations

import asyncio
import os
import time
import random
from typing import Optional, Tuple, Dict, Any, List
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

class StealthBrowser:
    """
    Browser automation with advanced anti-detection capabilities.
    """
    
    def __init__(self):
        self.driver = None
        self.is_initialized = False
        self.stealth_enabled = True
        
    async def initialize(self) -> bool:
        """Initialize the stealth browser"""
        try:
            # Try undetected-chrome first (best for anti-detection)
            if await self._init_undetected_chrome():
                self.is_initialized = True
                return True
            
            # Fallback to regular selenium with stealth
            if await self._init_selenium_stealth():
                self.is_initialized = True
                return True
            
            logger.warning("Failed to initialize any browser automation")
            return False
            
        except Exception as e:
            logger.error(f"Browser initialization failed: {e}")
            return False
    
    async def _init_undetected_chrome(self) -> bool:
        """Initialize undetected-chrome driver"""
        try:
            import undetected_chromedriver as uc
            from selenium.webdriver.chrome.options import Options
            
            # Chrome options for stealth
            options = Options()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Randomize window size
            window_sizes = [
                (1920, 1080), (1366, 768), (1536, 864), (1440, 900), (1280, 720)
            ]
            width, height = random.choice(window_sizes)
            options.add_argument(f'--window-size={width},{height}')
            
            # Additional stealth options
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins-discovery')
            options.add_argument('--disable-web-security')
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36')
            
            # Run in headless mode if specified
            if os.getenv('SELENIUM_HEADLESS') == '1':
                options.add_argument('--headless=new')
            
            # Initialize undetected chrome
            self.driver = uc.Chrome(options=options, version_main=None)
            
            # Additional stealth measures
            await self._apply_stealth_measures()
            
            logger.info("Undetected Chrome initialized successfully")
            return True
            
        except ImportError:
            logger.info("undetected-chromedriver not available, trying selenium")
            return False
        except Exception as e:
            logger.warning(f"Undetected Chrome initialization failed: {e}")
            return False
    
    async def _init_selenium_stealth(self) -> bool:
        """Initialize regular selenium with stealth measures"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            import chromedriver_autoinstaller
            
            # Auto-install chromedriver
            chromedriver_autoinstaller.install()
            
            # Chrome options
            options = Options()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Randomize user agent
            from ..antibot import AntiBot
            antibot = AntiBot()
            headers = antibot.generate_realistic_headers("https://example.com")
            options.add_argument(f'--user-agent={headers["User-Agent"]}')
            
            # Randomize window size
            window_sizes = [(1920, 1080), (1366, 768), (1536, 864), (1440, 900)]
            width, height = random.choice(window_sizes)
            options.add_argument(f'--window-size={width},{height}')
            
            if os.getenv('SELENIUM_HEADLESS') == '1':
                options.add_argument('--headless=new')
            
            # Initialize driver
            self.driver = webdriver.Chrome(options=options)
            
            # Apply stealth measures
            await self._apply_stealth_measures()
            
            logger.info("Selenium Chrome initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Selenium initialization failed: {e}")
            return False
    
    async def _apply_stealth_measures(self) -> None:
        """Apply JavaScript-based stealth measures"""
        if not self.driver:
            return
        
        try:
            # Remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Override chrome runtime
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            """)
            
            # Override permissions
            self.driver.execute_script("""
                const originalQuery = window.navigator.permissions.query;
                return window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            
            # Randomize screen properties
            screen_width = random.randint(1200, 1920)
            screen_height = random.randint(800, 1080)
            
            self.driver.execute_script(f"""
                Object.defineProperty(screen, 'width', {{
                    get: () => {screen_width}
                }});
                Object.defineProperty(screen, 'height', {{
                    get: () => {screen_height}
                }});
            """)
            
        except Exception as e:
            logger.warning(f"Failed to apply some stealth measures: {e}")
    
    async def fetch_with_browser(self, url: str, wait_time: float = 3.0) -> Tuple[str, int]:
        """
        Fetch a page using browser automation with human-like behavior.
        """
        if not self.is_initialized:
            if not await self.initialize():
                return "", 0
        
        try:
            # Simulate human behavior before navigation
            await self._simulate_pre_navigation_behavior()
            
            # Navigate to the page
            logger.info(f"Navigating to {url} with browser automation")
            self.driver.get(url)
            
            # Wait for initial load
            await asyncio.sleep(random.uniform(2.0, 4.0))
            
            # Simulate human-like interactions
            await self._simulate_human_interactions()
            
            # Wait for dynamic content
            await asyncio.sleep(wait_time)
            
            # Get page source
            html = self.driver.page_source
            
            # Simulate post-load behavior
            await self._simulate_post_load_behavior()
            
            return html, 200
            
        except Exception as e:
            logger.error(f"Browser fetch failed for {url}: {e}")
            return "", 0
    
    async def _simulate_pre_navigation_behavior(self) -> None:
        """Simulate behavior before navigating to target page"""
        try:
            # Sometimes visit a common site first (like Google)
            if random.random() < 0.3:
                self.driver.get("https://www.google.com")
                await asyncio.sleep(random.uniform(1.0, 2.0))
            
        except Exception as e:
            logger.warning(f"Pre-navigation simulation failed: {e}")
    
    async def _simulate_human_interactions(self) -> None:
        """Simulate human-like mouse movements and scrolling"""
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            from selenium.webdriver.common.by import By
            
            actions = ActionChains(self.driver)
            
            # Random mouse movements
            if random.random() < 0.7:
                for _ in range(random.randint(2, 5)):
                    x = random.randint(100, 800)
                    y = random.randint(100, 600)
                    actions.move_by_offset(x, y)
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                
                actions.perform()
            
            # Random scrolling
            if random.random() < 0.8:
                for _ in range(random.randint(2, 6)):
                    scroll_amount = random.randint(200, 800)
                    self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # Scroll back up sometimes
                if random.random() < 0.4:
                    self.driver.execute_script("window.scrollTo(0, 0);")
                    await asyncio.sleep(random.uniform(0.5, 1.0))
            
            # Random clicks on non-interactive elements (but safely)
            if random.random() < 0.3:
                try:
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    actions.move_to_element(body).click().perform()
                    await asyncio.sleep(random.uniform(0.2, 0.5))
                except:
                    pass  # Ignore click failures
            
        except Exception as e:
            logger.warning(f"Human interaction simulation failed: {e}")
    
    async def _simulate_post_load_behavior(self) -> None:
        """Simulate behavior after page loads"""
        try:
            # Sometimes wait a bit longer (reading time)
            if random.random() < 0.5:
                await asyncio.sleep(random.uniform(1.0, 3.0))
            
            # Random final scroll
            if random.random() < 0.4:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                await asyncio.sleep(random.uniform(0.5, 1.0))
            
        except Exception as e:
            logger.warning(f"Post-load simulation failed: {e}")
    
    async def solve_cloudflare_challenge(self, url: str, max_wait: float = 30.0) -> Tuple[str, int]:
        """
        Attempt to solve Cloudflare challenges automatically.
        """
        if not self.is_initialized:
            if not await self.initialize():
                return "", 0
        
        try:
            logger.info(f"Attempting to solve Cloudflare challenge for {url}")
            
            # Navigate to the page
            self.driver.get(url)
            
            # Wait for challenge to load
            await asyncio.sleep(3.0)
            
            # Check if we're on a challenge page
            page_source = self.driver.page_source.lower()
            if "checking your browser" in page_source or "cloudflare" in page_source:
                logger.info("Cloudflare challenge detected, waiting for resolution...")
                
                # Wait for challenge to resolve
                start_time = time.time()
                while time.time() - start_time < max_wait:
                    await asyncio.sleep(2.0)
                    current_source = self.driver.page_source.lower()
                    
                    # Check if challenge is resolved
                    if ("checking your browser" not in current_source and 
                        "cloudflare" not in current_source and
                        len(current_source) > 1000):
                        logger.info("Cloudflare challenge appears to be resolved")
                        break
                
                # Additional wait for page to fully load
                await asyncio.sleep(3.0)
            
            # Simulate human behavior after challenge
            await self._simulate_human_interactions()
            
            return self.driver.page_source, 200
            
        except Exception as e:
            logger.error(f"Cloudflare challenge solving failed: {e}")
            return "", 0
    
    async def get_cookies(self) -> List[Dict[str, Any]]:
        """Get all cookies from the current session"""
        if not self.driver:
            return []
        
        try:
            return self.driver.get_cookies()
        except Exception as e:
            logger.warning(f"Failed to get cookies: {e}")
            return []
    
    async def set_cookies(self, cookies: List[Dict[str, Any]]) -> None:
        """Set cookies for the current session"""
        if not self.driver or not cookies:
            return
        
        try:
            for cookie in cookies:
                self.driver.add_cookie(cookie)
        except Exception as e:
            logger.warning(f"Failed to set cookies: {e}")
    
    def close(self) -> None:
        """Close the browser"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
            finally:
                self.driver = None
                self.is_initialized = False
    
    def __del__(self):
        """Cleanup on destruction"""
        self.close()

# Global stealth browser instance
stealth_browser = StealthBrowser()