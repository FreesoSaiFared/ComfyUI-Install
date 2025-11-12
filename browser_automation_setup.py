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

    def __init__(self, comfyui_url: str = "http://localhost:8188", headless: bool = True, debug_port: int = 9222):
        self.comfyui_url = comfyui_url
        self.browser = None
        self.context = None
        self.page = None
        self.automation_method = None
        self.headless = headless
        self.debug_port = debug_port
        self.chrome_process = None  # For external Chrome process management
        self.profile_dir = f"/tmp/chrome_automation_profile_{int(time.time())}"

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

    def get_chrome_launch_args(self, user_data_dir: str = None) -> list:
        """Get comprehensive Chrome launch arguments for automation"""
        args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-web-security',
            '--disable-features=TranslateUI,VizDisplayCompositor',
            '--disable-ipc-flooding-protection',
            '--disable-software-rasterizer',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-background-networking',
            '--disable-default-apps',
            '--disable-extensions',
            '--disable-sync',
            '--disable-translate',
            '--disable-new-profile-management',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-background-mode',
            '--disable-component-update',
            '--disable-domain-reliability',
            '--disable-features=AudioServiceOutOfProcess',
            '--disable-logging',
            '--silent-launch',
            '--disable-search-engine-choice-screen',
            '--disable-restore-session-state',
            '--auto-open-devtools-for-tabs',  # Keep for debugging
        ]

        # Add user data directory if specified
        if user_data_dir:
            args.extend([f'--user-data-dir={user_data_dir}'])

        return args

    async def check_chrome_debug_port(self) -> bool:
        """Check if Chrome is running on the debug port"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f'http://localhost:{self.debug_port}/json/version', timeout=3) as response:
                    if response.status == 200:
                        version_info = await response.json()
                        print(f"✅ Chrome debugging port {self.debug_port} is active: {version_info.get('Browser', 'Unknown')}")
                        return True
        except Exception as e:
            print(f"⚠️  Chrome debugging port {self.debug_port} not available: {e}")
        return False

    async def start_chrome_with_debug(self) -> bool:
        """Start Chrome with debugging port enabled for non-headless mode"""
        if self.headless:
            return True  # No need for external Chrome in headless mode

        try:
            import subprocess

            # Check if Chrome is already running on debug port
            if await self.check_chrome_debug_port():
                print(f"✅ Chrome already running on debug port {self.debug_port}")
                return True

            # Start Chrome with debugging enabled
            chrome_binary = '/usr/bin/google-chrome'

            # Create user data directory
            os.makedirs(self.profile_dir, exist_ok=True)

            chrome_args = self.get_chrome_launch_args(self.profile_dir)
            chrome_args.extend([
                f'--remote-debugging-port={self.debug_port}',
                '--remote-debugging-address=0.0.0.0',
                '--new-window',
                'about:blank'
            ])

            print(f"🚀 Starting Chrome with debugging on port {self.debug_port}...")
            print(f"📁 Profile directory: {self.profile_dir}")

            self.chrome_process = subprocess.Popen(
                [chrome_binary] + chrome_args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # Wait for Chrome to start
            for i in range(10):  # Wait up to 10 seconds
                await asyncio.sleep(1)
                if await self.check_chrome_debug_port():
                    print(f"✅ Chrome started successfully on debug port {self.debug_port}")
                    return True
                elif self.chrome_process.poll() is not None:
                    print(f"❌ Chrome process exited with code: {self.chrome_process.poll()}")
                    return False

            print("⚠️  Chrome started but debug port not responding")
            return False

        except Exception as e:
            print(f"❌ Failed to start Chrome with debug: {e}")
            return False

    async def setup_playwright(self, headless: bool = None) -> bool:
        """Setup Playwright browser automation with non-headless support"""
        if headless is None:
            headless = self.headless

        try:
            self.playwright = await async_playwright().start()

            # Start Chrome with debug port if non-headless
            if not headless:
                if not await self.start_chrome_with_debug():
                    print("⚠️  Failed to start external Chrome, falling back to headless mode")
                    headless = True

            if headless:
                # Headless mode - use internal Playwright browser
                args = self.get_chrome_launch_args()
                self.browser = await self.playwright.chromium.launch(
                    headless=True,
                    args=args
                )
            else:
                # Non-headless mode - connect to existing Chrome via CDP
                print(f"🔗 Connecting to Chrome on debug port {self.debug_port}...")
                self.browser = await self.playwright.chromium.connect_over_cdp(
                    f'http://localhost:{self.debug_port}'
                )

            # Create context with optimal settings for ComfyUI
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )

            self.page = await self.context.new_page()
            self.automation_method = "playwright"

            mode = "headless" if headless else "non-headless (GUI)"
            print(f"✅ Playwright browser automation setup complete ({mode})")
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

    async def setup(self, headless: Optional[bool] = None, preferred_method: Optional[str] = None) -> bool:
        """Setup browser automation with preferred or best available method"""

        # Use instance default if no headless parameter provided
        if headless is None:
            headless = self.headless

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
        """Clean up browser resources and external Chrome process"""
        try:
            # Close page and context first
            if hasattr(self, 'page') and self.page:
                await self.page.close()
            if hasattr(self, 'context') and self.context:
                await self.context.close()

            # Close browser based on method
            if self.automation_method == "playwright":
                if hasattr(self, 'browser') and self.browser:
                    await self.browser.close()
                if hasattr(self, 'playwright') and self.playwright:
                    await self.playwright.stop()

            elif self.automation_method == "cdp":
                if hasattr(self, 'cdp_websocket'):
                    await self.cdp_websocket.close()
                if hasattr(self, 'chrome_process') and self.chrome_process:
                    self.chrome_process.terminate()

            elif self.automation_method == "selenium":
                if hasattr(self, 'driver'):
                    self.driver.quit()

            # Clean up external Chrome process if we started it
            if self.chrome_process and not self.headless:
                try:
                    print("🔄 Shutting down external Chrome process...")
                    self.chrome_process.terminate()
                    try:
                        self.chrome_process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        print("⚠️  Chrome didn't terminate gracefully, forcing shutdown...")
                        self.chrome_process.kill()
                        self.chrome_process.wait()
                    print("✅ External Chrome process shut down")
                except Exception as chrome_error:
                    print(f"⚠️  Error shutting down Chrome: {chrome_error}")

            # Clean up profile directory if it exists
            if os.path.exists(self.profile_dir) and not self.headless:
                try:
                    import shutil
                    shutil.rmtree(self.profile_dir)
                    print(f"🗑️  Cleaned up profile directory: {self.profile_dir}")
                except Exception as cleanup_error:
                    print(f"⚠️  Could not clean up profile directory: {cleanup_error}")

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