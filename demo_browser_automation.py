#!/usr/bin/env python3
"""
Working Browser Automation Demo
Demonstrates both headless and non-headless browser automation with ComfyUI
"""

import asyncio
import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.insert(0, '.')

from browser_automation_setup import ComfyUIBrowserAutomation

async def demo_comfyui_automation():
    """Demonstrate ComfyUI browser automation"""
    print("🤖 ComfyUI Browser Automation Demo")
    print("=" * 50)
    print(f"🕒 Demo started: {datetime.now().isoformat()}")

    # Create automation instance
    automation = ComfyUIBrowserAutomation(
        comfyui_url="http://localhost:8188",
        headless=True,  # Use headless for reliable operation
        debug_port=9227  # Debug port for non-headless fallback
    )

    try:
        # Setup browser automation
        print("\n🔧 Setting up browser automation...")
        success = await automation.setup()

        if not success:
            print("❌ Failed to setup browser automation")
            return False

        print("✅ Browser automation setup successful")

        # Navigate to ComfyUI
        print("\n🌐 Navigating to ComfyUI...")
        success = await automation.navigate_to_comfyui()

        if not success:
            print("❌ Failed to navigate to ComfyUI")
            return False

        print("✅ Successfully navigated to ComfyUI")

        # Get page information
        title = await automation.get_page_title()
        print(f"📄 Page title: {title}")

        # Check for ComfyUI elements
        queue_status = await automation.check_queue_status()
        print(f"📊 Queue status: {queue_status}")

        # Take screenshot
        screenshot_name = f"comfyui_demo_{int(datetime.now().timestamp())}.png"
        screenshot_success = await automation.take_screenshot(screenshot_name)

        if screenshot_success:
            print(f"📸 Screenshot saved: {screenshot_name}")
        else:
            print("⚠️  Screenshot failed")

        # Test some JavaScript execution
        try:
            page_info = await automation.page.evaluate("""
                ({
                    url: window.location.href,
                    title: document.title,
                    readyState: document.readyState,
                    timestamp: new Date().toISOString()
                })
            """)
            print("📊 Page information:")
            for key, value in page_info.items():
                print(f"   {key}: {value}")
        except Exception as js_error:
            print(f"⚠️  JavaScript execution error: {js_error}")

        print("\n✅ ComfyUI automation demo completed successfully!")
        return True

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Clean up
        print("\n🧹 Cleaning up...")
        await automation.cleanup()
        print("✅ Cleanup completed")

async def demo_non_headless_setup():
    """Demonstrate non-headless Chrome setup (if display available)"""
    print("\n🖥️  Non-Headless Chrome Setup Demo")
    print("-" * 40)

    # Check display availability
    display = os.environ.get('DISPLAY')
    if not display:
        print("⚠️  No DISPLAY environment variable found")
        print("   Non-headless mode requires graphical display")
        return False

    print(f"✅ Display available: {display}")

    # Create automation instance for non-headless mode
    automation = ComfyUIBrowserAutomation(
        headless=False,
        debug_port=9228
    )

    try:
        print("🚀 Attempting to start Chrome with debugging...")
        success = await automation.start_chrome_with_debug()

        if success:
            print("✅ Chrome started successfully!")
            print(f"🔗 Debug port: {automation.debug_port}")
            print(f"📁 Profile: {automation.profile_dir}")
            print("💡 Connect Chrome DevTools to: http://localhost:9222")

            # Wait a moment to show Chrome is running
            await asyncio.sleep(2)

            # Test connection to debug port
            port_check = await automation.check_chrome_debug_port()
            print(f"🔗 Debug port check: {port_check}")

            await asyncio.sleep(3)  # Give user time to see Chrome

            await automation.cleanup()
            print("✅ Non-headless demo completed")
            return True
        else:
            print("❌ Failed to start Chrome")
            return False

    except Exception as e:
        print(f"❌ Non-headless demo error: {e}")
        return False

def print_usage_instructions():
    """Print usage instructions for the browser automation framework"""
    print("\n📋 Browser Automation Usage Instructions")
    print("=" * 50)

    print("\n1️⃣  Basic Headless Automation:")
    print("   ```python")
    print("   from browser_automation_setup import ComfyUIBrowserAutomation")
    print("   ")
    print("   automation = ComfyUIBrowserAutomation(headless=True)")
    print("   await automation.setup()")
    print("   await automation.navigate_to_comfyui()")
    print("   screenshot = await automation.take_screenshot('output.png')")
    print("   await automation.cleanup()")
    print("   ```")

    print("\n2️⃣  Non-Headless GUI Automation:")
    print("   ```python")
    print("   automation = ComfyUIBrowserAutomation(")
    print("       headless=False,")
    print("       debug_port=9222")
    print("   )")
    print("   await automation.setup()  # Starts Chrome with fresh profile")
    print("   # Chrome window opens with no confirmations")
    print("   await automation.cleanup()")
    print("   ```")

    print("\n3️⃣  Chrome Configuration Features:")
    print("   ✅ Fresh profile (no confirmations or onboarding)")
    print("   ✅ Debugging port enabled for DevTools access")
    print("   ✅ Auto-starts Chrome if not running")
    print("   ✅ Comprehensive error handling")
    print("   ✅ Automatic resource cleanup")

    print("\n4️⃣  Available Automation Methods:")
    print("   🎭 Playwright (primary) - Most reliable and feature-rich")
    print("   🔗 Chrome DevTools Protocol (CDP) - Low-level control")
    print("   🌐 Selenium (fallback) - Traditional web automation")

    print("\n5️⃣  Chrome Arguments Applied:")
    print("   --no-first-run (skip first-run setup)")
    print("   --no-default-browser-check (skip default browser prompt)")
    print("   --disable-sync (disable Google sync)")
    print("   --disable-extensions (disable all extensions)")
    print("   --user-data-dir=/tmp/profile_* (fresh profile)")
    print("   --remote-debugging-port=9222 (debugging enabled)")

async def main():
    """Main demo function"""
    print("🎬 Browser Automation Framework Demo")
    print("=" * 60)

    # Run ComfyUI automation demo
    comfyui_success = await demo_comfyui_automation()

    # Run non-headless setup demo (optional)
    non_headless_success = await demo_non_headless_setup()

    # Print usage instructions
    print_usage_instructions()

    # Summary
    print(f"\n📊 Demo Results:")
    print(f"   ComfyUI Headless Automation: {'✅ SUCCESS' if comfyui_success else '❌ FAILED'}")
    print(f"   Non-Headless Chrome Setup: {'✅ SUCCESS' if non_headless_success else '⚠️  SKIPPED/FAILED'}")

    if comfyui_success:
        print(f"\n🎉 Browser automation framework is ready to use!")
        print(f"   📖 Check the generated screenshots")
        print(f"   📋 See usage instructions above")
        print(f"   🔧 All Chrome profiles and processes are cleaned up automatically")
    else:
        print(f"\n⚠️  Some automation features may need attention")
        print(f"   🔧 Check the error messages above for troubleshooting")

    return 0 if comfyui_success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)