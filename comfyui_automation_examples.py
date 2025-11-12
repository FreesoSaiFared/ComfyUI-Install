#!/usr/bin/env python3
"""
ComfyUI Browser Automation Examples
Demonstrates various automation tasks for ComfyUI workflows
"""

import asyncio
import json
import time
from pathlib import Path
from browser_automation_setup import ComfyUIBrowserAutomation

class ComfyUIAutomationExamples:
    """Examples of ComfyUI automation tasks"""

    def __init__(self, comfyui_url: str = "http://localhost:8188"):
        self.comfyui_url = comfyui_url
        self.automation = ComfyUIBrowserAutomation(comfyui_url)

    async def example_basic_navigation(self):
        """Example: Basic navigation and status check"""
        print("🔍 Example: Basic Navigation")
        print("-" * 30)

        try:
            # Setup browser
            await self.automation.setup(headless=False)

            # Navigate to ComfyUI
            await self.automation.navigate_to_comfyui()

            # Get page info
            title = await self.automation.get_page_title()
            print(f"✅ Page loaded: {title}")

            # Check queue status
            queue_status = await self.automation.check_queue_status()
            print(f"📊 Queue status: {queue_status}")

            # Take screenshot
            screenshot = await self.automation.take_screenshot("basic_navigation.png")

            return True

        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    async def example_load_workflow(self, workflow_path: str):
        """Example: Load a workflow file into ComfyUI"""
        print(f"📂 Example: Loading Workflow - {workflow_path}")
        print("-" * 30)

        try:
            await self.automation.setup(headless=False)
            await self.automation.navigate_to_comfyui()

            if self.automation.automation_method == "playwright":
                # Find and click the load button
                load_button = await self.automation.page.wait_for_selector(
                    '[data-testid="load-button"]', timeout=10000
                )
                await load_button.click()

                # Wait for file input
                file_input = await self.automation.page.wait_for_selector(
                    'input[type="file"]', timeout=5000
                )

                # Upload workflow file
                workflow_file = Path(workflow_path)
                await file_input.set_input_files(str(workflow_file))

                print(f"✅ Workflow loaded: {workflow_path}")

                # Take screenshot after loading
                await self.automation.take_screenshot("workflow_loaded.png")

                return True

            else:
                print("⚠️  This example works best with Playwright")
                return False

        except Exception as e:
            print(f"❌ Error loading workflow: {e}")
            return False

    async def example_queue_monitoring(self, duration: int = 30):
        """Example: Monitor ComfyUI queue for activity"""
        print(f"⏱️  Example: Queue Monitoring ({duration}s)")
        print("-" * 30)

        try:
            await self.automation.setup(headless=True)
            await self.automation.navigate_to_comfyui()

            start_time = time.time()
            status_history = []

            while time.time() - start_time < duration:
                queue_status = await self.automation.check_queue_status()
                timestamp = datetime.now().strftime("%H:%M:%S")

                status_entry = {
                    "timestamp": timestamp,
                    "status": queue_status
                }
                status_history.append(status_entry)

                print(f"[{timestamp}] Queue: {queue_status.get('text', 'Unknown')}")

                await asyncio.sleep(2)

            print(f"✅ Monitoring complete. Collected {len(status_history)} status updates")

            # Save monitoring results
            with open("queue_monitoring.json", "w") as f:
                json.dump(status_history, f, indent=2)

            return True

        except Exception as e:
            print(f"❌ Error in queue monitoring: {e}")
            return False

    async def example_workflow_execution_test(self, workflow_path: str):
        """Example: Test workflow execution timing"""
        print(f"🚀 Example: Workflow Execution Test - {workflow_path}")
        print("-" * 30)

        try:
            await self.automation.setup(headless=False)
            await self.automation.navigate_to_comfyui()

            if self.automation.automation_method != "playwright":
                print("⚠️  This example requires Playwright")
                return False

            # Load workflow
            await self.example_load_workflow(workflow_path)

            # Find and click queue prompt button
            queue_button = await self.automation.page.wait_for_selector(
                '#queue-button', timeout=10000
            )

            # Record start time
            start_time = time.time()
            print("⏱️  Starting workflow execution...")

            # Click to execute
            await queue_button.click()

            # Monitor execution
            execution_active = True
            execution_log = []

            while execution_active:
                queue_status = await self.automation.check_queue_status()
                current_time = time.time() - start_time

                log_entry = {
                    "elapsed_time": current_time,
                    "queue_status": queue_status,
                    "timestamp": datetime.now().isoformat()
                }
                execution_log.append(log_entry)

                print(f"[{current_time:.1f}s] {queue_status.get('text', 'Processing...')}")

                # Check if execution is complete (queue empty)
                if "Queue Prompt" in queue_status.get('text', ''):
                    execution_active = False

                await asyncio.sleep(1)

                # Timeout after 5 minutes
                if current_time > 300:
                    print("⚠️  Workflow execution timeout (5 minutes)")
                    break

            total_time = time.time() - start_time
            print(f"✅ Workflow completed in {total_time:.2f} seconds")

            # Take final screenshot
            await self.automation.take_screenshot("workflow_result.png")

            # Save execution log
            with open("workflow_execution_log.json", "w") as f:
                json.dump({
                    "workflow_path": workflow_path,
                    "total_time": total_time,
                    "execution_log": execution_log
                }, f, indent=2)

            return True

        except Exception as e:
            print(f"❌ Error in workflow execution test: {e}")
            return False

    async def example_performance_benchmark(self, workflow_paths: list):
        """Example: Performance benchmark multiple workflows"""
        print(f"🏁 Example: Performance Benchmark")
        print("-" * 30)

        results = []

        for workflow_path in workflow_paths:
            if not Path(workflow_path).exists():
                print(f"⚠️  Workflow not found: {workflow_path}")
                continue

            workflow_name = Path(workflow_path).name
            print(f"\n🧪 Testing: {workflow_name}")

            try:
                await self.automation.setup(headless=True)
                await self.automation.navigate_to_comfyui()

                start_time = time.time()

                # Load workflow (simplified version)
                if self.automation.automation_method == "playwright":
                    # Basic workflow load simulation
                    await self.automation.page.goto(f"file://{workflow_path}", wait_until='networkidle')

                load_time = time.time() - start_time

                result = {
                    "workflow_name": workflow_name,
                    "workflow_path": workflow_path,
                    "load_time": load_time,
                    "success": True,
                    "timestamp": datetime.now().isoformat()
                }

                results.append(result)
                print(f"✅ {workflow_name}: {load_time:.2f}s")

            except Exception as e:
                error_result = {
                    "workflow_name": workflow_name,
                    "workflow_path": workflow_path,
                    "load_time": 0,
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                results.append(error_result)
                print(f"❌ {workflow_name}: Failed - {e}")

            finally:
                await self.automation.cleanup()

        # Save benchmark results
        with open("performance_benchmark.json", "w") as f:
            json.dump({
                "test_date": datetime.now().isoformat(),
                "total_workflows": len(workflow_paths),
                "successful_tests": len([r for r in results if r['success']]),
                "results": results
            }, f, indent=2)

        print(f"\n📊 Benchmark Summary:")
        print(f"   Total workflows: {len(workflow_paths)}")
        print(f"   Successful: {len([r for r in results if r['success']])}")
        print(f"   Failed: {len([r for r in results if not r['success']])}")

        return results

    async def cleanup(self):
        """Clean up automation resources"""
        await self.automation.cleanup()

async def run_examples():
    """Run all automation examples"""
    print("🤖 ComfyUI Browser Automation Examples")
    print("=" * 50)

    examples = ComfyUIAutomationExamples()

    try:
        # Example 1: Basic navigation
        print("\n1️⃣ Running Basic Navigation Example...")
        await examples.example_basic_navigation()

        # Example 2: Queue monitoring
        print("\n2️⃣ Running Queue Monitoring Example...")
        await examples.example_queue_monitoring(10)  # Monitor for 10 seconds

        # Example 3: Load workflow (if available)
        workflow_path = "/home/ned/ComfyUI-Install/workflows/lightning_fast_video.json"
        if Path(workflow_path).exists():
            print("\n3️⃣ Running Workflow Load Example...")
            await examples.example_load_workflow(workflow_path)

        # Example 4: Performance benchmark
        print("\n4️⃣ Running Performance Benchmark...")
        workflows_to_test = [
            "/home/ned/ComfyUI-Install/workflows/lightning_fast_video.json",
            "/home/ned/ComfyUI-Install/workflows/ultra_fast_2step.json"
        ]
        await examples.example_performance_benchmark(workflows_to_test)

        print("\n✅ All examples completed successfully!")
        print("📁 Check generated files:")
        print("   - Screenshots: *.png")
        print("   - Queue monitoring: queue_monitoring.json")
        print("   - Performance data: performance_benchmark.json")

    except Exception as e:
        print(f"❌ Error running examples: {e}")

    finally:
        await examples.cleanup()

if __name__ == "__main__":
    asyncio.run(run_examples())