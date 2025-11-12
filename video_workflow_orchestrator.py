#!/usr/bin/env python3
"""
Video Workflow Model Validation Orchestrator
Parallel execution system for all video workflow validators using Claude Flow coordination
"""

import json
import os
import sys
import time
import asyncio
import subprocess
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import multiprocessing as mp

# Claude Flow imports (when available)
try:
    from mcp__claude_flow import *
except ImportError:
    print("Claude Flow modules not available, running in standalone mode")

@dataclass
class ValidationTask:
    """Represents a validation task for a specific category"""
    name: str
    worktree_path: str
    validator_script: str
    branch_name: str
    port: int
    priority: str  # high, medium, low

@dataclass
class ValidationResult:
    """Results from a validation task"""
    task_name: str
    success: bool
    total_workflows: int
    total_models: int
    found_models: int
    missing_models: int
    execution_time: float
    report_path: str
    error_message: Optional[str] = None
    detailed_metrics: Dict = None

@dataclass
class OrchestratorReport:
    """Complete orchestrator report"""
    execution_start: datetime
    execution_end: datetime
    total_execution_time: float
    validation_results: List[ValidationResult]
    overall_summary: Dict
    swarm_coordination_id: Optional[str] = None

class VideoWorkflowOrchestrator:
    """Main orchestrator for parallel video workflow validation"""

    def __init__(self, comfyui_path: str, max_workers: int = 4):
        self.comfyui_path = Path(comfyui_path)
        self.max_workers = max_workers
        self.worktrees_path = self.comfyui_path.parent / "worktrees"
        self.reports_path = self.comfyui_path / "validation_reports"

        # Create reports directory
        self.reports_path.mkdir(exist_ok=True)

        # Define validation tasks
        self.validation_tasks = [
            ValidationTask(
                name="LTX Video Workflows",
                worktree_path=str(self.worktrees_path / "ltx-workflows"),
                validator_script="ltx_workflow_validator.py",
                branch_name="ltx-video-validation",
                port=8188,
                priority="high"
            ),
            ValidationTask(
                name="Wan2 Video Workflows",
                worktree_path=str(self.worktrees_path / "wan2-workflows"),
                validator_script="wan2_workflow_validator.py",
                branch_name="wan2-video-validation",
                port=8189,
                priority="high"
            ),
            ValidationTask(
                name="VideoHelperSuite Workflows",
                worktree_path=str(self.worktrees_path / "video-helper-workflows"),
                validator_script="video_helper_suite_validator.py",
                branch_name="video-helper-validation",
                port=8190,
                priority="medium"
            ),
            ValidationTask(
                name="KJNodes Workflows",
                worktree_path=str(self.worktrees_path / "kj-nodes-workflows"),
                validator_script="kj_nodes_validator.py",
                branch_name="kj-nodes-validation",
                port=8191,
                priority="medium"
            ),
            ValidationTask(
                name="Generic Video Workflows",
                worktree_path=str(self.worktrees_path / "generic-video-workflows"),
                validator_script="generic_video_validator.py",
                branch_name="generic-video-validation",
                port=8192,
                priority="low"
            )
        ]

    def initialize_claude_flow_coordination(self) -> Optional[str]:
        """Initialize Claude Flow swarm coordination"""
        try:
            print("🔄 Initializing Claude Flow swarm coordination...")

            # Initialize swarm with mesh topology for optimal parallel processing
            swarm_result = mcp__claude_flow__swarm_init(
                topology="mesh",
                maxAgents=12,
                strategy="adaptive"
            )

            if swarm_result.get('success'):
                swarm_id = swarm_result.get('swarmId')
                print(f"✅ Swarm initialized: {swarm_id}")

                # Orchestrate the validation task
                task_result = mcp__claude_flow__task_orchestrate(
                    task="Execute parallel video workflow model validation across multiple categories",
                    strategy="parallel",
                    priority="high"
                )

                return swarm_id
            else:
                print("⚠️  Claude Flow initialization failed, proceeding with local execution")
                return None

        except Exception as e:
            print(f"⚠️  Claude Flow coordination error: {e}")
            print("🔄 Falling back to local parallel execution")
            return None

    def execute_validation_task(self, task: ValidationTask) -> ValidationResult:
        """Execute a single validation task"""
        print(f"🚀 Starting {task.name} validation...")
        start_time = time.time()

        try:
            # Change to worktree directory
            worktree_path = Path(task.worktree_path)
            if not worktree_path.exists():
                raise FileNotFoundError(f"Worktree not found: {task.worktree_path}")

            validator_script = worktree_path / task.validator_script
            if not validator_script.exists():
                raise FileNotFoundError(f"Validator script not found: {validator_script}")

            # Execute the validator script
            result = subprocess.run(
                [sys.executable, str(validator_script)],
                cwd=str(worktree_path),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            execution_time = time.time() - start_time

            if result.returncode != 0:
                error_message = f"Validation failed with exit code {result.returncode}: {result.stderr}"
                print(f"❌ {task.name} failed: {error_message}")
                return ValidationResult(
                    task_name=task.name,
                    success=False,
                    total_workflows=0,
                    total_models=0,
                    found_models=0,
                    missing_models=0,
                    execution_time=execution_time,
                    report_path="",
                    error_message=error_message
                )

            # Parse results from the validator output
            parsed_results = self._parse_validator_output(result.stdout, worktree_path)

            print(f"✅ {task.name} completed in {execution_time:.1f}s")
            return ValidationResult(
                task_name=task.name,
                success=True,
                execution_time=execution_time,
                **parsed_results
            )

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            error_message = "Validation timed out after 5 minutes"
            print(f"⏱️  {task.name} timed out")
            return ValidationResult(
                task_name=task.name,
                success=False,
                total_workflows=0,
                total_models=0,
                found_models=0,
                missing_models=0,
                execution_time=execution_time,
                report_path="",
                error_message=error_message
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_message = f"Unexpected error: {str(e)}"
            print(f"💥 {task.name} error: {error_message}")
            return ValidationResult(
                task_name=task.name,
                success=False,
                total_workflows=0,
                total_models=0,
                found_models=0,
                missing_models=0,
                execution_time=execution_time,
                report_path="",
                error_message=error_message
            )

    def _parse_validator_output(self, output: str, worktree_path: Path) -> Dict:
        """Parse validator output to extract results"""
        # Look for the summary section in the output
        lines = output.split('\n')
        summary_start = None

        for i, line in enumerate(lines):
            if 'WORKFLOW VALIDATION SUMMARY' in line:
                summary_start = i
                break

        if not summary_start:
            # Default values if parsing fails
            return {
                'total_workflows': 0,
                'total_models': 0,
                'found_models': 0,
                'missing_models': 0,
                'report_path': str(worktree_path / "validation_report.md")
            }

        # Extract metrics from summary
        metrics = {
            'total_workflows': 0,
            'total_models': 0,
            'found_models': 0,
            'missing_models': 0
        }

        for line in lines[summary_start:]:
            if 'Workflows analyzed:' in line:
                try:
                    metrics['total_workflows'] = int(line.split(':')[-1].strip())
                except (ValueError, IndexError):
                    pass
            elif 'Total models needed:' in line:
                try:
                    metrics['total_models'] = int(line.split(':')[-1].strip())
                except (ValueError, IndexError):
                    pass
            elif 'Models found:' in line:
                try:
                    metrics['found_models'] = int(line.split(':')[-1].strip())
                except (ValueError, IndexError):
                    pass
            elif 'Models missing:' in line:
                try:
                    metrics['missing_models'] = int(line.split(':')[-1].strip())
                except (ValueError, IndexError):
                    pass

        # Find report file
        report_path = worktree_path / "validation_report.md"
        if not report_path.exists():
            # Look for other possible report names
            for possible_report in worktree_path.glob("*validation_report.md"):
                report_path = possible_report
                break

        metrics['report_path'] = str(report_path)
        return metrics

    def execute_parallel_validation(self) -> List[ValidationResult]:
        """Execute all validation tasks in parallel"""
        print(f"🎯 Starting parallel validation with {self.max_workers} workers...")
        print(f"📋 {len(self.validation_tasks)} tasks to execute")
        print("="*60)

        # Sort tasks by priority
        sorted_tasks = sorted(self.validation_tasks, key=lambda t:
                             {'high': 0, 'medium': 1, 'low': 2}[t.priority])

        results = []

        # Execute high priority tasks first
        high_priority_tasks = [t for t in sorted_tasks if t.priority == 'high']
        if high_priority_tasks:
            print("🔥 Executing high priority tasks...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(self.max_workers, len(high_priority_tasks))) as executor:
                future_to_task = {executor.submit(self.execute_validation_task, task): task for task in high_priority_tasks}

                for future in concurrent.futures.as_completed(future_to_task):
                    task = future_to_task[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        print(f"💥 Task {task.name} failed: {e}")
                        results.append(ValidationResult(
                            task_name=task.name,
                            success=False,
                            total_workflows=0,
                            total_models=0,
                            found_models=0,
                            missing_models=0,
                            execution_time=0,
                            report_path="",
                            error_message=str(e)
                        ))

        # Execute medium priority tasks
        medium_priority_tasks = [t for t in sorted_tasks if t.priority == 'medium']
        if medium_priority_tasks:
            print("⚡ Executing medium priority tasks...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(self.max_workers, len(medium_priority_tasks))) as executor:
                future_to_task = {executor.submit(self.execute_validation_task, task): task for task in medium_priority_tasks}

                for future in concurrent.futures.as_completed(future_to_task):
                    task = future_to_task[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        print(f"💥 Task {task.name} failed: {e}")
                        results.append(ValidationResult(
                            task_name=task.name,
                            success=False,
                            total_workflows=0,
                            total_models=0,
                            found_models=0,
                            missing_models=0,
                            execution_time=0,
                            report_path="",
                            error_message=str(e)
                        ))

        # Execute low priority tasks
        low_priority_tasks = [t for t in sorted_tasks if t.priority == 'low']
        if low_priority_tasks:
            print("🔍 Executing low priority tasks...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(self.max_workers, len(low_priority_tasks))) as executor:
                future_to_task = {executor.submit(self.execute_validation_task, task): task for task in low_priority_tasks}

                for future in concurrent.futures.as_completed(future_to_task):
                    task = future_to_task[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        print(f"💥 Task {task.name} failed: {e}")
                        results.append(ValidationResult(
                            task_name=task.name,
                            success=False,
                            total_workflows=0,
                            total_models=0,
                            found_models=0,
                            missing_models=0,
                            execution_time=0,
                            report_path="",
                            error_message=str(e)
                        ))

        return results

    def generate_comprehensive_report(self, results: List[ValidationResult],
                                    execution_time: float,
                                    swarm_id: Optional[str] = None) -> str:
        """Generate comprehensive report of all validation results"""
        report_lines = [
            "# Video Workflow Model Validation - Comprehensive Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Execution Time: {execution_time:.1f} seconds",
            f"Swarm Coordination: {swarm_id or 'Local execution'}",
            "",
            "="*60,
            "",
        ]

        # Overall summary
        total_workflows = sum(r.total_workflows for r in results)
        total_models = sum(r.total_models for r in results)
        total_found = sum(r.found_models for r in results)
        total_missing = sum(r.missing_models for r in results)
        successful_tasks = sum(1 for r in results if r.success)
        failed_tasks = len(results) - successful_tasks

        overall_success_rate = (total_found / total_models * 100) if total_models > 0 else 0

        report_lines.extend([
            "## 🎯 Overall Summary",
            "",
            f"**Tasks Executed**: {successful_tasks}/{len(results)} successful",
            f"**Total Workflows Analyzed**: {total_workflows}",
            f"**Total Models Required**: {total_models}",
            f"**Models Found**: {total_found}",
            f"**Models Missing**: {total_missing}",
            f"**Overall Success Rate**: {overall_success_rate:.1f}%",
            "",
        ])

        # Task execution summary
        report_lines.extend([
            "## 📊 Task Execution Summary",
            ""
        ])

        for result in results:
            status_emoji = "✅" if result.success else "❌"
            success_rate = (result.found_models / result.total_models * 100) if result.total_models > 0 else 0

            report_lines.extend([
                f"### {status_emoji} {result.task_name}",
                f"- **Status**: {'Success' if result.success else 'Failed'}",
                f"- **Execution Time**: {result.execution_time:.1f}s",
                f"- **Workflows**: {result.total_workflows}",
                f"- **Models**: {result.found_models}/{result.total_models} ({success_rate:.1f}%)",
                f"- **Missing Models**: {result.missing_models}",
                f"- **Report**: `{result.report_path}`",
                ""
            ])

            if result.error_message:
                report_lines.append(f"**Error**: {result.error_message}")
                report_lines.append("")

        # Missing models catalog
        if total_missing > 0:
            report_lines.extend([
                "## 🚨 Missing Models Catalog",
                ""
            ])

            missing_by_category = {}
            for result in results:
                if result.report_path and Path(result.report_path).exists():
                    try:
                        with open(result.report_path, 'r') as f:
                            report_content = f.read()
                            # This is simplified - in a real implementation,
                            # you'd parse the markdown more carefully
                            if 'Missing Models Catalog' in report_content:
                                missing_by_category[result.task_name] = "See detailed report"
                    except Exception:
                        pass

            for task, info in missing_by_category.items():
                report_lines.extend([
                    f"### {task}",
                    info,
                    ""
                ])

        # Performance analysis
        report_lines.extend([
            "## ⚡ Performance Analysis",
            ""
        ])

        fastest_task = min(results, key=lambda r: r.execution_time)
        slowest_task = max(results, key=lambda r: r.execution_time)

        report_lines.extend([
            f"- **Fastest Task**: {fastest_task.task_name} ({fastest_task.execution_time:.1f}s)",
            f"- **Slowest Task**: {slowest_task.task_name} ({slowest_task.execution_time:.1f}s)",
            f"- **Average Task Time**: {sum(r.execution_time for r in results) / len(results):.1f}s",
            f"- **Parallel Efficiency**: {(execution_time / sum(r.execution_time for r in results) * 100):.1f}%",
            ""
        ])

        # Recommendations
        report_lines.extend([
            "## 💡 Recommendations",
            ""
        ])

        if total_missing > 0:
            report_lines.extend([
                "### 🚨 Missing Models Action Required",
                f"- **{total_missing} models** need to be downloaded",
                "- Check individual task reports for specific model names",
                "- Consider setting up automated model downloading",
                ""
            ])

        if failed_tasks > 0:
            report_lines.extend([
                "### 🔧 Failed Tasks",
                f"- **{failed_tasks} tasks** failed to execute",
                "- Review error messages above",
                "- Check validator scripts for issues",
                ""
            ])

        if overall_success_rate < 80:
            report_lines.extend([
                "### 📈 Model Management",
                "- Overall success rate is below 80%",
                "- Consider organizing model directories better",
                "- Validate model path configurations",
                ""
            ])

        # Footer
        report_lines.extend([
            "---",
            f"*Report generated by Video Workflow Orchestrator*",
            f"*Claude Flow Swarm ID: {swarm_id or 'N/A'}*",
        ])

        return "\n".join(report_lines)

    def run_validation(self) -> OrchestratorReport:
        """Run the complete validation orchestration"""
        execution_start = datetime.now()
        start_time = time.time()

        print("🚀 Starting Video Workflow Model Validation Orchestration")
        print("="*60)

        # Initialize Claude Flow coordination if available
        swarm_id = self.initialize_claude_flow_coordination()

        # Execute validation tasks
        validation_results = self.execute_parallel_validation()

        execution_time = time.time() - start_time
        execution_end = datetime.now()

        # Generate comprehensive report
        print("\n" + "="*60)
        print("📊 Generating comprehensive report...")

        comprehensive_report_content = self.generate_comprehensive_report(
            validation_results, execution_time, swarm_id
        )

        # Save comprehensive report
        report_file = self.reports_path / f"comprehensive_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(comprehensive_report_content)

        print(f"📄 Comprehensive report saved: {report_file}")

        # Calculate overall summary
        total_workflows = sum(r.total_workflows for r in validation_results)
        total_models = sum(r.total_models for r in validation_results)
        total_found = sum(r.found_models for r in validation_results)
        total_missing = sum(r.missing_models for r in validation_results)

        overall_summary = {
            'total_tasks': len(validation_results),
            'successful_tasks': sum(1 for r in validation_results if r.success),
            'failed_tasks': sum(1 for r in validation_results if not r.success),
            'total_workflows': total_workflows,
            'total_models': total_models,
            'found_models': total_found,
            'missing_models': total_missing,
            'overall_success_rate': (total_found / total_models * 100) if total_models > 0 else 0
        }

        return OrchestratorReport(
            execution_start=execution_start,
            execution_end=execution_end,
            total_execution_time=execution_time,
            validation_results=validation_results,
            overall_summary=overall_summary,
            swarm_coordination_id=swarm_id
        )

def main():
    """Main execution function"""
    # Configuration
    comfyui_path = "/home/ned/ComfyUI-Install/ComfyUI"

    # Initialize orchestrator
    orchestrator = VideoWorkflowOrchestrator(
        comfyui_path=comfyui_path,
        max_workers=4  # Adjust based on system capabilities
    )

    # Run validation
    report = orchestrator.run_validation()

    # Print final summary
    print("\n" + "="*60)
    print("🎉 VALIDATION ORCHESTRATION COMPLETED")
    print("="*60)
    print(f"⏱️  Total Time: {report.total_execution_time:.1f} seconds")
    print(f"📋 Tasks: {report.overall_summary['successful_tasks']}/{report.overall_summary['total_tasks']} successful")
    print(f"🗂️  Workflows: {report.overall_summary['total_workflows']}")
    print(f"🎯 Models: {report.overall_summary['found_models']}/{report.overall_summary['total_models']} found")
    print(f"⚠️  Missing: {report.overall_summary['missing_models']} models")
    print(f"📈 Success Rate: {report.overall_summary['overall_success_rate']:.1f}%")

    if report.overall_summary['missing_models'] > 0:
        print(f"\n🚨 Action Required: {report.overall_summary['missing_models']} models need to be downloaded!")
    else:
        print(f"\n✅ Excellent! All models are available!")

if __name__ == "__main__":
    main()