# ComfyUI Native Setup - Claude Flow Orchestrated

A comprehensive, portable ComfyUI installation and maintenance system powered by Claude Flow orchestration with Git worktrees for parallel development.

## 🚀 Quick Start

### Prerequisites
- NVIDIA RTX 3060 (or compatible CUDA GPU)
- NVIDIA Driver 575.57.08 with CUDA 12.9 support
- Python 3.10+
- Claude Code with Claude Flow MCP servers

### Clone & Restore
```bash
# Clone the repository
git clone https://github.com/yourusername/comfyui-native-setup.git
cd comfyui-native-setup

# Initialize Claude Flow
npx claude-flow@alpha hooks init

# Create canonical worktrees
/project:worktrees-init canonical 3

# Configure GitHub remote (if needed)
git remote add origin https://github.com/yourusername/comfyui-native-setup.git
git push -u origin main
```

## 🌳 Worktree Architecture

### Canonical Worktrees
1. **trees/env-setup** - Environment and dependency management
   - Python virtual environment setup
   - PyTorch/CUDA compatibility validation
   - ComfyUI custom nodes installation
   - Reproducible environment locking

2. **trees/models-integ** - Model path configuration and validation
   - `/home/ned/Models` integration
   - SwarmUI path mapping compatibility
   - Portable vs host-optimized configurations
   - Model validation and discovery

3. **trees/ops-maint** - Operations, monitoring, and maintenance
   - systemd service templates
   - Log routing and analysis
   - Health checks and watchdogs
   - Repair automation and playbooks

### Environment Isolation
Each worktree uses distinct ports and log paths:
- `env-setup`: COMFY_PORT=8188, LOG=logs/env-setup.log
- `models-integ`: COMFY_PORT=8189, LOG=logs/models-integ.log
- `ops-maint`: COMFY_PORT=8190, LOG=logs/ops-maint.log

## 🛠️ Development Workflow

### 1. Environment Setup (`env-setup`)
```bash
cd trees/env-setup
# Start Claude session
# Apply env-setup primer:
#   Goal: Create locked Python env with PyTorch/CUDA 12.9
#   Document decisions in docs/env/decision-log.md
#   Generate requirements.lock and bootstrap checklist
```

### 2. Model Integration (`models-integ`)
```bash
cd trees/models-integ
# Start Claude session
# Apply models-integ primer:
#   Goal: Maintain extra_model_paths.yaml templates
#   Validate SwarmUI path mappings
#   Create portable and host-optimized variants
```

### 3. Operations & Maintenance (`ops-maint`)
```bash
cd trees/ops-maint
# Start Claude session
# Apply ops-maint primer:
#   Goal: Create systemd templates and log routing
#   Implement health checks and watchdogs
#   Setup repair automation with Claude review
```

## 🤖 Claude Flow Integration

### Hooks & Checkpointing
- **Pre-command**: Safety validation and resource preparation
- **Post-command**: Code formatting and pattern training
- **Session-end**: Summary generation and metric tracking
- **Git checkpoints**: Automatic state preservation

### Agent Coordination
Each worktree has specialized agent roles:
- **env-setup**: Python package manager, CUDA validation specialist
- **models-integ**: File system mapper, path configuration expert
- **ops-maint**: Systems administrator, log analyst, repair technician

## 📁 Project Structure

```
comfyui-native-setup/
├── trees/
│   ├── env-setup/          # Environment management
│   ├── models-integ/       # Model path configuration
│   └── ops-maint/          # Operations & maintenance
├── docs/
│   ├── env/               # Environment documentation
│   ├── models/            # Model configuration docs
│   ├── ops/               # Operations documentation
│   └── summaries/         # Session summaries
├── config/
│   └── models/            # Model path templates
├── scripts/               # Utility scripts
├── .claude/commands/      # Custom Claude commands
├── CLAUDE.md              # Agent role definitions
└── README.md              # This file
```

## 🔧 Custom Commands

### Worktree Management
- `/project:worktrees-init <feature> <N>` - Create N worktrees for feature
- `/project:worktrees-merge <feature> <branches>` - Merge worktrees with review

### Development Commands
- `/env:validate` - Validate Python/PyTorch/CUDA setup
- `/models:scan` - Scan and validate model paths
- `/ops:health` - Run comprehensive health check

## 🔄 Merge Workflow

1. **Review Phase**: Claude Flow analyzes diffs and checks conflicts
2. **Merge Phase**: Squash-merge with linear history preservation
3. **Tagging**: Automatic release tagging (e.g., r720-native-v1)
4. **Documentation**: Generate CHANGELOG and deployment delta

## 📊 Monitoring & Observability

### Log Management
- Structured logging to dedicated files per worktree
- Claude Flow pattern recognition for issue detection
- Automatic log rotation and archival

### Performance Tracking
- GPU utilization monitoring
- Memory usage tracking
- Response time metrics
- Error rate analysis

## 🚨 Troubleshooting

### Common Issues
1. **Port Conflicts**: Ensure only one ComfyUI instance runs at a time
2. **CUDA Compatibility**: Validate driver version matches PyTorch requirements
3. **Model Path Issues**: Use models-integ worktree for path validation
4. **Service Failures**: Check ops-maint worktree for systemd configuration

### Getting Help
- Review worktree-specific documentation in `docs/`
- Check Claude Flow session summaries in `docs/summaries/`
- Use `/ops:health` for comprehensive diagnostics

## 🆕 New Machine Setup

1. Clone repository: `git clone [url] && cd comfyui-native-setup`
2. Run adaptation: `cd trees/models-integ && /models:adapt-new-machine`
3. Follow generated checklist for model path adjustments
4. Validate with `/env:validate` and `/ops:health`

## 🤝 Contributing

1. Create feature worktree: `/project:worktrees-init <feature> 1`
2. Develop in isolated environment
3. Submit for merge: `/project:worktrees-merge <feature> <branch>`
4. Review and approve via Claude Flow

## 📄 License

This project follows the same license as ComfyUI.

---

**Built with Claude Flow orchestration • Git worktrees for parallel development • Portable across machines**