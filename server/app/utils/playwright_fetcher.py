"""
Lightweight Playwright fetcher for JS-rendered pages.
This provides an async `fetch_with_playwright(url, timeout=15)` that returns (html, status).
Note: requires `playwright` to be installed and browsers to be installed (`playwright install chromium`).
"""
from typing import Tuple
import asyncio
import logging

logger = logging.getLogger(__name__)

async def fetch_with_playwright(url: str, timeout: float = 15.0) -> Tuple[str, int]:
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = await browser.new_context()
            page = await context.new_page()
            try:
                await page.goto(url, timeout=int(timeout * 1000), wait_until='networkidle')
            except Exception:
                # try a more forgiving load
                try:
                    await page.goto(url, timeout=int(timeout * 1000))
                except Exception as e:
                    logger.warning(f"Playwright navigation failed for {url}: {e}")
                    await browser.close()
                    return "", 0

            # allow some time for dynamic content to settle
            try:
                await asyncio.sleep(0.5)
            except Exception:
                pass

            try:
                content = await page.content()
            except Exception as e:
                logger.warning(f"Playwright failed to get content for {url}: {e}")
                content = ""

            await browser.close()
            return content or "", 200 if content else 0

    except Exception as e:
        logger.warning(f"Playwright unavailable or failed: {e}")
        return "", 0
