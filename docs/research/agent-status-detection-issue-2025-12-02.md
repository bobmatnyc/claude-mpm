# Agent Status Detection Issue Research

**Date**: 2025-12-02
**Researcher**: Claude Code (Research Agent)
**Issue**: Agents in `claude-mpm configure` show as "Available" when they should show as "Installed"

## Executive Summary

The agent status detection issue is caused by a **fundamental architecture mismatch** between:
1. **How agents are loaded into Claude Code sessions** (virtual deployment via `.mpm_deployment_state`)
2. **How `_is_agent_deployed()` checks for deployed agents** (physical file-based detection)

**Root Cause**: The 45 agents in the current Claude Code session exist as **virtual deployments** tracked in `.claude/agents/.mpm_deployment_state` but are NOT deployed as physical `.md` files. The `_is_agent_deployed()` method only checks for physical `.md` files in `.claude/agents/` and `.claude-mpm/agents/` directories, so it cannot detect virtually deployed agents.

**Impact**: All agents show as "Available" in `claude-mpm configure` even though 64 agents are actively loaded in the current Claude Code session.

---

## Architecture Deep Dive

### How Agents Get Into Claude Code Sessions

The Claude MPM system uses a **two-tier deployment architecture**:

#### Tier 1: Remote Agent Cache (Source)
- **Location**: `~/.claude-mpm/cache/remote-agents/`
- **Structure**: Organized by repository:
  ```
  ~/.claude-mpm/cache/remote-agents/
  ├── claude-mpm/
  │   ├── mpm-agent-manager.md
  │   ├── mpm-skills-manager.md
  │   └── BASE-AGENT.md
  ├── engineer/
  │   ├── python-engineer.md
  │   ├── javascript-engineer.md
  │   └── ...
  ├── qa/
  │   ├── qa.md
  │   ├── web-qa.md
  │   └── api-qa.md
  └── universal/
      ├── research.md
      ├── content-agent.md
      └── ...
  ```
- **Purpose**: Downloaded/synced from Git repositories during startup
- **Management**: Read-only cache maintained by `GitSourceManager`

#### Tier 2: Virtual Deployment State (Active)
- **Location**: `.claude/agents/.mpm_deployment_state`
- **Format**: JSON file tracking:
  - `deployment_hash`: Unique hash of current deployment
  - `agent_count`: Total agents (64 in current session)
  - `last_check_time`: Timestamp of last dependency check
  - `last_check_results`: Dependency satisfaction per agent
- **Purpose**: Tracks which cached agents are "virtually deployed" into Claude Code session
- **Key Insight**: **NO physical `.md` files are created in `.claude/agents/`**

### Framework Loader Agent Discovery Process

The `FrameworkLoader` in `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/framework_loader.py` discovers agents for the "Available Agent Capabilities" section via:

**Step 1: Get Deployed Agents** (lines 265-273)
```python
def _get_deployed_agents(self) -> Set[str]:
    """Get deployed agents with caching."""
    cached = self._cache_manager.get_deployed_agents()
    if cached is not None:
        return cached

    deployed = self.agent_loader.get_deployed_agents()
    self._cache_manager.set_deployed_agents(deployed)
    return deployed
```

**Step 2: Agent Loader Scans** (lines 21-48 in `agent_loader.py`)
```python
def get_deployed_agents(self) -> Set[str]:
    """Get a set of deployed agent names from .claude/agents/ directories."""
    deployed = set()

    # Check multiple locations for deployed agents
    agents_dirs = [
        Path.cwd() / ".claude" / "agents",  # Project-specific agents
        Path.home() / ".claude" / "agents",  # User's system agents
    ]

    for agents_dir in agents_dirs:
        if agents_dir.exists():
            for agent_file in agents_dir.glob("*.md"):
                if not agent_file.name.startswith("."):
                    deployed.add(agent_file.stem)

    return deployed
```

**Step 3: Generate Capabilities Section** (lines 365-408 in `framework_loader.py`)
```python
def _generate_agent_capabilities_section(self) -> str:
    """Generate agent capabilities section with caching."""
    # ... cache check ...

    # Get deployed agents from .claude/agents/
    deployed_agents = []
    agents_dirs = [
        Path.cwd() / ".claude" / "agents",
        Path.home() / ".claude" / "agents",
    ]

    for agents_dir in agents_dirs:
        if agents_dir.exists():
            for agent_file in agents_dir.glob("*.md"):
                if not agent_file.name.startswith("."):
                    agent_data = self._parse_agent_metadata(agent_file)
                    if agent_data:
                        deployed_agents.append(agent_data)

    # Generate capabilities section
    section = self.capability_generator.generate_capabilities_section(
        deployed_agents, local_agents
    )
```

**Critical Finding**: The framework loader generates the "Available Agent Capabilities" section by:
1. Looking for physical `.md` files in `.claude/agents/` directories
2. Parsing YAML frontmatter from those files
3. Formatting them into the system prompt

**However**: In the current deployment, `.claude/agents/` contains:
- `.dependency_cache` file
- `.mpm_deployment_state` file
- **NO `.md` agent files**

This means the 45 agents in the current session are coming from a **cached/stale capabilities section**, NOT from live agent file scanning.

---

## The Mismatch Problem

### Current Session State

**File System Reality**:
```bash
$ ls -la ~/.claude/agents/
total 16
drwxr-xr-x@  3 masa  staff    96 Dec  2 16:50 .
drwx------@ 16 masa  staff   512 Dec  2 17:12 ..
-rw-r--r--@  1 masa  staff  6148 Dec  1 09:39 .DS_Store

$ ls -la .claude/agents/
total 160
drwxr-xr-x@  4 masa  staff    128 Dec  2 16:50 .
drwxr-xr-x@ 18 masa  staff    576 Dec  1 16:53 ..
-rw-r--r--@  1 masa  staff  58505 Dec  1 15:01 .dependency_cache
-rw-r--r--@  1 masa  staff  18397 Dec  1 15:01 .mpm_deployment_state
```

**Virtual Deployment State** (`.claude/agents/.mpm_deployment_state`):
- **64 agents tracked** with full dependency satisfaction data
- Agents include: `gcp-ops`, `agent-manager`, `clerk-ops`, `golang-engineer`, `java-engineer`, `ops`, `mpm-agent-manager`, `version-control`, `web-ui`, `qa`, `refactoring-engineer`, `react-engineer`, `mpm-skills-manager`, `memory-manager`, `content-agent`, `nextjs-engineer`, `dart-engineer`, `research`, `product-owner`, `javascript-engineer`, `web-qa`, `project-organizer`, `python-engineer`, `engineer`, `documentation`, `typescript-engineer`, `tauri-engineer`, `rust-engineer`, `api-qa`, `agentic-coder-optimizer`, `vercel-ops`, `data-engineer`, `svelte-engineer`, `code-analyzer`, `security`, `ruby-engineer`, `imagemagick`, `php-engineer`, `ticketing`, and more

**Current Claude Session**:
- **45 agents** listed in "Available Agent Capabilities" section (shown in system prompt)
- This is likely from a **cached capabilities section** generated during a previous deployment

### The `_is_agent_deployed()` Problem

**Method Location**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/agent_state_manager.py` (lines 265-298)

**What It Does**:
```python
def _is_agent_deployed(self, agent_id: str) -> bool:
    """Check if agent is deployed in current project or user directory."""
    # For hierarchical IDs, check both full ID and leaf name
    agent_file_names = [f"{agent_id}.md"]

    if "/" in agent_id:
        leaf_name = agent_id.split("/")[-1]
        agent_file_names.append(f"{leaf_name}.md")

    # Check .claude-mpm/agents/ directory (project level)
    project_agents_dir = Path.cwd() / ".claude-mpm" / "agents"
    if project_agents_dir.exists():
        for agent_file_name in agent_file_names:
            agent_file = project_agents_dir / agent_file_name
            if agent_file.exists():
                return True

    # Check ~/.claude/agents/ directory (user level)
    user_agents_dir = Path.home() / ".claude" / "agents"
    if user_agents_dir.exists():
        for agent_file_name in agent_file_names:
            agent_file = user_agents_dir / agent_file_name
            if agent_file.exists():
                return True

    return False
```

**What It Checks**:
1. `.claude-mpm/agents/{agent_id}.md` (project-level, physical files)
2. `~/.claude/agents/{agent_id}.md` (user-level, physical files)

**What It DOESN'T Check**:
1. **Remote agent cache**: `~/.claude-mpm/cache/remote-agents/`
2. **Virtual deployment state**: `.claude/agents/.mpm_deployment_state`
3. **Cached capabilities**: Framework loader's cached section

**Result**: Returns `False` for ALL agents, causing them to show as "Available" instead of "Installed"

---

## Where the 45 Agents Come From

The 45 agents in the current Claude Code session's "Available Agent Capabilities" section are loaded from a **cached capabilities section** generated by the `FrameworkLoader`.

**Evidence**:

1. **Cache Location**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/framework_loader.py` (lines 365-408)
   - The `_generate_agent_capabilities_section()` method has caching:
   ```python
   # Try cache first
   cached_capabilities = self._cache_manager.get_capabilities()
   if cached_capabilities is not None:
       return cached_capabilities
   ```

2. **Cache TTL**: Capabilities cache has a 60-second TTL (line 182):
   ```python
   self.CAPABILITIES_CACHE_TTL = 60
   ```

3. **Stale Cache Problem**: If the capabilities section was generated when physical `.md` files existed in `.claude/agents/`, that cached section persists even after:
   - Physical files are removed
   - Virtual deployment replaces physical deployment
   - Agent state changes

4. **Current Session State**: The 45 agents in the system prompt match neither:
   - The 64 agents in `.mpm_deployment_state` (too few)
   - The 0 physical agents in `.claude/agents/` (too many)
   - This suggests a **stale cache from a previous deployment model**

---

## Solution Analysis

### Option 1: Check Virtual Deployment State (RECOMMENDED)

**Approach**: Update `_is_agent_deployed()` to read `.mpm_deployment_state` file

**Implementation**:
```python
def _is_agent_deployed(self, agent_id: str) -> bool:
    """Check if agent is deployed (physical or virtual)."""
    # Check virtual deployment state first (new deployment model)
    deployment_state_paths = [
        Path.cwd() / ".claude" / "agents" / ".mpm_deployment_state",
        Path.home() / ".claude" / "agents" / ".mpm_deployment_state",
    ]

    for state_path in deployment_state_paths:
        if state_path.exists():
            try:
                import json
                with state_path.open() as f:
                    state = json.load(f)

                # Check if agent is in last_check_results.agents
                agents = state.get("last_check_results", {}).get("agents", {})
                if agent_id in agents:
                    return True

                # Also check leaf name for hierarchical IDs
                if "/" in agent_id:
                    leaf_name = agent_id.split("/")[-1]
                    if leaf_name in agents:
                        return True
            except Exception as e:
                self.logger.debug(f"Failed to read deployment state: {e}")

    # Fallback: Check physical files (legacy deployment model)
    agent_file_names = [f"{agent_id}.md"]
    if "/" in agent_id:
        leaf_name = agent_id.split("/")[-1]
        agent_file_names.append(f"{leaf_name}.md")

    # Check .claude-mpm/agents/ directory
    project_agents_dir = Path.cwd() / ".claude-mpm" / "agents"
    if project_agents_dir.exists():
        for agent_file_name in agent_file_names:
            if (project_agents_dir / agent_file_name).exists():
                return True

    # Check ~/.claude/agents/ directory
    user_agents_dir = Path.home() / ".claude" / "agents"
    if user_agents_dir.exists():
        for agent_file_name in agent_file_names:
            if (user_agents_dir / agent_file_name).exists():
                return True

    return False
```

**Pros**:
- Correctly detects virtually deployed agents (the new architecture)
- Maintains backward compatibility with physical file deployments
- Aligns with actual deployment state

**Cons**:
- Adds dependency on `.mpm_deployment_state` format
- Requires JSON parsing for every check (could cache)
- Doesn't explain the 45 vs. 64 agent discrepancy

### Option 2: Check Remote Agent Cache

**Approach**: Update `_is_agent_deployed()` to check if agent exists in remote cache

**Implementation**:
```python
def _is_agent_deployed(self, agent_id: str) -> bool:
    """Check if agent is available in cache or deployed."""
    # Check remote agent cache
    remote_cache_root = Path.home() / ".claude-mpm" / "cache" / "remote-agents"
    if remote_cache_root.exists():
        # Search all subdirectories for agent
        for agent_file in remote_cache_root.rglob(f"{agent_id}.md"):
            return True

        # Also check leaf name for hierarchical IDs
        if "/" in agent_id:
            leaf_name = agent_id.split("/")[-1]
            for agent_file in remote_cache_root.rglob(f"{leaf_name}.md"):
                return True

    # ... rest of existing checks ...
```

**Pros**:
- Detects agents synced from remote sources
- Simple file-based check (no JSON parsing)

**Cons**:
- Conflates "cached" with "deployed" (semantically incorrect)
- Could show agents as "Installed" when they're only downloaded, not active
- Doesn't align with virtual deployment model

### Option 3: Synchronize Cache and Deployment State

**Approach**: Ensure capabilities cache is cleared when deployment state changes

**Implementation**:
- Clear capabilities cache when `.mpm_deployment_state` is updated
- Force framework loader to regenerate capabilities section
- Ensure system prompt reflects actual deployed agents

**Pros**:
- Addresses root cause (stale cache)
- Ensures system prompt accuracy

**Cons**:
- Doesn't fix the status detection in `configure` command
- Requires changes across multiple components
- More complex implementation

---

## Recommendations

### Primary Recommendation: Option 1 (Check Virtual Deployment State)

**Rationale**:
1. **Aligns with new architecture**: Virtual deployment via `.mpm_deployment_state` is the current deployment model
2. **Accurate status detection**: Shows agents as "Installed" only when they're actually active in Claude sessions
3. **Backward compatible**: Falls back to physical file checks for legacy deployments
4. **Clear semantics**: "Installed" = actively loaded in Claude Code, not just cached

**Implementation Priority**: HIGH
**Complexity**: MEDIUM
**Risk**: LOW (backward compatible)

### Secondary Recommendation: Investigate Cache/Session Discrepancy

**Issue**: 45 agents in current session vs. 64 agents in deployment state

**Investigation Needed**:
1. Why are only 45 agents in "Available Agent Capabilities" when 64 are tracked?
2. Is the capabilities section generated from a stale cache?
3. Should we force cache invalidation on Claude MPM startup?
4. How do we ensure system prompt reflects actual deployment state?

**Next Steps**:
1. Check capabilities cache location: `_cache_manager.get_capabilities()`
2. Verify cache TTL and invalidation triggers
3. Test capabilities regeneration after cache clear
4. Compare cached section with fresh generation from `.mpm_deployment_state`

### Tertiary Recommendation: Documentation Update

**Action**: Document the two-tier deployment architecture clearly

**Content Needed**:
1. **Architecture Overview**: Remote cache → Virtual deployment → Claude session
2. **Deployment State Format**: Explain `.mpm_deployment_state` structure
3. **Status Detection Logic**: How "Installed" vs. "Available" is determined
4. **Cache Behavior**: When capabilities are cached and regenerated
5. **Troubleshooting Guide**: What to check when status seems wrong

**Files to Update**:
- `/Users/masa/Projects/claude-mpm/docs/AGENTS_DEPLOYMENT.md`
- `/Users/masa/Projects/claude-mpm/README.md` (architecture section)
- `/Users/masa/Projects/claude-mpm/docs/troubleshooting/agent-status.md` (new)

---

## Technical Debt Identified

### Issue 1: Dual Deployment Models

**Problem**: The codebase supports both:
- Legacy physical file deployment (`.claude/agents/{agent}.md`)
- New virtual deployment (`.mpm_deployment_state`)

**Impact**: Confusion about which model is canonical, inconsistent status detection

**Recommendation**: Phase out physical deployment or clearly document when each is used

### Issue 2: Cache Invalidation Gaps

**Problem**: Capabilities cache can become stale when:
- Agents are deployed/undeployed
- Deployment state changes
- Physical files are removed

**Impact**: System prompt may not reflect actual agent availability

**Recommendation**: Implement robust cache invalidation on deployment state changes

### Issue 3: Multiple Sources of Truth

**Problem**: Agent availability checked in multiple places:
- Physical files in `.claude/agents/`
- Physical files in `.claude-mpm/agents/`
- Remote cache in `~/.claude-mpm/cache/remote-agents/`
- Virtual state in `.mpm_deployment_state`
- Cached capabilities section

**Impact**: Different parts of the system may have inconsistent views of agent status

**Recommendation**: Establish single source of truth (prefer `.mpm_deployment_state`)

---

## Files Analyzed

| File | Lines | Purpose |
|------|-------|---------|
| `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/agent_state_manager.py` | 265-298 | `_is_agent_deployed()` method |
| `/Users/masa/Projects/claude-mpm/src/claude_mpm/cli/commands/configure.py` | 950-999 | Agent table display logic |
| `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/framework_loader.py` | 1-542 | Framework loading and agent discovery |
| `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/framework/loaders/agent_loader.py` | 1-211 | Agent file scanning and loading |
| `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/framework/formatters/capability_generator.py` | 1-368 | Capabilities section generation |
| `.claude/agents/.mpm_deployment_state` | 1-840 | Virtual deployment state (64 agents) |

---

## Conclusion

The agent status detection issue is a **symptom of an architectural transition** from physical file-based deployment to virtual state-based deployment. The fix requires updating `_is_agent_deployed()` to check the `.mpm_deployment_state` file in addition to (or instead of) physical files.

Additionally, the discrepancy between the 45 agents in the current Claude session and the 64 agents in the deployment state suggests a **stale capabilities cache** that needs investigation and proper invalidation logic.

**Immediate Action Required**:
1. Implement Option 1 (check virtual deployment state) in `_is_agent_deployed()`
2. Investigate capabilities cache staleness
3. Document the two-tier deployment architecture
4. Add tests for virtual deployment detection

**Long-Term Actions**:
1. Establish `.mpm_deployment_state` as single source of truth
2. Implement robust cache invalidation
3. Phase out or clearly document physical file deployment
4. Add telemetry to track deployment model usage
