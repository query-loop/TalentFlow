#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import sys

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context()
        page = context.new_page()
        page.on("console", lambda msg: print(f"CONSOLE [{msg.type}] {msg.text}"))
        page.on("request", lambda r: print(f"REQUEST {r.method} {r.url}"))
        page.on("response", lambda r: print(f"RESPONSE {r.status} {r.url}"))
        print("Navigating to /app/pipelines-v2...")
        page.goto("http://localhost:5173/app/pipelines-v2", timeout=30000)
        page.wait_for_timeout(8000)
        print("Capture complete; closing browser")
        browser.close()
except Exception as e:
    print("ERROR:", e)
    sys.exit(1)
