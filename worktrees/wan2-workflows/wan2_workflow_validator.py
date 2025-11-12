#!/usr/bin/env python3
"""
Wan2 Video Workflow Model Validator
Specialized agent for analyzing Wan2 video workflows and validating model dependencies
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
    model_type: str  # checkpoint, lora, vae, clip, controlnet, etc.
    model_name: str
    model_path: Optional[str] = None
    node_id: Optional[str] = None
    node_type: Optional[str] = None
    strength: Optional[float] = None
    exists: bool = False
    full_path: Optional[str] = None
    model_category: Optional[str] = None  # diffusion, transformer, etc.

@dataclass
class ValidationResult:
    """Represents validation result for a workflow"""
    workflow_file: str
    total_models: int
    missing_models: int
    found_models: int
    model_references: List[ModelReference]
    workflow_name: Optional[str] = None
    wan2_version: Optional[str] = None
    video_resolution: Optional[Tuple[int, int]] = None

class Wan2WorkflowAnalyzer:
    """Specialized analyzer for Wan2 video workflows"""

    def __init__(self, comfyui_path: str, model_base_paths: List[str]):
        self.comfyui_path = Path(comfyui_path)
        self.model_base_paths = [Path(p) for p in model_base_paths]
        self.supported_extensions = {'.safetensors', '.ckpt', '.pth', '.pt', '.bin', '.gguf'}

    def discover_workflows(self) -> List[str]:
        """Discover Wan2 video workflows in the ComfyUI installation"""
        workflow_patterns = [
            "**/wan2_*.json",
            "**/Wan2_*.json",
            "**/wan-video*.json",
            "**/Wan_Video*.json",
            "**/wan2.1_*.json",
            "**/Wan2.1_*.json"
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
        """Extract model references from Wan2 workflow"""
        references = []

        if not workflow_data.get('nodes'):
            return references

        for node_id, node in workflow_data['nodes'].items():
            node_type = node.get('class_type', '')
            inputs = node.get('inputs', {})

            # Wan2-specific model patterns
            model_patterns = self._get_wan2_model_patterns(node_type)

            for pattern_info in model_patterns:
                field_name = pattern_info['field']
                model_type = pattern_info['type']
                model_category = pattern_info.get('category', 'unknown')

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
                        node_type=node_type,
                        model_category=model_category
                    )

                    # Extract additional parameters
                    if 'strength_field' in pattern_info and pattern_info['strength_field'] in inputs:
                        ref.strength = inputs[pattern_info['strength_field']]

                    references.append(ref)

        return references

    def _get_wan2_model_patterns(self, node_type: str) -> List[Dict]:
        """Get model field patterns for Wan2-specific nodes"""
        patterns = []

        # Wan2 Model Loader patterns
        if 'Wan2' in node_type or 'wan2' in node_type:
            if 'Loader' in node_type or 'loader' in node_type:
                patterns.extend([
                    {'field': 'model_name', 'type': 'transformer', 'category': 'wan2_transformer'},
                    {'field': 'vae_name', 'type': 'vae', 'category': 'wan2_vae'},
                    {'field': 'text_encoder_name', 'type': 'clip', 'category': 'wan2_clip'},
                    {'field': 'scheduler_name', 'type': 'scheduler', 'category': 'wan2_scheduler'}
                ])

            # Wan2 LoRA patterns
            if 'LoRA' in node_type or 'lora' in node_type:
                patterns.extend([
                    {'field': 'lora_name', 'type': 'lora', 'category': 'wan2_lora', 'strength_field': 'strength'},
                    {'field': 'model_name', 'type': 'lora', 'category': 'wan2_lora', 'strength_field': 'strength'}
                ])

            # Wan2 ControlNet patterns
            if 'Control' in node_type or 'control' in node_type:
                patterns.extend([
                    {'field': 'control_net_name', 'type': 'controlnet', 'category': 'wan2_controlnet'},
                    {'field': 'model_name', 'type': 'controlnet', 'category': 'wan2_controlnet'}
                ])

            # Wan2 T2V (Text-to-Video) patterns
            if 'T2V' in node_type or 't2v' in node_type or 'TextToVideo' in node_type:
                patterns.extend([
                    {'field': 'model_name', 'type': 'diffusion_model', 'category': 'wan2_t2v'},
                    {'field': 'transformer_name', 'type': 'transformer', 'category': 'wan2_transformer'}
                ])

            # Wan2 I2V (Image-to-Video) patterns
            if 'I2V' in node_type or 'i2v' in node_type or 'ImageToVideo' in node_type:
                patterns.extend([
                    {'field': 'model_name', 'type': 'diffusion_model', 'category': 'wan2_i2v'},
                    {'field': 'transformer_name', 'type': 'transformer', 'category': 'wan2_transformer'}
                ])

        # Wan2 Camera Control patterns
        if 'Camera' in node_type or 'camera' in node_type:
            if 'Control' in node_type:
                patterns.extend([
                    {'field': 'camera_model_name', 'type': 'camera_control', 'category': 'wan2_camera'},
                    {'field': 'model_name', 'type': 'camera_control', 'category': 'wan2_camera'}
                ])

        # Wan2 Fun Control patterns
        if 'FunControl' in node_type or 'FunControl' in node_type:
            patterns.extend([
                {'field': 'control_model_name', 'type': 'fun_control', 'category': 'wan2_fun'},
                {'field': 'model_name', 'type': 'fun_control', 'category': 'wan2_fun'}
            ])

        # General model patterns that might be used with Wan2
        general_patterns = {
            'CheckpointLoaderSimple': [{'field': 'ckpt_name', 'type': 'checkpoint', 'category': 'general'}],
            'VAELoader': [{'field': 'vae_name', 'type': 'vae', 'category': 'general'}],
            'CLIPTextEncode': [{'field': 'clip', 'type': 'clip', 'category': 'general'}],
            'LoraLoader': [
                {'field': 'lora_name', 'type': 'lora', 'category': 'general', 'strength_field': 'strength_model'},
                {'field': 'lora_name', 'type': 'lora', 'category': 'general', 'strength_field': 'strength_clip'}
            ],
            'ControlNetLoader': [{'field': 'control_net_name', 'type': 'controlnet', 'category': 'general'}],
            'UpscaleModelLoader': [{'field': 'model_name', 'type': 'upscale', 'category': 'general'}],
            'StyleModelLoader': [{'field': 'model_name', 'type': 'style_model', 'category': 'general'}],
        }

        if node_type in general_patterns:
            patterns.extend(general_patterns[node_type])

        return patterns

    def resolve_model_path(self, model_ref: ModelReference) -> Optional[str]:
        """Resolve and validate model file existence for Wan2 models"""
        model_name = model_ref.model_name

        # Define search paths based on model type and category
        search_paths = []

        # Wan2-specific model paths
        if model_ref.model_category == 'wan2_transformer':
            search_paths.extend([
                p / 'wan2' / 'transformers' / model_name,
                p / 'wan2.1' / 'transformers' / model_name,
                p / 'models' / 'wan2' / 'transformers' / model_name,
                p / 'models' / 'diffusion_models' / model_name
            ])
        elif model_ref.model_category == 'wan2_vae':
            search_paths.extend([
                p / 'wan2' / 'vae' / model_name,
                p / 'wan2.1' / 'vae' / model_name,
                p / 'models' / 'wan2' / 'vae' / model_name,
                p / 'vae' / model_name
            ])
        elif model_ref.model_category == 'wan2_clip':
            search_paths.extend([
                p / 'wan2' / 'clip' / model_name,
                p / 'wan2.1' / 'clip' / model_name,
                p / 'models' / 'wan2' / 'clip' / model_name,
                p / 'clip' / model_name
            ])
        elif model_ref.model_category == 'wan2_controlnet':
            search_paths.extend([
                p / 'wan2' / 'controlnet' / model_name,
                p / 'wan2.1' / 'controlnet' / model_name,
                p / 'models' / 'wan2' / 'controlnet' / model_name,
                p / 'controlnet' / model_name
            ])
        elif model_ref.model_category == 'wan2_camera':
            search_paths.extend([
                p / 'wan2' / 'camera_control' / model_name,
                p / 'wan2.1' / 'camera_control' / model_name,
                p / 'models' / 'wan2' / 'camera_control' / model_name,
                p / 'wan2_camera' / model_name
            ])
        elif model_ref.model_category == 'wan2_fun':
            search_paths.extend([
                p / 'wan2' / 'fun_control' / model_name,
                p / 'wan2.1' / 'fun_control' / model_name,
                p / 'models' / 'wan2' / 'fun_control' / model_name,
                p / 'wan2_fun' / model_name
            ])
        elif model_ref.model_category in ['wan2_t2v', 'wan2_i2v']:
            search_paths.extend([
                p / 'wan2' / 'video_models' / model_name,
                p / 'wan2.1' / 'video_models' / model_name,
                p / 'models' / 'wan2' / 'video_models' / model_name,
                p / 'diffusion_models' / model_name
            ])

        # General model paths
        if model_ref.model_type == 'checkpoint':
            search_paths.extend([
                p / 'checkpoints' / model_name,
                p / 'models' / 'checkpoints' / model_name,
                p / 'Stable-diffusion' / model_name
            ])
        elif model_ref.model_type == 'lora':
            search_paths.extend([
                p / 'loras' / model_name,
                p / 'models' / 'loras' / model_name,
                p / 'Lora' / model_name
            ])
        elif model_ref.model_type == 'vae':
            search_paths.extend([
                p / 'vae' / model_name,
                p / 'models' / 'vae' / model_name,
                p / 'VAE' / model_name
            ])
        elif model_ref.model_type == 'controlnet':
            search_paths.extend([
                p / 'controlnet' / model_name,
                p / 'models' / 'controlnet' / model_name,
                p / 'ControlNet' / model_name
            ])
        elif model_ref.model_type == 'upscale':
            search_paths.extend([
                p / 'upscale_models' / model_name,
                p / 'models' / 'upscale_models' / model_name,
                p / 'ESRGAN' / model_name,
                p / 'SwinIR' / model_name
            ])

        # Add common model directories
        for base_path in self.model_base_paths:
            search_paths.extend([
                base_path / model_ref.model_type / model_name,
                base_path / f"{model_ref.model_type}s" / model_name,
                base_path / 'wan2' / model_ref.model_type / model_name,
                base_path / 'wan2.1' / model_ref.model_type / model_name,
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
        """Validate a single Wan2 workflow"""
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

        # Extract video resolution if available
        video_resolution = None
        for node_id, node in workflow_data.get('nodes', {}).items():
            if 'Video' in node.get('class_type', '') or 'video' in node.get('class_type', '').lower():
                inputs = node.get('inputs', {})
                if 'width' in inputs and 'height' in inputs:
                    video_resolution = (inputs['width'], inputs['height'])
                    break

        return ValidationResult(
            workflow_file=workflow_file,
            workflow_name=workflow_name,
            total_models=total_models,
            missing_models=missing_models,
            found_models=found_models,
            model_references=model_refs,
            video_resolution=video_resolution
        )

    def validate_all_workflows(self) -> List[ValidationResult]:
        """Validate all discovered Wan2 workflows"""
        workflows = self.discover_workflows()
        results = []

        print(f"Found {len(workflows)} Wan2 workflows to validate...")

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
            "# Wan2 Video Workflow Model Validation Report",
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

        # Model category breakdown
        if total_models > 0:
            report_lines.append("## Model Category Breakdown")
            category_stats = {}

            for result in results:
                for ref in result.model_references:
                    category = ref.model_category or 'unknown'
                    if category not in category_stats:
                        category_stats[category] = {'total': 0, 'missing': 0}
                    category_stats[category]['total'] += 1
                    if not ref.exists:
                        category_stats[category]['missing'] += 1

            for category, stats in sorted(category_stats.items()):
                success_rate = (stats['total'] - stats['missing']) / stats['total'] * 100 if stats['total'] > 0 else 0
                report_lines.append(f"- **{category}**: {stats['total'] - stats['missing']}/{stats['total']} found ({success_rate:.1f}%)")
            report_lines.append("")

        # Missing models catalog
        if total_missing > 0:
            report_lines.append("## Missing Models Catalog")
            missing_by_category = {}

            for result in results:
                for ref in result.model_references:
                    if not ref.exists:
                        category = ref.model_category or 'unknown'
                        if category not in missing_by_category:
                            missing_by_category[category] = {}
                        model_type = ref.model_type
                        if model_type not in missing_by_category[category]:
                            missing_by_category[category][model_type] = set()
                        missing_by_category[category][model_type].add(ref.model_name)

            for category, types in sorted(missing_by_category.items()):
                report_lines.extend([
                    f"### {category.replace('_', ' ').title()}",
                    ""
                ])
                for model_type, models in sorted(types.items()):
                    report_lines.append(f"**{model_type.title()}**:")
                    for model in sorted(models):
                        report_lines.append(f"- {model}")
                    report_lines.append("")
                report_lines.append("")

        # Workflow details
        report_lines.append("## Workflow Details")
        report_lines.append("")

        for result in sorted(results, key=lambda r: r.missing_models, reverse=True):
            status = "✅ COMPLETE" if result.missing_models == 0 else f"❌ {result.missing_models} MISSING"
            resolution_info = f" ({result.video_resolution[0]}x{result.video_resolution[1]})" if result.video_resolution else ""

            report_lines.extend([
                f"### {result.workflow_name}{resolution_info} ({status})",
                f"**File**: `{result.workflow_file}`",
                f"**Models**: {result.found_models}/{result.total_models} found",
                ""
            ])

            if result.missing_models > 0:
                report_lines.append("**Missing Models**:")
                for ref in result.model_references:
                    if not ref.exists:
                        category_info = f" [{ref.model_category}]" if ref.model_category else ""
                        report_lines.append(f"- `{ref.model_name}` ({ref.model_type}){category_info}")
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
    analyzer = Wan2WorkflowAnalyzer(comfyui_path, model_base_paths)

    # Validate all workflows
    results = analyzer.validate_all_workflows()

    # Generate report
    report_file = "/home/ned/ComfyUI-Install/worktrees/wan2-workflows/wan2_validation_report.md"
    report_content = analyzer.generate_report(results, report_file)

    # Print summary
    print("\n" + "="*60)
    print("WAN2 VIDEO WORKFLOW VALIDATION SUMMARY")
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