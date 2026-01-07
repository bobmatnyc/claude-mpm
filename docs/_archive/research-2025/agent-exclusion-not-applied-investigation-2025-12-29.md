# Agent Exclusion Not Applied During Deployment - Root Cause Analysis

**Date**: 2025-12-29
**Investigator**: Research Agent
**Ticket Context**: User reported excluded agents still being deployed
**Status**: Root cause identified

## Problem Statement

User has project at `~/Clients/Recess/projects/data-manager` with configuration:

```yaml
excluded_agents:
  - dart-engineer
  - golang-engineer
  - java-engineer
  - php-engineer
  - phoenix-engineer
  - ruby-engineer
  - rust-engineer
  - svelte-engineer
  - tauri-engineer
```

However, running `/agents` command shows ALL agents deployed in `.claude/agents/`, including the excluded ones.

Recent fix to `_normalize_agent_name()` in `multi_source_deployment_service.py` handles name variations correctly, but old deployed agents weren't cleaned up.

## Investigation Summary

### Deployment Flow Analysis

The `/agents` CLI command uses a **different deployment path** than expected:

**Path 1: AgentDeploymentService.deploy_agents()** (NOT USED by /agents command)
- Location: `src/claude_mpm/services/agents/deployment/agent_deployment.py`
- Has exclusion filtering via `get_agents_for_deployment()` (lines 888-898)
- Has cleanup logic via `cleanup_excluded_agents()` (lines 964-967)
- Uses multi-source deployment with version comparison
- **This path is CORRECT but NEVER EXECUTED by /agents command**

**Path 2: GitSourceSyncService.deploy_agents_to_project()** (ACTUALLY USED)
- Location: `src/claude_mpm/services/agents/sources/git_source_sync_service.py`
- Called from: `src/claude_mpm/cli/commands/agents.py:599`
- **NO exclusion filtering whatsoever**
- **NO config-based filtering**
- Simply deploys ALL agents from `~/.claude-mpm/cache/agents/` to `.claude/agents/`

### Root Cause

**The `/agents` command bypasses the exclusion logic entirely.**

Flow of `/agents` command:
1. `AgentsCommand._deploy_agents()` (agents.py:560)
2. `GitSourceSyncService.sync_repository()` - syncs to cache
3. `GitSourceSyncService.deploy_agents_to_project()` - deploys from cache
4. `GitSourceSyncService._discover_cached_agents()` - discovers ALL cached agents
5. Copy ALL discovered agents to `.claude/agents/`

**Missing step**: No call to load project config and filter excluded agents.

### Code Evidence

**agents.py:599-603** - Deploys without exclusion awareness:
```python
deploy_result = git_sync.deploy_agents_to_project(
    project_dir=project_dir,
    agent_list=None,  # Deploy all cached agents ← NO FILTERING
    force=force,
)
```

**git_source_sync_service.py:993-994** - Discovers all agents:
```python
if agent_list is None:
    agent_list = self._discover_cached_agents()  # ← Returns ALL agents
```

**git_source_sync_service.py:1083-1091** - No exclusion logic:
```python
for file_path in self.cache_dir.rglob("*"):
    if file_path.is_file() and file_path.suffix in {".md", ".json"}:
        # Get relative path from cache directory
        relative_path = file_path.relative_to(self.cache_dir)
        relative_str = str(relative_path)

        # Exclude README and .gitignore
        if relative_str not in ["README.md", ".gitignore"]:
            cached_agents.append(relative_str)  # ← NO CONFIG FILTERING
```

### Why _normalize_agent_name() Fix Didn't Help

The recent fix to `_normalize_agent_name()` (multi_source_deployment_service.py:29-38) is correct:
```python
def _normalize_agent_name(name: str) -> str:
    """Normalize agent name for consistent comparison.

    Converts spaces, underscores to hyphens and lowercases.
    Examples:
        "Dart Engineer" -> "dart-engineer"
        "dart_engineer" -> "dart-engineer"
        "DART-ENGINEER" -> "dart-engineer"
    """
    return name.lower().replace(" ", "-").replace("_", "-")
```

This normalization is used in:
- `get_agents_for_deployment()` exclusion filtering (lines 545-583)
- `cleanup_excluded_agents()` would use it if called

**But these methods are never invoked by the /agents command.**

## Exclusion Logic Locations (Unused)

### Location 1: multi_source_deployment_service.py

**get_agents_for_deployment()** (lines 478-627):
- Line 545-583: Filters excluded agents using normalized names
- Line 549: Creates normalized excluded_set
- Line 570-575: Checks agent_name, agent_id, and file_stem against exclusions
- Line 582-583: Removes matched agents

**cleanup_excluded_agents()** (lines 632-729):
- Line 660: Creates expected_agents set from agents_to_deploy
- Line 677: Removes agents NOT in expected_agents
- Line 696: Unlinks excluded agent files

### Location 2: agent_deployment.py

**_get_multi_source_templates()** (lines 839-982):
- Line 895: Passes excluded_agents to get_agents_for_deployment()
- Line 964-967: Calls cleanup_excluded_agents()
- Line 974-977: Logs removal of excluded agents

**deploy_agents()** (lines 294-541):
- Line 393: Loads excluded_agents from config
- Line 442-451: Determines if multi-source deployment should be used
- Line 446-450: Calls _get_multi_source_templates() if multi-source is enabled

### Why These Aren't Called

The `/agents` command flow:
1. AgentsCommand._deploy_agents() (agents.py:560)
2. GitSourceSyncService.sync_repository()
3. GitSourceSyncService.deploy_agents_to_project() ← **STOPS HERE**

Never reaches:
- AgentDeploymentService.deploy_agents()
- AgentDeploymentService._get_multi_source_templates()
- MultiSourceAgentDeploymentService.get_agents_for_deployment()
- MultiSourceAgentDeploymentService.cleanup_excluded_agents()

## Fix Recommendations

### Option 1: Add Exclusion Filtering to GitSourceSyncService (Recommended)

**Modify**: `git_source_sync_service.py:deploy_agents_to_project()`

**Changes needed**:
1. Load project config to get excluded_agents list
2. Filter agent_list before deployment loop
3. Cleanup already-deployed excluded agents

**Implementation**:
```python
def deploy_agents_to_project(
    self,
    project_dir: Path,
    agent_list: Optional[List[str]] = None,
    force: bool = False,
) -> Dict[str, Any]:
    # ... existing setup ...

    # NEW: Load project config and get exclusions
    from claude_mpm.core.config import Config
    config = Config(working_directory=project_dir)
    excluded_agents = config.get("excluded_agents", [])

    # NEW: Normalize excluded names for comparison
    from claude_mpm.services.agents.deployment.multi_source_deployment_service import _normalize_agent_name
    excluded_set = {_normalize_agent_name(name) for name in excluded_agents}

    # Get agents from cache or use provided list
    if agent_list is None:
        agent_list = self._discover_cached_agents()

    # NEW: Filter excluded agents
    filtered_agent_list = [
        agent_path for agent_path in agent_list
        if _normalize_agent_name(Path(agent_path).stem) not in excluded_set
    ]

    # NEW: Cleanup already-deployed excluded agents
    cleanup_results = self._cleanup_excluded_agents(
        deployment_dir, excluded_set
    )

    # Use filtered list for deployment
    for agent_path in filtered_agent_list:
        # ... existing deployment logic ...
```

**Add new method**:
```python
def _cleanup_excluded_agents(
    self,
    deployment_dir: Path,
    excluded_set: Set[str],
) -> Dict[str, List[str]]:
    """Remove excluded agents from deployment directory.

    Args:
        deployment_dir: Directory containing deployed agents
        excluded_set: Set of normalized agent names to exclude

    Returns:
        Dictionary with removed agent names
    """
    cleanup_results = {"removed": []}

    if not deployment_dir.exists():
        return cleanup_results

    for item in deployment_dir.iterdir():
        if not item.is_file() or item.suffix != ".md":
            continue

        agent_name = _normalize_agent_name(item.stem)
        if agent_name in excluded_set:
            try:
                item.unlink()
                cleanup_results["removed"].append(item.stem)
                logger.info(f"Removed excluded agent: {item.stem}")
            except Exception as e:
                logger.error(f"Failed to remove {item.stem}: {e}")

    return cleanup_results
```

**Pros**:
- Minimal changes to existing code
- Fixes the actual problem at the source
- Consistent with current architecture
- Handles both new deployments and cleanup

**Cons**:
- Duplicates some logic from multi_source_deployment_service
- Adds config loading to git sync service

### Option 2: Route /agents Through AgentDeploymentService

**Modify**: `agents.py:_deploy_agents()`

**Changes needed**:
1. Remove GitSourceSyncService usage
2. Call AgentDeploymentService.deploy_agents() instead
3. Configure multi-source deployment mode

**Implementation**:
```python
def _deploy_agents(self, args, force=False) -> CommandResult:
    """Deploy agents using multi-source deployment with exclusions."""
    try:
        project_dir = Path.cwd()

        # Load config to get excluded_agents
        from ...core.config import Config
        config = Config(working_directory=project_dir)

        # Use AgentDeploymentService for deployment
        from ...services import AgentDeploymentService
        deployment_service = AgentDeploymentService(
            working_directory=project_dir,
            config=config
        )

        # Deploy with multi-source mode (applies exclusions)
        deploy_result = deployment_service.deploy_agents(
            target_dir=project_dir / ".claude" / "agents",
            force_rebuild=force,
            deployment_mode="project",  # Uses multi-source with exclusions
            config=config,
        )

        # Format results
        return CommandResult.success_result(
            data=deploy_result,
            message=f"Deployed {len(deploy_result['deployed'])} agents"
        )
```

**Pros**:
- Reuses existing, tested exclusion logic
- No code duplication
- Consistent deployment behavior

**Cons**:
- Larger architectural change
- May affect git sync workflow
- Requires careful testing

### Option 3: Add Post-Deployment Cleanup Hook

**Modify**: `agents.py:_deploy_agents()`

**Changes needed**:
1. Keep existing GitSourceSyncService flow
2. Add cleanup step after deployment
3. Load config and remove excluded agents

**Implementation**:
```python
def _deploy_agents(self, args, force=False) -> CommandResult:
    # ... existing deployment code ...

    # NEW: Post-deployment cleanup
    project_dir = Path.cwd()
    deployment_dir = project_dir / ".claude" / "agents"

    # Load config and apply exclusions
    from ...core.config import Config
    config = Config(working_directory=project_dir)
    excluded_agents = config.get("excluded_agents", [])

    if excluded_agents:
        cleanup_results = self._cleanup_excluded_agents_post_deploy(
            deployment_dir, excluded_agents
        )

        if cleanup_results["removed"]:
            self.logger.info(
                f"Removed {len(cleanup_results['removed'])} excluded agents"
            )
```

**Pros**:
- Minimal disruption to existing flow
- Quick fix for immediate problem
- Easy to test and verify

**Cons**:
- Band-aid solution
- Wasteful (deploys then removes)
- Doesn't prevent future issues

## Recommended Solution

**Option 1: Add Exclusion Filtering to GitSourceSyncService**

This is the best balance of:
- Fixing the root cause
- Minimal code changes
- Maintaining current architecture
- Handling both filtering and cleanup

Implementation priority:
1. Add `_cleanup_excluded_agents()` method to GitSourceSyncService
2. Load config in `deploy_agents_to_project()`
3. Filter agent_list before deployment
4. Cleanup existing excluded agents
5. Add logging for excluded agents

## Testing Recommendations

After implementing the fix:

1. **Test exclusion filtering**:
   ```bash
   # Add to project config
   echo "excluded_agents: [dart-engineer, golang-engineer]" >> .claude-mpm/mpm.yaml

   # Deploy agents
   mpm /agents

   # Verify excluded agents not deployed
   ls .claude/agents/ | grep -E "(dart-engineer|golang-engineer)"
   # Should return empty
   ```

2. **Test cleanup of existing excluded agents**:
   ```bash
   # Manually create excluded agent
   touch .claude/agents/rust-engineer.md

   # Deploy (should cleanup)
   mpm /agents

   # Verify removed
   ls .claude/agents/rust-engineer.md
   # Should not exist
   ```

3. **Test name normalization**:
   ```yaml
   # Test various formats in config
   excluded_agents:
     - "Dart Engineer"  # Space-separated
     - dart_engineer    # Underscore
     - GOLANG-ENGINEER  # Uppercase
   ```

## Related Files

### Primary Files to Modify
- `src/claude_mpm/services/agents/sources/git_source_sync_service.py`
  - Line 926: `deploy_agents_to_project()` method
  - Add: `_cleanup_excluded_agents()` method

### Supporting Files (Reference)
- `src/claude_mpm/services/agents/deployment/multi_source_deployment_service.py`
  - Line 29: `_normalize_agent_name()` function (use this)
  - Line 632: `cleanup_excluded_agents()` method (reference for cleanup logic)
  - Line 545-583: Exclusion filtering logic (reference for filtering)

- `src/claude_mpm/cli/commands/agents.py`
  - Line 560: `_deploy_agents()` method (calls git sync service)

- `src/claude_mpm/services/agents/deployment/agent_deployment.py`
  - Line 888-898: How exclusions should be loaded and applied
  - Line 964-967: How cleanup should be called

## Conclusion

The agent exclusion feature is **correctly implemented** but **never executed** because the `/agents` command uses a different deployment path (`GitSourceSyncService`) that lacks exclusion awareness.

The fix is straightforward: Add config loading and exclusion filtering to `GitSourceSyncService.deploy_agents_to_project()`, mirroring the logic already present in `AgentDeploymentService`.

The normalization fix was correct but insufficient because it only fixed one part of a two-phase deployment system where the `/agents` command uses the phase that has no exclusion logic.
