#!/usr/bin/env python3
"""
Browser Automation Setup for ComfyUI Testing
Supports both Playwright and CDP (Chrome DevTools Protocol)
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
import json
import time
from datetime import datetime

# Try to import Playwright first (preferred)
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️  Playwright not available")

# Try to import CDP (Chrome DevTools Protocol) as fallback
try:
    import websockets
    import aiohttp
    CDP_AVAILABLE = True
except ImportError:
    CDP_AVAILABLE = False
    print("⚠️  CDP libraries not available")

# Try Selenium as final fallback
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️  Selenium not available")

class ComfyUIBrowserAutomation:
    """Comprehensive browser automation for ComfyUI testing"""

    def __init__(self, comfyui_url: str = "http://localhost:8188"):
        self.comfyui_url = comfyui_url
        self.browser = None
        self.context = None
        self.page = None
        self.automation_method = None

    async def detect_best_method(self) -> str:
        """Detect the best available automation method"""
        if PLAYWRIGHT_AVAILABLE:
            return "playwright"
        elif CDP_AVAILABLE:
            return "cdp"
        elif SELENIUM_AVAILABLE:
            return "selenium"
        else:
            raise Exception("No browser automation method available")

    async def setup_playwright(self, headless: bool = True) -> bool:
        """Setup Playwright browser automation"""
        try:
            self.playwright = await async_playwright().start()

            # Launch browser with optimal settings for ComfyUI
            self.browser = await self.playwright.chromium.launch(
                headless=headless,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection',
                    '--enable-unsafe-swiftshader',
                    '--disable-software-rasterizer',
                ]
            )

            # Create context with good performance settings
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            )

            self.page = await self.context.new_page()
            self.automation_method = "playwright"

            print("✅ Playwright browser automation setup complete")
            return True

        except Exception as e:
            print(f"❌ Playwright setup failed: {e}")
            return False

    async def setup_cdp(self, headless: bool = True) -> bool:
        """Setup Chrome DevTools Protocol automation"""
        try:
            # Launch Chrome with remote debugging
            import subprocess

            chrome_args = [
                '/usr/bin/google-chrome',
                '--remote-debugging-port=9222',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--headless' if headless else '',
                f'--user-data-dir=/tmp/chrome_debug_{int(time.time())}'
            ]

            chrome_args = [arg for arg in chrome_args if arg]  # Remove empty args

            self.chrome_process = subprocess.Popen(chrome_args)
            time.sleep(3)  # Wait for Chrome to start

            # Connect to CDP via WebSocket
            self.cdp_ws_url = "ws://localhost:9222/devtools/browser"
            self.cdp_websocket = await websockets.connect(self.cdp_ws_url)

            self.automation_method = "cdp"
            print("✅ CDP browser automation setup complete")
            return True

        except Exception as e:
            print(f"❌ CDP setup failed: {e}")
            return False

    def setup_selenium(self, headless: bool = True) -> bool:
        """Setup Selenium browser automation"""
        try:
            chrome_options = Options()

            if headless:
                chrome_options.add_argument('--headless')

            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-setuid-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')

            # Disable images and CSS for faster loading (optional)
            chrome_options.add_argument('--blink-settings=imagesEnabled=false')

            self.driver = webdriver.Chrome(options=chrome_options)
            self.automation_method = "selenium"

            print("✅ Selenium browser automation setup complete")
            return True

        except Exception as e:
            print(f"❌ Selenium setup failed: {e}")
            return False

    async def setup(self, headless: bool = True, preferred_method: Optional[str] = None) -> bool:
        """Setup browser automation with preferred or best available method"""

        if preferred_method == "playwright" and PLAYWRIGHT_AVAILABLE:
            return await self.setup_playwright(headless)
        elif preferred_method == "cdp" and CDP_AVAILABLE:
            return await self.setup_cdp(headless)
        elif preferred_method == "selenium" and SELENIUM_AVAILABLE:
            return self.setup_selenium(headless)
        else:
            # Auto-detect best method
            method = await self.detect_best_method()
            print(f"🔄 Auto-detected best method: {method}")

            if method == "playwright":
                return await self.setup_playwright(headless)
            elif method == "cdp":
                return await self.setup_cdp(headless)
            elif method == "selenium":
                return self.setup_selenium(headless)

        return False

    async def navigate_to_comfyui(self) -> bool:
        """Navigate to ComfyUI interface"""
        try:
            if self.automation_method == "playwright":
                await self.page.goto(self.comfyui_url, wait_until='networkidle')
                await self.page.wait_for_selector('.comfyui-body', timeout=10000)
                print(f"✅ Navigated to ComfyUI: {self.comfyui_url}")
                return True

            elif self.automation_method == "selenium":
                self.driver.get(self.comfyui_url)
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'comfyui-body'))
                )
                print(f"✅ Navigated to ComfyUI: {self.comfyui_url}")
                return True

        except Exception as e:
            print(f"❌ Failed to navigate to ComfyUI: {e}")
            return False

    async def wait_for_comfyui_ready(self, timeout: int = 30) -> bool:
        """Wait for ComfyUI to be fully loaded and ready"""
        try:
            if self.automation_method == "playwright":
                # Wait for key ComfyUI elements
                await self.page.wait_for_selector('#queue-button', timeout=timeout * 1000)
                await self.page.wait_for_selector('#queue-button', state='visible')

                # Check if queue is empty or processing
                queue_status = await self.page.query_selector('#queue-button')
                if queue_status:
                    print("✅ ComfyUI queue system detected")

                return True

            elif self.automation_method == "selenium":
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.ID, 'queue-button'))
                )
                return True

        except Exception as e:
            print(f"❌ ComfyUI not ready after {timeout}s: {e}")
            return False

    async def take_screenshot(self, filename: Optional[str] = None) -> str:
        """Take a screenshot of the current page"""
        if filename is None:
            filename = f"comfyui_screenshot_{int(time.time())}.png"

        try:
            if self.automation_method == "playwright":
                await self.page.screenshot(path=filename)
            elif self.automation_method == "selenium":
                self.driver.save_screenshot(filename)

            print(f"📸 Screenshot saved: {filename}")
            return filename

        except Exception as e:
            print(f"❌ Screenshot failed: {e}")
            return ""

    async def get_page_title(self) -> str:
        """Get the current page title"""
        try:
            if self.automation_method == "playwright":
                return await self.page.title()
            elif self.automation_method == "selenium":
                return self.driver.title
        except:
            return ""

    async def check_queue_status(self) -> Dict[str, Any]:
        """Check ComfyUI queue status"""
        try:
            if self.automation_method == "playwright":
                queue_button = await self.page.query_selector('#queue-button')
                if queue_button:
                    text = await queue_button.inner_text()
                    return {"status": "found", "text": text, "running": True}
                else:
                    return {"status": "not_found", "text": "", "running": False}

            elif self.automation_method == "selenium":
                try:
                    queue_button = self.driver.find_element(By.ID, 'queue-button')
                    text = queue_button.text
                    return {"status": "found", "text": text, "running": True}
                except:
                    return {"status": "not_found", "text": "", "running": False}

        except Exception as e:
            return {"status": "error", "error": str(e), "running": False}

    async def cleanup(self):
        """Clean up browser resources"""
        try:
            if self.automation_method == "playwright":
                if self.context:
                    await self.context.close()
                if self.browser:
                    await self.browser.close()

            elif self.automation_method == "cdp":
                if hasattr(self, 'cdp_websocket'):
                    await self.cdp_websocket.close()
                if hasattr(self, 'chrome_process'):
                    self.chrome_process.terminate()

            elif self.automation_method == "selenium":
                if hasattr(self, 'driver'):
                    self.driver.quit()

            print("✅ Browser cleanup complete")

        except Exception as e:
            print(f"❌ Cleanup error: {e}")

async def test_browser_automation():
    """Test the browser automation setup"""
    print("🤖 Testing Browser Automation for ComfyUI")
    print("=" * 50)

    automation = ComfyUIBrowserAutomation()

    try:
        # Setup with best available method
        success = await automation.setup(headless=True)
        if not success:
            print("❌ Failed to setup browser automation")
            return False

        # Test navigation to ComfyUI
        success = await automation.navigate_to_comfyui()
        if not success:
            print("❌ Failed to navigate to ComfyUI")
            return False

        # Wait for ComfyUI to be ready
        success = await automation.wait_for_comfyui_ready()
        if not success:
            print("⚠️  ComfyUI might not be fully ready")

        # Get page info
        title = await automation.get_page_title()
        print(f"📄 Page title: {title}")

        # Check queue status
        queue_status = await automation.check_queue_status()
        print(f"📊 Queue status: {queue_status}")

        # Take screenshot
        screenshot = await automation.take_screenshot()

        print("✅ Browser automation test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

    finally:
        await automation.cleanup()

if __name__ == "__main__":
    asyncio.run(test_browser_automation())