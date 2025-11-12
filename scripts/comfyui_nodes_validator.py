#!/usr/bin/env python3
"""
ComfyUI Custom Nodes Validator

A comprehensive validation tool for checking custom node installations,
dependencies, and compatibility issues.
"""

import os
import sys
import json
import subprocess
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

class ValidationResult:
    """Represents a validation result"""
    def __init__(self, name: str, status: str, issues: List[str] = None, warnings: List[str] = None):
        self.name = name
        self.status = status  # "VALID", "WARNINGS", "INVALID", "ERROR"
        self.issues = issues or []
        self.warnings = warnings or []
        self.timestamp = datetime.now().isoformat()

    def add_issue(self, issue: str):
        """Add an issue to the validation result"""
        self.issues.append(issue)
        if self.status == "VALID":
            self.status = "INVALID"

    def add_warning(self, warning: str):
        """Add a warning to the validation result"""
        self.warnings.append(warning)
        if self.status == "VALID":
            self.status = "WARNINGS"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'name': self.name,
            'status': self.status,
            'issues': self.issues,
            'warnings': self.warnings,
            'timestamp': self.timestamp
        }

class CustomNodeValidator:
    """Validator for ComfyUI custom nodes"""

    def __init__(self, comfyui_path: str = None):
        self.comfyui_path = Path(comfyui_path) if comfyui_path else Path("/home/ned/ComfyUI-Install/ComfyUI")
        self.custom_nodes_path = self.comfyui_path / "custom_nodes"
        self.results = {}

    def validate_node_structure(self, node_path: Path) -> ValidationResult:
        """Validate basic structure of a custom node"""
        node_name = node_path.name
        result = ValidationResult(node_name, "VALID")

        if not node_path.exists():
            result.add_issue("Node directory does not exist")
            return result

        if not node_path.is_dir():
            result.add_issue("Node path is not a directory")
            return result

        # Check if directory is empty
        if not any(node_path.iterdir()):
            result.add_issue("Node directory is empty")
            return result

        # Check for __init__.py (required for Python packages)
        init_file = node_path / "__init__.py"
        if not init_file.exists():
            result.add_warning("Missing __init__.py (may not be a proper Python package)")

        # Check for common files
        has_requirements = (node_path / "requirements.txt").exists()
        has_install = (node_path / "install.py").exists()
        has_pyproject = (node_path / "pyproject.toml").exists()
        has_readme = any((node_path / f"README{ext}").exists() for ext in ["", ".md", ".txt"])

        if not any([has_requirements, has_install, has_pyproject]):
            result.add_warning("No dependency management files found (requirements.txt, install.py, or pyproject.toml)")

        if not has_readme:
            result.add_warning("No README file found")

        return result

    def validate_python_syntax(self, node_path: Path) -> ValidationResult:
        """Validate Python syntax in all .py files"""
        node_name = node_path.name
        result = ValidationResult(f"{node_name}_syntax", "VALID")

        syntax_errors = []
        py_files = list(node_path.rglob("*.py"))

        if not py_files:
            result.add_warning("No Python files found")
            return result

        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Try to compile the code
                compile(content, str(py_file), 'exec')

            except SyntaxError as e:
                syntax_errors.append(f"Syntax error in {py_file.name}: {e.msg} (line {e.lineno})")
            except UnicodeDecodeError:
                syntax_errors.append(f"Encoding error in {py_file.name}: unable to read as UTF-8")
            except Exception as e:
                syntax_errors.append(f"Error reading {py_file.name}: {str(e)}")

        if syntax_errors:
            for error in syntax_errors:
                result.add_issue(error)

        return result

    def validate_dependencies(self, node_path: Path) -> ValidationResult:
        """Validate dependencies in requirements.txt"""
        node_name = node_path.name
        result = ValidationResult(f"{node_name}_dependencies", "VALID")

        req_file = node_path / "requirements.txt"
        if not req_file.exists():
            return result  # No requirements to validate

        try:
            with open(req_file, 'r') as f:
                requirements = f.read().strip().split('\n')

            valid_packages = []
            invalid_packages = []

            for req in requirements:
                req = req.strip()
                if not req or req.startswith('#'):
                    continue

                # Check if requirement format is valid
                if self._is_valid_requirement(req):
                    valid_packages.append(req)
                else:
                    invalid_packages.append(req)

            if invalid_packages:
                for invalid in invalid_packages:
                    result.add_issue(f"Invalid requirement format: {invalid}")

            # Try to import valid packages
            missing_packages = []
            for package in valid_packages:
                package_name = self._extract_package_name(package)
                if package_name and not self._is_package_installed(package_name):
                    missing_packages.append(package_name)

            if missing_packages:
                for missing in missing_packages:
                    result.add_issue(f"Missing dependency: {missing}")

        except Exception as e:
            result.add_issue(f"Error reading requirements.txt: {str(e)}")

        return result

    def validate_git_repository(self, node_path: Path) -> ValidationResult:
        """Validate Git repository status"""
        node_name = node_path.name
        result = ValidationResult(f"{node_name}_git", "VALID")

        git_dir = node_path / ".git"
        if not git_dir.exists():
            return result  # Not a Git repository

        try:
            # Check if repository is valid
            repo_status = subprocess.run(
                ['git', '-C', str(node_path), 'status'],
                capture_output=True, text=True, timeout=10
            )

            if repo_status.returncode != 0:
                result.add_issue("Git repository is corrupted")
                return result

            # Check for uncommitted changes
            status_output = repo_status.stdout
            if "Changes not staged for commit" in status_output:
                result.add_warning("Git repository has uncommitted changes")

            # Check for untracked files
            if "Untracked files:" in status_output:
                result.add_warning("Git repository has untracked files")

            # Check remote
            remote_result = subprocess.run(
                ['git', '-C', str(node_path), 'remote', '-v'],
                capture_output=True, text=True, timeout=10
            )

            if remote_result.returncode != 0 or not remote_result.stdout.strip():
                result.add_warning("Git repository has no remote configured")

        except subprocess.TimeoutExpired:
            result.add_issue("Git repository check timed out")
        except FileNotFoundError:
            result.add_issue("Git command not found")
        except Exception as e:
            result.add_issue(f"Error checking Git repository: {str(e)}")

        return result

    def validate_node_mappings(self, node_path: Path) -> ValidationResult:
        """Validate NODE_CLASS_MAPPINGS in custom nodes"""
        node_name = node_path.name
        result = ValidationResult(f"{node_name}_mappings", "VALID")

        # Look for NODE_CLASS_MAPPINGS in Python files
        mapping_files = []
        for py_file in node_path.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "NODE_CLASS_MAPPINGS" in content:
                        mapping_files.append(py_file)
            except:
                continue

        if not mapping_files:
            result.add_warning("No NODE_CLASS_MAPPINGS found (may not be a valid ComfyUI node)")
            return result

        # Validate NODE_CLASS_MAPPINGS structure in each file
        for mapping_file in mapping_files:
            try:
                # Try to execute the file and check NODE_CLASS_MAPPINGS
                spec = importlib.util.spec_from_file_location("node_module", mapping_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    if hasattr(module, 'NODE_CLASS_MAPPINGS'):
                        mappings = getattr(module, 'NODE_CLASS_MAPPINGS')
                        if not isinstance(mappings, dict):
                            result.add_issue(f"NODE_CLASS_MAPPINGS in {mapping_file.name} is not a dictionary")
                        elif not mappings:
                            result.add_warning(f"NODE_CLASS_MAPPINGS in {mapping_file.name} is empty")
                    else:
                        result.add_warning(f"NODE_CLASS_MAPPINGS not found in {mapping_file.name} after import")

            except Exception as e:
                result.add_warning(f"Could not validate NODE_CLASS_MAPPINGS in {mapping_file.name}: {str(e)}")

        return result

    def validate_installation_script(self, node_path: Path) -> ValidationResult:
        """Validate install.py script if present"""
        node_name = node_path.name
        result = ValidationResult(f"{node_name}_install", "VALID")

        install_file = node_path / "install.py"
        if not install_file.exists():
            return result  # No install script

        try:
            # Check syntax of install script
            with open(install_file, 'r', encoding='utf-8') as f:
                content = f.read()

            compile(content, str(install_file), 'exec')

            # Check for dangerous operations
            dangerous_patterns = [
                'rm -rf', 'sudo', 'apt-get', 'pip install --force-reinstall'
            ]

            for pattern in dangerous_patterns:
                if pattern in content:
                    result.add_warning(f"Install script contains potentially dangerous operation: {pattern}")

            # Check for common good practices
            has_requirements_check = 'requirements.txt' in content
            has_error_handling = 'try:' in content and 'except' in content

            if not has_requirements_check and (node_path / "requirements.txt").exists():
                result.add_warning("Install script doesn't check for requirements.txt")

            if not has_error_handling:
                result.add_warning("Install script lacks error handling")

        except SyntaxError as e:
            result.add_issue(f"Syntax error in install.py: {e.msg} (line {e.lineno})")
        except Exception as e:
            result.add_issue(f"Error reading install.py: {str(e)}")

        return result

    def validate_all_nodes(self) -> Dict[str, ValidationResult]:
        """Validate all custom nodes"""
        print(f"🔍 Validating custom nodes in: {self.custom_nodes_path}")

        if not self.custom_nodes_path.exists():
            print(f"❌ Custom nodes directory not found: {self.custom_nodes_path}")
            return {}

        validation_results = {}

        for item in self.custom_nodes_path.iterdir():
            if item.is_dir() and not item.name.startswith('.') and item.name != '__pycache__':
                print(f"   Validating: {item.name}")

                node_results = {}

                # Run all validation checks
                node_results['structure'] = self.validate_node_structure(item)
                node_results['syntax'] = self.validate_python_syntax(item)
                node_results['dependencies'] = self.validate_dependencies(item)
                node_results['git'] = self.validate_git_repository(item)
                node_results['mappings'] = self.validate_node_mappings(item)
                node_results['install'] = self.validate_installation_script(item)

                # Determine overall status
                overall_status = "VALID"
                for check_name, result in node_results.items():
                    if result.status == "INVALID":
                        overall_status = "INVALID"
                        break
                    elif result.status == "WARNINGS" and overall_status == "VALID":
                        overall_status = "WARNINGS"

                # Create overall result
                all_issues = []
                all_warnings = []
                for check_name, result in node_results.items():
                    all_issues.extend([f"{check_name}: {issue}" for issue in result.issues])
                    all_warnings.extend([f"{check_name}: {warning}" for warning in result.warnings])

                overall_result = ValidationResult(item.name, overall_status, all_issues, all_warnings)
                overall_result.details = node_results  # Store detailed results

                validation_results[item.name] = overall_result

        self.results = validation_results
        return validation_results

    def print_summary(self):
        """Print validation summary"""
        if not self.results:
            print("❌ No validation results available")
            return

        total_nodes = len(self.results)
        valid_nodes = sum(1 for r in self.results.values() if r.status == "VALID")
        warning_nodes = sum(1 for r in self.results.values() if r.status == "WARNINGS")
        invalid_nodes = sum(1 for r in self.results.values() if r.status == "INVALID")

        print(f"\n📊 **Validation Summary**")
        print(f"   Total nodes: {total_nodes}")
        print(f"   ✅ Valid: {valid_nodes}")
        print(f"   ⚠️  Warnings: {warning_nodes}")
        print(f"   ❌ Invalid: {invalid_nodes}")

        print(f"\n📋 **Detailed Results**")
        for name, result in sorted(self.results.items()):
            status_icon = {
                "VALID": "✅",
                "WARNINGS": "⚠️",
                "INVALID": "❌",
                "ERROR": "🔥"
            }.get(result.status, "❓")

            print(f"   {status_icon} {name} ({result.status})")
            if result.issues:
                for issue in result.issues[:3]:  # Show first 3 issues
                    print(f"      🚨 {issue}")
                if len(result.issues) > 3:
                    print(f"      ... and {len(result.issues) - 3} more issues")

            if result.warnings:
                for warning in result.warnings[:3]:  # Show first 3 warnings
                    print(f"      ⚠️  {warning}")
                if len(result.warnings) > 3:
                    print(f"      ... and {len(result.warnings) - 3} more warnings")

    def export_results(self, output_file: str):
        """Export validation results to JSON"""
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'custom_nodes_path': str(self.custom_nodes_path),
            'validation_results': {name: result.to_dict() for name, result in self.results.items()},
            'summary': {
                'total_nodes': len(self.results),
                'valid_nodes': sum(1 for r in self.results.values() if r.status == "VALID"),
                'warning_nodes': sum(1 for r in self.results.values() if r.status == "WARNINGS"),
                'invalid_nodes': sum(1 for r in self.results.values() if r.status == "INVALID")
            }
        }

        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"✅ Validation results exported to: {output_file}")

    # Helper methods
    def _is_valid_requirement(self, requirement: str) -> bool:
        """Check if requirement string is valid"""
        # Basic validation for common requirement formats
        valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.,<>=!~#")
        return all(c in valid_chars or c.isspace() for c in requirement)

    def _extract_package_name(self, requirement: str) -> str:
        """Extract package name from requirement string"""
        # Remove version specifiers
        for separator in [">=", "<=", "==", "!=", ">", "<", "~="]:
            if separator in requirement:
                requirement = requirement.split(separator)[0]
        return requirement.strip()

    def _is_package_installed(self, package_name: str) -> bool:
        """Check if a Python package is installed"""
        try:
            spec = importlib.util.find_spec(package_name)
            return spec is not None
        except:
            return False

def main():
    """Main validation script"""
    print("🔍 ComfyUI Custom Nodes Validator")
    print("=" * 50)

    validator = CustomNodeValidator()

    # Run validation
    results = validator.validate_all_nodes()

    if results:
        validator.print_summary()

        # Export results
        export_dir = Path("/home/ned/ComfyUI-Install/config/custom_nodes")
        export_dir.mkdir(parents=True, exist_ok=True)
        validator.export_results(export_dir / "validation_results.json")

        print(f"\n📁 Results saved to: {export_dir}")

        # Exit with appropriate code
        invalid_count = sum(1 for r in results.values() if r.status == "INVALID")
        if invalid_count > 0:
            print(f"\n❌ {invalid_count} nodes have validation issues")
            sys.exit(1)
        else:
            print(f"\n✅ All nodes passed validation (some may have warnings)")
            sys.exit(0)
    else:
        print("❌ No nodes found to validate")
        sys.exit(1)

if __name__ == "__main__":
    main()