#!/usr/bin/env python3
"""
Robust Browser Automation for ComfyUI
Enhanced error handling and multiple fallback options
"""

import asyncio
import sys
import os
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, Union
from datetime import datetime
import traceback

# Enhanced import handling with detailed error reporting
def safe_import(module_name: str, fallback: Any = None) -> Any:
    """Safely import a module with detailed error reporting"""
    try:
        if module_name == "playwright.async_api":
            from playwright.async_api import async_playwright, Browser, BrowserContext, Page
            return {"async_playwright": async_playwright, "Browser": Browser, "BrowserContext": BrowserContext, "Page": Page}
        elif module_name == "playwright":
            import playwright
            return playwright
        elif module_name == "selenium":
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.chrome.service import Service
            return {
                "webdriver": webdriver,
                "Options": Options,
                "By": By,
                "WebDriverWait": WebDriverWait,
                "EC": EC,
                "Service": Service
            }
        elif module_name == "websockets":
            import websockets
            return websockets
        elif module_name == "aiohttp":
            import aiohttp
            return aiohttp
        else:
            return __import__(module_name)
    except ImportError as e:
        print(f"⚠️  Import warning: {module_name} not available - {e}")
        return fallback
    except Exception as e:
        print(f"❌ Import error for {module_name}: {e}")
        traceback.print_exc()
        return fallback

# Try to import all required modules
playwright_modules = safe_import("playwright.async_api", {})
playwright_available = bool(playwright_modules)
selenium_modules = safe_import("selenium", {})
selenium_available = bool(selenium_modules)
websockets_available = safe_import("websockets") is not None
aiohttp_available = safe_import("aiohttp") is not None

print(f"📦 Module availability:")
print(f"   Playwright: {'✅' if playwright_available else '❌'}")
print(f"   Selenium: {'✅' if selenium_available else '❌'}")
print(f"   WebSockets: {'✅' if websockets_available else '❌'}")
print(f"   aiohttp: {'✅' if aiohttp_available else '❌'}")

class RobustComfyUIAutomation:
    """Robust ComfyUI browser automation with enhanced error handling"""

    def __init__(self, comfyui_url: str = "http://localhost:8188", headless: bool = True):
        self.comfyui_url = comfyui_url
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.automation_method = None
        self.driver = None
        self.chrome_process = None
        self.websocket = None
        self.playwright_instance = None

    async def detect_and_setup_best_method(self) -> str:
        """Detect and setup the best available automation method"""
        methods = []

        if playwright_available:
            methods.append("playwright")
        if websockets_available and aiohttp_available:
            methods.append("cdp")
        if selenium_available:
            methods.append("selenium")

        print(f"🔍 Available methods: {methods}")

        for method in methods:
            print(f"🧪 Trying method: {method}")
            try:
                if method == "playwright":
                    success = await self.setup_playwright()
                elif method == "cdp":
                    success = await self.setup_cdp()
                elif method == "selenium":
                    success = self.setup_selenium()
                else:
                    continue

                if success:
                    self.automation_method = method
                    print(f"✅ Successfully set up: {method}")
                    return method
                else:
                    print(f"❌ Failed to setup: {method}")
                    await self.cleanup_partial_setup(method)

            except Exception as e:
                print(f"❌ Error setting up {method}: {e}")
                await self.cleanup_partial_setup(method)
                traceback.print_exc()

        raise Exception("No browser automation method could be setup successfully")

    async def cleanup_partial_setup(self, method: str):
        """Clean up partial setup for a specific method"""
        try:
            if method == "playwright" and self.playwright_instance:
                await self.playwright_instance.stop()
                self.playwright_instance = None
            elif method == "cdp" and self.chrome_process:
                self.chrome_process.terminate()
                try:
                    self.chrome_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.chrome_process.kill()
                self.chrome_process = None
            elif method == "cdp" and self.websocket:
                await self.websocket.close()
                self.websocket = None
            elif method == "selenium" and self.driver:
                self.driver.quit()
                self.driver = None
        except Exception as e:
            print(f"⚠️  Cleanup warning for {method}: {e}")

    async def setup_playwright(self) -> bool:
        """Setup Playwright browser automation"""
        try:
            if not playwright_available:
                print("❌ Playwright modules not available")
                return False

            print("🎭 Starting Playwright...")
            self.playwright_instance = await playwright_modules["async_playwright"]().start()

            # Try different browser launch configurations
            launch_configs = [
                {
                    "headless": self.headless,
                    "args": ['--no-sandbox', '--disable-setuid-sandbox'],
                    "timeout": 30000
                },
                {
                    "headless": self.headless,
                    "args": ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
                    "timeout": 30000
                },
                {
                    "headless": self.headless,
                    "args": ['--no-sandbox'],
                    "timeout": 30000
                }
            ]

            for i, config in enumerate(launch_configs):
                try:
                    print(f"   Attempt {i+1}/3: Launching with args: {config['args']}")
                    self.browser = await self.playwright_instance.chromium.launch(**config)
                    break
                except Exception as e:
                    print(f"   Attempt {i+1} failed: {e}")
                    if i == len(launch_configs) - 1:
                        raise

            print("✅ Browser launched successfully")

            # Create context with robust settings
            context_config = {
                'viewport': {'width': 1920, 'height': 1080},
                'user_agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'ignore_https_errors': True,
                'java_script_enabled': True
            }

            self.context = await self.browser.new_context(**context_config)
            self.page = await self.context.new_page()

            # Set default timeouts
            self.page.set_default_timeout(30000)
            self.page.set_default_navigation_timeout(30000)

            print("✅ Playwright context and page created")
            return True

        except Exception as e:
            print(f"❌ Playwright setup failed: {e}")
            return False

    async def setup_cdp(self) -> bool:
        """Setup Chrome DevTools Protocol automation"""
        try:
            if not (websockets_available and aiohttp_available):
                print("❌ CDP modules not available")
                return False

            print("🔧 Starting CDP browser...")

            # Try different Chrome launch configurations
            chrome_configs = [
                {
                    'args': ['--remote-debugging-port=9223', '--no-sandbox', '--disable-setuid-sandbox'],
                    'port': 9223
                },
                {
                    'args': ['--remote-debugging-port=9224', '--no-sandbox', '--disable-setuid-sandbox'],
                    'port': 9224
                }
            ]

            import subprocess

            for i, config in enumerate(chrome_configs):
                try:
                    print(f"   Attempt {i+1}/2: Chrome with port {config['port']}")

                    args = ['/usr/bin/google-chrome'] + config['args']
                    if self.headless:
                        args.append('--headless')

                    args = [arg for arg in args if arg]  # Remove empty args

                    self.chrome_process = subprocess.Popen(
                        args,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )

                    # Wait for Chrome to start
                    await asyncio.sleep(4)

                    # Test connection
                    async with aiohttp.ClientSession() as session:
                        try:
                            async with session.get(f'http://localhost:{config["port"]}/json/version', timeout=5) as response:
                                if response.status == 200:
                                    version_info = await response.json()
                                    print(f"✅ Chrome CDP ready: {version_info.get('Browser', 'Unknown')}")
                                    break
                        except:
                            print(f"   Attempt {i+1}: Could not connect to Chrome CDP")
                            if i == len(chrome_configs) - 1:
                                raise

                except Exception as e:
                    print(f"   Attempt {i+1} failed: {e}")
                    if self.chrome_process:
                        self.chrome_process.terminate()
                        try:
                            self.chrome_process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            self.chrome_process.kill()
                        self.chrome_process = None

            # Connect to CDP
            if not self.chrome_process:
                raise Exception("Chrome process failed to start")

            # Get targets and find a page
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:9223/json') as response:
                    targets = await response.json()

            page_target = None
            for target in targets:
                if target.get('type') == 'page':
                    page_target = target
                    break

            if not page_target:
                # Create a new page
                async with aiohttp.ClientSession() as session:
                    async with session.put('http://localhost:9223/json/new') as response:
                        new_page = await response.json()
                        page_target = new_page

            if page_target:
                ws_url = page_target['webSocketDebuggerUrl']
                self.websocket = await websockets.connect(ws_url)
                print(f"✅ Connected to CDP: {page_target['title']}")
                return True

        except Exception as e:
            print(f"❌ CDP setup failed: {e}")
            return False

    def setup_selenium(self) -> bool:
        """Setup Selenium browser automation"""
        try:
            if not selenium_available:
                print("❌ Selenium modules not available")
                return False

            print("🌐 Setting up Selenium...")
            chrome_options = selenium_modules["Options"]()

            # Add arguments for better performance
            selenium_args = [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--window-size=1920,1080',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images'
            ]

            if self.headless:
                chrome_options.add_argument('--headless')

            for arg in selenium_args:
                chrome_options.add_argument(arg)

            # Disable logging for cleaner output
            chrome_options.add_argument('--log-level=3')
            chrome_options.add_argument('--silent')

            try:
                self.driver = selenium_modules["webdriver"].Chrome(options=chrome_options)
                self.driver.set_page_load_timeout(30)
                print("✅ Selenium Chrome driver created")
                return True
            except Exception as e:
                print(f"❌ Selenium Chrome driver failed: {e}")
                return False

        except Exception as e:
            print(f"❌ Selenium setup failed: {e}")
            return False

    async def navigate_to_comfyui(self, timeout: int = 30) -> bool:
        """Navigate to ComfyUI with enhanced error handling"""
        try:
            print(f"🌐 Navigating to {self.comfyui_url}")

            if self.automation_method == "playwright":
                await self.page.goto(self.comfyui_url, wait_until='networkidle', timeout=timeout*1000)
                # Wait for page to be interactive
                await self.page.wait_for_load_state('domcontentloaded', timeout=timeout*1000)
                print("✅ Playwright navigation successful")

            elif self.automation_method == "selenium":
                self.driver.get(self.comfyui_url)
                # Wait for page to load
                WebDriverWait(self.driver, timeout).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                print("✅ Selenium navigation successful")

            elif self.automation_method == "cdp":
                await self.send_cdp_command('Page.navigate', {'url': self.comfyui_url})
                await asyncio.sleep(3)  # Wait for navigation
                print("✅ CDP navigation successful")

            return True

        except Exception as e:
            print(f"❌ Navigation failed: {e}")
            return False

    async def send_cdp_command(self, method: str, params: Optional[Dict] = None) -> Dict:
        """Send CDP command (only for CDP method)"""
        if self.automation_method != "cdp" or not self.websocket:
            raise Exception("CDP not available")

        import json
        try:
            message = {
                "id": int(time.time() * 1000),
                "method": method,
                "params": params or {}
            }

            await self.websocket.send(json.dumps(message))
            response_str = await self.websocket.recv()
            response = json.loads(response_str)

            if 'error' in response:
                raise Exception(f"CDP Error: {response['error']}")

            return response.get('result', {})

        except Exception as e:
            print(f"❌ CDP command failed: {e}")
            return {}

    async def take_screenshot(self, filename: Optional[str] = None) -> str:
        """Take screenshot with fallback handling"""
        if filename is None:
            filename = f"comfyui_screenshot_{int(time.time())}.png"

        try:
            if self.automation_method == "playwright":
                await self.page.screenshot(path=filename)
            elif self.automation_method == "selenium":
                self.driver.save_screenshot(filename)
            elif self.automation_method == "cdp":
                result = await self.send_cdp_command('Page.captureScreenshot', {'format': 'png'})
                if result.get('data'):
                    import base64
                    with open(filename, 'wb') as f:
                        f.write(base64.b64decode(result['data']))
                else:
                    raise Exception("No screenshot data returned")

            print(f"📸 Screenshot saved: {filename}")
            return filename

        except Exception as e:
            print(f"❌ Screenshot failed: {e}")
            return ""

    async def check_comfyui_status(self) -> Dict[str, Any]:
        """Check ComfyUI status across different methods"""
        status = {
            "automation_method": self.automation_method,
            "url": self.comfyui_url,
            "title": "",
            "comfyui_detected": False,
            "queue_button_found": False,
            "queue_status": "",
            "timestamp": datetime.now().isoformat()
        }

        try:
            if self.automation_method == "playwright":
                status["title"] = await self.page.title()

                # Check for ComfyUI elements
                try:
                    await self.page.wait_for_selector('.comfyui-body', timeout=5000)
                    status["comfyui_detected"] = True
                except:
                    pass

                try:
                    queue_button = await self.page.query_selector('#queue-button')
                    if queue_button:
                        status["queue_button_found"] = True
                        status["queue_status"] = await queue_button.inner_text()
                except:
                    pass

            elif self.automation_method == "selenium":
                status["title"] = self.driver.title

                try:
                    WebDriverWait(self.driver, 5).until(
                        lambda driver: driver.execute_script("return document.querySelector('.comfyui-body') !== null")
                    )
                    status["comfyui_detected"] = True
                except:
                    pass

                try:
                    queue_button = self.driver.find_element(selenium_modules["By"].ID, 'queue-button')
                    status["queue_button_found"] = True
                    status["queue_status"] = queue_button.text
                except:
                    pass

        except Exception as e:
            print(f"⚠️  Status check warning: {e}")

        return status

    async def cleanup(self):
        """Comprehensive cleanup of all resources"""
        print("🧹 Cleaning up browser automation resources...")

        try:
            # Cleanup Playwright
            if self.context:
                await self.context.close()
                self.context = None

            if self.browser:
                await self.browser.close()
                self.browser = None

            if self.playwright_instance:
                await self.playwright_instance.stop()
                self.playwright_instance = None

        except Exception as e:
            print(f"⚠️  Playwright cleanup warning: {e}")

        try:
            # Cleanup CDP
            if self.websocket:
                await self.websocket.close()
                self.websocket = None

            if self.chrome_process:
                self.chrome_process.terminate()
                try:
                    self.chrome_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.chrome_process.kill()
                self.chrome_process = None

        except Exception as e:
            print(f"⚠️  CDP cleanup warning: {e}")

        try:
            # Cleanup Selenium
            if self.driver:
                self.driver.quit()
                self.driver = None

        except Exception as e:
            print(f"⚠️  Selenium cleanup warning: {e}")

        print("✅ Cleanup complete")

async def test_robust_automation():
    """Test the robust browser automation implementation"""
    print("🧪 Testing Robust Browser Automation")
    print("=" * 50)

    try:
        automation = RobustComfyUIAutomation(headless=True)

        # Test method detection and setup
        method = await automation.detect_and_setup_best_method()
        print(f"✅ Automation method: {method}")

        # Test navigation
        nav_success = await automation.navigate_to_comfyui()
        if not nav_success:
            print("⚠️  Navigation failed, but this might be expected if ComfyUI isn't running")

        # Get status
        status = await automation.check_comfyui_status()
        print(f"📊 Status: {json.dumps(status, indent=2)}")

        # Take screenshot
        screenshot = await automation.take_screenshot("robust_test_screenshot.png")

        print("✅ Robust automation test completed!")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        traceback.print_exc()
        return False

    finally:
        await automation.cleanup()

if __name__ == "__main__":
    success = asyncio.run(test_robust_automation())
    sys.exit(0 if success else 1)