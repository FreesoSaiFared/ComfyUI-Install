#!/usr/bin/env python3
"""
ComfyUI-Manager Monitor Script

This script provides command-line monitoring of ComfyUI-Manager and custom nodes.
Usage: python comfyui_manager_monitor.py [options]

Commands:
  scan          - Scan all custom nodes and display summary
  monitor       - Start real-time monitoring of custom nodes directory
  api-test      - Test connectivity to ComfyUI-Manager API
  inventory     - Export current node inventory
  health        - Run health checks
  validate      - Validate custom node installations
"""

import sys
import os
import argparse
import json
import yaml
import signal
import time
from pathlib import Path

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from comfyui_manager_interface import ComfyUIManagerInterface, ComfyUIManagerConfig, CustomNodeInfo
from datetime import datetime

class ComfyUIManagerMonitor:
    """Command-line monitor for ComfyUI-Manager"""

    def __init__(self, config_file=None):
        self.config = self._load_config(config_file)
        self.manager = ComfyUIManagerInterface(self.config)
        self.running = False

    def _load_config(self, config_file):
        """Load configuration from file"""
        if config_file and Path(config_file).exists():
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
                return ComfyUIManagerConfig(**config_data.get('config', {}))
        return ComfyUIManagerConfig()

    def scan_nodes(self, detailed=False):
        """Scan and display custom nodes"""
        print("🔍 Scanning custom nodes...")
        nodes = self.manager.scan_all_nodes()

        if not nodes:
            print("❌ No custom nodes found!")
            return

        summary = self.manager.get_node_status_summary()
        print(f"\n📊 **Custom Nodes Summary**")
        print(f"   Total nodes: {summary['total_nodes']}")
        print(f"   Total size: {summary['total_size_mb']:.1f} MB")
        print(f"   Git managed: {summary['git_managed_nodes']}")
        print(f"   With requirements: {summary['nodes_with_requirements']}")
        print(f"   Monitoring: {'🟢 Active' if summary['monitoring_active'] else '🔴 Inactive'}")

        if detailed:
            print(f"\n📦 **Detailed Node Information**")
            for name, node in sorted(nodes.items()):
                git_icon = "🔧" if node.git_url else "📁"
                req_icon = "⚙️" if node.has_requirements else ""
                install_icon = "📜" if node.has_install_script else ""

                print(f"   {git_icon} **{name}**")
                print(f"      Path: {node.path}")
                print(f"      Size: {node.size_mb:.1f} MB")
                print(f"      Node files: {node.node_count}")
                print(f"      Version: {node.version}")
                if node.git_url:
                    print(f"      Git: {node.git_url}")
                print(f"      Features: {req_icon}requirements {install_icon}install script")
                print()

    def start_monitoring(self):
        """Start real-time monitoring"""
        print("🔄 Starting real-time monitoring...")
        print("Press Ctrl+C to stop monitoring\n")

        # Setup signal handler for graceful shutdown
        def signal_handler(signum, frame):
            print(f"\n🛑 Received signal {signum}, stopping monitoring...")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        self.manager.start_monitoring()
        self.running = True

        # Initial scan
        self.scan_nodes(detailed=False)

        print("👀 Watching for changes in custom_nodes directory...")

        try:
            while self.running:
                time.sleep(5)
                # Check for updates every 30 seconds
                if int(time.time()) % 30 == 0:
                    self._check_status()
        except KeyboardInterrupt:
            pass
        finally:
            self.manager.stop_monitoring()
            print("🛑 Monitoring stopped")

    def _check_status(self):
        """Periodic status check"""
        summary = self.manager.get_node_status_summary()
        print(f"⏰ Status check: {summary['total_nodes']} nodes, {summary['total_size_mb']:.1f} MB")

    def test_api(self):
        """Test API connectivity"""
        print("🔌 Testing ComfyUI-Manager API connectivity...")

        endpoints_to_test = [
            ('installed', 'Get installed nodes'),
            ('getlist', 'Get available nodes'),
            ('getmappings', 'Get node mappings'),
            ('snapshot_list', 'Get snapshot list')
        ]

        for endpoint, description in endpoints_to_test:
            print(f"   Testing {description}...")
            result = self.manager.make_api_request(endpoint)
            if result:
                if isinstance(result, list):
                    print(f"   ✅ Success: {len(result)} items returned")
                elif isinstance(result, dict):
                    print(f"   ✅ Success: {len(result)} keys in response")
                else:
                    print(f"   ✅ Success: Response received")
            else:
                print(f"   ❌ Failed: No response or error")

        # Test server connectivity
        import requests
        try:
            response = requests.get(f"http://{self.config.server_host}:{self.config.server_port}", timeout=5)
            if response.status_code == 200:
                print(f"   ✅ ComfyUI server is running on port {self.config.server_port}")
            else:
                print(f"   ⚠️  ComfyUI server responded with status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Cannot connect to ComfyUI server: {e}")

    def export_inventory(self, format_type='both'):
        """Export node inventory"""
        print(f"📤 Exporting node inventory...")

        export_dir = Path(self.config.custom_nodes_path).parent / 'config' / 'custom_nodes'
        export_dir.mkdir(parents=True, exist_ok=True)

        if format_type in ['json', 'both']:
            # Use the manager's export method
            self.manager.export_node_inventory(str(export_dir))
            print(f"   ✅ JSON exported to: {export_dir}/custom_nodes_inventory.json")

        if format_type in ['yaml', 'both']:
            # Custom YAML export with additional info
            inventory = {
                'export_timestamp': datetime.now().isoformat(),
                'comfyui_path': self.config.comfyui_path,
                'custom_nodes_path': self.config.custom_nodes_path,
                'nodes': {name: {
                    'name': node.name,
                    'path': node.path,
                    'version': node.version,
                    'status': node.status,
                    'git_url': node.git_url,
                    'size_mb': node.size_mb,
                    'node_count': node.node_count,
                    'has_requirements': node.has_requirements,
                    'has_install_script': node.has_install_script,
                    'last_updated': node.last_updated
                } for name, node in self.manager.nodes_cache.items()},
                'summary': self.manager.get_node_status_summary()
            }

            yaml_path = export_dir / 'custom_nodes_inventory_detailed.yaml'
            with open(yaml_path, 'w') as f:
                yaml.dump(inventory, f, default_flow_style=False, sort_keys=False)
            print(f"   ✅ YAML exported to: {yaml_path}")

    def health_check(self):
        """Run comprehensive health checks"""
        print("🏥 Running health checks...")

        checks = []

        # Check 1: Directories exist
        paths_to_check = [
            ('ComfyUI path', Path(self.config.comfyui_path)),
            ('Custom nodes path', Path(self.config.custom_nodes_path)),
            ('Config path', Path(self.config.config_path))
        ]

        for name, path in paths_to_check:
            if path.exists():
                checks.append((name, "✅", f"Found at {path}"))
            else:
                checks.append((name, "❌", f"Missing: {path}"))

        # Check 2: File permissions
        custom_nodes_path = Path(self.config.custom_nodes_path)
        if custom_nodes_path.exists():
            if os.access(custom_nodes_path, os.R_OK | os.W_OK):
                checks.append(('File permissions', "✅", "Read/write access to custom_nodes"))
            else:
                checks.append(('File permissions', "⚠️", "Limited access to custom_nodes"))

        # Check 3: Git repositories
        git_repos = 0
        git_issues = 0
        if self.manager.nodes_cache:
            for name, node in self.manager.nodes_cache.items():
                if node.git_url:
                    git_repos += 1
                    # Check if git repo is valid
                    try:
                        import git
                        git.Repo(node.path)
                    except:
                        git_issues += 1

            checks.append(('Git repositories', f"✅", f"{git_repos} found, {git_issues} issues"))

        # Check 4: API connectivity
        api_result = self.manager.make_api_request('installed')
        if api_result is not None:
            checks.append(('API connectivity', "✅", "ComfyUI-Manager API responding"))
        else:
            checks.append(('API connectivity', "❌", "Cannot connect to ComfyUI-Manager API"))

        # Check 5: Large nodes (size warning)
        large_nodes = [node for node in self.manager.nodes_cache.values() if node.size_mb > 100]
        if large_nodes:
            names = [node.name for node in large_nodes]
            checks.append(('Large nodes', "⚠️", f"{len(large_nodes)} nodes > 100MB: {', '.join(names[:3])}"))

        # Display results
        print(f"\n📋 **Health Check Results**")
        for name, status, message in checks:
            print(f"   {status} {name}: {message}")

        # Overall health
        failed = sum(1 for _, status, _ in checks if status == "❌")
        warnings = sum(1 for _, status, _ in checks if status == "⚠️")

        print(f"\n🎯 **Overall Health**: {'❌ Failed' if failed > 0 else '⚠️ Warnings' if warnings > 0 else '✅ Healthy'}")
        print(f"   Failed checks: {failed}")
        print(f"   Warnings: {warnings}")

    def validate_nodes(self):
        """Validate custom node installations"""
        print("🔍 Validating custom node installations...")

        if not self.manager.nodes_cache:
            print("   No nodes in cache, running scan first...")
            self.manager.scan_all_nodes()

        validation_results = []

        for name, node in self.manager.nodes_cache.items():
            issues = []

            # Check directory structure
            node_path = Path(node.path)
            if not node_path.exists():
                issues.append("Directory not found")
            elif not any(node_path.iterdir()):
                issues.append("Empty directory")

            # Check for __init__.py (standard for custom nodes)
            if not (node_path / '__init__.py').exists():
                issues.append("Missing __init__.py")

            # Check git repository health
            if node.git_url:
                try:
                    repo = git.Repo(node_path)
                    if repo.bare:
                        issues.append("Git repository is bare")
                    if repo.is_dirty():
                        issues.append("Git repository has uncommitted changes")
                except Exception as e:
                    issues.append(f"Git repository error: {e}")

            # Check requirements.txt if exists
            if node.has_requirements:
                req_file = node_path / 'requirements.txt'
                if req_file.exists():
                    try:
                        with open(req_file, 'r') as f:
                            reqs = f.read().strip()
                        if not reqs:
                            issues.append("Empty requirements.txt")
                    except:
                        issues.append("Cannot read requirements.txt")

            # Determine status
            if not issues:
                status = "✅ Valid"
            elif len(issues) <= 2:
                status = "⚠️ Minor issues"
            else:
                status = "❌ Issues detected"

            validation_results.append({
                'name': name,
                'status': status,
                'issues': issues,
                'node': node
            })

        # Display results
        print(f"\n📋 **Validation Results**")
        for result in validation_results:
            print(f"   {result['status']} {result['name']}")
            if result['issues']:
                for issue in result['issues']:
                    print(f"      - {issue}")

        # Summary
        valid = sum(1 for r in validation_results if r['status'] == "✅ Valid")
        warnings = sum(1 for r in validation_results if r['status'] == "⚠️ Minor issues")
        failed = sum(1 for r in validation_results if r['status'] == "❌ Issues detected")

        print(f"\n📊 **Validation Summary**")
        print(f"   Valid: {valid}")
        print(f"   Warnings: {warnings}")
        print(f"   Failed: {failed}")

def main():
    parser = argparse.ArgumentParser(description='ComfyUI-Manager Monitor')
    parser.add_argument('command', choices=['scan', 'monitor', 'api-test', 'inventory', 'health', 'validate'],
                       help='Command to execute')
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--detailed', '-d', action='store_true', help='Show detailed information')
    parser.add_argument('--format', '-f', choices=['json', 'yaml', 'both'], default='both',
                       help='Export format for inventory command')

    args = parser.parse_args()

    monitor = ComfyUIManagerMonitor(args.config)

    try:
        if args.command == 'scan':
            monitor.scan_nodes(detailed=args.detailed)
        elif args.command == 'monitor':
            monitor.start_monitoring()
        elif args.command == 'api-test':
            monitor.test_api()
        elif args.command == 'inventory':
            monitor.export_inventory(format_type=args.format)
        elif args.command == 'health':
            monitor.health_check()
        elif args.command == 'validate':
            monitor.validate_nodes()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()