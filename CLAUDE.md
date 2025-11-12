# Claude Code Configuration - ComfyUI Native Setup

## 🚨 CRITICAL: CONCURRENT EXECUTION & FILE MANAGEMENT

**ABSOLUTE RULES**:
1. ALL operations MUST be concurrent/parallel in a single message
2. **NEVER save working files, text/mds and tests to the root folder**
3. ALWAYS organize files in appropriate subdirectories
4. **USE CLAUDE CODE'S TASK TOOL** for spawning agents concurrently, not just MCP

### ⚡ GOLDEN RULE: "1 MESSAGE = ALL RELATED OPERATIONS"

**MANDATORY PATTERNS**:
- **TodoWrite**: ALWAYS batch ALL todos in ONE call (5-10+ todos minimum)
- **Task tool (Claude Code)**: ALWAYS spawn ALL agents in ONE message with full instructions
- **File operations**: ALWAYS batch ALL reads/writes/edits in ONE message
- **Bash commands**: ALWAYS batch ALL terminal operations in ONE message
- **Memory operations**: ALWAYS batch ALL memory store/retrieve in ONE message

### 🎯 CRITICAL: Claude Code Task Tool for Agent Execution

**Claude Code's Task tool is the PRIMARY way to spawn agents:**
```javascript
// ✅ CORRECT: Use Claude Code's Task tool for parallel agent execution
[Single Message]:
  Task("Environment Specialist", "Analyze Python dependencies and CUDA compatibility...", "backend-dev")
  Task("Model Integration Expert", "Configure model paths and validate SwarmUI compatibility...", "code-analyzer")
  Task("Operations Engineer", "Create systemd services and monitoring...", "cicd-engineer")
```

**MCP tools are ONLY for coordination setup:**
- `mcp__claude-flow__swarm_init` - Initialize coordination topology
- `mcp__claude-flow__agent_spawn` - Define agent types for coordination
- `mcp__claude-flow__task_orchestrate` - Orchestrate high-level workflows

### 📁 File Organization Rules

**NEVER save to root folder. Use these directories:**
- `/src` - Source code files
- `/tests` - Test files
- `/docs` - Documentation and markdown files
- `/config` - Configuration files
- `/scripts` - Utility scripts
- `/examples` - Example code

## 🌳 Worktree Architecture & Agent Roles

### trees/env-setup (Port 8188)
**Primary Agent Roles:**
- **Environment Specialist** (`backend-dev`): Python virtual environment management, PyTorch/CUDA compatibility validation, dependency resolution
- **Package Manager** (`coder`): Custom nodes installation, requirements file management, environment reproducibility
- **Validation Engineer** (`tester`): Environment testing, compatibility verification, performance benchmarking

**Key Directories:**
- `docs/env/` - Environment decisions and configuration
- `requirements.lock` - Locked dependencies
- `scripts/bootstrap.sh` - Environment setup script

### trees/models-integ (Port 8189)
**Primary Agent Roles:**
- **File System Mapper** (`code-analyzer`): Model path discovery, SwarmUI integration, path template generation
- **Configuration Expert** (`system-architect`): YAML configuration design, validation rules, portable vs optimized variants
- **Integration Specialist** (`backend-dev`): Model validation, compatibility testing, path resolution

**Key Directories:**
- `config/models/` - Model path templates
- `docs/models/` - Model configuration documentation
- `scripts/validate-models.py` - Model validation utilities

### trees/ops-maint (Port 8190)
**Primary Agent Roles:**
- **Systems Administrator** (`cicd-engineer`): systemd service creation, process management, deployment automation
- **Log Analyst** (`reviewer`): Log parsing, pattern recognition, issue detection, health monitoring
- **Repair Technician** (`tester`): Diagnostics, repair automation, system recovery, maintenance procedures

**Key Directories:**
- `ops/` - Operational configurations
- `docs/ops/` - Operations documentation
- `logs/` - Structured logging output

## 🎯 Worktree Agent Primers

### env-setup Primer
```
Goal: Produce a locked Python environment and PyTorch/CUDA combo suitable for NVIDIA driver 575.57.08 with CUDA 12.9 on RTX 3060, targeting ComfyUI and common custom nodes. Document decisions in docs/env/decision-log.md. Ensure reproducible install via requirements.lock and a bootstrap checklist. Avoid model files.
```

### models-integ Primer
```
Goal: Maintain extra_model_paths.yaml templates, and validate presence/mapping between /home/ned/Models and /home/ned/Projects/AI_ML/SwarmUI/models. Include SwarmUI alternate folder names (Stable-diffusion vs checkpoints, ESRGAN vs upscale_models). Provide "portable" and "host-optimized" variants of the YAML. Put them in configs/models/. Add a "new machine adapt" task that checks for the target machine's model paths and proposes path rewrites automatically.
```

### ops-maint Primer
```
Goal: Create systemd unit templates, log routing to /home/ned/ComfyUI-Install/logs, and a log triage policy for Claude-Flow (rotate, tail, detect CUDA/torch/conflicts, propose fixes). Implement a "dry-run repair" mode that opens a Claude review before executing changes. Keep everything under ops/ with README.
```

## 🚀 Custom Commands

### Worktree Management
- **worktrees-init**: `/.claude/commands/worktrees-init.md`
- **worktrees-merge**: `/.claude/commands/worktrees-merge.md`

### Development Commands
- **env:validate**: Validate Python/PyTorch/CUDA compatibility
- **models:scan**: Scan and validate model directory structure
- **models:adapt**: Adapt model paths for new machine
- **ops:health**: Comprehensive system health check
- **ops:repair**: Execute repair procedures (with review)

## 🤖 Claude Flow Integration

### Required Hooks
- **pre-command**: Safety validation, resource preparation, environment checks
- **post-command**: Code formatting, pattern training, memory updates
- **session-end**: Summary generation, metric export, checkpoint creation
- **git-checkpoint**: State preservation after significant changes

### Memory Structure
- `swarm/env-setup/` - Environment decisions and configurations
- `swarm/models-integ/` - Model path mappings and validation
- `swarm/ops-maint/` - Operational procedures and maintenance
- `sessions/` - Session summaries and next actions

## 🔄 Merge & Integration Workflow

### Safe Merge Process
1. **Conflict Detection**: Claude Flow analyzes potential conflicts
2. **Review Phase**: Automatic diff review and validation
3. **Linear Merge**: Squash-merge with clean history
4. **Release Tagging**: Automatic version tagging (e.g., r720-native-v1)
5. **Documentation**: CHANGELOG generation and deployment delta

### Branch Protection
- Main branch protected from direct commits
- All changes must come from worktree merges
- Claude Flow approval required for operational changes
- Automated testing before merge approval

## 📊 Monitoring & Observability

### Log Management
- Structured JSON logging per worktree
- Claude Flow pattern recognition for issue detection
- Automatic log rotation: 100MB files, 30-day retention
- Real-time log analysis for CUDA/PyTorch conflicts

### Performance Metrics
- GPU utilization tracking
- Memory usage monitoring
- Response time measurement
- Error rate analysis

## 🚨 Safety & Validation

### Pre-Command Validation
- Port conflict detection
- Resource availability checks
- File permission validation
- CUDA/PyTorch compatibility verification

### Operational Safety
- Dry-run mode for destructive operations
- Claude review required for system changes
- Automatic backup creation before modifications
- Rollback procedures for all operations

## 🎯 Success Criteria

### Environment Setup
- ✅ Reproducible Python environment with requirements.lock
- ✅ PyTorch 2.4+ with CUDA 12.9 compatibility
- ✅ All custom nodes installable and functional
- ✅ Bootstrap checklist for new machines

### Model Integration
- ✅ extra_model_paths.yaml templates for all configurations
- ✅ SwarmUI path compatibility validated
- ✅ Model discovery and validation working
- ✅ New machine adaptation procedure documented

### Operations & Maintenance
- ✅ Systemd service templates for all environments
- ✅ Log routing and analysis system active
- ✅ Health checks and monitoring operational
- ✅ Repair automation with review process

## 🛠️ Development Commands

### Build Commands
- `npm run build` - Build project (if applicable)
- `npm run test` - Run tests
- `npm run lint` - Linting
- `npm run typecheck` - Type checking

### SPARC Methodology
- `npx claude-flow sparc modes` - List available modes
- `npx claude-flow sparc run <mode> "<task>"` - Execute specific mode
- `npx claude-flow sparc tdd "<feature>"` - Run complete TDD workflow

## 🚀 Quick Setup

```bash
# Initialize Claude Flow
npx claude-flow@alpha hooks init

# Set up worktrees
/project:worktrees-init canonical 3

# Configure each worktree
cd trees/env-setup && set COMFY_PORT=8188
cd trees/models-integ && set COMFY_PORT=8189
cd trees/ops-maint && set COMFY_PORT=8190
```

## 🤝 Agent Coordination Protocol

### Every Agent MUST:

**1️⃣ BEFORE Work:**
```bash
npx claude-flow@alpha hooks pre-task --description "[task]"
npx claude-flow@alpha hooks session-restore --session-id "swarm-[id]"
```

**2️⃣ DURING Work:**
```bash
npx claude-flow@alpha hooks post-edit --file "[file]" --memory-key "swarm/[agent]/[step]"
npx claude-flow@alpha hooks notify --message "[what was done]"
```

**3️⃣ AFTER Work:**
```bash
npx claude-flow@alpha hooks post-task --task-id "[task]"
npx claude-flow@alpha hooks session-end --export-metrics true
```

---

**Remember: Claude Flow coordinates, Claude Code creates! Use worktrees for isolation, hooks for safety, and agents for specialization.**
- this directory is about configuring, running and maintaining the ComfyUI installation in ./ComfyUI
- this is the systems main ComfyUI installation. It must be always checked to be running and be started, preferably through system configuration, but if necessery directly
- always execute source ComfyUI/venv/bin/activate before doing any python installations

## 🚀 ComfyUI Startup Command

**Optimized startup for RTX 3060 12GB (VRAM efficient):**
```bash
cd /home/ned/ComfyUI-Install/ComfyUI
source venv/bin/activate
python main.py --listen 0.0.0.0 --port 8188 --cpu
```

**Background startup (VRAM optimized):**
```bash
cd /home/ned/ComfyUI-Install/ComfyUI
source venv/bin/activate && python main.py --listen 0.0.0.0 --port 8188 --cpu &
```

**Access Web Interface:** http://192.168.178.15:8188

**⚠️ Important:** The `--cpu` flag enables CPU offloading (keeps GPU active!) and reduces VRAM usage by offloading models to CPU when not in use.