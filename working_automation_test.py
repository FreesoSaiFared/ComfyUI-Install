#!/usr/bin/env python3
"""
Working Browser Automation Test
Fixed version that properly handles Playwright methods
"""

import asyncio
import sys
import time
from datetime import datetime

async def test_browser_launch():
    """Test actual browser launch with various configurations"""
    print("🧪 Testing browser launch configurations...")

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            # Test different launch configurations
            configs = [
                {
                    "name": "Headless Chromium",
                    "args": {
                        "headless": True,
                        "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
                    }
                },
                {
                    "name": "Headless with minimal args",
                    "args": {
                        "headless": True
                    }
                }
            ]

            for config in configs:
                try:
                    print(f"\n🚀 Testing: {config['name']}")

                    browser = await p.chromium.launch(**config['args'])
                    print(f"✅ Browser launched successfully: {config['name']}")

                    # Test context creation
                    context = await browser.new_context()
                    print("✅ Context created successfully")

                    # Test page creation
                    page = await context.new_page()
                    print("✅ Page created successfully")

                    # Test basic navigation to a blank page
                    await page.goto("about:blank")
                    print("✅ Navigation to about:blank successful")

                    # Get page title
                    title = await page.title()
                    print(f"✅ Page title: '{title}'")

                    # Test JavaScript evaluation
                    result = await page.evaluate("navigator.userAgent")
                    print(f"✅ User agent: {result[:50]}...")

                    # Clean up
                    await page.close()
                    await context.close()
                    await browser.close()
                    print(f"✅ {config['name']} - Clean shutdown successful")

                    return True

                except Exception as e:
                    print(f"❌ {config['name']} failed: {e}")
                    try:
                        if 'browser' in locals():
                            await browser.close()
                    except:
                        pass
                    continue

            return False

    except Exception as e:
        print(f"❌ Browser launch test failed: {e}")
        return False

async def test_comfyui_navigation():
    """Test navigation to ComfyUI"""
    print("\n🧪 Testing ComfyUI navigation...")

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            # Launch with basic configuration
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # Navigate to ComfyUI
            comfyui_url = "http://localhost:8188"
            print(f"🌐 Navigating to: {comfyui_url}")

            try:
                response = await page.goto(comfyui_url, wait_until='domcontentloaded', timeout=15000)
                print(f"✅ Navigation successful, response: {response}")

                # Wait for page to load
                await page.wait_for_load_state('networkidle', timeout=10000)
                print("✅ Page fully loaded")

                # Get page title
                title = await page.title()
                print(f"✅ Page title: '{title}'")

                # Test for ComfyUI elements
                try:
                    # Wait for any of these elements
                    comfyui_selectors = [
                        '.comfyui-body',
                        '#queue-button',
                        '[data-testid="queue-button"]',
                        'body'  # Fallback
                    ]

                    element_found = False
                    for selector in comfyui_selectors:
                        try:
                            await page.wait_for_selector(selector, timeout=3000)
                            element_text = await page.inner_text(selector)
                            print(f"✅ Element found: {selector} - '{element_text[:50]}...'")
                            element_found = True
                            break
                        except:
                            continue

                    if not element_found:
                        print("⚠️  No ComfyUI-specific elements found, but page loaded")

                except Exception as element_error:
                    print(f"⚠️  Element detection error: {element_error}")

                # Take screenshot
                screenshot_name = f"comfyui_navigation_{int(time.time())}.png"
                await page.screenshot(path=screenshot_name)
                print(f"✅ Screenshot saved: {screenshot_name}")

                # Test basic interaction - try to find queue button or similar
                try:
                    buttons = await page.query_selector_all('button')
                    print(f"✅ Found {len(buttons)} buttons on page")

                    for i, button in enumerate(buttons[:5]):  # Check first 5 buttons
                        button_text = await button.inner_text()
                        print(f"   Button {i+1}: '{button_text}'")

                        if 'queue' in button_text.lower():
                            print(f"   🎯 Found queue button: {button_text}")

                except Exception as button_error:
                    print(f"⚠️  Button detection error: {button_error}")

                return True

            except Exception as nav_error:
                print(f"❌ Navigation failed: {nav_error}")
                return False

            finally:
                # Clean up
                await page.close()
                await context.close()
                await browser.close()

    except Exception as e:
        print(f"❌ ComfyUI navigation test failed: {e}")
        return False

async def test_automation_methods():
    """Test different automation methods"""
    print("\n🧪 Testing automation methods availability...")

    methods_available = []

    # Test Playwright
    try:
        import playwright
        from playwright.async_api import async_playwright
        methods_available.append("Playwright")
        print("✅ Playwright method available")
    except ImportError:
        print("❌ Playwright not available")

    # Test CDP dependencies
    try:
        import websockets
        import aiohttp
        methods_available.append("CDP")
        print("✅ CDP method available")
    except ImportError:
        print("❌ CDP dependencies missing")

    # Test Selenium
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        methods_available.append("Selenium")
        print("✅ Selenium method available")
    except ImportError:
        print("❌ Selenium not available")

    print(f"✅ Available methods: {', '.join(methods_available)}")
    return len(methods_available) > 0

async def main():
    """Main test function"""
    print("🤖 Working Browser Automation Test")
    print("=" * 50)
    print(f"🕒 Test started: {datetime.now().isoformat()}")

    # Test automation methods
    methods_success = await test_automation_methods()
    if not methods_success:
        print("❌ No automation methods available")
        return 1

    # Test browser launch
    browser_success = await test_browser_launch()

    # Test ComfyUI navigation
    comfyui_success = await test_comfyui_navigation()

    # Summary
    print(f"\n📊 Test Summary:")
    print(f"   Automation methods: {'✅ PASS' if methods_success else '❌ FAIL'}")
    print(f"   Browser launch: {'✅ PASS' if browser_success else '❌ FAIL'}")
    print(f"   ComfyUI navigation: {'✅ PASS' if comfyui_success else '❌ FAIL'}")

    overall_success = methods_success and browser_success and comfyui_success
    print(f"\n🎯 Overall result: {'✅ SUCCESS' if overall_success else '❌ FAILURE'}")

    if overall_success:
        print("\n✅ Browser automation is fully working!")
        print("🚀 Ready for ComfyUI automation tasks")
        print("📸 Screenshots saved for verification")
    else:
        print("\n❌ Browser automation has issues")
        print("🔧 Check the error messages above")

    return 0 if overall_success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)