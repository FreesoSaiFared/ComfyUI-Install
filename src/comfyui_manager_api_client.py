#!/usr/bin/env python3
"""
ComfyUI-Manager API Client

A lightweight API client for interacting with ComfyUI-Manager's REST API endpoints.
Provides programmatic access to install, manage, and monitor custom nodes.
"""

import json
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import time

@dataclass
class ComfyUINode:
    """Represents a custom node in ComfyUI-Manager"""
    title: str
    author: str
    description: str
    reference: str
    files: List[str]
    install_type: str
    unique_id: str
    id: str
    version: Optional[str] = None
    installed: bool = False

@dataclass
class APIClientConfig:
    """Configuration for API client"""
    host: str = "localhost"
    port: int = 8188
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 5

class ComfyUIManagerAPIClient:
    """Client for ComfyUI-Manager API"""

    def __init__(self, config: Optional[APIClientConfig] = None):
        self.config = config or APIClientConfig()
        self.base_url = f"http://{self.config.host}:{self.config.port}"

    def _make_request(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None) -> Optional[Any]:
        """Make HTTP request to ComfyUI-Manager API"""
        url = f"{self.base_url}{endpoint}"

        for attempt in range(self.config.retry_attempts):
            try:
                if method == 'GET':
                    req = urllib.request.Request(url)
                elif method == 'POST':
                    req = urllib.request.Request(url, method='POST')
                    req.add_header('Content-Type', 'application/json')
                    if data:
                        req.data = json.dumps(data).encode('utf-8')
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                req.add_header('User-Agent', 'ComfyUI-Manager-APIClient/1.0')

                with urllib.request.urlopen(req, timeout=self.config.timeout) as response:
                    if response.status == 200:
                        response_data = response.read().decode('utf-8')
                        try:
                            return json.loads(response_data)
                        except json.JSONDecodeError:
                            return response_data
                    else:
                        print(f"HTTP {response.status}: {response.reason}")
                        return None

            except urllib.error.URLError as e:
                if attempt < self.config.retry_attempts - 1:
                    print(f"Request failed (attempt {attempt + 1}/{self.config.retry_attempts}): {e}")
                    time.sleep(self.config.retry_delay)
                else:
                    print(f"API request failed after {self.config.retry_attempts} attempts: {e}")
                    return None
            except Exception as e:
                print(f"Unexpected error: {e}")
                return None

        return None

    def test_connection(self) -> bool:
        """Test if we can connect to ComfyUI-Manager API"""
        print(f"Testing connection to {self.base_url}")
        result = self._make_request('/customnode/installed')
        if result is not None:
            print("✅ Successfully connected to ComfyUI-Manager API")
            return True
        else:
            print("❌ Failed to connect to ComfyUI-Manager API")
            return False

    def get_installed_nodes(self) -> Optional[List[ComfyUINode]]:
        """Get list of installed custom nodes"""
        print("Fetching installed nodes...")
        result = self._make_request('/customnode/installed')

        if result and isinstance(result, dict):
            # Convert dict values to ComfyUINode objects
            nodes = []
            for node_data in result.values():
                if isinstance(node_data, dict):
                    node = ComfyUINode(
                        title=node_data.get('title', ''),
                        author=node_data.get('author', ''),
                        description=node_data.get('description', ''),
                        reference=node_data.get('reference', ''),
                        files=node_data.get('files', []),
                        install_type=node_data.get('install_type', ''),
                        unique_id=node_data.get('unique_id', ''),
                        id=node_data.get('id', ''),
                        version=node_data.get('version'),
                        installed=True
                    )
                    nodes.append(node)
            return nodes

        return None

    def get_available_nodes(self) -> Optional[List[ComfyUINode]]:
        """Get list of available custom nodes from the registry"""
        print("Fetching available nodes...")
        result = self._make_request('/customnode/getlist')

        if result and isinstance(result, list):
            nodes = []
            for node_data in result:
                if isinstance(node_data, dict):
                    node = ComfyUINode(
                        title=node_data.get('title', ''),
                        author=node_data.get('author', ''),
                        description=node_data.get('description', ''),
                        reference=node_data.get('reference', ''),
                        files=node_data.get('files', []),
                        install_type=node_data.get('install_type', ''),
                        unique_id=node_data.get('unique_id', ''),
                        id=node_data.get('id', ''),
                        version=node_data.get('version'),
                        installed=False
                    )
                    nodes.append(node)
            return nodes

        return None

    def get_node_mappings(self) -> Optional[Dict[str, Any]]:
        """Get node mappings (which nodes provide which functionality)"""
        print("Fetching node mappings...")
        return self._make_request('/customnode/getmappings')

    def fetch_updates(self) -> Optional[Dict[str, Any]]:
        """Check for updates to installed custom nodes"""
        print("Fetching updates...")
        return self._make_request('/customnode/fetch_updates')

    def get_alternatives(self) -> Optional[Dict[str, Any]]:
        """Get alternative nodes for missing functionality"""
        print("Fetching alternatives...")
        return self._make_request('/customnode/alternatives')

    def get_snapshots(self) -> Optional[List[Dict[str, Any]]]:
        """Get list of saved snapshots"""
        print("Fetching snapshots...")
        return self._make_request('/snapshot/getlist')

    def install_node(self, node_id: str) -> bool:
        """Install a custom node by ID"""
        print(f"Installing node: {node_id}")
        # Note: This endpoint may require additional parameters or authentication
        data = {'node_id': node_id}
        result = self._make_request('/customnode/install', method='POST', data=data)
        return result is not None

    def uninstall_node(self, node_id: str) -> bool:
        """Uninstall a custom node by ID"""
        print(f"Uninstalling node: {node_id}")
        # Note: This endpoint may require additional parameters or authentication
        data = {'node_id': node_id}
        result = self._make_request('/customnode/uninstall', method='POST', data=data)
        return result is not None

    def update_all_nodes(self) -> bool:
        """Update all installed custom nodes"""
        print("Updating all nodes...")
        result = self._make_request('/manager/queue/update_all')
        return result is not None

    def get_system_status(self) -> Optional[Dict[str, Any]]:
        """Get system status from ComfyUI-Manager"""
        print("Getting system status...")
        return self._make_request('/system/stats')

    def print_node_summary(self, nodes: List[ComfyUINode]):
        """Print a summary of nodes"""
        if not nodes:
            print("No nodes found")
            return

        print(f"\n📊 **Node Summary ({len(nodes)} nodes)**")

        # Group by author
        authors = {}
        for node in nodes:
            author = node.author or 'Unknown'
            if author not in authors:
                authors[author] = []
            authors[author].append(node)

        for author, author_nodes in sorted(authors.items()):
            print(f"\n👤 **{author}** ({len(author_nodes)} nodes)")
            for node in sorted(author_nodes, key=lambda x: x.title):
                status = "✅" if node.installed else "⬜"
                version = f" v{node.version}" if node.version else ""
                print(f"   {status} {node.title}{version}")
                if node.description:
                    print(f"      {node.description[:80]}...")

    def export_node_list(self, nodes: List[ComfyUINode], filename: str):
        """Export node list to JSON file"""
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'api_endpoint': self.base_url,
            'total_nodes': len(nodes),
            'installed_nodes': sum(1 for node in nodes if node.installed),
            'nodes': [
                {
                    'title': node.title,
                    'author': node.author,
                    'description': node.description,
                    'reference': node.reference,
                    'install_type': node.install_type,
                    'unique_id': node.unique_id,
                    'id': node.id,
                    'version': node.version,
                    'installed': node.installed
                }
                for node in nodes
            ]
        }

        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"✅ Exported {len(nodes)} nodes to {filename}")

    def monitor_changes(self, interval_minutes: int = 5):
        """Monitor for changes in custom nodes"""
        print(f"🔄 Starting monitoring (checking every {interval_minutes} minutes)...")
        print("Press Ctrl+C to stop monitoring")

        try:
            last_known_nodes = None

            while True:
                print(f"\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Checking for changes...")

                current_nodes = self.get_installed_nodes()
                if current_nodes is None:
                    print("❌ Failed to get current nodes")
                    time.sleep(interval_minutes * 60)
                    continue

                if last_known_nodes:
                    # Compare with last known state
                    current_ids = {node.id: node for node in current_nodes}
                    last_ids = {node.id: node for node in last_known_nodes}

                    # Check for new installations
                    new_nodes = []
                    for node_id, node in current_ids.items():
                        if node_id not in last_ids:
                            new_nodes.append(node)
                            print(f"🆕 New node installed: {node.title}")

                    # Check for removals
                    removed_nodes = []
                    for node_id, node in last_ids.items():
                        if node_id not in current_ids:
                            removed_nodes.append(node)
                            print(f"🗑️  Node removed: {node.title}")

                    # Check for updates
                    updated_nodes = []
                    for node_id, node in current_ids.items():
                        if node_id in last_ids:
                            last_node = last_ids[node_id]
                            if last_node.version != node.version:
                                updated_nodes.append((last_node, node))
                                print(f"⬆️  Node updated: {node.title} ({last_node.version} -> {node.version})")

                    if not new_nodes and not removed_nodes and not updated_nodes:
                        print("✅ No changes detected")

                last_known_nodes = current_nodes

                # Wait for next check
                time.sleep(interval_minutes * 60)

        except KeyboardInterrupt:
            print(f"\n🛑 Monitoring stopped")

def main():
    """Demonstrate API client functionality"""
    print("🚀 ComfyUI-Manager API Client Demo")
    print("=" * 50)

    # Create client
    client = ComfyUIManagerAPIClient()

    # Test connection
    if not client.test_connection():
        print("❌ Cannot proceed - API connection failed")
        return

    # Get installed nodes
    print("\n" + "="*50)
    installed_nodes = client.get_installed_nodes()
    if installed_nodes:
        print(f"✅ Found {len(installed_nodes)} installed nodes")
        client.print_node_summary(installed_nodes)

        # Export installed nodes
        export_path = "/home/ned/ComfyUI-Install/config/custom_nodes/api_installed_nodes.json"
        client.export_node_list(installed_nodes, export_path)

    # Get available nodes
    print("\n" + "="*50)
    available_nodes = client.get_available_nodes()
    if available_nodes:
        print(f"✅ Found {len(available_nodes)} available nodes in registry")

        # Show some statistics
        total_available = len(available_nodes)
        total_installed = sum(1 for node in available_nodes if node.installed)
        print(f"   Available: {total_available}")
        print(f"   Already installed: {total_installed}")
        print(f"   Available for installation: {total_available - total_installed}")

    # Get node mappings
    print("\n" + "="*50)
    mappings = client.get_node_mappings()
    if mappings:
        print("✅ Node mappings retrieved")
        if isinstance(mappings, dict):
            print(f"   Mappings for {len(mappings)} node types")

    # Check for updates
    print("\n" + "="*50)
    updates = client.fetch_updates()
    if updates:
        print("✅ Update check completed")

    # Get snapshots
    print("\n" + "="*50)
    snapshots = client.get_snapshots()
    if snapshots:
        print(f"✅ Found {len(snapshots)} snapshots")

    print("\n🎯 Demo completed!")
    print("\n💡 You can now use this API client to:")
    print("   - Programmatically manage custom nodes")
    print("   - Monitor for changes")
    print("   - Automate backups and updates")
    print("   - Integrate with other tools")

if __name__ == "__main__":
    main()