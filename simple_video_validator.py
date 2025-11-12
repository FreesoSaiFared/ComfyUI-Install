#!/usr/bin/env python3
"""
Simple Video Workflow Model Validator
Direct validation of video workflows for missing model files
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime

class SimpleVideoValidator:
    def __init__(self, comfyui_path: str = "/home/ned/ComfyUI-Install/ComfyUI"):
        self.comfyui_path = Path(comfyui_path)
        self.model_paths = [
            self.comfyui_path / "models",
            Path("/home/ned/Models"),
            Path("/home/ned/Projects/AI_ML/SwarmUI/models")
        ]

    def parse_workflow(self, workflow_file: Path) -> Dict[str, Any]:
        """Parse a ComfyUI workflow JSON file and handle different formats"""
        try:
            with open(workflow_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle different workflow formats
            if isinstance(data, list):
                # API format - list of nodes
                nodes = {str(i): node for i, node in enumerate(data)}
            elif isinstance(data, dict):
                if 'nodes' in data:
                    # Standard format with 'nodes' key
                    nodes = data['nodes']
                elif 'extra' in data and 'ds' in data:
                    # Newer API format
                    nodes = {str(i): node for i, node in enumerate(data.get('extra', {}).get('ds', {}).get('nodes', []))}
                else:
                    # Fallback - try to find nodes in different keys
                    nodes = data.get('nodes', {})
            else:
                nodes = {}

            return {
                'nodes': nodes,
                'format': 'list' if isinstance(data, list) else 'dict',
                'raw_data': data
            }

        except Exception as e:
            print(f"Error parsing {workflow_file}: {e}")
            return {'nodes': {}, 'format': 'error', 'raw_data': {}}

    def extract_model_references(self, workflow_data: Dict) -> List[Dict[str, Any]]:
        """Extract model references from workflow nodes"""
        models = []
        nodes = workflow_data.get('nodes', {})

        for node_id, node in nodes.items():
            if not isinstance(node, dict):
                continue

            node_type = node.get('type', '')
            node_inputs = node.get('inputs', {})

            # Look for model inputs
            for input_name, input_value in node_inputs.items():
                model_info = None

                # Handle different model reference formats
                if isinstance(input_value, list) and len(input_value) >= 2:
                    # Standard format: [folder_name, filename, ...]
                    if isinstance(input_value[0], str) and isinstance(input_value[1], str):
                        model_info = {
                            'folder': input_value[0],
                            'filename': input_value[1],
                            'node_id': node_id,
                            'node_type': node_type,
                            'input_name': input_name
                        }
                elif isinstance(input_value, dict):
                    # Alternative format: {folder: ..., filename: ...}
                    folder = input_value.get('folder') or input_value.get('directory')
                    filename = input_value.get('filename') or input_value.get('file') or input_value.get('name')
                    if folder and filename:
                        model_info = {
                            'folder': folder,
                            'filename': filename,
                            'node_id': node_id,
                            'node_type': node_type,
                            'input_name': input_name
                        }
                elif isinstance(input_value, str) and '.' in input_value:
                    # String format - might be a direct filename
                    if any(input_value.lower().endswith(ext) for ext in ['.safetensors', '.ckpt', '.pth', '.pt', '.bin']):
                        model_info = {
                            'folder': 'unknown',
                            'filename': input_value,
                            'node_id': node_id,
                            'node_type': node_type,
                            'input_name': input_name
                        }

                if model_info:
                    # Categorize model type
                    folder_lower = model_info['folder'].lower()
                    filename_lower = model_info['filename'].lower()

                    if any(x in folder_lower for x in ['checkpoint', 'checkpoints', 'model']):
                        model_info['model_type'] = 'checkpoint'
                    elif 'lora' in folder_lower or 'lora' in filename_lower:
                        model_info['model_type'] = 'lora'
                    elif 'vae' in folder_lower or 'vae' in filename_lower:
                        model_info['model_type'] = 'vae'
                    elif 'controlnet' in folder_lower or 'control' in filename_lower:
                        model_info['model_type'] = 'controlnet'
                    elif 'upscale' in folder_lower or 'esrgan' in folder_lower:
                        model_info['model_type'] = 'upscale'
                    else:
                        model_info['model_type'] = 'other'

                    models.append(model_info)

        return models

    def check_model_exists(self, model_info: Dict[str, Any]) -> Tuple[bool, List[Path]]:
        """Check if a model file exists in any of the configured paths"""
        found_paths = []
        folder = model_info['folder']
        filename = model_info['filename']

        for model_path in self.model_paths:
            if not model_path.exists():
                continue

            # Direct path check
            direct_path = model_path / folder / filename
            if direct_path.exists():
                found_paths.append(direct_path)
                continue

            # Try common folder variations
            folder_variations = [
                folder,
                folder.lower(),
                folder.replace('_', '-'),
                folder.replace('-', '_'),
            ]

            for folder_var in folder_variations:
                check_path = model_path / folder_var / filename
                if check_path.exists():
                    found_paths.append(check_path)
                    break

            # Try recursive search for exact filename
            if not found_paths:
                try:
                    for found_file in model_path.rglob(filename):
                        if found_file.is_file():
                            found_paths.append(found_file)
                            break
                except Exception:
                    pass  # Skip if recursive search fails

        return len(found_paths) > 0, found_paths

    def validate_video_workflow(self, workflow_file: Path) -> Dict[str, Any]:
        """Validate a single video workflow file"""
        print(f"  Validating: {workflow_file.name}")

        # Parse workflow
        workflow_data = self.parse_workflow(workflow_file)

        # Extract model references
        models = self.extract_model_references(workflow_data)

        # Check if each model exists
        results = {
            'workflow_file': str(workflow_file),
            'total_models': len(models),
            'found_models': 0,
            'missing_models': 0,
            'models_detail': []
        }

        for model_info in models:
            exists, found_paths = self.check_model_exists(model_info)

            model_result = {
                **model_info,
                'exists': exists,
                'found_paths': [str(p) for p in found_paths]
            }

            results['models_detail'].append(model_result)

            if exists:
                results['found_models'] += 1
            else:
                results['missing_models'] += 1

        return results

    def find_video_workflows(self) -> List[Path]:
        """Find all video-related workflow files"""
        workflows = []

        # Main workflows directory
        main_workflows = [
            self.comfyui_path / "workflows" / "ltx_text2video_basic.json",
            self.comfyui_path / "workflows" / "ltx_rtx3060_final_test.json",
            self.comfyui_path / "workflows" / "ltx_rtx3060_optimized.json",
            self.comfyui_path / "workflows" / "wan2_text2video_rtx3060.json",
            self.comfyui_path / "workflows" / "wan2_image2video_rtx3060.json",
        ]

        workflows.extend([w for w in main_workflows if w.exists()])

        # VideoHelperSuite workflows
        vh_dir = self.comfyui_path / "custom_nodes" / "comfyui-videohelpersuite"
        if vh_dir.exists():
            workflows.extend(vh_dir.glob("tests/*.json"))
            workflows.extend(vh_dir.glob("video_formats/*.json"))

        # KJNodes video workflows
        kj_dir = self.comfyui_path / "custom_nodes" / "comfyui-kjnodes"
        if kj_dir.exists():
            workflows.extend(kj_dir.glob("example_workflows/*video*.json"))
            workflows.extend(kj_dir.glob("example_workflows/leapfusion_*.json"))

        return sorted(list(set(workflows)))

    def validate_all_workflows(self) -> Dict[str, Any]:
        """Validate all video workflows"""
        print("🎬 Simple Video Workflow Model Validator")
        print("=" * 50)

        # Find all video workflows
        workflows = self.find_video_workflows()
        print(f"📁 Found {len(workflows)} video workflows")

        if not workflows:
            print("❌ No video workflows found!")
            return {}

        # Validate each workflow
        all_results = []

        for workflow_file in workflows:
            try:
                result = self.validate_video_workflow(workflow_file)
                all_results.append(result)

                # Print summary for this workflow
                if result['missing_models'] == 0:
                    print(f"    ✅ All {result['total_models']} models found")
                else:
                    print(f"    ⚠️  {result['missing_models']}/{result['total_models']} models missing")

            except Exception as e:
                print(f"    ❌ Error: {e}")
                all_results.append({
                    'workflow_file': str(workflow_file),
                    'error': str(e),
                    'total_models': 0,
                    'found_models': 0,
                    'missing_models': 0
                })

        # Generate summary
        total_workflows = len(all_results)
        total_models = sum(r.get('total_models', 0) for r in all_results)
        total_found = sum(r.get('found_models', 0) for r in all_results)
        total_missing = sum(r.get('missing_models', 0) for r in all_results)

        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_workflows': total_workflows,
            'total_models': total_models,
            'found_models': total_found,
            'missing_models': total_missing,
            'success_rate': (total_found / total_models * 100) if total_models > 0 else 0,
            'workflows': all_results
        }

        # Print final summary
        print("\n" + "=" * 50)
        print("📊 VALIDATION SUMMARY")
        print("=" * 50)
        print(f"Workflows analyzed: {total_workflows}")
        print(f"Total models needed: {total_models}")
        print(f"Models found: {total_found}")
        print(f"Models missing: {total_missing}")
        print(f"Success rate: {summary['success_rate']:.1f}%")

        # Print missing models details
        missing_models = []
        for result in all_results:
            if 'models_detail' in result:
                for model in result['models_detail']:
                    if not model['exists']:
                        missing_models.append(model)

        if missing_models:
            print(f"\n🚨 MISSING MODELS ({len(missing_models)}):")
            for i, model in enumerate(missing_models, 1):
                print(f"  {i}. {model['filename']}")
                print(f"     Folder: {model['folder']}")
                print(f"     Type: {model['model_type']}")
                print(f"     Workflow: {Path(model.get('workflow_file', 'unknown')).name}")
                print()

        return summary

def main():
    """Main execution"""
    validator = SimpleVideoValidator()

    try:
        results = validator.validate_all_workflows()

        # Save results
        if results:
            output_file = Path("/home/ned/ComfyUI-Install/video_validation_results.json")
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Results saved to: {output_file}")

        return 0 if results.get('missing_models', 0) == 0 else 1

    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())