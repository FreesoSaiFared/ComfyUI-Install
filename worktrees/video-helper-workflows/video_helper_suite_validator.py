#!/usr/bin/env python3
"""
VideoHelperSuite Workflow Model Validator
Specialized agent for analyzing VideoHelperSuite workflows and validating model dependencies
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
    video_helper_type: Optional[str] = None  # video_format, video_load, etc.

@dataclass
class ValidationResult:
    """Represents validation result for a workflow"""
    workflow_file: str
    total_models: int
    missing_models: int
    found_models: int
    model_references: List[ModelReference]
    workflow_name: Optional[str] = None
    video_helper_version: Optional[str] = None
    video_nodes_count: int = 0

class VideoHelperSuiteAnalyzer:
    """Specialized analyzer for VideoHelperSuite workflows"""

    def __init__(self, comfyui_path: str, model_base_paths: List[str]):
        self.comfyui_path = Path(comfyui_path)
        self.model_base_paths = [Path(p) for p in model_base_paths]
        self.supported_extensions = {'.safetensors', '.ckpt', '.pth', '.pt', '.bin', '.onnx'}

    def discover_workflows(self) -> List[str]:
        """Discover VideoHelperSuite workflows in the ComfyUI installation"""
        workflow_patterns = [
            "**/video_*.json",
            "**/Video_*.json",
            "**/vh_*.json",
            "**/VH_*.json",
            "**/videohelper*.json",
            "**/VideoHelper*.json"
        ]

        workflows = []
        for pattern in workflow_patterns:
            workflows.extend(glob.glob(str(self.comfyui_path / pattern), recursive=True))

        # Also search in VideoHelperSuite custom node directory
        vhs_patterns = [
            "custom_nodes/ComfyUI-VideoHelperSuite/**/workflows/*.json",
            "custom_nodes/videohelpersuite/**/workflows/*.json"
        ]

        for pattern in vhs_patterns:
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
        """Extract model references from VideoHelperSuite workflow"""
        references = []

        if not workflow_data.get('nodes'):
            return references

        video_helper_nodes_count = 0

        for node_id, node in workflow_data['nodes'].items():
            node_type = node.get('class_type', '')
            inputs = node.get('inputs', {})

            # Count VideoHelperSuite nodes
            if self._is_video_helper_node(node_type):
                video_helper_nodes_count += 1

            # VideoHelperSuite-specific model patterns
            model_patterns = self._get_video_helper_model_patterns(node_type)

            for pattern_info in model_patterns:
                field_name = pattern_info['field']
                model_type = pattern_info['type']
                video_helper_type = pattern_info.get('vh_type', 'unknown')

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
                        video_helper_type=video_helper_type
                    )

                    # Extract additional parameters
                    if 'strength_field' in pattern_info and pattern_info['strength_field'] in inputs:
                        ref.strength = inputs[pattern_info['strength_field']]

                    references.append(ref)

        return references

    def _is_video_helper_node(self, node_type: str) -> bool:
        """Check if a node is from VideoHelperSuite"""
        video_helper_prefixes = [
            'VHS_', 'vhs_', 'Video', 'video', 'LoadVideo', 'SaveVideo',
            'VideoCombine', 'VideoInfo', 'VideoFormat', 'VideoLoad',
            'VideoSave', 'VideoResize', 'VideoTrim', 'VideoSplit',
            'VideoConcat', 'VideoScale', 'VideoConvert'
        ]

        return any(node_type.startswith(prefix) or prefix in node_type for prefix in video_helper_prefixes)

    def _get_video_helper_model_patterns(self, node_type: str) -> List[Dict]:
        """Get model field patterns for VideoHelperSuite nodes"""
        patterns = []

        # VideoHelperSuite-specific patterns
        if self._is_video_helper_node(node_type):
            # Video loading patterns (might reference frame interpolation models)
            if 'LoadVideo' in node_type or 'VideoLoad' in node_type:
                patterns.extend([
                    {'field': 'interpolation_model', 'type': 'interpolation', 'vh_type': 'frame_interpolation'},
                    {'field': 'frame_interpolation', 'type': 'interpolation', 'vh_type': 'frame_interpolation'}
                ])

            # Video enhancement patterns
            if 'VideoEnhance' in node_type or 'VideoUpscale' in node_type:
                patterns.extend([
                    {'field': 'enhancement_model', 'type': 'enhancement', 'vh_type': 'video_enhancement'},
                    {'field': 'upscale_model', 'type': 'upscale', 'vh_type': 'video_upscale'},
                    {'field': 'super_resolution_model', 'type': 'super_resolution', 'vh_type': 'video_sr'}
                ])

            # Video format conversion patterns
            if 'VideoFormat' in node_type or 'VideoConvert' in node_type:
                patterns.extend([
                    {'field': 'encoder_model', 'type': 'encoder', 'vh_type': 'video_encoder'},
                    {'field': 'decoder_model', 'type': 'decoder', 'vh_type': 'video_decoder'}
                ])

            # Video analysis patterns
            if 'VideoInfo' in node_type or 'VideoAnalyze' in node_type:
                patterns.extend([
                    {'field': 'analysis_model', 'type': 'analysis', 'vh_type': 'video_analysis'}
                ])

        # General model patterns used in video workflows
        general_patterns = {
            'CheckpointLoaderSimple': [{'field': 'ckpt_name', 'type': 'checkpoint', 'vh_type': 'general'}],
            'VAELoader': [{'field': 'vae_name', 'type': 'vae', 'vh_type': 'general'}],
            'CLIPTextEncode': [{'field': 'clip', 'type': 'clip', 'vh_type': 'general'}],
            'LoraLoader': [
                {'field': 'lora_name', 'type': 'lora', 'vh_type': 'general', 'strength_field': 'strength_model'},
                {'field': 'lora_name', 'type': 'lora', 'vh_type': 'general', 'strength_field': 'strength_clip'}
            ],
            'ControlNetLoader': [{'field': 'control_net_name', 'type': 'controlnet', 'vh_type': 'general'}],
            'UpscaleModelLoader': [{'field': 'model_name', 'type': 'upscale', 'vh_type': 'general'}],
            'StyleModelLoader': [{'field': 'model_name', 'type': 'style_model', 'vh_type': 'general'}],
            'GLIGENLoader': [{'field': 'model_name', 'type': 'gligen', 'vh_type': 'general'}],
            'HypernetworkLoader': [{'field': 'model_name', 'type': 'hypernetwork', 'vh_type': 'general'}],

            # Model loaders that might be used for video generation
            'UNETLoader': [{'field': 'unet_name', 'type': 'unet', 'vh_type': 'diffusion'}],
            'DiffusionLoader': [{'field': 'model_name', 'type': 'diffusion_model', 'vh_type': 'diffusion'}],
            'AnimateDiffLoader': [{'field': 'model_name', 'type': 'animatediff', 'vh_type': 'animation'}],
            'MotionModuleLoader': [{'field': 'model_name', 'type': 'motion_module', 'vh_type': 'animation'}],
            'IPAdapterModelLoader': [{'field': 'model_name', 'type': 'ip_adapter', 'vh_type': 'ip_adapter'}],

            # Frame interpolation models
            'RIFEModelLoader': [{'field': 'model_name', 'type': 'rife', 'vh_type': 'interpolation'}],
            'FILMModelLoader': [{'field': 'model_name', 'type': 'film', 'vh_type': 'interpolation'}],
            'IFNetModelLoader': [{'field': 'model_name', 'type': 'ifnet', 'vh_type': 'interpolation'}],

            # Video super-resolution models
            'RealESRGANLoader': [{'field': 'model_name', 'type': 'real_esrgan', 'vh_type': 'enhancement'}],
            'ESRGANLoader': [{'field': 'model_name', 'type': 'esrgan', 'vh_type': 'enhancement'}],
            'SwinIRLoader': [{'field': 'model_name', 'type': 'swinir', 'vh_type': 'enhancement'}],
        }

        if node_type in general_patterns:
            patterns.extend(general_patterns[node_type])

        return patterns

    def resolve_model_path(self, model_ref: ModelReference) -> Optional[str]:
        """Resolve and validate model file existence"""
        model_name = model_ref.model_name

        # Define search paths based on model type and VideoHelperSuite type
        search_paths = []

        # VideoHelperSuite-specific paths
        if model_ref.video_helper_type == 'frame_interpolation':
            search_paths.extend([
                p / 'video_models' / 'interpolation' / model_name,
                p / 'frame_interpolation' / model_name,
                p / 'RIFE' / model_name,
                p / 'FILM' / model_name,
                p / 'models' / 'interpolation' / model_name
            ])
        elif model_ref.video_helper_type == 'video_enhancement':
            search_paths.extend([
                p / 'video_models' / 'enhancement' / model_name,
                p / 'video_upscale' / model_name,
                p / 'Real-ESRGAN' / model_name,
                p / 'SwinIR' / model_name,
                p / 'models' / 'video_enhancement' / model_name
            ])
        elif model_ref.video_helper_type == 'video_encoder' or model_ref.video_helper_type == 'video_decoder':
            search_paths.extend([
                p / 'video_models' / 'codecs' / model_name,
                p / 'video_codecs' / model_name,
                p / 'models' / 'video_codecs' / model_name
            ])

        # Animation and motion models
        if model_ref.model_type == 'animatediff' or model_ref.model_type == 'motion_module':
            search_paths.extend([
                p / 'animatediff_models' / model_name,
                p / 'motion_modules' / model_name,
                p / 'models' / 'animatediff' / model_name,
                p / 'models' / 'Motion_Module' / model_name
            ])

        # General model paths
        if model_ref.model_type == 'checkpoint':
            search_paths.extend([
                p / 'checkpoints' / model_name,
                p / 'models' / 'checkpoints' / model_name,
                p / 'Stable-diffusion' / model_name,
                p / 'diffusion_models' / model_name
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
                p / 'SwinIR' / model_name,
                p / 'Real-ESRGAN' / model_name
            ])
        elif model_ref.model_type in ['rife', 'film', 'ifnet']:
            search_paths.extend([
                p / 'interpolation' / model_ref.model_type / model_name,
                p / 'frame_interpolation' / model_name,
                p / 'models' / 'interpolation' / model_name
            ])

        # Add common model directories
        for base_path in self.model_base_paths:
            search_paths.extend([
                base_path / model_ref.model_type / model_name,
                base_path / f"{model_ref.model_type}s" / model_name,
                base_path / 'video_models' / model_ref.model_type / model_name,
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
        """Validate a single VideoHelperSuite workflow"""
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

        # Count VideoHelperSuite nodes
        video_nodes_count = sum(1 for node in workflow_data.get('nodes', {}).values()
                              if self._is_video_helper_node(node.get('class_type', '')))

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
            model_references=model_refs,
            video_nodes_count=video_nodes_count
        )

    def validate_all_workflows(self) -> List[ValidationResult]:
        """Validate all discovered VideoHelperSuite workflows"""
        workflows = self.discover_workflows()
        results = []

        print(f"Found {len(workflows)} VideoHelperSuite workflows to validate...")

        for workflow_file in workflows:
            print(f"Validating: {Path(workflow_file).name}")
            result = self.validate_workflow(workflow_file)
            results.append(result)

            # Print summary for this workflow
            video_info = f" ({result.video_nodes_count} VHS nodes)" if result.video_nodes_count > 0 else ""
            if result.missing_models > 0:
                print(f"  ❌ {result.missing_models}/{result.total_models} models missing{video_info}")
            else:
                print(f"  ✅ All {result.total_models} models found{video_info}")

        return results

    def generate_report(self, results: List[ValidationResult], output_file: str = None) -> str:
        """Generate comprehensive validation report"""
        report_lines = [
            "# VideoHelperSuite Workflow Model Validation Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        # Summary statistics
        total_workflows = len(results)
        total_models = sum(r.total_models for r in results)
        total_missing = sum(r.missing_models for r in results)
        total_found = sum(r.found_models for r in results)
        total_vhs_nodes = sum(r.video_nodes_count for r in results)

        report_lines.extend([
            "## Summary",
            f"- **Total Workflows**: {total_workflows}",
            f"- **Total VHS Nodes**: {total_vhs_nodes}",
            f"- **Total Models**: {total_models}",
            f"- **Found Models**: {total_found}",
            f"- **Missing Models**: {total_missing}",
            f"- **Success Rate**: {(total_found/total_models*100):.1f}%" if total_models > 0 else "- **Success Rate**: N/A",
            "",
        ])

        # VHS type breakdown
        if total_models > 0:
            report_lines.append("## VideoHelperSuite Node Types")
            vhs_stats = {}

            for result in results:
                for ref in result.model_references:
                    vhs_type = ref.video_helper_type or 'unknown'
                    if vhs_type not in vhs_stats:
                        vhs_stats[vhs_type] = {'total': 0, 'missing': 0}
                    vhs_stats[vhs_type]['total'] += 1
                    if not ref.exists:
                        vhs_stats[vhs_type]['missing'] += 1

            for vhs_type, stats in sorted(vhs_stats.items()):
                success_rate = (stats['total'] - stats['missing']) / stats['total'] * 100 if stats['total'] > 0 else 0
                report_lines.append(f"- **{vhs_type}**: {stats['total'] - stats['missing']}/{stats['total']} found ({success_rate:.1f}%)")
            report_lines.append("")

        # Missing models catalog
        if total_missing > 0:
            report_lines.append("## Missing Models Catalog")
            missing_by_vhs_type = {}

            for result in results:
                for ref in result.model_references:
                    if not ref.exists:
                        vhs_type = ref.video_helper_type or 'unknown'
                        if vhs_type not in missing_by_vhs_type:
                            missing_by_vhs_type[vhs_type] = {}
                        model_type = ref.model_type
                        if model_type not in missing_by_vhs_type[vhs_type]:
                            missing_by_vhs_type[vhs_type][model_type] = set()
                        missing_by_vhs_type[vhs_type][model_type].add(ref.model_name)

            for vhs_type, types in sorted(missing_by_vhs_type.items()):
                report_lines.extend([
                    f"### {vhs_type.replace('_', ' ').title()}",
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
            vhs_info = f" ({result.video_nodes_count} VHS nodes)" if result.video_nodes_count > 0 else ""

            report_lines.extend([
                f"### {result.workflow_name}{vhs_info} ({status})",
                f"**File**: `{result.workflow_file}`",
                f"**Models**: {result.found_models}/{result.total_models} found",
                ""
            ])

            if result.missing_models > 0:
                report_lines.append("**Missing Models**:")
                for ref in result.model_references:
                    if not ref.exists:
                        vhs_info = f" [{ref.video_helper_type}]" if ref.video_helper_type and ref.video_helper_type != 'unknown' else ""
                        report_lines.append(f"- `{ref.model_name}` ({ref.model_type}){vhs_info}")
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
    analyzer = VideoHelperSuiteAnalyzer(comfyui_path, model_base_paths)

    # Validate all workflows
    results = analyzer.validate_all_workflows()

    # Generate report
    report_file = "/home/ned/ComfyUI-Install/worktrees/video-helper-workflows/video_helper_validation_report.md"
    report_content = analyzer.generate_report(results, report_file)

    # Print summary
    print("\n" + "="*60)
    print("VIDEOHELPER SUITE WORKFLOW VALIDATION SUMMARY")
    print("="*60)
    print(f"Workflows analyzed: {len(results)}")
    print(f"Total VHS nodes: {sum(r.video_nodes_count for r in results)}")
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