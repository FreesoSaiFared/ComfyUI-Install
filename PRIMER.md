# Model Integration Worktree Primer

## 🎯 Mission Objective

**Goal**: Maintain extra_model_paths.yaml templates, and validate presence/mapping between /home/ned/Models and /home/ned/Projects/AI_ML/SwarmUI/models. Include SwarmUI alternate folder names (Stable-diffusion vs checkpoints, ESRGAN vs upscale_models). Provide "portable" and "host-optimized" variants of the YAML. Put them in configs/models/. Add a "new machine adapt" task that checks for the target machine's model paths and proposes path rewrites automatically.

## 🚀 Immediate Action Items

### Phase 1: Path Discovery & Analysis
1. **Model Directory Survey**:
   - Scan `/home/ned/Models` structure and contents
   - Analyze `/home/ned/Projects/AI_ML/SwarmUI/models` organization
   - Document folder naming conventions and patterns
   - Identify model types and categories present

2. **SwarmUI Integration Mapping**:
   - Map SwarmUI folder names to ComfyUI conventions:
     - `Stable-diffusion` ↔ `checkpoints`
     - `ESRGAN` ↔ `upscale_models`
     - `VAE` ↔ `vae`
     - `LoRA` ↔ `loras`
     - etc.
   - Create cross-reference matrix for common model types

### Phase 2: Configuration Template Development
1. **Create Base Templates**:
   - `config/models/portable.yaml` - Relative paths for portability
   - `config/models/host-optimized.yaml` - Absolute paths for performance
   - `config/models/swarmui-compat.yaml` - SwarmUI compatibility mode

2. **Template Features**:
   - Path validation and existence checking
   - Fallback path configurations
   - Environment variable support
   - Comments explaining each model category

### Phase 3: Validation & Adaptation Tools
1. **Validation Scripts**:
   - `scripts/validate-models.py` - Check model path validity
   - `scripts/scan-models.py` - Discover and catalog models
   - `scripts/compare-dirs.py` - Compare model directories

2. **Adaptation System**:
   - `scripts/adapt-new-machine.py` - Auto-generate path rewrites
   - Template-based configuration generation
   - Interactive path selection interface

## 📊 Success Criteria

### Must-Have Outcomes
- ✅ Complete model path inventory of both directories
- ✅ Working extra_model_paths.yaml templates for all configurations
- ✅ SwarmUI path compatibility matrix documented
- ✅ Model validation scripts working correctly
- ✅ New machine adaptation procedure functional

### Configuration Deliverables
- `config/models/portable.yaml` - Portable configuration template
- `config/models/host-optimized.yaml` - Host-optimized template
- `config/models/swarmui-compat.yaml` - SwarmUI compatibility
- `docs/models/path-mapping.md` - Complete path reference
- `docs/models/swarmui-integration.md` - Integration guide

## 🛠️ Available Commands in This Worktree

- `/models:scan` - Scan and validate model directory structure
- `/models:validate` - Validate current model paths configuration
- `/models:adapt` - Adapt model paths for new machine
- `/models:compare` - Compare model directories
- `/models:generate-config` - Generate configuration from template

## 🤝 Agent Coordination

**Primary Agents**:
- **File System Mapper** (`code-analyzer`): Directory structure analysis, path discovery
- **Configuration Expert** (`system-architect`): YAML template design, validation rules
- **Integration Specialist** (`backend-dev`): Cross-platform compatibility, testing

**Memory Storage**: `swarm/models-integ/`
**Hook Integration**: All configuration changes and path decisions logged

## 📁 Directory Structure to Support

```
/home/ned/Models/
├── checkpoints/           # Stable diffusion models
├── vae/                 # VAE models
├── loras/               # LoRA models
├── upscale_models/      # ESRGAN/upscaling models
├── embeddings/          # Textual inversion
├── hypernetworks/       # Hypernetworks
└── controlnet/          # ControlNet models

/home/ned/Projects/AI_ML/SwarmUI/models/
├── Stable-diffusion/    # Equivalent to checkpoints
├── VAE/                 # Same as vae
├── LoRA/                # Same as loras
├── ESRGAN/              # Equivalent to upscale_models
└── ...
```

## ⚠️ Constraints & Guidelines

- **NEVER** assume absolute paths exist on other machines
- **ALWAYS** provide both portable and host-optimized variants
- **DOCUMENT** every path mapping decision
- **VALIDATE** model files actually exist
- **SUPPORT** both ComfyUI and SwarmUI naming conventions

## 🔧 Configuration Template Structure

```yaml
# config/models/portable.yaml example
portable:
  checkpoints: "../models/checkpoints"
  vae: "../models/vae"
  loras: "../models/loras"
  # ... relative paths for portability

host_optimized:
  checkpoints: "/home/ned/Models/checkpoints"
  vae: "/home/ned/Models/vae"
  # ... absolute paths for performance

swarmui_compatible:
  Stable-diffusion: "/home/ned/Models/checkpoints"
  ESRGAN: "/home/ned/Models/upscale_models"
  # ... SwarmUI naming convention
```

## 🔄 Next Steps After Completion

1. Test all configuration templates with actual ComfyUI startup
2. Validate SwarmUI compatibility on target system
3. Document adaptation procedure for new machines
4. Prepare for merge into main branch

---

**Remember: This worktree handles model path configuration. Focus on compatibility, validation, and portability across different setups.**