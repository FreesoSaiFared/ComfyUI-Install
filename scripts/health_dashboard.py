#!/usr/bin/env python3
"""
ComfyUI Health Dashboard

Interactive dashboard for monitoring ComfyUI health status,
custom nodes, system resources, and alerts. Provides real-time
visualization and management interface.
"""

import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import sys

# Try to import optional dependencies
try:
    import yaml
except ImportError:
    yaml = None

from health_monitor import ComfyUIHealthMonitor, HealthStatus, SystemMetrics

class HealthDashboard:
    """Interactive health monitoring dashboard"""

    def __init__(self):
        self.monitor = ComfyUIHealthMonitor()
        self.running = False
        self.refresh_interval = 5  # seconds
        self.show_details = False

    def clear_screen(self):
        """Clear terminal screen"""
        import os
        os.system('clear' if os.name == 'posix' else 'cls')

    def format_status_line(self, component: str, status: HealthStatus, width: int = 60) -> str:
        """Format a status line with consistent spacing"""
        icons = {
            "HEALTHY": "✅",
            "WARNING": "⚠️",
            "CRITICAL": "🔥",
            "UNKNOWN": "❓"
        }

        colors = {
            "HEALTHY": "\033[92m",  # Green
            "WARNING": "\033[93m",  # Yellow
            "CRITICAL": "\033[91m",  # Red
            "UNKNOWN": "\033[90m"   # Gray
        }

        reset_color = "\033[0m"
        icon = icons.get(status.status, "❓")
        color = colors.get(status.status, "")

        message = status.message[:width-20]
        if len(status.message) > width-20:
            message = message[:width-23] + "..."

        return f"{color}{icon} {component:15} {message}{reset_color}"

    def format_metrics_bar(self, metrics: SystemMetrics, width: int = 50) -> str:
        """Format system metrics as progress bars"""
        bars = []

        # CPU usage bar
        cpu_bars = int(metrics.cpu_usage / 100 * width)
        cpu_color = "\033[92m" if metrics.cpu_usage < 70 else "\033[93m" if metrics.cpu_usage < 90 else "\033[91m"
        bars.append(f"CPU:  {cpu_color}[{'█' * cpu_bars}{' ' * (width - cpu_bars)}] {metrics.cpu_usage:5.1f}%\033[0m")

        # Memory usage bar
        mem_bars = int(metrics.memory_usage / 100 * width)
        mem_color = "\033[92m" if metrics.memory_usage < 70 else "\033[93m" if metrics.memory_usage < 90 else "\033[91m"
        bars.append(f"MEM: {mem_color}[{'█' * mem_bars}{' ' * (width - mem_bars)}] {metrics.memory_usage:5.1f}%\033[0m")

        # Disk usage bar
        disk_bars = int(metrics.disk_usage / 100 * width)
        disk_color = "\033[92m" if metrics.disk_usage < 80 else "\033[93m" if metrics.disk_usage < 95 else "\033[91m"
        bars.append(f"DSK: {disk_color}[{'█' * disk_bars}{' ' * (width - disk_bars)}] {metrics.disk_usage:5.1f}%\033[0m")

        # GPU metrics if available
        if metrics.gpu_usage is not None and metrics.gpu_memory is not None:
            gpu_bars = int(metrics.gpu_usage / 100 * width)
            gpu_color = "\033[92m" if metrics.gpu_usage < 70 else "\033[93m" if metrics.gpu_usage < 90 else "\033[91m"
            bars.append(f"GPU: {gpu_color}[{'█' * gpu_bars}{' ' * (width - gpu_bars)}] {metrics.gpu_usage:5.1f}%\033[0m")

            mem_bars = int(metrics.gpu_memory / 100 * width)
            mem_color = "\033[92m" if metrics.gpu_memory < 70 else "\033[93m" if metrics.gpu_memory < 90 else "\033[91m"
            bars.append(f"VRAM:{mem_color}[{'█' * mem_bars}{' ' * (width - mem_bars)}] {metrics.gpu_memory:5.1f}%\033[0m")

        return bars

    def display_dashboard(self, health_results: Dict[str, HealthStatus], system_metrics: Optional[SystemMetrics] = None):
        """Display the main dashboard"""
        self.clear_screen()

        # Header
        print("=" * 80)
        print(f"🏥 ComfyUI Health Dashboard - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        # Overall status
        summary = self.monitor.get_health_summary()
        status_colors = {
            "HEALTHY": "\033[92m",
            "WARNING": "\033[93m",
            "CRITICAL": "\033[91m",
            "UNKNOWN": "\033[90m"
        }
        status_color = status_colors.get(summary["overall_status"], "")
        print(f"\n📊 Overall Status: {status_color}{summary['overall_status']}\033[0m")
        print(f"   Total Components: {sum(summary['component_counts'].values())}")
        print(f"   Healthy: {summary['component_counts']['HEALTHY']}")
        print(f"   Warnings: {summary['component_counts']['WARNING']}")
        print(f"   Critical: {summary['component_counts']['CRITICAL']}")
        print(f"   Monitoring: {'🟢 Active' if summary['monitoring_active'] else '🔴 Inactive'}")

        # Component status
        print(f"\n🔍 Component Status:")
        print("-" * 60)
        for name, status in health_results.items():
            print(self.format_status_line(name, status))

        # System metrics
        if system_metrics:
            print(f"\n💻 System Resources:")
            print("-" * 60)
            for bar in self.format_metrics_bar(system_metrics):
                print(bar)

        # Recent alerts
        if self.monitor.alerts:
            print(f"\n🚨 Recent Alerts:")
            print("-" * 60)
            recent_alerts = self.monitor.alerts[-3:]  # Show last 3 alerts
            for alert in recent_alerts:
                timestamp = datetime.fromisoformat(alert["timestamp"])
                print(f"   🔥 {timestamp.strftime('%H:%M:%S')} - {alert['component']}: {alert['message'][:60]}")

        # Custom nodes summary (if available)
        custom_nodes_status = health_results.get("custom_nodes")
        if custom_nodes_status and custom_nodes_status.details:
            nodes_data = custom_nodes_status.details.get("nodes", [])
            if nodes_data:
                print(f"\n📦 Custom Nodes Summary:")
                print("-" * 60)
                total_nodes = len(nodes_data)
                issues_count = sum(1 for node in nodes_data if node.get('has_issues', False))
                warnings_count = sum(1 for node in nodes_data if node.get('has_warnings', False))

                print(f"   Total Nodes: {total_nodes}")
                print(f"   With Issues: {issues_count}")
                print(f"   With Warnings: {warnings_count}")
                print(f"   Healthy: {total_nodes - issues_count - warnings_count}")

        # Controls
        print(f"\n⚙️  Controls:")
        print("-" * 60)
        print("   [r] Refresh now      [d] Toggle details      [m] Toggle monitoring")
        print("   [a] Show alerts      [s] Run health check   [x] Export report")
        print("   [h] Help             [q] Quit")

        if self.show_details:
            self.show_detailed_view(health_results)

    def show_detailed_view(self, health_results: Dict[str, HealthStatus]):
        """Show detailed component information"""
        print(f"\n🔍 Detailed View:")
        print("=" * 80)

        for name, status in health_results.items():
            print(f"\n📋 {name.upper()}:")
            print(f"   Status: {status.status}")
            print(f"   Message: {status.message}")
            print(f"   Timestamp: {status.timestamp}")

            if status.details:
                print(f"   Details:")
                for key, value in status.details.items():
                    if isinstance(value, dict) or isinstance(value, list):
                        print(f"     {key}: {json.dumps(value, indent=6)}")
                    else:
                        print(f"     {key}: {value}")

            if status.suggestions:
                print(f"   Suggestions:")
                for suggestion in status.suggestions:
                    print(f"     💡 {suggestion}")

        print("\n" + "=" * 80)
        input("Press Enter to continue...")

    def show_alerts_screen(self):
        """Show detailed alerts screen"""
        self.clear_screen()
        print("🚨 Alerts History")
        print("=" * 80)

        if not self.monitor.alerts:
            print("✅ No alerts in history")
        else:
            print(f"Total Alerts: {len(self.monitor.alerts)}")
            print("\nRecent Alerts (last 10):")
            print("-" * 80)

            for i, alert in enumerate(self.monitor.alerts[-10:]):
                timestamp = datetime.fromisoformat(alert["timestamp"])
                print(f"\n[{i+1}] {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"    Component: {alert['component']}")
                print(f"    Severity: {alert['severity']}")
                print(f"    Message: {alert['message']}")

                if alert.get('suggestions'):
                    print(f"    Suggestions:")
                    for suggestion in alert['suggestions']:
                        print(f"      💡 {suggestion}")

        print("\nPress Enter to return to dashboard...")
        input()

    def export_report(self):
        """Export health report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = f"/home/ned/ComfyUI-Install/config/health/health_dashboard_{timestamp}.json"

        try:
            self.monitor.export_health_report(export_path)
            print(f"\n✅ Health report exported to: {export_path}")
            time.sleep(2)
        except Exception as e:
            print(f"\n❌ Failed to export report: {e}")
            time.sleep(2)

    def run_interactive(self):
        """Run interactive dashboard"""
        self.running = True
        last_refresh = datetime.now()

        print("🏥 Starting ComfyUI Health Dashboard...")
        print("Initializing...")

        # Initial health check
        health_results = self.monitor.run_health_check()
        _, system_metrics = self.monitor.check_system_resources()

        print("Dashboard ready!")

        while self.running:
            try:
                # Auto-refresh based on interval
                if datetime.now() - last_refresh > timedelta(seconds=self.refresh_interval):
                    health_results = self.monitor.run_health_check()
                    _, system_metrics = self.monitor.check_system_resources()
                    last_refresh = datetime.now()

                # Display dashboard
                self.display_dashboard(health_results, system_metrics)

                # Handle user input
                import select
                import sys
                import termios
                import tty

                # Set up non-blocking input
                old_settings = termios.tcgetattr(sys.stdin)
                try:
                    tty.setraw(sys.stdin.fileno())
                    tty.setcbreak(sys.stdin.fileno())

                    # Wait for input with timeout
                    if select.select([sys.stdin], [], [], 1)[0]:
                        key = sys.stdin.read(1)
                        self.handle_keypress(key, health_results, system_metrics)
                        last_refresh = datetime.now()  # Force refresh after keypress

                finally:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

            except KeyboardInterrupt:
                self.running = False
                break
            except Exception as e:
                print(f"Error in dashboard: {e}")
                time.sleep(1)

        print("\n🛑 Dashboard stopped")

    def handle_keypress(self, key: str, health_results: Dict[str, HealthStatus], system_metrics: Optional[SystemMetrics]):
        """Handle user keypresses"""
        if key.lower() == 'q':
            self.running = False
        elif key.lower() == 'r':
            print("\n🔄 Refreshing...")
            health_results.update(self.monitor.run_health_check())
            _, system_metrics_new = self.monitor.check_system_resources()
            if system_metrics_new:
                system_metrics = system_metrics_new
        elif key.lower() == 'd':
            self.show_details = not self.show_details
        elif key.lower() == 'm':
            if self.monitor.running:
                self.monitor.stop_monitoring()
                print("\n🛑 Monitoring stopped")
            else:
                self.monitor.start_monitoring()
                print("\n🟢 Monitoring started")
            time.sleep(1)
        elif key.lower() == 'a':
            self.show_alerts_screen()
        elif key.lower() == 's':
            print("\n🔍 Running health check...")
            health_results.update(self.monitor.run_health_check())
            print("✅ Health check complete")
            time.sleep(1)
        elif key.lower() == 'x':
            self.export_report()
        elif key.lower() == 'h':
            self.show_help()

    def show_help(self):
        """Show help screen"""
        self.clear_screen()
        print("📖 Health Dashboard Help")
        print("=" * 80)
        print("""
This dashboard provides real-time monitoring of your ComfyUI installation.

CONTROLS:
  [r] Refresh - Run immediate health check and update display
  [d] Details - Toggle detailed component information view
  [m] Monitor - Start/stop continuous background monitoring
  [a] Alerts  - View detailed alerts history
  [s] Status  - Run full health status check
  [x] Export  - Export comprehensive health report to JSON
  [h] Help    - Show this help screen
  [q] Quit    - Exit the dashboard

STATUS INDICATORS:
  ✅ HEALTHY - Component is functioning normally
  ⚠️  WARNING  - Component has issues but is still operational
  🔥 CRITICAL - Component has serious problems requiring attention
  ❓ UNKNOWN  - Component status could not be determined

METRICS:
  CPU/MEM/DSK - System resource usage with color-coded levels
  GPU/VRAM    - NVIDIA GPU usage and memory (if available)
  Alerts      - Critical issues requiring immediate attention

COMPONENTS MONITORED:
  • Service    - ComfyUI process and API accessibility
  • Nodes      - Custom nodes installation and health
  • Resources  - System resource usage and performance
  • API        - ComfyUI-Manager connectivity and response

FEATURES:
  • Real-time health monitoring with configurable intervals
  • System resource visualization with progress bars
  • Alert system with actionable suggestions
  • Exportable health reports in JSON format
  • Background monitoring with automatic alerting
  • Detailed component diagnostics

TROUBLESHOOTING:
  • If components show CRITICAL status, review suggestions
  • High resource usage may indicate configuration issues
  • API connectivity issues may require service restart
  • Custom node issues often relate to missing dependencies

Press Enter to return to dashboard...
        """)
        input()

def main():
    """Main dashboard entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("ComfyUI Health Dashboard")
        print("Usage: python3 scripts/health_dashboard.py")
        print("\nLaunches interactive health monitoring dashboard for ComfyUI")
        print("\nRequirements:")
        print("  • ComfyUI installation at /home/ned/ComfyUI-Install/")
        print("  • Health monitor script (health_monitor.py)")
        print("  • Optional: YAML support for configuration")
        return

    try:
        dashboard = HealthDashboard()
        dashboard.run_interactive()
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped by user")
    except Exception as e:
        print(f"\n❌ Dashboard error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()