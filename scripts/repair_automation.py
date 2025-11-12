#!/usr/bin/env python3
"""
ComfyUI Repair Automation System

Automated repair and maintenance system for ComfyUI installations.
Detects common issues, provides repair suggestions, and can execute
automated fixes with user confirmation.
"""

import os
import sys
import json
import subprocess
import shutil
import time
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import re

# Import our other modules
try:
    from health_monitor import ComfyUIHealthMonitor, HealthStatus
    from dependency_resolver import ComfyUIDependencyResolver, DependencyInfo
except ImportError:
    print("Warning: Could not import health monitor and dependency resolver")

@dataclass
class RepairAction:
    """Represents a repair action"""
    name: str
    description: str
    severity: str  # "low", "medium", "high", "critical"
    category: str  # "service", "dependencies", "permissions", "files", "config"
    command: str
    auto_safe: bool  # Can be run automatically
    requires_restart: bool
    estimated_time: int  # seconds
    success_criteria: List[str]

@dataclass
class RepairResult:
    """Result of a repair action"""
    action_name: str
    success: bool
    output: str
    error: Optional[str]
    timestamp: str
    changes_made: List[str]

class ComfyUIRepairAutomation:
    """Main repair automation system"""

    def __init__(self, comfyui_path: str = None):
        self.comfyui_path = Path(comfyui_path) if comfyui_path else Path("/home/ned/ComfyUI-Install/ComfyUI")
        self.custom_nodes_path = self.comfyui_path / "custom_nodes"
        self.config_path = Path("/home/ned/ComfyUI-Install/config/repair_automation.json")

        # Initialize other systems
        self.health_monitor = ComfyUIHealthMonitor()
        self.dependency_resolver = ComfyUIDependencyResolver(str(self.comfyui_path))

        # Repair history
        self.repair_history = []
        self.pending_repairs = []

        # Configuration
        self.config = self._load_config()

        # Available repair actions
        self.repair_actions = self._define_repair_actions()

    def _load_config(self) -> Dict[str, Any]:
        """Load repair automation configuration"""
        default_config = {
            "auto_repair": False,  # Don't repair without confirmation
            "dry_run_first": True,  # Always show what will be done
            "backup_before_repair": True,
            "max_concurrent_repairs": 3,
            "repair_timeout": 300,  # 5 minutes per repair
            "safe_repair_categories": ["service", "dependencies"],
            "log_repairs": True,
            "retention_days": 30
        }

        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                print(f"Warning: Could not load config, using defaults: {e}")

        return default_config

    def _define_repair_actions(self) -> Dict[str, RepairAction]:
        """Define available repair actions"""
        return {
            "restart_comfyui": RepairAction(
                name="restart_comfyui",
                description="Restart ComfyUI service",
                severity="medium",
                category="service",
                command="systemctl --user restart comfyui || pkill -f ComfyUI/main.py",
                auto_safe=True,
                requires_restart=False,
                estimated_time=30,
                success_criteria=["ComfyUI process running", "API accessible"]
            ),

            "fix_permissions": RepairAction(
                name="fix_permissions",
                description="Fix file permissions for ComfyUI installation",
                severity="medium",
                category="permissions",
                command=f"chmod -R 755 {self.comfyui_path} && chown -R $USER:$USER {self.comfyui_path}",
                auto_safe=True,
                requires_restart=False,
                estimated_time=60,
                success_criteria=["Can write to ComfyUI directory", "Scripts executable"]
            ),

            "reinstall_missing_deps": RepairAction(
                name="reinstall_missing_deps",
                description="Reinstall all missing Python dependencies",
                severity="high",
                category="dependencies",
                command="cd {comfyui_path} && venv/bin/pip install -r requirements.txt",
                auto_safe=False,
                requires_restart=True,
                estimated_time=300,
                success_criteria=["All requirements.txt packages installed"]
            ),

            "clear_python_cache": RepairAction(
                name="clear_python_cache",
                description="Clear Python cache files",
                severity="low",
                category="files",
                command=f"find {self.comfyui_path} -name '*.pyc' -delete && find {self.comfyui_path} -name '__pycache__' -type d -exec rm -rf {{}} + 2>/dev/null || true",
                auto_safe=True,
                requires_restart=False,
                estimated_time=30,
                success_criteria=["No .pyc files found", "No __pycache__ directories"]
            ),

            "fix_node_dependencies": RepairAction(
                name="fix_node_dependencies",
                description="Install missing dependencies for all custom nodes",
                severity="high",
                category="dependencies",
                command="python3 {script_dir}/dependency_resolver.py install",
                auto_safe=False,
                requires_restart=True,
                estimated_time=600,
                success_criteria=["All custom node dependencies installed"]
            ),

            "reset_config_files": RepairAction(
                name="reset_config_files",
                description="Reset configuration files to defaults",
                severity="critical",
                category="config",
                command=f"cd {self.comfyui_path} && git checkout -- extras/extra_model_paths.yaml extras/example_extra_model_paths.yaml",
                auto_safe=False,
                requires_restart=True,
                estimated_time=60,
                success_criteria=["Config files restored to defaults"]
            ),

            "repair_git_repos": RepairAction(
                name="repair_git_repos",
                description="Repair corrupted Git repositories in custom nodes",
                severity="medium",
                category="files",
                command=f"find {self.custom_nodes_path} -name '.git' -type d -exec git -C {{}}/.. fsck --full 2>/dev/null \\;",
                auto_safe=True,
                requires_restart=False,
                estimated_time=120,
                success_criteria=["Git repositories repaired"]
            ),

            "cleanup_temp_files": RepairAction(
                name="cleanup_temp_files",
                description="Clean up temporary files and logs",
                severity="low",
                category="files",
                command=f"find {self.comfyui_path} -name '*.tmp' -delete -o -name '*.log' -size +10M -delete 2>/dev/null || true",
                auto_safe=True,
                requires_restart=False,
                estimated_time=30,
                success_criteria=["Temporary files cleaned", "Large log files rotated"]
            ),

            "fix_virtual_env": RepairAction(
                name="fix_virtual_env",
                description="Repair or recreate virtual environment",
                severity="critical",
                category="dependencies",
                command=f"cd {self.comfyui_path} && rm -rf venv && python3 -m venv venv && venv/bin/pip install --upgrade pip && venv/bin/pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121",
                auto_safe=False,
                requires_restart=True,
                estimated_time=900,
                success_criteria=["Virtual environment recreated", "PyTorch installed"]
            ),

            "restore_from_backup": RepairAction(
                name="restore_from_backup",
                description="Restore ComfyUI from latest backup",
                severity="critical",
                category="files",
                command="echo 'Manual restore required - check backup directory'",
                auto_safe=False,
                requires_restart=True,
                estimated_time=600,
                success_criteria=["Files restored from backup"]
            )
        }

    def diagnose_issues(self) -> List[Tuple[str, RepairAction]]:
        """Diagnose issues and recommend repair actions"""
        print("🔍 Diagnosing ComfyUI issues...")

        # Run health check
        health_results = self.health_monitor.run_health_check()

        # Scan dependencies
        dependencies = self.dependency_resolver.scan_dependencies()

        recommended_repairs = []

        # Analyze health results and recommend repairs
        for component, status in health_results.items():
            if status.status == "CRITICAL":
                if component == "comfyui_service":
                    recommended_repairs.append((f"Service down: {status.message}", self.repair_actions["restart_comfyui"]))
                elif component == "custom_nodes":
                    recommended_repairs.append((f"Custom nodes issues: {status.message}", self.repair_actions["fix_node_dependencies"]))
                elif component == "system_resources":
                    if "disk" in status.message.lower():
                        recommended_repairs.append((f"Disk space issues: {status.message}", self.repair_actions["cleanup_temp_files"]))
                elif component == "api_connectivity":
                    recommended_repairs.append((f"API connectivity issues: {status.message}", self.repair_actions["restart_comfyui"]))

            elif status.status == "WARNING":
                if "permission" in status.message.lower():
                    recommended_repairs.append((f"Permission issues: {status.message}", self.repair_actions["fix_permissions"]))

        # Check for dependency issues
        missing_deps = [dep for dep in dependencies.values() if not dep.is_installed]
        if len(missing_deps) > len(dependencies) * 0.3:  # More than 30% missing
            recommended_repairs.append((
                f"Many missing dependencies ({len(missing_deps)} of {len(dependencies)})",
                self.repair_actions["reinstall_missing_deps"]
            ))

        # Check for common file system issues
        self._check_filesystem_issues(recommended_repairs)

        # Remove duplicates and prioritize
        unique_repairs = {}
        for issue, action in recommended_repairs:
            if action.name not in unique_repairs:
                unique_repairs[action.name] = (issue, action)

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_repairs = sorted(
            unique_repairs.values(),
            key=lambda x: severity_order.get(x[1].severity, 4)
        )

        print(f"🔧 Found {len(sorted_repairs)} recommended repairs")
        return sorted_repairs

    def _check_filesystem_issues(self, repairs: List[Tuple[str, RepairAction]]):
        """Check for common filesystem issues"""
        # Check disk space
        try:
            result = subprocess.run(['df', str(self.comfyui_path.parent)], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    if len(parts) >= 5:
                        total = int(parts[1])
                        used = int(parts[2])
                        usage_percent = (used / total) * 100
                        if usage_percent > 90:
                            repairs.append((
                                f"Low disk space: {usage_percent:.1f}% used",
                                self.repair_actions["cleanup_temp_files"]
                            ))
        except:
            pass

        # Check for broken symlinks
        try:
            result = subprocess.run(
                ['find', str(self.comfyui_path), '-type', 'l', '!', '-exec', 'test', '-e', '{}', ';'],
                capture_output=True, text=True
            )
            if result.stdout.strip():
                repairs.append((
                    "Broken symlinks found",
                    self.repair_actions["fix_permissions"]
                ))
        except:
            pass

    def execute_repair(self, action: RepairAction, dry_run: bool = True) -> RepairResult:
        """Execute a repair action"""
        print(f"🔧 Executing repair: {action.name}")
        print(f"   Description: {action.description}")
        print(f"   Severity: {action.severity}")
        print(f"   Category: {action.category}")
        print(f"   Estimated time: {action.estimated_time}s")

        if dry_run:
            print("   🧪 DRY RUN - No changes will be made")
            return RepairResult(
                action_name=action.name,
                success=True,
                output="DRY RUN - No changes made",
                error=None,
                timestamp=datetime.now().isoformat(),
                changes_made=[]
            )

        # Create backup if configured
        if self.config.get("backup_before_repair", True):
            self._create_backup(action.name)

        # Execute the repair command
        start_time = time.time()
        try:
            # Format command with variables
            command = action.command.format(
                comfyui_path=str(self.comfyui_path),
                script_dir=str(Path(__file__).parent)
            )

            print(f"   Running: {command}")
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.config.get("repair_timeout", 300)
            )

            execution_time = time.time() - start_time

            # Determine success
            success = result.returncode == 0
            output = result.stdout
            error = result.stderr if result.stderr else None

            # Check success criteria
            if success and action.success_criteria:
                success = self._verify_success_criteria(action, output, error)

            changes_made = self._identify_changes(action, output, error)

            repair_result = RepairResult(
                action_name=action.name,
                success=success,
                output=output[:1000] + "..." if len(output) > 1000 else output,
                error=error[:500] + "..." if error and len(error) > 500 else error,
                timestamp=datetime.now().isoformat(),
                changes_made=changes_made
            )

            # Record repair
            self.repair_history.append(asdict(repair_result))

            print(f"   {'✅ Success' if success else '❌ Failed'} in {execution_time:.1f}s")
            if changes_made:
                print(f"   Changes made: {', '.join(changes_made)}")

            return repair_result

        except subprocess.TimeoutExpired:
            error_msg = f"Repair timed out after {self.config.get('repair_timeout', 300)} seconds"
            print(f"   ⏰ {error_msg}")
            return RepairResult(
                action_name=action.name,
                success=False,
                output="",
                error=error_msg,
                timestamp=datetime.now().isoformat(),
                changes_made=[]
            )

        except Exception as e:
            error_msg = f"Repair failed: {str(e)}"
            print(f"   ❌ {error_msg}")
            return RepairResult(
                action_name=action.name,
                success=False,
                output="",
                error=error_msg,
                timestamp=datetime.now().isoformat(),
                changes_made=[]
            )

    def _create_backup(self, action_name: str):
        """Create backup before repair"""
        backup_dir = Path("/home/ned/ComfyUI-Install/backups")
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"pre_{action_name}_{timestamp}"

        try:
            # Create a simple backup of critical files
            critical_files = [
                self.comfyui_path / "main.py",
                self.comfyui_path / "requirements.txt",
                self.comfyui_path / "nodes.py",
                self.custom_nodes_path
            ]

            backup_path = backup_dir / backup_name
            backup_path.mkdir(parents=True, exist_ok=True)

            for file_path in critical_files:
                if file_path.exists():
                    dest = backup_path / file_path.name
                    if file_path.is_dir():
                        shutil.copytree(file_path, dest, symlinks=True)
                    else:
                        shutil.copy2(file_path, dest)

            print(f"   💾 Backup created: {backup_path}")

        except Exception as e:
            print(f"   ⚠️  Backup failed: {e}")

    def _verify_success_criteria(self, action: RepairAction, output: str, error: str) -> bool:
        """Verify if success criteria were met"""
        if not action.success_criteria:
            return True

        # This is a simplified check - in reality, you'd want more sophisticated validation
        for criterion in action.success_criteria:
            if "running" in criterion.lower():
                # Check if ComfyUI is running
                try:
                    result = subprocess.run(['pgrep', '-f', 'ComfyUI/main.py'], capture_output=True)
                    if result.returncode != 0:
                        return False
                except:
                    return False

            elif "accessible" in criterion.lower():
                # Check API accessibility
                try:
                    import urllib.request
                    response = urllib.request.urlopen('http://localhost:8188/prompt', timeout=5)
                    if response.status != 200:
                        return False
                except:
                    return False

        return True

    def _identify_changes(self, action: RepairAction, output: str, error: str) -> List[str]:
        """Identify changes made by the repair action"""
        changes = []

        # Simple pattern-based change detection
        if "installed" in output.lower():
            changes.append("Packages installed")
        if "removed" in output.lower():
            changes.append("Files removed")
        if "restarted" in output.lower():
            changes.append("Service restarted")
        if "permissions" in output.lower():
            changes.append("Permissions updated")

        return changes

    def interactive_repair_session(self):
        """Run interactive repair session"""
        print("🔧 ComfyUI Repair Automation Session")
        print("=" * 50)

        # Diagnose issues
        repairs_needed = self.diagnose_issues()

        if not repairs_needed:
            print("✅ No issues detected that require repair")
            return

        print(f"\n📋 Recommended Repairs ({len(repairs_needed)}):")
        for i, (issue, action) in enumerate(repairs_needed):
            severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}[action.severity]
            print(f"\n[{i+1}] {severity_icon} {action.name}")
            print(f"     Issue: {issue}")
            print(f"     Description: {action.description}")
            print(f"     Category: {action.category}")
            print(f"     Auto-safe: {'Yes' if action.auto_safe else 'No'}")
            print(f"     Restart required: {'Yes' if action.requires_restart else 'No'}")

        # Ask user to select repairs
        print(f"\n⚙️  Repair Options:")
        print("   [all] Execute all recommended repairs")
        print("   [select] Select specific repairs")
        print("   [dry-run] Show what would be done")
        print("   [cancel] Cancel repair session")

        choice = input("\nSelect option: ").lower()

        if choice == "cancel":
            print("❌ Repair session cancelled")
            return

        elif choice == "dry-run":
            print("\n🧪 DRY RUN MODE - Showing what would be done:")
            for issue, action in repairs_needed:
                print(f"\n🔧 {action.name}")
                result = self.execute_repair(action, dry_run=True)
                if result.success:
                    print(f"   ✅ Would succeed")
                else:
                    print(f"   ❌ Would fail: {result.error}")
            return

        elif choice == "all":
            selected_actions = [action for issue, action in repairs_needed]
        elif choice == "select":
            selected_actions = []
            print(f"\nSelect repairs to execute (1-{len(repairs_needed)}), comma-separated:")
            selection = input("Repair numbers: ")
            try:
                indices = [int(x.strip()) - 1 for x in selection.split(',')]
                for idx in indices:
                    if 0 <= idx < len(repairs_needed):
                        selected_actions.append(repairs_needed[idx][1])
            except ValueError:
                print("❌ Invalid selection")
                return
        else:
            print("❌ Invalid option")
            return

        # Execute selected repairs
        print(f"\n🔧 Executing {len(selected_actions)} repairs...")

        successful_repairs = []
        failed_repairs = []

        for i, action in enumerate(selected_actions):
            print(f"\n[{i+1}/{len(selected_actions)}] Repairing: {action.name}")

            # Ask for confirmation unless auto-safe
            if not action.auto_safe:
                confirm = input(f"Execute {action.name}? [y/N] ").lower()
                if confirm != 'y':
                    print("   ⏭️  Skipped")
                    continue

            # Execute repair
            dry_run = self.config.get("dry_run_first", True)
            if i == 0 and dry_run:
                print("   🧪 First repair in dry-run mode")
                result = self.execute_repair(action, dry_run=True)
                confirm = input("   Proceed with actual repair? [y/N] ").lower()
                if confirm != 'y':
                    print("   ❌ Cancelled")
                    continue
                else:
                    result = self.execute_repair(action, dry_run=False)
            else:
                result = self.execute_repair(action, dry_run=False)

            if result.success:
                successful_repairs.append(action.name)
                print(f"   ✅ {action.name} completed successfully")
            else:
                failed_repairs.append(action.name)
                print(f"   ❌ {action.name} failed: {result.error}")

            # Check if restart is needed
            if result.success and action.requires_restart:
                print("   ⚠️  Restart required for changes to take effect")
                restart = input("   Restart ComfyUI now? [y/N] ").lower()
                if restart == 'y':
                    restart_action = self.repair_actions["restart_comfyui"]
                    restart_result = self.execute_repair(restart_action, dry_run=False)
                    if restart_result.success:
                        print("   ✅ ComfyUI restarted")

        # Summary
        print(f"\n📊 Repair Session Summary:")
        print(f"   Total repairs attempted: {len(selected_actions)}")
        print(f"   Successful: {len(successful_repairs)}")
        print(f"   Failed: {len(failed_repairs)}")

        if successful_repairs:
            print(f"   ✅ Successful repairs: {', '.join(successful_repairs)}")
        if failed_repairs:
            print(f"   ❌ Failed repairs: {', '.join(failed_repairs)}")

        # Save repair session log
        self._save_repair_session_log(selected_actions, successful_repairs, failed_repairs)

    def _save_repair_session_log(self, actions: List[RepairAction], successful: List[str], failed: List[str]):
        """Save repair session log"""
        if not self.config.get("log_repairs", True):
            return

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_type": "interactive",
            "actions_attempted": [action.name for action in actions],
            "successful_repairs": successful,
            "failed_repairs": failed,
            "total_attempts": len(actions),
            "success_rate": len(successful) / max(len(actions), 1) * 100
        }

        log_path = Path("/home/ned/ComfyUI-Install/logs/repair_sessions.json")
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing logs
        existing_logs = []
        if log_path.exists():
            try:
                with open(log_path, 'r') as f:
                    existing_logs = json.load(f)
            except:
                existing_logs = []

        existing_logs.append(log_entry)

        # Keep only last 100 sessions
        if len(existing_logs) > 100:
            existing_logs = existing_logs[-100:]

        with open(log_path, 'w') as f:
            json.dump(existing_logs, f, indent=2)

    def generate_repair_report(self) -> Dict[str, Any]:
        """Generate comprehensive repair report"""
        # Calculate repair statistics
        total_repairs = len(self.repair_history)
        successful_repairs = sum(1 for repair in self.repair_history if repair.get("success", False))
        failed_repairs = total_repairs - successful_repairs

        # Group repairs by category
        repairs_by_category = {}
        for repair in self.repair_history:
            action_name = repair.get("action_name", "")
            action = self.repair_actions.get(action_name)
            if action:
                category = action.category
                if category not in repairs_by_category:
                    repairs_by_category[category] = []
                repairs_by_category[category].append(repair)

        return {
            "timestamp": datetime.now().isoformat(),
            "repair_statistics": {
                "total_repairs": total_repairs,
                "successful_repairs": successful_repairs,
                "failed_repairs": failed_repairs,
                "success_rate": successful_repairs / max(total_repairs, 1) * 100,
                "last_repair": self.repair_history[-1]["timestamp"] if self.repair_history else None
            },
            "repairs_by_category": {
                category: {
                    "total": len(repairs),
                    "successful": sum(1 for r in repairs if r.get("success", False)),
                    "failed": len(repairs) - sum(1 for r in repairs if r.get("success", False))
                }
                for category, repairs in repairs_by_category.items()
            },
            "available_actions": {
                name: {
                    "description": action.description,
                    "severity": action.severity,
                    "category": action.category,
                    "auto_safe": action.auto_safe,
                    "estimated_time": action.estimated_time
                }
                for name, action in self.repair_actions.items()
            },
            "configuration": self.config,
            "recent_repairs": self.repair_history[-10:] if self.repair_history else []
        }

def main():
    """Main repair automation script"""
    print("🔧 ComfyUI Repair Automation")
    print("=" * 50)

    if len(sys.argv) > 1:
        command = sys.argv[1]

        repair_system = ComfyUIRepairAutomation()

        if command == "diagnose":
            # Diagnose issues
            repairs_needed = repair_system.diagnose_issues()
            print(f"\n📋 Found {len(repairs_needed)} issues requiring repair:")

            for issue, action in repairs_needed:
                severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}[action.severity]
                print(f"   {severity_icon} {action.name}: {issue}")

        elif command == "repair":
            # Interactive repair session
            repair_system.interactive_repair_session()

        elif command == "report":
            # Generate repair report
            report = repair_system.generate_repair_report()

            print(f"\n📊 Repair Report:")
            stats = report["repair_statistics"]
            print(f"   Total repairs: {stats['total_repairs']}")
            print(f"   Success rate: {stats['success_rate']:.1f}%")
            print(f"   Last repair: {stats['last_repair']}")

            print(f"\n📋 Available repair actions: {len(report['available_actions'])}")
            for name, info in report["available_actions"].items():
                severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}[info["severity"]]
                print(f"   {severity_icon} {name}: {info['description']}")

        elif command == "auto-repair":
            # Run automatic repair (only safe actions)
            repairs_needed = repair_system.diagnose_issues()
            safe_repairs = [action for issue, action in repairs_needed if action.auto_safe]

            print(f"\n🤖 Auto-repairing {len(safe_repairs)} safe repairs...")

            for action in safe_repairs:
                print(f"\n🔧 {action.name}")
                result = repair_system.execute_repair(action, dry_run=False)
                if result.success:
                    print(f"   ✅ {action.name} completed")
                else:
                    print(f"   ❌ {action.name} failed: {result.error}")

        else:
            print("Usage: python3 scripts/repair_automation.py [diagnose|repair|report|auto-repair]")
    else:
        print("Usage: python3 scripts/repair_automation.py [diagnose|repair|report|auto-repair]")

if __name__ == "__main__":
    main()