# Command: Merge Worktrees with Review and Validation

**Purpose**: Collectively merge a chosen subset of worktree branches into main with a linear history (rebase + squash), run a dry-run conflict check, and open a short "merge review" in Claude for a sanity pass. Tag the merge with a release note.

**Usage**: `/project:worktrees-merge <feature_name> <branches>`

**Parameters**:
- `feature_name`: Base feature name (e.g., "comfy-setup")
- `branches`: Comma-separated list of branch numbers (e.g., "1,2,3" or "1,3")

**Example**: `/project:worktrees-merge comfy-setup "1,2"` merges env-setup-1 and env-setup-2 into main

**Behavior**:
1. **Pre-merge Analysis**:
   - Check if main branch is protected
   - Verify working directory is clean
   - Validate specified worktree branches exist
   - Check for uncommitted changes in worktrees

2. **Conflict Detection**:
   - Perform dry-run merge to identify conflicts
   - Analyze potential file conflicts (extra_model_paths.yaml, configs, etc.)
   - Check for port and log path conflicts
   - Generate conflict report

3. **Review Phase**:
   - Open Claude review session with diff analysis
   - Present merge recommendations
   - Require confirmation before proceeding
   - Document merge decisions

4. **Safe Merge Process**:
   - Checkout main branch
   - Squash-merge each worktree branch linearly
   - Resolve conflicts if any (with Claude assistance)
   - Create comprehensive commit message
   - Tag release with semantic versioning

5. **Post-merge Tasks**:
   - Generate CHANGELOG entries
   - Create deployment delta documentation
   - Clean up merged branches (optional)
   - Update worktree status

**Safety Features**:
- **Dry-run mode**: Test merge without actual changes
- **Conflict detection**: Identify issues before merging
- **Claude review**: Human oversight for critical changes
- **Backup creation**: Automatic backup before destructive operations
- **Rollback capability**: Easy revert if issues arise

**Generated Documentation**:
- `docs/summaries/merge-<timestamp>.md` - Merge summary
- `CHANGELOG.md` - Updated changelog entries
- `docs/deployment/` - Deployment delta for new machines
- Git tag: `v<version>-<feature>-<date>`

**Conflict Resolution**:
- Automatic conflict detection for known file types:
  - `extra_model_paths.yaml`
  - `.env` files
  - Port configurations
  - Systemd service files
- Claude-assisted manual resolution for complex conflicts
- Preserves both changes with merge annotations

**Requirements**:
- Must be run from main repository root
- Clean working directory
- Target worktree branches must exist
- Claude Flow with session management

**Validation**:
- Pre-merge conflict report
- Post-merge integrity check
- Branch status verification
- Release tag confirmation

**Rollback Procedure**:
If issues detected post-merge:
1. `git reset --hard HEAD~1` (undo merge)
2. `git tag -d <tag>` (remove tag)
3. Restore from backup if created
4. Review with Claude and retry

**Example Output**:
```
✅ Pre-merge validation complete
📊 Conflict analysis: 2 potential conflicts detected
🤖 Opening Claude review session...
✅ Merge approved by Claude
🔄 Merging branches: env-setup-1, env-setup-2
📝 Created commit: feat: Add environment setup and model integration
🏷️  Tagged release: v1.0.0-comfy-setup-20251006
📋 Generated documentation in docs/summaries/
```