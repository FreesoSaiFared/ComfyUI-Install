# Command: Initialize Multiple Worktrees for Feature Development

**Purpose**: Given a feature name and N, create N git worktrees under ./trees/<feature>-i, each on its <feature>-i branch; seed each with a minimal environment (copy .env, CLAUDE.md, and settings). Auto-open Claude sessions and configure port isolation.

**Usage**: `/project:worktrees-init <feature_name> <count>`

**Parameters**:
- `feature_name`: Base name for the feature (e.g., "comfy-setup", "experimental")
- `count`: Number of worktrees to create (1-10 recommended)

**Example**: `/project:worktrees-init comfy-setup 3` creates trees/env-setup-1, trees/env-setup-2, trees/env-setup-3

**Behavior**:
1. Validate git repository state
2. Create N worktrees in ./trees/ directory
3. Create branches: <feature>-1, <feature>-2, etc.
4. Copy essential files to each worktree
5. Configure unique COMFY_PORT for each (8188, 8189, 8190+)
6. Set up log file paths per worktree
7. Auto-open Claude session in each worktree
8. Publish branches to origin if remote exists
9. Display worktree status and configuration summary

**Safety Features**:
- Prevents worktree creation in main repository
- Validates branch names don't conflict
- Checks for port conflicts
- Ensures proper file permissions
- Creates backup of existing configurations

**Generated Directory Structure**:
```
trees/
├── <feature>-1/
│   ├── .env
│   ├── CLAUDE.md
│   └── .claude/settings.json (with port config)
├── <feature>-2/
│   └── ...
└── <feature>-N/
    └── ...
```

**Environment Variables Set**:
- `COMFY_PORT`: 8188 + index (to avoid conflicts)
- `COMFY_LOG`: `/home/ned/ComfyUI-Install/logs/<feature>-<index>.log`
- `WORKTREE_NAME`: `<feature>-<index>`

**Requirements**:
- Must be run from git repository root
- Git worktrees support available
- Claude Flow MCP servers configured
- Ports 8188-8199 available (or configured range)

**Validation**:
- Prints git worktree list
- Confirms branches created and published
- Verifies environment isolation
- Tests port availability