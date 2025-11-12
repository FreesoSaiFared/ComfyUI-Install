#!/usr/bin/env python3
"""
Proper Video Workflow Model Validator
Handles ComfyUI workflow format correctly and validates model files
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime

class ProperVideoValidator:
    def __init__(self, comfyui_path: str = "/home/ned/ComfyUI-Install/ComfyUI"):
        self.comfyui_path = Path(comfyui_path)
        self.model_paths = [
            self.comfyui_path / "models",
            Path("/home/ned/Models"),
            Path("/home/ned/Projects/AI_ML/SwarmUI/models")
        ]

    def parse_workflow(self, workflow_file: Path) -> Dict[str, Any]:
        """Parse ComfyUI workflow and extract node data"""
        try:
            with open(workflow_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            nodes = {}

            # Handle different ComfyUI workflow formats
            if 'nodes' in data:
                # Standard format - nodes is a list
                for node in data['nodes']:
                    if isinstance(node, dict) and 'id' in node:
                        nodes[str(node['id'])] = node
            elif isinstance(data, list):
                # API format - list of nodes directly
                for i, node in enumerate(data):
                    if isinstance(node, dict):
                        nodes[str(i)] = node
            else:
                # Try to find nodes in other structures
                for key, value in data.items():
                    if isinstance(value, list) and value and isinstance(value[0], dict) and 'id' in value[0]:
                        for node in value:
                            if isinstance(node, dict) and 'id' in node:
                                nodes[str(node['id'])] = node

            return {
                'nodes': nodes,
                'total_nodes': len(nodes),
                'format': 'comfyui_standard' if 'nodes' in data else 'api_format'
            }

        except Exception as e:
            print(f"Error parsing {workflow_file}: {e}")
            return {'nodes': {}, 'total_nodes': 0, 'format': 'error'}

    def extract_model_references(self, workflow_data: Dict) -> List[Dict[str, Any]]:
        """Extract model references from workflow nodes"""
        models = []
        nodes = workflow_data.get('nodes', {})

        for node_id, node in nodes.items():
            if not isinstance(node, dict):
                continue

            node_type = node.get('type', '')

            # Check widgets_values for model references
            widgets_values = node.get('widgets_values', [])
            if widgets_values:
                for i, value in enumerate(widgets_values):
                    if isinstance(value, str) and self.is_model_filename(value):
                        model_info = {
                            'filename': value,
                            'node_id': node_id,
                            'node_type': node_type,
                            'source': 'widgets_values',
                            'index': i
                        }

                        # Try to determine model type from node type and context
                        model_info['model_type'] = self.determine_model_type(node_type, value)
                        model_info['folder'] = self.guess_model_folder(model_info['model_type'], value)

                        models.append(model_info)

            # Check inputs for model references
            inputs = node.get('inputs', [])
            if inputs:
                for input_info in inputs:
                    if isinstance(input_info, dict):
                        # Some inputs might contain model info directly
                        for key, value in input_info.items():
                            if isinstance(value, str) and self.is_model_filename(value):
                                model_info = {
                                    'filename': value,
                                    'node_id': node_id,
                                    'node_type': node_type,
                                    'source': 'inputs',
                                    'input_key': key
                                }

                                model_info['model_type'] = self.determine_model_type(node_type, value)
                                model_info['folder'] = self.guess_model_folder(model_info['model_type'], value)

                                models.append(model_info)

        return models

    def is_model_filename(self, filename: str) -> bool:
        """Check if a filename looks like a model file"""
        model_extensions = ['.safetensors', '.ckpt', '.pth', '.pt', '.bin', '.onnx']
        filename_lower = filename.lower()
        return any(filename_lower.endswith(ext) for ext in model_extensions)

    def determine_model_type(self, node_type: str, filename: str) -> str:
        """Determine model type based on node type and filename"""
        node_type_lower = node_type.lower()
        filename_lower = filename.lower()

        if 'ltx' in node_type_lower or 'ltx' in filename_lower:
            return 'ltx_video'
        elif 'wan2' in filename_lower or 'wan' in node_type_lower:
            return 'wan2_video'
        elif 'checkpoint' in node_type_lower:
            return 'checkpoint'
        elif 'lora' in node_type_lower or 'lora' in filename_lower:
            return 'lora'
        elif 'vae' in node_type_lower:
            return 'vae'
        elif 'clip' in node_type_lower:
            return 'clip'
        elif 'controlnet' in node_type_lower:
            return 'controlnet'
        elif 'upscale' in node_type_lower or 'esrgan' in filename_lower:
            return 'upscale'
        else:
            return 'unknown'

    def guess_model_folder(self, model_type: str, filename: str) -> str:
        """Guess the most likely folder for a model type"""
        folder_map = {
            'ltx_video': 'checkpoints',
            'wan2_video': 'checkpoints',
            'checkpoint': 'checkpoints',
            'lora': 'loras',
            'vae': 'vae',
            'clip': 'clip',
            'controlnet': 'controlnet',
            'upscale': 'upscale_models'
        }
        return folder_map.get(model_type, 'checkpoints')

    def check_model_exists(self, model_info: Dict[str, Any]) -> Tuple[bool, List[Path]]:
        """Check if a model file exists in any of the configured paths"""
        filename = model_info['filename']
        found_paths = []

        for model_path in self.model_paths:
            if not model_path.exists():
                continue

            # Check in expected folder first
            expected_folder = model_info.get('folder', 'checkpoints')
            direct_path = model_path / expected_folder / filename
            if direct_path.exists():
                found_paths.append(direct_path)
                continue

            # Try common folder variations
            folder_variations = [
                'checkpoints',
                'loras',
                'vae',
                'clip',
                'controlnet',
                'upscale_models',
                'unet',
                'models'
            ]

            for folder in folder_variations:
                check_path = model_path / folder / filename
                if check_path.exists():
                    found_paths.append(check_path)
                    break

            # If not found, try recursive search (limited depth)
            if not found_paths:
                try:
                    for folder in ['checkpoints', 'loras', 'vae']:
                        search_path = model_path / folder
                        if search_path.exists():
                            for found_file in search_path.rglob(filename):
                                if found_file.is_file():
                                    found_paths.append(found_file)
                                    break
                            if found_paths:
                                break
                except Exception:
                    pass  # Skip if recursive search fails

        return len(found_paths) > 0, found_paths

    def validate_video_workflow(self, workflow_file: Path) -> Dict[str, Any]:
        """Validate a single video workflow file"""
        print(f"  🔍 Analyzing: {workflow_file.name}")

        # Parse workflow
        workflow_data = self.parse_workflow(workflow_file)

        if workflow_data['total_nodes'] == 0:
            return {
                'workflow_file': str(workflow_file),
                'total_nodes': 0,
                'total_models': 0,
                'found_models': 0,
                'missing_models': 0,
                'models_detail': [],
                'error': 'No valid nodes found in workflow'
            }

        # Extract model references
        models = self.extract_model_references(workflow_data)

        # Check if each model exists
        results = {
            'workflow_file': str(workflow_file),
            'total_nodes': workflow_data['total_nodes'],
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

    def is_video_workflow(self, workflow_file: Path) -> bool:
        """Check if a workflow is likely video-related"""
        filename_lower = workflow_file.name.lower()

        # Check filename for video indicators
        video_keywords = ['video', 'ltx', 'wan', 'animation', 'motion', 'frames']
        if any(keyword in filename_lower for keyword in video_keywords):
            return True

        # For format files, check if they're in video format directories
        if 'video' in str(workflow_file).lower():
            return True

        return False

    def find_video_workflows(self) -> List[Path]:
        """Find all video-related workflow files"""
        workflows = []

        # Main workflows directory - check for video workflows
        main_workflows = list(self.comfyui_path.glob("workflows/*.json"))
        for workflow in main_workflows:
            if self.is_video_workflow(workflow):
                workflows.append(workflow)

        # VideoHelperSuite workflows - all are video-related
        vh_dir = self.comfyui_path / "custom_nodes" / "comfyui-videohelpersuite"
        if vh_dir.exists():
            workflows.extend(vh_dir.glob("tests/*.json"))
            workflows.extend(vh_dir.glob("video_formats/*.json"))

        # KJNodes workflows - filter for video-related
        kj_dir = self.comfyui_path / "custom_nodes" / "comfyui-kjnodes"
        if kj_dir.exists():
            kj_workflows = list(kj_dir.glob("example_workflows/*.json"))
            for workflow in kj_workflows:
                if self.is_video_workflow(workflow):
                    workflows.append(workflow)

        return sorted(list(set(workflows)))

    def validate_all_workflows(self) -> Dict[str, Any]:
        """Validate all video workflows"""
        print("🎬 Proper Video Workflow Model Validator")
        print("=" * 60)

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
                if result.get('error'):
                    print(f"    ❌ {result['error']}")
                elif result['missing_models'] == 0:
                    print(f"    ✅ All {result['total_models']} models found")
                else:
                    print(f"    ⚠️  {result['missing_models']}/{result['total_models']} models missing")

            except Exception as e:
                print(f"    💥 Unexpected error: {e}")
                all_results.append({
                    'workflow_file': str(workflow_file),
                    'error': str(e),
                    'total_nodes': 0,
                    'total_models': 0,
                    'found_models': 0,
                    'missing_models': 0
                })

        # Generate summary
        total_workflows = len(all_results)
        total_nodes = sum(r.get('total_nodes', 0) for r in all_results)
        total_models = sum(r.get('total_models', 0) for r in all_results)
        total_found = sum(r.get('found_models', 0) for r in all_results)
        total_missing = sum(r.get('missing_models', 0) for r in all_results)

        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_workflows': total_workflows,
            'total_nodes': total_nodes,
            'total_models': total_models,
            'found_models': total_found,
            'missing_models': total_missing,
            'success_rate': (total_found / total_models * 100) if total_models > 0 else 0,
            'workflows': all_results
        }

        # Print final summary
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Workflows analyzed: {total_workflows}")
        print(f"Total nodes processed: {total_nodes}")
        print(f"Total models needed: {total_models}")
        print(f"Models found: {total_found}")
        print(f"Models missing: {total_missing}")
        if total_models > 0:
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
            print("-" * 40)
            for i, model in enumerate(missing_models, 1):
                print(f"  {i}. {model['filename']}")
                print(f"     Type: {model['model_type']}")
                print(f"     Expected folder: {model['folder']}")
                print(f"     Node: {model['node_type']} (ID: {model['node_id']})")
                print(f"     Workflow: {Path(model.get('workflow_file', 'unknown')).name}")
                print()

        return summary

def main():
    """Main execution"""
    validator = ProperVideoValidator()

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