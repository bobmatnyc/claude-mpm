# deploy-all Using Built Agents from dist/ - Fix Implementation

**Date**: 2025-12-13
**Status**: ✅ FIXED
**Related Issue**: BASE-AGENT.md hierarchical composition not being used by deploy-all

## Problem Statement

The `claude-mpm agents deploy-all` command was deploying agents from the **source** directory (`agents/`) instead of the **built** directory (`dist/agents/`), causing deployed agents to have incorrect BASE-AGENT.md composition.

### Symptoms

- Root `agents/BASE-AGENT.md` correctly had NO "String Resources" section
- Engineer `agents/engineer/BASE-AGENT.md` correctly HAD "String Resources" section
- `build-agent.py --all` correctly built to `dist/agents/` with proper composition
- BUT: Deployed agents in `.claude/agents/` incorrectly had "String Resources" in QA, Documentation, etc.

### Expected Behavior

- **Engineer agents** (engineer, python-engineer, nextjs-engineer, etc.): SHOULD have "String Resources Best Practices" section
- **Non-engineer agents** (QA, Documentation, Ops, Security, Research): should NOT have "String Resources" section

The hierarchical BASE-AGENT.md system should only include `agents/engineer/BASE-AGENT.md` content for agents in the engineer tree.

## Root Cause Analysis

### Discovery Path Investigation

The `RemoteAgentDiscoveryService` was discovering agents from:
```
~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/
```

But it SHOULD have been discovering from:
```
~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/dist/agents/
```

### Code Flow

1. **SingleTierDeploymentService.deploy_all_agents()** calls `_discover_agents_in_repo()`
2. **_discover_agents_in_repo()** creates `RemoteAgentDiscoveryService(repo.cache_path)`
3. **RemoteAgentDiscoveryService.discover_remote_agents()** scans for `*.md` files
4. Discovery service checked for:
   - `{cache}/agents/` (source files) ✅ Found this
   - `{cache}/` (flattened cache)
   - But NOT `{cache}/dist/agents/` (built files) ❌ Never checked

5. **SingleTierDeploymentService._deploy_agent_file()** copied files directly from cache using `source_file` path
6. Result: Source files deployed instead of built files

### Why This Mattered

The `build-agent.py` script:
- Reads hierarchical BASE-AGENT.md files (root → category → subcategory)
- Composes final agent files by merging BASE-AGENT content
- Outputs to `dist/agents/` directory
- Example: QA agent gets only root BASE-AGENT, not engineer BASE-AGENT

Without using `dist/agents/`, the deployment bypassed the BASE-AGENT composition entirely.

## Solution Implementation

### File Modified

**File**: `src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py`

**Method**: `discover_remote_agents()` (lines 371-448)

### Change Description

Modified the directory resolution logic to check for `dist/agents/` directory FIRST:

**Before** (2 priorities):
1. `{cache}/agents/` - Git repo structure
2. `{cache}/` - Flattened cache structure

**After** (3 priorities):
1. `{cache}/dist/agents/` - Built output (PREFERRED) ⭐ NEW
2. `{cache}/agents/` - Source files (fallback)
3. `{cache}/` - Flattened cache (legacy)

### Code Changes

```python
# Support three cache structures (PRIORITY ORDER):
# 1. Built output: {path}/dist/agents/ - PREFERRED (built with BASE-AGENT composition)
# 2. Git repo path: {path}/agents/ - source files (fallback)
# 3. Flattened cache: {path}/ - directly contains category directories (legacy)

# Priority 1: Check for dist/agents/ (built output with BASE-AGENT composition)
dist_agents_dir = self.remote_agents_dir / "dist" / "agents"
agents_dir = self.remote_agents_dir / "agents"

if dist_agents_dir.exists():
    # PREFERRED: Use built agents from dist/agents/
    # These have BASE-AGENT.md files properly composed by build-agent.py
    self.logger.debug(f"Using built agents from dist: {dist_agents_dir}")
    scan_dir = dist_agents_dir
elif agents_dir.exists():
    # FALLBACK: Git repo structure - scan /agents/ subdirectory (source files)
    # This path is used when dist/agents/ hasn't been built yet
    self.logger.debug(f"Using source agents (no dist/ found): {agents_dir}")
    scan_dir = agents_dir
else:
    # LEGACY: Flattened cache structure
    # ... (existing code)
```

### Graceful Degradation

The fix maintains backward compatibility:
- If `dist/agents/` exists → Use built agents (preferred)
- If only `agents/` exists → Use source agents (fallback)
- If flattened cache → Use legacy path (compatibility)

This allows the system to work with:
- New agent repositories with build process
- Legacy agent repositories without build process
- Mixed environments during migration

## Verification

### Test Commands

```bash
# Clean deployment directory
rm -rf .claude/agents/*.md

# Force reinstall to pick up code changes
pipx install --force .

# Deploy all agents
claude-mpm agents deploy-all
```

### Verification Results

✅ **Non-engineer agents** (correctly NO "String Resources"):
```bash
$ grep -c "String Resources" .claude/agents/qa.md
0
$ grep -c "String Resources" .claude/agents/documentation.md
0
$ grep -c "String Resources" .claude/agents/ops.md
0
$ grep -c "String Resources" .claude/agents/security.md
0
$ grep -c "String Resources" .claude/agents/research.md
0
```

✅ **Engineer agents** (correctly HAVE "String Resources"):
```bash
$ grep -c "String Resources" .claude/agents/engineer.md
2
$ grep -c "String Resources" .claude/agents/python-engineer.md
2
$ grep -c "String Resources" .claude/agents/nextjs-engineer.md
2
$ grep -c "String Resources" .claude/agents/rust-engineer.md
2
```

**Explanation**: Count of 2 = section header + usage example

## Impact Assessment

### Benefits

1. **Correct BASE-AGENT Composition**: Deployed agents now reflect hierarchical BASE-AGENT.md structure
2. **Engineer-Specific Content**: "String Resources Best Practices" only in engineer agents
3. **Cleaner Non-Engineer Agents**: QA, Documentation, Ops, etc. don't have irrelevant engineering guidelines
4. **Build Process Integration**: Deployment now respects the build-agent.py workflow
5. **Graceful Degradation**: Backward compatible with repositories without dist/ directory

### Deployment Requirements

For agent repositories to use built agents, they must:
1. Have a `build-agent.py` script or equivalent build process
2. Generate output to `dist/agents/` directory
3. Properly compose BASE-AGENT.md files during build

### Migration Path

**Existing repositories**: Continue working with fallback to `agents/` directory

**New repositories**: Add build process to generate `dist/agents/`
```bash
# Example build command
cd ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents
./build-agent.py --all
```

## Related Documentation

- **Agent Cache Structure**: `docs/research/cache-update-workflow-analysis-2025-12-03.md`
- **BASE-AGENT Hierarchy**: `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/BASE-AGENT.md`
- **Build Process**: `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/build-agent.py`
- **Single-Tier Deployment**: `src/claude_mpm/services/agents/single_tier_deployment_service.py`

## Next Steps

1. ✅ Fix implemented and verified
2. ✅ Backward compatibility maintained
3. 📋 Consider adding build process to agent sync workflow
4. 📋 Document build process requirements for agent repository maintainers
5. 📋 Add integration test for dist/agents/ priority logic

## Code Commit

**Commit Message**:
```
fix(agents): prioritize dist/agents/ over source agents/ in discovery

The RemoteAgentDiscoveryService now checks for built agents in dist/agents/
before falling back to source files in agents/. This ensures BASE-AGENT.md
hierarchical composition is respected during deployment.

- Add dist/agents/ as Priority 1 discovery path
- Keep agents/ as Priority 2 fallback (backward compatible)
- Maintain legacy flattened cache support as Priority 3
- Update logging to show which path was used

Result: Engineer agents correctly have "String Resources Best Practices"
section, while non-engineer agents (QA, Documentation, Ops, Security)
correctly omit it.

Verified with:
- QA, Documentation, Ops, Security: 0 occurrences
- Engineer, Python-Engineer, NextJS-Engineer, Rust-Engineer: 2 occurrences
```

**Files Changed**:
- `src/claude_mpm/services/agents/deployment/remote_agent_discovery_service.py` (lines 403-448)

**Testing**:
- Manual deployment test with `claude-mpm agents deploy-all`
- Verification of deployed agent content
- Check backward compatibility with legacy paths
