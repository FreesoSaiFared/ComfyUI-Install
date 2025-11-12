#!/usr/bin/env python3
"""
Direct Chrome DevTools Protocol (CDP) Automation
Low-level browser control using WebSocket connection
"""

import asyncio
import json
import websockets
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

class CDPAutomation:
    """Direct CDP automation for ComfyUI"""

    def __init__(self, comfyui_url: str = "http://localhost:8188"):
        self.comfyui_url = comfyui_url
        self.chrome_process = None
        self.websocket = None
        self.message_id = 0

    async def launch_chrome_debug(self, headless: bool = True) -> bool:
        """Launch Chrome with remote debugging enabled"""
        try:
            chrome_args = [
                '/usr/bin/google-chrome',
                '--remote-debugging-port=9222',
                '--remote-debugging-address=0.0.0.0',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=TranslateUI',
                '--enable-automation',
                f'--user-data-dir=/tmp/chrome_cdp_{int(time.time())}'
            ]

            if headless:
                chrome_args.append('--headless')

            # Remove any empty args
            chrome_args = [arg for arg in chrome_args if arg]

            print("🚀 Launching Chrome with CDP enabled...")
            self.chrome_process = subprocess.Popen(
                chrome_args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # Wait for Chrome to start
            await asyncio.sleep(3)

            # Test connection
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get('http://localhost:9222/json/version') as response:
                        if response.status == 200:
                            version_info = await response.json()
                            print(f"✅ Chrome CDP ready: {version_info.get('Browser', 'Unknown')}")
                            return True
            except Exception as e:
                print(f"❌ Failed to connect to Chrome CDP: {e}")
                return False

        except Exception as e:
            print(f"❌ Failed to launch Chrome: {e}")
            return False

    async def connect_to_cdp(self) -> bool:
        """Connect to Chrome DevTools Protocol"""
        try:
            # Get list of targets
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:9222/json') as response:
                    targets = await response.json()

            # Find a page target or create one
            page_target = None
            for target in targets:
                if target.get('type') == 'page':
                    page_target = target
                    break

            if not page_target:
                # Create a new page
                async with aiohttp.ClientSession() as session:
                    async with session.put('http://localhost:9222/json/new') as response:
                        new_page = await response.json()
                        page_target = new_page

            if page_target:
                ws_url = page_target['webSocketDebuggerUrl']
                self.websocket = await websockets.connect(ws_url)
                print(f"✅ Connected to CDP: {page_target['title']}")
                return True

        except Exception as e:
            print(f"❌ Failed to connect to CDP: {e}")
            return False

    async def send_cdp_command(self, method: str, params: Optional[Dict] = None) -> Dict:
        """Send a CDP command and return the response"""
        if not self.websocket:
            raise Exception("Not connected to CDP")

        message = {
            "id": self.message_id,
            "method": method,
            "params": params or {}
        }

        self.message_id += 1

        await self.websocket.send(json.dumps(message))
        response_str = await self.websocket.recv()
        response = json.loads(response_str)

        if 'error' in response:
            raise Exception(f"CDP Error: {response['error']}")

        return response.get('result', {})

    async def navigate_to_url(self, url: str) -> bool:
        """Navigate to a specific URL"""
        try:
            result = await self.send_cdp_command('Page.navigate', {'url': url})
            frame_id = result.get('frameId')

            # Wait for navigation to complete
            await asyncio.sleep(2)

            # Verify navigation succeeded
            result = await self.send_cdp_command('Runtime.evaluate', {
                'expression': 'window.location.href'
            })

            current_url = result.get('result', {}).get('value', '')
            if url in current_url:
                print(f"✅ Navigated to: {url}")
                return True
            else:
                print(f"⚠️  Navigation to {url} may not have completed")
                return False

        except Exception as e:
            print(f"❌ Navigation failed: {e}")
            return False

    async def take_screenshot(self, filename: str) -> bool:
        """Take a screenshot of the current page"""
        try:
            result = await self.send_cdp_command('Page.captureScreenshot', {
                'format': 'png'
            })

            screenshot_data = result.get('data', '')
            if screenshot_data:
                # Decode base64 and save
                import base64
                with open(filename, 'wb') as f:
                    f.write(base64.b64decode(screenshot_data))

                print(f"📸 Screenshot saved: {filename}")
                return True

        except Exception as e:
            print(f"❌ Screenshot failed: {e}")
            return False

    async def evaluate_javascript(self, expression: str) -> Any:
        """Evaluate JavaScript in the page context"""
        try:
            result = await self.send_cdp_command('Runtime.evaluate', {
                'expression': expression,
                'returnByValue': True
            })

            return result.get('result', {}).get('value')

        except Exception as e:
            print(f"❌ JavaScript evaluation failed: {e}")
            return None

    async def wait_for_element(self, selector: str, timeout: int = 10) -> bool:
        """Wait for an element to appear on the page"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            # Check if element exists
            result = await self.evaluate_javascript(
                f'document.querySelector("{selector}") !== null'
            )

            if result:
                print(f"✅ Element found: {selector}")
                return True

            await asyncio.sleep(0.5)

        print(f"⚠️  Element not found within timeout: {selector}")
        return False

    async def get_element_text(self, selector: str) -> str:
        """Get text content of an element"""
        try:
            text = await self.evaluate_javascript(
                f'document.querySelector("{selector}")?.textContent || ""'
            )
            return str(text) if text else ""
        except:
            return ""

    async def click_element(self, selector: str) -> bool:
        """Click an element on the page"""
        try:
            # Wait for element first
            if await self.wait_for_element(selector, 5):
                await self.evaluate_javascript(
                    f'document.querySelector("{selector}").click()'
                )
                await asyncio.sleep(0.5)  # Wait for click to process
                print(f"🖱️  Clicked: {selector}")
                return True
            return False
        except Exception as e:
            print(f"❌ Click failed: {e}")
            return False

    async def get_page_title(self) -> str:
        """Get the current page title"""
        try:
            title = await self.evaluate_javascript('document.title')
            return str(title) if title else ""
        except:
            return ""

    async def check_comfyui_status(self) -> Dict[str, Any]:
        """Check ComfyUI-specific status"""
        status = {
            "comfyui_loaded": False,
            "queue_button_found": False,
            "queue_text": "",
            "page_title": ""
        }

        try:
            # Get page title
            status["page_title"] = await self.get_page_title()

            # Check if ComfyUI is loaded
            comfyui_loaded = await self.evaluate_javascript(
                'document.querySelector(".comfyui-body") !== null'
            )
            status["comfyui_loaded"] = bool(comfyui_loaded)

            # Check queue button
            queue_button = await self.evaluate_javascript(
                'document.querySelector("#queue-button") !== null'
            )
            status["queue_button_found"] = bool(queue_button)

            if queue_button:
                status["queue_text"] = await self.get_element_text("#queue-button")

        except Exception as e:
            print(f"⚠️  Error checking ComfyUI status: {e}")

        return status

    async def monitor_comfyui_queue(self, duration: int = 30) -> List[Dict]:
        """Monitor ComfyUI queue activity"""
        print(f"📊 Monitoring ComfyUI queue for {duration} seconds...")
        monitoring_data = []

        start_time = time.time()
        while time.time() - start_time < duration:
            status = await self.check_comfyui_status()
            status["timestamp"] = datetime.now().isoformat()
            status["elapsed"] = time.time() - start_time

            monitoring_data.append(status)
            print(f"[{status['elapsed']:.1f}s] Queue: {status.get('queue_text', 'Unknown')}")

            await asyncio.sleep(2)

        return monitoring_data

    async def cleanup(self):
        """Clean up CDP resources"""
        try:
            if self.websocket:
                await self.websocket.close()

            if self.chrome_process:
                self.chrome_process.terminate()
                try:
                    self.chrome_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.chrome_process.kill()

            print("✅ CDP cleanup complete")

        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")

async def test_cdp_automation():
    """Test CDP automation with ComfyUI"""
    print("🔧 Testing Chrome DevTools Protocol (CDP) Automation")
    print("=" * 60)

    cdp = CDPAutomation()

    try:
        # Launch Chrome with CDP
        if not await cdp.launch_chrome_debug(headless=True):
            print("❌ Failed to launch Chrome")
            return False

        # Connect to CDP
        if not await cdp.connect_to_cdp():
            print("❌ Failed to connect to CDP")
            return False

        # Navigate to ComfyUI
        print(f"🌐 Navigating to ComfyUI: {cdp.comfyui_url}")
        if not await cdp.navigate_to_url(cdp.comfyui_url):
            print("❌ Failed to navigate to ComfyUI")
            return False

        # Wait for ComfyUI to load
        await asyncio.sleep(5)

        # Check ComfyUI status
        status = await cdp.check_comfyui_status()
        print(f"📊 ComfyUI Status:")
        print(f"   Page Title: {status['page_title']}")
        print(f"   ComfyUI Loaded: {status['comfyui_loaded']}")
        print(f"   Queue Button: {status['queue_button_found']}")
        print(f"   Queue Text: {status['queue_text']}")

        # Take screenshot
        await cdp.take_screenshot("cdp_comfyui_screenshot.png")

        # Monitor queue for 10 seconds
        monitoring_data = await cdp.monitor_comfyui_queue(10)

        # Save monitoring data
        import json
        from datetime import datetime

        with open("cdp_monitoring_data.json", "w") as f:
            json.dump({
                "test_date": datetime.now().isoformat(),
                "monitoring_duration": 10,
                "data_points": len(monitoring_data),
                "monitoring_data": monitoring_data
            }, f, indent=2)

        print("✅ CDP automation test completed successfully!")
        print(f"📁 Generated files:")
        print(f"   - cdp_comfyui_screenshot.png")
        print(f"   - cdp_monitoring_data.json")

        return True

    except Exception as e:
        print(f"❌ CDP test failed: {e}")
        return False

    finally:
        await cdp.cleanup()

if __name__ == "__main__":
    asyncio.run(test_cdp_automation())