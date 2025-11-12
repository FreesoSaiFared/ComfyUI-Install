#!/usr/bin/env python3
"""
LTX Video Workflow Model Validator
Specialized agent for analyzing LTX video workflows and validating model dependencies
"""

import json
import os
import sys
import glob
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ModelReference:
    """Represents a model reference found in a workflow"""
    model_type: str  # checkpoint, lora, vae, clip, etc.
    model_name: str
    model_path: Optional[str] = None
    node_id: Optional[str] = None
    node_type: Optional[str] = None
    strength: Optional[float] = None
    exists: bool = False
    full_path: Optional[str] = None

@dataclass
class ValidationResult:
    """Represents validation result for a workflow"""
    workflow_file: str
    total_models: int
    missing_models: int
    found_models: int
    model_references: List[ModelReference]
    workflow_name: Optional[str] = None
    ltx_version: Optional[str] = None

class LTXWorkflowAnalyzer:
    """Specialized analyzer for LTX video workflows"""

    def __init__(self, comfyui_path: str, model_base_paths: List[str]):
        self.comfyui_path = Path(comfyui_path)
        self.model_base_paths = [Path(p) for p in model_base_paths]
        self.supported_extensions = {'.safetensors', '.ckpt', '.pth', '.pt', '.bin'}

    def discover_workflows(self) -> List[str]:
        """Discover LTX video workflows in the ComfyUI installation"""
        workflow_patterns = [
            "**/ltx_*.json",
            "**/LTX_*.json",
            "**/ltx-video*.json",
            "**/LTX_Video*.json"
        ]

        workflows = []
        for pattern in workflow_patterns:
            workflows.extend(glob.glob(str(self.comfyui_path / pattern), recursive=True))

        return sorted(list(set(workflows)))

    def parse_workflow(self, workflow_file: str) -> Dict:
        """Parse a ComfyUI workflow JSON file"""
        try:
            with open(workflow_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error parsing {workflow_file}: {e}")
            return {}

    def extract_model_references(self, workflow_data: Dict) -> List[ModelReference]:
        """Extract model references from LTX workflow"""
        references = []

        if not workflow_data.get('nodes'):
            return references

        for node_id, node in workflow_data['nodes'].items():
            node_type = node.get('class_type', '')
            inputs = node.get('inputs', {})

            # LTX-specific model patterns
            model_patterns = self._get_ltx_model_patterns(node_type)

            for pattern_info in model_patterns:
                field_name = pattern_info['field']
                model_type = pattern_info['type']

                if field_name in inputs:
                    model_value = inputs[field_name]

                    # Handle different input formats
                    if isinstance(model_value, list) and len(model_value) > 0:
                        model_name = str(model_value[0])
                    elif isinstance(model_value, str):
                        model_name = model_value
                    else:
                        continue

                    # Skip empty values and primitive types
                    if not model_name or model_name in ['none', 'None', '']:
                        continue

                    ref = ModelReference(
                        model_type=model_type,
                        model_name=model_name,
                        node_id=node_id,
                        node_type=node_type
                    )

                    # Extract additional parameters
                    if 'strength_field' in pattern_info and pattern_info['strength_field'] in inputs:
                        ref.strength = inputs[pattern_info['strength_field']]

                    references.append(ref)

        return references

    def _get_ltx_model_patterns(self, node_type: str) -> List[Dict]:
        """Get model field patterns for LTX-specific nodes"""
        patterns = []

        # LTX Model Loader patterns
        if 'LTX' in node_type or 'ltx' in node_type:
            if 'Loader' in node_type or 'loader' in node_type:
                patterns.extend([
                    {'field': 'model_name', 'type': 'checkpoint'},
                    {'field': 'vae_name', 'type': 'vae'},
                    {'field': 'clip_name', 'type': 'clip'}
                ])

            # LTX LoRA patterns
            if 'LoRA' in node_type or 'lora' in node_type:
                patterns.extend([
                    {'field': 'lora_name', 'type': 'lora', 'strength_field': 'strength_model'},
                    {'field': 'lora_name', 'type': 'lora', 'strength_field': 'strength_clip'}
                ])

            # LTX ControlNet patterns
            if 'Control' in node_type or 'control' in node_type:
                patterns.extend([
                    {'field': 'control_net_name', 'type': 'controlnet'},
                    {'field': 'model_name', 'type': 'controlnet'}
                ])

        # General video model patterns
        video_patterns = {
            'CheckpointLoaderSimple': [{'field': 'ckpt_name', 'type': 'checkpoint'}],
            'VAELoader': [{'field': 'vae_name', 'type': 'vae'}],
            'CLIPTextEncode': [{'field': 'clip', 'type': 'clip'}],  # Usually from checkpoint loader
            'LoraLoader': [
                {'field': 'lora_name', 'type': 'lora', 'strength_field': 'strength_model'},
                {'field': 'lora_name', 'type': 'lora', 'strength_field': 'strength_clip'}
            ],
            'ControlNetLoader': [{'field': 'control_net_name', 'type': 'controlnet'}],
        }

        if node_type in video_patterns:
            patterns.extend(video_patterns[node_type])

        return patterns

    def resolve_model_path(self, model_ref: ModelReference) -> Optional[str]:
        """Resolve and validate model file existence"""
        model_name = model_ref.model_name

        # Define search paths based on model type
        search_paths = []

        if model_ref.model_type == 'checkpoint':
            search_paths = [
                p / 'checkpoints' / model_name,
                p / 'models' / 'checkpoints' / model_name,
                p / 'Stable-diffusion' / model_name,
                p / 'base_model' / model_name
            ]
        elif model_ref.model_type == 'lora':
            search_paths = [
                p / 'loras' / model_name,
                p / 'models' / 'loras' / model_name,
                p / 'Lora' / model_name
            ]
        elif model_ref.model_type == 'vae':
            search_paths = [
                p / 'vae' / model_name,
                p / 'models' / 'vae' / model_name,
                p / 'VAE' / model_name
            ]
        elif model_ref.model_type == 'controlnet':
            search_paths = [
                p / 'controlnet' / model_name,
                p / 'models' / 'controlnet' / model_name,
                p / 'ControlNet' / model_name
            ]
        elif model_ref.model_type == 'clip':
            # CLIP models are usually bundled with checkpoints
            search_paths = [
                p / 'clip' / model_name,
                p / 'models' / 'clip' / model_name
            ]

        # Add common model directories
        for base_path in self.model_base_paths:
            search_paths.extend([
                base_path / model_ref.model_type / model_name,
                base_path / f"{model_ref.model_type}s" / model_name,
                base_path / model_name
            ])

        # Search for exact matches first
        for search_path in search_paths:
            if search_path.exists():
                return str(search_path)

        # Search with extensions
        for search_path in search_paths:
            if search_path.suffix == '':
                for ext in self.supported_extensions:
                    test_path = search_path.with_suffix(ext)
                    if test_path.exists():
                        return str(test_path)

        return None

    def validate_workflow(self, workflow_file: str) -> ValidationResult:
        """Validate a single LTX workflow"""
        workflow_data = self.parse_workflow(workflow_file)
        if not workflow_data:
            return ValidationResult(
                workflow_file=workflow_file,
                total_models=0,
                missing_models=0,
                found_models=0,
                model_references=[]
            )

        # Extract workflow metadata
        workflow_name = workflow_data.get('extra', {}).get('workflow', {}).get('title', Path(workflow_file).stem)

        # Extract model references
        model_refs = self.extract_model_references(workflow_data)

        # Validate model existence
        for ref in model_refs:
            ref.full_path = self.resolve_model_path(ref)
            ref.exists = ref.full_path is not None

        # Calculate statistics
        total_models = len(model_refs)
        found_models = sum(1 for ref in model_refs if ref.exists)
        missing_models = total_models - found_models

        return ValidationResult(
            workflow_file=workflow_file,
            workflow_name=workflow_name,
            total_models=total_models,
            missing_models=missing_models,
            found_models=found_models,
            model_references=model_refs
        )

    def validate_all_workflows(self) -> List[ValidationResult]:
        """Validate all discovered LTX workflows"""
        workflows = self.discover_workflows()
        results = []

        print(f"Found {len(workflows)} LTX workflows to validate...")

        for workflow_file in workflows:
            print(f"Validating: {Path(workflow_file).name}")
            result = self.validate_workflow(workflow_file)
            results.append(result)

            # Print summary for this workflow
            if result.missing_models > 0:
                print(f"  ❌ {result.missing_models}/{result.total_models} models missing")
            else:
                print(f"  ✅ All {result.total_models} models found")

        return results

    def generate_report(self, results: List[ValidationResult], output_file: str = None) -> str:
        """Generate comprehensive validation report"""
        report_lines = [
            "# LTX Video Workflow Model Validation Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        # Summary statistics
        total_workflows = len(results)
        total_models = sum(r.total_models for r in results)
        total_missing = sum(r.missing_models for r in results)
        total_found = sum(r.found_models for r in results)

        report_lines.extend([
            "## Summary",
            f"- **Total Workflows**: {total_workflows}",
            f"- **Total Models**: {total_models}",
            f"- **Found Models**: {total_found}",
            f"- **Missing Models**: {total_missing}",
            f"- **Success Rate**: {(total_found/total_models*100):.1f}%" if total_models > 0 else "- **Success Rate**: N/A",
            "",
        ])

        # Missing models catalog
        if total_missing > 0:
            report_lines.append("## Missing Models Catalog")
            missing_by_type = {}

            for result in results:
                for ref in result.model_references:
                    if not ref.exists:
                        model_type = ref.model_type
                        if model_type not in missing_by_type:
                            missing_by_type[model_type] = set()
                        missing_by_type[model_type].add(ref.model_name)

            for model_type, models in sorted(missing_by_type.items()):
                report_lines.extend([
                    f"### {model_type.title()} Models",
                    ""
                ])
                for model in sorted(models):
                    report_lines.append(f"- {model}")
                report_lines.append("")

        # Workflow details
        report_lines.append("## Workflow Details")
        report_lines.append("")

        for result in sorted(results, key=lambda r: r.missing_models, reverse=True):
            status = "✅ COMPLETE" if result.missing_models == 0 else f"❌ {result.missing_models} MISSING"
            report_lines.extend([
                f"### {result.workflow_name} ({status})",
                f"**File**: `{result.workflow_file}`",
                f"**Models**: {result.found_models}/{result.total_models} found",
                ""
            ])

            if result.missing_models > 0:
                report_lines.append("**Missing Models**:")
                for ref in result.model_references:
                    if not ref.exists:
                        report_lines.append(f"- `{ref.model_name}` ({ref.model_type})")
                report_lines.append("")

        report_content = "\n".join(report_lines)

        # Save to file if specified
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"Report saved to: {output_file}")

        return report_content

def main():
    """Main execution function"""
    # Configuration
    comfyui_path = "/home/ned/ComfyUI-Install/ComfyUI"
    model_base_paths = [
        "/home/ned/ComfyUI-Install/models",
        "/home/ned/Models",
        "/home/ned/Projects/AI_ML/SwarmUI/models"
    ]

    # Initialize analyzer
    analyzer = LTXWorkflowAnalyzer(comfyui_path, model_base_paths)

    # Validate all workflows
    results = analyzer.validate_all_workflows()

    # Generate report
    report_file = "/home/ned/ComfyUI-Install/worktrees/ltx-workflows/ltx_validation_report.md"
    report_content = analyzer.generate_report(results, report_file)

    # Print summary
    print("\n" + "="*60)
    print("LTX VIDEO WORKFLOW VALIDATION SUMMARY")
    print("="*60)
    print(f"Workflows analyzed: {len(results)}")
    print(f"Total models needed: {sum(r.total_models for r in results)}")
    print(f"Models found: {sum(r.found_models for r in results)}")
    print(f"Models missing: {sum(r.missing_models for r in results)}")

    if results:
        missing_count = sum(r.missing_models for r in results)
        if missing_count > 0:
            print(f"\n⚠️  {missing_count} models are missing!")
            print(f"📄 Detailed report: {report_file}")
        else:
            print(f"\n✅ All models are available!")

if __name__ == "__main__":
    main()