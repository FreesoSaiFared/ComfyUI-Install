#!/usr/bin/env python3
"""
Minimal Browser Automation Test
Tests only the core functionality without browser launch
"""

import asyncio
import sys
import time
from datetime import datetime

def test_imports():
    """Test all required imports"""
    print("🧪 Testing imports...")

    try:
        import playwright
        from playwright.async_api import async_playwright
        print("✅ Playwright imports successful")

        # Test CDP imports
        try:
            import websockets
            import aiohttp
            print("✅ CDP dependencies available")
        except ImportError as e:
            print(f"⚠️  CDP dependencies missing: {e}")

        # Test Selenium imports
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            print("✅ Selenium imports available")
        except ImportError as e:
            print(f"⚠️  Selenium dependencies missing: {e}")

        return True
    except ImportError as e:
        print(f"❌ Playwright import failed: {e}")
        return False

async def test_playwright_methods():
    """Test Playwright method detection"""
    print("🧪 Testing Playwright method availability...")

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            # Test browser type availability
            methods = []

            if hasattr(p, 'chromium'):
                methods.append('chromium')
                print("✅ Chromium browser available")

            if hasattr(p, 'firefox'):
                methods.append('firefox')
                print("✅ Firefox browser available")

            if hasattr(p, 'webkit'):
                methods.append('webkit')
                print("✅ WebKit browser available")

            print(f"✅ Available browser engines: {', '.join(methods)}")

            # Test launch parameters (without actually launching)
            try:
                # Test that we can access launch method
                chromium_launch = p.chromium.launch
                print("✅ Chromium launch method accessible")

                # Test browser context creation method
                new_context_method = p.chromium.new_context
                print("✅ Browser context method accessible")

                return True

            except Exception as e:
                print(f"❌ Browser method access failed: {e}")
                return False

    except Exception as e:
        print(f"❌ Playwright methods test failed: {e}")
        return False

async def test_automation_setup_class():
    """Test the automation setup class instantiation"""
    print("🧪 Testing automation setup class...")

    try:
        # Import the setup class
        import sys
        import os
        sys.path.insert(0, '.')

        # Try to import the main automation module
        try:
            from browser_automation_setup import ComfyUIBrowserAutomation
            print("✅ ComfyUIBrowserAutomation class imported")

            # Test instantiation (no setup call)
            automation = ComfyUIBrowserAutomation("http://localhost:8188")
            print(f"✅ Automation instance created: {automation.comfyui_url}")

            # Test method availability
            methods = ['setup', 'navigate_to_comfyui', 'take_screenshot', 'cleanup']
            for method in methods:
                if hasattr(automation, method):
                    print(f"✅ Method available: {method}")
                else:
                    print(f"❌ Method missing: {method}")

            return True

        except ImportError as e:
            print(f"⚠️  Could not import ComfyUIBrowserAutomation: {e}")
            return False

    except Exception as e:
        print(f"❌ Automation setup class test failed: {e}")
        return False

def test_comfyui_connection():
    """Test if ComfyUI is running without browser automation"""
    print("🧪 Testing ComfyUI connection...")

    try:
        import aiohttp
        import asyncio

        async def check_comfyui():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get('http://localhost:8188', timeout=5) as response:
                        if response.status == 200:
                            print("✅ ComfyUI is running on port 8188")
                            return True
                        else:
                            print(f"⚠️  ComfyUI returned status: {response.status}")
                            return False
            except Exception as e:
                print(f"⚠️  ComfyUI connection failed: {e}")
                return False

        return asyncio.run(check_comfyui())

    except ImportError:
        # Fallback to requests if aiohttp not available
        try:
            import requests
            response = requests.get('http://localhost:8188', timeout=5)
            if response.status_code == 200:
                print("✅ ComfyUI is running on port 8188")
                return True
            else:
                print(f"⚠️  ComfyUI returned status: {response.status_code}")
                return False
        except Exception as e:
            print(f"⚠️  ComfyUI connection failed: {e}")
            return False

def main():
    """Main test function"""
    print("🤖 Minimal Browser Automation Test")
    print("=" * 50)
    print(f"🕒 Test started: {datetime.now().isoformat()}")

    # Test imports
    import_success = test_imports()
    if not import_success:
        print("❌ Cannot proceed without proper imports")
        return 1

    # Test Playwright methods
    playwright_success = asyncio.run(test_playwright_methods())

    # Test automation setup class
    setup_success = asyncio.run(test_automation_setup_class())

    # Test ComfyUI connection
    comfyui_success = test_comfyui_connection()

    # Summary
    print(f"\n📊 Test Summary:")
    print(f"   Import test: {'✅ PASS' if import_success else '❌ FAIL'}")
    print(f"   Playwright methods: {'✅ PASS' if playwright_success else '❌ FAIL'}")
    print(f"   Setup class: {'✅ PASS' if setup_success else '❌ FAIL'}")
    print(f"   ComfyUI connection: {'✅ PASS' if comfyui_success else '⚠️  FAIL'}")

    overall_success = import_success and playwright_success and setup_success
    print(f"\n🎯 Overall result: {'✅ SUCCESS' if overall_success else '❌ FAILURE'}")

    if overall_success:
        print("\n✅ Browser automation framework is ready!")
        print("🚀 You can now use it for ComfyUI automation tasks")
        if comfyui_success:
            print("🌐 ComfyUI is running and accessible")
        else:
            print("⚠️  Start ComfyUI before using browser automation")
    else:
        print("\n❌ Browser automation setup incomplete")
        print("🔧 Check the error messages above for troubleshooting")

    return 0 if overall_success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)