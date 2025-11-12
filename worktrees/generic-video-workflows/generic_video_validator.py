#!/usr/bin/env python3
"""
Generic Video Workflow Model Validator
Specialized agent for analyzing general/unknown video workflows and validating model dependencies
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
    confidence: float = 1.0  # Confidence level that this is actually a model

@dataclass
class ValidationResult:
    """Represents validation result for a workflow"""
    workflow_file: str
    total_models: int
    missing_models: int
    found_models: int
    model_references: List[ModelReference]
    workflow_name: Optional[str] = None
    video_indicators: List[str] = None
    unknown_nodes: List[str] = None

class GenericVideoAnalyzer:
    """Specialized analyzer for generic/unknown video workflows"""

    def __init__(self, comfyui_path: str, model_base_paths: List[str]):
        self.comfyui_path = Path(comfyui_path)
        self.model_base_paths = [Path(p) for p in model_base_paths]
        self.supported_extensions = {'.safetensors', '.ckpt', '.pth', '.pt', '.bin', '.onnx', '.gguf'}

    def discover_workflows(self) -> List[str]:
        """Discover generic video workflows that don't fit other categories"""
        # First, find all JSON files that might be workflows
        all_workflows = set()

        # Look in common workflow directories
        workflow_dirs = [
            "workflows/**/*.json",
            "custom_nodes/**/workflows/*.json",
            "custom_nodes/**/examples/*.json",
            "*.json"
        ]

        for pattern in workflow_dirs:
            workflows = glob.glob(str(self.comfyui_path / pattern), recursive=True)
            all_workflows.update(workflows)

        # Filter out known categories (LTX, Wan2, VideoHelperSuite, KJNodes)
        filtered_workflows = []
        known_patterns = [
            'ltx_', 'LTX_', 'wan2', 'Wan2', 'video_', 'Video_',
            'vh_', 'VH_', 'kj_', 'KJ_', 'morph_', 'Morph_',
            'animation_', 'Animation_'
        ]

        for workflow in all_workflows:
            workflow_name = Path(workflow).name.lower()
            if not any(pattern.lower() in workflow_name for pattern in known_patterns):
                filtered_workflows.append(workflow)

        return sorted(filtered_workflows)

    def is_video_workflow(self, workflow_data: Dict) -> Tuple[bool, List[str]]:
        """Determine if a workflow is video-related and return indicators"""
        if not workflow_data.get('nodes'):
            return False, []

        video_indicators = []

        # Check node types for video indicators
        video_node_patterns = [
            'video', 'Video', 'animation', 'Animation', 'motion', 'Motion',
            'temporal', 'Temporal', 'sequence', 'Sequence', 'frame', 'Frame',
            'interpolate', 'Interpolate', 'upscale', 'Upscale', 'enhance', 'Enhance',
            'morph', 'Morph', 'blend', 'Blend', 'transition', 'Transition',
            'diffusers', 'Diffusers', 'stablevideo', 'StableVideo',
            'svd', 'SVD', 'zeroscope', 'Zeroscope', 'modelscope', 'ModelScope'
        ]

        for node_id, node in workflow_data['nodes'].items():
            node_type = node.get('class_type', '')

            for pattern in video_node_patterns:
                if pattern.lower() in node_type.lower():
                    video_indicators.append(f"Node: {node_type}")
                    break

        # Check workflow metadata
        workflow_title = workflow_data.get('extra', {}).get('workflow', {}).get('title', '')
        if any(indicator.lower() in workflow_title.lower() for indicator in video_node_patterns):
            video_indicators.append(f"Title: {workflow_title}")

        # Check node connections for video-like patterns
        node_connections = self._analyze_connections(workflow_data)
        if node_connections.get('has_temporal_connections'):
            video_indicators.append("Temporal connections detected")
        if node_connections.get('has_sequence_nodes'):
            video_indicators.append("Sequence nodes detected")
        if node_connections.get('has_frame_processing'):
            video_indicators.append("Frame processing detected")

        # Check for high resolution settings (common in video workflows)
        if node_connections.get('has_video_resolutions'):
            video_indicators.append("Video resolution settings detected")

        is_video = len(video_indicators) >= 2  # Need at least 2 indicators to be considered video

        return is_video, video_indicators

    def _analyze_connections(self, workflow_data: Dict) -> Dict:
        """Analyze node connections for video patterns"""
        if not workflow_data.get('nodes'):
            return {}

        connections = {
            'has_temporal_connections': False,
            'has_sequence_nodes': False,
            'has_frame_processing': False,
            'has_video_resolutions': False
        }

        # Look for common video node connection patterns
        temporal_patterns = ['temporal', 'sequence', 'frame', 'motion']
        sequence_patterns = ['batch', 'sequence', 'repeat', 'interpolate']
        frame_patterns = ['frame', 'video', 'image', 'resize', 'crop']

        for node_id, node in workflow_data['nodes'].items():
            node_type = node.get('class_type', '').lower()
            inputs = node.get('inputs', {})

            # Check for temporal/sequence patterns
            if any(pattern in node_type for pattern in temporal_patterns):
                connections['has_temporal_connections'] = True

            if any(pattern in node_type for pattern in sequence_patterns):
                connections['has_sequence_nodes'] = True

            if any(pattern in node_type for pattern in frame_patterns):
                connections['has_frame_processing'] = True

            # Check for video resolutions (typically > 1024 in one dimension)
            if any(key in inputs for key in ['width', 'height', 'resolution']):
                for key in ['width', 'height']:
                    if key in inputs:
                        try:
                            value = inputs[key]
                            if isinstance(value, (int, float)) and value > 1024:
                                connections['has_video_resolutions'] = True
                        except (ValueError, TypeError):
                            pass

        return connections

    def parse_workflow(self, workflow_file: str) -> Dict:
        """Parse a ComfyUI workflow JSON file"""
        try:
            with open(workflow_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error parsing {workflow_file}: {e}")
            return {}

    def extract_model_references(self, workflow_data: Dict) -> List[ModelReference]:
        """Extract model references from workflow with confidence scoring"""
        references = []

        if not workflow_data.get('nodes'):
            return references

        unknown_nodes = []

        for node_id, node in workflow_data['nodes'].items():
            node_type = node.get('class_type', '')
            inputs = node.get('inputs', {})

            # Check if this is an unknown node type
            if self._is_unknown_node_type(node_type):
                unknown_nodes.append(node_type)

            # Try to extract models using various patterns
            model_refs = self._extract_models_from_node(node_id, node_type, inputs)
            references.extend(model_refs)

        return references

    def _is_unknown_node_type(self, node_type: str) -> bool:
        """Check if node type is unknown/uncategorized"""
        # Known node types that definitely don't use models
        known_non_model_nodes = {
            'CLIPTextEncode', 'CLIPSetLastLayer', 'ConditioningAverage',
            'ConditioningCombine', 'ConditioningConcat', 'ConditioningSetArea',
            'ConditioningSetAreaPercentage', 'ConditioningSetMask',
            'ControlNetApply', 'SaveImage', 'PreviewImage', 'LoadImage',
            'ImageScale', 'ImageUpscale', 'ImageCrop', 'ImagePad',
            'ImageBlend', 'ImageComposite', 'LatentUpscale', 'LatentScale',
            'VAEEncode', 'VAEDecode', 'EmptyLatentImage', 'KSampler',
            'KSamplerAdvanced', 'NoiseInjector', 'RandomNoise',
            'CheckpointsLoaderState', 'CLIPVisionEncode', 'StyleModelApply',
            'ControlNetApplyAdvanced', 'IPAdapterApply', 'AddNoise',
            'PatchModelAddDownscale', 'PatchModelAddUpscale', 'ModelMerge',
            'ModelMergeSimple', 'ModelMergeBlock', 'ModelMergeSubtract',
            'ClipMerge', 'ClipMergeSubtract', 'ClipMergeAdd'
        }

        return node_type not in known_non_model_nodes

    def _extract_models_from_node(self, node_id: str, node_type: str, inputs: Dict) -> List[ModelReference]:
        """Extract models from a specific node with confidence scoring"""
        references = []

        # High confidence patterns (definitely models)
        high_confidence_patterns = {
            'ckpt_name': 'checkpoint',
            'model_name': 'diffusion_model',
            'vae_name': 'vae',
            'lora_name': 'lora',
            'control_net_name': 'controlnet',
            'unet_name': 'unet',
            'text_encoder_name': 'text_encoder',
            'transformer_name': 'transformer',
            'upscale_model_name': 'upscale',
            'style_model_name': 'style_model'
        }

        # Medium confidence patterns (likely models)
        medium_confidence_patterns = {
            'model': 'unknown_model',
            'name': 'unknown_model',
            'filename': 'unknown_model',
            'path': 'unknown_model'
        }

        # Low confidence patterns (could be models)
        low_confidence_patterns = {
            'file': 'possible_model',
            'file_name': 'possible_model',
            'weight': 'possible_model',
            'weights': 'possible_model'
        }

        def process_patterns(patterns: Dict, confidence: float):
            """Process patterns with given confidence level"""
            refs = []
            for field_name, model_type in patterns.items():
                if field_name in inputs:
                    model_value = inputs[field_name]

                    # Handle different input formats
                    if isinstance(model_value, list) and len(model_value) > 0:
                        model_name = str(model_value[0])
                    elif isinstance(model_value, str):
                        model_name = model_value
                    else:
                        continue

                    # Skip empty values and primitives
                    if not model_name or model_name in ['none', 'None', '']:
                        continue

                    # Skip obvious non-model values
                    if self._is_obvious_non_model(model_name):
                        continue

                    ref = ModelReference(
                        model_type=model_type,
                        model_name=model_name,
                        node_id=node_id,
                        node_type=node_type,
                        confidence=confidence
                    )
                    refs.append(ref)

            return refs

        # Process patterns by confidence level
        references.extend(process_patterns(high_confidence_patterns, 1.0))
        references.extend(process_patterns(medium_confidence_patterns, 0.7))
        references.extend(process_patterns(low_confidence_patterns, 0.4))

        return references

    def _is_obvious_non_model(self, value: str) -> bool:
        """Check if a value is obviously not a model name"""
        non_model_patterns = [
            r'^\d+$',  # Just numbers
            r'^[a-fA-F0-9-]{36}$',  # UUID-like
            r'^[a-zA-Z]$',  # Single letters (like node IDs)
            r'^(true|false|on|off|yes|no)$',  # Boolean values
            r'^[0-9.]+$',  # Float values
            r'^#[0-9a-fA-F]+$',  # Color codes
            r'^\d+x\d+$',  # Resolution formats
            r'^(256|512|768|1024|1536|2048)(?:\.0)?$',  # Common resolutions
        ]

        return any(re.match(pattern, value.strip()) for pattern in non_model_patterns)

    def resolve_model_path(self, model_ref: ModelReference) -> Optional[str]:
        """Resolve and validate model file existence"""
        model_name = model_ref.model_name

        # Define search paths based on model type
        search_paths = []

        if model_ref.model_type in ['checkpoint', 'diffusion_model']:
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
        elif model_ref.model_type in ['unknown_model', 'possible_model']:
            # For unknown types, search in multiple directories
            for subdir in ['checkpoints', 'loras', 'vae', 'controlnet', 'upscale_models', 'diffusion_models']:
                search_paths.extend([
                    p / subdir / model_name,
                    p / 'models' / subdir / model_name
                ])

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
        """Validate a single generic video workflow"""
        workflow_data = self.parse_workflow(workflow_file)
        if not workflow_data:
            return ValidationResult(
                workflow_file=workflow_file,
                total_models=0,
                missing_models=0,
                found_models=0,
                model_references=[],
                video_indicators=[],
                unknown_nodes=[]
            )

        # Check if this is actually a video workflow
        is_video, video_indicators = self.is_video_workflow(workflow_data)
        if not is_video:
            return ValidationResult(
                workflow_file=workflow_file,
                total_models=0,
                missing_models=0,
                found_models=0,
                model_references=[],
                video_indicators=video_indicators,
                unknown_nodes=[]
            )

        # Extract workflow metadata
        workflow_name = workflow_data.get('extra', {}).get('workflow', {}).get('title', Path(workflow_file).stem)

        # Extract model references
        model_refs = self.extract_model_references(workflow_data)

        # Get unknown nodes
        unknown_nodes = []
        for node_id, node in workflow_data.get('nodes', {}).items():
            if self._is_unknown_node_type(node.get('class_type', '')):
                unknown_nodes.append(node.get('class_type', ''))

        # Validate model existence
        for ref in model_refs:
            ref.full_path = self.resolve_model_path(ref)
            ref.exists = ref.full_path is not None

        # Calculate statistics (only count high confidence models)
        high_confidence_refs = [ref for ref in model_refs if ref.confidence >= 0.7]
        total_models = len(high_confidence_refs)
        found_models = sum(1 for ref in high_confidence_refs if ref.exists)
        missing_models = total_models - found_models

        return ValidationResult(
            workflow_file=workflow_file,
            workflow_name=workflow_name,
            total_models=total_models,
            missing_models=missing_models,
            found_models=found_models,
            model_references=high_confidence_refs,
            video_indicators=video_indicators,
            unknown_nodes=list(set(unknown_nodes))
        )

    def validate_all_workflows(self) -> List[ValidationResult]:
        """Validate all discovered generic video workflows"""
        workflows = self.discover_workflows()
        results = []
        skipped_count = 0

        print(f"Found {len(workflows)} candidate workflows to analyze...")

        for workflow_file in workflows:
            print(f"Analyzing: {Path(workflow_file).name}")
            result = self.validate_workflow(workflow_file)

            if len(result.video_indicators) == 0:
                skipped_count += 1
                print(f"  ⏭️  Skipped (not video-related)")
                continue

            results.append(result)

            # Print summary for this workflow
            unknown_info = f" ({len(result.unknown_nodes)} unknown)" if result.unknown_nodes else ""
            if result.missing_models > 0:
                print(f"  ❌ {result.missing_models}/{result.total_models} models missing{unknown_info}")
            else:
                print(f"  ✅ All {result.total_models} models found{unknown_info}")

        print(f"\nSkipped {skipped_count} non-video workflows")
        return results

    def generate_report(self, results: List[ValidationResult], output_file: str = None) -> str:
        """Generate comprehensive validation report"""
        report_lines = [
            "# Generic Video Workflow Model Validation Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        # Summary statistics
        total_workflows = len(results)
        total_models = sum(r.total_models for r in results)
        total_missing = sum(r.missing_models for r in results)
        total_found = sum(r.found_models for r in results)
        total_unknown_nodes = sum(len(r.unknown_nodes or []) for r in results)

        report_lines.extend([
            "## Summary",
            f"- **Total Video Workflows**: {total_workflows}",
            f"- **Total Models**: {total_models}",
            f"- **Found Models**: {total_found}",
            f"- **Missing Models**: {total_missing}",
            f"- **Unknown Node Types**: {total_unknown_nodes}",
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
                    f"### {model_type.replace('_', ' ').title()}",
                    ""
                ])
                for model in sorted(models):
                    report_lines.append(f"- {model}")
                report_lines.append("")
            report_lines.append("")

        # Unknown node types analysis
        if total_unknown_nodes > 0:
            report_lines.append("## Unknown Node Types Analysis")
            unknown_by_frequency = {}

            for result in results:
                for unknown_node in result.unknown_nodes or []:
                    unknown_by_frequency[unknown_node] = unknown_by_frequency.get(unknown_node, 0) + 1

            for node_type, frequency in sorted(unknown_by_frequency.items(), key=lambda x: x[1], reverse=True):
                report_lines.append(f"- **{node_type}**: Found in {frequency} workflow(s)")
            report_lines.append("")
            report_lines.append("⚠️  Unknown node types may require custom node installations")
            report_lines.append("")

        # Workflow details
        report_lines.append("## Workflow Details")
        report_lines.append("")

        for result in sorted(results, key=lambda r: r.missing_models, reverse=True):
            status = "✅ COMPLETE" if result.missing_models == 0 else f"❌ {result.missing_models} MISSING"
            unknown_info = f" ({len(result.unknown_nodes or [])} unknown)" if result.unknown_nodes else ""

            report_lines.extend([
                f"### {result.workflow_name}{unknown_info} ({status})",
                f"**File**: `{result.workflow_file}`",
                f"**Models**: {result.found_models}/{result.total_models} found",
                ""
            ])

            # Show video indicators
            if result.video_indicators:
                report_lines.append("**Video Indicators**:")
                for indicator in result.video_indicators[:5]:  # Limit to first 5
                    report_lines.append(f"- {indicator}")
                if len(result.video_indicators) > 5:
                    report_lines.append(f"- ... and {len(result.video_indicators) - 5} more")
                report_lines.append("")

            # Show unknown nodes
            if result.unknown_nodes:
                report_lines.append("**Unknown Node Types**:")
                for node in sorted(set(result.unknown_nodes))[:10]:  # Limit to first 10
                    report_lines.append(f"- {node}")
                if len(set(result.unknown_nodes)) > 10:
                    report_lines.append(f"- ... and {len(set(result.unknown_nodes)) - 10} more")
                report_lines.append("")

            if result.missing_models > 0:
                report_lines.append("**Missing Models**:")
                for ref in result.model_references:
                    if not ref.exists:
                        confidence_info = f" ({ref.confidence:.1f} confidence)" if ref.confidence < 1.0 else ""
                        report_lines.append(f"- `{ref.model_name}` ({ref.model_type}){confidence_info}")
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
    analyzer = GenericVideoAnalyzer(comfyui_path, model_base_paths)

    # Validate all workflows
    results = analyzer.validate_all_workflows()

    # Generate report
    report_file = "/home/ned/ComfyUI-Install/worktrees/generic-video-workflows/generic_video_validation_report.md"
    report_content = analyzer.generate_report(results, report_file)

    # Print summary
    print("\n" + "="*60)
    print("GENERIC VIDEO WORKFLOW VALIDATION SUMMARY")
    print("="*60)
    print(f"Video workflows analyzed: {len(results)}")
    print(f"Total models needed: {sum(r.total_models for r in results)}")
    print(f"Models found: {sum(r.found_models for r in results)}")
    print(f"Models missing: {sum(r.missing_models for r in results)}")
    print(f"Unknown node types: {sum(len(r.unknown_nodes or []) for r in results)}")

    if results:
        missing_count = sum(r.missing_models for r in results)
        if missing_count > 0:
            print(f"\n⚠️  {missing_count} models are missing!")
            print(f"📄 Detailed report: {report_file}")
        else:
            print(f"\n✅ All models are available!")

if __name__ == "__main__":
    main()