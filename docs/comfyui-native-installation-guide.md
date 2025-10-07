# ComfyUI Native Installation Guide

## Overview

This document describes the complete native installation of ComfyUI on Ubuntu Server with RTX 3060 GPU, featuring an 8-agent execution model using Claude Code and Claude Flow orchestration.

## Installation Approach

### 8-Agent Execution Model

The installation was executed using a specialized agent-based approach with the following roles:

1. **Environment Specialist** - System prerequisites and dependencies
2. **Repository Manager** - ComfyUI source code management
3. **Python Environment Expert** - Virtual environment and PyTorch setup
4. **Extension Manager** - ComfyUI-Manager and custom nodes
5. **File System Architect** - Model directory structure and paths
6. **Configuration Engineer** - YAML configuration and model mapping
7. **Operations Specialist** - Startup scripts and process management
8. **Systems Administrator** - Service creation and monitoring

### Key Directories

```
/home/ned/ComfyUI-Install/
├── ComfyUI/                 # Main ComfyUI installation
│   ├── venv/               # Python virtual environment
│   ├── custom_nodes/       # ComfyUI-Manager and extensions
│   ├── extra_model_paths.yaml  # Model path configuration
│   └── start_comfyui.sh   # Startup script
├── Models/                 # Centralized model storage
│   ├── checkpoints/        # SD checkpoints
│   ├── vae/               # VAE files
│   ├── loras/             # LoRA models
│   ├── upscale_models/    # Upscaling models
│   ├── embeddings/       # Text embeddings
│   ├── controlnet/        # ControlNet models
│   ├── clip/              # CLIP models
│   ├── clip_vision/       # CLIP vision models
│   └── configs/           # Model configs
├── docs/                   # Documentation
└── logs/                   # System logs
```

## Configuration Strategy

### Central Model Management

The installation uses a centralized model storage approach with `/home/ned/Models` as the primary location. This enables:

- **Single Source of Truth**: All AI tools access models from one location
- **Storage Efficiency**: No duplicate model files across different AI applications
- **Consistent Organization**: Standardized folder structure across all AI tools

### Model Path Configuration

The `extra_model_paths.yaml` file maps the central model directory to ComfyUI's expected structure:

```yaml
central_models:
  base_path: /home/ned/Models
  checkpoints: checkpoints
  vae: vae
  loras: loras
  upscale_models: upscale_models
  embeddings: embeddings
  controlnet: controlnet
  clip: clip
  clip_vision: clip_vision
  configs: configs
```

### SwarmUI Integration

The installation is designed to integrate with existing SwarmUI installations by:

1. **Path Mapping**: SwarmUI uses different folder names (e.g., "Stable-diffusion" vs "checkpoints")
2. **Symbolic Links**: Optional symlinks for backward compatibility
3. **Model Discovery**: Automatic detection and mapping of existing models

### GPU Optimization

RTX 3060 specific optimizations:
- **FP16 VAE**: `--fp16-vae` flag for reduced memory usage
- **Normal VRAM**: `--normalvram` flag for optimal memory management
- **CUDA 12.1**: Compatible with NVIDIA driver 575.57.08

## Technical Implementation

### Python Environment

```bash
# Clean Python 3.10 environment
python3.10 -m venv venv
source venv/bin/activate

# PyTorch with CUDA 12.1 support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Startup Script

```bash
#!/bin/bash
cd /home/ned/ComfyUI-Install/ComfyUI

# Optimized for RTX 3060 with 12GB VRAM
/home/ned/ComfyUI-Install/ComfyUI/venv/bin/python main.py \
    --listen 0.0.0.0 \
    --port 8188 \
    --fp16-vae \
    --normalvram \
    --extra-model-paths-config extra_model_paths.yaml
```

### Systemd Service

```ini
[Unit]
Description=ComfyUI Service
After=network.target

[Service]
User=ned
WorkingDirectory=/home/ned/ComfyUI-Install/ComfyUI
ExecStart=/home/ned/ComfyUI-Install/ComfyUI/start_comfyui.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Claude Code & Claude Flow Configuration

### Claude Code Setup

Claude Code is configured as the primary execution environment with:

**Project Instructions** (`/home/ned/CLAUDE.md`):
- Agent-based execution model
- Concurrent operation requirements
- File organization rules
- Safety and validation protocols

**Key Features**:
- **Task Tool**: Primary agent spawning mechanism
- **Concurrent Execution**: All operations in parallel within single messages
- **File Management**: Organized subdirectory structure
- **Safety Validation**: Pre-operation checks and reviews

### Claude Flow Integration

Claude Flow provides orchestration and coordination:

**MCP Server Configuration**:
```bash
claude mcp add claude-flow npx claude-flow@alpha mcp start
```

**Agent Coordination**:
- **Swarm Initialization**: Topology setup and agent definition
- **Task Orchestration**: High-level workflow management
- **Memory Management**: Cross-session state persistence
- **Hooks Integration**: Safety and validation automation

### Worktree Architecture

The installation uses a worktree-based approach:

1. **trees/env-setup** (Port 8188): Environment and dependencies
2. **trees/models-integ** (Port 8189): Model path integration
3. **trees/ops-maint** (Port 8190): Operations and maintenance

### Agent Coordination Protocol

All agents follow a standardized protocol:

**Pre-Task**:
```bash
npx claude-flow@alpha hooks pre-task --description "[task]"
npx claude-flow@alpha hooks session-restore --session-id "swarm-[id]"
```

**During Task**:
```bash
npx claude-flow@alpha hooks post-edit --file "[file]" --memory-key "swarm/[agent]/[step]"
npx claude-flow@alpha hooks notify --message "[what was done]"
```

**Post-Task**:
```bash
npx claude-flow@alpha hooks post-task --task-id "[task]"
npx claude-flow@alpha hooks session-end --export-metrics true
```

## Network Configuration

### Firewall Setup

```bash
# Allow ComfyUI port
sudo ufw allow 8188/tcp

# Verify firewall status
sudo ufw status
```

### Accessibility

- **Local Access**: http://localhost:8188
- **Network Access**: http://192.168.178.15:8188
- **Service Management**: `sudo systemctl {start|stop|restart} comfyui`

## Monitoring and Maintenance

### Service Status
```bash
sudo systemctl status comfyui
sudo journalctl -u comfyui -f
```

### Log Management
- **System Logs**: `/var/log/syslog`
- **Service Logs**: `journalctl -u comfyui`
- **Application Logs**: Available through systemd journal

### Health Checks
- **Web Interface**: HTTP 200 response from ComfyUI
- **Process Status**: Active systemd service
- **Memory Usage**: Monitor for leaks or excessive usage
- **GPU Utilization**: Check RTX 3060 performance

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: Missing Python dependencies
   ```bash
   source venv/bin/activate
   pip install [missing-module]
   ```

2. **CUDA Out of Memory**: Reduce batch sizes or use `--normalvram`
3. **Port Conflict**: Ensure port 8188 is available
4. **Permission Issues**: Verify file permissions in model directories

### Performance Optimization

- **GPU Memory**: Adjust VRAM flags based on available memory
- **Model Loading**: Consider model-specific optimizations
- **Network**: Ensure proper network configuration for remote access

## Security Considerations

### Network Security
- **Firewall**: Only expose necessary ports
- **Authentication**: Consider implementing authentication for production
- **Access Control**: Limit network access to trusted IPs

### File Security
- **Permissions**: Proper user/group permissions
- **Model Storage**: Secure sensitive model files
- **Logs**: Regular log rotation and review

## Future Enhancements

### Planned Improvements
1. **Automated Backups**: Model and configuration backups
2. **Monitoring Dashboard**: Real-time performance metrics
3. **Load Balancing**: Multiple instance support
4. **API Integration**: RESTful API for external applications

### Extension Support
- **Custom Nodes**: Automated installation and management
- **Model Management**: Version control and rollback
- **Workflow Templates**: Pre-configured workflow sharing

## Conclusion

This installation provides a robust, scalable ComfyUI environment that integrates seamlessly with existing AI infrastructure while maintaining high performance and reliability standards. The agent-based approach ensures systematic execution and comprehensive documentation of all installation and configuration decisions.

---

**Installation Date**: October 7, 2025
**System**: Ubuntu Server with RTX 3060
**Architecture**: Native (non-Docker)
**Management**: Claude Code + Claude Flow orchestration