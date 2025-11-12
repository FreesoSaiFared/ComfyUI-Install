#!/usr/bin/env python3
"""
Simple Custom Nodes Scanner
A lightweight script to scan and track custom nodes without external dependencies
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path

class CustomNodeScanner:
    """Simple scanner for custom nodes"""

    def __init__(self, comfyui_path=None):
        self.comfyui_path = Path(comfyui_path) if comfyui_path else Path("/home/ned/ComfyUI-Install/ComfyUI")
        self.custom_nodes_path = self.comfyui_path / "custom_nodes"
        self.nodes = {}

    def scan_directory(self, directory_path):
        """Scan a directory and return basic info"""
        path = Path(directory_path)
        if not path.exists() or not path.is_dir():
            return None

        info = {
            'name': path.name,
            'path': str(path),
            'exists': True,
            'file_count': 0,
            'python_files': 0,
            'has_requirements': False,
            'has_install_script': False,
            'has_git': False,
            'size_bytes': 0,
            'last_modified': None
        }

        try:
            # Basic file info
            info['last_modified'] = datetime.fromtimestamp(path.stat().st_mtime).isoformat()

            # Scan contents
            for item in path.rglob('*'):
                if item.is_file():
                    info['file_count'] += 1
                    info['size_bytes'] += item.stat().st_size

                    if item.suffix == '.py':
                        info['python_files'] += 1

                    if item.name == 'requirements.txt':
                        info['has_requirements'] = True
                    elif item.name == 'install.py':
                        info['has_install_script'] = True

            # Check if git repository
            git_dir = path / '.git'
            if git_dir.exists() and git_dir.is_dir():
                info['has_git'] = True
                # Try to get git info
                try:
                    result = subprocess.run(
                        ['git', '-C', str(path), 'remote', 'get-url', 'origin'],
                        capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        info['git_url'] = result.stdout.strip()

                    result = subprocess.run(
                        ['git', '-C', str(path), 'log', '-1', '--format=%h'],
                        capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        info['git_version'] = result.stdout.strip()

                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass

            info['size_mb'] = round(info['size_bytes'] / (1024 * 1024), 2)

            return info

        except Exception as e:
            return {'name': path.name, 'path': str(path), 'error': str(e)}

    def scan_all_nodes(self):
        """Scan all custom nodes"""
        print(f"🔍 Scanning custom nodes in: {self.custom_nodes_path}")

        if not self.custom_nodes_path.exists():
            print(f"❌ Custom nodes directory not found: {self.custom_nodes_path}")
            return {}

        nodes = {}
        total_size = 0

        for item in self.custom_nodes_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                print(f"   Scanning: {item.name}")
                node_info = self.scan_directory(item)
                if node_info and not node_info.get('error'):
                    nodes[item.name] = node_info
                    total_size += node_info.get('size_bytes', 0)

        self.nodes = nodes
        return nodes

    def print_summary(self):
        """Print summary of scanned nodes"""
        if not self.nodes:
            print("❌ No nodes found!")
            return

        total_nodes = len(self.nodes)
        total_size_mb = sum(node.get('size_mb', 0) for node in self.nodes.values())
        git_nodes = sum(1 for node in self.nodes.values() if node.get('has_git'))
        req_nodes = sum(1 for node in self.nodes.values() if node.get('has_requirements'))

        print(f"\n📊 **Custom Nodes Summary**")
        print(f"   Total nodes: {total_nodes}")
        print(f"   Total size: {total_size_mb:.1f} MB")
        print(f"   Git repositories: {git_nodes}")
        print(f"   With requirements: {req_nodes}")
        print(f"   Python files: {sum(node.get('python_files', 0) for node in self.nodes.values())}")

        print(f"\n📦 **Individual Nodes**")
        for name, node in sorted(self.nodes.items()):
            git_icon = "🔧" if node.get('has_git') else "📁"
            req_icon = "⚙️" if node.get('has_requirements') else ""
            install_icon = "📜" if node.get('has_install_script') else ""

            print(f"   {git_icon} {name}")
            print(f"      Size: {node.get('size_mb', 0):.1f} MB")
            print(f"      Files: {node.get('file_count', 0)} ({node.get('python_files', 0)} Python)")
            if node.get('git_url'):
                print(f"      Git: {node.get('git_url')}")
            print(f"      Features: {req_icon}requirements {install_icon}install script")

    def export_to_json(self, output_file):
        """Export nodes data to JSON"""
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'custom_nodes_path': str(self.custom_nodes_path),
            'nodes': self.nodes,
            'summary': {
                'total_nodes': len(self.nodes),
                'total_size_mb': sum(node.get('size_mb', 0) for node in self.nodes.values()),
                'git_nodes': sum(1 for node in self.nodes.values() if node.get('has_git')),
                'nodes_with_requirements': sum(1 for node in self.nodes.values() if node.get('has_requirements'))
            }
        }

        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"✅ Exported to: {output_file}")

def test_api_connectivity():
    """Test if ComfyUI API is accessible"""
    import urllib.request
    import urllib.error

    try:
        url = "http://localhost:8188/customnode/installed"
        print(f"🔌 Testing API connectivity: {url}")

        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'ComfyUI-Manager-Scanner/1.0')

        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                data = response.read().decode('utf-8')
                try:
                    json_data = json.loads(data)
                    print(f"✅ API connected successfully: {len(json_data)} items returned")
                    return json_data
                except json.JSONDecodeError:
                    print(f"⚠️ API responded but data is not valid JSON")
                    return None
            else:
                print(f"❌ API returned status: {response.status}")
                return None

    except urllib.error.URLError as e:
        print(f"❌ Cannot connect to API: {e}")
        return None
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return None

def main():
    """Main function"""
    print("🚀 ComfyUI Custom Nodes Scanner")
    print("=" * 50)

    scanner = CustomNodeScanner()

    # Scan nodes
    nodes = scanner.scan_all_nodes()

    if nodes:
        scanner.print_summary()

        # Export data
        export_dir = Path("/home/ned/ComfyUI-Install/config/custom_nodes")
        export_dir.mkdir(parents=True, exist_ok=True)
        scanner.export_to_json(export_dir / "custom_nodes_scan.json")

        print(f"\n📁 Export saved to: {export_dir}")

    # Test API
    print(f"\n🔌 Testing ComfyUI Manager API...")
    api_result = test_api_connectivity()

    if api_result and isinstance(api_result, list):
        print(f"📋 API Reports {len(api_result)} installed nodes:")
        for item in api_result[:5]:  # Show first 5
            if isinstance(item, dict) and 'title' in item:
                print(f"   - {item.get('title', 'Unknown')}")
        if len(api_result) > 5:
            print(f"   ... and {len(api_result) - 5} more")
    elif api_result:
        print(f"📋 API responded with data (format: {type(api_result)})")

    print(f"\n✅ Scan complete!")

if __name__ == "__main__":
    main()