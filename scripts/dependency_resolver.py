#!/usr/bin/env python3
"""
ComfyUI Dependency Resolver

Automated dependency resolution system for custom nodes.
Tracks missing dependencies, provides installation commands,
and manages resolution status across the custom nodes ecosystem.
"""

import os
import sys
import json
import subprocess
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
import re
import tempfile

@dataclass
class DependencyInfo:
    """Information about a dependency"""
    name: str
    version_spec: str
    source_node: str
    install_command: str
    is_installed: bool = False
    install_priority: int = 1  # 1=high, 2=medium, 3=low
    category: str = "python"  # python, system, other
    last_check: Optional[str] = None

@dataclass
class ResolutionStatus:
    """Status of dependency resolution"""
    total_dependencies: int
    resolved_dependencies: int
    failed_dependencies: int
    pending_dependencies: int
    last_resolution: str
    resolution_history: List[Dict[str, Any]]

class ComfyUIDependencyResolver:
    """Main dependency resolution system"""

    def __init__(self, comfyui_path: str = None):
        self.comfyui_path = Path(comfyui_path) if comfyui_path else Path("/home/ned/ComfyUI-Install/ComfyUI")
        self.custom_nodes_path = self.comfyui_path / "custom_nodes"
        self.venv_path = self.comfyui_path / "venv"

        # Dependency tracking
        self.dependencies: Dict[str, DependencyInfo] = {}
        self.resolution_history = []
        self.installation_queue = []
        self.installing = False

        # Configuration
        self.config = self._load_config()

        # Status tracking
        self.status = ResolutionStatus(
            total_dependencies=0,
            resolved_dependencies=0,
            failed_dependencies=0,
            pending_dependencies=0,
            last_resolution=datetime.now().isoformat(),
            resolution_history=[]
        )

    def _load_config(self) -> Dict[str, Any]:
        """Load resolver configuration"""
        default_config = {
            "auto_install": False,  # Don't install without confirmation
            "batch_size": 5,  # Install up to 5 dependencies at once
            "retry_count": 3,
            "timeout_seconds": 300,  # 5 minutes per installation
            "use_pip_upgrade": True,
            "skip_system_deps": True,  # Skip system-level dependencies
            "safe_packages": [  # Packages considered safe to auto-install
                "torch", "torchvision", "torchaudio",
                "numpy", "pillow", "opencv-python",
                "matplotlib", "scipy", "scikit-image",
                "transformers", "diffusers", "accelerate",
                "safetensors", "omegaconf", "pyyaml"
            ],
            "problematic_packages": [  # Packages that may need special handling
                "cupy", "jax", "jaxlib", "tensorflow",
                "onnx", "onnxruntime", "triton"
            ]
        }

        config_path = Path("/home/ned/ComfyUI-Install/config/dependency_resolver.json")
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                print(f"Warning: Could not load config, using defaults: {e}")

        return default_config

    def save_config(self):
        """Save current configuration"""
        config_path = Path("/home/ned/ComfyUI-Install/config")
        config_path.mkdir(parents=True, exist_ok=True)
        with open(config_path / "dependency_resolver.json", 'w') as f:
            json.dump(self.config, f, indent=2)

    def scan_dependencies(self) -> Dict[str, DependencyInfo]:
        """Scan all custom nodes for dependencies"""
        print(f"🔍 Scanning custom nodes for dependencies...")

        dependencies = {}
        problematic_deps = set()

        if not self.custom_nodes_path.exists():
            print("❌ Custom nodes directory not found")
            return dependencies

        for node_dir in self.custom_nodes_path.iterdir():
            if not node_dir.is_dir() or node_dir.name.startswith('.') or node_dir.name == '__pycache__':
                continue

            print(f"   Scanning: {node_dir.name}")
            node_dependencies = self._scan_node_dependencies(node_dir)

            for dep_info in node_dependencies:
                dep_key = f"{dep_info.name}_{dep_info.version_spec or 'latest'}"
                if dep_key not in dependencies:
                    dependencies[dep_key] = dep_info
                else:
                    # Add source node to existing dependency
                    existing = dependencies[dep_key]
                    if dep_info.source_node not in existing.source_node:
                        existing.source_node = f"{existing.source_node}, {dep_info.source_node}"

        # Check installation status
        self._check_installation_status(dependencies)

        self.dependencies = dependencies
        self._update_status()

        print(f"✅ Found {len(dependencies)} dependencies across custom nodes")
        return dependencies

    def _scan_node_dependencies(self, node_path: Path) -> List[DependencyInfo]:
        """Scan a single node for dependencies"""
        dependencies = []
        node_name = node_path.name

        # Check requirements.txt
        req_file = node_path / "requirements.txt"
        if req_file.exists():
            try:
                with open(req_file, 'r') as f:
                    requirements = f.read().strip().split('\n')

                for req in requirements:
                    req = req.strip()
                    if not req or req.startswith('#'):
                        continue

                    dep_info = self._parse_requirement(req, node_name)
                    if dep_info:
                        dependencies.append(dep_info)
            except Exception as e:
                print(f"     Warning: Could not read {req_file}: {e}")

        # Check install.py for import statements and pip calls
        install_file = node_path / "install.py"
        if install_file.exists():
            try:
                with open(install_file, 'r') as f:
                    content = f.read()

                # Find pip install commands
                pip_pattern = r'pip\s+install\s+([^\n]+)'
                matches = re.findall(pip_pattern, content, re.IGNORECASE)

                for match in matches:
                    # Extract package names from pip install command
                    packages = re.findall(r'([a-zA-Z0-9\-_.]+)', match)
                    for pkg in packages:
                        if len(pkg) > 2 and not pkg.startswith('-'):  # Skip flags
                            dep_info = DependencyInfo(
                                name=pkg.lower(),
                                version_spec="",
                                source_node=node_name,
                                install_command=f"pip install {pkg}",
                                category="python"
                            )
                            dependencies.append(dep_info)

                # Find import statements
                import_pattern = r'import\s+([a-zA-Z_][a-zA-Z0-9_]*)'
                imports = re.findall(import_pattern, content)

                for imp in imports:
                    if len(imp) > 2 and imp not in ['os', 'sys', 'json', 'time', 'pathlib', 'subprocess']:
                        dep_info = DependencyInfo(
                            name=imp,
                            version_spec="",
                            source_node=node_name,
                            install_command=f"pip install {imp}",
                            category="python"
                        )
                        dependencies.append(dep_info)

            except Exception as e:
                print(f"     Warning: Could not parse {install_file}: {e}")

        return dependencies

    def _parse_requirement(self, requirement: str, source_node: str) -> Optional[DependencyInfo]:
        """Parse a requirement string into DependencyInfo"""
        try:
            # Handle version specifiers
            version_specs = [">=", "<=", "==", "!=", ">", "<", "~=", "==="]
            version_spec = ""
            package_name = requirement

            for spec in version_specs:
                if spec in requirement:
                    parts = requirement.split(spec, 1)
                    package_name = parts[0].strip()
                    version_spec = f"{spec}{parts[1].strip()}"
                    break

            # Clean up package name
            package_name = package_name.lower().strip()
            if not package_name or len(package_name) < 2:
                return None

            # Skip comments and invalid entries
            if package_name.startswith('#') or '://' in package_name:
                return None

            # Determine install command
            install_command = f"pip install {requirement}"

            # Determine priority
            priority = 1  # Default medium
            if package_name in self.config.get("safe_packages", []):
                priority = 1  # High priority for safe packages
            elif package_name in self.config.get("problematic_packages", []):
                priority = 3  # Low priority for problematic packages

            return DependencyInfo(
                name=package_name,
                version_spec=version_spec,
                source_node=source_node,
                install_command=install_command,
                install_priority=priority,
                category="python"
            )

        except Exception:
            return None

    def _check_installation_status(self, dependencies: Dict[str, DependencyInfo]):
        """Check which dependencies are installed"""
        venv_python = self.venv_path / "bin" / "python"
        if not venv_python.exists():
            print("⚠️  Virtual environment not found, using system Python")
            venv_python = Path(sys.executable)

        for dep_info in dependencies.values():
            try:
                # Try to import the package
                result = subprocess.run(
                    [str(venv_python), "-c", f"import {dep_info.name}"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                dep_info.is_installed = result.returncode == 0
                dep_info.last_check = datetime.now().isoformat()

                if not dep_info.is_installed:
                    # Try to get version info if available
                    version_result = subprocess.run(
                        [str(venv_python), "-m", "pip", "show", dep_info.name],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if version_result.returncode == 0:
                        # Package exists but import failed - might be version conflict
                        dep_info.is_installed = True
                        print(f"   ⚠️  {dep_info.name} exists but import failed")

            except subprocess.TimeoutExpired:
                print(f"   ⚠️  Timeout checking {dep_info.name}")
                dep_info.last_check = datetime.now().isoformat()
            except Exception as e:
                print(f"   ⚠️  Error checking {dep_info.name}: {e}")
                dep_info.last_check = datetime.now().isoformat()

    def _update_status(self):
        """Update resolution status"""
        total = len(self.dependencies)
        resolved = sum(1 for dep in self.dependencies.values() if dep.is_installed)
        failed = sum(1 for dep in self.dependencies.values()
                    if not dep.is_installed and dep.install_priority == 3)
        pending = total - resolved - failed

        self.status.total_dependencies = total
        self.status.resolved_dependencies = resolved
        self.status.failed_dependencies = failed
        self.status.pending_dependencies = pending
        self.status.last_resolution = datetime.now().isoformat()

    def get_installation_plan(self) -> List[DependencyInfo]:
        """Get prioritized installation plan"""
        # Sort by priority, then by name
        pending_deps = [dep for dep in self.dependencies.values() if not dep.is_installed]
        pending_deps.sort(key=lambda x: (x.install_priority, x.name))

        return pending_deps

    def install_dependencies(self, dependencies: List[DependencyInfo], auto_confirm: bool = False) -> Dict[str, Any]:
        """Install a list of dependencies"""
        if self.installing:
            return {"status": "error", "message": "Installation already in progress"}

        self.installing = True
        results = {
            "success": [],
            "failed": [],
            "skipped": [],
            "start_time": datetime.now().isoformat(),
            "end_time": None
        }

        try:
            print(f"🔧 Installing {len(dependencies)} dependencies...")

            for i, dep in enumerate(dependencies):
                print(f"\n[{i+1}/{len(dependencies)}] Installing {dep.name}...")

                if dep.is_installed:
                    print(f"   ✅ Already installed")
                    results["skipped"].append(dep.name)
                    continue

                # Check if it's a safe package
                is_safe = dep.name in self.config.get("safe_packages", [])
                is_problematic = dep.name in self.config.get("problematic_packages", [])

                if not auto_confirm and not is_safe:
                    print(f"   🤔 Package: {dep.name}")
                    print(f"   Source nodes: {dep.source_node}")
                    print(f"   Install command: {dep.install_command}")
                    if is_problematic:
                        print(f"   ⚠️  This package may be problematic")

                    response = input("   Install this dependency? [Y/n/skip] ").lower()
                    if response == 'n':
                        print(f"   ❌ Skipped by user")
                        results["skipped"].append(dep.name)
                        continue
                    elif response == 'skip':
                        print(f"   ⏭️  Skipped")
                        results["skipped"].append(dep.name)
                        continue
                    elif response not in ['y', '']:
                        print(f"   ❌ Cancelled")
                        break

                # Install the dependency
                install_result = self._install_single_dependency(dep)
                if install_result["success"]:
                    results["success"].append(dep.name)
                    dep.is_installed = True
                else:
                    results["failed"].append({
                        "name": dep.name,
                        "error": install_result["error"]
                    })

                # Small delay between installations
                time.sleep(1)

        except Exception as e:
            print(f"❌ Installation error: {e}")
        finally:
            self.installing = False
            results["end_time"] = datetime.now().isoformat()

        # Record resolution attempt
        resolution_record = {
            "timestamp": datetime.now().isoformat(),
            "total_attempted": len(dependencies),
            "successful": len(results["success"]),
            "failed": len(results["failed"]),
            "skipped": len(results["skipped"]),
            "auto_confirm": auto_confirm
        }
        self.resolution_history.append(resolution_record)

        # Update status
        self._update_status()

        return results

    def _install_single_dependency(self, dep: DependencyInfo) -> Dict[str, Any]:
        """Install a single dependency"""
        venv_python = self.venv_path / "bin" / "python"
        if not venv_python.exists():
            venv_python = Path(sys.executable)

        try:
            # Build install command
            if dep.install_command.startswith('pip install'):
                # Use the specific install command
                cmd = dep.install_command.split()
                if self.config.get("use_pip_upgrade", True):
                    cmd.insert(2, "--upgrade")
            else:
                # Default pip install
                cmd = ["pip", "install", dep.name]
                if self.config.get("use_pip_upgrade", True):
                    cmd.append("--upgrade")

            # Use venv pip if available
            if venv_python != Path(sys.executable):
                venv_pip = venv_python.parent / "pip"
                if venv_pip.exists():
                    cmd[0] = str(venv_pip)

            print(f"   Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.get("timeout_seconds", 300)
            )

            if result.returncode == 0:
                print(f"   ✅ Successfully installed {dep.name}")
                return {"success": True}
            else:
                print(f"   ❌ Failed to install {dep.name}")
                print(f"   Error: {result.stderr[:200]}")
                return {"success": False, "error": result.stderr[:500]}

        except subprocess.TimeoutExpired:
            print(f"   ⏰ Timeout installing {dep.name}")
            return {"success": False, "error": "Installation timeout"}
        except Exception as e:
            print(f"   ❌ Error installing {dep.name}: {e}")
            return {"success": False, "error": str(e)}

    def auto_resolve_dependencies(self, auto_install: bool = False) -> Dict[str, Any]:
        """Automatically resolve all missing dependencies"""
        print("🤖 Starting automatic dependency resolution...")

        # Scan for dependencies
        dependencies = self.scan_dependencies()

        if not dependencies:
            print("✅ No dependencies found")
            return {"status": "success", "message": "No dependencies found"}

        # Get installation plan
        install_plan = self.get_installation_plan()

        if not install_plan:
            print("✅ All dependencies are already installed")
            return {"status": "success", "message": "All dependencies installed"}

        print(f"📋 Installation plan: {len(install_plan)} dependencies to install")

        # Group by priority
        high_priority = [d for d in install_plan if d.install_priority == 1]
        medium_priority = [d for d in install_plan if d.install_priority == 2]
        low_priority = [d for d in install_plan if d.install_priority == 3]

        print(f"   High priority: {len(high_priority)}")
        print(f"   Medium priority: {len(medium_priority)}")
        print(f"   Low priority: {len(low_priority)}")

        results = {}

        # Install high priority (safe packages)
        if high_priority and (auto_install or self.config.get("auto_install", False)):
            print("\n🔧 Installing high priority (safe) dependencies...")
            results["high_priority"] = self.install_dependencies(high_priority, auto_confirm=True)

        # Install medium priority with confirmation
        if medium_priority:
            print(f"\n🔧 Installing medium priority dependencies ({len(medium_priority)} packages)...")
            response = input("Install medium priority dependencies? [Y/n] ").lower()
            if response in ['y', '']:
                results["medium_priority"] = self.install_dependencies(medium_priority, auto_confirm=False)

        # Install low priority with explicit confirmation
        if low_priority:
            print(f"\n⚠️  Installing low priority (potentially problematic) dependencies...")
            response = input("Install low priority dependencies? [y/N] ").lower()
            if response == 'y':
                results["low_priority"] = self.install_dependencies(low_priority, auto_confirm=False)

        # Summary
        total_installed = sum(len(r.get("success", [])) for r in results.values())
        total_failed = sum(len(r.get("failed", [])) for r in results.values())

        print(f"\n📊 Resolution Summary:")
        print(f"   Total dependencies: {len(dependencies)}")
        print(f"   Already installed: {self.status.resolved_dependencies}")
        print(f"   Newly installed: {total_installed}")
        print(f"   Failed: {total_failed}")
        print(f"   Remaining: {len(install_plan) - total_installed - total_failed}")

        return {
            "status": "completed",
            "results": results,
            "summary": {
                "total_dependencies": len(dependencies),
                "resolved": self.status.resolved_dependencies,
                "newly_installed": total_installed,
                "failed": total_failed,
                "remaining": len(install_plan) - total_installed - total_failed
            }
        }

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive dependency report"""
        # Group dependencies by status
        installed_deps = [dep for dep in self.dependencies.values() if dep.is_installed]
        missing_deps = [dep for dep in self.dependencies.values() if not dep.is_installed]

        # Group by source node
        by_source = {}
        for dep in self.dependencies.values():
            for source in dep.source_node.split(", "):
                if source not in by_source:
                    by_source[source] = []
                by_source[source].append(dep)

        # Group by category
        by_category = {}
        for dep in self.dependencies.values():
            category = dep.category
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(dep)

        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_dependencies": len(self.dependencies),
                "installed": len(installed_deps),
                "missing": len(missing_deps),
                "installation_rate": len(installed_deps) / max(len(self.dependencies), 1) * 100
            },
            "by_source": {source: len(deps) for source, deps in by_source.items()},
            "by_category": {cat: len(deps) for cat, deps in by_category.items()},
            "priority_breakdown": {
                "high": len([d for d in missing_deps if d.install_priority == 1]),
                "medium": len([d for d in missing_deps if d.install_priority == 2]),
                "low": len([d for d in missing_deps if d.install_priority == 3])
            },
            "critical_nodes": self._get_critical_nodes(),
            "safe_to_auto_install": [d.name for d in missing_deps if d.name in self.config.get("safe_packages", [])],
            "problematic_packages": [d.name for d in missing_deps if d.name in self.config.get("problematic_packages", [])],
            "installation_history": self.resolution_history[-10:]  # Last 10 attempts
        }

    def _get_critical_nodes(self) -> List[Dict[str, Any]]:
        """Get nodes with critical dependency issues"""
        critical_nodes = []

        for dep in self.dependencies.values():
            if not dep.is_installed and dep.install_priority == 1:
                # This is a high-priority missing dependency
                for source in dep.source_node.split(", "):
                    critical_nodes.append({
                        "node": source,
                        "missing_dependency": dep.name,
                        "priority": "high",
                        "install_command": dep.install_command
                    })

        return critical_nodes

    def export_dependency_data(self, output_path: str):
        """Export dependency data to JSON file"""
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "config": self.config,
            "dependencies": {key: asdict(dep) for key, dep in self.dependencies.items()},
            "status": asdict(self.status),
            "report": self.generate_report()
        }

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"✅ Dependency data exported to: {output_path}")

def main():
    """Main dependency resolver script"""
    print("🔧 ComfyUI Dependency Resolver")
    print("=" * 50)

    resolver = ComfyUIDependencyResolver()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "scan":
            # Scan dependencies
            dependencies = resolver.scan_dependencies()
            print(f"\n📊 Found {len(dependencies)} dependencies")

            # Show summary
            installed = sum(1 for dep in dependencies.values() if dep.is_installed)
            missing = len(dependencies) - installed
            print(f"   Installed: {installed}")
            print(f"   Missing: {missing}")

            if missing > 0:
                print(f"\n🔧 Missing dependencies:")
                for dep in dependencies.values():
                    if not dep.is_installed:
                        priority_icon = "🔴" if dep.install_priority == 1 else "🟡" if dep.install_priority == 2 else "🟢"
                        print(f"   {priority_icon} {dep.name} (from {dep.source_node})")

        elif command == "install":
            # Auto-resolve dependencies
            results = resolver.auto_resolve_dependencies()
            if "summary" in results:
                summary = results["summary"]
                print(f"\n📊 Summary: {summary['newly_installed']} installed, {summary['failed']} failed")

        elif command == "plan":
            # Show installation plan
            dependencies = resolver.scan_dependencies()
            install_plan = resolver.get_installation_plan()

            print(f"\n📋 Installation Plan ({len(install_plan)} dependencies):")
            for i, dep in enumerate(install_plan):
                priority_icon = "🔴" if dep.install_priority == 1 else "🟡" if dep.install_priority == 2 else "🟢"
                print(f"   {i+1}. {priority_icon} {dep.name}")
                print(f"      From: {dep.source_node}")
                print(f"      Command: {dep.install_command}")

        elif command == "report":
            # Generate detailed report
            dependencies = resolver.scan_dependencies()
            report = resolver.generate_report()

            print(f"\n📊 Dependency Report:")
            print(f"   Total Dependencies: {report['summary']['total_dependencies']}")
            print(f"   Installation Rate: {report['summary']['installation_rate']:.1f}%")
            print(f"   Critical Nodes: {len(report['critical_nodes'])}")

            if report['critical_nodes']:
                print(f"\n🚨 Critical Nodes:")
                for node in report['critical_nodes']:
                    print(f"   {node['node']}: missing {node['missing_dependency']}")

            # Export report
            export_path = f"/home/ned/ComfyUI-Install/config/dependencies/dependency_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            resolver.export_dependency_data(export_path)

        else:
            print("Usage: python3 scripts/dependency_resolver.py [scan|install|plan|report]")
    else:
        print("Usage: python3 scripts/dependency_resolver.py [scan|install|plan|report]")

if __name__ == "__main__":
    main()