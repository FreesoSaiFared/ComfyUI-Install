#!/usr/bin/env python3
"""
Non-Headless Browser Automation Test
Tests GUI browser automation with Chrome debugging port and fresh profile
"""

import asyncio
import sys
import os
import time
from datetime import datetime

# Add current directory to path
sys.path.insert(0, '.')

from browser_automation_setup import ComfyUIBrowserAutomation

async def test_headless_mode():
    """Test traditional headless browser automation"""
    print("🔧 Testing Headless Mode (Traditional)")
    print("-" * 40)

    try:
        # Create automation instance with headless=True
        automation = ComfyUIBrowserAutomation(headless=True)

        # Setup browser automation
        success = await automation.setup()
        if not success:
            print("❌ Failed to setup headless browser automation")
            return False

        print("✅ Headless browser setup successful")

        # Test basic navigation
        await automation.page.goto("about:blank")
        title = await automation.page.title()
        print(f"✅ Headless navigation test: '{title}'")

        # Clean up
        await automation.cleanup()
        print("✅ Headless mode test completed successfully")
        return True

    except Exception as e:
        print(f"❌ Headless mode test failed: {e}")
        return False

async def test_non_headless_mode():
    """Test GUI browser automation with Chrome debugging"""
    print("\n🖥️  Testing Non-Headless Mode (GUI)")
    print("-" * 40)

    try:
        # Create automation instance with headless=False
        automation = ComfyUIBrowserAutomation(headless=False, debug_port=9223)

        # Setup browser automation (this will start external Chrome)
        success = await automation.setup()
        if not success:
            print("❌ Failed to setup non-headless browser automation")
            return False

        print("✅ Non-headless browser setup successful")
        print(f"📁 Chrome profile: {automation.profile_dir}")
        print(f"🔗 Debug port: {automation.debug_port}")

        # Test basic navigation - user should see Chrome window open
        await automation.page.goto("about:blank")
        title = await automation.page.title()
        print(f"✅ GUI navigation test: '{title}'")

        # Test JavaScript execution
        result = await automation.page.evaluate("navigator.userAgent")
        print(f"✅ User agent: {result[:80]}...")

        # Test window manipulation (only works in GUI mode)
        await automation.page.evaluate("""
            window.moveTo(100, 100);
            window.resizeTo(800, 600);
            window.focus();
        """)
        print("✅ Window manipulation test successful")

        # Give user time to see the browser window
        print("\n⏳ Chrome browser window should be visible...")
        print("   - Profile: Fresh automation profile (no confirmations)")
        print("   - Debug port: Enabled for developer tools")
        print("   - Window: Should be positioned and sized")

        await asyncio.sleep(3)  # Show window for 3 seconds

        # Clean up
        await automation.cleanup()
        print("✅ Non-headless mode test completed successfully")
        return True

    except Exception as e:
        print(f"❌ Non-headless mode test failed: {e}")
        return False

async def test_comfyui_integration():
    """Test ComfyUI integration with both modes"""
    print("\n🌐 Testing ComfyUI Integration")
    print("-" * 40)

    # Test with headless first
    print("\n1️⃣ Testing ComfyUI in Headless Mode:")
    try:
        automation_headless = ComfyUIBrowserAutomation(headless=True)
        success = await automation_headless.setup()

        if success:
            # Navigate to ComfyUI
            await automation_headless.page.goto("http://localhost:8188", wait_until='domcontentloaded', timeout=10000)
            title = await automation_headless.page.title()
            print(f"   ✅ ComfyUI loaded (headless): '{title}'")

            # Take screenshot
            screenshot_name = f"comfyui_headless_{int(time.time())}.png"
            await automation_headless.page.screenshot(path=screenshot_name)
            print(f"   📸 Screenshot saved: {screenshot_name}")

            await automation_headless.cleanup()
        else:
            print("   ⚠️  Could not setup headless browser")
    except Exception as e:
        print(f"   ⚠️  Headless ComfyUI test: {e}")

    # Test with non-headless
    print("\n2️⃣ Testing ComfyUI in GUI Mode:")
    try:
        automation_gui = ComfyUIBrowserAutomation(headless=False, debug_port=9224)
        success = await automation_gui.setup()

        if success:
            # Navigate to ComfyUI
            await automation_gui.page.goto("http://localhost:8188", wait_until='domcontentloaded', timeout=10000)
            title = await automation_gui.page.title()
            print(f"   ✅ ComfyUI loaded (GUI): '{title}'")

            # Test window manipulation for better viewing
            await automation_gui.page.evaluate("""
                window.moveTo(50, 50);
                window.resizeTo(1200, 800);
                window.focus();
            """)

            # Take screenshot
            screenshot_name = f"comfyui_gui_{int(time.time())}.png"
            await automation_gui.page.screenshot(path=screenshot_name)
            print(f"   📸 Screenshot saved: {screenshot_name}")

            print("\n   🖥️  ComfyUI should be visible in Chrome window!")
            print("   ⏳ Displaying for 5 seconds...")

            await asyncio.sleep(5)  # Show ComfyUI for 5 seconds

            await automation_gui.cleanup()
        else:
            print("   ⚠️  Could not setup GUI browser")
    except Exception as e:
        print(f"   ⚠️  GUI ComfyUI test: {e}")

async def test_chrome_debug_features():
    """Test Chrome debugging and developer tools features"""
    print("\n🔍 Testing Chrome Debug Features")
    print("-" * 40)

    try:
        # Create automation with debugging enabled
        automation = ComfyUIBrowserAutomation(headless=False, debug_port=9225)

        success = await automation.setup()
        if not success:
            print("❌ Failed to setup debugging browser")
            return False

        print("✅ Chrome debugging setup successful")
        print(f"🔗 Debug port: {automation.debug_port}")
        print(f"💡 You can connect Chrome DevTools to: http://localhost:{automation.debug_port}")

        # Navigate to a test page
        await automation.page.goto("data:text/html,<html><body><h1>Chrome Debug Test</h1><p>Open Chrome DevTools to see this page</p></body></html>")

        # Execute some JavaScript that would be useful for debugging
        debug_info = await automation.page.evaluate("""
            ({
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                language: navigator.language,
                screenResolution: `${screen.width}x${screen.height}`,
                windowSize: `${window.innerWidth}x${window.innerHeight}`,
                timestamp: new Date().toISOString()
            })
        """)

        print("📊 Browser Debug Information:")
        for key, value in debug_info.items():
            print(f"   {key}: {value}")

        # Test console logging (visible in Chrome DevTools)
        await automation.page.evaluate("""
            console.log('🤖 Browser Automation Test Started');
            console.log('📊 Debug Info:', arguments[0]);
            console.log('🔧 Developer tools should be open automatically');
        """, debug_info)

        print("\n⏳ Chrome window open with DevTools for 5 seconds...")
        print("💡 Check the Chrome DevTools console for debug messages")

        await asyncio.sleep(5)

        await automation.cleanup()
        print("✅ Chrome debug features test completed")
        return True

    except Exception as e:
        print(f"❌ Chrome debug test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🤖 Non-Headless Browser Automation Test Suite")
    print("=" * 60)
    print(f"🕒 Test started: {datetime.now().isoformat()}")

    results = {}

    # Test 1: Headless mode
    results['headless'] = await test_headless_mode()

    # Test 2: Non-headless mode
    results['non_headless'] = await test_non_headless_mode()

    # Test 3: ComfyUI integration
    results['comfyui'] = await test_comfyui_integration()

    # Test 4: Chrome debugging features
    results['debugging'] = await test_chrome_debug_features()

    # Summary
    print(f"\n📊 Test Results Summary:")
    print("=" * 40)

    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        test_display = test_name.replace('_', ' ').title()
        print(f"   {test_display:<20} {status}")

    overall_success = all(results.values())
    print(f"\n🎯 Overall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")

    if overall_success:
        print("\n🚀 Browser automation is fully functional!")
        print("   ✅ Headless mode: Working")
        print("   ✅ Non-headless mode: Working")
        print("   ✅ Chrome debugging: Enabled")
        print("   ✅ Fresh profiles: Configured")
        print("   ✅ ComfyUI integration: Tested")

        print("\n📋 Usage Examples:")
        print("   # Headless mode")
        print("   automation = ComfyUIBrowserAutomation(headless=True)")
        print("   await automation.setup()")
        print()
        print("   # GUI mode with debugging")
        print("   automation = ComfyUIBrowserAutomation(headless=False, debug_port=9222)")
        print("   await automation.setup()")
        print("   # Chrome window opens with fresh profile and DevTools")
    else:
        print("\n⚠️  Some browser automation features need attention")
        print("🔧 Check the error messages above for troubleshooting")

    return 0 if overall_success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)