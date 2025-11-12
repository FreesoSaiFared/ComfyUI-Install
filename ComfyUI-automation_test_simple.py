#!/usr/bin/env python3
"""
Simple Browser Automation Test
Quick test to verify basic functionality
"""

import asyncio
import sys
import time
import json
from datetime import datetime

def test_imports():
    """Test all required imports"""
    print("🧪 Testing imports...")

    try:
        import playwright
        from playwright.async_api import async_playwright
        print("✅ Playwright imports successful")
        return True
    except ImportError as e:
        print(f"❌ Playwright import failed: {e}")
        return False

async def test_basic_functionality():
    """Test basic functionality without full browser launch"""
    print("🧪 Testing basic functionality...")

    if not test_imports():
        return False

    # Import here to ensure scope
    from playwright.async_api import async_playwright

    try:
        print("🎭 Creating Playwright instance...")
        async with async_playwright() as p:
            print("✅ Playwright instance created")

            # Test browser info
            browsers = await p.chromium.launch(executable_path=None)
            browser_info = browsers.browser_type
            print(f"✅ Browser info: {browser_info}")

            # Test context creation
            context = await browsers.new_context()
            print("✅ Context created")

            # Test page creation
            page = await context.new_page()
            print("✅ Page created")

            # Test basic page operations
            title = await page.title()
            print(f"✅ Page title: '{title}'")

            # Test JavaScript evaluation
            result = await page.evaluate("navigator.userAgent")
            print(f"✅ User agent: {result[:50]}...")

            # Clean up
            await page.close()
            await context.close()
            await browsers.close()
            print("✅ Clean up successful")

        print("✅ All basic functionality tests passed")
        return True

    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

async def test_comfyui_connection():
    """Test connection to ComfyUI (if running)"""
    print("🧪 Testing ComfyUI connection...")

    if not test_imports():
        return False

    # Import here to ensure scope
    from playwright.async_api import async_playwright

    try:
        async with async_playwright() as p:
            print("🌐 Launching browser for ComfyUI test...")
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            comfyui_url = "http://localhost:8188"
            print(f"🔗 Attempting connection to: {comfyui_url}")

            try:
                # Try to navigate with a short timeout
                response = await page.goto(comfyui_url, wait_until='domcontentloaded', timeout=10000)
                print("✅ Connected to ComfyUI!")

                title = await page.title()
                print(f"✅ Page title: '{title}'")

                # Try to find ComfyUI elements
                try:
                    await page.wait_for_selector('.comfyui-body', timeout=5000)
                    print("✅ ComfyUI interface detected!")
                except:
                    print("⚠️  ComfyUI interface not found within timeout")

                # Try queue button
                try:
                    await page.wait_for_selector('#queue-button', timeout=3000)
                    queue_text = await page.inner_text('#queue-button')
                    print(f"✅ Queue button found: '{queue_text}'")
                except:
                    print("⚠️  Queue button not found")

            except Exception as nav_error:
                print(f"⚠️  Navigation failed (ComfyUI might not be running): {nav_error}")

            # Take screenshot regardless of navigation success
            screenshot_name = f"comfyui_test_{int(time.time())}.png"
            try:
                await page.screenshot(path=screenshot_name)
                print(f"✅ Screenshot saved: {screenshot_name}")
            except Exception as screenshot_error:
                print(f"⚠️  Screenshot failed: {screenshot_error}")

            # Clean up
            await page.close()
            await context.close()
            await browser.close()

        return True

    except Exception as e:
        print(f"❌ ComfyUI connection test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🤖 Simple Browser Automation Test")
    print("=" * 50)
    print(f"🕒 Test started: {datetime.now().isoformat()}")

    # Test imports first
    import_success = test_imports()
    if not import_success:
        print("❌ Cannot proceed without proper imports")
        return 1

    # Test basic functionality
    basic_success = asyncio.run(test_basic_functionality())

    # Test ComfyUI connection
    comfyui_success = asyncio.run(test_comfyui_connection())

    # Summary
    print(f"\n📊 Test Summary:")
    print(f"   Import test: {'✅ PASS' if import_success else '❌ FAIL'}")
    print(f"   Basic functionality: {'✅ PASS' if basic_success else '❌ FAIL'}")
    print(f"   ComfyUI connection: {'✅ PASS' if comfyui_success else '⚠️  SKIPPED/FAIL'}")

    overall_success = import_success and basic_success
    print(f"\n🎯 Overall result: {'✅ SUCCESS' if overall_success else '❌ FAILURE'}")

    if overall_success:
        print("\n✅ Browser automation is working!")
        print("🚀 You can now use it for ComfyUI automation tasks")
    else:
        print("\n❌ Browser automation setup incomplete")
        print("🔧 Check the error messages above for troubleshooting")

    return 0 if overall_success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)