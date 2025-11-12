#!/usr/bin/env python3
"""
KJNodes Workflow Model Validator
Specialized agent for analyzing KJNodes workflows and validating model dependencies
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
    kj_node_type: Optional[str] = None  # animation, morph, etc.

@dataclass
class ValidationResult:
    """Represents validation result for a workflow"""
    workflow_file: str
    total_models: int
    missing_models: int
    found_models: int
    model_references: List[ModelReference]
    workflow_name: Optional[str] = None
    kj_nodes_version: Optional[str] = None
    animation_nodes_count: int = 0
    morph_nodes_count: int = 0

class KJNodesAnalyzer:
    """Specialized analyzer for KJNodes workflows"""

    def __init__(self, comfyui_path: str, model_base_paths: List[str]):
        self.comfyui_path = Path(comfyui_path)
        self.model_base_paths = [Path(p) for p in model_base_paths]
        self.supported_extensions = {'.safetensors', '.ckpt', '.pth', '.pt', '.bin', '.onnx'}

    def discover_workflows(self) -> List[str]:
        """Discover KJNodes workflows in the ComfyUI installation"""
        workflow_patterns = [
            "**/kj_*.json",
            "**/KJ_*.json",
            "**/kjnodes_*.json",
            "**/KJNodes_*.json",
            "**/morph_*.json",
            "**/Morph_*.json",
            "**/animation_*.json",
            "**/Animation_*.json"
        ]

        workflows = []
        for pattern in workflow_patterns:
            workflows.extend(glob.glob(str(self.comfyui_path / pattern), recursive=True))

        # Also search in KJNodes custom node directory
        kj_patterns = [
            "custom_nodes/ComfyUI-KJNodes/**/workflows/*.json",
            "custom_nodes/kjnodes/**/workflows/*.json",
            "custom_nodes/ComfyUI-KJNodes/**/examples/*.json",
            "custom_nodes/kjnodes/**/examples/*.json"
        ]

        for pattern in kj_patterns:
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
        """Extract model references from KJNodes workflow"""
        references = []

        if not workflow_data.get('nodes'):
            return references

        animation_nodes_count = 0
        morph_nodes_count = 0

        for node_id, node in workflow_data['nodes'].items():
            node_type = node.get('class_type', '')
            inputs = node.get('inputs', {})

            # Count specialized KJNodes
            if self._is_kj_animation_node(node_type):
                animation_nodes_count += 1
            elif self._is_kj_morph_node(node_type):
                morph_nodes_count += 1

            # KJNodes-specific model patterns
            model_patterns = self._get_kj_nodes_model_patterns(node_type)

            for pattern_info in model_patterns:
                field_name = pattern_info['field']
                model_type = pattern_info['type']
                kj_node_type = pattern_info.get('kj_type', 'unknown')

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
                        kj_node_type=kj_node_type
                    )

                    # Extract additional parameters
                    if 'strength_field' in pattern_info and pattern_info['strength_field'] in inputs:
                        ref.strength = inputs[pattern_info['strength_field']]

                    references.append(ref)

        return references

    def _is_kj_animation_node(self, node_type: str) -> bool:
        """Check if a node is a KJNodes animation node"""
        animation_patterns = [
            'KJ_', 'Animate', 'Animation', 'Keyframe', 'Motion',
            'Interpolate', 'Blend', 'Transition', 'Morph'
        ]

        return any(pattern in node_type for pattern in animation_patterns)

    def _is_kj_morph_node(self, node_type: str) -> bool:
        """Check if a node is a KJNodes morph node"""
        morph_patterns = [
            'Morph', 'Blend', 'Interpolate', 'FaceMorph', 'ShapeMorph',
            'AudioReactive', 'Rhythm', 'Beat', 'Sync'
        ]

        return any(pattern in node_type for pattern in morph_patterns)

    def _get_kj_nodes_model_patterns(self, node_type: str) -> List[Dict]:
        """Get model field patterns for KJNodes"""
        patterns = []

        # KJNodes-specific patterns
        if self._is_kj_animation_node(node_type) or self._is_kj_morph_node(node_type):
            # Animation models
            if 'Animate' in node_type or 'Animation' in node_type:
                patterns.extend([
                    {'field': 'motion_model', 'type': 'motion_model', 'kj_type': 'animation'},
                    {'field': 'animation_model', 'type': 'animation_model', 'kj_type': 'animation'},
                    {'field': 'keyframe_model', 'type': 'keyframe_model', 'kj_type': 'animation'}
                ])

            # Morph and blend models
            if 'Morph' in node_type or 'Blend' in node_type:
                patterns.extend([
                    {'field': 'morph_model', 'type': 'morph_model', 'kj_type': 'morph'},
                    {'field': 'blend_model', 'type': 'blend_model', 'kj_type': 'morph'},
                    {'field': 'shape_model', 'type': 'shape_model', 'kj_type': 'morph'}
                ])

            # Face/feature models
            if 'Face' in node_type or 'Feature' in node_type:
                patterns.extend([
                    {'field': 'face_model', 'type': 'face_model', 'kj_type': 'face'},
                    {'field': 'feature_model', 'type': 'feature_model', 'kj_type': 'face'},
                    {'field': 'landmark_model', 'type': 'landmark_model', 'kj_type': 'face'}
                ])

            # Audio reactive models
            if 'Audio' in node_type or 'Beat' in node_type or 'Rhythm' in node_type:
                patterns.extend([
                    {'field': 'audio_model', 'type': 'audio_model', 'kj_type': 'audio'},
                    {'field': 'beat_detector', 'type': 'beat_detector', 'kj_type': 'audio'},
                    {'field': 'rhythm_model', 'type': 'rhythm_model', 'kj_type': 'audio'}
                ])

        # General model patterns commonly used with KJNodes
        general_patterns = {
            'CheckpointLoaderSimple': [{'field': 'ckpt_name', 'type': 'checkpoint', 'kj_type': 'general'}],
            'VAELoader': [{'field': 'vae_name', 'type': 'vae', 'kj_type': 'general'}],
            'CLIPTextEncode': [{'field': 'clip', 'type': 'clip', 'kj_type': 'general'}],
            'LoraLoader': [
                {'field': 'lora_name', 'type': 'lora', 'kj_type': 'general', 'strength_field': 'strength_model'},
                {'field': 'lora_name', 'type': 'lora', 'kj_type': 'general', 'strength_field': 'strength_clip'}
            ],
            'ControlNetLoader': [{'field': 'control_net_name', 'type': 'controlnet', 'kj_type': 'general'}],
            'UpscaleModelLoader': [{'field': 'model_name', 'type': 'upscale', 'kj_type': 'general'}],
            'StyleModelLoader': [{'field': 'model_name', 'type': 'style_model', 'kj_type': 'general'}],

            # Animation-specific models
            'AnimateDiffLoader': [{'field': 'model_name', 'type': 'animatediff', 'kj_type': 'animation'}],
            'MotionModuleLoader': [{'field': 'model_name', 'type': 'motion_module', 'kj_type': 'animation'}],
            'IPAdapterModelLoader': [{'field': 'model_name', 'type': 'ip_adapter', 'kj_type': 'animation'}],

            # Face and morph models
            'FaceAnalysisLoader': [{'field': 'model_name', 'type': 'face_analysis', 'kj_type': 'morph'}],
            'FaceMorphLoader': [{'field': 'model_name', 'type': 'face_morph', 'kj_type': 'morph'}],
            'ShapePredictorLoader': [{'field': 'model_name', 'type': 'shape_predictor', 'kj_type': 'morph'}],

            # Audio processing models
            'AudioModelLoader': [{'field': 'model_name', 'type': 'audio_model', 'kj_type': 'audio'}],
            'BeatDetectorLoader': [{'field': 'model_name', 'type': 'beat_detector', 'kj_type': 'audio'}],
            'RhythmAnalyzerLoader': [{'field': 'model_name', 'type': 'rhythm_analyzer', 'kj_type': 'audio'}],

            # Super resolution and enhancement
            'RealESRGANLoader': [{'field': 'model_name', 'type': 'real_esrgan', 'kj_type': 'enhancement'}],
            'ESRGANLoader': [{'field': 'model_name', 'type': 'esrgan', 'kj_type': 'enhancement'}],
            'SwinIRLoader': [{'field': 'model_name', 'type': 'swinir', 'kj_type': 'enhancement'}],
        }

        if node_type in general_patterns:
            patterns.extend(general_patterns[node_type])

        return patterns

    def resolve_model_path(self, model_ref: ModelReference) -> Optional[str]:
        """Resolve and validate model file existence"""
        model_name = model_ref.model_name

        # Define search paths based on model type and KJNodes type
        search_paths = []

        # KJNodes-specific paths
        if model_ref.kj_node_type == 'animation':
            search_paths.extend([
                p / 'animation_models' / model_name,
                p / 'animatediff_models' / model_name,
                p / 'motion_modules' / model_name,
                p / 'models' / 'animation' / model_name,
                p / 'models' / 'Motion_Module' / model_name
            ])
        elif model_ref.kj_node_type == 'morph':
            search_paths.extend([
                p / 'morph_models' / model_name,
                p / 'face_models' / model_name,
                p / 'shape_models' / model_name,
                p / 'models' / 'morph' / model_name,
                p / 'models' / 'face_analysis' / model_name
            ])
        elif model_ref.kj_node_type == 'face':
            search_paths.extend([
                p / 'face_models' / model_name,
                p / 'face_analysis' / model_name,
                p / 'landmark_models' / model_name,
                p / 'models' / 'face' / model_name,
                p / 'models' / 'facial_analysis' / model_name
            ])
        elif model_ref.kj_node_type == 'audio':
            search_paths.extend([
                p / 'audio_models' / model_name,
                p / 'beat_detection' / model_name,
                p / 'rhythm_analysis' / model_name,
                p / 'models' / 'audio' / model_name,
                p / 'models' / 'audio_processing' / model_name
            ])

        # Animation and motion specific models
        if model_ref.model_type == 'animatediff':
            search_paths.extend([
                p / 'animatediff_models' / model_name,
                p / 'motion_modules' / model_name,
                p / 'models' / 'animatediff' / model_name,
                p / 'models' / 'Motion_Module' / model_name
            ])
        elif model_ref.model_type == 'motion_module':
            search_paths.extend([
                p / 'motion_modules' / model_name,
                p / 'animatediff_models' / model_name,
                p / 'models' / 'motion' / model_name
            ])

        # Face analysis models
        elif model_ref.model_type in ['face_analysis', 'face_morph', 'shape_predictor']:
            search_paths.extend([
                p / 'face_analysis' / model_name,
                p / 'facial_landmarks' / model_name,
                p / 'shape_predictors' / model_name,
                p / 'models' / 'face_analysis' / model_name
            ])

        # Audio models
        elif model_ref.model_type in ['audio_model', 'beat_detector', 'rhythm_analyzer']:
            search_paths.extend([
                p / 'audio_models' / model_name,
                p / 'beat_detection' / model_name,
                p / 'rhythm_analysis' / model_name,
                p / 'models' / 'audio' / model_name
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

        # Add common model directories
        for base_path in self.model_base_paths:
            search_paths.extend([
                base_path / model_ref.model_type / model_name,
                base_path / f"{model_ref.model_type}s" / model_name,
                base_path / 'animation' / model_ref.model_type / model_name,
                base_path / 'morph' / model_ref.model_type / model_name,
                base_path / 'face' / model_ref.model_type / model_name,
                base_path / 'audio' / model_ref.model_type / model_name,
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
        """Validate a single KJNodes workflow"""
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

        # Count specialized KJNodes
        animation_nodes_count = sum(1 for node in workflow_data.get('nodes', {}).values()
                                  if self._is_kj_animation_node(node.get('class_type', '')))
        morph_nodes_count = sum(1 for node in workflow_data.get('nodes', {}).values()
                              if self._is_kj_morph_node(node.get('class_type', '')))

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
            animation_nodes_count=animation_nodes_count,
            morph_nodes_count=morph_nodes_count
        )

    def validate_all_workflows(self) -> List[ValidationResult]:
        """Validate all discovered KJNodes workflows"""
        workflows = self.discover_workflows()
        results = []

        print(f"Found {len(workflows)} KJNodes workflows to validate...")

        for workflow_file in workflows:
            print(f"Validating: {Path(workflow_file).name}")
            result = self.validate_workflow(workflow_file)
            results.append(result)

            # Print summary for this workflow
            node_info = []
            if result.animation_nodes_count > 0:
                node_info.append(f"{result.animation_nodes_count} anim")
            if result.morph_nodes_count > 0:
                node_info.append(f"{result.morph_nodes_count} morph")

            node_str = f" ({', '.join(node_info)})" if node_info else ""

            if result.missing_models > 0:
                print(f"  ❌ {result.missing_models}/{result.total_models} models missing{node_str}")
            else:
                print(f"  ✅ All {result.total_models} models found{node_str}")

        return results

    def generate_report(self, results: List[ValidationResult], output_file: str = None) -> str:
        """Generate comprehensive validation report"""
        report_lines = [
            "# KJNodes Workflow Model Validation Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        # Summary statistics
        total_workflows = len(results)
        total_models = sum(r.total_models for r in results)
        total_missing = sum(r.missing_models for r in results)
        total_found = sum(r.found_models for r in results)
        total_anim_nodes = sum(r.animation_nodes_count for r in results)
        total_morph_nodes = sum(r.morph_nodes_count for r in results)

        report_lines.extend([
            "## Summary",
            f"- **Total Workflows**: {total_workflows}",
            f"- **Animation Nodes**: {total_anim_nodes}",
            f"- **Morph Nodes**: {total_morph_nodes}",
            f"- **Total Models**: {total_models}",
            f"- **Found Models**: {total_found}",
            f"- **Missing Models**: {total_missing}",
            f"- **Success Rate**: {(total_found/total_models*100):.1f}%" if total_models > 0 else "- **Success Rate**: N/A",
            "",
        ])

        # KJNodes type breakdown
        if total_models > 0:
            report_lines.append("## KJNodes Node Types")
            kj_stats = {}

            for result in results:
                for ref in result.model_references:
                    kj_type = ref.kj_node_type or 'unknown'
                    if kj_type not in kj_stats:
                        kj_stats[kj_type] = {'total': 0, 'missing': 0}
                    kj_stats[kj_type]['total'] += 1
                    if not ref.exists:
                        kj_stats[kj_type]['missing'] += 1

            for kj_type, stats in sorted(kj_stats.items()):
                success_rate = (stats['total'] - stats['missing']) / stats['total'] * 100 if stats['total'] > 0 else 0
                report_lines.append(f"- **{kj_type}**: {stats['total'] - stats['missing']}/{stats['total']} found ({success_rate:.1f}%)")
            report_lines.append("")

        # Missing models catalog
        if total_missing > 0:
            report_lines.append("## Missing Models Catalog")
            missing_by_kj_type = {}

            for result in results:
                for ref in result.model_references:
                    if not ref.exists:
                        kj_type = ref.kj_node_type or 'unknown'
                        if kj_type not in missing_by_kj_type:
                            missing_by_kj_type[kj_type] = {}
                        model_type = ref.model_type
                        if model_type not in missing_by_kj_type[kj_type]:
                            missing_by_kj_type[kj_type][model_type] = set()
                        missing_by_kj_type[kj_type][model_type].add(ref.model_name)

            for kj_type, types in sorted(missing_by_kj_type.items()):
                report_lines.extend([
                    f"### {kj_type.replace('_', ' ').title()}",
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

            node_info = []
            if result.animation_nodes_count > 0:
                node_info.append(f"{result.animation_nodes_count} animation")
            if result.morph_nodes_count > 0:
                node_info.append(f"{result.morph_nodes_count} morph")

            node_str = f" ({', '.join(node_info)})" if node_info else ""

            report_lines.extend([
                f"### {result.workflow_name}{node_str} ({status})",
                f"**File**: `{result.workflow_file}`",
                f"**Models**: {result.found_models}/{result.total_models} found",
                ""
            ])

            if result.missing_models > 0:
                report_lines.append("**Missing Models**:")
                for ref in result.model_references:
                    if not ref.exists:
                        kj_info = f" [{ref.kj_node_type}]" if ref.kj_node_type and ref.kj_node_type != 'unknown' else ""
                        report_lines.append(f"- `{ref.model_name}` ({ref.model_type}){kj_info}")
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
    analyzer = KJNodesAnalyzer(comfyui_path, model_base_paths)

    # Validate all workflows
    results = analyzer.validate_all_workflows()

    # Generate report
    report_file = "/home/ned/ComfyUI-Install/worktrees/kj-nodes-workflows/kj_nodes_validation_report.md"
    report_content = analyzer.generate_report(results, report_file)

    # Print summary
    print("\n" + "="*60)
    print("KJNODES WORKFLOW VALIDATION SUMMARY")
    print("="*60)
    print(f"Workflows analyzed: {len(results)}")
    print(f"Animation nodes: {sum(r.animation_nodes_count for r in results)}")
    print(f"Morph nodes: {sum(r.morph_nodes_count for r in results)}")
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