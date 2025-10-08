# COMPACT LLM INSTRUCTIONS: ComfyUI Autonomous Maintenance System

## SYSTEM OVERVIEW
Autonomous ComfyUI maintenance system with Git-integrated logging, Claude Flow orchestration, and multi-agent development using 54 specialized agents across 3 Git worktrees.

## CORE ARCHITECTURE
```
ComfyUI-Install/
├── ComfyUI/ (submodule)          # Main application + models (17.6GB Wan 2.1)
├── trees/                        # Git worktrees for parallel dev
│   ├── env-setup/ (8188)        # Python/PyTorch/CUDA management
│   ├── models-integ/ (8189)      # Model path configuration
│   └── ops-maint/ (8190)         # System operations & monitoring
├── claude-flow/                  # Orchestration state
├── docs/                         # Decision logs & documentation
└── CLAUDE.md                     # Agent role definitions
```

## ORCHESTRATION PHILOSOPHY
**"Claude Flow coordinates, Claude Code creates"**

- **MCP Servers**: claude-flow@alpha (70+ tools) + optional ruv-swarm/flow-nexus
- **Agent Execution**: 54 specialized agents via Claude Code Task tool
- **Golden Rule**: "1 MESSAGE = ALL RELATED OPERATIONS"
- **Memory**: Cross-session persistence with Claude Flow
- **Safety**: Dry-run modes + human review for destructive ops

## AGENT ECOSYSTEM (54 AGENTS)
**Core**: coder, reviewer, tester, researcher, planner
**Coordination**: hierarchical/mesh/adaptive coordinators
**Development**: backend-dev, mobile-dev, ml-developer, api-docs
**GitHub**: pr-manager, code-review-swarm, issue-tracker
**SPARC**: sparc-coord, specification, architecture, refinement
**Performance**: perf-analyzer, task-orchestrator, memory-coordinator

## GIT WORKTREE METHODOLOGY
**3 Canonical Worktrees**:
1. **env-setup**: Environment Specialist + Package Manager + Validation Engineer
2. **models-integ**: File System Mapper + Configuration Expert + Integration Specialist
3. **ops-maint**: Systems Administrator + Log Analyst + Repair Technician

**Isolation**: Each worktree uses distinct ports (8188-8190) and dedicated logs

## MAINTENANCE AUTOMATION
**Health Monitoring**:
- Real-time API connectivity (20 nodes tracked)
- Custom node dependency validation (21 nodes monitored)
- System resources (CPU/memory/GPU tracking)
- Model path validation (SwarmUI integration)

**Self-Healing**:
- Automatic repair workflows with Claude review
- Pattern recognition from logs
- Dependency resolution automation
- Service restart capabilities

## CURRENT CHALLENGES
1. **Git Integration**: Manual commits, basic logging → Need automatic semantic commits
2. **Logging**: Basic JSON files → Need real-time streaming + predictive analysis
3. **Agent Coordination**: Manual selection → Need smart routing + load balancing
4. **Memory**: Basic persistence → Need long-term learning + pattern optimization

## ANALYSIS REQUESTS

### CHATGPT (GPT-4/GPT-4.5):
- Evaluate orchestration design improvements
- Optimize agent coordination strategies
- Design automatic Git integration
- Create intelligent log analysis system

### GEMINI (Ultra/Pro):
- Optimize 54-agent parallel execution
- Improve worktree isolation/merges
- Design predictive maintenance workflows
- Implement cross-session learning

### PERPLEXITY:
- Research maintenance system best practices
- Evaluate additional tool integrations
- Optimize Claude Flow performance
- Improve knowledge capture strategies

## SUCCESS METRICS
- **Uptime**: 99.9% availability with auto-recovery
- **Resolution**: <5 minutes detection-to-fix
- **Reproducibility**: 100% environment consistency
- **Efficiency**: Maintain 84.8% SWE-Bench solve rate

## DELIVERABLES REQUIRED
1. Critical analysis of current architecture
2. Innovative optimization proposals
3. Step-by-step implementation roadmap
4. Performance improvement estimates
5. Risk assessment + mitigation strategies

**GOAL**: Evolve to fully autonomous, self-learning ComfyUI maintenance system with every change automatically tracked in Git.

---
**Repository**: https://github.com/FreesoSaiFared/ComfyUI-Install
**Environment**: RTX 3060 + CUDA 12.9 + Ubuntu + Python 3.10+
**Models**: 17.6GB Wan 2.1 suite + 21 custom nodes