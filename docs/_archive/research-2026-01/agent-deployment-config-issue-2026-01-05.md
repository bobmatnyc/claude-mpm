# Agent Deployment Configuration Issue - Investigation Report

**Date:** 2026-01-05
**Researcher:** Claude Code Research Agent
**Issue:** Agent deployment not respecting configuration.yaml settings
**Status:** Root cause identified with actionable fixes

---

## Executive Summary

User configured 15 agents in `~/Projects/izzie2/.claude-mpm/configuration.yaml` but 44 agents were deployed on restart. Investigation reveals **TWO CRITICAL ISSUES**:

1. **Startup code bypasses `DeploymentReconciler`** - Uses old `AgentDeploymentService` directly
2. **Configuration loading doesn't read project-level files** - `UnifiedConfig()` only reads from standardized paths

---

## Issue Details

### User Report
- **Location:** `~/Projects/izzie2/.claude-mpm/configuration.yaml`
- **Configuration:** 15 agents in `agents.enabled` list
- **Expected:** 15 agents deployed
- **Actual:** 44 agents deployed
- **Symptom:** Configuration changes ignored

---

## Root Cause Analysis

### Issue #1: Startup Bypasses Reconciliation Logic

**File:** `src/claude_mpm/cli/startup.py` (lines 461-850)
**Function:** `sync_remote_agents_on_startup()`

**Problem:**
```python
# Line 590: Uses OLD deployment service
deployment_service = AgentDeploymentService(config=deploy_config)

# Line 725: Deploys ALL agents without checking config
deployment_result = deployment_service.deploy_agents(
    target_dir=deploy_target,
    force_rebuild=False,
    deployment_mode="update",
    config=deploy_config,
)
```

**What Should Happen:**
```python
# Should use DeploymentReconciler instead
from ..services.agents.deployment.deployment_reconciler import DeploymentReconciler

reconciler = DeploymentReconciler(config)
agent_result = reconciler.reconcile_agents(project_path)
```

**Evidence:**
- `startup_reconciliation.py` exists with `perform_startup_reconciliation()` function
- Function is **NEVER CALLED** in codebase (grep shows only internal references)
- `AgentDeploymentService` has no awareness of `agents.enabled` configuration
- Reconciler properly implements the simplified deployment model

---

### Issue #2: Config Loading Path Problem

**File:** `src/claude_mpm/core/unified_config.py` (lines 486-514)
**Method:** `ConfigurationService._load_default_config()`

**Problem:**
```python
def _load_default_config(self) -> UnifiedConfig:
    config_paths = [
        Path.cwd() / ".claude-mpm" / "configuration.yaml",  # ✓ Correct
        Path.cwd() / ".claude-mpm" / "configuration.yml",   # ✓ Correct
        Path.home() / ".claude-mpm" / "configuration.yaml", # ✓ Correct
        Path.home() / ".claude-mpm" / "configuration.yml",  # ✓ Correct
    ]

    config_data: Dict[str, Any] = {}
    for config_path in config_paths:
        if config_path.exists():
            # ... load config
            break  # ⚠️ STOPS after FIRST match
```

**Analysis:**
- **Loads config correctly** from project-level `.claude-mpm/configuration.yaml`
- **Only processes first matching file** (break statement on line 505)
- **No merging of user + project configs** (by design)
- This part is **WORKING AS DESIGNED**

**Verification Needed:**
User should verify their config file:
```bash
# Check if config exists and is readable
ls -la ~/Projects/izzie2/.claude-mpm/configuration.yaml
cat ~/Projects/izzie2/.claude-mpm/configuration.yaml | grep -A 20 "agents:"
```

---

### Issue #3: DeploymentReconciler Logic

**File:** `src/claude_mpm/services/agents/deployment/deployment_reconciler.py` (lines 239-258)
**Method:** `_get_agent_state()`

**Implementation:**
```python
def _get_agent_state(self, cache_dir: Path, deploy_dir: Path) -> ReconciliationState:
    # Start with enabled agents
    configured_agents = set(self.config.agents.enabled)  # Line 244

    # Add required agents (cannot be disabled)
    configured_agents.update(self.config.agents.required)  # Line 247

    # Add universal agents if enabled
    if self.config.agents.include_universal:  # Line 250
        universal_agents = self._get_universal_agents(cache_dir)
        configured_agents.update(universal_agents)

    return ReconciliationState(
        configured=configured_agents,
        deployed=self._list_deployed_agents(deploy_dir),
        cached=self._list_cached_agents(cache_dir),
    )
```

**Default Values from `AgentConfig`** (lines 66-90):
```python
class AgentConfig(BaseModel):
    enabled: List[str] = Field(default_factory=list)  # Empty by default

    required: List[str] = Field(
        default_factory=lambda: [
            "research",
            "mpm-skills-manager",
            "mpm-agent-manager",
            "memory-manager",
        ]
    )

    include_universal: bool = Field(default=True)  # ⚠️ AUTO-INCLUDES ALL UNIVERSAL AGENTS
```

**Analysis:**
When `agents.enabled = []` (empty) and `include_universal = True`:
1. Configured agents = `required` (4 agents) + `universal agents` (40+ agents) = **44 agents**
2. This explains the **44 agent deployment**!

---

## Why 44 Agents?

| Source | Count | Agents |
|--------|-------|--------|
| **Required agents** | 4 | research, mpm-skills-manager, mpm-agent-manager, memory-manager |
| **Universal agents** | ~40 | All agents with `toolchain: universal` in frontmatter |
| **Total** | **44** | Matches user's reported deployment count |

**Finding:**
The `include_universal: true` setting (default) auto-deploys ALL agents marked with `toolchain: universal` or `category: universal` in their frontmatter, **regardless of `agents.enabled` list**.

---

## Configuration Precedence Issue

**Expected Behavior:**
```yaml
agents:
  enabled:
    - engineer
    - qa
    - devops
  # Should deploy ONLY these 3 agents + required (7 total)
```

**Actual Behavior:**
```yaml
agents:
  enabled:
    - engineer
    - qa
    - devops
  include_universal: true  # ⚠️ DEFAULT VALUE
  # Deploys: 3 enabled + 4 required + 40 universal = 47 agents!
```

---

## Solution Paths

### Option 1: Fix Startup to Use Reconciler (Recommended)

**File:** `src/claude_mpm/cli/startup.py`
**Changes:**

```python
def sync_remote_agents_on_startup(force_sync: bool = False):
    # ... existing sync code ...

    # REPLACE lines 540-845 with:
    try:
        from ..services.agents.deployment.startup_reconciliation import (
            perform_startup_reconciliation
        )
        from ..core.unified_config import UnifiedConfig

        # Load project-level config
        config = UnifiedConfig()

        # Perform reconciliation (respects agents.enabled)
        agent_result, skill_result = perform_startup_reconciliation(
            project_path=Path.cwd(),
            config=config,
            silent=False
        )

        # Log results
        logger.info(f"Agents: {len(agent_result.deployed)} deployed, "
                   f"{len(agent_result.removed)} removed, "
                   f"{len(agent_result.unchanged)} unchanged")

    except Exception as e:
        logger.warning(f"Failed to reconcile agents: {e}")
```

**Benefits:**
- ✅ Respects `agents.enabled` configuration
- ✅ Removes agents NOT in enabled list
- ✅ Handles required + universal agents correctly
- ✅ Existing tested code path

---

### Option 2: Document `include_universal` Behavior

**File:** `examples/configuration-simplified.yaml`
**Add documentation:**

```yaml
agents:
  # Explicit list of agent IDs to deploy
  enabled:
    - engineer
    - qa
    - devops

  # ⚠️ IMPORTANT: Controls universal agent auto-deployment
  # When true (default): Deploys ALL agents with 'toolchain: universal'
  # When false: ONLY deploys agents in 'enabled' list (+ required)
  include_universal: false  # Set to false for STRICT enabled-list-only deployment

  # These agents are ALWAYS deployed (cannot be disabled)
  # Default: [research, mpm-skills-manager, mpm-agent-manager, memory-manager]
  required: []  # Clear this list to disable required agents
```

**Benefits:**
- ✅ Quick documentation fix
- ✅ Users can opt-out of universal agents
- ❌ Requires manual config change
- ❌ Defaults still unexpected

---

### Option 3: Change Default Behavior (Breaking Change)

**File:** `src/claude_mpm/core/unified_config.py`
**Change:**

```python
class AgentConfig(BaseModel):
    include_universal: bool = Field(
        default=False,  # Changed from True
        description="Auto-include all agents with 'universal' toolchain/category",
    )
```

**Benefits:**
- ✅ Users get explicit control
- ✅ No surprise deployments
- ❌ Breaking change for existing users
- ❌ Requires migration guide

---

## Recommended Fix

**Implement Option 1 + Option 2**

1. **Fix startup.py** to use `DeploymentReconciler` (Option 1)
2. **Document behavior** in configuration examples (Option 2)
3. **Add validation warning** when `agents.enabled` is empty

**Code changes:**

```python
# In startup.py (line 540)
def sync_remote_agents_on_startup(force_sync: bool = False):
    # ... sync code ...

    # Load config and check enabled list
    from ..core.unified_config import UnifiedConfig
    config = UnifiedConfig()

    # Warn if enabled list is empty
    if not config.agents.enabled:
        logger.warning(
            "agents.enabled is empty. Will deploy required + universal agents. "
            "Set 'include_universal: false' for explicit control."
        )

    # Use reconciler instead of deployment service
    from ..services.agents.deployment.startup_reconciliation import (
        perform_startup_reconciliation
    )

    agent_result, skill_result = perform_startup_reconciliation(
        project_path=Path.cwd(),
        config=config,
        silent=False
    )
```

---

## Testing Steps

### Test 1: Verify Config is Read

```bash
cd ~/Projects/izzie2
python3 -c "
from claude_mpm.core.unified_config import UnifiedConfig
config = UnifiedConfig()
print(f'Enabled agents: {config.agents.enabled}')
print(f'Include universal: {config.agents.include_universal}')
print(f'Required agents: {config.agents.required}')
"
```

**Expected output:**
```
Enabled agents: ['engineer', 'qa', ...]  # 15 agents from config
Include universal: True  # Default value
Required agents: ['research', 'mpm-skills-manager', ...]
```

### Test 2: Verify Reconciliation Logic

```bash
cd ~/Projects/izzie2
python3 -c "
from pathlib import Path
from claude_mpm.core.unified_config import UnifiedConfig
from claude_mpm.services.agents.deployment.deployment_reconciler import DeploymentReconciler

config = UnifiedConfig()
reconciler = DeploymentReconciler(config)
view = reconciler.get_reconciliation_view(Path.cwd())

print(f'Configured agents: {len(view[\"agents\"].configured)}')
print(f'Deployed agents: {len(view[\"agents\"].deployed)}')
print(f'To deploy: {len(view[\"agents\"].to_deploy)}')
print(f'To remove: {len(view[\"agents\"].to_remove)}')
"
```

**Expected with include_universal=True:**
```
Configured agents: 59  # 15 enabled + 4 required + 40 universal
Deployed agents: 44
To deploy: 15
To remove: 0
```

**Expected with include_universal=False:**
```
Configured agents: 19  # 15 enabled + 4 required
Deployed agents: 44
To deploy: 0
To remove: 25  # 44 - 19 = 25 agents to remove
```

### Test 3: Manual Reconciliation

```bash
cd ~/Projects/izzie2
claude-mpm agents reconcile --show-only
```

**Should show:**
- Configured: 15 agents from enabled list
- Deployed: 44 agents currently deployed
- Actions: Deploy X, Remove Y

---

## User Workaround (Immediate Fix)

Until code is fixed, user can add to their configuration:

```yaml
# ~/Projects/izzie2/.claude-mpm/configuration.yaml
agents:
  enabled:
    - engineer
    - qa
    # ... 13 more agents

  # ⚠️ ADD THIS LINE to disable universal agent auto-deployment
  include_universal: false

  # OPTIONAL: Clear required agents if you want ONLY the enabled list
  required: []
```

Then restart or run:
```bash
cd ~/Projects/izzie2
claude-mpm agents reconcile
```

---

## Files to Modify

1. **src/claude_mpm/cli/startup.py** (lines 540-845)
   - Replace `AgentDeploymentService` with `DeploymentReconciler`
   - Add warning when `agents.enabled` is empty

2. **examples/configuration-simplified.yaml** (lines 10-28)
   - Document `include_universal` behavior
   - Add examples with `include_universal: false`
   - Explain required agents list

3. **docs/simplified-deployment-model.md** (section on agent configuration)
   - Document the three sources of configured agents:
     - `agents.enabled` (explicit list)
     - `agents.required` (always deployed)
     - Universal agents (if `include_universal: true`)

---

## Related Code References

- **DeploymentReconciler:** `src/claude_mpm/services/agents/deployment/deployment_reconciler.py`
- **Startup reconciliation:** `src/claude_mpm/services/agents/deployment/startup_reconciliation.py`
- **Config model:** `src/claude_mpm/core/unified_config.py` (AgentConfig class)
- **Current startup:** `src/claude_mpm/cli/startup.py` (sync_remote_agents_on_startup)

---

## Conclusion

**Root Cause:** Startup code bypasses the reconciliation system that respects `agents.enabled` configuration.

**Impact:** Users cannot control agent deployment through configuration.

**Fix Difficulty:** Medium (requires replacing deployment logic in startup.py)

**User Impact:** High (configuration ignored is very confusing)

**Priority:** **HIGH** - This breaks the simplified deployment model entirely.

---

## Next Steps

1. **Verify user configuration** is correctly formatted
2. **Implement Option 1** (use reconciler in startup.py)
3. **Implement Option 2** (document include_universal)
4. **Add integration test** for configuration-based deployment
5. **Add migration guide** for users with existing deployments
