#!/usr/bin/env python3
"""
ComfyUI Health Monitor

Comprehensive health monitoring system for ComfyUI installation,
custom nodes, and system dependencies. Provides real-time monitoring,
automated health checks, and repair suggestions.
"""

import os
import sys
import json
import time
import subprocess
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import socket
import urllib.request
import urllib.error

@dataclass
class HealthStatus:
    """Represents health status of a component"""
    name: str
    status: str  # "HEALTHY", "WARNING", "CRITICAL", "UNKNOWN"
    message: str
    timestamp: str
    details: Optional[Dict[str, Any]] = None
    suggestions: Optional[List[str]] = None

@dataclass
class SystemMetrics:
    """System performance metrics"""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    gpu_usage: Optional[float]
    gpu_memory: Optional[float]
    timestamp: str

class ComfyUIHealthMonitor:
    """Main health monitoring system for ComfyUI"""

    def __init__(self, config_path: str = None):
        self.comfyui_path = Path("/home/ned/ComfyUI-Install/ComfyUI")
        self.custom_nodes_path = self.comfyui_path / "custom_nodes"
        self.config_path = Path(config_path) if config_path else \
            Path("/home/ned/ComfyUI-Install/config/health_monitor.json")

        self.health_history = []
        self.alerts = []
        self.running = False
        self.monitoring_thread = None

        # Load configuration
        self.config = self._load_config()

        # Initialize monitoring intervals
        self.check_interval = self.config.get("check_interval", 60)  # seconds
        self.api_timeout = self.config.get("api_timeout", 10)
        self.comfyui_port = self.config.get("comfyui_port", 8188)

    def _load_config(self) -> Dict[str, Any]:
        """Load monitoring configuration"""
        default_config = {
            "check_interval": 60,
            "api_timeout": 10,
            "comfyui_port": 8188,
            "enable_gpu_monitoring": True,
            "enable_dependency_tracking": True,
            "alert_thresholds": {
                "cpu_usage": 80.0,
                "memory_usage": 85.0,
                "disk_usage": 90.0,
                "gpu_memory_usage": 90.0
            },
            "repair_suggestions": True,
            "log_retention_days": 30
        }

        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                print(f"Warning: Could not load config, using defaults: {e}")

        return default_config

    def save_config(self):
        """Save current configuration"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

    def check_comfyui_service(self) -> HealthStatus:
        """Check if ComfyUI service is running and accessible"""
        status = HealthStatus(
            name="comfyui_service",
            status="UNKNOWN",
            message="Checking ComfyUI service...",
            timestamp=datetime.now().isoformat()
        )

        try:
            # Check if process is running
            result = subprocess.run(
                ["pgrep", "-f", "ComfyUI/main.py"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                status.details = {"running_pids": pids, "count": len(pids)}

                # Check API accessibility
                try:
                    response = urllib.request.urlopen(
                        f"http://localhost:{self.comfyui_port}/prompt",
                        timeout=self.api_timeout
                    )
                    if response.status == 200:
                        status.status = "HEALTHY"
                        status.message = f"ComfyUI running with {len(pids)} process(es), API accessible"
                    else:
                        status.status = "WARNING"
                        status.message = f"ComfyUI running but API returned status {response.status}"
                except urllib.error.URLError as e:
                    status.status = "WARNING"
                    status.message = f"ComfyUI running but API not accessible: {e}"
            else:
                status.status = "CRITICAL"
                status.message = "ComfyUI service not running"
                status.suggestions = [
                    "Start ComfyUI service: cd /home/ned/ComfyUI-Install/ComfyUI && python main.py --port 8188",
                    "Check startup scripts in /home/ned/ComfyUI-Install/scripts/",
                    "Review logs for startup errors"
                ]

        except Exception as e:
            status.status = "UNKNOWN"
            status.message = f"Error checking ComfyUI service: {e}"

        return status

    def check_custom_nodes_health(self) -> HealthStatus:
        """Check health of custom nodes"""
        status = HealthStatus(
            name="custom_nodes",
            status="UNKNOWN",
            message="Checking custom nodes...",
            timestamp=datetime.now().isoformat()
        )

        try:
            if not self.custom_nodes_path.exists():
                status.status = "CRITICAL"
                status.message = "Custom nodes directory not found"
                status.suggestions = [
                    "Create custom_nodes directory: mkdir -p /home/ned/ComfyUI-Install/ComfyUI/custom_nodes",
                    "Ensure ComfyUI installation is complete"
                ]
                return status

            # Scan nodes
            nodes = []
            total_issues = 0
            total_warnings = 0

            for item in self.custom_nodes_path.iterdir():
                if item.is_dir() and not item.name.startswith('.') and item.name != '__pycache__':
                    node_info = self._check_single_node_health(item)
                    nodes.append(node_info)

                    if node_info.get('has_issues', False):
                        total_issues += 1
                    if node_info.get('has_warnings', False):
                        total_warnings += 1

            status.details = {
                "total_nodes": len(nodes),
                "nodes_with_issues": total_issues,
                "nodes_with_warnings": total_warnings,
                "nodes": nodes
            }

            if total_issues > len(nodes) * 0.5:  # More than 50% have issues
                status.status = "CRITICAL"
                status.message = f"Critical: {total_issues}/{len(nodes)} nodes have serious issues"
                status.suggestions = [
                    "Run dependency installation for affected nodes",
                    "Check ComfyUI compatibility for each node",
                    "Consider removing problematic nodes"
                ]
            elif total_issues > 0:
                status.status = "WARNING"
                status.message = f"Warning: {total_issues} nodes have issues, {total_warnings} have warnings"
                status.suggestions = [
                    "Review validation results: python3 scripts/comfyui_nodes_validator.py",
                    "Install missing dependencies for affected nodes"
                ]
            else:
                status.status = "HEALTHY"
                status.message = f"All {len(nodes)} custom nodes appear healthy"

        except Exception as e:
            status.status = "UNKNOWN"
            status.message = f"Error checking custom nodes: {e}"

        return status

    def _check_single_node_health(self, node_path: Path) -> Dict[str, Any]:
        """Check health of a single custom node"""
        node_info = {
            "name": node_path.name,
            "path": str(node_path),
            "exists": True,
            "has_issues": False,
            "has_warnings": False,
            "issues": [],
            "warnings": []
        }

        try:
            # Check basic structure
            if not any(node_path.iterdir()):
                node_info["has_issues"] = True
                node_info["issues"].append("Node directory is empty")
                return node_info

            # Check for requirements.txt and dependencies
            req_file = node_path / "requirements.txt"
            if req_file.exists():
                missing_deps = self._check_requirements(req_file)
                if missing_deps:
                    node_info["has_issues"] = True
                    node_info["issues"].extend([f"Missing: {dep}" for dep in missing_deps])

            # Check for __init__.py
            init_file = node_path / "__init__.py"
            if not init_file.exists():
                node_info["has_warnings"] = True
                node_info["warnings"].append("Missing __init__.py")

            # Check Python syntax
            syntax_errors = self._check_python_syntax(node_path)
            if syntax_errors:
                node_info["has_issues"] = True
                node_info["issues"].extend(syntax_errors)

        except Exception as e:
            node_info["has_issues"] = True
            node_info["issues"].append(f"Error checking node: {e}")

        return node_info

    def _check_requirements(self, req_file: Path) -> List[str]:
        """Check if requirements are installed"""
        missing = []
        try:
            with open(req_file, 'r') as f:
                requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

            for req in requirements:
                # Extract package name (remove version specifiers)
                pkg_name = req.split('>=')[0].split('==')[0].split('<=')[0].strip()
                if not self._is_package_installed(pkg_name):
                    missing.append(pkg_name)
        except Exception:
            pass

        return missing

    def _check_python_syntax(self, node_path: Path) -> List[str]:
        """Check Python syntax in all .py files"""
        errors = []
        for py_file in node_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                compile(content, str(py_file), 'exec')
            except SyntaxError as e:
                errors.append(f"Syntax error in {py_file.name}: {e.msg}")
            except Exception:
                pass
        return errors

    def _is_package_installed(self, package_name: str) -> bool:
        """Check if a Python package is installed"""
        try:
            result = subprocess.run(
                [sys.executable, "-c", f"import {package_name}"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False

    def check_system_resources(self) -> Tuple[HealthStatus, Optional[SystemMetrics]]:
        """Check system resource usage"""
        status = HealthStatus(
            name="system_resources",
            status="UNKNOWN",
            message="Checking system resources...",
            timestamp=datetime.now().isoformat()
        )

        try:
            # Get CPU usage
            cpu_usage = self._get_cpu_usage()

            # Get memory usage
            memory_usage = self._get_memory_usage()

            # Get disk usage
            disk_usage = self._get_disk_usage()

            # Get GPU metrics if enabled
            gpu_metrics = None
            if self.config.get("enable_gpu_monitoring"):
                gpu_metrics = self._get_gpu_metrics()

            metrics = SystemMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                gpu_usage=gpu_metrics[0] if gpu_metrics else None,
                gpu_memory=gpu_metrics[1] if gpu_metrics else None,
                timestamp=datetime.now().isoformat()
            )

            status.details = asdict(metrics)

            # Check against thresholds
            thresholds = self.config.get("alert_thresholds", {})
            issues = []

            if cpu_usage > thresholds.get("cpu_usage", 80):
                issues.append(f"High CPU usage: {cpu_usage:.1f}%")

            if memory_usage > thresholds.get("memory_usage", 85):
                issues.append(f"High memory usage: {memory_usage:.1f}%")

            if disk_usage > thresholds.get("disk_usage", 90):
                issues.append(f"High disk usage: {disk_usage:.1f}%")

            if gpu_metrics and gpu_metrics[1] > thresholds.get("gpu_memory_usage", 90):
                issues.append(f"High GPU memory usage: {gpu_metrics[1]:.1f}%")

            if issues:
                status.status = "WARNING"
                status.message = f"Resource usage alerts: {', '.join(issues)}"
                status.suggestions = [
                    "Check for runaway processes",
                    "Consider restarting ComfyUI if resource usage is high",
                    "Monitor GPU memory usage during generation"
                ]
            else:
                status.status = "HEALTHY"
                status.message = f"System resources normal - CPU: {cpu_usage:.1f}%, Memory: {memory_usage:.1f}%, Disk: {disk_usage:.1f}%"

            return status, metrics

        except Exception as e:
            status.status = "UNKNOWN"
            status.message = f"Error checking system resources: {e}"
            return status, None

    def _get_cpu_usage(self) -> float:
        """Get CPU usage percentage"""
        try:
            # Try to use psutil if available, otherwise use simple method
            try:
                import psutil
                return psutil.cpu_percent(interval=1)
            except ImportError:
                # Fallback to /proc/stat
                with open('/proc/stat', 'r') as f:
                    stats = f.readline().split()
                idle = int(stats[4])
                total = sum(map(int, stats[1:]))
                time.sleep(1)
                with open('/proc/stat', 'r') as f:
                    stats2 = f.readline().split()
                idle2 = int(stats2[4])
                total2 = sum(map(int, stats2[1:]))
                return (1 - (idle2 - idle) / (total2 - total)) * 100
        except:
            return 0.0

    def _get_memory_usage(self) -> float:
        """Get memory usage percentage"""
        try:
            with open('/proc/meminfo', 'r') as f:
                meminfo = dict((i.split()[0].rstrip(':'), int(i.split()[1]))
                            for i in f.readlines())
            total = meminfo['MemTotal']
            available = meminfo['MemAvailable']
            return ((total - available) / total) * 100
        except:
            return 0.0

    def _get_disk_usage(self) -> float:
        """Get disk usage percentage"""
        try:
            result = subprocess.run(['df', '/home'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 5:
                    total = int(parts[1])
                    used = int(parts[2])
                    return (used / total) * 100
        except:
            return 0.0
        return 0.0

    def _get_gpu_metrics(self) -> Optional[Tuple[float, float]]:
        """Get GPU usage and memory usage"""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total', '--format=csv,noheader,nounits'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                values = result.stdout.strip().split(', ')
                if len(values) >= 3:
                    gpu_usage = float(values[0])
                    memory_used = float(values[1])
                    memory_total = float(values[2])
                    memory_percent = (memory_used / memory_total) * 100
                    return gpu_usage, memory_percent
        except:
            pass
        return None

    def check_api_connectivity(self) -> HealthStatus:
        """Check connectivity to ComfyUI-Manager API"""
        status = HealthStatus(
            name="api_connectivity",
            status="UNKNOWN",
            message="Checking API connectivity...",
            timestamp=datetime.now().isoformat()
        )

        try:
            # Test basic connectivity
            response = urllib.request.urlopen(
                f"http://localhost:{self.comfyui_port}/customnode/installed",
                timeout=self.api_timeout
            )

            if response.status == 200:
                data = response.read().decode('utf-8')
                try:
                    nodes_data = json.loads(data)
                    node_count = len(nodes_data) if isinstance(nodes_data, dict) else 0

                    status.status = "HEALTHY"
                    status.message = f"API connected successfully, {node_count} nodes reported"
                    status.details = {"response_status": response.status, "node_count": node_count}
                except json.JSONDecodeError:
                    status.status = "WARNING"
                    status.message = "API connected but response format invalid"
            else:
                status.status = "WARNING"
                status.message = f"API returned status {response.status}"
                status.suggestions = [
                    "Check if ComfyUI-Manager is properly installed",
                    "Verify ComfyUI is running on the correct port",
                    "Check ComfyUI logs for API errors"
                ]

        except urllib.error.URLError as e:
            status.status = "CRITICAL"
            status.message = f"Cannot connect to API: {e}"
            status.suggestions = [
                "Ensure ComfyUI is running",
                "Check firewall settings",
                "Verify port configuration"
            ]
        except Exception as e:
            status.status = "UNKNOWN"
            status.message = f"Error checking API: {e}"

        return status

    def run_health_check(self) -> Dict[str, HealthStatus]:
        """Run complete health check"""
        print(f"🏥 Running comprehensive health check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        results = {}

        # Run all health checks
        checks = [
            ("service", self.check_comfyui_service()),
            ("custom_nodes", self.check_custom_nodes_health()),
            ("system_resources", self.check_system_resources()[0]),
            ("api_connectivity", self.check_api_connectivity())
        ]

        for name, status in checks:
            results[name] = status
            print(f"   {status.name}: {status.status} - {status.message}")

        # Store results
        self.health_history.append({
            "timestamp": datetime.now().isoformat(),
            "results": {name: asdict(status) for name, status in results.items()}
        })

        # Generate alerts for critical issues
        self._generate_alerts(results)

        return results

    def _generate_alerts(self, results: Dict[str, HealthStatus]):
        """Generate alerts for critical health issues"""
        for name, status in results.items():
            if status.status == "CRITICAL":
                alert = {
                    "timestamp": datetime.now().isoformat(),
                    "component": name,
                    "severity": "CRITICAL",
                    "message": status.message,
                    "suggestions": status.suggestions or []
                }

                # Check if this is a new alert (not repeated within last hour)
                recent_alerts = [a for a in self.alerts if
                               datetime.fromisoformat(a["timestamp"]) > datetime.now() - timedelta(hours=1)]

                if not any(a["component"] == name and a["message"] == status.message for a in recent_alerts):
                    self.alerts.append(alert)
                    print(f"🚨 CRITICAL ALERT: {name} - {status.message}")

    def start_monitoring(self):
        """Start continuous monitoring"""
        if self.running:
            print("Monitoring already running")
            return

        print(f"🔄 Starting health monitoring (checking every {self.check_interval} seconds)...")
        self.running = True

        def monitoring_loop():
            while self.running:
                try:
                    self.run_health_check()

                    # Cleanup old alerts (older than 24 hours)
                    cutoff = datetime.now() - timedelta(hours=24)
                    self.alerts = [a for a in self.alerts
                                 if datetime.fromisoformat(a["timestamp"]) > cutoff]

                    # Cleanup old health history (keep last 1000 entries)
                    if len(self.health_history) > 1000:
                        self.health_history = self.health_history[-1000:]

                except Exception as e:
                    print(f"Error during health check: {e}")

                time.sleep(self.check_interval)

        self.monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
        self.monitoring_thread.start()

    def stop_monitoring(self):
        """Stop continuous monitoring"""
        if not self.running:
            return

        print("🛑 Stopping health monitoring...")
        self.running = False

        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)

    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary and recent metrics"""
        if not self.health_history:
            return {"status": "No health data available"}

        latest = self.health_history[-1]["results"]

        # Count status types
        status_counts = {"HEALTHY": 0, "WARNING": 0, "CRITICAL": 0, "UNKNOWN": 0}
        for component_data in latest.values():
            status = component_data.get("status", "UNKNOWN")
            status_counts[status] += 1

        overall_status = "HEALTHY"
        if status_counts["CRITICAL"] > 0:
            overall_status = "CRITICAL"
        elif status_counts["WARNING"] > 0:
            overall_status = "WARNING"
        elif status_counts["UNKNOWN"] > status_counts["HEALTHY"]:
            overall_status = "UNKNOWN"

        return {
            "timestamp": latest["service"]["timestamp"],
            "overall_status": overall_status,
            "component_counts": status_counts,
            "recent_alerts": self.alerts[-5:] if self.alerts else [],
            "monitoring_active": self.running,
            "total_checks": len(self.health_history)
        }

    def export_health_report(self, output_path: str):
        """Export comprehensive health report"""
        report = {
            "export_timestamp": datetime.now().isoformat(),
            "config": self.config,
            "current_health": self.get_health_summary(),
            "recent_health_history": self.health_history[-10:] if self.health_history else [],
            "alerts": self.alerts,
            "summary": {
                "total_checks_run": len(self.health_history),
                "active_alerts": len(self.alerts),
                "monitoring_uptime": "N/A"
            }
        }

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"📊 Health report exported to: {output_path}")

def main():
    """Main health monitoring script"""
    print("🏥 ComfyUI Health Monitor")
    print("=" * 50)

    monitor = ComfyUIHealthMonitor()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "check":
            # Run single health check
            results = monitor.run_health_check()
            print(f"\n📊 Health Summary:")
            for name, status in results.items():
                icon = {"HEALTHY": "✅", "WARNING": "⚠️", "CRITICAL": "🔥", "UNKNOWN": "❓"}[status.status]
                print(f"   {icon} {name}: {status.message}")

            # Export results
            export_dir = Path("/home/ned/ComfyUI-Install/config/health")
            export_dir.mkdir(parents=True, exist_ok=True)
            monitor.export_health_report(export_dir / f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

        elif command == "monitor":
            # Start continuous monitoring
            monitor.start_monitoring()
            print("Press Ctrl+C to stop monitoring...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                monitor.stop_monitoring()
                print(f"\n🛑 Monitoring stopped")

        elif command == "summary":
            # Show health summary
            summary = monitor.get_health_summary()
            print(f"\n📊 Health Summary:")
            print(f"   Overall Status: {summary['overall_status']}")
            print(f"   Total Checks: {summary['total_checks']}")
            print(f"   Active Alerts: {len(summary['recent_alerts'])}")
            print(f"   Monitoring: {'Active' if summary['monitoring_active'] else 'Inactive'}")

        elif command == "alerts":
            # Show recent alerts
            alerts = monitor.alerts[-10:] if monitor.alerts else []
            if alerts:
                print(f"\n🚨 Recent Alerts ({len(alerts)}):")
                for alert in alerts:
                    timestamp = datetime.fromisoformat(alert["timestamp"])
                    print(f"   {timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {alert['component']}: {alert['message']}")
            else:
                print("\n✅ No recent alerts")

        else:
            print("Usage: python3 scripts/health_monitor.py [check|monitor|summary|alerts]")
    else:
        print("Usage: python3 scripts/health_monitor.py [check|monitor|summary|alerts]")

if __name__ == "__main__":
    main()