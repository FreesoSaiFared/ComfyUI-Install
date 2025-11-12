#!/usr/bin/env python3
"""
ComfyUI-Manager Interface System

This module provides comprehensive monitoring and interface capabilities for ComfyUI-Manager,
including directory monitoring, API integration, and configuration management.
"""

import os
import json
import time
import asyncio
import logging
import requests
import yaml
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import threading
import subprocess
import git
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configuration
@dataclass
class ComfyUIManagerConfig:
    """Configuration for ComfyUI-Manager interface"""
    comfyui_path: str = "/home/ned/ComfyUI-Install/ComfyUI"
    custom_nodes_path: str = "/home/ned/ComfyUI-Install/ComfyUI/custom_nodes"
    config_path: str = "/home/ned/Projects/AI_ML/SwarmUI/dlbackend/ComfyUI/user/default/ComfyUI-Manager/config.ini"
    server_host: str = "localhost"
    server_port: int = 8188
    api_timeout: int = 30
    monitoring_interval: int = 60
    enable_file_watcher: bool = True
    log_level: str = "INFO"

@dataclass
class CustomNodeInfo:
    """Information about a custom node"""
    name: str
    path: str
    version: str = "unknown"
    status: str = "installed"
    git_url: Optional[str] = None
    last_updated: Optional[str] = None
    has_requirements: bool = False
    has_install_script: bool = False
    node_count: int = 0
    file_count: int = 0
    size_mb: float = 0.0

class CustomNodesEventHandler(FileSystemEventHandler):
    """File system event handler for custom nodes directory"""

    def __init__(self, manager_interface):
        self.manager_interface = manager_interface
        self.logger = logging.getLogger(__name__)

    def on_created(self, event):
        if not event.is_directory:
            return

        self.logger.info(f"New directory detected: {event.src_path}")
        # Delay processing to allow for git clone completion
        threading.Timer(5.0, self._process_new_node, args=[event.src_path]).start()

    def on_deleted(self, event):
        if not event.is_directory:
            return

        self.logger.info(f"Directory removed: {event.src_path}")
        self.manager_interface.remove_node_from_cache(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return

        # Check for key file modifications
        path = Path(event.src_path)
        if path.name in ['requirements.txt', 'install.py', 'pyproject.toml']:
            self.logger.info(f"Configuration file modified: {event.src_path}")
            node_dir = path.parent
            self.manager_interface.update_node_cache(node_dir)

    def _process_new_node(self, node_path: str):
        """Process a newly added node directory"""
        try:
            self.manager_interface.scan_node_directory(node_path)
        except Exception as e:
            self.logger.error(f"Error processing new node {node_path}: {e}")

class ComfyUIManagerInterface:
    """Main interface for ComfyUI-Manager monitoring and control"""

    def __init__(self, config: Optional[ComfyUIManagerConfig] = None):
        self.config = config or ComfyUIManagerConfig()
        self.logger = self._setup_logging()

        # Node cache
        self.nodes_cache: Dict[str, CustomNodeInfo] = {}
        self.last_cache_update = None

        # Monitoring
        self.observer = None
        self.is_monitoring = False

        # API endpoints (discovered from ComfyUI-Manager source)
        self.api_endpoints = {
            'installed': '/customnode/installed',
            'getlist': '/customnode/getlist',
            'getmappings': '/customnode/getmappings',
            'fetch_updates': '/customnode/fetch_updates',
            'alternatives': '/customnode/alternatives',
            'snapshot_list': '/snapshot/getlist',
            'external_models': '/externalmodel/getlist',
            'manager_queue': '/manager/queue/update_all'
        }

        self.logger.info("ComfyUI-Manager Interface initialized")

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)

    def get_api_url(self, endpoint: str) -> str:
        """Construct API URL for endpoint"""
        return f"http://{self.config.server_host}:{self.config.server_port}{endpoint}"

    def make_api_request(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None) -> Optional[Dict]:
        """Make request to ComfyUI-Manager API"""
        try:
            url = self.get_api_url(self.api_endpoints.get(endpoint, endpoint))
            self.logger.debug(f"Making {method} request to {url}")

            response = requests.request(
                method=method,
                url=url,
                json=data,
                timeout=self.config.api_timeout
            )

            if response.status_code == 200:
                return response.json()
            else:
                self.logger.warning(f"API request failed: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            self.logger.warning(f"API request error: {e}")
            return None

    def scan_node_directory(self, node_path: str) -> Optional[CustomNodeInfo]:
        """Scan a single node directory and extract information"""
        try:
            path = Path(node_path)
            if not path.exists() or not path.is_dir():
                return None

            node_name = path.name

            # Check if it's a git repository
            git_info = self._extract_git_info(path)

            # Check for requirements and install scripts
            has_requirements = (path / 'requirements.txt').exists()
            has_install_script = (path / 'install.py').exists()

            # Count Python files (potential nodes)
            py_files = list(path.rglob('*.py'))
            node_count = len([f for f in py_files if self._is_likely_node_file(f)])

            # Calculate directory size
            size_bytes = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
            size_mb = size_bytes / (1024 * 1024)

            node_info = CustomNodeInfo(
                name=node_name,
                path=str(path),
                version=git_info.get('version', 'unknown'),
                status='installed',
                git_url=git_info.get('url'),
                last_updated=git_info.get('last_updated'),
                has_requirements=has_requirements,
                has_install_script=has_install_script,
                node_count=node_count,
                file_count=len(py_files),
                size_mb=round(size_mb, 2)
            )

            # Update cache
            self.nodes_cache[node_name] = node_info
            self.logger.info(f"Scanned node: {node_name} ({node_count} nodes, {size_mb:.2f}MB)")

            return node_info

        except Exception as e:
            self.logger.error(f"Error scanning node directory {node_path}: {e}")
            return None

    def _extract_git_info(self, path: Path) -> Dict[str, str]:
        """Extract git information from a directory"""
        try:
            repo = git.Repo(path)

            # Get remote URL
            try:
                origin = repo.remote('origin')
                git_url = origin.url
            except:
                git_url = None

            # Get last commit date
            try:
                last_commit = repo.head.commit
                last_updated = last_commit.committed_datetime.isoformat()
            except:
                last_updated = None

            # Get version/commit hash
            try:
                version = repo.head.commit.hexsha[:8]
            except:
                version = "unknown"

            return {
                'url': git_url,
                'version': version,
                'last_updated': last_updated
            }

        except:
            return {}

    def _is_likely_node_file(self, file_path: Path) -> bool:
        """Check if a Python file is likely a node definition"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                return 'NODE_CLASS_MAPPINGS' in content or 'class ' in content
        except:
            return False

    def scan_all_nodes(self) -> Dict[str, CustomNodeInfo]:
        """Scan all custom nodes directories"""
        self.logger.info("Starting comprehensive scan of custom nodes...")

        nodes = {}
        custom_nodes_path = Path(self.config.custom_nodes_path)

        if not custom_nodes_path.exists():
            self.logger.error(f"Custom nodes path not found: {custom_nodes_path}")
            return nodes

        # Scan each directory in custom_nodes
        for item in custom_nodes_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                node_info = self.scan_node_directory(str(item))
                if node_info:
                    nodes[node_info.name] = node_info

        self.nodes_cache = nodes
        self.last_cache_update = datetime.now()

        self.logger.info(f"Scan complete: {len(nodes)} nodes found")
        return nodes

    def get_node_info(self, node_name: str) -> Optional[CustomNodeInfo]:
        """Get information about a specific node"""
        if node_name in self.nodes_cache:
            return self.nodes_cache[node_name]

        # Try to scan the specific node
        node_path = Path(self.config.custom_nodes_path) / node_name
        return self.scan_node_directory(str(node_path))

    def get_installed_nodes_from_api(self) -> Optional[List[Dict]]:
        """Get list of installed nodes from ComfyUI-Manager API"""
        return self.make_api_request('installed')

    def get_available_nodes_from_api(self) -> Optional[List[Dict]]:
        """Get list of available nodes from ComfyUI-Manager API"""
        return self.make_api_request('getlist')

    def start_monitoring(self):
        """Start file system monitoring"""
        if self.is_monitoring:
            self.logger.warning("Monitoring is already active")
            return

        try:
            self.observer = Observer()
            event_handler = CustomNodesEventHandler(self)

            self.observer.schedule(
                event_handler,
                self.config.custom_nodes_path,
                recursive=False
            )

            self.observer.start()
            self.is_monitoring = True

            self.logger.info(f"Started monitoring {self.config.custom_nodes_path}")

        except Exception as e:
            self.logger.error(f"Failed to start monitoring: {e}")

    def stop_monitoring(self):
        """Stop file system monitoring"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            self.is_monitoring = False
            self.logger.info("Stopped monitoring")

    def update_node_cache(self, node_path: str):
        """Update cache for a specific node"""
        self.scan_node_directory(node_path)

    def remove_node_from_cache(self, node_path: str):
        """Remove node from cache"""
        node_name = Path(node_path).name
        if node_name in self.nodes_cache:
            del self.nodes_cache[node_name]
            self.logger.info(f"Removed {node_name} from cache")

    def get_node_status_summary(self) -> Dict[str, Any]:
        """Get summary of all nodes"""
        if not self.nodes_cache:
            self.scan_all_nodes()

        total_nodes = len(self.nodes_cache)
        total_size = sum(node.size_mb for node in self.nodes_cache.values())
        git_nodes = sum(1 for node in self.nodes_cache.values() if node.git_url)
        nodes_with_requirements = sum(1 for node in self.nodes_cache.values() if node.has_requirements)

        return {
            'total_nodes': total_nodes,
            'total_size_mb': round(total_size, 2),
            'git_managed_nodes': git_nodes,
            'nodes_with_requirements': nodes_with_requirements,
            'last_updated': self.last_cache_update.isoformat() if self.last_cache_update else None,
            'monitoring_active': self.is_monitoring
        }

    def export_node_inventory(self, export_path: str):
        """Export node inventory to JSON and YAML files"""
        inventory = {
            'export_timestamp': datetime.now().isoformat(),
            'comfyui_path': self.config.comfyui_path,
            'custom_nodes_path': self.config.custom_nodes_path,
            'nodes': {name: asdict(node) for name, node in self.nodes_cache.items()},
            'summary': self.get_node_status_summary()
        }

        # Export as JSON
        json_path = Path(export_path) / 'custom_nodes_inventory.json'
        with open(json_path, 'w') as f:
            json.dump(inventory, f, indent=2)

        # Export as YAML
        yaml_path = Path(export_path) / 'custom_nodes_inventory.yaml'
        with open(yaml_path, 'w') as f:
            yaml.dump(inventory, f, default_flow_style=False)

        self.logger.info(f"Inventory exported to {export_path}")

    def __enter__(self):
        """Context manager entry"""
        self.start_monitoring()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop_monitoring()

def main():
    """Main function for testing the interface"""
    config = ComfyUIManagerConfig()

    with ComfyUIManagerInterface(config) as manager:
        # Initial scan
        print("Scanning custom nodes...")
        nodes = manager.scan_all_nodes()

        # Display summary
        summary = manager.get_node_status_summary()
        print(f"\nNode Summary:")
        print(f"  Total nodes: {summary['total_nodes']}")
        print(f"  Total size: {summary['total_size_mb']} MB")
        print(f"  Git managed: {summary['git_managed_nodes']}")
        print(f"  With requirements: {summary['nodes_with_requirements']}")

        # Display individual nodes
        print(f"\nInstalled Nodes:")
        for name, node in nodes.items():
            status_icon = "📦" if node.git_url else "📁"
            req_icon = "🔧" if node.has_requirements else ""
            print(f"  {status_icon} {name} ({node.node_count} nodes, {node.size_mb}MB) {req_icon}")

        # Test API connectivity
        print(f"\nTesting API connectivity...")
        installed = manager.get_installed_nodes_from_api()
        if installed:
            print(f"API reports {len(installed)} installed nodes")
        else:
            print("API connection failed or ComfyUI not running")

        # Export inventory
        export_dir = Path("/home/ned/ComfyUI-Install/config/custom_nodes")
        export_dir.mkdir(parents=True, exist_ok=True)
        manager.export_node_inventory(str(export_dir))

        print(f"\nMonitoring active... Press Ctrl+C to stop")
        try:
            while True:
                time.sleep(5)
        except KeyboardInterrupt:
            print("\nStopping monitoring...")

if __name__ == "__main__":
    main()