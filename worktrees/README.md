# Video Workflow Validation Worktrees

This directory contains the GitHub worktree structure for parallel video workflow model validation using Claude Flow coordination.

## Worktree Structure

```
worktrees/
├── ltx-workflows/           # LTX video workflow validation
├── wan2-workflows/          # Wan2 video workflow validation
├── video-helper-workflows/  # VideoHelperSuite workflow validation
├── kj-nodes-workflows/      # KJNodes workflow validation
└── generic-video-workflows/ # Generic/unknown video workflow validation
```

## Worktree Details

### ltx-workflows
- **Branch**: `ltx-video-validation`
- **Port**: 8188
- **Validator**: `ltx_workflow_validator.py`
- **Specialization**: LTX video generation workflows, checkpoints, LoRAs, VAEs

### wan2-workflows
- **Branch**: `wan2-video-validation`
- **Port**: 8189
- **Validator**: `wan2_workflow_validator.py`
- **Specialization**: Wan2 video models, transformers, camera controls, fun controls

### video-helper-workflows
- **Branch**: `video-helper-validation`
- **Port**: 8190
- **Validator**: `video_helper_suite_validator.py`
- **Specialization**: VideoHelperSuite nodes, video loading/saving, enhancement

### kj-nodes-workflows
- **Branch**: `kj-nodes-validation`
- **Port**: 8191
- **Validator**: `kj_nodes_validator.py`
- **Specialization**: KJNodes animation, morph, audio-reactive workflows

### generic-video-workflows
- **Branch**: `generic-video-validation`
- **Port**: 8192
- **Validator**: `generic_video_validator.py`
- **Specialization**: Unknown/fallback video workflows with intelligent detection

## Claude Flow Integration

The system uses Claude Flow mesh topology for optimal parallel processing:

```python
# Initialize mesh topology
mcp__claude_flow__swarm_init(
    topology="mesh",
    maxAgents=12,
    strategy="adaptive"
)
```

## Parallel Execution Strategy

1. **High Priority**: LTX and Wan2 workflows (most common video models)
2. **Medium Priority**: VideoHelperSuite and KJNodes (specialized video nodes)
3. **Low Priority**: Generic workflows (unknown/fallback patterns)

## Model Path Resolution

Each validator searches for models in multiple locations:

- `/home/ned/ComfyUI-Install/models/`
- `/home/ned/Models/`
- `/home/ned/Projects/AI_ML/SwarmUI/models/`
- ComfyUI standard directories (checkpoints, loras, vae, etc.)

## Usage

### Individual Validation
```bash
cd worktrees/ltx-workflows
python ltx_workflow_validator.py
```

### Parallel Orchestrated Validation
```bash
cd /home/ned/ComfyUI-Install
python video_workflow_orchestrator.py
```

## Report Locations

- Individual worktree reports: `worktrees/*/validation_report.md`
- Comprehensive report: `/home/ned/ComfyUI-Install/validation_reports/comprehensive_validation_report_YYYYMMDD_HHMMSS.md`

## Agent Capabilities

Each worktree contains specialized agents with these capabilities:

### Video Analysis Agents
- JSON workflow parsing
- Model reference extraction
- File system validation
- Path resolution

### Model Validation Agents
- Existence checking
- Format validation
- Compatibility verification
- Alternative location search

### Reporting Agents
- Markdown generation
- Statistics aggregation
- Missing model cataloging
- Performance analysis

## Performance Optimization

- **Parallel Processing**: Up to 4 concurrent validators
- **Intelligent Caching**: Model path caching for faster subsequent runs
- **Prioritized Execution**: High-value workflows analyzed first
- **Adaptive Scaling**: Claude Flow coordinates agent allocation

## Error Handling

- Graceful fallback when Claude Flow unavailable
- Individual worktree isolation prevents cascading failures
- Comprehensive error reporting with actionable recommendations
- Automatic retry mechanisms for transient issues

## Integration Points

### Claude Flow Swarm
- **WorkflowValidationCoordinator**: Central orchestration
- **ModelFileValidator**: Cross-worktree model validation
- **WorkTreeCoordinator**: Git worktree management
- **ReportGenerator**: Unified reporting

### File System Integration
- Symbolic link following for model aliases
- Multiple model directory support
- SwarmUI path compatibility
- Automatic path template generation

This architecture provides maximum parallel processing efficiency while maintaining comprehensive coverage of all video workflow types in the ComfyUI ecosystem.